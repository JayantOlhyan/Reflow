from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class PlatformCapabilities:
    video_upload: bool = False
    image_upload: bool = False
    carousel_upload: bool = False
    text_post: bool = False
    scheduled_publish: bool = False
    supported_aspect_ratios: List[str] = field(default_factory=lambda: ["16:9", "9:16", "1:1", "4:5"])
    supported_containers: List[str] = field(default_factory=lambda: ["mp4", "mov"])
    max_video_size_mb: int = 500
    max_title_length: int = 100
    max_description_length: int = 5000
    max_images_per_carousel: int = 10

class BaseOAuthProvider(ABC):
    """Abstract base class for OAuth 2.0 account authentication."""
    platform_id: str

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Constructs and returns the OAuth consent screen URL."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchanges an authorization code for access and refresh tokens."""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes an expired access token."""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revokes credentials on the external platform."""
        pass

    @abstractmethod
    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """Fetches account identity, channel/handle name, and avatar URL."""
        pass

class BasePlatformConnector(ABC):
    """Abstract base class for social media publishing connectors."""
    platform_id: str
    platform_name: str

    @abstractmethod
    def get_capabilities(self) -> PlatformCapabilities:
        """Returns the declared platform capabilities."""
        pass

    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Pre-validates title, description, tags, and parameters."""
        pass

    async def publish_video(
        self,
        video_path: str,
        metadata: Dict[str, Any],
        access_token: str,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Publishes a real video file to the platform and returns external IDs."""
        return not_implemented_response(self.platform_id, "video_upload")

    async def publish_image(
        self,
        image_path: str,
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a single image post to the platform."""
        return not_implemented_response(self.platform_id, "image_upload")

    async def publish_carousel(
        self,
        image_paths: List[str],
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a multi-image carousel post to the platform."""
        return not_implemented_response(self.platform_id, "carousel_upload")

    async def publish_text(
        self,
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a text/status post to the platform."""
        return not_implemented_response(self.platform_id, "text_post")

def not_implemented_response(platform: str, operation: str) -> Dict[str, Any]:
    return {
        "status": "not_implemented",
        "platform": platform,
        "operation": operation,
        "message": f"Real {platform} {operation} integration is not implemented yet. Scheduled for future phase."
    }
