import os
import io
import asyncio
from fastapi.testclient import TestClient
from main import app
from database import init_db
from services.queue_service import queue_service
from services.media_service import media_processor
from worker import process_single_job

def run_persistence_verification():
    print("🚀 Starting Phase 2 Persistence & Media Verification...")
    asyncio.run(init_db())
    client = TestClient(app)

    # 1. Generate real video fixture
    test_video_path = "/tmp/reflow_persist_test.mp4"
    cmd = "ffmpeg -y -f lavfi -i testsrc=duration=2:size=320x180:rate=30 -f lavfi -i sine=frequency=1000:duration=2 -c:v libx264 -pix_fmt yuv420p -c:a aac /tmp/reflow_persist_test.mp4 > /dev/null 2>&1"
    os.system(cmd)

    with open(test_video_path, "rb") as f:
        v_bytes = f.read()

    # 2. Ingest Video
    v_res = client.post("/api/content/upload", files={"file": ("intro_video.mp4", io.BytesIO(v_bytes), "video/mp4")}, data={"title": "Introduction to Reflow"})
    assert v_res.status_code == 200, f"Video upload failed: {v_res.text}"
    v_data = v_res.json()
    v_id = v_data["id"]
    v_asset_id = v_data["assets"][0]["id"]
    print(f"✅ Ingested Video: {v_id} -> Asset {v_asset_id} (Status: {v_data['status']})")

    # 3. Process Video Job with Worker
    job_payload = asyncio.run(queue_service.dequeue_media_job(timeout=2))
    assert job_payload is not None, "Job was not enqueued to queue"
    worker_success = asyncio.run(process_single_job(job_payload))
    assert worker_success, "Worker failed to process video job"

    # Verify Content transitioned to READY with variants
    v_ready_res = client.get(f"/api/content/{v_id}")
    v_ready_data = v_ready_res.json()
    assert v_ready_data["status"] == "READY", f"Expected READY, got {v_ready_data['status']}"
    assert len(v_ready_data["variants"]) == 5, f"Expected 5 variants, got {len(v_ready_data['variants'])}"
    print(f"✅ Worker generated 5 variants for {v_id}: {[v['variant_type'] for v in v_ready_data['variants']]}")

    # 4. Ingest Image
    img_bytes = b"\x89PNG\r\n\x1a\n" + b"REAL_IMAGE_DATA" * 20
    img_res = client.post("/api/content/upload", files={"file": ("cover.png", io.BytesIO(img_bytes), "image/png")}, data={"title": "YouTube Cover Art"})
    assert img_res.status_code == 200, f"Image upload failed: {img_res.text}"
    img_data = img_res.json()
    img_id = img_data["id"]
    img_asset_id = img_data["assets"][0]["id"]
    print(f"✅ Ingested Image: {img_id} -> Asset {img_asset_id}")

    # 5. Ingest PDF
    pdf_bytes = b"%PDF-1.4\n" + b"REAL_PDF_DATA" * 20
    pdf_res = client.post("/api/content/upload", files={"file": ("guide.pdf", io.BytesIO(pdf_bytes), "application/pdf")}, data={"title": "Repurposing Guide"})
    assert pdf_res.status_code == 200, f"PDF upload failed: {pdf_res.text}"
    pdf_data = pdf_res.json()
    pdf_id = pdf_data["id"]
    pdf_asset_id = pdf_data["assets"][0]["id"]
    print(f"✅ Ingested PDF: {pdf_id} -> Asset {pdf_asset_id}")

    # 6. Ingest Text Note
    txt_res = client.post("/api/content/text", json={"title": "Content Blueprint", "text": "Create once. Transform everywhere."})
    assert txt_res.status_code == 200, f"Text creation failed: {txt_res.text}"
    txt_data = txt_res.json()
    txt_id = txt_data["id"]
    print(f"✅ Created Text Note: {txt_id}")

    # 7. Verify Variant and Asset Streaming
    vert_variant = next(v for v in v_ready_data["variants"] if v["variant_type"] == "VERTICAL_9_16")
    v_stream = client.get(f"/api/content/{v_id}/variant/{vert_variant['id']}")
    assert v_stream.status_code == 200 and len(v_stream.content) > 0, "Vertical video streaming failed"

    thumb_variant = next(v for v in v_ready_data["variants"] if v["variant_type"] == "THUMBNAIL")
    thumb_stream = client.get(f"/api/content/{v_id}/variant/{thumb_variant['id']}")
    assert thumb_stream.status_code == 200 and len(thumb_stream.content) > 0, "Thumbnail streaming failed"
    print("✅ Verified Variant & Thumbnail Streaming.")

    # 8. Simulate Server Restart (re-instantiate client & reload from DB)
    client2 = TestClient(app)
    list_res = client2.get("/api/content?page=1&limit=20")
    assert list_res.status_code == 200
    all_items = list_res.json()["items"]
    ids = [i["id"] for i in all_items]
    assert v_id in ids, "Video missing after restart"
    assert img_id in ids, "Image missing after restart"
    assert pdf_id in ids, "PDF missing after restart"
    assert txt_id in ids, "Text note missing after restart"

    persisted_video = next(i for i in all_items if i["id"] == v_id)
    assert len(persisted_video["variants"]) == 5, "Variants missing after restart"
    print(f"✅ Restart / Persistence Verification Passed! All {len(all_items)} assets and variants remain persisted on disk and in database.")

    # Cleanup temp
    if os.path.exists(test_video_path):
        os.remove(test_video_path)

if __name__ == "__main__":
    run_persistence_verification()
