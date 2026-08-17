import apiClient from './client'

export const ApplicationsAPI = {
  list: (params = {}) => apiClient.get('/applications', { params }),
  get: (id) => apiClient.get(`/applications/${id}`),
  update: (id, data) => apiClient.patch(`/applications/${id}`, data),
  transition: (id, data) => apiClient.post(`/applications/${id}/transition`, data),
  delete: (id) => apiClient.delete(`/applications/${id}`),
  byStatus: () => apiClient.get('/applications/by-status'),
  generateInterviewGuide: (id, data = {}) => apiClient.post(`/applications/${id}/interview-guide`, data),
  clearInterviewGuide: (id) => apiClient.delete(`/applications/${id}/interview-guide`),
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
  retryEvaluation: (taskId) => apiClient.post(`/intake/evaluations/${taskId}/retry`),
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
}

export const AgentAPI = {
  chat: (payload) => apiClient.post('/agent/chat', payload),
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

export const AIConfigAPI = {
  getGlobalSettings: () => apiClient.get('/ai/global-settings'),
  updateGlobalSettings: (data) => apiClient.patch('/ai/global-settings', data),
  reindexEmbeddings: () => apiClient.post('/ai/reindex-embeddings'),
  listProviders: () => apiClient.get('/ai/providers'),
  createProvider: (data) => apiClient.post('/ai/providers', data),
  updateProvider: (id, data) => apiClient.patch(`/ai/providers/${id}`, data),
  deleteProvider: (id) => apiClient.delete(`/ai/providers/${id}`),
  testProvider: (id) => apiClient.post(`/ai/providers/${id}/test`),
  getProviderModels: (id) => apiClient.get(`/ai/providers/${id}/models`),
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
}

export const ActionItemsAPI = {
  list: (params = {}) => apiClient.get('/action-items', { params }),
  create: (data) => apiClient.post('/action-items', data),
  update: (id, data) => apiClient.patch(`/action-items/${id}`, data),
  updateUrgency: (id, manual_urgency) => apiClient.put(`/action-items/${id}/urgency`, { manual_urgency }),
  delete: (id) => apiClient.delete(`/action-items/${id}`),
}
