# Reflow — Phase 11 Architecture & Capabilities Audit

**Phase:** Phase 11 — Real Content Intelligence & Recommendation Engine  
**Date:** August 2026  
**Status:** Audit Complete  

---

## 1. Executive Summary

Phase 11 transforms Reflow from an analytics recording system into a **data-driven content intelligence and recommendation engine**.

Where Phase 10 answered **WHAT happened** (views, reach, impressions, likes, engagements, velocity), Phase 11 answers:
1. **WHAT PATTERNS appear in the user's historical content and performance data** (correlations between hooks, topics, formats, lengths, templates, posting times, and engagement).
2. **WHAT ACTIONS to try next** (evidence-backed recommendations, replication opportunities, content gap filling, and structured experiments).

### Core Architectural Mandates:
- **No Invented Conclusions / No Hallucinations**: Every single insight and recommendation must be directly grounded in and traceable to real stored database records.
- **Evidence-First Architecture**: Every recommendation includes sample count, median performance, account/platform baselines, and time range.
- **Strict Correlation vs Causation Language**: The system strictly uses correlation terminology (*"Posts published on Tuesdays were associated with +28% higher engagement"*) and never states causation (*"Posting on Tuesday causes higher engagement"*).
- **Configurable Minimum Sample Thresholds (`MIN_RECOMMENDATION_SAMPLES=5`)**: If insufficient historical publications exist, the system displays `"Insufficient data"` and suppresses spurious recommendations.
- **Deterministic Analytics First, AI Interpretation Second**: Mathematical aggregation, baseline calculations, topic normalization, and anomaly detection are computed deterministically. The LLM is used solely for natural language summarization with post-generation numeric verification.

---

## 2. Existing Data Assets Audit

| Data Layer | Available Entities & Fields | Relevance for Intelligence |
| :--- | :--- | :--- |
| **Analytics Snapshots** | `PostMetricSnapshot`: `views`, `impressions`, `reach`, `likes`, `comments`, `shares`, `saves`, `clicks`, `reposts`, `replies`, `engagements`, `watch_time_seconds`, `average_watch_time_seconds`, `completion_rate`, `captured_at`. | Performance metrics, engagement rate calculations, growth velocity, and time-series aggregation. |
| **Publication Records** | `Publication`: `id`, `content_id`, `variant_id`, `platform`, `status`, `title`, `description`, `privacy`, `tags_json`, `external_post_id`, `scheduled_at`, `published_at`, `timezone`. | Channel attribution, posting hour, posting day of week, hashtag count, description length. |
| **Content & Assets** | `Content` (`title`, `content_type`, `text_content`, `thumbnail_path`), `Asset` (`duration`, `width`, `height`, `file_size`, `codec`, `fps`), `ContentVariant` (`variant_type`, `aspect_ratio`). | Format classification (Video, Image, PDF, Text), duration bucketing, aspect ratio tracking (`9:16`, `16:9`, `1:1`, `4:5`). |
| **Transcripts & Briefs** | `Transcript` (`text`, `segments`), `ContentBrief` (`summary`, `topics_json`, `keywords_json`, `hooks_json`, `quotes_json`, `cta_suggestions_json`, `audience`, `tone`). | Topic extraction, keyword density, semantic classification, question/statistic/quote detection. |
| **Clips & Captions** | `Clip` (`hook`, `start_time`, `end_time`, `duration`, `score`, `reason`, `caption_style`, `highlight_keywords_json`), `ClipVariant` (`has_captions`, `aspect_ratio`). | Clip duration analysis, AI clip score correlation, hook type analysis, caption style performance. |
| **Carousels & Slides** | `Carousel` (`template`, `slide_count`, `aspect_ratio`), `CarouselSlide` (`purpose`, `layout`, `headline`, `body`, `tag`). | Design template performance (`MINIMAL`, `EDITORIAL`, `BOLD`, `EDUCATIONAL`), slide count optimal range, slide layout analysis. |

---

## 3. Intelligence Capabilities Gap Analysis

### 3.1 What Reflow Currently Has (Phase 0–10)
- ✅ Persistent publication history and multi-platform metric snapshots.
- ✅ Normalized metrics and engagement rate formulas.
- ✅ Single-publication growth velocities and period-over-period comparisons.
- ✅ Redis worker queue (`reflow:media_jobs`) and background scheduler daemon (`scheduler.py`).
- ✅ BYOK Multi-provider AI service (OpenAI, Gemini, deterministic mock fallback).

### 3.2 What Reflow Needs for Phase 11
1. **Feature Extraction Engine (`ContentFeatureExtractor`)**:
   - Deterministically extracts structured feature vectors from published content (hook category, normalized topic, duration bucket, posting day/hour, slide count, caption length, CTA presence).
2. **Hook Classification (`HookClassifier`)**:
   - Classifies first 3–5 seconds of video/clip or carousel slide 1 into deterministic hook archetypes: `QUESTION`, `STATISTIC`, `HOW_TO`, `PROBLEM`, `STORY`, `CURIOSITY`, `CONTRARIAN`, `DIRECT_CLAIM`.
3. **Topic Normalizer (`TopicClusterer`)**:
   - Canonicalizes related topics (e.g. `"AI agents"`, `"AI agent systems"`, `"autonomous agents"`) into normalized topic tags.
4. **Statistical Intelligence & Baseline Engine (`BaselineEngine`)**:
   - Computes account-wide, platform-wide, and format-wide median baselines.
   - Robust outlier mitigation using median, interquartile range (IQR), and trimmed averages.
5. **Pattern & Anomaly Detection**:
   - Computes correlation ratios vs baseline ($ER_{\text{pattern}} / ER_{\text{baseline}}$).
   - Identifies high-performing patterns and underperforming formats.
6. **Recommendation Engine (`RecommendationEngine`)**:
   - Generates typed candidate recommendations: `BEST_FORMAT`, `BEST_PLATFORM`, `BEST_TOPIC`, `BEST_HOOK`, `BEST_DURATION`, `BEST_POSTING_WINDOW`, `CONTENT_GAP`, `REPLICATION_OPPORTUNITY`, `EXPERIMENT_SUGGESTION`.
7. **Anti-Hallucination Verification Layer**:
   - Validates all AI-generated textual insights against underlying database values; rejects or overrides corrupted numeric claims.
8. **Persisted Intelligence Data Model**:
   - Relational entities: `PerformanceInsight`, `ContentPattern`, `ContentRecommendation`, `Experiment`.
9. **Intelligence REST API & UI**:
   - Full suite of `/api/intelligence/*` routes.
   - Interactive Intelligence page (`apps/web/src/app/intelligence/page.tsx`) with actionable links into Repurpose Studio, Carousel Studio, and Scheduler.

---

## 4. Planned Intelligence Data Architecture

```
                                  PUBLISHED CONTENT
                                          │
                         ┌────────────────┴────────────────┐
                         ▼                                 ▼
               Feature Extraction                 Analytics Snapshots
             (Hooks, Topics, Durations,         (Views, Engagements,
              Posting Times, Templates)          Rates, Velocities)
                         │                                 │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
                               Deterministic Baselines
                            (Account, Platform, Format)
                                          │
                                          ▼
                             Pattern & Anomaly Detection
                                          │
                                          ▼
                               Recommendation Engine
                         (Gaps, Replications, Experiments)
                                          │
                                          ▼
                              AI Phrasing & Validation
                           (Strict Numeric Verification)
                                          │
                                          ▼
                          Persisted Intelligence Database
                                          │
                         ┌────────────────┴────────────────┐
                         ▼                                 ▼
                 Intelligence REST API             Intelligence Dashboard
                (/api/intelligence/*)          (/intelligence with CTAs)
```
