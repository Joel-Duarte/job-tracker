/**
 * Job Tracker Companion Extension - Popup UI Controller
 */

import { getSettings, saveSettings, setSetting } from '../utils/storage.js';
import { normalizeAppUrl } from '../utils/api.js';

let extractedData = null;
let countdownTimer = null;
let autoSaveDebounceTimer = null;
let isAiAvailable = true;
let currentSettings = {
  dockMode: 'AUTO-DETECT',
  lastMode: 'AI_QUEUE',
  theme: 'LIGHT',
  appUrl: 'http://localhost:4173'
};

document.addEventListener('DOMContentLoaded', async () => {
  await initSettingsAndTheme();
  await checkBackendConnection();
  await extractActiveTab();
  setupEventListeners();
  setupClearFieldButtons();
  setupAutoSaveSettings();
  updateQueueBadgeCount();
});

/**
 * Initializes settings input fields and applies design theme.
 */
async function initSettingsAndTheme() {
  currentSettings = await getSettings();

  applyTheme(currentSettings.theme || 'LIGHT');

  const appUrlInput = document.getElementById('input-app-url');
  const themeSelect = document.getElementById('select-theme');
  const dockModeSelect = document.getElementById('select-dock-mode');
  const pollSelect = document.getElementById('select-poll-interval');
  const notifToggle = document.getElementById('toggle-notifications');

  if (appUrlInput) appUrlInput.value = currentSettings.appUrl || 'http://localhost:4173';
  if (themeSelect) themeSelect.value = currentSettings.theme || 'LIGHT';
  if (dockModeSelect) dockModeSelect.value = currentSettings.dockMode || 'AUTO-DETECT';
  if (pollSelect) pollSelect.value = String(currentSettings.pollInterval ?? 60);
  if (notifToggle) notifToggle.checked = currentSettings.notificationsEnabled ?? true;

  const modeVal = currentSettings.lastMode || 'AI_QUEUE';
  const modeRadio = document.querySelector(`input[name="ingestMode"][value="${modeVal}"]`);
  if (modeRadio) {
    modeRadio.checked = true;
    updateModeOptionLayout(modeVal);
  }
}

/**
 * Binds 1-click clear buttons to input fields.
 */
function setupClearFieldButtons() {
  document.querySelectorAll('.clear-field-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-target');
      if (targetId) {
        const inputEl = document.getElementById(targetId);
        if (inputEl) {
          inputEl.value = '';
          inputEl.focus();
          // Trigger input event for auto-save if clearing setting field
          inputEl.dispatchEvent(new Event('input'));
        }
      }
    });
  });
}

/**
 * Automatically persists settings on input/change events with temporary visual feedback.
 */
function setupAutoSaveSettings() {
  const appUrlInput = document.getElementById('input-app-url');
  const themeSel = document.getElementById('select-theme');
  const dockSel = document.getElementById('select-dock-mode');
  const pollSelect = document.getElementById('select-poll-interval');
  const notifToggle = document.getElementById('toggle-notifications');

  const triggerAutoSave = async () => {
    const updated = {
      appUrl: normalizeAppUrl(appUrlInput?.value || 'http://localhost:4173'),
      theme: themeSel?.value || 'LIGHT',
      dockMode: dockSel?.value || 'AUTO-DETECT',
      pollInterval: parseInt(pollSelect?.value || '60', 10),
      notificationsEnabled: notifToggle?.checked ?? true
    };

    await saveSettings(updated);
    currentSettings = { ...currentSettings, ...updated };
    applyTheme(updated.theme);

    try {
      chrome.runtime.sendMessage({ type: 'SETTINGS_UPDATED', settings: updated });
      const tabs = await chrome.tabs.query({});
      tabs.forEach((t) => {
        if (t.id) chrome.tabs.sendMessage(t.id, { type: 'SETTINGS_UPDATED', settings: updated }).catch(() => {});
      });
    } catch (e) {
      // Ignore
    }

    showAutoSaveIndicator();
  };

  if (appUrlInput) {
    appUrlInput.addEventListener('input', () => {
      clearTimeout(autoSaveDebounceTimer);
      autoSaveDebounceTimer = setTimeout(triggerAutoSave, 400);
    });
  }

  [themeSel, dockSel, pollSelect, notifToggle].forEach((el) => {
    if (el) {
      el.addEventListener('change', triggerAutoSave);
    }
  });
}

function showAutoSaveIndicator() {
  const statusMsg = document.getElementById('settings-status');
  if (statusMsg) {
    statusMsg.classList.remove('hidden', 'error');
    statusMsg.classList.add('success');
    statusMsg.textContent = '✓ Settings Saved';
    setTimeout(() => statusMsg.classList.add('hidden'), 1500);
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
 * Tests connection to backend via background message and verifies AI provider health.
 */
async function checkBackendConnection() {
  const connPill = document.getElementById('conn-pill');
  const connText = document.getElementById('conn-text');
  const aiOfflineBanner = document.getElementById('ai-offline-banner');
  const aiOpt = document.getElementById('mode-opt-ai');

  if (!connPill || !connText) return;

  connPill.className = 'conn-pill checking';
  connText.textContent = 'Checking...';

  chrome.runtime.sendMessage({ type: 'TEST_CONNECTION' }, (response) => {
    if (response && response.success && response.data && response.data.success) {
      const aiReady = response.data.config ? response.data.config.ai_ready : true;

      if (aiReady !== false) {
        connPill.className = 'conn-pill connected';
        connText.textContent = 'Connected';
        isAiAvailable = true;

        if (aiOfflineBanner) aiOfflineBanner.classList.add('hidden');
        if (aiOpt) {
          aiOpt.style.opacity = '1';
          aiOpt.style.pointerEvents = 'auto';
        }
      } else {
        connPill.className = 'conn-pill warning';
        connText.textContent = 'AI Offline';

        isAiAvailable = false;
        if (aiOfflineBanner) aiOfflineBanner.classList.remove('hidden');

        if (aiOpt) {
          aiOpt.style.opacity = '0.5';
          aiOpt.style.pointerEvents = 'none';
        }

        const directRadio = document.querySelector('input[name="ingestMode"][value="DIRECT_APPLIED"]');
        if (directRadio) {
          directRadio.checked = true;
          updateModeOptionLayout('DIRECT_APPLIED');
          setSetting('lastMode', 'DIRECT_APPLIED');
        }
      }
    } else {
      connPill.className = 'conn-pill error';
      connText.textContent = 'Offline';

      isAiAvailable = false;
      if (aiOfflineBanner) aiOfflineBanner.classList.remove('hidden');

      if (aiOpt) {
        aiOpt.style.opacity = '0.5';
        aiOpt.style.pointerEvents = 'none';
      }

      const directRadio = document.querySelector('input[name="ingestMode"][value="DIRECT_APPLIED"]');
      if (directRadio) {
        directRadio.checked = true;
        updateModeOptionLayout('DIRECT_APPLIED');
      }
    }
  });
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
      const wmSelect = document.getElementById('input-work-model');

      if (compInput && extractedData.company) compInput.value = extractedData.company;
      if (posInput && extractedData.title) posInput.value = extractedData.title;
      if (locInput && extractedData.location) locInput.value = extractedData.location;
      if (salInput && extractedData.salary) salInput.value = extractedData.salary;
      if (wmSelect && extractedData.work_model) wmSelect.value = extractedData.work_model;
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

  // Ingestion Mode Option Styling, Dynamic Field Toggling & Persistence
  document.querySelectorAll('input[name="ingestMode"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      const selectedMode = e.target.value;
      updateModeOptionLayout(selectedMode);
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
      const targetUrl = openAppBtn.getAttribute('data-url') || 'http://localhost:4173/assessments';
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
    clearCompletedBtn.addEventListener('click', () => {
      clearCompletedBtn.disabled = true;
      chrome.runtime.sendMessage({ type: 'CLEAR_COMPLETED' }, () => {
        clearCompletedBtn.disabled = false;
        loadEvaluationsList();
      });
    });
  }

  // Test Connection Button in Settings
  const testConnBtn = document.getElementById('btn-test-conn');
  if (testConnBtn) {
    testConnBtn.addEventListener('click', () => {
      const appUrlInput = document.getElementById('input-app-url');
      const statusMsg = document.getElementById('settings-status');
      testConnBtn.disabled = true;

      chrome.runtime.sendMessage(
        { type: 'TEST_CONNECTION', appUrl: appUrlInput ? appUrlInput.value : null },
        (response) => {
          testConnBtn.disabled = false;
          if (statusMsg) {
            statusMsg.classList.remove('hidden', 'success', 'error');
            if (response && response.success && response.data && response.data.success) {
              statusMsg.classList.add('success');
              statusMsg.textContent = response.data.message;
            } else {
              statusMsg.classList.add('error');
              statusMsg.textContent = `Error: ${response?.error || 'Cannot reach server'}`;
            }
          }
          checkBackendConnection();
        }
      );
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
 * Dynamically toggles input fields and submit button text based strictly on selected ingestion mode.
 * @param {'AI_QUEUE'|'DIRECT_APPLIED'} selectedMode
 */
function updateModeOptionLayout(selectedMode) {
  const aiOpt = document.getElementById('mode-opt-ai');
  const directOpt = document.getElementById('mode-opt-direct');
  const formFieldsContainer = document.getElementById('form-fields-container');
  const submitText = document.getElementById('btn-submit-text');
  const submitIcon = document.getElementById('btn-submit-icon');

  if (aiOpt) aiOpt.classList.toggle('active', selectedMode === 'AI_QUEUE');
  if (directOpt) directOpt.classList.toggle('active', selectedMode === 'DIRECT_APPLIED');

  if (selectedMode === 'AI_QUEUE') {
    if (submitText) submitText.textContent = 'Send Page to AI Assessment';
    if (submitIcon) submitIcon.textContent = '⚡';
    if (formFieldsContainer) formFieldsContainer.classList.add('hidden');
  } else {
    if (submitText) submitText.textContent = 'Save Application to Board';
    if (submitIcon) submitIcon.textContent = '📌';
    if (formFieldsContainer) formFieldsContainer.classList.remove('hidden');
  }
}

/**
 * Handles Capture & Send Job form submission with Full-Card State Swapping & Background Message Passing.
 */
async function handleCaptureSubmit() {
  const compInput = document.getElementById('input-company');
  const posInput = document.getElementById('input-position');
  const locInput = document.getElementById('input-location');
  const salInput = document.getElementById('input-salary');
  const wmSelect = document.getElementById('input-work-model');

  const selectedModeRadio = document.querySelector('input[name="ingestMode"]:checked');
  const ingestMode = selectedModeRadio ? selectedModeRadio.value : 'AI_QUEUE';

  let company = compInput?.value?.trim() || extractedData?.company || 'Job Posting';
  let position = posInput?.value?.trim() || extractedData?.title || 'Unknown Position';
  let location = locInput?.value?.trim() || extractedData?.location || '';
  let salary = salInput?.value?.trim() || extractedData?.salary || '';
  let work_model = wmSelect?.value || extractedData?.work_model || 'Unknown';

  if (ingestMode === 'DIRECT_APPLIED' && (!compInput?.value?.trim() || !posInput?.value?.trim())) {
    showFullCardFeedback({
      type: 'error',
      message: 'Please fill in both Company Name and Job Title before saving directly.'
    });
    return;
  }

  const settings = await getSettings();
  const appUrl = settings.appUrl || 'http://localhost:4173';
  const rawText = extractedData?.description_text || `${company} - ${position}\nLocation: ${location}`;
  const jobUrl = extractedData?.url || '';

  if (ingestMode === 'AI_QUEUE') {
    showFullCardFeedback({
      type: 'success',
      title: 'Queued for AI Assessment! 🚀',
      message: `Page sent to AI Queue for analysis.`,
      targetUrl: `${appUrl}/assessments`
    });

    chrome.runtime.sendMessage(
      {
        type: 'ENQUEUE_JOB',
        payload: {
          text: rawText,
          url: jobUrl
        }
      },
      (res) => {
        if (!res || !res.success) {
          showFullCardFeedback({
            type: 'error',
            message: res?.error || 'Unable to communicate with Job Tracker server.'
          });
        } else {
          updateQueueBadgeCount();
        }
      }
    );
  } else {
    showFullCardFeedback({
      type: 'success',
      title: 'Job Saved to Board! 📌',
      message: `Application recorded for ${company} - ${position} in stage APPLIED.`,
      targetUrl: `${appUrl}/applications`
    });

    chrome.runtime.sendMessage(
      {
        type: 'CLIP_JOB',
        payload: {
          company,
          position,
          url: jobUrl,
          description: rawText,
          location,
          salary,
          work_model,
          status: 'APPLIED'
        }
      },
      (res) => {
        if (!res || !res.success) {
          showFullCardFeedback({
            type: 'error',
            message: res?.error || 'Unable to save application to Job Tracker.'
          });
        }
      }
    );
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

    if (countdownBar) {
      countdownBar.style.transition = 'none';
      countdownBar.style.width = '100%';
      setTimeout(() => {
        countdownBar.style.transition = 'width 1.5s linear';
        countdownBar.style.width = '0%';
      }, 50);
    }

    countdownTimer = setTimeout(() => {
      resetFeedbackScreen();
    }, 1550);
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
 * Fetches recent evaluations via background message and renders queue list with interactive controls.
 */
function loadEvaluationsList() {
  const queueList = document.getElementById('queue-list');
  if (!queueList) return;

  queueList.innerHTML = '<div class="spinner-large" style="margin: 20px auto;"></div>';

  chrome.runtime.sendMessage({ type: 'GET_EVALUATIONS', limit: 20 }, async (response) => {
    if (!response || !response.success) {
      queueList.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">⚠️</span>
          <p style="color: var(--danger-color);">Unable to load queue tasks: ${escapeHtml(response?.error || 'Server offline')}</p>
        </div>
      `;
      return;
    }

    const tasks = response.data;
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

    queueList.querySelectorAll('.btn-task-cancel').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        btn.disabled = true;
        chrome.runtime.sendMessage({ type: 'CANCEL_EVALUATION', taskId: id }, () => loadEvaluationsList());
      });
    });

    queueList.querySelectorAll('.btn-task-retry').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        btn.disabled = true;
        chrome.runtime.sendMessage({ type: 'RETRY_EVALUATION', taskId: id }, () => loadEvaluationsList());
      });
    });

    queueList.querySelectorAll('.btn-task-delete').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        btn.disabled = true;
        chrome.runtime.sendMessage({ type: 'DELETE_EVALUATION', taskId: id }, () => loadEvaluationsList());
      });
    });

    updateQueueBadgeCount(tasks);
  });
}

/**
 * Updates tab badge count based on active tasks.
 * @param {Array} [tasksList]
 */
function updateQueueBadgeCount(tasksList) {
  const badgeEl = document.getElementById('queue-count-badge');
  if (!badgeEl) return;

  if (tasksList) {
    const activeCount = tasksList.filter((t) => t.status === 'QUEUED' || t.status === 'RUNNING' || t.status === 'PROCESSING').length;
    if (activeCount > 0) {
      badgeEl.textContent = String(activeCount);
      badgeEl.classList.remove('hidden');
    } else {
      badgeEl.classList.add('hidden');
    }
  } else {
    chrome.runtime.sendMessage({ type: 'GET_EVALUATIONS', limit: 50 }, (res) => {
      if (res && res.success && Array.isArray(res.data)) {
        const activeCount = res.data.filter((t) => t.status === 'QUEUED' || t.status === 'RUNNING' || t.status === 'PROCESSING').length;
        if (activeCount > 0) {
          badgeEl.textContent = String(activeCount);
          badgeEl.classList.remove('hidden');
        } else {
          badgeEl.classList.add('hidden');
        }
      }
    });
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
