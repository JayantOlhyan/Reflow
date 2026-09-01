from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from plugins.base_plugin import BasePlugin
from plugins.manifest import PluginManifest
from services.storage_service import BaseStorageService

class BaseStorageProviderPlugin(BasePlugin, BaseStorageService):
    """
    Plugin contract interface for Storage Providers (Local, S3, MinIO).
    Extends BasePlugin and BaseStorageService.
    """
    def __init__(self, manifest: PluginManifest, config: Optional[Dict[str, Any]] = None):
        BasePlugin.__init__(self, manifest, config)

    async def initialize(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "provider": self.manifest.id}

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

    def get_url(self, relative_path: str) -> str:
        """Returns accessible download/stream URL for asset."""
        return f"/storage/{relative_path.lstrip('/')}"
