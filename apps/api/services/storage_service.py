import os
import aiofiles
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict
from config import settings
from utils.logging import get_logger

logger = get_logger("StorageService")

EXTENSION_TO_CONTENT_TYPE = {
    # Video
    "mp4": "VIDEO",
    "mov": "VIDEO",
    "webm": "VIDEO",
    "mkv": "VIDEO",
    # Image
    "jpg": "IMAGE",
    "jpeg": "IMAGE",
    "png": "IMAGE",
    "webp": "IMAGE",
    # PDF
    "pdf": "PDF",
    # Text
    "txt": "TEXT",
    "md": "TEXT"
}

ALLOWED_MIME_PREFIXES = {
    "video/", "image/", "application/pdf", "text/", "application/octet-stream"
}

def detect_content_type(filename: str) -> Optional[str]:
    if not filename or "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    return EXTENSION_TO_CONTENT_TYPE.get(ext)

def validate_upload(filename: str, mime_type: str, file_size: int) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Multi-layer validation for uploaded file.
    Returns: (is_valid, content_type_or_none, error_message_or_none)
    """
    if not filename or "." not in filename:
        return False, None, "Invalid filename. File must have an extension."
    
    ext = filename.rsplit(".", 1)[-1].lower()
    content_type = EXTENSION_TO_CONTENT_TYPE.get(ext)
    if not content_type:
        return False, None, f"Unsupported file extension '.{ext}'. Supported: {', '.join(sorted(EXTENSION_TO_CONTENT_TYPE.keys()))}"
    
    # MIME validation
    if mime_type and not any(mime_type.lower().startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        return False, None, f"Unsupported MIME type '{mime_type}'."
        
    # Size validation
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        return False, None, f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        
    return True, content_type, None

def generate_storage_key(content_id: str, asset_id: str, filename: str) -> str:
    """Generates collision-free, path-safe storage key."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"content/{content_id}/original/{asset_id}.{ext}"

class BaseStorageService(ABC):
    @abstractmethod
    async def put(self, relative_path: str, data: bytes) -> str:
        pass

    @abstractmethod
    async def get(self, relative_path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    async def delete(self, relative_path: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, relative_path: str) -> bool:
        pass

    @abstractmethod
    def get_real_path(self, relative_path: str) -> str:
        pass

class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.STORAGE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> str:
        clean_path = os.path.normpath(relative_path).lstrip("/")
        full_path = os.path.abspath(os.path.join(self.base_dir, clean_path))
        if not full_path.startswith(self.base_dir):
            raise ValueError(f"Path traversal detected for '{relative_path}'. Access denied.")
        return full_path

    async def put(self, relative_path: str, data: bytes) -> str:
        safe_path = self._resolve_safe_path(relative_path)
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        async with aiofiles.open(safe_path, "wb") as f:
            await f.write(data)
        logger.info(f"Persisted storage file: {relative_path}")
        return relative_path

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
            logger.info(f"Deleted storage file: {relative_path}")
            return True
        return False

    async def exists(self, relative_path: str) -> bool:
        safe_path = self._resolve_safe_path(relative_path)
        return os.path.exists(safe_path)

    def get_real_path(self, relative_path: str) -> str:
        return self._resolve_safe_path(relative_path)

def get_storage_service() -> BaseStorageService:
    return LocalStorageService()

storage_service = get_storage_service()
