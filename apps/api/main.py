import sys
import os
import io
import json
import uuid
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form, Query, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.orm import selectinload
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional

from config import settings
from database import get_db, init_db
from models.entities import (
    Content, Asset, ContentVariant, Transcript, TranscriptSegment,
    ContentBrief, GeneratedContent, Carousel, CarouselSlide, SlideElement, CarouselExport,
    Clip, ClipVariant, PlatformConnection, Publication, Workflow, Job, SystemLog,
    PerformanceInsight, ContentPattern, ContentRecommendation, Experiment, ExperimentVariant, ExperimentResult,
    AutomationRule, AutomationExecution, AutomationActionExecution, Notification
)
from models.schemas import (
    NotificationResponse, NotificationListResponse, GlobalSearchResultItem, GlobalSearchResponse,
    ContentResponse, ContentListResponse, TextContentCreateRequest,
    TranscriptResponse, ContentBriefResponse, GeneratedContentResponse,
    AIGenerateRequest, RepurposeRequest, AICarouselPrompt, SchedulePostRequest,
    PlatformConnectionSchema, PlatformConnectionUpdate, HealthResponse, ApiResponse,
    JobResponse, CarouselResponse, CarouselListResponse, CarouselCreateRequest,
    CarouselUpdateRequest, SlideCreateRequest, SlideUpdateRequest, SlideReorderRequest,
    CarouselGenerateRequest, CarouselExportResponse,
    ClipResponse, ClipListResponse, ClipDiscoveryRequest, ClipUpdateRequest,
    ClipGenerateRequest, ClipVariantResponse,
    CaptionCueSchema, ClipCaptionsResponse, ClipCaptionsUpdateRequest, ClipCaptionRenderRequest,
    PlatformConnectionResponse, PlatformConnectionListResponse, OAuthStartResponse,
    PublicationCreateRequest, PublicationResponse, PublicationListResponse,
    BatchPublicationCreateRequest, BatchPublicationResponse, PublicationDestinationItem,
    ScheduleDestinationItem, SchedulePublicationCreateRequest, SchedulePublicationResponse,
    RescheduleRequest, CalendarEventItem, CalendarResponse,
    PostMetricSnapshotResponse, PublicationAnalyticsResponse, AnalyticsOverviewResponse,
    AnalyticsTimeseriesItem, AnalyticsTimeseriesResponse, PlatformAnalyticsItem,
    ContentAnalyticsItem, AnalyticsBackfillRequest, AnalyticsBackfillResponse,
    PerformanceInsightResponse, ContentPatternResponse, ContentRecommendationResponse,
    ExperimentResponse, TopicPerformanceItem, HookPerformanceItem,
    DurationPerformanceItem, PostingWindowItem, ContentGapItem,
    IntelligenceOverviewResponse, IntelligenceRefreshResponse,
    ExperimentVariantSchema, ExperimentResultResponse, ExperimentWarningSchema,
    ExperimentDetailResponse, ExperimentCreateRequest,
    AutomationRuleCreateRequest, AutomationRuleResponse, AutomationActionExecutionResponse,
    AutomationExecutionResponse, AutomationDetailResponse
)
from services.media_service import media_processor
from services.queue_service import queue_service
from services.ai_service import ai_service
from services.carousel_renderer import carousel_renderer
from services.carousel_helper import fetch_full_carousel
from services.clip_helper import fetch_full_clip, fetch_content_clips
from services.caption_service import caption_service
from services.publishing_service import publishing_service
from services.scheduler_service import scheduler_service
from services.analytics_service import analytics_service
from services.intelligence_service import intelligence_service
from connectors.youtube import youtube_oauth, youtube_connector
from services.encryption_service import encryption_service
from services.health_service import health_service
from services.storage_service import storage_service, validate_upload, generate_storage_key
from utils.logging import get_logger

logger = get_logger("ReflowAPI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Reflow API starting up... Initializing database schema.")
    await init_db()
    from plugins.loader import register_builtin_plugins
    register_builtin_plugins()
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
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import time
from collections import defaultdict

_rate_limit_store = defaultdict(list)

# Request ID, Rate Limiting & /api/v1 Path Aliasing Middleware
@app.middleware("http")
async def request_tracing_and_rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1/system"):
        request.scope["path"] = request.url.path.replace("/api/v1/system", "/api/system", 1)

    req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
    request.state.request_id = req_id

    # Rate limiting for heavy creation/processing routes
    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path
    if any(path.startswith(prefix) for prefix in ["/api/uploads", "/api/ai", "/api/clips", "/api/carousels", "/api/publications"]):
        now = time.time()
        window = 60.0
        max_requests = settings.RATE_LIMIT_PER_MINUTE
        history = [t for t in _rate_limit_store[client_ip] if now - t < window]
        if len(history) >= max_requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded ({max_requests} requests/min). Please try again shortly.",
                    "request_id": req_id
                },
                headers={"X-Request-ID": req_id}
            )
        history.append(now)
        _rate_limit_store[client_ip] = history

    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response

# Centralized Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", "unknown")
    detail = exc.detail
    if isinstance(detail, dict):
        error_code = detail.get("error", "HTTP_ERROR")
        message = detail.get("message", str(detail))
    else:
        error_code = "HTTP_ERROR"
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_code, "message": message, "request_id": req_id},
        headers={"X-Request-ID": req_id}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", "unknown")
    clean_errors = []
    for err in exc.errors():
        err_copy = dict(err)
        if "input" in err_copy and isinstance(err_copy["input"], bytes):
            err_copy["input"] = "[binary_data]"
        if "ctx" in err_copy and isinstance(err_copy["ctx"], dict):
            err_copy["ctx"] = {k: str(v) if isinstance(v, bytes) else v for k, v in err_copy["ctx"].items()}
        clean_errors.append(err_copy)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request payload.",
            "details": clean_errors,
            "request_id": req_id
        },
        headers={"X-Request-ID": req_id}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{req_id}] Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred.",
            "request_id": req_id
        },
        headers={"X-Request-ID": req_id}
    )

# ------------------------------------------------------------------------------
# Health & System Telemetry Checks
# ------------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def liveness_probe():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@app.get("/health/ready", tags=["System"])
async def readiness_probe():
    return await health_service.get_readiness_status()

@app.get("/api/system/health", tags=["System"])
async def system_health_telemetry():
    return await health_service.get_overall_health()

@app.get("/api/system/metrics", tags=["System"])
async def system_metrics():
    return await health_service.get_system_metrics()

@app.get("/api/system/settings", tags=["System"])
async def get_system_settings():
    return {
        "status": "success",
        "settings": {
            "gemini_configured": bool(settings.GEMINI_API_KEY),
            "openai_configured": bool(settings.OPENAI_API_KEY),
            "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
            "storage_provider": settings.STORAGE_PROVIDER,
            "storage_dir": settings.STORAGE_DIR,
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            "deployment_mode": settings.DEPLOYMENT_MODE,
            "version": settings.APP_VERSION
        }
    }

@app.post("/api/system/settings", tags=["System"])
async def update_system_settings(payload: Dict[str, Any]):
    if "gemini_api_key" in payload:
        settings.GEMINI_API_KEY = payload["gemini_api_key"] or None
    if "openai_api_key" in payload:
        settings.OPENAI_API_KEY = payload["openai_api_key"] or None
    if "anthropic_api_key" in payload:
        settings.ANTHROPIC_API_KEY = payload["anthropic_api_key"] or None
    if "storage_provider" in payload and payload["storage_provider"]:
        settings.STORAGE_PROVIDER = payload["storage_provider"]
    return {
        "status": "success",
        "message": "System settings updated successfully."
    }

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

    # Phase 9: Block deletion if active future scheduled publications exist
    now_utc = datetime.utcnow()
    res_sch = await db.execute(
        select(Publication).where(
            Publication.content_id == content_id,
            Publication.status == "SCHEDULED",
            Publication.scheduled_at >= now_utc
        )
    )
    scheduled_pubs = res_sch.scalars().all()
    if scheduled_pubs:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete content: {len(scheduled_pubs)} active scheduled publication(s) exist. Cancel scheduled posts before deleting content."
        )

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
    if req.caption_style is not None:
        clip.caption_style = req.caption_style
    if req.caption_enabled is not None:
        clip.caption_enabled = req.caption_enabled
    if req.highlight_keywords is not None:
        clip.highlight_keywords_json = json.dumps(req.highlight_keywords)

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
    if req.caption_style:
        clip.caption_style = req.caption_style
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
        include_thumbnail=req.include_thumbnail,
        burn_captions=req.burn_captions,
        caption_style=req.caption_style or clip.caption_style,
        highlight_keywords=clip.highlight_keywords
    )

    logger.info(f"Enqueued CLIP_RENDER job {job_id} for Clip {clip_id} (Burn Captions: {req.burn_captions}).")
    return ApiResponse(status="success", message=f"Clip generation queued (Job {job_id}).")

@app.get("/api/clips/{clip_id}/captions", response_model=ClipCaptionsResponse, tags=["Captions"])
async def get_clip_captions(clip_id: str, db: AsyncSession = Depends(get_db)):
    clip = await fetch_full_clip(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    t_res = await db.execute(select(Transcript).where(Transcript.content_id == clip.content_id))
    transcript = t_res.scalar_one_or_none()

    segments_data = []
    if transcript and transcript.segments:
        segments_data = [
            {"start_time": s.start_time, "end_time": s.end_time, "text": s.text}
            for s in transcript.segments
        ]

    cues = caption_service.generate_cues_from_segments(
        clip_start=clip.start_time,
        clip_end=clip.end_time,
        segments=segments_data,
        highlight_keywords=clip.highlight_keywords
    )

    srt_text = caption_service.build_srt(cues)
    vtt_text = caption_service.build_vtt(cues)

    return ClipCaptionsResponse(
        clip_id=clip_id,
        caption_style=clip.caption_style or "BOLD_PUNCH",
        caption_enabled=clip.caption_enabled,
        highlight_keywords=clip.highlight_keywords,
        cues=[CaptionCueSchema(start_time=c.start_time, end_time=c.end_time, text=c.text, highlight_words=c.highlight_words) for c in cues],
        srt_content=srt_text,
        vtt_content=vtt_text
    )

@app.put("/api/clips/{clip_id}/captions", response_model=ClipCaptionsResponse, tags=["Captions"])
async def update_clip_captions(clip_id: str, req: ClipCaptionsUpdateRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    if req.caption_style is not None:
        clip.caption_style = req.caption_style
    if req.caption_enabled is not None:
        clip.caption_enabled = req.caption_enabled
    if req.highlight_keywords is not None:
        clip.highlight_keywords_json = json.dumps(req.highlight_keywords)
    if req.custom_settings is not None:
        clip.caption_custom_settings_json = json.dumps(req.custom_settings)

    clip.updated_at = datetime.utcnow()
    await db.commit()

    return await get_clip_captions(clip_id, db)

@app.get("/api/clips/{clip_id}/captions/export.srt", tags=["Captions"])
async def export_clip_srt(clip_id: str, db: AsyncSession = Depends(get_db)):
    caps = await get_clip_captions(clip_id, db)
    return PlainTextResponse(
        content=caps.srt_content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="clip_{clip_id}.srt"'}
    )

@app.get("/api/clips/{clip_id}/captions/export.vtt", tags=["Captions"])
async def export_clip_vtt(clip_id: str, db: AsyncSession = Depends(get_db)):
    caps = await get_clip_captions(clip_id, db)
    return PlainTextResponse(
        content=caps.vtt_content,
        media_type="text/vtt"
    )

@app.post("/api/clips/{clip_id}/render-captions", response_model=ApiResponse, tags=["Captions"])
async def render_clip_captions(
    clip_id: str,
    req: ClipCaptionRenderRequest = ClipCaptionRenderRequest(),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    clip.status = "PROCESSING"
    if req.caption_style:
        clip.caption_style = req.caption_style
    if req.highlight_keywords is not None:
        clip.highlight_keywords_json = json.dumps(req.highlight_keywords)
    await db.commit()

    # Enqueue background caption render job
    job_id = f"job_clip_cap_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        content_id=clip.content_id,
        type="CLIP_CAPTION_RENDER",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=clip.content_id,
        asset_id=clip.source_asset_id,
        job_type="CLIP_CAPTION_RENDER",
        clip_id=clip_id,
        aspect_ratios=req.aspect_ratios,
        include_thumbnail=True,
        burn_captions=True,
        caption_style=req.caption_style or clip.caption_style,
        highlight_keywords=req.highlight_keywords or clip.highlight_keywords
    )

    logger.info(f"Enqueued CLIP_CAPTION_RENDER job {job_id} for Clip {clip_id}.")
    return ApiResponse(status="success", message=f"Caption render queued (Job {job_id}).")

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
async def stream_clip_primary(clip_id: str, prefer_captions: bool = False, db: AsyncSession = Depends(get_db)):
    clip = await fetch_full_clip(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    target_var = None
    if prefer_captions:
        target_var = next((v for v in clip.variants if v.has_captions and "9_16" in v.variant_type), None)
        if not target_var:
            target_var = next((v for v in clip.variants if v.has_captions), None)

    if not target_var:
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

# ------------------------------------------------------------------------------
# Platform Connections & Publishing (Phase 7 & 8)
# ------------------------------------------------------------------------------

SUPPORTED_PLATFORMS = [
    {"id": "youtube", "name": "YouTube", "platform": "youtube", "capabilities": ["video_upload", "scheduled_publish"]},
    {"id": "instagram", "name": "Instagram", "platform": "instagram", "capabilities": ["video_upload", "image_upload", "carousel_upload"]},
    {"id": "linkedin", "name": "LinkedIn", "platform": "linkedin", "capabilities": ["text_post", "image_upload", "video_upload", "carousel_upload"]},
    {"id": "x", "name": "X (Twitter)", "platform": "x", "capabilities": ["text_post", "image_upload", "video_upload"]},
    {"id": "facebook", "name": "Facebook", "platform": "facebook", "capabilities": ["text_post", "image_upload", "video_upload"]},
    {"id": "tiktok", "name": "TikTok", "platform": "tiktok", "capabilities": ["video_upload"]},
    {"id": "pinterest", "name": "Pinterest", "platform": "pinterest", "capabilities": ["image_upload", "video_upload"]},
    {"id": "threads", "name": "Threads", "platform": "threads", "capabilities": ["text_post", "image_upload", "video_upload", "carousel_upload"]}
]

@app.get("/api/connections", response_model=PlatformConnectionListResponse, tags=["Connections"])
async def list_platform_connections(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PlatformConnection).order_by(PlatformConnection.created_at.asc()))
    existing = {conn.platform: conn for conn in res.scalars().all()}

    # Ensure records exist for standard platforms
    conns_to_return = []
    for p in SUPPORTED_PLATFORMS:
        pid = p["platform"]
        if pid in existing:
            conns_to_return.append(existing[pid])
        else:
            # Seed default disconnected record
            new_conn = PlatformConnection(
                id=f"conn_{pid}",
                platform=pid,
                name=p["name"],
                account_name="",
                handle="",
                status="DISCONNECTED",
                capabilities_json=json.dumps(p["capabilities"]),
                scopes_json=json.dumps([]),
                metadata_json=json.dumps({})
            )
            db.add(new_conn)
            await db.commit()
            await db.refresh(new_conn)
            conns_to_return.append(new_conn)

    return PlatformConnectionListResponse(
        items=[
            PlatformConnectionResponse(
                id=c.id,
                platform=c.platform,
                name=c.name,
                account_name=c.account_name or "",
                handle=c.handle or "",
                external_account_id=c.external_account_id,
                status=c.status,
                avatar_url=c.avatar_url or "",
                capabilities=c.capabilities,
                scopes=c.scopes,
                token_expires_at=c.token_expires_at,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in conns_to_return
        ],
        total=len(conns_to_return)
    )

@app.get("/api/connections/{connection_id}", response_model=PlatformConnectionResponse, tags=["Connections"])
async def get_platform_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PlatformConnection).where(PlatformConnection.id == connection_id))
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found.")

    return PlatformConnectionResponse(
        id=conn.id,
        platform=conn.platform,
        name=conn.name,
        account_name=conn.account_name or "",
        handle=conn.handle or "",
        external_account_id=conn.external_account_id,
        status=conn.status,
        avatar_url=conn.avatar_url or "",
        capabilities=conn.capabilities,
        scopes=conn.scopes,
        token_expires_at=conn.token_expires_at,
        created_at=conn.created_at,
        updated_at=conn.updated_at
    )

@app.post("/api/connections/{platform}/start", response_model=OAuthStartResponse, tags=["Connections"])
async def start_platform_oauth(platform: str):
    """Generates an authorization URL with single-use CSRF state for any supported platform."""
    provider = publishing_service.get_oauth_provider(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f"OAuth provider for platform '{platform}' not found.")

    state = publishing_service.create_oauth_state(platform=platform, ttl_minutes=15)
    auth_url = provider.get_authorization_url(state=state)
    return OAuthStartResponse(platform=platform, authorization_url=auth_url, state=state)

@app.get("/api/connections/{platform}/callback", tags=["Connections"])
async def platform_oauth_callback(
    platform: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handles OAuth 2.0 redirect callback, validates state, and securely persists encrypted credentials."""
    if error:
        logger.warning(f"{platform} OAuth authorization error returned: {error}")
        return RedirectResponse(url=f"http://localhost:3000/connections?error={error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required authorization code or state.")

    # Validate and consume single-use state token
    is_valid_state = publishing_service.validate_and_consume_oauth_state(state=state, expected_platform=platform)
    if not is_valid_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state parameter. Possible CSRF attempt.")

    provider = publishing_service.get_oauth_provider(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f"OAuth provider for platform '{platform}' not found.")

    try:
        # Exchange authorization code for token dictionary
        token_data = await provider.exchange_code(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # Retrieve identity from Platform API
        account_info = await provider.fetch_account_info(access_token)

        # Encrypt tokens before storing in database
        enc_access = encryption_service.encrypt_token(access_token)
        enc_refresh = encryption_service.encrypt_token(refresh_token) if refresh_token else None
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Upsert PlatformConnection for Platform
        res = await db.execute(select(PlatformConnection).where(PlatformConnection.platform == platform))
        conn = res.scalar_one_or_none()
        if not conn:
            conn = PlatformConnection(
                id=f"conn_{platform}_{uuid.uuid4().hex[:8]}",
                platform=platform,
                name=platform.capitalize()
            )
            db.add(conn)

        conn.account_name = account_info.get("account_name", f"{platform.capitalize()} Account")
        conn.handle = account_info.get("handle", "")
        conn.external_account_id = account_info.get("external_account_id")
        conn.avatar_url = account_info.get("avatar_url", "")
        conn.status = "CONNECTED"
        conn.access_token_encrypted = enc_access
        if enc_refresh:
            conn.refresh_token_encrypted = enc_refresh
        conn.token_expires_at = expires_at

        connector = publishing_service.get_connector(platform)
        if connector:
            caps = connector.get_capabilities()
            cap_list = []
            if caps.video_upload: cap_list.append("video_upload")
            if caps.image_upload: cap_list.append("image_upload")
            if caps.carousel_upload: cap_list.append("carousel_upload")
            if caps.text_post: cap_list.append("text_post")
            if caps.scheduled_publish: cap_list.append("scheduled_publish")
            conn.capabilities_json = json.dumps(cap_list)

        conn.metadata_json = json.dumps(account_info.get("metadata", {}))
        conn.updated_at = datetime.utcnow()

        await db.commit()
        logger.info(f"Successfully connected {platform} account '{conn.account_name}' ({conn.handle}).")

        # Redirect user back to frontend connections page with success indicator
        return RedirectResponse(url=f"http://localhost:3000/connections?connected={platform}")

    except Exception as e:
        logger.error(f"{platform} OAuth callback processing failed: {e}")
        return RedirectResponse(url=f"http://localhost:3000/connections?error=auth_failed")

@app.post("/api/connections/{connection_id}/disconnect", tags=["Connections"])
async def disconnect_platform_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    """Revokes credentials and disconnects account while strictly preserving publication history."""
    res = await db.execute(select(PlatformConnection).where(PlatformConnection.id == connection_id))
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    # Try to revoke token on provider
    if conn.access_token_encrypted:
        try:
            token = encryption_service.decrypt_token(conn.access_token_encrypted)
            provider = publishing_service.get_oauth_provider(conn.platform)
            if provider:
                await provider.revoke_token(token)
        except Exception as e:
            logger.warning(f"Non-fatal error revoking token on disconnect: {e}")

    conn.access_token_encrypted = None
    conn.refresh_token_encrypted = None
    conn.status = "DISCONNECTED"
    conn.updated_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Connection {connection_id} ({conn.platform}) disconnected successfully.")
    return {"status": "success", "message": f"Connection {connection_id} disconnected."}

@app.post("/api/connections/{connection_id}/refresh", response_model=ApiResponse, tags=["Connections"])
async def refresh_connection_token(connection_id: str, db: AsyncSession = Depends(get_db)):
    """Forces immediate access token refresh."""
    res = await db.execute(select(PlatformConnection).where(PlatformConnection.id == connection_id))
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    try:
        await publishing_service.get_valid_access_token(conn, db)
        return ApiResponse(status="success", message="Token refreshed successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {e}")

# ------------------------------------------------------------------------------
# Publications API
# ------------------------------------------------------------------------------

@app.post("/api/publications", response_model=PublicationResponse, tags=["Publications"])
async def create_publication(req: PublicationCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    Creates a publication intent, performs pre-upload validation and idempotency check,
    and enqueues the asynchronous PLATFORM_PUBLISH job.
    """
    # 1. Verify Platform Connection
    res_conn = await db.execute(select(PlatformConnection).where(PlatformConnection.id == req.platform_connection_id))
    conn = res_conn.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Platform connection not found.")
    if conn.status != "CONNECTED":
        raise HTTPException(status_code=400, detail=f"Connection is in '{conn.status}' state. Reconnect required.")

    connector = publishing_service.get_connector(conn.platform)
    if not connector:
        raise HTTPException(status_code=501, detail={"code": "NOT_IMPLEMENTED", "message": f"Platform '{conn.platform}' is not implemented yet."})

    # 2. Pre-validate metadata against platform connector
    valid, err = connector.validate_metadata({
        "title": req.title,
        "description": req.description,
        "caption": req.description,
        "tags": req.tags,
        "privacy": req.privacy
    })
    if not valid:
        raise HTTPException(status_code=422, detail={"field": "metadata", "code": "VALIDATION_ERROR", "message": err})

    # 3. Compute Idempotency Hash
    payload_hash = publishing_service.compute_idempotency_hash(
        content_id=req.content_id,
        variant_id=req.variant_id,
        platform_connection_id=req.platform_connection_id,
        title=req.title,
        privacy=req.privacy
    )

    # 4. Check for Existing Publication (Idempotency Safety)
    existing_res = await db.execute(
        select(Publication).where(Publication.request_payload_hash == payload_hash).order_by(Publication.created_at.desc())
    )
    existing_pub = existing_res.scalars().first()
    if existing_pub and existing_pub.status in ["PUBLISHED", "UPLOADING", "QUEUED"]:
        logger.info(f"Idempotent publication request matched existing publication {existing_pub.id} (Status: {existing_pub.status}).")
        return PublicationResponse(
            id=existing_pub.id,
            content_id=existing_pub.content_id,
            variant_id=existing_pub.variant_id,
            platform_connection_id=existing_pub.platform_connection_id,
            platform=existing_pub.platform,
            status=existing_pub.status,
            title=existing_pub.title,
            description=existing_pub.description,
            privacy=existing_pub.privacy,
            tags=existing_pub.tags,
            external_post_id=existing_pub.external_post_id,
            external_url=existing_pub.external_url,
            error_code=existing_pub.error_code,
            error_message=existing_pub.error_message,
            attempt_count=existing_pub.attempt_count,
            created_at=existing_pub.created_at,
            updated_at=existing_pub.updated_at,
            published_at=existing_pub.published_at
        )

    # 5. Create Publication Record
    pub_id = f"pub_{uuid.uuid4().hex[:10]}"
    publication = Publication(
        id=pub_id,
        content_id=req.content_id,
        variant_id=req.variant_id,
        platform_connection_id=req.platform_connection_id,
        platform=conn.platform,
        status="QUEUED",
        title=req.title.strip(),
        description=(req.description or "").strip(),
        privacy=req.privacy.upper(),
        tags_json=json.dumps(req.tags),
        request_payload_hash=payload_hash,
        created_at=datetime.utcnow()
    )
    db.add(publication)
    await db.commit()
    await db.refresh(publication)

    # 6. Enqueue Background PLATFORM_PUBLISH Job
    job_id = f"job_pub_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        content_id=req.content_id,
        type="PLATFORM_PUBLISH",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=req.content_id,
        job_type="PLATFORM_PUBLISH",
        publication_id=pub_id
    )

    logger.info(f"Queued publication {pub_id} to {conn.platform} (Job {job_id}).")

    return PublicationResponse(
        id=publication.id,
        content_id=publication.content_id,
        variant_id=publication.variant_id,
        platform_connection_id=publication.platform_connection_id,
        platform=publication.platform,
        status=publication.status,
        title=publication.title,
        description=publication.description,
        privacy=publication.privacy,
        tags=publication.tags,
        external_post_id=publication.external_post_id,
        external_url=publication.external_url,
        error_code=publication.error_code,
        error_message=publication.error_message,
        attempt_count=publication.attempt_count,
        created_at=publication.created_at,
        updated_at=publication.updated_at,
        published_at=publication.published_at
    )

@app.post("/api/publications/batch", response_model=BatchPublicationResponse, tags=["Publications"])
async def create_batch_publications(req: BatchPublicationCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    Creates independent publication records and background jobs for multiple destinations in a single operation.
    Independent isolation: one destination failure will not prevent other destinations from executing.
    """
    created_pubs = []
    for dest in req.destinations:
        res_conn = await db.execute(select(PlatformConnection).where(PlatformConnection.id == dest.platform_connection_id))
        conn = res_conn.scalar_one_or_none()
        if not conn:
            continue

        title = (dest.title or "").strip() or "Reflow Social Post"
        desc = (dest.description or "").strip()
        privacy = (dest.privacy or "PRIVATE").upper()
        tags = dest.tags or []

        # Validate with connector
        connector = publishing_service.get_connector(conn.platform)
        if connector:
            valid, _ = connector.validate_metadata({"title": title, "description": desc, "caption": desc, "tags": tags})
            if not valid:
                logger.warning(f"Batch publish metadata validation warning for {conn.platform}")

        payload_hash = publishing_service.compute_idempotency_hash(
            content_id=req.content_id,
            variant_id=req.variant_id,
            platform_connection_id=conn.id,
            title=title,
            privacy=privacy
        )

        # Check existing publication
        existing_res = await db.execute(
            select(Publication).where(Publication.request_payload_hash == payload_hash).order_by(Publication.created_at.desc())
        )
        existing_pub = existing_res.scalars().first()
        if existing_pub and existing_pub.status in ["PUBLISHED", "UPLOADING", "QUEUED"]:
            created_pubs.append(PublicationResponse.model_validate(existing_pub))
            continue

        # Create new independent publication
        pub_id = f"pub_{uuid.uuid4().hex[:10]}"
        publication = Publication(
            id=pub_id,
            content_id=req.content_id,
            variant_id=req.variant_id,
            platform_connection_id=conn.id,
            platform=conn.platform,
            status="QUEUED" if conn.status == "CONNECTED" else "FAILED",
            error_code=None if conn.status == "CONNECTED" else "AUTH_ERROR",
            error_message=None if conn.status == "CONNECTED" else "Connection not in CONNECTED state",
            title=title,
            description=desc,
            privacy=privacy,
            tags_json=json.dumps(tags),
            request_payload_hash=payload_hash,
            created_at=datetime.utcnow()
        )
        db.add(publication)
        await db.commit()
        await db.refresh(publication)

        if conn.status == "CONNECTED":
            # Enqueue independent job
            job_id = f"job_pub_{uuid.uuid4().hex[:8]}"
            job = Job(
                id=job_id,
                content_id=req.content_id,
                type="PLATFORM_PUBLISH",
                status="QUEUED",
                created_at=datetime.utcnow()
            )
            db.add(job)
            await db.commit()

            await queue_service.enqueue_media_job(
                job_id=job_id,
                content_id=req.content_id,
                job_type="PLATFORM_PUBLISH",
                publication_id=pub_id
            )

        created_pubs.append(PublicationResponse.model_validate(publication))

    return BatchPublicationResponse(
        publications=created_pubs,
        queued_count=len([p for p in created_pubs if p.status == "QUEUED"])
    )

@app.get("/api/publications", response_model=PublicationListResponse, tags=["Publications"])
async def list_publications(
    content_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(Publication).order_by(Publication.created_at.desc())
    if content_id:
        query = query.where(Publication.content_id == content_id)

    res = await db.execute(query)
    pubs = res.scalars().all()

    return PublicationListResponse(
        items=[
            PublicationResponse(
                id=p.id,
                content_id=p.content_id,
                variant_id=p.variant_id,
                platform_connection_id=p.platform_connection_id,
                platform=p.platform,
                status=p.status,
                title=p.title,
                description=p.description,
                privacy=p.privacy,
                tags=p.tags,
                external_post_id=p.external_post_id,
                external_url=p.external_url,
                error_code=p.error_code,
                error_message=p.error_message,
                attempt_count=p.attempt_count,
                created_at=p.created_at,
                updated_at=p.updated_at,
                published_at=p.published_at
            )
            for p in pubs
        ],
        total=len(pubs)
    )

@app.get("/api/publications/{publication_id}", response_model=PublicationResponse, tags=["Publications"])
async def get_publication(publication_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Publication).where(Publication.id == publication_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Publication not found.")

    return PublicationResponse(
        id=p.id,
        content_id=p.content_id,
        variant_id=p.variant_id,
        platform_connection_id=p.platform_connection_id,
        platform=p.platform,
        status=p.status,
        title=p.title,
        description=p.description,
        privacy=p.privacy,
        tags=p.tags,
        external_post_id=p.external_post_id,
        external_url=p.external_url,
        error_code=p.error_code,
        error_message=p.error_message,
        attempt_count=p.attempt_count,
        created_at=p.created_at,
        updated_at=p.updated_at,
        published_at=p.published_at
    )

@app.post("/api/publications/{publication_id}/retry", response_model=PublicationResponse, tags=["Publications"])
async def retry_publication(publication_id: str, db: AsyncSession = Depends(get_db)):
    """Retries a failed publication."""
    res = await db.execute(select(Publication).where(Publication.id == publication_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Publication not found.")

    if p.status == "PUBLISHED":
        raise HTTPException(status_code=400, detail="Publication has already been successfully published.")

    p.status = "QUEUED"
    p.error_code = None
    p.error_message = None
    p.updated_at = datetime.utcnow()
    await db.commit()

    job_id = f"job_pub_retry_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        content_id=p.content_id,
        type="PLATFORM_PUBLISH",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=p.content_id,
        job_type="PLATFORM_PUBLISH",
        publication_id=p.id
    )

    logger.info(f"Retrying publication {p.id} (Job {job_id}).")

    return PublicationResponse(
        id=p.id,
        content_id=p.content_id,
        variant_id=p.variant_id,
        platform_connection_id=p.platform_connection_id,
        platform=p.platform,
        status=p.status,
        title=p.title,
        description=p.description,
        privacy=p.privacy,
        tags=p.tags,
        external_post_id=p.external_post_id,
        external_url=p.external_url,
        error_code=p.error_code,
        error_message=p.error_message,
        attempt_count=p.attempt_count,
        created_at=p.created_at,
        updated_at=p.updated_at,
        published_at=p.published_at
    )

@app.post("/api/publications/{publication_id}/cancel", response_model=PublicationResponse, tags=["Publications"])
async def cancel_publication(publication_id: str, db: AsyncSession = Depends(get_db)):
    """Cancels a pending scheduled or queued publication."""
    try:
        updated = await scheduler_service.cancel_publication(publication_id, db=db)
        return PublicationResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {e}")

# ------------------------------------------------------------------------------
# Phase 9: Real Scheduling & Content Calendar API
# ------------------------------------------------------------------------------

@app.post("/api/publications/schedule", response_model=SchedulePublicationResponse, tags=["Scheduling"])
async def schedule_publications_endpoint(req: SchedulePublicationCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    Schedules content for publication at a future date and time in the specified IANA timezone.
    Validates minimum lead time, converts local datetime to canonical UTC, and persists transactionally.
    """
    try:
        dest_dicts = [d.model_dump() for d in req.destinations]
        pubs = await scheduler_service.schedule_publications(
            content_id=req.content_id,
            destinations=dest_dicts,
            scheduled_time_str=req.scheduled_time,
            timezone_name=req.timezone,
            variant_id=req.variant_id,
            db=db
        )

        utc_time, _ = scheduler_service.parse_and_validate_schedule_time(
            req.scheduled_time,
            req.timezone,
            min_lead_seconds=0,
            enforce_future=False
        )

        return SchedulePublicationResponse(
            publications=[PublicationResponse.model_validate(p) for p in pubs],
            scheduled_count=len(pubs),
            scheduled_at_utc=utc_time,
            timezone=req.timezone
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Scheduling failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {e}")

@app.get("/api/publications/scheduled", response_model=PublicationListResponse, tags=["Scheduling"])
async def list_scheduled_publications(db: AsyncSession = Depends(get_db)):
    """Lists all upcoming scheduled and queued publications."""
    res = await db.execute(
        select(Publication)
        .where(Publication.status.in_(["SCHEDULED", "QUEUED"]))
        .order_by(Publication.scheduled_at.asc().nullslast(), Publication.created_at.desc())
    )
    pubs = res.scalars().all()
    return PublicationListResponse(
        items=[PublicationResponse.model_validate(p) for p in pubs],
        total=len(pubs)
    )

@app.get("/api/calendar", response_model=CalendarResponse, tags=["Scheduling"])
async def get_calendar_view(
    start: str = Query(..., description="Start date (YYYY-MM-DD or ISO datetime)"),
    end: str = Query(..., description="End date (YYYY-MM-DD or ISO datetime)"),
    timezone: str = Query("UTC", description="IANA timezone name"),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns calendar events for publications within the requested date/time window.
    Converts timestamps to the viewer's target timezone for display.
    """
    try:
        zi = scheduler_service.validate_timezone(timezone)
        start_clean = start.strip()
        if len(start_clean) == 10:
            start_clean += "T00:00:00"
        end_clean = end.strip()
        if len(end_clean) == 10:
            end_clean += "T23:59:59"

        start_dt_local = datetime.fromisoformat(start_clean).replace(tzinfo=zi)
        end_dt_local = datetime.fromisoformat(end_clean).replace(tzinfo=zi)

        start_utc = start_dt_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        end_utc = end_dt_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        events = await scheduler_service.get_calendar_events(
            start_utc=start_utc,
            end_utc=end_utc,
            view_timezone=timezone,
            platform=platform,
            status=status,
            db=db
        )

        return CalendarResponse(
            items=[CalendarEventItem(**ev) for ev in events],
            total=len(events),
            start_utc=start_utc,
            end_utc=end_utc,
            timezone=timezone
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Calendar query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Calendar query failed: {e}")

@app.post("/api/publications/{publication_id}/reschedule", response_model=PublicationResponse, tags=["Scheduling"])
async def reschedule_publication_endpoint(
    publication_id: str,
    req: RescheduleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reschedules a pending publication to a new target time."""
    try:
        updated = await scheduler_service.reschedule_publication(
            publication_id=publication_id,
            new_time_str=req.scheduled_time,
            timezone_name=req.timezone,
            db=db
        )
        return PublicationResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rescheduling error: {e}")

# ------------------------------------------------------------------------------
# Phase 10: Real Analytics & Performance Intelligence API
# ------------------------------------------------------------------------------

@app.get("/api/analytics/overview", response_model=AnalyticsOverviewResponse, tags=["Analytics"])
async def get_analytics_overview_endpoint(
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO)"),
    platform: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    now_utc = datetime.utcnow()
    s_date = datetime.fromisoformat(start) if start else (now_utc - timedelta(days=30))
    e_date = datetime.fromisoformat(end) if end else now_utc

    data = await analytics_service.get_overview_analytics(
        start_date=s_date,
        end_date=e_date,
        platform=platform,
        content_type=content_type,
        db=db
    )
    return AnalyticsOverviewResponse(**data)

@app.get("/api/analytics/timeseries", response_model=AnalyticsTimeseriesResponse, tags=["Analytics"])
async def get_analytics_timeseries_endpoint(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    now_utc = datetime.utcnow()
    s_date = datetime.fromisoformat(start) if start else (now_utc - timedelta(days=30))
    e_date = datetime.fromisoformat(end) if end else now_utc

    items = await analytics_service.get_timeseries_analytics(
        start_date=s_date,
        end_date=e_date,
        platform=platform,
        db=db
    )
    return AnalyticsTimeseriesResponse(
        items=[AnalyticsTimeseriesItem(**it) for it in items],
        total_days=len(items)
    )

@app.get("/api/analytics/platforms", response_model=List[PlatformAnalyticsItem], tags=["Analytics"])
async def get_platform_analytics_endpoint(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    now_utc = datetime.utcnow()
    s_date = datetime.fromisoformat(start) if start else (now_utc - timedelta(days=30))
    e_date = datetime.fromisoformat(end) if end else now_utc

    items = await analytics_service.get_platform_analytics(
        start_date=s_date,
        end_date=e_date,
        db=db
    )
    return [PlatformAnalyticsItem(**it) for it in items]

@app.get("/api/analytics/content", response_model=List[ContentAnalyticsItem], tags=["Analytics"])
async def get_content_analytics_endpoint(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    sort_by: str = Query("views"),
    db: AsyncSession = Depends(get_db)
):
    now_utc = datetime.utcnow()
    s_date = datetime.fromisoformat(start) if start else (now_utc - timedelta(days=30))
    e_date = datetime.fromisoformat(end) if end else now_utc

    items = await analytics_service.get_content_analytics(
        start_date=s_date,
        end_date=e_date,
        content_type=content_type,
        sort_by=sort_by,
        db=db
    )
    return [ContentAnalyticsItem(**it) for it in items]

@app.get("/api/analytics/publications/{publication_id}", response_model=PublicationAnalyticsResponse, tags=["Analytics"])
async def get_publication_analytics_endpoint(
    publication_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        data = await analytics_service.get_publication_analytics(publication_id=publication_id, db=db)
        pub = data["publication"]
        latest = data["latest_snapshot"]
        snapshots = data["snapshots"]

        latest_resp = None
        if latest:
            rate = analytics_service.calculate_engagement_rate(
                latest.likes, latest.comments, latest.shares, latest.saves, latest.reach, latest.impressions
            )
            v_rate = analytics_service.calculate_view_rate(latest.views, latest.impressions)
            latest_resp = PostMetricSnapshotResponse(
                id=latest.id,
                publication_id=latest.publication_id,
                platform=latest.platform,
                external_post_id=latest.external_post_id,
                captured_at=latest.captured_at,
                views=latest.views,
                impressions=latest.impressions,
                reach=latest.reach,
                likes=latest.likes,
                comments=latest.comments,
                shares=latest.shares,
                saves=latest.saves,
                clicks=latest.clicks,
                reposts=latest.reposts,
                replies=latest.replies,
                engagements=latest.engagements,
                watch_time_seconds=latest.watch_time_seconds,
                average_watch_time_seconds=latest.average_watch_time_seconds,
                completion_rate=latest.completion_rate,
                followers_gained=latest.followers_gained,
                engagement_rate=rate,
                view_rate=v_rate,
                raw_metrics=latest.raw_metrics
            )

        snap_list = []
        for s in snapshots:
            r = analytics_service.calculate_engagement_rate(s.likes, s.comments, s.shares, s.saves, s.reach, s.impressions)
            vr = analytics_service.calculate_view_rate(s.views, s.impressions)
            snap_list.append(PostMetricSnapshotResponse(
                id=s.id,
                publication_id=s.publication_id,
                platform=s.platform,
                external_post_id=s.external_post_id,
                captured_at=s.captured_at,
                views=s.views,
                impressions=s.impressions,
                reach=s.reach,
                likes=s.likes,
                comments=s.comments,
                shares=s.shares,
                saves=s.saves,
                clicks=s.clicks,
                reposts=s.reposts,
                replies=s.replies,
                engagements=s.engagements,
                watch_time_seconds=s.watch_time_seconds,
                average_watch_time_seconds=s.average_watch_time_seconds,
                completion_rate=s.completion_rate,
                followers_gained=s.followers_gained,
                engagement_rate=r,
                view_rate=vr,
                raw_metrics=s.raw_metrics
            ))

        return PublicationAnalyticsResponse(
            publication=PublicationResponse.model_validate(pub),
            content_title=data["content_title"],
            content_type=data["content_type"],
            latest_snapshot=latest_resp,
            snapshot_count=data["snapshot_count"],
            snapshots=snap_list,
            views_per_hour=data["views_per_hour"],
            engagements_per_hour=data["engagements_per_hour"],
            is_stale=data["is_stale"]
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve publication analytics: {e}")

@app.post("/api/analytics/publications/{publication_id}/refresh", tags=["Analytics"])
async def refresh_publication_analytics(
    publication_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Triggers an immediate asynchronous background sync for a publication's metrics."""
    res = await db.execute(select(Publication).where(Publication.id == publication_id))
    pub = res.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found.")

    if pub.status != "PUBLISHED":
        raise HTTPException(status_code=400, detail=f"Cannot refresh analytics for publication in '{pub.status}' state.")

    # Enforce refresh cooldown
    now_utc = datetime.utcnow()
    if pub.last_analytics_sync_at:
        delta = (now_utc - pub.last_analytics_sync_at).total_seconds()
        if delta < settings.ANALYTICS_REFRESH_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {int(settings.ANALYTICS_REFRESH_COOLDOWN_SECONDS - delta)} seconds before refreshing analytics again."
            )

    job_id = f"job_ana_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        content_id=pub.content_id,
        type="ANALYTICS_SYNC",
        status="QUEUED",
        created_at=now_utc
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        content_id=pub.content_id,
        job_type="ANALYTICS_SYNC",
        publication_id=pub.id
    )

    return {"status": "queued", "job_id": job_id, "message": "Analytics sync job queued."}

@app.post("/api/analytics/backfill", response_model=AnalyticsBackfillResponse, tags=["Analytics"])
async def backfill_analytics_endpoint(
    req: AnalyticsBackfillRequest,
    db: AsyncSession = Depends(get_db)
):
    s_date = datetime.fromisoformat(req.start_date) if req.start_date else None
    e_date = datetime.fromisoformat(req.end_date) if req.end_date else None

    count = await analytics_service.backfill_analytics(
        start_date=s_date,
        end_date=e_date,
        platform=req.platform,
        limit=req.limit,
        db=db
    )
    return AnalyticsBackfillResponse(
        queued_count=count,
        message=f"Successfully queued {count} historical analytics sync job(s)."
    )

@app.get("/api/analytics/export", tags=["Analytics"])
async def export_analytics_csv_endpoint(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    now_utc = datetime.utcnow()
    s_date = datetime.fromisoformat(start) if start else (now_utc - timedelta(days=30))
    e_date = datetime.fromisoformat(end) if end else now_utc

    csv_content = await analytics_service.export_analytics_csv(
        start_date=s_date,
        end_date=e_date,
        platform=platform,
        db=db
    )
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reflow_analytics_{now_utc.strftime('%Y%m%d')}.csv"}
    )

# ------------------------------------------------------------------------------
# Phase 11: Real Content Intelligence & Recommendation Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/intelligence/overview", response_model=IntelligenceOverviewResponse, tags=["Intelligence"])
async def get_intelligence_overview(db: AsyncSession = Depends(get_db)):
    """Returns account-wide content intelligence KPIs, baselines, top recommendations and content gaps."""
    overview = await intelligence_service.get_overview(db=db)
    return overview

@app.get("/api/intelligence/insights", response_model=List[PerformanceInsightResponse], tags=["Intelligence"])
async def list_intelligence_insights(
    scope: Optional[str] = Query(None, description="Scope filter: ACCOUNT, PLATFORM, CONTENT_TYPE, TOPIC, CLIP, CAROUSEL"),
    db: AsyncSession = Depends(get_db)
):
    """Returns persisted performance insights."""
    query = select(PerformanceInsight).order_by(PerformanceInsight.created_at.desc())
    if scope:
        query = query.where(PerformanceInsight.scope == scope.upper())
    res = await db.execute(query)
    insights = res.scalars().all()
    return insights

@app.get("/api/intelligence/recommendations", response_model=List[ContentRecommendationResponse], tags=["Intelligence"])
async def list_content_recommendations(
    status: str = Query("ACTIVE", description="Recommendation status filter: ACTIVE, DISMISSED, APPLIED"),
    type: Optional[str] = Query(None, description="Recommendation type filter"),
    db: AsyncSession = Depends(get_db)
):
    """Returns active evidence-backed content recommendations."""
    query = select(ContentRecommendation).where(ContentRecommendation.status == status.upper()).order_by(ContentRecommendation.created_at.desc())
    if type:
        query = query.where(ContentRecommendation.type == type.upper())
    res = await db.execute(query)
    recs = res.scalars().all()
    return recs

@app.get("/api/intelligence/patterns", response_model=List[ContentPatternResponse], tags=["Intelligence"])
async def list_content_patterns(
    pattern_type: Optional[str] = Query(None, description="Pattern type filter: HOOK, TOPIC, DURATION_BUCKET, POSTING_WINDOW, TEMPLATE"),
    db: AsyncSession = Depends(get_db)
):
    """Returns identified recurring content patterns."""
    query = select(ContentPattern).order_by(ContentPattern.sample_size.desc())
    if pattern_type:
        query = query.where(ContentPattern.pattern_type == pattern_type.upper())
    res = await db.execute(query)
    patterns = res.scalars().all()
    return patterns

@app.get("/api/intelligence/topics", response_model=List[TopicPerformanceItem], tags=["Intelligence"])
async def get_topic_performance(db: AsyncSession = Depends(get_db)):
    """Returns performance metrics grouped by normalized topic cluster."""
    topics = await intelligence_service.get_topic_performance(db=db)
    return topics

@app.get("/api/intelligence/hooks", response_model=List[HookPerformanceItem], tags=["Intelligence"])
async def get_hook_performance(db: AsyncSession = Depends(get_db)):
    """Returns performance breakdown by hook archetype."""
    hooks = await intelligence_service.get_hook_performance(db=db)
    return hooks

@app.get("/api/intelligence/durations", response_model=List[DurationPerformanceItem], tags=["Intelligence"])
async def get_duration_performance(db: AsyncSession = Depends(get_db)):
    """Returns performance breakdown by video/clip duration bucket."""
    durations = await intelligence_service.get_duration_performance(db=db)
    return durations

@app.get("/api/intelligence/posting-windows", response_model=List[PostingWindowItem], tags=["Intelligence"])
async def get_posting_windows(db: AsyncSession = Depends(get_db)):
    """Returns performance breakdown by localized day and hour posting windows."""
    windows = await intelligence_service.get_posting_windows(db=db)
    return windows

@app.get("/api/intelligence/content-gaps", response_model=List[ContentGapItem], tags=["Intelligence"])
async def get_content_gaps(db: AsyncSession = Depends(get_db)):
    """Returns high-performing topics lacking specific format representations."""
    overview = await intelligence_service.get_overview(db=db)
    return overview.get("content_gaps", [])

@app.get("/api/intelligence/experiments", response_model=List[ExperimentResponse], tags=["Intelligence"])
async def list_experiments(db: AsyncSession = Depends(get_db)):
    """Returns tracked content experiments."""
    experiments = await intelligence_service.get_experiments(db=db)
    return experiments

@app.post("/api/intelligence/refresh", response_model=IntelligenceRefreshResponse, tags=["Intelligence"])
async def refresh_intelligence_analysis(db: AsyncSession = Depends(get_db)):
    """Dispatches an asynchronous background job to recompute content patterns and recommendations."""
    job_id = f"job_intel_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        type="INTELLIGENCE_ANALYSIS",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        job_type="INTELLIGENCE_ANALYSIS"
    )

    logger.info(f"Enqueued INTELLIGENCE_ANALYSIS job {job_id}.")
    return IntelligenceRefreshResponse(
        status="queued",
        job_id=job_id,
        message="Intelligence analysis job queued successfully."
    )

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

# ------------------------------------------------------------------------------
# Phase 12: Content Experimentation API
# ------------------------------------------------------------------------------

@app.post("/api/experiments", response_model=ExperimentDetailResponse, tags=["Experiments"])
async def create_experiment_route(
    req: ExperimentCreateRequest,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    from services.experiment_service import experiment_service
    try:
        # Create experiment and default variants via service
        exp = await experiment_service.create_experiment(
            db=db,
            name=req.name,
            hypothesis=req.hypothesis,
            platform=req.platform,
            primary_metric=req.primary_metric,
            scope=req.scope,
            control_content_id=req.control_content_id,
            treatment_content_id=req.treatment_content_id,
            control_variant_id=req.control_variant_id,
            treatment_variant_id=req.treatment_variant_id,
            control_publication_id=req.control_publication_id,
            treatment_publication_id=req.treatment_publication_id,
            secondary_metrics=req.secondary_metrics,
            minimum_sample_size=req.minimum_sample_size or 5,
            confidence_level=req.confidence_level or 0.95,
            recommendation_id=req.recommendation_id,
            created_by=user_id
        )

        # Reload experiment and variants to avoid lazy-loading MissingGreenlet error
        res_exp = await db.execute(
            select(Experiment)
            .where(Experiment.id == exp.id)
            .options(selectinload(Experiment.variants))
        )
        exp = res_exp.scalar_one()

        # Trigger design validation
        warnings = await experiment_service.detect_confounds(db, exp)

        # Fetch clean details response
        return ExperimentDetailResponse(
            experiment=ExperimentResponse.model_validate(exp),
            variants=[ExperimentVariantSchema.model_validate(v) for v in exp.variants],
            results=[],
            warnings=[ExperimentWarningSchema(code=w["code"], message=w["message"]) for w in warnings]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/experiments", response_model=List[ExperimentResponse], tags=["Experiments"])
async def list_experiments(
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    query = select(Experiment).order_by(Experiment.created_at.desc())
    if user_id:
        query = query.where(or_(Experiment.created_by == None, Experiment.created_by == user_id))
    
    res = await db.execute(query)
    exps = res.scalars().all()
    return [ExperimentResponse.model_validate(e) for e in exps]

@app.get("/api/experiments/{experiment_id}", response_model=ExperimentDetailResponse, tags=["Experiments"])
async def get_experiment_details(
    experiment_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    from services.experiment_service import experiment_service
    res_exp = await db.execute(
        select(Experiment)
        .where(Experiment.id == experiment_id)
        .options(selectinload(Experiment.variants), selectinload(Experiment.evaluation_results))
    )
    exp = res_exp.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    # Ownership checks: Attempt another user's experiment. Verify: 403 or 404
    if user_id and exp.created_by and exp.created_by != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this experiment.")

    warnings = await experiment_service.detect_confounds(db, exp)

    return ExperimentDetailResponse(
        experiment=ExperimentResponse.model_validate(exp),
        variants=[ExperimentVariantSchema.model_validate(v) for v in exp.variants],
        results=[ExperimentResultResponse.model_validate(r) for r in exp.evaluation_results],
        warnings=[ExperimentWarningSchema(code=w["code"], message=w["message"]) for w in warnings]
    )

@app.post("/api/experiments/{experiment_id}/start", response_model=ExperimentDetailResponse, tags=["Experiments"])
async def start_experiment(
    experiment_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    from services.experiment_service import experiment_service
    res_exp = await db.execute(
        select(Experiment)
        .where(Experiment.id == experiment_id)
        .options(selectinload(Experiment.variants), selectinload(Experiment.evaluation_results))
    )
    exp = res_exp.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    if user_id and exp.created_by and exp.created_by != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this experiment.")

    # Validate design before transitioning to RUNNING
    warnings = await experiment_service.detect_confounds(db, exp)
    critical_errors = [w for w in warnings if w["code"] in ["INSUFFICIENT_VARIANTS", "INSUFFICIENT_DESIGN", "PLATFORM_MISMATCH"]]
    if critical_errors:
        raise HTTPException(status_code=400, detail=f"Cannot start experiment due to critical design flaws: {critical_errors[0]['message']}")

    exp.status = "RUNNING"
    exp.started_at = datetime.utcnow()
    await db.commit()

    # Reload to ensure updated status is cleanly returned with relationship data loaded
    res_exp2 = await db.execute(
        select(Experiment)
        .where(Experiment.id == experiment_id)
        .options(selectinload(Experiment.variants), selectinload(Experiment.evaluation_results))
    )
    exp = res_exp2.scalar_one()

    return ExperimentDetailResponse(
        experiment=ExperimentResponse.model_validate(exp),
        variants=[ExperimentVariantSchema.model_validate(v) for v in exp.variants],
        results=[ExperimentResultResponse.model_validate(r) for r in exp.evaluation_results],
        warnings=[ExperimentWarningSchema(code=w["code"], message=w["message"]) for w in warnings]
    )

@app.post("/api/experiments/{experiment_id}/refresh", response_model=ApiResponse, tags=["Experiments"])
async def refresh_experiment_evaluation(
    experiment_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    exp = await db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    if user_id and exp.created_by and exp.created_by != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this experiment.")

    # Enqueue background evaluation job
    job_id = f"job_exp_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        type="EXPERIMENT_EVALUATION",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        job_type="EXPERIMENT_EVALUATION",
        experiment_id=experiment_id
    )

    logger.info(f"Enqueued EXPERIMENT_EVALUATION job {job_id} for experiment {experiment_id}.")
    return ApiResponse(
        status="success",
        message="Experiment evaluation job queued successfully.",
        data={"job_id": job_id}
    )

@app.get("/api/experiments/export", tags=["Experiments"])
async def export_experiments_route(
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    # Retrieve all experiments
    query = select(Experiment).options(
        selectinload(Experiment.variants),
        selectinload(Experiment.evaluation_results)
    )
    if user_id:
        query = query.where(or_(Experiment.created_by == None, Experiment.created_by == user_id))

    res = await db.execute(query)
    exps = res.scalars().all()

    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "experiment_id", "experiment_name", "hypothesis", "scope", "platform", "status",
        "primary_metric", "sample_size", "winner_variant_id", "conclusion", "created_by",
        "variant_id", "variant_name", "role", "metric_value", "p_value", "statistical_significance", "practical_significance"
    ])

    for exp in exps:
        for var in exp.variants:
            # find result scorecard for this variant
            card = next((r for r in exp.evaluation_results if r.variant_id == var.id), None)
            writer.writerow([
                exp.id, exp.name or exp.title or "", exp.hypothesis, exp.scope, exp.platform, exp.status,
                exp.primary_metric, card.sample_size if card else 0, exp.winner_variant_id or "", exp.conclusion or "", exp.created_by or "",
                var.id, var.name, var.role,
                card.metric_value if card else "",
                card.p_value if card else "",
                card.statistical_significance if card else "",
                card.practical_significance if card else ""
            ])

    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=experiments_export.csv"}
    )

# Phase 13: Content Distribution & Automation Engine Endpoints
@app.post("/api/automations", response_model=AutomationRuleResponse, tags=["Automations"])
async def create_automation_rule(
    req: AutomationRuleCreateRequest,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule_id = f"rule_{uuid.uuid4().hex[:8]}"
    rule = AutomationRule(
        id=rule_id,
        name=req.name,
        description=req.description,
        enabled=req.enabled,
        trigger_type=req.trigger_type,
        scope=req.scope,
        cooldown_minutes=req.cooldown_minutes or 60,
        max_runs_per_day=req.max_runs_per_day or 5,
        status="ACTIVE",
        created_by=user_id
    )
    rule.conditions = req.conditions
    rule.actions = req.actions
    db.add(rule)
    await db.commit()
    return rule

@app.get("/api/automations", response_model=List[AutomationRuleResponse], tags=["Automations"])
async def list_automation_rules(
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    query = select(AutomationRule)
    if user_id:
        query = query.where(or_(AutomationRule.created_by == None, AutomationRule.created_by == user_id))
    res = await db.execute(query)
    return res.scalars().all()

@app.get("/api/automations/{rule_id}", response_model=AutomationDetailResponse, tags=["Automations"])
async def get_automation_rule(
    rule_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")
    
    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    # Fetch executions
    exec_res = await db.execute(
        select(AutomationExecution)
        .where(AutomationExecution.automation_id == rule_id)
        .options(selectinload(AutomationExecution.action_executions))
        .order_by(AutomationExecution.created_at.desc())
    )
    executions = exec_res.scalars().all()

    # Compute metric summaries
    succeeded = len([e for e in executions if e.status == "SUCCEEDED"])
    failed = len([e for e in executions if e.status == "FAILED"])
    skipped = len([e for e in executions if e.status == "SKIPPED"])
    total = len(executions)
    
    metrics = {
        "total_runs": total,
        "success_rate": (succeeded / total * 100) if total > 0 else 0,
        "failed_runs": failed,
        "skipped_runs": skipped
    }

    return {
        "rule": rule,
        "executions": executions,
        "metrics": metrics
    }

@app.put("/api/automations/{rule_id}", response_model=AutomationRuleResponse, tags=["Automations"])
async def update_automation_rule(
    rule_id: str,
    req: AutomationRuleCreateRequest,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")

    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    rule.name = req.name
    rule.description = req.description
    rule.enabled = req.enabled
    rule.trigger_type = req.trigger_type
    rule.scope = req.scope
    rule.conditions = req.conditions
    rule.actions = req.actions
    rule.cooldown_minutes = req.cooldown_minutes or 60
    rule.max_runs_per_day = req.max_runs_per_day or 5
    rule.updated_at = datetime.utcnow()

    await db.commit()
    return rule

@app.delete("/api/automations/{rule_id}", response_model=ApiResponse, tags=["Automations"])
async def delete_automation_rule(
    rule_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")

    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    await db.delete(rule)
    await db.commit()
    return ApiResponse(status="success", message="Automation rule deleted successfully.")

@app.post("/api/automations/{rule_id}/enable", response_model=AutomationRuleResponse, tags=["Automations"])
async def enable_automation_rule(
    rule_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")

    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    rule.enabled = True
    rule.status = "ACTIVE"
    rule.updated_at = datetime.utcnow()
    await db.commit()
    return rule

@app.post("/api/automations/{rule_id}/disable", response_model=AutomationRuleResponse, tags=["Automations"])
async def disable_automation_rule(
    rule_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")

    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    rule.enabled = False
    rule.status = "DISABLED"
    rule.updated_at = datetime.utcnow()
    await db.commit()
    return rule

@app.post("/api/automations/{rule_id}/run", response_model=AutomationExecutionResponse, tags=["Automations"])
async def run_automation_rule_manual(
    rule_id: str,
    entity_id: str = Query(..., description="The trigger entity ID to evaluate manually"),
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")

    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    # Create Execution bypassing safety limit checking
    exec_id = f"exec_man_{uuid.uuid4().hex[:8]}"
    execution = AutomationExecution(
        id=exec_id,
        automation_id=rule.id,
        trigger_event=f"manual.{rule.trigger_type.lower()}",
        trigger_entity_id=entity_id,
        status="QUEUED",
        execution_key=f"{rule.id}:{entity_id}:manual",
        created_at=datetime.utcnow()
    )
    db.add(execution)

    for act in rule.actions:
        act_exec = AutomationActionExecution(
            id=f"act_{uuid.uuid4().hex[:8]}",
            execution_id=exec_id,
            action_type=act.get("type", "UNKNOWN"),
            status="QUEUED",
            result_json="{}",
        )
        db.add(act_exec)

    await db.commit()

    # Enqueue in background worker
    job_id = f"job_auto_{uuid.uuid4().hex[:8]}"
    job = Job(
        id=job_id,
        type="AUTOMATION_EXECUTION",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(
        job_id=job_id,
        job_type="AUTOMATION_EXECUTION",
        execution_id=exec_id
    )

    # Fetch fresh execution back with selectinload to serialize correctly
    res_exec = await db.execute(
        select(AutomationExecution)
        .where(AutomationExecution.id == exec_id)
        .options(selectinload(AutomationExecution.action_executions))
    )
    return res_exec.scalar_one()

@app.get("/api/automations/{rule_id}/executions", response_model=List[AutomationExecutionResponse], tags=["Automations"])
async def list_rule_executions(
    rule_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")

    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    res = await db.execute(
        select(AutomationExecution)
        .where(AutomationExecution.automation_id == rule_id)
        .options(selectinload(AutomationExecution.action_executions))
        .order_by(AutomationExecution.created_at.desc())
    )
    return res.scalars().all()

@app.get("/api/automation-executions/{exec_id}", response_model=AutomationExecutionResponse, tags=["Automations"])
async def get_automation_execution(
    exec_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AutomationExecution)
        .where(AutomationExecution.id == exec_id)
        .options(
            selectinload(AutomationExecution.action_executions),
            selectinload(AutomationExecution.rule)
        )
    )
    execution = res.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Automation execution not found.")

    if user_id and execution.rule.created_by and execution.rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation execution.")

    return execution

@app.post("/api/automations/{rule_id}/dry-run", tags=["Automations"])
async def dry_run_automation_rule(
    rule_id: str,
    entity_id: str = Query(..., description="The trigger entity ID to dry-run"),
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found.")

    if user_id and rule.created_by and rule.created_by != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this automation rule.")

    # 1. Resolve event type matching trigger
    from services.event_bus import event_bus_service
    event_type = event_bus_service.TRIGGER_EVENT_MAP.get(rule.trigger_type, "content.ready")

    entity_class = event_bus_service.ENTITY_MAPPING.get(event_type)
    entity = None
    if entity_class:
        entity = await db.get(entity_class, entity_id)

    # 2. Evaluate conditions
    conditions_passed, skip_reason = event_bus_service.evaluate_conditions(entity, rule.conditions)
    
    # Previews result
    actions_to_execute = []
    if conditions_passed:
        for act in rule.actions:
            actions_to_execute.append(act.get("type", "UNKNOWN"))

    preview_message = (
        f"This automation would execute: {', '.join(actions_to_execute)}. No changes have been executed."
        if conditions_passed else
        f"This automation would be skipped because condition checks failed: {skip_reason}."
    )

    return {
        "status": "success",
        "conditions_passed": conditions_passed,
        "skip_reason": skip_reason,
        "actions_to_execute": actions_to_execute,
        "preview_message": preview_message
    }

@app.post("/api/automation-templates/{template}/create", response_model=AutomationRuleResponse, tags=["Automations"])
async def create_rule_from_template(
    template: str,
    name: str = Query(..., description="The custom name of the automation rule"),
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    from services.automation_service import automation_service
    try:
        rule = await automation_service.instantiate_template(db, template, name, user_id)
        return rule
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# PHASE 16: NOTIFICATIONS, SEARCH & PRODUCTIZATION ENDPOINTS
# ============================================================================

@app.get("/api/notifications", response_model=NotificationListResponse, tags=["Notifications"])
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
):
    """Fetches recent persistent system notifications and unread count."""
    from services.notification_service import notification_service
    res = await notification_service.get_notifications(limit=limit, unread_only=unread_only)
    return NotificationListResponse(items=res["items"], unread_count=res["unread_count"])

@app.post("/api/notifications/{notification_id}/read", tags=["Notifications"])
async def mark_notification_read(notification_id: str):
    """Marks a single notification as read."""
    from services.notification_service import notification_service
    success = await notification_service.mark_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"status": "success", "message": f"Notification {notification_id} marked as read."}

@app.post("/api/notifications/read-all", tags=["Notifications"])
async def mark_all_notifications_read():
    """Marks all notifications as read."""
    from services.notification_service import notification_service
    count = await notification_service.mark_all_read()
    return {"status": "success", "marked_read_count": count}

@app.get("/api/search", response_model=GlobalSearchResponse, tags=["Search"])
async def global_search(
    q: str = Query(..., min_length=1, description="Search query string"),
    db: AsyncSession = Depends(get_db)
):
    """Performs server-side search across Content, Clips, Carousels, Publications, Experiments, Automations."""
    query_str = f"%{q.strip()}%"
    results = []

    # 1. Search Content
    c_res = await db.execute(
        select(Content).where(or_(Content.title.ilike(query_str), Content.text_content.ilike(query_str))).limit(10)
    )
    for c in c_res.scalars().all():
        results.append(GlobalSearchResultItem(
            id=c.id,
            type="content",
            title=c.title,
            subtitle=f"{c.content_type} • {c.status}",
            url=f"/content/{c.id}",
            status=c.status,
            created_at=c.created_at
        ))

    # 2. Search Clips
    clip_res = await db.execute(
        select(Clip).where(or_(Clip.title.ilike(query_str), Clip.hook.ilike(query_str))).limit(10)
    )
    for cl in clip_res.scalars().all():
        results.append(GlobalSearchResultItem(
            id=cl.id,
            type="clip",
            title=cl.title or "Untitled Clip",
            subtitle=f"Clip ({cl.duration_seconds}s) • {cl.status}",
            url=f"/content/{cl.content_id}?tab=clips",
            status=cl.status,
            created_at=cl.created_at
        ))

    # 3. Search Carousels
    car_res = await db.execute(
        select(Carousel).where(Carousel.title.ilike(query_str)).limit(10)
    )
    for car in car_res.scalars().all():
        results.append(GlobalSearchResultItem(
            id=car.id,
            type="carousel",
            title=car.title or "Untitled Carousel",
            subtitle=f"Carousel ({car.slide_count} slides) • {car.status}",
            url=f"/content/{car.content_id}?tab=carousels",
            status=car.status,
            created_at=car.created_at
        ))

    # 4. Search Publications
    pub_res = await db.execute(
        select(Publication).where(or_(Publication.title.ilike(query_str), Publication.description.ilike(query_str))).limit(10)
    )
    for p in pub_res.scalars().all():
        results.append(GlobalSearchResultItem(
            id=p.id,
            type="publication",
            title=p.title or f"{p.platform.upper()} Publication",
            subtitle=f"{p.platform.upper()} • {p.status}",
            url=f"/publishing?id={p.id}",
            status=p.status,
            created_at=p.created_at
        ))

    # 5. Search Experiments
    exp_res = await db.execute(
        select(Experiment).where(or_(Experiment.name.ilike(query_str), Experiment.hypothesis.ilike(query_str))).limit(10)
    )
    for e in exp_res.scalars().all():
        results.append(GlobalSearchResultItem(
            id=e.id,
            type="experiment",
            title=e.name,
            subtitle=f"Experiment • {e.status}",
            url=f"/experiments?id={e.id}",
            status=e.status,
            created_at=e.created_at
        ))

    # 6. Search Automations
    aut_res = await db.execute(
        select(AutomationRule).where(or_(AutomationRule.name.ilike(query_str), AutomationRule.trigger_type.ilike(query_str))).limit(10)
    )
    for a in aut_res.scalars().all():
        results.append(GlobalSearchResultItem(
            id=a.id,
            type="automation",
            title=a.name,
            subtitle=f"Automation ({a.trigger_type})",
            url=f"/automations?id={a.id}",
            status="ACTIVE" if a.is_active else "INACTIVE",
            created_at=a.created_at
        ))

    return GlobalSearchResponse(query=q, results=results)

@app.post("/api/publications/{publication_id}/approve", response_model=PublicationResponse, tags=["Publications"])
async def approve_publication(publication_id: str, db: AsyncSession = Depends(get_db)):
    """Approves a publication awaiting approval and transitions it to SCHEDULED or QUEUED."""
    res = await db.execute(select(Publication).where(Publication.id == publication_id))
    pub = res.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found.")
    
    if pub.status in ["PUBLISHED", "PUBLISHING"]:
        raise HTTPException(status_code=400, detail=f"Cannot approve publication in {pub.status} status.")

    pub.status = "SCHEDULED" if pub.scheduled_at else "DRAFT"
    pub.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(pub)

    from services.notification_service import notification_service
    await notification_service.create_notification(
        notification_type="APPROVAL_SUCCESS",
        title="Publication Approved",
        message=f"Publication '{pub.title or pub.id}' was approved for {pub.platform.upper()}.",
        severity="SUCCESS",
        entity_type="publication",
        entity_id=pub.id
    )

    return PublicationResponse.model_validate(pub)

@app.post("/api/publications/approve-batch", tags=["Publications"])
async def approve_batch_publications(publication_ids: List[str], db: AsyncSession = Depends(get_db)):
    """Bulk approves multiple publications, skipping any in BLOCKED or FAILED state."""
    approved_count = 0
    skipped_count = 0

    for pub_id in publication_ids:
        res = await db.execute(select(Publication).where(Publication.id == pub_id))
        pub = res.scalar_one_or_none()
        if pub and pub.status not in ["FAILED", "PUBLISHED", "PUBLISHING"]:
            pub.status = "SCHEDULED" if pub.scheduled_at else "DRAFT"
            pub.updated_at = datetime.utcnow()
            approved_count += 1
        else:
            skipped_count += 1

    await db.commit()
    return {"status": "success", "approved_count": approved_count, "skipped_count": skipped_count}

@app.get("/api/clips/{clip_id}", response_model=ClipResponse, tags=["Clips"])
async def get_clip_detail(clip_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches details for a single clip."""
    res = await db.execute(
        select(Clip).options(selectinload(Clip.variants)).where(Clip.id == clip_id)
    )
    clip = res.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")
    return ClipResponse.model_validate(clip)

@app.get("/api/carousels/{carousel_id}", response_model=CarouselResponse, tags=["Carousels"])
async def get_carousel_detail(carousel_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches details for a single carousel."""
    res = await db.execute(
        select(Carousel).options(selectinload(Carousel.slides).selectinload(CarouselSlide.elements)).where(Carousel.id == carousel_id)
    )
    car = res.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Carousel not found.")
    return CarouselResponse.model_validate(car)

# ==============================================================================
# PHASE 17: EXTENSIBILITY, PLUGINS, WEBHOOKS & API KEYS
# ==============================================================================

from plugins.registry import plugin_registry
from plugins.manifest import PluginType
from models.entities import PluginConfiguration, WebhookEndpoint, APIKey
from models.schemas import (
    PluginListResponse, PluginSchema, WebhookResponse, WebhookCreateRequest,
    APIKeyCreateRequest, APIKeyCreatedResponse, APIKeyResponse
)
from services.webhook_service import webhook_service
import hashlib

@app.get("/api/plugins", response_model=PluginListResponse, tags=["Plugins"])
async def list_plugins(type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Lists registered plugins and their capabilities, status, and health."""
    ptype = PluginType(type.upper()) if type and hasattr(PluginType, type.upper()) else None
    plugins = plugin_registry.list_plugins(plugin_type=ptype, include_disabled=True)
    return PluginListResponse(plugins=[PluginSchema.model_validate(p) for p in plugins], total=len(plugins))

@app.get("/api/plugins/{plugin_id}", response_model=PluginSchema, tags=["Plugins"])
async def get_plugin_detail(plugin_id: str):
    """Fetches details, capabilities, permissions, and status of a specific plugin."""
    plugins = plugin_registry.list_plugins(include_disabled=True)
    match = next((p for p in plugins if p["id"] == plugin_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    return PluginSchema.model_validate(match)

@app.post("/api/plugins/{plugin_id}/enable", response_model=PluginSchema, tags=["Plugins"])
async def enable_plugin(plugin_id: str, db: AsyncSession = Depends(get_db)):
    """Enables an installed plugin."""
    success = plugin_registry.enable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found.")
    
    # Sync DB state
    res = await db.execute(select(PluginConfiguration).where(PluginConfiguration.plugin_id == plugin_id))
    cfg = res.scalar_one_or_none()
    if not cfg:
        cfg = PluginConfiguration(id=f"pcfg_{uuid.uuid4().hex[:8]}", plugin_id=plugin_id, enabled=True)
        db.add(cfg)
    else:
        cfg.enabled = True
        cfg.updated_at = datetime.utcnow()
    await db.commit()

    return await get_plugin_detail(plugin_id)

@app.post("/api/plugins/{plugin_id}/disable", response_model=PluginSchema, tags=["Plugins"])
async def disable_plugin(plugin_id: str, db: AsyncSession = Depends(get_db)):
    """Disables a plugin."""
    success = plugin_registry.disable_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found.")

    res = await db.execute(select(PluginConfiguration).where(PluginConfiguration.plugin_id == plugin_id))
    cfg = res.scalar_one_or_none()
    if not cfg:
        cfg = PluginConfiguration(id=f"pcfg_{uuid.uuid4().hex[:8]}", plugin_id=plugin_id, enabled=False)
        db.add(cfg)
    else:
        cfg.enabled = False
        cfg.updated_at = datetime.utcnow()
    await db.commit()

    return await get_plugin_detail(plugin_id)

@app.post("/api/plugins/{plugin_id}/health", tags=["Plugins"])
async def check_plugin_health(plugin_id: str):
    """Executes isolated health check on a specific plugin."""
    return await plugin_registry.health_check(plugin_id)

# ------------------------------------------------------------------------------
# Webhooks API
# ------------------------------------------------------------------------------

@app.get("/api/webhooks", response_model=List[WebhookResponse], tags=["Webhooks"])
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    """Lists registered outbound webhook endpoints."""
    res = await db.execute(select(WebhookEndpoint).order_by(WebhookEndpoint.created_at.desc()))
    endpoints = res.scalars().all()
    results = []
    for ep in endpoints:
        results.append(WebhookResponse(
            id=ep.id,
            url=ep.url,
            events=json.loads(ep.events_json or "[]"),
            enabled=ep.enabled,
            last_success_at=ep.last_success_at,
            last_failure_at=ep.last_failure_at,
            created_at=ep.created_at
        ))
    return results

@app.post("/api/webhooks", response_model=WebhookResponse, tags=["Webhooks"])
async def create_webhook(req: WebhookCreateRequest, db: AsyncSession = Depends(get_db)):
    """Registers a new outbound webhook endpoint with generated HMAC secret."""
    if not req.url.startswith("http://") and not req.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid webhook URL. Must start with http:// or https://")

    webhook_id = f"wh_{uuid.uuid4().hex[:10]}"
    secret = f"whsec_{uuid.uuid4().hex}"
    
    ep = WebhookEndpoint(
        id=webhook_id,
        url=req.url,
        events_json=json.dumps(req.events or ["content.ready", "publication.succeeded"]),
        enabled=True,
        secret=secret,
        created_at=datetime.utcnow()
    )
    db.add(ep)
    await db.commit()

    return WebhookResponse(
        id=ep.id,
        url=ep.url,
        events=json.loads(ep.events_json),
        enabled=ep.enabled,
        last_success_at=None,
        last_failure_at=None,
        created_at=ep.created_at
    )

@app.delete("/api/webhooks/{webhook_id}", tags=["Webhooks"])
async def delete_webhook(webhook_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a webhook endpoint."""
    res = await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id))
    ep = res.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")
    await db.delete(ep)
    await db.commit()
    return {"status": "success", "message": f"Webhook endpoint '{webhook_id}' deleted."}

@app.post("/api/webhooks/{webhook_id}/test", tags=["Webhooks"])
async def test_webhook(webhook_id: str, db: AsyncSession = Depends(get_db)):
    """Triggers a test signed payload to verify endpoint connectivity."""
    res = await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id))
    ep = res.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")

    test_data = {"test": True, "ping": "pong", "triggered_at": datetime.utcnow().isoformat()}
    delivered = await webhook_service._deliver_payload(ep.id, ep.url, webhook_service.compute_signature(ep.secret, int(time.time()), json.dumps(test_data).encode("utf-8")), json.dumps(test_data).encode("utf-8"))
    return {"status": "success" if delivered else "failed", "delivered": delivered, "url": ep.url}

# ------------------------------------------------------------------------------
# API Keys Authorization API
# ------------------------------------------------------------------------------

@app.post("/api/auth/api-keys", response_model=APIKeyCreatedResponse, tags=["Auth"])
async def create_api_key(req: APIKeyCreateRequest, db: AsyncSession = Depends(get_db)):
    """Creates a new API key. The raw key is returned ONCE and never stored plain in DB."""
    key_id = f"key_{uuid.uuid4().hex[:10]}"
    prefix = "reflow_live_"
    raw_secret = f"{prefix}{uuid.uuid4().hex}{uuid.uuid4().hex}"
    hashed_key = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)

    key_obj = APIKey(
        id=key_id,
        name=req.name,
        prefix=prefix,
        hashed_key=hashed_key,
        permissions_json=json.dumps(req.permissions or ["CONTENT_READ"]),
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )
    db.add(key_obj)
    await db.commit()

    return APIKeyCreatedResponse(
        id=key_obj.id,
        name=key_obj.name,
        prefix=prefix,
        raw_api_key=raw_secret,
        permissions=json.loads(key_obj.permissions_json),
        created_at=key_obj.created_at,
        expires_at=key_obj.expires_at
    )

@app.get("/api/auth/api-keys", response_model=List[APIKeyResponse], tags=["Auth"])
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    """Lists registered API keys with masked secrets."""
    res = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    keys = res.scalars().all()
    results = []
    for k in keys:
        results.append(APIKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            permissions=json.loads(k.permissions_json or "[]"),
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at
        ))
    return results

@app.delete("/api/auth/api-keys/{key_id}", tags=["Auth"])
async def revoke_api_key(key_id: str, db: AsyncSession = Depends(get_db)):
    """Revokes an API key."""
    res = await db.execute(select(APIKey).where(APIKey.id == key_id))
    k = res.scalar_one_or_none()
    if not k:
        raise HTTPException(status_code=404, detail="API key not found.")
    await db.delete(k)
    await db.commit()
    return {"status": "success", "message": f"API key '{key_id}' revoked successfully."}

# ==============================================================================
# PHASE 18: ECOSYSTEM & INTEGRATION HUB REST API ENDPOINTS
# ==============================================================================

from services.ecosystem_service import ecosystem_service
from models.schemas import (
    EcosystemPluginItem, EcosystemCatalogResponse, PluginInstallRequest,
    PluginUpdateRequest, PluginConfigureRequest, PluginAuditLogItem
)

@app.get("/api/ecosystem/plugins", response_model=EcosystemCatalogResponse, tags=["Ecosystem"])
async def list_ecosystem_plugins(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Plugin type category filter"),
    source: Optional[str] = Query(None, description="Source filter (OFFICIAL, COMMUNITY, LOCAL)"),
    installed_only: bool = Query(False, description="Filter installed plugins only"),
    updates_only: bool = Query(False, description="Filter available updates only"),
    db: AsyncSession = Depends(get_db)
):
    """Lists ecosystem catalog plugins with search, filter, and installation status."""
    items = await ecosystem_service.list_catalog(
        db, search_query=q, category=category, source_type=source,
        installed_only=installed_only, updates_only=updates_only
    )
    reg_url = getattr(settings, "PLUGIN_REGISTRY_URL", None) or "local://registry/registry.json"
    return EcosystemCatalogResponse(
        plugins=[EcosystemPluginItem.model_validate(i) for i in items],
        total=len(items),
        registry_url=reg_url,
        updated_at=datetime.utcnow().isoformat()
    )

@app.get("/api/ecosystem/plugins/{plugin_id}", response_model=EcosystemPluginItem, tags=["Ecosystem"])
async def get_ecosystem_plugin_detail(plugin_id: str, db: AsyncSession = Depends(get_db)):
    """Gets detailed ecosystem catalog metadata for a single plugin."""
    detail = await ecosystem_service.get_plugin_detail(db, plugin_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found in ecosystem catalog.")
    return EcosystemPluginItem.model_validate(detail)

@app.get("/api/ecosystem/categories", tags=["Ecosystem"])
async def get_ecosystem_categories():
    """Gets list of available plugin ecosystem categories."""
    return {
        "categories": [
            {"id": "ALL", "name": "All Categories"},
            {"id": "PLATFORM", "name": "Social Platforms"},
            {"id": "AI_PROVIDER", "name": "AI Providers"},
            {"id": "STORAGE", "name": "Storage Drivers"},
            {"id": "MEDIA_PROCESSOR", "name": "Media Processors"},
            {"id": "WORKFLOW_ACTION", "name": "Workflow Actions"},
            {"id": "ANALYTICS", "name": "Analytics Providers"}
        ]
    }

@app.post("/api/ecosystem/refresh", tags=["Ecosystem"])
async def refresh_ecosystem_catalog():
    """Forces catalog refresh from static registry or custom PLUGIN_REGISTRY_URL."""
    cat = await ecosystem_service.fetch_catalog(force_refresh=True)
    return {"status": "success", "total_plugins": len(cat.get("plugins", [])), "refreshed_at": datetime.utcnow().isoformat()}

@app.post("/api/plugins/install", tags=["Ecosystem"])
async def install_plugin(req: PluginInstallRequest, db: AsyncSession = Depends(get_db)):
    """Installs a plugin package with checksum verification, permission consent, and safety checks."""
    try:
        res = await ecosystem_service.install_plugin(
            db, plugin_id=req.plugin_id, version=req.version,
            source=req.source, accept_permissions=req.accept_permissions
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Installation failed: {e}")

@app.post("/api/plugins/{plugin_id}/update", tags=["Ecosystem"])
async def update_plugin(plugin_id: str, req: PluginUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Updates a plugin atomically with automated rollback on health check failure."""
    try:
        res = await ecosystem_service.update_plugin(db, plugin_id=plugin_id, confirm=req.confirm)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {e}")

@app.post("/api/plugins/{plugin_id}/uninstall", tags=["Ecosystem"])
async def uninstall_plugin(plugin_id: str, db: AsyncSession = Depends(get_db)):
    """Safely uninstalls a plugin while preserving user publication content."""
    try:
        res = await ecosystem_service.uninstall_plugin(db, plugin_id=plugin_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/plugins/{plugin_id}/configure", tags=["Ecosystem"])
async def configure_plugin(plugin_id: str, req: PluginConfigureRequest, db: AsyncSession = Depends(get_db)):
    """Configures plugin parameters with secret redaction."""
    res = await ecosystem_service.configure_plugin(db, plugin_id=plugin_id, config_dict=req.config)
    return res

@app.get("/api/plugins/{plugin_id}/audit-log", response_model=List[PluginAuditLogItem], tags=["Ecosystem"])
async def get_plugin_audit_log(plugin_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves audit log history for a plugin."""
    logs = await ecosystem_service.get_audit_logs(db, plugin_id=plugin_id)
    return [PluginAuditLogItem.model_validate(l) for l in logs]

@app.get("/api/ecosystem/metrics", tags=["Ecosystem"])
async def get_ecosystem_metrics():
    """Gets plugin ecosystem system health & operation metrics telemetry."""
    return ecosystem_service.metrics

# ==============================================================================
# PHASE 19: OBSERVABILITY, RELIABILITY & INCIDENT ENGINE REST API ENDPOINTS
# ==============================================================================

from services.incident_service import incident_service
from services.telemetry_service import telemetry_service
from models.entities import SystemJob, DeadLetterJob
from models.schemas import (
    SystemJobResponse, DeadLetterJobResponse, IncidentResponse,
    IncidentAcknowledgeRequest, IncidentResolveRequest, IncidentEventResponse,
    SystemEventResponse, AlertRuleResponse, AlertRuleCreateRequest,
    HealthHistoryResponse, WorkerHeartbeatResponse, TraceViewResponse
)

@app.get("/api/system/incidents", response_model=List[IncidentResponse], tags=["Incidents"])
async def list_incidents(
    status: Optional[str] = Query(None, description="Incident status filter (OPEN, INVESTIGATING, RESOLVED, CLOSED)"),
    severity: Optional[str] = Query(None, description="Severity filter (INFO, LOW, MEDIUM, HIGH, CRITICAL)"),
    component: Optional[str] = Query(None, description="Component filter"),
    db: AsyncSession = Depends(get_db)
):
    """Lists incidents with optional status, severity, and component filtering."""
    incidents = await incident_service.list_incidents(db, status=status, severity=severity, component=component)
    return [IncidentResponse.model_validate(i) for i in incidents]

@app.get("/api/system/incidents/{incident_id}", tags=["Incidents"])
async def get_incident_detail(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Gets detailed incident metadata including timeline history events."""
    inc = await incident_service.get_incident(db, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return inc

@app.post("/api/system/incidents/{incident_id}/acknowledge", tags=["Incidents"])
async def acknowledge_incident(incident_id: str, req: IncidentAcknowledgeRequest, db: AsyncSession = Depends(get_db)):
    """Marks an incident as INVESTIGATING and records operator acknowledgement."""
    try:
        return await incident_service.acknowledge_incident(db, incident_id, acknowledged_by=req.acknowledged_by or "Operator")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/system/incidents/{incident_id}/resolve", tags=["Incidents"])
async def resolve_incident(incident_id: str, req: IncidentResolveRequest, db: AsyncSession = Depends(get_db)):
    """Resolves an incident with mandatory resolution note explanation."""
    try:
        return await incident_service.resolve_incident(db, incident_id, resolution_note=req.resolution_note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/system/jobs/failed", response_model=List[DeadLetterJobResponse], tags=["Observability"])
async def list_dead_letter_jobs(db: AsyncSession = Depends(get_db)):
    """Lists permanently failed Dead Letter Queue (DLQ) jobs."""
    res = await db.execute(select(DeadLetterJob).where(DeadLetterJob.dismissed == False).order_by(DeadLetterJob.failed_at.desc()))
    dlq_jobs = res.scalars().all()
    return [DeadLetterJobResponse.model_validate(d) for d in dlq_jobs]

@app.post("/api/system/jobs/{job_id}/retry", tags=["Observability"])
async def retry_failed_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Manually retries a failed or dead-letter job."""
    res = await db.execute(select(SystemJob).where(SystemJob.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    job.status = "QUEUED"
    job.retry_count = 0
    await db.commit()

    payload = json.loads(job.payload_json or "{}")
    await queue_service._fallback_queue.put(payload)
    return {"status": "success", "job_id": job_id, "message": "Job re-queued for execution."}

@app.get("/api/system/trace/request/{request_id}", response_model=TraceViewResponse, tags=["Observability"])
async def trace_request_id(request_id: str, db: AsyncSession = Depends(get_db)):
    """Resolves end-to-end operational trace for a request_id."""
    res = await telemetry_service.trace_request(db, request_id)
    return TraceViewResponse.model_validate(res)

@app.get("/api/system/trace/job/{job_id}", response_model=TraceViewResponse, tags=["Observability"])
async def trace_job_id(job_id: str, db: AsyncSession = Depends(get_db)):
    """Resolves execution timeline for a job_id."""
    res = await telemetry_service.trace_job(db, job_id)
    return TraceViewResponse.model_validate(res)

@app.get("/api/system/trace/content/{content_id}", response_model=TraceViewResponse, tags=["Observability"])
async def trace_content_id(content_id: str, db: AsyncSession = Depends(get_db)):
    """Resolves lifecycle timeline for a content_id."""
    res = await telemetry_service.trace_content(db, content_id)
    return TraceViewResponse.model_validate(res)

@app.get("/api/system/telemetry/metrics", tags=["Observability"])
async def get_system_telemetry_metrics(db: AsyncSession = Depends(get_db)):
    """Returns histogram metric latency distributions and execution counts."""
    return await telemetry_service.get_metrics_telemetry(db)

@app.post("/api/system/maintenance", tags=["Observability"])
async def set_system_maintenance_mode(enabled: bool = Query(..., description="Enable/disable maintenance mode")):
    """Toggles operational Maintenance Mode (pausing automatic publishing)."""
    incident_service.set_maintenance_mode(enabled)
    return {"status": "success", "maintenance_mode": incident_service.is_maintenance_mode()}

from fastapi import APIRouter

from routers.v1 import (
    discovery as v1_discovery,
    content as v1_content,
    clips as v1_clips,
    carousels as v1_carousels,
    copy as v1_copy,
    governance as v1_governance,
    publications as v1_publications,
    schedules as v1_schedules,
    analytics as v1_analytics,
    experiments as v1_experiments,
    automations as v1_automations,
    jobs as v1_jobs,
    webhooks as v1_webhooks
)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(v1_discovery.router)
v1_router.include_router(v1_content.router)
v1_router.include_router(v1_clips.router)
v1_router.include_router(v1_carousels.router)
v1_router.include_router(v1_copy.router)
v1_router.include_router(v1_governance.router)
v1_router.include_router(v1_publications.router)
v1_router.include_router(v1_schedules.router)
v1_router.include_router(v1_analytics.router)
v1_router.include_router(v1_experiments.router)
v1_router.include_router(v1_automations.router)
v1_router.include_router(v1_jobs.router)
v1_router.include_router(v1_webhooks.router)

app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)




