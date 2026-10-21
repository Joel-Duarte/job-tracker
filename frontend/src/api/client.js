import axios from 'axios'
import { isDemoModeEnabled } from '../demo/demoStorage'
import { handleDemoRequest } from '../demo/apiAdapter'

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for client Demo Mode handling
apiClient.interceptors.request.use(
  async (config) => {
    if (isDemoModeEnabled()) {
      config.adapter = async (adapterConfig) => {
        return await handleDemoRequest(adapterConfig)
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for automatic store invalidation on mutations & error normalization
let mutationSyncTimer = null

function shouldTriggerApplicationsSync(config) {
  if (!config) return false
  const method = (config.method || 'get').toLowerCase()
  if (!['post', 'put', 'patch', 'delete'].includes(method)) return false
  const url = (config.url || '').split('?')[0]
  return (
    url.startsWith('/applications') ||
    url.startsWith('/action-items') ||
    url.startsWith('/staging') ||
    url.startsWith('/events') ||
    url.startsWith('/intake')
  )
}

apiClient.interceptors.response.use(
  (response) => {
    if (shouldTriggerApplicationsSync(response.config)) {
      import('../stores/applicationsStore')
        .then(({ useApplicationsStore }) => {
          const appStore = useApplicationsStore()
          appStore.invalidateCache()
          if (mutationSyncTimer) clearTimeout(mutationSyncTimer)
          mutationSyncTimer = setTimeout(() => {
            appStore.fetchApplications(true)
            const url = (response.config?.url || '').split('?')[0]
            if (
              appStore.selectedApplication?.id &&
              !url.startsWith(`/applications/${appStore.selectedApplication.id}`)
            ) {
              appStore.fetchApplicationDetail(appStore.selectedApplication.id)
            }
          }, 120)
        })
        .catch(() => {})
    }
    return response
  },
  (error) => {
    let message = 'An unexpected error occurred'
    const data = error.response?.data

    if (data?.detail) {
      if (Array.isArray(data.detail)) {
        // FastAPI 422 validation errors: array of { loc, msg, type }
        message = data.detail
          .map((item) => {
            if (typeof item === 'string') return item
            const field = item.loc ? item.loc.slice(1).join('.') : ''
            return field ? `${field}: ${item.msg}` : item.msg || JSON.stringify(item)
          })
          .join(', ')
      } else if (typeof data.detail === 'object') {
        message = data.detail.msg || data.detail.message || JSON.stringify(data.detail)
      } else {
        message = String(data.detail)
      }
    } else if (data?.message) {
      message = typeof data.message === 'object' ? JSON.stringify(data.message) : String(data.message)
    } else if (error.message) {
      message = error.message
    }

    console.error('[API Error]:', message)
    return Promise.reject(new Error(message))
  }
)

export default apiClient
