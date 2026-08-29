import asyncio
import os
import sys
import json
import uuid
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from sqlalchemy import select, delete

sys.path.append(os.path.dirname(__file__))

from config import settings
from database import init_db, async_session_factory
from models.entities import Content, Asset, PlatformConnection, Publication, Job
from services.encryption_service import encryption_service
from services.scheduler_service import scheduler_service
from services.queue_service import queue_service

class TestSchedulingEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        self.test_content_id = f"cnt_sch_{uuid.uuid4().hex[:8]}"
        self.test_conn_yt = f"conn_yt_{uuid.uuid4().hex[:6]}"
        self.test_conn_ig = f"conn_ig_{uuid.uuid4().hex[:6]}"
        self.test_conn_li = f"conn_li_{uuid.uuid4().hex[:6]}"

        queue_service.clear_queue()

    async def asyncTearDown(self):
        async with async_session_factory() as session:
            from sqlalchemy import delete
            await session.execute(delete(Job).where(Job.content_id == self.test_content_id))
            await session.execute(delete(Publication).where(Publication.content_id == self.test_content_id))
            await session.execute(delete(PlatformConnection).where(PlatformConnection.id.in_([
                self.test_conn_yt, self.test_conn_ig, self.test_conn_li
            ])))
            await session.execute(delete(Content).where(Content.id == self.test_content_id))
            await session.commit()

    async def test_01_timezone_and_utc_conversion(self):
        """Test 1: Validates IANA timezone handling, UTC conversion, and DST safety."""
        # 1. Valid IANA timezone
        zi_kolkata = scheduler_service.validate_timezone("Asia/Kolkata")
        self.assertEqual(zi_kolkata.key, "Asia/Kolkata")

        # 2. Invalid timezone name should raise ValueError
        with self.assertRaises(ValueError) as ctx:
            scheduler_service.validate_timezone("IST")
        self.assertIn("INVALID_TIMEZONE", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            scheduler_service.validate_timezone("GMT+5:30")
        self.assertIn("INVALID_TIMEZONE", str(ctx2.exception))

        # 3. Daylight Saving Time (DST) test for America/New_York
        # Summer (EDT, UTC-4): 2026-07-15 14:00:00 EDT -> 18:00:00 UTC
        utc_summer, _ = scheduler_service.parse_and_validate_schedule_time(
            "2026-07-15T14:00:00",
            "America/New_York",
            min_lead_seconds=0,
            enforce_future=False
        )
        self.assertEqual(utc_summer.hour, 18)

        # Winter (EST, UTC-5): 2026-12-15 14:00:00 EST -> 19:00:00 UTC
        utc_winter, _ = scheduler_service.parse_and_validate_schedule_time(
            "2026-12-15T14:00:00",
            "America/New_York",
            min_lead_seconds=0,
            enforce_future=False
        )
        self.assertEqual(utc_winter.hour, 19)

        # 4. Non-DST test for Asia/Kolkata (always UTC+5:30)
        # 2026-09-10 14:30:00 IST -> 09:00:00 UTC
        utc_kolkata, _ = scheduler_service.parse_and_validate_schedule_time(
            "2026-09-10T14:30:00",
            "Asia/Kolkata",
            min_lead_seconds=0,
            enforce_future=False
        )
        self.assertEqual(utc_kolkata.hour, 9)
        self.assertEqual(utc_kolkata.minute, 0)

    async def test_02_past_time_and_minimum_lead_time_enforcement(self):
        """Test 2: Enforces future time constraint and minimum lead time threshold."""
        past_str = (datetime.utcnow() - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")
        with self.assertRaises(ValueError) as ctx:
            scheduler_service.parse_and_validate_schedule_time(past_str, "UTC", min_lead_seconds=60, enforce_future=True)
        self.assertIn("SCHEDULE_TIME_IN_PAST", str(ctx.exception))

        near_future_str = (datetime.utcnow() + timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%S")
        with self.assertRaises(ValueError) as ctx2:
            scheduler_service.parse_and_validate_schedule_time(near_future_str, "UTC", min_lead_seconds=60, enforce_future=True)
        self.assertIn("MINIMUM_LEAD_TIME_VIOLATION", str(ctx2.exception))

    async def test_03_multi_platform_batch_scheduling(self):
        """Test 3: Schedules content across YouTube, Instagram, and LinkedIn with independent publication records."""
        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Scheduled Masterpiece", content_type="VIDEO", status="READY")
            c_yt = PlatformConnection(id=self.test_conn_yt, platform="youtube", name="YT", status="CONNECTED", access_token_encrypted="enc")
            c_ig = PlatformConnection(id=self.test_conn_ig, platform="instagram", name="IG", status="CONNECTED", access_token_encrypted="enc")
            c_li = PlatformConnection(id=self.test_conn_li, platform="linkedin", name="LI", status="CONNECTED", access_token_encrypted="enc")
            session.add_all([cnt, c_yt, c_ig, c_li])
            await session.commit()

        future_local = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT15:00:00")
        destinations = [
            {"platform_connection_id": self.test_conn_yt, "title": "YT Video", "description": "Desc on YT"},
            {"platform_connection_id": self.test_conn_ig, "title": "IG Reel", "description": "Caption on IG"},
            {"platform_connection_id": self.test_conn_li, "title": "LI Post", "description": "Thought on LI"}
        ]

        async with async_session_factory() as session:
            pubs = await scheduler_service.schedule_publications(
                content_id=self.test_content_id,
                destinations=destinations,
                scheduled_time_str=future_local,
                timezone_name="Asia/Kolkata",
                db=session
            )

        self.assertEqual(len(pubs), 3)
        for p in pubs:
            self.assertEqual(p.status, "SCHEDULED")
            self.assertEqual(p.timezone, "Asia/Kolkata")
            self.assertIsNotNone(p.scheduled_at)

        # Verify in DB
        async with async_session_factory() as session:
            from sqlalchemy import select
            db_res = await session.execute(select(Publication).where(Publication.content_id == self.test_content_id))
            db_pubs = db_res.scalars().all()
            self.assertEqual(len(db_pubs), 3)

    async def test_04_scheduler_atomic_claiming_and_dispatch(self):
        """Test 4: Scheduler atomically claims due publications and enqueues PLATFORM_PUBLISH jobs."""
        due_utc = datetime.utcnow() - timedelta(seconds=10) # due 10 seconds ago

        pub_id = f"pub_due_{uuid.uuid4().hex[:6]}"
        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Due Video", content_type="VIDEO", status="READY")
            conn = PlatformConnection(id=self.test_conn_yt, platform="youtube", name="YT", status="CONNECTED", access_token_encrypted="enc")
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_yt,
                platform="youtube",
                status="SCHEDULED",
                title="Due Post",
                scheduled_at=due_utc,
                timezone="UTC",
                request_payload_hash="hash_due"
            )
            session.add_all([cnt, conn, pub])
            await session.commit()

        # 1. Scheduler claims due publication
        claimed_ids = await scheduler_service.claim_due_publications(limit=50)
        self.assertIn(pub_id, claimed_ids)

        # Verify claim in DB
        async with async_session_factory() as session:
            db_pub = await session.get(Publication, pub_id)
            self.assertIsNotNone(db_pub.claimed_at)
            self.assertEqual(db_pub.claim_owner, scheduler_service.instance_id)

        # 2. Scheduler dispatches claimed publication
        dispatched_count = await scheduler_service.dispatch_claimed_publications(claimed_ids)
        self.assertEqual(dispatched_count, 1)

        # Verify DB state -> QUEUED and Job created
        async with async_session_factory() as session:
            db_pub = await session.get(Publication, pub_id)
            self.assertEqual(db_pub.status, "QUEUED")
            self.assertIsNone(db_pub.claimed_at)

            job_res = await session.execute(select(Job).where(Job.content_id == self.test_content_id))
            job = job_res.scalar_one_or_none()
            self.assertIsNotNone(job)
            self.assertEqual(job.type, "PLATFORM_PUBLISH")

    async def test_05_crash_and_stale_claim_recovery(self):
        """Test 5: Stale claim lease recovery when a scheduler instance crashes."""
        pub_id = f"pub_stale_{uuid.uuid4().hex[:6]}"
        stale_time = datetime.utcnow() - timedelta(seconds=300) # claimed 5 minutes ago

        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Stale Item", content_type="VIDEO", status="READY")
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform="youtube",
                status="SCHEDULED",
                title="Stale Video",
                scheduled_at=datetime.utcnow() - timedelta(seconds=60),
                claimed_at=stale_time,
                claim_owner="crashed_scheduler_inst",
                request_payload_hash="hash_stale"
            )
            session.add_all([cnt, pub])
            await session.commit()

        # Run recovery
        recovered = await scheduler_service.recover_stale_claims()
        self.assertGreaterEqual(recovered, 1)

        # Verify DB: claim is cleared and publication is eligible again
        async with async_session_factory() as session:
            db_pub = await session.get(Publication, pub_id)
            self.assertEqual(db_pub.status, "SCHEDULED")
            self.assertIsNone(db_pub.claimed_at)
            self.assertIsNone(db_pub.claim_owner)

    async def test_06_reschedule_and_cancel_lifecycle(self):
        """Test 6: Rescheduling and cancellation state transitions."""
        pub_id = f"pub_mod_{uuid.uuid4().hex[:6]}"
        initial_utc = datetime.utcnow() + timedelta(days=1)

        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Mod Content", content_type="VIDEO", status="READY")
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform="instagram",
                status="SCHEDULED",
                title="Initial Post",
                scheduled_at=initial_utc,
                timezone="UTC",
                request_payload_hash="hash_mod"
            )
            session.add_all([cnt, pub])
            await session.commit()

        # 1. Reschedule
        new_time_local = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT18:00:00")
        async with async_session_factory() as session:
            rescheduled_pub = await scheduler_service.reschedule_publication(
                publication_id=pub_id,
                new_time_str=new_time_local,
                timezone_name="America/New_York",
                db=session
            )
            self.assertEqual(rescheduled_pub.timezone, "America/New_York")

        # 2. Cancel
        async with async_session_factory() as session:
            cancelled_pub = await scheduler_service.cancel_publication(
                publication_id=pub_id,
                db=session
            )
            self.assertEqual(cancelled_pub.status, "CANCELLED")
            self.assertIsNotNone(cancelled_pub.cancelled_at)

        # Verify cancelled publications are NOT claimed by scheduler
        claimed_ids = await scheduler_service.claim_due_publications(limit=50)
        self.assertNotIn(pub_id, claimed_ids)

    async def test_07_calendar_events_query(self):
        """Test 7: Calendar range query localization."""
        pub_id = f"pub_cal_{uuid.uuid4().hex[:6]}"
        sched_utc = datetime.utcnow() + timedelta(hours=2)

        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Calendar Content", content_type="VIDEO", status="READY")
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform="x",
                status="SCHEDULED",
                title="Calendar Tweet",
                scheduled_at=sched_utc,
                timezone="Asia/Kolkata",
                request_payload_hash="hash_cal"
            )
            session.add_all([cnt, pub])
            await session.commit()

        async with async_session_factory() as session:
            events = await scheduler_service.get_calendar_events(
                start_utc=datetime.utcnow() - timedelta(days=1),
                end_utc=datetime.utcnow() + timedelta(days=2),
                view_timezone="Asia/Kolkata",
                db=session
            )

        matching = [e for e in events if e["publication_id"] == pub_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["content_title"], "Calendar Content")
        self.assertEqual(matching[0]["platform"], "x")
        self.assertTrue(len(matching[0]["scheduled_at_local"]) > 0)

    async def test_08_content_deletion_protection_for_scheduled_content(self):
        """Test 8: Prevents deleting content if it has future active scheduled publications."""
        pub_id = f"pub_del_{uuid.uuid4().hex[:6]}"
        sched_utc = datetime.utcnow() + timedelta(days=3)

        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Protected Content", content_type="VIDEO", status="READY")
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform="youtube",
                status="SCHEDULED",
                title="Protected Post",
                scheduled_at=sched_utc,
                timezone="UTC",
                request_payload_hash="hash_del"
            )
            session.add_all([cnt, pub])
            await session.commit()

        # Attempting to delete content with scheduled publication should be blocked
        from fastapi import HTTPException
        from main import delete_content

        async with async_session_factory() as session:
            with self.assertRaises(HTTPException) as ctx:
                await delete_content(self.test_content_id, db=session)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("active scheduled publication(s) exist", ctx.exception.detail)

    async def test_09_missed_schedule_handling(self):
        """Test 9: Verifies that missed schedules during downtime are dispatched according to policy."""
        pub_id = f"pub_missed_{uuid.uuid4().hex[:6]}"
        missed_utc = datetime.utcnow() - timedelta(hours=3) # scheduled 3 hours ago during downtime

        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Missed Video", content_type="VIDEO", status="READY")
            conn = PlatformConnection(id=self.test_conn_yt, platform="youtube", name="YT", status="CONNECTED", access_token_encrypted="enc")
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_yt,
                platform="youtube",
                status="SCHEDULED",
                title="Missed Post",
                scheduled_at=missed_utc,
                timezone="UTC",
                request_payload_hash="hash_missed"
            )
            session.add_all([cnt, conn, pub])
            await session.commit()

        # Scheduler recovers and claims missed publication
        claimed_ids = await scheduler_service.claim_due_publications(limit=50)
        self.assertIn(pub_id, claimed_ids)

        # Dispatch
        dispatched = await scheduler_service.dispatch_claimed_publications(claimed_ids)
        self.assertEqual(dispatched, 1)

        # Verify publication transitioned to QUEUED
        async with async_session_factory() as session:
            db_pub = await session.get(Publication, pub_id)
            self.assertEqual(db_pub.status, "QUEUED")

if __name__ == "__main__":
    unittest.main()
