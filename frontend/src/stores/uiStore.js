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

  // Initialize root class
  document.documentElement.className = theme.value

  return {
    theme,
    viewMode,
    isIngestModalOpen,
    isCommandPaletteOpen,
    activeDetailId,
    toast,
    showToast,
    hideToast,
    toggleTheme,
    setViewMode,
    openIngestModal,
    closeIngestModal,
    openDetail,
    closeDetail,
  }
})
