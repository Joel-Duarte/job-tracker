/**
 * Job Tracker Companion Extension - Background Service Worker
 * Manages background alarms, toolbar badge counter polling, and desktop notifications.
 */

import { getSettings } from '../utils/storage.js';
import { getEvaluations } from '../utils/api.js';

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

// Message Listener from Popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SETTINGS_UPDATED') {
    setupAlarm().then(() => updateBadgeCounter());
    sendResponse({ success: true });
  } else if (message.type === 'FORCE_POLL') {
    updateBadgeCounter().then((count) => sendResponse({ success: true, count }));
    return true; // async
  }
});

// Notification Click Listener
chrome.notifications.onClicked.addListener(async (notificationId) => {
  try {
    const settings = await getSettings();
    const baseUrl = (settings.appUrl || 'http://localhost:5173').replace(/\/+$/, '');
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
    const periodInMinutes = Math.max(0.25, pollIntervalSeconds / 60); // min 15 seconds
    chrome.alarms.create(ALARM_POLL_NAME, {
      delayInMinutes: 0.1,
      periodInMinutes: periodInMinutes
    });
    console.log(`[Job Tracker Worker] Alarm '${ALARM_POLL_NAME}' set for every ${pollIntervalSeconds}s.`);
  } else {
    console.log(`[Job Tracker Worker] Polling alarm disabled in settings.`);
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

    // Filter active running/queued tasks
    const activeTasks = tasks.filter(
      (t) => t.status === 'QUEUED' || t.status === 'RUNNING' || t.status === 'PROCESSING'
    );
    const count = activeTasks.length;

    // Update Toolbar Badge
    if (count > 0) {
      await chrome.action.setBadgeText({ text: String(count) });
      await chrome.action.setBadgeBackgroundColor({ color: '#6366F1' }); // Indigo
    } else {
      await chrome.action.setBadgeText({ text: '' });
    }

    // Check for task completion status transitions to trigger desktop notifications
    if (settings.notificationsEnabled !== false) {
      await checkNotifications(tasks);
    }

    return count;
  } catch (err) {
    console.warn('[Job Tracker Worker] Failed to update badge counter:', err.message);
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

        // Transition from active/queued to COMPLETED
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
        }
        // Transition from active/queued to FAILED
        else if (
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

      // Save updated state dictionary
      chrome.storage.local.set({ previousTaskStates: newStates }, resolve);
    });
  });
}
