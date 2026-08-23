# Job Tracker Companion Browser Extension

The **Job Tracker Companion** is a Manifest V3 browser extension designed for 1-click job posting capture, real-time AI fit assessment ingestion, and direct application tracking directly from your browser.

It features an isolated in-page Shadow DOM floating dock, domain-specific extractors for 20+ ATS and job boards, and a multi-tab management popup with real-time background task synchronization.

---

## 🚀 Installation & Browser Setup

The extension is cross-browser compatible and supports all major Chromium and Gecko browsers.

### 🌐 Chromium Browsers (Google Chrome, Brave, Microsoft Edge, Arc, Opera, Vivaldi)

1. Open your browser and navigate to the extension management page:
   - **Google Chrome:** `chrome://extensions`
   - **Brave:** `brave://extensions`
   - **Microsoft Edge:** `edge://extensions`
   - **Arc:** Open Settings → Extensions or type `arc://extensions`
2. Toggle **"Developer mode"** in the top-right corner.
3. Click the **"Load unpacked"** button.
4. Select the `extension/` directory from the root of your `job-tracker` repository.
5. The Job Tracker Companion icon will appear in your browser toolbar. We recommend pinning it for easy access.

---

### 🦊 Gecko Browsers (Mozilla Firefox, Floorp, Waterfox)

1. Open Firefox and enter `about:debugging#/runtime/this-firefox` in the address bar.
2. Click **"Load Temporary Add-on..."**.
3. Browse to the `extension/` directory in the repository and select `manifest.json`.
4. The extension will load immediately with full functionality enabled.

> [!NOTE]
> Firefox temporary add-ons stay loaded until the browser session is restarted.

---

## ✨ Core Features & Capabilities

### 1. In-Page Floating Shadow DOM Dock (`content/dock.js`)
- **Non-Intrusive & Isolated:** Encapsulated within an isolated Shadow DOM tree to ensure complete immunity from host page CSS styling.
- **Auto-Detection:** Automatically activates when visiting supported applicant tracking systems (Greenhouse, Lever, Workday, Ashby, LinkedIn, Indeed, Glassdoor) or arbitrary URLs containing job/career keywords (`/careers`, `/jobs`, `/apply`, `vacatures`, `stellenangebote`, `recrutement`, `vagas`).
- **Draggable & Collapsible Pill:** Freely reposition the dock anywhere on your screen. Expand or collapse it with a single click.
- **1-Click Actions:**
  - **⚡ Enqueue AI Assessment:** Extracts the page DOM and sends it to the AI evaluation pipeline to score match fit against your active candidate profile.
  - **📌 Direct Applied:** Instantly adds the job to your Kanban board under the `APPLIED` column with extracted job title, company name, location, and salary metadata.

---

### 2. Smart Hybrid DOM Extractor (`content/extractor.js`)
- **Specialized ATS Selectors:** High-fidelity parser tailored for LinkedIn, Greenhouse, Lever, Workday, Ashby, Indeed, and Glassdoor job boards.
- **Universal Semantic Fallback:** Intelligently scrapes arbitrary career sites by parsing standard semantic markup (`h1`, `article`, `[role="main"]`, schema.org metadata).
- **Data Sanitization:** Strips notification badges, localized tracking artifacts, and noisy breadcrumbs to ensure clean company and title naming.

---

### 3. Multi-Tab Extension Popup (`popup/popup.html`)

#### 🎯 Capture Tab
- **Active Tab Metadata:** Shows current page URL and auto-detected portal type.
- **Ingestion Mode Toggle:**
  - **🤖 AI Evaluation Queue:** Sends full page content for multi-factor candidate scoring and gap analysis.
  - **📌 Direct Applied:** Unlocks live-editable input fields (Company Name, Job Title, Location, Salary, Work Model) for immediate logging.
- **Progress Countdown:** Animated feedback bar with quick links to jump directly into Job Tracker or capture another opening.

#### ⚡ AI Queue Tab
- **Live Background Queue:** Real-time list of in-flight and completed evaluation tasks.
- **Task Management:** Inspect task status, trigger retries for failed tasks, and clean up completed jobs with one click (**🧹 Clear Completed**).

#### ⚙️ Settings Tab
- **App URL Configuration:** Define the base target URL of your running Job Tracker instance (e.g. `http://localhost:5173` or direct backend `http://localhost:8000`).
- **Theme Selection:** Match your setup with `Daylight` (Warm Light), `Midnight` (Cyan Dark), or `System Default`.
- **Dock Behavior:** Choose between `Auto-Detect`, `Always On (All Websites)`, or `Disabled (Popup Only)`.
- **Badge Counter Interval:** Configure background polling frequency (15s, 30s, 1m, or manual).
- **Desktop Notifications:** Toggle OS-level desktop notifications upon task completion or failure.
- **Connection Diagnostics:** Built-in **🔌 Test Connection** button to verify communication with the server.

---

## 🔧 Backend Connection & Troubleshooting

### Recommended Connection URLs
Depending on how you run Job Tracker, configure the **Job Tracker App URL** in the extension Settings tab:

| Deployment Mode | Recommended URL | Description |
| :--- | :--- | :--- |
| **Development (`./dev.sh`)** | `http://localhost:5173` | Proxies through Vite dev server with Hot Module Reloading |
| **Production (`./prod.sh`)** | `http://localhost:4173` | Production Nginx web server reverse proxy |
| **Direct Backend API** | `http://localhost:8000` | Direct FastAPI server (when running standalone `uvicorn`) |
| **Docker Direct Backend** | `http://localhost:8008` | Direct backend port exposed in `docker-compose.yml` |

---

### Common Troubleshooting Steps

#### 1. "Cannot connect to Job Tracker server"
- Click **"Test Connection"** under the Settings tab.
- Verify that Job Tracker is running (`curl -f http://localhost:8000/health` or `curl -f http://localhost:5173/api/v1/health`).
- If running backend directly on `localhost:8000` or `localhost:8008`, ensure that URL is saved in Settings.

#### 2. Floating Dock is not appearing on a career page
- Check the **In-Page Floating Widget Mode** setting in the extension popup. If set to `Auto-Detect`, the URL must match known ATS hosts or career keywords.
- Change the mode to **`All Websites (Always On)`** to force the dock on any web page.
- Refresh the tab after updating extension settings.

#### 3. AI Provider Offline Warning
- If you see `⚠️ AI Provider Offline - Defaulted to Direct Applied mode`, your configured AI provider (e.g. Local LM Studio or Cloud API key) is unreachable.
- Direct Applied mode remains fully operational so you can continue logging applications without interruption.
- Open the Job Tracker web app and navigate to **Settings → AI Providers** to verify provider health.

#### 4. Inspecting Extension Logs
- **Popup Logs:** Right-click inside the popup window and click **Inspect** to view the JavaScript console.
- **Background Worker Logs:** Navigate to `chrome://extensions`, locate **Job Tracker Companion**, and click **"Inspect views: service worker"**.
- **In-Page Dock Logs:** Open Chrome DevTools on the target job page (`F12`) to inspect content script logs.
