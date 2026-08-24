/**
 * Job Tracker Companion Extension - API Client
 */

import { getSettings } from './storage.js';

/**
 * Normalizes app URL by stripping trailing slashes.
 * @param {string} rawUrl
 * @returns {string}
 */
export function normalizeAppUrl(rawUrl) {
  if (!rawUrl) return 'http://localhost:4173';
  return rawUrl.trim().replace(/\/+$/, '');
}

/**
 * Tests connection to Job Tracker backend via app URL.
 * @param {string} [customAppUrl]
 * @returns {Promise<{ success: boolean; version?: string; message: string; config?: any }>}
 */
export async function testConnection(customAppUrl) {
  try {
    const settings = await getSettings();
    const baseUrl = normalizeAppUrl(customAppUrl || settings.appUrl);
    const targetUrl = `${baseUrl}/api/v1/intake/extension-config`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      return { success: false, message: `HTTP Error ${response.status}` };
    }

    const data = await response.json();
    return {
      success: true,
      version: '1.0.0',
      message: `Connected: ${baseUrl}`,
      config: data
    };
  } catch (err) {
    return {
      success: false,
      message: err.name === 'AbortError' ? 'Connection timed out' : (err.message || 'Cannot reach server')
    };
  }
}

/**
 * Enqueues a job for AI fit assessment.
 * @param {{ text?: string; url?: string; title_hint?: string }} payload
 * @returns {Promise<any>}
 */
export async function enqueueAssessment(payload) {
  const settings = await getSettings();
  const baseUrl = normalizeAppUrl(settings.appUrl);
  const response = await fetch(`${baseUrl}/api/v1/intake/enqueue-assessment`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Enqueue failed (${response.status}): ${errorText}`);
  }

  return await response.json();
}

/**
 * Direct clips a job to the applications board in APPLIED stage.
 * @param {{ company: string; position: string; url?: string; description?: string; location?: string; salary?: string; status?: string }} payload
 * @returns {Promise<any>}
 */
export async function clipJob(payload) {
  const settings = await getSettings();
  const baseUrl = normalizeAppUrl(settings.appUrl);
  const response = await fetch(`${baseUrl}/api/v1/extension/clip-job`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({
      status: 'APPLIED',
      ...payload
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Clip job failed (${response.status}): ${errorText}`);
  }

  return await response.json();
}

/**
 * Retrieves recent intake evaluation tasks.
 * @param {number} [limit=20]
 * @returns {Promise<Array<any>>}
 */
export async function getEvaluations(limit = 20) {
  const settings = await getSettings();
  const baseUrl = normalizeAppUrl(settings.appUrl);
  const response = await fetch(`${baseUrl}/api/v1/intake/evaluations?limit=${limit}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch evaluations (${response.status})`);
  }

  return await response.json();
}

/**
 * Cancels an active evaluation task.
 * @param {number|string} taskId
 */
export async function cancelEvaluation(taskId) {
  const settings = await getSettings();
  const baseUrl = normalizeAppUrl(settings.appUrl);
  const response = await fetch(`${baseUrl}/api/v1/intake/evaluations/${taskId}/cancel`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Cancel task failed (${response.status})`);
  }

  return await response.json();
}

/**
 * Retries a failed or cancelled evaluation task.
 * @param {number|string} taskId
 */
export async function retryEvaluation(taskId) {
  const settings = await getSettings();
  const baseUrl = normalizeAppUrl(settings.appUrl);
  const response = await fetch(`${baseUrl}/api/v1/intake/evaluations/${taskId}/retry`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Retry task failed (${response.status})`);
  }

  return await response.json();
}

/**
 * Deletes an evaluation task.
 * @param {number|string} taskId
 */
export async function deleteEvaluation(taskId) {
  const settings = await getSettings();
  const baseUrl = normalizeAppUrl(settings.appUrl);
  const response = await fetch(`${baseUrl}/api/v1/intake/evaluations/${taskId}`, {
    method: 'DELETE',
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Delete task failed (${response.status})`);
  }

  return await response.json();
}

/**
 * Clears all completed or failed evaluation tasks.
 */
export async function clearCompletedEvaluations() {
  const settings = await getSettings();
  const baseUrl = normalizeAppUrl(settings.appUrl);
  const response = await fetch(`${baseUrl}/api/v1/intake/evaluations/clear-completed`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Clear completed failed (${response.status})`);
  }

  return await response.json();
}
