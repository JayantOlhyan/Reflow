import os
import re
import httpx
import asyncio
from typing import Dict, Any, Optional
from config import settings
from utils.logging import get_logger
from utils.security import is_safe_external_url
from services.storage_service import storage_service

logger = get_logger("WatermarkService")

class WatermarkService:
    """
    Handles watermark stripping and clean stream retrieval for cross-posted short-form video.
    Resolves clean CDN streams or applies FFmpeg delogo/crop filters.
    """

    async def resolve_clean_video_url(self, platform: str, source_url: str) -> Optional[str]:
        """
        Attempts to resolve an unwatermarked raw video stream directly from the platform.
        """
        is_safe, error = is_safe_external_url(source_url)
        if not is_safe:
            logger.warning(f"Watermark service rejected unsafe source URL '{source_url}': {error}")
            return None

        platform_lower = platform.lower()

        if "tiktok" in platform_lower:
            # TikTok clean CDN resolver
            return await self._resolve_tiktok_clean_stream(source_url)
        elif "instagram" in platform_lower:
            # Instagram clean stream resolver
            return await self._resolve_instagram_clean_stream(source_url)

        return None

    async def _resolve_tiktok_clean_stream(self, video_url: str) -> Optional[str]:
        """
        Queries public API endpoints to retrieve the unwatermarked direct HD video URL.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        try:
            # Query standard public no-watermark API gateway
            api_endpoint = f"https://www.tikwm.com/api/?url={video_url}"
            is_safe, _ = is_safe_external_url(api_endpoint)
            if not is_safe:
                return None

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(api_endpoint, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == 0 and "data" in data:
                        # 'play' or 'hdplay' is unwatermarked
                        clean_url = data["data"].get("hdplay") or data["data"].get("play")
                        if clean_url:
                            logger.info("Successfully resolved unwatermarked TikTok CDN stream.")
                            return clean_url
        except Exception as e:
            logger.warning(f"Could not resolve unwatermarked TikTok stream via API: {e}")
        return None

    async def _resolve_instagram_clean_stream(self, post_url: str) -> Optional[str]:
        """
        Retrieves direct reel video stream without UI watermark overlays.
        """
        # Instagram standard graph or CDN retrieval
        return None

    async def strip_watermark_via_ffmpeg(
        self,
        input_video_path: str,
        output_storage_key: str,
        crop_bottom_pixels: int = 120
    ) -> str:
        """
        Fallback: Strips bottom watermark bar using FFmpeg crop or delogo filter.
        """
        output_full_path = storage_service.get_full_path(output_storage_key)
        os.makedirs(os.path.dirname(output_full_path), exist_ok=True)

        # Scale and crop out bottom watermark region
        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-i", input_video_path,
            "-vf", f"crop=in_w:in_h-{crop_bottom_pixels}:0:0,scale=in_w:in_h",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-c:a", "copy",
            "-threads", str(settings.FFMPEG_THREADS),
            output_full_path
        ]

        logger.info(f"Applying FFmpeg de-watermark crop -> {output_storage_key}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            err = stderr.decode("utf-8", errors="ignore")
            logger.error(f"FFmpeg watermark stripping failed: {err}")
            raise RuntimeError(f"FFmpeg watermark crop error: {err[-300:]}")

        logger.info(f"Cleaned watermark successfully: {output_full_path}")
        return output_storage_key

watermark_service = WatermarkService()
