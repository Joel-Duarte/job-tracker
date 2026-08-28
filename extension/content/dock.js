/**
 * Job Tracker Companion Extension - In-Page Floating Shadow DOM Dock
 */

(function initJobTrackerDock() {
  if (window.__JOB_TRACKER_DOCK_LOADED__) return;
  window.__JOB_TRACKER_DOCK_LOADED__ = true;

  const DOCK_ID = 'job-tracker-dock-host';
  let shadowRoot = null;
  let lastObservedUrl = window.location.href;
  let glassdoorObserver = null;
  let currentJobData = null;
  let isPillDragging = false;
  let currentSettings = {
    appUrl: 'http://localhost:4173',
    dockMode: 'AUTO-DETECT',
    dockExpanded: true,
    dockPosition: null,
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
    'indeed.com',
    'glassdoor.com',
    'glassdoor.co.uk'
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

  function shouldMountDock(mode) {
    if (mode === 'OFF') return false;
    if (mode === 'ALL_PAGES') return true;

    const host = window.location.hostname.toLowerCase();
    const href = window.location.href.toLowerCase();

    const isAtsHost = ATS_HOSTS.some((ats) => host.includes(ats));
    if (isAtsHost) return true;

    const hasJobKeyword = MULTI_LANG_JOB_KEYWORDS.some((kw) => href.includes(kw));
    return hasJobKeyword;
  }

  async function loadSettings() {
    return new Promise((resolve) => {
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(
          {
            appUrl: 'http://localhost:4173',
            dockMode: 'AUTO-DETECT',
            dockExpanded: true,
            dockPosition: null,
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
   * Unified Extractor Call (Single source of truth via extractor.js)
   */
  function extractPageJobData() {
    if (typeof window.__JOB_TRACKER_EXTRACT__ === 'function') {
      return window.__JOB_TRACKER_EXTRACT__();
    }
    return {
      url: window.location.href,
      title: document.title || 'Job Posting',
      company: 'Job Posting',
      description_text: document.body ? document.body.textContent.substring(0, 10000) : '',
      location: '',
      salary: '',
      work_model: 'Unknown',
      site_type: 'GENERIC'
    };
  }

  /**
   * Mounts or updates Shadow DOM floating dock widget.
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

      if (currentSettings.dockPosition && typeof currentSettings.dockPosition.top === 'number' && typeof currentSettings.dockPosition.left === 'number') {
        hostEl.style.cssText = `position: fixed; top: ${currentSettings.dockPosition.top}px; left: ${currentSettings.dockPosition.left}px; bottom: auto; right: auto; z-index: 2147483647; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;`;
      } else {
        hostEl.style.cssText = 'position: fixed; bottom: 24px; right: 24px; top: auto; left: auto; z-index: 2147483647; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;';
      }

      document.body.appendChild(hostEl);
      shadowRoot = hostEl.attachShadow({ mode: 'open' });
    } else {
      if (currentSettings.dockPosition && typeof currentSettings.dockPosition.top === 'number' && typeof currentSettings.dockPosition.left === 'number') {
        hostEl.style.top = `${currentSettings.dockPosition.top}px`;
        hostEl.style.left = `${currentSettings.dockPosition.left}px`;
        hostEl.style.bottom = 'auto';
        hostEl.style.right = 'auto';
      }
      shadowRoot = hostEl.shadowRoot;
    }

    currentJobData = extractPageJobData();
    let isDark = false;
    if (currentSettings.theme === 'DARK') {
      isDark = true;
    } else if (currentSettings.theme === 'SYSTEM') {
      isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    const primaryColor = isDark ? '#2dd4bf' : '#854d0e';
    const bgColor = isDark ? '#18181b' : '#ede3d5';
    const textColor = isDark ? '#f4f4f5' : '#1c1917';
    const mutedColor = isDark ? '#a1a1aa' : '#78716c';
    const borderColor = isDark ? '#27272a' : '#dcd1c4';
    const inputBg = isDark ? '#09090b' : '#faf6f0';
    const activeChipBg = isDark ? '#27272a' : '#dfd3c3';
    const activeChipBorder = isDark ? '1.5px solid #2dd4bf' : '1.5px solid #854d0e';
    const activeChipColor = isDark ? '#2dd4bf' : '#854d0e';

    let currentMode = currentSettings.lastMode || 'AI_QUEUE';
    const isExpanded = currentSettings.dockExpanded !== false;

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
          cursor: grab;
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
          cursor: grab;
          transition: background-color 0.3s ease;
        }

        .dock-header.sync-flash {
          background-color: ${activeChipBg};
          border-radius: 6px;
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

        .input-row-half {
          display: flex;
          gap: 6px;
          width: 100%;
        }

        .input-row-half .input-group {
          flex: 1;
        }

        .input-with-clear {
          position: relative;
          display: flex;
          align-items: center;
          width: 100%;
        }

        .dock-input {
          width: 100% !important;
          max-width: 100% !important;
          padding: 7px 24px 7px 9px;
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

        .dock-select {
          width: 100% !important;
          max-width: 100% !important;
          padding: 7px 9px;
          background: ${inputBg};
          border: 1px solid ${borderColor};
          border-radius: 6px;
          color: ${textColor};
          font-size: 12px;
        }

        .clear-btn-inline {
          position: absolute;
          right: 6px;
          background: transparent;
          border: none;
          color: ${mutedColor};
          cursor: pointer;
          font-size: 11px;
          padding: 2px;
        }

        .clear-btn-inline:hover {
          color: ${textColor};
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
          border: ${activeChipBorder};
          color: ${activeChipColor};
          background: ${activeChipBg};
          font-weight: 700;
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
        <!-- Collapsed Pill Button -->
        <button id="dock-pill-btn" class="pill-btn ${isExpanded ? 'hidden' : ''}">
          💼 Job Tracker
        </button>

        <!-- Card View -->
        <div id="dock-card-view" class="dock-card ${isExpanded ? '' : 'hidden'}">
          <div id="dock-header-el" class="dock-header">
            <span class="dock-title">💼 Job Tracker Capture</span>
            <div class="header-actions">
              <button id="dock-rescan-btn" class="ctrl-btn" title="Re-scan job details from page">🔄</button>
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

          <!-- Dynamic Ingestion Mode Container (Full 5 Fields in Applied Mode) -->
          <div id="mode-fields-direct" class="${currentMode === 'AI_QUEUE' ? 'hidden' : ''}">
            <div class="input-group" style="margin-bottom: 6px;">
              <label>Company Name</label>
              <div class="input-with-clear">
                <input type="text" id="dock-input-company" class="dock-input" value="${escapeHtml(currentJobData.company)}">
                <button class="clear-btn-inline" data-target="dock-input-company" title="Clear">✕</button>
              </div>
            </div>

            <div class="input-group" style="margin-bottom: 6px;">
              <label>Job Title</label>
              <div class="input-with-clear">
                <input type="text" id="dock-input-position" class="dock-input" value="${escapeHtml(currentJobData.title)}">
                <button class="clear-btn-inline" data-target="dock-input-position" title="Clear">✕</button>
              </div>
            </div>

            <div class="input-row-half" style="margin-bottom: 6px;">
              <div class="input-group">
                <label>Location</label>
                <div class="input-with-clear">
                  <input type="text" id="dock-input-location" class="dock-input" value="${escapeHtml(currentJobData.location)}">
                  <button class="clear-btn-inline" data-target="dock-input-location" title="Clear">✕</button>
                </div>
              </div>

              <div class="input-group">
                <label>Salary</label>
                <div class="input-with-clear">
                  <input type="text" id="dock-input-salary" class="dock-input" value="${escapeHtml(currentJobData.salary)}">
                  <button class="clear-btn-inline" data-target="dock-input-salary" title="Clear">✕</button>
                </div>
              </div>
            </div>

            <div class="input-group">
              <label>Work Model</label>
              <select id="dock-select-work-model" class="dock-select">
                <option value="Unknown" ${currentJobData.work_model === 'Unknown' ? 'selected' : ''}>Unknown</option>
                <option value="Remote" ${currentJobData.work_model === 'Remote' ? 'selected' : ''}>Remote</option>
                <option value="Hybrid" ${currentJobData.work_model === 'Hybrid' ? 'selected' : ''}>Hybrid</option>
                <option value="On-site" ${currentJobData.work_model === 'On-site' ? 'selected' : ''}>On-site</option>
              </select>
            </div>
          </div>

          <button id="dock-submit-btn" class="submit-btn">
            ${currentMode === 'AI_QUEUE' ? '⚡ Send Page to AI Assessment' : '🚀 Save Application'}
          </button>

          <div id="dock-status-msg" class="dock-status hidden"></div>
        </div>
      </div>
    `;

    setupDockEventListeners();
    setupDraggable(hostEl);
    checkFloatingAiHealthGating();
    scheduleHydrationRetries();
  }

  /**
   * Attaches drag handlers to pill and header for persistent drag positioning.
   */
  function setupDraggable(hostEl) {
    if (!shadowRoot) return;
    const pillBtn = shadowRoot.getElementById('dock-pill-btn');
    const headerEl = shadowRoot.getElementById('dock-header-el');

    if (pillBtn) enableDraggable(pillBtn, hostEl, true);
    if (headerEl) enableDraggable(headerEl, hostEl, false);
  }

  function enableDraggable(handleEl, hostEl, isPill = false) {
    let isDragging = false;
    let startX, startY, initialLeft, initialTop;
    let hasMoved = false;

    handleEl.style.cursor = 'grab';

    handleEl.addEventListener('mousedown', (e) => {
      if (e.target.closest('button:not(#dock-pill-btn)')) return;

      isDragging = true;
      hasMoved = false;
      if (isPill) isPillDragging = false;

      startX = e.clientX;
      startY = e.clientY;

      const rect = hostEl.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;

      handleEl.style.cursor = 'grabbing';
      document.body.style.userSelect = 'none';

      function onMouseMove(me) {
        if (!isDragging) return;
        const dx = me.clientX - startX;
        const dy = me.clientY - startY;

        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          hasMoved = true;
          if (isPill) isPillDragging = true;
        }

        if (hasMoved) {
          let newLeft = Math.max(10, Math.min(window.innerWidth - hostEl.offsetWidth - 10, initialLeft + dx));
          let newTop = Math.max(10, Math.min(window.innerHeight - hostEl.offsetHeight - 10, initialTop + dy));

          hostEl.style.top = `${newTop}px`;
          hostEl.style.left = `${newLeft}px`;
          hostEl.style.bottom = 'auto';
          hostEl.style.right = 'auto';
        }
      }

      function onMouseUp() {
        if (!isDragging) return;
        isDragging = false;
        handleEl.style.cursor = 'grab';
        document.body.style.userSelect = '';

        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);

        if (hasMoved) {
          const rect = hostEl.getBoundingClientRect();
          const pos = { top: rect.top, left: rect.left };
          if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
            chrome.storage.local.set({ dockPosition: pos });
          }
        }
      }

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    });
  }

  function scheduleHydrationRetries() {
    setTimeout(syncJobDetailsLive, 400);
    setTimeout(syncJobDetailsLive, 1000);
  }

  function checkFloatingAiHealthGating() {
    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id) {
      chrome.runtime.sendMessage({ type: 'TEST_CONNECTION' }, (response) => {
        if (!shadowRoot) return;
        const chipAi = shadowRoot.getElementById('chip-ai');
        const chipDirect = shadowRoot.getElementById('chip-direct');
        const modeFieldsDirect = shadowRoot.getElementById('mode-fields-direct');
        const submitBtn = shadowRoot.getElementById('dock-submit-btn');

        const aiReady = (response && response.success && response.data && response.data.config)
          ? response.data.config.ai_ready
          : true;

        if (aiReady === false) {
          if (chipAi) {
            chipAi.style.opacity = '0.5';
            chipAi.style.pointerEvents = 'none';
            chipAi.title = 'AI Provider Offline in Job Tracker';
            chipAi.classList.remove('active');
          }
          if (chipDirect) chipDirect.classList.add('active');
          if (modeFieldsDirect) modeFieldsDirect.classList.remove('hidden');
          if (submitBtn) submitBtn.textContent = '🚀 Save Application';
        }
      });
    }
  }

  function setupDockEventListeners() {
    if (!shadowRoot) return;

    const pillBtn = shadowRoot.getElementById('dock-pill-btn');
    const cardView = shadowRoot.getElementById('dock-card-view');
    const rescanBtn = shadowRoot.getElementById('dock-rescan-btn');
    const minBtn = shadowRoot.getElementById('dock-minimize-btn');
    const closeBtn = shadowRoot.getElementById('dock-close-btn');
    const chipAi = shadowRoot.getElementById('chip-ai');
    const chipDirect = shadowRoot.getElementById('chip-direct');
    const modeFieldsDirect = shadowRoot.getElementById('mode-fields-direct');
    const submitBtn = shadowRoot.getElementById('dock-submit-btn');
    const statusMsg = shadowRoot.getElementById('dock-status-msg');

    let selectedMode = currentSettings.lastMode || 'AI_QUEUE';

    if (rescanBtn) {
      rescanBtn.addEventListener('click', () => {
        syncJobDetailsLive();
        statusMsg.className = 'dock-status success';
        statusMsg.textContent = 'Page re-scanned! ✨';
        statusMsg.classList.remove('hidden');
        setTimeout(() => statusMsg.classList.add('hidden'), 1200);
      });
    }

    shadowRoot.querySelectorAll('.clear-btn-inline').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = btn.getAttribute('data-target');
        if (targetId) {
          const inputEl = shadowRoot.getElementById(targetId);
          if (inputEl) {
            inputEl.value = '';
            inputEl.focus();
          }
        }
      });
    });

    pillBtn.addEventListener('click', () => {
      if (isPillDragging) {
        isPillDragging = false;
        return;
      }
      pillBtn.classList.add('hidden');
      cardView.classList.remove('hidden');
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ dockExpanded: true });
      }
    });

    minBtn.addEventListener('click', () => {
      cardView.classList.add('hidden');
      pillBtn.classList.remove('hidden');
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ dockExpanded: false });
      }
    });

    closeBtn.addEventListener('click', () => {
      cardView.classList.add('hidden');
      pillBtn.classList.remove('hidden');
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ dockExpanded: false });
      }
    });

    chipAi.addEventListener('click', () => {
      selectedMode = 'AI_QUEUE';
      chipAi.classList.add('active');
      chipDirect.classList.remove('active');
      modeFieldsDirect.classList.add('hidden');
      submitBtn.textContent = '⚡ Send Page to AI Assessment';
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ lastMode: 'AI_QUEUE' });
      }
    });

    chipDirect.addEventListener('click', () => {
      selectedMode = 'DIRECT_APPLIED';
      chipDirect.classList.add('active');
      chipAi.classList.remove('active');
      modeFieldsDirect.classList.remove('hidden');
      submitBtn.textContent = '🚀 Save Application';
      if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.set({ lastMode: 'DIRECT_APPLIED' });
      }
    });

    submitBtn.addEventListener('click', async () => {
      const compInput = shadowRoot.getElementById('dock-input-company');
      const posInput = shadowRoot.getElementById('dock-input-position');
      const locInput = shadowRoot.getElementById('dock-input-location');
      const salInput = shadowRoot.getElementById('dock-input-salary');
      const wmSelect = shadowRoot.getElementById('dock-select-work-model');

      const company = compInput?.value?.trim() || currentJobData.company || 'Job Posting';
      const position = posInput?.value?.trim() || currentJobData.title || 'Unknown Position';
      const location = locInput?.value?.trim() || currentJobData.location || '';
      const salary = salInput?.value?.trim() || currentJobData.salary || '';
      const work_model = wmSelect?.value || currentJobData.work_model || 'Unknown';

      submitBtn.disabled = true;

      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id) {
        if (selectedMode === 'AI_QUEUE') {
          statusMsg.className = 'dock-status success';
          statusMsg.textContent = '✅ Queued for AI Assessment!';
          statusMsg.classList.remove('hidden');

          const titleHint = (company && position && company !== 'Job Posting')
            ? `${company} - ${position}`
            : (document.title?.trim() || position || 'Job Lead');

          chrome.runtime.sendMessage(
            {
              type: 'ENQUEUE_JOB',
              payload: {
                text: currentJobData.description_text,
                url: currentJobData.url,
                title_hint: titleHint.slice(0, 80)
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
          statusMsg.className = 'dock-status success';
          statusMsg.textContent = '✅ Saved to Applied!';
          statusMsg.classList.remove('hidden');

          chrome.runtime.sendMessage(
            {
              type: 'CLIP_JOB',
              payload: {
                company,
                position,
                url: currentJobData.url,
                description: currentJobData.description_text,
                location,
                salary,
                work_model,
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
      }

      setTimeout(() => {
        cardView.classList.add('hidden');
        pillBtn.classList.remove('hidden');
        submitBtn.disabled = false;
        statusMsg.classList.add('hidden');
      }, 1500);
    });
  }

  function setupSpaSelectionSync() {
    function handleLocationOrJobChange() {
      const currentUrl = window.location.href;
      if (currentUrl !== lastObservedUrl) {
        lastObservedUrl = currentUrl;
        triggerDelayedSyncs();
      }
    }

    function triggerDelayedSyncs() {
      syncJobDetailsLive();
      setTimeout(syncJobDetailsLive, 250);
      setTimeout(syncJobDetailsLive, 600);
    }

    window.addEventListener('popstate', handleLocationOrJobChange);
    window.addEventListener('hashchange', handleLocationOrJobChange);

    setInterval(handleLocationOrJobChange, 500);

    const host = window.location.hostname.toLowerCase();
    if (host.includes('glassdoor.com') || host.includes('glassdoor.co.uk') || host.includes('indeed.com')) {
      const targetContainer = document.querySelector('#JobDescriptionContainer, #jobsearch-ViewjobPaneWrapper, body');
      if (targetContainer) {
        glassdoorObserver = new MutationObserver(() => {
          triggerDelayedSyncs();
        });
        glassdoorObserver.observe(targetContainer, { childList: true, subtree: true });
      }

      document.addEventListener('click', (e) => {
        if (e.target.closest('[data-test="jobListing"], [data-test="job-details"], .JobsList_jobListItem__, .jobsearch-ResultsList')) {
          triggerDelayedSyncs();
        }
      });
    }
  }

  function syncJobDetailsLive() {
    if (!shadowRoot) return;
    const freshJobData = extractPageJobData();

    currentJobData = freshJobData;

    const compInput = shadowRoot.getElementById('dock-input-company');
    const posInput = shadowRoot.getElementById('dock-input-position');
    const locInput = shadowRoot.getElementById('dock-input-location');
    const salInput = shadowRoot.getElementById('dock-input-salary');
    const wmSelect = shadowRoot.getElementById('dock-select-work-model');
    const headerEl = shadowRoot.getElementById('dock-header-el');

    if (compInput) compInput.value = freshJobData.company;
    if (posInput) posInput.value = freshJobData.title;
    if (locInput) locInput.value = freshJobData.location;
    if (salInput) salInput.value = freshJobData.salary;
    if (wmSelect) wmSelect.value = freshJobData.work_model;

    if (headerEl) {
      headerEl.classList.add('sync-flash');
      setTimeout(() => headerEl.classList.remove('sync-flash'), 600);
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === 'SETTINGS_UPDATED') {
        renderDockUI();
      }
    });
  }

  renderDockUI();
  setupSpaSelectionSync();
})();
