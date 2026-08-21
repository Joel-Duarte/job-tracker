# Frontend Architecture & Developer Reference (`frontend.md`)

## Overview & Architecture

The frontend of **Job Tracker** is a modern, single-page application (SPA) built with **Vue 3** (Composition API `<script setup>`), **Vite**, **Pinia**, and **Vue Router**. It provides a real-time, responsive interface for managing job application pipelines, analyzing recruitment metrics, reviewing AI job evaluations, drafting cover letters, configuring AI model providers, and interacting with a conversational AI agent.

### Tech Stack & Tooling
* **Framework:** Vue 3 (Composition API with `<script setup>`)
* **Build Tool & Dev Server:** Vite
* **State Management:** Pinia stores (`useQueueStore`, `useApplicationsStore`, `useUiStore`, `useAgentChatStore`)
* **Routing:** Vue Router (HTML5 History Mode)
* **Iconography:** `lucide-vue-next`
* **HTTP Client:** Axios (in `src/api/client.js`)
* **Security & Sanitization:** `DOMPurify` (sanitizing all `v-html` bound Markdown and raw HTML content via `src/utils/markdown.js`)
* **Styling & Design System:** Custom CSS design system in `src/style.css` supporting dark/light modes and dynamic theme palettes (`ThemePalettePopover.vue`).

---

## Directory & File Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.js          # Base Axios HTTP client & error interceptors
│   │   └── endpoints.js       # Centralized API service functions grouped by domain
│   ├── components/
│   │   ├── agent/             # Floating AI Chat Widget
│   │   ├── common/            # PageHeader, CompanyLogo, DateTimePicker, ToastNotification
│   │   ├── drawers/           # ApplicationDetailDrawer
│   │   ├── layout/            # AppNavbar, FloatingQueueWidget, IntakeQueueDrawer, ThemePalettePopover
│   │   ├── modals/            # CoverLetterModal, MatchAnalysisModal, JobIntakeModal, etc.
│   │   └── settings/          # EmailAccountsSettings
│   ├── router/
│   │   └── index.js           # Vue Router route declarations
│   ├── stores/
│   │   ├── agentChatStore.js  # Conversational AI state & SSE message streaming
│   │   ├── applicationsStore.js # Application Kanban state & bulk actions
│   │   ├── queueStore.js      # Centralized intake evaluation queue & dynamic polling
│   │   └── uiStore.js         # Global UI state (modals, toasts, drawers)
│   ├── utils/
│   │   ├── fitScores.js       # Qualitative and programmatic fit score formatting
│   │   ├── formatters.js      # Currency, date, and text formatters
│   │   ├── markdown.js        # DOMPurify-sanitized Markdown renderer
│   │   └── scrubber.js        # Sensitive text scrubbing utilities
│   ├── views/                 # Core view pages
│   │   ├── ActionItemsView.vue
│   │   ├── AgentChatView.vue
│   │   ├── AnalyticsView.vue
│   │   ├── ApplicationsView.vue
│   │   ├── AssessmentsView.vue
│   │   ├── CandidateProfileView.vue
│   │   ├── DiagnosticsView.vue
│   │   ├── InterviewGuideView.vue
│   │   ├── JobIntakeView.vue
│   │   ├── QueueView.vue
│   │   ├── SearchView.vue
│   │   ├── SettingsView.vue
│   │   └── StagingView.vue
│   ├── App.vue                # Root shell component & global modal bindings
│   ├── main.js                # App bootstrap & Pinia/Router initialization
│   └── style.css              # Global CSS variables, theme palettes, and utility classes
├── index.html
├── vite.config.js
└── package.json
```

---

## Router & Views Architecture

Defined in `frontend/src/router/index.js`, the routing layer maps URLs to view components:

| Route Path | View Component | Description |
| :--- | :--- | :--- |
| `/` | `ApplicationsView.vue` | Primary Kanban board for managing applications across active and terminal stages. |
| `/analytics` | `AnalyticsView.vue` | Market Intelligence & Pipeline Funnel Performance dashboard with tabbed views. |
| `/tasks` | `ActionItemsView.vue` | Recruitment task list derived from email analysis and application events. |
| `/assessments` (`/intake`) | `AssessmentsView.vue` | AI Job Fit Assessment cards and candidate fit scores. |
| `/queue` | `QueueView.vue` | Real-time intake queue management, stage progression, and task retry/fix tools. |
| `/profile` | Redirects to `/settings?tab=profile` | Candidate profile management (CV text, skills, experience). |
| `/chat` | `AgentChatView.vue` | Full-screen conversational AI agent workspace. |
| `/staging` | `StagingView.vue` | Ambiguous email and lead resolution queue. |
| `/settings` | `SettingsView.vue` | AI provider bindings, cover letter automation thresholds, email credentials, and profile settings. |
| `/guide/:id` | `InterviewGuideView.vue` | Streaming AI interview preparation guide viewer. |
| `/diagnostics` | `DiagnosticsView.vue` | System telemetry traces, filter logs, and error diagnostics. |

### Core Views Deep-Dive

#### 1. `ApplicationsView.vue` (Kanban Pipeline Board)
* **Stage Columns:** Active stages (`APPLIED`, `ONLINE_ASSESSMENT`, `TECHNICAL_INTERVIEW`, `OFFER`) and terminal status toggles.
* **Chronological Sorting:** Cards are sorted by upcoming scheduled interview dates and decision deadlines.
* **Quick Advance Button (`.card-advance-btn`):** Positioned on the right side of cards to step applications through active stages sequentially.
* **Bulk Transitions:** Supports multi-select batch status transitions (e.g., withdrawing remaining active applications upon accepting an offer via `PostHireModal.vue`).

#### 2. `AnalyticsView.vue` (Market Intelligence & Pipeline Funnel)
Features a top-level tabbed navigation bar switching between two analytics perspectives:
* **Market Intelligence Tab (`activeTab = 'market'`):** Visualizes salary distributions, work model ratios (Remote/Hybrid/Onsite), top requested skills, and geographic job hotspots using data from `/api/v1/analytics/market-intelligence`.
* **Pipeline Funnel Performance Tab (`activeTab = 'funnel'`):** Displays recruitment conversion performance powered by `/api/v1/metrics/funnel` (and `/analytics/funnel`). Supports switching between **Weekly** and **Monthly** cohort periods (`period=weekly|monthly`) and displays conversion rates across stages (Intakes $\rightarrow$ Applications $\rightarrow$ Interviews $\rightarrow$ Offers) with trend deltas against previous periods.

#### 3. `SettingsView.vue` (AI Infrastructure & System Configuration)
Organized into tabbed sections (General/System, Candidate Profile, AI Providers & Models, Email Accounts):
* **AI Provider & Model Binding:** Configures OpenAI, Anthropic, or local LM Studio providers and binds specific models to AI task categories (`JOB_ASSESSMENT`, `EMAIL_EXTRACTION`, `INTERVIEW_GUIDE`, `JD_EXTRACTION`, `COVER_LETTER`).
* **Cover Letter Automation Settings:**
  * Toggle system setting `ENABLE_AUTO_COVER_LETTER`.
  * **Match Threshold Slider (`coverLetterMatchThreshold`):** Range input (0% - 100%) controlling the minimum fit score required to trigger automatic cover letter drafting at intake completion.
  * **Length Selector:** Configures default cover letter target length (`concise` ~150 words, `standard` ~300 words, `detailed` ~450 words).
* **Sampling Temperature Slider:** Features dual event binding (`@input` for real-time value display update, `@change` with debouncing for server persistence).
* **Email Accounts Management (`EmailAccountsSettings.vue`):** Integrates IMAP and OAuth email credentials. Credentials returned from backend APIs are masked as `'********'`, preserving existing secrets when saving without edits.

#### 4. `QueueView.vue` & `FloatingQueueWidget.vue` (Intake Queue Management)
* Driven by `useQueueStore`. Displays queued, processing, completed, failed, and cancelled evaluation tasks.
* **Dynamic Scraped Content Fixing (`FixJD` Modal):** If a task fails during scraping or keyword validation (`INVALID_JOB_CONTENT:`), users can manually paste/edit job descriptions. The action button dynamically labels as **"Provide Description"** when `raw_text` is empty and **"Edit Job Description"** when text exists.

---

## Component Hierarchy & Organization

Components are organized by functional scope inside `src/components/`:

```
src/components/
├── agent/
│   └── FloatingAgentChatWidget.vue   # Floating persistent chat widget across all views
├── common/
│   ├── CompanyLogo.vue               # Favicon & fallback domain logo renderer
│   ├── DateTimePicker.vue            # Viewport-aware date/time picker using <Teleport to="body">
│   ├── PageHeader.vue                # Standardized page title header with action slots
│   └── ToastNotification.vue         # Global toast message renderer
├── drawers/
│   └── ApplicationDetailDrawer.vue   # Comprehensive application details, stage updates, activity history
├── layout/
│   ├── AppNavbar.vue                 # Primary navigation header & unread badges
│   ├── FloatingQueueWidget.vue       # Collapsible live queue ticker with polling indicator
│   ├── IntakeQueueDrawer.vue         # Slide-over queue drawer
│   └── ThemePalettePopover.vue       # UI accent theme selector (Default, Teal, Purple, Warm, Glass)
├── modals/
│   ├── CoverLetterModal.vue          # Global Cover Letter viewer, editor, and tone/length generator
│   ├── IngestModal.vue               # URL / Job Description ingestion modal
│   ├── InterviewReaderModal.vue      # Interview guide reader popup
│   ├── JobIntakeModal.vue            # Quick job intake modal wrapper
│   ├── LogActivityModal.vue          # Application timeline activity logger
│   ├── MatchAnalysisModal.vue        # AI match breakdown with score badge cards
│   └── PostHireModal.vue             # Hired milestone celebration & bulk pipeline transition
└── settings/
    └── EmailAccountsSettings.vue     # Email account integration & credentials form
```

---

## State Management (Pinia Stores)

State management is centralized in `src/stores/`:

### 1. `useQueueStore` (`queueStore.js`)
Centralizes state and polling for background job intake evaluations.
* **Dynamic Adaptive Polling:** Automatically switches polling intervals based on activity:
  * **1.5s interval** when active tasks exist (`QUEUED` or `PROCESSING`).
  * **4.0s interval** when idle.
* **Optimistic Execution & Rollbacks:** Applies local optimistic task additions using temporary client IDs (`temp-${Date.now()}`), rolling back state and displaying error toasts upon server API failure.
* **Core Actions:** `enqueueAssessment`, `retryTask`, `cancelTask`, `fixJDEvaluation`, `deleteTask`, `bulkRetryTasks`, `bulkDeleteTasks`, `clearCompletedTasks`.

### 2. `useApplicationsStore` (`applicationsStore.js`)
Manages job applications, stage filtering, search queries, and application timeline events.
* Maintains reactive getters for active applications, terminal status counts, and pending action badges.
* Handles optimistic application stage updates and coordinates with backend bulk transition endpoints.

### 3. `useUiStore` (`uiStore.js`)
Controls global UI overlays, drawer visibility, modal parameters, and system notifications.
* **Global Modal Methods:** `openCoverLetterModal(appId)`, `openMatchAnalysisModal(app)`, `openLogActivityModal(appId)`, `openPostHireModal(app)`.
* **Toast System:** `showToast({ title, message, type })` with auto-dismissal timeouts.

### 4. `useAgentChatStore` (`agentChatStore.js`)
Manages state for conversational AI agent sessions, message history, and real-time Server-Sent Events (SSE) streaming.
* Sanitizes tool call outputs using compact JSON formatting and renders agent responses in real time.

---

## API Service Layer & Data-Fetching Patterns

Located in `src/api/`:

* **`client.js`:** Creates the Axios instance with base URL `/api/v1` and registers request/response interceptors for error handling and standardizing response payloads.
* **`endpoints.js`:** Exports domain-specific API objects:
  * `ApplicationsAPI`: CRUD operations, stage updates, bulk transitions, cover letter endpoints.
  * `IntakeAPI`: Enqueuing evaluations, queue task queries, task cancellation, JD fixes, bulk retry/delete.
  * `AnalyticsAPI`: Market intelligence metrics and funnel conversion data.
  * `SettingsAPI`: System settings, AI providers, model auto-discovery, task bindings.
  * `CandidateProfileAPI`: Profile CV text, anonymized CVs, and skill extractions.
  * `AgentChatAPI`: Stream endpoint `/agent/chat/stream` for SSE interaction.
  * `DiagnosticsAPI`: System trace telemetry filtering and error diagnostics.

### Data Fetching Patterns
1. **SSE Streaming:** Real-time generation streaming (for Agent Chat and Interview Guides) using `fetch` with `ReadableStream` readers to append streaming chunks into reactive UI state.
2. **Adaptive Polling:** Used in `useQueueStore` to monitor task execution without overwhelming the backend during idle states.
3. **Optimistic UI Updates with Error Rollback:** Immediate UI responsiveness for user actions (e.g. enqueuing tasks, status changes) backed by snapshot rollbacks on API failure.

---

## Form Controls & Interaction Models

### 1. Range Sliders & Real-time Feedback vs. Release Persistence
* **Real-time Input vs. Release Persistence Pattern:**
  * For immediate visual feedback (e.g., Sampling Temperature in `SettingsView.vue`), controls bind `@input` to update reactive UI state instantly while scheduling a debounced or delayed auto-save.
  * For threshold controls (e.g., Cover Letter Match Score Threshold slider), controls bind `@change` to emit server persistence calls when the user finishes dragging the thumb control, avoiding excessive API calls during drag.

### 2. Viewport-Aware Teleporting (`DateTimePicker.vue`)
* Uses Vue `<Teleport to="body">` combined with `position: fixed` and dynamic `getBoundingClientRect()` calculation.
* Ensures date/time popover pickers render above modal and drawer container boundaries (`overflow: hidden`) without clipping or alignment offset bugs.

### 3. Sanitized HTML Rendering (`v-html`)
* All dynamic Markdown content (AI fit explanations, interview guides, agent chat responses, job descriptions) passes through `renderMarkdown` in `src/utils/markdown.js`.
* Employs `DOMPurify.sanitize()` to prevent cross-site scripting (XSS) from untrusted scraped content or raw LLM outputs.

---

## Design System & Global Styling Standards

Global styles and design tokens are defined in `frontend/src/style.css`:

### 1. CSS Custom Properties & Themes
* Supports Light Mode, Dark Mode, and dynamic accent color palettes (`default`, `teal`, `purple`, `warm`, `glass`) managed via `ThemePalettePopover.vue`.
* Standard tokens: `--primary`, `--bg-app`, `--card-bg`, `--border-color`, `--text-primary`, `--text-muted`.

### 2. Standardized Score Badges
* Qualitative AI fit scores and programmatic match scores use standard utility components:
  * `.score-badge-card`: Rectangular container for match score display.
  * Tier Color Classes (via `getFitBadgeClass` in `src/utils/fitScores.js`):
    * `.fit-elite`: $\ge 85\%$ (Emerald/Green)
    * `.fit-high`: $70\% - 84\%$ (Indigo/Blue)
    * `.fit-medium`: $50\% - 69\%$ (Amber/Yellow)
    * `.fit-low`: $< 50\%$ (Rose/Red)

---

## Related Documentation & Cross-References

* **`AGENTS.md`:** Reference for backend environment configuration, database integration test tiers, pre-commit checklists, and frontend build commands (`npm run build`).
* **`tools.md`:** Specifications for the 8 custom AI agent tools invoked through `AgentChatView.vue`.
* **`guide.md`:** Database schema audit, entity relationship definitions, and 90-day rolling mock data generation rules.
