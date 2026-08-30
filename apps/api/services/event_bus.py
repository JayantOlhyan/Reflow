import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.entities import (
    AutomationRule, AutomationExecution, AutomationActionExecution,
    Content, Clip, Carousel, Publication, Experiment, ContentRecommendation, Job
)
from services.queue_service import queue_service
from utils.logging import get_logger

logger = get_logger("EventBus")

class EventBusService:
    # Maps event types to canonical DB entity classes they relate to
    ENTITY_MAPPING = {
        "content.ready": Content,
        "clip.ready": Clip,
        "carousel.ready": Carousel,
        "content.approved": Content,
        "publication.succeeded": Publication,
        "publication.failed": Publication,
        "analytics.updated": Publication,
        "experiment.completed": Experiment,
        "recommendation.created": ContentRecommendation,
    }

    # Maps trigger types to event types
    TRIGGER_EVENT_MAP = {
        "CONTENT_READY": "content.ready",
        "CLIP_CREATED": "clip.ready",
        "CAROUSEL_READY": "carousel.ready",
        "CONTENT_APPROVED": "content.approved",
        "ANALYTICS_UPDATED": "analytics.updated",
        "EXPERIMENT_COMPLETED": "experiment.completed",
        "RECOMMENDATION_CREATED": "recommendation.created",
    }

    async def dispatch_event(self, event_type: str, entity_id: str, db: AsyncSession) -> List[str]:
        """
        Receives an internal event, resolves matching rules, evaluates conditions/safety limits,
        and enqueues asynchronous executions.
        """
        logger.info(f"Dispatched event: {event_type} on entity: {entity_id}")
        
        # 1. Fetch enabled rules corresponding to this event trigger
        trigger_types = [k for k, v in self.TRIGGER_EVENT_MAP.items() if v == event_type]
        if not trigger_types:
            logger.info(f"No trigger mapped for event: {event_type}")
            return []

        res = await db.execute(
            select(AutomationRule)
            .where(
                AutomationRule.enabled == True,
                AutomationRule.status == "ACTIVE",
                AutomationRule.trigger_type.in_(trigger_types)
            )
        )
        rules = res.scalars().all()
        if not rules:
            logger.info(f"No active rules found matching triggers {trigger_types}")
            return []

        execution_ids = []
        for rule in rules:
            try:
                exec_id = await self.process_rule_for_event(db, rule, event_type, entity_id)
                if exec_id:
                    execution_ids.append(exec_id)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id} for event {event_type}: {e}", exc_info=True)

        return execution_ids

    async def process_rule_for_event(self, db: AsyncSession, rule: AutomationRule, event_type: str, entity_id: str) -> Optional[str]:
        """Evaluates conditions, safety checks, and creates execution if passing."""
        # 1. Idempotency Check: (rule_id + trigger_entity_id) must be unique
        execution_key = f"{rule.id}:{entity_id}"
        
        dup_res = await db.execute(
            select(AutomationExecution).where(AutomationExecution.execution_key == execution_key)
        )
        existing = dup_res.scalar_one_or_none()
        if existing:
            logger.info(f"Skipping duplicate execution for key {execution_key}. Idempotency guard triggered.")
            return None

        # 2. Load the trigger entity to evaluate conditions
        entity_class = self.ENTITY_MAPPING.get(event_type)
        entity = None
        if entity_class:
            entity = await db.get(entity_class, entity_id)
            if not entity:
                logger.warning(f"Trigger entity {entity_id} ({entity_class.__name__}) not found in DB. Skipping.")
                return None

        # 3. Check Safety Limits: Cooldown
        now = datetime.utcnow()
        if rule.last_run_at:
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes or 0)
            if now - rule.last_run_at < cooldown_delta:
                logger.info(f"Rule {rule.id} skipped due to cooldown limit. Cooldown remaining.")
                return await self.record_skipped_execution(db, rule, event_type, entity_id, execution_key, "COOLDOWN_LIMIT")

        # 4. Check Safety Limits: Max Daily Runs
        start_of_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_runs_res = await db.execute(
            select(func.count(AutomationExecution.id))
            .where(
                AutomationExecution.automation_id == rule.id,
                AutomationExecution.created_at >= start_of_today,
                AutomationExecution.status != "SKIPPED"
            )
        )
        daily_count = daily_runs_res.scalar() or 0
        if daily_count >= (rule.max_runs_per_day or 5):
            logger.info(f"Rule {rule.id} skipped due to max daily runs limit ({daily_count}/{rule.max_runs_per_day}).")
            return await self.record_skipped_execution(db, rule, event_type, entity_id, execution_key, "DAILY_RUN_LIMIT")

        # 5. Evaluate Conditions
        conditions_passed, skip_reason = self.evaluate_conditions(entity, rule.conditions)
        if not conditions_passed:
            logger.info(f"Rule {rule.id} skipped: condition check failed ({skip_reason}).")
            return await self.record_skipped_execution(db, rule, event_type, entity_id, execution_key, f"CONDITION_FAILED: {skip_reason}")

        # 6. Safety Validation: Platfrom Connection check if publication related
        # (Will check credentials and connections in the service during execution, but let's record success trigger here)

        # 7. Create Execution & Action Executions records
        exec_id = f"exec_{uuid.uuid4().hex[:8]}"
        execution = AutomationExecution(
            id=exec_id,
            automation_id=rule.id,
            trigger_event=event_type,
            trigger_entity_id=entity_id,
            status="QUEUED",
            execution_key=execution_key,
            created_at=now
        )
        db.add(execution)

        rule.last_run_at = now
        rule.next_run_at = now + timedelta(minutes=rule.cooldown_minutes or 60)

        # Create child action executions
        actions = rule.actions
        for idx, act in enumerate(actions):
            act_exec = AutomationActionExecution(
                id=f"act_{uuid.uuid4().hex[:8]}",
                execution_id=exec_id,
                action_type=act.get("type", "UNKNOWN"),
                status="QUEUED",
                result_json="{}",
            )
            db.add(act_exec)

        await db.commit()

        # Enqueue background execution job
        job_id = f"job_auto_{uuid.uuid4().hex[:8]}"
        job = Job(
            id=job_id,
            type="AUTOMATION_EXECUTION",
            status="QUEUED",
            created_at=datetime.utcnow()
        )
        db.add(job)
        await db.commit()

        await queue_service.enqueue_media_job(
            job_id=job_id,
            job_type="AUTOMATION_EXECUTION",
            execution_id=exec_id
        )

        logger.info(f"Rule {rule.id} triggered. Created execution {exec_id} with job {job_id}.")
        return exec_id

    async def record_skipped_execution(self, db: AsyncSession, rule: AutomationRule, event_type: str, entity_id: str, execution_key: str, reason: str) -> str:
        """Helper to store skipped execution records for history transparency."""
        exec_id = f"exec_skip_{uuid.uuid4().hex[:8]}"
        execution = AutomationExecution(
            id=exec_id,
            automation_id=rule.id,
            trigger_event=event_type,
            trigger_entity_id=entity_id,
            status="SKIPPED",
            error=reason,
            execution_key=execution_key,
            completed_at=datetime.utcnow()
        )
        db.add(execution)
        await db.commit()
        return exec_id

    def evaluate_conditions(self, entity: Any, conditions: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """
        Dynamically compares properties of the trigger entity against conditions criteria.
        E.g. condition: {"field": "content_type", "operator": "==", "value": "VIDEO"}
        """
        if not conditions:
            return True, None

        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator", "==")
            expected = cond.get("value")

            if not field:
                continue

            # Retrieve attribute from entity or default to None
            val = getattr(entity, field, None)
            
            # If the trigger is Clip and we check content_type, resolve parent Content properties
            if val is None and hasattr(entity, "content"):
                parent_content = getattr(entity, "content", None)
                if parent_content:
                    val = getattr(parent_content, field, None)

            # Resolve duration bucketing helper if checking duration on Content
            if field == "duration" and val is None:
                # check if there is duration inside assets
                if hasattr(entity, "assets") and entity.assets:
                    val = next((a.duration for a in entity.assets if a.duration), None)
                elif hasattr(entity, "duration"):
                    val = entity.duration

            if val is None:
                return False, f"Missing field '{field}' on entity"

            # Normalize comparisons
            if isinstance(val, str) and isinstance(expected, str):
                val = val.upper()
                expected = expected.upper()

            # Compare operators
            if operator == "==":
                if val != expected:
                    return False, f"{field} value '{val}' != expected '{expected}'"
            elif operator == "!=":
                if val == expected:
                    return False, f"{field} value '{val}' == expected '{expected}'"
            elif operator == ">":
                try:
                    if float(val) <= float(expected):
                        return False, f"{field} value '{val}' <= expected '{expected}'"
                except:
                    return False, f"Cannot evaluate greater_than on non-numeric types"
            elif operator == "<":
                try:
                    if float(val) >= float(expected):
                        return False, f"{field} value '{val}' >= expected '{expected}'"
                except:
                    return False, f"Cannot evaluate less_than on non-numeric types"
            elif operator == "in":
                # Check list membership
                if isinstance(expected, list):
                    if val not in expected:
                        return False, f"{field} '{val}' not in list {expected}"
                elif isinstance(expected, str):
                    if val not in expected.split(","):
                        return False, f"{field} '{val}' not in list '{expected}'"
            else:
                return False, f"Unknown operator '{operator}'"

        return True, None

event_bus_service = EventBusService()
