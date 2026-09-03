# Changelog — Reflow

All notable changes to the Reflow project across all implementation phases are documented in this file.

---

## [1.0.0] - 2026-09-03

### Added
- **Real Content Pipeline & Ingestion:** Multi-format file ingestion (MP4, MOV, WEBM, PDF, TXT) with automatic MIME validation and storage bounds.
- **Media Processing Engine:** FFmpeg-powered video variant generation, audio extraction, thumbnail extraction, and ffprobe metadata inspection.
- **AI Content Intelligence:** Automated transcript segmenting, summary brief generation, AI hook scoring, and viral clip candidate discovery.
- **Carousel & Slide Engine:** Multi-slide deck creation, visual element positioning, and PDF export rendering.
- **Captions & Short-Form Polish:** Kinetic, subtitle, and bold-punch caption styles with automated burn-in rendering.
- **Multi-Platform Publishing Engine:** YouTube, Instagram, LinkedIn, TikTok, and X platform connection management, OAuth token encryption, and status tracking.
- **Automations & Governance Rules:** Pre-publish compliance audits, brand voice guidelines, watermark policies, and automated webhook triggers.
- **Observability & Health Telemetry:** Structured JSON logging, trace views, Redis queue depth telemetry, system health diagnostics, and incident logs.
- **Resource Management & Backpressure (Phase 21):** Memory/disk quota controls, priority queueing, FFmpeg thread bounds (-threads 2), and AI request deduplication.
- **Security Hardening (Phase 24):** Outbound webhook SSRF protection, loopback port binding for Postgres/Redis in Docker Compose, and security response headers.
- **UX & Workflow Architecture (Phase 23):** 6-category sidebar workflow structure, 3-question operational dashboard, visual content lifecycle headers, 4-step creation wizards, and standardized error diagnostic modals.
