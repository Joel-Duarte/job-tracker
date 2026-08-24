# Job Tracker

### *AI-Powered Career Hub & Recruitment Intelligence Platform*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-4f46e5?style=for-the-badge&logo=github&logoColor=white)](https://joel-duarte.github.io/job-tracker/?ref=github)
[![Vue 3](https://img.shields.io/badge/Vue.js-3.5-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Camofox](https://img.shields.io/badge/Camofox-Stealth%20Scraper-FF6B6B?style=for-the-badge)](https://github.com/jo-inc/camofox-browser)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-red.svg?style=for-the-badge)](https://polyformproject.org/licenses/noncommercial/1.0.0)

---

**Job Tracker** is the all-in-one, local-first platform to automate job intake, assess skill fit with AI, practice interactive mock interviews, sync recruitment emails, and manage your job search pipeline. Built for privacy, speed, and intelligence.

> 🎮 **Live Interactive Demo:** Try Job Tracker directly in your browser without installing anything: **[https://joel-duarte.github.io/job-tracker/](https://joel-duarte.github.io/job-tracker/?ref=github)** (runs 100% client-side with full mock dataset & simulated AI workflows).

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                                                                             │
 │   🌐 Browser Extension  ──▶  ⚡ Async Intake Queue  ──▶  🤖 AI Fit Engine    │
 │   (1-Click ATS Grab)         (Camofox Stealth)          (Gap Dossier)       │
 │                                                                  │          │
 │                                                                  ▼          │
 │   📬 Email Sync (IMAP)  ──▶  📋 Kanban Pipeline    ──▶  🎙️ Mock Simulator  │
 │   (Dates & Actions)          (4 Active Stages)          (STAR Scorecards)   │
 │                                                                             │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌟 Why Job Tracker?

| Feature | Description |
| :--- | :--- |
| 🔒 **100% Private & Local-First** | Run entirely on your own hardware with **LM Studio** or **Ollama** (zero telemetry, zero cloud data leakage), or connect top-tier cloud models (**OpenAI**, **Anthropic**, **Gemini**, **OpenRouter**). |
| 🌐 **1-Click Browser Capture** | Floating capture dock for **LinkedIn**, **Indeed**, **Greenhouse**, **Lever**, **Workday**, and **Ashby**, with universal DOM fallback parsing. |
| 🤖 **Deep AI Fit & Gap Dossier** | Granular hard/soft skill breakdown, experience alignment scoring, ATS keyword analysis, and customized cover letters. |
| 🎙️ **Interactive Mock Interview Simulator** | Multi-turn voice and text simulations featuring specialized interviewer personas (*Technical Bar Raiser*, *Hiring Manager*, *Behavioral Coach*) and real-time STAR debrief scorecards. |
| 📬 **Automated Email Sync & Action Items** | Connects to **Gmail**, **Outlook**, or **IMAP** to extract interview schedules, rejection updates, and to-do deadlines automatically. |
| 📋 **Smart Kanban Pipeline** | 4 active stages (`APPLIED`, `ONLINE_ASSESSMENT`, `TECHNICAL_INTERVIEW`, `OFFER`), scheduled interview countdowns, automated staleness sweeper, and past wins archive. |

---

## 🚀 60-Second Quickstart

### Linux & macOS

```bash
# 1. Clone the repository
git clone https://github.com/Joel-Duarte/job-tracker.git
cd job-tracker

# 2. Launch Job Tracker
./jt start
```

### Windows (CMD / PowerShell)

```cmd
:: 1. Clone the repository
git clone https://github.com/Joel-Duarte/job-tracker.git
cd job-tracker

:: 2. Launch Job Tracker
jt.cmd start
```

### Direct Docker Compose

```bash
docker compose up -d
```

### 🌐 Access URLs & Ingress Architecture

Job Tracker is designed with a **closed-by-default, single-port ingress architecture**. All backend, database, and scraper services run securely inside the private Docker network and are never exposed directly to the outside host. Everything is accessed through the Frontend Reverse Proxy:

- **Web Application:** [http://localhost:4173](http://localhost:4173) *(Production)* or [http://localhost:5173](http://localhost:5173) *(Development)*
- **Interactive API Docs (Swagger UI):** [http://localhost:4173/api/docs](http://localhost:4173/api/docs) *(Production)* or [http://localhost:5173/api/docs](http://localhost:5173/api/docs) *(Development)*
- **ReDoc Documentation:** [http://localhost:4173/api/redoc](http://localhost:4173/api/redoc) *(Production)* or [http://localhost:5173/api/redoc](http://localhost:5173/api/redoc) *(Development)*
- **API Endpoints:** `http://localhost:4173/api/v1/...` *(proxied internally to FastAPI)*
- **Internal Services (Sealed in Docker Network):** Backend (`backend:8000`), Database (`db:5432`), and Camofox Scraper (`scraper:9377`) are protected and not exposed to the host.

---

## 🛠️ Unified CLI Management (`./jt` / `jt.cmd`)

Job Tracker includes a unified command-line interface for managing development and production environments across Linux, macOS, and Windows.

| Command | Usage | Description |
| :--- | :--- | :--- |
| `start` | `./jt start [--clean] [--open]` | Start production stack in background. Use `--clean` to wipe DB and boot pristine; `--open` to launch browser. |
| `dev` | `./jt dev` / `jt.cmd dev` | Start live development environment (isolated dev DB + hot reloading). |
| `stop` | `./jt stop` / `jt.cmd stop` | Gracefully stop all Job Tracker containers. |
| `status` | `./jt status` / `jt.cmd status` | Display the health status, exposed ports, and container states. |
| `logs` | `./jt logs [service]` | Stream live container logs (`./jt logs backend`, `./jt logs frontend`, etc.). |
| `open` | `./jt open` / `jt.cmd open` | Open the Job Tracker web application in your default browser. |
| `update` | `./jt update` / `jt.cmd update` | Pull the latest container images and rebuild application services. |
| `clean` / `reset` | `./jt clean` / `jt.cmd clean` | Wipe PostgreSQL database volumes and restart with a clean slate (prompts for confirmation). |
| `seed` | `./jt seed` / `jt.cmd seed` | Generate and seed fresh domain-tailored mock job applications via local LLM. |

---

## 🧩 Feature Tour

### 1. Smart Kanban Pipeline & Stage Tracking
Track applications across 4 active stages with automatic countdowns for scheduled interviews and decision deadlines.

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   📝 APPLIED    │──▶│ 💻 ONLINE ASMT  │──▶│ 🎙️ TECH INTRVW  │──▶│   🎉 OFFER      │
│ 5 Applications  │   │ 2 In Progress   │   │ In 2 days (10am)│   │ Decision: Dec 15│
└─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────────┘
                                                       │
                     ┌─────────────────────────────────┴───────────────────┐
                     ▼                                                     ▼
           🏆 HIRED / ACCEPTED                                    📦 ARCHIVED / WITHDRAWN
```

### 2. Deep AI Fit & Gap Dossier
Compare candidate CV profiles directly against ingested job descriptions using multi-agent LangGraph workflows.

```
  MATCH SCORE: 92% (Strong Fit)
  ├── 🟢 Core Competencies: Distributed Systems, Async Python, PostgreSQL (100% Match)
  ├── 🟡 Missing / Desired Skills: Rust, eBPF (Identified & Highlighted)
  ├── 📄 Generated Pitch: "Staff-level expertise scaling async pipelines with pgvector..."
  └── ✍️ Custom Cover Letter: 1-Click Export tailored to job posting requirements
```

### 3. Live Interactive Mock Interview Simulator
Practice behavioral, technical, and system design interviews tailored specifically to your target role.

```
  Interviewer Persona: [ 🛡️ Technical Bar Raiser ]
  Question Mode:       [ 💬 Multi-Turn STAR Drill ]

  Interviewer ❯ "Walk me through how you resolved a high-concurrency race condition in Postgres."
  Candidate   ❯ "We encountered deadlocks during peak write traffic on our booking ledger..."
  
  [ Real-Time STAR Feedback ]
  ├── Situation & Task: Clear and structured (Score: 9/10)
  ├── Action: Strong technical depth on row-level locking (Score: 10/10)
  └── Result: Quantified latency reduction by 40% (Score: 9/10)
```

### 4. Automated Email Sync & Action Item Extraction
Connect recruitment mailboxes via IMAP or OAuth (Gmail & Outlook) to automatically synchronize recruitment updates and populate to-do action items.

```
  📬 Inbound Email: "Invitation to Technical Interview at Figma"
  ├── 📅 Event Detected: Technical Interview on Thursday at 2:00 PM GMT
  ├── 🔄 Pipeline Action: Auto-transitioned application to "TECHNICAL_INTERVIEW"
  └── ✅ Action Item Created: "Confirm video call attendance with recruiter" (Due in 24h)
```

### 5. Companion Browser Extension
Capture job postings while browsing without switching tabs.

```
  ┌────────────────────────────────────────────────────────┐
  │ 🦊 Job Tracker Companion Dock                          │
  ├────────────────────────────────────────────────────────┤
  │ Role: Senior Distributed Systems Engineer              │
  │ Company: Stripe (stripe.com)                           │
  │ Location: Remote / San Francisco                       │
  │                                                        │
  │ [ ⚡ Enqueue AI Assessment ]   [ 📌 Save Directly ]   │
  └────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation & Deep Dives

Explore our guides to get the most out of Job Tracker:

| Document | Description |
| :--- | :--- |
| [`docs/QUICKSTART.md`](file:///home/joel/Projects/job-tracker/docs/QUICKSTART.md) | Detailed installation steps, first-run wizard guide, and troubleshooting FAQs. |
| [`docs/USER_GUIDE.md`](file:///home/joel/Projects/job-tracker/docs/USER_GUIDE.md) | Complete "Day in the Life" guide covering intake, AI analysis, simulations, and tracking. |
| [`docs/AI_PROVIDERS.md`](file:///home/joel/Projects/job-tracker/docs/AI_PROVIDERS.md) | Local AI configuration (LM Studio, Ollama) and Cloud AI setup (OpenAI, Anthropic, Gemini). |
| [`docs/OAUTH_SETUP.md`](file:///home/joel/Projects/job-tracker/docs/OAUTH_SETUP.md) | Complete step-by-step guide for Gmail/Outlook OAuth 2.0 and IMAP App-Specific Passwords. |
| [`docs/EXTERNAL_SERVICES.md`](file:///home/joel/Projects/job-tracker/docs/EXTERNAL_SERVICES.md) | Guide for connecting external PostgreSQL databases and custom Camofox scraper instances. |
| [`docs/ARCHITECTURE.md`](file:///home/joel/Projects/job-tracker/docs/ARCHITECTURE.md) | Architectural blueprints, LangGraph state machine flows, pgvector vector search, and Camofox scraper design. |
| [`extension/README.md`](file:///home/joel/Projects/job-tracker/extension/README.md) | Installation and setup guide for the companion Chrome, Brave, Edge, and Firefox browser extension. |
| [`backend/README.md`](file:///home/joel/Projects/job-tracker/backend/README.md) | Backend developer guide, API schemas, testing hierarchy, and database migration rules. |

---

## ⚙️ Tech Stack Summary

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Vue 3 (Composition API), Vite, Pinia, Lucide Icons | High-performance SPA with dark/light themes, Kanban drag-and-drop, radar scorecards, and live reactive store state. |
| **Backend API** | FastAPI, Python 3.12, AsyncIO, Uvicorn | Async REST API and WebSocket gateway with non-blocking database queries and worker orchestration. |
| **AI Orchestration** | LangChain, LangGraph, Pydantic | Multi-agent state machines, role-playing interview simulator, candidate fit evaluation, and customizable provider task bindings. |
| **Database & Vector Search** | PostgreSQL 16, pgvector, pg_trgm, SQLAlchemy 2 | Relational application storage, vector similarity search, fuzzy full-text matching, and Alembic migrations. |
| **Stealth Scraper** | Camofox (Headless Firefox Engine) | Anti-bot evasion, dynamic JavaScript execution, cookie dismissals, and high-fidelity DOM extraction. |
| **Browser Extension** | WebExtensions Manifest V3 | Cross-browser floating capture dock for Chrome, Brave, Edge, and Firefox with background sync. |

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

### Development Workflow

1. **Set Up Pre-Commit Hooks:**
   ```bash
   uv run --directory backend pre-commit install
   ```

2. **Run Quality Verification:**
   Before submitting changes, execute the pre-commit verification script ([`pre-commit.sh`](file:///home/joel/Projects/job-tracker/scripts/pre-commit.sh)):
   ```bash
   ./scripts/pre-commit.sh
   ```
   This automatically runs:
   - Backend Ruff format & lint checks (`uv run ruff format --check .`, `uv run ruff check .`)
   - Backend Pytest suite (`uv run pytest`)
   - Frontend Vite build & TypeScript checks (`npm run build`)

---

## 📄 License

This project is licensed under the **PolyForm Noncommercial License 1.0.0** — see the [LICENSE](LICENSE) file for details.

> Free for personal, educational, and individual non-commercial use. Commercial use, third-party SaaS hosting, redistribution for profit, and commercial exploitation are strictly prohibited without prior written permission from the copyright holder (Joel Duarte).
