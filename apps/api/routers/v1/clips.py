import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import Clip, APIKey
from models.schemas import ClipResponse, ClipUpdateRequest
from services.queue_service import queue_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Clips")
router = APIRouter(tags=["Public API — Clips"])

@router.post("/content/{content_id}/clips/discover", status_code=status.HTTP_202_ACCEPTED)
async def discover_clips(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CLIP_WRITE"))
):
    """Enqueues async AI clip discovery job. Returns 202 Accepted + job_id."""
    job_id = f"job_clip_disc_{uuid.uuid4().hex[:10]}"
    await queue_service.enqueue_media_job(job_id=job_id, content_id=content_id, job_type="CLIP_DISCOVERY")
    return {"job_id": job_id, "status": "QUEUED", "message": "Clip discovery job enqueued successfully."}

@router.get("/content/{content_id}/clips", response_model=List[ClipResponse])
async def list_content_clips(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CLIP_READ"))
):
    """Lists clips discovered for a content item."""
    res = await db.execute(select(Clip).where(Clip.content_id == content_id))
    clips = res.scalars().all()
    return [ClipResponse.model_validate(c) for c in clips]

@router.get("/clips/{id}", response_model=ClipResponse)
async def get_clip_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CLIP_READ"))
):
    """Gets clip detail by ID."""
    res = await db.execute(select(Clip).where(Clip.id == id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Clip '{id}' not found."}})
    return ClipResponse.model_validate(clip)

@router.put("/clips/{id}", response_model=ClipResponse)
async def update_clip(
    id: str,
    req: ClipUpdateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CLIP_WRITE"))
):
    """Updates clip title, boundaries, or quality score."""
    res = await db.execute(select(Clip).where(Clip.id == id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Clip '{id}' not found."}})

    if req.title is not None:
        clip.title = req.title
    if req.start_time is not None:
        clip.start_time = req.start_time
    if req.end_time is not None:
        clip.end_time = req.end_time

    await db.commit()
    await db.refresh(clip)
    return ClipResponse.model_validate(clip)

@router.delete("/clips/{id}")
async def delete_clip(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CLIP_WRITE"))
):
    """Deletes clip and attached video variants."""
    res = await db.execute(select(Clip).where(Clip.id == id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Clip '{id}' not found."}})

    await db.delete(clip)
    await db.commit()
    return {"status": "success", "id": id, "message": "Clip deleted."}

@router.post("/clips/{id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_clip_variants(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CLIP_WRITE"))
):
    """Enqueues async FFmpeg clip extraction & variant transcoding job. Returns 202 Accepted + job_id."""
    res = await db.execute(select(Clip).where(Clip.id == id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Clip '{id}' not found."}})

    job_id = f"job_clip_gen_{uuid.uuid4().hex[:10]}"
    await queue_service.enqueue_media_job(job_id=job_id, content_id=clip.content_id, clip_id=id, job_type="CLIP_GENERATION")
    return {"job_id": job_id, "status": "QUEUED", "message": "Clip video generation job enqueued."}
