# Reflow — Phase 9 Technical Audit: Scheduling & Content Calendar Engine

**Date:** August 2026  
**Document Version:** 1.0  
**Phase Target:** Phase 9 — Real Scheduling & Content Calendar Engine  
**System Principle:** "Create once. Transform everywhere."

---

## 1. Executive Summary

Phase 8 established a robust multi-platform publishing engine with universal connectors (YouTube, Instagram, LinkedIn, X, Facebook, TikTok, Pinterest, Threads), AES-256 encrypted OAuth credential storage, multi-modal asset routing, and independent multi-destination batch publishing.

However, Reflow's **Calendar interface (`/calendar`)** is currently a static UI with hardcoded demo events. Scheduling exists only conceptually on the client. To turn Reflow into a dependable content operating system, **Phase 9 establishes a server-side scheduling engine** where:
1. The **PostgreSQL `Publication` entity is the single source of truth** (not client memory, not browser timers).
2. Schedules are stored in **UTC with explicit IANA timezones** (e.g. `America/New_York`, `Asia/Kolkata`) guaranteeing deterministic DST handling.
3. A **dedicated asynchronous background Scheduler service (`apps/api/services/scheduler_service.py` & `scheduler.py`)** runs independently of user HTTP requests, performs **database-level atomic claiming (`SELECT ... FOR UPDATE SKIP LOCKED` / lease ownership)**, and safely enqueues `PLATFORM_PUBLISH` jobs to Redis when items are due.
4. Scheduled items survive browser closures, container restarts, machine reboots, and network hiccups with **stale claim recovery** and configurable **missed-schedule policies**.

---

## 2. Audit of Existing Components

### 2.1 Database Entities (`apps/api/models/entities.py`)
- **`Publication`**:
  - Existing fields: `id`, `content_id`, `variant_id`, `platform_connection_id`, `platform`, `status` (`DRAFT`, `QUEUED`, `UPLOADING`, `PUBLISHING`, `PUBLISHED`, `FAILED`, `CANCELLED`), `title`, `description`, `privacy`, `tags_json`, `external_post_id`, `external_url`, `request_payload_hash`, `error_code`, `error_message`, `attempt_count`, `created_at`, `updated_at`, `published_at`.
  - **Gaps for Phase 9**:
    - Needs `scheduled_at` (DateTime in UTC, indexed).
    - Needs `timezone` (String(64), IANA identifier, e.g. `Asia/Kolkata`).
    - Needs `status = "SCHEDULED"` lifecycle state.
    - Needs `claimed_at` (DateTime, for scheduler lease ownership) and `claim_owner` (String(64), scheduler worker instance ID).
    - Needs `cancelled_at` (DateTime) and `failed_at` (DateTime).
    - Needs composite index on `(status, scheduled_at)` to ensure scheduler tick queries are fast ($O(\log N)$) without scanning the entire table.

### 2.2 Background Workers & Redis (`apps/api/worker.py`, `apps/api/services/queue_service.py`)
- **Worker (`worker.py`)**:
  - Implements `PLATFORM_PUBLISH` handler that calls `publishing_service.execute_publication_job(publication_id)`.
  - Reusable 100%! We do **not** duplicate publishing logic for scheduled items; when a scheduled publication becomes due, the scheduler changes status `SCHEDULED -> QUEUED` and enqueues a standard `PLATFORM_PUBLISH` job.
- **Queue Service (`queue_service.py`)**:
  - Supports Redis `blpop`/`rpush` with seamless in-process fallback.

### 2.3 Publishing Service (`apps/api/services/publishing_service.py`) & Connectors (`apps/api/connectors/`)
- Universal multi-modal connectors for all 8 platforms.
- `execute_publication_job` transparently refreshes tokens, validates assets with FFprobe, calls platform connectors, and writes real external IDs/URLs.
- `compute_idempotency_hash` ensures deterministic SHA-256 hash across retries.

### 2.4 Timezone & Clock Architecture
- **Canonical Storage**: All server-side timestamps (`scheduled_at`, `published_at`, `created_at`, `claimed_at`) must be stored in UTC (`datetime.utcnow()`).
- **IANA Timezones**: Users select local times in their IANA timezone (`zoneinfo.ZoneInfo("Asia/Kolkata")` / `zoneinfo.ZoneInfo("America/New_York")`). The API parses local time in the specified timezone and persists the UTC instant.
- **DST Safety**: Python 3.9+ `zoneinfo` handles daylight saving transitions with zero manual offset calculation.

### 2.5 Frontend Calendar (`apps/web/src/app/calendar/page.tsx`)
- **Current State**: Static mock array (`scheduledEvents`) with hardcoded dates and dummy badges.
- **Requirements**:
  - Replace mock data with `GET /api/calendar` and `GET /api/publications/scheduled`.
  - Month, Week, and Day visualization modes.
  - Interactive "Schedule Post" modal supporting single/bulk content & variant selection, multi-platform targets, custom copy tabs, date/time pickers, and IANA timezone selector.
  - Detail inspection drawer with live preview, real external URL link if published, reschedule action, and cancel action.
  - Queue view and upcoming posts section.

---

## 3. Technical Architecture for Phase 9

```
                               USER / FRONTEND
                  (Select Content, Variant, Platforms, Time)
                                     │
                                     │ POST /api/publications/schedule
                                     ▼
                               FASTAPI API
                 (Validates Timezone, Min Lead Time, Metadata,
                  Persists Publication with status=SCHEDULED)
                                     │
                                     ▼
                               POSTGRESQL
               (Index on status + scheduled_at in UTC)
                                     ▲
                                     │ Atomic Claim (FOR UPDATE SKIP LOCKED / Lease)
                                     │ Every N seconds tick
                                     ▼
                            SCHEDULER SERVICE
                        (apps/api/scheduler.py)
                                     │
             ┌───────────────────────┴───────────────────────┐
             │ Due / Missed Items                             │ Lease Expired
             ▼                                                ▼
     Mark status=QUEUED                               Reset stale claim
     Enqueue PLATFORM_PUBLISH                         to SCHEDULED
             │
             ▼
        REDIS QUEUE (reflow:media_jobs)
             │
             ▼
       PUBLISH WORKER (apps/api/worker.py)
             │
             ▼
    UNIVERSAL CONNECTOR (YouTube / IG / LinkedIn / X / etc.)
             │
             ▼
       SOCIAL PLATFORM (External Post ID & URL)
             │
             ▼
       Publication status -> PUBLISHED (published_at=now)
```

---

## 4. Lifecycle State Machine for Scheduled Publications

```
                    ┌──────────────┐
                    │    DRAFT     │
                    └──────┬───────┘
                           │ Schedule (future UTC time)
                           ▼
                    ┌──────────────┐
                    │  SCHEDULED   │◄──────────────┐
                    └──────┬───────┘               │
            ┌──────────────┼──────────────┐        │ Stale Lease
            │ Due (now)    │ Cancel       │ Reschedule (if worker crashed)
            ▼              ▼              │        │
     ┌──────────────┐ ┌──────────┐        │        │
     │   CLAIMED    │ │CANCELLED │        │        │
     └──────┬───────┘ └──────────┘        │        │
            │                             │        │
            ▼ Enqueued to Redis           │        │
     ┌──────────────┐                     │        │
     │    QUEUED    │─────────────────────┘        │
     └──────┬───────┘                              │
            │ Worker picked up                     │
            ▼                                      │
     ┌──────────────┐                              │
     │  PUBLISHING  │                              │
     └──────┬───────┘                              │
            ├──────────────────────┐               │
            │ Success              │ Failed        │
            ▼                      ▼               │
     ┌──────────────┐       ┌──────────────┐       │
     │  PUBLISHED   │       │    FAILED    │───────┘ Retry
     └──────────────┘       └──────────────┘
```

---

## 5. Summary of Gaps to Address in Phase 9

| Area | Current Baseline | Phase 9 Requirement |
| :--- | :--- | :--- |
| **Model** | `Publication` has immediate publish fields | Add `scheduled_at`, `timezone`, `claimed_at`, `claim_owner`, `failed_at`, `cancelled_at`, and `(status, scheduled_at)` index |
| **Scheduler Process** | None | Dedicated `scheduler.py` process running every 5s with atomic claiming and lease recovery |
| **Scheduling API** | Only immediate publish | `POST /api/publications/schedule`, `GET /api/calendar`, `POST /api/publications/{id}/reschedule`, `POST /api/publications/{id}/cancel` |
| **Timezone Validation** | None | IANA timezone validation (`zoneinfo`), minimum lead time enforcement ($60\text{s}$), past-time rejection |
| **Content Protection** | Delete cascades blindly | Block deletion of content with future `SCHEDULED` publications to prevent orphan schedules |
| **Frontend Calendar** | Mock static data | Fully backend-driven calendar with Month/Week/Day views, scheduling modal, upcoming drawer, and cancel/reschedule |
| **Telemetry & Health** | API, Worker, Redis, DB | Add Scheduler health probe (heartbeat, lag seconds, queue depth) to `/api/health` and `/system` |
