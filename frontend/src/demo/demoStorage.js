import { INITIAL_MOCK_DATA } from './mockData'

const DEMO_STORAGE_KEY = 'jt_demo_db_v1'
const DEMO_MODE_FLAG_KEY = 'jt_demo_mode'

export function isDemoModeEnabled() {
  const localVal = localStorage.getItem(DEMO_MODE_FLAG_KEY)
  if (localVal !== null) {
    return localVal === 'true'
  }
  return import.meta.env.VITE_DEMO_MODE === 'true'
}

export function setDemoModeEnabled(enabled) {
  localStorage.setItem(DEMO_MODE_FLAG_KEY, enabled ? 'true' : 'false')
}

export function getDemoDb() {
  const dataStr = localStorage.getItem(DEMO_STORAGE_KEY)
  if (!dataStr) {
    return initDemoDb()
  }
  try {
    return JSON.parse(dataStr)
  } catch (err) {
    console.error('Failed to parse demo storage, re-initializing:', err)
    return initDemoDb()
  }
}

export function saveDemoDb(db) {
  localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(db))
}

export function initDemoDb() {
  const initial = JSON.parse(JSON.stringify(INITIAL_MOCK_DATA))
  saveDemoDb(initial)
  return initial
}

export function resetDemoDb() {
  return initDemoDb()
}
