import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import InboundSource, SourceFeedItem
from services.source_ingestion_service import source_ingestion_service
from utils.logging import get_logger

logger = get_logger("SourcesRouter")

router = APIRouter(prefix="/sources", tags=["Inbound Sources"])

class InboundSourceCreate(BaseModel):
    name: str = Field(..., max_length=128)
    source_type: str = Field(..., description="PODCAST_RSS, YOUTUBE_CHANNEL, TIKTOK, INSTAGRAM, CLOUD_FOLDER, LOCAL_FOLDER")
    config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

class InboundSourceUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

@router.get("", response_model=List[Dict[str, Any]])
async def list_inbound_sources(db: AsyncSession = Depends(get_db)):
    """List all configured inbound sources."""
    stmt = select(InboundSource).order_by(InboundSource.created_at.desc())
    result = await db.execute(stmt)
    sources = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "source_type": s.source_type,
            "config": s.config,
            "last_polled_at": s.last_polled_at.isoformat() if s.last_polled_at else None,
            "last_item_external_id": s.last_item_external_id,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in sources
    ]

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_inbound_source(payload: InboundSourceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new inbound source (e.g. Podcast RSS, folder watcher)."""
    source_id = f"src_{uuid.uuid4().hex[:12]}"
    source = InboundSource(
        id=source_id,
        name=payload.name,
        source_type=payload.source_type.upper(),
        config_json=json.dumps(payload.config),
        is_active=payload.is_active
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return {
        "id": source.id,
        "name": source.name,
        "source_type": source.source_type,
        "config": source.config,
        "is_active": source.is_active,
        "created_at": source.created_at.isoformat()
    }

@router.get("/{source_id}")
async def get_inbound_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Get details and recent items for an inbound source."""
    source = await db.get(InboundSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    items_stmt = select(SourceFeedItem).where(
        SourceFeedItem.source_id == source_id
    ).order_by(SourceFeedItem.detected_at.desc()).limit(20)
    items = (await db.execute(items_stmt)).scalars().all()

    return {
        "id": source.id,
        "name": source.name,
        "source_type": source.source_type,
        "config": source.config,
        "last_polled_at": source.last_polled_at.isoformat() if source.last_polled_at else None,
        "is_active": source.is_active,
        "recent_items": [
            {
                "id": it.id,
                "external_id": it.external_id,
                "title": it.title,
                "media_url": it.media_url,
                "ingestion_status": it.ingestion_status,
                "content_id": it.content_id,
                "detected_at": it.detected_at.isoformat() if it.detected_at else None
            }
            for it in items
        ]
    }

@router.post("/{source_id}/poll")
async def trigger_source_poll(source_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger polling for an inbound source."""
    try:
        result = await source_ingestion_service.poll_source(db, source_id)
        return result
    except Exception as e:
        logger.error(f"Manual poll failed for source '{source_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inbound_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an inbound source."""
    source = await db.get(InboundSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    await db.delete(source)
    await db.commit()
    return None
