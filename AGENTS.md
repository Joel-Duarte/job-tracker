# Project Spec & Agent Instructions

## Overview
Job Tracker is a full-stack, AI-powered application designed to help users track job applications, extract information from job postings and emails, and organize recruitment workflows. The system automatically categorizes emails, assesses job fit based on candidate profiles, extracts skills, generates personalized interview guides, and maintains a structured timeline of recruitment events.

## Architecture

### Frontend
- **Framework:** Vue 3 (Composition API)
- **Tooling:** Vite
- **State Management:** Pinia
- **Routing:** Vue Router
- **UI Components:** Built with custom CSS (in `src/style.css` and scoped Vue components) and `lucide-vue-next` for iconography.
- **Key Views:**
  - `ApplicationsView`: Kanban board for tracking job applications through various stages.
  - `AssessmentsView`: Dashboard for reviewing AI job assessments.
  - `CandidateProfileView`: Management of user resumes, skills, and core competencies.
  - `JobIntakeView`: Tools to paste URLs or job descriptions for ingestion.
  - `ActionItemsView`: To-do list generated from emails and application updates.
  - `StagingView`: Review and manual resolution area for ambiguous or low-confidence extractions.
  - `AgentChatView`: Conversational AI agent interface to query application data.
  - `PastWinsView`: Archive and showcase for accepted offers, hired milestones, and celebration analytics.

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL 16 with `pgvector` and `pg_trgm` extensions.
- **ORM:** SQLAlchemy (AsyncSession / `asyncpg`).
- **AI & LLM Orchestration:** LangChain and LangGraph for workflows (e.g., job evaluation, interview guide generation).
- **Runtime Configuration:** AI providers, model bindings, OAuth client credentials, and email credentials are configured through the Settings UI and stored in PostgreSQL; deployment environment variables provide only bootstrap, infrastructure, and encryption settings.
- **Stealth Scraper:** `camofox` running as a separate service for browser automation and anti-bot bypass.
- **Key Services:**
  - `scraper.py`: Extracts job descriptions from URLs, bypassing cookie banners and "show more" toggles via Camofox Javascript evaluation.
  - `domain_resolver.py`: Multi-tier company domain extraction engine (direct URL parsing, 20+ ATS host filtering, AI domain extraction, and Clearbit autocomplete fallback) ensuring accurate `CompanyModel.domain` and favicon resolution.
  - `llm.py` / `llm_factory.py`: Abstractions over OpenAI, Anthropic, or local open-source models for various prompts (summarization, extraction, matching).
  - `intake_graph.py` & `interview_guide_graph.py`: LangGraph state machines managing complex data extraction and document generation.
  - `email_fetcher.py`: Connects to IMAP or OAuth to pull recruitment emails, deduplicating via `message_id`.
  - `evaluation_worker.py`: Background worker for processing async evaluations in a 4-stage pipeline.
  - `staleness_archiver`: Background lifecycle job that sweeps across all 4 active application stages (`APPLIED`, `ONLINE_ASSESSMENT`, `TECHNICAL_INTERVIEW`, `OFFER`) and transitions inactive applications to `ARCHIVED` (rather than `REJECTED`), leaving all terminal statuses untouched.

### Infrastructure & Development Startup
- **Local Development:** Run `./dev.sh` (or `./dev.sh --reset` to wipe and restart). This spins up `db` (PostgreSQL), `scraper` (Camofox), `backend` (FastAPI), and `frontend` (Vite dev server) using `docker-compose.dev.yml`.
- **Automatic Mock Dataset Seeding:** When `./dev.sh` or a clean database boots in development mode (`ENVIRONMENT=development` or `SEED_DEV_DATA=true`), the backend automatically populates a comprehensive, domain-tailored mock dataset:
  - 1 Active Candidate CV profile (Staff Distributed Systems Engineer)
  - 5 Applications across statuses (`APPLIED`, `TECHNICAL_INTERVIEW`, `OFFER`, `ONLINE_ASSESSMENT`, `REJECTED`) with full candidate dossiers and match analysis payloads (`Stripe`, `Linear`, `Figma`, `Datadog`, `Airbnb`)
  - 5 Job Postings with salaries, ATS skills, and markdown descriptions
  - 8 Application Timeline Events and 5 Action Items with varying deadlines/urgencies
  - 3 Staging Queue items for triage
  - 3 Intake AI evaluation tasks: 2 `COMPLETED` tasks with full match dossiers and 1 retryable `FAILED` task (with simulated network error) for testing UI retry functionality
  - 1 Active AI Provider: `Local LM studio` (`openai` provider type, `http://192.168.1.187:1234/v1`, max concurrency `1`, empty key)
  - 5 AI Task Bindings (`GLOBAL_DEFAULT`, `JOB_ASSESSMENT`, `EMAIL_EXTRACTION`, `INTERVIEW_GUIDE`, `JD_EXTRACTION`) bound to `Local LM studio`
  - 2 Connected Email Accounts
- **Dynamic Local LLM Mock Data Generator:** Run `./dev.sh --generate-mocks` (or `uv run python -m app.services.mock_generator --seed-db`) to query your local LM Studio instance and synthesize fresh, domain-accurate tech job leads, dossiers, and timeline events for testing new fields.
- **Branch Schema Resilience (Schema Auto-Sync):** On backend startup, `ensure_db_schema()` automatically verifies required PostgreSQL extensions (`vector`, `pg_trgm`), syncs tables from ORM metadata, and executes non-destructive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements for all registered model fields. Switching between feature branches with new fields never breaks existing database tables or queries.
- **Production Mode:** Run `./prod.sh` (using `docker-compose.yml` with `ENVIRONMENT=production`). All services run permanently in the background with `restart: unless-stopped`, meaning they automatically auto-start on PC/system boot whenever the Docker daemon starts and only stop when explicitly taken down (`./prod.sh --down`). Seed data is strictly skipped in production.

## Core Domains & Data Models
- **Applications:** `ApplicationModel` linked to `CompanyModel` (persisting canonical corporate `domain`). 
  - **Statuses (`AllowedApplicationStatus`):**
    - *Active Stages (4):* `APPLIED`, `ONLINE_ASSESSMENT`, `TECHNICAL_INTERVIEW`, `OFFER`.
    - *Terminal Statuses:* `HIRED`, `ARCHIVED`, `WITHDRAWN`, `REJECTED` (terminal records are immutable to automated staleness transitions).
  - **Sorting & Deadlines:** Cards in Kanban columns are chronologically sorted by upcoming scheduled interviews (`TECHNICAL_INTERVIEW`) and decision deadlines (`OFFER`).
  - **Bulk Transition Engine (`POST /api/v1/applications/bulk-transition`):** Transitions batches of matching non-terminal applications simultaneously (e.g., auto-withdrawing or archiving remaining active applications upon accepting an offer via `PostHireModal`). Bulk operations automatically generate application timeline events and dismiss associated pending `ActionItemModel` tasks.
- **Candidate Profile:** `CandidateCVModel` stores raw resumes, anonymized versions, extracted skills, domain expertise, and years of experience.
- **System Settings & Onboarding:** `SystemSettingsModel` tracks global runtime settings, feature flags (`enable_email_intake`, `enable_embeddings`, `enable_auto_cover_letter`), and onboarding completion state (`has_completed_onboarding`).
- **Email Accounts:** `EmailAccountModel` manages multi-provider email synchronization (`IMAP`, `GMAIL_OAUTH`, `MS_GRAPH_OAUTH`) with encrypted credentials, token refresh lifecycles, and mailbox folder selection.
- **Intake/Staging:** Raw leads are ingested as `StagingItemModel` or evaluated directly into `IntakeEvaluationTaskModel`. Supports bulk task management endpoints (`POST /api/v1/intake/evaluations/bulk-retry` and `POST /api/v1/intake/evaluations/bulk-delete`).
- **Emails & Events:** `ApplicationEventModel` (tied to an app) or `OtherEventModel` (general recruitment spam/newsletters).
- **Action Items:** `ActionItemModel` tracks tasks and deadlines (`PENDING`, `COMPLETED`, `DISMISSED`). An application's `has_action_required` badge strictly reflects whether active `PENDING` action items exist.
- **Vector Embeddings:** Uses `pgvector` (`ApplicationEmbeddingModel`) to allow semantic search over job applications.

---

## Agent Guidelines & Development Rules

### 1. Backend Testing Strategy (Database-First Protocol)
The PostgreSQL database is the cornerstone of the application—it holds `pgvector` vector embeddings, `pg_trgm` fuzzy text matching indexes, application states, mock datasets, AI provider task bindings, and LangGraph checkpointer pools.

**Agents MUST follow this 4-tier database resolution hierarchy for running backend tests:**

1. **Tier 1 (Automatic Testcontainers - Default):**
   ```bash
   # Run full test suite in backend/
   uv run pytest
   ```
   `conftest.py` automatically uses `testcontainers.postgres` to spin up an isolated `pgvector/pgvector:pg16` container per test session.

2. **Tier 2 (Standalone Database Container):**
   If Testcontainers cannot start (due to Docker socket permissions, rootless Docker, or ryuk limits), start the standalone database container:
   ```bash
   # Start only the PostgreSQL + pgvector container
   docker compose up -d db
   
   # Run full test suite (conftest detects port 54320 automatically)
   uv run pytest
   ```

3. **Tier 3 (Explicit Test Database URL):**
   If testing against a dedicated local or remote PostgreSQL instance:
   ```bash
   TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:54320/postgres" uv run pytest
   ```

4. **Tier 4 (Constrained Sandbox Fallback):**
   If Docker and PostgreSQL are strictly unavailable in the agent's environment:
   ```bash
   # Runs only pure non-containerized unit tests
   uv run pytest -m "not docker"
   ```
   > [!WARNING]
   > Agents falling back to Tier 4 must explicitly state in their final summary that database integration tests were skipped due to environment constraints.

### 2. Frontend & UI Testing Protocol
When creating or modifying Vue components, layouts, stores, or styling:

1. **Live Development Stack & Mock Data:**
   Run `./dev.sh` (or `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`) to start the hot-reloading development environment.
   - Frontend UI: `http://localhost:5173`
   - Backend API: `http://localhost:5173/api`
   - Auto-seeded mock dataset provides realistic test data across all views (Kanban board, AI fit dossiers, timeline events, action items).

2. **Visual & Interactive Verification:**
   - Use browser / Chrome DevTools tools (or take screenshots) to verify UI elements, layout responsiveness, modal interactions, and Pinia store reactivity against `http://localhost:5173`.
   - Check browser console logs for any Vue reactivity warnings or runtime errors.

3. **Compilation & Type Check:**
   In `frontend/`, always run:
   ```bash
   npm run build
   ```
   This compiles all Vue SFC templates and TypeScript/JavaScript to ensure zero bundling errors or broken imports.

4. **No-Docker UI Fallback:**
   If Docker is unavailable, agents must run `npm run build` for structural validation and may run `npm run dev` locally.

### 3. General Development Rules
- **Formatting & Linting:** The backend uses `ruff` (`uv run ruff check .`, `uv run ruff format .`, `uv run ruff format --check .`). Always ensure 0 lint errors and clean formatting before committing.
- **Dependency Management:** The backend uses `uv` for managing packages and running commands.
- **Asynchronous Code:** The backend relies heavily on `async/await` for database operations (`AsyncSession`), HTTP requests (`httpx`), and LLM calls. Always use non-blocking functions.
- **LangGraph State Serialization:** NEVER store non-msgpack-serializable objects (such as SQLAlchemy `AsyncSession` or database connection pools) directly in LangGraph `State` TypedDicts, as LangGraph checkpoint savers serialize state using msgpack/jsonplus. Always inject database sessions or clients via `RunnableConfig` (`config["configurable"]["db"]`) and extract them within node functions.
- **Database Connection Pools:** `psycopg_pool.AsyncConnectionPool` instances cannot be reopened once closed. In test fixtures, always instantiate fresh pool instances per test and ensure `LazyAsyncPostgresSaver` locks and event loops are dynamically bound to the current running event loop.
- **Modifying the UI:** When modifying frontend features, ensure the component's setup script (`<script setup>`) interacts with `pinia` stores (like `uiStore` or `applicationsStore`) correctly for state reactivity. Ensure Lucide icons used are imported from `lucide-vue-next`.
- **Modifying the Database:** If adding a new field to a database model, update the corresponding Pydantic schemas in the `schemas/` directory to reflect the change for both request validation and response serialization.

### 4. Telemetry & Diagnostics Tracing Protocol (Mandatory)
Every new or modified LLM call, external network request (scrapers, IMAP/OAuth email fetchers, 3rd-party APIs), background worker task, vector embedding generation, or complex programmatic workflow that can fail **MUST register traces with the diagnostics telemetry system** (`trace_events` table).

### 5. Living Spec Maintenance (AGENTS.md)
When introducing architectural changes, agents MUST keep `AGENTS.md` synchronized with the ground truth:
- **When to update:**
  - Adding or modifying database models, core enums, or table relations under `## Core Domains & Data Models`.
  - Introducing new background services or core pipeline components under `### Key Services`.
  - Adding new top-level frontend routes/views under `### Key Views`.
  - Introducing new setup, testing, or database migration commands.
- **Rules of engagement:**
  - **No Changelogs:** Never append date-stamped logs, commit notes, or "what was changed" narratives. Update the reference definitions in-place.
  - **Conciseness:** Keep descriptions brief and dense. Do not inflate token count with verbose prose.

#### A. AI & LLM Invocations (LangChain / LangGraph)
Every call to `chain.ainvoke`, `chat_model.ainvoke`, `graph.ainvoke`, or `tool.ainvoke` **MUST** pass `PostgresTracer` in its RunnableConfig callbacks:
```python
from app.services.postgres_tracer import PostgresTracer

# In standalone chains or router probes:
response = await chain.ainvoke(
    {"input": text},
    config={"callbacks": [PostgresTracer()]},
)

# In LangGraph graph invocations:
result = await intake_graph.ainvoke(
    initial_state,
    config={"configurable": {"db": db}, "callbacks": [PostgresTracer()]},
)
```

#### B. Programmatic Operations & Background Tasks (Non-LLM)
For non-LLM asynchronous code (web scraping, email sync, background worker queues, vector embeddings, scheduled tasks), wrap the operation using the `trace_operation` async context manager from `app.services.telemetry`:
```python
from app.services.telemetry import trace_operation

async def scrape_custom_portal(url: str, db: AsyncSession | None = None) -> ScrapedData:
    async with trace_operation(
        category="scraper",          # Standard categories: "llm", "scraper", "email_sync", "worker", "embedding"
        name="scrape_custom_portal",  # Descriptive snake_case task name
        inputs={"url": url},         # Inputs context (sanitized of secrets/passwords)
        db=db,                       # Optional: pass explicit session (recommended in tests)
    ) as ctx:
        # Perform work
        result = await browser.fetch(url)
        
        # Populate structured outputs upon success
        ctx["outputs"] = {"char_count": len(result.text), "title": result.title}
        
        # Optional: Explicitly mark failure without raising an exception:
        # ctx["error"] = "Custom validation failed: Missing job title"
        
        return result
```

#### C. Tracing Best Practices & Test Isolation:
1. **Categories:** Use canonical category strings (`"llm"`, `"scraper"`, `"email_sync"`, `"worker"`, `"embedding"`) so traces appear under the correct filter tabs on the `/diagnostics` dashboard.
2. **Payload Sanitization:** Never pass raw passwords, secret API keys, or full OAuth refresh tokens into `inputs` or `metadata`.
3. **Error Capture:** Unhandled exceptions raised inside `trace_operation` are automatically caught, measured for duration, recorded with full tracebacks in `trace_events`, and then re-raised cleanly.
4. **Test Fixtures:** In Pytest database tests (`test_*.py`), always pass `db=db_session` to `trace_operation` or `record_diagnostic_event` to ensure writes use the active test transaction and avoid connection concurrency locks.

---

## Pre-Commit Verification & Git Hooks

The repository uses `pre-commit` (configured in `.pre-commit-config.yaml`) with Ruff hooks for fast automated linting and formatting on every git commit.

### 1. Setting up Git Hooks (One-Time Setup)
```bash
# In backend/ or workspace root with uv
uv run --directory backend pre-commit install
```

### 2. Manual Pre-Commit Run Across All Files
```bash
uv run --directory backend pre-commit run --all-files
```

### 3. Pre-Commit Verification Checklist (Required Before Submitting)
Before committing or completing tasks, agents and developers must execute and pass `./scripts/pre-commit.sh` or run the individual checks:

#### Backend Checks (Run in `backend/`)
1. **Format Check:** `uv run ruff format --check .` (Fix with `uv run ruff format .`)
2. **Lint Check:** `uv run ruff check .` (Fix with `uv run ruff check --fix .`)
3. **Test Suite:** `uv run pytest` (Runs full test suite including database tests; use `uv run pytest -m "not docker"` only if Docker is strictly absent)

#### Frontend Checks (Run in `frontend/`)
1. **Build Check:** `npm run build` (Ensures TypeScript types, templates, and bundling compile without errors)
2. **Lint Check:** `npm run lint --if-present`

---

## Workflow Execution (For Automated Agents)
1. **Read Intent & Context:** Understand user requirements and inspect related backend models, schemas, routers, and frontend components.
2. **Draft Plan:** Create an implementation plan artifact when making multi-step or architectural changes.
3. **Database & UI Preparation:**
   - For backend tests: Ensure database access via Testcontainers (`uv run pytest`) or `docker compose up -d db`.
   - For UI changes: Spin up `./dev.sh` to test visually against seeded mock data at `http://localhost:5173`.
4. **TDD / Incremental Implementation:** Write or update tests before implementing logic; validate changes incrementally.
5. **Run Pre-Commit Verification:** Run `./scripts/pre-commit.sh` (or individual Ruff, Pytest, and npm build checks).
6. **Verify 0 Errors:** Ensure all tests pass and 0 lint/format/build errors remain before submitting.