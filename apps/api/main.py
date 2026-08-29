import sys
import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Dict, Any, List

from config import settings
from database import get_db, init_db
from models.entities import Content, ContentVariant, PlatformConnection, Workflow, Job, SystemLog
from models.schemas import (
    ContentItem, ContentCreateRequest, RepurposeRequest,
    AICarouselPrompt, SchedulePostRequest, PlatformConnectionSchema,
    PlatformConnectionUpdate, HealthResponse, ApiResponse
)
from services.media_service import media_processor
from services.ai_service import ai_service
from services.health_service import health_service
from services.storage_service import storage_service, validate_upload
from utils.logging import get_logger

logger = get_logger("ReflowAPI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    logger.info("Reflow API starting up... Initializing database schema.")
    await init_db()
    yield
    logger.info("Reflow API shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Open-source self-hosted content repurposing engine",
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
    """Simple liveness probe indicating the HTTP process is running."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@app.get("/api/system/health", response_model=HealthResponse, tags=["System"])
async def system_health_telemetry():
    """Real active component health check for Database, Storage, FFmpeg, and AI."""
    health_data = await health_service.get_overall_health()
    return health_data

# ------------------------------------------------------------------------------
# Overview Dashboard Metrics
# ------------------------------------------------------------------------------

@app.get("/api/overview", tags=["Overview"])
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Returns genuine overview metrics calculated from database records with NO fake fallbacks."""
    # Count total content
    total_res = await db.execute(select(func.count(Content.id)))
    total_count = total_res.scalar() or 0

    # Count published content
    pub_res = await db.execute(select(func.count(Content.id)).where(Content.status == "published"))
    published_count = pub_res.scalar() or 0

    # Count scheduled jobs
    sched_res = await db.execute(select(func.count(Job.id)).where(Job.status == "QUEUED"))
    scheduled_count = sched_res.scalar() or 0

    # Count failed jobs
    failed_res = await db.execute(select(func.count(Job.id)).where(Job.status == "FAILED"))
    failed_count = failed_res.scalar() or 0

    # Fetch recent jobs
    recent_jobs_res = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(5))
    recent_jobs = recent_jobs_res.scalars().all()

    # Fetch connections
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
# Content Library CRUD
# ------------------------------------------------------------------------------

@app.get("/api/content", response_model=List[ContentItem], tags=["Content"])
async def list_content(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).order_by(Content.created_at.desc()))
    items = result.scalars().all()
    return [
        ContentItem(
            id=item.id,
            title=item.title,
            type=item.type,
            source=item.source or "",
            thumbnail=item.thumbnail or "",
            duration=item.duration,
            slide_count=item.slide_count,
            dimensions=item.dimensions,
            status=item.status,
            created_at=item.created_at.strftime("%b %d, %Y") if item.created_at else None,
            destinations=[],
            variants=[]
        )
        for item in items
    ]

@app.post("/api/content", response_model=ContentItem, tags=["Content"])
async def create_content(req: ContentCreateRequest, db: AsyncSession = Depends(get_db)):
    new_id = f"cnt-{int(datetime.utcnow().timestamp())}"
    content = Content(
        id=new_id,
        title=req.title,
        type=req.type,
        source=req.source or "",
        thumbnail=req.thumbnail or "",
        duration=req.duration,
        slide_count=req.slide_count,
        dimensions=req.dimensions,
        status="draft"
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    logger.info(f"Created content asset: {content.id} ({content.title})")
    
    return ContentItem(
        id=content.id,
        title=content.title,
        type=content.type,
        source=content.source,
        thumbnail=content.thumbnail,
        duration=content.duration,
        slide_count=content.slide_count,
        dimensions=content.dimensions,
        status=content.status,
        created_at="Just now",
        destinations=req.destinations,
        variants=[]
    )

@app.delete("/api/content/{content_id}", response_model=ApiResponse, tags=["Content"])
async def delete_content(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content item not found.")
    await db.delete(content)
    await db.commit()
    return ApiResponse(status="success", message=f"Content {content_id} deleted successfully.")

# ------------------------------------------------------------------------------
# Repurposing & AI Transformation
# ------------------------------------------------------------------------------

@app.post("/api/repurpose/generate", tags=["Repurpose"])
async def generate_repurpose(req: RepurposeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == req.content_id))
    content = result.scalar_one_or_none()
    title = content.title if content else "Untitled Content Asset"
    
    outputs = await ai_service.generate_platform_repurpose(
        source_title=title,
        destinations=req.destinations
    )
    return {
        "content_id": req.content_id,
        "target_format": req.target_format,
        "outputs": outputs
    }

# ------------------------------------------------------------------------------
# Carousel Studio
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
# Platform Connections & Publishing (Explicit Not Implemented in Phase 0)
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
    """Explicitly returns not_implemented in Phase 0."""
    return {
        "status": "not_implemented",
        "platform": platform,
        "operation": "publish",
        "message": "Real publishing integration is not implemented yet. Scheduled for Phase 5."
    }

@app.post("/api/schedule", tags=["Publishing"])
async def schedule_content(req: SchedulePostRequest):
    """Explicitly returns not_implemented in Phase 0."""
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
