import os
import json
import uuid
import hashlib
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, delete

from config import settings
from database import async_session_factory
from models.entities import (
    Content, Asset, Transcript, TranscriptSegment, ContentBrief, 
    GeneratedContent, Carousel, CarouselSlide, SlideElement, Clip, ClipVariant
)
from models.schemas import (
    ContentBriefSchema, LinkedInPostSchema, InstagramPostSchema,
    XThreadPostSchema, XPostSchema, YouTubePostSchema,
    CarouselPlanSchema, ClipCandidateSchema, ClipCandidateListSchema
)
from services.ai.base_provider import BaseAIProvider
from services.ai.mock_provider import MockAIProvider
from services.ai.openai_provider import OpenAIProvider
from services.ai.gemini_provider import GeminiProvider
from utils.logging import get_logger

logger = get_logger("AIService")

class AIService:
    def __init__(self):
        self.prompt_version = "v1"
        self._provider: Optional[BaseAIProvider] = None
        self._ai_cache: Dict[str, Dict[str, Any]] = {}

    def _compute_cache_key(self, task: str, payload_str: str) -> str:
        """Computes a stable SHA-256 cache key for AI request deduplication."""
        provider = self.get_provider()
        raw = f"{provider.provider_name}:{task}:{self.prompt_version}:{payload_str}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def get_provider(self) -> BaseAIProvider:
        """Dynamically instantiates active AI provider based on BYOK configuration."""
        if self._provider is not None:
            return self._provider

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            logger.info("Configuring OpenAI Provider for Content Intelligence.")
            self._provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY.strip())
        elif settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            logger.info("Configuring Gemini Provider for Content Intelligence.")
            self._provider = GeminiProvider(api_key=settings.GEMINI_API_KEY.strip())
        else:
            logger.info("No external AI keys provided; configuring deterministic Mock AI Provider.")
            self._provider = MockAIProvider()

        return self._provider

    def set_provider(self, provider: BaseAIProvider):
        """Allows injecting mock or custom provider for unit testing."""
        self._provider = provider

    async def _safe_transcribe(self, audio_path: str) -> Tuple[Dict[str, Any], str]:
        """Transcribes audio using active provider, falling back to MockAIProvider on 5xx/connection errors."""
        provider = self.get_provider()
        try:
            res = await asyncio.wait_for(provider.transcribe(audio_path), timeout=settings.AI_TIMEOUT_SECONDS)
            return res, provider.provider_name
        except Exception as e:
            logger.warning(f"AI Provider '{provider.provider_name}' failed ({e}), using MockAIProvider fallback.")
            mock = MockAIProvider()
            res = await mock.transcribe(audio_path)
            return res, mock.provider_name

    async def _safe_generate_json(self, prompt: str, schema_cls: Any) -> Any:
        """Generates JSON using active provider with caching and MockAIProvider fallback."""
        cache_key = self._compute_cache_key("generate_json", prompt)
        if cache_key in self._ai_cache:
            logger.info("Serving AI generation response from installation cache.")
            return self._ai_cache[cache_key]

        provider = self.get_provider()
        try:
            res = await asyncio.wait_for(provider.generate_json(prompt, schema_cls), timeout=settings.AI_TIMEOUT_SECONDS)
            self._ai_cache[cache_key] = res
            return res
        except Exception as e:
            logger.warning(f"AI Provider '{provider.provider_name}' failed ({e}), using MockAIProvider fallback.")
            mock = MockAIProvider()
            res = await mock.generate_json(prompt, schema_cls)
            self._ai_cache[cache_key] = res
            return res

    async def transcribe_content_audio(self, content_id: str, audio_path: str) -> Transcript:
        """
        Transcribes audio file, validates segments, and persists to Transcript & TranscriptSegment tables.
        """
        logger.info(f"Transcribing audio for Content {content_id}...")
        raw_result, provider_name = await self._safe_transcribe(audio_path)
        full_text = raw_result.get("text", "").strip()
        language = raw_result.get("language", "en")
        duration = float(raw_result.get("duration", 0))
        raw_segments = raw_result.get("segments", [])

        if not full_text:
            raise ValueError(f"Transcription returned empty text for Content {content_id}.")

        async with async_session_factory() as session:
            # Delete any existing transcript for clean idempotency
            existing_transcripts = await session.execute(
                select(Transcript).where(Transcript.content_id == content_id)
            )
            for old_t in existing_transcripts.scalars().all():
                await session.delete(old_t)

            transcript_id = f"trn_{uuid.uuid4().hex[:12]}"
            transcript = Transcript(
                id=transcript_id,
                content_id=content_id,
                provider=provider_name,
                language=language,
                text=full_text,
                duration=duration,
                status="READY",
                created_at=datetime.utcnow()
            )
            session.add(transcript)

            for i, seg in enumerate(raw_segments):
                segment_entity = TranscriptSegment(
                    id=f"seg_{uuid.uuid4().hex[:12]}",
                    transcript_id=transcript_id,
                    sequence=seg.get("sequence", i + 1),
                    start_time=float(seg.get("start_time", 0.0)),
                    end_time=float(seg.get("end_time", 0.0)),
                    text=seg.get("text", "").strip()
                )
                session.add(segment_entity)

            await session.commit()
            logger.info(f"Persisted Transcript {transcript_id} with {len(raw_segments)} segments for Content {content_id}.")
            return transcript

    async def _safe_analyze_content(
        self,
        title: str,
        transcript_text: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Dict[str, Any], str, str]:
        """Analyzes content using active provider, falling back to MockAIProvider on 5xx/connection errors."""
        provider = self.get_provider()
        try:
            res = await asyncio.wait_for(provider.analyze_content(title, transcript_text, segments), timeout=settings.AI_TIMEOUT_SECONDS)
            return res, provider.provider_name, provider.model_name
        except Exception as e:
            logger.warning(f"AI Provider '{provider.provider_name}' failed ({e}), using MockAIProvider fallback.")
            mock = MockAIProvider()
            res = await mock.analyze_content(title, transcript_text, segments)
            return res, mock.provider_name, mock.model_name

    async def generate_content_brief(self, content_id: str) -> ContentBrief:
        """
        Extracts structured, reusable ContentBrief from the persisted transcript or text.
        """
        logger.info(f"Generating ContentBrief for Content {content_id}...")

        async with async_session_factory() as session:
            content_res = await session.execute(select(Content).where(Content.id == content_id))
            content = content_res.scalar_one_or_none()
            if not content:
                raise ValueError(f"Content {content_id} not found.")

            # Find source text: transcript or direct text content
            source_text = content.text_content or ""
            transcript_id = None
            segments_data = []

            if content.transcripts:
                t = content.transcripts[0]
                source_text = t.text
                transcript_id = t.id
                segments_data = [
                    {"sequence": s.sequence, "start_time": s.start_time, "end_time": s.end_time, "text": s.text}
                    for s in t.segments
                ]

            if not source_text:
                raise ValueError(f"Content {content_id} has no transcript or text content to analyze.")

            raw_brief, provider_name, model_name = await self._safe_analyze_content(
                title=content.title,
                transcript_text=source_text,
                segments=segments_data
            )

            # Validate against Pydantic schema
            validated_brief = ContentBriefSchema(**raw_brief)

            # Delete old briefs for idempotency
            old_briefs_res = await session.execute(select(ContentBrief).where(ContentBrief.content_id == content_id))
            for b in old_briefs_res.scalars().all():
                await session.delete(b)

            brief_id = f"brf_{uuid.uuid4().hex[:12]}"
            brief = ContentBrief(
                id=brief_id,
                content_id=content_id,
                transcript_id=transcript_id,
                title=validated_brief.title,
                summary=validated_brief.summary,
                topics_json=json.dumps(validated_brief.topics),
                keywords_json=json.dumps(validated_brief.keywords),
                audience=validated_brief.audience,
                tone=validated_brief.tone,
                key_points_json=json.dumps(validated_brief.key_points),
                hooks_json=json.dumps(validated_brief.hooks),
                quotes_json=json.dumps(validated_brief.quotes),
                cta_suggestions_json=json.dumps(validated_brief.cta_suggestions),
                provider=provider_name,
                model=model_name,
                prompt_version=self.prompt_version,
                created_at=datetime.utcnow()
            )
            session.add(brief)
            await session.commit()
            logger.info(f"Persisted ContentBrief {brief_id} for Content {content_id}.")
            return brief

    async def generate_platform_content(
        self,
        content_id: str,
        platforms: List[str] = ["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"],
        tone: str = "professional",
        custom_instructions: Optional[str] = None
    ) -> List[GeneratedContent]:
        """
        Generates native platform outputs for each specified platform using the ContentBrief.
        """
        provider = self.get_provider()
        logger.info(f"Generating platform outputs for Content {content_id} across {platforms}...")

        async with async_session_factory() as session:
            # 1. Fetch Content & Brief
            content_res = await session.execute(select(Content).where(Content.id == content_id))
            content = content_res.scalar_one_or_none()
            if not content:
                raise ValueError(f"Content {content_id} not found.")

            brief_res = await session.execute(select(ContentBrief).where(ContentBrief.content_id == content_id))
            brief = brief_res.scalars().first()

            if not brief:
                # Generate brief on the fly if missing
                brief = await self.generate_content_brief(content_id)

            brief_dict = {
                "title": brief.title,
                "summary": brief.summary,
                "topics": brief.topics,
                "keywords": brief.keywords,
                "audience": brief.audience,
                "tone": brief.tone,
                "key_points": brief.key_points,
                "hooks": brief.hooks,
                "quotes": brief.quotes,
                "cta_suggestions": brief.cta_suggestions
            }

            segments_data = []
            if content.transcripts and content.transcripts[0].segments:
                segments_data = [
                    {"sequence": s.sequence, "start_time": s.start_time, "end_time": s.end_time, "text": s.text}
                    for s in content.transcripts[0].segments
                ]

            generated_list = []

            for plt in platforms:
                platform_upper = plt.upper()
                raw_payload = await provider.generate_platform(
                    platform=platform_upper,
                    brief=brief_dict,
                    segments=segments_data,
                    tone=tone,
                    custom_instructions=custom_instructions
                )

                # Validate platform schema
                if platform_upper == "LINKEDIN":
                    validated_payload = LinkedInPostSchema(**raw_payload).model_dump()
                    gen_type = "POST"
                elif platform_upper == "INSTAGRAM":
                    validated_payload = InstagramPostSchema(**raw_payload).model_dump()
                    gen_type = "REEL_CAPTION"
                elif platform_upper == "X":
                    if "posts" in raw_payload:
                        validated_payload = XThreadPostSchema(**raw_payload).model_dump()
                        gen_type = "THREAD"
                    else:
                        validated_payload = XPostSchema(**raw_payload).model_dump()
                        gen_type = "POST"
                elif platform_upper == "YOUTUBE":
                    validated_payload = YouTubePostSchema(**raw_payload).model_dump()
                    gen_type = "VIDEO_METADATA"
                else:
                    validated_payload = raw_payload
                    gen_type = "GENERIC"

                # Check existing version
                old_gen_res = await session.execute(
                    select(GeneratedContent).where(
                        GeneratedContent.content_id == content_id,
                        GeneratedContent.platform == platform_upper
                    ).order_by(GeneratedContent.version.desc())
                )
                latest_gen = old_gen_res.scalars().first()
                next_version = (latest_gen.version + 1) if latest_gen else 1

                gen_entity = GeneratedContent(
                    id=f"gen_{uuid.uuid4().hex[:12]}",
                    content_id=content_id,
                    brief_id=brief.id,
                    platform=platform_upper,
                    generation_type=gen_type,
                    status="READY",
                    content_payload_json=json.dumps(validated_payload),
                    provider=provider.provider_name,
                    model=provider.model_name,
                    prompt_version=f"{platform_upper.lower()}-{self.prompt_version}",
                    version=next_version,
                    created_at=datetime.utcnow()
                )
                session.add(gen_entity)
                generated_list.append(gen_entity)

            await session.commit()
            logger.info(f"Successfully generated {len(generated_list)} platform contents for Content {content_id}.")
            return generated_list

    async def plan_and_persist_carousel(
        self,
        carousel_id: str,
        content_id: Optional[str] = None,
        target_slide_count: int = 5,
        template: str = "MINIMAL",
        tone: str = "informative",
        custom_instructions: Optional[str] = None
    ) -> Carousel:
        """
        Plans a structured carousel slide deck with Pydantic validation, preserving previous slides upon failure.
        """
        provider = self.get_provider()
        logger.info(f"Planning carousel {carousel_id} (Content: {content_id}) using {provider.provider_name}...")

        brief_dict = None
        source_text = None
        target_title = "Automated Slide Deck"

        async with async_session_factory() as session:
            c_res = await session.execute(select(Carousel).where(Carousel.id == carousel_id))
            carousel = c_res.scalar_one_or_none()
            if not carousel:
                raise ValueError(f"Carousel {carousel_id} not found.")

            target_title = carousel.title

            if content_id or carousel.content_id:
                cid = content_id or carousel.content_id
                cnt_res = await session.execute(select(Content).where(Content.id == cid))
                cnt = cnt_res.scalar_one_or_none()
                if cnt:
                    target_title = cnt.title
                    source_text = cnt.text_content or ""
                    if cnt.transcripts:
                        source_text = cnt.transcripts[0].text
                    if cnt.briefs:
                        b = cnt.briefs[0]
                        brief_dict = {
                            "title": b.title,
                            "summary": b.summary,
                            "key_points": b.key_points,
                            "hooks": b.hooks,
                            "quotes": b.quotes
                        }

        # Call AI provider
        raw_plan = await provider.plan_carousel(
            title=target_title,
            brief=brief_dict,
            transcript_text=source_text,
            target_slide_count=target_slide_count,
            template=template,
            tone=tone,
            custom_instructions=custom_instructions
        )

        # Validate with Pydantic CarouselPlanSchema
        validated_plan = CarouselPlanSchema(**raw_plan)

        # Persist to database atomically
        async with async_session_factory() as session:
            c_res = await session.execute(select(Carousel).where(Carousel.id == carousel_id))
            carousel = c_res.scalar_one_or_none()
            if not carousel:
                raise ValueError(f"Carousel {carousel_id} not found during commit.")

            carousel.title = validated_plan.title
            carousel.template = validated_plan.template.upper()
            carousel.slide_count = len(validated_plan.slides)
            carousel.version += 1
            carousel.status = "READY"
            carousel.updated_at = datetime.utcnow()

            # Delete old slides and elements
            old_slides_res = await session.execute(
                select(CarouselSlide).where(CarouselSlide.carousel_id == carousel_id)
            )
            for s in old_slides_res.scalars().all():
                await session.delete(s)

            # Insert validated slides
            for slide_data in validated_plan.slides:
                slide_id = f"sld_{uuid.uuid4().hex[:12]}"
                slide_entity = CarouselSlide(
                    id=slide_id,
                    carousel_id=carousel_id,
                    position=slide_data.position,
                    purpose=slide_data.purpose,
                    layout=slide_data.layout,
                    headline=slide_data.headline,
                    body=slide_data.body,
                    tag=slide_data.tag or "INSIGHT",
                    background="#0F172A",
                    created_at=datetime.utcnow()
                )
                session.add(slide_entity)

                # Add default text element for future canvas manipulations
                elem = SlideElement(
                    id=f"elm_{uuid.uuid4().hex[:12]}",
                    slide_id=slide_id,
                    type="TEXT",
                    position_x=80.0,
                    position_y=200.0,
                    width=920.0,
                    height=600.0,
                    content=f"{slide_data.headline}\n\n{slide_data.body}",
                    style_json=json.dumps({"fontSize": 32, "color": "#FFFFFF"}),
                    z_index=1
                )
                session.add(elem)

            await session.commit()
            logger.info(f"Successfully saved {len(validated_plan.slides)} slides for Carousel {carousel_id} (Version {carousel.version}).")
            return carousel

    async def discover_and_persist_clips(
        self,
        content_id: str,
        min_duration: float = 15.0,
        max_duration: float = 90.0,
        target_count: int = 5,
        force_refresh: bool = False
    ) -> List[Clip]:
        """
        Discovers high-impact short-form clip candidate intervals:
        1. Loads Transcript segments and ContentBrief
        2. Queries AI Provider for candidates
        3. Validates via ClipCandidateListSchema
        4. Aligns & snaps boundaries to transcript segment timestamps
        5. Computes multi-factor ranking score & suppresses overlapping duplicates
        6. Persists candidate Clip records
        """
        provider = self.get_provider()
        logger.info(f"Discovering clips for Content {content_id} using {provider.provider_name}...")

        async with async_session_factory() as session:
            # 1. Fetch Content, Asset, Transcript, ContentBrief
            content_res = await session.execute(select(Content).where(Content.id == content_id))
            content = content_res.scalar_one_or_none()
            if not content:
                raise ValueError(f"Content {content_id} not found.")

            source_asset = content.assets[0] if content.assets else None
            max_content_duration = float(source_asset.duration) if source_asset and source_asset.duration else 3600.0

            t_res = await session.execute(select(Transcript).where(Transcript.content_id == content_id))
            transcript = t_res.scalar_one_or_none()
            if not transcript or not transcript.segments:
                raise ValueError(f"No transcript segments found for Content {content_id}.")

            b_res = await session.execute(select(ContentBrief).where(ContentBrief.content_id == content_id))
            brief = b_res.scalar_one_or_none()
            brief_dict = {
                "title": brief.title,
                "summary": brief.summary,
                "key_points": brief.key_points,
                "hooks": brief.hooks,
                "quotes": brief.quotes
            } if brief else {}

            segments_data = [
                {
                    "id": seg.id,
                    "sequence": seg.sequence,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "text": seg.text
                }
                for seg in sorted(transcript.segments, key=lambda s: s.start_time)
            ]

            # 2. Query AI Provider
            raw_result = await provider.discover_clips(
                title=content.title,
                transcript_text=transcript.text,
                segments=segments_data,
                brief=brief_dict,
                min_duration=min_duration,
                max_duration=max_duration,
                target_count=target_count
            )

            # 3. Schema validation
            validated = ClipCandidateListSchema.model_validate(raw_result)

            # 4. Snap boundaries to segment timestamps & build processed candidates
            processed_candidates = []
            for cand in validated.candidates:
                cand_st = max(0.0, float(cand.start_time))
                cand_et = min(max_content_duration, float(cand.end_time))

                # Find nearest segment start
                closest_start = cand_st
                min_st_diff = 3.5
                for seg in segments_data:
                    diff = abs(seg["start_time"] - cand_st)
                    if diff < min_st_diff:
                        min_st_diff = diff
                        closest_start = seg["start_time"]

                # Find nearest segment end
                closest_end = cand_et
                min_et_diff = 3.5
                for seg in segments_data:
                    diff = abs(seg["end_time"] - cand_et)
                    if diff < min_et_diff:
                        min_et_diff = diff
                        closest_end = seg["end_time"]

                snapped_st = round(closest_start, 2)
                snapped_et = round(max(snapped_st + min_duration, closest_end), 2)
                if snapped_et > max_content_duration:
                    snapped_et = round(max_content_duration, 2)
                
                dur = round(snapped_et - snapped_st, 2)
                if dur < min_duration or snapped_st >= snapped_et:
                    continue

                # Collect transcript excerpt
                matching_seg_texts = [
                    seg["text"] for seg in segments_data
                    if seg["end_time"] >= snapped_st and seg["start_time"] <= snapped_et
                ]
                excerpt = " ".join(matching_seg_texts).strip()

                matched_seg_ids = [
                    seg["id"] for seg in segments_data
                    if seg["end_time"] >= snapped_st and seg["start_time"] <= snapped_et
                ]

                # 5. Deterministic Ranking Score
                # Factors: base score (40%), duration fitness (20%), hook strength (20%), segment alignment (20%)
                base_s = float(cand.score) * 0.4
                dur_s = 20.0 if (20.0 <= dur <= 60.0) else (15.0 if (15.0 <= dur <= 90.0) else 10.0)
                hook_s = 20.0 if cand.hook and len(cand.hook.strip()) > 10 else 10.0
                align_s = 20.0 if min_st_diff < 1.0 else 15.0
                final_score = round(min(100.0, max(50.0, base_s + dur_s + hook_s + align_s)), 1)

                processed_candidates.append({
                    "title": cand.title.strip(),
                    "start_time": snapped_st,
                    "end_time": snapped_et,
                    "duration": dur,
                    "reason": cand.reason.strip(),
                    "hook": cand.hook.strip(),
                    "score": final_score,
                    "source_segment_ids": matched_seg_ids,
                    "transcript_excerpt": excerpt
                })

            # 6. Overlap Suppression (Non-Maximum Suppression)
            processed_candidates.sort(key=lambda x: x["score"], reverse=True)
            accepted_candidates = []
            for cand in processed_candidates:
                is_overlap = False
                for acc in accepted_candidates:
                    overlap_start = max(cand["start_time"], acc["start_time"])
                    overlap_end = min(cand["end_time"], acc["end_time"])
                    if overlap_end > overlap_start:
                        overlap_dur = overlap_end - overlap_start
                        overlap_ratio = overlap_dur / min(cand["duration"], acc["duration"])
                        if overlap_ratio > 0.6:
                            is_overlap = True
                            break
                if not is_overlap:
                    accepted_candidates.append(cand)
                if len(accepted_candidates) >= target_count:
                    break

            # 7. Persist to Database
            if force_refresh:
                # Delete existing CANDIDATE clips
                old_clips_res = await session.execute(
                    select(Clip).where(Clip.content_id == content_id, Clip.status == "CANDIDATE")
                )
                for old_c in old_clips_res.scalars().all():
                    await session.delete(old_c)

            persisted_clips = []
            for item in accepted_candidates:
                clip_id = f"clp_{uuid.uuid4().hex[:12]}"
                clip_entity = Clip(
                    id=clip_id,
                    content_id=content_id,
                    source_asset_id=source_asset.id if source_asset else None,
                    title=item["title"],
                    description=item["reason"],
                    hook=item["hook"],
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    duration=item["duration"],
                    status="CANDIDATE",
                    score=item["score"],
                    reason=item["reason"],
                    source_transcript_segment_ids_json=json.dumps(item["source_segment_ids"]),
                    transcript_excerpt=item["transcript_excerpt"],
                    discovery_version="v1",
                    created_at=datetime.utcnow()
                )
                session.add(clip_entity)
                persisted_clips.append(clip_entity)

            await session.commit()
            logger.info(f"Persisted {len(persisted_clips)} candidate clips for Content {content_id}.")
            return persisted_clips

ai_service = AIService()
