import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from utils.logging import get_logger
from models.entities import (
    Workflow,
    WorkflowExecution,
    Content,
    Asset,
    ContentVariant,
    Clip,
    Publication,
    SourceFeedItem
)
from services.audiogram_service import audiogram_service
from services.drip_queue_service import drip_queue_service
from services.storage_service import storage_service

logger = get_logger("WorkflowEngineService")

class WorkflowEngineService:
    """
    Executes automated end-to-end repurposing workflows:
    Source Ingestion -> Rule Filtering -> Transformations (Clips/Audiograms) -> Drip Scheduling / Approvals.
    """

    async def execute_workflow(
        self,
        db: AsyncSession,
        workflow_id: str,
        content_id: Optional[str] = None,
        feed_item_id: Optional[str] = None
    ) -> Dict[str, Any]:
        workflow = await db.get(Workflow, workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        if not workflow.active:
            return {"status": "skipped", "message": f"Workflow '{workflow.name}' is inactive."}

        # Resolve Content
        content: Optional[Content] = None
        if content_id:
            content = await db.get(Content, content_id)
        elif feed_item_id:
            feed_item = await db.get(SourceFeedItem, feed_item_id)
            if feed_item and feed_item.content_id:
                content = await db.get(Content, feed_item.content_id)

        if not content:
            raise ValueError("No Content found to execute workflow against.")

        # Initialize Execution Record
        execution = WorkflowExecution(
            id=f"wfx_{uuid.uuid4().hex[:12]}",
            workflow_id=workflow.id,
            source_feed_item_id=feed_item_id,
            content_id=content.id,
            status="RUNNING",
            logs_json="[]"
        )
        db.add(execution)
        await db.flush()

        logs: List[str] = [f"Starting workflow '{workflow.name}' for Content '{content.title}' ({content.id})"]

        try:
            # 1. Evaluate Filter Rules
            passed, filter_msg = self._evaluate_filters(workflow, content)
            if not passed:
                logs.append(f"Filter check skipped: {filter_msg}")
                execution.status = "SKIPPED"
                execution.error = filter_msg
                execution.logs_json = json.dumps(logs)
                execution.completed_at = datetime.utcnow()
                await db.commit()
                return {"status": "skipped", "reason": filter_msg, "execution_id": execution.id}

            logs.append("All workflow filters passed successfully.")

            # 2. Perform Transformation Actions
            actions_cfg = workflow.actions_config
            action_type = actions_cfg.get("action_type", "AI_CLIPS")
            target_variant_id: Optional[str] = None

            if action_type == "AUDIOGRAM" and content.content_type in ("AUDIO", "PODCAST"):
                logs.append("Executing Audiogram generation for audio content.")
                audiogram_res = await self._generate_audiogram_variant(db, content, actions_cfg)
                target_variant_id = audiogram_res["variant_id"]
                logs.append(f"Audiogram rendered successfully: variant_id={target_variant_id}")
            else:
                logs.append(f"Action '{action_type}' processed for {content.content_type} content.")

            # 3. Schedule or Stage Publications
            destinations = workflow.destinations
            created_publications: List[str] = []

            if destinations:
                drip_cfg = workflow.drip_config
                drip_enabled = drip_cfg.get("drip_enabled", False)
                interval_hours = drip_cfg.get("interval_hours", 4)
                active_start = drip_cfg.get("active_hours_start", 9)
                active_end = drip_cfg.get("active_hours_end", 21)

                scheduled_times: List[datetime] = []
                if drip_enabled:
                    scheduled_times = drip_queue_service.calculate_drip_schedule(
                        count=len(destinations),
                        interval_hours=interval_hours,
                        active_hours_start=active_start,
                        active_hours_end=active_end
                    )

                for idx, dest in enumerate(destinations):
                    platform = dest.get("platform", "youtube")
                    connection_id = dest.get("connection_id")
                    caption_tpl = dest.get("custom_caption", "{{title}}\n\n{{description}}")

                    formatted_caption = caption_tpl.replace("{{title}}", content.title or "")
                    formatted_caption = formatted_caption.replace("{{description}}", (content.text_content or "")[:500])

                    pub_status = "SCHEDULED" if (workflow.mode == "AUTOMATIC" and drip_enabled) else ("QUEUED" if workflow.mode == "AUTOMATIC" else "DRAFT")
                    sched_at = scheduled_times[idx] if (drip_enabled and idx < len(scheduled_times)) else None

                    pub = Publication(
                        id=f"pub_{uuid.uuid4().hex[:12]}",
                        content_id=content.id,
                        variant_id=target_variant_id,
                        platform_connection_id=connection_id,
                        platform=platform,
                        status=pub_status,
                        title=content.title,
                        description=formatted_caption,
                        privacy=dest.get("privacy", "PUBLIC"),
                        scheduled_at=sched_at,
                        request_payload_hash=uuid.uuid4().hex
                    )
                    db.add(pub)
                    await db.flush()
                    created_publications.append(pub.id)
                    logs.append(f"Created Publication {pub.id} for {platform} (status={pub_status})")

            # 4. Mark Execution Succeeded
            execution.status = "SUCCEEDED"
            execution.completed_at = datetime.utcnow()
            workflow.last_run_at = datetime.utcnow()
            workflow.execution_count = (workflow.execution_count or 0) + 1
            logs.append("Workflow execution finished successfully.")
            execution.logs_json = json.dumps(logs)
            await db.commit()

            return {
                "status": "succeeded",
                "execution_id": execution.id,
                "workflow_id": workflow.id,
                "publications_count": len(created_publications),
                "publication_ids": created_publications
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            logs.append(f"Error during execution: {str(e)}")
            execution.status = "FAILED"
            execution.error = str(e)
            execution.logs_json = json.dumps(logs)
            execution.completed_at = datetime.utcnow()
            await db.commit()
            raise

    def _evaluate_filters(self, workflow: Workflow, content: Content) -> tuple[bool, str]:
        """Evaluates whether content passes workflow filter criteria."""
        filters = workflow.filters
        text_corpus = f"{content.title} {content.text_content or ''}".lower()

        # Include hashtags
        include_tags = [t.lower().strip() for t in filters.get("include_hashtags", []) if t.strip()]
        if include_tags and not any(tag in text_corpus for tag in include_tags):
            return False, f"Content does not contain required include hashtags: {include_tags}"

        # Exclude hashtags
        exclude_tags = [t.lower().strip() for t in filters.get("exclude_hashtags", []) if t.strip()]
        if exclude_tags and any(tag in text_corpus for tag in exclude_tags):
            return False, f"Content contains excluded hashtag: {exclude_tags}"

        return True, "Passed"

    async def _generate_audiogram_variant(self, db: AsyncSession, content: Content, actions_cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes audiogram video variant using audiogram_service."""
        # Find audio asset
        stmt = select(Asset).where(Asset.content_id == content.id).order_by(Asset.created_at.desc())
        asset = (await db.execute(stmt)).scalars().first()
        if not asset:
            raise ValueError(f"No audio asset found for Content {content.id}")

        audio_full_path = storage_service.get_full_path(asset.storage_key)
        aspect_ratio = actions_cfg.get("aspect_ratio", "9:16")
        waveform_style = actions_cfg.get("waveform_style", "BARS")
        waveform_color = actions_cfg.get("waveform_color", "#6366F1")

        variant_id = f"var_{uuid.uuid4().hex[:12]}"
        out_key = f"content/{content.id}/variants/{variant_id}_audiogram_{aspect_ratio.replace(':', '_')}.mp4"

        res = await audiogram_service.generate_audiogram(
            audio_file_path=audio_full_path,
            output_storage_key=out_key,
            aspect_ratio=aspect_ratio,
            waveform_style=waveform_style,
            waveform_color=waveform_color
        )

        variant = ContentVariant(
            id=variant_id,
            content_id=content.id,
            source_asset_id=asset.id,
            variant_type="VERTICAL_9_16" if aspect_ratio == "9:16" else "SQUARE_1_1",
            storage_key=out_key,
            mime_type="video/mp4",
            file_size=res["file_size"],
            width=res["width"],
            height=res["height"],
            status="READY"
        )
        db.add(variant)
        await db.flush()

        return {"variant_id": variant_id, "storage_key": out_key}

workflow_engine_service = WorkflowEngineService()
