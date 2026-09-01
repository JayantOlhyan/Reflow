# Phase 20 Audit — Real Public API & Developer SDK Platform

## 1. Executive Summary

Reflow possesses complete internal engines for video processing, AI transcription, short-form clip generation, server-side carousel decks, multi-platform publishing, scheduling, analytics, experimentation, automation rules, governance quality control, and extensibility.

However, external applications, AI agents, and third-party workflow tools (such as n8n) currently lack a unified, versioned, developer-friendly **Public API (`/api/v1`)** with scoped API key authorization, request idempotency (`Idempotency-Key`), standardized async 202 job responses, signed webhook payloads, and typed client SDKs (Python & TypeScript).

This audit evaluates the current REST endpoint inventory, security boundaries, and API architecture to establish the blueprint for Phase 20.

---

## 2. Inventory & Identified API Gaps

### 2.1 Unversioned & Mixed Public/Internal Endpoints
- **Current State**: Endpoints are split across `/api/content`, `/api/publishing`, `/api/clips`, `/api/carousels`, `/api/system`, etc., without explicit `/api/v1` public versioning or separation between frontend internal APIs and external developer APIs.
- **Impact**: Breaking internal changes risk breaking external third-party integrations.

### 2.2 Lack of Scope Enforcement & Granular Permissions
- **Current State**: `APIKey` model exists with `permissions_json`, but public API routes do not systematically enforce required scopes (`CONTENT_READ`, `CONTENT_WRITE`, `CLIP_READ`, `CLIP_WRITE`, `CAROUSEL_READ`, `CAROUSEL_WRITE`, `PUBLISH`, `ANALYTICS_READ`, `EXPERIMENT_READ`, `EXPERIMENT_WRITE`, `AUTOMATION_READ`, `AUTOMATION_WRITE`, `GOVERNANCE_READ`, `GOVERNANCE_WRITE`, `WEBHOOK_READ`, `WEBHOOK_WRITE`).
- **Impact**: AI agents or external tools could exceed intended least-privilege permissions.

### 2.3 Long-Running Request Blocking
- **Current State**: Some heavy operations (such as clip generation, carousel rendering, or platform publishing) keep HTTP requests open instead of immediately returning a `202 Accepted` response with a `job_id` for asynchronous polling (`GET /api/v1/jobs/{id}`).
- **Impact**: HTTP request timeouts occur on external API clients during heavy media processing.

### 2.4 Missing Idempotency Key Storage
- **Current State**: Duplicate mutation requests (e.g. `publish`, `schedule`, `generate`, `automation trigger`) rely on in-memory or single-model checks rather than persistent `Idempotency-Key` header validation (`409 Conflict` on payload mismatch).
- **Impact**: Accidental network retries risk duplicate social posts or redundant processing.

### 2.5 Inconsistent Error Schemas
- **Current State**: Internal FastAPI exceptions return mixed error structures.
- **Impact**: External developers require a standardized error model:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Explicit error description",
      "request_id": "req_12345"
    }
  }
  ```

### 2.6 Missing Developer SDKs & Documentation
- **Current State**: Developer SDKs (`packages/python-sdk` and `packages/typescript-sdk`) and interactive developer portal pages (`/developers`) are missing.

---

## 3. Targeted Phase 20 Public API Architecture

```
 External Applications / AI Agents / n8n / SDKs
                         │
                         ▼
        ┌──────────────────────────────────┐
        │        /api/v1 Gateway           │
        │  (Bearer API Key & Scope Check)  │
        │  (Idempotency & Rate Limiting)   │
        └────────────────┬─────────────────┘
                         │
        ┌────────────────▼─────────────────┐
        │          Reflow Engine           │
        │ Content | Clips | Carousels |    │
        │ Governance | Publishing | Jobs   │
        └──────────────────────────────────┘
```

1. **Versioned REST Base (`/api/v1`)**: Stable resources for `Content`, `Assets`, `Clips`, `Carousels`, `Copy`, `Governance`, `Publications`, `Schedules`, `Analytics`, `Experiments`, `Automations`, `Jobs`, `Webhooks`.
2. **Async 202 Job Responses**: Heavy media & AI operations return `202 Accepted` + `job_id` for polling (`GET /api/v1/jobs/{id}`).
3. **Idempotency Service (`Idempotency-Key`)**: Persists request hash and response to prevent duplicate executions (`409 Conflict` on mismatch).
4. **Scoped API Key Auth (`APIKey`)**: Strict scope validation (`CONTENT_READ`, `PUBLISH`, etc.).
5. **Python SDK (`packages/python-sdk`) & TypeScript SDK (`packages/typescript-sdk`)**.
6. **Developer Portal (`/developers`)**: Interactive UI for API Key management, Webhook subscriptions, SDK guides, and OpenAPI spec.
