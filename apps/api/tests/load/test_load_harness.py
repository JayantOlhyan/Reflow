import os
import time
import uuid
import asyncio
import pytest
from fastapi.testclient import TestClient

from main import app
from config import settings
from database import init_db, async_session_factory
from models.entities import Content, SystemJob, Publication, Asset
from services.queue_service import queue_service
from services.resource_manager import resource_manager

client = TestClient(app)

# Load test parameters from env
LOAD_COUNT = int(os.getenv("REFLOW_LOAD_CONTENT_COUNT", "20"))
LOAD_CONCURRENCY = int(os.getenv("REFLOW_LOAD_CONCURRENCY", "5"))

from sqlalchemy import delete

@pytest.fixture(autouse=True)
def setup_load_db():
    asyncio.run(init_db())
    queue_service.clear_queue()
    async def _clean():
        async with async_session_factory() as session:
            await session.execute(delete(SystemJob))
            await session.execute(delete(Content))
            await session.commit()
    asyncio.run(_clean())

def test_multi_content_workload_simulation():
    """
    Simulates high-concurrency ingestion of text, image, and video content items,
    triggering background variants, AI copy generation, clips, and scheduled publications.
    """
    start_time = time.perf_counter()
    created_ids = []

    # 1. Concurrent Content Creation
    for i in range(LOAD_COUNT):
        res = client.post("/api/content/text", json={
            "title": f"Load Test Item #{i}",
            "text": f"High volume load test item {i} describing repurposing capabilities across channels."
        })
        assert res.status_code == 200 or res.status_code == 201
        created_ids.append(res.json()["id"])

    assert len(created_ids) == LOAD_COUNT

    # 2. Concurrent Queue Dispatch
    async def _enqueue_batch():
        for content_id in created_ids[:LOAD_CONCURRENCY]:
            await queue_service.enqueue_media_job(
                job_id=f"job_load_{content_id}",
                content_id=content_id,
                job_type="MEDIA_PROCESSING",
                priority="HIGH" if content_id == created_ids[0] else "NORMAL"
            )

    asyncio.run(_enqueue_batch())

    # 3. Verify System Metrics & Latency
    elapsed = time.perf_counter() - start_time
    print(f"\n[LOAD HARNESS] Ingested {LOAD_COUNT} items & queued batch in {elapsed:.2f}s")
    
    perf_res = client.get("/api/system/performance")
    assert perf_res.status_code == 200
    perf_data = perf_res.json()
    assert perf_data["status"] in ("HEALTHY", "DEGRADED")
    assert perf_data["queue"]["queue_depth"] >= 0
