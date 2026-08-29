# Reflow — Phase 2 Architecture & Codebase Audit

**Date:** 2026-08-29  
**Status:** Completed  
**Objective:** Audit existing media handling, database models, storage layout, Redis queue infrastructure, and worker readiness prior to implementing the real media processing engine.

---

## 1. Current State of Media Handling

| Component | Current Implementation | Phase 2 Goal |
| :--- | :--- | :--- |
| **Video Ingestion** | Uploads raw file synchronously to `content/{content_id}/original/{asset_id}.mp4` | Ingest original, create Content (status: `PROCESSING`), create Asset, create Job, enqueue to Redis worker, and return immediately. |
| **FFprobe Metadata** | Basic test probe returning fallback dictionary | Real async subprocess extracting `width`, `height`, `duration`, `fps`, `codecs`, `bitrate`, updating `Asset` and `Content` records. |
| **FFmpeg Transcoding** | Synchronous helper in `services/media_service.py` with hardcoded `./storage/processed` paths | Isolated background worker execution producing validated variants with `libx264` + `aac` + `yuv420p` encoding at target aspect ratios (16:9, 9:16, 1:1, 4:5) and a real thumbnail. |
| **Variant Persistence** | Basic table placeholder in `models/entities.py` | Full `ContentVariant` entity with structured fields (`variant_type`, `storage_key`, `mime_type`, `file_size`, `width`, `height`, `duration`, `status`). |
| **Background Processing** | In-memory synchronous prototype | Dedicated background worker (`apps/api/worker.py`) driven by Redis Queue (`reflow:media_jobs`). |

---

## 2. Existing Schema & Model Audit

- **`Content`**: Contains `id`, `title`, `content_type` (`VIDEO`, `IMAGE`, `PDF`, `TEXT`), `status` (`UPLOADING`, `READY`, `FAILED`, `PROCESSING`), `created_at`, `updated_at`.
- **`Asset`**: Contains `id`, `content_id`, `original_filename`, `storage_key`, `mime_type`, `file_size`, `duration`, `width`, `height`.
- **`ContentVariant`**: Needs extension to track `source_asset_id`, `variant_type` (`THUMBNAIL`, `LANDSCAPE_16_9`, `VERTICAL_9_16`, `SQUARE_1_1`, `PORTRAIT_4_5`), `storage_key`, `mime_type`, `file_size`, `width`, `height`, `duration`, and `status`.
- **`Job`**: Needs `content_id`, `asset_id`, `started_at`, `completed_at`, and `max_attempts` fields for tracking background media jobs.

---

## 3. Storage Layout & Path Strategy

Original files are strictly preserved:
```
storage/
└── content/
    └── {content_id}/
        ├── original/
        │   └── {asset_id}.mp4
        └── variants/
            ├── thumb_{variant_id}.jpg
            ├── 16x9_{variant_id}.mp4
            ├── 9x16_{variant_id}.mp4
            ├── 1x1_{variant_id}.mp4
            └── 4x5_{variant_id}.mp4
```
All generated variants are initially written to temporary files, validated for zero corruption, and atomically finalized to their permanent storage keys.

---

## 4. Redis & Worker Architecture

```
FastAPI (POST /api/content/upload)
   │ (1. Save Original, 2. Create Job in DB)
   ▼
Redis List Queue (`reflow:media_jobs`)
   │
   ▼
Media Worker (`apps/api/worker.py`)
   ├── 1. Read job & mark RUNNING in DB
   ├── 2. Probe original with FFprobe
   ├── 3. Generate thumbnail (00:00:01)
   ├── 4. Generate 9:16 vertical variant (1080x1920)
   ├── 5. Generate 1:1 square variant (1080x1080)
   ├── 6. Generate 4:5 portrait variant (1080x1350)
   ├── 7. Validate each output with FFprobe
   ├── 8. Atomic save to storage & persist ContentVariant in DB
   └── 9. Mark Job SUCCEEDED & Content READY
```

---

## 5. Security & Stability Controls

1. **Subprocess Safety**: All `ffmpeg` and `ffprobe` executions use tokenized argument lists (`asyncio.create_subprocess_exec`) without shell interpolation (`shell=False`).
2. **Original Immutability**: The original user video is read-only and never overwritten or moved.
3. **Idempotency**: Before processing, the worker checks if valid `READY` variants exist to avoid redundant duplicate transcoding.
4. **Cascade Deletion**: Deleting content cleans up all physical files (`original/`, `variants/`, and thumbnails) and database records.
