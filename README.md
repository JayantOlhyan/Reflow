# Reflow

> Self-Hosted Open-Source Content Repurposing & Distribution System

![Reflow Banner](docs/assets/reflow-banner.png)

Reflow is an open-source, self-hosted content operating system that transforms long-form video and audio content into short-form vertical clips, multi-slide PDF carousels, and burned-in subtitle videos — automatically scheduling and publishing them across major social platforms.

## Overview

Content creators and marketing teams often spend hours manually extracting clips, generating captions, and drafting posts for different platforms. Reflow automates this workflow locally or on your own infrastructure. It processes large media files using local FFmpeg and integrates with AI providers (Google Gemini, OpenAI, Anthropic) for intelligent analysis, summarization, and clipping recommendations.

## Why This Project Exists

Most content repurposing platforms are expensive, cloud-based SaaS products that hold your media and social credentials hostage. Reflow exists to give you full ownership of your data, media assets, and social platform connections. It operates completely within your infrastructure, scaling vertically with your hardware.

## Features

- **Local Media Processing:** Uses local FFmpeg to transcode videos, extract audio, and burn in custom subtitles (`-threads` bounded for hardware safety).
- **AI-Powered Intelligence:** Generates transcripts, content briefs, and viral hook suggestions using Gemini, OpenAI, or Anthropic.
- **Automated Clipping:** Discover and generate short-form vertical clips (9:16) from long-form landscape video (16:9).
- **Carousel Studio:** Generates multi-slide carousels from text/video transcripts and exports them as PDFs for LinkedIn or Instagram.
- **Multi-Platform Publishing & Scheduling:** Direct OAuth integrations to schedule posts across YouTube, LinkedIn, X (Twitter), Instagram, Facebook, TikTok, Pinterest, and Threads.
- **Analytics & Experiments (A/B Testing):** Track cross-platform engagement, run split tests on titles/hooks, and generate content recommendations.
- **Automations:** Rule-based engine to automate the workflow pipeline (e.g., automatically clip videos that meet specific conditions).
- **Governance & Compliance:** Quality checks, watermark enforcement, brand profiles, and manual review sign-offs before publishing.
- **Plugin System:** Extensible plugin architecture via Python SDK (`reflow-sdk`).

## Architecture

Reflow employs an async-first distributed monolith architecture with background workers and message queues to safely handle long-running media processing without blocking the API.

```text
User
 ↓
[ Next.js 16 Web UI ] (Port 3000)
 ↓
[ FastAPI Backend ] (Port 8000) ──► [ PostgreSQL / SQLite ]
 ↓
[ Redis Queue ] (Media Jobs / Carousels / Webhooks)
 ↓
[ Python Background Workers & Schedulers ] ──► [ FFmpeg ]
```

## Tech Stack

### Frontend
- **Framework:** Next.js 16.3.3 (React 19)
- **Styling:** Tailwind CSS v4, Framer Motion
- **Icons:** Lucide React
- **Language:** TypeScript 5

### Backend
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL (via asyncpg) or SQLite (via aiosqlite), SQLAlchemy, Alembic
- **Caching & Queues:** Redis 7
- **Media Engine:** FFmpeg

### Infrastructure
- **Containerization:** Docker & Docker Compose
- **Storage:** Local Disk (configurable to S3/R2)

## Repository Structure

```text
Reflow/
├── apps/
│   ├── web/                # Next.js Frontend
│   └── api/                # FastAPI Backend & Workers
├── packages/               # Shared libraries
│   ├── plugin-sdk/         # Reflow Plugin SDK
│   ├── python-sdk/         # Python Client SDK
│   └── typescript-sdk/     # TS Client SDK
├── storage/                # Default local storage volume
├── docs/                   # Documentation assets
├── docker-compose.yml      # Container orchestration
└── package.json            # Monorepo configuration
```

## Prerequisites

- **Docker:** v2.20+ (with Docker Compose)
- **Git**
- *(Optional but recommended)* System with decent CPU/RAM if processing 4K/heavy video workloads.
- API Key from Google Gemini, OpenAI, or Anthropic (for AI functionality).

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Edit `.env` to add your AI Provider keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`) and customize secrets.

### 3. Start the application
```bash
docker compose up -d
```

### 4. Access the UI
Navigate to `http://localhost:3000` in your browser.

## Environment Variables

| Variable | Required | Purpose | Example |
| -------- | -------- | ------- | ------- |
| `ENVIRONMENT` | No | execution environment | `production` |
| `DATABASE_URL` | No | Database connection string | `postgresql+asyncpg://reflow:password@postgres:5432/reflow` |
| `REDIS_URL` | No | Redis connection string | `redis://redis:6379/0` |
| `ENCRYPTION_SECRET` | Yes (Prod) | 32+ char key to encrypt OAuth tokens | `super_secret_32_character_string_here` |
| `GEMINI_API_KEY` | Optional | Google Gemini key for AI | `AIza...` |
| `OPENAI_API_KEY` | Optional | OpenAI key for AI | `sk-...` |
| `STORAGE_PROVIDER` | No | Storage backend (`local`, `s3`, `r2`) | `local` |
| `MEDIA_WORKER_CONCURRENCY` | No | Number of parallel media tasks | `2` |

*For social integrations (YouTube, LinkedIn, X, Meta, TikTok), configure the respective `CLIENT_ID` and `CLIENT_SECRET` variables in `.env` or via the web UI settings.*

## Database

Reflow uses **PostgreSQL 16** by default in Docker, but gracefully degrades to **SQLite** for bare-metal rapid testing.

**Key Models:**
- `Content`: The central entity representing a source video/audio/text.
- `Asset` & `ContentVariant`: Media files linked to Content.
- `Clip`: Short-form vertical derivations.
- `Carousel`: Multi-slide derivations.
- `PlatformConnection`: Encrypted OAuth tokens for social accounts.
- `Publication`: Scheduled posts mapped to connections.

Migrations are handled automatically by Alembic at startup via `init_db()`.

## API

Reflow exposes a RESTful API under `/api`.

**Common Endpoints:**
- `GET /api/content` - List all content
- `POST /api/content/upload` - Ingest media (multipart/form-data)
- `POST /api/content/{id}/generate` - Trigger AI generation for platforms
- `POST /api/carousels` - Create a carousel
- `GET /health` - System liveness

Rate limiting is enforced heavily on generation and processing routes (default 60/min per IP).

## Authentication

Reflow is designed for single-user or isolated multi-user team deployments (`DEPLOYMENT_MODE`).
Social authentication (OAuth 2.0) is handled via `/api/connections/{platform}/authorize`. Refresh tokens are securely stored using symmetric AES encryption via `ENCRYPTION_SECRET`.

## Security

- **Encryption at Rest:** All OAuth access and refresh tokens are encrypted in the database.
- **Strict CORS:** Enforced on API routes.
- **Resource Limits:** Hard limits on maximum upload size (default 500MB), queue depth (100 jobs max to prevent memory exhaustion), and disk quota management.
- **Sandboxing:** FFmpeg executes via controlled subprocess boundaries, terminating heavily delayed/hanging jobs automatically.

## Deployment

Deploy using the provided `docker-compose.yml`.

The stack spins up:
1. `web` (Next.js frontend)
2. `api` (FastAPI web server)
3. `worker` (FFmpeg background processor)
4. `scheduler` (Publication dispatcher)
5. `postgres` & `redis`

For production, ensure `ENCRYPTION_SECRET` is updated, place behind a reverse proxy (like Nginx/Traefik) for SSL, and configure persistent volumes for `/var/lib/postgresql/data` and `/app/storage`.

## Development Workflow

### Backend
```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

## Known Limitations

- **FFmpeg Bottlenecks:** Heavy 4K transcodes will consume significant CPU. Media processing is purposefully bounded (`-threads 2`) per job to avoid crashing the server.
- **Clips Generation Context:** Automated clipping requires transcript availability (which means AI must be configured).
- **Single Node Queue:** Currently uses a basic Redis queue. Horizontal scaling of workers requires a shared network filesystem (like EFS) for `storage/` if `local` storage provider is used.

## Roadmap

### Completed
- Core ingestion and UI.
- OpenAI/Gemini integration.
- YouTube, LinkedIn, X, Instagram publishing.
- Scheduled publishing engine.

### Planned
- Advanced Video Editor UI (timeline trimming).
- Automated B-Roll generation.
- Multi-tenancy billing implementation.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

## License

Reflow is released under the MIT License. See `LICENSE` for details.

## AI / Developer Orientation

If you are an AI agent analyzing or modifying this codebase:

- **Frontend (`apps/web`):** Next.js App Router structure. Major features are in `apps/web/src/app` (e.g., `/content`, `/publishing`, `/analytics`).
- **Backend (`apps/api`):** FastAPI app defined in `main.py`. Database models are in `models/entities.py`.
- **Workers (`apps/api/worker.py` & `scheduler.py`):** These run as separate daemon processes in Docker. `worker.py` handles FFmpeg, `scheduler.py` polls for due publications and analytics syncs.
- **Database (`apps/api/database.py`):** Utilizes `asyncpg`/`aiosqlite`.
- **Modifying AI logic:** Inspect `apps/api/services/ai_service.py` (if it exists) or related routes in `main.py`.
- **Modifying Media logic:** Inspect `apps/api/services/media_service.py`.
- **Warning:** Do not modify `ENCRYPTION_SECRET` handling lightly, as it breaks all existing social OAuth tokens.
