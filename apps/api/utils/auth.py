import hashlib
import json
from datetime import datetime
from typing import List, Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.entities import APIKey
from utils.logging import get_logger

logger = get_logger("APIAuth")

async def get_current_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """
    Extracts and validates API Key from 'Authorization: Bearer reflow_live_...'
    or 'X-API-Key: reflow_live_...' headers.
    """
    raw_key = None
    if authorization and authorization.startswith("Bearer "):
        raw_key = authorization[7:].strip()
    elif x_api_key:
        raw_key = x_api_key.strip()

    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Missing API Key header. Use 'Authorization: Bearer <key>' or 'X-API-Key: <key>'"}}
        )

    hashed = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
    res = await db.execute(select(APIKey).where(APIKey.hashed_key == hashed))
    api_key_obj = res.scalar_one_or_none()

    if not api_key_obj:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "INVALID_API_KEY", "message": "The provided API key is invalid or revoked."}}
        )

    if api_key_obj.expires_at and datetime.utcnow() > api_key_obj.expires_at:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "EXPIRED_API_KEY", "message": "This API key has expired."}}
        )

    api_key_obj.last_used_at = datetime.utcnow()
    await db.commit()

    return api_key_obj

class ScopeChecker:
    def __init__(self, *required_scopes: str):
        self.required_scopes = required_scopes

    async def __call__(self, api_key: APIKey = Depends(get_current_api_key)) -> APIKey:
        try:
            assigned_scopes = set(json.loads(api_key.permissions_json or "[]"))
        except Exception:
            assigned_scopes = set()

        missing_scopes = [s for s in self.required_scopes if s not in assigned_scopes]
        if missing_scopes and "*" not in assigned_scopes:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "FORBIDDEN_SCOPE",
                        "message": f"Insufficient API key scopes. Missing required scope(s): {', '.join(missing_scopes)}"
                    }
                }
            )

        return api_key

def require_api_key_scopes(*required_scopes: str):
    return ScopeChecker(*required_scopes)
