# Reflow — Self-Hosted Open-Source Content Repurposing & Distribution System

<p align="center">
  <img src="docs/assets/reflow-banner.png" alt="Reflow v1.0.0 Banner" width="800" onerror="this.style.display='none'"/>
</p>

Reflow is an open-source, self-hosted content operating system that transforms long-form video and audio content into short-form vertical clips, multi-slide PDF carousels, and burned-in subtitle videos — automatically scheduling and publishing them across YouTube, Instagram, LinkedIn, TikTok, and X.

---

## Key Features

- 🎥 **FFmpeg Media Core:** Auto-transcoding, multi-resolution variant rendering, audio extraction, and subtitle burn-in.
- 🧠 **AI Content Intelligence:** Automated transcript summarization, viral clip scoring, and hook recommendations powered by Gemini or OpenAI.
- 🎨 **Carousel Studio:** Multi-slide deck creation, visual element positioning, and vector PDF export rendering.
- 📱 **Multi-Platform Publishing:** Single-click and scheduled dispatches to YouTube, Instagram, LinkedIn, TikTok, and X with automatic token refresh.
- 🛡️ **Governance & Compliance:** Pre-publish rule audits, brand voice enforcement, watermark policies, and review sign-offs.
- ⚡ **Resource Bounded:** Queue backpressure controls, disk quota protection, FFmpeg thread bounds (`-threads 2`), and AI request caching.
- 🔌 **Ecosystem & Public API:** Open REST API (`/api/v1`), Python SDK (`reflow-sdk`), TypeScript SDK (`@reflow/sdk`), and plugin extensibility.

---

## ⚡ 10-Minute Quickstart

### Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/) (v2.20+)
- Git

### 1. Clone Repository & Configure Environment
```bash
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow
cp .env.example .env
```

### 2. Launch Services
```bash
docker compose up -d
```

### 3. Open Web UI
Open your browser to `http://localhost:3000` to complete the 3-step setup wizard and start repurposing media!

---

## 🏛️ System Architecture

```
                                [ Next.js Web UI ]
                                   (Port 3000)
                                        │
                                        ▼
                               [ FastAPI Backend ] ◄────► [ PostgreSQL 16 ]
                                   (Port 8000)             (Database)
                                        │
                                        ▼
                                [ Redis 7 Queue ]
                                        │
                      ┌─────────────────┴─────────────────┐
                      ▼                                   ▼
             [ Media Worker ]                    [ Scheduler Worker ]
            (FFmpeg Transcoding)                 (Publication Dispatch)
```

---

## 📖 Documentation Directory

- 🚀 [Quickstart Guide](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/QUICKSTART.md)
- ⚙️ [Production Deployment Guide](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/DEPLOYMENT.md)
- 🛠️ [Troubleshooting Guide](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/TROUBLESHOOTING.md)
- 🛡️ [Security Policy & Controls](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/SECURITY.md)
- 🔌 [Plugin Development Guide](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/PLUGIN-DEVELOPMENT.md)
- 📜 [Third-Party Licenses](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/THIRD-PARTY-LICENSES.md)

---

## 📄 License
Reflow is released under the [MIT License](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/LICENSE).
