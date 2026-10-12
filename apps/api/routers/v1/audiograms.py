import os
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import Content, Asset, AudiogramTemplate, APIKey
from services.audiogram_service import audiogram_service
from services.storage_service import storage_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Audiograms")
router = APIRouter(tags=["Public API — Audiograms"])

class AudiogramTemplateCreate(BaseModel):
    name: str = Field(..., max_length=128)
    aspect_ratio: str = Field(default="9:16")
    waveform_style: str = Field(default="BARS")
    waveform_color: str = Field(default="#6366F1")
    background_color: str = Field(default="#0F172A")
    background_image_path: Optional[str] = None
    title_template: Optional[str] = "{{title}}"
    show_progress_bar: bool = True
    progress_bar_color: str = "#10B981"
    caption_style: str = "BOLD_PUNCH"

class AudiogramGenerateRequest(BaseModel):
    template_id: Optional[str] = None
    aspect_ratio: str = "9:16"
    waveform_style: str = "BARS"
    waveform_color: str = "#6366F1"
    background_color: str = "#0F172A"
    duration: Optional[float] = None

DEFAULT_TEMPLATES = [
    {
        "id": "tpl_vert_bars",
        "name": "Vertical Stories & Reels (Bars)",
        "aspect_ratio": "9:16",
        "waveform_style": "BARS",
        "waveform_color": "#6366F1",
        "background_color": "#0F172A",
        "caption_style": "BOLD_PUNCH"
    },
    {
        "id": "tpl_sq_wave",
        "name": "Square Feed (Smooth Wave)",
        "aspect_ratio": "1:1",
        "waveform_style": "LINE",
        "waveform_color": "#10B981",
        "background_color": "#18181B",
        "caption_style": "CLEAN_SUB"
    },
    {
        "id": "tpl_land_classic",
        "name": "Landscape YouTube (Classic Bars)",
        "aspect_ratio": "16:9",
        "waveform_style": "BARS",
        "waveform_color": "#EC4899",
        "background_color": "#09090B",
        "caption_style": "BOLD_PUNCH"
    }
]

@router.get("/audiograms/templates")
async def list_audiogram_templates(
    db: AsyncSession = Depends(get_db)
):
    """Lists saved audiogram templates."""
    res = await db.execute(select(AudiogramTemplate))
    db_templates = res.scalars().all()
    
    if not db_templates:
        return DEFAULT_TEMPLATES
        
    return [
        {
            "id": t.id,
            "name": t.name,
            "aspect_ratio": t.aspect_ratio,
            "waveform_style": t.waveform_style,
            "waveform_color": t.waveform_color,
            "background_color": t.background_color,
            "background_image_path": t.background_image_path,
            "title_template": t.title_template,
            "show_progress_bar": t.show_progress_bar,
            "progress_bar_color": t.progress_bar_color,
            "caption_style": t.caption_style
        }
        for t in db_templates
    ]

@router.post("/audiograms/templates", status_code=status.HTTP_201_CREATED)
async def create_audiogram_template(
    payload: AudiogramTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """Creates a new audiogram template."""
    tmpl = AudiogramTemplate(
        id=f"tpl_aud_{uuid.uuid4().hex[:10]}",
        name=payload.name,
        aspect_ratio=payload.aspect_ratio,
        waveform_style=payload.waveform_style,
        waveform_color=payload.waveform_color,
        background_color=payload.background_color,
        background_image_path=payload.background_image_path,
        title_template=payload.title_template,
        show_progress_bar=payload.show_progress_bar,
        progress_bar_color=payload.progress_bar_color,
        caption_style=payload.caption_style
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return {"status": "success", "id": tmpl.id, "name": tmpl.name}

@router.post("/content/{content_id}/audiograms/generate")
async def generate_content_audiogram(
    content_id: str,
    req: AudiogramGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generates an MP4 audiogram from an audio or video asset belonging to a content item."""
    c_res = await db.execute(select(Content).where(Content.id == content_id))
    content = c_res.scalar_one_or_none()
    if not content:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Content item '{content_id}' not found."}}
        )

    # Locate an audio or video asset for this content
    a_res = await db.execute(
        select(Asset).where(
            Asset.content_id == content_id,
            Asset.type.in_(["AUDIO_EXTRACTED", "RAW_UPLOAD", "VIDEO_OPTIMIZED"])
        )
    )
    assets = a_res.scalars().all()
    if not assets:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NO_MEDIA", "message": "Content item has no usable audio or video assets."}}
        )

    # Prefer AUDIO_EXTRACTED, fallback to any available asset
    source_asset = next((a for a in assets if a.type == "AUDIO_EXTRACTED"), assets[0])
    source_path = storage_service.get_full_path(source_asset.storage_key)

    if not os.path.exists(source_path):
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "FILE_MISSING", "message": f"Media file '{source_asset.storage_key}' not found on storage."}}
        )

    # If template_id provided, load options from template
    aspect_ratio = req.aspect_ratio
    waveform_style = req.waveform_style
    waveform_color = req.waveform_color
    background_color = req.background_color

    if req.template_id:
        t_res = await db.execute(select(AudiogramTemplate).where(AudiogramTemplate.id == req.template_id))
        tmpl = t_res.scalar_one_or_none()
        if tmpl:
            aspect_ratio = tmpl.aspect_ratio
            waveform_style = tmpl.waveform_style
            waveform_color = tmpl.waveform_color
            background_color = tmpl.background_color

    output_key = f"audiograms/{content_id}_{uuid.uuid4().hex[:8]}.mp4"

    try:
        render_res = await audiogram_service.generate_audiogram(
            audio_file_path=source_path,
            output_storage_key=output_key,
            aspect_ratio=aspect_ratio,
            waveform_style=waveform_style,
            waveform_color=waveform_color,
            background_color=background_color,
            duration=req.duration
        )
    except Exception as e:
        logger.error(f"Audiogram synthesis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "RENDER_FAILED", "message": f"Audiogram synthesis failed: {str(e)}"}}
        )

    # Create Asset record
    audiogram_asset = Asset(
        id=f"ast_aud_{uuid.uuid4().hex[:10]}",
        content_id=content_id,
        type="VIDEO_VARIANT",
        storage_key=output_key,
        mime_type="video/mp4",
        file_size=render_res.get("file_size", 0),
        duration=req.duration or content.duration_seconds or 0
    )
    db.add(audiogram_asset)
    await db.commit()
    await db.refresh(audiogram_asset)

    return {
        "status": "success",
        "asset_id": audiogram_asset.id,
        "storage_key": output_key,
        "aspect_ratio": aspect_ratio,
        "waveform_style": waveform_style,
        "file_size": render_res.get("file_size", 0),
        "url": f"/api/content/{content_id}/asset/{audiogram_asset.id}"
    }
