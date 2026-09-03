# Third-Party Open Source License Audit

Reflow is distributed under the **MIT License**. The following third-party software packages and dependencies are utilized:

---

## 1. Backend Python Dependencies (`apps/api/requirements.txt`)

| Package | Version | License | Usage |
|---|---|---|---|
| FastAPI | `^0.109.0` | MIT | Asynchronous Web Framework |
| Uvicorn | `^0.27.0` | BSD-3-Clause | ASGI Web Server |
| SQLAlchemy | `^2.0.25` | MIT | SQL ORM & Database Driver |
| Pydantic | `^2.6.0` | MIT | Schema Validation |
| Redis | `^5.0.1` | MIT | Queue & Cache Client |
| Asyncpg | `^0.29.0` | Apache-2.0 | Asynchronous PostgreSQL Client |
| HTTPX | `^0.26.0` | BSD-3-Clause | Asynchronous HTTP Client |
| Pytest | `^8.0.0` | MIT | Automated Testing Suite |

---

## 2. Frontend Node.js Dependencies (`apps/web/package.json`)

| Package | Version | License | Usage |
|---|---|---|---|
| Next.js | `16.3.3` | MIT | React Application Framework |
| React | `19.2.8` | MIT | UI Component Rendering |
| TailwindCSS | `^4.0.0` | MIT | Utility-first CSS Styling |
| Lucide React | `^1.37.0` | ISC | System UI Icons |
| Framer Motion | `^13.1.1` | MIT | UI Animations |

---

## 3. Infrastructure & Binary Components

| Component | Version | License | Usage |
|---|---|---|---|
| FFmpeg | 6.x / 7.x | LGPL v2.1+ / GPL v2+ | Video & Audio Processing |
| PostgreSQL | 16-alpine | PostgreSQL License | Relational Database |
| Redis | 7-alpine | BSD-3-Clause | Memory Data Store & Queue |
