from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseAIProvider(ABC):
    provider_name: str = "base"
    model_name: str = "base-model"

    @abstractmethod
    async def transcribe(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribes audio file.
        Returns:
            {
                "text": str,
                "language": str,
                "duration": float,
                "segments": [
                    {"sequence": int, "start_time": float, "end_time": float, "text": str}
                ]
            }
        """
        pass

    @abstractmethod
    async def analyze_content(
        self,
        title: str,
        transcript_text: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes source transcript and returns structured ContentBrief dictionary.
        """
        pass

    @abstractmethod
    async def generate_platform(
        self,
        platform: str,
        brief: Dict[str, Any],
        segments: Optional[List[Dict[str, Any]]] = None,
        tone: str = "professional",
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates platform-specific structured output (LinkedIn, Instagram, X, YouTube).
        """
        pass
