from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from plugins.base_plugin import BasePlugin
from plugins.manifest import PluginManifest

class BaseMediaProcessorPlugin(BasePlugin, ABC):
    """
    Plugin contract interface for Media Processors (FFmpeg, CloudTranscoder).
    """
    def __init__(self, manifest: PluginManifest, config: Optional[Dict[str, Any]] = None):
        super().__init__(manifest, config)

    async def initialize(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "processor": self.manifest.id}

    @abstractmethod
    async def probe(self, file_path: str) -> Dict[str, Any]:
        """Probes media metadata (duration, width, height, codec, fps)."""
        pass

    @abstractmethod
    async def generate_thumbnail(self, input_path: str, output_path: str, timestamp_seconds: float = 1.0) -> str:
        """Generates thumbnail image from video file."""
        pass

    @abstractmethod
    async def transcode(self, input_path: str, output_path: str, target_aspect_ratio: str) -> str:
        """Transcodes video into specified aspect ratio (9:16, 1:1, 4:5, 16:9)."""
        pass

    @abstractmethod
    async def extract_clip(self, input_path: str, output_path: str, start_seconds: float, end_seconds: float) -> str:
        """Extracts sub-clip segment from video."""
        pass

    @abstractmethod
    def validate_media_file(self, file_path: str) -> bool:
        """Validates media integrity."""
        pass
