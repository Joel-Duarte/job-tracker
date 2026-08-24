import { INITIAL_MOCK_DATA } from './mockData'

const DEMO_STORAGE_KEY = 'jt_demo_db_v1'
const DEMO_MODE_FLAG_KEY = 'jt_demo_mode'

export function isDemoModeEnabled() {
  const localVal = localStorage.getItem(DEMO_MODE_FLAG_KEY)
  if (localVal !== null) {
    return localVal === 'true'
  }
  // Default to true in client demo mode
  return true
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

function adjustRelativeDates(db) {
  const now = Date.now()
  const MS_PER_DAY = 86400000
  const MS_PER_HOUR = 3600000

  // Candidate profile
  if (db.candidate_profile) {
    db.candidate_profile.parsed_at = new Date(now - MS_PER_DAY * 5).toISOString()
    db.candidate_profile.created_at = new Date(now - MS_PER_DAY * 30).toISOString()
  }

  // Applications
  if (Array.isArray(db.applications)) {
    db.applications.forEach((app) => {
      if (app.id === 'app_stripe_001') {
        app.application_date = new Date(now - MS_PER_DAY * 8).toISOString()
        app.last_activity_at = new Date(now - MS_PER_DAY * 1).toISOString()
        app.nearest_due_date = new Date(now + MS_PER_DAY * 3).toISOString()
        app.cover_letter_generated_at = new Date(now - MS_PER_DAY * 2).toISOString()
        if (app.events) {
          app.events[0].created_at = new Date(now - MS_PER_DAY * 1).toISOString()
          app.events[0].raw_payload.decision_deadline = new Date(now + MS_PER_DAY * 3).toISOString()
          if (app.events[1]) app.events[1].created_at = new Date(now - MS_PER_DAY * 4).toISOString()
          if (app.events[2]) app.events[2].created_at = new Date(now - MS_PER_DAY * 7).toISOString()
        }
      } else if (app.id === 'app_linear_002') {
        app.application_date = new Date(now - MS_PER_DAY * 7).toISOString()
        app.last_activity_at = new Date(now - MS_PER_DAY * 7).toISOString()
        app.scheduled_interview_at = null
        app.nearest_due_date = null
        if (app.events && app.events[0]) {
          app.events[0].created_at = new Date(now - MS_PER_DAY * 7).toISOString()
        }
      } else if (app.id === 'app_figma_003') {
        app.application_date = new Date(now - MS_PER_DAY * 6).toISOString()
        app.last_activity_at = new Date(now - MS_PER_DAY * 6).toISOString()
        if (app.events && app.events[0]) {
          app.events[0].created_at = new Date(now - MS_PER_DAY * 6).toISOString()
        }
      } else if (app.id === 'app_datacamp_004') {
        app.application_date = new Date(now - MS_PER_DAY * 5).toISOString()
        app.last_activity_at = new Date(now - MS_PER_HOUR * 3).toISOString()
        app.nearest_due_date = new Date(now + MS_PER_HOUR * 12).toISOString() // < 24 hours!
        if (app.events && app.events[0]) {
          app.events[0].created_at = new Date(now - MS_PER_HOUR * 3).toISOString()
        }
      } else if (app.id === 'app_snowflake_005') {
        app.application_date = new Date(now - MS_PER_DAY * 10).toISOString()
        app.last_activity_at = new Date(now - MS_PER_DAY * 5).toISOString()
        if (app.events && app.events[0]) {
          app.events[0].created_at = new Date(now - MS_PER_DAY * 5).toISOString()
        }
      }
    })
  }

  // Action items
  if (Array.isArray(db.action_items)) {
    db.action_items.forEach((item) => {
      if (item.id === 'action_001') {
        item.created_at = new Date(now - MS_PER_DAY * 1).toISOString()
        item.due_date = new Date(now + MS_PER_DAY * 3).toISOString()
      } else if (item.id === 'action_002') {
        item.created_at = new Date(now - MS_PER_DAY * 1).toISOString()
        item.due_date = new Date(now + MS_PER_DAY * 2).toISOString()
      } else if (item.id === 'action_003') {
        item.created_at = new Date(now - MS_PER_HOUR * 3).toISOString()
        item.due_date = new Date(now + MS_PER_HOUR * 12).toISOString() // < 24 hours!
      } else if (item.id === 'action_004') {
        item.created_at = new Date(now - MS_PER_DAY * 3).toISOString()
        item.due_date = new Date(now + MS_PER_DAY * 4).toISOString()
      } else if (item.id === 'action_005') {
        item.created_at = new Date(now - MS_PER_DAY * 5).toISOString()
        item.due_date = new Date(now - MS_PER_DAY * 3).toISOString()
      }
    })
  }

  // Staging items
  if (Array.isArray(db.staging_items)) {
    db.staging_items.forEach((item, idx) => {
      item.created_at = new Date(now - MS_PER_DAY * (idx + 1)).toISOString()
    })
  }

  // Intake evaluations
  if (Array.isArray(db.intake_evaluations)) {
    db.intake_evaluations.forEach((task) => {
      if (task.id === 'task_eval_101') {
        task.created_at = new Date(now - MS_PER_DAY * 8).toISOString()
        task.completed_at = new Date(now - MS_PER_DAY * 8).toISOString()
      } else if (task.id === 'task_eval_102') {
        task.created_at = new Date(now - MS_PER_DAY * 5).toISOString()
        task.completed_at = new Date(now - MS_PER_DAY * 5).toISOString()
      } else if (task.id === 'task_eval_103') {
        task.created_at = new Date(now - MS_PER_HOUR * 2).toISOString()
        task.completed_at = new Date(now - MS_PER_HOUR * 2).toISOString()
      }
    })
  }

  // Interview sessions & chats
  if (Array.isArray(db.interview_sessions) && db.interview_sessions[0]) {
    db.interview_sessions[0].created_at = new Date(now - MS_PER_DAY * 2).toISOString()
  }
  if (Array.isArray(db.agent_chats) && db.agent_chats[0]) {
    db.agent_chats[0].created_at = new Date(now - MS_PER_DAY * 1).toISOString()
  }

  return db
}

export function initDemoDb() {
  const initial = adjustRelativeDates(JSON.parse(JSON.stringify(INITIAL_MOCK_DATA)))
  saveDemoDb(initial)
  return initial
}

export function resetDemoDb() {
  // ClearIndexedDB databases if any exist
  if (window.indexedDB && window.indexedDB.databases) {
    window.indexedDB.databases().then((dbs) => {
      dbs.forEach((db) => {
        if (db.name) window.indexedDB.deleteDatabase(db.name)
      })
    }).catch(() => {})
  }

  // Clear demo localStorage keys
  localStorage.removeItem(DEMO_STORAGE_KEY)

  return initDemoDb()
}
