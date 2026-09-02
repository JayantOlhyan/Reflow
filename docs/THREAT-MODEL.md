# Reflow Threat Model

## 1. System Overview & Asset Inventory
Reflow is a self-hosted content repurposing engine. Key assets needing protection include:
- **User Content & Media Assets:** Source videos, audio files, transcripts, clips, carousels, export PDFs.
- **Platform OAuth Tokens & Credentials:** YouTube, Instagram, LinkedIn, TikTok, X access & refresh tokens encrypted at rest.
- **API Keys & Secrets:** Hashed API keys, HMAC webhook secrets, AI provider API keys.
- **Infrastructure Services:** PostgreSQL database, Redis task queue, local file storage volumes.

---

## 2. Threat Actors & Attack Vectors

### 2.1 Anonymous Attacker (External Unauthenticated)
- **Goal:** Gain unauthorized access to system resources, trigger expensive AI/FFmpeg workloads, probe internal endpoints, or exploit SSRF.
- **Surface:** Public API endpoints (`/api/v1/discovery`, `/health`), Webhook callbacks, upload endpoints.
- **Mitigation:** Strict API key authentication on protected routes, rate limiting (60 req/min), SSRF URL validation, CORS restriction.

### 2.2 Authenticated Low-Privilege User / Malicious Tenant
- **Goal:** Escalate privileges, access another tenant's content items (IDOR/BOLA), or manipulate publication schedules.
- **Surface:** `/api/content`, `/api/clips`, `/api/publications`, `/api/analytics`.
- **Mitigation:** Server-side tenant scoping on all SQL queries (`tenant_id = current_tenant`), RBAC scope checks.

### 2.3 Restricted API Key Attacker
- **Goal:** Perform unauthorized write/delete actions using a read-only or scope-restricted key.
- **Surface:** Public API `/api/v1/*` routes.
- **Mitigation:** Fine-grained scope evaluation (`require_api_key_scopes("WRITE")`).

### 2.4 Malicious Plugin / Ecosystem Author
- **Goal:** Exfiltrate environment secrets or corrupt local filesystem storage via custom plugins.
- **Surface:** Plugin loader, custom connectors, registry manifests.
- **Mitigation:** SHA-256 manifest checksum verification, restricted plugin permissions, process isolation documentation.

### 2.5 Malicious Uploaded File
- **Goal:** Achieve Remote Code Execution (RCE) via FFmpeg command injection, path traversal (`../`), or Zip bombs.
- **Surface:** Ingestion endpoints (`/api/uploads`, `/api/repurpose`).
- **Mitigation:** `secure_filename()` sanitization, server-side MIME checks, strict storage root bounds (`abspath.startswith(STORAGE_DIR)`), list-based `subprocess.exec` (`shell=False`).

---

## 3. Trust Boundaries & Security Assumptions
1. **Database & Redis:** Intended to run inside isolated internal Docker networks (`reflow-net`) without public exposure.
2. **Environment Variables:** Presumed securely injected into containers at boot; redacted from structured logs.
3. **AI Services & Cloud Providers:** Treated as untrusted external inputs; responses validated before storage.
