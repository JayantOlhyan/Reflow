# Reflow Security Policy & Architecture

## Security Architecture Overview
Reflow implements a multi-layer defense-in-depth architecture designed for self-hosted, open-source content operating system deployments.

### Key Security Controls
1. **Authentication & API Keys:**
   - Public API (`/api/v1`) enforces API key authentication using hashed keys (`SHA-256`).
   - Scopes (`READ`, `WRITE`, `ADMIN`, `WEBHOOK_READ`, `WEBHOOK_WRITE`) are evaluated server-side.
2. **Tenant Isolation:**
   - All content items, assets, clips, carousels, and publications are server-side scoped by `tenant_id` and `user_id`.
3. **SSRF Mitigation:**
   - Outbound HTTP deliveries (webhooks, connectors) validate target URLs via `is_safe_external_url()`.
   - Outbound requests targeting loopback (`127.0.0.0/8`, `::1`), private RFC 1918 networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), or link-local metadata IPs (`169.254.169.254`) are blocked.
4. **File Storage & FFmpeg Execution:**
   - Filenames are sanitized via `secure_filename`. Path traversal (`../`, URL-encoded paths) is rejected.
   - FFmpeg subprocesses run without a shell (`shell=False`), restricted to `-threads 2` and bounded by process timeouts (`FFMPEG_TIMEOUT_SECONDS = 300`).
5. **Secret Redaction:**
   - Structured JSON logs redact sensitive headers (`Authorization`, `X-API-Key`) and secret values.
6. **Infrastructure Isolation:**
   - Production Docker deployments bind internal services (Postgres, Redis) to loopback `127.0.0.1` interfaces only.

---

## Reporting Vulnerabilities
To report a security vulnerability, please email security@reflow.dev or submit a private security advisory on GitHub.
