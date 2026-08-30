import re
import json
import uuid
import statistics
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import async_session_factory
from models.entities import (
    Publication, PostMetricSnapshot, Content, Asset, ContentVariant,
    Clip, Carousel, ContentBrief, PerformanceInsight, ContentPattern,
    ContentRecommendation, Experiment, Job
)
from services.queue_service import queue_service
from services.ai_service import ai_service
from utils.logging import get_logger

logger = get_logger("IntelligenceService")

class IntelligenceService:

    # --------------------------------------------------------------------------
    # 1. Feature Extraction & Normalization
    # --------------------------------------------------------------------------

    def classify_hook(self, text: Optional[str]) -> str:
        """
        Classifies hook text into 8 canonical archetypes:
        QUESTION | STATISTIC | HOW_TO | PROBLEM | STORY | CURIOSITY | CONTRARIAN | DIRECT_CLAIM
        """
        if not text or not text.strip():
            return "DIRECT_CLAIM"

        t = text.strip().lower()

        # 1. Contrarian / Hot Take Hook
        if any(w in t for w in ["unpopular opinion", "why you shouldn't", "is dead", "nobody needs", "lies you were told"]):
            return "CONTRARIAN"

        # 2. Problem / Pain Point Hook
        if any(w in t for w in ["struggling with", "stop doing", "the biggest mistake", "worst error", "wrong way", "ruining your"]):
            return "PROBLEM"

        # 3. How-to / Tutorial Hook
        if t.startswith(("how to ", "step by step", "guide to ", "the formula to ", "tutorial:")):
            return "HOW_TO"

        # 4. Curiosity / Revelation Hook
        if any(w in t for w in ["the secret", "hidden trick", "nobody talks about", "i discovered", "what happened when"]):
            return "CURIOSITY"

        # 5. Story / Narrative Hook
        if any(w in t for w in ["years ago", "when i started", "last week i", "my journey", "how i built", "story time"]):
            return "STORY"

        # 6. Question Hook
        if "?" in t or t.startswith(("why ", "what if ", "how come ", "did you know", "is it possible")):
            return "QUESTION"

        # 7. Statistic / Metric Hook
        if re.search(r'\b\d+(\.\d+)?%|\b\d+\s*(x|million|billion|thousand|k|m)\b|\bstatistics?\b|\bstudy\b', t):
            return "STATISTIC"

        # 8. Direct Value Claim (Default)
        return "DIRECT_CLAIM"

    def normalize_topic(self, topic: Optional[str]) -> str:
        """
        Canonicalizes topic variations into normalized cluster slugs.
        e.g. 'AI agents', 'AI agent systems', 'autonomous agents' -> 'ai-agents'
        """
        if not topic or not topic.strip():
            return "general"

        t = topic.lower().strip()
        t = re.sub(r'[^\w\s-]', '', t)

        # Synonym clusters
        if any(k in t for k in ["ai agent", "autonomous agent", "agentic", "agent system"]):
            return "ai-agents"
        if any(k in t for k in ["llm", "large language model", "gpt", "gemini", "claude", "openai"]):
            return "language-models"
        if any(k in t for k in ["repurpose", "repurposing", "content workflow", "content strategy"]):
            return "content-repurposing"
        if any(k in t for k in ["short form", "shorts", "reels", "tiktok video", "clips"]):
            return "short-form-video"
        if any(k in t for k in ["carousel", "slide deck", "infographic", "linkedin document"]):
            return "carousels"
        if any(k in t for k in ["automation", "scheduler", "pipeline", "infrastructure"]):
            return "workflow-automation"
        if any(k in t for k in ["growth", "distribution", "social media growth", "algorithm"]):
            return "audience-growth"

        # Default slugify
        return re.sub(r'[\s_]+', '-', t)[:40]

    def get_duration_bucket(self, duration_seconds: Optional[float]) -> str:
        """Categorizes duration into standard analytical buckets."""
        if duration_seconds is None or duration_seconds <= 0:
            return "UNKNOWN"
        if duration_seconds <= 15:
            return "0-15s"
        if duration_seconds <= 30:
            return "15-30s"
        if duration_seconds <= 60:
            return "30-60s"
        if duration_seconds <= 120:
            return "60-120s"
        return "120s+"

    def extract_features(
        self,
        pub: Publication,
        content: Optional[Content],
        clip: Optional[Clip],
        carousel: Optional[Carousel],
        snapshot: Optional[PostMetricSnapshot]
    ) -> Dict[str, Any]:
        """Extracts structured feature vector and localized posting parameters for a published post."""
        # 1. Local Timezone Handling
        pub_tz = ZoneInfo(pub.timezone or "UTC") if pub.timezone else ZoneInfo("UTC")
        pub_time = pub.published_at or pub.scheduled_at or pub.created_at
        if pub_time.tzinfo is None:
            local_time = pub_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(pub_tz)
        else:
            local_time = pub_time.astimezone(pub_tz)

        day_name = local_time.strftime("%A")
        hour_val = local_time.hour
        hour_bucket = f"{hour_val:02d}:00-{(hour_val+1)%24:02d}:00"

        # 2. Hook and Text Extraction
        hook_candidate = pub.title
        if clip and clip.hook:
            hook_candidate = clip.hook
        elif carousel and carousel.slides:
            hook_candidate = carousel.slides[0].headline or carousel.slides[0].body or pub.title

        hook_type = self.classify_hook(hook_candidate)

        # 3. Topic Extraction
        raw_topic = "general"
        if content and content.briefs:
            b_topics = content.briefs[0].topics
            if b_topics:
                raw_topic = b_topics[0]
        topic = self.normalize_topic(raw_topic)

        # 4. Duration
        duration_sec = None
        if clip:
            duration_sec = clip.duration
        elif content and content.assets and content.assets[0].duration:
            duration_sec = float(content.assets[0].duration)
        dur_bucket = self.get_duration_bucket(duration_sec)

        # 5. Format & Template
        c_type = content.content_type if content else "TEXT"
        if clip:
            format_type = "CLIP"
        elif carousel:
            format_type = "CAROUSEL"
        else:
            format_type = c_type

        # 6. Additional Signals
        desc = pub.description or ""
        tags = pub.tags or []
        has_cta = any(k in desc.lower() for k in ["subscribe", "follow", "comment", "link in bio", "share", "read more", "check out"])
        has_stat = bool(re.search(r'\b\d+%\b|\b\d+\s*(k|m|x)\b', desc))

        # 7. Metrics
        er = None
        views = None
        engagements = None
        if snapshot:
            views = snapshot.views
            engagements = snapshot.engagements
            denom = snapshot.reach if (snapshot.reach and snapshot.reach > 0) else (snapshot.impressions if (snapshot.impressions and snapshot.impressions > 0) else None)
            if denom and denom > 0:
                num = (snapshot.likes or 0) + (snapshot.comments or 0) + (snapshot.shares or 0) + (snapshot.saves or 0)
                er = round((num / denom) * 100.0, 2)

        return {
            "publication_id": pub.id,
            "content_id": content.id if content else None,
            "platform": pub.platform.lower(),
            "format_type": format_type,
            "content_type": c_type,
            "topic": topic,
            "hook_type": hook_type,
            "duration_seconds": duration_sec,
            "duration_bucket": dur_bucket,
            "day_of_week": day_name,
            "hour_of_day": hour_val,
            "hour_bucket": hour_bucket,
            "has_cta": has_cta,
            "has_stat": has_stat,
            "hashtag_count": len(tags),
            "carousel_template": carousel.template if carousel else None,
            "slide_count": len(carousel.slides) if carousel else 0,
            "views": views,
            "engagements": engagements,
            "engagement_rate": er
        }

    # --------------------------------------------------------------------------
    # 2. Statistical Baselines & Outlier Handling
    # --------------------------------------------------------------------------

    def compute_trimmed_median(self, values: List[float], trim_ratio: float = 0.05) -> Optional[float]:
        """Calculates robust median while trimming extreme distribution tails."""
        valid = [v for v in values if v is not None and v >= 0]
        if not valid:
            return None
        valid.sort()
        n = len(valid)
        if n <= 2:
            return round(statistics.median(valid), 2)

        trim_count = int(n * trim_ratio)
        trimmed = valid[trim_count : n - trim_count] if (n - 2 * trim_count) > 0 else valid
        return round(statistics.median(trimmed), 2)

    def derive_confidence(self, sample_size: int, ratio_or_diff: float) -> str:
        """Determines objective confidence level based strictly on evidence volume and effect size."""
        if sample_size < settings.MIN_RECOMMENDATION_SAMPLES:
            return "INSUFFICIENT_DATA"
        if sample_size >= 15 and abs(ratio_or_diff) >= 20.0:
            return "HIGH"
        if sample_size >= 8 and abs(ratio_or_diff) >= 10.0:
            return "MEDIUM"
        return "LOW"

    # --------------------------------------------------------------------------
    # 3. Anti-Hallucination Claim Validation
    # --------------------------------------------------------------------------

    def verify_and_sanitize_claim(
        self,
        ai_claim: str,
        evidence: Dict[str, Any],
        fallback_summary: str
    ) -> str:
        """
        Scans AI generated claims for numbers and verifies every number against real evidence.
        Rejects/replaces hallucinated statistics with canonical correlation phrasing.
        """
        # Strict correlation language replacement
        sanitized = re.sub(r'\bcauses\b|\bcaused\b|\bcausing\b', 'was associated with', ai_claim, flags=re.IGNORECASE)

        # Extract all integer/float numbers from AI text
        found_numbers = re.findall(r'\b\d+(?:\.\d+)?\b', sanitized)

        # Build set of valid numbers from evidence dictionary
        valid_nums = set()
        for k, v in evidence.items():
            if isinstance(v, (int, float)):
                valid_nums.add(round(float(v), 1))
                valid_nums.add(round(float(v), 0))
                valid_nums.add(int(v))

        # If AI mentions arbitrary foreign numbers not in evidence, revert to deterministic fallback
        for num_str in found_numbers:
            val = float(num_str)
            # allow common small words/years or check presence in evidence
            if val in [1, 2, 3, 4, 5, 2024, 2025, 2026]:
                continue
            is_valid = any(abs(val - vn) <= 0.5 for vn in valid_nums)
            if not is_valid:
                logger.warning(f"Anti-hallucination guard rejected claim containing invalid number {val}. Falling back to canonical text.")
                return fallback_summary

        return sanitized

    # --------------------------------------------------------------------------
    # 4. Pattern Detection, Recommendations & Content Gaps
    # --------------------------------------------------------------------------

    async def run_full_analysis(self, db: AsyncSession = None) -> Dict[str, Any]:
        """
        Executes full incremental content intelligence pipeline:
        Feature Extraction -> Baselines -> Pattern Detection -> Recommendations -> Persistence.
        """
        async with async_session_factory() as session:
            # 1. Fetch published publications and associated relational assets
            res = await session.execute(
                select(Publication)
                .where(Publication.status == "PUBLISHED")
                .order_by(Publication.published_at.desc())
            )
            publications = res.scalars().all()

            if not publications:
                logger.info("No published publications found for intelligence analysis.")
                return {"status": "completed", "analyzed_count": 0, "sufficient_data": False}

            # 2. Extract feature vectors
            features_list: List[Dict[str, Any]] = []
            for pub in publications:
                # Content
                c_res = await session.execute(select(Content).where(Content.id == pub.content_id))
                content = c_res.scalar_one_or_none()

                # Clip
                clip = None
                if pub.variant_id:
                    cv_res = await session.execute(select(Clip).where(Clip.id == pub.variant_id))
                    clip = cv_res.scalar_one_or_none()

                # Carousel
                carousel = None
                if content and content.carousels:
                    carousel = content.carousels[0]

                # Latest Snapshot
                snap_res = await session.execute(
                    select(PostMetricSnapshot)
                    .where(PostMetricSnapshot.publication_id == pub.id)
                    .order_by(PostMetricSnapshot.captured_at.desc())
                    .limit(1)
                )
                snapshot = snap_res.scalar_one_or_none()

                feat = self.extract_features(pub, content, clip, carousel, snapshot)
                features_list.append(feat)

            total_posts = len(features_list)
            is_sufficient = total_posts >= settings.MIN_RECOMMENDATION_SAMPLES

            # 3. Calculate Account Baselines
            all_ers = [f["engagement_rate"] for f in features_list if f["engagement_rate"] is not None]
            all_views = [float(f["views"]) for f in features_list if f["views"] is not None]

            account_median_er = self.compute_trimmed_median(all_ers, settings.OUTLIER_TRIM_PERCENTILE)
            account_median_views = self.compute_trimmed_median(all_views, settings.OUTLIER_TRIM_PERCENTILE)

            # 4. Clean old insights & recommendations for atomic idempotency
            await session.execute(delete(PerformanceInsight))
            await session.execute(delete(ContentPattern))
            await session.execute(delete(ContentRecommendation))
            await session.commit()

            insights_to_add: List[PerformanceInsight] = []
            patterns_to_add: List[ContentPattern] = []
            recs_to_add: List[ContentRecommendation] = []

            # 5. Cold-Start / Insufficient Data Guardrail
            if not is_sufficient or account_median_er is None:
                logger.info(f"Insufficient historical data ({total_posts}/{settings.MIN_RECOMMENDATION_SAMPLES} posts). Generating cold-start guidance.")
                cold_rec = ContentRecommendation(
                    id=f"rec_cold_{uuid.uuid4().hex[:8]}",
                    type="EXPERIMENT_SUGGESTION",
                    scope="ACCOUNT",
                    title="Publish more content to unlock AI intelligence",
                    recommendation_text=f"Publish at least {settings.MIN_RECOMMENDATION_SAMPLES} posts across your channels to enable evidence-backed content intelligence.",
                    why_text=f"Reflow requires a minimum sample size of {settings.MIN_RECOMMENDATION_SAMPLES} historical publications to produce reliable, statistically sound pattern analysis without guessing.",
                    action_type="CREATE_POST",
                    evidence_json=json.dumps({"total_posts": total_posts, "required_posts": settings.MIN_RECOMMENDATION_SAMPLES}),
                    sample_size=total_posts,
                    confidence="INSUFFICIENT_DATA",
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                )
                session.add(cold_rec)
                await session.commit()
                return {
                    "status": "completed",
                    "analyzed_count": total_posts,
                    "sufficient_data": False,
                    "account_baseline_er": account_median_er
                }

            # ------------------------------------------------------------------
            # 6. Hook Performance Analysis
            # ------------------------------------------------------------------
            hooks_map: Dict[str, List[float]] = {}
            for f in features_list:
                hk = f["hook_type"]
                if f["engagement_rate"] is not None:
                    hooks_map.setdefault(hk, []).append(f["engagement_rate"])

            best_hook = None
            best_hook_ratio = 0.0

            for hk, er_list in hooks_map.items():
                if len(er_list) >= 2:
                    med_er = self.compute_trimmed_median(er_list)
                    if med_er and account_median_er and account_median_er > 0:
                        delta = round(((med_er - account_median_er) / account_median_er) * 100.0, 1)
                        ratio = round(med_er / account_median_er, 2)
                        is_pos = delta >= 0

                        pattern = ContentPattern(
                            id=f"pat_hk_{uuid.uuid4().hex[:8]}",
                            pattern_type="HOOK",
                            feature_name="hook_type",
                            feature_value=hk,
                            sample_size=len(er_list),
                            median_engagement_rate=med_er,
                            correlation_ratio=ratio,
                            is_positive=is_pos,
                            evidence_json=json.dumps({"sample_size": len(er_list), "median_er": med_er, "baseline_er": account_median_er, "delta_pct": delta}),
                            created_at=datetime.utcnow()
                        )
                        patterns_to_add.append(pattern)

                        if ratio > best_hook_ratio and len(er_list) >= 3:
                            best_hook = hk
                            best_hook_ratio = ratio

            if best_hook and best_hook_ratio >= 1.15:
                hk_count = len(hooks_map[best_hook])
                hk_er = self.compute_trimmed_median(hooks_map[best_hook])
                delta_pct = round(((hk_er - account_median_er) / account_median_er) * 100.0, 1)
                conf = self.derive_confidence(hk_count, delta_pct)

                recs_to_add.append(ContentRecommendation(
                    id=f"rec_hk_{uuid.uuid4().hex[:8]}",
                    type="BEST_HOOK",
                    scope="ACCOUNT",
                    title=f"Prioritize {best_hook.replace('_', ' ')} hooks",
                    recommendation_text=f"Incorporate more {best_hook.replace('_', ' ')} style openers in upcoming video scripts and carousels.",
                    why_text=f"Posts utilizing '{best_hook}' openers were associated with a {delta_pct}% higher median engagement rate ({hk_er}%) compared to the account baseline ({account_median_er}%).",
                    action_type="CREATE_CLIP",
                    evidence_json=json.dumps({"sample_size": hk_count, "median_er": hk_er, "baseline_er": account_median_er, "delta_pct": delta_pct}),
                    sample_size=hk_count,
                    confidence=conf,
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                ))

            # ------------------------------------------------------------------
            # 7. Duration Analysis (Video / Clips)
            # ------------------------------------------------------------------
            duration_map: Dict[str, List[float]] = {}
            for f in features_list:
                db_key = f["duration_bucket"]
                if db_key != "UNKNOWN" and f["engagement_rate"] is not None:
                    duration_map.setdefault(db_key, []).append(f["engagement_rate"])

            best_dur = None
            best_dur_ratio = 0.0

            for db_key, er_list in duration_map.items():
                if len(er_list) >= 2:
                    med_er = self.compute_trimmed_median(er_list)
                    if med_er and account_median_er and account_median_er > 0:
                        delta = round(((med_er - account_median_er) / account_median_er) * 100.0, 1)
                        ratio = round(med_er / account_median_er, 2)

                        patterns_to_add.append(ContentPattern(
                            id=f"pat_dur_{uuid.uuid4().hex[:8]}",
                            pattern_type="DURATION_BUCKET",
                            feature_name="duration_bucket",
                            feature_value=db_key,
                            sample_size=len(er_list),
                            median_engagement_rate=med_er,
                            correlation_ratio=ratio,
                            is_positive=delta >= 0,
                            evidence_json=json.dumps({"sample_size": len(er_list), "median_er": med_er, "baseline_er": account_median_er, "delta_pct": delta}),
                            created_at=datetime.utcnow()
                        ))

                        if ratio > best_dur_ratio and len(er_list) >= 3:
                            best_dur = db_key
                            best_dur_ratio = ratio

            if best_dur and best_dur_ratio >= 1.15:
                dur_count = len(duration_map[best_dur])
                dur_er = self.compute_trimmed_median(duration_map[best_dur])
                delta_pct = round(((dur_er - account_median_er) / account_median_er) * 100.0, 1)
                conf = self.derive_confidence(dur_count, delta_pct)

                recs_to_add.append(ContentRecommendation(
                    id=f"rec_dur_{uuid.uuid4().hex[:8]}",
                    type="BEST_DURATION",
                    scope="ACCOUNT",
                    title=f"Optimize clip length around {best_dur}",
                    recommendation_text=f"Aim for short-form video durations in the {best_dur} range.",
                    why_text=f"Clips in the '{best_dur}' duration bucket were associated with a {delta_pct}% higher median engagement rate ({dur_er}%) over historical publications.",
                    action_type="CREATE_CLIP",
                    evidence_json=json.dumps({"sample_size": dur_count, "median_er": dur_er, "baseline_er": account_median_er, "delta_pct": delta_pct}),
                    sample_size=dur_count,
                    confidence=conf,
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                ))

            # ------------------------------------------------------------------
            # 8. Posting Window Analysis
            # ------------------------------------------------------------------
            window_map: Dict[str, List[float]] = {}
            for f in features_list:
                w_key = f"{f['day_of_week']} {f['hour_bucket']}"
                if f["engagement_rate"] is not None:
                    window_map.setdefault(w_key, []).append(f["engagement_rate"])

            best_win = None
            best_win_ratio = 0.0

            for w_key, er_list in window_map.items():
                if len(er_list) >= 2:
                    med_er = self.compute_trimmed_median(er_list)
                    if med_er and account_median_er and account_median_er > 0:
                        delta = round(((med_er - account_median_er) / account_median_er) * 100.0, 1)
                        ratio = round(med_er / account_median_er, 2)
                        if ratio > best_win_ratio and len(er_list) >= 2:
                            best_win = w_key
                            best_win_ratio = ratio

            if best_win and best_win_ratio >= 1.2:
                win_count = len(window_map[best_win])
                win_er = self.compute_trimmed_median(window_map[best_win])
                delta_pct = round(((win_er - account_median_er) / account_median_er) * 100.0, 1)
                conf = self.derive_confidence(win_count, delta_pct)

                recs_to_add.append(ContentRecommendation(
                    id=f"rec_win_{uuid.uuid4().hex[:8]}",
                    type="BEST_POSTING_WINDOW",
                    scope="ACCOUNT",
                    title=f"Schedule next publication around {best_win}",
                    recommendation_text=f"Queue your upcoming scheduled content for the {best_win} local window.",
                    why_text=f"Posts published during '{best_win}' were associated with stronger historical engagement ({win_er}% vs {account_median_er}% baseline).",
                    action_type="SCHEDULE_POST",
                    evidence_json=json.dumps({"sample_size": win_count, "median_er": win_er, "baseline_er": account_median_er, "delta_pct": delta_pct}),
                    sample_size=win_count,
                    confidence=conf,
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                ))

            # ------------------------------------------------------------------
            # 9. Content Gaps Discovery
            # ------------------------------------------------------------------
            topic_formats: Dict[str, Dict[str, int]] = {}
            topic_ers: Dict[str, List[float]] = {}

            for f in features_list:
                top = f["topic"]
                fmt = f["format_type"]
                topic_formats.setdefault(top, {}).setdefault(fmt, 0)
                topic_formats[top][fmt] += 1
                if f["engagement_rate"] is not None:
                    topic_ers.setdefault(top, []).append(f["engagement_rate"])

            for top, formats in topic_formats.items():
                top_total = sum(formats.values())
                top_er = self.compute_trimmed_median(topic_ers.get(top, []))
                if top_total >= 3 and top_er and account_median_er and top_er >= account_median_er:
                    # Check if missing Carousels
                    if formats.get("CAROUSEL", 0) == 0:
                        recs_to_add.append(ContentRecommendation(
                            id=f"rec_gap_{uuid.uuid4().hex[:8]}",
                            type="CONTENT_GAP",
                            scope="TOPIC",
                            title=f"Create a Carousel on '{top}'",
                            recommendation_text=f"Design a structured carousel slide deck covering '{top}'.",
                            why_text=f"You have {top_total} high-performing posts around '{top}' (median ER: {top_er}%), but have not published any carousels on this topic yet.",
                            action_type="CREATE_CAROUSEL",
                            action_payload_json=json.dumps({"topic": top}),
                            evidence_json=json.dumps({"sample_size": top_total, "topic_median_er": top_er, "existing_carousels": 0}),
                            sample_size=top_total,
                            confidence="MEDIUM",
                            status="ACTIVE",
                            created_at=datetime.utcnow()
                        ))

            # ------------------------------------------------------------------
            # 10. Replication Opportunities (High-performing Video Repurposing)
            # ------------------------------------------------------------------
            for f in features_list:
                if f["format_type"] in ["VIDEO", "CLIP"] and f["views"] and account_median_views:
                    if f["views"] >= (account_median_views * 1.5):
                        recs_to_add.append(ContentRecommendation(
                            id=f"rec_rep_{uuid.uuid4().hex[:8]}",
                            type="REPLICATION_OPPORTUNITY",
                            scope="CLIP",
                            title=f"Repurpose top video #{f['publication_id'][-6:]}",
                            recommendation_text="Extract additional vertical short clips and a multi-slide carousel from this high-performing source video.",
                            why_text=f"This post produced {f['views']} views (exceeding account median of {account_median_views} views by 50%+).",
                            action_type="CREATE_CLIP",
                            action_payload_json=json.dumps({"content_id": f["content_id"]}),
                            evidence_json=json.dumps({"views": f["views"], "account_median_views": account_median_views}),
                            sample_size=1,
                            confidence="MEDIUM",
                            status="ACTIVE",
                            created_at=datetime.utcnow()
                        ))
                        break # Limit to 1 replication recommendation per run

            # ------------------------------------------------------------------
            # 11. Experiment Suggestion
            # ------------------------------------------------------------------
            exp_id = f"exp_{uuid.uuid4().hex[:8]}"
            exp = Experiment(
                id=exp_id,
                title="Hook Performance A/B Test",
                hypothesis="Using Statistic-based openers will increase median engagement rate by at least 15% over Direct Claims.",
                variable_tested="hook_type",
                control_baseline=account_median_er,
                success_metric="engagement_rate",
                target_sample_size=5,
                current_sample_size=min(total_posts, 5),
                status="RUNNING",
                results_json=json.dumps({"baseline_er": account_median_er, "target_delta_pct": 15.0}),
                created_at=datetime.utcnow()
            )
            session.add(exp)

            # Persist all insights, patterns, and recommendations
            session.add_all(insights_to_add)
            session.add_all(patterns_to_add)
            session.add_all(recs_to_add)
            await session.commit()

            logger.info(f"Intelligence analysis completed: {len(patterns_to_add)} patterns, {len(recs_to_add)} recommendations, 1 experiment persisted.")
            return {
                "status": "completed",
                "analyzed_count": total_posts,
                "sufficient_data": True,
                "account_baseline_er": account_median_er,
                "recommendations_count": len(recs_to_add),
                "patterns_count": len(patterns_to_add)
            }

    # --------------------------------------------------------------------------
    # 5. Retrieval Query Methods for API Endpoints
    # --------------------------------------------------------------------------

    async def get_overview(self, db: AsyncSession) -> Dict[str, Any]:
        """Returns intelligence overview KPIs, freshness, top recommendations and content gaps."""
        pub_count_res = await db.execute(select(func.count(Publication.id)).where(Publication.status == "PUBLISHED"))
        total_posts = pub_count_res.scalar() or 0

        is_sufficient = total_posts >= settings.MIN_RECOMMENDATION_SAMPLES

        # Fetch patterns
        pat_res = await db.execute(select(ContentPattern).order_by(ContentPattern.sample_size.desc()))
        patterns = pat_res.scalars().all()

        # Fetch recommendations
        rec_res = await db.execute(select(ContentRecommendation).where(ContentRecommendation.status == "ACTIVE"))
        recommendations = rec_res.scalars().all()

        # Fetch insights
        ins_res = await db.execute(select(PerformanceInsight).order_by(PerformanceInsight.created_at.desc()))
        insights = ins_res.scalars().all()

        # Compute baselines from snapshots
        snap_res = await db.execute(select(PostMetricSnapshot))
        snaps = snap_res.scalars().all()
        ers = []
        views = []
        for s in snaps:
            if s.views is not None: views.append(float(s.views))
            denom = s.reach if (s.reach and s.reach > 0) else (s.impressions if (s.impressions and s.impressions > 0) else None)
            if denom and denom > 0:
                num = (s.likes or 0) + (s.comments or 0) + (s.shares or 0) + (s.saves or 0)
                ers.append(round((num / denom) * 100.0, 2))

        baseline_er = self.compute_trimmed_median(ers) if ers else None
        baseline_views = self.compute_trimmed_median(views) if views else None

        # Content Gaps
        gaps = [r for r in recommendations if r.type == "CONTENT_GAP"]
        gap_items = []
        for g in gaps:
            ev = g.evidence
            gap_items.append({
                "topic": g.action_payload.get("topic", "general"),
                "existing_posts_count": g.sample_size,
                "missing_format": "CAROUSEL",
                "opportunity_reason": g.why_text,
                "topic_median_engagement_rate": ev.get("topic_median_er"),
                "action_type": g.action_type or "CREATE_CAROUSEL",
                "action_payload": g.action_payload
            })

        latest_time = recommendations[0].created_at if recommendations else None
        is_stale = False
        if latest_time:
            is_stale = (datetime.utcnow() - latest_time).total_seconds() > (settings.INTELLIGENCE_STALE_AFTER_HOURS * 3600)

        return {
            "total_analyzed_posts": total_posts,
            "account_baseline_engagement_rate": baseline_er,
            "account_baseline_views": baseline_views,
            "is_sufficient_data": is_sufficient,
            "minimum_samples_required": settings.MIN_RECOMMENDATION_SAMPLES,
            "last_analyzed_at": latest_time or datetime.utcnow(),
            "is_stale": is_stale,
            "top_recommendations": recommendations,
            "key_insights": insights,
            "content_gaps": gap_items
        }

    async def get_topic_performance(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Returns aggregated topic performance breakdown."""
        pat_res = await db.execute(
            select(ContentPattern).where(ContentPattern.pattern_type == "TOPIC")
        )
        patterns = pat_res.scalars().all()
        return [
            {
                "topic": p.feature_value,
                "sample_size": p.sample_size,
                "median_views": p.median_views,
                "median_engagement_rate": p.median_engagement_rate,
                "best_post_title": None,
                "best_post_id": None,
                "performance_vs_baseline_pct": round(((p.correlation_ratio - 1.0) * 100.0), 1) if p.correlation_ratio else None,
                "confidence": self.derive_confidence(p.sample_size, (p.correlation_ratio - 1.0) * 100.0 if p.correlation_ratio else 0.0)
            }
            for p in patterns
        ]

    async def get_hook_performance(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Returns aggregated hook performance breakdown."""
        pat_res = await db.execute(
            select(ContentPattern).where(ContentPattern.pattern_type == "HOOK")
        )
        patterns = pat_res.scalars().all()
        return [
            {
                "hook_type": p.feature_value,
                "sample_size": p.sample_size,
                "median_views": p.median_views,
                "median_engagement_rate": p.median_engagement_rate,
                "performance_vs_baseline_pct": round(((p.correlation_ratio - 1.0) * 100.0), 1) if p.correlation_ratio else None,
                "confidence": self.derive_confidence(p.sample_size, (p.correlation_ratio - 1.0) * 100.0 if p.correlation_ratio else 0.0)
            }
            for p in patterns
        ]

    async def get_duration_performance(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Returns aggregated duration bucket performance."""
        pat_res = await db.execute(
            select(ContentPattern).where(ContentPattern.pattern_type == "DURATION_BUCKET")
        )
        patterns = pat_res.scalars().all()
        return [
            {
                "bucket": p.feature_value,
                "sample_size": p.sample_size,
                "median_views": p.median_views,
                "median_engagement_rate": p.median_engagement_rate,
                "performance_vs_baseline_pct": round(((p.correlation_ratio - 1.0) * 100.0), 1) if p.correlation_ratio else None,
                "confidence": self.derive_confidence(p.sample_size, (p.correlation_ratio - 1.0) * 100.0 if p.correlation_ratio else 0.0)
            }
            for p in patterns
        ]

    async def get_posting_windows(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Returns aggregated posting window performance."""
        rec_res = await db.execute(
            select(ContentRecommendation).where(ContentRecommendation.type == "BEST_POSTING_WINDOW")
        )
        recs = rec_res.scalars().all()
        result = []
        for r in recs:
            ev = r.evidence
            parts = r.title.replace("Schedule next publication around ", "").split(" ")
            day = parts[0] if parts else "Unknown"
            hour_b = parts[1] if len(parts) > 1 else "Unknown"
            result.append({
                "day_of_week": day,
                "hour_bucket": hour_b,
                "sample_size": r.sample_size,
                "median_engagement_rate": ev.get("median_er"),
                "performance_vs_baseline_pct": ev.get("delta_pct"),
                "confidence": r.confidence
            })
        return result

    async def get_experiments(self, db: AsyncSession) -> List[Experiment]:
        """Returns list of tracked content experiments."""
        res = await db.execute(select(Experiment).order_by(Experiment.created_at.desc()))
        return res.scalars().all()

intelligence_service = IntelligenceService()
