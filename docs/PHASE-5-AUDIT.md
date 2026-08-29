# Reflow — Phase 5 Architecture & Intelligent Clip Engine Audit

**Date:** 2026-08-29  
**Status:** Completed  
**Objective:** Audit the existing MediaService, FFmpeg infrastructure, Transcript and ContentBrief data models, Repurpose Studio UI, and background worker queue prior to implementing the Real Intelligent Clip Engine.

---

## 1. Current State vs. Phase 5 Requirements

| Component | Current State | Phase 5 Requirement |
| :--- | :--- | :--- |
| **Clip Data Model** | None (ad-hoc frontend flags) | First-class relational entities (`Clip`, `ClipVariant`) with cascade deletion, timestamp ranges, ranking scores, reasons, and transcript segment traceability. |
| **Clip Discovery** | None | Asynchronous AI Clip Discovery analyzing timestamped `Transcript` + `ContentBrief` to identify high-value standalone moments (15–90s) with boundary snapping. |
| **Ranking & Deduplication** | None | Multi-factor deterministic ranking formula (hook strength, completeness, density, duration) and interval overlap suppression. |
| **Clip Extraction** | Transcodes entire source video | Real frame-accurate FFmpeg sub-clipping from source master (`-ss`, `-to`, `-avoid_negative_ts make_zero`) creating verified master clips. |
| **Aspect-Ratio Variants** | Source video variants only | Clip-specific multi-aspect ratio generation (`9:16`, `1:1`, `4:5`, `16:9`) and thumbnails for each extracted clip. |
| **Repurpose Studio UI** | Static platform text cards & full video player | Interactive Clip Studio area in Repurpose Studio with candidate list, source region preview player, timestamp editor, and instant download. |
| **Storage & Streaming** | `content/{id}/variants/` | Isolated clip directory `content/{content_id}/clips/{clip_id}/` with secure streaming endpoints. |

---

## 2. Relational Hierarchy & Traceability

```
Content (Original Video)
   ├── Transcript (Verbatim Spoken Text)
   │     └── TranscriptSegment (start_time, end_time, text)
   ├── ContentBrief (Topics, Summary, Key Points, Hooks)
   └── Clip (id, title, hook, start_time, end_time, duration, score, reason)
         └── ClipVariant (id, variant_type [MASTER, 9:16, 1:1, 4:5, 16:9, THUMBNAIL], storage_key)
```

---

## 3. Asynchronous Pipeline & Worker Execution

```
USER (Repurpose Studio)
  │ (Triggers "Discover Clips")
  ▼
POST /api/content/{content_id}/clips/discover
  │ (Enqueue Job & Return Immediately)
  ▼
Worker: `CLIP_DISCOVERY`
  ├── 1. Load Transcript & ContentBrief
  ├── 2. AIService.discover_clips()
  ├── 3. Pydantic validation (start >= 0, end <= source_duration, duration in [15, 90])
  ├── 4. Boundary snapping to nearest transcript segments
  ├── 5. Overlap suppression & quality ranking
  └── 6. Persist candidate Clip records in DB
  ▼
USER Reviews Candidates & Adjusts Timestamps in Studio
  │
  ▼
POST /api/clips/{clip_id}/generate
  │ (Enqueue Job & Return Immediately)
  ▼
Worker: `CLIP_RENDER`
  ├── 1. FFmpeg sub-clipping from original source asset -> master.mp4
  ├── 2. FFprobe validation (duration, video/audio stream, codec)
  ├── 3. Aspect-ratio transforms (9:16 default, 1:1, 4:5, 16:9) + Thumbnail
  └── 4. Mark Clip & ClipVariants READY
```

---

## 4. Security & Safety Principles
1. **Source Untrusted Input**: AI timestamps are strictly validated against physical asset duration probed by FFprobe.
2. **No Command Injection**: FFmpeg subprocess arguments are passed as structured parameter arrays, never concatenated shell strings.
3. **Storage Isolation**: Clip files are saved in `content/{content_id}/clips/{clip_id}/` and served via safe streaming endpoints with path traversal defense.
4. **Idempotency & Cost Control**: Discovery results are cached per `discovery_version` (`v1`) and only run on explicit user action.
