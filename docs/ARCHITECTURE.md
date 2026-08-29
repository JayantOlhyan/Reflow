# Reflow — System Architecture

**"Create once. Transform everywhere."**

Reflow is an open-source, self-hosted content operating system for creators and developers. This document describes the system architecture established through Phase 4.

---

## 1. High-Level Architecture Diagram

```
                                 REFLOW
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
           CONTENT                 AI                CAROUSEL
              │                    │                    │
           Original                │                    │
              │                    │                    │
           FFprobe                 │                    │
              │                    │                    │
           FFmpeg                  │                    │
              │                    │                    │
        ┌─────┴─────┐              │                    │
        │           │              │                    │
     Variants     Audio            │                    │
                    │              │                    │
                    ▼              │                    │
               Transcript ─────────┤                    │
                    │              │                    │
                    ▼              │                    │
              ContentBrief ────────┼────────────────────┤
                    │              │                    │
         ┌──────────┼───────────┐  │                    ▼
         ▼          ▼           ▼  │             Carousel Planner
     LinkedIn   Instagram       X  │                    │
         │          │           │  │                    ▼
         └──────────┼───────────┘  │             Structured Slides
                    │              │                    │
                 YouTube           │                    ▼
                    │              │              Design System
                    ▼              ▼                    │
            REPURPOSE STUDIO  AI SERVICE                ▼
                                                     Renderer
                                                        │
                                                        ▼
                                                  PNG / PDF EXPORTS
```

---

## 2. Core Subsystems

### 2.1 Frontend (`apps/web`)
- **Framework**: Next.js 16 (App Router), React 19, TypeScript.
- **Styling & UI**: Tailwind CSS v4, custom dark theme aesthetic (`#0B0D12` background, `#111827` cards, `#1F2937` borders).
- **Carousel Studio (`/carousel`)**: 3-column studio featuring slide thumbnails, live 1080x1080 canvas preview with design template switches (`MINIMAL`, `EDITORIAL`, `BOLD`, `EDUCATIONAL`), real-time auto-saving properties inspector, AI generation modal, and export download modal (PNG / PDF).

### 2.2 Backend API (`apps/api`)
- **Framework**: FastAPI with async route handlers and standard error envelopes.
- **Carousel API**: Full CRUD (`/api/carousels`), slide operations (`/api/carousels/{id}/slides`), slide reordering (`/api/carousels/{id}/slides/reorder`), async AI generation (`/api/carousels/{id}/generate`), and server-side rendering (`/api/carousels/{id}/render`).

### 2.3 Media, AI, & Clip Worker Subsystem (`apps/api/worker.py`)
- **Queue**: Redis list queue (`reflow:media_jobs`) with in-process fallback.
- **Worker Pipeline**:
  - `MEDIA_PROCESSING`: Aspect-ratio transcoding + thumbnails.
  - `TRANSCRIPTION`: Audio extraction + speech-to-text.
  - `CONTENT_ANALYSIS`: Structured `ContentBrief` synthesis.
  - `CONTENT_GENERATION`: Platform copies for LinkedIn, Instagram, X, and YouTube.
  - `CAROUSEL_GENERATION`: AI slide deck planning + server-side rendering.
  - `CAROUSEL_RENDER`: Server-side rasterization of 1080x1080 PNG slides and multi-page PDF compilation.
  - `CLIP_DISCOVERY`: AI transcript boundary snapping, scoring, and candidate moment discovery.
  - `CLIP_RENDER`: Frame-accurate subclip extraction, validation, and multi-ratio variant transcoding.

### 2.4 Intelligent Clip Engine (`apps/api/services/media_service.py` & `ai_service.py`)
- **Moment Discovery**: Boundary snapping to transcript segments ($\pm 3.5\text{s}$), non-maximum overlap suppression (Jaccard IoU $> 0.6$), and 50–100 multi-factor quality scoring.
- **Frame-Accurate Video Extraction**: Standardized FFmpeg sub-clipping (`-avoid_negative_ts make_zero -movflags +faststart`) and FFprobe validation.
- **Aspect-Ratio Variants**: Real video transcoding into `9:16` (1080x1920), `1:1` (1080x1080), `4:5` (1080x1350), and `16:9` (1920x1080) with centered thumbnail frame extraction.
- **Storage**: Organized under `content/{content_id}/clips/{clip_id}/variants/{ratio}.mp4` with secure streaming via `/api/clips/{id}/variant/{var_id}` and `/api/clips/{id}/stream`.

### 2.5 Server-Side Carousel Rendering Engine (`apps/api/services/carousel_renderer.py`)
- **Design System**: 4 deterministic styling themes with controlled typography scale, contrast ratios, and pagination chips.
- **Rasterizer**: Produces high-resolution 1080x1080 PNG slide images and compiles standard multi-page PDF documents.
- **Storage**: Persistent storage under `content/{content_id}/carousels/{carousel_id}/` with secure streaming via `/api/carousels/{id}/export/{export_id}`.

### 2.6 Caption & Subtitle Engine (`apps/api/services/caption_service.py`)
- **Segmentation & Time Shifting**: Aligns transcript segments with clip time ranges $[start\_time, end\_time]$ and partitions long sentences into punchy 1–4 word beats with sub-second timing.
- **Styling Presets**: Four distinct themes (`BOLD_PUNCH`, `CLEAN_SUBTITLE`, `KINETIC_HIGHLIGHT`, `MINIMAL_WHITE`) with word-level highlight tags.
- **Safe-Area Layouts**: Aspect-ratio safe margins (`9:16` at $260–320\text{px}$, `1:1` at $80–90\text{px}$, `4:5` at $110–130\text{px}$, `16:9` at $50–70\text{px}$) to avoid TikTok, Reels, and Shorts UI overlap.
- **Burning Engine & Preservation**: Generates RGBA overlays, burns subtitles via FFmpeg while strictly preserving clean variants, and validates outputs via FFprobe.
- **Exports**: RFC-compliant SubRip (`.srt`) and WebVTT (`.vtt`) streaming and download endpoints.

### 2.7 Multi-Platform Publishing Engine (`apps/api/services/publishing_service.py` & `connectors/`)
- **Credential Encryption**: Server-side symmetric AES-256 / Fernet encryption (`ENCRYPTION_SECRET`) protecting OAuth access and refresh tokens at rest with zero exposure to frontend or logs.
- **Universal Connectors**:
  - **YouTube**: Resumable video uploads (`uploadType=resumable`), privacy controls (`PRIVATE`/`UNLISTED`/`PUBLIC`), channel profile lookup.
  - **Instagram**: 3-stage Graph API Reels container creation, status polling (`FINISHED`), photo & carousel post publishing.
  - **LinkedIn**: 2-stage UGC media upload, text feed posts, and member identity resolution.
  - **X (Twitter)**: API v2 tweet publication, character limit verification ($\le 280$), and media uploads.
  - **Facebook**: Meta Pages API feed and video publishing.
  - **TikTok, Pinterest, Threads**: Declared capabilities and standard publishing contracts.
- **Multi-Modal Routing**: Automatically routes content variants (original video, vertical clip, captioned MP4, slide PNG deck, PDF document, or text copy) to the matching platform connector.
- **Batch Publishing & Failure Isolation**: `POST /api/publications/batch` creates independent `Publication` and `Job` records per destination. Failures on one platform do not affect other platforms.
- **Idempotency Hashing**: Deterministic SHA-256 payload hashing prevents duplicate uploads across retries.

### 2.8 Scheduling & Content Calendar Engine (`apps/api/services/scheduler_service.py` & `scheduler.py`)
- **Single Source of Truth**: The `Publication` database model stores canonical UTC `scheduled_at` timestamps alongside standard IANA timezone identifiers (`zoneinfo.ZoneInfo`).
- **Composite Index**: `Index("ix_publications_status_scheduled_at", "status", "scheduled_at")` optimizes high-frequency scheduler queries without table scanning.
- **Standalone Scheduler Daemon**: Background process (`apps/api/scheduler.py`) running every 5 seconds, independent of HTTP web requests.
- **Atomic Lease Claiming**: Queries due publications (`status == 'SCHEDULED' and scheduled_at <= now_utc()`) and atomically claims ownership (`claimed_at`, `claim_owner`).
- **Crash & Stale Claim Recovery**: Claims older than 120 seconds are automatically reset to `SCHEDULED` for retry without duplicating publish jobs.
- **Missed-Schedule Recovery**: Re-executes or handles publications that came due while the server was offline (`SCHEDULER_MISSED_POLICY="EXECUTE_IMMEDIATELY"`).
- **Worker Queue Reuse**: Dispatches due items by transitioning status to `QUEUED` and enqueueing standard `PLATFORM_PUBLISH` jobs into the Redis queue (`reflow:media_jobs`).
- **Content Deletion Protection**: Content deletion is blocked if future active scheduled posts exist.
- **Calendar API**: Fast range-based queries (`GET /api/calendar`) returning localized datetime strings across Month, Week, and Day views.

### 2.9 Database Layer (`apps/api/database.py`)
- **Engine**: SQLAlchemy Async engine supporting SQLite (development) and PostgreSQL (production).
- **Entities**: `Content`, `Asset`, `ContentVariant`, `Transcript`, `TranscriptSegment`, `ContentBrief`, `GeneratedContent`, `Carousel`, `CarouselSlide`, `SlideElement`, `CarouselExport`, `Clip`, `ClipVariant`, `PlatformConnection`, `Publication`, `Job`, `SystemLog`.
