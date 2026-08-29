import sys
import os
import io
import unittest
import asyncio
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(__file__))

from main import app
from database import init_db
from services.storage_service import storage_service, validate_upload
from services.queue_service import queue_service
from worker import process_single_job

class TestReflowPipeline(unittest.TestCase):
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

    def test_02_valid_video_upload_and_processing_state(self):
        """Verify uploading a video immediately sets status PROCESSING and queues job."""
        fake_video = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41" + b"\x00" * 1024
        file_payload = ("test_video.mp4", io.BytesIO(fake_video), "video/mp4")
        
        res = self.client.post(
            "/api/content/upload",
            files={"file": file_payload},
            data={"title": "Masterclass Video"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["title"], "Masterclass Video")
        self.assertEqual(data["content_type"], "VIDEO")
        self.assertEqual(data["status"], "PROCESSING")
        self.assertEqual(len(data["assets"]), 1)
        
        asset = data["assets"][0]
        self.assertEqual(asset["original_filename"], "test_video.mp4")
        self.assertEqual(asset["mime_type"], "video/mp4")
        self.assertEqual(asset["file_size"], len(fake_video))
        
        # Verify physical original file exists on disk
        real_path = storage_service.get_real_path(asset["storage_key"])
        self.assertTrue(os.path.exists(real_path))

    def test_03_valid_image_upload(self):
        """Verify uploading a real PNG image."""
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 512
        file_payload = ("thumbnail.png", io.BytesIO(fake_png), "image/png")
        
        res = self.client.post(
            "/api/content/upload",
            files={"file": file_payload},
            data={"title": "Custom Thumbnail"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["content_type"], "IMAGE")
        self.assertEqual(data["status"], "READY")
        self.assertEqual(len(data["assets"]), 1)
        self.assertEqual(data["assets"][0]["mime_type"], "image/png")

    def test_04_valid_pdf_upload(self):
        """Verify uploading a real PDF document."""
        fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n" + b"\x00" * 256
        file_payload = ("whitepaper.pdf", io.BytesIO(fake_pdf), "application/pdf")
        
        res = self.client.post(
            "/api/content/upload",
            files={"file": file_payload},
            data={"title": "Creator Whitepaper"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["content_type"], "PDF")
        self.assertEqual(data["status"], "READY")
        self.assertEqual(len(data["assets"]), 1)

    def test_05_direct_text_content_creation(self):
        """Verify creating text/markdown content directly."""
        payload = {
            "title": "Architecture Design Notes",
            "text": "# Reflow Architecture\n\n- Modular connectors\n- Local-first persistence"
        }
        res = self.client.post("/api/content/text", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["title"], "Architecture Design Notes")
        self.assertEqual(data["content_type"], "TEXT")
        self.assertEqual(data["status"], "READY")
        self.assertIn("Modular connectors", data["text_content"])

    def test_06_unsupported_file_extension(self):
        """Verify rejection of executable or disallowed file types."""
        fake_exe = b"MZ\x90\x00\x03\x00\x00\x00"
        file_payload = ("malware.exe", io.BytesIO(fake_exe), "application/x-msdownload")
        
        res = self.client.post(
            "/api/content/upload",
            files={"file": file_payload}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported file extension", res.json()["message"])

    def test_07_path_traversal_attack_prevention(self):
        """Verify that malicious filenames containing path traversals are sanitized safely."""
        fake_data = b"Safe content"
        file_payload = ("../../../../etc/passwd.mp4", io.BytesIO(fake_data), "video/mp4")
        
        res = self.client.post(
            "/api/content/upload",
            files={"file": file_payload}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        storage_key = data["assets"][0]["storage_key"]
        
        self.assertTrue(storage_key.startswith("content/"))
        self.assertNotIn("..", storage_key)

    def test_08_duplicate_filenames_no_collision(self):
        """Verify two uploads with the exact same filename receive distinct IDs and do not overwrite."""
        file1 = ("podcast.mp4", io.BytesIO(b"Episode 1 content"), "video/mp4")
        file2 = ("podcast.mp4", io.BytesIO(b"Episode 2 completely different content"), "video/mp4")
        
        res1 = self.client.post("/api/content/upload", files={"file": file1})
        res2 = self.client.post("/api/content/upload", files={"file": file2})
        
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)
        
        data1 = res1.json()
        data2 = res2.json()
        
        self.assertNotEqual(data1["id"], data2["id"])
        self.assertNotEqual(data1["assets"][0]["storage_key"], data2["assets"][0]["storage_key"])

    def test_09_content_listing_filtering_and_search(self):
        """Verify pagination, type filtering, and search in GET /api/content."""
        res_all = self.client.get("/api/content?page=1&limit=50")
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.json()
        self.assertGreaterEqual(data_all["total"], 1)
        self.assertIsInstance(data_all["items"], list)

        res_video = self.client.get("/api/content?type=VIDEO")
        self.assertEqual(res_video.status_code, 200)
        for item in res_video.json()["items"]:
            self.assertEqual(item["content_type"], "VIDEO")

        res_search = self.client.get("/api/content?search=Masterclass")
        self.assertEqual(res_search.status_code, 200)
        self.assertTrue(any("Masterclass" in i["title"] for i in res_search.json()["items"]))

    def test_10_asset_streaming_access(self):
        """Verify streaming asset file returns correct content and Content-Type."""
        fake_content = b"Binary streamable content for preview"
        file_payload = ("stream_test.txt", io.BytesIO(fake_content), "text/plain")
        
        upload_res = self.client.post("/api/content/upload", files={"file": file_payload})
        self.assertEqual(upload_res.status_code, 200)
        uploaded = upload_res.json()
        content_id = uploaded["id"]
        asset_id = uploaded["assets"][0]["id"]

        stream_res = self.client.get(f"/api/content/{content_id}/asset/{asset_id}")
        self.assertEqual(stream_res.status_code, 200)
        self.assertEqual(stream_res.content, fake_content)
        self.assertIn("text/plain", stream_res.headers.get("content-type", ""))

    def test_11_content_deletion_and_physical_cleanup(self):
        """Verify deleting Content removes database records and deletes physical files."""
        fake_content = b"Content to be deleted"
        file_payload = ("delete_me.mp4", io.BytesIO(fake_content), "video/mp4")
        
        upload_res = self.client.post("/api/content/upload", files={"file": file_payload})
        uploaded = upload_res.json()
        content_id = uploaded["id"]
        storage_key = uploaded["assets"][0]["storage_key"]
        real_path = storage_service.get_real_path(storage_key)
        
        self.assertTrue(os.path.exists(real_path))

        # Delete
        del_res = self.client.delete(f"/api/content/{content_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["status"], "success")

        # Verify physical file is gone
        self.assertFalse(os.path.exists(real_path))

        # Verify 404 on subsequent get
        get_res = self.client.get(f"/api/content/{content_id}")
        self.assertEqual(get_res.status_code, 404)

if __name__ == "__main__":
    unittest.main()
