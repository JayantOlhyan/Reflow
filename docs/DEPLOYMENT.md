# Reflow Production Deployment & Hardening Guide

## Production Deployment Architecture

```
                                [ Reverse Proxy / Nginx / Caddy ]
                                      (TLS 443 termination)
                                                │
                      ┌─────────────────────────┴─────────────────────────┐
                      ▼                                                   ▼
            [ Reflow Web Container ]                             [ Reflow API Container ]
               (Next.js App:3000)                                   (FastAPI:8000)
                      │                                                   │
                      └─────────────────────────┬─────────────────────────┘
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                           [ PostgreSQL:5432 ]      [ Redis:6379 ]
                            (127.0.0.1 bound)      (127.0.0.1 bound)
```

---

## Production Security Recommendations

1. **Host Firewall & Egress Filter:**
   - Expose ports `80` and `443` through an external reverse proxy (Caddy/Nginx with Let's Encrypt).
   - Ensure Postgres (`5432`) and Redis (`6379`) remain bound to loopback `127.0.0.1` or internal Docker overlay networks (`reflow-net`).
2. **Environment Secret Management:**
   - Generate a strong 32-byte secret for `ENCRYPTION_SECRET`:
     ```bash
     openssl rand -hex 32
     ```
   - Never commit `.env` files to git.
3. **Storage & Temp Volume Permissions:**
   - Ensure storage directory `/app/storage` is mounted on persistent, backed-up block storage.
