import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import GovernanceResult, GovernancePolicy, APIKey
from services.quality_control_service import quality_control_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Governance")
router = APIRouter(prefix="", tags=["Public API — Governance"])

@router.post("/content/{content_id}/governance/evaluate")
async def evaluate_governance(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("GOVERNANCE_READ"))
):
    """Evaluates content governance quality control checks against active policies."""
    report = await quality_control_service.run_pipeline(session=db, content_id=content_id)
    return report

@router.get("/governance/policies")
async def list_policies(
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("GOVERNANCE_READ"))
):
    """Lists active brand governance policies and compliance rules."""
    res = await db.execute(select(GovernancePolicy).where(GovernancePolicy.is_active == True))
    policies = res.scalars().all()
    return {"policies": policies}

@router.get("/governance/reports/{report_id}")
async def get_governance_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("GOVERNANCE_READ"))
):
    """Gets detailed governance quality report by ID."""
    res = await db.execute(select(GovernanceResult).where(GovernanceResult.id == report_id))
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Governance report '{report_id}' not found."}})
    return report
