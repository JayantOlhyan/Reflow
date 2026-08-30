import sys
import os
import unittest
import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from database import init_db, async_session_factory
from models.entities import (
    Experiment, ExperimentVariant, ExperimentResult, Content, Publication,
    PostMetricSnapshot, ContentRecommendation, ContentPattern, Job
)
from services.experiment_service import experiment_service

sys.path.append(os.path.dirname(__file__))

class TestExperimentEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        async with async_session_factory() as session:
            # Clean database tables
            await session.execute(delete(ExperimentResult))
            await session.execute(delete(ExperimentVariant))
            await session.execute(delete(Experiment))
            await session.execute(delete(PostMetricSnapshot))
            await session.execute(delete(Publication))
            await session.execute(delete(ContentPattern))
            await session.execute(delete(ContentRecommendation))
            await session.execute(delete(Content))
            await session.execute(delete(Job))
            await session.commit()

    async def test_01_create_experiment_success(self):
        """Verifies successful experiment creation with control and treatment variants."""
        async with async_session_factory() as session:
            # Add dummy content
            c = Content(id="c_test_01", title="Source Content", content_type="VIDEO", status="READY")
            session.add(c)
            await session.commit()

        async with async_session_factory() as session:
            exp = await experiment_service.create_experiment(
                db=session,
                name="Test Experiment 01",
                hypothesis="Statistic hooks perform better than direct claims.",
                platform="linkedin",
                primary_metric="engagement_rate",
                scope="HOOK",
                control_content_id="c_test_01",
                treatment_content_id="c_test_01"
            )
            self.assertIsNotNone(exp.id)
            self.assertEqual(exp.status, "DRAFT")
            self.assertEqual(exp.scope, "HOOK")

            # Check that variants are persisted
            res = await session.execute(select(ExperimentVariant).where(ExperimentVariant.experiment_id == exp.id))
            variants = res.scalars().all()
            self.assertEqual(len(variants), 2)
            self.assertTrue(any(v.role == "CONTROL" for v in variants))
            self.assertTrue(any(v.role == "TREATMENT" for v in variants))

    async def test_02_invalid_design_different_platforms(self):
        """Verifies that an experiment with different platforms throws an exception or fails validation."""
        async with async_session_factory() as session:
            c = Content(id="c_test_02", title="Source Content", content_type="VIDEO", status="READY")
            pub_ctrl = Publication(id="pub_c_02", content_id="c_test_02", title="Ctrl Title", platform="youtube", status="PUBLISHED", request_payload_hash="h1")
            pub_treat = Publication(id="pub_t_02", content_id="c_test_02", title="Treat Title", platform="linkedin", status="PUBLISHED", request_payload_hash="h2")
            session.add_all([c, pub_ctrl, pub_treat])
            await session.commit()

        async with async_session_factory() as session:
            # Rejects different platforms
            with self.assertRaises(ValueError):
                await experiment_service.create_experiment(
                    db=session,
                    name="Test Mismatched Platforms",
                    hypothesis="Should fail",
                    platform="linkedin",
                    primary_metric="engagement_rate",
                    scope="HOOK",
                    control_content_id="c_test_02",
                    treatment_content_id="c_test_02",
                    control_publication_id="pub_c_02",
                    treatment_publication_id="pub_t_02"
                )

    async def test_03_design_validation_different_content_family(self):
        """Verifies rejection of different source contents for single-variable hook tests."""
        async with async_session_factory() as session:
            c1 = Content(id="c_test_03_a", title="Content A", content_type="VIDEO", status="READY")
            c2 = Content(id="c_test_03_b", title="Content B", content_type="VIDEO", status="READY")
            session.add_all([c1, c2])
            await session.commit()

        async with async_session_factory() as session:
            with self.assertRaises(ValueError):
                # Cannot test hooks across different content items (breaks single variable principle)
                await experiment_service.create_experiment(
                    db=session,
                    name="Mismatched Source Contents",
                    hypothesis="Should fail",
                    platform="linkedin",
                    primary_metric="engagement_rate",
                    scope="HOOK",
                    control_content_id="c_test_03_a",
                    treatment_content_id="c_test_03_b"
                )

    async def test_04_equal_window_protection(self):
        """Verifies that an experiment does not declare a winner if observations are not yet time-aligned."""
        async with async_session_factory() as session:
            c = Content(id="c_test_04", title="Source Content", content_type="VIDEO", status="READY")
            # Control published 30 hours ago (has 24h data)
            pub_ctrl = Publication(
                id="pub_c_04", content_id="c_test_04", title="Ctrl 04", platform="linkedin", status="PUBLISHED",
                published_at=datetime.utcnow() - timedelta(hours=30), request_payload_hash="h1"
            )
            # Treatment published 6 hours ago (incomplete evaluation window)
            pub_treat = Publication(
                id="pub_t_04", content_id="c_test_04", title="Treat 04", platform="linkedin", status="PUBLISHED",
                published_at=datetime.utcnow() - timedelta(hours=6), request_payload_hash="h2"
            )
            session.add_all([c, pub_ctrl, pub_treat])

            # Snapshots
            snap_c = PostMetricSnapshot(
                id="snap_c_04", publication_id="pub_c_04", platform="linkedin", views=1000, reach=1000, engagements=50,
                captured_at=pub_ctrl.published_at + timedelta(hours=24)
            )
            snap_t = PostMetricSnapshot(
                id="snap_t_04", publication_id="pub_t_04", platform="linkedin", views=1000, reach=1000, engagements=80,
                captured_at=pub_treat.published_at + timedelta(hours=5)
            )
            session.add_all([snap_c, snap_t])
            await session.commit()

        async with async_session_factory() as session:
            exp = await experiment_service.create_experiment(
                db=session,
                name="Test Age Mismatch",
                hypothesis="Statistic hooks perform better",
                platform="linkedin",
                primary_metric="engagement_rate",
                scope="HOOK",
                control_content_id="c_test_04",
                treatment_content_id="c_test_04",
                control_publication_id="pub_c_04",
                treatment_publication_id="pub_t_04",
                evaluation_window_hours=24
            )
            exp.status = "RUNNING"
            await session.commit()

            # Evaluate
            res = await experiment_service.evaluate_experiment(session, exp.id)
            # Should not conclude since treatment is pending (age < 24 hours)
            self.assertEqual(res["status"], "collecting_data")
            
            # Reload experiment
            db_exp = await session.get(Experiment, exp.id)
            self.assertNotEqual(db_exp.status, "COMPLETED")
            self.assertIsNone(db_exp.winner_variant_id)

    async def test_05_insufficient_data(self):
        """Verifies that an experiment under the minimum sample size gets the INSUFFICIENT_DATA status."""
        async with async_session_factory() as session:
            c = Content(id="c_test_05", title="Source Content", content_type="VIDEO", status="READY")
            # Only 1 publication for control and 1 for treatment (total 2 < minimum_sample_size 5)
            pub_ctrl = Publication(id="pub_c_05", content_id="c_test_05", title="Ctrl 05", platform="linkedin", status="PUBLISHED", published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash="h1")
            pub_treat = Publication(id="pub_t_05", content_id="c_test_05", title="Treat 05", platform="linkedin", status="PUBLISHED", published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash="h2")
            session.add_all([c, pub_ctrl, pub_treat])

            snap_c = PostMetricSnapshot(id="snap_c_05", publication_id="pub_c_05", platform="linkedin", views=100, reach=100, engagements=5, captured_at=pub_ctrl.published_at + timedelta(hours=24))
            snap_t = PostMetricSnapshot(id="snap_t_05", publication_id="pub_t_05", platform="linkedin", views=100, reach=100, engagements=8, captured_at=pub_treat.published_at + timedelta(hours=24))
            session.add_all([snap_c, snap_t])
            await session.commit()

        async with async_session_factory() as session:
            exp = await experiment_service.create_experiment(
                db=session,
                name="Test Insufficient Samples",
                hypothesis="Should show insufficient data",
                platform="linkedin",
                primary_metric="engagement_rate",
                scope="HOOK",
                control_content_id="c_test_05",
                treatment_content_id="c_test_05",
                control_publication_id="pub_c_05",
                treatment_publication_id="pub_t_05",
                minimum_sample_size=5,
                evaluation_window_hours=24
            )
            exp.status = "RUNNING"
            await session.commit()

            res = await experiment_service.evaluate_experiment(session, exp.id)
            self.assertEqual(res["status"], "insufficient_data")

            # Reload to check status in db
            db_exp = await session.get(Experiment, exp.id)
            self.assertEqual(db_exp.status, "INSUFFICIENT_DATA")

    async def test_06_zero_baseline_handling(self):
        """Verifies that if the control baseline is zero, relative effect is represented as None/unavailable."""
        res = experiment_service.calculate_rate_z_test(
            ctrl_successes=0, ctrl_trials=100,
            treat_successes=5, treat_trials=100
        )
        self.assertEqual(res["effect_size_absolute"], 0.05)
        self.assertIsNone(res["effect_size_relative"])

    async def test_07_statistical_significance_and_winner(self):
        """Creates synthetic aligned publications and verifies Z-test statistical significance and winner logic."""
        async with async_session_factory() as session:
            c = Content(id="c_test_07", title="Source Content", content_type="VIDEO", status="READY")
            session.add(c)

            # We create 3 publications for control and 3 for treatment (total 6 >= minimum_sample_size 5)
            # Treatment has a massive success rate (e.g. 50/100) vs Control (e.g. 5/100)
            for i in range(3):
                pc = Publication(
                    id=f"pub_ctrl_{i}", content_id="c_test_07", title="Ctrl", platform="linkedin", status="PUBLISHED",
                    published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash=f"hc_{i}"
                )
                pt = Publication(
                    id=f"pub_treat_{i}", content_id="c_test_07", title="Treat", platform="linkedin", status="PUBLISHED",
                    published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash=f"ht_{i}"
                )
                session.add_all([pc, pt])

                sc = PostMetricSnapshot(
                    id=f"snap_ctrl_{i}", publication_id=f"pub_ctrl_{i}", platform="linkedin", views=100, reach=100, engagements=5,
                    captured_at=pc.published_at + timedelta(hours=24)
                )
                st = PostMetricSnapshot(
                    id=f"snap_treat_{i}", publication_id=f"pub_treat_{i}", platform="linkedin", views=100, reach=100, engagements=50,
                    captured_at=pt.published_at + timedelta(hours=24)
                )
                session.add_all([sc, st])

            await session.commit()

        async with async_session_factory() as session:
            exp = await experiment_service.create_experiment(
                db=session,
                name="Significant Hook Test",
                hypothesis="Statistic hooks outperform direct claim hooks",
                platform="linkedin",
                primary_metric="engagement_rate",
                scope="HOOK",
                control_content_id="c_test_07",
                treatment_content_id="c_test_07",
                minimum_sample_size=5,
                evaluation_window_hours=24
            )
            # Bind publications to variants manually for multi-post aggregations
            from sqlalchemy.orm import selectinload
            res_exp = await session.execute(
                select(Experiment)
                .where(Experiment.id == exp.id)
                .options(selectinload(Experiment.variants))
            )
            exp = res_exp.scalar_one()
            variants = exp.variants
            ctrl_var = next(v for v in variants if v.role == "CONTROL")
            treat_var = next(v for v in variants if v.role == "TREATMENT")

            ctrl_var.content_variant_id = "v_control"
            treat_var.content_variant_id = "v_treatment"

            # Update publications
            for i in range(3):
                pub_c = await session.get(Publication, f"pub_ctrl_{i}")
                pub_c.variant_id = "v_control"
                pub_t = await session.get(Publication, f"pub_treat_{i}")
                pub_t.variant_id = "v_treatment"

            exp.status = "RUNNING"
            await session.commit()

            # Evaluate
            eval_res = await experiment_service.evaluate_experiment(session, exp.id)
            self.assertEqual(eval_res["status"], "completed")
            self.assertEqual(eval_res["conclusion"], "VARIANT_B_WINS") # Treatment wins!

            # Verification of scorecard results
            db_exp = await session.get(Experiment, exp.id)
            self.assertEqual(db_exp.status, "COMPLETED")
            self.assertEqual(db_exp.conclusion, "VARIANT_B_WINS")
            self.assertIsNotNone(db_exp.winner_variant_id)

    async def test_08_outlier_resistance(self):
        """Verifies that trimmed medians prevent viral outliers from falsely driving winner declarations."""
        async with async_session_factory() as session:
            c = Content(id="c_test_08", title="Source Content", content_type="VIDEO", status="READY")
            session.add(c)

            for i in range(5):
                pc = Publication(id=f"pub_ctrl_out_{i}", content_id="c_test_08", title="Ctrl", variant_id="v_ctrl_out", platform="linkedin", status="PUBLISHED", published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash=f"hco_{i}")
                pt = Publication(id=f"pub_treat_out_{i}", content_id="c_test_08", title="Treat", variant_id="v_treat_out", platform="linkedin", status="PUBLISHED", published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash=f"hto_{i}")
                session.add_all([pc, pt])

                # Control views = 1000 uniformly
                sc = PostMetricSnapshot(id=f"snap_ctrl_out_{i}", publication_id=f"pub_ctrl_out_{i}", platform="linkedin", views=1000, reach=1000, engagements=50, captured_at=pc.published_at + timedelta(hours=24))
                # Treatment views = 1000 uniformly except i=0 which is 1000000 (viral outlier)
                views_cnt = 1000000 if i == 0 else 1000
                st = PostMetricSnapshot(id=f"snap_treat_out_{i}", publication_id=f"pub_treat_out_{i}", platform="linkedin", views=views_cnt, reach=views_cnt, engagements=50, captured_at=pt.published_at + timedelta(hours=24))
                session.add_all([sc, st])

            await session.commit()

        async with async_session_factory() as session:
            exp = await experiment_service.create_experiment(
                db=session,
                name="Outlier Resistant Test",
                hypothesis="Should not declare treatment a winner because views difference is purely driven by one outlier post",
                platform="linkedin",
                primary_metric="views",
                scope="HOOK",
                control_content_id="c_test_08",
                treatment_content_id="c_test_08",
                minimum_sample_size=5,
                evaluation_window_hours=24
            )
            # Map variants
            from sqlalchemy.orm import selectinload
            res_exp = await session.execute(
                select(Experiment)
                .where(Experiment.id == exp.id)
                .options(selectinload(Experiment.variants))
            )
            exp = res_exp.scalar_one()
            for v in exp.variants:
                if v.role == "CONTROL": v.content_variant_id = "v_ctrl_out"
                if v.role == "TREATMENT": v.content_variant_id = "v_treat_out"
            
            exp.status = "RUNNING"
            await session.commit()

            eval_res = await experiment_service.evaluate_experiment(session, exp.id)
            # Median/Trimmed values should be equal (1000 vs 1000), yielding NO CLEAR WINNER
            self.assertEqual(eval_res["conclusion"], "NO_CLEAR_WINNER")

    async def test_09_posting_confound_warning(self):
        """Verifies confound warnings for mismatched posting times."""
        async with async_session_factory() as session:
            c = Content(id="c_test_09", title="Source Content", content_type="VIDEO", status="READY")
            # Control posted 5 days ago, Treatment posted 1 hour ago
            pub_ctrl = Publication(
                id="pub_c_09", content_id="c_test_09", title="Ctrl", platform="linkedin", status="PUBLISHED",
                published_at=datetime.utcnow() - timedelta(days=5), request_payload_hash="h1"
            )
            pub_treat = Publication(
                id="pub_t_09", content_id="c_test_09", title="Treat", platform="linkedin", status="PUBLISHED",
                published_at=datetime.utcnow() - timedelta(hours=1), request_payload_hash="h2"
            )
            session.add_all([c, pub_ctrl, pub_treat])
            await session.commit()

        async with async_session_factory() as session:
            exp = await experiment_service.create_experiment(
                db=session,
                name="Time Confound Test",
                hypothesis="Will generate warning",
                platform="linkedin",
                primary_metric="engagement_rate",
                scope="HOOK",
                control_content_id="c_test_09",
                treatment_content_id="c_test_09",
                control_publication_id="pub_c_09",
                treatment_publication_id="pub_t_09"
            )
            warnings = await experiment_service.detect_confounds(session, exp)
            self.assertTrue(any(w["code"] == "POSTING_TIME_MISMATCH" for w in warnings))

    async def test_10_ownership_security(self):
        """Verifies 403 authorization boundary for different user identities."""
        from httpx import AsyncClient, ASGITransport
        from main import app

        async with async_session_factory() as session:
            c = Content(id="c_test_10", title="Source Content", content_type="VIDEO", status="READY")
            session.add(c)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Create as user "alice"
            res = await ac.post("/api/experiments", json={
                "name": "Alice's Experiment",
                "hypothesis": "Alice's hook test is better",
                "platform": "linkedin",
                "scope": "HOOK",
                "control_content_id": "c_test_10",
                "treatment_content_id": "c_test_10"
            }, headers={"X-User-Id": "alice"})
            if res.status_code != 200:
                print(f"FAILED CREATE RESPONSE: {res.status_code} - {res.text}")
            self.assertEqual(res.status_code, 200)
            exp_id = res.json()["experiment"]["id"]

            # Try to read as "bob" -> must return 403
            res_bob = await ac.get(f"/api/experiments/{exp_id}", headers={"X-User-Id": "bob"})
            self.assertEqual(res_bob.status_code, 403)

            # Try to read as "alice" -> must succeed
            res_alice = await ac.get(f"/api/experiments/{exp_id}", headers={"X-User-Id": "alice"})
            self.assertEqual(res_alice.status_code, 200)

    async def test_11_closed_loop_feedback_loop(self):
        """Verifies that completed experiment results feed back to recommendations and update confidence levels."""
        async with async_session_factory() as session:
            c = Content(id="c_test_11", title="Source Content", content_type="VIDEO", status="READY")
            session.add(c)

            # Recommendation & Pattern
            rec = ContentRecommendation(
                id="rec_test_11", type="BEST_HOOK", scope="ACCOUNT", title="Statistic hooks recommend",
                recommendation_text="Use statistics", why_text="Because stats", confidence="MEDIUM"
            )
            pat = ContentPattern(
                id="pat_test_11", pattern_type="HOOK", feature_name="hook_type", feature_value="STATISTIC",
                correlation_ratio=1.2, sample_size=5
            )
            session.add_all([rec, pat])

            # Publications & Snapshots matching high performance for Treatment (v_treat_11)
            for i in range(3):
                pc = Publication(id=f"pub_ctrl_11_{i}", content_id="c_test_11", title="Ctrl", variant_id="v_ctrl_11", platform="linkedin", status="PUBLISHED", published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash=f"hc11_{i}")
                pt = Publication(id=f"pub_treat_11_{i}", content_id="c_test_11", title="Treat", variant_id="v_treat_11", platform="linkedin", status="PUBLISHED", published_at=datetime.utcnow() - timedelta(hours=36), request_payload_hash=f"ht11_{i}")
                session.add_all([pc, pt])

                sc = PostMetricSnapshot(id=f"snap_ctrl_11_{i}", publication_id=f"pub_ctrl_11_{i}", platform="linkedin", views=100, reach=100, engagements=5, captured_at=pc.published_at + timedelta(hours=24))
                st = PostMetricSnapshot(id=f"snap_treat_11_{i}", publication_id=f"pub_treat_11_{i}", platform="linkedin", views=100, reach=100, engagements=60, captured_at=pt.published_at + timedelta(hours=24))
                session.add_all([sc, st])

            await session.commit()

        async with async_session_factory() as session:
            exp = await experiment_service.create_experiment(
                db=session,
                name="Closed Loop Test",
                hypothesis="Stats hooks work better",
                platform="linkedin",
                primary_metric="engagement_rate",
                scope="HOOK",
                control_content_id="c_test_11",
                treatment_content_id="c_test_11",
                minimum_sample_size=5,
                evaluation_window_hours=24,
                recommendation_id="rec_test_11"
            )
            from sqlalchemy.orm import selectinload
            res_exp = await session.execute(
                select(Experiment)
                .where(Experiment.id == exp.id)
                .options(selectinload(Experiment.variants))
            )
            exp = res_exp.scalar_one()
            for v in exp.variants:
                if v.role == "CONTROL": v.content_variant_id = "v_ctrl_11"
                if v.role == "TREATMENT": v.content_variant_id = "v_treat_11"
            
            exp.status = "RUNNING"
            await session.commit()

            # Evaluate (should complete and declare Treatment B as winner)
            await experiment_service.evaluate_experiment(session, exp.id)

            # Check that recommendation confidence was bumped to HIGH in closed-loop feedback
            db_rec = await session.get(ContentRecommendation, "rec_test_11")
            self.assertEqual(db_rec.confidence, "HIGH")

            # Check pattern correlation ratio got boosted
            db_pat = await session.get(ContentPattern, "pat_test_11")
            self.assertGreater(db_pat.correlation_ratio, 1.2)

if __name__ == "__main__":
    unittest.main()
