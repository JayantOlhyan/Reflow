import unittest
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from database import init_db, async_session_factory
from models.entities import Publication, PostMetricSnapshot, PlatformConnection, Content
from services.analytics_service import analytics_service
from services.publishing_service import publishing_service

class TestAnalyticsEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        self.test_content_id = f"cnt_test_{uuid.uuid4().hex[:8]}"
        self.test_conn_id = f"conn_test_{uuid.uuid4().hex[:8]}"
        self.test_pub_id = f"pub_test_{uuid.uuid4().hex[:8]}"

        async with async_session_factory() as session:
            # Create test content
            content = Content(
                id=self.test_content_id,
                title="Phase 10 Analytics Master Video",
                content_type="VIDEO",
                created_at=datetime.utcnow()
            )
            session.add(content)

            # Create test platform connection
            conn = PlatformConnection(
                id=self.test_conn_id,
                name="Reflow Tech",
                platform="youtube",
                account_name="Reflow Tech",
                handle="@reflowtech",
                status="CONNECTED",
                created_at=datetime.utcnow()
            )
            session.add(conn)

            # Create test publication
            pub = Publication(
                id=self.test_pub_id,
                content_id=self.test_content_id,
                platform="youtube",
                platform_connection_id=self.test_conn_id,
                status="PUBLISHED",
                title="Phase 10 Published Video",
                description="Test Description",
                request_payload_hash="hash_test_12345",
                external_post_id="dQw4w9WgXcQ",
                external_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                published_at=datetime.utcnow() - timedelta(days=2),
                analytics_status="NOT_SYNCED",
                created_at=datetime.utcnow() - timedelta(days=2)
            )
            session.add(pub)
            await session.commit()

    # 1. Metric Normalization & NULL semantics
    async def test_metric_normalization_null_semantics(self):
        # Raw dict with explicit 0 and missing fields
        raw = {
            "views": 0,
            "likes": 150,
            "comments": 25,
            "shares": None
            # impressions and reach omitted
        }
        norm = analytics_service.normalize_metrics("youtube", raw)

        self.assertEqual(norm["views"], 0, "Explicit zero should be preserved as 0, not None or fallback")
        self.assertEqual(norm["likes"], 150)
        self.assertEqual(norm["comments"], 25)
        self.assertIsNone(norm["shares"], "Missing/None shares should remain None")
        self.assertIsNone(norm["impressions"], "Omitted impressions should remain None")
        self.assertIsNone(norm["reach"], "Omitted reach should remain None")
        self.assertEqual(norm["engagements"], 175, "Engagements should sum available engagement dimensions")

    # 2. Engagement Rate Mathematical Integrity (No Zero Division)
    async def test_engagement_rate_zero_division_protection(self):
        # Case A: Denominator is 0
        rate_zero = analytics_service.calculate_engagement_rate(
            likes=10, comments=5, shares=0, saves=0, reach=0, impressions=0
        )
        self.assertIsNone(rate_zero, "Engagement rate must be None when reach/impressions is 0")

        # Case B: Denominator is None
        rate_none = analytics_service.calculate_engagement_rate(
            likes=10, comments=5, shares=0, saves=0, reach=None, impressions=None
        )
        self.assertIsNone(rate_none, "Engagement rate must be None when reach and impressions are None")

        # Case C: Valid Reach
        rate_valid = analytics_service.calculate_engagement_rate(
            likes=50, comments=10, shares=5, saves=5, reach=1000, impressions=1500
        )
        # Numerator = 70, Denominator = 1000 (reach preferred) -> 7.0%
        self.assertEqual(rate_valid, 7.0)

        # Case D: Reach is None, Valid Impressions
        rate_imp = analytics_service.calculate_engagement_rate(
            likes=20, comments=10, shares=0, saves=0, reach=None, impressions=500
        )
        # Numerator = 30, Denominator = 500 -> 6.0%
        self.assertEqual(rate_imp, 6.0)

    # 3. Snapshot Creation & Immutability
    async def test_snapshot_creation_and_immutability(self):
        async with async_session_factory() as session:
            # Create Snapshot 1
            snap1 = PostMetricSnapshot(
                id=f"snap_{uuid.uuid4().hex[:8]}",
                publication_id=self.test_pub_id,
                platform="youtube",
                external_post_id="dQw4w9WgXcQ",
                captured_at=datetime.utcnow() - timedelta(hours=5),
                views=100,
                likes=10,
                comments=2,
                engagements=12,
                created_at=datetime.utcnow() - timedelta(hours=5)
            )
            session.add(snap1)

            # Create Snapshot 2 (Later time)
            snap2 = PostMetricSnapshot(
                id=f"snap_{uuid.uuid4().hex[:8]}",
                publication_id=self.test_pub_id,
                platform="youtube",
                external_post_id="dQw4w9WgXcQ",
                captured_at=datetime.utcnow(),
                views=350,
                likes=35,
                comments=8,
                engagements=43,
                created_at=datetime.utcnow()
            )
            session.add(snap2)
            await session.commit()

            # Verify both snapshots persist independently
            res = await session.execute(
                select(PostMetricSnapshot)
                .where(PostMetricSnapshot.publication_id == self.test_pub_id)
                .order_by(PostMetricSnapshot.captured_at.asc())
            )
            snaps = res.scalars().all()
            self.assertEqual(len(snaps), 2, "Historical snapshots must be preserved immutably")
            self.assertEqual(snaps[0].views, 100)
            self.assertEqual(snaps[1].views, 350)

    # 4. Publication Drill-down & Hourly Growth Velocity
    async def test_publication_drilldown_and_velocity(self):
        async with async_session_factory() as session:
            snap1 = PostMetricSnapshot(
                id=f"snap_v1_{uuid.uuid4().hex[:8]}",
                publication_id=self.test_pub_id,
                platform="youtube",
                captured_at=datetime.utcnow() - timedelta(hours=2),
                views=200,
                engagements=20
            )
            snap2 = PostMetricSnapshot(
                id=f"snap_v2_{uuid.uuid4().hex[:8]}",
                publication_id=self.test_pub_id,
                platform="youtube",
                captured_at=datetime.utcnow(),
                views=600,
                engagements=80
            )
            session.add_all([snap1, snap2])
            await session.commit()

            drill = await analytics_service.get_publication_analytics(self.test_pub_id, db=session)
            self.assertEqual(drill["snapshot_count"], 2)
            self.assertEqual(drill["latest_snapshot"].views, 600)
            # Delta views = 400 over 2.0 hours -> 200.0 views/hr
            self.assertIsNotNone(drill["views_per_hour"])
            self.assertAlmostEqual(drill["views_per_hour"], 200.0, delta=1.0)
            # Delta engagements = 60 over 2.0 hours -> 30.0 eng/hr
            self.assertIsNotNone(drill["engagements_per_hour"])
            self.assertAlmostEqual(drill["engagements_per_hour"], 30.0, delta=1.0)

    # 5. Overview KPI Aggregation & Period Comparison
    async def test_overview_aggregation_and_comparison(self):
        async with async_session_factory() as session:
            # Add snapshot for test publication
            snap = PostMetricSnapshot(
                id=f"snap_ov_{uuid.uuid4().hex[:8]}",
                publication_id=self.test_pub_id,
                platform="youtube",
                captured_at=datetime.utcnow(),
                views=1200,
                impressions=1500,
                likes=120,
                comments=30,
                engagements=150
            )
            session.add(snap)
            await session.commit()

            start = datetime.utcnow() - timedelta(days=7)
            end = datetime.utcnow()
            overview = await analytics_service.get_overview_analytics(start, end, db=session)

            self.assertGreaterEqual(overview["total_publications"], 1)
            self.assertGreaterEqual(overview["total_views"], 1200)
            self.assertGreaterEqual(overview["total_engagements"], 150)
            self.assertIsNotNone(overview["average_engagement_rate"])

    # 6. Platform Capabilities & Metrics Declaration
    def test_platform_capabilities_analytics_declarations(self):
        yt = publishing_service.get_connector("youtube")
        ig = publishing_service.get_connector("instagram")
        li = publishing_service.get_connector("linkedin")
        x = publishing_service.get_connector("x")
        fb = publishing_service.get_connector("facebook")
        tt = publishing_service.get_connector("tiktok")

        self.assertTrue(yt.get_capabilities().supports_analytics)
        self.assertIn("views", yt.get_capabilities().supported_metrics)

        self.assertTrue(ig.get_capabilities().supports_analytics)
        self.assertIn("reach", ig.get_capabilities().supported_metrics)

        self.assertTrue(li.get_capabilities().supports_analytics)
        self.assertIn("clicks", li.get_capabilities().supported_metrics)

        self.assertTrue(x.get_capabilities().supports_analytics)
        self.assertIn("reposts", x.get_capabilities().supported_metrics)

        self.assertTrue(fb.get_capabilities().supports_analytics)
        self.assertFalse(tt.get_capabilities().supports_analytics, "TikTok analytics should remain unsupported/False")

    # 7. Timeseries Daily Bucket Aggregation
    async def test_timeseries_daily_bucket_aggregation(self):
        async with async_session_factory() as session:
            start = datetime.utcnow() - timedelta(days=5)
            end = datetime.utcnow()
            ts = await analytics_service.get_timeseries_analytics(start, end, db=session)

            self.assertEqual(len(ts), 6, "Timeseries should produce daily buckets for each day in range")
            for item in ts:
                self.assertIn("date", item)
                self.assertIn("publications_count", item)

    # 8. Content Attribution Leaderboard
    async def test_content_analytics_leaderboard(self):
        async with async_session_factory() as session:
            snap = PostMetricSnapshot(
                id=f"snap_cnt_{uuid.uuid4().hex[:8]}",
                publication_id=self.test_pub_id,
                platform="youtube",
                captured_at=datetime.utcnow(),
                views=850,
                engagements=95
            )
            session.add(snap)
            await session.commit()

            start = datetime.utcnow() - timedelta(days=7)
            end = datetime.utcnow()
            content_perf = await analytics_service.get_content_analytics(start, end, db=session)

            self.assertGreaterEqual(len(content_perf), 1)
            item = next((c for c in content_perf if c["content_id"] == self.test_content_id), None)
            self.assertIsNotNone(item)
            self.assertEqual(item["title"], "Phase 10 Analytics Master Video")
            self.assertIn("youtube", item["platforms"])
            self.assertEqual(item["total_views"], 850)

    # 9. CSV Export Formatting with NULL Preservation
    async def test_csv_export_formatting(self):
        async with async_session_factory() as session:
            start = datetime.utcnow() - timedelta(days=7)
            end = datetime.utcnow()
            csv_out = await analytics_service.export_analytics_csv(start, end, db=session)

            self.assertIn("Publication ID,Content Title,Platform,Published At", csv_out)
            self.assertIn(self.test_pub_id, csv_out)
            self.assertIn("youtube", csv_out)

    # 10. Status Decoupling on Auth Failure
    async def test_status_decoupling_on_auth_failure(self):
        async with async_session_factory() as session:
            # Set connection status to EXPIRED/FAILED
            conn_res = await session.execute(select(PlatformConnection).where(PlatformConnection.id == self.test_conn_id))
            conn = conn_res.scalar_one()
            conn.status = "EXPIRED"
            conn.access_token_encrypted = ""
            conn.refresh_token_encrypted = ""
            await session.commit()

            # Attempt sync
            snap = await analytics_service.sync_publication_metrics(self.test_pub_id)
            self.assertIsNone(snap)

            # Verify publication status is still PUBLISHED, but analytics_status is REAUTH_REQUIRED
            pub_res = await session.execute(select(Publication).where(Publication.id == self.test_pub_id))
            pub = pub_res.scalar_one()
            self.assertEqual(pub.status, "PUBLISHED", "Publication post status must NEVER change to FAILED due to metrics sync issue")
            self.assertEqual(pub.analytics_status, "REAUTH_REQUIRED")
            self.assertEqual(pub.analytics_error_code, "CONNECTION_NOT_CONNECTED")

if __name__ == "__main__":
    unittest.main()
