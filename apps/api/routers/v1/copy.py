import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import Content, APIKey
from services.queue_service import queue_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Copy")
router = APIRouter(tags=["Public API — Copy Generation"])

class CopyGenerationRequest(BaseModel):
    platform: str # e.g. YOUTUBE, INSTAGRAM, LINKEDIN, TWITTER
    tone: Optional[str] = "professional"
    language: Optional[str] = "en"
    instructions: Optional[str] = None

@router.post("/content/{content_id}/copy", status_code=status.HTTP_202_ACCEPTED)
async def generate_platform_copy(
    content_id: str,
    req: CopyGenerationRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_WRITE"))
):
    """Enqueues AI platform copy generation job. Returns 202 Accepted + job_id."""
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Content item '{content_id}' not found."}})

    job_id = f"job_copy_gen_{uuid.uuid4().hex[:10]}"
    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=content_id,
        platform=req.platform,
        tone=req.tone,
        instructions=req.instructions,
        job_type="COPY_GENERATION"
    )
    return {
        "job_id": job_id,
        "status": "QUEUED",
        "message": f"Platform copy generation job enqueued for {req.platform}."
    }
