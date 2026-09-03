# Reflow 10-Minute Quickstart Guide

This guide gets a complete self-hosted Reflow environment running in less than 10 minutes.

---

## Prerequisites
- **Docker & Docker Compose** (v2.20+)
- **Git**
- 4GB RAM / 2 CPU cores minimum

---

## Step 1: Clone Repository
```bash
git clone https://github.com/JayantOlhyan/Reflow.git
cd Reflow
```

---

## Step 2: Configure Environment
```bash
cp .env.example .env
```
*(Optional: Open `.env` to add your `GEMINI_API_KEY` or `OPENAI_API_KEY` for AI clip discovery).*

---

## Step 3: Launch Docker Container Stack
```bash
docker compose up -d
```

---

## Step 4: Access Workspace & Complete Setup
1. Open your browser to `http://localhost:3000`.
2. Follow the 3-step setup wizard.
3. Import your first video item in the **Content Library** (`/content`).
4. Open **Repurpose Studio** (`/repurpose`) to auto-generate vertical short clips and multi-slide carousels!
