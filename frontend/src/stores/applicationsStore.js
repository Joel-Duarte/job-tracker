import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { ApplicationsAPI } from '../api/endpoints'
import { useUIStore } from './uiStore'
import { getDemoDb } from '../demo/demoStorage'

const VALID_DATE_RANGES = ['all', '7d', '30d', '90d', 'custom']

function loadSavedDateRange() {
  try {
    const saved = localStorage.getItem('jobtracker_apps_date_range')
    return VALID_DATE_RANGES.includes(saved) ? saved : 'all'
  } catch {
    return 'all'
  }
}

function loadSavedDateBound(key) {
  try {
    return localStorage.getItem(key) || ''
  } catch {
    return ''
  }
}

export const useApplicationsStore = defineStore('applications', () => {
  const uiStore = useUIStore()

  // Flat application array for backward compatibility
  const applications = ref([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref(null)

  // Filters
  const searchQuery = ref('')
  const selectedStatus = ref('')
  const actionRequiredOnly = ref(false)
  const minMatchScore = ref(null)
  const selectedWorkModel = ref('') // '' | 'Remote' | 'Hybrid' | 'On-site'
  const selectedDateRange = ref(loadSavedDateRange()) // 'all' | '7d' | '30d' | '90d' | 'custom'
  const customDateStart = ref(loadSavedDateBound('jobtracker_apps_custom_date_start'))
  const customDateEnd = ref(loadSavedDateBound('jobtracker_apps_custom_date_end'))

  // Selected item / Drawer state
  const selectedApplication = ref(null)
  const loadingDetail = ref(false)

  // View mode
  const pipelineViewMode = ref('active') // 'active' | 'archive' | 'hired'
  const lastFetchedAt = ref(null)
  const isStale = ref(false)
  const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes cache TTL

  // Global Stage Counts from SQL aggregation
  const stageCounts = ref({
    APPLIED: 0,
    TECHNICAL_INTERVIEW: 0,
    OFFER: 0,
    ARCHIVED: 0,
    HIRED: 0,
    total_active: 0,
  })

  // Breakdown counts for Archived/Closed filter pills
  const archiveCounts = ref({
    all: 0,
    ghosted_post_applied: 0,
    ghosted_applied: 0,
    rejected: 0,
    withdrawn: 0,
  })

  // Selected subcategory filter in Archive View
  const archiveFilter = ref('all') // 'all' | 'ghosted_post_applied' | 'ghosted_applied' | 'rejected' | 'withdrawn'

  // Dedicated paginated state per archive subcategory
  const archiveSubState = ref({
    all: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    ghosted_post_applied: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    ghosted_applied: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    rejected: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    withdrawn: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
  })

  const currentArchiveState = computed(() => {
    return archiveSubState.value[archiveFilter.value] || archiveSubState.value.all
  })

  // Per-column paginated state
  const columnState = ref({
    APPLIED: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    TECHNICAL_INTERVIEW: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    OFFER: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    ARCHIVED: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
    HIRED: { items: [], total: 0, offset: 0, hasMore: true, loading: false },
  })

  watch([selectedDateRange, customDateStart, customDateEnd], ([range, start, end]) => {
    try {
      localStorage.setItem('jobtracker_apps_date_range', range || 'all')
      localStorage.setItem('jobtracker_apps_custom_date_start', start || '')
      localStorage.setItem('jobtracker_apps_custom_date_end', end || '')
    } catch {
      // ignore storage errors
    }
  })

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

  const STATUSES = [
    { key: 'ASSESSMENT', label: 'AI Assessment', color: 'assessment' },
    { key: 'APPLIED', label: 'Applied', color: 'applied' },
    { key: 'TECHNICAL_INTERVIEW', label: 'Interview', color: 'interview' },
    { key: 'OFFER', label: 'Offer', color: 'offer' },
    { key: 'REJECTED', label: 'Rejected', color: 'rejected' },
  ]

  const ACTIVE_STATUSES = [
    { key: 'APPLIED', label: 'Applied', color: 'applied' },
    { key: 'TECHNICAL_INTERVIEW', label: 'Interview', color: 'interview' },
    { key: 'OFFER', label: 'Offer', color: 'offer' },
  ]

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

  function getAppInterviewTimestamp(app) {
    const stage = (app.latest_event?.raw_payload?.interview_stage || '').trim()
    if (stage === 'Task Completed / Awaiting Response') {
      return null
    }
    const raw =
      app.scheduled_interview_at ||
      app.latest_event?.raw_payload?.scheduled_at
    if (!raw) return null
    const ts = new Date(raw).getTime()
    return isNaN(ts) ? null : ts
  }

  function getAppOfferDeadlineTimestamp(app) {
    const raw =
      app.nearest_due_date ||
      app.latest_event?.raw_payload?.decision_deadline
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
    const nowTs = Date.now()
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

  function processColumnItems(stageKey, rawItems) {
    if (!rawItems || rawItems.length === 0) return []

    const filtered = rawItems.filter((app) => {
      if (!matchesDateRange(app)) return false

      if (minMatchScore.value !== null && minMatchScore.value !== undefined && minMatchScore.value !== '') {
        const targetMin = Number(minMatchScore.value)
        if (targetMin > 0) {
          const score =
            app.match_score ??
            app.latest_event?.raw_payload?.match_score ??
            app.latest_event?.raw_payload?.fit_score ??
            null
          if (score === null || Number(score) < targetMin) {
            return false
          }
        }
      }
      return true
    })

    const mode = kanbanSortMode.value || 'smart'
    const list = [...filtered]

    if (mode === 'latest_activity') {
      return list.sort((a, b) => getAppActivityTimestamp(b) - getAppActivityTimestamp(a))
    }
    if (mode === 'next_scheduled') {
      return sortByNextScheduled(list)
    }
    if (mode === 'match_score') {
      return list.sort((a, b) => {
        const diff = getAppScore(b) - getAppScore(a)
        if (diff !== 0) return diff
        return getAppActivityTimestamp(b) - getAppActivityTimestamp(a)
      })
    }

    // Default: 'smart'
    const nowTs = Date.now()
    if (stageKey === 'APPLIED') {
      return list.sort((a, b) => getAppActivityTimestamp(b) - getAppActivityTimestamp(a))
    }
    if (stageKey === 'TECHNICAL_INTERVIEW') {
      return list.sort((a, b) => {
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
    }
    if (stageKey === 'OFFER') {
      return list.sort((a, b) => {
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

    return list
  }

  // Kanban columns with sorting & date/score filtering applied
  const kanbanColumns = computed(() => {
    return {
      APPLIED: processColumnItems('APPLIED', columnState.value.APPLIED.items),
      TECHNICAL_INTERVIEW: processColumnItems('TECHNICAL_INTERVIEW', columnState.value.TECHNICAL_INTERVIEW.items),
      OFFER: processColumnItems('OFFER', columnState.value.OFFER.items),
    }
  })

  const activeApplications = computed(() => {
    const combined = [
      ...columnState.value.APPLIED.items,
      ...columnState.value.TECHNICAL_INTERVIEW.items,
      ...columnState.value.OFFER.items,
    ]
    const seen = new Set()
    return combined.filter((a) => {
      if (!a?.id || seen.has(a.id)) return false
      seen.add(a.id)
      return matchesDateRange(a)
    })
  })

  const archivedApplications = computed(() => {
    const sub = currentArchiveState.value
    return (sub.items || []).filter((a) => matchesDateRange(a))
  })

  const hiredApplications = computed(() => {
    return (columnState.value.HIRED.items || []).filter((a) => matchesDateRange(a))
  })

  function syncApplicationsList() {
    const map = new Map()
    applications.value.forEach((a) => {
      if (a?.id) map.set(a.id, a)
    })
    Object.values(columnState.value).forEach((col) => {
      col.items.forEach((a) => {
        if (a?.id) map.set(a.id, a)
      })
    })
    Object.values(archiveSubState.value).forEach((sub) => {
      sub.items.forEach((a) => {
        if (a?.id) map.set(a.id, a)
      })
    })
    applications.value = Array.from(map.values())
  }

  function getDateFilterParams() {
    const range = selectedDateRange.value
    if (!range || range === 'all') return {}

    const now = new Date()
    if (range === '7d') {
      return { start_date: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString() }
    }
    if (range === '30d') {
      return { start_date: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString() }
    }
    if (range === '90d') {
      return { start_date: new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString() }
    }
    if (range === 'custom') {
      const params = {}
      if (customDateStart.value) {
        params.start_date = customDateStart.value
      }
      if (customDateEnd.value) {
        params.end_date = customDateEnd.value
      }
      return params
    }
    return {}
  }

  const currentFilterSignature = computed(() => {
    return JSON.stringify({
      q: (searchQuery.value || '').trim(),
      action_required: Boolean(actionRequiredOnly.value),
      work_model: selectedWorkModel.value || '',
      date_range: selectedDateRange.value || 'all',
      start_date: customDateStart.value || '',
      end_date: customDateEnd.value || '',
    })
  })
  const lastActiveSignature = ref('')
  const lastArchiveSignature = ref('')
  const lastHiredSignature = ref('')

  // Fetch fast stage counts from backend SQL aggregation
  async function fetchStageCounts() {
    try {
      const params = {
        ...getDateFilterParams(),
      }
      if (searchQuery.value && searchQuery.value.trim()) {
        params.q = searchQuery.value.trim()
      }
      if (actionRequiredOnly.value) {
        params.action_required = true
      }
      if (selectedWorkModel.value) {
        params.work_model = selectedWorkModel.value
      }
      const res = await ApplicationsAPI.getStageCounts(params)
      const data = res.data || {}
      stageCounts.value = {
        APPLIED: data.counts?.APPLIED || 0,
        TECHNICAL_INTERVIEW: data.counts?.TECHNICAL_INTERVIEW || 0,
        OFFER: data.counts?.OFFER || 0,
        ARCHIVED: data.counts?.ARCHIVED || 0,
        HIRED: data.counts?.HIRED || 0,
        total_active: data.total_active || 0,
      }
      if (data.archive_counts) {
        archiveCounts.value = {
          all: data.archive_counts.all || 0,
          ghosted_post_applied: data.archive_counts.ghosted_post_applied || 0,
          ghosted_applied: data.archive_counts.ghosted_applied || 0,
          rejected: data.archive_counts.rejected || 0,
          withdrawn: data.archive_counts.withdrawn || 0,
        }
      }
      total.value = data.total_active || 0
    } catch (err) {
      console.error('Failed to fetch stage counts:', err)
    }
  }

  // Paginated column fetch
  async function fetchColumn(stage, reset = false) {
    if (stage === 'ARCHIVED') {
      await fetchArchive(archiveFilter.value, reset)
      return
    }
    const col = columnState.value[stage]
    if (!col) return
    if (col.loading) return
    if (!reset && !col.hasMore) return

    col.loading = true
    const offset = reset ? 0 : col.offset
    const limit = 25

    try {
      const params = {
        status: stage,
        limit,
        offset,
        ...getDateFilterParams(),
      }
      if (searchQuery.value && searchQuery.value.trim()) {
        params.q = searchQuery.value.trim()
      }
      if (actionRequiredOnly.value) {
        params.action_required = true
      }
      if (selectedWorkModel.value) {
        params.work_model = selectedWorkModel.value
      }

      const res = await ApplicationsAPI.list(params)
      const items = res.data.items || []
      const totalCount = res.data.total ?? items.length

      if (reset) {
        col.items = items
        col.offset = items.length
      } else {
        const existingIds = new Set(col.items.map((i) => i.id))
        const deduped = items.filter((i) => !existingIds.has(i.id))
        col.items.push(...deduped)
        col.offset += items.length
      }
      col.total = totalCount
      col.hasMore = col.items.length < totalCount && items.length >= limit

      syncApplicationsList()
    } catch (err) {
      error.value = err.message
    } finally {
      col.loading = false
    }
  }

  // Dedicated paginated fetch for archive subcategories
  async function fetchArchive(subFilter = archiveFilter.value, reset = false) {
    const sub = archiveSubState.value[subFilter]
    if (!sub) return
    if (sub.loading) return
    if (!reset && !sub.hasMore) return

    sub.loading = true
    const offset = reset ? 0 : sub.offset
    const limit = 25

    try {
      const params = {
        status: 'ARCHIVED',
        archive_filter: subFilter,
        limit,
        offset,
        ...getDateFilterParams(),
      }
      if (searchQuery.value && searchQuery.value.trim()) {
        params.q = searchQuery.value.trim()
      }
      if (actionRequiredOnly.value) {
        params.action_required = true
      }
      if (selectedWorkModel.value) {
        params.work_model = selectedWorkModel.value
      }

      const res = await ApplicationsAPI.list(params)
      const items = res.data.items || []
      const totalCount = res.data.total ?? items.length

      if (reset) {
        sub.items = items
        sub.offset = items.length
      } else {
        const existingIds = new Set(sub.items.map((i) => i.id))
        const deduped = items.filter((i) => !existingIds.has(i.id))
        sub.items.push(...deduped)
        sub.offset += items.length
      }
      sub.total = totalCount
      sub.hasMore = sub.items.length < totalCount && items.length >= limit

      if (archiveFilter.value === subFilter) {
        columnState.value.ARCHIVED = { ...sub }
      }
      syncApplicationsList()
    } catch (err) {
      error.value = err.message
    } finally {
      sub.loading = false
      if (archiveFilter.value === subFilter) {
        columnState.value.ARCHIVED = { ...sub }
      }
    }
  }

  async function setArchiveFilter(newFilter) {
    archiveFilter.value = newFilter
    columnState.value.ARCHIVED = archiveSubState.value[newFilter] || archiveSubState.value.all
    const sub = archiveSubState.value[newFilter]
    if (sub && sub.items.length === 0 && sub.hasMore) {
      await fetchArchive(newFilter, true)
    }
  }

  async function loadMoreArchive() {
    await fetchArchive(archiveFilter.value, false)
  }

  async function loadMoreColumn(stage) {
    if (stage === 'ARCHIVED') {
      await loadMoreArchive()
    } else {
      await fetchColumn(stage, false)
    }
  }

  // Main board fetcher
  async function fetchApplications(force = false) {
    const isFresh =
      !force &&
      !isStale.value &&
      lastFetchedAt.value !== null &&
      (columnState.value.APPLIED.items.length > 0 || columnState.value.ARCHIVED.items.length > 0) &&
      Date.now() - lastFetchedAt.value < CACHE_TTL_MS

    if (isFresh) {
      return
    }

    loading.value = applications.value.length === 0
    error.value = null
    try {
      await fetchStageCounts()
      if (force) {
        for (const key of Object.keys(archiveSubState.value)) {
          archiveSubState.value[key] = { items: [], total: 0, offset: 0, hasMore: true, loading: false }
        }
        for (const stage of ['APPLIED', 'TECHNICAL_INTERVIEW', 'OFFER', 'HIRED']) {
          columnState.value[stage] = { items: [], total: 0, offset: 0, hasMore: true, loading: false }
        }
        lastActiveSignature.value = ''
        lastArchiveSignature.value = ''
        lastHiredSignature.value = ''
      }
      const curSig = currentFilterSignature.value
      if (pipelineViewMode.value === 'active') {
        await Promise.all([
          fetchColumn('APPLIED', true),
          fetchColumn('TECHNICAL_INTERVIEW', true),
          fetchColumn('OFFER', true),
        ])
        lastActiveSignature.value = curSig
      } else if (pipelineViewMode.value === 'archive') {
        await fetchArchive(archiveFilter.value, true)
        lastArchiveSignature.value = curSig
      } else if (pipelineViewMode.value === 'hired') {
        await fetchColumn('HIRED', true)
        lastHiredSignature.value = curSig
      }
      lastFetchedAt.value = Date.now()
      isStale.value = false
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  // Watch pipelineViewMode to lazily load archive / hired / active cards when tabs switch
  watch(pipelineViewMode, async (newMode) => {
    const curSig = currentFilterSignature.value
    if (newMode === 'active') {
      if (lastActiveSignature.value !== curSig) {
        await Promise.all([
          fetchColumn('APPLIED', true),
          fetchColumn('TECHNICAL_INTERVIEW', true),
          fetchColumn('OFFER', true),
        ])
        lastActiveSignature.value = curSig
      }
    } else if (newMode === 'archive') {
      if (lastArchiveSignature.value !== curSig) {
        await fetchArchive(archiveFilter.value, true)
        lastArchiveSignature.value = curSig
      }
    } else if (newMode === 'hired') {
      if (lastHiredSignature.value !== curSig) {
        await fetchColumn('HIRED', true)
        lastHiredSignature.value = curSig
      }
    }
  })

  // Debounced server search / filter reload
  let filterDebounceTimer = null
  watch(
    [
      searchQuery,
      actionRequiredOnly,
      selectedWorkModel,
      selectedDateRange,
      customDateStart,
      customDateEnd,
    ],
    () => {
      if (filterDebounceTimer) clearTimeout(filterDebounceTimer)
      filterDebounceTimer = setTimeout(() => {
        fetchApplications(true)
      }, 300)
    }
  )

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
      await fetchApplications(true)
      if (selectedApplication.value?.id) {
        await fetchApplicationDetail(selectedApplication.value.id)
      }
    }
  }

  async function fetchApplicationDetail(id) {
    loadingDetail.value = true
    try {
      const res = await ApplicationsAPI.get(id)
      selectedApplication.value = res.data

      for (const col of Object.values(columnState.value)) {
        const idx = col.items.findIndex((a) => a.id === id)
        if (idx !== -1) {
          col.items[idx].has_action_required = res.data.has_action_required
          col.items[idx].nearest_due_date = res.data.nearest_due_date
          col.items[idx].scheduled_interview_at = res.data.scheduled_interview_at
        }
      }
      syncApplicationsList()
    } catch (err) {
      error.value = err.message
    } finally {
      loadingDetail.value = false
    }
  }

  function mergeDetailIntoListItem(existingItem, detailData) {
    if (!detailData) return existingItem
    const { events, action_items, ...rest } = detailData
    const merged = {
      ...existingItem,
      ...rest,
      latest_event: detailData.latest_event || events?.[0] || existingItem?.latest_event || null,
    }
    delete merged.events
    delete merged.action_items
    return merged
  }

  const STAGE_MAP_TARGET = {
    APPLIED: 'APPLIED',
    RECRUITER_CONTACT: 'APPLIED',
    IN_PROGRESS: 'APPLIED',
    PENDING: 'APPLIED',
    PHONE_SCREEN: 'TECHNICAL_INTERVIEW',
    ONLINE_ASSESSMENT: 'TECHNICAL_INTERVIEW',
    TECHNICAL_INTERVIEW: 'TECHNICAL_INTERVIEW',
    BEHAVIORAL_INTERVIEW: 'TECHNICAL_INTERVIEW',
    ONSITE_INTERVIEW: 'TECHNICAL_INTERVIEW',
    FINAL_INTERVIEW: 'TECHNICAL_INTERVIEW',
    INTERVIEW: 'TECHNICAL_INTERVIEW',
    SCREENING: 'TECHNICAL_INTERVIEW',
    OFFER: 'OFFER',
    ARCHIVED: 'ARCHIVED',
    WITHDRAWN: 'ARCHIVED',
    REJECTED: 'ARCHIVED',
    HIRED: 'HIRED',
  }

  async function updateStatus(applicationId, newStatus) {
    return transitionApplication(applicationId, { status: newStatus })
  }

  async function transitionApplication(applicationId, transitionData) {
    const columnSnapshot = JSON.parse(JSON.stringify(columnState.value))
    const stageCountsSnapshot = { ...stageCounts.value }
    const selectedSnapshot = selectedApplication.value ? JSON.parse(JSON.stringify(selectedApplication.value)) : null

    let foundApp = null
    let sourceStage = null
    for (const [st, col] of Object.entries(columnState.value)) {
      const idx = col.items.findIndex((a) => a.id === applicationId)
      if (idx !== -1) {
        foundApp = col.items[idx]
        sourceStage = st
        col.items.splice(idx, 1)
        if (col.total > 0) col.total--
        break
      }
    }

    const updatedStatus = transitionData.status || foundApp?.status
    const targetColKey = STAGE_MAP_TARGET[(updatedStatus || '').toUpperCase()]

    if (foundApp && targetColKey && columnState.value[targetColKey]) {
      const updatedApp = { ...foundApp, ...transitionData }
      columnState.value[targetColKey].items.unshift(updatedApp)
      columnState.value[targetColKey].total = (columnState.value[targetColKey].total || 0) + 1
    }

    if (sourceStage && stageCounts.value[sourceStage] > 0) {
      stageCounts.value[sourceStage]--
    }
    if (targetColKey) {
      stageCounts.value[targetColKey] = (stageCounts.value[targetColKey] || 0) + 1
    }
    const activeStages = ['APPLIED', 'TECHNICAL_INTERVIEW', 'OFFER']
    const wasActive = activeStages.includes(sourceStage)
    const isActiveNow = activeStages.includes(targetColKey)
    if (wasActive && !isActiveNow) stageCounts.value.total_active = Math.max(0, stageCounts.value.total_active - 1)
    if (!wasActive && isActiveNow) stageCounts.value.total_active++

    if (selectedApplication.value && selectedApplication.value.id === applicationId) {
      selectedApplication.value = { ...selectedApplication.value, ...transitionData }
    }

    syncApplicationsList()

    try {
      const res = await ApplicationsAPI.transition(applicationId, transitionData)
      const updated = res.data
      if (targetColKey && columnState.value[targetColKey]) {
        const idx = columnState.value[targetColKey].items.findIndex((a) => a.id === applicationId)
        if (idx !== -1) {
          columnState.value[targetColKey].items[idx] = mergeDetailIntoListItem(
            columnState.value[targetColKey].items[idx],
            updated
          )
        }
      }
      if (selectedApplication.value && selectedApplication.value.id === applicationId) {
        selectedApplication.value = { ...selectedApplication.value, ...updated }
      }
      syncApplicationsList()
      return updated
    } catch (err) {
      columnState.value = columnSnapshot
      stageCounts.value = stageCountsSnapshot
      selectedApplication.value = selectedSnapshot
      syncApplicationsList()
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

  async function bulkTransition(targetStatus, fromStatuses, excludeIds = [], notes = null) {
    const columnSnapshot = JSON.parse(JSON.stringify(columnState.value))
    const stageCountsSnapshot = { ...stageCounts.value }

    try {
      const res = await ApplicationsAPI.bulkTransition({
        target_status: targetStatus,
        from_statuses: fromStatuses,
        exclude_ids: excludeIds,
        notes,
      })
      await fetchApplications(true)
      return res.data
    } catch (err) {
      columnState.value = columnSnapshot
      stageCounts.value = stageCountsSnapshot
      syncApplicationsList()
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

  function removeApplicationsForCompany(companyId) {
    for (const col of Object.values(columnState.value)) {
      col.items = col.items.filter(
        (a) =>
          String(a.company_id) !== String(companyId) &&
          String(a.company?.id) !== String(companyId)
      )
    }
    syncApplicationsList()
    fetchStageCounts()

    if (
      selectedApplication.value &&
      (String(selectedApplication.value.company_id) === String(companyId) ||
        String(selectedApplication.value.company?.id) === String(companyId))
    ) {
      selectedApplication.value = null
      uiStore.closeApplicationDrawer()
    }
  }

  async function deleteApplication(applicationId) {
    const columnSnapshot = JSON.parse(JSON.stringify(columnState.value))
    const stageCountsSnapshot = { ...stageCounts.value }
    const selectedSnapshot = selectedApplication.value ? JSON.parse(JSON.stringify(selectedApplication.value)) : null

    let sourceStage = null
    for (const [st, col] of Object.entries(columnState.value)) {
      const idx = col.items.findIndex((a) => a.id === applicationId)
      if (idx !== -1) {
        sourceStage = st
        col.items.splice(idx, 1)
        if (col.total > 0) col.total--
        break
      }
    }

    if (sourceStage && stageCounts.value[sourceStage] > 0) {
      stageCounts.value[sourceStage]--
    }
    const activeStages = ['APPLIED', 'TECHNICAL_INTERVIEW', 'OFFER']
    if (activeStages.includes(sourceStage)) {
      stageCounts.value.total_active = Math.max(0, stageCounts.value.total_active - 1)
    }

    if (selectedApplication.value && selectedApplication.value.id === applicationId) {
      selectedApplication.value = null
      uiStore.closeApplicationDrawer()
    }

    syncApplicationsList()

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('application:deleted', { detail: { applicationId } }))
    }

    try {
      await ApplicationsAPI.delete(applicationId)
      uiStore.showToast('Application deleted', 'info')
    } catch (err) {
      columnState.value = columnSnapshot
      stageCounts.value = stageCountsSnapshot
      selectedApplication.value = selectedSnapshot
      syncApplicationsList()
      uiStore.showToast(err.message || 'Failed to delete application', 'error')
      throw err
    }
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('company:deleted', (event) => {
      const { companyId, deletedApplications } = event.detail || {}
      if (companyId && deletedApplications) {
        removeApplicationsForCompany(companyId)
        fetchApplications(true)
      }
    })
  }

  async function updateApplication(applicationId, payload) {
    try {
      const res = await ApplicationsAPI.update(applicationId, payload)
      selectedApplication.value = res.data
      for (const col of Object.values(columnState.value)) {
        const idx = col.items.findIndex((a) => String(a.id) === String(applicationId))
        if (idx !== -1) {
          col.items[idx] = mergeDetailIntoListItem(col.items[idx], res.data)
        }
      }
      syncApplicationsList()
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
    stageCounts,
    archiveCounts,
    columnState,
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
    fetchStageCounts,
    fetchColumn,
    loadMoreColumn,
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
    removeApplicationsForCompany,
    invalidateCache,
    checkAndSyncWithBadges,
    lastFetchedAt,
    isStale,
    archiveFilter,
    archiveSubState,
    currentArchiveState,
    setArchiveFilter,
    loadMoreArchive,
    fetchArchive,
  }
})
