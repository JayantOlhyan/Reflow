import os
import aiofiles
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from config import settings
from utils.logging import get_logger

logger = get_logger("StorageService")

ALLOWED_EXTENSIONS = {
    "mp4", "mov", "avi", "mkv", "webm",
    "png", "jpg", "jpeg", "webp", "gif",
    "pdf", "txt", "md"
}

ALLOWED_MIME_PREFIXES = {"video/", "image/", "application/pdf", "text/"}
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB

def validate_upload(filename: str, mime_type: str, file_size: int) -> Tuple[bool, Optional[str]]:
    """Validates file upload extension, MIME type, and size to prevent unsafe uploads."""
    if not filename or "." not in filename:
        return False, "Invalid filename. File must have an extension."
    
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file extension '.{ext}'."
    
    if not any(mime_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        return False, f"Unsupported MIME type '{mime_type}'."
        
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, f"File exceeds maximum allowed size of 500MB."
        
    return True, None

class BaseStorageService(ABC):
    @abstractmethod
    async def put(self, relative_path: str, data: bytes) -> str:
        """Stores binary data at the specified path and returns the resolved path/key."""
        pass

    @abstractmethod
    async def get(self, relative_path: str) -> Optional[bytes]:
        """Retrieves binary data from the specified path."""
        pass

    @abstractmethod
    async def delete(self, relative_path: str) -> bool:
        """Deletes file at the specified path."""
        pass

    @abstractmethod
    async def exists(self, relative_path: str) -> bool:
        """Checks if file exists at the specified path."""
        pass

    @abstractmethod
    def get_url(self, relative_path: str) -> str:
        """Returns public or internal accessible URL for the stored asset."""
        pass

class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.STORAGE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> str:
        """Prevents path traversal by ensuring the target stays within base_dir."""
        clean_path = os.path.normpath(relative_path).lstrip("/")
        full_path = os.path.abspath(os.path.join(self.base_dir, clean_path))
        if not full_path.startswith(self.base_dir):
            raise ValueError("Access denied: path traversal attempt detected.")
        return full_path

    async def put(self, relative_path: str, data: bytes) -> str:
        safe_path = self._resolve_safe_path(relative_path)
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        async with aiofiles.open(safe_path, "wb") as f:
            await f.write(data)
        logger.info(f"Stored file: {relative_path}")
        return safe_path

    async def get(self, relative_path: str) -> Optional[bytes]:
        safe_path = self._resolve_safe_path(relative_path)
        if not os.path.exists(safe_path):
            return None
        async with aiofiles.open(safe_path, "rb") as f:
            return await f.read()

    async def delete(self, relative_path: str) -> bool:
        safe_path = self._resolve_safe_path(relative_path)
        if os.path.exists(safe_path):
            os.remove(safe_path)
            logger.info(f"Deleted file: {relative_path}")
            return True
        return False

    async def exists(self, relative_path: str) -> bool:
        safe_path = self._resolve_safe_path(relative_path)
        return os.path.exists(safe_path)

    def get_url(self, relative_path: str) -> str:
        clean_rel = relative_path.lstrip("/")
        return f"/storage/{clean_rel}"

def get_storage_service() -> BaseStorageService:
    # Phase 0 defaults cleanly to local filesystem storage
    return LocalStorageService()

storage_service = get_storage_service()
