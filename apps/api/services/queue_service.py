import json
import asyncio
from typing import Optional, Dict, Any
from config import settings
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

    async def enqueue_media_job(self, job_id: str, content_id: str, asset_id: str, job_type: str = "MEDIA_PROCESSING") -> bool:
        """Pushes a job to the Redis queue or fallback queue."""
        payload = {
            "job_id": job_id,
            "content_id": content_id,
            "asset_id": asset_id,
            "job_type": job_type
        }
        raw_msg = json.dumps(payload)

        try:
            r = await self.get_redis_client()
            if r:
                await r.rpush(self.queue_name, raw_msg)
                logger.info(f"Enqueued {job_type} job {job_id} to Redis queue '{self.queue_name}'.")
                return True
        except Exception as e:
            logger.warning(f"Redis enqueue failed ({e}), pushing to in-process queue.")

        await self._fallback_queue.put(payload)
        logger.info(f"Enqueued {job_type} job {job_id} to fallback queue.")
        return True

    async def dequeue_media_job(self, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """Pops a job from the Redis queue or fallback queue."""
        try:
            r = await self.get_redis_client()
            if r:
                res = await r.blpop(self.queue_name, timeout=timeout)
                if res:
                    _, raw_msg = res
                    return json.loads(raw_msg)
        except Exception as e:
            pass

        try:
            return await asyncio.wait_for(self._fallback_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

queue_service = QueueService()
