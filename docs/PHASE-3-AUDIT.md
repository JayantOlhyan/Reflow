# Reflow — Phase 3 Architecture & AI Engine Audit

**Date:** 2026-08-29  
**Status:** Completed  
**Objective:** Audit existing media infrastructure, BYOK AI configuration, job processing, and database schemas prior to implementing the provider-independent AI intelligence pipeline.

---

## 1. Current State vs. Phase 3 Requirements

| Component | Current State | Phase 3 Requirement |
| :--- | :--- | :--- |
| **Audio Extraction** | Media engine creates video aspect ratio variants | Add clean audio extraction helper in `MediaService` (`extract_audio`) saving temporary MP3/AAC for Whisper/Gemini. |
| **Transcription** | None | Real async transcription pipeline storing full text and normalized timestamped segments (`Transcript` and `TranscriptSegment`). |
| **Content Understanding** | Static fallback dictionary in `ai_service.py` | Provider-independent `ContentBrief` extraction analyzing summary, key points, hooks, quotes, topics, keywords, audience, and tone. |
| **Platform Generation** | Generic mocked string templates | Platform-native generators with custom prompt structures and Pydantic schemas for **LinkedIn**, **Instagram**, **X (with thread support & character validation)**, and **YouTube (with real timestamped chapters)**. |
| **Persistence Model** | `Content`, `Asset`, `ContentVariant`, `Job` | Add `Transcript`, `TranscriptSegment`, `ContentBrief`, and `GeneratedContent` tables with foreign key cascades. |
| **Asynchronous Pipeline** | Redis worker processes `MEDIA_PROCESSING` jobs | Extend Redis worker to execute dependency-ordered jobs: `MEDIA_PROCESSING` $\rightarrow$ `TRANSCRIPTION` $\rightarrow$ `CONTENT_ANALYSIS` $\rightarrow$ `CONTENT_GENERATION`. |

---

## 2. AI Provider Architecture & BYOK

```
                              AIService (Facade)
                                      │
                ┌─────────────────────┼─────────────────────┐
                ▼                     ▼                     ▼
          OpenAIProvider        GeminiProvider         MockProvider
         (Whisper / GPT-4o)   (Gemini 1.5 Flash/Pro)   (Deterministic CI/CD)
```

- **BYOK Credentials**: `OPENAI_API_KEY`, `GEMINI_API_KEY` stored exclusively in server environment (`config.py`).
- **Security & Redaction**: Keys are never logged, never returned in API payloads, and never persisted in database tables.
- **Prompt Injection Defense**: Source transcripts are demarcated strictly as untrusted input data blocks; system prompts enforce authoritative instruction hierarchy.

---

## 3. Storage & Cleanup Strategy

- Audio files extracted for transcription are written to temporary working directories and cleaned up immediately after transcription finishes.
- Original video assets in `content/{content_id}/original/` remain untouched.
- Generated content outputs and briefs are stored in relational database tables with JSON payload serialization for rich structured data.

---

## 4. End-to-End Dependency Pipeline

```
USER UPLOAD (Video)
       │
       ▼
Media Worker: FFprobe + FFmpeg Aspect Ratio Variants
       │ (On Media SUCCESS)
       ▼
Audio Extraction (FFmpeg temp audio)
       │
       ▼
Transcription (AI Provider / Whisper / Gemini)
       │ (Persist Transcript + Segments)
       ▼
Content Analysis (Extract ContentBrief)
       │ (Persist ContentBrief)
       ▼
Platform Generation (LinkedIn, Instagram, X Thread, YouTube Chapters)
       │ (Persist GeneratedContent records)
       ▼
Repurpose Studio UI
```
