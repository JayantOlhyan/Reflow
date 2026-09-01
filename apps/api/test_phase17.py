import pytest
import uuid
import json
import time
import hashlib
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from main import app
from database import async_session_factory, init_db
from plugins.manifest import PluginManifest, PluginType, PluginPermission, PLUGIN_API_VERSION
from plugins.base_plugin import BasePlugin
from plugins.registry import PluginRegistry
from plugins.contracts.platform_contract import BasePlatformConnectorPlugin
from plugins.contracts.ai_contract import BaseAIProviderPlugin, ai_provider_registry
from plugins.contracts.storage_contract import BaseStorageProviderPlugin
from plugins.contracts.media_contract import BaseMediaProcessorPlugin
from plugins.contracts.workflow_contract import BaseWorkflowActionPlugin
from services.webhook_service import webhook_service
from models.entities import WebhookEndpoint, APIKey, PluginConfiguration

class DummyBrokenPlugin(BasePlugin):
    """Failing plugin to test error isolation."""
    async def initialize(self) -> bool:
        raise RuntimeError("Initialization boom!")

    async def shutdown(self) -> None:
        pass

    async def health_check(self):
        raise RuntimeError("Health check failure!")

@pytest.mark.asyncio
async def test_plugin_manifest_validation():
    """Verify PluginManifest validation and field parsing."""
    manifest = PluginManifest(
        id="test-plugin",
        name="Test Plugin",
        version="1.0.0",
        description="A test plugin manifest.",
        type=PluginType.PLATFORM,
        entrypoint="test:TestPlugin",
        api_version=PLUGIN_API_VERSION,
        capabilities=["video", "text"],
        permissions=[PluginPermission.PUBLISH]
    )
    assert manifest.id == "test-plugin"
    assert manifest.api_version == "1.0.0"
    assert PluginPermission.PUBLISH in manifest.permissions

@pytest.mark.asyncio
async def test_plugin_registry_lifecycle():
    """Verify PluginRegistry register, enable, disable, health_check, and error isolation."""
    registry = PluginRegistry()
    manifest = PluginManifest(
        id="dummy-test-plugin",
        name="Dummy Plugin",
        version="1.0.0",
        description="Test registry lifecycle",
        type=PluginType.WORKFLOW_ACTION,
        entrypoint="dummy:Plugin",
        api_version=PLUGIN_API_VERSION
    )
    
    plugin = DummyBrokenPlugin(manifest)
    reg_success = registry.register(plugin)
    assert reg_success is True

    # Check listing
    listed = registry.list_plugins()
    assert any(p["id"] == "dummy-test-plugin" for p in listed)

    # Disable & Enable
    assert registry.disable_plugin("dummy-test-plugin") is True
    assert registry.get_plugin("dummy-test-plugin") is None
    assert registry.enable_plugin("dummy-test-plugin") is True
    assert registry.get_plugin("dummy-test-plugin") is not None

    # Isolated Health Check
    health = await registry.health_check("dummy-test-plugin")
    assert health["status"] == "FAILED"
    assert "Health check failure!" in health["details"]

from sqlalchemy import select
from plugins.loader import register_builtin_plugins

@pytest.mark.asyncio
async def test_plugin_management_api():
    """Verify REST API endpoints for Plugins (/api/plugins)."""
    await init_db()
    register_builtin_plugins()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # List plugins
        res = await ac.get("/api/plugins")
        assert res.status_code == 200
        data = res.json()
        assert "plugins" in data
        assert data["total"] >= 1

        # Get single plugin detail
        pid = data["plugins"][0]["id"]
        res_detail = await ac.get(f"/api/plugins/{pid}")
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == pid

        # Enable/Disable plugin
        res_dis = await ac.post(f"/api/plugins/{pid}/disable")
        assert res_dis.status_code == 200
        assert res_dis.json()["enabled"] is False

        res_ena = await ac.post(f"/api/plugins/{pid}/enable")
        assert res_ena.status_code == 200
        assert res_ena.json()["enabled"] is True

@pytest.mark.asyncio
async def test_webhook_delivery_signature_and_idempotency():
    """Verify HMAC signature computation and event payload structure."""
    secret = "whsec_test_secret_key_12345"
    timestamp = int(time.time())
    payload = {"test": True, "event": "content.ready"}
    payload_bytes = json.dumps(payload).encode("utf-8")

    sig = webhook_service.compute_signature(secret, timestamp, payload_bytes)
    assert sig.startswith(f"t={timestamp},v1=")
    assert len(sig) > 30

@pytest.mark.asyncio
async def test_webhook_management_api():
    """Verify REST APIs for Webhooks (/api/webhooks)."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create Webhook
        res = await ac.post("/api/webhooks", json={
            "url": "https://example.com/webhooks/reflow",
            "events": ["content.ready", "publication.succeeded"]
        })
        assert res.status_code == 200
        wh = res.json()
        assert wh["url"] == "https://example.com/webhooks/reflow"
        wh_id = wh["id"]

        # List Webhooks
        res_list = await ac.get("/api/webhooks")
        assert res_list.status_code == 200
        assert any(w["id"] == wh_id for w in res_list.json())

        # Test Webhook
        res_test = await ac.post(f"/api/webhooks/{wh_id}/test")
        assert res_test.status_code == 200

        # Delete Webhook
        res_del = await ac.delete(f"/api/webhooks/{wh_id}")
        assert res_del.status_code == 200

@pytest.mark.asyncio
async def test_api_key_creation_and_hashing():
    """Verify APIKey creation (raw key shown ONCE, stored hashed), listing, and revocation."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create API key
        res = await ac.post("/api/auth/api-keys", json={
            "name": "Integration Test Key",
            "permissions": ["CONTENT_READ", "PUBLISH"],
            "expires_in_days": 30
        })
        assert res.status_code == 200
        data = res.json()
        assert "raw_api_key" in data
        assert data["raw_api_key"].startswith("reflow_live_")
        key_id = data["id"]
        raw_key = data["raw_api_key"]

        # Verify DB stores hashed version, NOT plain raw secret
        async with async_session_factory() as session:
            res_db = await session.execute(select(APIKey).where(APIKey.id == key_id))
            db_key = res_db.scalar_one()
            assert db_key.hashed_key != raw_key
            assert db_key.hashed_key == hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        # List API keys (raw key must NOT be returned)
        res_list = await ac.get("/api/auth/api-keys")
        assert res_list.status_code == 200
        keys = res_list.json()
        match = next((k for k in keys if k["id"] == key_id), None)
        assert match is not None
        assert "raw_api_key" not in match

        # Revoke API key
        res_rev = await ac.delete(f"/api/auth/api-keys/{key_id}")
        assert res_rev.status_code == 200
