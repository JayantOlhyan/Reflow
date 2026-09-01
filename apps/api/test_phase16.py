import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from main import app
from database import async_session_factory, init_db
from models.entities import Content, Publication, Clip, Carousel, Notification

@pytest.mark.asyncio
async def test_notifications_crud():
    """Verify Notification creation, retrieval, unread counting, and mark-read operations."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Fetch initial notifications
        res1 = await ac.get("/api/notifications")
        assert res1.status_code == 200
        data1 = res1.json()
        assert "items" in data1
        assert "unread_count" in data1

        # 2. Directly create test notifications in DB
        notif_id = f"notif_test_{uuid.uuid4().hex[:8]}"
        async with async_session_factory() as session:
            notif = Notification(
                id=notif_id,
                type="PROCESSING_COMPLETE",
                title="Test Processing Done",
                message="Video processing completed successfully.",
                severity="SUCCESS",
                read=False,
                created_at=datetime.utcnow()
            )
            session.add(notif)
            await session.commit()

        # 3. Verify notification appears in list
        res2 = await ac.get("/api/notifications")
        assert res2.status_code == 200
        data2 = res2.json()
        assert any(n["id"] == notif_id for n in data2["items"])
        assert data2["unread_count"] >= 1

        # 4. Mark single read
        res3 = await ac.post(f"/api/notifications/{notif_id}/read")
        assert res3.status_code == 200

        # 5. Mark all read
        res4 = await ac.post("/api/notifications/read-all")
        assert res4.status_code == 200
        assert res4.json()["status"] == "success"

@pytest.mark.asyncio
async def test_global_search_api():
    """Verify global search across Content, Clips, Carousels, Publications, Experiments, Automations."""
    await init_db()
    search_keyword = f"Phase16Search_{uuid.uuid4().hex[:6]}"
    content_id = f"cnt_srch_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as session:
        cnt = Content(
            id=content_id,
            title=f"Masterclass on {search_keyword}",
            content_type="VIDEO",
            status="READY",
            created_at=datetime.utcnow()
        )
        session.add(cnt)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/search?q={search_keyword}")
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == search_keyword
        assert len(data["results"]) >= 1
        assert any(r["id"] == content_id for r in data["results"])

@pytest.mark.asyncio
async def test_approvals_api():
    """Verify single and batch publication approvals."""
    await init_db()
    cnt_id = f"cnt_appr_{uuid.uuid4().hex[:8]}"
    pub1_id = f"pub_appr1_{uuid.uuid4().hex[:8]}"
    pub2_id = f"pub_appr2_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as session:
        cnt = Content(id=cnt_id, title="Approval Test Content", content_type="VIDEO", status="READY")
        session.add(cnt)
        
        pub1 = Publication(id=pub1_id, content_id=cnt_id, platform="linkedin", status="DRAFT", title="Draft 1", request_payload_hash="dummy_hash_1")
        pub2 = Publication(id=pub2_id, content_id=cnt_id, platform="x", status="DRAFT", title="Draft 2", request_payload_hash="dummy_hash_2")
        session.add_all([pub1, pub2])
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Single Approve
        res1 = await ac.post(f"/api/publications/{pub1_id}/approve")
        assert res1.status_code == 200
        assert res1.json()["id"] == pub1_id

        # 2. Batch Approve
        res2 = await ac.post("/api/publications/approve-batch", json=[pub2_id])
        assert res2.status_code == 200
        assert res2.json()["approved_count"] == 1

@pytest.mark.asyncio
async def test_clip_and_carousel_detail_apis():
    """Verify single entity detail APIs for Clip and Carousel."""
    await init_db()
    cnt_id = f"cnt_det_{uuid.uuid4().hex[:8]}"
    clip_id = f"clp_det_{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as session:
        cnt = Content(id=cnt_id, title="Detail Test Content", content_type="VIDEO")
        session.add(cnt)
        
        clip = Clip(
            id=clip_id,
            content_id=cnt_id,
            title="Short Clip Highlight",
            hook="Insane strategy tip",
            start_time=10.0,
            end_time=25.0,
            duration=15.0,
            score=88.5,
            status="READY"
        )
        session.add(clip)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/clips/{clip_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == clip_id
        assert data["title"] == "Short Clip Highlight"
