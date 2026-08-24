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

// Response interceptor for error normalization
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred'
    console.error('[API Error]:', message)
    return Promise.reject(new Error(message))
  }
)

export default apiClient
