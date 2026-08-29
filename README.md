<div align="center">
  <h1>Reflow</h1>
  <p><strong>Create once. Transform everywhere.</strong></p>
  <p>An open-source, self-hosted content operating system for creators and developers.</p>
</div>

---

## ⚡ Overview

**Reflow** is a self-hosted content operating system designed to take single canonical assets—videos, carousels, images, PDFs, or text—and transform them into platform-tailored native formats for **Instagram, YouTube, TikTok, LinkedIn, X (Twitter), Facebook, and Threads**.

### 🌟 Core Philosophy
- **Self-Hosting First**: Your content, credentials, and database remain 100% on your own infrastructure.
- **Intelligent Clip Engine**: Automated short-form moment discovery from long-form video, transcript boundary snapping, multi-factor quality ranking (50–100), frame-accurate FFmpeg sub-clipping, and standard aspect ratio transcoding (`9:16`, `1:1`, `4:5`, `16:9`).
- **Carousel & Content Creation Engine**: Structured multi-slide carousel creation, AI planning from source content or `ContentBrief`, 4 deterministic design templates, server-side 1080x1080 PNG rasterization, and multi-page PDF export.
- **AI Content Intelligence**: Provider-independent AI engine (OpenAI & Gemini) with audio extraction, timestamped transcription, reusable `ContentBrief` synthesis, and platform-native generation.
- **Asynchronous Media Engine**: Redis-backed background worker generates real aspect ratio variants (`16:9`, `9:16`, `1:1`, `4:5`) and thumbnails using FFmpeg/FFprobe.
- **Real Content Pipeline**: Multi-layer validated ingestion, collision-free storage, and transactional persistence.
- **BYOK (Bring Your Own Key)**: Zero markup on AI models (Google Gemini & OpenAI).

---

## 🚦 Implementation Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **Scheduling & Content Calendar Engine** | ✅ Implemented (Phase 9) | Server-side background scheduler daemon (`scheduler.py`) with atomic PostgreSQL lease claiming (`(status, scheduled_at)` composite index), IANA timezone resolution (`zoneinfo`), DST transition handling, minimum lead-time validation, crash/stale lease recovery, missed-schedule execution, content deletion guardrails, full Month/Week/Day calendar UI (`/calendar`), and rescheduling & cancellation lifecycle. |
| **Multi-Platform Publishing Engine** | ✅ Implemented (Phase 8) | Universal connector architecture covering YouTube, Instagram (Reels, photos, carousels), LinkedIn (text, video UGC posts), X (API v2 tweets), Facebook Pages, TikTok, Pinterest, and Threads with AES-256 encrypted tokens at rest, multi-destination batch publishing (`/api/publications/batch`), independent failure isolation, SHA-256 idempotency, and Repurpose Studio multi-platform publishing modal. |
| **Captions & Subtitle Polish** | ✅ Implemented (Phase 6) | Short-form transcript cue alignment, 1–4 word punchy beat chunking, styling presets (`BOLD_PUNCH`, `CLEAN_SUBTITLE`, `KINETIC_HIGHLIGHT`, `MINIMAL_WHITE`), keyword highlight formatting, safe-area margin calculation for Reels/TikTok/Shorts, FFmpeg burned captions, clean clip preservation, live synchronized player overlay, and SRT/VTT exports. |
| **Intelligent Clip Engine** | ✅ Implemented (Phase 5) | Relational `Clip` & `ClipVariant` models, transcript boundary snapping ($\pm 3.5\text{s}$), non-maximum overlap suppression, 50–100 quality scoring, frame-accurate FFmpeg extraction (`-avoid_negative_ts make_zero`), `9:16` / `1:1` / `4:5` / `16:9` variants, centered thumbnail extraction, and Repurpose Studio timeline fine-tuning. |
| **Carousel & Content Creation** | ✅ Implemented (Phase 4) | Relational `Carousel`, `CarouselSlide`, `SlideElement`, `CarouselExport` tables, AI planner, design templates (`MINIMAL`, `EDITORIAL`, `BOLD`, `EDUCATIONAL`), 1080x1080 PNG & multi-page PDF renderer, slide reordering, versioning, and Carousel Studio UI. |
| **AI Content Intelligence** | ✅ Implemented (Phase 3) | Audio extraction, timestamped transcription, `ContentBrief` extraction, platform-specific copies (LinkedIn, Instagram, X threads, YouTube chapters), prompt versioning, and validation. |
| **Real Media Engine** | ✅ Implemented (Phase 2) | Asynchronous Redis worker, real FFprobe metadata extraction, FFmpeg variant generation (9:16, 1:1, 4:5, 16:9, Thumbnail), atomic persistence, and streaming. |
| **Real Content Ingestion** | ✅ Implemented (Phase 1) | Real multipart upload for Video (`.mp4`, `.mov`, `.webm`, `.mkv`), Image (`.png`, `.jpg`, `.webp`), PDF (`.pdf`), and Text (`.txt`, `.md`, inline notes). |
| **Storage & Persistence** | ✅ Implemented (Phase 1) | `BaseStorageService` / `LocalStorageService` with path traversal defense, collision-safe keys (`content/{id}/original/{asset_id}.ext`), and orphan rollback. |
| **Content Library & Previews** | ✅ Implemented (Phase 1–9) | Real Content 1 $\rightarrow$ N Asset $\rightarrow$ N Variant $\rightarrow$ N AI Outputs $\rightarrow$ N Carousels $\rightarrow$ N Clips & Captioned Variants $\rightarrow$ N Publications $\rightarrow$ N Scheduled Calendar Events, live processing polling, and Repurpose Studio. |
| **Database & Models** | ✅ Implemented (Phase 0–9) | SQLAlchemy async engine (SQLite dev / PostgreSQL prod), relational tables with foreign-key cascade deletion. |
| **Health Telemetry** | ✅ Implemented (Phase 0 & 9) | Active component checks for Database, Storage, FFmpeg, Redis, AI keys, and Scheduler daemon heartbeat. |
| **Workflow Engine** | 🟡 Visual Prototype (Phase 10) | Interactive node graph simulator; DAG execution engine scheduled for Phase 10. |

---

## 🏗️ Architecture

```
                                       REFLOW
                                          │
               ┌──────────────────────────┼──────────────────────────┐
               │                          │                          │
            CONTENT                       AI                      CAROUSEL
               │                          │                          │
            Original                      │                          │
               │                          │                          │
            FFprobe                       │                          │
               │                          │                          │
            FFmpeg                        │                          │
               │                          │                          │
         ┌─────┴─────┐                    │                          │
         │           │                    │                          │
      Variants     Audio                  │                          │
                     │                    │                          │
                     ▼                    │                          │
                Transcript ───────────────┤                          │
                     │                    │                          │
                     ▼                    │                          │
               ContentBrief ──────────────┼──────────────────────────┤
                     │                    │                          │
          ┌──────────┼───────────┐        │                          ▼
          ▼          ▼           ▼        │                   Carousel Planner
      LinkedIn   Instagram       X        │                          │
          │          │           │        │                          ▼
          └──────────┼───────────┘        │                   Structured Slides
                     │                    │                          │
                  YouTube                 ▼                          ▼
                     │             AI CLIP ENGINE              Design System
                     ▼                    │                          │
             REPURPOSE STUDIO             ▼                          ▼
                     │             Frame-accurate                Renderer
                     │             FFmpeg Extracts                   │
                     │                    │                          ▼
                     ▼                    ▼                   PNG / PDF EXPORTS
              SHORT-FORM CLIPS    9:16 / 1:1 / 4:5 / 16:9
```

---

## 🚀 Quickstart (Self-Hosting with Docker)

```bash
# 1. Clone the repository
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow

# 2. Copy environment template and configure BYOK AI keys
cp .env.example .env

# 3. Start Reflow with Docker Compose (web, api, worker, postgres, redis)
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🛠️ Local Development

### Prerequisites
- Node.js >= 18
- Python >= 3.9
- FFmpeg & FFprobe

### Running the Frontend
```bash
cd apps/web
npm install
npm run dev
# Running on http://localhost:3000
```

### Running the Backend API
```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
# Running on http://localhost:8000
```

### Running the Media & AI Worker
```bash
cd apps/api
source venv/bin/activate
python worker.py
```

---

## 🧪 Testing

```bash
# Run all backend tests (API pipeline, media engine, AI engine, carousel engine, persistence)
apps/api/venv/bin/python3 apps/api/test_api.py
apps/api/venv/bin/python3 apps/api/test_media_engine.py
apps/api/venv/bin/python3 apps/api/test_ai_engine.py
apps/api/venv/bin/python3 apps/api/test_carousel_engine.py
apps/api/venv/bin/python3 apps/api/test_persistence.py

# Run frontend build verification
cd apps/web && npm run build
```

---

## 📄 License
Reflow is released under the **MIT License**.
