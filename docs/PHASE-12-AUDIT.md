# Reflow — Phase 12 Architecture & Experimentation Audit

**Phase:** Phase 12 — Real Content Experimentation & A/B Testing Engine  
**Status:** Audit Complete  

---

## 1. Executive Summary
Phase 12 introduces a robust, mathematically sound, evidence-first content experimentation system to Reflow. Rather than relying on simple heuristics, the engine allows creators to design, track, evaluate, and conclude A/B (or multi-variant) tests across social platforms. Crucially, the system enforces single-variable experimental design, detects confounds (e.g., posting time or platform mismatches), runs proper statistical analysis (Two-Proportion Z-tests, effect sizes, confidence intervals), and provides a closed-loop system feeding results back into Content Intelligence to refine recommendations dynamically.

---

## 2. Reusable Infrastructure & Assets Audit

| Layer | Reusable Assets | Relevance to A/B Testing |
| :--- | :--- | :--- |
| **Data Entities** | `Content`, `ContentVariant`, `Clip`, `ClipVariant`, `Carousel`, `CarouselSlide`, `Publication` | Real media assets and publications that serve as the foundation for the control and treatment variants. |
| **Analytics Engine** | `PostMetricSnapshot` | Source of truth for engagement, view, and click telemetry. Snapshots capture performance over time. |
| **Publishing & Workers** | Redis queue `reflow:media_jobs`, background worker daemon (`worker.py`) | Queue worker can execute the `EXPERIMENT_EVALUATION` job asynchronously without blocking web requests. |
| **Scheduler** | `scheduler.py` | Sweeps running experiments and enqueues evaluation jobs periodically as new snapshots arrive. |
| **Content Intelligence** | `ContentRecommendation`, `ContentPattern` | Suggests A/B tests based on observed patterns; updates recommendation confidence scores when experiments succeed or fail. |

---

## 3. Experimentation Capabilities Gap Analysis

### 3.1 What Reflow Currently Lacks
1. **Experimentation Data Models**:
   - `Experiment`: Track hypothesis, status, platform, sample size, primary metric, evaluation window, and conclusion.
   - `ExperimentVariant`: Bind variants directly to real `Content` and `Publication` items with clear roles (`CONTROL` or `TREATMENT`).
   - `ExperimentResult`: Store the historical scorecard of evaluations over time, preventing overwrite and showing trend evolution.
2. **Design Validation**:
   - Rejection of invalid experimental designs (e.g., cross-platform comparisons, mixing formats, multi-variable adjustments without warnings).
3. **Statistical Engine**:
   - Calculation of p-values, z-scores, absolute and relative effect sizes, and Wald confidence intervals.
   - Guardrails against division-by-zero when the control baseline is zero.
   - Conservative winner declaration logic (ensuring sample size and statistical/practical significance thresholds are met).
4. **Time-Aligned Snapshot Evaluation**:
   - Guarding against comparison bias by comparing metric snapshots captured at matching time deltas (e.g., strictly 24 hours or 48 hours post-publication).
5. **Confound and Warning Detection**:
   - Automated flagging of posting-time shifts, mismatched platforms, multiple altered variables, or unequal evaluation windows.
6. **Closed-Loop Intelligence Feedback**:
   - Automatically adjusting recommendation confidence based on experimental confirmations or refutations.

---

## 4. Platform API & Experimentation Constraints

Most target platforms (YouTube, Instagram, LinkedIn, X, Facebook) **do not support native A/B testing APIs** for organic content posting. Therefore:
- **Observational Controlled Experiments**: Reflow will publish control and treatment variants as separate, sequential publications.
- **Labeling**: The UI must explicitly label these as "Controlled Experiments" (noting platform-side observational limits) rather than "Native A/B tests".
- **Confounder Mitigation**: Because posts are published sequentially, Reflow must warn the user of posting time mismatches (e.g., weekday vs weekend) or account mismatches.
- **Media Preservation**: For thumbnail or caption tests where media cannot be changed post-publish, separate variant files must be created.
