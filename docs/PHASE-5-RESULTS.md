# Reflow — Phase 5 Results & Verification

**Date:** 2026-08-29  
**Status:** Completed & Verified  
**Milestone:** Phase 5 — Real Intelligent Clip Engine

---

## 1. Implementation Summary

Phase 5 turns Reflow into an intelligent clip discovery and media extraction system capable of identifying high-impact short-form moments from long-form video, snapping boundaries to transcript segments, ranking candidates using multi-factor quality scoring, extracting frame-accurate video clips with FFmpeg, and transcoding aspect-ratio variants (`9:16`, `1:1`, `4:5`, `16:9`) alongside video thumbnails.

```
LONG-FORM VIDEO
       ↓
TRANSCRIPT (Timestamped Segments)
       ↓
CONTENT BRIEF (Topics, Key Points, Hooks)
       ↓
AI CLIP ANALYSIS (AIService.discover_and_persist_clips)
       ↓
CANDIDATE MOMENTS (Snapping to boundaries + Non-Max Suppression)
       ↓
RANKING & SCORING (Deterministic 50–100 Multi-Factor Quality Score)
       ↓
USER SELECTION / TIMELINE FINE-TUNING (Repurpose Studio Clips Tab)
       ↓
FFMPEG EXTRACTION (Frame-accurate -ss / -to -avoid_negative_ts make_zero)
       ↓
MASTER CLIP + ASPECT-RATIO VARIANTS (9:16 Vertical, 1:1 Square, 4:5, 16:9)
       ↓
PERSISTENT MEDIA & DOWNLOADS (Clip Library / Repurpose Studio)
```

---

## 2. Core Subsystems Implemented

### 2.1 First-Class Relational Clip Data Model (`apps/api/models/entities.py`)
- **`Clip`**: `id`, `content_id`, `source_asset_id`, `title`, `description`, `hook`, `start_time`, `end_time`, `duration`, `status` (`CANDIDATE`, `SELECTED`, `PROCESSING`, `READY`, `FAILED`), `score` (0–100), `reason`, `source_transcript_segment_ids_json`, `transcript_excerpt`, `thumbnail_path`, `discovery_version`.
- **`ClipVariant`**: `id`, `clip_id`, `variant_type` (`MASTER`, `VERTICAL_9_16`, `SQUARE_1_1`, `PORTRAIT_4_5`, `LANDSCAPE_16_9`, `THUMBNAIL`), `aspect_ratio`, `storage_key`, `mime_type`, `width`, `height`, `duration`, `file_size`, `status` (`QUEUED`, `PROCESSING`, `READY`, `FAILED`).
- Relational cascading rules: deleting `Content` removes all related `Clip` and `ClipVariant` rows and triggers physical storage cleanup.

### 2.2 AI Clip Discovery & Quality Ranking Engine (`apps/api/services/ai_service.py` & AI Providers)
- Analyzes timestamped transcript segments and `ContentBrief` without sending giant raw video files directly to LLMs.
- Boundary Snapping: Adjusts AI candidate start/end times to nearest transcript segment boundaries within $\pm 3.5\text{s}$ tolerance.
- Multi-Factor Quality Scoring:
  $$\text{FinalScore} = \min(100.0, \max(50.0, \text{RawScore} \times 0.4 + \text{DurationScore} \times 0.2 + \text{HookScore} \times 0.2 + \text{AlignmentScore} \times 0.2))$$
- Non-Maximum Overlap Suppression: Deduplicates overlapping clip intervals with Jaccard-like intersection over union $> 0.60$, retaining the highest scoring moment.
- Pydantic validation via `ClipCandidateListSchema` protecting against hallucinations and out-of-bounds timestamps.

### 2.3 Frame-Accurate Video Clip & Variant Generation (`apps/api/services/media_service.py`)
- Master Clip Extraction: Frame-accurate seeking via `ffmpeg -ss {start} -to {end} -i {src} -avoid_negative_ts make_zero -c:v libx264 -c:a aac -movflags +faststart`.
- Probe Validation: Validates master subclip duration, width, height, and audio stream using `ffprobe`.
- Thumbnail Generation: Extracts a sharp JPEG frame from the exact center of the clip duration.
- Transcoding Variants: Generates standardized aspect ratio variants (`VERTICAL_9_16` 1080x1920, `SQUARE_1_1` 1080x1080, `PORTRAIT_4_5` 1080x1350, `LANDSCAPE_16_9` 1920x1080).
- Storage Organization: Saved under collision-free keys `content/{content_id}/clips/{clip_id}/variants/{ratio}.mp4`.

### 2.4 REST API Endpoints (`apps/api/main.py`)
- `POST /api/content/{content_id}/clips/discover`: Queue background AI clip discovery.
- `GET /api/content/{content_id}/clips`: List all discovered clips and variants for a content item.
- `GET /api/clips/{clip_id}`: Retrieve single clip with all child variants.
- `PUT /api/clips/{clip_id}`: Update clip title, hook, start_time, and end_time.
- `POST /api/clips/{clip_id}/generate`: Queue background FFmpeg extraction and variant generation.
- `DELETE /api/clips/{clip_id}`: Delete clip entity and purge physical files from disk.
- `GET /api/clips/{clip_id}/variant/{variant_id}`: Stream specific video or thumbnail variant.
- `GET /api/clips/{clip_id}/stream`: Stream primary video directly for frontend player integration.

### 2.5 Repurpose Studio Clips UI (`apps/web/src/app/repurpose/page.tsx`)
- Studio Mode Switcher: "Platform Copy (Phase 3)" vs "AI Video Clips (Phase 5)".
- "Discover AI Clips" action triggering background discovery with real-time feedback.
- Candidate moment cards with title, hook, duration, timestamp range, ranking score pill, reason, transcript excerpt, and live status.
- Interactive Region Preview: Clicking a candidate seeks the video player to the start time and plays the clip region.
- Interactive Timeline Fine-Tuning: Edit start time and end time with instant duration calculation and persistence.
- Target Aspect Ratio Selector (`9:16`, `1:1`, `4:5`, `16:9`) with "Render Clip" action.
- Direct MP4 download button and stream player for rendered clips.

---

## 3. Automated Test Verification

```bash
apps/api/venv/bin/python3 apps/api/test_api.py
apps/api/venv/bin/python3 apps/api/test_media_engine.py
apps/api/venv/bin/python3 apps/api/test_ai_engine.py
apps/api/venv/bin/python3 apps/api/test_carousel_engine.py
apps/api/venv/bin/python3 apps/api/test_clip_engine.py
apps/api/venv/bin/python3 apps/api/test_persistence.py
```

### Results:
- **Phase 0 & 1 Ingestion Pipeline**: ✅ 11/11 tests passed
- **Phase 2 Media Engine**: ✅ 6/6 tests passed
- **Phase 3 AI Intelligence**: ✅ 5/5 tests passed
- **Phase 4 Carousel Engine**: ✅ 4/4 tests passed
- **Phase 5 Clip Engine**: ✅ 4/4 tests passed (`test_01_clip_and_variant_crud`, `test_02_ai_clip_discovery_and_ranking`, `test_03_real_ffmpeg_clip_extraction_and_variants`, `test_04_end_to_end_worker_clip_pipeline`)
- **Persistence & Cascade Deletion**: ✅ PASSED across all entities.

**Total Automated Tests**: 30 executed — **30/30 PASSED** (0 failures).

---

## 4. Frontend Build Verification

```bash
cd apps/web && npx next build --webpack
```
- Compiled successfully in 1429ms
- Finished TypeScript validation in 1013ms
- Prerendered static pages: 13/13 in 162ms
- 0 TypeScript errors, 0 lint warnings.
