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

### Infrastructure
- Docker Compose is used for local development, managing `db` (Postgres), `scraper` (Camofox), `backend`, and `frontend`.
- Development scripts (`dev.sh`) orchestrate starting up components.

## Core Domains & Data Models
- **Applications:** `ApplicationModel` linked to `CompanyModel`. Tracks status (`APPLIED`, `TECHNICAL_INTERVIEW`, `OFFER`, `REJECTED`, `ASSESSMENT`), dates, and linked timeline events.
- **Candidate Profile:** `CandidateCVModel` stores raw resumes, anonymized versions, extracted skills, domain expertise, and years of experience.
- **Intake/Staging:** Raw leads are ingested as `StagingItemModel` or evaluated directly into `IntakeEvaluationTaskModel`.
- **Emails & Events:** `ApplicationEventModel` (tied to an app) or `OtherEventModel` (general recruitment spam/newsletters).
- **Action Items:** `ActionItemModel` tracks deadlines and next steps (e.g., reply to recruiter, interview scheduled).
- **Vector Embeddings:** Uses `pgvector` (`ApplicationEmbeddingModel`) to allow semantic search over job applications.

## Agent Guidelines & Development Rules
- **Formatting:** The backend uses `ruff` for formatting and linting (`uv run ruff check`, `uv run ruff format`).
- **Dependency Management:** The backend uses `uv` for managing packages and running commands.
- **Testing:** The backend uses `pytest` and `pytest-asyncio`. Run tests locally with `uv run pytest`. Be aware that tests rely on `testcontainers` which might have specific mount restrictions in certain Docker-in-Docker sandbox environments.
- **Asynchronous Code:** The backend relies heavily on `async/await` for database operations (`AsyncSession`), HTTP requests (`httpx`), and LLM calls. Always use non-blocking functions.
- **State Changes:** After every action that modifies code state, verify the outcome using read operations (e.g., `cat` or `grep`).
- **Modifying the UI:** When modifying frontend features, ensure the component's setup script (`<script setup>`) interacts with `pinia` stores (like `uiStore` or `applicationsStore`) correctly for state reactivity. Ensure Lucide icons used are imported from `lucide-vue-next`.
- **Modifying the Database:** If adding a new field to a database model, update the corresponding Pydantic schemas in the `schemas/` directory to reflect the change for both request validation and response serialization.

## Workflow Execution (For Automated Agents)
1. Read the user's intent.
2. Search through models, schemas, routers, and services in the backend.
3. Search through views, stores, and components in the frontend.
4. Draft a plan using `set_plan`.
5. Write or modify tests before implementing core logic (TDD).
6. Implement the logic incrementally, validating at each step.
7. Confirm complete and correct implementation using `pytest` (backend) or frontend checks.
8. Call `pre_commit_instructions` before submitting.