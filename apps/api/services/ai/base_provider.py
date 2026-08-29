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

    @abstractmethod
    async def plan_carousel(
        self,
        title: str,
        brief: Optional[Dict[str, Any]] = None,
        transcript_text: Optional[str] = None,
        target_slide_count: int = 5,
        template: str = "MINIMAL",
        tone: str = "informative",
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Plans a structured carousel slide deck.
        Returns:
            {
                "title": str,
                "template": str,
                "slides": [
                    {
                        "position": int,
                        "purpose": str,
                        "layout": str,
                        "headline": str,
                        "body": str,
                        "tag": str
                    }
                ]
            }
        """
        pass

    @abstractmethod
    async def discover_clips(
        self,
        title: str,
        transcript_text: str,
        segments: List[Dict[str, Any]],
        brief: Optional[Dict[str, Any]] = None,
        min_duration: float = 15.0,
        max_duration: float = 90.0,
        target_count: int = 5
    ) -> Dict[str, Any]:
        """
        Discovers high-impact short-form clip candidate intervals (15–90s)
        based on transcript segments and ContentBrief.
        Returns:
            {
                "candidates": [
                    {
                        "title": str,
                        "start_time": float,
                        "end_time": float,
                        "reason": str,
                        "hook": str,
                        "score": float,
                        "source_segment_ids": List[str]
                    }
                ]
            }
        """
        pass

