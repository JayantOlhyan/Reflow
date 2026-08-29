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

### 2.3 Media & AI Worker Subsystem (`apps/api/worker.py`)
- **Queue**: Redis list queue (`reflow:media_jobs`) with in-process fallback.
- **Worker Pipeline**:
  - `MEDIA_PROCESSING`: Aspect-ratio transcoding + thumbnails.
  - `TRANSCRIPTION`: Audio extraction + speech-to-text.
  - `CONTENT_ANALYSIS`: Structured `ContentBrief` synthesis.
  - `CONTENT_GENERATION`: Platform copies for LinkedIn, Instagram, X, and YouTube.
  - `CAROUSEL_GENERATION`: AI slide deck planning + server-side rendering.
  - `CAROUSEL_RENDER`: Server-side rasterization of 1080x1080 PNG slides and multi-page PDF compilation.

### 2.4 Server-Side Carousel Rendering Engine (`apps/api/services/carousel_renderer.py`)
- **Design System**: 4 deterministic styling themes with controlled typography scale, contrast ratios, and pagination chips.
- **Rasterizer**: Produces high-resolution 1080x1080 PNG slide images and compiles standard multi-page PDF documents.
- **Storage**: Persistent storage under `content/{content_id}/carousels/{carousel_id}/` with secure streaming via `/api/carousels/{id}/export/{export_id}`.

### 2.5 Database Layer (`apps/api/database.py`)
- **Engine**: SQLAlchemy Async engine supporting SQLite (development) and PostgreSQL (production).
- **Entities**: `Content`, `Asset`, `ContentVariant`, `Transcript`, `TranscriptSegment`, `ContentBrief`, `GeneratedContent`, `Carousel`, `CarouselSlide`, `SlideElement`, `CarouselExport`, `Job`, `SystemLog`.
