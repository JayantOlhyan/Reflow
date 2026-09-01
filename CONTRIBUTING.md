# Contributing to Reflow

Thank you for your interest in contributing to **Reflow**, the open-source self-hosted content operating system!

---

## 1. Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- FFmpeg and FFprobe binaries installed on system PATH
- Docker & Docker Compose (Optional for local containerized development)

### Local Environment Quickstart

1. **Clone & Environment Setup**:
   ```bash
   git clone https://github.com/JayantOlhyan/Reflow.git
   cd Reflow
   cp .env.example .env
   ```

2. **Backend Setup (`apps/api`)**:
   ```bash
   cd apps/api
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Database Migration & Backend Launch**:
   ```bash
   # Execute database migrations
   alembic upgrade head

   # Start backend API server
   uvicorn main:app --reload --port 8000
   ```

4. **Frontend Setup (`apps/web`)**:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

---

## 2. Code Architecture & Rules

- **Strict Zero-Fake-Data Rule**: Never introduce fake metrics, mock values, or dummy zero fallbacks in production endpoints.
- **Async DB Sessions**: Use SQLAlchemy `AsyncSession` with asyncpg/aiosqlite drivers.
- **FFmpeg Safety**: Never use `shell=True` or shell string concatenation for FFmpeg calls. Use list-based subprocess arrays.
- **Migration Rules**: Any change altering database entities MUST be accompanied by an Alembic migration script under `apps/api/alembic/versions/`.

---

## 3. Testing Guidelines

Run the full backend test suite before submitting a Pull Request:
```bash
cd apps/api
pytest -v
```

Run frontend production build verification:
```bash
cd apps/web
npm run build
```

---

## 4. Pull Request Checklist

Before submitting your PR:
- [ ] Code follows existing formatting and architectural conventions.
- [ ] All pytest tests pass cleanly (`pytest`).
- [ ] Frontend builds without TypeScript or Next.js errors (`npm run build`).
- [ ] New database alterations include an Alembic migration.
- [ ] No hardcoded secrets or environment assumptions exist.
