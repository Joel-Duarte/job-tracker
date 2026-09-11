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
  - `ApplicationsView`: Kanban board for tracking job applications through active stages, with date filtering, drag-and-drop action dock, and an integrated "Past Wins" showcase for accepted offers and hired milestones.
  - `AssessmentsView`: Dashboard for reviewing AI job fit assessments, skill breakdowns, and gap dossiers.
  - `QueueView`: Central asynchronous AI task queue (`/queue`) with live stage progress, bulk retry/cancellation, and interactive result inspection.
  - `AnalyticsView`: Analytics hub featuring funnel conversion metrics and the "Role Alignment & CV Tuning" career intelligence suite.
  - `CandidateProfileView`: Master management of user resumes, skills, spoken languages, and core competencies (accessible via `/settings?tab=profile`).
  - `CompaniesView`: Directory of employer entities, multi-application history, candidate ratings/notes, and live company intelligence with contextual `CompanyDetailDrawer`.
  - `ActionItemsView`: High-priority to-do hub generated automatically from recruitment emails and application updates.
  - `StagingView`: Triage and manual 2-step resolution area for ambiguous or low-confidence email extractions.
  - `AgentChatView`: Unified conversational assistant and live interactive mock interview simulation suite supporting multi-turn drill downs, multiple-choice challenges, voice transcription, debrief scorecards, and session continuation across practice formats.
  - `DiagnosticsView`: Deep system telemetry dashboard (`/diagnostics`) tracking execution latency, trace spans, error rates, token consumption, and dollar savings.

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL 16 with `pgvector` and `pg_trgm` extensions.
- **ORM:** SQLAlchemy (AsyncSession / `asyncpg`).
- **Database Migrations:** Alembic with async PostgreSQL engine (`backend/alembic.ini`, `backend/alembic/env.py`).
- **AI & LLM Orchestration:** LangChain and LangGraph for workflows (e.g., job evaluation, interview guide generation).
- **Runtime Configuration:** AI providers, model bindings, OAuth client credentials, and email credentials are configured through the Settings UI and stored in PostgreSQL; deployment environment variables provide only bootstrap, infrastructure, and encryption settings.
- **Stealth Scraper:** `camofox` running as a separate service for browser automation and anti-bot bypass.
- **Key Services:**
  - `scraper.py`: Extracts job descriptions from URLs, bypassing cookie banners and "show more" toggles via Camofox Javascript evaluation.
  - `domain_resolver.py`: Multi-tier company domain extraction engine (direct URL parsing, 20+ ATS host filtering, AI domain extraction, and Clearbit autocomplete fallback) ensuring accurate `CompanyModel.domain` and favicon resolution.
  - `llm.py` / `llm_factory.py`: Abstractions over OpenAI, Anthropic, or local open-source models for various prompts (job spec extraction, email categorization, candidate assessment, zero-hallucination cover letter, and application form Q&A generation).
  - `intake_graph.py` & `interview_guide_graph.py`: LangGraph state machines managing complex data extraction and document generation.
  - `interview_simulator_service.py`: Interactive role-playing mock interview simulator supporting multiple question formats (`TEXT_CONVERSATIONAL`, `MULTIPLE_CHOICE`, `HYBRID`), interviewer personas (`TECHNICAL_BAR_RAISER`, `HIRING_MANAGER`, `BEHAVIORAL_CULTURE`, `SUPPORTIVE_COACH`), adaptive local (unlimited)/cloud (120s) timeouts, real-time STAR evaluation, and post-session debrief scorecards saved to application notes and timeline events.
  - `email_fetcher.py`: Connects to IMAP or OAuth to pull recruitment emails, deduplicating via `message_id`.
  - `evaluation_worker.py`: Background worker for processing async evaluations in a 4-stage pipeline, including `APPLICATION_QA` and `COVER_LETTER` generation tasks.
  - `staleness_archiver`: Background lifecycle job that sweeps across all 4 active application stages (`APPLIED`, `ONLINE_ASSESSMENT`, `TECHNICAL_INTERVIEW`, `OFFER`) and transitions inactive applications to `ARCHIVED` (rather than `REJECTED`), leaving all terminal statuses untouched.
  - `pricing_service.py`: Computes token consumption, dollar costs, and local LLM cloud savings using configurable model rates and extraction from diagnostic telemetry traces.
  - `agent_tools.py`: Comprehensive LangChain tool execution suite powering `AgentChatView`, providing 23+ database query, vector search, status mutation, and async queueing tools spanning pipeline tracking, company intelligence dossiers, mock interview practice, cover letter drafting, application form Q&A, role alignment career roadmaps, and live web research.
  - `benchmark_service.py`: Hardware-aware LLM capacity probe service verifying single/dual-stream throughput, n-gram degenerative loop detection, and grounded skill checks with optimal concurrency recommendations.
  - `provider_lifecycle_service.py`: VRAM and engine sleep/unload lifecycle adapter supporting LM Studio, Ollama, vLLM, and SGLang.
  - `web_limiter.py`: Shared token bucket rate limiter and provider-specific concurrency ceilings (DDGS, SearXNG, Camofox).
  - `web_search.py`: Multi-provider search engine supporting DuckDuckGo (`ddgs`) and self-hosted `SearXNG` with automatic health fallback, token-bucket throttling, and Camofox webpage scraping.
  - `company_research.py`: Domain-anchored query builder and AI relevance guardrail engine synthesizing corporate mission, tech culture, and public ratings with entity caching on `CompanyModel`.
  - `company_resolver.py`: Multi-tier employer deduplication engine utilizing exact normalized names, canonical domains, and `pg_trgm` fuzzy similarity matching (>0.85).

### Infrastructure & Development Startup
- **Unified Daily-Driver CLI Launcher (`jt`):** Run `./jt` on Linux/macOS or `jt.cmd` / `jt` on Windows. Includes `jt update` (automatically saves a pre-update PostgreSQL database snapshot to `backups/` before pulling and migrating) and standalone `jt backup`.
- **Local Development:** Run `./jt dev` (or `./jt dev --reset` to wipe and restart). This spins up `db` (PostgreSQL), `scraper` (Camofox), `backend` (FastAPI), and `frontend` (Vite dev server) using `docker-compose.dev.yml`.
- **Automatic Mock Dataset Seeding:** When `./jt dev` or a clean database boots in development mode (`ENVIRONMENT=development` or `SEED_DEV_DATA=true`), the backend automatically populates a comprehensive, domain-tailored mock dataset:
  - 1 Active Candidate CV profile (Staff Distributed Systems Engineer)
  - 5 Applications across statuses (`APPLIED`, `TECHNICAL_INTERVIEW`, `OFFER`, `ONLINE_ASSESSMENT`, `REJECTED`) with full candidate dossiers and match analysis payloads (`Stripe`, `Linear`, `Figma`, `Datadog`, `Airbnb`)
  - 5 Job Postings with salaries, ATS skills, and markdown descriptions
  - 8 Application Timeline Events and 5 Action Items with varying deadlines/urgencies
  - 3 Staging Queue items for triage
  - 3 Intake AI evaluation tasks: 2 `COMPLETED` tasks with full match dossiers and 1 retryable `FAILED` task (with simulated network error) for testing UI retry functionality
  - 1 Active AI Provider: `Local LM studio` (`openai` provider type, `http://192.168.1.187:1234/v1`, max concurrency `2`, auto_release_vram_minutes `10`, empty key)
  - 5 AI Task Bindings (`GLOBAL_DEFAULT`, `JOB_ASSESSMENT`, `EMAIL_EXTRACTION`, `INTERVIEW_GUIDE`, `JD_EXTRACTION`) bound to `Local LM studio`
  - 2 Connected Email Accounts
- **Dynamic Local LLM Mock Data Generator:** Run `./jt seed` (or `uv run python -m app.services.mock_generator --seed-db`) to query your local LM Studio instance and synthesize fresh, domain-accurate tech job leads, dossiers, and timeline events for testing new fields.
- **Production Mode:** Run `./jt` or `./jt start` (using `docker-compose.yml` with `ENVIRONMENT=production`). All services run permanently in the background with `restart: unless-stopped`, meaning they automatically auto-start on PC/system boot whenever the Docker daemon starts and only stop when explicitly taken down (`./jt stop`). Seed data is strictly skipped in production.

## Core Domains & Data Models
- **AI Providers & Capacity Lifecycle:** `AIProviderModel` manages LLM providers, engine classification (`engine_type`: `auto`, `lmstudio`, `ollama`, `vllm`, `sglang`, `cloud`), model bindings, cost rates, concurrency ceilings (`max_concurrency`), priority preemption with interactive headroom, targeted idle VRAM unloading (`auto_release_vram_minutes`), and hardware benchmark verification.
- **Companies & Employer Directory:** `CompanyModel` manages employer entities, corporate domain, candidate notes (`notes`), pros (`pros` JSONB), red flags (`red_flags` JSONB), and live synthesized intelligence (`company_research` JSONB, `researched_at`). Supported by CRUD (including `POST /api/v1/companies` with optional immediate web intelligence queueing), explicit company deletion with optional linked-application deletion, live web research refresh, and deduplication merge endpoints (`POST /api/v1/companies/merge`).
- **Applications:** `ApplicationModel` linked to `CompanyModel` (persisting canonical corporate `domain`). Persists cover letters (`cover_letter_text`, `cover_letter_status`), application form Q&A pairs (`application_questions` JSONB), and durable assessment identity (`is_assessment`) so archived assessment dossiers remain independent of queue task status.
  - **Statuses (`AllowedApplicationStatus`):**
    - *Active Stages (4):* `APPLIED`, `ONLINE_ASSESSMENT`, `TECHNICAL_INTERVIEW`, `OFFER`.
    - *Terminal Statuses:* `HIRED`, `ARCHIVED`, `WITHDRAWN`, `REJECTED` (terminal records are immutable to automated staleness transitions).
  - **Sorting & Deadlines:** Cards in Kanban columns are chronologically sorted by upcoming scheduled interviews (`TECHNICAL_INTERVIEW`) and decision deadlines (`OFFER`).
  - **Bulk Transition Engine (`POST /api/v1/applications/bulk-transition`):** Transitions batches of matching non-terminal applications simultaneously (e.g., auto-withdrawing or archiving remaining active applications upon accepting an offer via `PostHireModal`). Bulk operations automatically generate application timeline events and dismiss associated pending `ActionItemModel` tasks.
- **Candidate Profile:** `CandidateCVModel` stores raw resumes, anonymized versions, extracted skills, domain expertise, spoken languages with proficiencies (`spoken_languages`), and years of experience.
- **Mock Interview Simulations:** `InterviewSessionModel` manages multi-turn interview simulations optionally tied to target job applications. Stores per-turn challenge and candidate response transcripts (`turns_data`), question mode (`question_mode`), overall readiness rating (`readiness_rating`), overall score (`overall_score`), and debrief summary feedback (`summary_feedback`).
- **System Settings & Onboarding:** `SystemSettingsModel` tracks global runtime settings, feature flags (`enable_email_intake`, `enable_embeddings`, `enable_web_search`, `enable_auto_cover_letter`), search engine configuration (`search_provider`, `searxng_url`), and onboarding completion state (`has_completed_onboarding`).
- **Email Accounts:** `EmailAccountModel` manages multi-provider email synchronization (`IMAP`, `GMAIL_OAUTH`, `MS_GRAPH_OAUTH`) with encrypted credentials, token refresh lifecycles, and mailbox folder selection.
- **Intake/Staging:** Raw leads are ingested as `StagingItemModel` or evaluated directly into `IntakeEvaluationTaskModel`. Supports bulk task management endpoints (`POST /api/v1/intake/evaluations/bulk-retry` and `POST /api/v1/intake/evaluations/bulk-delete`).
- **Emails & Events:** `ApplicationEventModel` (tied to an app) or `OtherEventModel` (general recruitment spam/newsletters).
- **Action Items:** `ActionItemModel` tracks tasks and deadlines (`PENDING`, `COMPLETED`, `DISMISSED`). An application's `has_action_required` badge strictly reflects whether active `PENDING` action items exist.
- **Role Alignment Dossiers:** `RoleAlignmentDossierModel` stores structured AI career intelligence dossiers (executive positioning, tailored bullet rewrites, technical interview talking points, skill roadmaps) linked to `CandidateCVModel` and `role_track`.
- **Vector Embeddings:** Uses `pgvector` (`ApplicationEmbeddingModel`) to allow semantic search over job applications.

---

## Agent Guidelines & Development Rules

> [!IMPORTANT]
> **No Preemptive Builds or Tests:** Never run `uv run pytest`, `npm run build`, or start dev servers upon initial startup, during task planning, or while answering investigatory questions. For code exploration and search, use `ripwire` or `graphify`. Run test suites and build commands **strictly after modifying code** to verify your changes.

### 1. Backend Testing Protocol (Post-Edit Verification Only)
When executing backend tests to verify code changes (during TDD or before completing a task), agents MUST follow this 4-tier database resolution hierarchy:

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

### 2. Frontend & UI Testing Protocol (Post-Edit Verification Only)
When creating or modifying Vue components, layouts, stores, or styling:

1. **Live Development Stack & Mock Data:**
   Run `./jt dev` (or `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`) to start the hot-reloading development environment when live visual testing is required.
   - Frontend UI: `http://localhost:5173`
   - Backend API: `http://localhost:5173/api`
   - Auto-seeded mock dataset provides realistic test data across all views (Kanban board, AI fit dossiers, timeline events, action items).

2. **Visual & Interactive Verification:**
   - Use browser / Chrome DevTools tools (or take screenshots) to verify UI elements, layout responsiveness, modal interactions, and Pinia store reactivity against `http://localhost:5173`.
   - Check browser console logs for any Vue reactivity warnings or runtime errors.

3. **Compilation & Type Check (Post-Edit Only):**
   Only after modifying frontend code, in `frontend/`, run:
   ```bash
   npm run build
   ```
   This compiles all Vue SFC templates and TypeScript/JavaScript to ensure zero bundling errors or broken imports. Do NOT run this if no frontend changes were made.

4. **No-Docker UI Fallback:**
   If Docker is unavailable, agents run `npm run build` after editing for structural validation and may run `npm run dev` locally.

### 3. General Development Rules
- **Formatting & Linting:** The backend uses `ruff` (`uv run ruff check .`, `uv run ruff format .`, `uv run ruff format --check .`). Always ensure 0 lint errors and clean formatting before committing.
- **Dependency Management:** The backend uses `uv` for managing packages and running commands.
- **Asynchronous Code:** The backend relies heavily on `async/await` for database operations (`AsyncSession`), HTTP requests (`httpx`), and LLM calls. Always use non-blocking functions.
- **LangGraph State Serialization:** NEVER store non-msgpack-serializable objects (such as SQLAlchemy `AsyncSession` or database connection pools) directly in LangGraph `State` TypedDicts, as LangGraph checkpoint savers serialize state using msgpack/jsonplus. Always inject database sessions or clients via `RunnableConfig` (`config["configurable"]["db"]`) and extract them within node functions.
- **Database Connection Pools:** `psycopg_pool.AsyncConnectionPool` instances cannot be reopened once closed. In test fixtures, always instantiate fresh pool instances per test and ensure `LazyAsyncPostgresSaver` locks and event loops are dynamically bound to the current running event loop.
- **Database Schema Migrations (Alembic):** All database schema changes, new tables, and column additions MUST be performed via Alembic migration scripts in `backend/alembic/versions/`. Never execute ad-hoc raw `ALTER TABLE` statements inside `ensure_db_schema()` or application runtime bootstrap code.
  - Apply migrations: `uv run alembic upgrade head`
  - Inspect history & current heads: `uv run alembic heads` and `uv run alembic history`
  - Generate a new migration revision: `uv run alembic revision -m "description_of_change"`
- **Queue-First LLM Architecture (Mandatory Rule):** Any new or modified LLM feature that performs generation, synthesis, document drafting, or long-running AI extraction (e.g. Application Form Q&A generation, Cover Letters, Role Alignment Dossiers, Mock Interview debriefs, Job Spec extractions) **MUST be executed asynchronously via the central background evaluation queue** (`IntakeEvaluationTaskModel` / `evaluation_worker.py`). Direct blocking LLM calls on synchronous HTTP request handlers are strictly prohibited.
- **Settings & AI Task Binding Registration:** Every new LLM feature/task type MUST be:
  1. Registered in the `AITaskType` enum and task bindings registry (`backend/app/models/llm.py` and `backend/app/schemas/ai_config.py`).
  2. Provided with an authoritative default prompt template in `DEFAULT_PROMPTS` (`backend/app/core/prompts.py`) containing strict anti-hallucination and CV-grounding directives (and escaping all JSON schema `{`/`}` as `{{`/`}}`).
  3. Fully configurable within the **Settings UI** (`SettingsView.vue`), allowing users to bind distinct local/cloud AI providers, assign specific model tags, configure task parameters (temperature, max tokens, custom instructions), and customize prompt templates.
  4. Equipped with a dedicated, domain-tailored pipeline stepper, status badges, expandable preview drawer, and 1-click action buttons in `QueueView.vue` and floating queue widgets.
- **Modifying the UI & Theming Rules (Midnight & Daylight):**
  - **Zero Hardcoded Colors:** NEVER hardcode HEX values (`#ffffff`, `#000000`, `#18181b`), static RGB/RGBA (`rgba(255, 255, 255, ...)`, `rgba(0, 0, 0, ...)`), or arbitrary framework palette colors in Vue components or scoped styles.
  - **Mandatory Design System Tokens (`src/style.css`):** All components and modal/drawer popovers MUST strictly consume CSS custom properties so that both the OLED dark (**Midnight**) and warm stone light (**Daylight** / `html.daylight`) themes adapt seamlessly:
    - *Surfaces & Panels:* `var(--bg-elevated)` for dropdowns/popovers/modals, `var(--bg-surface)` / `var(--bg-surface-hover)` for buttons/options, `var(--bg-input)` for search/form fields, `var(--bg-app)` / `var(--bg-card)`.
    - *Text Hierarchy:* `var(--text-main)` for primary text/headers, `var(--text-secondary)` for subheadings/labels, `var(--text-muted)` for metadata/icons/placeholders, `var(--text-faint)`.
    - *Borders & Outlines:* `var(--border-color)` for default edges, `var(--border-subtle)` for internal dividers/subtle borders, `var(--border-focus)` for active inputs.
    - *Accents & Actions:* `var(--primary)` (emerald in Midnight, warm saddle in Daylight), `var(--primary-hover)`, `var(--primary-subtle)` for soft badge/button backgrounds, `var(--primary-glow)`, `var(--primary-contrast)`.
    - *Radii, Shadows & Motion:* `var(--radius-xs)`, `var(--radius-sm)`, `var(--radius-md)`, `var(--radius-lg)`, `var(--shadow-sm)`, `var(--shadow-md)`, `var(--shadow-lg)`, `var(--transition-fast)`.
  - **Reactivity & Icons:** Ensure `<script setup>` interacts with Pinia stores (`uiStore`, `applicationsStore`) correctly for reactivity. All icons MUST be imported from `lucide-vue-next`.
- **Modifying the Database:** If adding a new field to a database model, update the corresponding Pydantic schemas in the `schemas/` directory to reflect the change for both request validation and response serialization, and generate an Alembic migration.
- **Two-Tier Codebase Exploration (Graphify + Ripwire):** This project pairs Graphify for macro architecture with Ripwire for micro code navigation and verification:
  - *Macro / Architecture (Graphify):* For high-level system flows, community clusters, or cross-module relationships, query the knowledge graph via `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"`. Keep the graph current with `graphify update .` after code edits.
  - *Micro / Symbol Search & Impact (Ripwire):* To locate exact symbols, signatures, or implementations, run `ripwire . --for="<task or symbol>"`. Inspect call hierarchies with `ripwire . --callers="<sym>"` and measure blast radius with `ripwire . --impact="<sym>"`. Avoid reading whole large files when ripwire returns the exact definition and callers.
  - *Situational Awareness:* Run `ripwire . --situ` to inspect uncommitted edits for transitive blast radius, affected stores/files, and targeted tests before running full test suites.
  - *Tool Precedence:* Do NOT use native `grep_search` or `find_by_name` as default code navigation tools; use `ripwire` or `graphify` instead. Reserve `grep_search` only for exact string literals.

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
3. **Front end visual checks:** `VITE_DEMO_MODE=true npm run dev` (Use this always when having to test changes or additions to frontend)
---

## Workflow Execution (For Automated Agents)
1. **Read Intent & Context (Two-Tier Navigation):** Understand user requirements. Query Graphify (`graphify query "<question>"`) for high-level module/flow mapping; use Ripwire (`ripwire . --for="<symbol/task>"` and `ripwire . --callers="<sym>"`) to inspect exact signatures, callers, and dependencies without reading whole files. **Do NOT run test suites or build commands during research/read-only tasks.**
2. **Draft Plan (When Warranted):** Create an implementation plan artifact when making multi-step or architectural changes. Do not run commands that modify state or execute test suites while planning.
3. **Targeted Implementation:** Implement changes incrementally and surgically. Modify only the necessary files.
4. **Post-Edit Verification (Only After Code Edits):**
   - Run `ripwire . --situ` to inspect uncommitted changes, assess blast radius, and identify affected test suites.
   - For backend changes: Run the targeted test suite (e.g. `uv run pytest backend/app/tests/test_specific.py`). Full suite `uv run pytest` is only needed during final pre-commit or when shared/database core code changes.
   - For frontend changes: Run `npm run build` in `frontend/` to confirm template/TypeScript compilation.
   - Do NOT run frontend builds if only backend code was modified, and vice-versa.
5. **Pre-Commit Verification:** Ensure `uv run ruff format --check .` and `uv run ruff check .` pass with 0 errors before completing.