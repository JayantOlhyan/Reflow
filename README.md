<div align="center">
  <h1>Reflow</h1>
  <p><strong>Create once. Transform everywhere.</strong></p>
  <p>An open-source, self-hosted content operating system for creators and developers.</p>
</div>

---

## ⚡ Overview

**Reflow** is a self-hosted content operating system designed to take single canonical assets—videos, carousels, images, PDFs, or text—and transform them into platform-tailored native formats for **Instagram, YouTube, TikTok, LinkedIn, X (Twitter), Facebook, and Threads**.

### 🌟 Core Philosophy
- **Self-Hosting First**: Your content, credentials, and database remain 100% on your own infrastructure.
- **Real Content Pipeline**: Multi-layer validated ingestion, collision-free storage, and transactional persistence.
- **BYOK (Bring Your Own Key)**: Zero markup on AI models (Google Gemini & OpenAI).
- **Native Platform Adaptation**: Platform-specific hooks, character limits, aspect ratios, and tags.

---

## 🚦 Implementation Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **Real Content Ingestion** | ✅ Implemented (Phase 1) | Real multipart upload for Video (`.mp4`, `.mov`, `.webm`, `.mkv`), Image (`.png`, `.jpg`, `.webp`), PDF (`.pdf`), and Text (`.txt`, `.md`, inline notes). |
| **Storage & Persistence** | ✅ Implemented (Phase 1) | `BaseStorageService` / `LocalStorageService` with path traversal defense, collision-safe keys (`content/{id}/original/{asset_id}.ext`), and orphan rollback. |
| **Content Library & Streaming** | ✅ Implemented (Phase 1) | Real Content 1 $\rightarrow$ N Asset relationship, asset streaming (`/api/content/{id}/asset/{asset_id}`), real deletion with storage cleanup. |
| **Database & Models** | ✅ Implemented (Phase 0 & 1) | SQLAlchemy async engine (SQLite dev / PostgreSQL prod), schema initialization, and cascade deletion. |
| **Health Telemetry** | ✅ Implemented (Phase 0) | Active component checks for Database, Storage, FFmpeg, and AI keys. |
| **FFmpeg Media Service** | 🟡 Prototype (Phase 2) | Transcoding foundation present; automated pipeline scheduled for Phase 2. |
| **AI Generation Engine** | 🟡 Implemented (BYOK) | Gemini/OpenAI SDK support with deterministic fallback for offline development. |
| **Publishing Connectors** | 🟡 Prototype / Mock (Phase 5) | Standard connector architecture with explicit `not_implemented` status responses. |
| **Workflow Engine** | 🟡 Visual Prototype (Phase 6) | Interactive node graph simulator; DAG execution engine scheduled for Phase 6. |

---

## 🏗️ Architecture

```
USER / BROWSER
      │ (Multipart File Upload / Text Creation)
      ▼
Next.js Frontend (apps/web)
      │ (POST /api/content/upload or /api/content/text)
      ▼
FastAPI Backend (apps/api)
      ├── 1. Multi-Layer Validation (Extension, MIME, Size Limits)
      ├── 2. Collision-Free Storage Key Generation (content/{content_id}/original/{asset_id}.{ext})
      ├── 3. Storage Persistence (LocalStorageService with Path Traversal Defense)
      ├── 4. Database Transaction (Content 1 -> N Asset Records)
      └── 5. Error Cleanup Rollback (Auto-delete physical file if DB fails)
      ▼
Database (SQLite / PostgreSQL) & File Storage (./storage/content/...)
      │
      ▼
Content Library View & Asset Streaming (/api/content/{content_id}/asset/{asset_id})
```

---

## 🚀 Quickstart (Self-Hosting with Docker)

```bash
# 1. Clone the repository
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow

# 2. Copy environment template
cp .env.example .env

# 3. Start Reflow with Docker Compose
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🛠️ Local Development

### Prerequisites
- Node.js >= 18
- Python >= 3.9
- FFmpeg

### Running the Frontend
```bash
cd apps/web
npm install
npm run dev
# Running on http://localhost:3000
```

### Running the Backend
```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
# Running on http://localhost:8000
```

---

## 🧪 Testing

```bash
# Run backend test suite
python3 apps/api/test_api.py

# Run persistence & real-file verification
python3 apps/api/test_persistence.py

# Run frontend build verification
cd apps/web && npm run build
```

---

## 📄 License
Reflow is released under the **MIT License**.
