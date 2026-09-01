import os
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import async_session_factory
from models.entities import TmpFileRecord, Asset, ClipVariant, CarouselExport
from utils.logging import get_logger

logger = get_logger("TmpStorageService")

class TmpStorageService:
    """
    Manages temporary file allocation, lifetime tracking, and scheduled purges.
    Maintains breakdown of disk usage across originals, variants, clips, carousels, exports, and temp files.
    """
    _instance: Optional['TmpStorageService'] = None

    def __init__(self):
        self.tmp_dir = os.path.abspath(os.path.join(settings.STORAGE_DIR, "tmp"))
        os.makedirs(self.tmp_dir, exist_ok=True)

    @classmethod
    def get_instance(cls) -> 'TmpStorageService':
        if cls._instance is None:
            cls._instance = TmpStorageService()
        return cls._instance

    def create_tmp_file_path(self, prefix: str = "tmp", extension: str = ".tmp") -> str:
        """Generates a safe managed temporary file path inside storage/tmp/."""
        filename = f"{prefix}_{uuid.uuid4().hex[:12]}{extension}"
        return os.path.join(self.tmp_dir, filename)

    async def register_tmp_file(
        self,
        db: AsyncSession,
        file_path: str,
        owner: str = "system",
        ttl_hours: int = 24
    ) -> TmpFileRecord:
        """Registers a temporary file in DB with owner and expiration timestamp."""
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        rec = TmpFileRecord(
            id=f"tmp_{uuid.uuid4().hex[:10]}",
            file_path=os.path.abspath(file_path),
            owner=owner,
            file_size=file_size,
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        return rec

    async def purge_expired_tmp_files(self, db: AsyncSession) -> Dict[str, Any]:
        """Purges expired temporary files from disk and removes database records."""
        now = datetime.utcnow()
        res = await db.execute(select(TmpFileRecord).where(TmpFileRecord.expires_at <= now))
        records = res.scalars().all()

        purged_count = 0
        freed_bytes = 0

        for r in records:
            if os.path.exists(r.file_path):
                try:
                    size = os.path.getsize(r.file_path)
                    os.remove(r.file_path)
                    freed_bytes += size
                except Exception as e:
                    logger.warning(f"Failed to delete temp file '{r.file_path}': {e}")
            await db.delete(r)
            purged_count += 1

        # Also sweep files in storage/tmp/ older than 24h not tracked in DB
        for fname in os.listdir(self.tmp_dir):
            fpath = os.path.join(self.tmp_dir, fname)
            if os.path.isfile(fpath):
                file_age_hours = (datetime.utcnow().timestamp() - os.path.getmtime(fpath)) / 3600.0
                if file_age_hours > 24:
                    try:
                        freed_bytes += os.path.getsize(fpath)
                        os.remove(fpath)
                        purged_count += 1
                    except Exception:
                        pass

        await db.commit()
        logger.info(f"Purged {purged_count} expired temporary files (Freed {freed_bytes / (1024**2):.2f} MB)")
        return {
            "purged_count": purged_count,
            "freed_mb": round(freed_bytes / (1024 ** 2), 2)
        }

    def _get_dir_size(self, path: str) -> int:
        """Calculates total directory size in bytes recursively."""
        if not os.path.exists(path):
            return 0
        total = 0
        if os.path.isfile(path):
            return os.path.getsize(path)
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
        return total

    async def get_storage_breakdown(self, db: AsyncSession) -> Dict[str, Any]:
        """Returns exact disk storage breakdown across all categories."""
        storage_base = os.path.abspath(settings.STORAGE_DIR)
        
        tmp_size = self._get_dir_size(self.tmp_dir)
        originals_size = self._get_dir_size(os.path.join(storage_base, "uploads"))
        variants_size = self._get_dir_size(os.path.join(storage_base, "variants"))
        clips_size = self._get_dir_size(os.path.join(storage_base, "clips"))
        carousels_size = self._get_dir_size(os.path.join(storage_base, "carousels"))
        exports_size = self._get_dir_size(os.path.join(storage_base, "exports"))
        
        total_used = originals_size + variants_size + clips_size + carousels_size + exports_size + tmp_size
        
        return {
            "categories": {
                "originals_mb": round(originals_size / (1024 ** 2), 2),
                "variants_mb": round(variants_size / (1024 ** 2), 2),
                "clips_mb": round(clips_size / (1024 ** 2), 2),
                "carousels_mb": round(carousels_size / (1024 ** 2), 2),
                "exports_mb": round(exports_size / (1024 ** 2), 2),
                "temporary_mb": round(tmp_size / (1024 ** 2), 2)
            },
            "total_used_mb": round(total_used / (1024 ** 2), 2),
            "total_used_gb": round(total_used / (1024 ** 3), 2),
            "quota_gb": settings.MAX_STORAGE_GB,
            "temp_limit_gb": settings.TEMP_STORAGE_LIMIT_GB
        }

tmp_storage_service = TmpStorageService.get_instance()
