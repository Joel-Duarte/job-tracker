import apiClient from './client'

export const ApplicationsAPI = {
  list: (params = {}) => apiClient.get('/applications', { params }),
  get: (id) => apiClient.get(`/applications/${id}`),
  update: (id, data) => apiClient.patch(`/applications/${id}`, data),
  transition: (id, data) => apiClient.post(`/applications/${id}/transition`, data),
  bulkTransition: (data) => apiClient.post('/applications/bulk-transition', data),
  delete: (id) => apiClient.delete(`/applications/${id}`),
  byStatus: () => apiClient.get('/applications/by-status'),
  generateInterviewGuide: (id, data = {}) => apiClient.post(`/applications/${id}/interview-guide`, data),
  clearInterviewGuide: (id) => apiClient.delete(`/applications/${id}/interview-guide`),
  getCoverLetter: (id) => apiClient.get(`/applications/${id}/cover-letter`),
  generateCoverLetter: (id, data = {}) => apiClient.post(`/applications/${id}/cover-letter/generate`, data),
  updateCoverLetter: (id, data) => apiClient.patch(`/applications/${id}/cover-letter`, data),
  regenerateCoverLetter: (id, data = {}) => apiClient.post(`/applications/${id}/cover-letter/regenerate`, data),
}

export const IntakeAPI = {
  paste: (data) => apiClient.post('/intake/paste', data),
  upload: (formData) =>
    apiClient.post('/intake/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  assessJob: (data) => apiClient.post('/intake/assess-job', data),
  enqueueAssessment: (data) => apiClient.post('/intake/enqueue-assessment', data),
  getEvaluations: (limit = 50) => apiClient.get('/intake/evaluations', { params: { limit } }),
  deleteEvaluation: (taskId) => apiClient.delete(`/intake/evaluations/${taskId}`),
  cancelEvaluation: (taskId) => apiClient.post(`/intake/evaluations/${taskId}/cancel`),
  retryEvaluation: (taskId) => apiClient.post(`/intake/evaluations/${taskId}/retry`),
  fixJDEvaluation: (taskId, data) => apiClient.post(`/intake/evaluations/${taskId}/fix-jd`, data),
  bulkRetryEvaluations: (taskIds) => apiClient.post('/intake/evaluations/bulk-retry', { task_ids: taskIds }),
  bulkDeleteEvaluations: (taskIds) => apiClient.post('/intake/evaluations/bulk-delete', { task_ids: taskIds }),
  clearCompletedEvaluations: () => apiClient.post('/intake/evaluations/clear-completed'),
  confirmAssessment: (data) => apiClient.post('/intake/confirm-assessment', data),
  getExtensionConfig: () => apiClient.get('/intake/extension-config'),
  syncAccount: (data) => apiClient.post('/intake/sync-account', data),
  getTaskStatus: (taskId) => apiClient.get(`/intake/tasks/${taskId}`),
}


export const CandidateProfileAPI = {
  get: () => apiClient.get('/profile/cv'),
  save: (rawText) => apiClient.post('/profile/cv', { raw_text: rawText }),
  getTaskStatus: (taskId) => apiClient.get(`/profile/cv/tasks/${taskId}`),
  update: (id, data) => apiClient.patch(`/profile/cv/${id}`, data),
  delete: (id) => apiClient.delete(`/profile/cv/${id}`),
  parseFile: (formData) =>
    apiClient.post('/profile/cv/parse-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

export const AgentAPI = {
  listChats: () => apiClient.get('/agent/chats'),
  getChat: (id) => apiClient.get(`/agent/chats/${id}`),
  deleteChat: (id) => apiClient.delete(`/agent/chats/${id}`),
  chat: (messages, chatId = null) => apiClient.post('/agent/chat', { messages, chat_id: chatId }),
}

export const PromptsAPI = {
  list: () => apiClient.get('/prompts'),
  get: (name) => apiClient.get(`/prompts/${name}`),
  update: (name, template) => apiClient.patch(`/prompts/${name}`, { template }),
  reset: (name) => apiClient.post(`/prompts/${name}/reset`),
}

export const StagingAPI = {
  list: (params = {}) => apiClient.get('/staging', { params }),
  resolve: (id, data) => apiClient.post(`/staging/${id}/resolve`, data),
  delete: (id) => apiClient.delete(`/staging/${id}`),
}

export const SearchAPI = {
  semantic: (query, limit = 10, threshold = 0.5) =>
    apiClient.get('/search/semantic', { params: { query, limit, threshold } }),
  companies: (q = '') => apiClient.get('/search/companies', { params: { q } }),
}

export const SystemSettingsAPI = {
  get: () => apiClient.get('/config/system'),
  update: (data) => apiClient.patch('/config/system', data),
}

export const AIConfigAPI = {
  checkHealth: () => apiClient.get('/config/ai/health'),
  getGlobalSettings: () => apiClient.get('/ai/global-settings'),
  updateGlobalSettings: (data) => apiClient.patch('/ai/global-settings', data),
  reindexEmbeddings: () => apiClient.post('/ai/reindex-embeddings'),
  listProviders: () => apiClient.get('/ai/providers'),
  createProvider: (data) => apiClient.post('/ai/providers', data),
  updateProvider: (id, data) => apiClient.patch(`/ai/providers/${id}`, data),
  deleteProvider: (id) => apiClient.delete(`/ai/providers/${id}`),
  testProvider: (id) => apiClient.post(`/ai/providers/${id}/test`),
  getProviderModels: (id) => apiClient.get(`/ai/providers/${id}/models`),
  probeModel: (id, modelName) => apiClient.post(`/ai/providers/${id}/probe-model`, { model_name: modelName }),
  listBindings: () => apiClient.get('/ai/bindings'),
  setBinding: (taskType, data) => apiClient.put(`/ai/bindings/${taskType}`, data),
  deleteBinding: (taskType) => apiClient.delete(`/ai/bindings/${taskType}`),
  testBinding: (taskType) => apiClient.post(`/ai/bindings/${taskType}/test`),
}


export const EmailAccountsAPI = {
  list: () => apiClient.get('/email_accounts'),
  get: (id) => apiClient.get(`/email_accounts/${id}`),
  create: (data) => apiClient.post('/email_accounts', data),
  update: (id, data) => apiClient.patch(`/email_accounts/${id}`, data),
  delete: (id) => apiClient.delete(`/email_accounts/${id}`),
  getOAuthUrl: (params) => apiClient.get('/email_accounts/oauth/authorize-url', { params }),
  getOAuthConfig: () => apiClient.get('/email_accounts/oauth/config'),
  getFolders: (id) => apiClient.get(`/email_accounts/${id}/folders`),
  clearHistory: (id) => apiClient.delete(`/email_accounts/${id}/processed-emails`),
  clearAllHistory: () => apiClient.delete('/email_accounts/processed-emails/all'),
}

export const ActionItemsAPI = {
  list: (params = {}) => apiClient.get('/action-items', { params }),
  create: (data) => apiClient.post('/action-items', data),
  update: (id, data) => apiClient.patch(`/action-items/${id}`, data),
  updateUrgency: (id, manual_urgency) => apiClient.put(`/action-items/${id}/urgency`, { manual_urgency }),
  delete: (id) => apiClient.delete(`/action-items/${id}`),
}

export const DiagnosticsAPI = {
  export: () => apiClient.get('/diagnostics/export', { responseType: 'blob' }),
  getStats: () => apiClient.get('/diagnostics/stats'),
  getTraces: (params = {}) => apiClient.get('/diagnostics/traces', { params }),
  getTrace: (runId) => apiClient.get(`/diagnostics/traces/${runId}`),
  purge: () => apiClient.delete('/diagnostics/purge')
}
export const AnalyticsAPI = {
  getOverview: (params = {}) => apiClient.get('/analytics/overview', { params }),
  getWorkModelBreakdown: () => apiClient.get('/analytics/work-model-breakdown'),
  getFunnelMetrics: (params = {}) => apiClient.get('/analytics/funnel', { params }),
}

export const InterviewSimulatorAPI = {
  startSession: (data) => apiClient.post('/interviews/sessions/start', data),
  evaluateAnswer: (sessionId, data) => apiClient.post(`/interviews/sessions/${sessionId}/evaluate-answer`, data),
  nextQuestion: (sessionId) => apiClient.post(`/interviews/sessions/${sessionId}/next-question`),
  drillDown: (sessionId, data = {}) => apiClient.post(`/interviews/sessions/${sessionId}/drill-down`, data),
  finalizeSession: (sessionId) => apiClient.post(`/interviews/sessions/${sessionId}/finalize`),
  saveNotes: (sessionId, data = {}) => apiClient.post(`/interviews/sessions/${sessionId}/save-notes`, data),
  getSession: (sessionId) => apiClient.get(`/interviews/sessions/${sessionId}`),
  listSessions: (params = {}) => apiClient.get('/interviews/sessions', { params }),
  deleteSession: (sessionId) => apiClient.delete(`/interviews/sessions/${sessionId}`),
}

export const EventsAPI = {
  delete: (id, source = 'application') => apiClient.delete(`/events/${id}`, { params: { source } }),
}

