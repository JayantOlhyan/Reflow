import sys
import os
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(__file__))
from main import app

class TestReflowAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_status(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["product"], "Reflow")
        self.assertEqual(data["tagline"], "Create once. Transform everywhere.")

    def test_overview_endpoint(self):
        response = self.client.get("/api/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("metrics", data)
        self.assertIn("recent_activity", data)
        self.assertGreaterEqual(data["metrics"]["total"], 1)

    def test_content_library(self):
        response = self.client.get("/api/content")
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 1)

    def test_repurpose_generation(self):
        payload = {
            "content_id": "cnt-1",
            "target_format": "9:16",
            "destinations": ["instagram", "youtube", "linkedin", "x", "tiktok"]
        }
        response = self.client.post("/api/repurpose/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("outputs", data)
        self.assertIn("instagram", data["outputs"])
        self.assertIn("linkedin", data["outputs"])
        self.assertIn("x", data["outputs"])

    def test_carousel_generation(self):
        payload = {
            "topic": "5 Lessons from Building Open Source SaaS",
            "slide_count": 4
        }
        response = self.client.post("/api/carousels/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("slides", data)
        self.assertEqual(len(data["slides"]), 4)

    def test_system_health(self):
        response = self.client.get("/api/system/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["database"], "healthy")
        self.assertEqual(data["ffmpeg"], "healthy")

if __name__ == "__main__":
    unittest.main()
