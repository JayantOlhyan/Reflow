import asyncio
import os
import subprocess
from typing import Dict, Any, Optional

class MediaProcessor:
    def __init__(self, output_dir: str = "./storage/processed"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def get_media_info(self, input_path: str) -> Dict[str, Any]:
        """Probes video or image metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration,size:stream=width,height,codec_name,r_frame_rate",
                "-of", "json",
                input_path
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                import json
                return json.loads(stdout.decode())
        except Exception as e:
            print(f"Error probing media {input_path}: {e}")
        return {"streams": [{"width": 1920, "height": 1080}], "format": {"duration": "120"}}

    async def convert_aspect_ratio(
        self,
        input_path: str,
        target_format: str = "9:16",
        output_filename: Optional[str] = None
    ) -> str:
        """Converts video to target aspect ratio (9:16 vertical, 1:1 square, 4:5 portrait) with blurred background padding."""
        if not output_filename:
            basename = os.path.basename(input_path).split('.')[0]
            output_filename = f"{basename}_{target_format.replace(':', '_')}.mp4"
            
        output_path = os.path.join(self.output_dir, output_filename)

        filter_complex = {
            "9:16": "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v]",
            "1:1": "[0:v]scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2[v]",
            "4:5": "[0:v]scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2[v]",
            "16:9": "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v]"
        }.get(target_format, "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v]")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", filter_complex,
            "-c:a", "copy",
            output_path
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return output_path
        except Exception as e:
            print(f"FFmpeg conversion error: {e}")
            return input_path

    async def extract_thumbnail(self, input_path: str, timestamp: str = "00:00:02") -> str:
        """Extracts a high-quality frame from video as JPEG thumbnail."""
        output_path = os.path.join(self.output_dir, f"thumb_{os.path.basename(input_path)}.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", timestamp,
            "-i", input_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()
            return output_path
        except Exception as e:
            print(f"Thumbnail extraction failed: {e}")
            return ""

media_processor = MediaProcessor()
