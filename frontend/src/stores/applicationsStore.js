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
    const timestampCache = new WeakMap()

    function getAppInterviewTimestamp(app) {
      if (!app) return null
      const cached = timestampCache.get(app)?.interview
      if (cached !== undefined) return cached
      let val = null
      const stage = (app.latest_event?.raw_payload?.interview_stage || '').trim()
      if (stage !== 'Task Completed / Awaiting Response') {
        const raw =
          app.scheduled_interview_at ||
          app.latest_event?.raw_payload?.scheduled_at ||
          app.events?.find((e) => e.raw_payload?.scheduled_at)?.raw_payload?.scheduled_at
        if (raw) {
          const ts = new Date(raw).getTime()
          val = isNaN(ts) ? null : ts
        }
      }
      const entry = timestampCache.get(app) || {}
      entry.interview = val
      timestampCache.set(app, entry)
      return val
    }

    function getAppOfferDeadlineTimestamp(app) {
      if (!app) return null
      const cached = timestampCache.get(app)?.offer
      if (cached !== undefined) return cached
      let val = null
      const raw =
        app.nearest_due_date ||
        app.latest_event?.raw_payload?.decision_deadline ||
        app.events?.find((e) => e.raw_payload?.decision_deadline)?.raw_payload?.decision_deadline
      if (raw) {
        const ts = new Date(raw).getTime()
        val = isNaN(ts) ? null : ts
      }
      const entry = timestampCache.get(app) || {}
      entry.offer = val
      timestampCache.set(app, entry)
      return val
    }

    function getAppActivityTimestamp(app) {
      if (!app) return 0
      const cached = timestampCache.get(app)?.activity
      if (cached !== undefined) return cached
      let val = 0
      const raw = app.last_activity_at || app.application_date || app.created_at
      if (raw) {
        const ts = new Date(raw).getTime()
        val = isNaN(ts) ? 0 : ts
      }
      const entry = timestampCache.get(app) || {}
      entry.activity = val
      timestampCache.set(app, entry)
      return val
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

  function toSummary(app) {
    if (!app) return app
    const {
      events,
      action_items,
      interview_guide_html,
      ...summary
    } = app
    return summary
  }

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
      const rawItems = res.data.items || []
      applications.value = rawItems.map(toSummary)
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
        applications.value[idx] = toSummary({ ...applications.value[idx], ...updated })
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

  async function quickWithdraw(applicationId, reason = 'Withdrawn by candidate') {
    return transitionApplication(applicationId, {
      status: 'WITHDRAWN',
      notes: reason,
    })
  }

  async function bulkTransition(targetStatus, fromStatuses, excludeIds = [], notes = null) {
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
      error.value = err.message
      throw err
    }
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
