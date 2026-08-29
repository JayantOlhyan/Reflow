from typing import Dict, Any, List
from connectors.base import BasePlatformConnector, not_implemented_response

class InstagramConnector(BasePlatformConnector):
    platform_id = "instagram"
    platform_name = "Instagram"

    def get_capabilities(self) -> List[str]:
        return ["video", "reels", "image", "carousel", "caption", "scheduling"]

    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        return False

    async def publish(self, media_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return not_implemented_response(self.platform_id, "publish")

    async def schedule(self, media_path: str, metadata: Dict[str, Any], scheduled_time: str) -> Dict[str, Any]:
        return not_implemented_response(self.platform_id, "schedule")
