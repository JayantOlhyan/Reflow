import uuid
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import Publication, APIKey
from models.schemas import PublicationCreateRequest, PublicationResponse
from services.publishing_service import publishing_service
from services.queue_service import queue_service
from services.idempotency_service import idempotency_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Publications")
router = APIRouter(prefix="/publications", tags=["Public API — Publications"])

@router.post("", response_model=PublicationResponse)
async def create_publication(
    req: PublicationCreateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Creates a multi-platform publication payload with Idempotency-Key support."""
    req_hash = idempotency_service.hash_payload(req.model_dump())
    if idempotency_key:
        try:
            cached = await idempotency_service.check_idempotency(db, idempotency_key, req_hash)
            if cached:
                status_code, data = cached
                return PublicationResponse.model_validate(data)
        except ValueError as e:
            if "IDEMPOTENCY_CONFLICT" in str(e):
                raise HTTPException(status_code=409, detail={"error": {"code": "IDEMPOTENCY_CONFLICT", "message": str(e)}})
            raise

    pub = Publication(
        id=f"pub_{uuid.uuid4().hex[:10]}",
        content_id=req.content_id,
        variant_id=req.variant_id,
        platform_connection_id=req.platform_connection_id,
        platform="INSTAGRAM",
        status="DRAFT",
        title=req.title,
        description=req.description or "",
        request_payload_hash=hashlib.sha256(req_hash.encode('utf-8')).hexdigest()[:64]
    )
    db.add(pub)
    await db.commit()
    await db.refresh(pub)

    res_data = PublicationResponse.model_validate(pub).model_dump(mode="json")

    if idempotency_key:
        await idempotency_service.record_idempotency(db, idempotency_key, req_hash, 200, res_data)

    return pub

@router.get("", response_model=List[PublicationResponse])
async def list_publications(
    content_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Lists publications with optional content_id, status, or platform filtering."""
    stmt = select(Publication)
    if content_id:
        stmt = stmt.where(Publication.content_id == content_id)
    if status:
        stmt = stmt.where(Publication.status == status)
    if platform:
        stmt = stmt.where(Publication.platform == platform)

    res = await db.execute(stmt)
    pubs = res.scalars().all()
    return [PublicationResponse.model_validate(p) for p in pubs]

@router.get("/{id}", response_model=PublicationResponse)
async def get_publication_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Gets publication detail by ID."""
    res = await db.execute(select(Publication).where(Publication.id == id))
    pub = res.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Publication '{id}' not found."}})
    return PublicationResponse.model_validate(pub)

@router.post("/{id}/publish", status_code=status.HTTP_202_ACCEPTED)
async def trigger_publication(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Enqueues multi-platform publishing dispatch job. Returns 202 Accepted + job_id."""
    res = await db.execute(select(Publication).where(Publication.id == id))
    pub = res.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Publication '{id}' not found."}})

    job_id = f"job_pub_{uuid.uuid4().hex[:10]}"
    await queue_service.enqueue_media_job(job_id=job_id, content_id=pub.content_id, publication_id=id, job_type="PLATFORM_PUBLISHING")
    return {"job_id": job_id, "status": "QUEUED", "message": "Publication dispatch job enqueued."}

@router.post("/{id}/cancel")
async def cancel_publication(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Cancels a scheduled or pending publication."""
    res = await db.execute(select(Publication).where(Publication.id == id))
    pub = res.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Publication '{id}' not found."}})

    pub.status = "CANCELLED"
    await db.commit()
    return {"status": "success", "id": id, "message": "Publication cancelled."}

@router.post("/{id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_publication(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("PUBLISH"))
):
    """Retries a failed publication dispatch. Returns 202 Accepted + job_id."""
    res = await db.execute(select(Publication).where(Publication.id == id))
    pub = res.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Publication '{id}' not found."}})

    pub.status = "QUEUED"
    await db.commit()

    job_id = f"job_pub_retry_{uuid.uuid4().hex[:10]}"
    await queue_service.enqueue_media_job(job_id=job_id, content_id=pub.content_id, publication_id=id, job_type="PLATFORM_PUBLISHING")
    return {"job_id": job_id, "status": "QUEUED", "message": "Publication retry job enqueued."}
