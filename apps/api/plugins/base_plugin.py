from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from plugins.manifest import PluginManifest

class BasePlugin(ABC):
    """
    Base contract interface for all Reflow plugins.
    Every plugin must declare a manifest and implement lifecycle methods.
    """
    manifest: PluginManifest

    def __init__(self, manifest: PluginManifest, config: Optional[Dict[str, Any]] = None):
        self.manifest = manifest
        self.config = config or {}
        self.enabled: bool = True

    @abstractmethod
    async def initialize(self) -> bool:
        """Called when plugin is loaded into memory."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Called when plugin is unloaded or disabled."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Exposes plugin health status."""
        pass

    def configuration_schema(self) -> Dict[str, Any]:
        """Returns JSON schema describing expected configuration parameters."""
        return self.manifest.configuration
