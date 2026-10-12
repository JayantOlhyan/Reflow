import sys
import os
import uuid
import unittest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app
from database import init_db, async_session_factory
from models.entities import Content, Asset, InboundSource, SourceFeedItem, Workflow, WorkflowExecution
from services.podcast_ingestion_service import podcast_ingestion_service
from services.drip_queue_service import drip_queue_service
from services.workflow_engine_service import workflow_engine_service
from services.audiogram_service import audiogram_service
from services.storage_service import storage_service
from config import settings

SAMPLE_PODCAST_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>The Reflow Tech Show</title>
    <description>Open source content automation and architecture</description>
    <link>https://reflow.local</link>
    <itunes:image href="https://reflow.local/cover.jpg" />
    <item>
      <title>Episode 42: How to Repurpose Content on Autopilot</title>
      <description>In this episode we break down automated distribution pipelines #repurpose #automation</description>
      <guid>ep_42_guid_unique</guid>
      <pubDate>Mon, 12 Oct 2026 12:00:00 GMT</pubDate>
      <itunes:duration>1800</itunes:duration>
      <enclosure url="https://reflow.local/audio/ep42.mp3" type="audio/mpeg" length="25000000" />
    </item>
    <item>
      <title>Episode 41: Audio to Video with Audiograms</title>
      <description>Visualizing soundwaves for LinkedIn and TikTok</description>
      <guid>ep_41_guid_unique</guid>
      <pubDate>Mon, 05 Oct 2026 12:00:00 GMT</pubDate>
      <itunes:duration>30:00</itunes:duration>
      <enclosure url="https://reflow.local/audio/ep41.mp3" type="audio/mpeg" length="24000000" />
    </item>
  </channel>
</rss>
"""

class TestRepurposeEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncio.run(init_db())
        cls.client = TestClient(app)

    def test_01_podcast_rss_parsing(self):
        """Verify PodcastIngestionService parses channel and episode metadata accurately."""
        parsed = podcast_ingestion_service.parse_feed_xml(SAMPLE_PODCAST_RSS)
        self.assertEqual(parsed["title"], "The Reflow Tech Show")
        self.assertEqual(parsed["episode_count"], 2)
        
        ep1 = parsed["episodes"][0]
        self.assertEqual(ep1["guid"], "ep_42_guid_unique")
        self.assertEqual(ep1["title"], "Episode 42: How to Repurpose Content on Autopilot")
        self.assertEqual(ep1["duration_seconds"], 1800)
        self.assertEqual(ep1["media_url"], "https://reflow.local/audio/ep42.mp3")

        ep2 = parsed["episodes"][1]
        self.assertEqual(ep2["duration_seconds"], 1800) # 30:00 -> 1800s

    def test_02_drip_queue_scheduling(self):
        """Verify DripQueueService spaces out publications within active hours."""
        schedule = drip_queue_service.calculate_drip_schedule(
            count=3,
            interval_hours=4,
            active_hours_start=9,
            active_hours_end=21,
            start_time=datetime(2026, 10, 13, 10, 0, 0)
        )
        self.assertEqual(len(schedule), 3)
        # First post at 14:00, second at 18:00, third at 22:00 pushed to next day 09:00
        self.assertEqual(schedule[0].hour, 14)
        self.assertEqual(schedule[1].hour, 18)
        self.assertEqual(schedule[2].hour, 9)
        self.assertTrue(schedule[2] > schedule[1])

    def test_03_inbound_sources_api_lifecycle(self):
        """Verify creating, listing, getting, and deleting inbound sources via API."""
        # Create Source
        create_res = self.client.post("/api/v1/sources", json={
            "name": "My Weekly Podcast",
            "source_type": "PODCAST_RSS",
            "config": {"feed_url": "https://podcast.example.com/rss.xml"},
            "is_active": True
        })
        self.assertEqual(create_res.status_code, 201)
        source_id = create_res.json()["id"]

        # List Sources
        list_res = self.client.get("/api/v1/sources")
        self.assertEqual(list_res.status_code, 200)
        ids = [s["id"] for s in list_res.json()]
        self.assertIn(source_id, ids)

        # Get Source Details
        get_res = self.client.get(f"/api/v1/sources/{source_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["name"], "My Weekly Podcast")

        # Cleanup Delete
        del_res = self.client.delete(f"/api/v1/sources/{source_id}")
        self.assertEqual(del_res.status_code, 204)

    def test_04_workflows_api_lifecycle_and_execution(self):
        """Verify creating, running, and updating automated workflows."""
        # 1. Create content item to test with
        test_cnt_id = f"cnt_test_wf_{uuid.uuid4().hex[:8]}"
        async def create_test_content():
            async with async_session_factory() as session:
                cnt = Content(
                    id=test_cnt_id,
                    title="Automated Multi-Platform Strategy #repurpose",
                    content_type="VIDEO",
                    status="READY",
                    text_content="Full transcript describing automated content distribution."
                )
                session.add(cnt)
                await session.commit()
        asyncio.run(create_test_content())

        # 2. Create Workflow
        wf_res = self.client.post("/api/v1/workflows", json={
            "name": "YouTube to Shorts & Reels",
            "mode": "AUTOMATIC",
            "active": True,
            "filters": {
                "include_hashtags": ["#repurpose"],
                "exclude_hashtags": ["#sponsor"]
            },
            "actions_config": {
                "action_type": "AI_CLIPS",
                "aspect_ratios": ["9:16"]
            },
            "destinations": [
                {
                    "platform": "youtube",
                    "privacy": "PUBLIC",
                    "custom_caption": "Watch full: {{title}}"
                },
                {
                    "platform": "instagram",
                    "privacy": "PUBLIC",
                    "custom_caption": "{{title}} - Link in bio"
                }
            ],
            "drip_config": {
                "drip_enabled": True,
                "interval_hours": 3
            }
        })
        self.assertEqual(wf_res.status_code, 201)
        wf_id = wf_res.json()["id"]

        # 3. Execute Workflow Run
        run_res = self.client.post(f"/api/v1/workflows/{wf_id}/run", json={
            "content_id": test_cnt_id
        })
        self.assertEqual(run_res.status_code, 200)
        run_data = run_res.json()
        self.assertEqual(run_data["status"], "succeeded")
        self.assertEqual(run_data["publications_count"], 2)

        # 4. Get Workflow with Executions
        detail_res = self.client.get(f"/api/v1/workflows/{wf_id}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["execution_count"], 1)
        self.assertGreaterEqual(len(detail_res.json()["recent_executions"]), 1)

        # 5. Delete Workflow
        del_wf = self.client.delete(f"/api/v1/workflows/{wf_id}")
        self.assertEqual(del_wf.status_code, 204)

    def test_05_audiograms_api_lifecycle(self):
        """Verify audiogram templates listing and creation."""
        # 1. List templates
        tpl_res = self.client.get("/api/v1/audiograms/templates")
        self.assertEqual(tpl_res.status_code, 200)
        templates = tpl_res.json()
        self.assertGreaterEqual(len(templates), 1)

        # 2. Create custom template
        create_res = self.client.post("/api/v1/audiograms/templates", json={
            "name": "Custom Emerald Podcast",
            "aspect_ratio": "9:16",
            "waveform_style": "LINE",
            "waveform_color": "#10B981",
            "background_color": "#09090B",
            "caption_style": "BOLD_PUNCH"
        })
        self.assertEqual(create_res.status_code, 201)
        created = create_res.json()
        self.assertEqual(created["status"], "success")
        self.assertIn("tpl_aud_", created["id"])

        # 3. Verify it appears in template list
        list_again = self.client.get("/api/v1/audiograms/templates")
        self.assertEqual(list_again.status_code, 200)
        names = [t["name"] for t in list_again.json()]
        self.assertIn("Custom Emerald Podcast", names)

    def test_06_audiogram_ffmpeg_synthesis(self):
        """Verify local FFmpeg generates an MP4 audiogram with waveform and valid metadata."""
        import wave
        import math
        import struct

        # Synthesize 1 second sine wave audio
        sample_rate = 44100
        duration = 1.0
        frequency = 440.0
        n_samples = int(sample_rate * duration)
        
        test_audio_path = os.path.join(settings.STORAGE_DIR, "test_audio.wav")
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        with wave.open(test_audio_path, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for i in range(n_samples):
                val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
                data = struct.pack("<h", val)
                wav_file.writeframesraw(data)

        out_key = "audiograms/test_output.mp4"
        async def run_render():
            return await audiogram_service.generate_audiogram(
                audio_file_path=test_audio_path,
                output_storage_key=out_key,
                aspect_ratio="9:16",
                waveform_style="BARS",
                waveform_color="#EC4899",
                background_color="#0F172A",
                duration=1.0
            )

        res = asyncio.run(run_render())
        self.assertEqual(res["aspect_ratio"], "9:16")
        self.assertEqual(res["width"], 1080)
        self.assertEqual(res["height"], 1920)
        self.assertGreater(res["file_size"], 1000)
        
        full_path = storage_service.get_full_path(out_key)
        self.assertTrue(os.path.exists(full_path))

if __name__ == "__main__":
    unittest.main()
