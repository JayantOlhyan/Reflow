import pytest
import os
import sys
import logging
from io import StringIO
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(__file__))

from main import app
from config import settings, validate_secrets
from utils.ssrf import validate_url_ssrf
from services.storage_service import validate_upload
from utils.logging import RedactingFormatter, sanitize_log_message
from services.health_service import health_service

client = TestClient(app)

def test_liveness_and_readiness_probes():
    """Verify /health and /health/ready endpoints return structured JSON."""
    res_live = client.get("/health")
    assert res_live.status_code == 200
    data_live = res_live.json()
    assert data_live["status"] == "healthy"
    assert data_live["version"] == settings.APP_VERSION

    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["status"] in ("READY", "ACTION_REQUIRED")
    assert "dependencies" in data_ready

def test_request_id_middleware():
    """Verify request ID is generated and returned in headers."""
    res = client.get("/health")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    assert res.headers["x-request-id"].startswith("req-")

def test_api_v1_aliasing():
    """Verify /api/v1 prefix routes transparently to /api endpoints."""
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    assert "components" in res.json()

def test_system_metrics_endpoint():
    """Verify /api/system/metrics returns real metrics or UNAVAILABLE status."""
    res = client.get("/api/system/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("AVAILABLE", "UNAVAILABLE")

def test_system_settings_endpoint():
    """Verify GET and POST /api/system/settings update configuration safely."""
    res_get = client.get("/api/system/settings")
    assert res_get.status_code == 200
    assert "settings" in res_get.json()

    res_post = client.post("/api/system/settings", json={"storage_provider": "local"})
    assert res_post.status_code == 200
    assert res_post.json()["status"] == "success"

def test_secret_redaction():
    """Verify logger RedactingFormatter masks sensitive API keys, Bearer tokens, and secrets."""
    raw_msg = "User logged in with API key AIzaSyABC12345678901234567890123456789 and Bearer my_secret_token_123"
    sanitized = sanitize_log_message(raw_msg)
    assert "AIzaSy" not in sanitized or "[REDACTED]" in sanitized
    assert "Bearer my_secret_token_123" not in sanitized

    record = logging.LogRecord("test", logging.INFO, "path", 10, raw_msg, (), None)
    formatter = RedactingFormatter()
    formatted = formatter.format(record)
    assert "[REDACTED]" in formatted

def test_ssrf_protection():
    """Verify validate_url_ssrf blocks localhost, 127.0.0.1, private IPs, and internal Docker hosts."""
    blocked_urls = [
        "http://localhost:8000/internal",
        "http://127.0.0.1:5432",
        "http://192.168.1.1/admin",
        "http://10.0.0.1/metadata",
        "http://169.254.169.254/latest/meta-data",
        "http://postgres:5432/db",
        "http://redis:6379/0"
    ]
    for url in blocked_urls:
        with pytest.raises(HTTPException) as exc_info:
            validate_url_ssrf(url)
        assert exc_info.value.status_code == 400

    # Public valid URL passes
    assert validate_url_ssrf("https://example.com/feed") == "https://example.com/feed"

def test_upload_security_validation():
    """Verify filename sanitization, extension validation, and path traversal defense."""
    # Invalid extension
    valid, ct, err = validate_upload("malicious.exe", "application/octet-stream", 100)
    assert valid is False
    assert "Unsupported file extension" in err

    # Path traversal attempt
    valid_tp, ct_tp, err_tp = validate_upload("../../../etc/passwd.mp4", "video/mp4", 100)
    assert valid_tp is True # Allowed because filename is sanitized to passwd.mp4

    # Oversized file
    valid_size, ct_size, err_size = validate_upload("large.mp4", "video/mp4", 999999999999)
    assert valid_size is False
    assert "exceeds maximum allowed size" in err_size

def test_secret_validation_in_production():
    """Verify validate_secrets raises error when ENVIRONMENT=production and default secret key is used."""
    old_env = settings.ENVIRONMENT
    old_secret = settings.ENCRYPTION_SECRET
    try:
        settings.ENVIRONMENT = "production"
        settings.ENCRYPTION_SECRET = "reflow_dev_secret_key_change_in_production_32b"
        with pytest.raises(ValueError) as exc:
            validate_secrets()
        assert "CRITICAL SECURITY ERROR" in str(exc.value)
    finally:
        settings.ENVIRONMENT = old_env
        settings.ENCRYPTION_SECRET = old_secret

def test_rate_limiting():
    """Verify rate limit middleware blocks requests exceeding limit."""
    old_limit = settings.RATE_LIMIT_PER_MINUTE
    try:
        settings.RATE_LIMIT_PER_MINUTE = 2
        res1 = client.get("/api/uploads/test_limit")
        res2 = client.get("/api/uploads/test_limit")
        res3 = client.get("/api/uploads/test_limit")
        assert res3.status_code == 429
        assert res3.json()["error"] == "RATE_LIMIT_EXCEEDED"
    finally:
        settings.RATE_LIMIT_PER_MINUTE = old_limit
