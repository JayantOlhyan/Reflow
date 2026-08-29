# Reflow — System Architecture

**"Create once. Transform everywhere."**

Reflow is an open-source, self-hosted content operating system for creators and developers. This document describes the system architecture established in Phase 0.

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    User([Creator / Browser]) -->|HTTP / React 19| Web[Next.js Frontend (apps/web)]
    Web -->|REST API / JSON| API[FastAPI Backend (apps/api)]
    
    API --> Config[Centralized Settings (pydantic-settings)]
    API --> Logging[Structured Logger]
    API --> Health[Health Telemetry Service]
    API --> DB[(Database: SQLite / PostgreSQL)]
    API --> Storage[(Storage: Local Filesystem / S3 / R2)]
    
    API --> Media[FFmpeg Media Service]
    API --> AI[AI Engine Service]
    API --> Connectors[Platform Connectors]
    
    Connectors --> YT[YouTube Connector]
    Connectors --> IG[Instagram Connector]
    Connectors --> TT[TikTok Connector]
    Connectors --> LI[LinkedIn Connector]
    Connectors --> X[X / Twitter Connector]
    Connectors --> FB[Facebook Connector]
```

---

## 2. Core Subsystems

### 2.1 Frontend (`apps/web`)
- **Framework**: Next.js 16 (App Router), React 19, TypeScript.
- **Styling & UI**: Tailwind CSS v4, custom dark theme aesthetic (`#0B0D12` background, `#111827` cards, `#1F2937` borders), Framer Motion for smooth canvas interactions.
- **API Communication**: Centralized HTTP client (`apps/web/src/lib/api.ts`) managing normalized error handling, empty states, and loading states without fallback hallucinations.

### 2.2 Backend API (`apps/api`)
- **Framework**: FastAPI with async route handlers and standard error envelopes.
- **Configuration**: Pydantic `BaseSettings` (`config.py`) strictly loading from environment variables and `.env` with validation.
- **Logging**: Structured JSON/formatted logging utility (`apps/api/utils/logging.py`) with secret redaction.

### 2.3 Database Layer (`apps/api/database.py`)
- **ORM / Engine**: SQLAlchemy Async engine supporting:
  - Development / Self-Hosted single node: `sqlite+aiosqlite:///./storage/reflow.db`
  - Production / Multi-worker: `postgresql+asyncpg://...`
- **Core Entities**:
  - `Content`: Source canonical asset metadata.
  - `Asset`: Physical media files (video, audio, images, PDF).
  - `ContentVariant`: Platform-specific output formats (e.g. 9:16 vertical crop, 4:5 portrait).
  - `PlatformConnection`: Local OAuth tokens and platform configuration.
  - `Workflow` & `WorkflowExecution`: Pipeline definitions and run traces.
  - `Job`: Background job tracking (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `RETRYING`, `CANCELLED`).
  - `SystemLog`: Structured operational log records.

### 2.4 Storage Abstraction (`apps/api/services/storage_service.py`)
- Standard interface: `BaseStorageService` providing `put()`, `get()`, `delete()`, `exists()`, and `get_url()`.
- Default implementation: `LocalStorageService` with strict path traversal prevention.

### 2.5 Media Processing (`apps/api/services/media_service.py`)
- Async subprocess wrapper over `ffmpeg` and `ffprobe` for transcoding, scaling, aspect ratio conversion (16:9 to 9:16 with blur pad), and thumbnail extraction.

### 2.6 Platform Connectors (`apps/api/connectors/`)
- `BasePlatformConnector` defining:
  - `get_capabilities()` $\rightarrow$ List of supported media types and operations.
  - `validate_credentials()` $\rightarrow$ Verifies local token health.
  - `publish()` $\rightarrow$ Dispatches publication (returns explicit `not_implemented` status in Phase 0).
  - `schedule()` $\rightarrow$ Dispatches schedule request (returns explicit `not_implemented` status in Phase 0).

### 2.7 Health Telemetry (`apps/api/services/health_service.py`)
- Active component probing for Database, Redis, Storage filesystem, FFmpeg binary, and AI provider credentials, reporting real statuses (`healthy`, `degraded`, `unavailable`, `not_configured`).

---

## 3. Security Architecture

1. **Self-Hosted Data Ownership**: All OAuth tokens, media assets, and database records remain exclusively on the user's infrastructure.
2. **Credential Redaction**: API keys and tokens are never logged or exposed to client endpoints.
3. **Upload Sanitization**: Filenames are sanitized, MIME types validated, and storage paths restricted against directory traversal attacks.
