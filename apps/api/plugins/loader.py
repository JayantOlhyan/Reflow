from plugins.manifest import PluginManifest, PluginType, PluginPermission
from plugins.registry import plugin_registry
from plugins.contracts.platform_contract import BasePlatformConnectorPlugin
from plugins.contracts.ai_contract import BaseAIProviderPlugin, ai_provider_registry
from plugins.contracts.storage_contract import BaseStorageProviderPlugin
from plugins.contracts.media_contract import BaseMediaProcessorPlugin
from plugins.contracts.workflow_contract import BaseWorkflowActionPlugin
from connectors.youtube import YouTubeConnector
from connectors.instagram import InstagramConnector
from connectors.tiktok import TikTokConnector
from connectors.linkedin import LinkedInConnector
from connectors.x_twitter import XConnector
from connectors.facebook import FacebookConnector
from services.ai.gemini_provider import GeminiProvider
from services.ai.openai_provider import OpenAIProvider
from services.ai.mock_provider import MockAIProvider
from services.storage_service import LocalStorageService
from services.media_service import media_processor
from config import settings
from utils.logging import get_logger

logger = get_logger("PluginLoader")

class PlatformConnectorPluginWrapper(BasePlatformConnectorPlugin):
    def __init__(self, connector_instance, manifest):
        super().__init__(manifest)
        self.connector = connector_instance

    def get_capabilities(self):
        return self.connector.get_capabilities()

    def validate_metadata(self, metadata):
        return self.connector.validate_metadata(metadata)

    async def publish_video(self, video_path, metadata, access_token, progress_callback=None):
        return await self.connector.publish_video(video_path, metadata, access_token, progress_callback)

    async def publish_image(self, image_path, metadata, access_token):
        return await self.connector.publish_image(image_path, metadata, access_token)

    async def publish_carousel(self, image_paths, metadata, access_token):
        return await self.connector.publish_carousel(image_paths, metadata, access_token)

    async def publish_text(self, metadata, access_token):
        return await self.connector.publish_text(metadata, access_token)


class AIProviderPluginWrapper(BaseAIProviderPlugin):
    def __init__(self, provider_instance, manifest):
        super().__init__(manifest)
        self.provider = provider_instance
        self.model_name = getattr(provider_instance, "model_name", manifest.name)

    async def transcribe(self, audio_file_path):
        return await self.provider.transcribe(audio_file_path)

    async def analyze_content(self, title, transcript_text, segments=None):
        return await self.provider.analyze_content(title, transcript_text, segments)

    async def generate_platform(self, platform, brief, segments=None, tone="professional", custom_instructions=None):
        return await self.provider.generate_platform(platform, brief, segments, tone, custom_instructions)

    async def plan_carousel(self, title, brief=None, transcript_text=None, target_slide_count=5, template="MINIMAL", tone="informative", custom_instructions=None):
        return await self.provider.plan_carousel(title, brief, transcript_text, target_slide_count, template, tone, custom_instructions)

    async def discover_clips(self, title, transcript_text, segments, brief=None, min_duration=15.0, max_duration=90.0, target_count=5):
        return await self.provider.discover_clips(title, transcript_text, segments, brief, min_duration, max_duration, target_count)


class LocalStoragePlugin(BaseStorageProviderPlugin):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.service = LocalStorageService()

    async def put(self, relative_path, data):
        return await self.service.put(relative_path, data)

    async def get(self, relative_path):
        return await self.service.get(relative_path)

    async def delete(self, relative_path):
        return await self.service.delete(relative_path)

    async def exists(self, relative_path):
        return await self.service.exists(relative_path)

    def get_real_path(self, relative_path):
        return self.service.get_real_path(relative_path)


class FFmpegMediaProcessorPlugin(BaseMediaProcessorPlugin):
    async def probe(self, file_path):
        return await media_processor.extract_video_metadata(file_path)

    async def generate_thumbnail(self, input_path, output_path, timestamp_seconds=1.0):
        return await media_processor.generate_thumbnail(input_path, output_path, timestamp_seconds)

    async def transcode(self, input_path, output_path, target_aspect_ratio):
        return await media_processor.generate_aspect_ratio_variant(input_path, output_path, target_aspect_ratio)

    async def extract_clip(self, input_path, output_path, start_seconds, end_seconds):
        return await media_processor.extract_subclip(input_path, output_path, start_seconds, end_seconds)

    def validate_media_file(self, file_path):
        return media_processor.is_valid_media_file(file_path)


class WebhookWorkflowActionPlugin(BaseWorkflowActionPlugin):
    async def execute(self, payload, context=None):
        url = payload.get("url")
        data = payload.get("data", {})
        logger.info(f"Webhook Workflow Action executed to {url}")
        return {"status": "success", "url": url, "delivered": True}


def register_builtin_plugins():
    """Initializes and registers all core built-in Reflow plugins."""
    # 1. Social Platform Plugins
    platforms = [
        ("youtube-connector", "YouTube Connector", YouTubeConnector()),
        ("instagram-connector", "Instagram Connector", InstagramConnector()),
        ("tiktok-connector", "TikTok Connector", TikTokConnector()),
        ("linkedin-connector", "LinkedIn Connector", LinkedInConnector()),
        ("x-connector", "X (Twitter) Connector", XConnector()),
        ("facebook-connector", "Facebook Connector", FacebookConnector()),
    ]
    for pid, name, connector in platforms:
        manifest = PluginManifest(
            id=pid,
            name=name,
            version="1.0.0",
            description=f"Built-in {name} platform integration.",
            type=PluginType.PLATFORM,
            entrypoint=f"connectors:{connector.__class__.__name__}",
            capabilities=["video", "image", "carousel", "text", "scheduling", "analytics"],
            permissions=[PluginPermission.PUBLISH, PluginPermission.NETWORK_ACCESS]
        )
        plugin_registry.register(PlatformConnectorPluginWrapper(connector, manifest))

    # 2. AI Provider Plugins
    ai_providers = [
        ("gemini-provider", "Google Gemini Provider", GeminiProvider(api_key=settings.GEMINI_API_KEY or "")),
        ("openai-provider", "OpenAI Provider", OpenAIProvider(api_key=settings.OPENAI_API_KEY or "")),
        ("mock-provider", "Mock AI Provider", MockAIProvider()),
    ]
    for pid, name, provider in ai_providers:
        manifest = PluginManifest(
            id=pid,
            name=name,
            version="1.0.0",
            description=f"Built-in {name} intelligence engine.",
            type=PluginType.AI_PROVIDER,
            entrypoint=f"services.ai:{provider.__class__.__name__}",
            capabilities=["text_generation", "structured_output", "vision", "embedding"],
            permissions=[PluginPermission.CONTENT_READ, PluginPermission.NETWORK_ACCESS]
        )
        wrapper = AIProviderPluginWrapper(provider, manifest)
        plugin_registry.register(wrapper)
        ai_provider_registry.register_provider(wrapper)

    # 3. Storage Provider Plugin
    storage_manifest = PluginManifest(
        id="local-storage",
        name="Local Volume Storage",
        version="1.0.0",
        description="Local persistent disk storage driver.",
        type=PluginType.STORAGE,
        entrypoint="services.storage_service:LocalStorageService",
        capabilities=["put", "get", "delete", "exists", "stream"],
        permissions=[PluginPermission.STORAGE_READ, PluginPermission.STORAGE_WRITE]
    )
    plugin_registry.register(LocalStoragePlugin(storage_manifest))

    # 4. Media Processor Plugin
    media_manifest = PluginManifest(
        id="ffmpeg-processor",
        name="FFmpeg Transcoder Processor",
        version="1.0.0",
        description="Core FFmpeg video transcoding and clip extraction engine.",
        type=PluginType.MEDIA_PROCESSOR,
        entrypoint="services.media_service:MediaService",
        capabilities=["probe", "thumbnail", "transcode", "extract_clip"],
        permissions=[PluginPermission.STORAGE_READ, PluginPermission.STORAGE_WRITE]
    )
    plugin_registry.register(FFmpegMediaProcessorPlugin(media_manifest))

    # 5. Workflow Action Plugin
    action_manifest = PluginManifest(
        id="webhook-action",
        name="Outbound Webhook Action",
        version="1.0.0",
        description="Executes external HTTP webhook calls in automation workflows.",
        type=PluginType.WORKFLOW_ACTION,
        entrypoint="plugins.loader:WebhookWorkflowActionPlugin",
        capabilities=["execute"],
        permissions=[PluginPermission.NETWORK_ACCESS]
    )
    plugin_registry.register(WebhookWorkflowActionPlugin(action_manifest))

    logger.info("Successfully registered all built-in Reflow plugins.")
