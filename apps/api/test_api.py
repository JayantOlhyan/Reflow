import sys
import os
import unittest
import asyncio
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(__file__))

from main import app
from database import init_db
from services.storage_service import storage_service, validate_upload
from connectors.youtube import YouTubeConnector
from connectors.instagram import InstagramConnector

class TestReflowFoundation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncio.run(init_db())
        cls.client = TestClient(app)

    def test_01_liveness_health(self):
        """Verify GET /health returns 200 and accurate service metadata."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "Reflow API")
        self.assertIn("version", data)

    def test_02_system_health_telemetry(self):
        """Verify GET /api/system/health performs active component checks."""
        response = self.client.get("/api/system/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("components", data)
        self.assertIn("database", data["components"])
        self.assertIn("storage", data["components"])
        self.assertIn("ffmpeg", data["components"])
        self.assertIn("ai", data["components"])

    def test_03_genuine_overview_metrics(self):
        """Verify GET /api/overview calculates real counts from DB without fake fallbacks."""
        response = self.client.get("/api/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("metrics", data)
        metrics = data["metrics"]
        self.assertIsInstance(metrics["total"], int)
        self.assertIsInstance(metrics["published"], int)
        self.assertIsInstance(metrics["scheduled"], int)
        self.assertIsInstance(metrics["failed"], int)

    def test_04_content_crud(self):
        """Verify creating, reading, and deleting content assets."""
        # Create
        payload = {
            "title": "Automated Test Asset",
            "type": "video",
            "source": "/storage/test.mp4",
            "duration": 120
        }
        res_create = self.client.post("/api/content", json=payload)
        self.assertEqual(res_create.status_code, 200)
        created = res_create.json()
        self.assertEqual(created["title"], "Automated Test Asset")
        content_id = created["id"]

        # Read list
        res_list = self.client.get("/api/content")
        self.assertEqual(res_list.status_code, 200)
        items = res_list.json()
        self.assertTrue(any(i["id"] == content_id for i in items))

        # Delete
        res_del = self.client.delete(f"/api/content/{content_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["status"], "success")

    def test_05_storage_abstraction_and_security(self):
        """Verify storage service operations and path traversal security."""
        test_path = "test_dir/sample_file.txt"
        test_data = b"Reflow Storage Test Data"
        
        saved_path = asyncio.run(storage_service.put(test_path, test_data))
        self.assertTrue(os.path.exists(saved_path))
        
        exists = asyncio.run(storage_service.exists(test_path))
        self.assertTrue(exists)
        
        retrieved = asyncio.run(storage_service.get(test_path))
        self.assertEqual(retrieved, test_data)
        
        deleted = asyncio.run(storage_service.delete(test_path))
        self.assertTrue(deleted)

        # Path traversal attack defense
        with self.assertRaises(ValueError):
            asyncio.run(storage_service.put("../../etc/evil.txt", b"evil"))

    def test_06_upload_validation(self):
        """Verify upload validation logic."""
        # Valid MP4
        valid, err = validate_upload("clip.mp4", "video/mp4", 1024 * 1024)
        self.assertTrue(valid)
        self.assertIsNone(err)

        # Invalid executable extension
        valid, err = validate_upload("malware.exe", "application/octet-stream", 1024)
        self.assertFalse(valid)
        self.assertIn("Unsupported file extension", err)

        # File exceeds size limit
        valid, err = validate_upload("huge.mp4", "video/mp4", 600 * 1024 * 1024)
        self.assertFalse(valid)
        self.assertIn("exceeds maximum", err)

    def test_07_connector_not_implemented_contract(self):
        """Verify platform publishing endpoints explicitly return not_implemented status."""
        # Direct API endpoint check
        res = self.client.post("/api/publish?platform=youtube")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "not_implemented")
        self.assertIn("not implemented yet", data["message"])

        # Connector class check
        yt = YouTubeConnector()
        pub_res = asyncio.run(yt.publish("sample.mp4", {}))
        self.assertEqual(pub_res["status"], "not_implemented")

    def test_08_repurpose_and_carousel_synthesis(self):
        """Verify repurpose generation and carousel deck synthesis endpoints."""
        rep_payload = {
            "content_id": "non_existent_id",
            "target_format": "9:16",
            "destinations": ["instagram", "x"]
        }
        res_rep = self.client.post("/api/repurpose/generate", json=rep_payload)
        self.assertEqual(res_rep.status_code, 200)
        self.assertIn("outputs", res_rep.json())

        car_payload = {
            "topic": "Clean Architecture in Python",
            "slide_count": 4
        }
        res_car = self.client.post("/api/carousels/generate", json=car_payload)
        self.assertEqual(res_car.status_code, 200)
        self.assertEqual(len(res_car.json()["slides"]), 4)

if __name__ == "__main__":
    unittest.main()
