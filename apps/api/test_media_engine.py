import sys
import os
import io
import json
import uuid
import asyncio
import tempfile
import unittest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.append(os.path.dirname(__file__))

from main import app
from database import init_db, async_session_factory
from models.entities import Content, Asset, ContentVariant, Job
from services.media_service import media_processor
from services.storage_service import storage_service
from services.queue_service import queue_service
from worker import process_single_job

class TestReflowMediaEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncio.run(init_db())
        cls.client = TestClient(app)
        cls.temp_dir = tempfile.mkdtemp(prefix="reflow_test_media_")

        # Generate a small, deterministic 2-second test MP4 video using ffmpeg
        cls.test_video_path = os.path.join(cls.temp_dir, "fixture_16_9.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x180:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            cls.test_video_path
        ]
        os.system(" ".join(cmd) + " > /dev/null 2>&1")

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        queue_service.clear_queue()

    def test_01_ffprobe_metadata_extraction(self):
        """Verify FFprobe extracts correct structured metadata from real video."""
        meta = asyncio.run(media_processor.probe_media(self.test_video_path))
        self.assertEqual(meta["width"], 320)
        self.assertEqual(meta["height"], 180)
        self.assertEqual(meta["duration"], 2)
        self.assertEqual(meta["fps"], 30)
        self.assertEqual(meta["codec"], "h264")
        self.assertTrue(meta["has_audio"])

    def test_02_thumbnail_generation(self):
        """Verify extracting a real JPEG thumbnail from video."""
        out_thumb = os.path.join(self.temp_dir, "thumb_test.jpg")
        asyncio.run(media_processor.generate_thumbnail(self.test_video_path, out_thumb, "00:00:01"))
        self.assertTrue(os.path.exists(out_thumb))
        self.assertGreater(os.path.getsize(out_thumb), 0)

        meta = asyncio.run(media_processor.validate_output(out_thumb, expected_type="image"))
        self.assertEqual(meta["width"], 320)
        self.assertEqual(meta["height"], 180)

    def test_03_aspect_ratio_variants_generation(self):
        """Verify generating 9:16, 1:1, 4:5, and 16:9 variants."""
        for target_fmt, (expected_w, expected_h) in [
            ("9:16", (1080, 1920)),
            ("1:1", (1080, 1080)),
            ("4:5", (1080, 1350)),
            ("16:9", (1920, 1080))
        ]:
            out_var = os.path.join(self.temp_dir, f"var_{target_fmt.replace(':', '_')}.mp4")
            asyncio.run(media_processor.generate_variant(self.test_video_path, out_var, target_fmt, has_audio=True))
            self.assertTrue(os.path.exists(out_var))
            self.assertGreater(os.path.getsize(out_var), 0)

            meta = asyncio.run(media_processor.validate_output(out_var, expected_type="video"))
            self.assertEqual(meta["width"], expected_w)
            self.assertEqual(meta["height"], expected_h)
            self.assertEqual(meta["codec"], "h264")

    def test_04_end_to_end_upload_and_worker_processing(self):
        """
        Verify real end-to-end flow:
        1. Video Upload -> returns immediately with status PROCESSING and QUEUED Job
        2. Worker processes the Job -> extracts metadata, creates thumbnail + 4 variants
        3. Content transitions to READY with 5 ContentVariant records
        """
        with open(self.test_video_path, "rb") as f:
            file_bytes = f.read()

        # 1. Upload Video
        res = self.client.post(
            "/api/content/upload",
            files={"file": ("real_demo.mp4", io.BytesIO(file_bytes), "video/mp4")},
            data={"title": "E2E Media Engine Demo"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        content_id = data["id"]
        asset_id = data["assets"][0]["id"]
        self.assertEqual(data["status"], "PROCESSING")

        # 2. Dequeue from queue & execute worker
        payload = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertIsNotNone(payload)
        self.assertEqual(payload["content_id"], content_id)
        self.assertEqual(payload["asset_id"], asset_id)

        worker_res = asyncio.run(process_single_job(payload))
        self.assertTrue(worker_res)

        # 3. Verify Content is now READY and has 5 variants
        get_res = self.client.get(f"/api/content/{content_id}")
        self.assertEqual(get_res.status_code, 200)
        content_data = get_res.json()
        self.assertEqual(content_data["status"], "READY")
        self.assertEqual(len(content_data["variants"]), 5)  # THUMBNAIL, 9:16, 1:1, 4:5, 16:9

        variant_types = [v["variant_type"] for v in content_data["variants"]]
        self.assertIn("THUMBNAIL", variant_types)
        self.assertIn("VERTICAL_9_16", variant_types)
        self.assertIn("SQUARE_1_1", variant_types)
        self.assertIn("PORTRAIT_4_5", variant_types)
        self.assertIn("LANDSCAPE_16_9", variant_types)

        # Verify physical variant files exist on disk
        for v in content_data["variants"]:
            real_p = storage_service.get_real_path(v["storage_key"])
            self.assertTrue(os.path.exists(real_p))

        # 4. Verify variant streaming
        vert_var = next(v for v in content_data["variants"] if v["variant_type"] == "VERTICAL_9_16")
        stream_res = self.client.get(f"/api/content/{content_id}/variant/{vert_var['id']}")
        self.assertEqual(stream_res.status_code, 200)
        self.assertEqual(stream_res.headers.get("content-type"), "video/mp4")
        self.assertGreater(len(stream_res.content), 0)

        # 5. Verify cascade deletion cleans up original + all variants
        del_res = self.client.delete(f"/api/content/{content_id}")
        self.assertEqual(del_res.status_code, 200)

        for v in content_data["variants"]:
            real_p = storage_service.get_real_path(v["storage_key"])
            self.assertFalse(os.path.exists(real_p))

    def test_05_idempotency_avoids_duplicate_variants(self):
        """Verify processing the same content twice does not duplicate variants."""
        with open(self.test_video_path, "rb") as f:
            file_bytes = f.read()

        res = self.client.post(
            "/api/content/upload",
            files={"file": ("idempotent_test.mp4", io.BytesIO(file_bytes), "video/mp4")},
            data={"title": "Idempotency Test"}
        )
        content_id = res.json()["id"]
        asset_id = res.json()["assets"][0]["id"]
        payload = asyncio.run(queue_service.dequeue_media_job(timeout=1))

        # Run worker 1st time
        asyncio.run(process_single_job(payload))

        # Clear downstream jobs from queue and run MEDIA_PROCESSING again
        queue_service.clear_queue()
        asyncio.run(process_single_job(payload))

        get_res = self.client.get(f"/api/content/{content_id}")
        self.assertEqual(len(get_res.json()["variants"]), 5)

        # Clean up
        self.client.delete(f"/api/content/{content_id}")

    def test_06_corrupt_video_failure_handling(self):
        """Verify corrupt media file is handled gracefully and marked FAILED without crashing."""
        corrupt_bytes = b"\x00\x00\x00\x1cftypisom" + b"GARBAGE_DATA" * 50
        res = self.client.post(
            "/api/content/upload",
            files={"file": ("corrupt.mp4", io.BytesIO(corrupt_bytes), "video/mp4")},
            data={"title": "Corrupt Media"}
        )
        content_id = res.json()["id"]
        payload = asyncio.run(queue_service.dequeue_media_job(timeout=1))

        worker_res = asyncio.run(process_single_job(payload))
        self.assertFalse(worker_res)

        # Clean up
        self.client.delete(f"/api/content/{content_id}")

if __name__ == "__main__":
    unittest.main()
