from typing import Dict, Any, List
from connectors.base import BasePlatformConnector

class InstagramConnector(BasePlatformConnector):
    platform_id = "instagram"
    platform_name = "Instagram"

    def get_capabilities(self) -> List[str]:
        return ["video", "reels", "image", "carousel", "caption", "scheduling"]

    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        return True

    async def publish(self, media_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "published", "platform": "instagram", "post_id": "ig_sample_456"}

    async def schedule(self, media_path: str, metadata: Dict[str, Any], scheduled_time: str) -> Dict[str, Any]:
        return {"status": "scheduled", "platform": "instagram", "scheduled_time": scheduled_time}
