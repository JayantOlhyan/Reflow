# Reflow — Observability & Reliability Architecture

Reflow includes a production-ready observability, correlation tracing, health telemetry, and job reliability engine. Operators can monitor real-time resource utilization, trace operations from API requests down to social platform publishing dispatches, inspect Dead-Letter Queues (DLQ), and manage incident lifecycles without fake telemetry.

---

## 1. Core Principles

- **Zero Fake Telemetry**: All metrics (CPU, RAM, Disk), queue sizes, component health probes, worker heartbeats, and incidents are derived from real execution data and OS system calls (`psutil`, database connectivity, Redis ping).
- **End-to-End Correlation**: Operations propagate correlation identifiers: `request_id`, `job_id`, `content_id`, `publication_id`, `automation_id`, `plugin_id`.
- **Secret Redaction**: Credentials, tokens, API keys, passwords, and private user transcripts are automatically sanitized in log outputs (`utils/logging.py`) and excluded from metric labels.
- **Dead-Letter Queue (DLQ)**: Jobs that fail permanently after reaching `max_retries` are routed to `DeadLetterJob` records for manual operator inspection and 1-click retry.

---

## 2. Structured JSON Logging Model

```json
{
  "timestamp": "2026-09-01T21:45:00Z",
  "level": "INFO",
  "service": "QueueService",
  "event": "JOB_COMPLETED",
  "request_id": "req_a1b2c3d4",
  "job_id": "job_998877",
  "content_id": "cnt_443322",
  "publication_id": "pub_110011",
  "platform": "INSTAGRAM",
  "duration_ms": 1245.5,
  "status": "SUCCEEDED"
}
```

---

## 3. End-to-End Trace Views

Reflow provides 3 correlation trace resolution endpoints:
- `GET /api/system/trace/request/{request_id}`: Resolves the complete chain of API request, background job, and system events.
- `GET /api/system/trace/job/{job_id}`: Resolves job queueing time, execution start, worker retries, DLQ routing, and completion.
- `GET /api/system/trace/content/{content_id}`: Resolves complete lifecycle timeline from raw ingest to AI processing, clip/carousel generation, governance quality checks, multi-platform publishing, and analytics.

---

## 4. Maintenance Mode

Self-hosted operators can enable Maintenance Mode (`POST /api/system/maintenance?enabled=true`). When active:
- Outbound automatic platform publishing and scheduled automation rules are safely paused.
- Ingestion and manual editing remain available.
- The UI displays an operational Maintenance Mode banner across `/system`.
