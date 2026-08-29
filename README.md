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
- **BYOK (Bring Your Own Key)**: Zero markup on AI models (Google Gemini & OpenAI).
- **Native Platform Adaptation**: Platform-specific hooks, character limits, aspect ratios, and tags.
- **Honest System Contracts**: Clean empty states, zero fake metric fallbacks, and explicit `not_implemented` status handling for unintegrated connectors.

---

## 🚦 Implementation Status (Phase 0 Foundation)

| Component | Status | Details |
| :--- | :--- | :--- |
| **Frontend UI Shell** | ✅ Implemented | Complete 11-page dark theme application with Next.js 16 (App Router), Tailwind CSS v4, and Lucide/Custom SVGs. |
| **Database & Models** | ✅ Implemented | SQLAlchemy async engine supporting SQLite (dev) and PostgreSQL (prod), schema initialization, and model entities. |
| **Storage Abstraction** | ✅ Implemented | `BaseStorageService` with `LocalStorageService` provider and path traversal security. |
| **Health Telemetry** | ✅ Implemented | Real active component checks (`/api/system/health`) for Database, Storage, FFmpeg, and AI keys. |
| **FFmpeg Media Service** | ✅ Implemented | Transcoding, aspect ratio conversion (16:9 to 9:16 vertical crop guide), frame extraction. |
| **AI Generation Engine** | 🟡 Implemented (BYOK) | Gemini/OpenAI SDK support with deterministic fallback for offline/development mode. |
| **Publishing Connectors** | 🟡 Prototype / Mock | Base connector architecture with explicit `not_implemented` status responses on publishing/scheduling calls (Phase 5). |
| **Workflow Engine** | 🟡 Visual Prototype | Visual node graph and interactive simulation interface (DAG execution in Phase 6). |
| **Background Queue** | 🟡 Foundation Model | `Job` lifecycle status model (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `RETRYING`, `CANCELLED`). |

---

## 🏗️ Architecture

```
                    Browser
                       │
                       ▼
                 Next.js Frontend (apps/web)
                       │
                       ▼
                 FastAPI Backend (apps/api)
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      PostgreSQL     Redis       Storage
      (or SQLite)  (Queue)    (Local / S3 / R2)
                       │
                       ▼
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       FFmpeg       AI Engine    Platform Connectors
     (Transcode) (Gemini/OpenAI)     │ (Explicit not_implemented)
                                     ├── YouTube
                                     ├── Instagram
                                     ├── TikTok
                                     ├── LinkedIn
                                     ├── X (Twitter)
                                     └── Facebook
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
# Run backend foundation test suite
python3 apps/api/test_api.py

# Run frontend build verification
cd apps/web && npm run build
```

---

## 📄 License
Reflow is released under the **MIT License**.
