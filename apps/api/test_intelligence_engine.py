import unittest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, delete

from database import async_session_factory, init_db
from models.entities import (
    Content, Asset, ContentVariant, Clip, Carousel, CarouselSlide,
    Publication, PostMetricSnapshot, PerformanceInsight, ContentPattern,
    ContentRecommendation, Experiment, Job
)
from services.intelligence_service import intelligence_service
from config import settings

class TestIntelligenceEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        async with async_session_factory() as session:
            # Clean test data
            await session.execute(delete(PostMetricSnapshot))
            await session.execute(delete(Publication))
            await session.execute(delete(Clip))
            await session.execute(delete(CarouselSlide))
            await session.execute(delete(Carousel))
            await session.execute(delete(ContentVariant))
            await session.execute(delete(Asset))
            from models.entities import ContentBrief, GeneratedContent
            await session.execute(delete(ContentBrief))
            await session.execute(delete(GeneratedContent))
            await session.execute(delete(Content))
            await session.execute(delete(PerformanceInsight))
            await session.execute(delete(ContentPattern))
            await session.execute(delete(ContentRecommendation))
            await session.execute(delete(Experiment))
            await session.execute(delete(Job))
            await session.commit()

    async def test_01_hook_classification(self):
        """Verifies deterministic classification of 8 hook archetypes."""
        self.assertEqual(intelligence_service.classify_hook("Why does nobody talk about this?"), "QUESTION")
        self.assertEqual(intelligence_service.classify_hook("Did you know 85% of startups fail in year 1?"), "QUESTION") # Leading question
        self.assertEqual(intelligence_service.classify_hook("Over 78% of creators quit within 30 days."), "STATISTIC")
        self.assertEqual(intelligence_service.classify_hook("How to build an AI agent system from scratch"), "HOW_TO")
        self.assertEqual(intelligence_service.classify_hook("Stop doing this biggest mistake in your code"), "PROBLEM")
        self.assertEqual(intelligence_service.classify_hook("Why you shouldn't use microservices for small apps"), "CONTRARIAN")
        self.assertEqual(intelligence_service.classify_hook("The secret trick behind 10x developer productivity"), "CURIOSITY")
        self.assertEqual(intelligence_service.classify_hook("Years ago when I started programming in Python"), "STORY")
        self.assertEqual(intelligence_service.classify_hook("Building software faster with Reflow"), "DIRECT_CLAIM")

    async def test_02_topic_normalization(self):
        """Verifies deterministic topic normalization into clustered slugs."""
        self.assertEqual(intelligence_service.normalize_topic("AI agents"), "ai-agents")
        self.assertEqual(intelligence_service.normalize_topic("Autonomous AI agent systems"), "ai-agents")
        self.assertEqual(intelligence_service.normalize_topic("LLM prompt engineering with OpenAI"), "language-models")
        self.assertEqual(intelligence_service.normalize_topic("Content repurposing strategies"), "content-repurposing")
        self.assertEqual(intelligence_service.normalize_topic("Short Form Video & Reels"), "short-form-video")
        self.assertEqual(intelligence_service.normalize_topic("Carousel slide decks"), "carousels")

    async def test_03_duration_bucketing(self):
        """Verifies duration ranges are bucketed accurately."""
        self.assertEqual(intelligence_service.get_duration_bucket(12.5), "0-15s")
        self.assertEqual(intelligence_service.get_duration_bucket(28.0), "15-30s")
        self.assertEqual(intelligence_service.get_duration_bucket(45.0), "30-60s")
        self.assertEqual(intelligence_service.get_duration_bucket(90.0), "60-120s")
        self.assertEqual(intelligence_service.get_duration_bucket(180.0), "120s+")
        self.assertEqual(intelligence_service.get_duration_bucket(None), "UNKNOWN")

    async def test_04_outlier_resistance(self):
        """Verifies that a single viral post does not distort median baseline calculations."""
        # 1 viral post (150% ER) among normal posts (4-6% ER)
        ers = [4.2, 5.1, 4.8, 5.5, 6.0, 150.0]
        med = intelligence_service.compute_trimmed_median(ers)
        # Median should remain around ~5.3%, not skewed by 150.0%
        self.assertLess(med, 10.0)
        self.assertGreater(med, 4.0)

    async def test_05_anti_hallucination_guard(self):
        """Verifies that AI claim validation rejects or overrides hallucinated numbers."""
        evidence = {
            "sample_size": 18,
            "median_er": 6.8,
            "baseline_er": 4.5,
            "delta_pct": 51.1
        }
        valid_ai_text = "Clips with Question hooks were associated with 6.8% median engagement rate across 18 posts."
        sanitized = intelligence_service.verify_and_sanitize_claim(
            valid_ai_text,
            evidence,
            fallback_summary="Default fallback"
        )
        self.assertIn("6.8%", sanitized)

        # AI hallucinates a non-existent number "94%" and claim "causes"
        hallucinated_ai_text = "Using hooks causes 94% higher engagement across 42 posts."
        sanitized_hallucination = intelligence_service.verify_and_sanitize_claim(
            hallucinated_ai_text,
            evidence,
            fallback_summary="Fallback: associated with higher performance."
        )
        self.assertEqual(sanitized_hallucination, "Fallback: associated with higher performance.")

    async def test_06_cold_start_insufficient_data(self):
        """Verifies that when publications count < MIN_RECOMMENDATION_SAMPLES, cold start guidance is returned."""
        async with async_session_factory() as session:
            # Create only 2 published posts
            c = Content(id="c_test_cold", title="Test Cold", content_type="VIDEO", status="READY")
            session.add(c)

            for i in range(2):
                p = Publication(
                    id=f"pub_cold_{i}",
                    content_id="c_test_cold",
                    platform="youtube",
                    status="PUBLISHED",
                    title=f"Cold Post {i}",
                    request_payload_hash=f"hash_{i}",
                    published_at=datetime.utcnow()
                )
                session.add(p)
            await session.commit()

        res = await intelligence_service.run_full_analysis()
        self.assertFalse(res["sufficient_data"])
        self.assertEqual(res["analyzed_count"], 2)

        # Verify overview reports insufficient data
        async with async_session_factory() as session:
            ov = await intelligence_service.get_overview(session)
            self.assertFalse(ov["is_sufficient_data"])
            self.assertEqual(ov["total_analyzed_posts"], 2)
            self.assertEqual(len(ov["top_recommendations"]), 1)
            self.assertEqual(ov["top_recommendations"][0].confidence, "INSUFFICIENT_DATA")

    async def test_07_full_analysis_patterns_and_recommendations(self):
        """Creates sufficient publications and verifies pattern detection, best hook, best duration, and experiment generation."""
        async with async_session_factory() as session:
            c = Content(id="c_full_test", title="Full AI Analysis Video", content_type="VIDEO", status="READY")
            session.add(c)

            # Create 8 publications: 5 with STATISTIC hook (high ER), 3 with DIRECT_CLAIM (baseline ER)
            for i in range(8):
                is_stat = i < 5
                pub_id = f"pub_full_{i}"
                clip_id = f"clip_full_{i}"

                clip = Clip(
                    id=clip_id,
                    content_id=c.id,
                    title=f"Clip {i}",
                    hook=f"Over {70 + i}% of developers agree on this metric" if is_stat else f"General update number {i}",
                    start_time=0.0,
                    end_time=35.0, # 30-60s duration bucket
                    duration=35.0,
                    status="READY"
                )
                session.add(clip)

                p = Publication(
                    id=pub_id,
                    content_id=c.id,
                    variant_id=clip_id,
                    platform="instagram",
                    status="PUBLISHED",
                    title=f"Post {i}: {clip.hook}",
                    timezone="America/New_York",
                    request_payload_hash=f"hash_full_{i}",
                    published_at=datetime(2026, 8, 25, 18, 0, 0) # Tuesday 18:00
                )
                session.add(p)

                # Add Snapshot
                snap = PostMetricSnapshot(
                    id=f"snap_full_{i}",
                    publication_id=pub_id,
                    platform="instagram",
                    views=2000 if is_stat else 800,
                    reach=1000,
                    likes=80 if is_stat else 30, # 8% ER vs 3% ER
                    comments=10 if is_stat else 5,
                    shares=10 if is_stat else 5,
                    captured_at=datetime.utcnow()
                )
                session.add(snap)

            await session.commit()

        # Run analysis
        result = await intelligence_service.run_full_analysis()
        self.assertTrue(result["sufficient_data"])
        self.assertEqual(result["analyzed_count"], 8)
        self.assertGreater(result["recommendations_count"], 0)
        self.assertGreater(result["patterns_count"], 0)

        # Check DB entities
        async with async_session_factory() as session:
            ov = await intelligence_service.get_overview(session)
            self.assertTrue(ov["is_sufficient_data"])
            self.assertIsNotNone(ov["account_baseline_engagement_rate"])

            # Check Hook performance
            hooks = await intelligence_service.get_hook_performance(session)
            stat_hook = next((h for h in hooks if h["hook_type"] == "STATISTIC"), None)
            self.assertIsNotNone(stat_hook)
            self.assertEqual(stat_hook["sample_size"], 5)

            # Check Duration performance
            durations = await intelligence_service.get_duration_performance(session)
            dur_bucket = next((d for d in durations if d["bucket"] == "30-60s"), None)
            self.assertIsNotNone(dur_bucket)
            self.assertEqual(dur_bucket["sample_size"], 8)

            # Check Experiments
            exps = await intelligence_service.get_experiments(session)
            self.assertGreaterEqual(len(exps), 1)
            self.assertEqual(exps[0].variable_tested, "hook_type")

    async def test_08_content_gap_discovery(self):
        """Verifies detection of high-performing topics lacking specific format representations (e.g. Carousels)."""
        async with async_session_factory() as session:
            c = Content(id="c_gap_test", title="AI Agents Deep Dive", content_type="VIDEO", status="READY")
            session.add(c)

            # Brief with topic
            from models.entities import ContentBrief
            b = ContentBrief(
                id="b_gap_test",
                content_id=c.id,
                title="AI Agents",
                summary="Deep dive into autonomous AI agents",
                topics_json=json.dumps(["AI agents"])
            )
            session.add(b)

            # 6 published Video/Clip posts on AI agents with high ER, 0 carousels
            for i in range(6):
                pub_id = f"pub_gap_{i}"
                clip_id = f"clip_gap_{i}"
                clip = Clip(id=clip_id, content_id=c.id, title=f"AI Agent Clip {i}", start_time=0.0, end_time=25.0, duration=25.0, status="READY")
                session.add(clip)

                p = Publication(
                    id=pub_id,
                    content_id=c.id,
                    variant_id=clip_id,
                    platform="linkedin",
                    status="PUBLISHED",
                    title=f"AI Agents post {i}",
                    request_payload_hash=f"hash_gap_{i}",
                    published_at=datetime.utcnow()
                )
                session.add(p)

                snap = PostMetricSnapshot(
                    id=f"snap_gap_{i}",
                    publication_id=pub_id,
                    platform="linkedin",
                    views=5000,
                    reach=2000,
                    likes=140, # 8% ER
                    comments=20,
                    shares=0,
                    captured_at=datetime.utcnow()
                )
                session.add(snap)

            await session.commit()

        await intelligence_service.run_full_analysis()

        async with async_session_factory() as session:
            ov = await intelligence_service.get_overview(session)
            gap = next((g for g in ov["content_gaps"] if g["topic"] == "ai-agents"), None)
            self.assertIsNotNone(gap)
            self.assertEqual(gap["missing_format"], "CAROUSEL")
            self.assertEqual(gap["action_type"], "CREATE_CAROUSEL")

    async def test_09_replication_opportunity(self):
        """Verifies repurposing suggestions for high-performing video content."""
        async with async_session_factory() as session:
            c = Content(id="c_rep_test", title="Viral Masterclass", content_type="VIDEO", status="READY")
            session.add(c)

            # 6 posts total, one of them has 50k views vs median 5k views
            for i in range(6):
                p = Publication(
                    id=f"pub_rep_{i}",
                    content_id=c.id,
                    platform="youtube",
                    status="PUBLISHED",
                    title=f"Masterclass {i}",
                    request_payload_hash=f"hash_rep_{i}",
                    published_at=datetime.utcnow()
                )
                session.add(p)

                views_cnt = 50000 if i == 0 else 5000
                snap = PostMetricSnapshot(
                    id=f"snap_rep_{i}",
                    publication_id=f"pub_rep_{i}",
                    platform="youtube",
                    views=views_cnt,
                    reach=views_cnt,
                    likes=views_cnt // 20,
                    comments=10,
                    captured_at=datetime.utcnow()
                )
                session.add(snap)

            await session.commit()

        await intelligence_service.run_full_analysis()

        async with async_session_factory() as session:
            recs = await session.execute(
                select(ContentRecommendation).where(ContentRecommendation.type == "REPLICATION_OPPORTUNITY")
            )
            rep_rec = recs.scalars().first()
            self.assertIsNotNone(rep_rec)
            self.assertIn("Repurpose top video", rep_rec.title)
            self.assertEqual(rep_rec.action_type, "CREATE_CLIP")

    async def test_10_async_intelligence_refresh_job(self):
        """Verifies that an INTELLIGENCE_ANALYSIS job is correctly enqueued and processed."""
        from services.queue_service import queue_service
        from worker import process_single_job

        async with async_session_factory() as session:
            job_id = f"job_test_intel_{uuid.uuid4().hex[:8]}"
            job = Job(
                id=job_id,
                type="INTELLIGENCE_ANALYSIS",
                status="QUEUED",
                created_at=datetime.utcnow()
            )
            session.add(job)
            await session.commit()

        # Execute single job in worker
        success = await process_single_job({
            "job_id": job_id,
            "job_type": "INTELLIGENCE_ANALYSIS"
        })
        self.assertTrue(success)

        async with async_session_factory() as session:
            job_res = await session.execute(select(Job).where(Job.id == job_id))
            job = job_res.scalar_one_or_none()
            self.assertEqual(job.status, "SUCCEEDED")

    async def test_11_intelligence_rest_endpoints(self):
        """Tests the FastAPI routes for intelligence endpoints."""
        from httpx import AsyncClient, ASGITransport
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Overview
            res_ov = await ac.get("/api/intelligence/overview")
            self.assertEqual(res_ov.status_code, 200)
            ov_data = res_ov.json()
            self.assertIn("total_analyzed_posts", ov_data)
            self.assertIn("is_sufficient_data", ov_data)

            # 2. Insights
            res_ins = await ac.get("/api/intelligence/insights")
            self.assertEqual(res_ins.status_code, 200)

            # 3. Recommendations
            res_rec = await ac.get("/api/intelligence/recommendations")
            self.assertEqual(res_rec.status_code, 200)

            # 4. Patterns
            res_pat = await ac.get("/api/intelligence/patterns")
            self.assertEqual(res_pat.status_code, 200)

            # 5. Topics
            res_top = await ac.get("/api/intelligence/topics")
            self.assertEqual(res_top.status_code, 200)

            # 6. Hooks
            res_hk = await ac.get("/api/intelligence/hooks")
            self.assertEqual(res_hk.status_code, 200)

            # 7. Durations
            res_dur = await ac.get("/api/intelligence/durations")
            self.assertEqual(res_dur.status_code, 200)

            # 8. Posting Windows
            res_win = await ac.get("/api/intelligence/posting-windows")
            self.assertEqual(res_win.status_code, 200)

            # 9. Content Gaps
            res_gap = await ac.get("/api/intelligence/content-gaps")
            self.assertEqual(res_gap.status_code, 200)

            # 10. Experiments
            res_exp = await ac.get("/api/intelligence/experiments")
            self.assertEqual(res_exp.status_code, 200)

            # 11. Refresh endpoint
            res_ref = await ac.post("/api/intelligence/refresh")
            self.assertEqual(res_ref.status_code, 200)
            ref_data = res_ref.json()
            self.assertEqual(ref_data["status"], "queued")
            self.assertTrue(ref_data["job_id"].startswith("job_intel_"))

if __name__ == "__main__":
    unittest.main()
