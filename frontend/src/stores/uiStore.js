import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const theme = ref(localStorage.getItem('jt_theme') || 'dark')
  const viewMode = ref(localStorage.getItem('jt_view_mode') || 'kanban') // 'kanban' | 'table'
  const isIngestModalOpen = ref(false)
  const isCommandPaletteOpen = ref(false)
  const activeDetailId = ref(null)

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

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem('jt_theme', theme.value)
    document.documentElement.className = theme.value
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

  function openDetail(id) {
    activeDetailId.value = id
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

  // Initialize root class
  document.documentElement.className = theme.value

  return {
    theme,
    viewMode,
    defaultCurrency,
    SUPPORTED_CURRENCIES,
    isIngestModalOpen,
    isCommandPaletteOpen,
    activeDetailId,
    intakeQueue,
    isQueueDrawerOpen,
    toast,
    showToast,
    hideToast,
    toggleTheme,
    setViewMode,
    setDefaultCurrency,
    openIngestModal,
    closeIngestModal,
    openDetail,
    closeDetail,
    addIntakeTask,
    updateIntakeTask,
    removeIntakeTask,
    clearCompletedIntakeTasks,
  }
})

