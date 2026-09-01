import { defineStore } from 'pinia'
import { ref } from 'vue'
import { AnalyticsAPI, IntakeAPI } from '../api/endpoints'
import { useUIStore } from './uiStore'
import { useQueueStore } from './queueStore'

const STORAGE_KEY_PREFIX = 'jt_analytics_v2_'

const DEFAULT_OVERVIEW = {
  total_applications: 0,
  active_pipeline_count: 0,
  interview_rate: 0.0,
  offer_rate: 0.0,
  average_fit_score: null,
  top_in_demand_skills: [],
  priority_skill_gaps: [],
  pipeline_funnel: [
    { stage: 'Applied', count: 0, conversion_rate: 0, dropoff_rate: 0, dropped_count: 0, active_count: 0 },
    { stage: 'Interview', count: 0, conversion_rate: 0, dropoff_rate: 0, dropped_count: 0, active_count: 0 },
    { stage: 'Offer', count: 0, conversion_rate: 0, dropoff_rate: 0, dropped_count: 0, active_count: 0 },
  ],
  work_model_distribution: { remote_count: 0, hybrid_count: 0, onsite_count: 0, unknown_count: 0 },
  salary_insights: [],
}

const DEFAULT_FUNNEL = {
  period_type: 'weekly',
  summary_kpis: {
    intakes: { label: 'Total Intake Leads', value: 0, trend_percentage: null, is_positive: true },
    applications: { label: 'Submitted Applications', value: 0, trend_percentage: null, is_positive: true },
    interviews: { label: 'Interview Conversions', value: 0, trend_percentage: null, is_positive: true },
    offers: { label: 'Offers Received', value: 0, trend_percentage: null, is_positive: true },
  },
  chart_data: [],
  table_data: [],
}

const DEFAULT_ALIGNMENT = {
  detected_tracks: [
    { key: 'all', label: 'All Tracks', job_count: 0 },
    { key: 'backend', label: 'Backend Engineering', job_count: 0 },
    { key: 'fullstack', label: 'Full-Stack Engineering', job_count: 0 },
    { key: 'frontend', label: 'Frontend Engineering', job_count: 0 },
    { key: 'data_ai', label: 'AI & Data Engineering', job_count: 0 },
    { key: 'devops', label: 'DevOps & Cloud SRE', job_count: 0 },
  ],
  selected_track: 'all',
  total_analyzed_jobs: 0,
  vocabulary_shifts: [],
  bullet_reframes: [],
  missing_prerequisites: [],
}

function loadCachedData(key, fallback) {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${key}`)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function saveCachedData(key, value) {
  try {
    if (value) {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${key}`, JSON.stringify(value))
    } else {
      localStorage.removeItem(`${STORAGE_KEY_PREFIX}${key}`)
    }
  } catch {}
}

export const useAnalyticsStore = defineStore('analytics', () => {
  const uiStore = useUIStore()

  // Overview / Market State (Instant 0ms render from localStorage or default template)
  const overviewData = ref(loadCachedData('overview', DEFAULT_OVERVIEW))
  const loadingOverview = ref(false)
  const lastFetchedOverview = ref(null)
  const overviewFiltersKey = ref('')

  // Funnel Performance State
  const funnelData = ref(loadCachedData('funnel', DEFAULT_FUNNEL))
  const loadingFunnel = ref(false)
  const lastFetchedFunnel = ref(null)
  const funnelPeriodKey = ref('')

  // Role Alignment State (Keyed by track/query for instant switching)
  const roleAlignmentCache = ref(
    loadCachedData('alignment', {
      'all-all': DEFAULT_ALIGNMENT,
    })
  )
  const loadingAlignment = ref(false)
  const lastFetchedAlignment = ref({})

  // Global recalculation state
  const isRecalculating = ref(false)
  const lastRecalculatedAt = ref(null)

  const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes

  function invalidateAll() {
    lastFetchedOverview.value = null
    lastFetchedFunnel.value = null
    lastFetchedAlignment.value = {}
    roleAlignmentCache.value = { 'all-all': DEFAULT_ALIGNMENT }
    overviewData.value = DEFAULT_OVERVIEW
    funnelData.value = DEFAULT_FUNNEL
    saveCachedData('overview', null)
    saveCachedData('funnel', null)
    saveCachedData('alignment', null)
  }

  async function fetchOverview(params = {}, force = false) {
    const key = JSON.stringify(params)
    const isFresh =
      !force &&
      overviewData.value &&
      overviewFiltersKey.value === key &&
      lastFetchedOverview.value &&
      Date.now() - lastFetchedOverview.value < CACHE_TTL_MS

    if (isFresh) return overviewData.value

    try {
      const res = await AnalyticsAPI.getOverview(params)
      overviewData.value = res.data
      lastFetchedOverview.value = Date.now()
      overviewFiltersKey.value = key
      saveCachedData('overview', res.data)
      return res.data
    } catch (err) {
      // Background revalidation error: silent fallback to existing cached UI
      console.warn('Silent analytics overview background refresh error:', err)
    } finally {
      loadingOverview.value = false
    }
  }

  async function fetchFunnel(params = {}, force = false) {
    const period = params.period || 'weekly'
    const isFresh =
      !force &&
      funnelData.value &&
      funnelPeriodKey.value === period &&
      lastFetchedFunnel.value &&
      Date.now() - lastFetchedFunnel.value < CACHE_TTL_MS

    if (isFresh) return funnelData.value

    try {
      const res = await AnalyticsAPI.getFunnelMetrics(params)
      funnelData.value = res.data
      lastFetchedFunnel.value = Date.now()
      funnelPeriodKey.value = period
      saveCachedData('funnel', res.data)
      return res.data
    } catch (err) {
      console.warn('Silent funnel metrics background refresh error:', err)
    } finally {
      loadingFunnel.value = false
    }
  }

  async function fetchRoleAlignment(params = {}, force = false) {
    const track = (params.role_track || 'all').trim().toLowerCase()
    const days = params.days || null
    const cacheKey = `${track}-${days || 'all'}`

    const cached = roleAlignmentCache.value[cacheKey]
    const lastTime = lastFetchedAlignment.value[cacheKey]
    const isFresh = !force && cached && lastTime && Date.now() - lastTime < CACHE_TTL_MS

    if (isFresh) return cached

    try {
      const res = await AnalyticsAPI.getRoleAlignment(params)
      const updatedCache = {
        ...roleAlignmentCache.value,
        [cacheKey]: res.data,
      }
      roleAlignmentCache.value = updatedCache
      lastFetchedAlignment.value = {
        ...lastFetchedAlignment.value,
        [cacheKey]: Date.now(),
      }
      saveCachedData('alignment', updatedCache)
      return res.data
    } catch (err) {
      console.warn('Silent role alignment background refresh error:', err)
    } finally {
      loadingAlignment.value = false
    }
  }

  async function recalculate(currentFilters = {}) {
    isRecalculating.value = true
    try {
      await AnalyticsAPI.recalculate()
      invalidateAll()
      lastRecalculatedAt.value = Date.now()

      // Re-fetch current visible data
      await Promise.allSettled([
        fetchOverview(currentFilters.overviewParams || {}, true),
        fetchFunnel(currentFilters.funnelParams || {}, true),
        fetchRoleAlignment(currentFilters.alignmentParams || {}, true),
      ])
      uiStore.showToast('Analytics synchronized!', 'success')
    } catch (err) {
      uiStore.showToast(err.message || 'Failed to recalculate analytics', 'error')
    } finally {
      isRecalculating.value = false
    }
  }

  // AI Strategic Dossier State (Keyed by track)
  const dossierCache = ref(loadCachedData('dossiers', {}))
  const loadingDossier = ref(false)

  async function fetchDossier(role_track = 'all', force = false) {
    const track = (role_track || 'all').trim().toLowerCase()
    if (!force && dossierCache.value[track]) {
      return dossierCache.value[track]
    }

    try {
      const res = await AnalyticsAPI.getRoleAlignmentDossier(track)
      if (res?.data) {
        const updated = {
          ...dossierCache.value,
          [track]: res.data,
        }
        dossierCache.value = updated
        saveCachedData('dossiers', updated)
        return res.data
      }
      return null
    } catch (err) {
      console.warn('Silent dossier fetch error:', err)
      return null
    }
  }

  async function enhanceDossier(role_track = 'all') {
    const track = (role_track || 'all').trim().toLowerCase()
    loadingDossier.value = true
    try {
      const res = await AnalyticsAPI.enhanceRoleAlignment(track)
      const taskId = res?.data?.task_id

      if (!taskId) {
        // Fallback for direct response or demo mode
        if (res?.data?.dossier) {
          const updated = {
            ...dossierCache.value,
            [track]: res.data,
          }
          dossierCache.value = updated
          saveCachedData('dossiers', updated)
          uiStore.showToast('✨ AI Strategic Dossier synthesized successfully!', 'success')
          return res.data
        }
        return null
      }

      // Notify queue store so floating queue widget updates immediately
      const queueStore = useQueueStore()
      queueStore.fetchTasks(true)
      uiStore.showToast('Queued AI Strategic Dossier synthesis in background...', 'info')

      // Poll task until COMPLETED or FAILED
      let attempts = 0
      const maxAttempts = 60 // 2 minutes (every 2s)
      while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 2000))
        attempts++
        try {
          const taskRes = await IntakeAPI.getEvaluation(taskId)
          const taskData = taskRes?.data
          if (taskData?.status === 'COMPLETED') {
            const freshDossier = await fetchDossier(track, true)
            queueStore.fetchTasks(true)
            uiStore.showToast('✨ AI Strategic Dossier synthesized successfully!', 'success')
            return freshDossier
          } else if (taskData?.status === 'FAILED' || taskData?.status === 'CANCELLED') {
            queueStore.fetchTasks(true)
            throw new Error(taskData?.error_message || 'AI dossier synthesis task failed.')
          }
        } catch (pollErr) {
          if (pollErr.message && !pollErr.message.includes('Network Error')) {
            throw pollErr
          }
        }
      }
      throw new Error('AI dossier synthesis timed out in background queue.')
    } catch (err) {
      uiStore.showToast(err.message || 'Failed to synthesize AI Strategic Dossier', 'error')
      throw err
    } finally {
      loadingDossier.value = false
    }
  }

  return {
    overviewData,
    loadingOverview,
    lastFetchedOverview,
    funnelData,
    loadingFunnel,
    lastFetchedFunnel,
    roleAlignmentCache,
    loadingAlignment,
    lastFetchedAlignment,
    dossierCache,
    loadingDossier,
    isRecalculating,
    lastRecalculatedAt,
    fetchOverview,
    fetchFunnel,
    fetchRoleAlignment,
    fetchDossier,
    enhanceDossier,
    recalculate,
    invalidateAll,
  }
})
