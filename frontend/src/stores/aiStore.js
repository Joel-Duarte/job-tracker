import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { AIConfigAPI } from '../api/endpoints'
import { useUIStore } from './uiStore'

export const useAIStore = defineStore('ai', () => {
  const uiStore = useUIStore()

  const providers = ref([])
  const loadingProviders = ref(false)
  const vramStatus = ref({
    provider_id: null,
    provider_name: '',
    engine: '',
    status: 'UNKNOWN', // 'ACTIVE' | 'SLEEPING' | 'UNKNOWN'
    is_loaded: false,
    vram_allocated_mb: 0,
    message: '',
  })
  const isReleasingVRAM = ref(false)
  const isBenchmarking = ref(false)
  const benchmarkResult = ref(null)
  const isWakingUp = ref(false)

  // Determine if a provider is local / private
  function isProviderLocal(provider) {
    if (!provider) return false
    const type = (provider.provider_type || '').toLowerCase()
    if (type === 'ollama' || type === 'local') return true
    const url = (provider.base_url || '').toLowerCase()
    if (
      url.includes('localhost') ||
      url.includes('127.0.0.1') ||
      url.includes('192.168.') ||
      url.includes('10.') ||
      url.includes('172.16.') ||
      url.includes('0.0.0.0') ||
      url.includes(':1234') ||
      url.includes(':11434') ||
      url.includes(':8000') ||
      url.includes(':30000')
    ) {
      return true
    }
    const inCost = Number(provider.input_cost_per_million) || 0
    const outCost = Number(provider.output_cost_per_million) || 0
    return inCost === 0 && outCost === 0 && (type === 'openai' || type === 'custom')
  }

  const activeLocalProvider = computed(() => {
    return providers.value.find((p) => p.is_active && isProviderLocal(p)) || null
  })

  const isLocalActive = computed(() => {
    return Boolean(activeLocalProvider.value)
  })

  const localModelStatus = computed(() => {
    if (isWakingUp.value) return 'WAKING'
    if (vramStatus.value.status === 'SLEEPING' || (!vramStatus.value.is_loaded && vramStatus.value.status !== 'ACTIVE')) {
      return 'SLEEPING'
    }
    if (vramStatus.value.status === 'ACTIVE' || vramStatus.value.is_loaded) {
      return 'ACTIVE'
    }
    return 'UNKNOWN'
  })

  async function fetchProviders() {
    loadingProviders.value = true
    try {
      const res = await AIConfigAPI.listProviders()
      providers.value = res.data || []
      if (activeLocalProvider.value) {
        await fetchVRAMStatus(activeLocalProvider.value.id)
      }
    } catch (err) {
      console.warn('Failed to load AI providers in aiStore:', err)
    } finally {
      loadingProviders.value = false
    }
  }

  async function fetchVRAMStatus(providerId = null) {
    const targetId = providerId || activeLocalProvider.value?.id
    if (!targetId) return

    try {
      const res = await AIConfigAPI.getVRAMStatus(targetId)
      if (res.data) {
        vramStatus.value = {
          provider_id: res.data.provider_id,
          provider_name: res.data.provider_name,
          engine: res.data.engine,
          status: res.data.status,
          is_loaded: Boolean(res.data.is_loaded),
          vram_allocated_mb: res.data.vram_allocated_mb || 0,
          message: res.data.message || '',
        }
      }
    } catch (err) {
      console.warn('Failed to fetch VRAM status for provider', targetId, err)
    }
  }

  async function releaseVRAM(providerId = null) {
    const targetId = providerId || activeLocalProvider.value?.id
    if (!targetId) {
      uiStore.showToast('No active local AI provider configured for VRAM release', 'warning')
      return false
    }

    isReleasingVRAM.value = true
    try {
      const res = await AIConfigAPI.releaseVRAM(targetId)
      vramStatus.value = {
        ...vramStatus.value,
        status: 'SLEEPING',
        is_loaded: false,
        vram_allocated_mb: 0,
      }
      uiStore.showToast(res.data?.message || 'Model unloaded. GPU VRAM released successfully.', 'success')
      return true
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to release GPU VRAM'
      uiStore.showToast(msg, 'error')
      return false
    } finally {
      isReleasingVRAM.value = false
    }
  }

  function triggerWakeUpNotification() {
    if (localModelStatus.value === 'SLEEPING') {
      isWakingUp.value = true
      uiStore.showToast('Waking up local model & loading weights to GPU (3–5s)...', 'info', 5000)
      setTimeout(async () => {
        isWakingUp.value = false
        if (activeLocalProvider.value) {
          await fetchVRAMStatus(activeLocalProvider.value.id)
        }
      }, 4500)
    }
  }

  async function runCapacityBenchmark(providerId, payload = {}) {
    isBenchmarking.value = true
    benchmarkResult.value = null
    try {
      const res = await AIConfigAPI.runBenchmark(providerId, payload)
      benchmarkResult.value = res.data
      return res.data
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Capacity benchmark failed'
      uiStore.showToast(msg, 'error')
      throw err
    } finally {
      isBenchmarking.value = false
    }
  }

  return {
    providers,
    loadingProviders,
    vramStatus,
    isReleasingVRAM,
    isBenchmarking,
    benchmarkResult,
    isWakingUp,
    activeLocalProvider,
    isLocalActive,
    localModelStatus,
    isProviderLocal,
    fetchProviders,
    fetchVRAMStatus,
    releaseVRAM,
    triggerWakeUpNotification,
    runCapacityBenchmark,
  }
})
