# Job Tracker Backend Service

The **Job Tracker Backend** is a high-performance, asynchronous REST API and AI workflow engine built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL 16 (pgvector & pg_trgm)**, and **LangGraph**.

---

## 🛠️ Prerequisites & Environment Setup

- **Python:** `3.12+`
- **Package Manager:** [`uv`](https://docs.astral.sh/uv/) (Ultra-fast Python package installer and resolver)
- **Database:** PostgreSQL 16+ with `pgvector` and `pg_trgm` extensions enabled (or Docker to run via Testcontainers/Docker Compose)

### 1. Install Dependencies
In the `backend/` directory, install project dependencies and development tools using `uv`:

```bash
cd backend
uv sync
```

### 2. Environment Configuration
Create a `.env` file in `backend/` or rely on the root `.env`:

```env
# Database Settings
POSTGRES_HOST=localhost
POSTGRES_PORT=54320
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres

# Server & Security
ENVIRONMENT=development
SEED_DEV_DATA=true
SECRET_KEY=development-only-secret-key
ADMIN_SECRET=dev-admin-secret
PUBLIC_API_URL=http://localhost:8000
PUBLIC_FRONTEND_URL=http://localhost:5173

# Camofox Scraper Integration
CAMOUFOX_ENDPOINT=http://localhost:9377
```

---

## 🚀 Running the Development Server

### Option A: Standalone Python Server (Direct via `uv`)
Make sure PostgreSQL is running on port 54320 (e.g. via `docker compose up -d db` from the repository root), then start the hot-reloading FastAPI server:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs (Swagger UI): `http://localhost:8000/docs`
- ReDoc API Documentation: `http://localhost:8000/redoc`
- Health Check Endpoint: `http://localhost:8000/health`

### Option B: Full Dev Stack via Docker Compose
From the repository root, start all microservices (PostgreSQL, Camofox Scraper, Backend, and Frontend):

```bash
./dev.sh
```

---

## 🗄️ Database Schema Migrations (Alembic)

Database schema alterations, indexes, and new tables MUST be managed through Alembic migrations.

### Apply Latest Migrations
```bash
uv run alembic upgrade head
```

### Create a New Migration Revision
```bash
uv run alembic revision --autogenerate -m "add_column_to_applications"
# OR manual empty revision:
uv run alembic revision -m "create_new_feature_table"
```

### Inspect Migration History & Heads
```bash
uv run alembic history
uv run alembic heads
```

> [!IMPORTANT]
> Never execute ad-hoc raw `ALTER TABLE` statements inside runtime bootstrap code. Always create clean, reversible Alembic migration files under `backend/alembic/versions/`.

---

## 🧪 4-Tier Backend Testing Protocol

The test suite relies heavily on PostgreSQL features (`pgvector` for 768-dim embeddings, `pg_trgm` for trigram fuzzy matching, and LangGraph checkpointer pools). Agents and developers MUST follow the 4-tier database resolution hierarchy:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      4-TIER DATABASE TEST RESOLUTION                   │
│                                                                        │
│  Tier 1: Automatic Testcontainers (Default)                            │
│          uv run pytest                                                 │
│          Spins up an isolated pgvector/pgvector:pg16 container.        │
│                                                                        │
│  Tier 2: Standalone Database Container (If Testcontainers restricted)  │
│          docker compose up -d db                                       │
│          uv run pytest                                                 │
│                                                                        │
│  Tier 3: Explicit Test Database URL (Custom / Remote Postgres)         │
│          TEST_DATABASE_URL="postgresql+asyncpg://..." uv run pytest    │
│                                                                        │
│  Tier 4: Non-Docker Sandbox Fallback (Pure unit tests only)            │
│          uv run pytest -m "not docker"                                 │
└────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Automatic Testcontainers (Default)
```bash
uv run pytest
```
`conftest.py` automatically spins up a clean, isolated `pgvector/pgvector:pg16` container per test session.

### Tier 2: Standalone Database Container
If running in an environment with container socket limits or rootless Docker:
```bash
# 1. Start the database container
docker compose up -d db

# 2. Run test suite (conftest automatically connects to localhost:54320)
uv run pytest
```

### Tier 3: Explicit Test Database URL
```bash
TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:54320/postgres" uv run pytest
```

### Tier 4: Constrained Non-Docker Fallback
If Docker is strictly unavailable in the execution environment:
```bash
uv run pytest -m "not docker"
```

---

## 🎨 Code Quality, Formatting & Linting

We enforce strict formatting and linting standards using [Ruff](https://astral.sh/ruff).

### Format Code
```bash
uv run ruff format .
```

### Lint & Auto-Fix Code
```bash
uv run ruff check --fix .
```

### Verification Checks (Pre-Commit)
```bash
uv run ruff format --check .
uv run ruff check .
```

---

## 📊 Telemetry & Diagnostics Tracing

Every LLM call and programmatic workflow (scraping, email sync, embeddings, background worker tasks) must register telemetry in the `trace_events` table.

### Tracing AI & LangChain Invocations
Pass `PostgresTracer` in `RunnableConfig` callbacks:
```python
from app.services.postgres_tracer import PostgresTracer

response = await chain.ainvoke(
    {"input": prompt_text},
    config={"callbacks": [PostgresTracer()]},
)
```

### Tracing Programmatic Tasks (Scraper, Email Sync, Workers)
Wrap async code blocks with `trace_operation`:
```python
from app.services.telemetry import trace_operation


async def sync_mailbox(account_id: int, db=None):
    async with trace_operation(
        category="email_sync",
        name="sync_mailbox",
        inputs={"account_id": account_id},
        db=db,
    ) as ctx:
        items = await fetch_messages(account_id)
        ctx["outputs"] = {"count": len(items)}
        return items
```

---

## 📁 Directory Structure

```
backend/
├── alembic/                  # Alembic database migration scripts
├── app/
│   ├── core/                 # Config, DB connection pools, LLM factory, Prompts
│   ├── models/               # SQLAlchemy Declarative Models
│   │   ├── applications.py   # Applications, Companies, Events, ActionItems, Embeddings
│   │   ├── candidate_profile.py # Candidate CV, Resumes, Extracted Skills
│   │   ├── diagnostics.py    # TraceEventModel (Telemetry)
│   │   ├── email_accounts.py # Multi-Provider Email Account configs
│   │   └── interview_session.py # Mock Interview simulation sessions
│   ├── routers/              # API REST Endpoints (/api/v1)
│   ├── schemas/              # Pydantic v2 Request/Response validation models
│   ├── services/             # Graphs, Scrapers, Evaluators, and Services
│   │   ├── intake_graph.py   # LangGraph Lead & Email Intake pipeline
│   │   ├── interview_guide_graph.py # LangGraph Interview Prep Guide generator
│   │   ├── interview_simulator_service.py # Real-time Mock Interview Simulator
│   │   ├── scraper.py        # Camofox Browser Automation wrapper
│   │   ├── email_fetcher.py  # IMAP & OAuth Mailbox synchronizer
│   │   └── telemetry.py      # Telemetry tracing helpers
│   └── main.py               # FastAPI application entrypoint & lifespan
└── pyproject.toml            # Project dependencies and tool configs
```
