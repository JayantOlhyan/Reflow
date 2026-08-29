import sys
import os
import io
import json
import uuid
import asyncio
import tempfile
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.append(os.path.dirname(__file__))

from main import app
from database import init_db, async_session_factory
from models.entities import Content, Asset, Transcript, TranscriptSegment, Clip, ClipVariant, Job
from services.caption_service import caption_service, CaptionCue
from services.media_service import media_processor
from services.storage_service import storage_service

def create_sample_mp4() -> bytes:
    """Generates a 3-second real MP4 video with a test audio tone."""
    temp_in = tempfile.mktemp(suffix=".mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=3",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        temp_in
    ]
    import subprocess
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    with open(temp_in, "rb") as f:
        data = f.read()
    if os.path.exists(temp_in):
        os.remove(temp_in)
    return data

class TestCaptionEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()
        self.client = TestClient(app)

    async def test_01_caption_segmentation_and_timing(self):
        """Test 1: Verifies cue extraction, relative time shifting, and word sub-chunking."""
        segments = [
            {"start_time": 0.0, "end_time": 8.0, "text": "Welcome to the ultimate content creation guide for modern creators."},
            {"start_time": 8.0, "end_time": 16.0, "text": "Repurposing videos into short-form clips drives exponential reach across platforms."},
            {"start_time": 16.0, "end_time": 25.0, "text": "Unrelated segment after the clip."}
        ]

        # Clip from 5.0s to 12.0s (duration: 7.0s)
        cues = caption_service.generate_cues_from_segments(
            clip_start=5.0,
            clip_end=12.0,
            segments=segments,
            highlight_keywords=["repurposing", "creation", "reach"],
            max_words_per_cue=4
        )

        self.assertGreater(len(cues), 0)
        self.assertEqual(cues[0].start_time, 0.0)
        for c in cues:
            self.assertGreaterEqual(c.start_time, 0.0)
            self.assertLessEqual(c.end_time, 7.05)
            self.assertLessEqual(len(c.text.split()), 4)

        highlighted = [c for c in cues if c.highlight_words]
        self.assertGreater(len(highlighted), 0)

    async def test_02_srt_vtt_ass_formats(self):
        """Test 2: Verifies standard SRT, WebVTT, and ASS output formats."""
        cues = [
            CaptionCue(start_time=0.0, end_time=2.5, text="Create once.", highlight_words=["create"]),
            CaptionCue(start_time=2.5, end_time=5.0, text="Transform everywhere.", highlight_words=["transform"])
        ]

        # 1. SRT
        srt = caption_service.build_srt(cues)
        self.assertIn("1", srt)
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt)
        self.assertIn("Create once.", srt)

        # 2. VTT
        vtt = caption_service.build_vtt(cues)
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:00.000 --> 00:00:02.500", vtt)

        # 3. ASS
        ass_9_16 = caption_service.build_ass(cues, style_name="BOLD_PUNCH", aspect_ratio="9:16", highlight_keywords=["create", "transform"])
        self.assertIn("[Script Info]", ass_9_16)
        self.assertIn("PlayResX: 1080", ass_9_16)
        self.assertIn("PlayResY: 1920", ass_9_16)
        self.assertIn("MarginV", ass_9_16)
        self.assertIn("Dialogue:", ass_9_16)

    async def test_03_ffmpeg_caption_burn_and_ffprobe(self):
        """Test 3: Burns styled caption overlay onto a real test video and validates with FFprobe."""
        temp_dir = tempfile.mkdtemp(prefix="reflow_test_cap_")
        try:
            video_src = os.path.join(temp_dir, "test_clip_src.mp4")
            cmd_gen = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=30:duration=3",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-c:v", "libx264", "-c:a", "aac",
                video_src
            ]
            proc = await asyncio.create_subprocess_exec(*cmd_gen, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            self.assertTrue(os.path.exists(video_src))

            cues = [
                CaptionCue(start_time=0.0, end_time=1.5, text="Reflow Captions", highlight_words=["reflow"]),
                CaptionCue(start_time=1.5, end_time=3.0, text="Viral Short Form", highlight_words=["viral"])
            ]

            video_out = os.path.join(temp_dir, "test_clip_captioned.mp4")
            await media_processor.burn_captions_to_video(
                input_video_path=video_src,
                output_video_path=video_out,
                cues=cues,
                width=720,
                height=1280,
                style_name="BOLD_PUNCH",
                aspect_ratio="9:16",
                highlight_keywords=["reflow", "viral"],
                has_audio=True
            )

            self.assertTrue(os.path.exists(video_out))
            meta = await media_processor.validate_output(video_out, expected_type="video")
            self.assertEqual(meta["width"], 720)
            self.assertEqual(meta["height"], 1280)
            self.assertGreaterEqual(meta["duration"], 2.8)
            self.assertGreater(meta["file_size"], 1000)
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def test_04_full_caption_api_and_worker_pipeline(self):
        """Test 4: End-to-end test of caption persistence, background job, and clean/captioned variants."""
        content_id = f"cnt_cap_{uuid.uuid4().hex[:8]}"
        asset_id = f"ast_cap_{uuid.uuid4().hex[:8]}"
        clip_id = f"clp_cap_{uuid.uuid4().hex[:8]}"

        video_bytes = create_sample_mp4()
        storage_key = f"content/{content_id}/assets/{asset_id}/video.mp4"
        await storage_service.put(storage_key, video_bytes)

        async with async_session_factory() as session:
            content = Content(id=content_id, title="Test Video for Captions", content_type="VIDEO", status="READY")
            session.add(content)

            asset = Asset(id=asset_id, content_id=content_id, original_filename="video.mp4", storage_key=storage_key, mime_type="video/mp4", width=640, height=360, duration=3.0)
            session.add(asset)

            transcript = Transcript(id=f"tr_{content_id}", content_id=content_id, text="Short form captioning pipeline test.", duration=3.0, status="COMPLETED")
            session.add(transcript)

            seg1 = TranscriptSegment(id=f"ts1_{content_id}", transcript_id=transcript.id, sequence=1, start_time=0.0, end_time=1.5, text="Short form captioning")
            seg2 = TranscriptSegment(id=f"ts2_{content_id}", transcript_id=transcript.id, sequence=2, start_time=1.5, end_time=3.0, text="pipeline test.")
            session.add(seg1)
            session.add(seg2)

            clip = Clip(
                id=clip_id,
                content_id=content_id,
                source_asset_id=asset_id,
                title="Captions Pipeline Clip",
                start_time=0.0,
                end_time=3.0,
                duration=3.0,
                status="CANDIDATE",
                caption_style="BOLD_PUNCH",
                caption_enabled=True,
                highlight_keywords_json='["captioning", "pipeline"]'
            )
            session.add(clip)
            await session.commit()

        # 1. Test GET /api/clips/{id}/captions
        cap_res = self.client.get(f"/api/clips/{clip_id}/captions")
        self.assertEqual(cap_res.status_code, 200)
        cap_data = cap_res.json()
        self.assertEqual(cap_data["clip_id"], clip_id)
        self.assertGreater(len(cap_data["cues"]), 0)
        self.assertIn("Short", cap_data["srt_content"])

        # 2. Test PUT /api/clips/{id}/captions
        put_res = self.client.put(f"/api/clips/{clip_id}/captions", json={
            "caption_style": "KINETIC_HIGHLIGHT",
            "highlight_keywords": ["captioning", "test"]
        })
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.json()["caption_style"], "KINETIC_HIGHLIGHT")

        # 3. Test SRT / VTT endpoints
        srt_res = self.client.get(f"/api/clips/{clip_id}/captions/export.srt")
        self.assertEqual(srt_res.status_code, 200)
        self.assertIn("00:00:", srt_res.text)

        vtt_res = self.client.get(f"/api/clips/{clip_id}/captions/export.vtt")
        self.assertEqual(vtt_res.status_code, 200)
        self.assertIn("WEBVTT", vtt_res.text)

        # 4. Trigger Caption Render
        rnd_res = self.client.post(f"/api/clips/{clip_id}/render-captions", json={
            "aspect_ratios": ["9:16"],
            "caption_style": "BOLD_PUNCH"
        })
        self.assertEqual(rnd_res.status_code, 200)

        # Process media directly
        await media_processor.process_clip_media(
            clip_id=clip_id,
            aspect_ratios=["9:16"],
            include_thumbnail=True,
            burn_captions=True,
            caption_style="BOLD_PUNCH"
        )

        # Verify persisted Clip and variants
        clip_res = self.client.get(f"/api/clips/{clip_id}")
        self.assertEqual(clip_res.status_code, 200)
        clip_detail = clip_res.json()
        self.assertEqual(clip_detail["status"], "READY")

        variants = clip_detail["variants"]
        clean_vars = [v for v in variants if not v["has_captions"] and v["variant_type"] != "THUMBNAIL"]
        captioned_vars = [v for v in variants if v["has_captions"]]

        self.assertGreater(len(clean_vars), 0, "Clean variants must be preserved!")
        self.assertGreater(len(captioned_vars), 0, "Captioned variants must be generated!")
        self.assertTrue(any(v["has_captions"] and "9_16" in v["variant_type"] for v in captioned_vars))

        # Test streaming captioned variant
        cap_var = captioned_vars[0]
        stream_res = self.client.get(f"/api/clips/{clip_id}/variant/{cap_var['id']}")
        self.assertEqual(stream_res.status_code, 200)
        self.assertGreater(len(stream_res.content), 1000)

if __name__ == "__main__":
    unittest.main()
