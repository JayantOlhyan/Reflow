import time
import hmac
import hashlib
import json
import uuid
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select
from database import async_session_factory
from models.entities import WebhookEndpoint
from utils.logging import get_logger

logger = get_logger("WebhookService")

class WebhookService:
    """
    Outbound Webhook Delivery Service.
    Dispatches signed payloads for Reflow lifecycle events.
    """
    _instance: Optional['WebhookService'] = None

    @classmethod
    def get_instance(cls) -> 'WebhookService':
        if cls._instance is None:
            cls._instance = WebhookService()
        return cls._instance

    def compute_signature(self, secret: str, timestamp: int, payload_bytes: bytes) -> str:
        """Computes HMAC-SHA256 signature for payload verification."""
        message = f"{timestamp}.".encode("utf-8") + payload_bytes
        signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={signature}"

    async def dispatch_event(self, event_type: str, data: Dict[str, Any]) -> int:
        """
        Dispatches an event to all matching active webhook endpoints.
        Returns the count of triggered endpoints.
        """
        async with async_session_factory() as session:
            res = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.enabled == True))
            endpoints = res.scalars().all()

        matching = [ep for ep in endpoints if event_type in json.loads(ep.events_json or "[]")]
        if not matching:
            return 0

        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        timestamp = int(time.time())
        payload = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "data": data
        }
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')

        dispatched_count = 0
        for ep in matching:
            signature = self.compute_signature(ep.secret, timestamp, payload_bytes)
            # Dispatch asynchronously in background task
            asyncio.create_task(self._deliver_payload(ep.id, ep.url, signature, payload_bytes))
            dispatched_count += 1

        logger.info(f"Dispatched webhook event '{event_type}' ({event_id}) to {dispatched_count} endpoint(s).")
        return dispatched_count

    async def _deliver_payload(self, endpoint_id: str, url: str, signature: str, payload_bytes: bytes, max_retries: int = 3) -> bool:
        """Delivers signed webhook payload with exponential backoff retries."""
        from utils.security import is_safe_external_url
        is_safe, err = is_safe_external_url(url)
        if not is_safe:
            logger.error(f"Webhook delivery blocked by SSRF security check for {url}: {err}")
            await self._update_endpoint_status(endpoint_id, success=False)
            return False

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Reflow-Webhook/1.0",
            "X-Reflow-Signature": signature
        }

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, content=payload_bytes, headers=headers)
                    if resp.status_code >= 200 and resp.status_code < 300:
                        logger.info(f"Webhook delivery succeeded to {url} (attempt {attempt})")
                        await self._update_endpoint_status(endpoint_id, success=True)
                        return True
                    else:
                        logger.warning(f"Webhook delivery returned HTTP {resp.status_code} from {url} (attempt {attempt})")
            except Exception as e:
                logger.warning(f"Webhook delivery failed to {url} (attempt {attempt}): {e}")

            if attempt < max_retries:
                await asyncio.sleep(2 ** (attempt - 1))

        logger.error(f"Webhook delivery permanently failed to {url} after {max_retries} attempts.")
        await self._update_endpoint_status(endpoint_id, success=False)
        return False

    async def _update_endpoint_status(self, endpoint_id: str, success: bool):
        try:
            async with async_session_factory() as session:
                res = await session.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id))
                ep = res.scalar_one_or_none()
                if ep:
                    if success:
                        ep.last_success_at = datetime.utcnow()
                    else:
                        ep.last_failure_at = datetime.utcnow()
                    ep.updated_at = datetime.utcnow()
                    await session.commit()
        except Exception as e:
            logger.warning(f"Failed to update webhook endpoint status for {endpoint_id}: {e}")

webhook_service = WebhookService.get_instance()
