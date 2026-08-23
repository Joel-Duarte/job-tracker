/**
 * Job Tracker Companion Extension - Chrome Storage Wrapper
 */

const DEFAULT_SETTINGS = {
  appUrl: 'http://localhost:5173',
  dockMode: 'AUTO-DETECT', // 'AUTO-DETECT' | 'ALL_PAGES' | 'OFF'
  dockExpanded: true,      // boolean: floating dock open/closed persistence
  theme: 'LIGHT',          // 'LIGHT' | 'DARK' | 'SYSTEM'
  lastMode: 'AI_QUEUE',    // 'AI_QUEUE' | 'DIRECT_APPLIED'
  pollInterval: 60,        // seconds (15, 30, 60, 0=Off)
  notificationsEnabled: true
};

/**
 * Retrieves all stored settings merged with defaults.
 * @returns {Promise<typeof DEFAULT_SETTINGS>}
 */
export async function getSettings() {
  return new Promise((resolve) => {
    if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
      resolve({ ...DEFAULT_SETTINGS });
      return;
    }
    chrome.storage.local.get(DEFAULT_SETTINGS, (result) => {
      resolve({ ...DEFAULT_SETTINGS, ...result });
    });
  });
}

/**
 * Persists settings updates to chrome.storage.local.
 * @param {Partial<typeof DEFAULT_SETTINGS>} settings
 * @returns {Promise<void>}
 */
export async function saveSettings(settings) {
  return new Promise((resolve, reject) => {
    if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
      resolve();
      return;
    }
    chrome.storage.local.set(settings, () => {
      if (chrome.runtime.lastError) {
        reject(chrome.runtime.lastError);
      } else {
        resolve();
      }
    });
  });
}

/**
 * Retrieves a single setting value.
 * @param {string} key
 * @param {any} defaultValue
 */
export async function getSetting(key, defaultValue = null) {
  const settings = await getSettings();
  return settings[key] !== undefined ? settings[key] : defaultValue;
}

/**
 * Sets a single setting value.
 * @param {string} key
 * @param {any} value
 */
export async function setSetting(key, value) {
  await saveSettings({ [key]: value });
}
