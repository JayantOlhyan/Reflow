import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, delete, func

from config import settings
from database import async_session_factory
from models.entities import SystemJob, DeadLetterJob
from services.resource_manager import resource_manager, QueueOverflowError
from utils.logging import get_logger

logger = get_logger("QueueService")

class QueueService:
    """
    Priority-Aware Queue Service with Concurrency Control & Backpressure Protection.
    Supports Priority Levels: CRITICAL, HIGH, NORMAL, LOW.
    Resource Categories: CPU_INTENSIVE, MEMORY_INTENSIVE, NETWORK, LIGHTWEIGHT.
    """
    def __init__(self):
        self.queue_name = settings.REDIS_MEDIA_QUEUE
        self._redis = None
        self._fallback_queue_items: List[Dict[str, Any]] = []

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
        self._fallback_queue_items.clear()

    async def get_queue_depth(self) -> int:
        """Returns total current pending queued jobs across Redis and Fallback queues."""
        try:
            r = await self.get_redis_client()
            if r:
                return await r.llen(self.queue_name)
        except Exception:
            pass
        return len(self._fallback_queue_items)

    async def enqueue_media_job(
        self, 
        job_id: str, 
        content_id: Optional[str] = None, 
        asset_id: Optional[str] = None,
        publication_id: Optional[str] = None,
        job_type: str = "MEDIA_PROCESSING",
        priority: str = "NORMAL",
        resource_category: str = "LIGHTWEIGHT",
        max_retries: int = 3,
        **kwargs
    ) -> bool:
        """
        Pushes a job to Redis/Fallback queue with backpressure checks and priority tags.
        """
        current_depth = await self.get_queue_depth()
        resource_manager.validate_queue_backpressure(current_depth)

        payload = {
            "job_id": job_id,
            "content_id": content_id,
            "asset_id": asset_id,
            "publication_id": publication_id,
            "job_type": job_type,
            "priority": priority.upper(),
            "resource_category": resource_category.upper(),
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
                # High/Critical priority jobs pushed to left (processed first), others to right
                if priority.upper() in ("CRITICAL", "HIGH"):
                    await r.lpush(self.queue_name, raw_msg)
                else:
                    await r.rpush(self.queue_name, raw_msg)
                logger.info(f"Enqueued {priority} {job_type} job {job_id} to Redis queue '{self.queue_name}'.", extra={"job_id": job_id, "content_id": content_id})
                return True
        except Exception as e:
            logger.warning(f"Redis enqueue failed ({e}), pushing to in-process queue.")

        if priority.upper() in ("CRITICAL", "HIGH"):
            self._fallback_queue_items.insert(0, payload)
        else:
            self._fallback_queue_items.append(payload)

        logger.info(f"Enqueued {priority} {job_type} job {job_id} to fallback queue.", extra={"job_id": job_id, "content_id": content_id})
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
            if self._fallback_queue_items:
                job_data = self._fallback_queue_items.pop(0)

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

    async def complete_job(self, job_id: str, result_summary: Optional[str] = None):
        """Marks a SystemJob as SUCCEEDED in the database."""
        async with async_session_factory() as session:
            res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
            job = res.scalar_one_or_none()
            if job:
                job.status = "SUCCEEDED"
                job.completed_at = datetime.utcnow()
                job.error_message = None
                await session.commit()
                logger.info(f"SystemJob '{job_id}' completed successfully.", extra={"job_id": job_id})

    async def fail_job(self, job_id: str, error_message: str, error_code: str = "PROCESSING_FAILED") -> bool:
        """Handles job failure, increments retry count, or moves to Dead Letter Queue."""
        async with async_session_factory() as session:
            res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
            job = res.scalar_one_or_none()
            if not job:
                logger.error(f"Cannot fail non-existent SystemJob '{job_id}'.")
                return False

            job.retry_count += 1
            job.error_code = error_code
            job.last_error = error_message

            if job.retry_count < job.max_retries:
                job.status = "QUEUED"
                backoff_delay = min(300, 2 ** job.retry_count * 2)
                await session.commit()

                # Re-enqueue
                try:
                    r = await self.get_redis_client()
                    if r:
                        await r.rpush(self.queue_name, job.payload_json)
                    else:
                        payload = json.loads(job.payload_json)
                        self._fallback_queue_items.append(payload)
                except Exception:
                    pass
                logger.warning(f"SystemJob '{job_id}' failed (Attempt {job.retry_count}/{job.max_retries}). Retrying in {backoff_delay}s.", extra={"job_id": job_id})
                return False

            # Exhausted retries -> Dead Letter Queue
            job.status = "FAILED"
            job.failed_at = datetime.utcnow()

            existing_dlq_res = await session.execute(select(DeadLetterJob).where(DeadLetterJob.job_id == job.id))
            if not existing_dlq_res.scalar_one_or_none():
                dlq = DeadLetterJob(
                    id=f"dlq_{uuid.uuid4().hex[:10]}",
                    job_id=job.id,
                    job_type=job.job_type,
                    content_id=job.content_id,
                    publication_id=job.publication_id,
                    attempts=job.retry_count,
                    error_code=error_code,
                    last_error=error_message,
                    failed_at=datetime.utcnow()
                )
                session.add(dlq)
            await session.commit()
            logger.error(f"SystemJob '{job_id}' permanently failed and moved to Dead Letter Queue (DLQ).", extra={"job_id": job_id})
            return True

    async def record_job_failure(self, job_id: str, error_message: str, error_code: str = "PROCESSING_FAILED", retryable: bool = True) -> bool:
        """Alias for compatibility with failure tracking."""
        return await self.fail_job(job_id=job_id, error_message=error_message, error_code=error_code)

    async def detect_stale_jobs(self, timeout_minutes: int = 10) -> int:
        """Finds RUNNING jobs older than timeout_minutes and marks them STALE."""
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        async with async_session_factory() as session:
            res = await session.execute(
                select(SystemJob).where(
                    SystemJob.status == "RUNNING",
                    SystemJob.started_at <= threshold
                )
            )
            stale_jobs = res.scalars().all()
            for job in stale_jobs:
                job.status = "STALE"
            await session.commit()
            return len(stale_jobs)

    async def get_queue_metrics(self) -> Dict[str, Any]:
        """Calculates comprehensive queue metrics for telemetry and performance monitoring."""
        current_depth = await self.get_queue_depth()
        async with async_session_factory() as session:
            # Count queued jobs by type
            type_stmt = select(SystemJob.job_type, func.count()).where(SystemJob.status == "QUEUED").group_by(SystemJob.job_type)
            type_res = await session.execute(type_stmt)
            by_type = dict(type_res.all())

            # Oldest queued job age
            oldest_stmt = select(func.min(SystemJob.queued_at)).where(SystemJob.status == "QUEUED")
            oldest_res = await session.execute(oldest_stmt)
            oldest_ts = oldest_res.scalar()
            oldest_age_sec = (datetime.utcnow() - oldest_ts).total_seconds() if oldest_ts else 0

            # Count total jobs by status
            status_stmt = select(SystemJob.status, func.count()).group_by(SystemJob.status)
            status_res = await session.execute(status_stmt)
            by_status = dict(status_res.all())

            return {
                "queue_depth": current_depth,
                "max_queue_depth": settings.MAX_QUEUE_DEPTH,
                "oldest_job_age_seconds": round(oldest_age_sec, 1),
                "by_type": by_type,
                "by_status": by_status,
                "is_saturated": current_depth >= settings.MAX_QUEUE_DEPTH
            }

queue_service = QueueService()
