import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ApplicationsAPI } from '../api/endpoints'
import { useUIStore } from './uiStore'
import { getDemoDb } from '../demo/demoStorage'

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
  const selectedDateRange = ref('all') // 'all' | '7d' | '30d' | '90d' | 'custom'
  const customDateStart = ref('')
  const customDateEnd = ref('')
  const selectedApplication = ref(null)
  const loadingDetail = ref(false)

  const pipelineViewMode = ref('active') // 'active' | 'archive' | 'hired'
  const lastFetchedAt = ref(null)
  const isStale = ref(false)
  const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes cache TTL

  function invalidateCache() {
    isStale.value = true
  }

  const KANBAN_SORT_OPTIONS = [
    { key: 'smart', label: 'Smart Adaptive', shortLabel: 'Smart' },
    { key: 'latest_activity', label: 'Latest Activity', shortLabel: 'Latest' },
    { key: 'next_scheduled', label: 'Next Scheduled', shortLabel: 'Scheduled' },
    { key: 'match_score', label: 'Fit Score', shortLabel: 'Fit Score' },
  ]

  const kanbanSortMode = ref(localStorage.getItem('jobtracker_kanban_sort_mode') || 'smart')

  function setKanbanSortMode(mode) {
    kanbanSortMode.value = mode
    try {
      localStorage.setItem('jobtracker_kanban_sort_mode', mode)
    } catch {
      // ignore storage error
    }
  }

  function getAppActivityDate(app) {
    if (!app) return null
    return (
      app.latest_event?.email_received_at ||
      app.latest_event?.created_at ||
      app.events?.[0]?.email_received_at ||
      app.events?.[0]?.created_at ||
      app.last_activity_at ||
      app.application_date ||
      app.applied_at ||
      app.created_at ||
      app.updated_at ||
      null
    )
  }

  function matchesDateRange(app) {
    if (!selectedDateRange.value || selectedDateRange.value === 'all') return true

    const appDateRaw = getAppActivityDate(app)
    if (!appDateRaw) return true

    const appTime = new Date(appDateRaw).getTime()
    if (isNaN(appTime)) return true

    const now = Date.now()
    if (selectedDateRange.value === '7d') {
      return appTime >= now - 7 * 24 * 60 * 60 * 1000
    }
    if (selectedDateRange.value === '30d') {
      return appTime >= now - 30 * 24 * 60 * 60 * 1000
    }
    if (selectedDateRange.value === '90d') {
      return appTime >= now - 90 * 24 * 60 * 60 * 1000
    }
    if (selectedDateRange.value === 'custom') {
      let matchesStart = true
      let matchesEnd = true

      if (customDateStart.value) {
        const startTs = new Date(customDateStart.value).setHours(0, 0, 0, 0)
        matchesStart = appTime >= startTs
      }
      if (customDateEnd.value) {
        const endTs = new Date(customDateEnd.value).setHours(23, 59, 59, 999)
        matchesEnd = appTime <= endTs
      }
      return matchesStart && matchesEnd
    }

    return true
  }

  function matchesWorkModel(app) {
    if (!selectedWorkModel.value) return true
    const target = selectedWorkModel.value.toLowerCase().replace(/[^a-z]/g, '')
    const current = (app.work_model || app.match_analysis_payload?.work_model || '').toLowerCase().replace(/[^a-z]/g, '')
    return current.includes(target) || target.includes(current)
  }

  function matchesSearch(app) {
    if (!searchQuery.value) return true
    const q = searchQuery.value.toLowerCase().trim()
    if (!q) return true
    const company = (app.company?.name || '').toLowerCase()
    const position = (app.position || '').toLowerCase()
    const location = (app.location || '').toLowerCase()
    const workModel = (app.work_model || '').toLowerCase()
    const salaryMin = app.salary_min ? String(app.salary_min) : ''
    const salaryMax = app.salary_max ? String(app.salary_max) : ''
    return (
      company.includes(q) ||
      position.includes(q) ||
      location.includes(q) ||
      workModel.includes(q) ||
      salaryMin.includes(q) ||
      salaryMax.includes(q)
    )
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

  function appNeedsAction(app) {
    if (app.has_action_required) return true
    try {
      const db = getDemoDb()
      return (db.action_items || []).some(
        (item) => String(item.application_id) === String(app.id) && item.status === 'PENDING'
      )
    } catch {
      return false
    }
  }

  const TERMINAL_STATUSES = ['HIRED', 'ARCHIVED', 'WITHDRAWN', 'REJECTED']
  const PENDING_ASSESSMENT_STATUSES = [
    'ASSESSMENT',
    'QUEUED',
    'PROCESSING',
    'FETCHING',
    'EXTRACTING',
    'MATCHING',
    'ASSESSING',
    'SAVING',
    'FAILED',
    'CANCELLED',
  ]

  const activeApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || '').toUpperCase()
      if (!status || TERMINAL_STATUSES.includes(status) || PENDING_ASSESSMENT_STATUSES.includes(status)) {
        return false
      }
      if (actionRequiredOnly.value) {
        if (!appNeedsAction(a)) return false
      }
      return matchesWorkModel(a) && matchesSearch(a) && matchesDateRange(a)
    })
  })

  const archivedApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || '').toUpperCase()
      return (
        ['ARCHIVED', 'WITHDRAWN', 'REJECTED'].includes(status) &&
        matchesWorkModel(a) &&
        matchesSearch(a) &&
        matchesDateRange(a)
      )
    })
  })

  const hiredApplications = computed(() => {
    return applications.value.filter((a) => {
      const status = (a.status || '').toUpperCase()
      return status === 'HIRED' && matchesWorkModel(a) && matchesSearch(a) && matchesDateRange(a)
    })
  })

  const kanbanColumns = computed(() => {
    const columns = {
      APPLIED: [],
      TECHNICAL_INTERVIEW: [],
      OFFER: [],
    }

    applications.value.forEach((app) => {
      // Filter by search query if active
      if (!matchesSearch(app)) return

      // Filter by work model if active
      if (!matchesWorkModel(app)) return

      // Filter by date range if active
      if (!matchesDateRange(app)) return

      // Filter by action required if active
      if (actionRequiredOnly.value && !appNeedsAction(app)) return

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

      const rawStatus = (app.status || '').toUpperCase()
      let statusKey = ''
      if (['APPLIED', 'RECRUITER_CONTACT', 'IN_PROGRESS', 'PENDING'].includes(rawStatus)) {
        statusKey = 'APPLIED'
      } else if ([
        'PHONE_SCREEN',
        'ONLINE_ASSESSMENT',
        'TECHNICAL_INTERVIEW',
        'BEHAVIORAL_INTERVIEW',
        'ONSITE_INTERVIEW',
        'FINAL_INTERVIEW',
        'INTERVIEW',
        'SCREENING',
      ].includes(rawStatus)) {
        statusKey = 'TECHNICAL_INTERVIEW'
      } else if (rawStatus === 'OFFER') {
        statusKey = 'OFFER'
      }

      // Strictly include only active pipeline stages (APPLIED, TECHNICAL_INTERVIEW, OFFER)
      if (statusKey && columns[statusKey]) {
        columns[statusKey].push(app)
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

    function getAppScheduledOrDeadlineTimestamp(app) {
      return getAppInterviewTimestamp(app) ?? getAppOfferDeadlineTimestamp(app)
    }

    function getAppActivityTimestamp(app) {
      const raw = getAppActivityDate(app)
      if (!raw) return 0
      const ts = new Date(raw).getTime()
      return isNaN(ts) ? 0 : ts
    }

    function getAppScore(app) {
      const score =
        app.match_score ??
        app.match_analysis_payload?.ai_fit_score ??
        app.match_analysis_payload?.fit_score ??
        app.match_analysis_payload?.match_score ??
        app.match_analysis_payload?.keyword_overlap_score ??
        app.latest_event?.raw_payload?.match_score ??
        app.latest_event?.raw_payload?.fit_score ??
        app.latest_event?.raw_payload?.overall_fit_score ??
        -1
      const num = Number(score)
      return isNaN(num) ? -1 : num
    }

    function sortByNextScheduled(list) {
      return list.sort((a, b) => {
        const tsA = getAppScheduledOrDeadlineTimestamp(a)
        const tsB = getAppScheduledOrDeadlineTimestamp(b)

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
    }

    const mode = kanbanSortMode.value || 'smart'

    if (mode === 'latest_activity') {
      columns.APPLIED.sort((a, b) => getAppActivityTimestamp(b) - getAppActivityTimestamp(a))
      columns.TECHNICAL_INTERVIEW.sort((a, b) => getAppActivityTimestamp(b) - getAppActivityTimestamp(a))
      columns.OFFER.sort((a, b) => getAppActivityTimestamp(b) - getAppActivityTimestamp(a))
    } else if (mode === 'next_scheduled') {
      sortByNextScheduled(columns.APPLIED)
      sortByNextScheduled(columns.TECHNICAL_INTERVIEW)
      sortByNextScheduled(columns.OFFER)
    } else if (mode === 'match_score') {
      const scoreSorter = (a, b) => {
        const diff = getAppScore(b) - getAppScore(a)
        if (diff !== 0) return diff
        return getAppActivityTimestamp(b) - getAppActivityTimestamp(a)
      }
      columns.APPLIED.sort(scoreSorter)
      columns.TECHNICAL_INTERVIEW.sort(scoreSorter)
      columns.OFFER.sort(scoreSorter)
    } else {
      // Default: 'smart' (stage-adaptive)
      // Sort APPLIED by last activity (most recent first)
      columns.APPLIED.sort((a, b) => getAppActivityTimestamp(b) - getAppActivityTimestamp(a))

      // Sort TECHNICAL_INTERVIEW chronologically by upcoming interview date
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

      // Sort OFFER by nearest decision deadline
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
    }

    return columns
  })

  const lastKnownTotalApps = ref(null)
  const lastKnownLatestActivityAt = ref(null)

  async function checkAndSyncWithBadges(badgeData) {
    if (!badgeData) return

    const totalApps = badgeData.total_applications_count ?? 0
    const latestActivity = badgeData.latest_activity_at ?? null

    const hasAppsCountChanged =
      lastKnownTotalApps.value !== null && lastKnownTotalApps.value !== totalApps
    const hasActivityChanged =
      lastKnownLatestActivityAt.value !== null &&
      lastKnownLatestActivityAt.value !== latestActivity

    lastKnownTotalApps.value = totalApps
    lastKnownLatestActivityAt.value = latestActivity

    if (hasAppsCountChanged || hasActivityChanged) {
      isStale.value = true
      // If we already have applications loaded in memory, silently refetch fresh data
      if (applications.value.length > 0) {
        await fetchApplications(true)
      }
      // If an application drawer is currently open, refresh its detail
      if (selectedApplication.value?.id) {
        await fetchApplicationDetail(selectedApplication.value.id)
      }
    }
  }

  async function fetchApplications(force = false) {
    const isFresh =
      !force &&
      !isStale.value &&
      lastFetchedAt.value !== null &&
      applications.value.length > 0 &&
      Date.now() - lastFetchedAt.value < CACHE_TTL_MS

    if (isFresh) {
      return
    }

    loading.value = applications.value.length === 0
    error.value = null
    try {
      const params = {
        limit: 1000,
        offset: 0,
      }
      const res = await ApplicationsAPI.list(params)
      applications.value = res.data.items || []
      total.value = res.data.total || (res.data.items || []).length
      lastFetchedAt.value = Date.now()
      isStale.value = false
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
      rejection_date: new Date().toISOString().substring(0, 10),
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
      uiStore.showToast(err.message || 'Failed to delete application', 'error')
      throw err
    }
  }

  // Update application fields (e.g. position, company_name)
  async function updateApplication(applicationId, payload) {
    try {
      const res = await ApplicationsAPI.update(applicationId, payload)
      selectedApplication.value = res.data
      const idx = applications.value.findIndex((a) => String(a.id) === String(applicationId))
      if (idx !== -1) {
        applications.value[idx] = {
          ...applications.value[idx],
          ...res.data,
        }
      }
      return res.data
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
    selectedDateRange,
    customDateStart,
    customDateEnd,
    selectedApplication,
    loadingDetail,
    pipelineViewMode,
    STATUSES,
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    PENDING_ASSESSMENT_STATUSES,
    activeApplications,
    archivedApplications,
    hiredApplications,
    kanbanColumns,
    kanbanSortMode,
    setKanbanSortMode,
    KANBAN_SORT_OPTIONS,
    getAppActivityDate,
    fetchApplications,
    fetchApplicationDetail,
    fetchApplication: fetchApplicationDetail,
    updateStatus,
    updateApplication,
    transitionApplication,
    quickReject,
    quickWithdraw,
    bulkTransition,
    restoreToActive,
    deleteApplication,
    invalidateCache,
    checkAndSyncWithBadges,
    lastFetchedAt,
    isStale,
  }
})
