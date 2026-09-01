from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import SystemJob, APIKey
from models.schemas import SystemJobResponse
from services.queue_service import queue_service
from services.telemetry_service import telemetry_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Jobs")
router = APIRouter(prefix="/jobs", tags=["Public API — Jobs"])

@router.get("/{id}", response_model=SystemJobResponse)
async def get_job_status(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_READ"))
):
    """
    Polls job execution status.
    Returns status (QUEUED, RUNNING, SUCCEEDED, FAILED, STALE), timestamps, and error details.
    """
    res = await db.execute(select(SystemJob).where(SystemJob.id == id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Job '{id}' not found."}})
    return SystemJobResponse.model_validate(job)

@router.get("/{id}/events")
async def get_job_events(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_READ"))
):
    """Gets execution trace timeline for a job."""
    res = await telemetry_service.trace_job(db, id)
    return res

@router.post("/{id}/retry")
async def retry_job(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_WRITE"))
):
    """Manually retries a failed background job."""
    res = await db.execute(select(SystemJob).where(SystemJob.id == id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Job '{id}' not found."}})

    job.status = "QUEUED"
    job.retry_count = 0
    await db.commit()

    return {"status": "success", "job_id": id, "message": "Job re-queued for execution."}
