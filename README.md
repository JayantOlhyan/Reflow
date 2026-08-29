<div align="center">
  <h1>Reflow</h1>
  <p><strong>Create once. Transform everywhere.</strong></p>
  <p>An open-source, self-hosted content operating system for creators and developers.</p>
</div>

---

## ⚡ Overview

**Reflow** is a self-hosted platform that allows creators to create, transform, repurpose, schedule, and distribute content across multiple social platforms from a single interface.

A single canonical asset—whether video, image, PDF, carousel, or text—is automatically turned into native formats for **Instagram, YouTube, TikTok, LinkedIn, X (Twitter), Facebook, and Threads**.

### 🌟 Core Philosophy
- **Self-Hosting First**: Your content, your credentials, your database.
- **BYOK (Bring Your Own Key)**: Zero SaaS markups on AI generation (Google Gemini & OpenAI).
- **Native Platform Adaptation**: Platform-specific hooks, character limits, aspect ratios, and tags.
- **Modular Connector Architecture**: Easily contribute new platform connectors.

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
       FFmpeg       AI Engine    Publishing Connectors
     (Transcode) (Gemini/OpenAI)     │
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
git clone https://github.com/your-username/reflow.git
cd reflow

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
pip install -r requirements.txt
python main.py
# Running on http://localhost:8000
```

---

## 📦 Features Matrix

| Feature | Description |
| :--- | :--- |
| **Overview Dashboard** | Real-time content volume, platform distribution donut charts, recent activity |
| **Content Library** | Multi-format asset library (Video, Carousel, Image, Text, Drafts) |
| **Repurpose Studio** | 16:9, 9:16 vertical, 1:1 square, 4:5 portrait transforms with AI platform copy |
| **Carousel Builder** | Visual slide canvas, typography presets, AI deck generation from prompts/PDF |
| **Workflow Builder** | Interactive node pipeline graph (Triggers → AI → Transform → Outputs) |
| **Calendar Scheduler** | Week and month scheduling grid with platform-colored badges |
| **Connections** | OAuth & API token manager stored locally with zero cloud telemetry |
| **System Operations** | Real-time service health, asynchronous queue inspector, retry engine, logs |

---

## 📄 License
Reflow is released under the **MIT License**.
