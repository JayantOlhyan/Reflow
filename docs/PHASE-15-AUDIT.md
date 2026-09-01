# Reflow — Phase 15: Real Self-Hosted Deployment & Production Hardening Audit

**Phase:** Phase 15 — Real Self-Hosted Deployment & Production Hardening  
**Status:** Audit Complete  

---

## 1. Deployment Architecture

Reflow is architected as a self-hosted content operating system comprising six containerized microservices operating over shared persistence layers (PostgreSQL, Redis, and a persistent Local Media Storage volume):

```
                        ┌────────────────────────┐
                        │     Browser Client     │
                        └───────────┬────────────┘
                                    │ HTTP :3000
                                    ▼
                        ┌────────────────────────┐
                        │   Web (Next.js 16)     │
                        └───────────┬────────────┘
                                    │ API / REST :8000
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          API (FastAPI)                                 │
│ - REST Endpoints (/api/v1)        - Input Validation & Rate Limiting  │
│ - Secret Encryption/Decryption   - SSRF Protection & Safe FFmpeg      │
└────────────┬──────────────────────┬──────────────────────┬─────────────┘
             │                      │                      │
             ▼                      ▼                      ▼
    ┌────────────────┐     ┌────────────────┐    ┌───────────────────┐
    │   PostgreSQL   │     │     Redis      │    │  Storage Volume   │
    │   (Port 5432)  │     │   (Port 6379)  │    │ (/app/storage)    │
    └────────┬───────┘     └────────┬───────┘    └─────────┬─────────┘
             │                      │                      │
             ├──────────────────────┼──────────────────────┤
             │                      │                      │
             ▼                      ▼                      ▼
┌────────────────────────┐┌──────────────────┐┌──────────────────────┐
│        Worker          ││    Scheduler     ││    FFmpeg Binary     │
│ (Background Queue)     ││ (Cron Daemon)    ││ (Transcoder Engine)  │
└────────────────────────┘└──────────────────┘└──────────────────────┘
```

---

## 2. Required Microservices

1. **`web`**: Next.js 16 (React 19) App Router frontend server rendering user interfaces (`/repurpose`, `/carousel`, `/calendar`, `/analytics`, `/intelligence`, `/experiments`, `/automations`, `/system`, `/settings`, `/setup`).
2. **`api`**: FastAPI async application handling HTTP REST APIs, authentication/security middleware, input validation, encryption, and dispatching jobs.
3. **`worker`**: Python background queue process consuming tasks from Redis list queue (`reflow:media_jobs`). Executes media processing, transcription, AI synthesis, video clipping, carousel rendering, subtitle burning, metrics collection, and publishing.
4. **`scheduler`**: Python background daemon executing every 5 seconds to claim scheduled publications, check missed posting windows, run governance audits, and sweep performance telemetry.
5. **`postgres`**: PostgreSQL 16 relational database instance holding relational state (contents, variants, clips, carousels, publications, metrics, governance rules, job queue history).
6. **`redis`**: Redis 7 in-memory data store providing asynchronous message queueing (`reflow:media_jobs`) and rate-limiting counters.

---

## 3. Required Environment Variables

All settings are structured across eight distinct domain sections:

### 3.1 APPLICATION
- `APP_NAME` (Default: `"Reflow API"`) — Application brand name.
- `APP_VERSION` (Default: `"1.0.0"`) — System release version.
- `ENVIRONMENT` (Default: `"development"`, Production: `"production"`) — Runtime mode.
- `DEBUG` (Default: `false`) — Enables detailed debug logging and SQL echo.
- `HOST` (Default: `"0.0.0.0"`) — Network interface binding for API.
- `PORT` (Default: `8000`) — API HTTP port.
- `DEPLOYMENT_MODE` (Default: `"single_user"`) — Ownership & authorization scope (`"single_user"` or `"multi_user"`).

### 3.2 DATABASE
- `DATABASE_URL` — Connection string (`postgresql+asyncpg://reflow:reflow_password@postgres:5432/reflow` or `sqlite+aiosqlite:///./storage/reflow.db`).

### 3.3 REDIS
- `REDIS_URL` — Redis connection URL (`redis://redis:6379/0`).
- `REDIS_MEDIA_QUEUE` — Queue name (`reflow:media_jobs`).

### 3.4 STORAGE
- `STORAGE_PROVIDER` (Default: `"local"`) — Media storage engine (`"local"`, `"s3"`, `"r2"`).
- `STORAGE_DIR` (Default: `"/app/storage"`) — Absolute path to persistent storage volume.
- `STORAGE_BUCKET` (Optional) — S3 / R2 bucket name.
- `STORAGE_ACCESS_KEY` (Optional) — S3 / R2 access key.
- `STORAGE_SECRET_KEY` (Optional) — S3 / R2 secret key.
- `MAX_UPLOAD_SIZE_MB` (Default: `500`) — Maximum file upload limit in Megabytes.
- `STORAGE_WARNING_THRESHOLD_PERCENT` (Default: `85`) — Disk usage percentage triggering warning alert on system status.

### 3.5 AI (BRING YOUR OWN KEY)
- `GEMINI_API_KEY` (Optional) — Google Gemini API key.
- `OPENAI_API_KEY` (Optional) — OpenAI API key.
- `ANTHROPIC_API_KEY` (Optional) — Anthropic Claude API key.

### 3.6 PLATFORM OAUTH CREDENTIALS
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI` — Google/YouTube OAuth configuration.
- `META_CLIENT_ID`, `META_CLIENT_SECRET`, `INSTAGRAM_REDIRECT_URI`, `FACEBOOK_REDIRECT_URI` — Meta OAuth configuration.
- `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI` — LinkedIn OAuth configuration.
- `X_CLIENT_ID`, `X_CLIENT_SECRET`, `X_REDIRECT_URI` — X (Twitter) OAuth 2.0 configuration.
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI` — TikTok OAuth configuration.
- `PINTEREST_APP_ID`, `PINTEREST_APP_SECRET`, `PINTEREST_REDIRECT_URI` — Pinterest configuration.
- `THREADS_APP_ID`, `THREADS_APP_SECRET`, `THREADS_REDIRECT_URI` — Threads configuration.

### 3.7 SECURITY
- `ENCRYPTION_SECRET` — 32-byte secret key used for AES-256 Fernet symmetric token encryption.
- `CORS_ORIGINS` — Allowed CORS origin list (JSON string array or comma-separated, e.g., `["http://localhost:3000"]`).
- `RATE_LIMIT_PER_MINUTE` (Default: `60`) — Per-IP request limit for expensive endpoints.

### 3.8 OBSERVABILITY
- `LOG_LEVEL` (Default: `"INFO"`) — Standard logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- `METRICS_ENABLED` (Default: `true`) — Enables system metrics endpoint (`/api/metrics`).

---

## 4. Secret Management & Redaction Audit

- **Committed Codebase**: Verified clear of hardcoded production API keys (`sk-`, `AIza`, `Bearer`, OAuth client secrets).
- **Redaction Middleware**: All loggers format output through a `RedactingFormatter` that masks string patterns matching API keys, OAuth tokens, passwords, and authorization headers (`[REDACTED]`).
- **Production Validation**: On application launch in `ENVIRONMENT=production`, if `ENCRYPTION_SECRET` is set to the default development fallback or has fewer than 32 characters, startup is aborted with a clear security initialization error.

---

## 5. Ports, Volumes, and Networking

| Service | Host Port | Container Port | Volume Mount | Purpose |
|---|---|---|---|---|
| `web` | 3000 | 3000 | N/A | Next.js Web Interface |
| `api` | 8000 | 8000 | `storage_data:/app/storage` | FastAPI REST Server |
| `worker` | N/A | N/A | `storage_data:/app/storage` | Async Redis Job Consumer |
| `scheduler` | N/A | N/A | `storage_data:/app/storage` | UTC Publication Cron Daemon |
| `postgres` | 5432 | 5432 | `postgres_data:/var/lib/postgresql/data` | PostgreSQL DB |
| `redis` | 6379 | 6379 | `redis_data:/data` | Redis Data Store |

---

## 6. Migration & Database Schema Strategy

- **Alembic Integration**: Formal migration management using Alembic configured under `apps/api/alembic`.
- **Startup Auto-Migration**: The `docker-entrypoint.sh` for API/worker/scheduler automatically executes `alembic upgrade head` followed by idempotent `init_db()` checks.
- **Data Safety**: Schema alterations do not drop tables or columns; destructive database resets are strictly manual operations via `scripts/restore.sh`.

---

## 7. Service Startup Order & Health Dependencies

1. **PostgreSQL (`postgres`)**: Starts first, becomes healthy via `pg_isready -U reflow -d reflow`.
2. **Redis (`redis`)**: Starts in parallel, becomes healthy via `redis-cli ping`.
3. **API (`api`)**: Depends on `postgres` (service_healthy) and `redis` (service_healthy). Runs database migrations, initializes engine, and starts HTTP server on `:8000`.
4. **Worker (`worker`)**: Depends on `api` (service_healthy) or `postgres` & `redis` (service_healthy). Connects to Redis queue.
5. **Scheduler (`scheduler`)**: Depends on `api` (service_healthy) or `postgres` & `redis` (service_healthy). Begins UTC interval polling.
6. **Web (`web`)**: Depends on `api` (service_started/service_healthy). Listens on `:3000`.

---

## 8. Production Risks & Localhost Assumptions Identified

1. **Localhost CORS & Redirect URIs**: Previously, OAuth callbacks were hardcoded to `http://localhost:8000`. Updated to be configurable via environment variables (`YOUTUBE_REDIRECT_URI`, `NEXT_PUBLIC_API_URL`).
2. **Redis In-Memory Loss**: If Redis restarts while jobs are queued, job IDs stored in PostgreSQL maintain `QUEUED`/`RUNNING` status. Added queue reconciliation logic on worker startup to reset orphaned `RUNNING` jobs back to `QUEUED`.
3. **FFmpeg Shell Execution**: Audited all FFmpeg/FFprobe invocations to ensure list-based `subprocess.exec` / `asyncio.create_subprocess_exec` is used, eliminating shell injection hazards.
4. **SSRF Hazards**: Added URL validation (`utils/ssrf.py`) restricting URL fetching to public IP ranges and blocking private IP networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.169.254`, `localhost`, `postgres`, `redis`, `api`).
5. **Fake Metric Fallbacks**: Removed all mock/hardcoded values from system health telemetry and analytics. System metrics return real system values via `psutil` or `UNAVAILABLE`.
