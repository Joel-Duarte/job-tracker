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

  const MULTI_LANG_JOB_KEYWORDS = [
    // English
    '/careers', '/jobs', '/job/', '/openings', '/positions', '/apply', 'careers.', 'jobs.',
    'engineer', 'software', 'developer', 'work-with-us', 'join-us',
    // Dutch
    'vacature', 'vacatures',
    // German
    'stellenangebot', 'stellenangebote', 'karriere',
    // French
    'emploi', 'recrutement', 'offres-emploi',
    // Portuguese & Spanish
    'vaga', 'vagas', 'empleo', 'trabajo', 'postulate'
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

    const hasJobKeyword = MULTI_LANG_JOB_KEYWORDS.some((kw) => href.includes(kw));
    return hasJobKeyword;
  }

  /**
   * Reads settings from extension storage.
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
    let isDark = false;
    if (currentSettings.theme === 'DARK') {
      isDark = true;
    } else if (currentSettings.theme === 'SYSTEM') {
      isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    const primaryColor = isDark ? '#2dd4bf' : '#854d0e'; // Cyan Dark / Saddle Light
    const bgColor = isDark ? '#18181b' : '#ffffff';
    const textColor = isDark ? '#f4f4f5' : '#0f172a';
    const mutedColor = isDark ? '#a1a1aa' : '#64748b';
    const borderColor = isDark ? '#27272a' : '#e2e8f0';
    const inputBg = isDark ? '#09090b' : '#f8fafc';

    const currentMode = currentSettings.lastMode || 'AI_QUEUE';

    shadowRoot.innerHTML = `
      <style>
        *, *::before, *::after {
          box-sizing: border-box !important;
        }

        :host {
          all: initial;
        }

        .dock-wrapper {
          width: 320px;
          max-width: 100%;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          font-size: 13px;
          color: ${textColor};
        }

        .pill-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: ${primaryColor};
          color: ${isDark ? '#09090b' : '#ffffff'};
          border-radius: 30px;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
          cursor: pointer;
          font-weight: 700;
          font-size: 13px;
          border: none;
          transition: transform 0.2s ease;
          margin-left: auto;
        }

        .pill-btn:hover {
          transform: translateY(-2px);
        }

        .dock-card {
          width: 100%;
          max-width: 100%;
          background: ${bgColor};
          border: 1px solid ${borderColor};
          border-radius: 14px;
          padding: 14px;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
          display: flex;
          flex-direction: column;
          gap: 10px;
          animation: slideUp 0.2s ease-out;
        }

        .dock-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid ${borderColor};
          padding-bottom: 8px;
          width: 100%;
        }

        .dock-title {
          font-weight: 700;
          font-size: 13px;
          display: flex;
          align-items: center;
          gap: 6px;
          color: ${textColor};
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .ctrl-btn {
          background: transparent;
          border: none;
          cursor: pointer;
          color: ${mutedColor};
          font-size: 14px;
          padding: 2px 6px;
          border-radius: 4px;
        }

        .ctrl-btn:hover {
          color: ${textColor};
          background: ${borderColor};
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
          width: 100%;
        }

        .input-group label {
          font-size: 11px;
          font-weight: 600;
          color: ${mutedColor};
        }

        .dock-input {
          width: 100% !important;
          max-width: 100% !important;
          padding: 8px 10px;
          background: ${inputBg};
          border: 1px solid ${borderColor};
          border-radius: 6px;
          color: ${textColor};
          font-size: 12px;
        }

        .dock-input:focus {
          outline: none;
          border-color: ${primaryColor};
        }

        .mode-row {
          display: flex;
          gap: 6px;
          width: 100%;
        }

        .mode-chip {
          flex: 1;
          padding: 7px 8px;
          border: 1px solid ${borderColor};
          border-radius: 6px;
          text-align: center;
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          background: ${inputBg};
          color: ${mutedColor};
        }

        .mode-chip.active {
          border-color: ${primaryColor};
          color: ${primaryColor};
          background: rgba(133, 77, 14, 0.12);
        }

        .submit-btn {
          width: 100% !important;
          padding: 10px;
          background: ${primaryColor};
          color: ${isDark ? '#09090b' : '#ffffff'};
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
          padding: 8px;
          border-radius: 6px;
          text-align: center;
          font-weight: 600;
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
        <button id="dock-pill-btn" class="pill-btn hidden">
          💼 Job Tracker
        </button>

        <div id="dock-card-view" class="dock-card">
          <div class="dock-header">
            <span class="dock-title">💼 Job Tracker Capture</span>
            <div class="header-actions">
              <button id="dock-minimize-btn" class="ctrl-btn" title="Minimize">—</button>
              <button id="dock-close-btn" class="ctrl-btn" title="Close">✕</button>
            </div>
          </div>

          <div class="input-group">
            <label>Ingestion Mode</label>
            <div class="mode-row">
              <div id="chip-ai" class="mode-chip ${currentMode === 'AI_QUEUE' ? 'active' : ''}">🤖 AI Queue</div>
              <div id="chip-direct" class="mode-chip ${currentMode === 'DIRECT_APPLIED' ? 'active' : ''}">📌 Applied</div>
            </div>
          </div>

          <!-- Dynamic Ingestion Mode Container -->
          <div id="mode-fields-direct" class="${currentMode === 'AI_QUEUE' ? 'hidden' : ''}">
            <div class="input-group" style="margin-bottom: 6px;">
              <label>Company Name</label>
              <input type="text" id="dock-input-company" class="dock-input" value="${escapeHtml(jobData.company)}">
            </div>

            <div class="input-group">
              <label>Job Title</label>
              <input type="text" id="dock-input-position" class="dock-input" value="${escapeHtml(jobData.title)}">
            </div>
          </div>

          <button id="dock-submit-btn" class="submit-btn">
            ${currentMode === 'AI_QUEUE' ? '⚡ Send Page to AI Assessment' : '🚀 Save Application'}
          </button>

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
    const minBtn = shadowRoot.getElementById('dock-minimize-btn');
    const closeBtn = shadowRoot.getElementById('dock-close-btn');
    const chipAi = shadowRoot.getElementById('chip-ai');
    const chipDirect = shadowRoot.getElementById('chip-direct');
    const modeFieldsDirect = shadowRoot.getElementById('mode-fields-direct');
    const submitBtn = shadowRoot.getElementById('dock-submit-btn');
    const statusMsg = shadowRoot.getElementById('dock-status-msg');

    let selectedMode = currentSettings.lastMode || 'AI_QUEUE';

    pillBtn.addEventListener('click', () => {
      pillBtn.classList.add('hidden');
      cardView.classList.remove('hidden');
    });

    minBtn.addEventListener('click', () => {
      cardView.classList.add('hidden');
      pillBtn.classList.remove('hidden');
    });

    closeBtn.addEventListener('click', () => {
      cardView.classList.add('hidden');
      pillBtn.classList.add('hidden');
    });

    chipAi.addEventListener('click', () => {
      selectedMode = 'AI_QUEUE';
      chipAi.classList.add('active');
      chipDirect.classList.remove('active');
      modeFieldsDirect.classList.add('hidden');
      submitBtn.textContent = '⚡ Send Page to AI Assessment';
    });

    chipDirect.addEventListener('click', () => {
      selectedMode = 'DIRECT_APPLIED';
      chipDirect.classList.add('active');
      chipAi.classList.remove('active');
      modeFieldsDirect.classList.remove('hidden');
      submitBtn.textContent = '🚀 Save Application';
    });

    submitBtn.addEventListener('click', async () => {
      const compInput = shadowRoot.getElementById('dock-input-company');
      const posInput = shadowRoot.getElementById('dock-input-position');

      const company = compInput?.value?.trim() || jobData.company || 'Job Posting';
      const position = posInput?.value?.trim() || jobData.title || 'Unknown Position';

      submitBtn.disabled = true;

      // Background Message Passing (no direct fetch)
      if (selectedMode === 'AI_QUEUE') {
        // Optimistic Instant Feedback
        statusMsg.className = 'dock-status success';
        statusMsg.textContent = '✅ Queued for AI Assessment!';
        statusMsg.classList.remove('hidden');

        chrome.runtime.sendMessage(
          {
            type: 'ENQUEUE_JOB',
            payload: {
              text: jobData.description_text,
              url: jobData.url,
              title_hint: `${company} - ${position}`
            }
          },
          (res) => {
            if (!res || !res.success) {
              statusMsg.className = 'dock-status error';
              statusMsg.textContent = `Error: ${res?.error || 'Failed to queue'}`;
              submitBtn.disabled = false;
            }
          }
        );
      } else {
        // Optimistic Instant Feedback for Direct Clip
        statusMsg.className = 'dock-status success';
        statusMsg.textContent = '✅ Saved to Applied!';
        statusMsg.classList.remove('hidden');

        chrome.runtime.sendMessage(
          {
            type: 'CLIP_JOB',
            payload: {
              company,
              position,
              url: jobData.url,
              description: jobData.description_text,
              status: 'APPLIED'
            }
          },
          (res) => {
            if (!res || !res.success) {
              statusMsg.className = 'dock-status error';
              statusMsg.textContent = `Error: ${res?.error || 'Failed to clip'}`;
              submitBtn.disabled = false;
            }
          }
        );
      }

      // Smooth 1.5s auto-collapse
      setTimeout(() => {
        cardView.classList.add('hidden');
        pillBtn.classList.remove('hidden');
        submitBtn.disabled = false;
        statusMsg.classList.add('hidden');
      }, 1500);
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

  if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === 'SETTINGS_UPDATED') {
        renderDockUI();
      }
    });
  }

  renderDockUI();
})();
