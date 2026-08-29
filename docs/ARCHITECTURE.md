# Reflow — System Architecture

**"Create once. Transform everywhere."**

Reflow is an open-source, self-hosted content operating system for creators and developers. This document describes the system architecture established through Phase 3.

---

## 1. High-Level Architecture Diagram

```
                         REFLOW
                            │
                   ┌────────┴────────┐
                   │                 │
                CONTENT             AI
                   │                 │
                Original             │
                   │                 │
                FFprobe              │
                   │                 │
                FFmpeg               │
                   │                 │
             ┌─────┴─────┐           │
             │           │           │
          Variants     Audio         │
                         │           │
                         ▼           │
                    Transcript ──────┤
                         │           │
                         ▼           │
                   ContentBrief ─────┤
                         │           │
              ┌──────────┼───────────┤
              ▼          ▼           ▼
          LinkedIn   Instagram       X
              │          │           │
              └──────────┼───────────┘
                         │
                      YouTube
                         │
                         ▼
                 REPURPOSE STUDIO
```

---

## 2. Core Subsystems

### 2.1 Frontend (`apps/web`)
- **Framework**: Next.js 16 (App Router), React 19, TypeScript.
- **Styling & UI**: Tailwind CSS v4, custom dark theme aesthetic (`#0B0D12` background, `#111827` cards, `#1F2937` borders).
- **Repurpose Studio**: Interactive multi-platform studio showing real video variant streaming, collapsible timestamped transcripts, `ContentBrief` takeaways, and native platform outputs for LinkedIn, Instagram, X (with thread cards and character validation), and YouTube (with real timestamped chapters).

### 2.2 Backend API (`apps/api`)
- **Framework**: FastAPI with async route handlers and standard error envelopes.
- **Configuration**: Pydantic `BaseSettings` (`config.py`) loading from environment variables and `.env`.
- **Logging**: Structured JSON/formatted logging utility (`apps/api/utils/logging.py`) with secret redaction.

### 2.3 Media Engine & Worker Subsystem (`apps/api/services/media_service.py` & `apps/api/worker.py`)
- **Queue**: Redis list queue (`reflow:media_jobs`) with in-process fallback.
- **Worker**: Dedicated background worker executing dependency-ordered jobs:
  `MEDIA_PROCESSING` $\rightarrow$ `TRANSCRIPTION` $\rightarrow$ `CONTENT_ANALYSIS` $\rightarrow$ `CONTENT_GENERATION`.
- **Transcoding**: Aspect-ratio variants (`9:16`, `1:1`, `4:5`, `16:9`), real JPEG thumbnails (`00:00:01`), and clean audio extraction for speech-to-text.

### 2.4 AI Content Intelligence Engine (`apps/api/services/ai/`)
- **Provider Abstraction**: `BaseAIProvider`, `OpenAIProvider`, `GeminiProvider`, and `MockAIProvider`.
- **BYOK (Bring Your Own Key)**: Zero markup, keys remain server-side only.
- **Prompt Injection Defense**: Source transcript is strictly treated as untrusted user data.
- **Structured Outputs**: Validated against Pydantic schemas before persistence.

### 2.5 Database Layer (`apps/api/database.py`)
- **Engine**: SQLAlchemy Async engine supporting SQLite (development) and PostgreSQL (production).
- **Entities**:
  - `Content`: Source canonical asset.
  - `Asset`: Physical original files with probed metadata.
  - `ContentVariant`: Generated aspect-ratio variants.
  - `Transcript` & `TranscriptSegment`: Verbatim text with timestamps.
  - `ContentBrief`: Reusable structured intelligence.
  - `GeneratedContent`: Platform-specific native copies.
  - `Job`: Background job lifecycle state tracking.
