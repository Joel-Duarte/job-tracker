import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { IntakeAPI } from '../api/endpoints'
import { useUIStore } from './uiStore'

export const useQueueStore = defineStore('queue', () => {
  const uiStore = useUIStore()

  const tasks = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Reactive Computed Getters
  const activeTasks = computed(() =>
    tasks.value.filter((t) => ['QUEUED', 'PROCESSING'].includes(t.status))
  )

  const failedTasks = computed(() =>
    tasks.value.filter((t) => ['FAILED', 'CANCELLED'].includes(t.status))
  )

  const completedTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'COMPLETED')
  )

  const runningCount = computed(() =>
    tasks.value.filter((t) => t.status === 'PROCESSING').length
  )

  const pendingCount = computed(() =>
    tasks.value.filter((t) => t.status === 'QUEUED').length
  )

  const activeCount = computed(() => activeTasks.value.length)
  const failedCount = computed(() => failedTasks.value.length)
  const completedCount = computed(() => completedTasks.value.length)
  const notificationCount = computed(() => activeCount.value + failedCount.value)

  const readyAssessmentsCount = computed(() => {
    let passedSet = new Set()
    try {
      passedSet = new Set(JSON.parse(localStorage.getItem('job_tracker_passed_assessments') || '[]'))
    } catch {
      // ignore JSON parse error
    }
    return tasks.value.filter(
      (t) =>
        (t.task_type === 'JOB_ASSESSMENT' || !t.task_type) &&
        t.status === 'COMPLETED' &&
        !passedSet.has(String(t.id))
    ).length
  })

  // Fetch Queue Evaluations from API
  async function fetchTasks(silent = false) {
    if (!silent) loading.value = true
    error.value = null
    try {
      const res = await IntakeAPI.getEvaluations(100)
      if (Array.isArray(res.data)) {
        tasks.value = res.data
      }
    } catch (err) {
      error.value = err.message
      if (!silent) {
        uiStore.showToast(err.message || 'Failed to fetch queue evaluations', 'error')
      }
    } finally {
      if (!silent) loading.value = false
    }
  }

  // 1. Enqueue Assessment Optimistically
  async function enqueueAssessment(payload) {
    const tempId = `temp-${Date.now()}`
    const tempTask = {
      id: tempId,
      job_url: payload.url || null,
      raw_text: payload.text || null,
      title_hint: payload.url || (payload.text ? payload.text.slice(0, 40) + '...' : 'Job Assessment'),
      status: 'QUEUED',
      stage: 'QUEUED',
      task_type: 'JOB_ASSESSMENT',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    // Optimistically add temp task to state
    tasks.value = [tempTask, ...tasks.value]

    try {
      const res = await IntakeAPI.enqueueAssessment(payload)
      const createdTask = res.data
      // Replace temp item with server response data if returned
      const idx = tasks.value.findIndex((t) => t.id === tempId)
      if (idx !== -1) {
        if (createdTask && createdTask.id) {
          tasks.value[idx] = createdTask
        } else {
          // If response didn't return full object, keep temp task or fetch queue
          await fetchTasks(true)
        }
      }
      uiStore.showToast('Job queued for AI evaluation!', 'success')
      return createdTask
    } catch (err) {
      // Rollback optimistic addition
      tasks.value = tasks.value.filter((t) => t.id !== tempId)
      uiStore.showToast(err.message || 'Failed to enqueue assessment', 'error')
      throw err
    }
  }

  // 2. Retry Task Optimistically
  async function retryTask(taskId) {
    const previousSnapshot = [...tasks.value]

    // Optimistically update status to QUEUED
    const idx = tasks.value.findIndex((t) => t.id === taskId)
    if (idx !== -1) {
      tasks.value[idx] = {
        ...tasks.value[idx],
        status: 'QUEUED',
        stage: 'QUEUED',
        error_message: null,
      }
    }

    try {
      const res = await IntakeAPI.retryEvaluation(taskId)
      uiStore.showToast(`Task #${taskId} re-queued for execution!`, 'success')
      if (res.data) {
        const updatedIdx = tasks.value.findIndex((t) => t.id === taskId)
        if (updatedIdx !== -1) {
          tasks.value[updatedIdx] = { ...tasks.value[updatedIdx], ...res.data }
        }
      }
      return res.data
    } catch (err) {
      // Rollback
      tasks.value = previousSnapshot
      uiStore.showToast(err.message || `Failed to retry task #${taskId}`, 'error')
      throw err
    }
  }

  // 3. Delete Task Optimistically
  async function deleteTask(taskId) {
    const previousSnapshot = [...tasks.value]

    // Optimistically filter out task
    tasks.value = tasks.value.filter((t) => t.id !== taskId)

    try {
      await IntakeAPI.deleteEvaluation(taskId)
      uiStore.showToast(`Task #${taskId} dismissed`, 'info')
    } catch (err) {
      // Rollback
      tasks.value = previousSnapshot
      uiStore.showToast(err.message || `Failed to delete task #${taskId}`, 'error')
      throw err
    }
  }

  // 4. Bulk Retry Tasks Optimistically
  async function bulkRetryTasks(taskIds) {
    if (!taskIds || taskIds.length === 0) return
    const previousSnapshot = [...tasks.value]
    const idSet = new Set(taskIds)

    // Optimistically update matching tasks
    tasks.value = tasks.value.map((t) => {
      if (idSet.has(t.id)) {
        return {
          ...t,
          status: 'QUEUED',
          stage: 'QUEUED',
          error_message: null,
        }
      }
      return t
    })

    try {
      const res = await IntakeAPI.bulkRetryEvaluations(taskIds)
      const affected = res.data?.affected_count ?? taskIds.length
      const skipped = res.data?.skipped_count ?? 0
      uiStore.showToast(`Bulk retry completed: ${affected} retried, ${skipped} skipped`, 'success')
      return res.data
    } catch (err) {
      // Rollback
      tasks.value = previousSnapshot
      uiStore.showToast(err.message || 'Failed to bulk retry tasks', 'error')
      throw err
    }
  }

  // 5. Bulk Delete Tasks Optimistically
  async function bulkDeleteTasks(taskIds) {
    if (!taskIds || taskIds.length === 0) return
    const previousSnapshot = [...tasks.value]
    const idSet = new Set(taskIds)

    // Optimistically remove tasks
    tasks.value = tasks.value.filter((t) => !idSet.has(t.id))

    try {
      const res = await IntakeAPI.bulkDeleteEvaluations(taskIds)
      const deleted = res.data?.deleted_count ?? taskIds.length
      const skipped = res.data?.skipped_count ?? 0
      uiStore.showToast(`Bulk delete completed: ${deleted} deleted, ${skipped} skipped`, 'info')
      return res.data
    } catch (err) {
      // Rollback
      tasks.value = previousSnapshot
      uiStore.showToast(err.message || 'Failed to bulk delete tasks', 'error')
      throw err
    }
  }

  // 6. Clear Completed Tasks Optimistically
  async function clearCompletedTasks() {
    const previousSnapshot = [...tasks.value]

    // Optimistically remove completed & failed tasks
    tasks.value = tasks.value.filter(
      (t) => !['COMPLETED', 'FAILED', 'CANCELLED'].includes(t.status)
    )

    try {
      const res = await IntakeAPI.clearCompletedEvaluations()
      uiStore.showToast(`Cleared ${res.data.cleared_count || 0} completed/failed tasks`, 'success')
      return res.data
    } catch (err) {
      // Rollback
      tasks.value = previousSnapshot
      uiStore.showToast(err.message || 'Failed to clear completed tasks', 'error')
      throw err
    }
  }

  // 7. Confirm Assessment Optimistically
  async function confirmAssessment(data, taskId = null) {
    const previousSnapshot = [...tasks.value]

    if (taskId) {
      // Mark or filter out task from queue if needed
      tasks.value = tasks.value.filter((t) => t.id !== taskId)
    }

    try {
      const res = await IntakeAPI.confirmAssessment(data)
      uiStore.showToast('Assessment confirmed and saved to pipeline!', 'success')
      return res.data
    } catch (err) {
      tasks.value = previousSnapshot
      uiStore.showToast(err.message || 'Failed to confirm assessment', 'error')
      throw err
    }
  }

  return {
    tasks,
    loading,
    error,
    activeTasks,
    failedTasks,
    completedTasks,
    runningCount,
    pendingCount,
    activeCount,
    failedCount,
    completedCount,
    notificationCount,
    readyAssessmentsCount,
    fetchTasks,
    enqueueAssessment,
    retryTask,
    deleteTask,
    bulkRetryTasks,
    bulkDeleteTasks,
    clearCompletedTasks,
    confirmAssessment,
  }
})
