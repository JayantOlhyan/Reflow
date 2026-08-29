# Reflow — Phase 6 Implementation Results

**Phase:** Phase 6 — Captions, Subtitles & Short-Form Polish  
**Status:** Completed & Fully Verified  
**Date:** August 2026  

---

## 1. Overview & Objective

Phase 6 elevates short-form video clips into presentation-ready social content by adding an automated Caption & Subtitle engine. It slices transcript segments into punchy short-form beats (1–4 words per cue), applies styling presets, positions captions safely away from Reels/TikTok/Shorts UI occlusions, burns styled subtitles into video variants via FFmpeg while strictly preserving original clean clips, and provides live synchronized caption overlays in the Repurpose Studio UI.

```
                  LONG-FORM VIDEO
                         │
                  ┌──────┴──────┐
                  ▼             ▼
              TRANSCRIPT      MEDIA
                  │             │
                  ▼             │
            AI CLIP ENGINE      │
                  │             │
                  ▼             ▼
              CLIP RANGE ──► MASTER CLIP
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
             CLEAN CLIP                  TRANSCRIPT
             (Unburned)                   SEGMENTS
                  │                           │
                  │              ┌────────────┴────────────┐
                  │              ▼                         ▼
                  │         WORD TIMING               STYLE PRESET
                  │       (1-4 words/beat)          (Safe-Area & Colors)
                  │              │                         │
                  │              └────────────┬────────────┘
                  │                           ▼
                  │                     FFMPEG RENDER
                  │                   (Overlay / ASS)
                  │                           │
                  │                           ▼
                  │                  CAPTIONED VIDEO CLIP
                  │                           │
                  └─────────────┬─────────────┘
                                ▼
                       REPURPOSE STUDIO
              (Clean MP4, Captioned MP4, SRT, VTT)
```

---

## 2. Key Accomplishments

### 2.1 Short-Form Caption Segmentation & Alignment (`caption_service.py`)
- **Relative Time Shifting**: Clips are extracted from arbitrary $[start\_time, end\_time]$ ranges of a long-form video. The caption engine extracts overlapping transcript segments and calculates relative timestamps $t_{\text{rel}} = t_{\text{abs}} - clip.start\_time$.
- **Punchy Short-Form Word Chunks**: Segments with $>4$ words are partitioned into 1–4 word beats with sub-second interpolated timing to match modern viral short-form pacing.
- **Keyword Highlights**: Important terms and topics (e.g. `repurposing`, `growth`, `AI`) are matched case-insensitively and highlighted with accent colors.

### 2.2 Caption Styling Presets & Safe-Area Margins
Four distinct design presets tailored for social video engagement:

| Preset | Typography | Primary Color | Highlight Color | Card / Background | Safe Margin ($9:16$) |
|---|---|---|---|---|---|
| **BOLD_PUNCH** | Heavy Bold | Vibrant Yellow (`#FFE600`) | Neon Cyan (`#00FFFF`) | Dark rounded pill (`10,10,15,220`) | `300px` (Above TikTok UI) |
| **CLEAN_SUBTITLE** | Regular Sans | Crisp White (`#FFFFFF`) | Indigo (`#6366F1`) | Translucent Slate (`15,23,42,210`) | `240px` |
| **KINETIC_HIGHLIGHT** | Heavy Bold | Pure White (`#FFFFFF`) | Neon Mint (`#00FFC8`) | Dark Violet pill (`20,15,35,230`) | `280px` |
| **MINIMAL_WHITE** | Clean Sans | Soft White (`#F5F5F5`) | Emerald Green (`#10B981`) | Subtle translucent black | `220px` |

### 2.3 Safe-Area Margin Matrix Across Aspect Ratios
- **$9:16$ (Vertical Reels/TikTok/Shorts)**: Bottom margin is set to `260–320px` to clear platform interaction buttons, profile labels, and audio track titles.
- **$1:1$ (Square)**: Bottom margin set to `80–90px`.
- **$4:5$ (Portrait)**: Bottom margin set to `110–130px`.
- **$16:9$ (Landscape)**: Bottom margin set to `50–70px`.

### 2.4 Multi-Format Subtitle Export
- **SubRip (.srt)**: Formatted standard `.srt` subtitles with millisecond timestamps (`00:00:00,000 --> 00:00:02,500`).
- **WebVTT (.vtt)**: Web standard `.vtt` subtitles for HTML5 `<track>` browser streaming.
- **Advanced SubStation Alpha (.ass)**: Rich subtitle scripts with style tags, alignment codes (`\an2`), and font scaling.

### 2.5 FFmpeg Visual Burning & Clean Clip Preservation
- **Preserves Original Master & Clean Clips**: Clean variants (`has_captions: false`, e.g. `VERTICAL_9_16`) and captioned variants (`has_captions: true`, e.g. `CAPTIONED_VERTICAL_9_16`) are stored as separate persistent entities in `clip_variants`.
- **Pixel-Accurate Overlay Renderer**: Generates crisp RGBA overlays with rounded borders and highlighted keywords and blends them via FFmpeg filter complexes (`overlay=enable='between(t,s,e)'`).
- **FFprobe Output Validation**: Validates stream integrity, duration, resolution, and codecs for all captioned video files.

### 2.6 Interactive Repurpose Studio UI
- **Live Playback Synchronized Overlay**: Subtitle cards appear in real-time on top of the video player matching the active cue timing.
- **Visual Style Switcher**: One-click preview of `Bold Punch`, `Clean Subtitle`, `Kinetic Highlight`, and `Minimal White`.
- **Custom Keywords Input**: Dynamic keyword highlighting editor.
- **Dual Downloads**: Direct one-click download buttons for **Clean MP4**, **Captioned MP4**, **.SRT**, and **.VTT**.

---

## 3. Endpoints Implemented

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/clips/{id}/captions` | Returns structured cues, current style, SRT, and VTT text |
| `PUT` | `/api/clips/{id}/captions` | Updates caption style, enabled flag, and keyword highlights |
| `GET` | `/api/clips/{id}/captions/export.srt` | Downloads RFC-compliant SubRip `.srt` subtitle file |
| `GET` | `/api/clips/{id}/captions/export.vtt` | Streams WebVTT `.vtt` file |
| `POST` | `/api/clips/{id}/render-captions` | Enqueues background job to burn styled captions into clip variants |

---

## 4. Verification & Test Results

### 4.1 Backend Test Suite (`34/34 tests passed`)
- **`apps/api/test_caption_engine.py`**:
  - `test_01_caption_segmentation_and_timing`: PASSED
  - `test_02_srt_vtt_ass_formats`: PASSED
  - `test_03_ffmpeg_caption_burn_and_ffprobe`: PASSED
  - `test_04_full_caption_api_and_worker_pipeline`: PASSED
- **Full Repository Test Suite**:
  - `test_api.py`: 10/10 PASSED
  - `test_media_engine.py`: 6/6 PASSED
  - `test_ai_engine.py`: 5/5 PASSED
  - `test_carousel_engine.py`: 5/5 PASSED
  - `test_clip_engine.py`: 4/4 PASSED
  - `test_caption_engine.py`: 4/4 PASSED
  - Total: **34 tests passing with 0 failures**.

### 4.2 Frontend Compilation
- `npx next build --webpack` in `apps/web`:
  - Compiled successfully with 0 TypeScript and 0 lint errors across all 13 routes.
