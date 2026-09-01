# Reflow — Public API v1 Reference

The Reflow Public REST API (`/api/v1`) enables external applications, script workers, AI agents, and third-party automation tools (such as n8n) to programmatically ingest, process, transform, govern, schedule, and publish content.

---

## Base URL & Authentication

```http
http://localhost:8000/api/v1
```

All requests must include a valid Bearer API key header:
```http
Authorization: Bearer reflow_live_...
```

Alternatively, use the `X-API-Key` header:
```http
X-API-Key: reflow_live_...
```

---

## Available Scopes

| Scope | Description |
|---|---|
| `CONTENT_READ` | Query and inspect content items and attached media assets. |
| `CONTENT_WRITE` | Create, upload, text ingest, or delete content items. |
| `CLIP_READ` | List and inspect discovered short-form clips. |
| `CLIP_WRITE` | Trigger AI clip discovery and FFmpeg video clip generation. |
| `CAROUSEL_READ` | Inspect carousel slide decks and export PDF/PNG decks. |
| `CAROUSEL_WRITE` | Create, update, or render server-side carousel decks. |
| `PUBLISH` | Create, schedule, publish, cancel, or retry social platform posts. |
| `ANALYTICS_READ` | Access performance metrics and overview intelligence. |
| `EXPERIMENT_READ` | Inspect A/B test experiments. |
| `EXPERIMENT_WRITE` | Create, update, start, or stop A/B test experiments. |
| `AUTOMATION_READ` | List automation rules. |
| `AUTOMATION_WRITE` | Create, update, delete, enable, or disable automation rules. |
| `GOVERNANCE_READ` | Evaluate quality control checks and policy rules. |
| `WEBHOOK_READ` | List webhook subscriptions. |
| `WEBHOOK_WRITE` | Subscribe, delete, or test outbound webhooks. |

---

## Idempotency Key (`Idempotency-Key`)

For mutation endpoints (`POST /api/v1/publications`, `POST /api/v1/schedules`, `POST /api/v1/clips/.../generate`), pass a unique string header:
```http
Idempotency-Key: req_unique_uuid_12345
```
If the same key is sent with identical payload, the cached response is returned. If the key is reused with a different request payload, the API returns `409 Conflict`.

---

## Asynchronous Operations & Job Polling (202 Accepted)

Heavy tasks (clip discovery, clip generation, carousel rendering, copy generation, platform publishing) return `202 Accepted` immediately with a `job_id`:
```json
{
  "job_id": "job_clip_disc_a1b2c3d4",
  "status": "QUEUED",
  "message": "Clip discovery job enqueued successfully."
}
```

Poll job status via:
```http
GET /api/v1/jobs/{job_id}
```
When status reaches `SUCCEEDED`, output results are available.
