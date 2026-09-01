import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select

from models.entities import IdempotencyRecord
from utils.logging import get_logger

logger = get_logger("IdempotencyService")

class IdempotencyService:
    """
    Manages persistent request idempotency key validation.
    Prevents duplicate execution of dangerous mutation requests (publishing, scheduling, generation).
    """
    _instance: Optional['IdempotencyService'] = None

    @classmethod
    def get_instance(cls) -> 'IdempotencyService':
        if cls._instance is None:
            cls._instance = IdempotencyService()
        return cls._instance

    def hash_payload(self, data: Any) -> str:
        """Creates a stable SHA-256 hash representation of request payload."""
        if isinstance(data, (dict, list)):
            raw = json.dumps(data, sort_keys=True)
        else:
            raw = str(data)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    async def check_idempotency(self, session, key: str, request_hash: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Validates idempotency key against database.
        - Matching key & payload hash -> returns (status_code, cached_response_dict)
        - Matching key but DIFFERENT payload hash -> raises ValueError("IDEMPOTENCY_CONFLICT")
        - Key not found -> returns None
        """
        if not key or not key.strip():
            return None

        res = await session.execute(
            select(IdempotencyRecord).where(IdempotencyRecord.key == key.strip())
        )
        record = res.scalar_one_or_none()
        if not record:
            return None

        if record.request_hash != request_hash:
            logger.warning(f"Idempotency conflict detected for key '{key}'")
            raise ValueError("IDEMPOTENCY_CONFLICT: Idempotency-Key reused with different request payload.")

        try:
            cached_data = json.loads(record.response_json or "{}")
        except:
            cached_data = {}

        logger.info(f"Idempotency cache hit for key '{key}' (status={record.status_code})")
        return (record.status_code, cached_data)

    async def record_idempotency(self, session, key: str, request_hash: str, status_code: int, response_data: Dict[str, Any]):
        """Records idempotency key response in database."""
        if not key or not key.strip():
            return

        rec = IdempotencyRecord(
            id=str(uuid.uuid4()),
            key=key.strip(),
            request_hash=request_hash,
            status_code=status_code,
            response_json=json.dumps(response_data),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        session.add(rec)
        await session.commit()

idempotency_service = IdempotencyService.get_instance()
