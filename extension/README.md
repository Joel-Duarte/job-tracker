# Job Tracker Companion Browser Extension

The **Job Tracker Companion** browser extension allows 1-click job posting capture, real-time AI fit assessment ingestion, and direct application tracking directly from your browser. It supports site-specific extraction rules for major job portals (LinkedIn, Glassdoor, Indeed, Greenhouse, Lever, Workday, Ashby) as well as a high-fidelity universal fallback parser for arbitrary career pages.

---

## 🚀 Installation Guide

### 🦊 Firefox (Gecko)
1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox` in the address bar.
2. Click **"Load Temporary Add-on..."**.
3. Navigate to the `extension/` directory and select `manifest.json`.
4. The Job Tracker Companion icon will appear in your Firefox toolbar, and the floating capture dock will automatically activate when visiting recognized job pages.

> **Note:** Temporary add-ons in Firefox remain active until the browser is restarted.

---

### 🌐 Chrome, Edge, Brave, and Arc (Chromium)
1. Open your browser and navigate to the extension management page:
   - **Chrome:** `chrome://extensions`
   - **Brave:** `brave://extensions`
   - **Edge:** `edge://extensions`
2. Enable **"Developer mode"** (toggle in the top-right corner).
3. Click **"Load unpacked"**.
4. Select the `extension/` directory located at the root of the Job Tracker repository.
5. The extension will be installed immediately.

---

## ✨ Features

- **Floating In-Page Dock:** Non-intrusive floating pill mounted on job pages with 1-click **Enqueue AI Assessment** and **Direct Applied** actions.
- **Smart Hybrid Extraction:** High-precision selectors for top career sites plus fallback page parsing.
- **Auto Theme Matching:** Light ("Daylight") and Dark ("Night") themes mirroring Job Tracker's UI.
- **Real-Time Badge Counter:** Background task status counter and Desktop OS notifications when AI evaluation completes.
- **Multi-Tab Extension Popup:** Dedicated Capture, AI Queue management (Cancel, Retry, Delete), and Backend Settings tabs.

---

## 🔧 Configuration

By default, the extension connects to the local backend API at `http://localhost:8000`. You can update the backend host URL at any time via the **Settings** tab in the extension popup.
