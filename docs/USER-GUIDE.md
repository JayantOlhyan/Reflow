# Reflow — End-to-End User Guide

Reflow is an AI-native content engine that transforms raw long-form videos, audio, documents, and text notes into multi-platform social media posts, short clips, visual carousels, and automated publication schedules.

---

## 1. Quick Start ("Clone → Configure → Run")

### Step 1: Clone & Configure
```bash
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow
cp .env.example .env
```
Edit `.env` to set your desired `PORT`, `JWT_SECRET`, and optional AI keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`).

### Step 2: Start Containers
```bash
docker compose up -d
```
Verify that all services (`api`, `web`, `postgres`, `redis`, `worker`) are running:
```bash
docker compose ps
```

### Step 3: Open Setup Wizard
Navigate to `http://localhost:3000/setup` to run the 6-step guided onboarding wizard:
1. **System Health Check**: Verifies PostgreSQL, Redis, Media Storage volume, and FFmpeg installation.
2. **Media Storage**: Verifies local volume permissions (`./storage`).
3. **AI Provider Keys (BYOK)**: Add or update your Google Gemini or OpenAI API keys.
4. **Platform Connections**: Connect social platforms (YouTube, LinkedIn, X, Instagram, TikTok).
5. **Brand Profile & Governance**: Configure tone of voice, forbidden claim keywords, and mandatory tags.
6. **Launch Workspace**: Confirm readiness and launch your first content item.

---

## 2. Canonical Content Lifecycle

Reflow follows a single canonical product loop:

`SOURCE → UNDERSTAND → CREATE → REVIEW → GOVERN → SCHEDULE → PUBLISH → ANALYZE → LEARN`

```
  ┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
  │  Source Upload  ├─────►│ AI Understanding    ├─────►│  Repurpose Studio   │
  │  (Video/Text)   │      │ (Transcript & Hook) │      │  (Clips & Carousels)│
  └─────────────────┘      └─────────────────────┘      └──────────┬──────────┘
                                                                   │
  ┌─────────────────┐      ┌─────────────────────┐      ┌──────────▼──────────┐
  │ Analytics &     │◄─────┤ Multi-Platform      │◄─────┤ Approval & Governance│
  │ Closed-Loop     │      │ Publishing & Calendar│     │ Quality Control     │
  └─────────────────┘      └─────────────────────┘      └─────────────────────┘
```

---

## 3. Core Feature Walkthrough

### 3.1 Global Navigation (`Header` & `CommandPalette`)
- **Global Search (`Cmd + K`)**: Instant search across all long-form source assets, clips, carousels, publication drafts, A/B experiments, and automation rules.
- **Notification Center**: Real-time slide-over panel displaying background processing completion, governance flags, and publishing status events.
- **Quick Create (`+ Create`)**: Global button to instantly upload media or paste text notes from any page.

### 3.2 Unified Content Workspace (`/content/[id]`)
Each content item has a dedicated unified workspace containing:
1. **Header & Metadata**: Status badges, content type, duration, file size, creation timestamp.
2. **Lifecycle Progress**: 5-stage visual progress bar (`Uploaded` → `Understood` → `Created` → `Scheduled` → `Published`).
3. **Interactive Transcript**: Searchable transcript with click-to-seek timestamp jumping on video player.
4. **Repurpose Actions**: One-click clip discovery, carousel generation, and platform copy drafting.
5. **Generated Clips & Carousels**: Visual preview grid of generated sub-assets with virality scores.
6. **Platform Copy Preview**: Platform-customized text variations (LinkedIn, X, YouTube, Instagram).
7. **Governance Status**: Claim verification results and policy compliance flags.
8. **Analytics Summary**: Post-publication impressions, clicks, and engagement.

### 3.3 Centralized Approval Center (`/approvals`)
- View all pending publication drafts requiring review.
- **Single & Bulk Approvals**: Approve individual items or bulk-approve multiple posts at once.
- **Quality Control Safeguard**: Publications flagged with `BLOCKED` governance errors are automatically prevented from bulk approval.

### 3.4 Publishing Workspace (`/publishing`)
- Tabbed filters: `All`, `Drafts`, `Scheduled`, `Publishing`, `Published`, `Failed`.
- **Detail Slide-over**: Inspect full post payload, scheduled UTC time, and platform connection.
- **One-Click Retry**: Re-queue failed publications with a single click.

---

## 4. Operational Commands

- **Run Backend Tests**: `cd apps/api && python3 -m pytest -v`
- **Run Frontend Build**: `cd apps/web && npm run build`
- **Check Service Readiness**: `curl http://localhost:8000/health/ready`
