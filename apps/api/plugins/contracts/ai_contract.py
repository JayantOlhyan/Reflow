from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from plugins.base_plugin import BasePlugin
from plugins.manifest import PluginManifest, PluginType
from services.ai.base_provider import BaseAIProvider
from utils.logging import get_logger

logger = get_logger("AIProviderRegistry")

class BaseAIProviderPlugin(BasePlugin, BaseAIProvider):
    """
    Plugin contract interface for AI Providers (Gemini, OpenAI, Anthropic, Custom LLM).
    Extends BasePlugin and BaseAIProvider.
    """
    def __init__(self, manifest: PluginManifest, config: Optional[Dict[str, Any]] = None):
        BasePlugin.__init__(self, manifest, config)
        self.provider_name = manifest.id.replace("-provider", "")

    async def initialize(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "provider": self.provider_name}

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generates plain text output."""
        res = await self.generate_platform("general", {"summary": prompt}, tone="professional")
        return res.get("text_content") or str(res)

    async def generate_structured(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generates structured JSON output matching schema."""
        return await self.analyze_content("Structured Generation", prompt, None)


class AIProviderRegistry:
    """Registry managing active AI Provider plugins."""
    _instance: Optional['AIProviderRegistry'] = None

    def __init__(self):
        self._providers: Dict[str, BaseAIProviderPlugin] = {}
        self._default_provider: str = "gemini"

    @classmethod
    def get_instance(cls) -> 'AIProviderRegistry':
        if cls._instance is None:
            cls._instance = AIProviderRegistry()
        return cls._instance

    def register_provider(self, provider: BaseAIProviderPlugin) -> None:
        name = provider.provider_name.lower()
        self._providers[name] = provider
        logger.info(f"Registered AI Provider plugin: {name}")

    def get_provider(self, name: Optional[str] = None) -> Optional[BaseAIProviderPlugin]:
        target = (name or self._default_provider).lower()
        return self._providers.get(target) or self._providers.get(self._default_provider)

    def set_default_provider(self, name: str) -> bool:
        if name.lower() in self._providers:
            self._default_provider = name.lower()
            logger.info(f"Set default AI provider to: {name}")
            return True
        return False

    def list_providers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.provider_name,
                "model": p.model_name,
                "is_default": name == self._default_provider,
                "capabilities": p.manifest.capabilities
            }
            for name, p in self._providers.items()
        ]

ai_provider_registry = AIProviderRegistry.get_instance()
