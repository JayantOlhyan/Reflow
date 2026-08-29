from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BasePlatformConnector(ABC):
    platform_id: str
    platform_name: str
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Returns list of supported capabilities for this platform."""
        pass

    @abstractmethod
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validates OAuth tokens or API keys."""
        pass

    @abstractmethod
    async def publish(self, media_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Publishes content to the platform."""
        pass

    @abstractmethod
    async def schedule(self, media_path: str, metadata: Dict[str, Any], scheduled_time: str) -> Dict[str, Any]:
        """Schedules content on the platform."""
        pass

def not_implemented_response(platform: str, operation: str) -> Dict[str, Any]:
    return {
        "status": "not_implemented",
        "platform": platform,
        "operation": operation,
        "message": f"Real {platform} {operation} integration is not implemented yet."
    }
