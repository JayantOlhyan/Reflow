import sys
import os
import unittest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from database import init_db, async_session_factory
from models.entities import (
    AutomationRule, AutomationExecution, AutomationActionExecution,
    Content, Publication, PlatformConnection, Job
)
from services.event_bus import event_bus_service
from services.automation_service import automation_service

sys.path.append(os.path.dirname(__file__))

class TestAutomationEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        async with async_session_factory() as session:
            # Clean database tables
            await session.execute(delete(AutomationActionExecution))
            await session.execute(delete(AutomationExecution))
            await session.execute(delete(AutomationRule))
            await session.execute(delete(Publication))
            await session.execute(delete(PlatformConnection))
            await session.execute(delete(Content))
            await session.execute(delete(Job))
            await session.commit()

    async def test_01_create_rule_persistence(self):
        """Verifies that an automation rule is successfully persisted in the database."""
        async with async_session_factory() as session:
            rule_id = f"rule_{uuid.uuid4().hex[:8]}"
            rule = AutomationRule(
                id=rule_id,
                name="Test Rule 01",
                description="Trigger on content ready",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                cooldown_minutes=60,
                max_runs_per_day=5,
                status="ACTIVE",
                created_by="user_abc"
            )
            rule.conditions = [{"field": "content_type", "operator": "==", "value": "VIDEO"}]
            rule.actions = [{"type": "SEND_NOTIFICATION", "message": "Hi"}]
            session.add(rule)
            await session.commit()

        async with async_session_factory() as session:
            db_rule = await session.get(AutomationRule, rule_id)
            self.assertIsNotNone(db_rule)
            self.assertEqual(db_rule.name, "Test Rule 01")
            self.assertEqual(len(db_rule.conditions), 1)
            self.assertEqual(db_rule.conditions[0]["field"], "content_type")
            self.assertEqual(len(db_rule.actions), 1)
            self.assertEqual(db_rule.actions[0]["type"], "SEND_NOTIFICATION")

    async def test_02_event_dispatch_queued(self):
        """Verifies that dispatching an event creates an execution and action execution in QUEUED state."""
        async with async_session_factory() as session:
            # Set up rule
            rule = AutomationRule(
                id="rule_02",
                name="Clip Generator",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                cooldown_minutes=60,
                max_runs_per_day=5,
                status="ACTIVE"
            )
            rule.conditions = [{"field": "content_type", "operator": "==", "value": "VIDEO"}]
            rule.actions = [{"type": "SEND_NOTIFICATION", "message": "Content ready notification"}]
            
            # Set up matching Content
            c = Content(id="content_02", title="Test Video", content_type="VIDEO", status="READY")
            
            session.add_all([rule, c])
            await session.commit()

        async with async_session_factory() as session:
            # Dispatch event
            exec_ids = await event_bus_service.dispatch_event("content.ready", "content_02", session)
            self.assertEqual(len(exec_ids), 1)

        async with async_session_factory() as session:
            # Check execution
            res = await session.execute(
                select(AutomationExecution)
                .where(AutomationExecution.id == exec_ids[0])
                .options(selectinload(AutomationExecution.action_executions))
            )
            execution = res.scalar_one_or_none()
            self.assertIsNotNone(execution)
            self.assertEqual(execution.status, "QUEUED")
            self.assertEqual(len(execution.action_executions), 1)
            self.assertEqual(execution.action_executions[0].status, "QUEUED")
            self.assertEqual(execution.action_executions[0].action_type, "SEND_NOTIFICATION")

    async def test_03_conditions_matching_and_skipping(self):
        """Verifies that conditions are evaluated correctly, skipping mismatching content type triggers."""
        async with async_session_factory() as session:
            rule = AutomationRule(
                id="rule_03",
                name="Video Only Rule",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                cooldown_minutes=60,
                max_runs_per_day=5,
                status="ACTIVE"
            )
            rule.conditions = [{"field": "content_type", "operator": "==", "value": "VIDEO"}]
            rule.actions = [{"type": "SEND_NOTIFICATION"}]
            
            # Mismatching Content: TEXT type
            c = Content(id="content_03", title="Text note", content_type="TEXT", status="READY")
            session.add_all([rule, c])
            await session.commit()

        async with async_session_factory() as session:
            exec_ids = await event_bus_service.dispatch_event("content.ready", "content_03", session)
            # SKIPPED: Condition check failed
            self.assertEqual(len(exec_ids), 1)

        async with async_session_factory() as session:
            execution = await session.get(AutomationExecution, exec_ids[0])
            self.assertEqual(execution.status, "SKIPPED")
            self.assertIn("CONDITION_FAILED", execution.error)

    async def test_04_idempotency_guard(self):
        """Verifies that triggering the same rule with the same entity id twice is blocked by idempotency."""
        async with async_session_factory() as session:
            rule = AutomationRule(
                id="rule_04",
                name="Idempotency rule",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                status="ACTIVE"
            )
            rule.actions = [{"type": "SEND_NOTIFICATION"}]
            c = Content(id="content_04", title="Video", content_type="VIDEO")
            session.add_all([rule, c])
            await session.commit()

        async with async_session_factory() as session:
            # 1st dispatch
            exec_ids_1 = await event_bus_service.dispatch_event("content.ready", "content_04", session)
            self.assertEqual(len(exec_ids_1), 1)

            # 2nd dispatch (should be skipped due to duplicate execution key)
            exec_ids_2 = await event_bus_service.dispatch_event("content.ready", "content_04", session)
            self.assertEqual(len(exec_ids_2), 0)

    async def test_05_safety_limit_daily_and_cooldown(self):
        """Verifies that rule execution triggers are blocked by daily run counts or cooldown limits."""
        async with async_session_factory() as session:
            rule = AutomationRule(
                id="rule_05",
                name="Rate limit rule",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                cooldown_minutes=15,
                max_runs_per_day=1, # strictly limit to 1 run
                status="ACTIVE",
                last_run_at=datetime.utcnow() - timedelta(minutes=5) # currently in cooldown
            )
            rule.actions = [{"type": "SEND_NOTIFICATION"}]
            c = Content(id="content_05", title="Video", content_type="VIDEO")
            session.add_all([rule, c])
            await session.commit()

        async with async_session_factory() as session:
            exec_ids = await event_bus_service.dispatch_event("content.ready", "content_05", session)
            self.assertEqual(len(exec_ids), 1)

        async with async_session_factory() as session:
            execution = await session.get(AutomationExecution, exec_ids[0])
            self.assertEqual(execution.status, "SKIPPED")
            self.assertIn("COOLDOWN_LIMIT", execution.error)

    async def test_06_permanent_failure_isolation(self):
        """Verifies that expired credentials raise permanent error, mark action BLOCKED, and pause the rule."""
        async with async_session_factory() as session:
            rule = AutomationRule(
                id="rule_06",
                name="Publishing rule",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                status="ACTIVE"
            )
            rule.actions = [{"type": "PUBLISH", "platform": "youtube", "platform_connection_id": "conn_bad"}]
            
            conn = PlatformConnection(
                id="conn_bad",
                platform="youtube",
                name="Test Connection",
                status="EXPIRED", # Expired connection!
                token_expires_at=datetime.utcnow() - timedelta(hours=1)
            )
            
            c = Content(id="content_06", title="Video", content_type="VIDEO")
            
            session.add_all([rule, conn, c])
            await session.commit()

        # Run manually to verify failure propagation
        async with async_session_factory() as session:
            exec_id = f"exec_06"
            execution = AutomationExecution(
                id=exec_id,
                automation_id="rule_06",
                trigger_event="content.ready",
                trigger_entity_id="content_06",
                status="QUEUED",
                execution_key="key_06"
            )
            act_exec = AutomationActionExecution(
                id="act_06",
                execution_id=exec_id,
                action_type="PUBLISH",
                status="QUEUED"
            )
            session.add_all([execution, act_exec])
            await session.commit()

        async with async_session_factory() as session:
            success = await automation_service.execute_execution_pipeline(session, exec_id)
            self.assertFalse(success)

        async with async_session_factory() as session:
            # Check status of action execution and rule
            db_act = await session.get(AutomationActionExecution, "act_06")
            self.assertEqual(db_act.status, "BLOCKED")
            self.assertIn("expired", db_act.error.lower())

            db_rule = await session.get(AutomationRule, "rule_06")
            self.assertEqual(db_rule.status, "ERROR")
            self.assertIn("permanent connection error", db_rule.description)

    async def test_07_partial_failure_isolation(self):
        """Verifies that if action A succeeds but action B fails, action A is not rolled back."""
        async with async_session_factory() as session:
            rule = AutomationRule(
                id="rule_07",
                name="Split actions rule",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                status="ACTIVE"
            )
            # Action 1: Send notification (will succeed)
            # Action 2: Publish with bad connection (will fail)
            rule.actions = [
                {"type": "SEND_NOTIFICATION", "message": "Success notification"},
                {"type": "PUBLISH", "platform": "youtube", "platform_connection_id": "conn_missing"}
            ]
            c = Content(id="content_07", title="Video", content_type="VIDEO")
            session.add_all([rule, c])
            await session.commit()

        async with async_session_factory() as session:
            exec_id = "exec_07"
            execution = AutomationExecution(
                id=exec_id,
                automation_id="rule_07",
                trigger_event="content.ready",
                trigger_entity_id="content_07",
                status="QUEUED",
                execution_key="key_07"
            )
            ae1 = AutomationActionExecution(id="act_07_1", execution_id=exec_id, action_type="SEND_NOTIFICATION", status="QUEUED")
            ae2 = AutomationActionExecution(id="act_07_2", execution_id=exec_id, action_type="PUBLISH", status="QUEUED")
            session.add_all([execution, ae1, ae2])
            await session.commit()

        async with async_session_factory() as session:
            await automation_service.execute_execution_pipeline(session, exec_id)

        async with async_session_factory() as session:
            db_ae1 = await session.get(AutomationActionExecution, "act_07_1")
            db_ae2 = await session.get(AutomationActionExecution, "act_07_2")
            
            # Action 1 remains SUCCEEDED
            self.assertEqual(db_ae1.status, "SUCCEEDED")
            # Action 2 is BLOCKED (due to missing connection error)
            self.assertEqual(db_ae2.status, "BLOCKED")

    async def test_08_approval_gate_blocks(self):
        """Verifies that actions requiring approval transition to WAITING_APPROVAL state."""
        async with async_session_factory() as session:
            rule = AutomationRule(
                id="rule_08",
                name="Approval rule",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="REQUIRE_APPROVAL", # Scope enforces approval gate
                status="ACTIVE"
            )
            rule.actions = [{"type": "PUBLISH", "platform": "linkedin"}]
            c = Content(id="content_08", title="Video", content_type="VIDEO")
            session.add_all([rule, c])
            await session.commit()

        async with async_session_factory() as session:
            exec_id = "exec_08"
            execution = AutomationExecution(
                id=exec_id,
                automation_id="rule_08",
                trigger_event="content.ready",
                trigger_entity_id="content_08",
                status="QUEUED",
                execution_key="key_08"
            )
            act_exec = AutomationActionExecution(
                id="act_08",
                execution_id=exec_id,
                action_type="PUBLISH",
                status="QUEUED"
            )
            session.add_all([execution, act_exec])
            await session.commit()

        async with async_session_factory() as session:
            await automation_service.execute_execution_pipeline(session, exec_id)

        async with async_session_factory() as session:
            db_act = await session.get(AutomationActionExecution, "act_08")
            db_exec = await session.get(AutomationExecution, exec_id)
            
            # Action is held in WAITING_APPROVAL
            self.assertEqual(db_act.status, "WAITING_APPROVAL")
            self.assertEqual(db_exec.status, "WAITING")

    async def test_09_dry_run_preview(self):
        """Verifies dry run preview resolves action counts without mutations."""
        # Setup DB Rule
        async with async_session_factory() as session:
            rule = AutomationRule(
                id="rule_09",
                name="Dry run rule",
                enabled=True,
                trigger_type="CONTENT_READY",
                scope="AUTO_APPROVE",
                status="ACTIVE"
            )
            rule.conditions = [{"field": "content_type", "operator": "==", "value": "VIDEO"}]
            rule.actions = [{"type": "GENERATE_CLIPS"}, {"type": "SEND_NOTIFICATION"}]
            c = Content(id="content_09", title="Video", content_type="VIDEO")
            session.add_all([rule, c])
            await session.commit()

        # Execute dry-run directly on event bus service conditions helper
        async with async_session_factory() as session:
            event_type = event_bus_service.TRIGGER_EVENT_MAP.get(rule.trigger_type)
            entity = await session.get(Content, "content_09")
            
            passed, _ = event_bus_service.evaluate_conditions(entity, rule.conditions)
            self.assertTrue(passed)
            self.assertEqual(len(rule.actions), 2)
            
            # Verify no job or execution was created in database
            jobs_count = await session.execute(select(Job))
            self.assertEqual(len(jobs_count.scalars().all()), 0)
            
            execs_count = await session.execute(select(AutomationExecution))
            self.assertEqual(len(execs_count.scalars().all()), 0)
