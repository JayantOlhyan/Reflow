from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BasePlatformConnector(ABC):
    platform_id: str
    platform_name: str
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Returns the list of supported capabilities for this platform."""
        pass

    @abstractmethod
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validates that OAuth tokens or API keys are valid."""
        pass

    @abstractmethod
    async def publish(self, media_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Publishes content to the platform and returns platform post ID."""
        pass

    @abstractmethod
    async def schedule(self, media_path: str, metadata: Dict[str, Any], scheduled_time: str) -> Dict[str, Any]:
        """Schedules content on the platform API."""
        pass
