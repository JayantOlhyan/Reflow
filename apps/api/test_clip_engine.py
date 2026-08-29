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
from models.entities import Content, Asset, Transcript, TranscriptSegment, ContentBrief, Clip, ClipVariant, Job
from services.storage_service import storage_service
from services.queue_service import queue_service
from services.ai_service import ai_service
from services.ai.mock_provider import MockAIProvider
from services.media_service import media_processor
from worker import process_single_job

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

class TestReflowClipEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncio.run(init_db())
        cls.client = TestClient(app)
        ai_service.set_provider(MockAIProvider())

    def setUp(self):
        queue_service.clear_queue()

    def test_01_clip_and_variant_crud(self):
        """Verify Clip creation, timestamp updating, and cascading variant deletion."""
        # 1. Create text source content for parent relation
        cnt_res = self.client.post("/api/content/text", json={
            "title": "Clip Model Verification Content",
            "text": "Source context for clip models."
        })
        self.assertEqual(cnt_res.status_code, 200)
        content_id = cnt_res.json()["id"]

        # 2. Add Clip manually via async DB session
        async def _insert_clip():
            async with async_session_factory() as session:
                c = Clip(
                    id="clp_test_crud_01",
                    content_id=content_id,
                    title="Essential Distributed Systems Lesson",
                    hook="Stop designing monolithic bottlenecks.",
                    start_time=10.0,
                    end_time=45.0,
                    duration=35.0,
                    status="CANDIDATE",
                    score=92.5,
                    reason="Clear technical thesis with concise hook."
                )
                session.add(c)
                await session.commit()

        asyncio.run(_insert_clip())

        # 3. Fetch Clip via API
        get_res = self.client.get("/api/clips/clp_test_crud_01")
        self.assertEqual(get_res.status_code, 200)
        clip_data = get_res.json()
        self.assertEqual(clip_data["title"], "Essential Distributed Systems Lesson")
        self.assertEqual(clip_data["duration"], 35.0)

        # 4. Update timestamps & title
        put_res = self.client.put("/api/clips/clp_test_crud_01", json={
            "title": "Scalable Systems Blueprint",
            "start_time": 12.0,
            "end_time": 50.0
        })
        self.assertEqual(put_res.status_code, 200)
        updated = put_res.json()
        self.assertEqual(updated["title"], "Scalable Systems Blueprint")
        self.assertEqual(updated["start_time"], 12.0)
        self.assertEqual(updated["end_time"], 50.0)
        self.assertEqual(updated["duration"], 38.0)

        # 5. Delete Clip
        del_res = self.client.delete("/api/clips/clp_test_crud_01")
        self.assertEqual(del_res.status_code, 200)

        # Verify 404
        self.assertEqual(self.client.get("/api/clips/clp_test_crud_01").status_code, 404)

        # Clean content
        self.client.delete(f"/api/content/{content_id}")

    def test_02_ai_clip_discovery_and_ranking(self):
        """Verify AI Clip discovery aligns boundaries to transcript segments and applies ranking scores."""
        # 1. Ingest Video Content
        video_bytes = create_sample_mp4()
        upload_res = self.client.post(
            "/api/content/upload",
            files={"file": ("keynote_talk.mp4", io.BytesIO(video_bytes), "video/mp4")}
        )
        self.assertEqual(upload_res.status_code, 200)
        content_id = upload_res.json()["id"]

        # 2. Add transcript segments and brief
        async def _seed_intelligence():
            async with async_session_factory() as session:
                trn_id = f"trn_{uuid.uuid4().hex[:8]}"
                t = Transcript(
                    id=trn_id,
                    content_id=content_id,
                    provider="mock",
                    language="en",
                    duration=60.0,
                    text="Welcome to the presentation. Here is why distributed queues change everything."
                )
                session.add(t)
                session.add(TranscriptSegment(
                    id=f"seg_{uuid.uuid4().hex[:8]}", transcript_id=trn_id, sequence=1,
                    start_time=0.0, end_time=14.2, text="Welcome to the presentation."
                ))
                session.add(TranscriptSegment(
                    id=f"seg_{uuid.uuid4().hex[:8]}", transcript_id=trn_id, sequence=2,
                    start_time=14.5, end_time=39.8, text="Here is why distributed queues change everything."
                ))
                session.add(TranscriptSegment(
                    id=f"seg_{uuid.uuid4().hex[:8]}", transcript_id=trn_id, sequence=3,
                    start_time=40.0, end_time=60.0, text="In summary, create once and transform everywhere."
                ))
                b = ContentBrief(
                    id=f"brf_{uuid.uuid4().hex[:8]}",
                    content_id=content_id,
                    title="How distributed queues decouple heavy media tasks.",
                    summary="How distributed queues decouple heavy media tasks.",
                    topics_json=json.dumps(["Queues", "Architecture"]),
                    keywords_json=json.dumps(["FFmpeg", "Redis"]),
                    key_points_json=json.dumps(["Decouple heavy video encoding from synchronous HTTP requests"]),
                    hooks_json=json.dumps(["Why most media workflows bottleneck under load"]),
                    quotes_json=json.dumps(["Create once and transform everywhere."]),
                    cta_suggestions_json=json.dumps(["Deploy locally with Docker"])
                )
                session.add(b)
                await session.commit()

        asyncio.run(_seed_intelligence())

        # 3. Run AI Clip Discovery directly via AIService
        discovered_clips = asyncio.run(ai_service.discover_and_persist_clips(
            content_id=content_id,
            min_duration=15.0,
            max_duration=90.0,
            target_count=3,
            force_refresh=True
        ))
        self.assertGreaterEqual(len(discovered_clips), 1)

        # 4. Verify candidate fields through API
        list_res = self.client.get(f"/api/content/{content_id}/clips")
        self.assertEqual(list_res.status_code, 200)
        items = list_res.json()["items"]
        self.assertGreaterEqual(len(items), 1)

        c0 = items[0]
        self.assertEqual(c0["status"], "CANDIDATE")
        self.assertGreaterEqual(c0["score"], 50.0)
        self.assertGreater(len(c0["hook"]), 0)
        self.assertGreater(len(c0["source_transcript_segment_ids"]), 0)
        self.assertGreater(len(c0["transcript_excerpt"]), 0)

        # Clean content
        self.client.delete(f"/api/content/{content_id}")

    def test_03_real_ffmpeg_clip_extraction_and_variants(self):
        """Verify real FFmpeg sub-clipping and 9:16 aspect ratio variant generation with FFprobe validation."""
        # 1. Ingest real test video
        video_bytes = create_sample_mp4()
        upload_res = self.client.post(
            "/api/content/upload",
            files={"file": ("raw_interview.mp4", io.BytesIO(video_bytes), "video/mp4")}
        )
        content_id = upload_res.json()["id"]
        asset_id = upload_res.json()["assets"][0]["id"]

        # 2. Add Clip manually
        async def _add_clip():
            async with async_session_factory() as session:
                c = Clip(
                    id="clp_real_ffmpeg_01",
                    content_id=content_id,
                    source_asset_id=asset_id,
                    title="Architecture Highlight",
                    hook="The secret to fast media pipelines.",
                    start_time=0.5,
                    end_time=2.5,
                    duration=2.0,
                    status="CANDIDATE",
                    score=95.0
                )
                session.add(c)
                await session.commit()

        asyncio.run(_add_add_clip := _add_clip())

        # 3. Process media for clip (extract master + 9:16 variant + thumbnail)
        asyncio.run(media_processor.process_clip_media(
            clip_id="clp_real_ffmpeg_01",
            aspect_ratios=["9:16", "1:1"],
            include_thumbnail=True
        ))

        # 4. Verify Clip is READY and variants exist
        clip_res = self.client.get("/api/clips/clp_real_ffmpeg_01")
        self.assertEqual(clip_res.status_code, 200)
        clip_data = clip_res.json()
        self.assertEqual(clip_data["status"], "READY")
        self.assertGreaterEqual(len(clip_data["variants"]), 3) # MASTER + 9:16 + 1:1 + THUMBNAIL

        # Check 9:16 variant
        var_916 = next(v for v in clip_data["variants"] if v["variant_type"] == "VERTICAL_9_16")
        self.assertEqual(var_916["width"], 1080)
        self.assertEqual(var_916["height"], 1920)

        # Check 1:1 variant
        var_11 = next(v for v in clip_data["variants"] if v["variant_type"] == "SQUARE_1_1")
        self.assertEqual(var_11["width"], 1080)
        self.assertEqual(var_11["height"], 1080)

        # 5. Verify physical streaming endpoints
        stream_res = self.client.get(f"/api/clips/clp_real_ffmpeg_01/variant/{var_916['id']}")
        self.assertEqual(stream_res.status_code, 200)
        self.assertEqual(stream_res.headers.get("content-type"), "video/mp4")
        self.assertGreater(len(stream_res.content), 0)

        primary_stream = self.client.get("/api/clips/clp_real_ffmpeg_01/stream")
        self.assertEqual(primary_stream.status_code, 200)
        self.assertEqual(primary_stream.headers.get("content-type"), "video/mp4")

        # 6. Delete Clip and verify physical files are removed
        real_916_path = storage_service.get_real_path(var_916["storage_key"])
        self.assertTrue(os.path.exists(real_916_path))

        self.client.delete("/api/clips/clp_real_ffmpeg_01")
        self.assertFalse(os.path.exists(real_916_path))

        # Cleanup content
        self.client.delete(f"/api/content/{content_id}")

    def test_04_end_to_end_worker_clip_pipeline(self):
        """
        Verify end-to-end asynchronous worker pipeline for Clips:
        1. API triggers CLIP_DISCOVERY job -> worker processes candidates
        2. API triggers CLIP_RENDER job -> worker cuts real master and 9:16 variant
        3. Verify all metadata and media are persisted and cascade deletion cleans storage.
        """
        video_bytes = create_sample_mp4()
        upload_res = self.client.post(
            "/api/content/upload",
            files={"file": ("full_webinar.mp4", io.BytesIO(video_bytes), "video/mp4")}
        )
        content_id = upload_res.json()["id"]

        # Seed intelligence
        async def _seed_data():
            async with async_session_factory() as session:
                trn_id = f"trn_{uuid.uuid4().hex[:8]}"
                t = Transcript(
                    id=trn_id,
                    content_id=content_id,
                    provider="mock",
                    language="en",
                    duration=60.0,
                    text="High performance media transcoding with Reflow."
                )
                session.add(t)
                session.add(TranscriptSegment(
                    id=f"seg_{uuid.uuid4().hex[:8]}", transcript_id=trn_id, sequence=1,
                    start_time=0.0, end_time=20.0, text="High performance media transcoding with Reflow."
                ))
                b = ContentBrief(
                    id=f"brf_{uuid.uuid4().hex[:8]}",
                    content_id=content_id,
                    title="Full walkthrough of video transcoding.",
                    summary="Full walkthrough of video transcoding.",
                    topics_json=json.dumps(["Media", "Architecture"]),
                    keywords_json=json.dumps(["FFmpeg", "NextJS"]),
                    key_points_json=json.dumps(["Automate content transformation effortlessly"]),
                    hooks_json=json.dumps(["Stop wasting hours on manual editing"]),
                    quotes_json=json.dumps(["Create once and transform everywhere."]),
                    cta_suggestions_json=json.dumps(["Star Reflow on GitHub"])
                )
                session.add(b)
                await session.commit()

        asyncio.run(_seed_data())

        # 1. Trigger Async Clip Discovery via API
        queue_service.clear_queue()
        disc_res = self.client.post(f"/api/content/{content_id}/clips/discover", json={
            "min_duration": 15.0,
            "max_duration": 45.0,
            "target_count": 2
        })
        self.assertEqual(disc_res.status_code, 200)

        # Dequeue and process CLIP_DISCOVERY job
        payload_disc = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertIsNotNone(payload_disc)
        self.assertEqual(payload_disc["job_type"], "CLIP_DISCOVERY")
        worker_disc_ok = asyncio.run(process_single_job(payload_disc))
        self.assertTrue(worker_disc_ok)

        # 2. Fetch discovered clips
        clips_res = self.client.get(f"/api/content/{content_id}/clips")
        self.assertEqual(clips_res.status_code, 200)
        items = clips_res.json()["items"]
        self.assertGreaterEqual(len(items), 1)
        target_clip_id = items[0]["id"]

        # 3. Trigger Async Clip Render via API
        render_res = self.client.post(f"/api/clips/{target_clip_id}/generate", json={
            "aspect_ratios": ["9:16"],
            "include_thumbnail": True
        })
        self.assertEqual(render_res.status_code, 200)

        # Dequeue and process CLIP_RENDER job
        payload_rnd = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertIsNotNone(payload_rnd)
        self.assertEqual(payload_rnd["job_type"], "CLIP_RENDER")
        worker_rnd_ok = asyncio.run(process_single_job(payload_rnd))
        self.assertTrue(worker_rnd_ok)

        # 4. Verify Clip is READY with 9:16 variant
        fresh_clip = self.client.get(f"/api/clips/{target_clip_id}").json()
        self.assertEqual(fresh_clip["status"], "READY")
        self.assertTrue(any(v["variant_type"] == "VERTICAL_9_16" for v in fresh_clip["variants"]))

        # 5. Delete Content -> cascade delete clips and files
        del_content_res = self.client.delete(f"/api/content/{content_id}")
        self.assertEqual(del_content_res.status_code, 200)
        self.assertEqual(self.client.get(f"/api/clips/{target_clip_id}").status_code, 404)

if __name__ == "__main__":
    unittest.main()
