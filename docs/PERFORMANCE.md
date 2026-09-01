# Reflow Performance Architecture & Guidelines

## 1. Concurrency Model
Reflow uses domain-isolated async worker pools to manage system load:
- **Media Transcoding**: Default `2` concurrent workers (`MEDIA_WORKER_CONCURRENCY=2`), bounded by `-threads 2` FFmpeg flag.
- **AI Operations**: Default `3` concurrent workers (`AI_WORKER_CONCURRENCY=3`), guarded by prompt deduplication.
- **Publishing & OAuth**: Default `5` concurrent workers (`PUBLISH_WORKER_CONCURRENCY=5`).
- **Webhooks**: Default `5` concurrent workers (`WEBHOOK_WORKER_CONCURRENCY=5`).

---

## 2. Priority Queuing
Queue jobs carry priority levels:
- `CRITICAL` / `HIGH`: Inserted at the head of queue (social posts due immediately, webhooks).
- `NORMAL` / `LOW`: Appended to tail of queue (heavy background video transcodes, analytics sweeps).

---

## 3. Backpressure & Queue Saturation
When pending queue depth reaches `MAX_QUEUE_DEPTH` (default: 100), new non-critical job submissions trigger HTTP `429 Too Many Requests` or `503 Service Unavailable` backpressure responses with `Retry-After: 30`.

---

## 4. Hardware Optimization Tuning

### SQLite Optimization:
```env
DATABASE_URL=sqlite+aiosqlite:///./storage/reflow.db
```

### PostgreSQL Connection Pool Tuning (Production):
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/reflow
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```
