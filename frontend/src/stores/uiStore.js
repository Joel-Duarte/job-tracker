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

  // Initialize root class
  document.documentElement.className = theme.value

  return {
    theme,
    viewMode,
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

