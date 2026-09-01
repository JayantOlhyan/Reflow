import pytest
import os
import json
import uuid
from httpx import AsyncClient, ASGITransport
from main import app
from database import async_session_factory, init_db
from services.ecosystem_service import ecosystem_service
from plugins.loader import register_builtin_plugins

@pytest.mark.asyncio
async def test_registry_validation_and_schema():
    """Verify local static registry catalog schema and parsing."""
    cat = await ecosystem_service.fetch_catalog(force_refresh=True)
    assert "plugins" in cat
    plugins = cat["plugins"]
    assert len(plugins) >= 6
    assert any(p["id"] == "youtube-connector" for p in plugins)

@pytest.mark.asyncio
async def test_permission_consent_and_security_warnings():
    """Verify rejection when permission consent is refused."""
    await init_db()
    async with async_session_factory() as session:
        with pytest.raises(ValueError) as exc_info:
            await ecosystem_service.install_plugin(
                session, plugin_id="youtube-connector", accept_permissions=False
            )
        assert "PERMISSION_CONSENT_REQUIRED" in str(exc_info.value)

@pytest.mark.asyncio
async def test_circular_dependency_rejection():
    """Verify circular dependency detection algorithm (A -> B and B -> A)."""
    mock_catalog_map = {
        "plugin-a": {"id": "plugin-a", "dependencies": ["plugin-b"]},
        "plugin-b": {"id": "plugin-b", "dependencies": ["plugin-a"]}
    }
    has_cycle = ecosystem_service.detect_circular_dependencies("plugin-a", mock_catalog_map)
    assert has_cycle is True

@pytest.mark.asyncio
async def test_plugin_configuration_and_secret_redaction():
    """Verify secret configuration masking in API responses and audit logs."""
    await init_db()
    async with async_session_factory() as session:
        res = await ecosystem_service.configure_plugin(
            session, plugin_id="x-connector", config_dict={"api_key": "secret_live_12345", "client_id": "public_id"}
        )
        assert res["status"] == "success"
        config = res["config"]
        assert config["api_key"] == "********"
        assert config["client_id"] == "public_id"

        logs = await ecosystem_service.get_audit_logs(session, plugin_id="x-connector")
        assert len(logs) >= 1
        assert logs[0]["action"] == "CONFIG_CHANGED"
        assert logs[0]["details"]["config"]["api_key"] == "********"

@pytest.mark.asyncio
async def test_ssrf_protection_for_custom_registries():
    """Verify SSRF protection blocks private, internal, and loopback remote registry URLs."""
    assert ecosystem_service._is_ssrf_safe_url("https://registry.reflow.dev/catalog.json") is True
    assert ecosystem_service._is_ssrf_safe_url("http://169.254.169.254/latest/meta-data") is False
    assert ecosystem_service._is_ssrf_safe_url("http://192.168.1.100/registry.json") is False
    assert ecosystem_service._is_ssrf_safe_url("http://10.0.0.1/registry.json") is False

@pytest.mark.asyncio
async def test_plugin_installation_and_safe_uninstall():
    """Verify complete plugin installation, state persistence, and safe uninstall."""
    await init_db()
    register_builtin_plugins()

    async with async_session_factory() as session:
        # Install
        inst_res = await ecosystem_service.install_plugin(
            session, plugin_id="example-platform-connector", accept_permissions=True
        )
        assert inst_res["status"] == "success"
        assert inst_res["plugin_id"] == "example-platform-connector"

        # Detail check
        detail = await ecosystem_service.get_plugin_detail(session, "example-platform-connector")
        assert detail is not None
        assert detail["is_installed"] is True

        # Safe Uninstall
        uninst_res = await ecosystem_service.uninstall_plugin(session, "example-platform-connector")
        assert uninst_res["status"] == "success"

        # Verify detail reflects uninstalled
        detail_after = await ecosystem_service.get_plugin_detail(session, "example-platform-connector")
        assert detail_after["is_installed"] is False

@pytest.mark.asyncio
async def test_ecosystem_rest_apis():
    """Verify REST API endpoints for Ecosystem (/api/ecosystem/...)."""
    await init_db()
    register_builtin_plugins()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # List Catalog
        res_list = await ac.get("/api/ecosystem/plugins")
        assert res_list.status_code == 200
        data = res_list.json()
        assert "plugins" in data
        assert data["total"] >= 6

        # Get Plugin Detail
        pid = data["plugins"][0]["id"]
        res_detail = await ac.get(f"/api/ecosystem/plugins/{pid}")
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == pid

        # Get Categories
        res_cat = await ac.get("/api/ecosystem/categories")
        assert res_cat.status_code == 200
        assert "categories" in res_cat.json()

        # Get Metrics
        res_met = await ac.get("/api/ecosystem/metrics")
        assert res_met.status_code == 200
        metrics = res_met.json()
        assert "plugin_install_total" in metrics

        # Install via API
        res_inst = await ac.post("/api/plugins/install", json={"plugin_id": pid, "accept_permissions": True})
        assert res_inst.status_code == 200

        # Configure via API
        res_conf = await ac.post(f"/api/plugins/{pid}/configure", json={"config": {"api_key": "my_secret"}})
        assert res_conf.status_code == 200
        assert res_conf.json()["config"]["api_key"] == "********"

        # Audit Log via API
        res_audit = await ac.get(f"/api/plugins/{pid}/audit-log")
        assert res_audit.status_code == 200
        assert len(res_audit.json()) >= 1

        # Uninstall via API
        res_uninst = await ac.post(f"/api/plugins/{pid}/uninstall")
        assert res_uninst.status_code == 200
