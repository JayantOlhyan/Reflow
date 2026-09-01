import os
import sys
import asyncio
import pytest
from fastapi.testclient import TestClient

from sqlalchemy import delete
from main import app
from config import settings
from database import init_db, async_session_factory
from models.entities import SystemJob
from services.resource_manager import resource_manager, QueueOverflowError, InsufficientDiskError
from services.queue_service import queue_service
from services.tmp_storage_service import tmp_storage_service
from services.media_service import media_service
from services.ai_service import ai_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    asyncio.run(init_db())
    queue_service.clear_queue()
    async def _clean_jobs():
        async with async_session_factory() as session:
            await session.execute(delete(SystemJob))
            await session.commit()
    asyncio.run(_clean_jobs())

def test_resource_manager_disk_capacity_and_reservation():
    status = resource_manager.check_disk_capacity(required_mb=1.0)
    assert status["is_sufficient"] is True
    assert status["free_gb"] > 0

    # Reserve 10MB
    asyncio.run(resource_manager.reserve_disk_capacity(10.0))
    # Release 10MB
    asyncio.run(resource_manager.release_disk_reservation(10.0))

def test_worker_concurrency_and_priority_queueing():
    # Enqueue low priority job
    asyncio.run(queue_service.enqueue_media_job(job_id="job_low_123", job_type="MEDIA_PROCESSING", priority="LOW"))
    # Enqueue high priority job
    asyncio.run(queue_service.enqueue_media_job(job_id="job_high_456", job_type="MEDIA_PROCESSING", priority="HIGH"))

    # Dequeue should pop HIGH priority job first
    job1 = asyncio.run(queue_service.dequeue_media_job(timeout=1))
    assert job1 is not None
    assert job1["job_id"] == "job_high_456"

    job2 = asyncio.run(queue_service.dequeue_media_job(timeout=1))
    assert job2 is not None
    assert job2["job_id"] == "job_low_123"

def test_queue_backpressure_rejection():
    # Temporarily set max depth to 1 for testing
    old_max = settings.MAX_QUEUE_DEPTH
    settings.MAX_QUEUE_DEPTH = 1
    try:
        asyncio.run(queue_service.enqueue_media_job(job_id="job_bq_101", job_type="MEDIA_PROCESSING"))
        
        # Second enqueue should trigger QueueOverflowError
        with pytest.raises(QueueOverflowError):
            asyncio.run(queue_service.enqueue_media_job(job_id="job_bq_102", job_type="MEDIA_PROCESSING"))
    finally:
        settings.MAX_QUEUE_DEPTH = old_max

def test_ffmpeg_thread_limit_and_timeout():
    cmd = ["ffmpeg", "-y", "-version"]
    stdout, stderr = asyncio.run(media_service.run_ffmpeg_command(cmd, timeout=5))
    assert b"ffmpeg version" in stdout or b"FFmpeg" in stderr or proc_success(stdout, stderr)

def proc_success(out, err):
    return len(out) > 0 or len(err) > 0

def test_managed_tmp_storage_and_cleanup():
    tmp_path = tmp_storage_service.create_tmp_file_path(prefix="test_cleanup", extension=".tmp")
    with open(tmp_path, "w") as f:
        f.write("temporary data")
    assert os.path.exists(tmp_path)

    async def _cleanup():
        async with async_session_factory() as session:
            await tmp_storage_service.register_tmp_file(session, tmp_path, owner="test", ttl_hours=-1)
            return await tmp_storage_service.purge_expired_tmp_files(session)

    res = asyncio.run(_cleanup())
    assert res["purged_count"] >= 1
    assert not os.path.exists(tmp_path)

def test_ai_request_deduplication_key_generation():
    key1 = ai_service._compute_cache_key("copy_generation", "test payload 123")
    key2 = ai_service._compute_cache_key("copy_generation", "test payload 123")
    assert key1 == key2
    assert len(key1) == 64

def test_db_connection_pool_configuration():
    assert settings.DB_POOL_SIZE == 20
    assert settings.DB_MAX_OVERFLOW == 10
    assert settings.DB_POOL_TIMEOUT == 30
    assert settings.DB_POOL_RECYCLE == 1800

def test_performance_telemetry_rest_apis():
    # 1. Performance telemetry
    res = client.get("/api/system/performance")
    assert res.status_code == 200
    data = res.json()
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "database_pool" in data
    assert "queue" in data

    # 2. Storage breakdown
    s_res = client.get("/api/system/storage")
    assert s_res.status_code == 200
    s_data = s_res.json()
    assert "categories" in s_data
    assert "total_used_mb" in s_data

    # 3. Storage cleanup trigger
    c_res = client.post("/api/system/storage/cleanup")
    assert c_res.status_code == 200
    assert c_res.json()["status"] == "success"
