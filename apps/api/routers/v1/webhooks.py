from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import APIKey
from models.schemas import WebhookCreateRequest as WebhookEndpointCreateRequest, WebhookResponse as WebhookEndpointResponse
from services.webhook_service import webhook_service
from utils.auth import require_api_key_scopes
from utils.logging import get_logger

logger = get_logger("PublicAPI.Webhooks")
router = APIRouter(prefix="/webhooks", tags=["Public API — Webhooks"])

@router.get("", response_model=List[WebhookEndpointResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("WEBHOOK_READ"))
):
    """Lists registered outbound webhook endpoints."""
    endpoints = await webhook_service.list_endpoints(db)
    return [WebhookEndpointResponse.model_validate(e) for e in endpoints]

@router.post("", response_model=WebhookEndpointResponse)
async def create_webhook(
    req: WebhookEndpointCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("WEBHOOK_WRITE"))
):
    """Subscribes an HTTPS webhook endpoint to event triggers."""
    from utils.security import is_safe_external_url
    is_safe, err = is_safe_external_url(req.url)
    if not is_safe:
        raise HTTPException(
            status_code=400,
            detail={"error": "SSRF_SECURITY_VIOLATION", "message": f"Webhook URL rejected: {err}"}
        )

    endpoint, raw_secret = await webhook_service.create_endpoint(
        db, url=req.url, events=req.events
    )
    res = WebhookEndpointResponse.model_validate(endpoint)
    res.secret = raw_secret # Returned once upon creation
    return res

@router.get("/{id}", response_model=WebhookEndpointResponse)
async def get_webhook_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("WEBHOOK_READ"))
):
    """Gets webhook endpoint detail."""
    endpoint = await webhook_service.get_endpoint(db, id)
    if not endpoint:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Webhook '{id}' not found."}})
    return WebhookEndpointResponse.model_validate(endpoint)

@router.delete("/{id}")
async def delete_webhook(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("WEBHOOK_WRITE"))
):
    """Deletes webhook endpoint subscription."""
    success = await webhook_service.delete_endpoint(db, id)
    if not success:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": f"Webhook '{id}' not found."}})
    return {"status": "success", "id": id, "message": "Webhook subscription deleted."}

@router.post("/{id}/test")
async def test_webhook(
    id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(require_api_key_scopes("WEBHOOK_WRITE"))
):
    """Sends a test ping event delivery to webhook endpoint."""
    res = await webhook_service.send_test_event(db, id)
    return res
