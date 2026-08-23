/**
 * Job Tracker Companion Extension - Popup UI Controller
 */

import { getSettings, saveSettings, setSetting } from '../utils/storage.js';
import { testConnection, enqueueAssessment, clipJob, getEvaluations, normalizeApiUrl } from '../utils/api.js';

let extractedData = null;

document.addEventListener('DOMContentLoaded', async () => {
  await initSettingsUI();
  await checkBackendConnection();
  await extractActiveTab();
  setupEventListeners();
  updateQueueBadgeCount();
});

/**
 * Initializes settings input fields from storage.
 */
async function initSettingsUI() {
  const settings = await getSettings();

  const apiUrlInput = document.getElementById('input-api-url');
  const webAppUrlInput = document.getElementById('input-webapp-url');
  const pollSelect = document.getElementById('select-poll-interval');
  const notifToggle = document.getElementById('toggle-notifications');

  if (apiUrlInput) apiUrlInput.value = settings.apiBaseUrl || 'http://localhost:8000';
  if (webAppUrlInput) webAppUrlInput.value = settings.webAppUrl || 'http://localhost:5173';
  if (pollSelect) pollSelect.value = String(settings.pollInterval ?? 60);
  if (notifToggle) notifToggle.checked = settings.notificationsEnabled ?? true;

  // Set last selected ingestion mode
  const modeVal = settings.lastMode || 'AI_QUEUE';
  const modeRadio = document.querySelector(`input[name="ingestMode"][value="${modeVal}"]`);
  if (modeRadio) {
    modeRadio.checked = true;
    updateModeOptionStyles(modeVal);
  }
}

/**
 * Tests connection to backend and updates header pill.
 */
async function checkBackendConnection() {
  const connPill = document.getElementById('conn-pill');
  const connText = document.getElementById('conn-text');

  if (!connPill || !connText) return;

  connPill.className = 'conn-pill checking';
  connText.textContent = 'Checking...';

  const result = await testConnection();
  if (result.success) {
    connPill.className = 'conn-pill connected';
    connText.textContent = 'Connected';
  } else {
    connPill.className = 'conn-pill error';
    connText.textContent = 'Offline';
  }
}

/**
 * Injects DOM extractor script into active browser tab and populates input fields.
 */
async function extractActiveTab() {
  const siteBadge = document.getElementById('site-type-badge');
  const urlDisplay = document.getElementById('meta-url');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      if (siteBadge) siteBadge.textContent = 'No Active Tab';
      return;
    }

    if (urlDisplay) {
      urlDisplay.textContent = tab.url || 'Restricted Page';
      urlDisplay.title = tab.url || '';
    }

    // Check if URL is inject-able (not chrome://, edge://, file:// etc.)
    if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('edge://') || tab.url.startsWith('chrome-extension://')) {
      if (siteBadge) siteBadge.textContent = 'Internal Tab';
      return;
    }

    // Execute content/extractor.js in active tab
    const [executionResult] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content/extractor.js']
    });

    if (executionResult && executionResult.result) {
      extractedData = executionResult.result;

      if (siteBadge) {
        siteBadge.textContent = extractedData.site_type || 'GENERIC';
      }

      const compInput = document.getElementById('input-company');
      const posInput = document.getElementById('input-position');
      const locInput = document.getElementById('input-location');
      const salInput = document.getElementById('input-salary');

      if (compInput && extractedData.company) compInput.value = extractedData.company;
      if (posInput && extractedData.title) posInput.value = extractedData.title;
      if (locInput && extractedData.location) locInput.value = extractedData.location;
      if (salInput && extractedData.salary) salInput.value = extractedData.salary;
    }
  } catch (err) {
    console.warn('DOM extraction warning:', err);
    if (siteBadge) siteBadge.textContent = 'Generic Fallback';
  }
}

/**
 * Sets up popup event listeners.
 */
function setupEventListeners() {
  // Navigation Tabs
  document.querySelectorAll('.nav-tab').forEach((tabBtn) => {
    tabBtn.addEventListener('click', (e) => {
      const targetTab = e.currentTarget.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });

  // Ingestion Mode Option Styling & Persistence
  document.querySelectorAll('input[name="ingestMode"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      const selectedMode = e.target.value;
      updateModeOptionStyles(selectedMode);
      setSetting('lastMode', selectedMode);
    });
  });

  // Primary Submit Button
  const submitBtn = document.getElementById('btn-capture-submit');
  if (submitBtn) {
    submitBtn.addEventListener('click', handleCaptureSubmit);
  }

  // Refresh Queue
  const refreshQueueBtn = document.getElementById('btn-refresh-queue');
  if (refreshQueueBtn) {
    refreshQueueBtn.addEventListener('click', loadEvaluationsList);
  }

  // Test Connection Button in Settings
  const testConnBtn = document.getElementById('btn-test-conn');
  if (testConnBtn) {
    testConnBtn.addEventListener('click', async () => {
      const apiUrlInput = document.getElementById('input-api-url');
      const statusMsg = document.getElementById('settings-status');
      testConnBtn.disabled = true;

      const res = await testConnection(apiUrlInput ? apiUrlInput.value : null);
      testConnBtn.disabled = false;

      if (statusMsg) {
        statusMsg.classList.remove('hidden', 'success', 'error');
        if (res.success) {
          statusMsg.classList.add('success');
          statusMsg.textContent = res.message;
        } else {
          statusMsg.classList.add('error');
          statusMsg.textContent = `Error: ${res.message}`;
        }
      }
      await checkBackendConnection();
    });
  }

  // Save Settings Button
  const saveSettingsBtn = document.getElementById('btn-save-settings');
  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', async () => {
      const apiUrlInput = document.getElementById('input-api-url');
      const webAppUrlInput = document.getElementById('input-webapp-url');
      const pollSelect = document.getElementById('select-poll-interval');
      const notifToggle = document.getElementById('toggle-notifications');
      const statusMsg = document.getElementById('settings-status');

      const updated = {
        apiBaseUrl: normalizeApiUrl(apiUrlInput?.value || 'http://localhost:8000'),
        webAppUrl: normalizeApiUrl(webAppUrlInput?.value || 'http://localhost:5173'),
        pollInterval: parseInt(pollSelect?.value || '60', 10),
        notificationsEnabled: notifToggle?.checked ?? true
      };

      await saveSettings(updated);

      // Notify background worker of alarm interval change
      try {
        chrome.runtime.sendMessage({ type: 'SETTINGS_UPDATED', settings: updated });
      } catch (e) {
        // Ignore if worker dormant
      }

      if (statusMsg) {
        statusMsg.classList.remove('hidden', 'error');
        statusMsg.classList.add('success');
        statusMsg.textContent = 'Settings saved successfully!';
        setTimeout(() => statusMsg.classList.add('hidden'), 3000);
      }

      await checkBackendConnection();
    });
  }

  // Open in Tracker Button
  const openTrackerBtn = document.getElementById('btn-open-tracker');
  if (openTrackerBtn) {
    openTrackerBtn.addEventListener('click', async () => {
      const targetUrl = openTrackerBtn.getAttribute('data-url') || 'http://localhost:5173/applications';
      chrome.tabs.create({ url: targetUrl });
    });
  }
}

/**
 * Switches tab view.
 * @param {string} tabName
 */
function switchTab(tabName) {
  document.querySelectorAll('.nav-tab').forEach((btn) => {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
  });

  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `tab-${tabName}`);
  });

  if (tabName === 'queue') {
    loadEvaluationsList();
  }
}

/**
 * Updates mode option card highlight styling.
 * @param {string} selectedMode
 */
function updateModeOptionStyles(selectedMode) {
  const aiOpt = document.getElementById('mode-opt-ai');
  const directOpt = document.getElementById('mode-opt-direct');

  if (aiOpt) aiOpt.classList.toggle('active', selectedMode === 'AI_QUEUE');
  if (directOpt) directOpt.classList.toggle('active', selectedMode === 'DIRECT_APPLIED');
}

/**
 * Handles Capture & Send Job form submission.
 */
async function handleCaptureSubmit() {
  const compInput = document.getElementById('input-company');
  const posInput = document.getElementById('input-position');
  const locInput = document.getElementById('input-location');
  const salInput = document.getElementById('input-salary');
  const submitBtn = document.getElementById('btn-capture-submit');

  const company = compInput?.value?.trim() || '';
  const position = posInput?.value?.trim() || '';
  const location = locInput?.value?.trim() || '';
  const salary = salInput?.value?.trim() || '';

  if (!company || !position) {
    showStatusCard({
      type: 'error',
      title: 'Missing Required Fields',
      message: 'Please provide both Company Name and Job Title.'
    });
    return;
  }

  const selectedModeRadio = document.querySelector('input[name="ingestMode"]:checked');
  const ingestMode = selectedModeRadio ? selectedModeRadio.value : 'AI_QUEUE';

  submitBtn.disabled = true;
  showStatusCard({
    type: 'loading',
    title: 'Capturing Job Posting...',
    message: ingestMode === 'AI_QUEUE'
      ? 'Enqueuing raw DOM text into AI Evaluation Queue...'
      : 'Sending job directly to Applications board...'
  });

  const settings = await getSettings();
  const webAppUrl = settings.webAppUrl || 'http://localhost:5173';

  try {
    const rawText = extractedData?.description_text || `${company} - ${position}\nLocation: ${location}`;
    const jobUrl = extractedData?.url || '';

    if (ingestMode === 'AI_QUEUE') {
      const res = await enqueueAssessment({
        text: rawText,
        url: jobUrl,
        title_hint: `${company} - ${position}`
      });

      showStatusCard({
        type: 'success',
        title: 'Queued for AI Assessment! 🚀',
        message: `Task #${res.id} queued successfully. Our AI will analyze skill fit and pros/cons.`,
        actionUrl: `${webAppUrl}/assessments`
      });
      updateQueueBadgeCount();
    } else {
      const res = await clipJob({
        company,
        position,
        url: jobUrl,
        description: rawText,
        location,
        salary,
        status: 'APPLIED'
      });

      showStatusCard({
        type: 'success',
        title: 'Job Saved to Board! 📌',
        message: `Application recorded for ${company} - ${position} in stage APPLIED.`,
        actionUrl: `${webAppUrl}/applications`
      });
    }
  } catch (err) {
    showStatusCard({
      type: 'error',
      title: 'Submission Failed',
      message: err.message || 'Unable to communicate with Job Tracker backend.'
    });
  } finally {
    submitBtn.disabled = false;
  }
}

/**
 * Shows result feedback status card.
 */
function showStatusCard({ type, title, message, actionUrl }) {
  const card = document.getElementById('capture-status-card');
  const spinner = document.getElementById('status-spinner');
  const icon = document.getElementById('status-icon');
  const titleEl = document.getElementById('status-title');
  const msgEl = document.getElementById('status-message');
  const actionsEl = document.getElementById('status-actions');
  const openTrackerBtn = document.getElementById('btn-open-tracker');

  if (!card) return;

  card.classList.remove('hidden');

  if (type === 'loading') {
    spinner.classList.remove('hidden');
    icon.textContent = '';
  } else if (type === 'success') {
    spinner.classList.add('hidden');
    icon.textContent = '✅';
  } else {
    spinner.classList.add('hidden');
    icon.textContent = '⚠️';
  }

  if (titleEl) titleEl.textContent = title;
  if (msgEl) msgEl.textContent = message;

  if (actionUrl && openTrackerBtn) {
    actionsEl.classList.remove('hidden');
    openTrackerBtn.setAttribute('data-url', actionUrl);
  } else if (actionsEl) {
    actionsEl.classList.add('hidden');
  }
}

/**
 * Fetches recent evaluations and renders queue tab list.
 */
async function loadEvaluationsList() {
  const queueList = document.getElementById('queue-list');
  if (!queueList) return;

  queueList.innerHTML = '<div class="spinner" style="margin: 20px auto;"></div>';

  try {
    const tasks = await getEvaluations(20);

    if (!tasks || tasks.length === 0) {
      queueList.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📥</span>
          <p>No evaluation tasks found.</p>
        </div>
      `;
      return;
    }

    const settings = await getSettings();
    const webAppUrl = settings.webAppUrl || 'http://localhost:5173';

    queueList.innerHTML = tasks.map((task) => {
      const titleHint = task.title_hint || 'Job Assessment';
      const status = task.status || 'QUEUED';

      let fitScoreBadge = '';
      if (task.result_json && task.result_json.fit_score !== undefined) {
        fitScoreBadge = `<span class="fit-score-pill">${task.result_json.fit_score}% Fit</span>`;
      } else if (task.result_json && task.result_json.match_score !== undefined) {
        fitScoreBadge = `<span class="fit-score-pill">${task.result_json.match_score}% Fit</span>`;
      }

      const createdTime = task.created_at ? new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

      return `
        <div class="queue-item-card">
          <div class="queue-item-header">
            <div>
              <div class="queue-item-company">${escapeHtml(titleHint)}</div>
              <div class="queue-item-title">${escapeHtml(task.stage || status)}</div>
            </div>
            <span class="status-pill ${status}">${status}</span>
          </div>
          <div class="queue-item-footer">
            <span>${createdTime}</span>
            <div style="display: flex; gap: 6px; align-items: center;">
              ${fitScoreBadge}
              <button class="btn btn-secondary btn-sm open-app-link" data-url="${webAppUrl}/assessments">
                View
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Attach click listeners for item view buttons
    queueList.querySelectorAll('.open-app-link').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const targetUrl = e.currentTarget.getAttribute('data-url');
        chrome.tabs.create({ url: targetUrl });
      });
    });

    updateQueueBadgeCount(tasks);
  } catch (err) {
    queueList.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">⚠️</span>
        <p style="color: var(--danger-color);">Unable to load queue tasks: ${escapeHtml(err.message)}</p>
      </div>
    `;
  }
}

/**
 * Updates tab badge count based on active tasks.
 * @param {Array} [tasksList]
 */
async function updateQueueBadgeCount(tasksList) {
  const badgeEl = document.getElementById('queue-count-badge');
  if (!badgeEl) return;

  try {
    const tasks = tasksList || await getEvaluations(50);
    const activeCount = tasks.filter((t) => t.status === 'QUEUED' || t.status === 'RUNNING' || t.status === 'PROCESSING').length;

    if (activeCount > 0) {
      badgeEl.textContent = String(activeCount);
      badgeEl.classList.remove('hidden');
    } else {
      badgeEl.classList.add('hidden');
    }
  } catch (err) {
    badgeEl.classList.add('hidden');
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
