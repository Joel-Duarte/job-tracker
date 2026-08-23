# 🚀 Job Tracker: Quickstart & Daily Driving Guide

Welcome to **Job Tracker** — the full-stack, AI-powered application designed to manage your job search end-to-end. From 1-click web scraping and AI job fit assessments to automatic email synchronization, mock interview practice, and Kanban application tracking, Job Tracker keeps your recruitment pipeline organized and actionable.

This guide will walk you through installation, first-time onboarding, browser extension setup, daily CLI operations, configuration, and troubleshooting.

---

## 📋 Prerequisites

Job Tracker is packaged with containerized Docker services to ensure zero dependency conflicts and seamless cross-platform support.

### System Requirements
- **Operating System:** Linux (Ubuntu/Debian, Fedora, Arch), macOS (Apple Silicon or Intel), or Windows 10/11 (with WSL2).
- **Docker Engine:** Docker 24.0+ & Docker Compose v2.20+ (or **Docker Desktop**).
- **Hardware Recommendations:**
  - Cloud AI mode (OpenAI, Anthropic, Gemini, OpenRouter): 2 CPU cores, 4 GB RAM.
  - Local AI mode (LM Studio, Ollama running 7B–14B models): 4+ CPU cores, 16+ GB RAM (or dedicated NVIDIA/Apple Silicon GPU).

> [!NOTE]
> Ensure the Docker daemon is running before executing startup commands (`docker info`). On Windows and macOS, make sure Docker Desktop is launched and healthy.

---

## ⚡ 1-Command Quickstart

Start Job Tracker in permanent production mode with a single command:

### Linux & macOS
```bash
./jt start
# or alternatively:
./prod.sh
```

### Windows (Command Prompt / PowerShell)
```cmd
jt.cmd start
REM or alternatively:
docker compose up -d
```

### Accessing the Services & Architecture
Job Tracker operates on a **closed-by-default, single-port ingress architecture**. All backend API workers, PostgreSQL database, and Camofox scraper instances run securely isolated within the internal Docker network. Access to the entire platform is unified through the Frontend Reverse Proxy:

- **🌐 Web Application UI:** [`http://localhost:4173`](http://localhost:4173) *(Production)* or [`http://localhost:5173`](http://localhost:5173) *(Development)*
- **📚 Interactive API Docs (Swagger UI):** [`http://localhost:4173/api/docs`](http://localhost:4173/api/docs) *(Production)* or [`http://localhost:5173/api/docs`](http://localhost:5173/api/docs) *(Development)*
- **📖 ReDoc API Reference:** [`http://localhost:4173/api/redoc`](http://localhost:4173/api/redoc) *(Production)* or [`http://localhost:5173/api/redoc`](http://localhost:5173/api/redoc) *(Development)*
- **🔒 Internal Services:** The FastAPI backend (`backend:8000`), PostgreSQL (`db:5432`), and Camofox scraper (`scraper:9377`) remain sealed within the private Docker network, eliminating external host port collisions.

> [!TIP]
> **Production Boot Persistence:**
> All production containers run with the Docker policy `restart: unless-stopped`. They will automatically start on PC or server boot whenever Docker starts. To stop them permanently, run `./jt stop` (or `./prod.sh --down`).

---

## 🧑‍💻 Development Mode (Live Hot-Reloading)

If you are developing features, modifying Vue components, or tweaking backend endpoints:

```bash
# Linux / macOS
./jt dev
# or: ./dev.sh

# Windows
jt.cmd dev
```
- **Frontend (Vite HMR):** [`http://localhost:5173`](http://localhost:5173)
- **Backend API (Reverse-proxied):** [`http://localhost:5173/api`](http://localhost:5173/api)
- **Dev Seed Dataset:** In development mode, the database automatically boots with realistic mock tech applications, job postings, timeline events, action items, and an active local AI provider configuration.

---

## 🧙 First-Time In-App Onboarding Wizard

When you open the web UI for the first time, Job Tracker automatically launches the **5-Step Onboarding Wizard** to configure your workspace in under two minutes:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Job Tracker Setup Wizard                        │
│                                                                        │
│  [1] AI Provider  ➜  [2] Candidate CV  ➜  [3] Preferences  ➜  [4] Sync  │
│                                                                        │
│                      ➜  [5] Launch Workspace 🚀                       │
└────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Connect Your AI Provider
Job Tracker is model-agnostic. Choose your preferred AI engine:
1. **Local LM Studio / Local Ollama (100% Private):** Zero data leaves your computer. Default endpoint `http://192.168.x.x:1234/v1` (LM Studio) or `http://localhost:11434/v1` (Ollama).
2. **Cloud Providers (OpenAI, Anthropic Claude, Google Gemini, OpenRouter):** Enter your API key.
3. Click **"Test Connection"** — Job Tracker verifies network connectivity and dynamically discovers all loaded models directly from the provider endpoint.
4. Select your primary model (e.g., `qwen2.5-7b-instruct`, `gpt-4o-mini`, `gemini-2.0-flash`, `claude-3-5-haiku`) and click **Next**.

> [!NOTE]
> For in-depth instructions on setting up local and cloud AI backends, see [AI Providers Documentation](file:///home/joel/Projects/job-tracker/docs/AI_PROVIDERS.md).

### Step 2: Upload or Paste Candidate CV
1. Upload your resume (PDF, DOCX, TXT, or Markdown) or paste the raw text.
2. **Built-in PII Anonymizer:** Review how Job Tracker automatically scrubs personal identifying information (phone numbers, personal emails, physical addresses) before LLM prompt injection while preserving your core technical competencies, years of experience, and project achievements.
3. Click **Save & Proceed** (or Skip to add later via Profile settings).

### Step 3: Configure Workspace Preferences
- **Default Currency:** Select USD (`$`), EUR (`€`), GBP (`£`), CAD (`$`), AUD (`$`), or JPY (`¥`) for salary tracking.
- **pgvector Embedding Search:** Enable dense semantic similarity search across applications and job descriptions.
- **Auto Cover Letter Synthesis:** Toggle automatic cover letter generation with custom fit threshold percentages (e.g., auto-generate when job fit score $\ge$ 70%).

### Step 4: (Optional) Connect Email Sync
Automate interview invites, online assessments, and recruiter update tracking:
- **Google / Gmail:** Secure OAuth2 authorization or App Password.
- **Microsoft Outlook / 365:** Microsoft Graph OAuth2 or App Password.
- **Apple iCloud / Fastmail / Yahoo / Custom IMAP:** Direct IMAP connection over SSL (Port 993).
- Choose your recruitment folder (e.g., `INBOX`, `Jobs`, `Recruitment`) and sync schedule.

### Step 5: Launch!
Click **"Launch Job Tracker"** to enter your workspace. Your background evaluation worker starts immediately, ready to triage and assess leads.

---

## 🧩 Companion Browser Extension Installation

The **Job Tracker Companion** extension adds a 1-click capture pill directly onto job boards (LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, Workday, Ashby, and arbitrary company career portals).

```
 ┌───────────────────────────────────────────────────────────┐
 │ LinkedIn Job Page                       [ Job Tracker 🎯 ]│
 │ Senior Backend Engineer                 ┌─────────────────┤
 │ Stripe • Remote • $180k - $220k         │ ⚡ Enqueue AI   │
 │                                         │ 📌 Apply Direct │
 └─────────────────────────────────────────┴─────────────────┘
```

### Chromium Browsers (Google Chrome, Brave, Microsoft Edge, Arc)
1. Open your browser extension management page:
   - **Chrome:** `chrome://extensions`
   - **Brave:** `brave://extensions`
   - **Edge:** `edge://extensions`
2. Toggle **Developer mode** in the top-right corner.
3. Click **"Load unpacked"**.
4. Select the `extension/` directory located at the root of the Job Tracker repository.
5. Pin the Job Tracker Companion icon to your browser toolbar.

### Mozilla Firefox
1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`.
2. Click **"Load Temporary Add-on..."**.
3. Select `extension/manifest.json` inside the repository `extension/` folder.

### Extension Settings
By default, the browser extension communicates with the reverse proxy API at `http://localhost:4173` (production) or `http://localhost:5173` (development). Click the extension icon in your toolbar, go to the **Settings** tab, and adjust the backend URL if running on a custom port or remote server.

---

## 💻 CLI Commands Reference (`./jt` & `jt.cmd`)

Job Tracker includes a unified CLI management script (`jt` for Unix, `jt.cmd` for Windows).

| Command | Action | Description |
| :--- | :--- | :--- |
| `./jt start` | Start Production | Boots PostgreSQL, Camofox Scraper, FastAPI Backend, and Nginx UI permanently in background. |
| `./jt dev` | Start Development | Launches Vite HMR frontend (`:5173`) with live backend reloading and auto-seeded mock data. |
| `./jt stop` | Stop Services | Gracefully stops all active Job Tracker containers. |
| `./jt status` | Service Health | Displays the live running state, CPU/RAM, and health status of all service containers. |
| `./jt logs` | Follow Logs | Streams real-time aggregated logs from all services (use `Ctrl+C` to exit). |
| `./jt open` | Open in Browser | Opens the Job Tracker web application in your default desktop browser. |
| `./jt update` | Pull & Rebuild | Pulls the latest container bases, recompiles frontend assets, and restarts containers. |
| `./jt seed` | Seed Dev Data | Populates the database with realistic sample candidates, applications, events, and action items. |
| `./jt reset` | Factory Reset | ⚠️ Wipes the PostgreSQL database volume and restarts with a clean slate. |

> [!NOTE]
> You can also run the underlying bash scripts directly:
> - Production: `./prod.sh` (supports flags like `./prod.sh --logs`, `./prod.sh --status`, `./prod.sh --down`, `./prod.sh --reset`)
> - Development: `./dev.sh` (supports flags like `./dev.sh --generate-mocks`, `./dev.sh --reset`, `./dev.sh --down`)

---

## ⚙️ Environment Configuration (`.env`)

Job Tracker comes with sensible defaults. To customize ports, credentials, or encryption keys, create or edit `.env` in the repository root:

```ini
# ==============================================================================
# Job Tracker Environment Configuration
# ==============================================================================

# Application Environment ('production' or 'development')
ENVIRONMENT=production

# Service Port Mappings
FRONTEND_PORT=4173       # Production Web UI port (http://localhost:4173)
BACKEND_PORT=8008        # FastAPI REST API port (http://localhost:8008)
POSTGRES_PORT=54320      # PostgreSQL host port (localhost:54320)
CAMOUFOX_PORT=9377       # Camofox Scraper port (http://localhost:9377)

# PostgreSQL Database Credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres

# Security & Encryption Secrets
# Generated automatically if left empty, or provide a 32-byte Fernet key
SECRET_KEY=
ADMIN_SECRET=

# Reverse Proxy & Host URL Overrides (Optional)
PUBLIC_API_URL=
PUBLIC_FRONTEND_URL=

# Scraper Internal Network Endpoint
CAMOUFOX_ENDPOINT=http://scraper:9377

# Logging Level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
LOG_LEVEL=INFO
```

---

## 🛠️ Troubleshooting & FAQ

### 1. Port Conflict (e.g., Port `4173` or `54320` is already in use)
- **Symptom:** Docker logs report `bind: address already in use`.
- **Solution:** Edit `.env` and change the conflicting port (for example, set `FRONTEND_PORT=4200` or `POSTGRES_PORT=54321`), then run `./jt start`.

### 2. Local LLM (LM Studio / Ollama) Connection Failed from Inside Docker
- **Symptom:** In Onboarding Step 1 or `/settings`, testing connection to `http://localhost:1234/v1` reports `Connection Refused`.
- **Cause:** `localhost` inside a Docker container refers to the container itself, not your host machine.
- **Solution:**
  - Use your machine's local LAN IP (e.g. `http://192.168.1.150:1234/v1`).
  - Or use Docker's host gateway alias: `http://host.docker.internal:1234/v1` (LM Studio) or `http://host.docker.internal:11434/v1` (Ollama).
  - Ensure LM Studio or Ollama is listening on all interfaces (`0.0.0.0`), not just `127.0.0.1`.

### 3. How do I completely wipe data and start fresh?
Run:
```bash
./jt reset
# or
./prod.sh --reset
```
This safely stops containers, deletes the `job_tracker_postgres_data` volume, and boots a clean database instance.

### 4. How do I inspect live backend errors or scraper activity?
To stream logs in real time:
```bash
./jt logs
# or view backend only:
docker compose logs -f backend
```

### 5. Docker Daemon is not running
- **Linux:** Run `sudo systemctl start docker`.
- **macOS / Windows:** Start the **Docker Desktop** application from your Applications menu or system tray.

---

## 🎯 Next Steps

- Explore the [AI Providers Guide](file:///home/joel/Projects/job-tracker/docs/AI_PROVIDERS.md) to fine-tune per-task model bindings and configure transparent failovers.
- Visit `/applications` in the web app to manage your Kanban pipeline.
- Practice multi-turn behavioral and technical interview questions in `/assistant` (Mock Interview Simulator).
