# Reflow — Public API v1 Quickstart Guide

Get up and running with the Reflow Public API in 5 minutes.

---

## Step 1: Create an API Key
1. Open the Reflow web dashboard and navigate to **Developers** (`/developers`).
2. Click **Create New API Key**.
3. Name your key (e.g. `cURL Quickstart`) and check requested scopes (`CONTENT_READ`, `CONTENT_WRITE`, `CLIP_WRITE`, `PUBLISH`).
4. Copy the revealed Bearer token (`reflow_live_...`).

---

## Step 2: Ingest Text Content via cURL

```bash
curl -X POST http://localhost:8000/api/v1/content/text \
  -H "Authorization: Bearer reflow_live_your_key_here" \
  -F "title=Quickstart Post" \
  -F "raw_text=Reflow makes content repurposing seamless across all social platforms."
```

Output:
```json
{
  "id": "cnt_a1b2c3d4",
  "title": "Quickstart Post",
  "type": "TEXT",
  "created_at": "2026-09-01T21:55:00Z"
}
```

---

## Step 3: Trigger Asynchronous Clip Discovery

```bash
curl -X POST http://localhost:8000/api/v1/content/cnt_a1b2c3d4/clips/discover \
  -H "Authorization: Bearer reflow_live_your_key_here"
```

Output (HTTP 202 Accepted):
```json
{
  "job_id": "job_clip_disc_889900",
  "status": "QUEUED",
  "message": "Clip discovery job enqueued successfully."
}
```

---

## Step 4: Poll Job Completion

```bash
curl -X GET http://localhost:8000/api/v1/jobs/job_clip_disc_889900 \
  -H "Authorization: Bearer reflow_live_your_key_here"
```

Output:
```json
{
  "id": "job_clip_disc_889900",
  "status": "SUCCEEDED",
  "retry_count": 0
}
```
