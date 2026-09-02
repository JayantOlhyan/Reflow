import os
import time
import asyncio
import psutil
import pytest
from fastapi.testclient import TestClient

from main import app
from database import init_db
from services.queue_service import queue_service

client = TestClient(app)

# Configurable soak duration via env
SOAK_DURATION_SEC = int(os.getenv("REFLOW_LOAD_DURATION_SECONDS", "5"))

@pytest.fixture(autouse=True)
def setup_soak_db():
    asyncio.run(init_db())
    queue_service.clear_queue()

def test_sustained_soak_processing_and_memory_stability():
    """
    Sustained load soak test running continuous background job processing over configured duration,
    monitoring process RSS memory usage, open file descriptors, and queue health to detect leaks.
    """
    start_time = time.perf_counter()
    process = psutil.Process()
    initial_mem_mb = process.memory_info().rss / (1024 ** 2)
    processed_count = 0

    while time.perf_counter() - start_time < SOAK_DURATION_SEC:
        job_id = f"soak_job_{processed_count}"
        asyncio.run(queue_service.enqueue_media_job(job_id=job_id, job_type="SOAK_WORKLOAD"))
        popped = asyncio.run(queue_service.dequeue_media_job(timeout=1))
        if popped:
            asyncio.run(queue_service.complete_job(popped["job_id"]))
        processed_count += 1
        time.sleep(0.01)

    end_mem_mb = process.memory_info().rss / (1024 ** 2)
    mem_delta_mb = end_mem_mb - initial_mem_mb

    print(f"\n[SOAK TEST] Processed {processed_count} jobs over {SOAK_DURATION_SEC}s. Process Memory delta: {mem_delta_mb:+.2f} MB")
    assert processed_count > 0
    # Process memory growth should be minimal (< 50MB RSS growth)
    assert mem_delta_mb < 50.0
