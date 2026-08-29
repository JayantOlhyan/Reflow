# Reflow — Phase 9 Implementation Results

**Phase:** Phase 9 — Real Scheduling & Content Calendar Engine  
**Status:** Completed & Fully Verified  
**Date:** August 2026  

---

## 1. Overview & Core Objective

Phase 9 transforms Reflow's calendar from a static visual mockup into a **server-side scheduling engine**. The system enables creators to select content variants, choose multiple target social destinations (YouTube, Instagram, LinkedIn, X, Facebook, TikTok, Pinterest, Threads), customize platform-specific copy, pick target dates and times in their IANA timezone, and persist durable schedules in PostgreSQL that dispatch automatically via Redis workers.

```
                              CALENDAR / REPURPOSE STUDIO
                          (Select Content, Variant, Platforms, Time)
                                             │
                                             │ POST /api/publications/schedule
                                             ▼
                                     FASTAPI BACKEND
                     (Validates IANA Timezone, Min Lead Time >= 60s,
                      Persists Publication with status=SCHEDULED in UTC)
                                             │
                                             ▼
                                     POSTGRESQL
                       (Index on status + scheduled_at in UTC)
                                             ▲
                                             │ Atomic Query & Lease Claiming
                                             │ (Every SCHEDULER_POLL_INTERVAL_SECONDS)
                                             ▼
                                     SCHEDULER DAEMON
                                  (apps/api/scheduler.py)
                                             │
                     ┌───────────────────────┴───────────────────────┐
                     │ Due / Missed Items                             │ Stale Lease (> 120s)
                     ▼                                                ▼
             Mark status=QUEUED                               Reset stale claim
             Create PLATFORM_PUBLISH Job                      back to SCHEDULED
                     │
                     ▼
                REDIS QUEUE (reflow:media_jobs)
                     │
                     ▼
               PUBLISHING WORKER (apps/api/worker.py)
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

## 2. Key Accomplishments

### 2.1 Database Scheduling & Lease Model (`apps/api/models/entities.py`, `database.py`)
- **Single Source of Truth**: The `Publication` entity now natively manages the entire scheduling lifecycle:
  - `scheduled_at`: Canonical naive UTC timestamp, indexed.
  - `timezone`: Canonical IANA timezone identifier (e.g. `America/New_York`, `Asia/Kolkata`).
  - `claimed_at`: UTC timestamp when scheduler acquired lease.
  - `claim_owner`: Scheduler daemon instance ID holding claim.
  - `cancelled_at` & `failed_at`: Explicit terminal lifecycle timestamps.
- **Composite Query Index**: Added `Index("ix_publications_status_scheduled_at", "status", "scheduled_at")` ensuring $O(\log N)$ fast indexing on scheduler ticks without full-table scans.

### 2.2 Timezone & Daylight Saving Time (DST) Handling
- **Canonical Storage**: All dates and times are validated and stored in UTC.
- **IANA Timezones**: Users select local times in standard IANA identifiers (`zoneinfo.ZoneInfo`).
- **Deterministic DST**: Correctly resolves UTC hours across DST shifts (e.g. `America/New_York` Summer EDT UTC-4 vs. Winter EST UTC-5) and non-DST regions (`Asia/Kolkata` UTC+5:30).
- **Validation**: Rejects invalid timezones (`"IST"`, `"GMT+5:30"`) and past times (`SCHEDULE_TIME_IN_PAST`), while enforcing a configurable minimum scheduling lead time (`SCHEDULER_MIN_LEAD_SECONDS=60`).

### 2.3 Background Scheduler Daemon (`apps/api/scheduler.py` & `scheduler_service.py`)
- **Independent Execution**: Runs as an independent background daemon outside the API request lifecycle (configured as `scheduler` service in `docker-compose.yml`).
- **Atomic Claiming**: Periodically finds due publications (`status == 'SCHEDULED' and scheduled_at <= now()`) and acquires a lease claim (`claimed_at`, `claim_owner`).
- **Crash & Stale Claim Recovery**: Periodically inspects publications with claims older than `SCHEDULER_CLAIM_LEASE_SECONDS=120` without completed queueing and resets them back to eligible `SCHEDULED` state.
- **Missed-Schedule Handling**: Automatically recovers and dispatches publications that became due while the server was offline (`SCHEDULER_MISSED_POLICY="EXECUTE_IMMEDIATELY"`).
- **Worker Reuse**: Reuses the production Phase 7/8 `PLATFORM_PUBLISH` worker and Redis queue (`reflow:media_jobs`).

### 2.4 Scheduling & Calendar REST API (`apps/api/main.py`)
- `POST /api/publications/schedule`: Multi-destination schedule creation with independent publication records.
- `GET /api/publications/scheduled`: Lists upcoming scheduled and queued publications.
- `GET /api/calendar`: Range-based query $[start, end]$ with viewer timezone conversion and platform/status filters.
- `POST /api/publications/{id}/reschedule`: Reschedules pending `SCHEDULED` publication to a new target time.
- `POST /api/publications/{id}/cancel`: Atomically cancels pending publication (`status="CANCELLED"`).
- `DELETE /api/content/{id}`: Protected to block deletion if active future scheduled publications exist.
- `GET /api/health`: Includes Scheduler engine status, instance ID, and lag metrics.

### 2.5 Frontend Calendar & System Views (`apps/web`)
- **Interactive Calendar (`/calendar`)**:
  - Month, Week, and Day views displaying live backend events.
  - Timezone selector with real-time conversion.
  - "Schedule Post" modal with content/variant picker, multi-platform selector, per-platform copy tabs, and date/time pickers.
  - Event detail inspection drawer with live preview, external URL links, reschedule time picker, and cancellation.
  - Upcoming posts sidebar queue.
- **System Telemetry (`/system`)**:
  - Scheduler Engine component card displaying status (`HEALTHY`/`IDLE`), instance ID, lag seconds, and worker queue status.

---

## 3. Automated Test Suite Results

Full backend test discovery across all phases (Phases 0 through 9):
```bash
apps/api/venv/bin/python3 -m unittest discover -s apps/api -p "test_*.py" -v
```

**Results:**
- `test_api.py`: 10/10 PASSED
- `test_media_engine.py`: 6/6 PASSED
- `test_ai_engine.py`: 5/5 PASSED
- `test_carousel_engine.py`: 5/5 PASSED
- `test_clip_engine.py`: 4/4 PASSED
- `test_caption_engine.py`: 4/4 PASSED
- `test_publishing_engine.py`: 6/6 PASSED
- `test_multi_platform_publishing.py`: 5/5 PASSED
- `test_scheduling_engine.py`: 9/9 PASSED
  - `test_01_timezone_and_utc_conversion`: PASSED
  - `test_02_past_time_and_minimum_lead_time_enforcement`: PASSED
  - `test_03_multi_platform_batch_scheduling`: PASSED
  - `test_04_scheduler_atomic_claiming_and_dispatch`: PASSED
  - `test_05_crash_and_stale_claim_recovery`: PASSED
  - `test_06_reschedule_and_cancel_lifecycle`: PASSED
  - `test_07_calendar_events_query`: PASSED
  - `test_08_content_deletion_protection_for_scheduled_content`: PASSED
  - `test_09_missed_schedule_handling`: PASSED

**Total: 54 tests passing with 0 failures and 0 errors.**

### Frontend Build Verification
- `npx next build --webpack` in `apps/web`:
  - Compiled successfully with 0 TypeScript and 0 lint errors across all 13 routes.
