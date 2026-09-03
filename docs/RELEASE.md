# Reflow v1.0.0 Release Notes

We are thrilled to announce the official open-source release of **Reflow v1.0.0** — a self-hosted content repurposing and multi-platform distribution operating system.

---

## What is Reflow?
Reflow allows creators, media teams, and developers to transform long-form audio/video content into high-retention short clips, multi-slide PDF carousels, and burned-in subtitle videos — automatically scheduling and dispatching them across YouTube, Instagram, LinkedIn, TikTok, and X.

---

## Key Highlights of v1.0.0

- **Self-Hosted Infrastructure:** 100% open-source Docker deployment (`docker compose up -d`) with PostgreSQL, Redis, and local/S3 file storage.
- **FFmpeg Media Core:** Multi-resolution video transcoding, thumbnail generation, and custom caption burn-in without third-party rendering fees.
- **AI Content Intelligence:** Multi-provider support (Gemini, OpenAI) for automated transcript summarization, viral clip scoring, and hook recommendations.
- **Multi-Platform Publishing:** Batch scheduling, automated OAuth token refresh, state aggregation, and 1-click retry for failed dispatches.
- **Ecosystem & Public API:** Full REST API (`/api/v1`) with API key scope permissions, Python SDK (`reflow-sdk`), TypeScript SDK (`@reflow/sdk`), and plugin extensibility.
- **Production Hardened:** Bounded concurrency controls, SSRF protections, system health telemetry, structured logging, and non-root Docker execution.

---

## Quickstart
```bash
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow
cp .env.example .env
docker compose up -d
```
Visit `http://localhost:3000` to launch the Reflow workspace.

---

## Documentation Links
- [Quickstart Guide](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/QUICKSTART.md)
- [Production Deployment Guide](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/DEPLOYMENT.md)
- [Troubleshooting Guide](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/TROUBLESHOOTING.md)
- [Security Policy](file:///Users/jayantolhyan/Desktop/my%20projects/open%20source%20/Reflow/docs/SECURITY.md)
