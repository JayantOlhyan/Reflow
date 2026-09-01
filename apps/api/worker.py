import asyncio
import os
import sys
import tempfile
import uuid
from datetime import datetime
from sqlalchemy import select, update

sys.path.append(os.path.dirname(__file__))

from config import settings
from database import async_session_factory, init_db
from models.entities import Job, Content, Asset, Transcript, ContentBrief, GeneratedContent, Carousel, Clip, ClipVariant
from services.queue_service import queue_service
from services.media_service import media_processor
from services.storage_service import storage_service
from services.ai_service import ai_service
from services.carousel_renderer import carousel_renderer
from services.publishing_service import publishing_service
from services.analytics_service import analytics_service
from services.intelligence_service import intelligence_service
from utils.logging import get_logger

logger = get_logger("MediaWorker")

async def process_single_job(payload: dict) -> bool:
    """Processes a single job from the queue with dependency-ordered downstream dispatch."""
    job_id = payload.get("job_id")
    content_id = payload.get("content_id")
    asset_id = payload.get("asset_id")
    carousel_id = payload.get("carousel_id")
    clip_id = payload.get("clip_id")
    job_type = payload.get("job_type", "MEDIA_PROCESSING")

    logger.info(f"Processing job {job_id} (Type: {job_type}) for Content: {content_id or carousel_id}")

    async with async_session_factory() as session:
        job_res = await session.execute(select(Job).where(Job.id == job_id))
        job = job_res.scalar_one_or_none()

        if not job:
            logger.warn(f"Job {job_id} not found in database, cancelling.")
            return False

        if content_id and not carousel_id:
            content_res = await session.execute(select(Content).where(Content.id == content_id))
            if not content_res.scalar_one_or_none():
                logger.warn(f"Content {content_id} not found in database, cancelling.")
                job.status = "CANCELLED"
                await session.commit()
                return False

        # Mark RUNNING
        job.status = "RUNNING"
        job.started_at = datetime.utcnow()
        job.attempts += 1
        await session.commit()

    try:
        if job_type == "MEDIA_PROCESSING":
            # 1. Execute FFprobe & FFmpeg media variant generation
            await media_processor.process_content_media(content_id, asset_id)

            # Auto-enqueue downstream TRANSCRIPTION job
            next_job_id = f"job_{uuid.uuid4().hex[:12]}"
            async with async_session_factory() as session:
                next_job = Job(
                    id=next_job_id,
                    content_id=content_id,
                    asset_id=asset_id,
                    type="TRANSCRIPTION",
                    status="QUEUED",
                    created_at=datetime.utcnow()
                )
                session.add(next_job)
                await session.commit()

            await queue_service.enqueue_media_job(next_job_id, content_id, asset_id, job_type="TRANSCRIPTION")

        elif job_type == "TRANSCRIPTION":
            # 2. Extract temporary audio & transcribe
            async with async_session_factory() as session:
                asset_res = await session.execute(select(Asset).where(Asset.id == asset_id))
                asset = asset_res.scalar_one_or_none()
                if not asset:
                    raise ValueError(f"Asset {asset_id} not found.")

                orig_path = storage_service.get_real_path(asset.storage_key)

            temp_audio = tempfile.mktemp(suffix=".mp3", prefix=f"reflow_audio_{content_id}_")
            try:
                await media_processor.extract_audio(orig_path, temp_audio)
                await ai_service.transcribe_content_audio(content_id, temp_audio)
            finally:
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)

            # Auto-enqueue downstream CONTENT_ANALYSIS job
            next_job_id = f"job_{uuid.uuid4().hex[:12]}"
            async with async_session_factory() as session:
                next_job = Job(
                    id=next_job_id,
                    content_id=content_id,
                    asset_id=asset_id,
                    type="CONTENT_ANALYSIS",
                    status="QUEUED",
                    created_at=datetime.utcnow()
                )
                session.add(next_job)
                await session.commit()

            await queue_service.enqueue_media_job(next_job_id, content_id, asset_id, job_type="CONTENT_ANALYSIS")

        elif job_type == "CONTENT_ANALYSIS":
            # 3. Generate ContentBrief
            await ai_service.generate_content_brief(content_id)

            # Auto-enqueue downstream CONTENT_GENERATION job
            next_job_id = f"job_{uuid.uuid4().hex[:12]}"
            async with async_session_factory() as session:
                next_job = Job(
                    id=next_job_id,
                    content_id=content_id,
                    asset_id=asset_id,
                    type="CONTENT_GENERATION",
                    status="QUEUED",
                    created_at=datetime.utcnow()
                )
                session.add(next_job)
                await session.commit()

            await queue_service.enqueue_media_job(next_job_id, content_id, asset_id, job_type="CONTENT_GENERATION")

        elif job_type == "CONTENT_GENERATION":
            # 4. Generate multi-platform outputs
            await ai_service.generate_platform_content(
                content_id=content_id,
                platforms=["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"]
            )
            # Dispatch event
            from services.event_bus import event_bus_service
            async with async_session_factory() as session:
                await event_bus_service.dispatch_event("content.ready", content_id, session)

        elif job_type == "CAROUSEL_GENERATION":
            # 5. Plan and render AI carousel deck
            slide_count = payload.get("slide_count", 5)
            template = payload.get("template", "MINIMAL")
            tone = payload.get("tone", "informative")
            custom_prompt = payload.get("custom_prompt")

            await ai_service.plan_and_persist_carousel(
                carousel_id=carousel_id,
                content_id=content_id,
                target_slide_count=slide_count,
                template=template,
                tone=tone,
                custom_instructions=custom_prompt
            )
            await carousel_renderer.render_carousel_deck(carousel_id)

        elif job_type == "CAROUSEL_RENDER":
            # 6. Render carousel PNGs and PDF
            await carousel_renderer.render_carousel_deck(carousel_id)
            # Dispatch event
            from services.event_bus import event_bus_service
            async with async_session_factory() as session:
                await event_bus_service.dispatch_event("carousel.ready", carousel_id, session)

        elif job_type == "CLIP_DISCOVERY":
            # 7. Discover candidate clips from transcript & ContentBrief
            min_dur = payload.get("min_duration", 15.0)
            max_dur = payload.get("max_duration", 90.0)
            t_count = payload.get("target_count", 5)
            f_refresh = payload.get("force_refresh", False)

            await ai_service.discover_and_persist_clips(
                content_id=content_id,
                min_duration=min_dur,
                max_duration=max_dur,
                target_count=t_count,
                force_refresh=f_refresh
            )

        elif job_type in ["CLIP_RENDER", "CLIP_CAPTION_RENDER"]:
            # 8. Render master clip, aspect ratio variants, and optional burned captions
            clip_id = payload.get("clip_id")
            aspect_ratios = payload.get("aspect_ratios", ["9:16"])
            inc_thumb = payload.get("include_thumbnail", True)
            burn_caps = payload.get("burn_captions", job_type == "CLIP_CAPTION_RENDER")
            cap_style = payload.get("caption_style")
            hl_words = payload.get("highlight_keywords")

            await media_processor.process_clip_media(
                clip_id=clip_id,
                aspect_ratios=aspect_ratios,
                include_thumbnail=inc_thumb,
                burn_captions=burn_caps,
                caption_style=cap_style,
                highlight_keywords=hl_words
            )
            # Dispatch event
            from services.event_bus import event_bus_service
            async with async_session_factory() as session:
                await event_bus_service.dispatch_event("clip.ready", clip_id, session)

        elif job_type == "PLATFORM_PUBLISH":
            # 9. Execute external platform publication
            publication_id = payload.get("publication_id")
            pub_res = await publishing_service.execute_publication_job(publication_id=publication_id)

            # Auto-enqueue initial metrics sync immediately following successful publication
            if pub_res and pub_res.get("status") == "published":
                ana_job_id = f"job_ana_{uuid.uuid4().hex[:8]}"
                async with async_session_factory() as session:
                    ana_job = Job(
                        id=ana_job_id,
                        content_id=content_id,
                        type="ANALYTICS_SYNC",
                        status="QUEUED",
                        created_at=datetime.utcnow()
                    )
                    session.add(ana_job)
                    await session.commit()

                await queue_service.enqueue_media_job(
                    job_id=ana_job_id,
                    content_id=content_id,
                    job_type="ANALYTICS_SYNC",
                    publication_id=publication_id
                )
                # Dispatch event
                from services.event_bus import event_bus_service
                async with async_session_factory() as session:
                    await event_bus_service.dispatch_event("publication.succeeded", publication_id, session)
            else:
                # Dispatch failed event
                from services.event_bus import event_bus_service
                async with async_session_factory() as session:
                    await event_bus_service.dispatch_event("publication.failed", publication_id, session)

        elif job_type == "ANALYTICS_SYNC":
            # 10. Sync performance metrics from external platform
            publication_id = payload.get("publication_id")
            await analytics_service.sync_publication_metrics(publication_id=publication_id)
            # Dispatch event
            from services.event_bus import event_bus_service
            async with async_session_factory() as session:
                await event_bus_service.dispatch_event("analytics.updated", publication_id, session)

        elif job_type == "INTELLIGENCE_ANALYSIS":
            # 11. Run full content intelligence and pattern analysis pipeline
            await intelligence_service.run_full_analysis()

        elif job_type == "EXPERIMENT_EVALUATION":
            # 12. Run A/B test evaluation and statistical analysis
            experiment_id = payload.get("experiment_id")
            from services.experiment_service import experiment_service
            async with async_session_factory() as session:
                await experiment_service.evaluate_experiment(session, experiment_id)
            # Dispatch event
            from services.event_bus import event_bus_service
            async with async_session_factory() as session:
                await event_bus_service.dispatch_event("experiment.completed", experiment_id, session)

        elif job_type == "AUTOMATION_EXECUTION":
            # 13. Run rule distribution and actions pipeline
            execution_id = payload.get("execution_id")
            from services.automation_service import automation_service
            async with async_session_factory() as session:
                await automation_service.execute_execution_pipeline(session, execution_id)

        elif job_type == "QUALITY_CONTROL":
            # 14. Run governance quality checks
            variant_id = payload.get("variant_id")
            publication_id = payload.get("publication_id")
            platform = payload.get("platform", "linkedin")
            from services.quality_control_service import quality_control_service
            async with async_session_factory() as session:
                await quality_control_service.run_pipeline(
                    session=session,
                    content_id=content_id,
                    variant_id=variant_id,
                    publication_id=publication_id,
                    platform=platform
                )

        # Mark Job SUCCEEDED
        async with async_session_factory() as session:
            job_res = await session.execute(select(Job).where(Job.id == job_id))
            job = job_res.scalar_one_or_none()
            if job:
                job.status = "SUCCEEDED"
                job.completed_at = datetime.utcnow()
                job.error = None
                await session.commit()

        logger.info(f"Job {job_id} ({job_type}) completed successfully.")
        return True

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Job {job_id} ({job_type}) failed on attempt: {err_msg}")

        # Determine if error is permanent (corrupt data, missing asset/content)
        is_permanent = "not found" in err_msg.lower() or "invalid data" in err_msg.lower() or "moov atom" in err_msg.lower()

        async with async_session_factory() as session:
            job_res = await session.execute(select(Job).where(Job.id == job_id))
            job = job_res.scalar_one_or_none()

            content_res = None
            if content_id:
                content_res_obj = await session.execute(select(Content).where(Content.id == content_id))
                content_res = content_res_obj.scalar_one_or_none()

            if carousel_id and not content_id:
                c_obj = await session.execute(select(Carousel).where(Carousel.id == carousel_id))
                c_item = c_obj.scalar_one_or_none()
                if c_item:
                    c_item.status = "FAILED"

            if clip_id:
                cl_obj = await session.execute(select(Clip).where(Clip.id == clip_id))
                cl_item = cl_obj.scalar_one_or_none()
                if cl_item:
                    cl_item.status = "FAILED"

            if job:
                if not is_permanent and job.attempts < job.max_attempts:
                    job.status = "RETRYING"
                    job.error = f"Attempt {job.attempts} failed: {err_msg}"
                    await session.commit()
                    # Re-enqueue
                    await asyncio.sleep(2)
                    await queue_service.enqueue_media_job(job_id, content_id, asset_id, job_type=job_type)
                else:
                    job.status = "FAILED"
                    job.completed_at = datetime.utcnow()
                    job.error = f"Permanent failure: {err_msg}"
                    if content_res and job_type == "MEDIA_PROCESSING":
                        content_res.status = "FAILED"
                    await session.commit()
        return False

async def reconcile_orphaned_jobs():
    """Recovers jobs that were left in RUNNING state due to a worker container restart."""
    try:
        async with async_session_factory() as session:
            orphans_res = await session.execute(
                select(Job).where(Job.status == "RUNNING")
            )
            orphans = orphans_res.scalars().all()
            for job in orphans:
                logger.info(f"Reconciling orphaned job {job.id} (Type: {job.type}) reset to QUEUED.")
                job.status = "QUEUED"
                await session.commit()
                await queue_service.enqueue_media_job(
                    job.id, job.content_id, job.asset_id,
                    carousel_id=getattr(job, "carousel_id", None),
                    clip_id=getattr(job, "clip_id", None),
                    job_type=job.type
                )
    except Exception as e:
        logger.warn(f"Orphaned job reconciliation notice: {e}")

async def run_worker():
    """Continuous background worker loop."""
    logger.info(f"Reflow Media & AI Worker started (concurrency={settings.MEDIA_WORKER_CONCURRENCY}). Listening for jobs...")
    await init_db()
    await reconcile_orphaned_jobs()

    while True:
        try:
            job_payload = await queue_service.dequeue_media_job(timeout=3)
            if job_payload:
                await process_single_job(job_payload)
            else:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Media & AI Worker shutting down gracefully.")
            break
        except Exception as e:
            logger.error(f"Unexpected worker error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_worker())
