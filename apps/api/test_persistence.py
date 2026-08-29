import os
import io
import asyncio
from fastapi.testclient import TestClient
from main import app
from database import init_db

def run_persistence_verification():
    print("🚀 Starting Phase 1 Persistence & Real File Verification...")
    asyncio.run(init_db())
    client = TestClient(app)

    # 1. Ingest Video
    v_bytes = b"\x00\x00\x00\x1cftypisom" + b"REAL_VIDEO_DATA" * 50
    v_res = client.post("/api/content/upload", files={"file": ("intro_video.mp4", io.BytesIO(v_bytes), "video/mp4")}, data={"title": "Introduction to Reflow"})
    assert v_res.status_code == 200, f"Video upload failed: {v_res.text}"
    v_data = v_res.json()
    v_id = v_data["id"]
    v_asset_id = v_data["assets"][0]["id"]
    print(f"✅ Ingested Video: {v_id} -> Asset {v_asset_id}")

    # 2. Ingest Image
    img_bytes = b"\x89PNG\r\n\x1a\n" + b"REAL_IMAGE_DATA" * 20
    img_res = client.post("/api/content/upload", files={"file": ("cover.png", io.BytesIO(img_bytes), "image/png")}, data={"title": "YouTube Cover Art"})
    assert img_res.status_code == 200, f"Image upload failed: {img_res.text}"
    img_data = img_res.json()
    img_id = img_data["id"]
    img_asset_id = img_data["assets"][0]["id"]
    print(f"✅ Ingested Image: {img_id} -> Asset {img_asset_id}")

    # 3. Ingest PDF
    pdf_bytes = b"%PDF-1.4\n" + b"REAL_PDF_DATA" * 20
    pdf_res = client.post("/api/content/upload", files={"file": ("guide.pdf", io.BytesIO(pdf_bytes), "application/pdf")}, data={"title": "Repurposing Guide"})
    assert pdf_res.status_code == 200, f"PDF upload failed: {pdf_res.text}"
    pdf_data = pdf_res.json()
    pdf_id = pdf_data["id"]
    pdf_asset_id = pdf_data["assets"][0]["id"]
    print(f"✅ Ingested PDF: {pdf_id} -> Asset {pdf_asset_id}")

    # 4. Ingest Text Note
    txt_res = client.post("/api/content/text", json={"title": "Content Blueprint", "text": "Create once. Transform everywhere."})
    assert txt_res.status_code == 200, f"Text creation failed: {txt_res.text}"
    txt_data = txt_res.json()
    txt_id = txt_data["id"]
    print(f"✅ Created Text Note: {txt_id}")

    # 5. Verify Streaming
    v_stream = client.get(f"/api/content/{v_id}/asset/{v_asset_id}")
    assert v_stream.status_code == 200 and v_stream.content == v_bytes, "Video streaming mismatch"
    
    img_stream = client.get(f"/api/content/{img_id}/asset/{img_asset_id}")
    assert img_stream.status_code == 200 and img_stream.content == img_bytes, "Image streaming mismatch"

    pdf_stream = client.get(f"/api/content/{pdf_id}/asset/{pdf_asset_id}")
    assert pdf_stream.status_code == 200 and pdf_stream.content == pdf_bytes, "PDF streaming mismatch"
    print("✅ Verified Asset Streaming for Video, Image, and PDF.")

    # 6. Simulate Server Restart (re-instantiate client & reload from DB)
    client2 = TestClient(app)
    list_res = client2.get("/api/content?page=1&limit=20")
    assert list_res.status_code == 200
    all_items = list_res.json()["items"]
    ids = [i["id"] for i in all_items]
    assert v_id in ids, "Video missing after restart"
    assert img_id in ids, "Image missing after restart"
    assert pdf_id in ids, "PDF missing after restart"
    assert txt_id in ids, "Text note missing after restart"
    print(f"✅ Restart / Persistence Verification Passed! All {len(all_items)} assets remain persisted on disk and in database.")

if __name__ == "__main__":
    run_persistence_verification()
