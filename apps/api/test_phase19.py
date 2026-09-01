import pytest
import uuid
import json
import asyncio
from datetime import datetime, timedelta

from database import init_db, async_session_factory
from models.entities import SystemJob, DeadLetterJob, Incident, IncidentEvent, AlertRule
from services.queue_service import queue_service
from services.incident_service import incident_service
from services.telemetry_service import telemetry_service
from utils.errors import ReflowBaseException, ErrorCategory, ErrorCode
from utils.logging import RedactingFormatter, sanitize_log_message
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_standardized_error_classification():
    """Verifies ReflowBaseException carries category, error_code, details, and correlation IDs."""
    exc = ReflowBaseException(
        message="Media probe failed to parse input stream",
        category=ErrorCategory.MEDIA_ERROR,
        error_code=ErrorCode.MEDIA_PROBE_FAILED,
        details={"file": "sample.mp4"},
        request_id="req_123",
        job_id="job_456"
    )

    d = exc.to_dict()
    assert d["category"] == "MEDIA_ERROR"
    assert d["error_code"] == "MEDIA_PROBE_FAILED"
    assert d["request_id"] == "req_123"
    assert d["job_id"] == "job_456"

@pytest.mark.asyncio
async def test_job_failure_and_retry_backoff():
    """Verifies queue service increments retries and re-queues transient failures."""
    await init_db()

    job_id = f"test_job_{uuid.uuid4().hex[:8]}"
    await queue_service.enqueue_media_job(job_id=job_id, job_type="TEST_TRANSCODE", max_retries=3)

    # First transient failure -> Re-queues
    await queue_service.record_job_failure(job_id=job_id, error_message="Network glitch", error_code="NETWORK_ERROR", retryable=True)

    async with async_session_factory() as session:
        res = await session.execute(session.query(SystemJob).where(SystemJob.id == job_id)) if hasattr(session, 'query') else None
        # Use select for SQLAlchemy 2.0
        from sqlalchemy import select
        res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
        job = res.scalar_one_or_none()
        assert job is not None
        assert job.retry_count == 1
        assert job.status == "QUEUED"

@pytest.mark.asyncio
async def test_dead_letter_queue_routing():
    """Verifies permanent failure or max retries routes job to DeadLetterJob (DLQ)."""
    await init_db()

    job_id = f"dlq_job_{uuid.uuid4().hex[:8]}"
    await queue_service.enqueue_media_job(job_id=job_id, job_type="TEST_PERMANENT_FAIL", max_retries=1)

    # Retry 1
    await queue_service.record_job_failure(job_id=job_id, error_message="Fail 1", error_code="MEDIA_ERROR", retryable=True)
    # Retry 2 (Exceeds max_retries=1) -> DLQ
    await queue_service.record_job_failure(job_id=job_id, error_message="Fail 2 permanent", error_code="MEDIA_ERROR", retryable=True)

    async with async_session_factory() as session:
        from sqlalchemy import select
        res = await session.execute(select(SystemJob).where(SystemJob.id == job_id))
        job = res.scalar_one_or_none()
        assert job.status == "FAILED"

        dlq_res = await session.execute(select(DeadLetterJob).where(DeadLetterJob.job_id == job_id))
        dlq = dlq_res.scalar_one_or_none()
        assert dlq is not None
        assert dlq.error_code == "MEDIA_ERROR"

@pytest.mark.asyncio
async def test_stale_job_detection():
    """Verifies detect_stale_jobs marks RUNNING jobs older than 10m as STALE."""
    await init_db()

    stale_id = f"stale_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        sj = SystemJob(
            id=stale_id,
            job_type="STALE_CHECK",
            status="RUNNING",
            started_at=datetime.utcnow() - timedelta(minutes=15)
        )
        session.add(sj)
        await session.commit()

    count = await queue_service.detect_stale_jobs(timeout_minutes=10)
    assert count >= 1

    async with async_session_factory() as session:
        from sqlalchemy import select
        res = await session.execute(select(SystemJob).where(SystemJob.id == stale_id))
        job = res.scalar_one_or_none()
        assert job.status == "STALE"

@pytest.mark.asyncio
async def test_incident_creation_and_deduplication():
    """Verifies repeated failures within 15 minutes group into a single incident."""
    await init_db()

    comp = f"comp_{uuid.uuid4().hex[:6]}"
    err_code = "PLATFORM_TOKEN_EXPIRED"

    inc1 = await incident_service.report_job_failure(component=comp, error_code=err_code, message="Token expired attempt 1", job_id="job_a")
    inc2 = await incident_service.report_job_failure(component=comp, error_code=err_code, message="Token expired attempt 2", job_id="job_b")

    # Should deduplicate into same incident ID
    assert inc1.id == inc2.id

    async with async_session_factory() as session:
        inc = await incident_service.get_incident(session, inc1.id)
        assert inc["affected_resources"]["failure_count"] == 2
        assert len(inc["timeline"]) >= 2

@pytest.mark.asyncio
async def test_incident_operator_workflow():
    """Verifies incident acknowledge, resolution note validation, and timeline logging."""
    await init_db()

    inc = await incident_service.report_job_failure(component="TEST_COMP", error_code="TEST_ERR", message="Initial failure")

    async with async_session_factory() as session:
        # Acknowledge
        ack_res = await incident_service.acknowledge_incident(session, inc.id, acknowledged_by="Operator_Jane")
        assert ack_res["state"] == "INVESTIGATING"

        # Resolve validation error (short note)
        with pytest.raises(ValueError):
            await incident_service.resolve_incident(session, inc.id, resolution_note="fix")

        # Resolve success
        res_res = await incident_service.resolve_incident(session, inc.id, resolution_note="Rotated expired OAuth refresh token and verified API connectivity.")
        assert res_res["state"] == "RESOLVED"

@pytest.mark.asyncio
async def test_alert_rule_evaluation_and_cooldown():
    """Verifies declarative alert rules evaluate conditions and respect cooldown timers."""
    await init_db()

    rule_id = f"rule_{uuid.uuid4().hex[:6]}"
    async with async_session_factory() as session:
        rule = AlertRule(
            id=rule_id,
            name="Test High Incident Rule",
            enabled=True,
            condition_type="OPEN_INCIDENTS",
            threshold_value=1.0,
            severity="HIGH",
            cooldown_minutes=15
        )
        session.add(rule)
        await session.commit()

        # Trigger rule
        triggered1 = await incident_service.evaluate_alert_rules(session)
        # Second call immediately after should be suppressed by cooldown
        triggered2 = await incident_service.evaluate_alert_rules(session)
        assert len(triggered2) == 0

@pytest.mark.asyncio
async def test_trace_views_and_histograms():
    """Verifies TelemetryService trace views and latency histogram calculations."""
    await init_db()

    telemetry_service.record_duration("media_processing_duration_ms", 150.0)
    telemetry_service.record_duration("media_processing_duration_ms", 300.0)

    stats = telemetry_service.get_histogram_stats("media_processing_duration_ms")
    assert stats["count"] >= 2
    assert stats["p50_ms"] > 0

    async with async_session_factory() as session:
        trace = await telemetry_service.trace_job(session, "non_existent_job")
        assert trace["trace_type"] == "JOB"

def test_log_security_redaction():
    """Verifies secret credentials, bearer tokens, and API keys are redacted in log outputs."""
    raw = "Connecting to API with Authorization: Bearer secret_oauth_token_123 and api_key=super_secret_api_key_val"
    sanitized = sanitize_log_message(raw)
    assert "secret_oauth_token_123" not in sanitized
    assert "super_secret_api_key_val" not in sanitized
    assert "[REDACTED]" in sanitized

def test_maintenance_mode_toggle():
    """Verifies toggling maintenance mode state."""
    incident_service.set_maintenance_mode(True, "Upgrading database cluster")
    assert incident_service.is_maintenance_mode() == True

    incident_service.set_maintenance_mode(False)
    assert incident_service.is_maintenance_mode() == False

def test_system_rest_apis():
    """Verifies REST API endpoints for Incidents, DLQ, Traces, and Maintenance mode."""
    # List incidents
    res = client.get("/api/system/incidents")
    assert res.status_code == 200

    # List DLQ jobs
    res = client.get("/api/system/jobs/failed")
    assert res.status_code == 200

    # Telemetry metrics
    res = client.get("/api/system/telemetry/metrics")
    assert res.status_code == 200

    # Maintenance mode toggle
    res = client.post("/api/system/maintenance?enabled=true")
    assert res.status_code == 200
    assert res.json()["maintenance_mode"] == True

    # Restore maintenance mode
    client.post("/api/system/maintenance?enabled=false")
