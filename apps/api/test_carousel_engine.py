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
from models.entities import Content, Carousel, CarouselSlide, SlideElement, CarouselExport, Job
from services.storage_service import storage_service
from services.queue_service import queue_service
from services.ai_service import ai_service
from services.ai.mock_provider import MockAIProvider
from services.carousel_renderer import carousel_renderer
from worker import process_single_job

class TestReflowCarouselEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncio.run(init_db())
        cls.client = TestClient(app)
        ai_service.set_provider(MockAIProvider())

    def setUp(self):
        queue_service.clear_queue()

    def test_01_carousel_crud_and_versioning(self):
        """Verify Carousel, Slide CRUD, and automatic version incrementation."""
        # 1. Create Carousel
        create_res = self.client.post("/api/carousels", json={
            "title": "System Scalability Playbook",
            "template": "EDITORIAL",
            "aspect_ratio": "1:1"
        })
        self.assertEqual(create_res.status_code, 200)
        c_data = create_res.json()
        carousel_id = c_data["id"]
        self.assertEqual(c_data["title"], "System Scalability Playbook")
        self.assertEqual(c_data["version"], 1)

        # 2. Add Slides
        s1_res = self.client.post(f"/api/carousels/{carousel_id}/slides", json={
            "headline": "01. Partitioning Strategies",
            "body": "Split databases vertically or horizontally to avoid single-node contention.",
            "tag": "DATABASE"
        })
        self.assertEqual(s1_res.status_code, 200)
        s1_data = s1_res.json()
        self.assertEqual(s1_data["version"], 2)
        self.assertEqual(len(s1_data["slides"]), 1)
        slide_1_id = s1_data["slides"][0]["id"]

        s2_res = self.client.post(f"/api/carousels/{carousel_id}/slides", json={
            "headline": "02. Event-Driven Queues",
            "body": "Decouple heavy transcoding operations from synchronous HTTP lifecycles.",
            "tag": "ASYNC"
        })
        self.assertEqual(s2_res.status_code, 200)
        s2_data = s2_res.json()
        self.assertEqual(s2_data["version"], 3)
        self.assertEqual(len(s2_data["slides"]), 2)
        slide_2_id = s2_data["slides"][1]["id"]

        # 3. Update Slide copy
        update_slide_res = self.client.put(f"/api/carousels/{carousel_id}/slides/{slide_1_id}", json={
            "headline": "01. Dynamic Sharding"
        })
        self.assertEqual(update_slide_res.status_code, 200)
        self.assertEqual(update_slide_res.json()["version"], 4)
        self.assertEqual(update_slide_res.json()["slides"][0]["headline"], "01. Dynamic Sharding")

        # 4. Reorder Slides
        reorder_res = self.client.put(f"/api/carousels/{carousel_id}/slides/reorder", json={
            "slide_ids": [slide_2_id, slide_1_id]
        })
        self.assertEqual(reorder_res.status_code, 200)
        reordered_slides = reorder_res.json()["slides"]
        self.assertEqual(reordered_slides[0]["id"], slide_2_id)
        self.assertEqual(reordered_slides[0]["position"], 1)
        self.assertEqual(reordered_slides[1]["id"], slide_1_id)
        self.assertEqual(reordered_slides[1]["position"], 2)

        # 5. Delete Carousel
        del_res = self.client.delete(f"/api/carousels/{carousel_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_02_ai_carousel_planning_and_validation(self):
        """Verify AI Carousel planner produces schema-validated multi-slide decks."""
        # Create text source content
        cnt_res = self.client.post("/api/content/text", json={
            "title": "High Performance Caching",
            "text": "Redis caching strategies, cache invalidation, cache stampede protection."
        })
        content_id = cnt_res.json()["id"]

        # Create carousel linked to content
        car_res = self.client.post("/api/carousels", json={
            "content_id": content_id,
            "title": "High Performance Caching",
            "template": "BOLD"
        })
        carousel_id = car_res.json()["id"]

        # Plan carousel with AI
        carousel_obj = asyncio.run(ai_service.plan_and_persist_carousel(
            carousel_id=carousel_id,
            content_id=content_id,
            target_slide_count=5,
            template="BOLD"
        ))
        self.assertEqual(carousel_obj.slide_count, 5)
        self.assertEqual(carousel_obj.template, "BOLD")

        # Fetch carousel from API
        fetch_res = self.client.get(f"/api/carousels/{carousel_id}")
        self.assertEqual(fetch_res.status_code, 200)
        deck = fetch_res.json()
        self.assertEqual(len(deck["slides"]), 5)
        self.assertEqual(deck["slides"][0]["purpose"], "HOOK")
        self.assertEqual(deck["slides"][-1]["purpose"], "CTA")

        # Clean up
        self.client.delete(f"/api/carousels/{carousel_id}")
        self.client.delete(f"/api/content/{content_id}")

    def test_03_server_side_rendering_and_pdf_export(self):
        """Verify rendering 1080x1080 PNG slides and multi-page PDF document."""
        car_res = self.client.post("/api/carousels", json={
            "title": "Render Engine Verification",
            "template": "MINIMAL"
        })
        carousel_id = car_res.json()["id"]

        # Add 3 test slides
        for i in range(1, 4):
            self.client.post(f"/api/carousels/{carousel_id}/slides", json={
                "headline": f"Slide Number {i:02d}",
                "body": f"Detailed architectural explanation for slide {i}.",
                "tag": f"STEP {i}"
            })

        # Render Deck
        render_res = self.client.post(f"/api/carousels/{carousel_id}/render")
        self.assertEqual(render_res.status_code, 200)
        render_data = render_res.json()["data"]
        self.assertEqual(render_data["slide_count"], 3)
        self.assertGreater(render_data["pdf_size"], 0)
        self.assertEqual(len(render_data["slides_png"]), 3)

        # Verify physical files exist on storage
        pdf_real_path = storage_service.get_real_path(render_data["pdf_key"])
        self.assertTrue(os.path.exists(pdf_real_path))
        self.assertGreater(os.path.getsize(pdf_real_path), 100)

        for png_key in render_data["slides_png"]:
            png_real_path = storage_service.get_real_path(png_key)
            self.assertTrue(os.path.exists(png_real_path))
            with open(png_real_path, "rb") as f:
                header = f.read(8)
                self.assertEqual(header, b'\x89PNG\r\n\x1a\n')

        # Test export streaming endpoint
        car_fresh = self.client.get(f"/api/carousels/{carousel_id}").json()
        self.assertGreaterEqual(len(car_fresh["exports"]), 2)
        pdf_exp = next(e for e in car_fresh["exports"] if e["format"] == "PDF")

        stream_res = self.client.get(f"/api/carousels/{carousel_id}/export/{pdf_exp['id']}")
        self.assertEqual(stream_res.status_code, 200)
        self.assertEqual(stream_res.headers.get("content-type"), "application/pdf")
        self.assertGreater(len(stream_res.content), 0)

        # Cleanup
        self.client.delete(f"/api/carousels/{carousel_id}")
        self.assertFalse(os.path.exists(pdf_real_path))

    def test_04_end_to_end_worker_carousel_generation(self):
        """
        Verify end-to-end async worker job processing for CAROUSEL_GENERATION:
        1. API triggers async generation -> job enqueued
        2. Worker processes job -> plans slides -> renders PNGs + PDF -> marks READY
        3. Verify all slides and exports are persisted and downloadable.
        """
        car_res = self.client.post("/api/carousels", json={
            "title": "Async Worker Carousel Demo",
            "template": "EDUCATIONAL"
        })
        carousel_id = car_res.json()["id"]

        # 1. Trigger Async Generation
        gen_res = self.client.post(f"/api/carousels/{carousel_id}/generate", json={
            "slide_count": 6,
            "template": "EDUCATIONAL"
        })
        self.assertEqual(gen_res.status_code, 200)

        # 2. Dequeue and execute worker
        payload = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        self.assertIsNotNone(payload)
        self.assertEqual(payload["job_type"], "CAROUSEL_GENERATION")
        self.assertEqual(payload["carousel_id"], carousel_id)

        worker_ok = asyncio.run(process_single_job(payload))
        self.assertTrue(worker_ok)

        # 3. Verify Carousel is now READY with 6 slides and exports
        fetch_res = self.client.get(f"/api/carousels/{carousel_id}")
        self.assertEqual(fetch_res.status_code, 200)
        deck = fetch_res.json()
        self.assertEqual(deck["status"], "READY")
        self.assertEqual(len(deck["slides"]), 6)
        self.assertGreaterEqual(len(deck["exports"]), 1)

        # Cleanup
        self.client.delete(f"/api/carousels/{carousel_id}")

if __name__ == "__main__":
    unittest.main()
