import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, delete, func

from config import settings
from database import async_session_factory
from models.entities import SystemJob, DeadLetterJob
from utils.logging import get_logger

logger = get_logger("QueueService")

class QueueService:
    def __init__(self):
        self.queue_name = settings.REDIS_MEDIA_QUEUE
        self._redis = None
        self._fallback_queue: asyncio.Queue = asyncio.Queue()

    async def get_redis_client(self):
        if self._redis is None and settings.REDIS_URL:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2.0)
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis not available ({e}), using in-process queue fallback.")
                self._redis = None
        return self._redis

    def clear_queue(self):
        """Drains in-process fallback queue (used in testing)."""
        while not self._fallback_queue.empty():
            try:
                self._fallback_queue.get_nowait()
            except Exception:
                break

    async def enqueue_media_job(
        self, 
        job_id: str, 
        content_id: Optional[str] = None, 
        asset_id: Optional[str] = None,
        publication_id: Optional[str] = None,
        job_type: str = "MEDIA_PROCESSING",
        max_retries: int = 3,
        **kwargs
    ) -> bool:
        """Pushes a job to Redis/Fallback queue and records SystemJob entity."""
        payload = {
            "job_id": job_id,
            "content_id": content_id,
            "asset_id": asset_id,
            "publication_id": publication_id,
            "job_type": job_type,
            **kwargs
        }
        raw_msg = json.dumps(payload)

        # Record SystemJob state in DB
        async with async_session_factory() as session:
            job_obj = SystemJob(
                id=job_id,
                job_type=job_type,
                status="QUEUED",
                content_id=content_id,
                asset_id=asset_id,
                publication_id=publication_id,
                retry_count=0,
                max_retries=max_retries,
                queued_at=datetime.utcnow(),
                payload_json=raw_msg
            )
            session.add(job_obj)
            await session.commit()

        try:
            r = await self.get_redis_client()
            if r:
                await r.rpush(self.queue_name, raw_msg)
                logger.info(f"Enqueued {job_type} job {job_id} to Redis queue '{self.queue_name}'.", extra={"job_id": job_id, "content_id": content_id})
                return True
        except Exception as e:
            logger.warning(f"Redis enqueue failed ({e}), pushing to in-process queue.")

        await self._fallback_queue.put(payload)
        logger.info(f"Enqueued {job_type} job {job_id} to fallback queue.", extra={"job_id": job_id, "content_id": content_id})
        return True

    async def dequeue_media_job(self, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """Pops a job from the Redis queue or fallback queue and marks RUNNING."""
        job_data = None
        try:
            r = await self.get_redis_client()
            if r:
                res = await r.blpop(self.queue_name, timeout=timeout)
                if res:
                    _, raw_msg = res
                    job_data = json.loads(raw_msg)
        except Exception:
            pass

        if not job_data:
            try:
                job_data = await asyncio.wait_for(self._fallback_queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                return None

        if job_data and "job_id" in job_data:
            job_id = job_data["job_id"]
            async with async_session_factory() as session:
                res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
                job = res.scalar_one_or_none()
                if job:
                    job.status = "RUNNING"
                    job.started_at = datetime.utcnow()
                    await session.commit()

        return job_data

    async def record_job_completion(self, job_id: str, duration_ms: float = 0.0):
        """Marks a SystemJob as SUCCEEDED."""
        async with async_session_factory() as session:
            res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
            job = res.scalar_one_or_none()
            if job:
                job.status = "SUCCEEDED"
                job.completed_at = datetime.utcnow()
                job.duration_ms = duration_ms
                await session.commit()

    async def record_job_failure(
        self,
        job_id: str,
        error_message: str,
        error_code: str = "INTERNAL_ERROR",
        retryable: bool = True
    ):
        """
        Handles job failure: increments retry count, performs exponential backoff re-queueing
        if retries remain, or routes permanent failures to DeadLetterJob (DLQ).
        """
        async with async_session_factory() as session:
            res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
            job = res.scalar_one_or_none()
            
            if not job:
                return

            job.retry_count += 1
            job.last_error = error_message
            job.error_code = error_code

            if retryable and job.retry_count <= job.max_retries:
                job.status = "QUEUED"
                await session.commit()
                
                # Re-queue job
                payload = json.loads(job.payload_json or "{}")
                payload["retry_count"] = job.retry_count
                raw_msg = json.dumps(payload)
                try:
                    r = await self.get_redis_client()
                    if r:
                        await r.rpush(self.queue_name, raw_msg)
                    else:
                        await self._fallback_queue.put(payload)
                except Exception:
                    await self._fallback_queue.put(payload)
                logger.warning(f"Job {job_id} failed (attempt {job.retry_count}/{job.max_retries}). Re-queued for retry.")
            else:
                # Permanent Failure -> Dead Letter Queue (DLQ)
                job.status = "FAILED"
                job.failed_at = datetime.utcnow()

                dlq_entry = DeadLetterJob(
                    id=str(uuid.uuid4()),
                    job_id=job_id,
                    job_type=job.job_type,
                    content_id=job.content_id,
                    publication_id=job.publication_id,
                    attempts=job.retry_count,
                    last_error=error_message,
                    error_code=error_code,
                    failed_at=datetime.utcnow()
                )
                session.add(dlq_entry)
                await session.commit()
                logger.error(f"Job {job_id} permanently failed after {job.retry_count} attempts. Routed to DeadLetterJob queue.")

                # Trigger incident check if needed
                from services.incident_service import incident_service
                await incident_service.report_job_failure(
                    component=job.job_type,
                    error_code=error_code,
                    message=error_message,
                    job_id=job_id,
                    content_id=job.content_id
                )

    async def detect_stale_jobs(self, timeout_minutes: int = 10) -> int:
        """Detects jobs stuck in RUNNING beyond timeout_minutes and marks STALE."""
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stale_count = 0
        async with async_session_factory() as session:
            res = await session.execute(
                select(SystemJob).where(SystemJob.status == "RUNNING", SystemJob.started_at < cutoff)
            )
            stale_jobs = res.scalars().all()
            for sj in stale_jobs:
                sj.status = "STALE"
                sj.last_error = f"Job timed out after remaining RUNNING for >{timeout_minutes}m."
                sj.error_code = "STALE_JOB_TIMEOUT"
                stale_count += 1
                logger.warning(f"Stale job detected: {sj.id} (type={sj.job_type}). Marked STALE.")

                # Route stale job to DLQ
                dlq = DeadLetterJob(
                    id=str(uuid.uuid4()),
                    job_id=sj.id,
                    job_type=sj.job_type,
                    content_id=sj.content_id,
                    publication_id=sj.publication_id,
                    attempts=sj.retry_count,
                    last_error=sj.last_error,
                    error_code="STALE_JOB_TIMEOUT"
                )
                session.add(dlq)

            await session.commit()
        return stale_count

queue_service = QueueService()
