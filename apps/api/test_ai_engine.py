import sys
import os
import io
import json
import asyncio
import tempfile
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.append(os.path.dirname(__file__))

from main import app
from database import init_db, async_session_factory
from models.entities import Content, Asset, ContentVariant, Transcript, TranscriptSegment, ContentBrief, GeneratedContent, Job
from services.media_service import media_processor
from services.storage_service import storage_service
from services.queue_service import queue_service
from services.ai_service import ai_service
from services.ai.mock_provider import MockAIProvider
from worker import process_single_job

class TestReflowAIEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncio.run(init_db())
        cls.client = TestClient(app)
        cls.temp_dir = tempfile.mkdtemp(prefix="reflow_test_ai_")

        # Generate a small 2-second test MP4 video with sine audio
        cls.test_video_path = os.path.join(cls.temp_dir, "fixture_ai_16_9.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x180:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            cls.test_video_path
        ]
        os.system(" ".join(cmd) + " > /dev/null 2>&1")

        # Ensure Mock AI provider is active for deterministic testing
        ai_service.set_provider(MockAIProvider())

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_audio_extraction(self):
        """Verify extracting clean MP3 audio from source video."""
        out_audio = os.path.join(self.temp_dir, "extracted_test_audio.mp3")
        asyncio.run(media_processor.extract_audio(self.test_video_path, out_audio))
        self.assertTrue(os.path.exists(out_audio))
        self.assertGreater(os.path.getsize(out_audio), 0)

    def test_02_transcription_and_segment_persistence(self):
        """Verify transcription produces timestamped segments and persists to database."""
        out_audio = os.path.join(self.temp_dir, "extracted_test_audio.mp3")
        
        # Create dummy content
        res = self.client.post("/api/content/text", json={"title": "Transcript Test", "text": "Placeholder"})
        content_id = res.json()["id"]

        transcript = asyncio.run(ai_service.transcribe_content_audio(content_id, out_audio))
        self.assertIsNotNone(transcript.id)
        self.assertEqual(transcript.content_id, content_id)
        self.assertGreater(len(transcript.text), 10)

        # Query endpoint
        resp = self.client.get(f"/api/content/{content_id}/transcript")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data["segments"]), 1)
        self.assertIn("start_time", data["segments"][0])
        self.assertIn("end_time", data["segments"][0])

        # Cleanup
        self.client.delete(f"/api/content/{content_id}")

    def test_03_content_brief_extraction(self):
        """Verify generating and persisting a structured ContentBrief."""
        res = self.client.post("/api/content/text", json={"title": "Masterclass Architecture", "text": "In this guide we cover automated video pipelines, FFmpeg transcoding, and AI repurposing."})
        content_id = res.json()["id"]

        brief = asyncio.run(ai_service.generate_content_brief(content_id))
        self.assertIsNotNone(brief.id)
        self.assertEqual(brief.title, "Masterclass Architecture")
        self.assertGreater(len(brief.summary), 10)
        self.assertGreater(len(brief.key_points), 0)
        self.assertGreater(len(brief.hooks), 0)

        # Query endpoint
        resp = self.client.get(f"/api/content/{content_id}/brief")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["title"], "Masterclass Architecture")
        self.assertIsInstance(data["topics"], list)
        self.assertIsInstance(data["key_points"], list)

        # Cleanup
        self.client.delete(f"/api/content/{content_id}")

    def test_04_platform_specific_generators(self):
        """Verify LinkedIn, Instagram, X (with thread support), and YouTube platform generators."""
        res = self.client.post("/api/content/text", json={"title": "Building Reflow in Public", "text": "How we built an open source AI content operating system."})
        content_id = res.json()["id"]

        # Generate all 4 platforms
        items = asyncio.run(ai_service.generate_platform_content(
            content_id=content_id,
            platforms=["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"]
        ))
        self.assertEqual(len(items), 4)

        # Query endpoint
        resp = self.client.get(f"/api/content/{content_id}/generated")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 4)

        platforms = [g["platform"] for g in data]
        self.assertIn("LINKEDIN", platforms)
        self.assertIn("INSTAGRAM", platforms)
        self.assertIn("X", platforms)
        self.assertIn("YOUTUBE", platforms)

        # Verify X thread structure
        x_item = next(g for g in data if g["platform"] == "X")
        self.assertEqual(x_item["generation_type"], "THREAD")
        self.assertGreater(len(x_item["payload"]["posts"]), 1)

        # Verify YouTube chapters
        yt_item = next(g for g in data if g["platform"] == "YOUTUBE")
        self.assertIn("chapters", yt_item["payload"])
        self.assertGreater(len(yt_item["payload"]["chapters"]), 0)

        # Cleanup
        self.client.delete(f"/api/content/{content_id}")

    def test_05_end_to_end_worker_ai_pipeline(self):
        """
        Verify the full async dependency-ordered worker pipeline:
        1. Video Upload -> MEDIA_PROCESSING job
        2. Worker processes media -> auto-enqueues TRANSCRIPTION job
        3. Worker transcribes audio -> auto-enqueues CONTENT_ANALYSIS job
        4. Worker analyzes brief -> auto-enqueues CONTENT_GENERATION job
        5. Worker generates platform outputs
        6. Verify all relational records exist and are queryable.
        """
        with open(self.test_video_path, "rb") as f:
            v_bytes = f.read()

        upload_res = self.client.post(
            "/api/content/upload",
            files={"file": ("pipeline_demo.mp4", io.BytesIO(v_bytes), "video/mp4")},
            data={"title": "Full AI Pipeline Demo"}
        )
        self.assertEqual(upload_res.status_code, 200)
        content_id = upload_res.json()["id"]

        # Step 1: Process MEDIA_PROCESSING job
        payload1 = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertEqual(payload1["job_type"], "MEDIA_PROCESSING")
        self.assertTrue(asyncio.run(process_single_job(payload1)))

        # Step 2: Process TRANSCRIPTION job
        payload2 = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertEqual(payload2["job_type"], "TRANSCRIPTION")
        self.assertTrue(asyncio.run(process_single_job(payload2)))

        # Step 3: Process CONTENT_ANALYSIS job
        payload3 = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertEqual(payload3["job_type"], "CONTENT_ANALYSIS")
        self.assertTrue(asyncio.run(process_single_job(payload3)))

        # Step 4: Process CONTENT_GENERATION job
        payload4 = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertEqual(payload4["job_type"], "CONTENT_GENERATION")
        self.assertTrue(asyncio.run(process_single_job(payload4)))

        # Verify Content has all 5 variants + transcript + brief + 4 generated contents
        get_res = self.client.get(f"/api/content/{content_id}")
        self.assertEqual(get_res.status_code, 200)
        content_data = get_res.json()
        self.assertEqual(len(content_data["variants"]), 5)
        self.assertEqual(len(content_data["transcripts"]), 1)
        self.assertEqual(len(content_data["briefs"]), 1)
        self.assertEqual(len(content_data["generated_contents"]), 4)

        # Verify single platform regeneration
        regen_res = self.client.post(f"/api/content/{content_id}/regenerate/LINKEDIN?tone=bold")
        self.assertEqual(regen_res.status_code, 200)

        # Cleanup
        del_res = self.client.delete(f"/api/content/{content_id}")
        self.assertEqual(del_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
