import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ApplicationsAPI } from '../api/endpoints'

export const useApplicationsStore = defineStore('applications', () => {
  const applications = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref(null)
  const searchQuery = ref('')
  const selectedStatus = ref('')
  const actionRequiredOnly = ref(false)
  const minMatchScore = ref(null)
  const selectedApplication = ref(null)
  const loadingDetail = ref(false)

  const pipelineViewMode = ref('active') // 'active' | 'archive'

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

  const activeApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || 'APPLIED').toUpperCase()
      return status !== 'REJECTED'
    })
  })

  const archivedApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || '').toUpperCase()
      return status === 'REJECTED'
    })
  })

  const kanbanColumns = computed(() => {
    const columns = {
      APPLIED: [],
      TECHNICAL_INTERVIEW: [],
      OFFER: [],
    }

    applications.value.forEach((app) => {
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
    } catch (err) {
      error.value = err.message
    } finally {
      loadingDetail.value = false
    }
  }

  async function updateStatus(applicationId, newStatus) {
    try {
      await ApplicationsAPI.update(applicationId, { status: newStatus })
      // Update local array
      const target = applications.value.find((a) => a.id === applicationId)
      if (target) {
        target.status = newStatus
      }
      if (selectedApplication.value && selectedApplication.value.id === applicationId) {
        selectedApplication.value.status = newStatus
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function transitionApplication(applicationId, transitionData) {
    try {
      const res = await ApplicationsAPI.transition(applicationId, transitionData)
      const updated = res.data
      const idx = applications.value.findIndex((a) => a.id === applicationId)
      if (idx !== -1) {
        applications.value[idx] = { ...applications.value[idx], ...updated }
      }
      if (selectedApplication.value && selectedApplication.value.id === applicationId) {
        selectedApplication.value = { ...selectedApplication.value, ...updated }
      }
      return updated
    } catch (err) {
      error.value = err.message
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

  async function restoreToActive(applicationId, targetStatus = 'APPLIED') {
    return transitionApplication(applicationId, {
      status: targetStatus,
      notes: 'Restored to active pipeline',
    })
  }

  async function deleteApplication(applicationId) {
    try {
      await ApplicationsAPI.delete(applicationId)
      applications.value = applications.value.filter((a) => a.id !== applicationId)
      total.value = Math.max(0, total.value - 1)
      if (selectedApplication.value && selectedApplication.value.id === applicationId) {
        selectedApplication.value = null
      }
    } catch (err) {
      error.value = err.message
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
    selectedApplication,
    loadingDetail,
    pipelineViewMode,
    STATUSES,
    ACTIVE_STATUSES,
    activeApplications,
    archivedApplications,
    kanbanColumns,
    fetchApplications,
    fetchApplicationDetail,
    updateStatus,
    transitionApplication,
    quickReject,
    restoreToActive,
    deleteApplication,
  }
})
