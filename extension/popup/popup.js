/**
 * Job Tracker Companion Extension - Popup UI Controller
 */

import { getSettings, saveSettings, setSetting } from '../utils/storage.js';
import {
  testConnection,
  enqueueAssessment,
  clipJob,
  getEvaluations,
  cancelEvaluation,
  retryEvaluation,
  deleteEvaluation,
  clearCompletedEvaluations,
  normalizeAppUrl
} from '../utils/api.js';

let extractedData = null;
let countdownTimer = null;

document.addEventListener('DOMContentLoaded', async () => {
  await initSettingsAndTheme();
  await checkBackendConnection();
  await extractActiveTab();
  setupEventListeners();
  updateQueueBadgeCount();
});

/**
 * Initializes settings input fields and applies design theme.
 */
async function initSettingsAndTheme() {
  const settings = await getSettings();

  // Apply Theme
  applyTheme(settings.theme || 'LIGHT');

  const appUrlInput = document.getElementById('input-app-url');
  const themeSelect = document.getElementById('select-theme');
  const dockModeSelect = document.getElementById('select-dock-mode');
  const pollSelect = document.getElementById('select-poll-interval');
  const notifToggle = document.getElementById('toggle-notifications');

  if (appUrlInput) appUrlInput.value = settings.appUrl || 'http://localhost:5173';
  if (themeSelect) themeSelect.value = settings.theme || 'LIGHT';
  if (dockModeSelect) dockModeSelect.value = settings.dockMode || 'AUTO-DETECT';
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
 * Applies color theme to popup document element.
 * @param {'LIGHT'|'DARK'|'SYSTEM'} themeMode
 */
function applyTheme(themeMode) {
  let effectiveTheme = 'light';
  if (themeMode === 'DARK') {
    effectiveTheme = 'dark';
  } else if (themeMode === 'SYSTEM') {
    effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', effectiveTheme);
}

/**
 * Tests connection to backend via appUrl and updates header pill.
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

    if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('edge://') || tab.url.startsWith('chrome-extension://')) {
      if (siteBadge) siteBadge.textContent = 'Internal Tab';
      return;
    }

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
 * Sets up event listeners.
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

  // Theme Selector live preview
  const themeSelect = document.getElementById('select-theme');
  if (themeSelect) {
    themeSelect.addEventListener('change', (e) => {
      applyTheme(e.target.value);
    });
  }

  // Primary Submit Button
  const submitBtn = document.getElementById('btn-capture-submit');
  if (submitBtn) {
    submitBtn.addEventListener('click', handleCaptureSubmit);
  }

  // Feedback Screen Controls
  const openAppBtn = document.getElementById('btn-open-app-dashboard');
  if (openAppBtn) {
    openAppBtn.addEventListener('click', async () => {
      const targetUrl = openAppBtn.getAttribute('data-url') || 'http://localhost:5173/assessments';
      chrome.tabs.create({ url: targetUrl });
    });
  }

  const captureAnotherBtn = document.getElementById('btn-capture-another');
  if (captureAnotherBtn) {
    captureAnotherBtn.addEventListener('click', resetFeedbackScreen);
  }

  const tryAgainBtn = document.getElementById('btn-try-again');
  if (tryAgainBtn) {
    tryAgainBtn.addEventListener('click', resetFeedbackScreen);
  }

  // Refresh Queue Button
  const refreshQueueBtn = document.getElementById('btn-refresh-queue');
  if (refreshQueueBtn) {
    refreshQueueBtn.addEventListener('click', loadEvaluationsList);
  }

  // Clear Completed Queue Tasks Button
  const clearCompletedBtn = document.getElementById('btn-clear-completed');
  if (clearCompletedBtn) {
    clearCompletedBtn.addEventListener('click', async () => {
      clearCompletedBtn.disabled = true;
      try {
        await clearCompletedEvaluations();
        await loadEvaluationsList();
      } catch (e) {
        console.error('Failed clearing completed evaluations:', e);
      } finally {
        clearCompletedBtn.disabled = false;
      }
    });
  }

  // Test Connection Button in Settings
  const testConnBtn = document.getElementById('btn-test-conn');
  if (testConnBtn) {
    testConnBtn.addEventListener('click', async () => {
      const appUrlInput = document.getElementById('input-app-url');
      const statusMsg = document.getElementById('settings-status');
      testConnBtn.disabled = true;

      const res = await testConnection(appUrlInput ? appUrlInput.value : null);
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
      const appUrlInput = document.getElementById('input-app-url');
      const themeSel = document.getElementById('select-theme');
      const dockSel = document.getElementById('select-dock-mode');
      const pollSelect = document.getElementById('select-poll-interval');
      const notifToggle = document.getElementById('toggle-notifications');
      const statusMsg = document.getElementById('settings-status');

      const updated = {
        appUrl: normalizeAppUrl(appUrlInput?.value || 'http://localhost:5173'),
        theme: themeSel?.value || 'LIGHT',
        dockMode: dockSel?.value || 'AUTO-DETECT',
        pollInterval: parseInt(pollSelect?.value || '60', 10),
        notificationsEnabled: notifToggle?.checked ?? true
      };

      await saveSettings(updated);
      applyTheme(updated.theme);

      // Notify background worker and active tabs of setting updates
      try {
        chrome.runtime.sendMessage({ type: 'SETTINGS_UPDATED', settings: updated });
        const tabs = await chrome.tabs.query({});
        tabs.forEach((t) => {
          if (t.id) chrome.tabs.sendMessage(t.id, { type: 'SETTINGS_UPDATED', settings: updated }).catch(() => {});
        });
      } catch (e) {
        // Ignore
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
 * Handles Capture & Send Job form submission with Full-Card State Swapping.
 */
async function handleCaptureSubmit() {
  const compInput = document.getElementById('input-company');
  const posInput = document.getElementById('input-position');
  const locInput = document.getElementById('input-location');
  const salInput = document.getElementById('input-salary');

  const company = compInput?.value?.trim() || '';
  const position = posInput?.value?.trim() || '';
  const location = locInput?.value?.trim() || '';
  const salary = salInput?.value?.trim() || '';

  if (!company || !position) {
    showFullCardFeedback({
      type: 'error',
      message: 'Please fill in both Company Name and Job Title before submitting.'
    });
    return;
  }

  const selectedModeRadio = document.querySelector('input[name="ingestMode"]:checked');
  const ingestMode = selectedModeRadio ? selectedModeRadio.value : 'AI_QUEUE';

  showFullCardFeedback({
    type: 'loading',
    message: ingestMode === 'AI_QUEUE'
      ? 'Enqueuing DOM markup into AI Evaluation Queue...'
      : 'Sending job directly to Applications board...'
  });

  const settings = await getSettings();
  const appUrl = settings.appUrl || 'http://localhost:5173';

  try {
    const rawText = extractedData?.description_text || `${company} - ${position}\nLocation: ${location}`;
    const jobUrl = extractedData?.url || '';

    if (ingestMode === 'AI_QUEUE') {
      const res = await enqueueAssessment({
        text: rawText,
        url: jobUrl,
        title_hint: `${company} - ${position}`
      });

      showFullCardFeedback({
        type: 'success',
        title: 'Queued for AI Assessment! 🚀',
        message: `Task #${res.id} queued successfully for ${company}.`,
        targetUrl: `${appUrl}/assessments`
      });
      updateQueueBadgeCount();
    } else {
      await clipJob({
        company,
        position,
        url: jobUrl,
        description: rawText,
        location,
        salary,
        status: 'APPLIED'
      });

      showFullCardFeedback({
        type: 'success',
        title: 'Job Saved to Board! 📌',
        message: `Application recorded for ${company} - ${position} in stage APPLIED.`,
        targetUrl: `${appUrl}/applications`
      });
    }
  } catch (err) {
    showFullCardFeedback({
      type: 'error',
      message: err.message || 'Unable to communicate with Job Tracker server.'
    });
  }
}

/**
 * Swaps form card with full-card feedback screen.
 */
function showFullCardFeedback({ type, title, message, targetUrl }) {
  const formContainer = document.getElementById('capture-form-container');
  const feedbackCard = document.getElementById('full-card-feedback');
  const loadingState = document.getElementById('feedback-loading');
  const successState = document.getElementById('feedback-success');
  const errorState = document.getElementById('feedback-error');

  const loadingMsg = document.getElementById('feedback-loading-msg');
  const successTitle = document.getElementById('feedback-success-title');
  const successMsg = document.getElementById('feedback-success-msg');
  const errorMsg = document.getElementById('feedback-error-msg');
  const openAppBtn = document.getElementById('btn-open-app-dashboard');
  const countdownBar = document.getElementById('countdown-bar');

  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }

  if (formContainer) formContainer.classList.add('hidden');
  if (feedbackCard) feedbackCard.classList.remove('hidden');

  if (loadingState) loadingState.classList.add('hidden');
  if (successState) successState.classList.add('hidden');
  if (errorState) errorState.classList.add('hidden');

  if (type === 'loading') {
    if (loadingState) loadingState.classList.remove('hidden');
    if (loadingMsg) loadingMsg.textContent = message;
  } else if (type === 'success') {
    if (successState) successState.classList.remove('hidden');
    if (successTitle) successTitle.textContent = title || 'Job Captured Successfully!';
    if (successMsg) successMsg.textContent = message || '';

    if (openAppBtn && targetUrl) {
      openAppBtn.setAttribute('data-url', targetUrl);
    }

    // Start 2.5 second auto-reset countdown
    if (countdownBar) {
      countdownBar.style.transition = 'none';
      countdownBar.style.width = '100%';
      setTimeout(() => {
        countdownBar.style.transition = 'width 2.5s linear';
        countdownBar.style.width = '0%';
      }, 50);
    }

    countdownTimer = setTimeout(() => {
      resetFeedbackScreen();
    }, 2550);
  } else {
    if (errorState) errorState.classList.remove('hidden');
    if (errorMsg) errorMsg.textContent = message || 'An error occurred during capture.';
  }
}

/**
 * Resets full-card feedback screen back to form view.
 */
function resetFeedbackScreen() {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }

  const formContainer = document.getElementById('capture-form-container');
  const feedbackCard = document.getElementById('full-card-feedback');

  if (feedbackCard) feedbackCard.classList.add('hidden');
  if (formContainer) formContainer.classList.remove('hidden');
}

/**
 * Fetches recent evaluations and renders queue tab list with dynamic action buttons.
 */
async function loadEvaluationsList() {
  const queueList = document.getElementById('queue-list');
  if (!queueList) return;

  queueList.innerHTML = '<div class="spinner-large" style="margin: 20px auto;"></div>';

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

    queueList.innerHTML = tasks.map((task) => {
      const taskId = task.id;
      const titleHint = task.title_hint || 'Job Assessment';
      const status = task.status || 'QUEUED';

      let fitScoreBadge = '';
      if (task.result_json && task.result_json.fit_score !== undefined) {
        fitScoreBadge = `<span class="fit-score-pill">${task.result_json.fit_score}% Fit</span>`;
      } else if (task.result_json && task.result_json.match_score !== undefined) {
        fitScoreBadge = `<span class="fit-score-pill">${task.result_json.match_score}% Fit</span>`;
      }

      // Determine Task Action Buttons
      let actionButtonsHtml = '';
      if (status === 'QUEUED' || status === 'RUNNING' || status === 'PROCESSING') {
        actionButtonsHtml = `<button class="btn btn-outline-danger btn-xs btn-task-cancel" data-id="${taskId}">Cancel</button>`;
      } else if (status === 'FAILED' || status === 'CANCELLED') {
        actionButtonsHtml = `
          <button class="btn btn-secondary btn-xs btn-task-retry" data-id="${taskId}">Retry</button>
          <button class="btn btn-outline-danger btn-xs btn-task-delete" data-id="${taskId}">Delete</button>
        `;
      } else if (status === 'COMPLETED') {
        actionButtonsHtml = `
          ${fitScoreBadge}
          <button class="btn btn-secondary btn-xs btn-task-delete" data-id="${taskId}">Delete</button>
        `;
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
            <div class="task-action-group">
              ${actionButtonsHtml}
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Attach Task Control Click Listeners
    queueList.querySelectorAll('.btn-task-cancel').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        btn.disabled = true;
        try {
          await cancelEvaluation(id);
          await loadEvaluationsList();
        } catch (err) {
          console.error('Cancel task failed:', err);
        }
      });
    });

    queueList.querySelectorAll('.btn-task-retry').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        btn.disabled = true;
        try {
          await retryEvaluation(id);
          await loadEvaluationsList();
        } catch (err) {
          console.error('Retry task failed:', err);
        }
      });
    });

    queueList.querySelectorAll('.btn-task-delete').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        btn.disabled = true;
        try {
          await deleteEvaluation(id);
          await loadEvaluationsList();
        } catch (err) {
          console.error('Delete task failed:', err);
        }
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
