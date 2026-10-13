import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import Workflow, WorkflowExecution, InboundSource, SourceFeedItem, Content, Publication
from services.workflow_engine_service import workflow_engine_service
from utils.logging import get_logger

logger = get_logger("WorkflowsRouter")

router = APIRouter(prefix="/workflows", tags=["Workflows"])

class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = ""
    active: bool = True
    trigger: Optional[str] = "Source Ingestion"
    source_id: Optional[str] = None
    mode: str = Field(default="AUTOMATIC", description="AUTOMATIC or APPROVAL_REQUIRED")
    filters: Dict[str, Any] = Field(default_factory=dict)
    actions_config: Dict[str, Any] = Field(default_factory=dict)
    destinations: List[Dict[str, Any]] = Field(default_factory=list)
    drip_config: Dict[str, Any] = Field(default_factory=dict)

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    source_id: Optional[str] = None
    mode: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    actions_config: Optional[Dict[str, Any]] = None
    destinations: Optional[List[Dict[str, Any]]] = None
    drip_config: Optional[Dict[str, Any]] = None

class WorkflowRunPayload(BaseModel):
    content_id: Optional[str] = None
    feed_item_id: Optional[str] = None
    custom_caption: Optional[str] = None

@router.get("", response_model=List[Dict[str, Any]])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    """List all configured workflows."""
    stmt = select(Workflow).order_by(Workflow.created_at.desc())
    result = await db.execute(stmt)
    workflows = result.scalars().all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "active": w.active,
            "trigger": w.trigger,
            "source_id": w.source_id,
            "mode": w.mode,
            "filters": w.filters,
            "actions_config": w.actions_config,
            "destinations": w.destinations,
            "drip_config": w.drip_config,
            "last_run_at": w.last_run_at.isoformat() if w.last_run_at else None,
            "execution_count": w.execution_count or 0,
            "created_at": w.created_at.isoformat() if w.created_at else None
        }
        for w in workflows
    ]

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    """Create a new automated repurposing workflow."""
    wf_id = f"wf_{uuid.uuid4().hex[:12]}"
    workflow = Workflow(
        id=wf_id,
        name=payload.name,
        description=payload.description or "",
        active=payload.active,
        trigger=payload.trigger or "Source Ingestion",
        source_id=payload.source_id,
        mode=payload.mode.upper(),
        filters_json=json.dumps(payload.filters),
        actions_config_json=json.dumps(payload.actions_config),
        destinations_json=json.dumps(payload.destinations),
        drip_config_json=json.dumps(payload.drip_config)
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return {
        "id": workflow.id,
        "name": workflow.name,
        "mode": workflow.mode,
        "active": workflow.active,
        "created_at": workflow.created_at.isoformat()
    }

@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Get workflow details and recent execution history."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    exec_stmt = select(WorkflowExecution).where(
        WorkflowExecution.workflow_id == workflow_id
    ).order_by(WorkflowExecution.created_at.desc()).limit(15)
    executions = (await db.execute(exec_stmt)).scalars().all()

    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "active": workflow.active,
        "trigger": workflow.trigger,
        "source_id": workflow.source_id,
        "mode": workflow.mode,
        "filters": workflow.filters,
        "actions_config": workflow.actions_config,
        "destinations": workflow.destinations,
        "drip_config": workflow.drip_config,
        "last_run_at": workflow.last_run_at.isoformat() if workflow.last_run_at else None,
        "execution_count": workflow.execution_count or 0,
        "recent_executions": [
            {
                "id": ex.id,
                "status": ex.status,
                "error": ex.error,
                "content_id": ex.content_id,
                "logs": ex.logs,
                "created_at": ex.created_at.isoformat() if ex.created_at else None,
                "completed_at": ex.completed_at.isoformat() if ex.completed_at else None
            }
            for ex in executions
        ]
    }

@router.get("/{workflow_id}/content")
async def get_workflow_content(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Get all content items / episodes detected from this workflow's source and their status."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    if not workflow.source_id:
        return {"workflow_id": workflow_id, "items": []}

    stmt = select(SourceFeedItem).where(
        SourceFeedItem.source_id == workflow.source_id
    ).order_by(SourceFeedItem.detected_at.desc()).limit(50)
    feed_items = (await db.execute(stmt)).scalars().all()

    content_ids = [it.content_id for it in feed_items if it.content_id]
    contents_map = {}
    publications_map = {}

    if content_ids:
        c_stmt = select(Content).where(Content.id.in_(content_ids))
        contents = (await db.execute(c_stmt)).scalars().all()
        contents_map = {c.id: c for c in contents}

        p_stmt = select(Publication).where(Publication.content_id.in_(content_ids))
        pubs = (await db.execute(p_stmt)).scalars().all()
        for p in pubs:
            publications_map.setdefault(p.content_id, []).append(p)

    results = []
    for it in feed_items:
        c = contents_map.get(it.content_id)
        pubs = publications_map.get(it.content_id, [])
        results.append({
            "id": it.id,
            "external_id": it.external_id,
            "title": it.title,
            "media_url": it.media_url,
            "ingestion_status": it.ingestion_status,
            "content_id": it.content_id,
            "duration": c.duration_seconds if c else None,
            "thumbnail": c.thumbnail_path if c else None,
            "detected_at": it.detected_at.isoformat() if it.detected_at else None,
            "publications": [
                {
                    "id": p.id,
                    "platform": p.platform,
                    "status": p.status,
                    "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
                    "published_at": p.published_at.isoformat() if p.published_at else None,
                    "external_url": p.external_url
                }
                for p in pubs
            ]
        })

    return {
        "workflow_id": workflow_id,
        "workflow_name": workflow.name,
        "source_id": workflow.source_id,
        "mode": workflow.mode,
        "items": results
    }

@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, payload: WorkflowUpdate, db: AsyncSession = Depends(get_db)):
    """Update workflow configuration."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    if payload.name is not None: workflow.name = payload.name
    if payload.description is not None: workflow.description = payload.description
    if payload.active is not None: workflow.active = payload.active
    if payload.source_id is not None: workflow.source_id = payload.source_id
    if payload.mode is not None: workflow.mode = payload.mode.upper()
    if payload.filters is not None: workflow.filters_json = json.dumps(payload.filters)
    if payload.actions_config is not None: workflow.actions_config_json = json.dumps(payload.actions_config)
    if payload.destinations is not None: workflow.destinations_json = json.dumps(payload.destinations)
    if payload.drip_config is not None: workflow.drip_config_json = json.dumps(payload.drip_config)

    await db.commit()
    await db.refresh(workflow)
    return {"status": "updated", "id": workflow.id, "name": workflow.name}

@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    payload: Optional[WorkflowRunPayload] = None,
    db: AsyncSession = Depends(get_db)
):
    """Executes a workflow pipeline against a content item or feed item."""
    content_id = payload.content_id if payload else None
    feed_item_id = payload.feed_item_id if payload else None

    try:
        result = await workflow_engine_service.execute_workflow(
            db=db,
            workflow_id=workflow_id,
            content_id=content_id,
            feed_item_id=feed_item_id,
            custom_caption=payload.custom_caption if payload else None
        )
        return result
    except Exception as e:
        logger.error(f"Error running workflow '{workflow_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a workflow."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    await db.delete(workflow)
    await db.commit()
    return None
