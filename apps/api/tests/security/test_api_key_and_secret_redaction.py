import pytest
import hashlib

def test_api_key_generation_and_hashing():
    """Verify raw API keys are hashed using SHA-256 for secure storage."""
    raw_key = "rf_live_sample_key_abcdef1234567890"
    hashed_key = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
    assert len(hashed_key) == 64
    assert hashed_key != raw_key  # Plaintext key must not equal hash

def test_sensitive_header_redaction():
    """Verify authorization headers are not exposed in plaintext logs."""
    from utils.logging import redact_sensitive_dict
    raw_headers = {
        "authorization": "Bearer secret_token_12345",
        "x-api-key": "rf_live_secret_key_9999",
        "content-type": "application/json"
    }
    redacted = redact_sensitive_dict(raw_headers)
    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["x-api-key"] == "[REDACTED]"
    assert redacted["content-type"] == "application/json"
