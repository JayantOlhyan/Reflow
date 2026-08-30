import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.entities import (
    AutomationRule, AutomationExecution, AutomationActionExecution,
    Content, Clip, Carousel, Publication, Experiment, ContentRecommendation,
    PlatformConnection, Job
)
from services.ai_service import ai_service
from services.publishing_service import publishing_service
from services.experiment_service import experiment_service
from services.scheduler_service import scheduler_service
from services.queue_service import queue_service
from utils.logging import get_logger

logger = get_logger("AutomationService")

class AutomationService:

    async def execute_execution_pipeline(self, db: AsyncSession, execution_id: str) -> bool:
        """
        Executes the queued actions inside an AutomationExecution.
        Supports failure isolation, WAITING_APPROVAL blocks, and retry handling.
        """
        logger.info(f"Executing automation pipeline for run {execution_id}")
        
        # Load execution and rule
        res = await db.execute(
            select(AutomationExecution)
            .where(AutomationExecution.id == execution_id)
            .options(
                selectinload(AutomationExecution.action_executions),
                selectinload(AutomationExecution.rule)
            )
        )
        execution = res.scalar_one_or_none()
        if not execution:
            logger.error(f"AutomationExecution {execution_id} not found.")
            return False

        if execution.status in ["SUCCEEDED", "FAILED", "SKIPPED"]:
            logger.info(f"Execution {execution_id} is already in terminal state: {execution.status}")
            return True

        rule = execution.rule
        execution.status = "RUNNING"
        execution.started_at = datetime.utcnow()
        await db.commit()

        # Load actions config
        actions_config = rule.actions
        action_executions = execution.action_executions

        pipeline_failed = False
        approval_blocked = False

        for idx, act_config in enumerate(actions_config):
            act_type = act_config.get("type")
            # Find the matching action execution record
            act_exec = next((ae for ae in action_executions if ae.action_type == act_type), None)
            if not act_exec:
                # Fallback: create dynamically if missing
                act_exec = AutomationActionExecution(
                    id=f"act_{uuid.uuid4().hex[:8]}",
                    execution_id=execution.id,
                    action_type=act_type,
                    status="QUEUED",
                    result_json="{}"
                )
                db.add(act_exec)
                await db.commit()

            if act_exec.status == "SUCCEEDED":
                logger.info(f"Action {act_type} already succeeded. Skipping.")
                continue

            # Check if this action requires human-in-the-loop approval
            # E.g. Rule has global REQUIRE_APPROVAL, or action has require_approval=True
            require_approval = act_config.get("require_approval", False) or rule.scope == "REQUIRE_APPROVAL"
            if require_approval and act_exec.status != "APPROVED":
                # Mark WAITING_APPROVAL and block all downstream actions
                act_exec.status = "WAITING_APPROVAL"
                execution.status = "WAITING"
                execution.error = f"Action {act_type} requires approval before execution."
                await db.commit()
                logger.info(f"Action {act_type} blocked waiting for approval.")
                approval_blocked = True
                break

            # Execute the action
            act_exec.status = "RUNNING"
            act_exec.started_at = datetime.utcnow()
            await db.commit()

            try:
                result = await self.run_single_action(db, rule, execution, act_config)
                act_exec.status = "SUCCEEDED"
                act_exec.completed_at = datetime.utcnow()
                act_exec.result = result
                act_exec.error = None
                await db.commit()
                logger.info(f"Action {act_type} executed successfully.")
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Action {act_type} failed: {err_msg}", exc_info=True)
                
                # Check if transient, permanent or governance
                is_governance = "governance policy" in err_msg.lower() or "governance warnings" in err_msg.lower()
                is_permanent = any(phrase in err_msg.lower() for phrase in [
                    "credential", "unauthorized", "expired", "invalid", "scopes", "not found"
                ])

                act_exec.completed_at = datetime.utcnow()
                act_exec.error = err_msg

                if is_governance:
                    act_exec.status = "BLOCKED"
                    pipeline_failed = True
                    execution.error = f"Publishing blocked by governance policy: {err_msg}"
                    break
                elif is_permanent:
                    act_exec.status = "BLOCKED"
                    # Permanent credential failures pause the rule and set status to ERROR
                    rule.status = "ERROR"
                    rule.description = f"Paused due to permanent connection error: {err_msg}"
                    pipeline_failed = True
                    logger.warning(f"Connection/Auth failure: Paused rule {rule.id} to prevent endless retries.")
                    break
                else:
                    act_exec.status = "FAILED"
                    pipeline_failed = True
                    # Transient error, stop pipeline but do not delete rule status
                    break

        # Final Status Update
        if pipeline_failed:
            execution.status = "FAILED"
            execution.completed_at = datetime.utcnow()
        elif approval_blocked:
            execution.status = "WAITING"
        else:
            execution.status = "SUCCEEDED"
            execution.completed_at = datetime.utcnow()
            execution.error = None

        await db.commit()
        return not pipeline_failed

    async def run_single_action(self, db: AsyncSession, rule: AutomationRule, execution: AutomationExecution, act_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single action backed by Reflow core service layers.
        """
        act_type = act_config.get("type")
        entity_id = execution.trigger_entity_id
        logger.info(f"Executing action type '{act_type}' for entity '{entity_id}'")

        if act_type == "GENERATE_CLIPS":
            # Call ai_service clip discovery
            # Ensure entity is a Content object
            content = await db.get(Content, entity_id)
            if not content:
                raise ValueError(f"Content {entity_id} not found.")
            
            logger.info(f"Running automated clip discovery for content: {entity_id}")
            clips = await ai_service.discover_and_persist_clips(
                content_id=entity_id,
                min_duration=act_config.get("min_duration", 15.0),
                max_duration=act_config.get("max_duration", 90.0),
                target_count=act_config.get("target_count", 5),
                force_refresh=True
            )
            
            # Enqueue rendering for discovered clips
            rendered_jobs = []
            for clip in clips:
                job_id = f"job_clip_{uuid.uuid4().hex[:8]}"
                render_job = Job(
                    id=job_id,
                    content_id=entity_id,
                    type="CLIP_RENDER",
                    status="QUEUED",
                    created_at=datetime.utcnow()
                )
                db.add(render_job)
                await db.commit()

                await queue_service.enqueue_media_job(
                    job_id=job_id,
                    content_id=entity_id,
                    job_type="CLIP_RENDER",
                    clip_id=clip.id,
                    aspect_ratios=act_config.get("aspect_ratios", ["9:16"]),
                    include_thumbnail=True,
                    burn_captions=act_config.get("burn_captions", False),
                    caption_style=act_config.get("caption_style")
                )
                rendered_jobs.append(job_id)

            return {"clips_discovered": len(clips), "rendered_jobs": rendered_jobs}

        elif act_type == "GENERATE_CAROUSEL":
            # Create a Carousel record and enqueue generation job
            content = await db.get(Content, entity_id)
            if not content:
                raise ValueError(f"Content {entity_id} not found.")

            carousel_id = f"crsl_{uuid.uuid4().hex[:8]}"
            carousel = Carousel(
                id=carousel_id,
                content_id=entity_id,
                title=f"Auto Carousel: {content.title}",
                status="PROCESSING",
                template=act_config.get("template", "MINIMAL")
            )
            db.add(carousel)
            await db.commit()

            # Enqueue CAROUSEL_GENERATION
            job_id = f"job_crsl_{uuid.uuid4().hex[:8]}"
            gen_job = Job(
                id=job_id,
                content_id=entity_id,
                type="CAROUSEL_GENERATION",
                status="QUEUED",
                created_at=datetime.utcnow()
            )
            db.add(gen_job)
            await db.commit()

            await queue_service.enqueue_media_job(
                job_id=job_id,
                content_id=entity_id,
                job_type="CAROUSEL_GENERATION",
                carousel_id=carousel_id,
                slide_count=act_config.get("slide_count", 5),
                template=act_config.get("template", "MINIMAL"),
                tone=act_config.get("tone", "informative")
            )

            return {"carousel_id": carousel_id, "generation_job": job_id}

        elif act_type == "GENERATE_PLATFORM_COPY":
            # Triggers generating captions/platform descriptions
            await ai_service.generate_platform_content(
                content_id=entity_id,
                platforms=act_config.get("platforms", ["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"])
            )
            return {"status": "copy_generation_triggered"}

        elif act_type == "SCHEDULE_PUBLICATION":
            # Governance / Quality Control validation gate
            from services.quality_control_service import quality_control_service
            platform = act_config.get("platform", "linkedin")
            qc_result = await quality_control_service.run_pipeline(
                session=db,
                content_id=entity_id,
                platform=platform
            )
            if qc_result["status"] == "BLOCKED":
                raise ValueError("Publishing blocked by governance policy.")

            # Automate scheduling
            content = await db.get(Content, entity_id)
            if not content:
                raise ValueError(f"Content {entity_id} not found.")

            # Resolve connection and details
            conn_id = act_config.get("platform_connection_id")
            platform = act_config.get("platform", "linkedin")

            if not conn_id:
                # Find first active connection for this platform
                res_conn = await db.execute(
                    select(PlatformConnection)
                    .where(PlatformConnection.platform == platform, PlatformConnection.status == "CONNECTED")
                )
                conn = res_conn.scalars().first()
                if not conn:
                    raise ValueError(f"No active connection found for platform: {platform}")
                conn_id = conn.id

            # Verify connection health
            await self.verify_platform_connection(db, conn_id)

            # Global Rate & Interval Safety Checks
            await self.check_global_safety_limits(db, platform)

            # Duplicate Publish Check
            await self.check_duplicate_publication(db, entity_id, platform)

            # Check content routing compatibility matrix
            self.route_content_capability(content.content_type, platform)

            # Create publication
            pub_id = f"pub_{uuid.uuid4().hex[:6]}"
            pub = Publication(
                id=pub_id,
                content_id=entity_id,
                platform_connection_id=conn_id,
                platform=platform,
                title=content.title,
                description=content.text_content or "",
                privacy="PRIVATE",
                status="SCHEDULED",
                scheduled_at=datetime.utcnow() + timedelta(hours=act_config.get("delay_hours", 2)),
                timezone=act_config.get("timezone", "UTC")
            )
            db.add(pub)
            await db.commit()

            return {"publication_id": pub_id, "scheduled_at": pub.scheduled_at.isoformat()}

        elif act_type == "PUBLISH":
            # Governance / Quality Control validation gate
            from services.quality_control_service import quality_control_service
            platform = act_config.get("platform", "linkedin")
            qc_result = await quality_control_service.run_pipeline(
                session=db,
                content_id=entity_id,
                platform=platform
            )
            if qc_result["status"] == "BLOCKED":
                raise ValueError("Publishing blocked by governance policy.")

            # Immediate publication
            content = await db.get(Content, entity_id)
            if not content:
                raise ValueError(f"Content {entity_id} not found.")

            conn_id = act_config.get("platform_connection_id")
            platform = act_config.get("platform", "linkedin")

            if not conn_id:
                res_conn = await db.execute(
                    select(PlatformConnection)
                    .where(PlatformConnection.platform == platform, PlatformConnection.status == "CONNECTED")
                )
                conn = res_conn.scalars().first()
                if not conn:
                    raise ValueError(f"No active connection found for platform: {platform}")
                conn_id = conn.id

            # Verify connection health
            await self.verify_platform_connection(db, conn_id)

            # Global safety check
            await self.check_global_safety_limits(db, platform)

            # Duplicate post check
            await self.check_duplicate_publication(db, entity_id, platform)

            # Content routing check
            self.route_content_capability(content.content_type, platform)

            # Create publication in QUEUED status
            pub_id = f"pub_{uuid.uuid4().hex[:6]}"
            pub = Publication(
                id=pub_id,
                content_id=entity_id,
                platform_connection_id=conn_id,
                platform=platform,
                title=content.title,
                description=content.text_content or "",
                privacy="PRIVATE",
                status="QUEUED",
                published_at=datetime.utcnow()
            )
            db.add(pub)
            await db.commit()

            # Enqueue PLATFORM_PUBLISH job
            job_id = f"job_sch_{uuid.uuid4().hex[:8]}"
            job = Job(
                id=job_id,
                content_id=entity_id,
                type="PLATFORM_PUBLISH",
                status="QUEUED",
                created_at=datetime.utcnow()
            )
            db.add(job)
            await db.commit()

            await queue_service.enqueue_media_job(
                job_id=job_id,
                content_id=entity_id,
                job_type="PLATFORM_PUBLISH",
                publication_id=pub_id
            )

            return {"publication_id": pub_id, "job_id": job_id}

        elif act_type == "CREATE_EXPERIMENT":
            # Automate experiment setup
            exp = await experiment_service.create_experiment(
                db=db,
                name=act_config.get("name", f"Auto Experiment {uuid.uuid4().hex[:4]}"),
                hypothesis=act_config.get("hypothesis", "Tested variant performs better."),
                platform=act_config.get("platform", "linkedin"),
                primary_metric=act_config.get("primary_metric", "engagement_rate"),
                scope=act_config.get("scope", "HOOK"),
                control_content_id=entity_id,
                treatment_content_id=entity_id,
                minimum_sample_size=act_config.get("minimum_sample_size", 5),
                confidence_level=act_config.get("confidence_level", 0.95),
            )
            return {"experiment_id": exp.id}

        elif act_type == "SEND_NOTIFICATION":
            # Log structured notification to DB or system logs
            from models.entities import SystemLog
            log_id = f"log_{uuid.uuid4().hex[:8]}"
            sys_log = SystemLog(
                id=log_id,
                level="INFO",
                service="AUTOMATION",
                message=f"[AUTOMATION RUN] Rule: '{rule.name}' message: {act_config.get('message', 'Triggered')}",
                created_at=datetime.utcnow()
            )
            db.add(sys_log)
            await db.commit()
            return {"status": "notification_sent", "log_id": log_id}

        else:
            raise ValueError(f"Unsupported action type: {act_type}")

    async def verify_platform_connection(self, db: AsyncSession, connection_id: str):
        """Checks connection health, validity, and scope status."""
        conn = await db.get(PlatformConnection, connection_id)
        if not conn:
            raise ValueError(f"PlatformConnection {connection_id} not found.")

        if conn.status != "CONNECTED":
            raise ValueError(f"Connection is not in CONNECTED state: {conn.status}")

        if conn.token_expires_at and conn.token_expires_at <= datetime.utcnow():
            # Invalidate connection status
            conn.status = "EXPIRED"
            await db.commit()
            raise ValueError(f"Platform credentials have expired. Please reconnect {conn.platform}.")

    async def check_global_safety_limits(self, db: AsyncSession, platform: str):
        """
        Guarantees Reflow safety gates are met:
        - Daily platform limit
        - Min interval between posts
        """
        start_of_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Platform-specific daily limit (Max 5 posts/day)
        plat_cnt_res = await db.execute(
            select(func.count(Publication.id))
            .where(
                Publication.platform == platform,
                Publication.status.in_(["PUBLISHED", "SCHEDULED"]),
                Publication.published_at >= start_of_today
            )
        )
        plat_count = plat_cnt_res.scalar() or 0
        if plat_count >= 5:
            raise ValueError(f"Global safety limit reached: cannot publish/schedule more than 5 posts per day on {platform} (current: {plat_count}).")

        # 2. Min interval between posts (Max 60 minutes)
        one_hour_ago = datetime.utcnow() - timedelta(minutes=60)
        interval_res = await db.execute(
            select(func.count(Publication.id))
            .where(
                Publication.platform == platform,
                Publication.status.in_(["PUBLISHED", "SCHEDULED"]),
                or_(
                    Publication.published_at >= one_hour_ago,
                    Publication.scheduled_at >= one_hour_ago
                )
            )
        )
        recent_count = interval_res.scalar() or 0
        if recent_count > 0:
            raise ValueError(f"Global safety interval conflict: must keep at least 60 minutes interval between publications on {platform}.")

    async def check_duplicate_publication(self, db: AsyncSession, content_id: str, platform: str):
        """Prevents duplicate posts of same content on same platform within 24h."""
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        dup_res = await db.execute(
            select(Publication)
            .where(
                Publication.content_id == content_id,
                Publication.platform == platform,
                Publication.status.in_(["PUBLISHED", "SCHEDULED"]),
                or_(
                    Publication.published_at >= one_day_ago,
                    Publication.scheduled_at >= one_day_ago
                )
            )
        )
        existing = dup_res.scalars().first()
        if existing:
            raise ValueError(f"Duplicate prevention: content {content_id} was already published/scheduled on {platform} within the last 24 hours (Publication: {existing.id}).")

    def route_content_capability(self, content_type: str, platform: str):
        """
        Validates content layout against platform capability matrix:
        - VIDEO -> YouTube, Instagram, LinkedIn, X
        - CAROUSEL -> LinkedIn, Instagram
        - TEXT -> LinkedIn, X
        """
        matrix = {
            "VIDEO": ["youtube", "instagram", "linkedin", "x", "facebook", "tiktok"],
            "CAROUSEL": ["linkedin", "instagram", "facebook"],
            "TEXT": ["linkedin", "x"]
        }
        allowed = matrix.get(content_type.upper(), [])
        if platform.lower() not in allowed:
            raise ValueError(f"Platform capability mismatch: content format '{content_type}' cannot be routed to platform '{platform}'.")

    async def instantiate_template(self, db: AsyncSession, template_name: str, name: str, user_id: Optional[str] = None) -> AutomationRule:
        """Creates pre-packaged rules templates."""
        rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        
        templates = {
            "auto_clip_generator": {
                "description": "Auto-generate, style, and burn captions on vertical short clips whenever long videos are ready.",
                "trigger_type": "CONTENT_READY",
                "scope": "REQUIRE_APPROVAL",
                "conditions": [{"field": "content_type", "operator": "==", "value": "VIDEO"}],
                "actions": [{
                    "type": "GENERATE_CLIPS",
                    "min_duration": 15.0,
                    "max_duration": 60.0,
                    "target_count": 3,
                    "burn_captions": True,
                    "caption_style": "BOLD_PUNCH"
                }],
            },
            "auto_carousel_generator": {
                "description": "Generate dynamic educational carousels automatically when textual/note content is ready.",
                "trigger_type": "CONTENT_READY",
                "scope": "AUTO_APPROVE",
                "conditions": [{"field": "content_type", "operator": "==", "value": "TEXT"}],
                "actions": [{
                    "type": "GENERATE_CAROUSEL",
                    "template": "EDITORIAL",
                    "slide_count": 5,
                    "tone": "educational"
                }],
            },
            "auto_social_distribution": {
                "description": "Automatically route and schedule completed video content to active social platform queues.",
                "trigger_type": "CONTENT_APPROVED",
                "scope": "AUTO_APPROVE",
                "conditions": [{"field": "content_type", "operator": "==", "value": "VIDEO"}],
                "actions": [
                    {"type": "GENERATE_PLATFORM_COPY", "platforms": ["LINKEDIN", "X"]},
                    {"type": "SCHEDULE_PUBLICATION", "platform": "linkedin", "delay_hours": 1},
                    {"type": "SCHEDULE_PUBLICATION", "platform": "x", "delay_hours": 2}
                ]
            }
        }

        config = templates.get(template_name.lower())
        if not config:
            raise ValueError(f"Unknown template name: {template_name}")

        rule = AutomationRule(
            id=rule_id,
            name=name,
            description=config["description"],
            enabled=True,
            trigger_type=config["trigger_type"],
            scope=config["scope"],
            cooldown_minutes=60,
            max_runs_per_day=5,
            status="ACTIVE",
            created_by=user_id
        )
        rule.conditions = config["conditions"]
        rule.actions = config["actions"]

        db.add(rule)
        await db.commit()
        return rule

automation_service = AutomationService()
