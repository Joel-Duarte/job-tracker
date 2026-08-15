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
  const selectedApplication = ref(null)
  const loadingDetail = ref(false)

  // Status mapping - Assessment is before Applied as requested
  const STATUSES = [
    { key: 'ASSESSMENT', label: 'AI Assessment', color: 'assessment' },
    { key: 'APPLIED', label: 'Applied', color: 'applied' },
    { key: 'TECHNICAL_INTERVIEW', label: 'Interview', color: 'interview' },
    { key: 'OFFER', label: 'Offer', color: 'offer' },
    { key: 'REJECTED', label: 'Rejected', color: 'rejected' },
  ]

  const kanbanColumns = computed(() => {
    const columns = {
      ASSESSMENT: [],
      APPLIED: [],
      TECHNICAL_INTERVIEW: [],
      OFFER: [],
      REJECTED: [],
    }

    applications.value.forEach((app) => {
      let statusKey = app.status ? app.status.toUpperCase() : 'APPLIED'
      if (statusKey === 'ONLINE_ASSESSMENT' || statusKey === 'INTERVIEW') {
        statusKey = 'TECHNICAL_INTERVIEW'
      }

      if (columns[statusKey]) {
        columns[statusKey].push(app)
      } else {
        // Fallback to applied
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
        limit: 100,
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
    selectedApplication,
    loadingDetail,
    STATUSES,
    kanbanColumns,
    fetchApplications,
    fetchApplicationDetail,
    updateStatus,
    transitionApplication,
    deleteApplication,
  }
})
