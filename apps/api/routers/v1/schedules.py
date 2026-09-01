from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from database import get_db
from models.entities import Publication, APIKey
from services.scheduler_service import scheduler_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Schedules")
router = APIRouter(prefix="/schedules", tags=["Public API — Scheduling"])

class ScheduleCreateRequest(BaseModel):
    publication_id: str
    scheduled_at: datetime
    timezone: Optional[str] = "UTC"

@router.post("")
async def create_schedule(
    req: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Schedules a publication item for UTC atomic dispatch."""
    res = await scheduler_service.schedule_publications(db, publication_ids=[req.publication_id], scheduled_at=req.scheduled_at, user_timezone=req.timezone)
    return res

@router.get("")
async def list_schedules(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Lists calendar scheduled publication events."""
    events = await scheduler_service.get_calendar_events(db, start_str=start, end_str=end)
    return events

@router.get("/{id}")
async def get_schedule(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Gets schedule detail by publication ID."""
    res = await db.execute(select(Publication).where(Publication.id == id))
    pub = res.scalar_one_or_none()
    if not pub or pub.status != "SCHEDULED":
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Schedule not found."}})
    return pub

@router.put("/{id}")
async def update_schedule(
    id: str,
    scheduled_at: datetime,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Reschedules publication time."""
    res = await scheduler_service.reschedule_publication(db, publication_id=id, new_scheduled_at=scheduled_at)
    return res

@router.delete("/{id}")
async def delete_schedule(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Cancels scheduled publication dispatch."""
    res = await scheduler_service.cancel_publication(db, publication_id=id)
    return res
