import sys
import os
import io
import json
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Optional

from config import settings
from database import get_db, init_db
from models.entities import (
    Content, Asset, ContentVariant, Transcript, TranscriptSegment,
    ContentBrief, GeneratedContent, Carousel, CarouselSlide, SlideElement, CarouselExport,
    Clip, ClipVariant, PlatformConnection, Workflow, Job, SystemLog
)
from models.schemas import (
    ContentResponse, ContentListResponse, TextContentCreateRequest,
    TranscriptResponse, ContentBriefResponse, GeneratedContentResponse,
    AIGenerateRequest, RepurposeRequest, AICarouselPrompt, SchedulePostRequest,
    PlatformConnectionSchema, PlatformConnectionUpdate, HealthResponse, ApiResponse,
    JobResponse, CarouselResponse, CarouselListResponse, CarouselCreateRequest,
    CarouselUpdateRequest, SlideCreateRequest, SlideUpdateRequest, SlideReorderRequest,
    CarouselGenerateRequest, CarouselExportResponse,
    ClipResponse, ClipListResponse, ClipDiscoveryRequest, ClipUpdateRequest,
    ClipGenerateRequest, ClipVariantResponse
)
from services.media_service import media_processor
from services.queue_service import queue_service
from services.ai_service import ai_service
from services.carousel_renderer import carousel_renderer
from services.carousel_helper import fetch_full_carousel
from services.clip_helper import fetch_full_clip, fetch_content_clips
from services.health_service import health_service
from services.storage_service import storage_service, validate_upload, generate_storage_key
from utils.logging import get_logger

logger = get_logger("ReflowAPI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Reflow API starting up... Initializing database schema.")
    await init_db()
    yield
    logger.info("Reflow API shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Open-source self-hosted content operating system",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "code": exc.status_code, "message": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "validation_error", "message": "Invalid request payload.", "details": exc.errors()}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "internal_error", "message": "An internal server error occurred."}
    )

# ------------------------------------------------------------------------------
# Health Checks
# ------------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def liveness_probe():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@app.get("/api/system/health", response_model=HealthResponse, tags=["System"])
async def system_health_telemetry():
    return await health_service.get_overall_health()

# ------------------------------------------------------------------------------
# Overview Dashboard Metrics
# ------------------------------------------------------------------------------

@app.get("/api/overview", tags=["Overview"])
async def get_overview(db: AsyncSession = Depends(get_db)):
    total_content_res = await db.execute(select(func.count(Content.id)))
    total_count = total_content_res.scalar() or 0

    recent_res = await db.execute(select(Content).order_by(Content.created_at.desc()).limit(5))
    recent_items = recent_res.scalars().all()

    connections_res = await db.execute(select(PlatformConnection))
    connections = connections_res.scalars().all()

    recent_activity = [
        {
            "id": c.id,
            "title": c.title,
            "type": c.content_type,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in recent_items
    ]

    return {
        "metrics": {
            "total": total_count,
            "published": 0,
            "scheduled": 0,
            "failed": 0
        },
        "recent_activity": recent_activity,
        "connections": [PlatformConnectionSchema.model_validate(c).model_dump() for c in connections]
    }

# ------------------------------------------------------------------------------
# Content Library API
# ------------------------------------------------------------------------------

@app.get("/api/content", response_model=ContentListResponse, tags=["Content"])
async def list_content(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Content)

    if type and type.upper() != "ALL":
        query = query.where(Content.content_type == type.upper())
    if status and status.upper() != "ALL":
        query = query.where(Content.status == status.upper())
    if search:
        query = query.where(Content.title.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_count_res = await db.execute(count_query)
    total_count = total_count_res.scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    paginated_query = query.order_by(Content.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(paginated_query)
    items = res.scalars().all()

    return {
        "items": [ContentResponse.model_validate(item) for item in items],
        "total": total_count,
        "page": page,
        "limit": limit
    }

@app.get("/api/content/{content_id}", response_model=ContentResponse, tags=["Content"])
async def get_content(content_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Content).where(Content.id == content_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found.")
    return ContentResponse.model_validate(item)

@app.post("/api/content/upload", response_model=ContentResponse, tags=["Content"])
async def upload_content_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    mime_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()
    file_size = len(file_bytes)

    is_valid, content_type, err_msg = validate_upload(file.filename, mime_type, file_size)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    content_id = f"cnt_{uuid.uuid4().hex[:12]}"
    asset_id = f"ast_{uuid.uuid4().hex[:12]}"
    clean_title = title.strip() if title and title.strip() else os.path.splitext(file.filename)[0]

    storage_key = generate_storage_key(content_id, asset_id, file.filename)

    try:
        await storage_service.put(storage_key, file_bytes)
    except Exception as e:
        logger.error(f"Failed to persist file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file to storage.")

    # Ingest record
    initial_status = "PROCESSING" if content_type == "VIDEO" else "READY"
    content = Content(
        id=content_id,
        title=clean_title,
        content_type=content_type,
        status=initial_status,
        created_at=datetime.utcnow()
    )
    db.add(content)

    asset = Asset(
        id=asset_id,
        content_id=content_id,
        original_filename=file.filename,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=file_size,
        created_at=datetime.utcnow()
    )
    db.add(asset)
    await db.commit()
    await db.refresh(content)

    if content_type == "VIDEO":
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(
            id=job_id,
            content_id=content_id,
            asset_id=asset_id,
            type="MEDIA_PROCESSING",
            status="QUEUED",
            created_at=datetime.utcnow()
        )
        db.add(job)
        await db.commit()
        await queue_service.enqueue_media_job(job_id, content_id, asset_id, job_type="MEDIA_PROCESSING")

    logger.info(f"Successfully ingested {content_type} asset '{file.filename}' -> Content ID: {content_id} (Status: {initial_status})")
    return ContentResponse.model_validate(content)

@app.post("/api/content/text", response_model=ContentResponse, tags=["Content"])
async def create_text_content(payload: TextContentCreateRequest, db: AsyncSession = Depends(get_db)):
    content_id = f"cnt_{uuid.uuid4().hex[:12]}"
    content = Content(
        id=content_id,
        title=payload.title.strip(),
        content_type="TEXT",
        status="READY",
        text_content=payload.text.strip(),
        created_at=datetime.utcnow()
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    logger.info(f"Created text content asset: {content_id} ({payload.title})")
    return ContentResponse.model_validate(content)

@app.get("/api/content/{content_id}/asset/{asset_id}", tags=["Content"])
async def stream_asset(content_id: str, asset_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.content_id == content_id)
    )
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    real_path = storage_service.get_real_path(asset.storage_key)
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Asset physical file missing.")

    return FileResponse(
        real_path,
        media_type=asset.mime_type,
        filename=asset.original_filename
    )

@app.get("/api/content/{content_id}/variant/{variant_id}", tags=["Content"])
async def stream_variant(content_id: str, variant_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(ContentVariant).where(ContentVariant.id == variant_id, ContentVariant.content_id == content_id)
    )
    variant = res.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found.")

    real_path = storage_service.get_real_path(variant.storage_key)
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Variant physical file missing.")

    return FileResponse(
        real_path,
        media_type=variant.mime_type
    )

@app.post("/api/content/{content_id}/reprocess", tags=["Content"])
async def reprocess_media_content(content_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")
    if content.content_type != "VIDEO" or not content.assets:
        raise HTTPException(status_code=400, detail="Only video content with assets can be reprocessed.")

    primary_asset = content.assets[0]
    content.status = "PROCESSING"

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = Job(
        id=job_id,
        content_id=content_id,
        asset_id=primary_asset.id,
        type="MEDIA_PROCESSING",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(job_id, content_id, primary_asset.id, job_type="MEDIA_PROCESSING")
    return {"status": "success", "message": f"Reprocessing queued for content {content_id} (Job ID: {job_id})"}

@app.delete("/api/content/{content_id}", tags=["Content"])
async def delete_content(content_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    # Clean storage
    for asset in content.assets:
        try: await storage_service.delete(asset.storage_key)
        except Exception: pass

    for variant in content.variants:
        try: await storage_service.delete(variant.storage_key)
        except Exception: pass

    for carousel in content.carousels:
        for export in carousel.exports:
            try: await storage_service.delete(export.storage_key)
            except Exception: pass

    for clip in content.clips:
        for c_var in clip.variants:
            try: await storage_service.delete(c_var.storage_key)
            except Exception: pass
        if clip.thumbnail_path:
            try: await storage_service.delete(clip.thumbnail_path)
            except Exception: pass

    await db.delete(content)
    await db.commit()
    logger.info(f"Deleted Content {content_id} and all related physical storage variants & AI outputs.")
    return {"status": "success", "message": f"Content {content_id} deleted successfully."}

# ------------------------------------------------------------------------------
# Phase 3 AI Content Intelligence API
# ------------------------------------------------------------------------------

@app.get("/api/content/{content_id}/transcript", response_model=TranscriptResponse, tags=["AI Intelligence"])
async def get_content_transcript(content_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Transcript).where(Transcript.content_id == content_id))
    transcript = res.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found for this content.")
    return TranscriptResponse.model_validate(transcript)

@app.get("/api/content/{content_id}/brief", response_model=ContentBriefResponse, tags=["AI Intelligence"])
async def get_content_brief(content_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ContentBrief).where(ContentBrief.content_id == content_id))
    brief = res.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="ContentBrief not found for this content.")
    return ContentBriefResponse.model_validate(brief)

@app.get("/api/content/{content_id}/generated", response_model=List[GeneratedContentResponse], tags=["AI Intelligence"])
async def get_generated_content_list(content_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(GeneratedContent)
        .where(GeneratedContent.content_id == content_id)
        .order_by(GeneratedContent.platform, GeneratedContent.version.desc())
    )
    items = res.scalars().all()
    # Deduplicate to show latest version of each platform
    seen = set()
    latest_items = []
    for it in items:
        if it.platform not in seen:
            seen.add(it.platform)
            latest_items.append(it)
    return [GeneratedContentResponse.model_validate(it) for it in latest_items]

@app.post("/api/content/{content_id}/generate", response_model=ApiResponse, tags=["AI Intelligence"])
async def trigger_ai_generation(
    content_id: str,
    req: AIGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    try:
        await ai_service.generate_platform_content(
            content_id=content_id,
            platforms=req.platforms,
            tone=req.tone or "professional",
            custom_instructions=req.custom_instructions
        )
        return ApiResponse(status="success", message="AI generation executed successfully.")
    except Exception as e:
        logger.error(f"AI generation failed for Content {content_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/content/{content_id}/regenerate/{platform}", response_model=ApiResponse, tags=["AI Intelligence"])
async def regenerate_single_platform(
    content_id: str,
    platform: str,
    tone: Optional[str] = Query("professional"),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    plt_upper = platform.upper()
    if plt_upper not in ["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"]:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    try:
        await ai_service.generate_platform_content(
            content_id=content_id,
            platforms=[plt_upper],
            tone=tone or "professional"
        )
        return ApiResponse(status="success", message=f"Successfully regenerated {plt_upper} content.")
    except Exception as e:
        logger.error(f"Regeneration failed for {plt_upper}: {e}")
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")

# ------------------------------------------------------------------------------
# Phase 4 Carousel Engine API
# ------------------------------------------------------------------------------

@app.post("/api/carousels", response_model=CarouselResponse, tags=["Carousels"])
async def create_carousel(req: CarouselCreateRequest, db: AsyncSession = Depends(get_db)):
    carousel_id = f"car_{uuid.uuid4().hex[:12]}"
    carousel = Carousel(
        id=carousel_id,
        content_id=req.content_id,
        title=req.title.strip(),
        template=req.template.upper() if req.template else "MINIMAL",
        aspect_ratio=req.aspect_ratio or "1:1",
        status="DRAFT",
        slide_count=0,
        version=1,
        created_at=datetime.utcnow()
    )
    db.add(carousel)
    await db.commit()
    
    full_carousel = await fetch_full_carousel(db, carousel_id)
    logger.info(f"Created Carousel {carousel_id} ('{carousel.title}')")
    return CarouselResponse.model_validate(full_carousel)

@app.get("/api/carousels", response_model=CarouselListResponse, tags=["Carousels"])
async def list_carousels(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Carousel)
        .options(
            selectinload(Carousel.slides).selectinload(CarouselSlide.elements),
            selectinload(Carousel.exports)
        )
        .order_by(Carousel.updated_at.desc())
    )
    count_res = await db.execute(select(func.count(Carousel.id)))
    total = count_res.scalar() or 0

    offset = (page - 1) * limit
    res = await db.execute(query.offset(offset).limit(limit))
    items = res.scalars().all()

    return {
        "items": [CarouselResponse.model_validate(c) for c in items],
        "total": total,
        "page": page,
        "limit": limit
    }

@app.get("/api/carousels/{carousel_id}", response_model=CarouselResponse, tags=["Carousels"])
async def get_carousel(carousel_id: str, db: AsyncSession = Depends(get_db)):
    carousel = await fetch_full_carousel(db, carousel_id)
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")
    return CarouselResponse.model_validate(carousel)

@app.put("/api/carousels/{carousel_id}", response_model=CarouselResponse, tags=["Carousels"])
async def update_carousel(carousel_id: str, req: CarouselUpdateRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Carousel).where(Carousel.id == carousel_id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")

    if req.title is not None:
        carousel.title = req.title.strip()
    if req.template is not None:
        carousel.template = req.template.upper()
    if req.aspect_ratio is not None:
        carousel.aspect_ratio = req.aspect_ratio

    carousel.version += 1
    carousel.updated_at = datetime.utcnow()
    await db.commit()

    full_carousel = await fetch_full_carousel(db, carousel_id)
    return CarouselResponse.model_validate(full_carousel)

@app.delete("/api/carousels/{carousel_id}", tags=["Carousels"])
async def delete_carousel(carousel_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Carousel).where(Carousel.id == carousel_id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")

    for export in carousel.exports:
        try: await storage_service.delete(export.storage_key)
        except Exception: pass

    await db.delete(carousel)
    await db.commit()
    return {"status": "success", "message": f"Carousel {carousel_id} deleted."}

@app.post("/api/carousels/{carousel_id}/generate", response_model=ApiResponse, tags=["Carousels"])
async def generate_carousel(
    carousel_id: str,
    req: CarouselGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Carousel).where(Carousel.id == carousel_id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")

    carousel.status = "GENERATING"
    await db.commit()

    # Enqueue background job
    job_id = f"job_car_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        content_id=carousel.content_id,
        type="CAROUSEL_GENERATION",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=carousel.content_id,
        asset_id=None,
        job_type="CAROUSEL_GENERATION",
        carousel_id=carousel_id,
        slide_count=req.slide_count,
        template=req.template,
        tone=req.tone,
        custom_prompt=req.custom_prompt
    )

    return ApiResponse(status="success", message=f"Carousel generation queued (Job {job_id}).")

@app.post("/api/carousels/{carousel_id}/slides", response_model=CarouselResponse, tags=["Carousels"])
async def add_carousel_slide(carousel_id: str, req: SlideCreateRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Carousel).where(Carousel.id == carousel_id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")

    pos = req.position if req.position is not None else (carousel.slide_count + 1)
    slide_id = f"sld_{uuid.uuid4().hex[:12]}"
    slide = CarouselSlide(
        id=slide_id,
        carousel_id=carousel_id,
        position=pos,
        purpose=req.purpose,
        layout=req.layout,
        headline=req.headline.strip(),
        body=req.body.strip(),
        tag=req.tag or "TIP",
        background=req.background or "#0F172A",
        created_at=datetime.utcnow()
    )
    db.add(slide)

    elem = SlideElement(
        id=f"elm_{uuid.uuid4().hex[:12]}",
        slide_id=slide_id,
        type="TEXT",
        content=f"{req.headline}\n\n{req.body}",
        style_json=json.dumps({"fontSize": 32, "color": "#FFFFFF"})
    )
    db.add(elem)

    carousel.slide_count += 1
    carousel.version += 1
    carousel.updated_at = datetime.utcnow()
    await db.commit()

    full_carousel = await fetch_full_carousel(db, carousel_id)
    return CarouselResponse.model_validate(full_carousel)

@app.put("/api/carousels/{carousel_id}/slides/reorder", response_model=CarouselResponse, tags=["Carousels"])
async def reorder_carousel_slides(
    carousel_id: str,
    req: SlideReorderRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Carousel).where(Carousel.id == carousel_id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")

    s_res = await db.execute(select(CarouselSlide).where(CarouselSlide.carousel_id == carousel_id))
    slides_map = {s.id: s for s in s_res.scalars().all()}

    for new_pos, sid in enumerate(req.slide_ids, start=1):
        if sid in slides_map:
            slides_map[sid].position = new_pos

    carousel.version += 1
    carousel.updated_at = datetime.utcnow()
    await db.commit()

    full_carousel = await fetch_full_carousel(db, carousel_id)
    return CarouselResponse.model_validate(full_carousel)

@app.put("/api/carousels/{carousel_id}/slides/{slide_id}", response_model=CarouselResponse, tags=["Carousels"])
async def update_carousel_slide(
    carousel_id: str,
    slide_id: str,
    req: SlideUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Carousel).where(Carousel.id == carousel_id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")

    s_res = await db.execute(
        select(CarouselSlide).where(CarouselSlide.id == slide_id, CarouselSlide.carousel_id == carousel_id)
    )
    slide = s_res.scalar_one_or_none()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found.")

    if req.headline is not None:
        slide.headline = req.headline.strip()
    if req.body is not None:
        slide.body = req.body.strip()
    if req.tag is not None:
        slide.tag = req.tag.strip()
    if req.purpose is not None:
        slide.purpose = req.purpose
    if req.layout is not None:
        slide.layout = req.layout
    if req.background is not None:
        slide.background = req.background

    slide.updated_at = datetime.utcnow()
    carousel.version += 1
    carousel.updated_at = datetime.utcnow()
    await db.commit()

    full_carousel = await fetch_full_carousel(db, carousel_id)
    return CarouselResponse.model_validate(full_carousel)

    carousel.version += 1
    carousel.updated_at = datetime.utcnow()
    await db.commit()

    full_carousel = await fetch_full_carousel(db, carousel_id)
    return CarouselResponse.model_validate(full_carousel)

@app.post("/api/carousels/{carousel_id}/render", tags=["Carousels"])
async def render_carousel_exports(carousel_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Carousel).where(Carousel.id == carousel_id))
    carousel = res.scalar_one_or_none()
    if not carousel:
        raise HTTPException(status_code=404, detail="Carousel not found.")

    try:
        render_result = await carousel_renderer.render_carousel_deck(carousel_id)
        return {"status": "success", "message": "Render completed.", "data": render_result}
    except Exception as e:
        logger.error(f"Render failed for Carousel {carousel_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Render failed: {str(e)}")

@app.get("/api/carousels/{carousel_id}/export/{export_id}", tags=["Carousels"])
async def stream_carousel_export(carousel_id: str, export_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(CarouselExport).where(CarouselExport.id == export_id, CarouselExport.carousel_id == carousel_id)
    )
    export = res.scalar_one_or_none()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found.")

    real_path = storage_service.get_real_path(export.storage_key)
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Export physical file missing.")

    media_type = "application/pdf" if export.format == "PDF" else "image/png"
    filename = f"carousel_{carousel_id}.pdf" if export.format == "PDF" else f"slide_{carousel_id}.png"
    return FileResponse(real_path, media_type=media_type, filename=filename)

# Legacy / Adapter endpoint
@app.post("/api/carousels/generate", tags=["Carousel"])
async def generate_carousel_deck_legacy(prompt: AICarouselPrompt):
    topic = prompt.topic.strip() or "Automate Your Content Engine"
    slides = [
        {"id": "g1", "title": topic, "subtitle": "01 / 04", "body": "The definitive blueprint for high-impact creators.", "tag": "OVERVIEW"},
        {"id": "g2", "title": "The Repetitive Bottleneck", "subtitle": "02 / 04", "body": "Creators waste over 15 hours weekly manually formatting cross-platform content.", "tag": "PROBLEM"},
        {"id": "g3", "title": "The Unified Pipeline", "subtitle": "03 / 04", "body": "Feed one canonical asset into Reflow to generate native formats everywhere.", "tag": "SOLUTION"},
        {"id": "g4", "title": "Start Automating", "subtitle": "04 / 04", "body": "Deploy locally with Docker and own your data and distribution end-to-end.", "tag": "ACTION"}
    ]
    return {"slides": slides}

# Legacy repurpose endpoint adapter for backward compatibility
@app.post("/api/repurpose/generate", tags=["Repurpose"])
async def generate_repurpose(req: RepurposeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == req.content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    # Generate ContentBrief & Platform Contents
    platforms = [d.upper() for d in req.destinations]
    generated_items = await ai_service.generate_platform_content(
        content_id=req.content_id,
        platforms=platforms
    )
    outputs = {}
    for g in generated_items:
        outputs[g.platform.lower()] = g.payload

    return {
        "content_id": req.content_id,
        "target_format": req.target_format,
        "outputs": outputs
    }

# ------------------------------------------------------------------------------
# Phase 5 Intelligent Clip Engine API
# ------------------------------------------------------------------------------

@app.post("/api/content/{content_id}/clips/discover", response_model=ApiResponse, tags=["Clips"])
async def discover_content_clips(
    content_id: str,
    req: ClipDiscoveryRequest = ClipDiscoveryRequest(),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    if content.content_type != "VIDEO":
        raise HTTPException(status_code=400, detail="Clip discovery is only supported for video content.")

    # Enqueue background job
    job_id = f"job_clip_disc_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        content_id=content_id,
        type="CLIP_DISCOVERY",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=content_id,
        asset_id=None,
        job_type="CLIP_DISCOVERY",
        min_duration=req.min_duration,
        max_duration=req.max_duration,
        target_count=req.target_count,
        force_refresh=req.force_refresh
    )

    logger.info(f"Enqueued CLIP_DISCOVERY job {job_id} for Content {content_id}.")
    return ApiResponse(status="success", message=f"Clip discovery queued (Job {job_id}).")

@app.get("/api/content/{content_id}/clips", response_model=ClipListResponse, tags=["Clips"])
async def list_content_clips(content_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    clips = await fetch_content_clips(db, content_id)
    return {
        "items": [ClipResponse.model_validate(c) for c in clips],
        "total": len(clips)
    }

@app.get("/api/clips/{clip_id}", response_model=ClipResponse, tags=["Clips"])
async def get_clip(clip_id: str, db: AsyncSession = Depends(get_db)):
    clip = await fetch_full_clip(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")
    return ClipResponse.model_validate(clip)

@app.put("/api/clips/{clip_id}", response_model=ClipResponse, tags=["Clips"])
async def update_clip(clip_id: str, req: ClipUpdateRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    if req.title is not None:
        clip.title = req.title.strip()
    if req.hook is not None:
        clip.hook = req.hook.strip()
    if req.start_time is not None:
        if req.start_time < 0:
            raise HTTPException(status_code=400, detail="Start time cannot be negative.")
        clip.start_time = float(req.start_time)
    if req.end_time is not None:
        if req.end_time <= clip.start_time:
            raise HTTPException(status_code=400, detail="End time must be greater than start time.")
        clip.end_time = float(req.end_time)

    clip.duration = round(clip.end_time - clip.start_time, 2)
    clip.updated_at = datetime.utcnow()
    await db.commit()

    full_clip = await fetch_full_clip(db, clip_id)
    return ClipResponse.model_validate(full_clip)

@app.post("/api/clips/{clip_id}/generate", response_model=ApiResponse, tags=["Clips"])
async def generate_clip(
    clip_id: str,
    req: ClipGenerateRequest = ClipGenerateRequest(),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    clip.status = "PROCESSING"
    await db.commit()

    # Enqueue background job
    job_id = f"job_clip_rnd_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        content_id=clip.content_id,
        type="CLIP_RENDER",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=clip.content_id,
        asset_id=clip.source_asset_id,
        job_type="CLIP_RENDER",
        clip_id=clip_id,
        aspect_ratios=req.aspect_ratios,
        include_thumbnail=req.include_thumbnail
    )

    logger.info(f"Enqueued CLIP_RENDER job {job_id} for Clip {clip_id}.")
    return ApiResponse(status="success", message=f"Clip generation queued (Job {job_id}).")

@app.delete("/api/clips/{clip_id}", tags=["Clips"])
async def delete_clip(clip_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    for var in clip.variants:
        try: await storage_service.delete(var.storage_key)
        except Exception: pass
    if clip.thumbnail_path:
        try: await storage_service.delete(clip.thumbnail_path)
        except Exception: pass

    await db.delete(clip)
    await db.commit()
    logger.info(f"Deleted Clip {clip_id} and all related physical media variants.")
    return {"status": "success", "message": f"Clip {clip_id} deleted."}

@app.get("/api/clips/{clip_id}/variant/{variant_id}", tags=["Clips"])
async def stream_clip_variant(clip_id: str, variant_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(ClipVariant).where(ClipVariant.id == variant_id, ClipVariant.clip_id == clip_id)
    )
    variant = res.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Clip variant not found.")

    real_path = storage_service.get_real_path(variant.storage_key)
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Clip variant physical file missing.")

    return FileResponse(real_path, media_type=variant.mime_type)

@app.get("/api/clips/{clip_id}/stream", tags=["Clips"])
async def stream_clip_primary(clip_id: str, db: AsyncSession = Depends(get_db)):
    clip = await fetch_full_clip(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    target_var = next((v for v in clip.variants if v.variant_type in ["VERTICAL_9_16", "MASTER"]), None)
    if not target_var and clip.variants:
        target_var = clip.variants[0]

    if not target_var:
        raise HTTPException(status_code=404, detail="No media variant available for this clip.")

    real_path = storage_service.get_real_path(target_var.storage_key)
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Clip physical media missing.")

    return FileResponse(real_path, media_type=target_var.mime_type)

# ------------------------------------------------------------------------------
# Platform Connections & Publishing (Phase 5)
# ------------------------------------------------------------------------------

@app.get("/api/connections", tags=["Connections"])
async def list_connections():
    return [
        {"id": "youtube", "name": "YouTube", "handle": "@JayantOlhyan", "connected": True, "capabilities": ["Video", "Shorts", "Thumbnails", "Scheduling"]},
        {"id": "instagram", "name": "Instagram", "handle": "@jayantolhyan", "connected": True, "capabilities": ["Reels", "Carousels", "Images", "Scheduling"]},
        {"id": "tiktok", "name": "TikTok", "handle": "@jayant.olhyan", "connected": True, "capabilities": ["Videos", "Captions", "Scheduling"]},
        {"id": "linkedin", "name": "LinkedIn", "handle": "Jayant Olhyan", "connected": True, "capabilities": ["Posts", "Carousels (PDF)", "Videos", "Scheduling"]},
        {"id": "x", "name": "X (Twitter)", "handle": "@JayantOlhyan", "connected": True, "capabilities": ["Tweets", "Threads", "Media", "Scheduling"]},
        {"id": "facebook", "name": "Facebook", "handle": "", "connected": False, "capabilities": ["Posts", "Videos", "Images", "Scheduling"]},
        {"id": "pinterest", "name": "Pinterest", "handle": "", "connected": False, "capabilities": ["Pins", "Idea Pins", "Scheduling"]},
        {"id": "threads", "name": "Threads", "handle": "", "connected": False, "capabilities": ["Text", "Media", "Scheduling"]}
    ]

@app.post("/api/publish", tags=["Publishing"])
async def publish_content(platform: str):
    return {
        "status": "not_implemented",
        "platform": platform,
        "operation": "publish",
        "message": "Real publishing integration is not implemented yet. Scheduled for Phase 5."
    }

@app.post("/api/schedule", tags=["Publishing"])
async def schedule_content(req: SchedulePostRequest):
    return {
        "status": "not_implemented",
        "platform": req.platform,
        "operation": "schedule",
        "message": "Real platform scheduling integration is not implemented yet. Scheduled for Phase 5."
    }

# ------------------------------------------------------------------------------
# Workflows & System Telemetry
# ------------------------------------------------------------------------------

@app.post("/api/workflows/{workflow_id}/run", tags=["Workflows"])
async def run_workflow_simulation(workflow_id: str):
    return {
        "status": "simulated",
        "workflow_id": workflow_id,
        "message": f"Workflow {workflow_id} simulated successfully. Real execution engine scheduled for Phase 6."
    }

@app.get("/api/system/jobs", tags=["System"])
async def list_system_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(20))
    jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "type": j.type,
            "status": j.status,
            "attempts": j.attempts,
            "error": j.error,
            "created_at": j.created_at.isoformat() if j.created_at else None
        }
        for j in jobs
    ]

@app.get("/api/system/logs", tags=["System"])
async def list_system_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemLog).order_by(SystemLog.created_at.desc()).limit(50))
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "level": l.level,
            "service": l.service,
            "message": l.message,
            "timestamp": l.created_at.strftime("%H:%M:%S") if l.created_at else "00:00:00"
        }
        for l in logs
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
