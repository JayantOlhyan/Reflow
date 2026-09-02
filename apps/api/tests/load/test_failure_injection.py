import os
import uuid
import asyncio
import pytest
from sqlalchemy import select, delete
from fastapi.testclient import TestClient

from main import app
from database import init_db, async_session_factory
from models.entities import SystemJob, DeadLetterJob, TmpFileRecord
from services.queue_service import queue_service
from services.media_service import media_service
from services.ai_service import ai_service
from services.tmp_storage_service import tmp_storage_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_failure_db():
    asyncio.run(init_db())
    queue_service.clear_queue()

def test_redis_failure_and_fallback_resilience():
    """Simulates Redis disconnect and verifies fallback to in-process priority queue."""
    # Force Redis client to None to simulate Redis downtime
    queue_service._redis = None

    job_id_high = f"fail_job_high_{uuid.uuid4().hex[:6]}"
    job_id_low = f"fail_job_low_{uuid.uuid4().hex[:6]}"

    asyncio.run(queue_service.enqueue_media_job(job_id=job_id_low, priority="LOW"))
    asyncio.run(queue_service.enqueue_media_job(job_id=job_id_high, priority="HIGH"))

    depth = asyncio.run(queue_service.get_queue_depth())
    assert depth >= 2

    popped = asyncio.run(queue_service.dequeue_media_job(timeout=1))
    assert popped is not None
    assert popped["job_id"] == job_id_high  # High priority popped first in fallback mode

def test_ffmpeg_timeout_file_cleanup_injection():
    """Simulates FFmpeg timeout and verifies partial temp file is automatically unlinked."""
    tmp_output = tmp_storage_service.create_tmp_file_path(prefix="corrupt_out", extension=".mp4")
    
    # Create fake partial file
    with open(tmp_output, "w") as f:
        f.write("partial binary data")

    assert os.path.exists(tmp_output)

    # Command pointing to non-existent executable or timing out
    cmd = ["ffmpeg", "-y", "-i", "non_existent.mp4", tmp_output]

    with pytest.raises((ValueError, TimeoutError, Exception)):
        asyncio.run(media_service.run_ffmpeg_command(cmd, timeout=1))

    # Partial file must be unlinked/removed
    assert not os.path.exists(tmp_output)

def test_ai_provider_5xx_fallback_injection():
    """Simulates AI provider 5xx endpoint failure and verifies fallback to MockAIProvider."""
    # Instantiating custom AI provider that throws RuntimeError (5xx)
    class BrokenAIProvider:
        provider_name = "BrokenProvider500"
        async def transcribe(self, path):
            raise RuntimeError("HTTP 500 Internal Server Error from AI API")
        async def generate_json(self, prompt, schema):
            raise RuntimeError("HTTP 503 Service Unavailable from AI API")

    ai_service.set_provider(BrokenAIProvider())

    # Call should fall back cleanly to MockAIProvider without crashing
    raw_result, p_name = asyncio.run(ai_service._safe_transcribe("sample.mp3"))
    assert "text" in raw_result
    assert len(raw_result["text"]) > 0
    assert p_name == "mock"

def test_worker_crash_and_stale_job_recovery():
    """Simulates worker process crash leaving job in RUNNING state and verifies stale recovery."""
    stale_id = f"crash_{uuid.uuid4().hex[:8]}"

    def get_old_timestamp():
        from datetime import datetime, timedelta
        return datetime.utcnow() - timedelta(minutes=15)

    async def _setup_running_job():
        async with async_session_factory() as session:
            job = SystemJob(
                id=stale_id,
                job_type="TRANSCODE",
                status="RUNNING",
                started_at=get_old_timestamp()
            )
            session.add(job)
            await session.commit()

    asyncio.run(_setup_running_job())

    # Trigger stale job sweep
    recovered_count = asyncio.run(queue_service.detect_stale_jobs(timeout_minutes=10))
    assert recovered_count >= 1

    async def _verify_stale():
        async with async_session_factory() as session:
            res = await session.execute(select(SystemJob).where(SystemJob.id == stale_id))
            job = res.scalar_one_or_none()
            assert job is not None
            assert job.status == "STALE"

    asyncio.run(_verify_stale())
