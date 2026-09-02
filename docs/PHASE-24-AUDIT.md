# Phase 24 — Security, Privacy & Release Hardening Audit

## Executive Summary
This document provides the baseline security audit of **Reflow** prior to code hardening in Phase 24. Reflow is an open-source, self-hosted content repurposing and distribution platform with FastAPI backend, Next.js frontend, PostgreSQL, Redis queues, FFmpeg media worker, AI integrations, plugin ecosystem, webhooks, and public REST APIs (`/api/v1`).

---

## 1. Audit Scope & Component Overview

| Component | Path | Language / Tech | Primary Security Function |
|---|---|---|---|
| API Backend | `apps/api/` | Python 3.9 / FastAPI / SQLAlchemy / SQLModel | Auth, Authorization, Rate Limiting, Processing Engines |
| Web Frontend | `apps/web/` | TypeScript / Next.js (App Router) / Tailwind | UI, Error Diagnostic Presentation, API client |
| Plugin System | `plugins/` | Python / JSON Manifests | Hook dispatch, custom connectors, AI prompt overrides |
| Plugin Registry | `registry/` | JSON Manifests | Plugin discovery, checksum integrity validation |
| Scripts & CLI | `scripts/` | Shell / Python | Health diagnostics, backup/restore manifests |
| Self-Hosted Infra | `docker/`, `docker-compose.yml` | Docker / Alpine / Postgres / Redis | Container isolation, network topology, non-root execution |
| Security & Docs | `docs/`, `.github/` | Markdown | Security guidelines, release manifests |

---

## 2. Baseline Security Assessment Matrix

### 2.1 Authentication & Authorization
- **API Key Scope Enforcement:** API Keys support scopes (`READ`, `WRITE`, `ADMIN`, `WEBHOOK_READ`, `WEBHOOK_WRITE`).
- **Missing Checks / Weaknesses:** Certain legacy endpoints under `/api/content` rely on session/tenant headers without checking owner IDs server-side, creating potential IDOR/BOLA vectors.

### 2.2 Outbound Requests & SSRF
- **Outbound Webhooks:** `WebhookService._deliver_payload` accepts arbitrary HTTPS/HTTP target URLs without checking if destination resolves to private or loopback IP ranges (`127.0.0.1`, `10.0.0.0/8`, `169.254.169.254`, `::1`).
- **Remediation:** Introduce `is_safe_external_url()` utility enforcing DNS resolution checks against private and link-local CIDR blocks.

### 2.3 File Storage & Path Traversal
- **Upload Validation:** `validate_upload()` checks extensions and MIME prefixes. `generate_storage_key()` uses `os.path.basename()`.
- **Path Traversal Guards:** File download and stream endpoints require absolute root directory validation (`abspath` must start with `storage_dir`).

### 2.4 Subprocess Execution & FFmpeg Security
- **Command Invocation:** `media_service.py` uses `asyncio.create_subprocess_exec()` with explicit list arguments (`shell=False`).
- **Resource Constraints:** FFmpeg commands are bounded to `-threads 2` and enforced by configurable timeouts (`settings.FFMPEG_TIMEOUT_SECONDS = 300`).

### 2.5 Secret Hygiene & Redaction
- **API Key Storage:** API key hashes (SHA-256) are persisted. Raw keys are shown only once upon generation.
- **Log Security:** Structured logging redacts authorization headers and tokens.

---

## 3. Findings Classification Summary
| ID | Title | Severity | Status |
|---|---|---|---|
| `SEC-P0-01` | Outbound Webhook SSRF vulnerability to Internal Networks | P0 (Critical) | Pending Fix |
| `SEC-P1-01` | Potential Tenant IDOR on Content Asset Retrieval | P1 (High) | Pending Fix |
| `SEC-P1-02` | Docker Compose Public Port Exposure of Internal Redis | P1 (High) | Pending Fix |
| `SEC-P2-01` | Missing Security Headers on API and Next.js Responses | P2 (Medium) | Pending Fix |
| `SEC-P2-02` | Unsanitized Filename Characters in Output Zip Generation | P2 (Medium) | Pending Fix |
