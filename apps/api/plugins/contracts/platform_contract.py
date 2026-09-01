from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from plugins.base_plugin import BasePlugin
from plugins.manifest import PluginManifest, PluginType, PluginPermission
from connectors.base import BasePlatformConnector, PlatformCapabilities

class BasePlatformConnectorPlugin(BasePlugin, BasePlatformConnector):
    """
    Plugin contract interface for Social Media Platform Connectors.
    Extends BasePlugin and BasePlatformConnector.
    """
    def __init__(self, manifest: PluginManifest, config: Optional[Dict[str, Any]] = None):
        BasePlugin.__init__(self, manifest, config)
        self.platform_id = manifest.id.replace("-connector", "")
        self.platform_name = manifest.name

    async def initialize(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "platform": self.platform_id}

    @abstractmethod
    def get_capabilities(self) -> PlatformCapabilities:
        pass

    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        pass
