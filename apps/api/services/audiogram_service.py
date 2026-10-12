import os
import uuid
import asyncio
import subprocess
from typing import Dict, Any, Optional
from config import settings
from utils.logging import get_logger
from services.storage_service import storage_service

logger = get_logger("AudiogramService")

class AudiogramService:
    """
    Synthesizes video audiograms from audio tracks using local FFmpeg.
    Generates dynamic audio waveforms (sound waves), background canvases,
    progress bars, and captions.
    """

    ASPECT_RATIO_DIMENSIONS = {
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "16:9": (1920, 1080),
        "4:5": (1080, 1350)
    }

    async def generate_audiogram(
        self,
        audio_file_path: str,
        output_storage_key: str,
        aspect_ratio: str = "9:16",
        waveform_style: str = "BARS",
        waveform_color: str = "#6366F1",
        background_color: str = "#0F172A",
        background_image_path: Optional[str] = None,
        duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes an MP4 audiogram from an audio file using FFmpeg filtergraphs.
        """
        width, height = self.ASPECT_RATIO_DIMENSIONS.get(aspect_ratio, (1080, 1920))
        output_full_path = storage_service.get_full_path(output_storage_key)
        os.makedirs(os.path.dirname(output_full_path), exist_ok=True)

        # Convert hex color (#RRGGBB) to 0xRRGGBB for FFmpeg
        clean_color = waveform_color.lstrip("#")
        ffmpeg_color = f"0x{clean_color}"

        # Position waveform in lower-middle section
        wave_width = int(width * 0.85)
        wave_height = int(height * 0.15)
        pos_x = int((width - wave_width) / 2)
        pos_y = int(height * 0.65)

        # Choose filter mode: line or p2p
        wave_mode = "line" if waveform_style.upper() in ("LINE", "WAVE") else "p2p"

        # Construct FFmpeg command
        filter_spec = (
            f"[1:a]showwaves=s={wave_width}x{wave_height}:mode={wave_mode}:colors={ffmpeg_color}[wave];"
        )
        if background_image_path and os.path.exists(background_image_path):
            cmd = [
                settings.FFMPEG_PATH,
                "-y",
                "-loop", "1",
                "-i", background_image_path,
                "-i", audio_file_path,
                "-filter_complex",
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}[bg];"
                f"{filter_spec}[bg][wave]overlay={pos_x}:{pos_y}:shortest=1[v]",
                "-map", "[v]",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-threads", str(settings.FFMPEG_THREADS),
            ]
        else:
            hex_bg = background_color.lstrip("#")
            cmd = [
                settings.FFMPEG_PATH,
                "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x{hex_bg}:s={width}x{height}",
                "-i", audio_file_path,
                "-filter_complex",
                f"{filter_spec}[0:v][wave]overlay={pos_x}:{pos_y}:shortest=1[v]",
                "-map", "[v]",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-threads", str(settings.FFMPEG_THREADS),
            ]

        if duration:
            cmd.extend(["-t", str(duration)])

        cmd.append(output_full_path)

        logger.info(f"Rendering audiogram ({aspect_ratio}, {waveform_style}) -> {output_storage_key}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.FFMPEG_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Audiogram render timed out after {settings.FFMPEG_TIMEOUT_SECONDS}s.")

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="ignore")
            logger.error(f"FFmpeg audiogram error: {error_msg}")
            raise RuntimeError(f"FFmpeg failed with exit code {process.returncode}: {error_msg[-400:]}")

        file_size = os.path.getsize(output_full_path)
        logger.info(f"Successfully generated audiogram: {output_full_path} ({file_size} bytes)")

        return {
            "storage_key": output_storage_key,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "waveform_style": waveform_style,
            "file_size": file_size
        }

audiogram_service = AudiogramService()
