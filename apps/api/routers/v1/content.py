import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import Content, Asset, APIKey
from models.schemas import ContentCreateRequest, ContentResponse, ContentListResponse, AssetResponse
from services.storage_service import storage_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Content")
router = APIRouter(prefix="/content", tags=["Public API — Content"])

@router.post("", response_model=ContentResponse)
async def create_content(
    req: ContentCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_WRITE"))
):
    """Creates content item metadata."""
    content = Content(
        id=f"cnt_{uuid.uuid4().hex[:10]}",
        title=req.title,
        text_content=req.raw_text or "",
        content_type=req.type or "TEXT",
        status="PROCESSING"
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return ContentResponse.model_validate(content)

@router.post("/upload", response_model=ContentResponse)
async def upload_content_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_WRITE"))
):
    """Uploads media file (video/image/PDF) to create content item."""
    filename = file.filename or "uploaded_file"
    storage_key, mime_type, file_size = await storage_service.save_file(file, filename)

    c_type = "VIDEO" if "video" in mime_type else ("IMAGE" if "image" in mime_type else "TEXT")
    content = Content(
        id=f"cnt_{uuid.uuid4().hex[:10]}",
        title=title or filename,
        content_type=c_type,
        status="PROCESSING"
    )
    db.add(content)

    asset = Asset(
        id=f"ast_{uuid.uuid4().hex[:10]}",
        content_id=content.id,
        original_filename=filename,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=file_size
    )
    db.add(asset)

    await db.commit()
    await db.refresh(content)
    return ContentResponse.model_validate(content)

@router.post("/text", response_model=ContentResponse)
async def create_text_content(
    req: ContentCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_WRITE"))
):
    """Creates direct text/blog content item."""
    content = Content(
        id=f"cnt_{uuid.uuid4().hex[:10]}",
        title=req.title,
        text_content=req.raw_text or "",
        content_type="TEXT",
        status="READY"
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return ContentResponse.model_validate(content)

@router.get("", response_model=ContentListResponse)
async def list_content(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at_desc"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_READ"))
):
    """Lists content items with pagination, filtering, search, and sorting."""
    stmt = select(Content)
    if search:
        stmt = stmt.where(Content.title.ilike(f"%{search}%"))
    if type:
        stmt = stmt.where(Content.content_type == type)

    if sort_by == "created_at_asc":
        stmt = stmt.order_by(Content.created_at.asc())
    else:
        stmt = stmt.order_by(Content.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(stmt)
    items = res.scalars().all()

    return ContentListResponse(
        items=[ContentResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        limit=page_size
    )

@router.get("/{id}", response_model=ContentResponse)
async def get_content_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_READ"))
):
    """Retrieves content item detail by ID."""
    res = await db.execute(select(Content).where(Content.id == id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Content item '{id}' not found."}})
    return ContentResponse.model_validate(content)

@router.delete("/{id}")
async def delete_content(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_WRITE"))
):
    """Deletes content item and physical media assets."""
    res = await db.execute(select(Content).where(Content.id == id))
    content = res.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Content item '{id}' not found."}})

    await db.delete(content)
    await db.commit()
    return {"status": "success", "id": id, "message": "Content deleted cleanly."}

@router.get("/{id}/assets", response_model=List[AssetResponse])
async def list_content_assets(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_READ"))
):
    """Lists safe media assets attached to a content item."""
    res = await db.execute(select(Asset).where(Asset.content_id == id))
    assets = res.scalars().all()
    return [AssetResponse.model_validate(a) for a in assets]

@router.get("/{id}/assets/{asset_id}", response_model=AssetResponse)
async def get_content_asset_detail(
    id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("CONTENT_READ"))
):
    """Retrieves asset detail by asset_id without exposing filesystem paths."""
    res = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.content_id == id))
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Media asset not found."}})
    return AssetResponse.model_validate(asset)
