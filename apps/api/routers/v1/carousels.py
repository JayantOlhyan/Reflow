import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import Carousel, CarouselSlide, APIKey
from models.schemas import CarouselResponse, CarouselCreateRequest, CarouselUpdateRequest
from services.carousel_renderer import carousel_renderer
from services.carousel_helper import fetch_full_carousel
from services.queue_service import queue_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Carousels")
router = APIRouter(tags=["Public API — Carousels"])

@router.post("/content/{content_id}/carousels", response_model=CarouselResponse)
async def create_carousel(
    content_id: str,
    req: CarouselCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CAROUSEL_WRITE"))
):
    """Creates a new carousel slide deck for content."""
    carousel = Carousel(
        id=f"car_{uuid.uuid4().hex[:10]}",
        content_id=content_id,
        title=req.title,
        theme=req.theme or "modern",
        status="DRAFT"
    )
    db.add(carousel)
    await db.flush()

    if req.slides:
        for idx, slide_data in enumerate(req.slides):
            slide = CarouselSlide(
                id=f"sld_{uuid.uuid4().hex[:10]}",
                carousel_id=carousel.id,
                slide_index=idx,
                title=slide_data.title or f"Slide {idx + 1}",
                body=slide_data.body or ""
            )
            db.add(slide)

    await db.commit()
    full_carousel = await fetch_full_carousel(db, carousel.id)
    return CarouselResponse.model_validate(full_carousel)

@router.get("/content/{content_id}/carousels", response_model=List[CarouselResponse])
async def list_content_carousels(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CAROUSEL_READ"))
):
    """Lists carousels for a content item."""
    res = await db.execute(select(Carousel).where(Carousel.content_id == content_id))
    carousels = res.scalars().all()
    full_list = []
    for c in carousels:
        fc = await fetch_full_carousel(db, c.id)
        if fc:
            full_list.append(CarouselResponse.model_validate(fc))
    return full_list

@router.get("/carousels/{id}", response_model=CarouselResponse)
async def get_carousel_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CAROUSEL_READ"))
):
    """Gets carousel detail by ID."""
    carousel = await fetch_full_carousel(db, id)
    if not carousel:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Carousel '{id}' not found."}})
    return CarouselResponse.model_validate(carousel)

@router.put("/carousels/{id}", response_model=CarouselResponse)
async def update_carousel(
    id: str,
    req: CarouselUpdateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CAROUSEL_WRITE"))
):
    """Updates carousel slides or theme."""
    res = await db.execute(select(Carousel).where(Carousel.id == id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Carousel '{id}' not found."}})

    if req.title:
        carousel.title = req.title
    if req.theme:
        carousel.theme = req.theme

    await db.commit()
    full_carousel = await fetch_full_carousel(db, id)
    return CarouselResponse.model_validate(full_carousel)

@router.delete("/carousels/{id}")
async def delete_carousel(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CAROUSEL_WRITE"))
):
    """Deletes carousel deck."""
    res = await db.execute(select(Carousel).where(Carousel.id == id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Carousel '{id}' not found."}})

    await db.delete(carousel)
    await db.commit()
    return {"status": "success", "id": id, "message": "Carousel deleted."}

@router.post("/carousels/{id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_carousel_images(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CAROUSEL_WRITE"))
):
    """Enqueues async server-side slide rendering & PDF export job. Returns 202 Accepted + job_id."""
    res = await db.execute(select(Carousel).where(Carousel.id == id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Carousel '{id}' not found."}})

    job_id = f"job_car_gen_{uuid.uuid4().hex[:10]}"
    await queue_service.enqueue_media_job(job_id=job_id, content_id=carousel.content_id, carousel_id=id, job_type="CAROUSEL_GENERATION")
    return {"job_id": job_id, "status": "QUEUED", "message": "Carousel rendering job enqueued."}

@router.post("/carousels/{id}/export")
async def export_carousel(
    id: str,
    format: str = "pdf",
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CAROUSEL_READ"))
):
    """Exports carousel deck as PDF document or PNG slide zip archive."""
    full_carousel = await fetch_full_carousel(db, id)
    if not full_carousel:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Carousel '{id}' not found."}})

    slides = [s.model_dump() if hasattr(s, "model_dump") else s.__dict__ for s in getattr(full_carousel, "slides", [])]
    export_res = await carousel_renderer.render_deck(deck_id=id, slides=slides, theme=getattr(full_carousel, "theme", "modern"))
    return export_res
