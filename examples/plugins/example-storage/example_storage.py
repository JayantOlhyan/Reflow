# EXAMPLE ONLY - Storage Driver Plugin Demonstration
from plugins.contracts.storage_contract import BaseStorageProviderPlugin
from typing import Dict, Any, Optional

class ExampleStoragePlugin(BaseStorageProviderPlugin):
    def __init__(self, manifest, config=None):
        super().__init__(manifest, config)
        self._store: Dict[str, bytes] = {}

    async def put(self, relative_path: str, data: bytes) -> str:
        self._store[relative_path] = data
        return relative_path

    async def get(self, relative_path: str) -> Optional[bytes]:
        return self._store.get(relative_path)

    async def delete(self, relative_path: str) -> bool:
        if relative_path in self._store:
            del self._store[relative_path]
            return True
        return False

    async def exists(self, relative_path: str) -> bool:
        return relative_path in self._store

    def get_real_path(self, relative_path: str) -> str:
        return f"/mock_storage/{relative_path}"
