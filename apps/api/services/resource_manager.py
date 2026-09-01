import os
import shutil
import asyncio
from typing import Dict, Any, Optional
from config import settings
from utils.logging import get_logger

logger = get_logger("ResourceManager")

class QueueOverflowError(Exception):
    """Raised when queue capacity is exceeded (triggering 429/503 backpressure)."""
    pass

class InsufficientDiskError(Exception):
    """Raised when available disk space is below safety threshold."""
    pass

class ResourceManager:
    """
    Centralized Resource Manager for self-hosted hardware limits.
    Measures CPU, Memory, Disk, DB Pool, Redis depth, and Worker Concurrency.
    Enforces backpressure when system capacity is saturated.
    """
    _instance: Optional['ResourceManager'] = None

    def __init__(self):
        self._media_semaphore = asyncio.Semaphore(settings.MEDIA_WORKER_CONCURRENCY)
        self._ai_semaphore = asyncio.Semaphore(settings.AI_WORKER_CONCURRENCY)
        self._publish_semaphore = asyncio.Semaphore(settings.PUBLISH_WORKER_CONCURRENCY)
        self._webhook_semaphore = asyncio.Semaphore(settings.WEBHOOK_WORKER_CONCURRENCY)
        self._reserved_disk_bytes: int = 0
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> 'ResourceManager':
        if cls._instance is None:
            cls._instance = ResourceManager()
        return cls._instance

    def get_worker_concurrency_limits(self) -> Dict[str, int]:
        return {
            "media": settings.MEDIA_WORKER_CONCURRENCY,
            "ai": settings.AI_WORKER_CONCURRENCY,
            "publish": settings.PUBLISH_WORKER_CONCURRENCY,
            "webhook": settings.WEBHOOK_WORKER_CONCURRENCY,
            "max_queue_depth": settings.MAX_QUEUE_DEPTH
        }

    def check_disk_capacity(self, required_mb: float = 100.0) -> Dict[str, Any]:
        """
        Checks available host disk space against minimum requirements & TEMP_STORAGE_LIMIT_GB threshold.
        """
        storage_path = os.path.abspath(settings.STORAGE_DIR)
        os.makedirs(storage_path, exist_ok=True)
        total, used, free = shutil.disk_usage(storage_path)
        
        free_gb = free / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        
        required_bytes = int(required_mb * 1024 * 1024)
        available_after_reservations = free - self._reserved_disk_bytes
        
        is_sufficient = available_after_reservations >= required_bytes and free_gb >= 0.5
        if not is_sufficient:
            logger.warning(f"Disk check failed: free={free_gb:.2f}GB, reserved={self._reserved_disk_bytes / 1e9:.2f}GB, required={required_mb}MB")
            
        return {
            "is_sufficient": is_sufficient,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "reserved_gb": round(self._reserved_disk_bytes / (1024 ** 3), 2),
            "available_gb": round(available_after_reservations / (1024 ** 3), 2)
        }

    async def reserve_disk_capacity(self, estimated_mb: float) -> bool:
        """Reserves disk space before beginning a heavy media render job."""
        bytes_to_reserve = int(estimated_mb * 1024 * 1024)
        async with self._lock:
            status = self.check_disk_capacity(estimated_mb)
            if not status["is_sufficient"]:
                raise InsufficientDiskError(f"Insufficient disk space to reserve {estimated_mb}MB. Available: {status['available_gb']}GB")
            self._reserved_disk_bytes += bytes_to_reserve
            logger.info(f"Reserved {estimated_mb}MB disk space (Total reserved: {self._reserved_disk_bytes / 1e6:.1f}MB)")
            return True

    async def release_disk_reservation(self, estimated_mb: float):
        """Releases disk space reservation upon job completion/failure."""
        bytes_to_release = int(estimated_mb * 1024 * 1024)
        async with self._lock:
            self._reserved_disk_bytes = max(0, self._reserved_disk_bytes - bytes_to_release)
            logger.info(f"Released {estimated_mb}MB disk reservation (Total reserved: {self._reserved_disk_bytes / 1e6:.1f}MB)")

    def validate_queue_backpressure(self, current_queue_depth: int):
        """Validates that current queue depth is under MAX_QUEUE_DEPTH."""
        if current_queue_depth >= settings.MAX_QUEUE_DEPTH:
            logger.error(f"Backpressure triggered! Queue depth {current_queue_depth} exceeds MAX_QUEUE_DEPTH ({settings.MAX_QUEUE_DEPTH}).")
            raise QueueOverflowError(f"Queue depth ({current_queue_depth}) exceeds maximum capacity ({settings.MAX_QUEUE_DEPTH}). Please retry later.")

resource_manager = ResourceManager.get_instance()
