import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ApplicationsAPI } from '../api/endpoints'
import { useUIStore } from './uiStore'

export const useApplicationsStore = defineStore('applications', () => {
  const uiStore = useUIStore()

  const applications = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref(null)
  const searchQuery = ref('')
  const selectedStatus = ref('')
  const actionRequiredOnly = ref(false)
  const minMatchScore = ref(null)
  const selectedWorkModel = ref('') // '' | 'Remote' | 'Hybrid' | 'On-site'
  const selectedApplication = ref(null)
  const loadingDetail = ref(false)

  const pipelineViewMode = ref('active') // 'active' | 'archive' | 'hired'

  function matchesWorkModel(app) {
    if (!selectedWorkModel.value) return true
    const target = selectedWorkModel.value.toLowerCase().replace(/[^a-z]/g, '')
    const current = (app.work_model || app.match_analysis_payload?.work_model || '').toLowerCase().replace(/[^a-z]/g, '')
    return current.includes(target) || target.includes(current)
  }

  // Full status list
  const STATUSES = [
    { key: 'ASSESSMENT', label: 'AI Assessment', color: 'assessment' },
    { key: 'APPLIED', label: 'Applied', color: 'applied' },
    { key: 'TECHNICAL_INTERVIEW', label: 'Interview', color: 'interview' },
    { key: 'OFFER', label: 'Offer', color: 'offer' },
    { key: 'REJECTED', label: 'Rejected', color: 'rejected' },
  ]

  // Active Pipeline Stages for the main Kanban Board
  const ACTIVE_STATUSES = [
    { key: 'APPLIED', label: 'Applied', color: 'applied' },
    { key: 'TECHNICAL_INTERVIEW', label: 'Interview', color: 'interview' },
    { key: 'OFFER', label: 'Offer', color: 'offer' },
  ]

  const TERMINAL_STATUSES = ['HIRED', 'ARCHIVED', 'WITHDRAWN', 'REJECTED']

  const activeApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || 'APPLIED').toUpperCase()
      if (TERMINAL_STATUSES.includes(status)) return false
      return matchesWorkModel(a)
    })
  })

  const archivedApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || '').toUpperCase()
      return ['ARCHIVED', 'WITHDRAWN', 'REJECTED'].includes(status) && matchesWorkModel(a)
    })
  })

  const hiredApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || '').toUpperCase()
      return status === 'HIRED' && matchesWorkModel(a)
    })
  })

  const kanbanColumns = computed(() => {
    const columns = {
      APPLIED: [],
      TECHNICAL_INTERVIEW: [],
      OFFER: [],
    }

    applications.value.forEach((app) => {
      // Filter by work model if active
      if (!matchesWorkModel(app)) return

      // Filter by min match score if active
      if (minMatchScore.value !== null && minMatchScore.value !== undefined && minMatchScore.value !== '') {
        const targetMin = Number(minMatchScore.value)
        if (targetMin > 0) {
          const score = app.match_score ?? app.latest_event?.raw_payload?.match_score ?? app.latest_event?.raw_payload?.fit_score ?? null
          if (score === null || Number(score) < targetMin) {
            return
          }
        }
      }

      let statusKey = app.status ? app.status.toUpperCase() : 'APPLIED'
      if (statusKey === 'ONLINE_ASSESSMENT' || statusKey === 'INTERVIEW') {
        statusKey = 'TECHNICAL_INTERVIEW'
      }

      // If app is in REJECTED or ASSESSMENT, it doesn't display on active 3-stage board
      if (columns[statusKey]) {
        columns[statusKey].push(app)
      } else if (statusKey === 'ASSESSMENT') {
        // In case any legacy assessment exists, group into Applied or leave for Assessments Studio
        columns.APPLIED.push(app)
      }
    })

    const nowTs = Date.now()

    function getAppInterviewTimestamp(app) {
      const stage = (app.latest_event?.raw_payload?.interview_stage || '').trim()
      if (stage === 'Task Completed / Awaiting Response') {
        return null
      }
      const raw =
        app.scheduled_interview_at ||
        app.latest_event?.raw_payload?.scheduled_at ||
        app.events?.find((e) => e.raw_payload?.scheduled_at)?.raw_payload?.scheduled_at
      if (!raw) return null
      const ts = new Date(raw).getTime()
      return isNaN(ts) ? null : ts
    }

    function getAppOfferDeadlineTimestamp(app) {
      const raw =
        app.nearest_due_date ||
        app.latest_event?.raw_payload?.decision_deadline ||
        app.events?.find((e) => e.raw_payload?.decision_deadline)?.raw_payload?.decision_deadline
      if (!raw) return null
      const ts = new Date(raw).getTime()
      return isNaN(ts) ? null : ts
    }

    function getAppActivityTimestamp(app) {
      const raw = app.last_activity_at || app.application_date || app.created_at
      if (!raw) return 0
      const ts = new Date(raw).getTime()
      return isNaN(ts) ? 0 : ts
    }

    // Sort APPLIED: newest activity first
    columns.APPLIED.sort((a, b) => getAppActivityTimestamp(b) - getAppActivityTimestamp(a))

    // Sort TECHNICAL_INTERVIEW: upcoming interviews first (ascending), then past, then unscheduled
    columns.TECHNICAL_INTERVIEW.sort((a, b) => {
      const tsA = getAppInterviewTimestamp(a)
      const tsB = getAppInterviewTimestamp(b)

      const isFutureA = tsA !== null && tsA >= nowTs
      const isFutureB = tsB !== null && tsB >= nowTs

      if (isFutureA && isFutureB) return tsA - tsB
      if (isFutureA) return -1
      if (isFutureB) return 1

      const isPastA = tsA !== null && tsA < nowTs
      const isPastB = tsB !== null && tsB < nowTs
      if (isPastA && isPastB) return tsB - tsA
      if (isPastA) return -1
      if (isPastB) return 1

      return getAppActivityTimestamp(b) - getAppActivityTimestamp(a)
    })

    // Sort OFFER: soonest decision deadline first (ascending), then past, then received date
    columns.OFFER.sort((a, b) => {
      const tsA = getAppOfferDeadlineTimestamp(a)
      const tsB = getAppOfferDeadlineTimestamp(b)

      const isFutureA = tsA !== null && tsA >= nowTs
      const isFutureB = tsB !== null && tsB >= nowTs

      if (isFutureA && isFutureB) return tsA - tsB
      if (isFutureA) return -1
      if (isFutureB) return 1

      const isPastA = tsA !== null && tsA < nowTs
      const isPastB = tsB !== null && tsB < nowTs
      if (isPastA && isPastB) return tsB - tsA
      if (isPastA) return -1
      if (isPastB) return 1

      return getAppActivityTimestamp(b) - getAppActivityTimestamp(a)
    })

    return columns
  })

  async function fetchApplications() {
    loading.value = true
    error.value = null
    try {
      const params = {
        limit: 200,
        offset: 0,
      }
      if (searchQuery.value) params.q = searchQuery.value
      if (selectedStatus.value) params.status = selectedStatus.value
      if (actionRequiredOnly.value) params.action_required = true

      const res = await ApplicationsAPI.list(params)
      applications.value = res.data.items || []
      total.value = res.data.total || 0
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchApplicationDetail(id) {
    loadingDetail.value = true
    try {
      const res = await ApplicationsAPI.get(id)
      selectedApplication.value = res.data
      const idx = applications.value.findIndex((a) => a.id === id)
      if (idx !== -1) {
        applications.value[idx].has_action_required = res.data.has_action_required
        applications.value[idx].nearest_due_date = res.data.nearest_due_date
        applications.value[idx].scheduled_interview_at = res.data.scheduled_interview_at
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loadingDetail.value = false
    }
  }

  // Optimistic updateStatus
  async function updateStatus(applicationId, newStatus) {
    const appsSnapshot = JSON.parse(JSON.stringify(applications.value))
    const selectedSnapshot = selectedApplication.value ? JSON.parse(JSON.stringify(selectedApplication.value)) : null

    // Optimistic local update
    const target = applications.value.find((a) => a.id === applicationId)
    if (target) {
      target.status = newStatus
    }
    if (selectedApplication.value && selectedApplication.value.id === applicationId) {
      selectedApplication.value.status = newStatus
    }

    try {
      await ApplicationsAPI.update(applicationId, { status: newStatus })
    } catch (err) {
      // Rollback
      applications.value = appsSnapshot
      selectedApplication.value = selectedSnapshot
      error.value = err.message
      uiStore.showToast(err.message || 'Failed to update application status', 'error')
      throw err
    }
  }

  // Optimistic transitionApplication
  async function transitionApplication(applicationId, transitionData) {
    const appsSnapshot = JSON.parse(JSON.stringify(applications.value))
    const selectedSnapshot = selectedApplication.value ? JSON.parse(JSON.stringify(selectedApplication.value)) : null

    // Optimistic local update
    const idx = applications.value.findIndex((a) => a.id === applicationId)
    if (idx !== -1) {
      applications.value[idx] = { ...applications.value[idx], ...transitionData }
    }
    if (selectedApplication.value && selectedApplication.value.id === applicationId) {
      selectedApplication.value = { ...selectedApplication.value, ...transitionData }
    }

    try {
      const res = await ApplicationsAPI.transition(applicationId, transitionData)
      const updated = res.data
      if (idx !== -1) {
        applications.value[idx] = { ...applications.value[idx], ...updated }
      }
      if (selectedApplication.value && selectedApplication.value.id === applicationId) {
        selectedApplication.value = { ...selectedApplication.value, ...updated }
      }
      return updated
    } catch (err) {
      // Rollback
      applications.value = appsSnapshot
      selectedApplication.value = selectedSnapshot
      error.value = err.message
      uiStore.showToast(err.message || 'Failed to transition application', 'error')
      throw err
    }
  }

  async function quickReject(applicationId, rejectionReason = 'Quick rejection') {
    return transitionApplication(applicationId, {
      status: 'REJECTED',
      rejection_date: new Date().toISOString(),
      rejection_reason: rejectionReason,
      notes: 'Moved to archive via quick reject',
    })
  }

  async function quickWithdraw(applicationId, reason = 'Withdrawn by candidate') {
    return transitionApplication(applicationId, {
      status: 'WITHDRAWN',
      notes: reason,
    })
  }

  // Optimistic bulkTransition
  async function bulkTransition(targetStatus, fromStatuses, excludeIds = [], notes = null) {
    const appsSnapshot = JSON.parse(JSON.stringify(applications.value))
    const excludeSet = new Set(excludeIds)
    const fromSet = new Set(fromStatuses)

    // Optimistically update eligible applications
    applications.value.forEach((a) => {
      if (fromSet.has(a.status) && !excludeSet.has(a.id)) {
        a.status = targetStatus
      }
    })

    try {
      const res = await ApplicationsAPI.bulkTransition({
        target_status: targetStatus,
        from_statuses: fromStatuses,
        exclude_ids: excludeIds,
        notes,
      })
      const updatedIds = new Set(res.data.updated_ids || [])
      applications.value.forEach((a) => {
        if (updatedIds.has(a.id)) {
          a.status = targetStatus
        }
      })
      return res.data
    } catch (err) {
      // Rollback
      applications.value = appsSnapshot
      error.value = err.message
      uiStore.showToast(err.message || 'Failed bulk application transition', 'error')
      throw err
    }
  }

  async function restoreToActive(applicationId, targetStatus = 'APPLIED') {
    return transitionApplication(applicationId, {
      status: targetStatus,
      notes: 'Restored to active pipeline',
    })
  }

  // Optimistic deleteApplication
  async function deleteApplication(applicationId) {
    const appsSnapshot = JSON.parse(JSON.stringify(applications.value))
    const totalSnapshot = total.value
    const selectedSnapshot = selectedApplication.value ? JSON.parse(JSON.stringify(selectedApplication.value)) : null

    // Optimistically remove application
    applications.value = applications.value.filter((a) => a.id !== applicationId)
    total.value = Math.max(0, total.value - 1)
    if (selectedApplication.value && selectedApplication.value.id === applicationId) {
      selectedApplication.value = null
    }

    try {
      await ApplicationsAPI.delete(applicationId)
      uiStore.showToast('Application deleted', 'info')
    } catch (err) {
      // Rollback
      applications.value = appsSnapshot
      total.value = totalSnapshot
      selectedApplication.value = selectedSnapshot
      error.value = err.message
      uiStore.showToast(err.message || 'Failed to delete application', 'error')
      throw err
    }
  }

  return {
    applications,
    total,
    loading,
    error,
    searchQuery,
    selectedStatus,
    actionRequiredOnly,
    minMatchScore,
    selectedWorkModel,
    selectedApplication,
    loadingDetail,
    pipelineViewMode,
    STATUSES,
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    activeApplications,
    archivedApplications,
    hiredApplications,
    kanbanColumns,
    fetchApplications,
    fetchApplicationDetail,
    updateStatus,
    transitionApplication,
    quickReject,
    quickWithdraw,
    bulkTransition,
    restoreToActive,
    deleteApplication,
  }
})
