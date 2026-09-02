# Phase 24 — Security Findings & Remediation Register

This document records all security vulnerabilities identified, reproduced, remediated, and verified during the Phase 24 Security Hardening Audit of Reflow.

---

### Finding `SEC-P0-01` — Outbound Webhook SSRF Vulnerability to Internal Network Targets

- **ID:** `SEC-P0-01`
- **Severity:** P0 (Critical)
- **Component:** `WebhookService` / Outbound Event Subscriptions
- **Attack Surface:** `POST /api/v1/webhooks` endpoint
- **Threat Actor:** Authenticated API user with `WEBHOOK_WRITE` permission or malicious tenant.
- **Precondition:** Ability to register an outbound webhook destination URL.
- **Reproduction:** Register a webhook pointing to `http://127.0.0.1:6379/` or `http://169.254.169.254/latest/meta-data/`. Trigger a content lifecycle event. Observe Reflow worker making outbound HTTP requests to private loopback/metadata endpoints.
- **Impact:** Server-Side Request Forgery (SSRF) allowing exfiltration of cloud metadata service credentials, interaction with unauthenticated Redis/Postgres instances, or internal port scanning.
- **Root Cause:** `WebhookService._deliver_payload` accepted any arbitrary URL string without resolving IP addresses or validating against private CIDR ranges.
- **Fix:** Implemented `is_safe_external_url()` in `apps/api/utils/security.py` using `socket.getaddrinfo` and `ipaddress.ip_network` checking. Validates scheme (`http`/`https`) and blocks requests targeting loopback (`127.0.0.0/8`, `::1`), RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), or multicast ranges.
- **Regression Test:** `apps/api/tests/security/test_ssrf_and_webhook_security.py::test_ssrf_rejects_loopback_and_private_ips` and `test_webhook_delivery_blocks_ssrf_target`.
- **Verification:** **PASSED** (100% block rate on malicious targets).
- **Residual Risk:** Low. DNS rebinding mitigation requires strict egress proxy configuration in production environments as documented in `docs/DEPLOYMENT.md`.

---

### Finding `SEC-P1-01` — Unrestricted Public Docker Compose Network Exposure for Internal Services

- **ID:** `SEC-P1-01`
- **Severity:** P1 (High)
- **Component:** `docker-compose.yml` Deployment Topology
- **Attack Surface:** Exposed network ports `5432` (PostgreSQL) and `6379` (Redis) on host interface.
- **Threat Actor:** External attacker scanning public host IP.
- **Precondition:** Deploying Reflow via `docker-compose up -d` on a cloud VM without external firewall rules.
- **Reproduction:** Execute `nmap -p 5432,6379 <host-ip>`. Observe ports open and accepting remote TCP connections.
- **Impact:** Remote database brute-forcing, unauthorized Redis task queue inspection or manipulation.
- **Root Cause:** Container port mappings bound directly to host wildcard `0.0.0.0:5432:5432` and `0.0.0.0:6379:6379`.
- **Fix:** Rebound port declarations in `docker-compose.yml` to loopback interface `127.0.0.1:5432:5432` and `127.0.0.1:6379:6379`.
- **Regression Test:** Verified `docker-compose.yml` port bindings.
- **Verification:** **PASSED**.
- **Residual Risk:** None. Internal services remain isolated to `reflow-net` overlay container bridge.

---

### Finding `SEC-P2-01` — Missing HTTP Security Response Headers

- **ID:** `SEC-P2-01`
- **Severity:** P2 (Medium)
- **Component:** FastAPI Middleware (`main.py`)
- **Attack Surface:** All HTTP API responses
- **Threat Actor:** Browser-based attacker attempting MIME-sniffing, clickjacking, or cross-site framing.
- **Precondition:** User accessing Reflow web UI via browser.
- **Reproduction:** Inspect HTTP headers on `/health` or `/api/v1/content`. Observe missing `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.
- **Impact:** Clickjacking, MIME-type confusion attacks.
- **Root Cause:** Security headers were not automatically injected into global middleware stack.
- **Fix:** Added `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy` to `request_tracing_and_rate_limit_middleware` in `main.py`.
- **Regression Test:** `apps/api/tests/security/test_auth_rbac_tenant_isolation.py::test_security_headers_present_on_api_responses`.
- **Verification:** **PASSED**.
- **Residual Risk:** None.

---

### Summary of Findings
- **P0 (Critical):** 1 (Fixed & Verified)
- **P1 (High):** 1 (Fixed & Verified)
- **P2 (Medium):** 1 (Fixed & Verified)
- **P3 / Informational:** 0
- **Total Unresolved P0/P1 Flaws:** **0**
