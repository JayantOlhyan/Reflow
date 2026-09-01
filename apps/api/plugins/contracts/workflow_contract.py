from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from plugins.base_plugin import BasePlugin
from plugins.manifest import PluginManifest

class BaseWorkflowActionPlugin(BasePlugin, ABC):
    """
    Plugin contract interface for Workflow Automation Actions (Webhook, Email, Slack, CustomTransform).
    """
    action_name: str
    action_description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    def __init__(self, manifest: PluginManifest, config: Optional[Dict[str, Any]] = None):
        super().__init__(manifest, config)
        self.action_name = manifest.name
        self.action_description = manifest.description
        self.input_schema = manifest.configuration.get("input_schema", {})
        self.output_schema = manifest.configuration.get("output_schema", {})

    async def initialize(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "action": self.action_name}

    @abstractmethod
    async def execute(self, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes action logic with typed payload and execution context.
        Returns output dictionary matching output_schema.
        """
        pass
