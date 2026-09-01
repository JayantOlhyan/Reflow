"""
Reflow Plugin SDK
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

PLUGIN_SDK_VERSION = "1.0.0"

class PluginManifest(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str = "Developer"
    type: str
    entrypoint: str
    api_version: str = PLUGIN_SDK_VERSION
    capabilities: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    configuration: Dict[str, Any] = Field(default_factory=dict)

class BasePlugin(ABC):
    def __init__(self, manifest: PluginManifest, config: Optional[Dict[str, Any]] = None):
        self.manifest = manifest
        self.config = config or {}
        self.enabled = True

    @abstractmethod
    async def initialize(self) -> bool:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass
