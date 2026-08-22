import { defineStore } from 'pinia'
import { ref } from 'vue'
import { AIConfigAPI } from '../api/endpoints'

export const useUIStore = defineStore('ui', () => {
  const theme = ref(localStorage.getItem('jt_theme') || 'midnight')
  const viewMode = ref(localStorage.getItem('jt_view_mode') || 'kanban') // 'kanban' | 'table'
  const isIngestModalOpen = ref(false)
  const isJobIntakeModalOpen = ref(false)
  const isCommandPaletteOpen = ref(false)
  const isCoverLetterModalOpen = ref(false)
  const coverLetterAppId = ref(null)
  const activeDetailId = ref(null)
  const detailActiveTab = ref('timeline')

  // Notification Toast
  const toast = ref({
    show: false,
    message: '',
    type: 'info', // 'info' | 'success' | 'error' | 'warning'
  })

  function showToast(message, type = 'info', duration = 4000) {
    toast.value = { show: true, message, type }
    setTimeout(() => {
      if (toast.value.message === message) {
        toast.value.show = false
      }
    }, duration)
  }

  function hideToast() {
    toast.value.show = false
  }

  function openJobIntakeModal() {
    isJobIntakeModalOpen.value = true
  }

  function closeJobIntakeModal() {
    isJobIntakeModalOpen.value = false
  }

  function openIngestModal() {
    isIngestModalOpen.value = true
  }

  function closeIngestModal() {
    isIngestModalOpen.value = false
  }

  function openCoverLetterModal(appId) {
    coverLetterAppId.value = appId
    isCoverLetterModalOpen.value = true
  }

  function closeCoverLetterModal() {
    isCoverLetterModalOpen.value = false
    coverLetterAppId.value = null
  }

  const customDarkBg = ref(localStorage.getItem('jt_custom_dark_bg') || '')
  const customDarkSurface = ref(localStorage.getItem('jt_custom_dark_surface') || '')
  const customDarkPrimary = ref(localStorage.getItem('jt_custom_dark_primary') || '')
  const customDarkBorder = ref(localStorage.getItem('jt_custom_dark_border') || '')

  const customLightBg = ref(localStorage.getItem('jt_custom_light_bg') || '')
  const customLightSurface = ref(localStorage.getItem('jt_custom_light_surface') || '')
  const customLightPrimary = ref(localStorage.getItem('jt_custom_light_primary') || '')
  const customLightBorder = ref(localStorage.getItem('jt_custom_light_border') || '')

  function hexToRgba(hex, alpha) {
    if (!hex || !hex.startsWith('#')) return `rgba(56, 189, 248, ${alpha})`
    let c = hex.substring(1)
    if (c.length === 3) c = c.split('').map((x) => x + x).join('')
    const num = parseInt(c, 16)
    if (isNaN(num)) return `rgba(56, 189, 248, ${alpha})`
    const r = (num >> 16) & 255
    const g = (num >> 8) & 255
    const b = num & 255
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }

  function getContrastColor(hex) {
    if (!hex || !hex.startsWith('#')) return '#ffffff'
    let c = hex.substring(1)
    if (c.length === 3) c = c.split('').map((x) => x + x).join('')
    const num = parseInt(c, 16)
    if (isNaN(num)) return '#ffffff'
    const r = (num >> 16) & 255
    const g = (num >> 8) & 255
    const b = num & 255
    // Relative luminance YIQ calculation (WCAG standard)
    const yiq = (r * 299 + g * 587 + b * 114) / 1000
    return yiq >= 128 ? '#0a0d14' : '#ffffff'
  }

  function applyCustomColors() {
    const isDark = theme.value === 'midnight'
    const bg = isDark ? customDarkBg.value : customLightBg.value
    const surface = isDark ? customDarkSurface.value : customLightSurface.value
    const primary = isDark ? customDarkPrimary.value : customLightPrimary.value
    const border = isDark ? customDarkBorder.value : customLightBorder.value

    const rootStyle = document.documentElement.style

    // 1. Background Canvas
    if (bg) {
      rootStyle.setProperty('--bg-app', bg)
    } else {
      rootStyle.removeProperty('--bg-app')
    }

    // 2. Card / Surface
    if (surface) {
      rootStyle.setProperty('--bg-surface', surface)
      rootStyle.setProperty('--bg-card', surface)
      rootStyle.setProperty('--bg-main', surface)
      rootStyle.setProperty('--bg-elevated', surface)
    } else {
      rootStyle.removeProperty('--bg-surface')
      rootStyle.removeProperty('--bg-card')
      rootStyle.removeProperty('--bg-main')
      rootStyle.removeProperty('--bg-elevated')
    }

    // 3. Primary Accent & Dynamic Contrast Text
    const effectivePrimary = primary || (isDark ? '#2dd4bf' : '#854d0e')
    const contrastText = getContrastColor(effectivePrimary)
    rootStyle.setProperty('--primary-contrast', contrastText)

    if (primary) {
      rootStyle.setProperty('--primary', primary)
      rootStyle.setProperty('--primary-hover', primary)
      rootStyle.setProperty('--text-primary', primary)
      rootStyle.setProperty('--border-focus', primary)
      rootStyle.setProperty('--primary-glow', hexToRgba(primary, 0.22))
      rootStyle.setProperty('--primary-subtle', hexToRgba(primary, 0.10))
    } else {
      rootStyle.removeProperty('--primary')
      rootStyle.removeProperty('--primary-hover')
      rootStyle.removeProperty('--text-primary')
      rootStyle.removeProperty('--border-focus')
      rootStyle.removeProperty('--primary-glow')
      rootStyle.removeProperty('--primary-subtle')
    }

    // 4. Border / Divider
    if (border) {
      rootStyle.setProperty('--border-color', border)
      rootStyle.setProperty('--border-subtle', border)
    } else {
      rootStyle.removeProperty('--border-color')
      rootStyle.removeProperty('--border-subtle')
    }
  }

  function setTheme(newTheme) {
    theme.value = newTheme
    localStorage.setItem('jt_theme', newTheme)
    document.documentElement.className = newTheme
    applyCustomColors()
  }

  function toggleTheme() {
    setTheme(theme.value === 'midnight' ? 'daylight' : 'midnight')
  }

  function setCustomColor(themeName, key, colorHex) {
    const storageKey = `jt_custom_${themeName === 'midnight' ? 'dark' : 'light'}_${key}`
    if (themeName === 'midnight') {
      if (key === 'bg') customDarkBg.value = colorHex
      else if (key === 'surface') customDarkSurface.value = colorHex
      else if (key === 'primary') customDarkPrimary.value = colorHex
      else if (key === 'border') customDarkBorder.value = colorHex
    } else {
      if (key === 'bg') customLightBg.value = colorHex
      else if (key === 'surface') customLightSurface.value = colorHex
      else if (key === 'primary') customLightPrimary.value = colorHex
      else if (key === 'border') customLightBorder.value = colorHex
    }
    localStorage.setItem(storageKey, colorHex)
    applyCustomColors()
  }

  function resetCustomColor(themeName, key) {
    const storageKey = `jt_custom_${themeName === 'midnight' ? 'dark' : 'light'}_${key}`
    if (themeName === 'midnight') {
      if (key === 'bg') customDarkBg.value = ''
      else if (key === 'surface') customDarkSurface.value = ''
      else if (key === 'primary') customDarkPrimary.value = ''
      else if (key === 'border') customDarkBorder.value = ''
    } else {
      if (key === 'bg') customLightBg.value = ''
      else if (key === 'surface') customLightSurface.value = ''
      else if (key === 'primary') customLightPrimary.value = ''
      else if (key === 'border') customLightBorder.value = ''
    }
    localStorage.removeItem(storageKey)
    applyCustomColors()
  }

  function resetAllCustomColors(themeName) {
    ;['bg', 'surface', 'primary', 'border'].forEach((k) => resetCustomColor(themeName, k))
  }

  // Alias functions for backward compatibility
  function setCustomBg(themeName, colorHex) {
    setCustomColor(themeName, 'bg', colorHex)
  }

  function resetCustomBg(themeName) {
    resetCustomColor(themeName, 'bg')
  }

  function setViewMode(mode) {
    viewMode.value = mode
    localStorage.setItem('jt_view_mode', mode)
  }

  function openIngestModal() {
    isIngestModalOpen.value = true
  }

  function closeIngestModal() {
    isIngestModalOpen.value = false
  }

  function openDetail(id, tab = 'timeline') {
    activeDetailId.value = id
    detailActiveTab.value = tab
  }

  function closeDetail() {
    activeDetailId.value = null
  }

  // Background Intake Tasks Queue
  const intakeQueue = ref([])
  const isQueueDrawerOpen = ref(false)

  function addIntakeTask(task) {
    intakeQueue.value.unshift(task)
    isQueueDrawerOpen.value = true
  }

  function updateIntakeTask(id, patch) {
    const item = intakeQueue.value.find(t => t.id === id)
    if (item) {
      Object.assign(item, patch)
    }
  }

  function removeIntakeTask(id) {
    intakeQueue.value = intakeQueue.value.filter(t => t.id !== id)
    if (intakeQueue.value.length === 0) {
      isQueueDrawerOpen.value = false
    }
  }

  function clearCompletedIntakeTasks() {
    intakeQueue.value = intakeQueue.value.filter(t => t.status === 'running')
  }

  // Global Settings
  const enableEmbeddings = ref(true)
  const enableAutoCoverLetter = ref(false)
  const coverLetterMatchThreshold = ref(70)
  const coverLetterLength = ref('standard')

  function setEnableEmbeddings(val) {
    enableEmbeddings.value = val
  }

  // Currency Preference
  const defaultCurrency = ref(localStorage.getItem('jt_currency') || 'USD')
  const SUPPORTED_CURRENCIES = [
    { code: 'USD', symbol: '$', label: 'USD ($)' },
    { code: 'EUR', symbol: '€', label: 'EUR (€)' },
    { code: 'GBP', symbol: '£', label: 'GBP (£)' },
    { code: 'CAD', symbol: 'CAD $', label: 'CAD ($)' },
    { code: 'AUD', symbol: 'AUD $', label: 'AUD ($)' },
    { code: 'CHF', symbol: 'CHF', label: 'CHF' },
    { code: 'JPY', symbol: '¥', label: 'JPY (¥)' },
    { code: 'SGD', symbol: 'SGD $', label: 'SGD ($)' },
    { code: 'BRL', symbol: 'R$', label: 'BRL (R$)' },
    { code: 'INR', symbol: '₹', label: 'INR (₹)' },
  ]

  function setDefaultCurrency(curr) {
    defaultCurrency.value = curr
    localStorage.setItem('jt_currency', curr)
  }

  // Auto-Archiver Preferences
  const autoArchiveEnabled = ref(localStorage.getItem('jt_auto_archiver_enabled') !== 'false')
  const autoArchiveDays = ref(parseInt(localStorage.getItem('jt_auto_archiver_days') || '30', 10))

  function setAutoArchiveEnabled(val) {
    autoArchiveEnabled.value = val
    localStorage.setItem('jt_auto_archiver_enabled', val ? 'true' : 'false')
  }

  function setAutoArchiveDays(days) {
    autoArchiveDays.value = days
    localStorage.setItem('jt_auto_archiver_days', String(days))
  }


  // AI Health Monitoring State
  const aiStatus = ref('unconfigured') // 'healthy' | 'degraded' | 'offline' | 'unconfigured'
  const aiLatencyMs = ref(0)
  const aiActiveProviderName = ref('')
  const aiModelName = ref('')
  const aiErrorMessage = ref(null)
  const aiFallbackProviderName = ref(null)
  const aiProviderType = ref(null)
  const aiBaseUrl = ref(null)
  const aiProviderId = ref(null)
  const aiFallbackProviderId = ref(null)
  const isCheckingAIHealth = ref(false)
  const isRetryModalOpen = ref(false)

  let healthTimer = null
  let isMonitorInitialized = false

  async function checkAIHealth() {
    isCheckingAIHealth.value = true
    try {
      const res = await AIConfigAPI.checkHealth()
      const data = res.data || {}
      aiStatus.value = data.status || 'unconfigured'
      aiLatencyMs.value = data.latency_ms || 0
      aiActiveProviderName.value = data.provider_name || ''
      aiModelName.value = data.model_name || ''
      aiErrorMessage.value = data.error_message || null
      aiFallbackProviderName.value = data.fallback_provider_name || null
      aiProviderType.value = data.provider_type || null
      aiBaseUrl.value = data.base_url || null
      aiProviderId.value = data.provider_id || null
      aiFallbackProviderId.value = data.fallback_provider_id || null
    } catch (err) {
      aiStatus.value = 'offline'
      aiErrorMessage.value = err?.response?.data?.detail || err?.message || 'Connection failed'
    } finally {
      isCheckingAIHealth.value = false
    }
  }

  function openRetryModal() {
    isRetryModalOpen.value = true
  }

  function closeRetryModal() {
    isRetryModalOpen.value = false
  }

  function initAIHealthMonitor() {
    if (isMonitorInitialized) return
    isMonitorInitialized = true

    checkAIHealth()

    window.addEventListener('focus', () => {
      checkAIHealth()
    })

    function startTimer() {
      if (!healthTimer) {
        healthTimer = setInterval(() => {
          if (!document.hidden) {
            checkAIHealth()
          }
        }, 60000)
      }
    }

    function stopTimer() {
      if (healthTimer) {
        clearInterval(healthTimer)
        healthTimer = null
      }
    }

    startTimer()

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        stopTimer()
      } else {
        checkAIHealth()
        startTimer()
      }
    })
  }

  // Route Preservation State
  const lastNonSettingsRoute = ref(null)

  function setLastNonSettingsRoute(path) {
    if (path && typeof path === 'string' && !path.startsWith('/settings')) {
      lastNonSettingsRoute.value = path
    }
  }

  function clearLastNonSettingsRoute() {
    lastNonSettingsRoute.value = null
  }

  // Theme Palette Popover State
  const isThemePopoverOpen = ref(false)

  function toggleThemePopover() {
    isThemePopoverOpen.value = !isThemePopoverOpen.value
  }

  function openThemePopover() {
    isThemePopoverOpen.value = true
  }

  function closeThemePopover() {
    isThemePopoverOpen.value = false
  }

  // Initialize root class and custom theme colors
  document.documentElement.className = theme.value
  applyCustomColors()

  return {
    theme,
    customDarkBg,
    customDarkSurface,
    customDarkPrimary,
    customDarkBorder,
    customLightBg,
    customLightSurface,
    customLightPrimary,
    customLightBorder,
    setCustomColor,
    resetCustomColor,
    resetAllCustomColors,
    setCustomBg,
    resetCustomBg,
    viewMode,
    defaultCurrency,
    SUPPORTED_CURRENCIES,
    isIngestModalOpen,
    isJobIntakeModalOpen,
    isCommandPaletteOpen,
    isCoverLetterModalOpen,
    coverLetterAppId,
    openCoverLetterModal,
    closeCoverLetterModal,
    activeDetailId,
    detailActiveTab,
    intakeQueue,
    isQueueDrawerOpen,
    isThemePopoverOpen,
    toggleThemePopover,
    openThemePopover,
    closeThemePopover,
    toast,
    showToast,
    hideToast,
    setTheme,
    toggleTheme,
    setViewMode,
    setDefaultCurrency,
    openIngestModal,
    closeIngestModal,
    openJobIntakeModal,
    closeJobIntakeModal,
    openDetail,
    closeDetail,
    addIntakeTask,
    updateIntakeTask,
    removeIntakeTask,
    clearCompletedIntakeTasks,
    enableEmbeddings,
    setEnableEmbeddings,
    enableAutoCoverLetter,
    coverLetterMatchThreshold,
    coverLetterLength,
    autoArchiveEnabled,
    autoArchiveDays,
    setAutoArchiveEnabled,
    setAutoArchiveDays,
    lastNonSettingsRoute,
    setLastNonSettingsRoute,
    clearLastNonSettingsRoute,
    aiStatus,
    aiLatencyMs,
    aiActiveProviderName,
    aiModelName,
    aiErrorMessage,
    aiFallbackProviderName,
    aiProviderType,
    aiBaseUrl,
    aiProviderId,
    aiFallbackProviderId,
    isCheckingAIHealth,
    isRetryModalOpen,
    checkAIHealth,
    openRetryModal,
    closeRetryModal,
    initAIHealthMonitor,
  }
})
