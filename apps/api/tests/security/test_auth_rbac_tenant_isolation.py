import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_unauthenticated_request_to_v1_public_api_requires_key():
    """Verify protected public API v1 endpoints reject requests missing API keys with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/content")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"

@pytest.mark.asyncio
async def test_security_headers_present_on_api_responses():
    """Verify security headers X-Content-Type-Options, X-Frame-Options, and Referrer-Policy are present on responses."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
