import apiClient from '../api/client'
import { db, initAndSeedDatabase, exportLocalDatabaseJSON, importLocalDatabaseJSON } from '../db/localDatabase'
import {
  parseJobDescriptionWithBYOK,
  generateCoverLetterWithBYOK,
  generateInterviewGuideWithBYOK,
  executeBYOKCompletion
} from './byokAiClient'

export function getStorageMode() {
  const savedMode = localStorage.getItem('VITE_STORAGE_MODE')
  if (savedMode && ['backend', 'local', 'demo'].includes(savedMode)) {
    return savedMode
  }
  return import.meta.env.VITE_STORAGE_MODE || 'backend'
}

export function setStorageMode(mode) {
  if (['backend', 'local', 'demo'].includes(mode)) {
    localStorage.setItem('VITE_STORAGE_MODE', mode)
    if (mode === 'demo' || mode === 'local') {
      initAndSeedDatabase()
    }
  }
}

export function isLocalOrDemoMode() {
  const mode = getStorageMode()
  return mode === 'local' || mode === 'demo'
}

// System Settings Adapter
export const SystemSettingsAdapter = {
  async get() {
    if (!isLocalOrDemoMode()) return apiClient.get('/config/system')
    const settings = await db.system_settings.toArray()
    const settingsObj = {}
    settings.forEach(s => { settingsObj[s.key] = s.value })
    return { data: settingsObj }
  },

  async update(data) {
    if (!isLocalOrDemoMode()) return apiClient.patch('/config/system', data)
    for (const [key, value] of Object.entries(data)) {
      await db.system_settings.put({ key, value })
    }
    return { data }
  }
}

// Applications Adapter
export const ApplicationsAdapter = {
  async list(params = {}) {
    if (!isLocalOrDemoMode()) return apiClient.get('/applications', { params })
    let apps = await db.applications.toArray()
    if (params.status) {
      apps = apps.filter(a => a.status === params.status)
    }
    if (params.search) {
      const q = params.search.toLowerCase()
      apps = apps.filter(a => a.company_name.toLowerCase().includes(q) || a.title.toLowerCase().includes(q))
    }
    return { data: apps }
  },

  async get(id) {
    if (!isLocalOrDemoMode()) return apiClient.get(`/applications/${id}`)
    const app = await db.applications.get(Number(id))
    if (!app) throw new Error('Application not found in local DB')
    return { data: app }
  },

  async update(id, data) {
    if (!isLocalOrDemoMode()) return apiClient.patch(`/applications/${id}`, data)
    const numericId = Number(id)
    const existing = await db.applications.get(numericId)
    if (!existing) throw new Error('Application not found')
    const updated = { ...existing, ...data, updated_at: new Date().toISOString() }
    await db.applications.put(updated)
    return { data: updated }
  },

  async transition(id, data) {
    if (!isLocalOrDemoMode()) return apiClient.post(`/applications/${id}/transition`, data)
    const numericId = Number(id)
    const app = await db.applications.get(numericId)
    if (!app) throw new Error('Application not found')

    app.status = data.to_status || data.status || app.status
    app.updated_at = new Date().toISOString()
    if (!app.timeline_events) app.timeline_events = []
    app.timeline_events.push({
      id: Date.now(),
      event_type: app.status,
      title: `Transitioned to ${app.status}`,
      description: data.notes || `Moved application stage to ${app.status}`,
      created_at: new Date().toISOString()
    })
    await db.applications.put(app)
    return { data: app }
  },

  async bulkTransition(data) {
    if (!isLocalOrDemoMode()) return apiClient.post('/applications/bulk-transition', data)
    const { application_ids, to_status } = data
    for (const id of application_ids) {
      await this.transition(id, { to_status })
    }
    return { data: { success: true, count: application_ids.length } }
  },

  async delete(id) {
    if (!isLocalOrDemoMode()) return apiClient.delete(`/applications/${id}`)
    await db.applications.delete(Number(id))
    return { data: { success: true } }
  },

  async byStatus() {
    if (!isLocalOrDemoMode()) return apiClient.get('/applications/by-status')
    const apps = await db.applications.toArray()
    const grouped = {}
    apps.forEach(app => {
      const s = app.status || 'APPLIED'
      if (!grouped[s]) grouped[s] = []
      grouped[s].push(app)
    })
    return { data: grouped }
  },

  async generateInterviewGuide(id) {
    if (!isLocalOrDemoMode()) return apiClient.post(`/applications/${id}/interview-guide`)
    const app = await db.applications.get(Number(id))
    const profile = (await db.candidate_profile.toArray())[0]
    const guideText = await generateInterviewGuideWithBYOK(app, profile)
    app.interview_guide_markdown = guideText
    app.updated_at = new Date().toISOString()
    await db.applications.put(app)
    return { data: app }
  },

  async clearInterviewGuide(id) {
    if (!isLocalOrDemoMode()) return apiClient.delete(`/applications/${id}/interview-guide`)
    const app = await db.applications.get(Number(id))
    if (app) {
      app.interview_guide_markdown = null
      await db.applications.put(app)
    }
    return { data: app }
  },

  async getCoverLetter(id) {
    if (!isLocalOrDemoMode()) return apiClient.get(`/applications/${id}/cover-letter`)
    const app = await db.applications.get(Number(id))
    return { data: { cover_letter_text: app?.cover_letter_text || '', status: app?.cover_letter_status || 'idle' } }
  },

  async generateCoverLetter(id, data = {}) {
    if (!isLocalOrDemoMode()) return apiClient.post(`/applications/${id}/cover-letter/generate`, data)
    const app = await db.applications.get(Number(id))
    const profile = (await db.candidate_profile.toArray())[0]
    const letter = await generateCoverLetterWithBYOK(app, profile, data.length || 'standard', data.instructions || '')
    app.cover_letter_text = letter
    app.cover_letter_status = 'generated'
    app.cover_letter_generated_at = new Date().toISOString()
    await db.applications.put(app)
    return { data: app }
  },

  async updateCoverLetter(id, data) {
    if (!isLocalOrDemoMode()) return apiClient.patch(`/applications/${id}/cover-letter`, data)
    const app = await db.applications.get(Number(id))
    if (app) {
      app.cover_letter_text = data.cover_letter_text
      await db.applications.put(app)
    }
    return { data: app }
  },

  async regenerateCoverLetter(id, data = {}) {
    return this.generateCoverLetter(id, data)
  }
}

// Intake Adapter
export const IntakeAdapter = {
  async paste(data) {
    if (!isLocalOrDemoMode()) return apiClient.post('/intake/paste', data)
    const parsed = await parseJobDescriptionWithBYOK(data.raw_text)
    const newApp = {
      id: Date.now(),
      company_name: parsed.company_name || 'Unknown Company',
      title: parsed.title || 'Target Position',
      location: parsed.location || 'Remote',
      work_model: parsed.work_model || 'Remote',
      salary_range: parsed.salary_range || 'N/A',
      status: 'APPLIED',
      fit_score: 85,
      programmatic_match_score: 85,
      applied_date: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      url: data.url || '',
      description: data.raw_text,
      timeline_events: [
        { id: Date.now(), event_type: 'INTAKE', title: 'Application Created via Smart Paste', description: 'Pasted job description imported locally.', created_at: new Date().toISOString() }
      ],
      match_analysis_payload: {
        strengths: ['Parsed skills match local profile candidate requirements'],
        gaps: [],
        recommendations: ['Review extracted job title and company details']
      }
    }
    await db.applications.add(newApp)
    return { data: newApp }
  },

  async enqueueAssessment(data) {
    if (!isLocalOrDemoMode()) return apiClient.post('/intake/enqueue-assessment', data)
    const task = {
      id: Date.now(),
      status: 'COMPLETED',
      stage: 'COMPLETED',
      company_name: data.company_name || 'Extracted Company',
      job_title: data.job_title || 'Extracted Title',
      raw_text: data.raw_text || '',
      created_at: new Date().toISOString()
    }
    await db.evaluations.add(task)
    return { data: task }
  },

  async getEvaluations(limit = 50) {
    if (!isLocalOrDemoMode()) return apiClient.get('/intake/evaluations', { params: { limit } })
    const evals = await db.evaluations.reverse().limit(limit).toArray()
    return { data: evals }
  },

  async deleteEvaluation(taskId) {
    if (!isLocalOrDemoMode()) return apiClient.delete(`/intake/evaluations/${taskId}`)
    await db.evaluations.delete(Number(taskId))
    return { data: { success: true } }
  },

  async cancelEvaluation(taskId) {
    if (!isLocalOrDemoMode()) return apiClient.post(`/intake/evaluations/${taskId}/cancel`)
    const task = await db.evaluations.get(Number(taskId))
    if (task) {
      task.status = 'CANCELLED'
      await db.evaluations.put(task)
    }
    return { data: task }
  },

  async retryEvaluation(taskId) {
    if (!isLocalOrDemoMode()) return apiClient.post(`/intake/evaluations/${taskId}/retry`)
    const task = await db.evaluations.get(Number(taskId))
    if (task) {
      task.status = 'COMPLETED'
      await db.evaluations.put(task)
    }
    return { data: task }
  },

  async clearCompletedEvaluations() {
    if (!isLocalOrDemoMode()) return apiClient.post('/intake/evaluations/clear-completed')
    await db.evaluations.where('status').equals('COMPLETED').delete()
    return { data: { success: true } }
  },

  async confirmAssessment(data) {
    if (!isLocalOrDemoMode()) return apiClient.post('/intake/confirm-assessment', data)
    const newApp = {
      id: Date.now(),
      company_name: data.company_name || 'Confirmed Company',
      title: data.job_title || 'Confirmed Role',
      status: 'APPLIED',
      fit_score: 90,
      applied_date: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    await db.applications.add(newApp)
    return { data: newApp }
  },

  async getExtensionConfig() {
    if (!isLocalOrDemoMode()) return apiClient.get('/intake/extension-config')
    return { data: { ai_ready: true, local_mode: true } }
  },

  async syncAccount(data) {
    if (!isLocalOrDemoMode()) return apiClient.post('/intake/sync-account', data)
    return { data: { status: 'disabled', message: 'Email sync disabled in client-first local mode.' } }
  }
}

// Candidate Profile Adapter
export const CandidateProfileAdapter = {
  async get() {
    if (!isLocalOrDemoMode()) return apiClient.get('/profile/cv')
    const profiles = await db.candidate_profile.toArray()
    return { data: profiles[0] || null }
  },

  async save(rawText) {
    if (!isLocalOrDemoMode()) return apiClient.post('/profile/cv', { raw_text: rawText })
    const existing = (await db.candidate_profile.toArray())[0]
    const profile = existing || { id: 1, full_name: 'Alex Mercer', parsed_skills: ['Distributed Systems', 'Go', 'Vue 3'] }
    profile.raw_text = rawText
    profile.updated_at = new Date().toISOString()
    await db.candidate_profile.put(profile)
    return { data: profile }
  },

  async parseFile(formData) {
    if (!isLocalOrDemoMode()) {
      return apiClient.post('/profile/cv/parse-file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    }
    const file = formData.get('file')
    let text = ''
    if (file) {
      text = await file.text()
    }
    return { data: { raw_text: text || 'Extracted local text content' } }
  }
}

// Action Items Adapter
export const ActionItemsAdapter = {
  async list(params = {}) {
    if (!isLocalOrDemoMode()) return apiClient.get('/action-items', { params })
    let items = await db.action_items.toArray()
    if (params.status) items = items.filter(i => i.status === params.status)
    return { data: items }
  },

  async create(data) {
    if (!isLocalOrDemoMode()) return apiClient.post('/action-items', data)
    const newItem = {
      id: Date.now(),
      application_id: data.application_id || null,
      company_name: data.company_name || '',
      title: data.title,
      status: 'PENDING',
      due_date: data.due_date || new Date().toISOString(),
      urgency: data.urgency || 'MEDIUM',
      priority: data.priority || 'MEDIUM',
      notes: data.notes || ''
    }
    await db.action_items.add(newItem)
    return { data: newItem }
  },

  async update(id, data) {
    if (!isLocalOrDemoMode()) return apiClient.patch(`/action-items/${id}`, data)
    const numericId = Number(id)
    const existing = await db.action_items.get(numericId)
    if (!existing) throw new Error('Action item not found')
    const updated = { ...existing, ...data }
    await db.action_items.put(updated)
    return { data: updated }
  },

  async delete(id) {
    if (!isLocalOrDemoMode()) return apiClient.delete(`/action-items/${id}`)
    await db.action_items.delete(Number(id))
    return { data: { success: true } }
  }
}

// Diagnostics Adapter
export const DiagnosticsAdapter = {
  async getStats() {
    if (!isLocalOrDemoMode()) return apiClient.get('/diagnostics/stats')
    const traceCount = await db.diagnostics.count()
    return { data: { total_traces: traceCount, success_traces: traceCount, error_traces: 0 } }
  },

  async getTraces(params = {}) {
    if (!isLocalOrDemoMode()) return apiClient.get('/diagnostics/traces', { params })
    const traces = await db.diagnostics.toArray()
    return { data: traces }
  },

  async purge() {
    if (!isLocalOrDemoMode()) return apiClient.delete('/diagnostics/purge')
    await db.diagnostics.clear()
    return { data: { success: true } }
  }
}

// Analytics Adapter
export const AnalyticsAdapter = {
  async getOverview(params = {}) {
    if (!isLocalOrDemoMode()) return apiClient.get('/analytics/overview', { params })
    const apps = await db.applications.toArray()
    const total = apps.length
    const active = apps.filter(a => !['HIRED', 'REJECTED', 'WITHDRAWN'].includes(a.status)).length
    const offers = apps.filter(a => a.status === 'OFFER' || a.status === 'HIRED').length

    return {
      data: {
        total_applications: total,
        active_applications: active,
        total_offers: offers,
        avg_fit_score: 92
      }
    }
  },

  async getFunnelMetrics(params = {}) {
    if (!isLocalOrDemoMode()) return apiClient.get('/analytics/funnel', { params })
    const apps = await db.applications.toArray()
    const counts = {
      intake: apps.length,
      applied: apps.filter(a => a.status !== 'INTAKE').length,
      interviewing: apps.filter(a => ['ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW'].includes(a.status)).length,
      offers: apps.filter(a => ['OFFER', 'HIRED'].includes(a.status)).length,
      hired: apps.filter(a => a.status === 'HIRED').length
    }
    return { data: counts }
  }
}

// Settings & AI Configuration Adapter
export const AIConfigAdapter = {
  async checkHealth() {
    if (!isLocalOrDemoMode()) return apiClient.get('/config/ai/health')
    const activeProvider = (await db.ai_providers.where('is_active').equals(1).or('is_active').equals(true).toArray())[0]
    return {
      data: {
        status: activeProvider ? 'healthy' : 'unconfigured',
        mode: getStorageMode(),
        active_provider: activeProvider?.name || 'Local IndexedDB BYOK'
      }
    }
  },

  async getGlobalSettings() {
    if (!isLocalOrDemoMode()) return apiClient.get('/ai/global-settings')
    return {
      data: {
        ENABLE_EMBEDDINGS: true,
        ENABLE_AUTO_COVER_LETTER: true,
        COVER_LETTER_MATCH_THRESHOLD: 70,
        COVER_LETTER_LENGTH: 'standard'
      }
    }
  },

  async updateGlobalSettings(data) {
    if (!isLocalOrDemoMode()) return apiClient.patch('/ai/global-settings', data)
    return { data }
  },

  async listProviders() {
    if (!isLocalOrDemoMode()) return apiClient.get('/ai/providers')
    const providers = await db.ai_providers.toArray()
    return { data: providers }
  },

  async createProvider(data) {
    if (!isLocalOrDemoMode()) return apiClient.post('/ai/providers', data)
    const newProv = {
      id: Date.now(),
      name: data.name || 'Custom Provider',
      provider_type: data.provider_type || 'openai',
      base_url: data.base_url || '',
      api_key: data.api_key || '',
      is_active: data.is_active ?? true,
      is_fallback: data.is_fallback ?? false
    }
    await db.ai_providers.add(newProv)
    return { data: newProv }
  },

  async updateProvider(id, data) {
    if (!isLocalOrDemoMode()) return apiClient.patch(`/ai/providers/${id}`, data)
    const prov = await db.ai_providers.get(Number(id))
    if (!prov) throw new Error('Provider not found')
    const updated = { ...prov, ...data }
    await db.ai_providers.put(updated)
    return { data: updated }
  },

  async deleteProvider(id) {
    if (!isLocalOrDemoMode()) return apiClient.delete(`/ai/providers/${id}`)
    await db.ai_providers.delete(Number(id))
    return { data: { success: true } }
  },

  async listBindings() {
    if (!isLocalOrDemoMode()) return apiClient.get('/ai/bindings')
    return { data: [] }
  },

  async setBinding(taskType, data) {
    if (!isLocalOrDemoMode()) return apiClient.put(`/ai/bindings/${taskType}`, data)
    return { data }
  }
}

// Email Accounts Adapter
export const EmailAccountsAdapter = {
  async list() {
    if (!isLocalOrDemoMode()) return apiClient.get('/email_accounts')
    const accounts = await db.email_accounts.toArray()
    return { data: accounts }
  }
}

// Agent Chat Adapter
export const AgentAdapter = {
  async chat(messages, chatId = null) {
    if (!isLocalOrDemoMode()) return apiClient.post('/agent/chat', { messages, chat_id: chatId })

    const lastMsg = messages[messages.length - 1]?.content || ''
    const apps = await db.applications.toArray()
    const appSummary = apps.map(a => `- ${a.title} at ${a.company_name} (${a.status}, Fit: ${a.fit_score}%)`).join('\n')

    const prompt = `User Query: ${lastMsg}\n\nContextual Applications in Local Database:\n${appSummary}`
    const systemPrompt = `You are an intelligent Job Application Assistant operating in client-first local mode.`

    try {
      const response = await executeBYOKCompletion({ prompt, systemPrompt })
      return { data: { response, chat_id: chatId || Date.now() } }
    } catch (err) {
      return {
        data: {
          response: `[Local Agent] I processed your request: "${lastMsg}". You currently have ${apps.length} active applications stored in IndexedDB. (Note: Configure BYOK AI keys in Settings for LLM completions).`,
          chat_id: chatId || Date.now()
        }
      }
    }
  }
}
