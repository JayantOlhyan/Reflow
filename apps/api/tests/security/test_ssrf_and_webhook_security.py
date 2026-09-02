import pytest
import asyncio
from utils.security import is_safe_external_url

def test_ssrf_rejects_loopback_and_private_ips():
    """Verify SSRF validator blocks localhost, 127.0.0.1, private IPs, and cloud metadata endpoints."""
    bad_urls = [
        "http://127.0.0.1:8000/api/system",
        "http://localhost:6379",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/config",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:8080/debug",
        "file:///etc/passwd"
    ]
    for url in bad_urls:
        is_safe, err = is_safe_external_url(url)
        assert is_safe is False, f"URL '{url}' should have been rejected by SSRF guard."
        assert err is not None

def test_ssrf_allows_valid_public_urls():
    """Verify SSRF validator permits safe public HTTPS URLs."""
    good_urls = [
        "https://api.github.com/webhooks",
        "https://hooks.slack.com/services/T00/B00/X00",
        "https://example.com/callback"
    ]
    for url in good_urls:
        is_safe, err = is_safe_external_url(url)
        assert is_safe is True, f"URL '{url}' should be allowed: {err}"

@pytest.mark.asyncio
async def test_webhook_delivery_blocks_ssrf_target():
    """Verify WebhookService delivers fail status without HTTP request when target URL is SSRF vector."""
    from services.webhook_service import webhook_service
    success = await webhook_service._deliver_payload("ep-test", "http://127.0.0.1:6379", "sig-123", b"{}")
    assert success is False
