from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import APIKey
from models.schemas import AutomationRuleCreateRequest, AutomationRuleResponse
from services.automation_service import automation_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Automations")
router = APIRouter(prefix="/automations", tags=["Public API — Automations"])

@router.get("", response_model=List[AutomationRuleResponse])
async def list_automations(
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("AUTOMATION_READ"))
):
    """Lists automation rules."""
    rules = await automation_service.list_rules(db)
    return [AutomationRuleResponse.model_validate(r) for r in rules]

@router.post("", response_model=AutomationRuleResponse)
async def create_automation(
    req: AutomationRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("AUTOMATION_WRITE"))
):
    """Creates a new closed-loop automation rule."""
    rule = await automation_service.create_rule(
        db,
        name=req.name,
        trigger_event=req.trigger_event,
        conditions=[c.model_dump() for c in req.conditions],
        actions=[a.model_dump() for a in req.actions]
    )
    return AutomationRuleResponse.model_validate(rule)

@router.get("/{id}", response_model=AutomationRuleResponse)
async def get_automation_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("AUTOMATION_READ"))
):
    """Gets automation rule detail by ID."""
    rule = await automation_service.get_rule(db, id)
    if not rule:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Automation rule '{id}' not found."}})
    return AutomationRuleResponse.model_validate(rule)

@router.delete("/{id}")
async def delete_automation(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("AUTOMATION_WRITE"))
):
    """Deletes automation rule."""
    success = await automation_service.delete_rule(db, id)
    if not success:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Automation rule '{id}' not found."}})
    return {"status": "success", "id": id, "message": "Automation rule deleted."}

@router.post("/{id}/enable")
async def enable_automation(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("AUTOMATION_WRITE"))
):
    """Enables automation rule."""
    res = await automation_service.set_rule_enabled(db, id, enabled=True)
    return res

@router.post("/{id}/disable")
async def disable_automation(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("AUTOMATION_WRITE"))
):
    """Disables automation rule."""
    res = await automation_service.set_rule_enabled(db, id, enabled=False)
    return res
