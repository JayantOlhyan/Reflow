# Reflow — Content Operating System

> **"Create once. Transform everywhere."**

Reflow is an open-source, self-hosted content operating system for creators and developers. It converts raw videos, text, and documents into vertical short-form video clips with animated burn-in captions, multi-slide carousels (PNG/PDF), blog copy, and scheduled multi-platform social publications.

---

## Features

- **Open-Source Plugin Ecosystem (`/plugins`)**: Contract-driven plugin architecture (`PluginRegistry`) for custom social platforms, AI providers, storage drivers, media transcoders, and workflow actions with error isolation, permissions, and CLI generator (`python scripts/create-plugin.py`).
- **Outbound Webhooks System (`/settings/webhooks`)**: Signed HTTP webhook delivery (HMAC-SHA256) with exponential backoff retries and recipient event deduplication.
- **Public REST API & API Keys**: Scoped API key authorization with SHA-256 hashed storage, OpenAPI specs, and developer SDK (`packages/plugin-sdk/`).
- **Unified Content Workspace (`/content/[id]`)**: Single 10-section hub for every content item linking lifecycle timeline, media player, interactive transcript with timestamp jumping, clips, carousels, platform copy, governance, and analytics.
- **Centralized Approval Center (`/approvals`)**: Single and bulk publication approval with automated governance quality control safeguards.
- **Publishing Workspace (`/publishing`)**: Tabbed status management (`Draft`, `Scheduled`, `Publishing`, `Published`, `Failed`), post payload inspection, and one-click retry.
- **Global Search & Command Palette (`Cmd + K`)**: Instant server-side search across Content, Clips, Carousels, Publications, Experiments, and Automations.
- **Persistent Notification Drawer**: Real-time slide-over panel delivering job completions, governance alerts, and publishing status events.
- **Automated Video Repurposing**: Ingest long-form videos and automatically generate aspect-ratio variants (`9:16`, `1:1`, `4:5`, `16:9`), speech-to-text transcripts, and structured content briefs.
- **Intelligent Short-Form Clip Engine**: AI moment discovery with transcript boundary snapping, quality scoring, sub-clipping, and aspect-ratio transcoding.
- **Dynamic Captions & Subtitles**: Word-level highlight burn-in captions with safe-area layouts for TikTok, Instagram Reels, and YouTube Shorts.
- **Server-Side Carousel Studio**: Interactive 1080x1080 slide deck planner with rasterization to PNG slide images and multi-page PDF documents.
- **Multi-Platform Publishing Engine**: Direct integration with YouTube, Instagram, LinkedIn, X (Twitter), Facebook Pages, TikTok, Pinterest, and Threads with symmetric token encryption (`ENCRYPTION_SECRET`).
- **UTC Scheduler & Content Calendar**: Independent UTC scheduler daemon with atomic publication claiming and stale-claim recovery.
- **Content Governance & Quality Control**: Centralized policy engine checking video resolution, brand forbidden terms, duplicate publication windows, and factual claim traceability.
- **Closed-Loop Automation Engine**: Lifecycle event triggers (`content.ready`, `clip.ready`) executing custom automation pipelines with rate limits and human-in-the-loop approval gates.
- **Self-Hosted Infrastructure Telemetry**: First-run 6-step setup checklist (`/setup`), real CPU/Memory/Disk metrics (`psutil`), non-destructive database backup/restore scripts (`scripts/backup.sh`, `scripts/restore.sh`), and zero fake mock data.

---

## Architecture Overview

Reflow consists of 6 containerized microservices operating over shared persistence layers:

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

For complete technical specifications, review [`docs/ARCHITECTURE.md`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/ARCHITECTURE.md).

---

## System Requirements

- **Docker**: Docker 24.0+ and Docker Compose v2.0+
- **Host OS**: Linux, macOS, or Windows (via WSL2)
- **Minimum Resources**: 2 CPU cores, 4GB RAM, 20GB free disk storage
- **FFmpeg**: Included in Docker images (or system FFmpeg 5.0+ for bare-metal setup)

---

## Quick Start ("Clone → Configure → Run")

Reflow becomes fully operational with a single `docker compose up -d` command without running manual database commands or build scripts.

```bash
# 1. Clone repository
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow

# 2. Copy environment template
cp .env.example .env

# 3. Start all services via Docker Compose
docker compose up -d
```

### Accessing Reflow
- **Web App**: [http://localhost:3000](http://localhost:3000)
- **First-Run Setup Checklist**: [http://localhost:3000/setup](http://localhost:3000/setup)
- **Backend API Health**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive OpenAPI Specification**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Environment Configuration

Reflow environment variables are defined in `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` or `production` mode |
| `DEPLOYMENT_MODE` | `single_user` | `single_user` security scope |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis queue connection URL |
| `STORAGE_PROVIDER` | `local` | Media storage engine (`local`) |
| `STORAGE_DIR` | `/app/storage` | Persistent media directory |
| `ENCRYPTION_SECRET` | 32+ char secret | AES-256 Fernet OAuth encryption key |
| `GEMINI_API_KEY` | *(Optional)* | Google Gemini API Key |
| `OPENAI_API_KEY` | *(Optional)* | OpenAI API Key |

For detailed variable documentation, review [`.env.example`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/.env.example).

---

## AI Provider & Platform Setup

### 1. AI Setup (Bring Your Own Key)
Configure Google Gemini or OpenAI keys via the web interface under `/settings` or in `.env`:
```env
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...
```

### 2. Platform Connections
Configure platform credentials under `/connections` to enable multi-channel publishing to YouTube, Instagram, X (Twitter), LinkedIn, Meta, TikTok, Pinterest, and Threads.

---

## Backup & Restore

### Database & Media Backup
```bash
./scripts/backup.sh
```
Creates timestamped database dumps and media storage archives under `./storage/backups/`.

### Database & Media Restore
```bash
./scripts/restore.sh ./storage/backups/reflow_db_YYYYMMDD_HHMMSS.sql ./storage/backups/reflow_media_YYYYMMDD_HHMMSS.tar.gz
```

### Safe Storage Cleanup
```bash
./scripts/cleanup.sh
```

---

## Documentation

- **Deployment Guide**: [`docs/DEPLOYMENT.md`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/DEPLOYMENT.md)
- **Architecture Specification**: [`docs/ARCHITECTURE.md`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/ARCHITECTURE.md)
- **Security Policy**: [`SECURITY.md`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/SECURITY.md)
- **Contributing Guide**: [`CONTRIBUTING.md`](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/CONTRIBUTING.md)

---

## Security & Limitations

- **Single-User Scope**: Reflow operates under single-user ownership assumptions. Ensure your server firewall isolates port 8000/3000 to trusted networks.
- **SSRF Defense**: Server-side URL fetching strictly blocks private IP ranges and internal container hostnames.
- **Upload Hardening**: File extensions, MIME types, and file sizes are strictly validated.

---

## License

Reflow is open-source software licensed under the MIT License.
