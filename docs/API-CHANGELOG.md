# Reflow — Public API v1 Changelog

Reflow adheres to Semantic Versioning (`MAJOR.MINOR.PATCH`) for all Public API (`/api/v1`) releases.

---

## [1.0.0] - 2026-09-01

### Initial Release — Public API v1 & Developer SDK Platform

- **Stable Resource Endpoints (`/api/v1`)**:
  - `Content`: metadata ingest, file upload, text ingest, list, get, delete, assets.
  - `Clips`: discover (202 Accepted), list, get, update, delete, generate (202 Accepted).
  - `Carousels`: create, list, get, update, delete, generate (202 Accepted), export (PNG/PDF).
  - `Copy`: platform copy generation (202 Accepted).
  - `Governance`: evaluate, summary, checks.
  - `Publications`: create (with Idempotency-Key), list, get, publish (202 Accepted), cancel, retry.
  - `Schedules`: create, list, get, update, delete.
  - `Analytics`: overview, content, publications, platforms.
  - `Experiments`: list, create, get, start, stop.
  - `Automations`: list, create, get, delete, enable, disable.
  - `Jobs`: status polling, events trace, retry.
  - `Webhooks`: list, create, get, delete, test ping.
- **Idempotency Key Support**: `Idempotency-Key` header validation on mutation endpoints.
- **Scoped API Key Auth**: Granular scope permissions (`CONTENT_READ`, `PUBLISH`, etc.).
- **Client SDKs**: Official Python (`reflow-sdk`) and TypeScript (`@reflow/sdk`) libraries.
- **Developer Portal UI**: Interactive key and webhook subscription manager (`/developers`).
