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
from models.entities import Job, Content, Asset, Transcript, ContentBrief, GeneratedContent
from services.queue_service import queue_service
from services.media_service import media_processor
from services.storage_service import storage_service
from services.ai_service import ai_service
from utils.logging import get_logger

logger = get_logger("MediaWorker")

async def process_single_job(payload: dict) -> bool:
    """Processes a single job from the queue with dependency-ordered downstream dispatch."""
    job_id = payload.get("job_id")
    content_id = payload.get("content_id")
    asset_id = payload.get("asset_id")
    job_type = payload.get("job_type", "MEDIA_PROCESSING")

    logger.info(f"Processing job {job_id} (Type: {job_type}) for Content: {content_id}")

    async with async_session_factory() as session:
        job_res = await session.execute(select(Job).where(Job.id == job_id))
        job = job_res.scalar_one_or_none()

        content_res = await session.execute(select(Content).where(Content.id == content_id))
        content = content_res.scalar_one_or_none()

        if not job or not content:
            logger.warn(f"Job {job_id} or Content {content_id} not found in database, cancelling.")
            if job:
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

            content_res = await session.execute(select(Content).where(Content.id == content_id))
            content = content_res.scalar_one_or_none()

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
                    if content and job_type == "MEDIA_PROCESSING":
                        content.status = "FAILED"
                    await session.commit()
        return False

async def run_worker():
    """Continuous background worker loop."""
    logger.info(f"Reflow Media & AI Worker started (concurrency={settings.MEDIA_WORKER_CONCURRENCY}). Listening for jobs...")
    await init_db()

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
