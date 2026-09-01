# Phase 21 — Real Performance, Scalability & Resource Management Audit

## Executive Summary
This architectural audit inspects Reflow's resource consumption, query performance, concurrency limits, queue depth, media processing overhead, AI request patterns, temporary storage management, and frontend polling behaviors on self-hosted hardware setups.

---

## 1. Identified Performance & Resource Bottlenecks

### A. Database Queries & Connection Pressure
1. **N+1 Query Hazards**:
   - `GET /api/content` and `GET /api/v1/content`: When rendering lists of content, assets, clips, variants, and briefs were loaded lazily in loops unless explicitly joined, leading to multiple round-trip queries per listed item.
   - `GET /api/publications`: Publication details fetching platform connections and associated content individually.
2. **Missing Database Indexes**:
   - `contents` table lacked compound index on `(content_type, status, created_at)`.
   - `system_jobs` table lacked compound index on `(status, job_type, queued_at)`.
   - `publications` table lacked index on `(platform, status, scheduled_at)`.
   - `idempotency_records` table lacked index on `expires_at` for background cleanup sweeps.
3. **Hardcoded DB Pool Configuration**:
   - `database.py` initialized `create_async_engine` with default connection pool settings without explicit `pool_size`, `max_overflow`, `pool_timeout`, and `pool_recycle` overrides from `Settings`.

### B. Worker Concurrency & Queue Management
1. **Unbounded Queue Depth**:
   - `QueueService.enqueue_media_job()` accepted jobs infinitely into Redis / fallback queues without checking maximum queue depth bounds.
2. **Missing Priority Queuing**:
   - Single FIFO queue structure where heavy media jobs (e.g., 500MB video transcoding) blocked lightweight time-sensitive jobs (e.g., immediate social publication dispatch, webhook signature deliveries).
3. **No Backpressure Signal**:
   - Saturated workers or full queues resulted in silent queuing or timeouts rather than immediate `429 Too Many Requests` or `503 Service Unavailable` responses to API callers.

### C. Media Engine & FFmpeg Resource Exhaustion
1. **Unlimited Thread Spawning**:
   - `FFmpeg` invocations in `services/media_engine.py` and `services/clip_engine.py` did not restrict thread counts (`-threads 2`), permitting a single render process to consume 100% of host CPU cores.
2. **Missing FFmpeg Process Timeouts**:
   - Long-running or corrupted media files could hang `FFmpeg` sub-processes indefinitely, holding worker slots and process locks.
3. **Unmanaged Temporary Storage & Leaks**:
   - Transcoded clips, thumbnail frames, and intermediate carousel slide renders were saved to ad-hoc temporary paths without ownership metadata, `created_at` timestamps, or expiration policies.
4. **Lack of Disk Capacity Checks**:
   - Expensive media processing jobs executed regardless of available free disk space, leading to out-of-disk crashes during large video renders.

### D. AI Engine & Provider Quota Protection
1. **Duplicate AI Generation**:
   - Identical prompts for copy generation or clip discovery on the same source text triggered redundant external AI API requests.
2. **Lack of Installation-Scoped Caching**:
   - Safe, deterministic AI responses lacked a local cache layer to reduce latency and API billable costs.
3. **Missing Unhandled AI Rate-Limit Backoff**:
   - AI rate limits (`429` from OpenAI/Gemini/Anthropic) were caught as generic errors rather than triggering structured backoff retries.

### E. Frontend Polling & Response Payload Size
1. **Static Polling Interval**:
   - Web frontend polled `GET /api/jobs/{id}` at fixed 2-second intervals indefinitely, generating unnecessary API traffic even for long-running multi-minute renders.
2. **Failure to Stop Polling**:
   - Certain job components continued polling even after receiving terminal job states (`SUCCEEDED`, `FAILED`, `STALE`).

---

## 2. Resource Management Target Model

| Resource Domain | Metric | Target Limit / Control Strategy |
| :--- | :--- | :--- |
| **CPU / Worker Slots** | Concurrent FFmpeg & Worker Tasks | Configurable `MEDIA_WORKER_CONCURRENCY` (Default: 2) |
| **Queue Capacity** | Max Pending Jobs in Redis / Fallback | Configurable `MAX_QUEUE_DEPTH` (Default: 100), 429 Backpressure |
| **Disk Space** | Free Disk Threshold | Configurable `TEMP_STORAGE_LIMIT_GB` (Default: 10GB), Pre-Job Checks |
| **DB Connections** | Active Async Engine Connections | Configurable `DB_POOL_SIZE` (20), `DB_MAX_OVERFLOW` (10) |
| **AI Provider Quota** | AI API Requests / Minute | Deterministic Cache + Rate Limit Retry-After Backoff |
| **Temporary Files** | Expiration Sweep | Scheduled Auto-Cleanup of Expired Files in `storage/tmp/` |
