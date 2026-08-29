# Reflow — Phase 10 Architecture & Capabilities Audit

**Phase:** Phase 10 — Real Analytics & Performance Intelligence Engine  
**Date:** August 2026  
**Status:** Audit Complete  

---

## 1. Executive Summary

Phase 10 turns Reflow's static analytics mockup into a **real performance analytics and intelligence system**. The objective is to ingest genuine post performance metrics from published social platforms (YouTube, Instagram, LinkedIn, X, Facebook, TikTok, Pinterest, Threads), record immutable historical snapshots over time, compute normalized cross-platform performance indicators (views, reach, engagements, valid engagement rates, velocities), and attribute metrics accurately across source contents, variants, clips, carousels, and connected platform accounts.

---

## 2. Existing System Audit

### 2.1 Analytics UI Audit (`apps/web/src/app/analytics/page.tsx`)
- **Current State**: Hardcoded static mockup with fake numbers (`"428.5K impressions"`, `"+24.8%"`, fake table for YouTube Shorts, Reels, LinkedIn, X).
- **Shortcomings**:
  - No connection to backend API or database.
  - Hardcodes arbitrary engagement percentages.
  - Lacks date filtering, platform filtering, content type filtering, and publication drill-down.
  - Converts absent metrics into fake numbers rather than displaying honest "Unavailable" badges.

### 2.2 Publication & Metadata Model (`apps/api/models/entities.py`)
- **`Publication` Entity**:
  - Established in Phase 7/8/9 with `id`, `content_id`, `variant_id`, `platform_connection_id`, `platform`, `status` (`DRAFT`, `SCHEDULED`, `QUEUED`, `UPLOADING`, `PUBLISHING`, `PUBLISHED`, `FAILED`, `CANCELLED`), `title`, `description`, `privacy`, `tags_json`, `external_post_id`, `external_url`, `request_payload_hash`, `scheduled_at`, `published_at`.
  - **Key Asset for Analytics**: `external_post_id` stores the authoritative platform post identifier returned upon real publication (e.g. YouTube Video ID, Instagram Media ID, LinkedIn UGC URN, X Tweet ID).
  - **Missing for Analytics**:
    - `analytics_status` (`NOT_SYNCED`, `SYNCING`, `AVAILABLE`, `PARTIAL`, `UNAVAILABLE`, `FAILED`, `REAUTH_REQUIRED`).
    - `last_analytics_sync_at` (DateTime).
    - `analytics_error_code` / `analytics_error_message`.

### 2.3 Connector Architecture & Platform Capabilities (`apps/api/connectors/`)
- `BasePlatformConnector` currently defines publishing contracts (`publish_video`, `publish_image`, `publish_carousel`, `publish_text`) and `PlatformCapabilities`.
- **Missing Capabilities**:
  - `get_post_metrics(external_post_id: str, access_token: str) -> Optional[Dict[str, Any]]` method on `BasePlatformConnector`.
  - `analytics_supported: bool` and `supported_metrics: List[str]` on `PlatformCapabilities`.
- **Platform-Specific Metrics Availability**:
  - **YouTube**: Supported via YouTube Data API v3 (`videos.list?part=statistics&id={video_id}`) -> `viewCount`, `likeCount`, `commentCount`.
  - **Instagram**: Supported via Meta Graph API (`/{media-id}/insights?metric=reach,impressions,saved,shares` or basic counts `like_count`, `comments_count`).
  - **LinkedIn**: Supported via LinkedIn UGC API (`/organizationalEntityAcls` / `/ugcPosts`) -> `views`, `likes`, `comments`, `shares`, `clicks`.
  - **X (Twitter)**: Supported via Twitter API v2 (`/2/tweets/{id}?tweet.fields=public_metrics`) -> `impression_count`, `retweet_count`, `reply_count`, `like_count`, `quote_count`, `bookmark_count`.
  - **Facebook**: Supported via Graph API Page Post insights (`reactions`, `comments`, `video_views`).
  - **TikTok / Pinterest / Threads**: Explicitly declared as `UNAVAILABLE` or stubbed for future API expansions without fabricating fake metrics.

### 2.4 Worker & Queue Architecture (`apps/api/worker.py`, `services/queue_service.py`)
- Reusable Redis queue (`reflow:media_jobs`) and background worker loop already handle `MEDIA_PROCESSING`, `TRANSCRIPTION`, `CONTENT_ANALYSIS`, `CONTENT_GENERATION`, `CAROUSEL_GENERATION`, `CAROUSEL_RENDER`, `CLIP_GENERATION`, `CLIP_CAPTION_RENDER`, `PLATFORM_PUBLISH`.
- Can seamlessly accept `ANALYTICS_SYNC` jobs without introducing a separate, disconnected queuing daemon.

### 2.5 Scheduler Daemon (`apps/api/scheduler.py`, `services/scheduler_service.py`)
- Continuous background loop polling every 5s.
- Can easily incorporate an analytics sync trigger (`ANALYTICS_SYNC_INTERVAL_MINUTES=60`, with tiered frequencies: high frequency for fresh $<24\text{h}$ posts, moderate for $<7\text{d}$ posts, lower for $>7\text{d}$ posts).

---

## 3. Core Architectural Requirements for Phase 10

1. **Persistent Immutable Metric Snapshots (`PostMetricSnapshot`)**:
   - Stores typed, structured metric snapshots over time (`views`, `impressions`, `reach`, `likes`, `comments`, `shares`, `saves`, `clicks`, `reposts`, `replies`, `engagements`, `watch_time_seconds`, `average_watch_time_seconds`, `completion_rate`, `followers_gained`, `raw_metrics_json`).
   - Strict `NULL` semantics: `NULL` means metric is unavailable from platform API; `0` means the platform explicitly reported zero. Never convert `NULL` to `0`.
2. **Platform Metric Normalization**:
   - Universal internal normalization mapping platform-native terminology into standard Reflow dimensions while preserving platform-specific attributes in structured representation.
3. **Valid Mathematical Calculations**:
   - `engagement_rate = (likes + comments + shares + saves) / reach` (or `impressions`). If denominator is 0 or `NULL`, output is `UNAVAILABLE`.
   - Period comparison ($Current \text{ vs } Previous$) with percentage shifts; handles zero-denominator as `N/A`.
   - Growth velocity ($views / hour$, $engagements / hour$) computed from delta between historical snapshots.
   - Minimum sample size threshold (`MIN_ANALYTICS_SAMPLE_SIZE=100`) before declaring top-performing content.
4. **Resilient Background Sync Architecture**:
   - Reuses existing Redis queue and worker with `ANALYTICS_SYNC` job type.
   - Auto-triggers initial sync upon successful publication.
   - Rate limit handling with exponential backoff and auth failure handling (`REAUTH_REQUIRED`).
   - Independent `analytics_status` on `Publication` that never alters core publication state.
5. **Multi-Dimension Filtering & Attribution**:
   - Aggregations by Content, Variant, Clip, Carousel, Platform, Platform Connection, Date Range (7d, 30d, 90d, All time, Custom).
   - CSV export and manual refresh endpoints with cooldown rate limiting.
