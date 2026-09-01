# Phase 19 Audit — Real Observability, Reliability & Incident Engine

## 1. Executive Summary

Reflow has robust underlying engines for video processing, AI intelligence, multi-platform publishing, scheduling, governance, and extensibility. However, it lacks a unified, structured observability framework to answer critical operational questions during production incidents:
- *What failed? Why did it fail? Which component, content item, publication, or platform was affected? Did the system retry? How long did it take? What should the operator do to recover?*

This audit identifies gaps in telemetry, logging consistency, correlation tracking, failure classification, job state management, dead-letter queuing, incident management, and health telemetry, establishing the blueprint for Phase 19.

---

## 2. Identified Observability & Reliability Gaps

### 2.1 Missing & Inconsistent Correlation IDs
- **Current State**: Request ID middleware exists (`X-Request-ID`), but background jobs, scheduler claims, automation triggers, webhooks, and AI invocations do not consistently propagate `request_id`, `job_id`, `content_id`, `publication_id`, `automation_id`, and `plugin_id`.
- **Impact**: Operators cannot trace an end-to-end lifecycle from initial API upload to final social platform publication or webhook dispatch.

### 2.2 Unclassified Failures & Unstandardized Error Codes
- **Current State**: Errors are caught as generic `Exception` or `ValueError` strings.
- **Impact**: No standardized error classification categories (`VALIDATION_ERROR`, `NETWORK_ERROR`, `TIMEOUT_ERROR`, `AI_ERROR`, `PLATFORM_ERROR`, `PLUGIN_ERROR`, `GOVERNANCE_ERROR`, `STORAGE_ERROR`, etc.) or specific error codes (`MEDIA_PROBE_FAILED`, `PLATFORM_TOKEN_EXPIRED`, `AI_TIMEOUT`, `STORAGE_WRITE_FAILED`).

### 2.3 Job State Machine Ambiguity & Stuck Jobs
- **Current State**: In-process fallback queues and Redis queue jobs do not maintain persistent state transitions (`QUEUED` → `RUNNING` → `SUCCEEDED` / `FAILED` / `STALE`).
- **Impact**: Long-running jobs that stall or crash leave no trace, becoming orphan jobs without explicit timeout marking (`STALE`) or Dead-Letter Queueing (`DeadLetterJob`).

### 2.4 Missing Incident Management & Deduplication
- **Current State**: Repeated job failures, component health drops, or platform rate limits raise warnings in stdout logs but do not create persistent, grouped `Incident` entities (`OPEN`, `INVESTIGATING`, `MITIGATED`, `RESOLVED`, `CLOSED`) with severity levels (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Impact**: Operators receive no grouped incident notifications or audit timelines, leading to alert fatigue or missed outages.

### 2.5 Health Check Isolation & Dependency Distinction
- **Current State**: Health check `/health` returns `healthy` or `degraded`, but doesn't distinguish external dependency outages (e.g. Instagram API down) from internal Reflow component failures (PostgreSQL down).
- **Impact**: External platform issues could wrongly indicate core Reflow failure. Worker and Scheduler heartbeats are missing.

### 2.6 Metrics Telemetry & Cardinality Safety
- **Current State**: Ad-hoc counter dictionaries exist in some services, but structured Prometheus-style histogram distributions (`api_request_duration`, `job_duration`, `media_processing_duration`) and system resource thresholds (`CPU`, `Memory`, `Disk`) with alert rules are missing.

---

## 3. Targeted Phase 18 -> Phase 19 Architecture

```
                                  OPERATION / REQUEST
                                           │
                                  ┌────────▼────────┐
                                  │   Request ID    │
                                  └────────┬────────┘
                                           │
                                  ┌────────▼────────┐
                                  │ Correlation IDs │
                        (job_id, content_id, publication_id, etc.)
                                  └────────┬────────┘
                                           │
       ┌───────────────────┬───────────────┼───────────────┬───────────────────┐
       │                   │               │               │                   │
┌──────▼──────┐     ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐     ┌──────▼──────┐
│  Structured │     │   Metrics   │ │ Job State   │ │  Incident   │     │ Dead-Letter │
│ JSON Logger │     │ Telemetry   │ │ Machine     │ │ Engine      │     │ Queue (DLQ) │
└─────────────┘     └─────────────┘ └─────────────┘ └─────────────┘     └─────────────┘
```

1. **Structured Log Model (`utils/logging.py`)**: Standardized JSON fields (`timestamp`, `level`, `service`, `event`, `request_id`, `job_id`, `content_id`, `publication_id`, `platform`, `plugin_id`, `duration_ms`, `error_code`).
2. **Standardized Error Categories & Error Codes**: `ErrorCategory` enum and specific `ErrorCode` identifiers with secret redaction.
3. **Persistent Job State Machine & DLQ (`models/entities.py`, `services/queue_service.py`)**: `SystemJob` & `DeadLetterJob` tracking states (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `STALE`) with exponential backoff retries and stuck job recovery daemon.
4. **Incident Engine (`services/incident_service.py`)**: Automatic incident creation from repeated failures, incident grouping/deduplication, severity levels, timeline tracking, and operator resolution notes.
5. **Worker & Scheduler Heartbeats**: Heartbeat telemetry tracking worker/scheduler liveness (`UNHEALTHY` if heartbeat > 30s stale).
6. **System Telemetry & Alerts**: Declarative `AlertRule` engine with cooldown deduplication and System Dashboard UI (`/system` & `/system/incidents`).
7. **Trace Views**: Full request/job/content end-to-end trace endpoints (`GET /api/system/trace/request/{id}`, `GET /api/system/trace/job/{id}`, `GET /api/system/trace/content/{id}`).
8. **Maintenance Mode**: Operational toggle (`PAUSED_PUBLISHING`) for self-hosted operators.
