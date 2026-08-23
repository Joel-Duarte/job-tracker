/**
 * Job Tracker Companion Extension - API Client
 */

import { getSettings } from './storage.js';

/**
 * Normalizes base API URL by stripping trailing slashes and ensuring standard suffix.
 * @param {string} rawUrl
 * @returns {string}
 */
export function normalizeApiUrl(rawUrl) {
  if (!rawUrl) return 'http://localhost:8000';
  let url = rawUrl.trim().replace(/\/+$/, '');
  return url;
}

/**
 * Tests connection to Job Tracker backend.
 * @param {string} [customBaseUrl]
 * @returns {Promise<{ success: boolean; version?: string; message: string }>}
 */
export async function testConnection(customBaseUrl) {
  try {
    const settings = await getSettings();
    const baseUrl = normalizeApiUrl(customBaseUrl || settings.apiBaseUrl);
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
      message: `Connected: API ${baseUrl}`,
      config: data
    };
  } catch (err) {
    return {
      success: false,
      message: err.name === 'AbortError' ? 'Connection timed out' : (err.message || 'Cannot reach backend')
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
  const baseUrl = normalizeApiUrl(settings.apiBaseUrl);
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
  const baseUrl = normalizeApiUrl(settings.apiBaseUrl);
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
  const baseUrl = normalizeApiUrl(settings.apiBaseUrl);
  const response = await fetch(`${baseUrl}/api/v1/intake/evaluations?limit=${limit}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch evaluations (${response.status})`);
  }

  return await response.json();
}
