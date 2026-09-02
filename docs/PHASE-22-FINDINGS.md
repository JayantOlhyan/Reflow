# Phase 22 — Bug Triage & Findings Ledger

## Bug Triage Table

| ID | Severity | Scenario | Root Cause | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FIND-22-01** | P0 — Duplicate Publishing | Concurrent scheduler instances claiming due publications | `claim_due_publications` selected candidate IDs and updated them in two un-guarded queries, allowing duplicate claims | IDENTIFIED & READY TO FIX |
| **FIND-22-02** | P1 — Storage Leak | FFmpeg process timeout during video transcode | Exception handler killed process but failed to unlink un-registered intermediate temp file | IDENTIFIED & READY TO FIX |
| **FIND-22-03** | P1 — AI Provider Error | AI API returning HTTP 500 / 503 error | `AIService` did not fallback to deterministic mock provider on 5xx errors | IDENTIFIED & READY TO FIX |
| **FIND-22-04** | P2 — Queue Backpressure | Redis connection drop during heavy load | `get_queue_depth` checked fallback queue length using different lock boundaries | IDENTIFIED & READY TO FIX |
| **FIND-22-05** | P2 — Frontend Polling | Large job list state updates | Fixed 2-second interval polling on `/system` page did not pause on browser tab blur | IDENTIFIED & READY TO FIX |

---

## Detailed Finding Analysis & Fix Specifications

### FIND-22-01: Concurrent Scheduler Claim Race Condition (P0)
- **Severity**: P0 (Duplicate Publishing Hazard)
- **Scenario**: When running multiple Reflow scheduler daemons for high availability, both instances run `claim_due_publications()` simultaneously.
- **Reproduction**: Trigger two concurrent calls to `scheduler_service.claim_due_publications(limit=10)`.
- **Root Cause**: The initial query fetched candidate `id`s using `SELECT`, and a separate `UPDATE` query marked them claimed. Between the `SELECT` and `UPDATE`, both instances selected the same candidate IDs.
- **Fix Specification**: Use atomic conditional update filtering by `claim_owner`:
  ```python
  # Update candidate where claimed_at is NULL or expired
  update(Publication).where(
      Publication.id == pub_id,
      Publication.status == "SCHEDULED",
      or_(Publication.claimed_at == None, Publication.claimed_at < lease_threshold)
  ).values(claimed_at=now_utc, claim_owner=self.instance_id)
  ```
  And verify that only rows where `claim_owner == self.instance_id` after commit are actually returned as claimed!

### FIND-22-02: Temp File Leak on FFmpeg Subprocess Timeout (P1)
- **Severity**: P1 (Storage Leak)
- **Scenario**: Transcoding large or corrupted video assets when FFmpeg times out.
- **Reproduction**: Pass dummy un-endable input stream or zero timeout to `run_ffmpeg_command`.
- **Root Cause**: `TimeoutError` killed the process but left partial 0-byte or incomplete `.mp4` file on disk without cleanup.
- **Fix Specification**: Unlink `output_path` in `except TimeoutError` block inside `media_service.py` and `clip_service.py`.

### FIND-22-03: AI Provider 5xx Exception Propagation (P1)
- **Severity**: P1 (Service Availability)
- **Scenario**: Provider endpoint returns HTTP 500/503 or network failure when `OPENAI_API_KEY` is set.
- **Reproduction**: Mock OpenAI client raising `APIError` 500.
- **Root Cause**: Unhandled exception bubble up instead of falling back to Mock provider.
- **Fix Specification**: Catch 5xx API exceptions in `AIService` and fallback gracefully to `MockAIProvider` when enabled.

### FIND-22-04: Queue Depth Synchronization in Fallback Mode (P2)
- **Severity**: P2 (Metrics Consistency)
- **Scenario**: Fallback queue depth tracking under Redis failure.
- **Fix Specification**: Unify `_fallback_queue_items` counting and depth reporting in `QueueService`.

### FIND-22-05: Frontend Polling Window Visibility Optimization (P2)
- **Severity**: P2 (Performance UX)
- **Scenario**: `/system` page polling when tab is inactive.
- **Fix Specification**: Pause polling interval when `document.visibilityState === 'hidden'`.
