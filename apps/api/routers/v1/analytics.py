from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import APIKey
from services.analytics_service import analytics_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Analytics")
router = APIRouter(prefix="/analytics", tags=["Public API — Analytics"])

@router.get("/overview")
async def get_analytics_overview(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("ANALYTICS_READ"))
):
    """Retrieves high-level performance intelligence overview across published content."""
    overview = await analytics_service.get_overview_analytics(db, start_str=start, end_str=end)
    return overview

@router.get("/content/{id}")
async def get_content_analytics(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("ANALYTICS_READ"))
):
    """Retrieves aggregated analytics metrics for a content item."""
    data = await analytics_service.get_content_analytics(db, content_id=id)
    return data

@router.get("/publications/{id}")
async def get_publication_analytics(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("ANALYTICS_READ"))
):
    """Retrieves real-time analytics for a specific platform publication post."""
    data = await analytics_service.get_publication_analytics(db, publication_id=id)
    if not data:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Publication analytics not found."}})
    return data

@router.get("/platforms")
async def get_platform_analytics(
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("ANALYTICS_READ"))
):
    """Retrieves comparative cross-platform performance metrics."""
    data = await analytics_service.get_platform_analytics(db)
    return data
