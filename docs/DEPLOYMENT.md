# Reflow — Self-Hosted Production Deployment Guide

This guide describes how to deploy, configure, backup, restore, and maintain a production instance of Reflow using Docker Compose or local bare-metal setup.

---

## 1. Quick Start ("Clone → Configure → Run")

Reflow is designed to start with zero manual database creation or npm/pip setup commands.

```bash
# 1. Clone the repository
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow

# 2. Copy the environment configuration template
cp .env.example .env

# 3. Configure production secrets (REQUIRED for production mode)
# Edit ENCRYPTION_SECRET in .env to a custom 32+ character key

# 4. Start all services in detached mode
docker compose up -d
```

Once running, access Reflow at:
- **Web App**: `http://localhost:3000`
- **Setup Checklist**: `http://localhost:3000/setup`
- **API Server & Health**: `http://localhost:8000/health`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`

---

## 2. Docker Architecture & Services

The Docker Compose setup starts 6 containerized microservices:

| Service | Container Name | Description | Port |
|---|---|---|---|
| `web` | `reflow_web` | Next.js 16 App Router UI | `3000` |
| `api` | `reflow_api` | FastAPI REST API Server | `8000` |
| `worker` | `reflow_worker` | Async Redis Media & AI Task Consumer | N/A |
| `scheduler` | `reflow_scheduler` | UTC Publication Cron Daemon | N/A |
| `postgres` | `reflow_postgres` | PostgreSQL 16 Database | `5432` |
| `redis` | `reflow_redis` | Redis 7 Queue & Cache | `6379` |

---

## 5. Performance & Resource Tuning

Reflow provides environment variables to tune worker concurrency and database connection pools for your target hardware node:

```env
# Concurrency & Queue Limits
MEDIA_WORKER_CONCURRENCY=2
AI_WORKER_CONCURRENCY=3
PUBLISH_WORKER_CONCURRENCY=5
WEBHOOK_WORKER_CONCURRENCY=5
MAX_QUEUE_DEPTH=100

# Storage & Quotas
MAX_STORAGE_GB=50.0
TEMP_STORAGE_LIMIT_GB=10.0

# Database Async Connection Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```
For detailed hardware profiles and capacity guidelines, review [`docs/CAPACITY.md`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/CAPACITY.md) and [`docs/PERFORMANCE.md`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/PERFORMANCE.md).

---

## 3. Database Migrations

Reflow manages schema migrations using **Alembic**.

When starting via Docker Compose, container entrypoint scripts automatically execute:
```bash
alembic upgrade head
```
prior to starting API server, worker, or scheduler daemons.

### Manual Migration Commands (Development / Maintenance)

To run migrations manually:
```bash
cd apps/api

# Apply latest migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Generate a new migration revision
alembic revision -m "add_custom_table"
```

---

## 4. Backup & Restore Procedures

Reflow includes non-destructive automated backup and restore scripts under `scripts/`.

### 4.1 Database & Media Backup

To create a timestamped PostgreSQL database dump and storage tarball:
```bash
./scripts/backup.sh
```
Archives are saved in `./storage/backups/`:
- `reflow_db_YYYYMMDD_HHMMSS.sql`
- `reflow_media_YYYYMMDD_HHMMSS.tar.gz`

### 4.2 Database & Media Restore

> [!CAUTION]
> Restore operations overwrite current data in the PostgreSQL database.

```bash
# Execute restore with target backup files
./scripts/restore.sh ./storage/backups/reflow_db_20260901_120000.sql ./storage/backups/reflow_media_20260901_120000.tar.gz
```

### 4.3 Safe Cleanup

To remove temporary FFmpeg transcode chunks and health check artifacts without affecting active user media:
```bash
./scripts/cleanup.sh
```

---

## 5. Troubleshooting & Health Verification

1. **First-Run Verification**: Visit `http://localhost:3000/setup` to review system readiness.
2. **Health Endpoints**:
   - `GET /health` (Lightweight liveness probe)
   - `GET /health/ready` (Dependency readiness check)
   - `GET /api/system/metrics` (Real CPU, RAM, and Disk metrics)
3. **Inspect Logs**:
   ```bash
   docker compose logs -f api
   docker compose logs -f worker
   docker compose logs -f scheduler
   ```
