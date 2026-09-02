import uuid
import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from fastapi.testclient import TestClient

from main import app
from database import init_db, async_session_factory
from models.entities import Publication, SystemJob
from services.queue_service import queue_service
from services.scheduler_service import SchedulerService, scheduler_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_restart_db():
    asyncio.run(init_db())
    queue_service.clear_queue()

def test_concurrent_scheduler_daemons_atomic_claim_idempotency():
    """
    Simulates two concurrent scheduler daemon instances running claim_due_publications()
    simultaneously on due publications. Verifies that each publication is claimed by
    EXACTLY ONE scheduler instance with zero duplicate jobs or double publishing.
    """
    due_id = f"pub_due_{uuid.uuid4().hex[:8]}"
    now_utc = datetime.utcnow()
    past_due = now_utc - timedelta(minutes=5)

    async def _setup_due_pub():
        async with async_session_factory() as session:
            pub = Publication(
                id=due_id,
                title="Test Scheduled Video",
                content_id="content_test_123",
                platform="YOUTUBE",
                status="SCHEDULED",
                scheduled_at=past_due,
                timezone="UTC",
                request_payload_hash="payload_hash_test_123"
            )
            session.add(pub)
            await session.commit()

    asyncio.run(_setup_due_pub())

    # Instantiate two independent scheduler daemons
    sched1 = SchedulerService()
    sched2 = SchedulerService()

    # Run concurrent claims
    async def _concurrent_claim():
        res1, res2 = await asyncio.gather(
            sched1.claim_due_publications(limit=10),
            sched2.claim_due_publications(limit=10)
        )
        return res1, res2

    claimed1, claimed2 = asyncio.run(_concurrent_claim())

    # Exactly one scheduler daemon must have claimed due_id
    total_claims = len(claimed1) + len(claimed2)
    assert total_claims == 1
    assert (due_id in claimed1 and due_id not in claimed2) or (due_id in claimed2 and due_id not in claimed1)

    # Dispatch claimed publications
    if claimed1:
        asyncio.run(sched1.dispatch_claimed_publications(claimed1))
    if claimed2:
        asyncio.run(sched2.dispatch_claimed_publications(claimed2))

    # Verify publication status in DB is QUEUED or PUBLISHING, and exactly 1 SystemJob created
    async def _verify_pub_state():
        async with async_session_factory() as session:
            res = await session.execute(select(Publication).where(Publication.id == due_id))
            pub = res.scalar_one_or_none()
            assert pub is not None
            assert pub.status in ("QUEUED", "PUBLISHING")

            jobs_res = await session.execute(select(SystemJob).where(SystemJob.publication_id == due_id))
            jobs = jobs_res.scalars().all()
            assert len(jobs) == 1

    asyncio.run(_verify_pub_state())

def test_application_restart_service_health():
    """Verifies API router and health endpoints return HEALTHY after service startup."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("healthy", "HEALTHY")
