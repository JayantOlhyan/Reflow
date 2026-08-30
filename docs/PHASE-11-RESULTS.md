# Reflow — Phase 11 Implementation Results

**Phase:** Phase 11 — Real Content Intelligence & Recommendation Engine  
**Status:** COMPLETE  
**Test Suite:** 11/11 Phase 11 Tests Passing | 75/75 Total Test Suite Passing  
**Frontend:** Clean production build across all 14 routes (`next build --webpack`)  

---

## 1. Executive Summary

Phase 11 transforms Reflow from an analytics-recording system into an **intelligent, data-driven content recommendation engine**.

Where Phase 10 answered **WHAT happened** (views, reach, impressions, likes, engagements, velocity), Phase 11 answers:
1. **WHAT PATTERNS appear in the user's historical content and performance data** (correlations between hooks, topics, formats, lengths, templates, posting times, and engagement).
2. **WHAT ACTIONS to try next** (evidence-backed recommendations, replication opportunities, content gap filling, and structured experiments).

### Core Architectural Mandates Met:
- **No Invented Conclusions / No Hallucinations**: Every single insight and recommendation is directly grounded in and traceable to real stored database records.
- **Evidence-First Architecture**: Every recommendation includes sample count, median performance, account/platform baselines, and time range.
- **Strict Correlation vs Causation Language**: The system strictly uses correlation terminology (*"Posts published on Tuesdays were associated with +28% higher engagement"*) and never states causation (*"Posting on Tuesday causes higher engagement"*).
- **Configurable Minimum Sample Thresholds (`MIN_RECOMMENDATION_SAMPLES=5`)**: If insufficient historical publications exist, the system displays `"Insufficient data"` and suppresses spurious recommendations.
- **Deterministic Analytics First, AI Interpretation Second**: Mathematical aggregation, baseline calculations, topic normalization, and anomaly detection are computed deterministically. The LLM is used solely for natural language summarization with post-generation numeric verification.

---

## 2. Intelligence Architecture & Capabilities

| Capability | Implementation | Description |
| :--- | :--- | :--- |
| **Hook Classification** | `classify_hook()` | Classifies text into 8 canonical archetypes: `QUESTION`, `STATISTIC`, `HOW_TO`, `PROBLEM`, `STORY`, `CURIOSITY`, `CONTRARIAN`, `DIRECT_CLAIM`. |
| **Topic Normalization** | `normalize_topic()` | Canonicalizes semantic variants into consistent cluster slugs (e.g. `"AI agents"`, `"AI agent systems"` $\rightarrow$ `"ai-agents"`). |
| **Duration Bucketing** | `get_duration_bucket()` | Standard duration segmentation: `0-15s`, `15-30s`, `30-60s`, `60-120s`, `120s+`. |
| **Statistical Baselines** | `compute_trimmed_median()` | Computes trimmed distribution medians across account, platform, and content formats, preventing single viral anomalies from skewing baselines. |
| **Confidence Scoring** | `derive_confidence()` | Objective classification (`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT_DATA`) based strictly on sample size and effect size. |
| **Anti-Hallucination Guard** | `verify_and_sanitize_claim()` | Scans AI generated claims for numeric tokens and verifies every number against real evidence dictionary before persisting. |
| **Content Gap Discovery** | `run_full_analysis()` | Detects high-performing topics lacking specific format representations (e.g. 5+ video posts with 0 carousels). |
| **Replication Opportunities**| `run_full_analysis()` | Identifies top-performing long-form videos exceeding account median views by 50%+ and suggests clip and carousel extraction. |
| **Experiment Engine** | `Experiment` entity | Tracks structured content experiments with hypothesis, tested variable, control baseline, target sample size, and progress. |
| **Asynchronous Worker Job** | `INTELLIGENCE_ANALYSIS` | Background processing on Redis worker queue (`reflow:media_jobs`) and periodic scheduler sweeps (`scheduler.py`). |

---

## 3. Intelligence Data Model & Schemas

### Relational Entities (`apps/api/models/entities.py`)
- `PerformanceInsight`: Persisted findings (`type`, `scope`, `platform`, `title`, `description`, `evidence_json`, `sample_size`, `confidence`, `baseline_value`, `observed_value`, `delta_pct`).
- `ContentPattern`: Recurring patterns (`pattern_type`, `feature_name`, `feature_value`, `sample_size`, `median_views`, `median_engagement_rate`, `correlation_ratio`, `is_positive`).
- `ContentRecommendation`: Actionable advice (`type`, `scope`, `platform`, `title`, `recommendation_text`, `why_text`, `action_type`, `action_payload_json`, `evidence_json`, `sample_size`, `confidence`, `status`).
- `Experiment`: Hypotheses tracker (`title`, `hypothesis`, `variable_tested`, `control_baseline`, `success_metric`, `target_sample_size`, `current_sample_size`, `status`, `results_json`).

---

## 4. REST API Endpoints

- `GET /api/intelligence/overview`: Account-wide KPIs, baselines, top recommendations, freshness, and content gaps.
- `GET /api/intelligence/insights`: Persisted performance insights.
- `GET /api/intelligence/recommendations`: Active evidence-backed content recommendations.
- `GET /api/intelligence/patterns`: Identified recurring content patterns.
- `GET /api/intelligence/topics`: Performance grouped by normalized topic cluster.
- `GET /api/intelligence/hooks`: Performance breakdown by hook archetype.
- `GET /api/intelligence/durations`: Performance breakdown by duration bucket.
- `GET /api/intelligence/posting-windows`: Localized optimal posting windows.
- `GET /api/intelligence/content-gaps`: High-performing topics lacking format representations.
- `GET /api/intelligence/experiments`: Tracked content experiments.
- `POST /api/intelligence/refresh`: Asynchronous worker job dispatcher.

---

## 5. Verification Results

```bash
$ PYTHONPATH=apps/api apps/api/venv/bin/python3 -m unittest discover -s apps/api -p "test_*.py" -v
----------------------------------------------------------------------
Ran 75 tests in 17.466s
OK

$ cd apps/web && npx next build --webpack
▲ Next.js 16.3.3 (webpack)
✓ Compiled successfully
✓ Generating static pages (14/14)
```
