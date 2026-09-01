import time
import asyncio
import pytest
from fastapi.testclient import TestClient

from main import app
from database import init_db
from services.resource_manager import resource_manager
from services.queue_service import queue_service

client = TestClient(app)

import uuid
from sqlalchemy import delete
from models.entities import SystemJob
from database import async_session_factory

@pytest.fixture(autouse=True)
def setup_benchmark_db():
    asyncio.run(init_db())
    queue_service.clear_queue()
    async def _clean():
        async with async_session_factory() as session:
            await session.execute(delete(SystemJob))
            await session.commit()
    asyncio.run(_clean())

def test_benchmark_api_response_latency():
    """Measures p50, p95, p99 response latency for high-frequency telemetry API."""
    latencies = []
    for _ in range(50):
        start = time.perf_counter()
        res = client.get("/api/system/performance")
        duration = (time.perf_counter() - start) * 1000.0  # ms
        assert res.status_code == 200
        latencies.append(duration)

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    
    print(f"\n[BENCHMARK] Telemetry API Latency: p50={p50:.2f}ms, p95={p95:.2f}ms")
    assert p50 < 100.0  # Sub-100ms requirement for local self-hosted API

def test_benchmark_queue_throughput():
    """Measures enqueue/dequeue operations per second (ops/sec)."""
    num_jobs = 100
    batch_prefix = uuid.uuid4().hex[:6]
    start = time.perf_counter()
    
    for i in range(num_jobs):
        asyncio.run(queue_service.enqueue_media_job(job_id=f"bm_job_{batch_prefix}_{i}", job_type="BENCHMARK"))
        
    enqueue_time = time.perf_counter() - start
    enqueue_ops = num_jobs / enqueue_time

    start_deq = time.perf_counter()
    for _ in range(num_jobs):
        asyncio.run(queue_service.dequeue_media_job(timeout=1))
        
    dequeue_time = time.perf_counter() - start_deq
    dequeue_ops = num_jobs / dequeue_time

    print(f"\n[BENCHMARK] Queue Operations: Enqueue={enqueue_ops:.1f} ops/sec, Dequeue={dequeue_ops:.1f} ops/sec")
    assert enqueue_ops > 100.0
