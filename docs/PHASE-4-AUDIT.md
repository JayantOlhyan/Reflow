# Reflow — Phase 4 Architecture & Carousel Engine Audit

**Date:** 2026-08-29  
**Status:** Completed  
**Objective:** Audit the existing Carousel UI, data models, AI planning capabilities, and rendering pipeline prior to implementing the real, editable carousel creation engine.

---

## 1. Current State vs. Phase 4 Requirements

| Component | Current State | Phase 4 Requirement |
| :--- | :--- | :--- |
| **Carousel Storage** | Frontend in-memory state with static slide placeholders | First-class relational database entities (`Carousel`, `CarouselSlide`, `SlideElement`, `CarouselExport`) with foreign key cascade. |
| **AI Generation** | Client-side fake generator returning 4 hardcoded slides | Real async AI carousel planner consuming `ContentBrief` / `Transcript` via `AIService` and validating output against Pydantic `CarouselPlanSchema`. |
| **Design System** | Basic hardcoded color palette | Deterministic design templates (`MINIMAL`, `EDITORIAL`, `BOLD`, `EDUCATIONAL`) with controlled typography hierarchy, spacing, accent treatment, and layouts (`TITLE`, `TITLE_BODY`, `QUOTE`, `STATISTIC`, `CTA`). |
| **Rendering Engine** | None | Dedicated server-side rendering pipeline producing pixel-perfect 1080x1080 slide images (PNG/JPG) and multi-page PDF documents without client-side screenshot hacks. |
| **Editing & Reordering** | Ephemeral frontend state | Full CRUD API with explicit save, slide reordering (`PUT /api/carousels/{id}/slides/reorder`), and carousel version incrementation. |
| **Export & Persistence** | Static download button placeholder | Atomic file generation saved to `content/{content_id}/carousels/{carousel_id}/` and secure streaming via API endpoints. |

---

## 2. Carousel Data Model & Relational Hierarchy

```
Content (Canonical Source)
   └── Carousel (id, title, template, aspect_ratio, version, status)
         ├── CarouselSlide (id, position, purpose, layout, background)
         │     └── SlideElement (id, type, position, size, content, style_json)
         └── CarouselExport (id, format [PNG/JPG/PDF], storage_key, carousel_version)
```

---

## 3. Asynchronous Workflow & Queue Dispatch

```
USER
  │ (Select Source Content & Target Slides)
  ▼
POST /api/carousels/{id}/generate
  │ (Create Job & Return Immediately)
  ▼
Redis Queue (`reflow:media_jobs` with job_type="CAROUSEL_GENERATION")
  │
  ▼
Media & AI Worker (`apps/api/worker.py`)
  ├── 1. Fetch ContentBrief & Source Transcript
  ├── 2. AIService.plan_carousel() with Pydantic validation
  ├── 3. Persist CarouselSlides & SlideElements in DB
  ├── 4. Render 1080x1080 PNG slides & PDF document
  └── 5. Mark Carousel & Job READY
  ▼
Carousel Editor (apps/web/src/app/carousel/page.tsx)
```

---

## 4. Security & Isolation Controls

1. **Untrusted Input Protection**: Source text and transcript are treated strictly as data blocks; system prompts enforce authoritative template layout constraints.
2. **Deterministic Layouts**: The LLM determines semantic purpose (`HOOK`, `INSIGHT`, `STATISTIC`, `CTA`) and copy; the renderer controls layout geometry, margins, and typography without arbitrary code execution.
3. **Storage Isolation**: Exported PNG and PDF files are stored in `content/{content_id}/carousels/{carousel_id}/` and served via safe streaming endpoints with path traversal protection.
4. **Idempotency & Versioning**: Modifications increment `carousel.version`, invalidating stale export files and ensuring users always download current renders.
