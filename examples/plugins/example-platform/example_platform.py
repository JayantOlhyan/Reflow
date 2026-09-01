# EXAMPLE ONLY - Platform Plugin Demonstration
from plugins.contracts.platform_contract import BasePlatformConnectorPlugin
from connectors.base import PlatformCapabilities
from typing import Dict, Any, Tuple, Optional

class ExamplePlatformPlugin(BasePlatformConnectorPlugin):
    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=True,
            text_post=True,
            scheduled_publish=True,
            supports_analytics=True
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not metadata.get("title"):
            return False, "Title is required for ExamplePlatform posts."
        return True, None

    async def publish_text(self, metadata: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "external_id": "example_post_12345",
            "url": "https://example-social.com/p/12345"
        }
