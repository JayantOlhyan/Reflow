# Reflow Security Policy & Hardening Guidelines

## 1. Supported Versions

| Version | Supported |
|---|---|
| 1.0.x (Phase 15+) | :white_check_mark: Yes |
| < 1.0.0 | :x: No |

---

## 2. Security Architecture & Single-User Mode

Reflow is primarily designed for **self-hosted, single-user deployment** (`DEPLOYMENT_MODE=single_user`).

- **OAuth Credential Security**: OAuth access and refresh tokens for connected platforms (YouTube, Instagram, X, LinkedIn, Meta, TikTok) are encrypted at rest using AES-256 Fernet symmetric encryption key (`ENCRYPTION_SECRET`).
- **Zero API Key Leakage**: Sensitive API keys and authorization headers are never logged. Log outputs pass through a `RedactingFormatter` that masks sensitive token strings (`[REDACTED]`).
- **Production Key Enforcement**: In `ENVIRONMENT=production`, startup fails if `ENCRYPTION_SECRET` is set to default development fallback key or has fewer than 32 characters.

---

## 3. Defense Mechanisms

### 3.1 Server-Side Request Forgery (SSRF) Protection
All URL targets accepted by Reflow (e.g. web resource ingestion) are validated via `apps/api/utils/ssrf.py`.
Requests to private IP spaces (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.169.254`), loopback addresses, and internal Docker service names (`postgres`, `redis`, `api`) are strictly rejected.

### 3.2 File Upload Hardening
Uploads processed via `/api/content/upload` undergo multi-stage validation:
- **Filename Sanitization**: Path traversal sequences (`..`, slashes) are stripped using `os.path.basename`.
- **Extension & MIME Validation**: Only whitelisted extension and MIME types (`mp4`, `mov`, `jpg`, `png`, `pdf`, `txt`, `md`) are allowed.
- **Size Enforcement**: Uploads exceeding `MAX_UPLOAD_SIZE_MB` (Default: 500MB) are rejected before memory loading.

### 3.3 Command Execution Safety
All FFmpeg and FFprobe media processing commands use argument array invocations (`asyncio.create_subprocess_exec(["ffmpeg", "-i", ...])`). Shell string interpolation (`shell=True`) is strictly prohibited across the codebase.

### 3.4 Rate Limiting
Expensive creation and processing endpoints (`/api/uploads`, `/api/ai`, `/api/clips`, `/api/carousels`, `/api/publications`) enforce per-IP rate limiting (`RATE_LIMIT_PER_MINUTE`, default 60 req/min).

---

## 4. Reporting Vulnerabilities

If you discover a security vulnerability in Reflow, please report it directly to the repository maintainers rather than opening a public issue.

Email: `jayantolhyan@gmail.com`
Response Window: Within 48 hours.
