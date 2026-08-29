# Reflow — Phase 7 Architectural Audit: Platform Publishing Engine

**Status:** Completed Audit  
**Date:** August 2026  

---

## 1. Existing Connectors & Publishing Infrastructure Audit

We audited the existing connector files in `apps/api/connectors/`, models in `apps/api/models/entities.py`, config in `apps/api/config.py`, and endpoints in `apps/api/main.py`.

### 1.1 Connector Classifications

| File | Status | Notes / Findings |
|---|---|---|
| `apps/api/connectors/base.py` | **PLACEHOLDER** | Defines basic abstract methods (`get_capabilities`, `validate_credentials`, `publish`, `schedule`) and `not_implemented_response`. Needs formal `PlatformCapabilities` schema, OAuth provider abstractions, and retry/rate-limiting contracts. |
| `apps/api/connectors/youtube.py` | **NOT_IMPLEMENTED** | Returns stubbed `not_implemented_response`. Needs full implementation: OAuth 2.0 flow, token encryption/refresh, channel metadata retrieval, media validation, resumable chunked video upload, and error classification. |
| `apps/api/connectors/instagram.py` | **NOT_IMPLEMENTED** | Returns stubbed `not_implemented_response`. Properly categorized as NOT_IMPLEMENTED (deferred to subsequent phases). |
| `apps/api/connectors/linkedin.py` | **NOT_IMPLEMENTED** | Returns stubbed `not_implemented_response`. Properly categorized as NOT_IMPLEMENTED. |
| `apps/api/connectors/x_twitter.py` | **NOT_IMPLEMENTED** | Returns stubbed `not_implemented_response`. Properly categorized as NOT_IMPLEMENTED. |
| `apps/api/connectors/facebook.py` | **NOT_IMPLEMENTED** | Returns stubbed `not_implemented_response`. Properly categorized as NOT_IMPLEMENTED. |
| `apps/api/connectors/tiktok.py` | **NOT_IMPLEMENTED** | Returns stubbed `not_implemented_response`. Properly categorized as NOT_IMPLEMENTED. |

### 1.2 Data Model Audit
- **`PlatformConnection` entity**:
  - Existing fields: `id`, `name`, `handle`, `connected`, `avatar_url`, `capabilities_json`, `created_at`, `updated_at`.
  - Missing security fields: `platform`, `account_name`, `external_account_id`, `status` (`CONNECTED`, `DISCONNECTED`, `REAUTH_REQUIRED`, `EXPIRED`), `access_token_encrypted`, `refresh_token_encrypted`, `token_expires_at`, `scopes_json`, `metadata_json`.
- **Publishing Records**:
  - Missing first-class `Publication` entity tracking publication attempts, external post IDs (`external_post_id`, `external_url`), idempotency payload hashes, and structured error codes.

### 1.3 Security & Credential Storage Audit
- Tokens must **NEVER** be stored in plaintext.
- We need a secure server-side symmetric encryption layer (`services/encryption_service.py`) using `Fernet` / `AES-256-GCM` keyed from `ENCRYPTION_KEY` in environment.
- Pydantic response schemas must strictly omit all `*_encrypted` token fields.
- Logger secret-redaction must filter out `access_token`, `refresh_token`, `client_secret`, and `authorization_code`.

### 1.4 Frontend Connections & Studio Audit
- `apps/web/src/app/connections/page.tsx` had client-side mock state with toggle switches. It must be refactored to fetch real connection records, initiate Google/YouTube OAuth redirect flows, handle callback states, and display `Coming Soon` on non-YouTube platforms.
- `apps/web/src/app/repurpose/page.tsx` needs a dedicated **Publishing Flow**: selecting video variant, picking connected YouTube channel, editing Title/Description/Tags/Privacy, confirming publish, tracking background upload progress, and displaying publication history with real external links.

---

## 2. Phase 7 Architecture Design Blueprint

```
 ┌────────────────────────────────────────────────────────┐
 │                   REPURPOSE STUDIO                     │
 │          (Select Variant & Edit YouTube Metadata)       │
 └──────────────────────────┬─────────────────────────────┘
                            │ POST /api/publications
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │                     FASTAPI API                        │
 │  1. Check Idempotency Hash                             │
 │  2. Validate Metadata & Video File                     │
 │  3. Create Publication (Status: QUEUED)               │
 │  4. Enqueue Job: PLATFORM_PUBLISH                      │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │                    REDIS WORKER                        │
 │  1. Load Encrypted Connection Credentials              │
 │  2. Check Token Expiration & Refresh if needed         │
 │  3. Update Publication -> UPLOADING                    │
 │  4. Stream video chunks to YouTube v3 API              │
 │  5. Receive Real Video ID & URL                        │
 │  6. Update Publication -> PUBLISHED                    │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │                YOUTUBE PLATFORM (REAL)                 │
 │            https://www.youtube.com/watch?v=...         │
 └────────────────────────────────────────────────────────┘
```
