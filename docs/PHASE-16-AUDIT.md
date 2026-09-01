# Reflow — Phase 16: Product Experience & Workspace Audit

**Phase:** Phase 16 — Real End-to-End Content Workspace & Productization  
**Status:** Audit Complete  

---

## 1. Executive Summary

Reflow has successfully implemented 15 core architectural and engine phases (Media Processing, AI Synthesis, Carousels, Clips, Captions, Multi-Platform Connectors, UTC Scheduler, Performance Intelligence, Experimentation, Closed-Loop Automation, Governance, and Self-Hosted Production Hardening).

However, because these 15 phases were added sequentially, the user interface currently functions as a collection of feature silos rather than a unified product.

The primary objective of Phase 16 is to unify all subsystems into a single, cohesive **Content Workspace** (`/content/{id}`) and a canonical **Product Journey**:

$$\text{SOURCE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{CREATE} \longrightarrow \text{REVIEW} \longrightarrow \text{GOVERN} \longrightarrow \text{SCHEDULE} \longrightarrow \text{PUBLISH} \longrightarrow \text{ANALYZE} \longrightarrow \text{LEARN}$$

---

## 2. Comprehensive Page-by-Page Audit

### 2.1 Overview Dashboard (`/`)
- **Gaps / Issues**: Exposes vanity numbers without direct actionability. Lacks a "Needs Attention" queue prioritizing failed posts, blocked governance rules, expired tokens, or pending approvals.
- **Improvements Required**: Redesign into an action-oriented dashboard showing Needs Attention (highest priority), Upcoming Schedule, Recent Performance, and Smart Recommendations routing into creation flows.

### 2.2 Content Library (`/content`)
- **Gaps / Issues**: Clicking a content item does not open a comprehensive single-content workspace. Users cannot view source assets, transcripts, clips, carousels, generated copies, governance results, and analytics in a single unified view.
- **Improvements Required**: Add direct navigation from library items to a dedicated `/content/{id}` Unified Content Workspace.

### 2.3 Unified Content Workspace (`/content/{id}`) — *NEW*
- **Gaps / Issues**: Currently missing. Content assets are fragmented across separate tools (`/repurpose`, `/carousel`, `/calendar`).
- **Improvements Required**: Build a 10-section workspace centered around a single source item:
  1. Source Content Header & Metadata
  2. Content Lifecycle Timeline
  3. Real Media / Document Preview Player
  4. Interactive Transcript (with Search, Copy, Jump-to-Time)
  5. Repurpose & Smart Actions
  6. Generated Clip Workspace
  7. Generated Carousel Workspace
  8. Platform-Specific Copy Workspace
  9. Governance Checks & Overrides
  10. Asset Performance & Experiment Results

### 2.4 Approval Center (`/approvals`) — *NEW*
- **Gaps / Issues**: Currently, approvals are scattered or handled only inside publication modals. No centralized location exists for reviewing pending content, clips, carousels, or scheduled posts awaiting sign-off.
- **Improvements Required**: Build a centralized `/approvals` center with single-item and bulk-approval controls (preventing bulk approval of `BLOCKED` items).

### 2.5 Publishing Workspace (`/publishing`) — *NEW*
- **Gaps / Issues**: Publications are viewed within the calendar grid or individual post modals. Lacks a dedicated publishing queue management table with status filtering (`Draft`, `Waiting Approval`, `Scheduled`, `Publishing`, `Published`, `Failed`).
- **Improvements Required**: Build `/publishing` workspace with real `Publication` entity models and detailed publication view.

### 2.6 Notifications & Command Palette — *NEW*
- **Gaps / Issues**: Background operations (worker jobs, automation triggers, publishing runs) communicate via raw logs or toast messages without a persistent notification center or keyboard command palette.
- **Improvements Required**:
  - Implement `Notification` database entity & REST endpoints (`GET /api/notifications`, `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all`).
  - Add Header Notification Drawer & Bell badge.
  - Add keyboard command palette (`Cmd+K` / `Ctrl+K`) for instant navigation and actions.
  - Add Global Quick Create (`+ Create`) menu in Header.

### 2.7 Setup & Onboarding (`/setup`)
- **Gaps / Issues**: Created in Phase 15 as a status checklist. Lacks step-by-step guided onboarding flow (`System Check` → `Storage` → `AI Provider` → `Platform Connections` → `Brand Profile` → `First Upload`).
- **Improvements Required**: Upgrade `/setup` into an interactive 6-step setup wizard tracking completion status.

### 2.8 Settings & System (`/settings` & `/system`)
- **Gaps / Issues**: Settings page was partially hardcoded in early phases; system page displayed raw database logs without clean filtering.
- **Improvements Required**: Group settings into clear domain tabs (`General`, `AI Providers`, `Storage`, `Platform OAuth`, `Publishing`, `Automation`, `Governance`, `System`). Show real capabilities matrix per platform connection (`Supported` vs `Unsupported`).

---

## 3. Product Inconsistencies & Navigation Fixes

1. **Terminology Standardization**:
   - Standardize terms across UI: "Source Content", "Clip", "Carousel", "Platform Copy", "Publication", "Governance Policy", "Automation Rule", "Experiment".
2. **Deep Linking**:
   - Ensure every core entity has a stable deep-link route (`/content/{id}`, `/clips/{id}`, `/carousels/{id}`, `/experiments/{id}`, `/automations/{id}`, `/publications/{id}`).
   - Browser refresh on any page must restore full entity state without relying on transient in-memory React state.
3. **Unsaved Changes Defense**:
   - Add dirty-state warnings when navigating away from slide/copy editors with unsaved edits.
4. **Unsupported Feature Indicators**:
   - Explicitly display *"Not supported by this platform"* badges (e.g. carousels on X/Twitter) rather than disabling buttons without explanation.
