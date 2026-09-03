# Reflow Production Troubleshooting Guide

This guide provides symptom-cause-fix steps for common operational issues in production deployments.

---

### 1. PostgreSQL Connection Failure
- **Symptom:** API logs show `asyncpg.exceptions.CannotConnectNowError` or `Connection refused`.
- **Cause:** PostgreSQL container is starting up or database credentials mismatch.
- **Check:** Run `docker compose ps` to verify `reflow_postgres` status.
- **Fix:** Check `DATABASE_URL` in `.env`. Ensure host is set to `postgres` inside Docker container networks.

---

### 2. Redis Task Queue Saturated / Backpressure (HTTP 429)
- **Symptom:** API returns `QUEUE_OVERFLOW` (HTTP 429).
- **Cause:** Pending job count exceeded `MAX_QUEUE_DEPTH` (default 100).
- **Check:** Inspect worker concurrency and active queue depth via `http://localhost:8000/api/system/metrics`.
- **Fix:** Increase `MEDIA_WORKER_CONCURRENCY` in `.env` or scale `worker` containers:
  ```bash
  docker compose up -d --scale worker=3
  ```

---

### 3. FFmpeg Command Timeout / Processing Failed
- **Symptom:** Video variant generation fails with `FFmpeg timeout`.
- **Cause:** Video file is corrupt or duration exceeds system timeout (`FFMPEG_TIMEOUT_SECONDS = 300`).
- **Check:** Inspect media worker logs: `docker compose logs worker`.
- **Fix:** Increase `FFMPEG_TIMEOUT_SECONDS` in `.env` or check source video codec compatibility with `ffprobe`.

---

### 4. Platform Connection Re-Authentication Required
- **Symptom:** Scheduled publication status changes to `REAUTH_REQUIRED`.
- **Cause:** OAuth access token expired and refresh token was revoked by provider.
- **Check:** Navigate to **Connections** (`/connections`) in the Reflow web UI.
- **Fix:** Click **Re-authenticate Account** to acquire fresh OAuth tokens.
