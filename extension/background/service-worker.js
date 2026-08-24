/**
 * Job Tracker Companion Extension - Background Service Worker
 * Handles background alarms, queue polling, desktop notifications, and message passing.
 */

import { getSettings } from '../utils/storage.js';
import {
  getEvaluations,
  enqueueAssessment,
  clipJob,
  cancelEvaluation,
  retryEvaluation,
  deleteEvaluation,
  clearCompletedEvaluations,
  testConnection
} from '../utils/api.js';

const ALARM_POLL_NAME = 'poll_ai_queue';

// Service Worker Startup / Installation Lifecycle
chrome.runtime.onInstalled.addListener(async () => {
  console.log('[Job Tracker Worker] Extension installed/updated.');
  await setupAlarm();
  await updateBadgeCounter();
});

chrome.runtime.onStartup.addListener(async () => {
  console.log('[Job Tracker Worker] Browser startup.');
  await setupAlarm();
  await updateBadgeCounter();
});

// Alarm Listener
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_POLL_NAME) {
    await updateBadgeCounter();
  }
});

// Centralized Message Listener for Content Scripts & Popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) return false;

  switch (message.type) {
    case 'ENQUEUE_JOB':
      enqueueAssessment(message.payload)
        .then((data) => {
          updateBadgeCounter();
          sendResponse({ success: true, data });
        })
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true; // async response

    case 'CLIP_JOB':
      clipJob(message.payload)
        .then((data) => {
          updateBadgeCounter();
          sendResponse({ success: true, data });
        })
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case 'GET_EVALUATIONS':
      getEvaluations(message.limit || 20)
        .then((data) => sendResponse({ success: true, data }))
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case 'CANCEL_EVALUATION':
      cancelEvaluation(message.taskId)
        .then((data) => {
          updateBadgeCounter();
          sendResponse({ success: true, data });
        })
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case 'RETRY_EVALUATION':
      retryEvaluation(message.taskId)
        .then((data) => {
          updateBadgeCounter();
          sendResponse({ success: true, data });
        })
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case 'DELETE_EVALUATION':
      deleteEvaluation(message.taskId)
        .then((data) => {
          updateBadgeCounter();
          sendResponse({ success: true, data });
        })
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case 'CLEAR_COMPLETED':
      clearCompletedEvaluations()
        .then((data) => {
          updateBadgeCounter();
          sendResponse({ success: true, data });
        })
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case 'TEST_CONNECTION':
      testConnection(message.appUrl)
        .then((data) => sendResponse({ success: true, data }))
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case 'SETTINGS_UPDATED':
      setupAlarm().then(() => updateBadgeCounter());
      sendResponse({ success: true });
      break;

    case 'FORCE_POLL':
      updateBadgeCounter().then((count) => sendResponse({ success: true, count }));
      return true;
  }
});

// Notification Click Listener
chrome.notifications.onClicked.addListener(async (notificationId) => {
  try {
    const settings = await getSettings();
    const baseUrl = (settings.appUrl || 'http://localhost:4173').replace(/\/+$/, '');
    const targetUrl = `${baseUrl}/assessments`;
    chrome.tabs.create({ url: targetUrl });
    chrome.notifications.clear(notificationId);
  } catch (err) {
    console.error('[Job Tracker Worker] Failed to handle notification click:', err);
  }
});

/**
 * Re-configures the chrome.alarms scheduler based on pollInterval setting.
 */
async function setupAlarm() {
  const settings = await getSettings();
  const pollIntervalSeconds = settings.pollInterval ?? 60;

  await chrome.alarms.clear(ALARM_POLL_NAME);

  if (pollIntervalSeconds > 0) {
    const periodInMinutes = Math.max(0.25, pollIntervalSeconds / 60);
    chrome.alarms.create(ALARM_POLL_NAME, {
      delayInMinutes: 0.1,
      periodInMinutes: periodInMinutes
    });
  }
}

/**
 * Polls backend evaluation queue, updates toolbar badge counter, and emits desktop notifications.
 */
async function updateBadgeCounter() {
  try {
    const settings = await getSettings();
    const tasks = await getEvaluations(50);

    if (!Array.isArray(tasks)) return 0;

    const activeTasks = tasks.filter(
      (t) => t.status === 'QUEUED' || t.status === 'RUNNING' || t.status === 'PROCESSING'
    );
    const count = activeTasks.length;

    if (count > 0) {
      await chrome.action.setBadgeText({ text: String(count) });
      await chrome.action.setBadgeBackgroundColor({ color: '#854d0e' }); // Saddle Brown
    } else {
      await chrome.action.setBadgeText({ text: '' });
    }

    if (settings.notificationsEnabled !== false) {
      await checkNotifications(tasks);
    }

    return count;
  } catch (err) {
    return 0;
  }
}

/**
 * Compares current task list with stored previous statuses to emit notifications.
 * @param {Array} currentTasks
 */
async function checkNotifications(currentTasks) {
  return new Promise((resolve) => {
    chrome.storage.local.get(['previousTaskStates'], async (res) => {
      const prevStates = res.previousTaskStates || {};
      const newStates = {};

      for (const task of currentTasks) {
        if (!task || !task.id) continue;
        const taskIdStr = String(task.id);
        const prevStatus = prevStates[taskIdStr];
        const currentStatus = task.status;

        newStates[taskIdStr] = currentStatus;

        if (
          (prevStatus === 'QUEUED' || prevStatus === 'RUNNING' || prevStatus === 'PROCESSING') &&
          currentStatus === 'COMPLETED'
        ) {
          const titleHint = task.title_hint || 'Job Lead';
          let scoreText = '';
          if (task.result_json && task.result_json.fit_score !== undefined) {
            scoreText = ` (${task.result_json.fit_score}% Fit)`;
          } else if (task.result_json && task.result_json.match_score !== undefined) {
            scoreText = ` (${task.result_json.match_score}% Fit)`;
          }

          chrome.notifications.create(`eval-complete-${task.id}`, {
            type: 'basic',
            iconUrl: chrome.runtime.getURL('icons/icon-48.png'),
            title: 'Evaluation Complete ✨',
            message: `Fit Assessment ready for ${titleHint}${scoreText}. Click to view details in Job Tracker.`,
            priority: 2
          });
        } else if (
          (prevStatus === 'QUEUED' || prevStatus === 'RUNNING' || prevStatus === 'PROCESSING') &&
          currentStatus === 'FAILED'
        ) {
          const titleHint = task.title_hint || 'Job Lead';
          chrome.notifications.create(`eval-failed-${task.id}`, {
            type: 'basic',
            iconUrl: chrome.runtime.getURL('icons/icon-48.png'),
            title: 'Evaluation Failed ⚠️',
            message: `Assessment for ${titleHint} failed: ${task.error_message || 'Unspecified error'}. Click to review in Job Tracker.`,
            priority: 1
          });
        }
      }

      chrome.storage.local.set({ previousTaskStates: newStates }, resolve);
    });
  });
}
