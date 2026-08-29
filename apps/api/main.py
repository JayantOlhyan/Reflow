import sys
import os
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from typing import Dict, Any, List, Optional

from config import settings
from database import get_db, init_db
from models.entities import (
    Content, Asset, ContentVariant, Transcript, TranscriptSegment,
    ContentBrief, GeneratedContent, PlatformConnection, Workflow, Job, SystemLog
)
from models.schemas import (
    ContentResponse, ContentListResponse, TextContentCreateRequest,
    TranscriptResponse, ContentBriefResponse, GeneratedContentResponse,
    AIGenerateRequest, RepurposeRequest, AICarouselPrompt, SchedulePostRequest,
    PlatformConnectionSchema, PlatformConnectionUpdate, HealthResponse, ApiResponse,
    JobResponse
)
from services.media_service import media_processor
from services.queue_service import queue_service
from services.ai_service import ai_service
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
    total_res = await db.execute(select(func.count(Content.id)))
    total_count = total_res.scalar() or 0

    pub_res = await db.execute(select(func.count(Content.id)).where(Content.status == "READY"))
    published_count = pub_res.scalar() or 0

    sched_res = await db.execute(select(func.count(Job.id)).where(Job.status == "QUEUED"))
    scheduled_count = sched_res.scalar() or 0

    failed_res = await db.execute(select(func.count(Job.id)).where(Job.status == "FAILED"))
    failed_count = failed_res.scalar() or 0

    recent_jobs_res = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(5))
    recent_jobs = recent_jobs_res.scalars().all()

    conn_res = await db.execute(select(PlatformConnection))
    connections = conn_res.scalars().all()

    return {
        "metrics": {
            "total": total_count,
            "published": published_count,
            "scheduled": scheduled_count,
            "failed": failed_count
        },
        "recent_activity": [
            {
                "id": j.id,
                "title": j.type,
                "status": j.status.lower(),
                "created_at": j.created_at.isoformat() if j.created_at else None
            }
            for j in recent_jobs
        ],
        "connections": [
            {
                "id": c.id,
                "name": c.name,
                "handle": c.handle,
                "connected": c.connected,
                "capabilities": c.capabilities
            }
            for c in connections
        ]
    }

# ------------------------------------------------------------------------------
# Content Ingestion & Media Processing Pipeline
# ------------------------------------------------------------------------------

@app.post("/api/content/upload", response_model=ContentResponse, tags=["Content"])
async def upload_content(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    filename = file.filename or "uploaded_file"
    file_bytes = await file.read()
    file_size = len(file_bytes)
    mime_type = file.content_type or "application/octet-stream"

    # Multi-layer validation
    is_valid, detected_type, error_msg = validate_upload(filename, mime_type, file_size)
    if not is_valid or not detected_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    content_id = f"cnt_{uuid.uuid4().hex[:12]}"
    asset_id = f"ast_{uuid.uuid4().hex[:12]}"
    content_title = title.strip() if title and title.strip() else filename

    storage_key = generate_storage_key(content_id, asset_id, filename)

    # 1. Write to storage
    try:
        await storage_service.put(storage_key, file_bytes)
    except Exception as e:
        logger.error(f"Storage write failed for {filename}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist file to storage.")

    # 2. Persist Content + Asset in Database
    try:
        initial_status = "PROCESSING" if detected_type == "VIDEO" else "READY"
        content = Content(
            id=content_id,
            title=content_title,
            content_type=detected_type,
            status=initial_status,
            created_at=datetime.utcnow()
        )
        db.add(content)

        asset = Asset(
            id=asset_id,
            content_id=content_id,
            original_filename=filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=file_size,
            created_at=datetime.utcnow()
        )
        db.add(asset)

        job = None
        if detected_type == "VIDEO":
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
        await db.refresh(content)

        # 3. Enqueue to Background Media Worker via Redis
        if detected_type == "VIDEO" and job:
            await queue_service.enqueue_media_job(job.id, content_id, asset_id, job_type="MEDIA_PROCESSING")

        logger.info(f"Successfully ingested {detected_type} asset '{filename}' -> Content ID: {content_id} (Status: {initial_status})")
        return content

    except Exception as e:
        logger.error(f"Database error saving {content_id}, rolling back storage: {e}")
        await storage_service.delete(storage_key)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database transaction failed during content ingestion.")

@app.post("/api/content/text", response_model=ContentResponse, tags=["Content"])
async def create_text_content(
    req: TextContentCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    content_id = f"cnt_{uuid.uuid4().hex[:12]}"
    content = Content(
        id=content_id,
        title=req.title,
        content_type="TEXT",
        status="READY",
        text_content=req.text,
        created_at=datetime.utcnow()
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    logger.info(f"Created text content asset: {content.id} ({content.title})")
    return content

@app.post("/api/content/{content_id}/reprocess", response_model=ApiResponse, tags=["Content"])
async def reprocess_content_media(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content or content.content_type != "VIDEO":
        raise HTTPException(status_code=404, detail="Video content item not found.")

    if not content.assets:
        raise HTTPException(status_code=400, detail="Content has no associated media assets.")

    asset_id = content.assets[0].id
    content.status = "PROCESSING"

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
    return ApiResponse(status="success", message=f"Media reprocessing queued for Content {content_id}.")

@app.get("/api/content", response_model=ContentListResponse, tags=["Content"])
async def list_content(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Content)
    count_stmt = select(func.count(Content.id))

    if type and type.upper() != "ALL":
        stmt = stmt.where(Content.content_type == type.upper())
        count_stmt = count_stmt.where(Content.content_type == type.upper())

    if status:
        stmt = stmt.where(Content.status == status.upper())
        count_stmt = count_stmt.where(Content.status == status.upper())

    if search:
        search_filter = or_(
            Content.title.ilike(f"%{search}%"),
            Content.text_content.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    offset = (page - 1) * limit
    stmt = stmt.order_by(Content.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return ContentListResponse(
        items=items,
        total=total_count,
        page=page,
        limit=limit
    )

@app.get("/api/content/{content_id}", response_model=ContentResponse, tags=["Content"])
async def get_content(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found.")
    return content

@app.get("/api/content/{content_id}/asset/{asset_id}", tags=["Content"])
async def stream_asset(content_id: str, asset_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.content_id == content_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset file not found.")

    real_path = storage_service.get_real_path(asset.storage_key)
    if not os.path.exists(real_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage file missing from disk.")

    return FileResponse(
        path=real_path,
        media_type=asset.mime_type,
        filename=asset.original_filename
    )

@app.get("/api/content/{content_id}/variant/{variant_id}", tags=["Content"])
async def stream_variant(content_id: str, variant_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContentVariant).where(ContentVariant.id == variant_id, ContentVariant.content_id == content_id))
    variant = result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant file not found.")

    real_path = storage_service.get_real_path(variant.storage_key)
    if not os.path.exists(real_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant file missing from disk.")

    return FileResponse(
        path=real_path,
        media_type=variant.mime_type,
        filename=os.path.basename(variant.storage_key)
    )

@app.delete("/api/content/{content_id}", response_model=ApiResponse, tags=["Content"])
async def delete_content(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found.")

    for asset in content.assets:
        try:
            await storage_service.delete(asset.storage_key)
        except Exception:
            pass

    for variant in content.variants:
        try:
            await storage_service.delete(variant.storage_key)
        except Exception:
            pass

    await db.delete(content)
    await db.commit()
    logger.info(f"Deleted Content {content_id} and all related physical storage variants & AI outputs.")
    return ApiResponse(status="success", message=f"Content {content_id} and all related variants deleted.")

# ------------------------------------------------------------------------------
# Phase 3 AI Content Intelligence Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/content/{content_id}/transcript", response_model=TranscriptResponse, tags=["AI Intelligence"])
async def get_transcript(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transcript).where(Transcript.content_id == content_id))
    transcript = result.scalars().first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found for this content.")
    return transcript

@app.get("/api/content/{content_id}/brief", response_model=ContentBriefResponse, tags=["AI Intelligence"])
async def get_content_brief(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContentBrief).where(ContentBrief.content_id == content_id))
    brief = result.scalars().first()
    if not brief:
        raise HTTPException(status_code=404, detail="ContentBrief not found for this content.")
    return ContentBriefResponse(
        id=brief.id,
        content_id=brief.content_id,
        transcript_id=brief.transcript_id,
        title=brief.title,
        summary=brief.summary,
        topics=brief.topics,
        keywords=brief.keywords,
        audience=brief.audience,
        tone=brief.tone,
        key_points=brief.key_points,
        hooks=brief.hooks,
        quotes=brief.quotes,
        cta_suggestions=brief.cta_suggestions,
        provider=brief.provider,
        model=brief.model,
        prompt_version=brief.prompt_version,
        created_at=brief.created_at
    )

@app.get("/api/content/{content_id}/generated", response_model=List[GeneratedContentResponse], tags=["AI Intelligence"])
async def get_generated_content(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GeneratedContent)
        .where(GeneratedContent.content_id == content_id)
        .order_by(GeneratedContent.platform.asc(), GeneratedContent.version.desc())
    )
    items = result.scalars().all()
    return [
        GeneratedContentResponse(
            id=g.id,
            content_id=g.content_id,
            brief_id=g.brief_id,
            platform=g.platform,
            generation_type=g.generation_type,
            status=g.status,
            payload=g.payload,
            provider=g.provider,
            model=g.model,
            prompt_version=g.prompt_version,
            version=g.version,
            created_at=g.created_at
        )
        for g in items
    ]

@app.post("/api/content/{content_id}/generate", response_model=ApiResponse, tags=["AI Intelligence"])
async def trigger_ai_generation(
    content_id: str,
    req: AIGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content asset not found.")

    asset_id = content.assets[0].id if content.assets else "text_asset"
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = Job(
        id=job_id,
        content_id=content_id,
        asset_id=asset_id,
        type="CONTENT_GENERATION",
        status="QUEUED",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()

    await queue_service.enqueue_media_job(job_id, content_id, asset_id, job_type="CONTENT_GENERATION")
    return ApiResponse(status="success", message=f"AI generation job {job_id} queued for {req.platforms}.")

@app.post("/api/content/{content_id}/regenerate/{platform}", response_model=ApiResponse, tags=["AI Intelligence"])
async def regenerate_single_platform(
    content_id: str,
    platform: str,
    tone: Optional[str] = "professional",
    db: AsyncSession = Depends(get_db)
):
    plt_upper = platform.upper()
    if plt_upper not in ["LINKEDIN", "INSTAGRAM", "X", "YOUTUBE"]:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    # Generate immediately in async handler or via queue
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
# Carousel Studio (Phase 4)
# ------------------------------------------------------------------------------

@app.post("/api/carousels/generate", tags=["Carousel"])
async def generate_carousel_deck(prompt: AICarouselPrompt):
    topic = prompt.topic.strip() or "Automate Your Content Engine"
    slides = [
        {"id": "g1", "title": topic, "subtitle": "01 / 04", "body": "The definitive blueprint for high-impact creators.", "tag": "OVERVIEW"},
        {"id": "g2", "title": "The Repetitive Bottleneck", "subtitle": "02 / 04", "body": "Creators waste over 15 hours weekly manually formatting cross-platform content.", "tag": "PROBLEM"},
        {"id": "g3", "title": "The Unified Pipeline", "subtitle": "03 / 04", "body": "Feed one canonical asset into Reflow to generate native formats everywhere.", "tag": "SOLUTION"},
        {"id": "g4", "title": "Start Automating", "subtitle": "04 / 04", "body": "Deploy locally with Docker and own your data and distribution end-to-end.", "tag": "ACTION"}
    ]
    return {"slides": slides}

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
