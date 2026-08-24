# Job Tracker Companion Chrome Web Store Submission & Developer Spec

## 1. Store Metadata

- **Extension Title:** Job Tracker Companion
- **Version:** 1.0.0
- **Short Summary (132 chars max):** 1-Click job description capture, AI fit assessment, and application tracking for Job Tracker.
- **Category:** Productivity / Workflow
- **Language:** English (United States)
- **Detailed Description:**
  > Streamline your job search with Job Tracker Companion. Capture job postings with 1-Click directly from your active browser tab across LinkedIn, Greenhouse, Lever, Workday, Ashby, Indeed, and custom career portals.
  >
  > Key Features:
  > - **1-Click Smart Hybrid DOM Capture:** Automatically extracts job title, company name, location, salary, and description from active tab context.
  > - **Zero-Ban Client-Side Extraction:** Reads rendered page markup locally in your browser with zero automated bot traffic footprint.
  > - **AI Fit Assessment Queue:** Routes captured jobs directly into Job Tracker's AI evaluation pipeline to score skill match, highlight pros/cons, and generate interview prep recommendations.
  > - **Direct Application Ingestion:** Instantly save clipped jobs to your Job Tracker Kanban board in stage APPLIED.
  > - **Real-Time Toolbar Badge Counter:** Monitor background evaluation tasks in real-time with automatic desktop notifications upon completion.
  > - **Self-Hosted & Privacy First:** Connects directly to your own Job Tracker server instance. Zero middleman telemetry or external tracking.

---

## 2. Permissions Justifications for Web Store Review Team

| Permission | Justification for Reviewer |
| :--- | :--- |
| `activeTab` | Required to inspect the current active tab when the user clicks the extension popup action button to extract job details (title, company, description). |
| `scripting` | Used exclusively to inject `content/extractor.js` into the active tab context upon explicit user button click to parse job markup. |
| `storage` | Required to store user configuration settings locally (configured Job Tracker backend URL, last-used ingestion mode, badge refresh interval). |
| `alarms` | Required to schedule periodic background wake-ups for the service worker to poll the user's Job Tracker server for AI evaluation progress. |
| `notifications` | Used to trigger native desktop alerts when an async background AI fit evaluation task finishes processing or encounters an error. |
| `<all_urls>` | Necessary to allow the extension to execute DOM extraction on arbitrary company career sites and send API requests to user-configured custom backend server URLs (e.g. `http://localhost:8000` or self-hosted IP domains). |

---

## 3. Privacy Policy & Data Handling Disclosure

1. **Local DOM Processing:** Page text extraction occurs entirely locally within the user's active browser context.
2. **User-Controlled Destination:** Captured job payloads are sent directly to the user's configured Job Tracker backend URL (`http://localhost:8000` or custom server).
3. **Zero Third-Party Telemetry:** Job Tracker Companion contains zero analytics, tracking scripts, ad pixels, or third-party diagnostic services.
4. **Data Isolation:** No user credentials or session cookies from target job portals are read, stored, or transmitted.

---

## 4. Developer Instructions (Load Unpacked)

### How to Install in Chrome / Edge / Brave
1. Clone the repository or navigate to the repository directory.
2. Open Chrome and navigate to `chrome://extensions`.
3. Enable **Developer mode** using the toggle switch in the upper-right corner.
4. Click **Load unpacked** in the top-left toolbar.
5. Select the `extension/` folder located at the root of the Job Tracker repository.
6. Click the extension icon in your browser toolbar to open the Job Tracker Companion popup.
7. Ensure your Job Tracker backend server is running (`http://localhost:4173`) and test connection in the **Settings** tab.
