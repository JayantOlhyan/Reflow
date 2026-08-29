# Reflow — Phase 8 Architectural Audit: Multi-Platform Publishing Engine

**Status:** Completed Audit  
**Date:** August 2026  

---

## 1. Phase 7 Architecture Baseline & Reusable Subsystems

In Phase 7, Reflow established a complete, secure publishing foundation:
- **`PlatformConnection` entity**: Stores `platform`, `account_name`, `handle`, `external_account_id`, `status` (`CONNECTED`, `DISCONNECTED`, `REAUTH_REQUIRED`), `scopes_json`, `capabilities_json`, and encrypted credentials.
- **`EncryptionService`**: AES-128-CBC + HMAC-SHA256 (Fernet) keyed from `ENCRYPTION_SECRET`. Zero plaintext credentials in database or frontend API responses.
- **`Publication` entity**: First-class publication model storing `content_id`, `variant_id`, `platform_connection_id`, `platform`, `status` (`DRAFT`, `QUEUED`, `UPLOADING`, `PUBLISHING`, `PUBLISHED`, `FAILED`, `REAUTH_REQUIRED`, `CANCELLED`), `request_payload_hash`, `external_post_id`, `external_url`, `error_code`, `error_message`, and `attempt_count`.
- **`PublishingService`**: Handles single-use CSRF OAuth state tokens, transparent token refresh, idempotency hashing, and worker orchestration.
- **Generic Redis Worker**: Executes `PLATFORM_PUBLISH` jobs asynchronously.
- **YouTube Connector**: Fully implemented and verified.

---

## 2. Multi-Platform Extension Requirements

### 2.1 Connector Contract Generalization
`BasePlatformConnector` must support multiple media modalities without duplicating worker or queue pipelines:
- `publish_video(video_path, metadata, access_token)`
- `publish_image(image_path, metadata, access_token)`
- `publish_carousel(image_paths, metadata, access_token)`
- `publish_text(metadata, access_token)`
- `validate_metadata(metadata)` -> Pre-upload constraints checking
- `get_capabilities()` -> PlatformCapabilities declaration

### 2.2 Capability Matrix

| Platform | Video | Image | Carousel | Text | Multi-Ratio Support | Key Restrictions |
|---|---|---|---|---|---|---|
| **YouTube** | YES | NO | NO | NO | `16:9`, `9:16`, `1:1`, `4:5` | Title $\le 100$, Description $\le 5000$, Resumable upload |
| **Instagram** | YES (Reels) | YES | YES | NO | `9:16` (Reels), `1:1`, `4:5` | Meta Graph API container polling |
| **LinkedIn** | YES | YES | YES (PDF/Doc) | YES | `16:9`, `1:1`, `9:16` | Text $\le 3000$, 2-stage asset upload |
| **X (Twitter)** | YES | YES | YES (Multi-image) | YES | `16:9`, `1:1`, `9:16` | Text $\le 280$, API v2 endpoints |
| **Facebook** | YES | YES | NO | YES | `16:9`, `1:1`, `4:5`, `9:16` | Page access tokens & Page Feed API |
| **TikTok** | YES | NO | NO | NO | `9:16` | Video duration 3s–10min |
| **Pinterest** | YES | YES | NO | NO | `2:3`, `9:16`, `1:1` | Board ID required, Link support |
| **Threads** | YES | YES | YES | YES | `1:1`, `9:16`, `16:9` | Threads API v1 |

### 2.3 Multi-Platform & Batch Publishing Architecture

```
                  REPURPOSE STUDIO
     (Select Multi-Destinations: YouTube, Instagram, LinkedIn)
                            │
                            │ POST /api/publications/batch
                            ▼
                    FASTAPI BACKEND
          (Creates N independent Publications)
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   Publication 1      Publication 2      Publication 3
     (YouTube)         (Instagram)        (LinkedIn)
         │                  │                  │
         ▼ (QUEUED)         ▼ (QUEUED)         ▼ (QUEUED)
       Job 1              Job 2              Job 3
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                            ▼
                    REDIS WORKER
          (Dispatches each to respective connector)
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
  YouTubeConnector   InstagramConnector LinkedInConnector
         │                  │                  │
         ▼                  ▼                  ▼
     PUBLISHED          PUBLISHED          PUBLISHED
 (youtube.com/...)  (instagram.com/..) (linkedin.com/..)
```

---

## 3. Strict Quality & Anti-Simulation Directives
- **Zero Simulation / Fake IDs**: Every connector must either execute official API calls and return confirmed platform URLs, or return `NOT_IMPLEMENTED` / `CONFIGURATION_REQUIRED`.
- **Independent Failure Isolation**: If one platform encounters rate limits or auth errors, all other platforms proceed independently without cascading failures.
- **Per-Destination Retries**: Retrying operates on individual publication IDs.
