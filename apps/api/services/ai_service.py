import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete

from config import settings
from database import async_session_factory
from models.entities import Content, Asset, Transcript, TranscriptSegment, ContentBrief, GeneratedContent
from models.schemas import (
    ContentBriefSchema, LinkedInPostSchema, InstagramPostSchema,
    XThreadPostSchema, XPostSchema, YouTubePostSchema
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

    async def transcribe_content_audio(self, content_id: str, audio_path: str) -> Transcript:
        """
        Transcribes audio file, validates segments, and persists to Transcript & TranscriptSegment tables.
        """
        provider = self.get_provider()
        logger.info(f"Transcribing audio for Content {content_id} using {provider.provider_name}...")

        raw_result = await provider.transcribe(audio_path)
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
                provider=provider.provider_name,
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

    async def generate_content_brief(self, content_id: str) -> ContentBrief:
        """
        Extracts structured, reusable ContentBrief from the persisted transcript or text.
        """
        provider = self.get_provider()
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

            raw_brief = await provider.analyze_content(
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
                provider=provider.provider_name,
                model=provider.model_name,
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

ai_service = AIService()
