import apiClient from './client'
import {
  ApplicationsAdapter,
  IntakeAdapter,
  CandidateProfileAdapter,
  AgentAdapter,
  ActionItemsAdapter,
  DiagnosticsAdapter,
  AnalyticsAdapter,
  AIConfigAdapter,
  SystemSettingsAdapter,
  EmailAccountsAdapter
} from '../services/storageAdapter'

export const ApplicationsAPI = {
  list: (params = {}) => ApplicationsAdapter.list(params),
  get: (id) => ApplicationsAdapter.get(id),
  update: (id, data) => ApplicationsAdapter.update(id, data),
  transition: (id, data) => ApplicationsAdapter.transition(id, data),
  bulkTransition: (data) => ApplicationsAdapter.bulkTransition(data),
  delete: (id) => ApplicationsAdapter.delete(id),
  byStatus: () => ApplicationsAdapter.byStatus(),
  generateInterviewGuide: (id, data = {}) => ApplicationsAdapter.generateInterviewGuide(id, data),
  clearInterviewGuide: (id) => ApplicationsAdapter.clearInterviewGuide(id),
  getCoverLetter: (id) => ApplicationsAdapter.getCoverLetter(id),
  generateCoverLetter: (id, data = {}) => ApplicationsAdapter.generateCoverLetter(id, data),
  updateCoverLetter: (id, data) => ApplicationsAdapter.updateCoverLetter(id, data),
  regenerateCoverLetter: (id, data = {}) => ApplicationsAdapter.regenerateCoverLetter(id, data),
}

export const IntakeAPI = {
  paste: (data) => IntakeAdapter.paste(data),
  upload: (formData) => IntakeAdapter.upload ? IntakeAdapter.upload(formData) : apiClient.post('/intake/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  assessJob: (data) => apiClient.post('/intake/assess-job', data),
  enqueueAssessment: (data) => IntakeAdapter.enqueueAssessment(data),
  getEvaluations: (limit = 50) => IntakeAdapter.getEvaluations(limit),
  deleteEvaluation: (taskId) => IntakeAdapter.deleteEvaluation(taskId),
  cancelEvaluation: (taskId) => IntakeAdapter.cancelEvaluation(taskId),
  retryEvaluation: (taskId) => IntakeAdapter.retryEvaluation(taskId),
  fixJDEvaluation: (taskId, data) => apiClient.post(`/intake/evaluations/${taskId}/fix-jd`, data),
  bulkRetryEvaluations: (taskIds) => apiClient.post('/intake/evaluations/bulk-retry', { task_ids: taskIds }),
  bulkDeleteEvaluations: (taskIds) => apiClient.post('/intake/evaluations/bulk-delete', { task_ids: taskIds }),
  clearCompletedEvaluations: () => IntakeAdapter.clearCompletedEvaluations(),
  confirmAssessment: (data) => IntakeAdapter.confirmAssessment(data),
  getExtensionConfig: () => IntakeAdapter.getExtensionConfig(),
  syncAccount: (data) => IntakeAdapter.syncAccount(data),
  getTaskStatus: (taskId) => apiClient.get(`/intake/tasks/${taskId}`),
}

export const CandidateProfileAPI = {
  get: () => CandidateProfileAdapter.get(),
  save: (rawText) => CandidateProfileAdapter.save(rawText),
  getTaskStatus: (taskId) => apiClient.get(`/profile/cv/tasks/${taskId}`),
  update: (id, data) => CandidateProfileAdapter.update ? CandidateProfileAdapter.update(id, data) : apiClient.patch(`/profile/cv/${id}`, data),
  delete: (id) => CandidateProfileAdapter.delete ? CandidateProfileAdapter.delete(id) : apiClient.delete(`/profile/cv/${id}`),
  parseFile: (formData) => CandidateProfileAdapter.parseFile(formData),
}

export const AgentAPI = {
  listChats: () => apiClient.get('/agent/chats'),
  getChat: (id) => apiClient.get(`/agent/chats/${id}`),
  deleteChat: (id) => apiClient.delete(`/agent/chats/${id}`),
  chat: (messages, chatId = null) => AgentAdapter.chat(messages, chatId),
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
  clearResolved: (daysOlderThan = null) =>
    apiClient.delete('/staging/resolved', {
      params: daysOlderThan !== null ? { days_older_than: daysOlderThan } : {},
    }),
}

export const SearchAPI = {
  semantic: (query, limit = 10, threshold = 0.5) =>
    apiClient.get('/search/semantic', { params: { query, limit, threshold } }),
  companies: (q = '') => apiClient.get('/search/companies', { params: { q } }),
}

export const SystemSettingsAPI = {
  get: () => SystemSettingsAdapter.get(),
  update: (data) => SystemSettingsAdapter.update(data),
}

export const AIConfigAPI = {
  checkHealth: () => AIConfigAdapter.checkHealth(),
  getGlobalSettings: () => AIConfigAdapter.getGlobalSettings(),
  updateGlobalSettings: (data) => AIConfigAdapter.updateGlobalSettings(data),
  reindexEmbeddings: () => apiClient.post('/ai/reindex-embeddings'),
  listProviders: () => AIConfigAdapter.listProviders(),
  createProvider: (data) => AIConfigAdapter.createProvider(data),
  updateProvider: (id, data) => AIConfigAdapter.updateProvider(id, data),
  deleteProvider: (id) => AIConfigAdapter.deleteProvider(id),
  testProvider: (id) => apiClient.post(`/ai/providers/${id}/test`),
  getProviderModels: (id) => apiClient.get(`/ai/providers/${id}/models`),
  probeModel: (id, modelName) => apiClient.post(`/ai/providers/${id}/probe-model`, { model_name: modelName }),
  listBindings: () => AIConfigAdapter.listBindings(),
  setBinding: (taskType, data) => AIConfigAdapter.setBinding(taskType, data),
  deleteBinding: (taskType) => apiClient.delete(`/ai/bindings/${taskType}`),
  testBinding: (taskType) => apiClient.post(`/ai/bindings/${taskType}/test`),
}

export const EmailAccountsAPI = {
  list: () => EmailAccountsAdapter.list(),
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
  list: (params = {}) => ActionItemsAdapter.list(params),
  create: (data) => ActionItemsAdapter.create(data),
  update: (id, data) => ActionItemsAdapter.update(id, data),
  updateUrgency: (id, manual_urgency) => ActionItemsAdapter.update(id, { manual_urgency }),
  delete: (id) => ActionItemsAdapter.delete(id),
}

export const DiagnosticsAPI = {
  export: () => apiClient.get('/diagnostics/export', { responseType: 'blob' }),
  getStats: () => DiagnosticsAdapter.getStats(),
  getTraces: (params = {}) => DiagnosticsAdapter.getTraces(params),
  getTrace: (runId) => apiClient.get(`/diagnostics/traces/${runId}`),
  purge: () => DiagnosticsAdapter.purge()
}

export const AnalyticsAPI = {
  getOverview: (params = {}) => AnalyticsAdapter.getOverview(params),
  getWorkModelBreakdown: () => apiClient.get('/analytics/work-model-breakdown'),
  getFunnelMetrics: (params = {}) => AnalyticsAdapter.getFunnelMetrics(params),
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
