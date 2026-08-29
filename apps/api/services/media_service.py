import asyncio
import os
import json
import uuid
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy import select, update
from config import settings
from database import async_session_factory
from models.entities import Content, Asset, ContentVariant, Carousel, CarouselSlide, Clip, ClipVariant, Job
from services.storage_service import storage_service
from utils.logging import get_logger

logger = get_logger("MediaService")

class MediaService:
    def __init__(self):
        self.ffmpeg_path = settings.FFMPEG_PATH
        self.ffprobe_path = settings.FFPROBE_PATH

    async def probe_media(self, file_path: str) -> Dict[str, Any]:
        """Probes video or image metadata using ffprobe safely."""
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=width,height,codec_name,codec_type,r_frame_rate,bit_rate",
            "-of", "json",
            file_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode().strip()
            raise ValueError(f"FFprobe failed to inspect media: {err_msg}")

        data = json.loads(stdout.decode())
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        width = int(video_stream["width"]) if video_stream and "width" in video_stream else None
        height = int(video_stream["height"]) if video_stream and "height" in video_stream else None
        duration = int(float(fmt.get("duration", 0))) if fmt.get("duration") else None
        bitrate = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None
        vcodec = video_stream.get("codec_name") if video_stream else None
        acodec = audio_stream.get("codec_name") if audio_stream else None

        fps = None
        if video_stream and "r_frame_rate" in video_stream:
            try:
                num, den = video_stream["r_frame_rate"].split("/")
                fps = round(float(num) / float(den)) if float(den) > 0 else None
            except Exception:
                fps = None

        return {
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "codec": vcodec,
            "audio_codec": acodec,
            "has_audio": audio_stream is not None,
            "bitrate": bitrate,
            "file_size": int(fmt.get("size", 0)) if fmt.get("size") else None
        }

    async def extract_audio(self, input_path: str, output_path: str) -> str:
        """
        Extracts clean audio as 16kHz mono MP3 for speech-to-text transcription.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            output_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ValueError(f"Audio extraction failed: {stderr.decode().strip()}")
        return output_path

    async def generate_thumbnail(self, input_path: str, output_path: str, timestamp: str = "00:00:01") -> str:
        """Extracts a high quality frame from the video as a JPEG thumbnail."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = [
            self.ffmpeg_path, "-y",
            "-ss", timestamp,
            "-i", input_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ValueError(f"Thumbnail extraction failed: {stderr.decode().strip()}")
        return output_path

    async def generate_variant(
        self,
        input_path: str,
        output_path: str,
        target_format: str,
        has_audio: bool = True
    ) -> str:
        """
        Transcodes video into target aspect ratio (16:9, 9:16, 1:1, 4:5)
        using deterministic scaling/padding with black bars, H.264 video, and AAC audio.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        filter_complex = {
            "9:16": "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            "1:1": "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=black",
            "4:5": "scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2:color=black",
            "16:9": "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
        }.get(target_format, "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black")

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-vf", filter_complex,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "22",
            "-movflags", "+faststart"
        ]

        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.append("-an")

        cmd.append(output_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ValueError(f"FFmpeg variant generation for {target_format} failed: {stderr.decode().strip()}")
        return output_path

    async def validate_output(self, output_path: str, expected_type: str = "video") -> Dict[str, Any]:
        """Validates that output exists, has size > 0, and is readable by FFprobe."""
        if not os.path.exists(output_path):
            raise ValueError(f"Output file {output_path} does not exist.")
        size = os.path.getsize(output_path)
        if size == 0:
            raise ValueError(f"Output file {output_path} is empty (0 bytes).")
        
        meta = await self.probe_media(output_path)
        if expected_type == "video" and not meta.get("width"):
            raise ValueError(f"Output file {output_path} is not a valid video.")
        return meta

    async def process_content_media(self, content_id: str, asset_id: str) -> None:
        """
        Orchestrates full media processing for a video content asset:
        1. Probes original asset metadata
        2. Generates thumbnail
        3. Generates 9:16, 1:1, 4:5, 16:9 variants atomically
        4. Persists ContentVariant records in DB
        5. Updates Content status to READY
        """
        logger.info(f"Starting media processing for Content: {content_id}, Asset: {asset_id}")

        async with async_session_factory() as session:
            # 1. Fetch Content & Asset records
            content_res = await session.execute(select(Content).where(Content.id == content_id))
            content = content_res.scalar_one_or_none()
            asset_res = await session.execute(select(Asset).where(Asset.id == asset_id, Asset.content_id == content_id))
            asset = asset_res.scalar_one_or_none()

            if not content or not asset:
                raise ValueError(f"Content {content_id} or Asset {asset_id} not found in database.")

            original_path = storage_service.get_real_path(asset.storage_key)
            if not os.path.exists(original_path):
                raise ValueError(f"Original media file missing from storage: {asset.storage_key}")

            # 2. Extract and update metadata
            meta = await self.probe_media(original_path)
            asset.width = meta["width"]
            asset.height = meta["height"]
            asset.duration = meta["duration"]
            asset.fps = meta["fps"]
            asset.codec = meta["codec"]
            asset.bitrate = meta["bitrate"]

            has_audio = meta.get("has_audio", True)
            logger.info(f"Probed original media {asset.original_filename}: {meta['width']}x{meta['height']}, {meta['duration']}s, {meta['fps']}fps, codec: {meta['codec']}")

            # Check existing variants for idempotency
            existing_vars_res = await session.execute(select(ContentVariant).where(ContentVariant.content_id == content_id))
            existing_variants = {v.variant_type: v for v in existing_vars_res.scalars().all()}

            temp_dir = tempfile.mkdtemp(prefix=f"reflow_proc_{content_id}_")
            try:
                # 3. Generate Thumbnail
                if "THUMBNAIL" not in existing_variants:
                    thumb_temp = os.path.join(temp_dir, "thumb.jpg")
                    await self.generate_thumbnail(original_path, thumb_temp, timestamp="00:00:01")
                    thumb_meta = await self.validate_output(thumb_temp, expected_type="image")
                    
                    thumb_var_id = f"var_thumb_{uuid.uuid4().hex[:8]}"
                    thumb_key = f"content/{content_id}/variants/{thumb_var_id}.jpg"
                    
                    with open(thumb_temp, "rb") as f:
                        await storage_service.put(thumb_key, f.read())

                    thumb_variant = ContentVariant(
                        id=thumb_var_id,
                        content_id=content_id,
                        source_asset_id=asset_id,
                        variant_type="THUMBNAIL",
                        storage_key=thumb_key,
                        mime_type="image/jpeg",
                        file_size=thumb_meta.get("file_size") or os.path.getsize(thumb_temp),
                        width=thumb_meta.get("width"),
                        height=thumb_meta.get("height"),
                        status="READY"
                    )
                    session.add(thumb_variant)
                    content.thumbnail_path = thumb_key
                    logger.info(f"Generated Thumbnail: {thumb_key}")

                # 4. Generate Target Formats (9:16, 1:1, 4:5, 16:9)
                target_formats = [
                    ("VERTICAL_9_16", "9:16"),
                    ("SQUARE_1_1", "1:1"),
                    ("PORTRAIT_4_5", "4:5"),
                    ("LANDSCAPE_16_9", "16:9")
                ]

                for var_type, fmt_ratio in target_formats:
                    if var_type in existing_variants:
                        logger.info(f"Variant {var_type} already exists for content {content_id}, skipping.")
                        continue

                    var_temp = os.path.join(temp_dir, f"var_{fmt_ratio.replace(':', '_')}.mp4")
                    await self.generate_variant(original_path, var_temp, fmt_ratio, has_audio=has_audio)
                    var_meta = await self.validate_output(var_temp, expected_type="video")

                    var_id = f"var_{uuid.uuid4().hex[:8]}"
                    var_key = f"content/{content_id}/variants/{fmt_ratio.replace(':', '_')}_{var_id}.mp4"

                    with open(var_temp, "rb") as f:
                        await storage_service.put(var_key, f.read())

                    variant = ContentVariant(
                        id=var_id,
                        content_id=content_id,
                        source_asset_id=asset_id,
                        variant_type=var_type,
                        storage_key=var_key,
                        mime_type="video/mp4",
                        file_size=var_meta.get("file_size") or os.path.getsize(var_temp),
                        width=var_meta.get("width"),
                        height=var_meta.get("height"),
                        duration=var_meta.get("duration"),
                        fps=var_meta.get("fps"),
                        codec=var_meta.get("codec"),
                        status="READY"
                    )
                    session.add(variant)
                    logger.info(f"Generated Variant {var_type} ({fmt_ratio}): {var_key} ({var_meta.get('width')}x{var_meta.get('height')})")

                content.status = "READY"
                await session.commit()
                logger.info(f"All media variants generated successfully for Content {content_id}.")
            finally:
                # Cleanup temp directory
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    async def extract_clip(
        self,
        source_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
        has_audio: bool = True
    ) -> str:
        """
        Extracts a sub-clip from source video from start_time to end_time
        using frame-accurate seeking and clean timestamps.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        duration = max(0.1, end_time - start_time)
        cmd = [
            self.ffmpeg_path, "-y",
            "-ss", f"{start_time:.3f}",
            "-to", f"{end_time:.3f}",
            "-i", source_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "20",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart"
        ]
        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.append("-an")

        cmd.append(output_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ValueError(f"FFmpeg clip extraction failed: {stderr.decode().strip()}")
        return output_path

    async def process_clip_media(
        self,
        clip_id: str,
        aspect_ratios: Optional[List[str]] = None,
        include_thumbnail: bool = True
    ) -> None:
        """
        Extracts master video clip and generates requested aspect ratio variants atomically:
        1. Validates clip and source asset
        2. Cuts master.mp4 via FFmpeg extract_clip
        3. Probes master.mp4 via FFprobe
        4. Generates thumbnail
        5. Generates requested variants (9:16, 1:1, 4:5, 16:9)
        6. Persists ClipVariant records and marks Clip READY
        """
        if aspect_ratios is None:
            aspect_ratios = ["9:16"]

        logger.info(f"Starting media processing for Clip {clip_id} (Ratios: {aspect_ratios})")

        async with async_session_factory() as session:
            clip_res = await session.execute(select(Clip).where(Clip.id == clip_id))
            clip = clip_res.scalar_one_or_none()
            if not clip:
                raise ValueError(f"Clip {clip_id} not found in database.")

            clip.status = "PROCESSING"
            await session.commit()

            content_res = await session.execute(select(Content).where(Content.id == clip.content_id))
            content = content_res.scalar_one_or_none()
            if not content or not content.assets:
                clip.status = "FAILED"
                await session.commit()
                raise ValueError(f"Content {clip.content_id} or source asset not found for Clip {clip_id}.")

            primary_asset = content.assets[0]
            original_path = storage_service.get_real_path(primary_asset.storage_key)
            if not os.path.exists(original_path):
                clip.status = "FAILED"
                await session.commit()
                raise ValueError(f"Original media file missing from storage: {primary_asset.storage_key}")

            source_meta = await self.probe_media(original_path)
            has_audio = source_meta.get("has_audio", True)

            temp_dir = tempfile.mkdtemp(prefix=f"reflow_clip_{clip_id}_")
            try:
                # 1. Extract Master Clip
                master_temp = os.path.join(temp_dir, "master.mp4")
                await self.extract_clip(
                    source_path=original_path,
                    start_time=clip.start_time,
                    end_time=clip.end_time,
                    output_path=master_temp,
                    has_audio=has_audio
                )
                master_meta = await self.validate_output(master_temp, expected_type="video")

                master_var_id = f"clv_master_{uuid.uuid4().hex[:8]}"
                master_key = f"content/{clip.content_id}/clips/{clip_id}/master.mp4"

                with open(master_temp, "rb") as f:
                    await storage_service.put(master_key, f.read())

                master_variant = ClipVariant(
                    id=master_var_id,
                    clip_id=clip_id,
                    variant_type="MASTER",
                    aspect_ratio="16:9",
                    storage_key=master_key,
                    mime_type="video/mp4",
                    width=master_meta.get("width"),
                    height=master_meta.get("height"),
                    duration=master_meta.get("duration") or clip.duration,
                    file_size=master_meta.get("file_size") or os.path.getsize(master_temp),
                    status="READY"
                )
                session.add(master_variant)

                # 2. Thumbnail
                if include_thumbnail:
                    thumb_temp = os.path.join(temp_dir, "thumb.jpg")
                    await self.generate_thumbnail(master_temp, thumb_temp, timestamp="00:00:00.500")
                    thumb_meta = await self.validate_output(thumb_temp, expected_type="image")

                    thumb_var_id = f"clv_thumb_{uuid.uuid4().hex[:8]}"
                    thumb_key = f"content/{clip.content_id}/clips/{clip_id}/thumbnail.jpg"

                    with open(thumb_temp, "rb") as f:
                        await storage_service.put(thumb_key, f.read())

                    thumb_variant = ClipVariant(
                        id=thumb_var_id,
                        clip_id=clip_id,
                        variant_type="THUMBNAIL",
                        aspect_ratio="1:1",
                        storage_key=thumb_key,
                        mime_type="image/jpeg",
                        width=thumb_meta.get("width"),
                        height=thumb_meta.get("height"),
                        file_size=thumb_meta.get("file_size") or os.path.getsize(thumb_temp),
                        status="READY"
                    )
                    session.add(thumb_variant)
                    clip.thumbnail_path = thumb_key

                # 3. Target Aspect Ratios
                ratio_map = {
                    "9:16": "VERTICAL_9_16",
                    "1:1": "SQUARE_1_1",
                    "4:5": "PORTRAIT_4_5",
                    "16:9": "LANDSCAPE_16_9"
                }

                for ratio in aspect_ratios:
                    var_type = ratio_map.get(ratio, f"VARIANT_{ratio.replace(':', '_')}")
                    ratio_clean = ratio.replace(":", "x")
                    var_temp = os.path.join(temp_dir, f"{ratio_clean}.mp4")

                    await self.generate_variant(master_temp, var_temp, target_format=ratio, has_audio=has_audio)
                    var_meta = await self.validate_output(var_temp, expected_type="video")

                    var_id = f"clv_{ratio_clean}_{uuid.uuid4().hex[:8]}"
                    var_key = f"content/{clip.content_id}/clips/{clip_id}/variants/{ratio_clean}.mp4"

                    with open(var_temp, "rb") as f:
                        await storage_service.put(var_key, f.read())

                    variant = ClipVariant(
                        id=var_id,
                        clip_id=clip_id,
                        variant_type=var_type,
                        aspect_ratio=ratio,
                        storage_key=var_key,
                        mime_type="video/mp4",
                        width=var_meta.get("width"),
                        height=var_meta.get("height"),
                        duration=var_meta.get("duration") or clip.duration,
                        file_size=var_meta.get("file_size") or os.path.getsize(var_temp),
                        status="READY"
                    )
                    session.add(variant)
                    logger.info(f"Generated Clip Variant {ratio} -> {var_key}")

                clip.status = "READY"
                clip.updated_at = datetime.utcnow()
                await session.commit()
                logger.info(f"Clip {clip_id} processing completed successfully.")
            except Exception as e:
                clip.status = "FAILED"
                await session.commit()
                logger.error(f"Clip {clip_id} processing failed: {e}")
                raise
            finally:
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

media_processor = MediaService()
