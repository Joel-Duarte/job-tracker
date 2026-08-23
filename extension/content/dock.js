/**
 * Job Tracker Companion Extension - In-Page Floating Shadow DOM Dock
 */

(function initJobTrackerDock() {
  if (window.__JOB_TRACKER_DOCK_LOADED__) return;
  window.__JOB_TRACKER_DOCK_LOADED__ = true;

  const DOCK_ID = 'job-tracker-dock-host';
  let shadowRoot = null;
  let currentSettings = {
    appUrl: 'http://localhost:5173',
    dockMode: 'AUTO-DETECT',
    theme: 'LIGHT',
    lastMode: 'AI_QUEUE'
  };

  const ATS_HOSTS = [
    'linkedin.com',
    'greenhouse.io',
    'lever.co',
    'myworkdayjobs.com',
    'workday.com',
    'ashbyhq.com',
    'indeed.com'
  ];

  const JOB_URL_KEYWORDS = [
    '/careers',
    '/jobs',
    '/job/',
    '/openings',
    '/positions',
    '/apply',
    'careers.',
    'jobs.'
  ];

  /**
   * Evaluates if floating dock should mount on active page based on dockMode.
   */
  function shouldMountDock(mode) {
    if (mode === 'OFF') return false;
    if (mode === 'ALL_PAGES') return true;

    // AUTO-DETECT logic
    const host = window.location.hostname.toLowerCase();
    const href = window.location.href.toLowerCase();

    const isAtsHost = ATS_HOSTS.some((ats) => host.includes(ats));
    if (isAtsHost) return true;

    const hasJobKeyword = JOB_URL_KEYWORDS.some((kw) => href.includes(kw));
    return hasJobKeyword;
  }

  /**
   * Reads settings from extension storage or message.
   */
  async function loadSettings() {
    return new Promise((resolve) => {
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(
          {
            appUrl: 'http://localhost:5173',
            dockMode: 'AUTO-DETECT',
            theme: 'LIGHT',
            lastMode: 'AI_QUEUE'
          },
          (res) => {
            currentSettings = { ...currentSettings, ...res };
            resolve(currentSettings);
          }
        );
      } else {
        resolve(currentSettings);
      }
    });
  }

  /**
   * Extracts job data using page DOM.
   */
  function extractPageJobData() {
    const docTitle = document.title || '';
    const h1 = document.querySelector('h1')?.textContent?.trim() || '';
    const cleanUrl = window.location.href;

    // Fallback extraction
    let title = h1 || docTitle;
    let company = document.querySelector('meta[property="og:site_name"]')?.content || '';

    if (!company && docTitle.includes(' at ')) {
      company = docTitle.split(' at ')[1].split(' ')[0];
    } else if (!company && docTitle.includes(' - ')) {
      const parts = docTitle.split(' - ');
      company = parts[parts.length - 1];
    }

    if (!company) company = 'Job Posting';

    const descEl = document.querySelector('article, main, #job-description, .job-description, body') || document.body;
    const bodyText = descEl ? descEl.textContent.substring(0, 15000) : '';

    return {
      url: cleanUrl,
      title: title.substring(0, 100),
      company: company.substring(0, 60),
      description_text: bodyText,
      location: '',
      salary: ''
    };
  }

  /**
   * Mounts or removes Shadow DOM floating dock widget.
   */
  async function renderDockUI() {
    await loadSettings();

    const mount = shouldMountDock(currentSettings.dockMode);
    let hostEl = document.getElementById(DOCK_ID);

    if (!mount) {
      if (hostEl) hostEl.remove();
      return;
    }

    if (!hostEl) {
      hostEl = document.createElement('div');
      hostEl.id = DOCK_ID;
      hostEl.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 2147483647; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;';
      document.body.appendChild(hostEl);
      shadowRoot = hostEl.attachShadow({ mode: 'open' });
    } else {
      shadowRoot = hostEl.shadowRoot;
    }

    const jobData = extractPageJobData();
    let themeAttr = 'light';
    if (currentSettings.theme === 'DARK') {
      themeAttr = 'dark';
    } else if (currentSettings.theme === 'SYSTEM') {
      themeAttr = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    shadowRoot.innerHTML = `
      <style>
        :host {
          all: initial;
        }

        .dock-wrapper {
          --bg: ${themeAttr === 'dark' ? '#1e293b' : '#ffffff'};
          --text: ${themeAttr === 'dark' ? '#f8fafc' : '#0f172a'};
          --muted: ${themeAttr === 'dark' ? '#94a3b8' : '#64748b'};
          --border: ${themeAttr === 'dark' ? '#334155' : '#e2e8f0'};
          --primary: ${themeAttr === 'dark' ? '#6366f1' : '#4f46e5'};
          --input-bg: ${themeAttr === 'dark' ? '#0f172a' : '#f8fafc'};
          --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1);

          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          font-size: 13px;
          color: var(--text);
        }

        .pill-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: var(--primary);
          color: #ffffff;
          border-radius: 30px;
          box-shadow: var(--shadow);
          cursor: pointer;
          font-weight: 700;
          font-size: 13px;
          border: none;
          transition: transform 0.2s ease;
        }

        .pill-btn:hover {
          transform: translateY(-2px);
        }

        .dock-card {
          width: 320px;
          background: var(--bg);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 16px;
          box-shadow: var(--shadow);
          display: flex;
          flex-direction: column;
          gap: 12px;
          animation: slideUp 0.2s ease-out;
        }

        .dock-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid var(--border);
          padding-bottom: 8px;
        }

        .dock-title {
          font-weight: 700;
          font-size: 14px;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .close-btn {
          background: transparent;
          border: none;
          cursor: pointer;
          color: var(--muted);
          font-size: 16px;
          padding: 2px 6px;
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .input-group label {
          font-size: 11px;
          font-weight: 600;
          color: var(--muted);
        }

        .dock-input {
          width: 100%;
          padding: 7px 10px;
          background: var(--input-bg);
          border: 1px solid var(--border);
          border-radius: 6px;
          color: var(--text);
          font-size: 12px;
          box-sizing: border-color 0.2s ease;
        }

        .dock-input:focus {
          outline: none;
          border-color: var(--primary);
        }

        .mode-row {
          display: flex;
          gap: 8px;
        }

        .mode-chip {
          flex: 1;
          padding: 6px 8px;
          border: 1px solid var(--border);
          border-radius: 6px;
          text-align: center;
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          background: var(--input-bg);
          color: var(--muted);
        }

        .mode-chip.active {
          border-color: var(--primary);
          color: var(--primary);
          background: rgba(79, 70, 229, 0.1);
        }

        .submit-btn {
          width: 100%;
          padding: 9px;
          background: var(--primary);
          color: #ffffff;
          border: none;
          border-radius: 6px;
          font-weight: 700;
          font-size: 12px;
          cursor: pointer;
          margin-top: 4px;
        }

        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .dock-status {
          font-size: 11px;
          padding: 6px 8px;
          border-radius: 6px;
          text-align: center;
        }

        .dock-status.success {
          background: rgba(16, 185, 129, 0.15);
          color: #059669;
        }

        .dock-status.error {
          background: rgba(239, 68, 68, 0.15);
          color: #dc2626;
        }

        .hidden { display: none !important; }

        @keyframes slideUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      </style>

      <div class="dock-wrapper">
        <button id="dock-pill-btn" class="pill-btn">
          💼 Job Tracker
        </button>

        <div id="dock-card-view" class="dock-card hidden">
          <div class="dock-header">
            <span class="dock-title">💼 Job Tracker Capture</span>
            <button id="dock-close-btn" class="close-btn">✕</button>
          </div>

          <div class="input-group">
            <label>Company Name</label>
            <input type="text" id="dock-input-company" class="dock-input" value="${escapeHtml(jobData.company)}">
          </div>

          <div class="input-group">
            <label>Job Title</label>
            <input type="text" id="dock-input-position" class="dock-input" value="${escapeHtml(jobData.title)}">
          </div>

          <div class="input-group">
            <label>Ingestion Mode</label>
            <div class="mode-row">
              <div id="chip-ai" class="mode-chip ${currentSettings.lastMode === 'AI_QUEUE' ? 'active' : ''}">🤖 AI Queue</div>
              <div id="chip-direct" class="mode-chip ${currentSettings.lastMode === 'DIRECT_APPLIED' ? 'active' : ''}">📌 Applied</div>
            </div>
          </div>

          <button id="dock-submit-btn" class="submit-btn">🚀 Capture & Send Job</button>

          <div id="dock-status-msg" class="dock-status hidden"></div>
        </div>
      </div>
    `;

    setupDockEventListeners(jobData);
  }

  function setupDockEventListeners(jobData) {
    if (!shadowRoot) return;

    const pillBtn = shadowRoot.getElementById('dock-pill-btn');
    const cardView = shadowRoot.getElementById('dock-card-view');
    const closeBtn = shadowRoot.getElementById('dock-close-btn');
    const chipAi = shadowRoot.getElementById('chip-ai');
    const chipDirect = shadowRoot.getElementById('chip-direct');
    const submitBtn = shadowRoot.getElementById('dock-submit-btn');
    const statusMsg = shadowRoot.getElementById('dock-status-msg');

    let selectedMode = currentSettings.lastMode || 'AI_QUEUE';

    pillBtn.addEventListener('click', () => {
      pillBtn.classList.add('hidden');
      cardView.classList.remove('hidden');
    });

    closeBtn.addEventListener('click', () => {
      cardView.classList.add('hidden');
      pillBtn.classList.remove('hidden');
    });

    chipAi.addEventListener('click', () => {
      selectedMode = 'AI_QUEUE';
      chipAi.classList.add('active');
      chipDirect.classList.remove('active');
    });

    chipDirect.addEventListener('click', () => {
      selectedMode = 'DIRECT_APPLIED';
      chipDirect.classList.add('active');
      chipAi.classList.remove('active');
    });

    submitBtn.addEventListener('click', async () => {
      const compInput = shadowRoot.getElementById('dock-input-company');
      const posInput = shadowRoot.getElementById('dock-input-position');

      const company = compInput?.value?.trim() || '';
      const position = posInput?.value?.trim() || '';

      if (!company || !position) {
        statusMsg.className = 'dock-status error';
        statusMsg.textContent = 'Please fill in Company and Position.';
        statusMsg.classList.remove('hidden');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending...';
      statusMsg.classList.add('hidden');

      const baseUrl = currentSettings.appUrl.replace(/\/+$/, '');

      try {
        if (selectedMode === 'AI_QUEUE') {
          const res = await fetch(`${baseUrl}/api/v1/intake/enqueue-assessment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: jobData.description_text,
              url: jobData.url,
              title_hint: `${company} - ${position}`
            })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          statusMsg.className = 'dock-status success';
          statusMsg.textContent = 'Queued in Job Tracker! 🚀';
        } else {
          const res = await fetch(`${baseUrl}/api/v1/extension/clip-job`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              company,
              position,
              url: jobData.url,
              description: jobData.description_text,
              status: 'APPLIED'
            })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          statusMsg.className = 'dock-status success';
          statusMsg.textContent = 'Saved to Applications! 📌';
        }
        statusMsg.classList.remove('hidden');

        setTimeout(() => {
          cardView.classList.add('hidden');
          pillBtn.classList.remove('hidden');
          submitBtn.disabled = false;
          submitBtn.textContent = '🚀 Capture & Send Job';
          statusMsg.classList.add('hidden');
        }, 2000);
      } catch (err) {
        statusMsg.className = 'dock-status error';
        statusMsg.textContent = `Error: ${err.message || 'Cannot reach server'}`;
        statusMsg.classList.remove('hidden');
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 Capture & Send Job';
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Listen for setting changes
  if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === 'SETTINGS_UPDATED') {
        renderDockUI();
      }
    });
  }

  renderDockUI();
})();
