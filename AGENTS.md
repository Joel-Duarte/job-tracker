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

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL 16 with `pgvector` and `pg_trgm` extensions.
- **ORM:** SQLAlchemy (AsyncSession / `asyncpg`).
- **AI & LLM Orchestration:** LangChain and LangGraph for workflows (e.g., job evaluation, interview guide generation).
- **Stealth Scraper:** `camofox` running as a separate service for browser automation and anti-bot bypass.
- **Key Services:**
  - `scraper.py`: Extracts job descriptions from URLs, bypassing cookie banners and "show more" toggles via Camofox Javascript evaluation.
  - `llm.py` / `llm_factory.py`: Abstractions over OpenAI, Anthropic, or local open-source models for various prompts (summarization, extraction, matching).
  - `intake_graph.py` & `interview_guide_graph.py`: LangGraph state machines managing complex data extraction and document generation.
  - `email_fetcher.py`: Connects to IMAP or OAuth to pull recruitment emails, deduplicating via `message_id`.
  - `evaluation_worker.py`: Background worker for processing async evaluations in a 4-stage pipeline.

### Infrastructure & Development Startup
- **Local Development:** Run `./dev.sh` (or `./dev.sh --reset` to wipe and restart). This spins up `db` (PostgreSQL), `scraper` (Camofox), `backend` (FastAPI), and `frontend` (Vite dev server) using `docker-compose.dev.yml`.
- **Automatic Mock Dataset Seeding:** When `./dev.sh` or a clean database boots in development mode (`ENVIRONMENT=development` or `SEED_DEV_DATA=true`), the backend automatically populates a comprehensive, domain-tailored mock dataset:
  - 1 Active Candidate CV profile (Staff Distributed Systems Engineer)
  - 5 Applications across statuses (`APPLIED`, `TECHNICAL_INTERVIEW`, `OFFER`, `ONLINE_ASSESSMENT`, `REJECTED`) with full candidate dossiers and match analysis payloads (`Stripe`, `Linear`, `Figma`, `Datadog`, `Airbnb`)
  - 5 Job Postings with salaries, ATS skills, and markdown descriptions
  - 8 Application Timeline Events and 5 Action Items with varying deadlines/urgencies
  - 3 Staging Queue items for triage and 3 Intake AI evaluation tasks
  - 3 AI Providers / Task Bindings and 2 Email accounts
- **Production Mode:** Run `./prod.sh` (using `docker-compose.yml` with `ENVIRONMENT=production`). Seed data is strictly skipped in production.

## Core Domains & Data Models
- **Applications:** `ApplicationModel` linked to `CompanyModel`. Tracks status (`APPLIED`, `TECHNICAL_INTERVIEW`, `OFFER`, `REJECTED`, `ASSESSMENT`), dates, and linked timeline events.
- **Candidate Profile:** `CandidateCVModel` stores raw resumes, anonymized versions, extracted skills, domain expertise, and years of experience.
- **Intake/Staging:** Raw leads are ingested as `StagingItemModel` or evaluated directly into `IntakeEvaluationTaskModel`.
- **Emails & Events:** `ApplicationEventModel` (tied to an app) or `OtherEventModel` (general recruitment spam/newsletters).
- **Action Items:** `ActionItemModel` tracks deadlines and next steps (e.g., reply to recruiter, interview scheduled).
- **Vector Embeddings:** Uses `pgvector` (`ApplicationEmbeddingModel`) to allow semantic search over job applications.

## Agent Guidelines & Development Rules
- **Formatting & Linting:** The backend uses `ruff` for formatting and linting (`uv run ruff check .`, `uv run ruff format .`, `uv run ruff format --check .`). Always ensure 0 lint errors and clean formatting before committing.
- **Dependency Management:** The backend uses `uv` for managing packages and running commands.
- **Testing (Fast Unit Tests vs Container Tests):**
  - **Prefer Non-Docker Unit Tests:** Agents and developers should prefer running fast unit tests: `uv run pytest -m "not docker"`. This skips container startup and validates business logic, extractors, schemas, scrapers, and LLM utilities in seconds without requiring Docker daemon permissions.
  - **Database Integration Tests:** Tests requiring database access are auto-marked with `@pytest.mark.docker`. When run (`uv run pytest`), `conftest.py` will attempt Testcontainers, or fall back to an active `./dev.sh` Postgres instance (`localhost:54320`) or `TEST_DATABASE_URL`. If Docker is not available in the agent environment, tests gracefully skip instead of crashing.
  - Full containerized integration test coverage is always verified automatically on GitHub Actions CI.
- **Asynchronous Code:** The backend relies heavily on `async/await` for database operations (`AsyncSession`), HTTP requests (`httpx`), and LLM calls. Always use non-blocking functions.
- **LangGraph State Serialization:** NEVER store non-msgpack-serializable objects (such as SQLAlchemy `AsyncSession` or database connection pools) directly in LangGraph `State` TypedDicts, as LangGraph checkpoint savers serialize state using msgpack/jsonplus. Always inject database sessions or clients via `RunnableConfig` (`config["configurable"]["db"]`) and extract them within node functions.
- **Database Connection Pools:** `psycopg_pool.AsyncConnectionPool` instances cannot be reopened once closed. In test fixtures, always instantiate fresh pool instances per test and ensure `LazyAsyncPostgresSaver` locks and event loops are dynamically bound to the current running event loop.
- **State Changes:** After every action that modifies code state, verify the outcome using read operations (e.g., `cat` or `grep`).
- **Modifying the UI:** When modifying frontend features, ensure the component's setup script (`<script setup>`) interacts with `pinia` stores (like `uiStore` or `applicationsStore`) correctly for state reactivity. Ensure Lucide icons used are imported from `lucide-vue-next`.
- **Modifying the Database:** If adding a new field to a database model, update the corresponding Pydantic schemas in the `schemas/` directory to reflect the change for both request validation and response serialization.

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
Before committing or submitting changes, agents and developers must execute and pass the following checklist:

#### Backend Checks (Run in `backend/` or via `./scripts/pre-commit.sh`)
1. **Format Check:** `uv run ruff format --check .` (Fix with `uv run ruff format .`)
2. **Lint Check:** `uv run ruff check .` (Fix with `uv run ruff check --fix .`)
3. **Test Suite:** `uv run pytest -m "not docker"` (or `uv run pytest` if Docker/Postgres is available)

#### Frontend Checks (Run in `frontend/`)
1. **Build Check:** `npm run build` (Ensures TypeScript types and templates compile without errors)
2. **Lint Check:** `npm run lint --if-present`

---

## Workflow Execution (For Automated Agents)
1. Read the user's intent.
2. Search through models, schemas, routers, and services in the backend.
3. Search through views, stores, and components in the frontend.
4. Draft a plan using `set_plan` or implementation plan artifact.
5. Write or modify tests before implementing core logic (TDD).
6. Implement the logic incrementally, validating at each step.
7. Run the **Pre-Commit Verification Checklist** (Ruff format check, Ruff lint check, pytest, and frontend build).
8. Verify all checks pass with 0 errors before committing or completing the task.