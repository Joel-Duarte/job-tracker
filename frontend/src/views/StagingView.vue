<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { StagingAPI } from '../api/endpoints'
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Mail,
  Building2,
  Loader2,
  Sparkles,
  Link as LinkIcon,
  Search,
  Check,
  Calendar,
  Layers,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  ArrowUpDown,
  Trash2,
  Clock,
  User,
  FileText,
  Globe,
  PlusCircle,
  AlertCircle,
  X,
} from 'lucide-vue-next'
import PageHeader from '../components/common/PageHeader.vue'
import DateTimePicker from '../components/common/DateTimePicker.vue'
import CompanyLogo from '../components/common/CompanyLogo.vue'
import { renderEmailBody } from '../utils/emailRenderer'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

// State
const stagingItems = ref([])
const totalCount = ref(0)
const loading = ref(false)
const isLoadingMore = ref(false)
const isSubmitting = ref(false)
const selectedFilter = ref('PENDING') // 'PENDING' | 'PROCESSED'
const pendingCount = ref(0)
const searchFilterQuery = ref('')
const sortOrder = ref('FIFO') // 'FIFO' (Oldest Email First) | 'LIFO' (Newest Email First)

const hasMore = computed(() => stagingItems.value.length < totalCount.value)
const itemsListRef = ref(null)

// Resolved Cleanup State
const clearOlderThanDays = ref(90) // 90 | 30 | 7 | null (All)
const isClearingResolved = ref(false)

// Master-detail active selection
const selectedItemId = ref(null)
const emailViewMode = ref('formatted') // 'formatted' | 'raw'

// Resolution Form State
const resolutionMode = ref('create') // 'create' | 'link'
const selectedExistingAppId = ref(null)
const appSearchQuery = ref('')
const includeArchivedApps = ref(false)
const showRawJobDesc = ref(false)

const resolveForm = ref({
  company: '',
  position: '',
  status: 'APPLIED',
  job_url: '',
  description_markdown: '',
  event_type: 'APPLICATION_CONFIRMATION',
  summary: '',
  action_required: false,
  action: '',
  due_date: '',
})

// Item extraction helpers
function getItemCompany(item) {
  if (!item) return 'Unknown Company'
  return (
    item.extracted_data?.company ||
    item.extracted_data?.company_name ||
    item.suggested_company ||
    'Unknown Company'
  )
}

function getItemPosition(item) {
  if (!item) return 'Position Not Specified'
  return (
    item.extracted_data?.position ||
    item.suggested_position ||
    'Software Engineer'
  )
}

function getDetectedEventType(item) {
  if (!item) return 'APPLICATION_CONFIRMATION'
  const extracted = item.extracted_data || {}
  return extracted.event_type || extracted.email_event_type || 'APPLICATION_CONFIRMATION'
}

function getAutoDetectedStatus(item) {
  const eventType = (getDetectedEventType(item) || '').toUpperCase()
  if (
    eventType.includes('INTERVIEW') ||
    eventType.includes('ASSESSMENT') ||
    eventType.includes('OA') ||
    eventType.includes('SCREEN')
  ) {
    return 'TECHNICAL_INTERVIEW'
  }
  if (eventType.includes('REJECT') || eventType.includes('NOT_MOVING_FORWARD')) {
    return 'REJECTED'
  }
  if (eventType.includes('OFFER')) {
    return 'OFFER'
  }
  return 'APPLIED'
}

function formatEventTypeLabel(eventType) {
  const t = (eventType || '').toUpperCase()
  if (t.includes('INTERVIEW')) return 'Interview Invitation'
  if (t.includes('REJECT')) return 'Rejection Notice'
  if (t.includes('OFFER')) return 'Offer Letter'
  if (t.includes('OA') || t.includes('ASSESSMENT')) return 'Assessment / Test'
  return 'Application Confirmation'
}

function getEventTypeBadgeClass(eventType) {
  const t = (eventType || '').toUpperCase()
  if (t.includes('OFFER')) return 'badge-offer'
  if (t.includes('INTERVIEW') || t.includes('OA') || t.includes('ASSESSMENT')) return 'badge-interview'
  if (t.includes('REJECT')) return 'badge-rejected'
  return 'badge-applied'
}

// Computed Urgency
const computedUrgency = computed(() => {
  if (resolveForm.value.due_date) {
    const due = new Date(resolveForm.value.due_date)
    if (!isNaN(due.getTime())) {
      const diffHours = (due.getTime() - Date.now()) / (1000 * 60 * 60)
      if (diffHours <= 48) return 'HIGH'
      if (diffHours <= 24 * 7) return 'MEDIUM'
      return 'LOW'
    }
  }
  const text = (resolveForm.value.action || '').toLowerCase()
  if (
    ['urgent', 'deadline', 'asap', 'schedule', 'interview', 'offer', 'expir', 'today', 'tomorrow'].some((w) =>
      text.includes(w)
    )
  ) {
    return 'HIGH'
  }
  return 'MEDIUM'
})

const computedUrgencyLabel = computed(() => {
  if (resolveForm.value.due_date) {
    const due = new Date(resolveForm.value.due_date)
    if (!isNaN(due.getTime())) {
      const diffHours = (due.getTime() - Date.now()) / (1000 * 60 * 60)
      if (diffHours < 0) return '⚡ High (Past Due)'
      if (diffHours <= 48) return '⚡ High (Due in <48h)'
      if (diffHours <= 24 * 7) return 'Medium (Due in <7d)'
      return 'Low (>7 days out)'
    }
  }
  if (computedUrgency.value === 'HIGH') return '⚡ High (Time-Sensitive Action)'
  return 'Medium Urgency'
})

// Filtered & Sorted Queue Items
const filteredAndSortedItems = computed(() => {
  let items = [...stagingItems.value]

  // Search filter
  if (searchFilterQuery.value.trim()) {
    const q = searchFilterQuery.value.toLowerCase().trim()
    items = items.filter((item) => {
      const comp = getItemCompany(item).toLowerCase()
      const pos = getItemPosition(item).toLowerCase()
      const sender = (item.email_sender || '').toLowerCase()
      const senderName = (item.email_sender_name || '').toLowerCase()
      const subject = (item.email_subject || '').toLowerCase()
      return (
        comp.includes(q) ||
        pos.includes(q) ||
        sender.includes(q) ||
        senderName.includes(q) ||
        subject.includes(q)
      )
    })
  }

  // FIFO / LIFO sorting on email received_at date (fallback to created_at)
  items.sort((a, b) => {
    const dateA = new Date(a.email_received_at || a.created_at).getTime()
    const dateB = new Date(b.email_received_at || b.created_at).getTime()
    return sortOrder.value === 'FIFO' ? dateA - dateB : dateB - dateA
  })

  return items
})

// Selected Item in Master-Detail
const selectedItem = computed(() => {
  if (!selectedItemId.value) return null
  return stagingItems.value.find((i) => i.id === selectedItemId.value) || null
})

const selectedItemIndex = computed(() => {
  if (!selectedItemId.value) return -1
  return filteredAndSortedItems.value.findIndex((i) => i.id === selectedItemId.value)
})

const hasPreviousItem = computed(() => selectedItemIndex.value > 0)
const hasNextItem = computed(() => selectedItemIndex.value >= 0 && selectedItemIndex.value < filteredAndSortedItems.value.length - 1)

function selectPreviousItem() {
  if (hasPreviousItem.value) {
    const prev = filteredAndSortedItems.value[selectedItemIndex.value - 1]
    if (prev) selectItem(prev)
  }
}

function selectNextItem() {
  if (hasNextItem.value) {
    const next = filteredAndSortedItems.value[selectedItemIndex.value + 1]
    if (next) selectItem(next)
  }
}

// Applications search for linking
const filteredExistingApps = computed(() => {
  let apps = appStore.applications || []
  if (!includeArchivedApps.value) {
    apps = apps.filter((a) => !['REJECTED', 'ARCHIVED', 'WITHDRAWN'].includes(a.status))
  }
  if (!appSearchQuery.value.trim()) return apps
  const q = appSearchQuery.value.toLowerCase().trim()
  return apps.filter(
    (a) =>
      (a.company?.name || '').toLowerCase().includes(q) ||
      (a.position || '').toLowerCase().includes(q)
  )
})

// Populate resolveForm whenever selected item changes
function selectItem(item) {
  if (!item) return
  selectedItemId.value = item.id
  resolutionMode.value = 'create'
  selectedExistingAppId.value = null
  includeArchivedApps.value = false
  appSearchQuery.value = getItemCompany(item) || ''
  showRawJobDesc.value = false
  emailViewMode.value = 'formatted'

  const extracted = item.extracted_data || {}
  const autoStatus = getAutoDetectedStatus(item)
  const eventType = getDetectedEventType(item)

  let extractedDueDate = ''
  if (extracted.due_date) {
    try {
      const parsed = new Date(extracted.due_date)
      if (!isNaN(parsed.getTime())) {
        extractedDueDate = parsed.toISOString().split('T')[0]
      }
    } catch {
      // ignore
    }
  }

  resolveForm.value = {
    company: getItemCompany(item),
    position: getItemPosition(item),
    status: autoStatus,
    job_url: '',
    description_markdown: '',
    event_type: eventType,
    summary:
      extracted.summary ||
      item.email_subject ||
      `Received ${formatEventTypeLabel(eventType)} from ${getItemCompany(item)}`,
    action_required: Boolean(extracted.action_required),
    action: extracted.action || '',
    due_date: extractedDueDate,
  }

  // Pre-match existing application if high confidence
  const companyName = getItemCompany(item).toLowerCase().trim()
  const matchedApp = (appStore.applications || []).find(
    (a) => (a.company?.name || '').toLowerCase().trim() === companyName
  )
  if (matchedApp) {
    selectedExistingAppId.value = matchedApp.id
  }
}

// Watch sorted items to keep selection stable
watch(
  () => filteredAndSortedItems.value,
  (items) => {
    if (items.length > 0) {
      if (!selectedItemId.value || !items.some((i) => i.id === selectedItemId.value)) {
        selectItem(items[0])
      }
    } else {
      selectedItemId.value = null
    }
  },
  { immediate: true }
)

// Fetch Staging Items API
async function fetchStagingItems(silent = false) {
  if (!silent) {
    loading.value = true
  }
  try {
    const res = await StagingAPI.list({
      status: selectedFilter.value,
      search: searchFilterQuery.value.trim() || undefined,
      limit: 50,
      offset: 0,
    })
    stagingItems.value = res.data.items || []
    totalCount.value = res.data.total ?? stagingItems.value.length

    if (selectedFilter.value === 'PENDING') {
      pendingCount.value = res.data.total ?? stagingItems.value.length
    } else {
      StagingAPI.list({ status: 'PENDING', limit: 1 })
        .then((pRes) => {
          pendingCount.value = pRes.data.total ?? 0
        })
        .catch(() => {})
    }
  } catch (err) {
    if (!silent) {
      uiStore.showToast(err.message, 'error')
    }
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

// Load more items (incremental batch scroll)
async function loadMoreItems() {
  if (isLoadingMore.value || !hasMore.value) return
  isLoadingMore.value = true
  try {
    const res = await StagingAPI.list({
      status: selectedFilter.value,
      search: searchFilterQuery.value.trim() || undefined,
      limit: 50,
      offset: stagingItems.value.length,
    })
    const newItems = res.data.items || []
    stagingItems.value = [...stagingItems.value, ...newItems]
    totalCount.value = res.data.total ?? totalCount.value
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isLoadingMore.value = false
  }
}

// Load all remaining items in queue
async function loadAllItems() {
  if (isLoadingMore.value || !hasMore.value) return
  isLoadingMore.value = true
  try {
    const remaining = totalCount.value - stagingItems.value.length
    const res = await StagingAPI.list({
      status: selectedFilter.value,
      search: searchFilterQuery.value.trim() || undefined,
      limit: Math.min(remaining, 500),
      offset: stagingItems.value.length,
    })
    const newItems = res.data.items || []
    stagingItems.value = [...stagingItems.value, ...newItems]
    totalCount.value = res.data.total ?? totalCount.value
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isLoadingMore.value = false
  }
}

function handleSidebarScroll() {
  if (!itemsListRef.value || isLoadingMore.value || loading.value || !hasMore.value) return
  const { scrollTop, scrollHeight, clientHeight } = itemsListRef.value
  if (scrollTop + clientHeight >= scrollHeight - 60) {
    loadMoreItems()
  }
}

// Debounce server search
let searchDebounceTimeout = null
watch(searchFilterQuery, () => {
  if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout)
  searchDebounceTimeout = setTimeout(() => {
    fetchStagingItems(true)
  }, 300)
})

// Clear Resolved Execution
async function executeClearResolved() {
  isClearingResolved.value = true
  try {
    const res = await StagingAPI.clearResolved(clearOlderThanDays.value)
    uiStore.showToast(res.data.message || 'Resolved items cleared', 'success')
    await fetchStagingItems()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to clear resolved items', 'error')
  } finally {
    isClearingResolved.value = false
  }
}

async function quickDismissItem(item) {
  if (!item) return
  const isSelected = selectedItemId.value === item.id
  const currentIndex = filteredAndSortedItems.value.findIndex((i) => i.id === item.id)

  try {
    await StagingAPI.delete(item.id)
    uiStore.showToast('Item dismissed', 'info')
    await fetchStagingItems(true)

    if (isSelected) {
      const remainingItems = filteredAndSortedItems.value
      if (remainingItems.length > 0) {
        const nextIndex = currentIndex < remainingItems.length ? currentIndex : remainingItems.length - 1
        selectItem(remainingItems[nextIndex])
      } else {
        selectedItemId.value = null
      }
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to dismiss item', 'error')
  }
}

let stagingPollInterval = null

function handleKeyDown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
    return
  }
  if (e.key === 'ArrowLeft' || e.key === 'k') {
    selectPreviousItem()
  } else if (e.key === 'ArrowRight' || e.key === 'j') {
    selectNextItem()
  }
}

onMounted(() => {
  fetchStagingItems()
  if (appStore.applications.length === 0) {
    appStore.fetchApplications()
  }

  window.addEventListener('keydown', handleKeyDown)

  // Background real-time polling
  stagingPollInterval = setInterval(() => {
    fetchStagingItems(true)
  }, 4000)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  if (stagingPollInterval) {
    clearInterval(stagingPollInterval)
  }
})

// Submit Resolution with Auto-Advance
async function submitResolution() {
  if (!selectedItem.value) return
  isSubmitting.value = true

  const currentIndex = selectedItemIndex.value

  try {
    const payload = {
      status: resolveForm.value.status,
      event_type: resolveForm.value.event_type,
      summary: resolveForm.value.summary.trim() || null,
      action_required: resolveForm.value.action_required,
      action: resolveForm.value.action?.trim() || null,
      urgency: resolveForm.value.action_required ? computedUrgency.value : null,
      due_date:
        resolveForm.value.action_required && resolveForm.value.due_date
          ? new Date(resolveForm.value.due_date).toISOString()
          : null,
      job_url: resolveForm.value.job_url.trim() || null,
      description_markdown: resolveForm.value.description_markdown.trim() || null,
    }

    if (resolutionMode.value === 'create') {
      if (!resolveForm.value.company.trim() || !resolveForm.value.position.trim()) {
        uiStore.showToast('Company and Position are required.', 'warning')
        isSubmitting.value = false
        return
      }

      await StagingAPI.resolve(selectedItem.value.id, {
        ...payload,
        company: resolveForm.value.company.trim(),
        position: resolveForm.value.position.trim(),
        create_new: true,
      })

      uiStore.showToast(
        `Created '${resolveForm.value.company}' application & recorded timeline event!`,
        'success'
      )
    } else {
      if (!selectedExistingAppId.value) {
        uiStore.showToast('Please select an existing application to link with.', 'warning')
        isSubmitting.value = false
        return
      }

      const matchedApp = appStore.applications.find((a) => a.id === selectedExistingAppId.value)
      await StagingAPI.resolve(selectedItem.value.id, {
        ...payload,
        application_id: selectedExistingAppId.value,
        company: matchedApp?.company?.name || resolveForm.value.company,
        position: matchedApp?.position || resolveForm.value.position,
        create_new: false,
      })

      uiStore.showToast(
        `Linked email event to '${matchedApp?.company?.name || 'application'}'!`,
        'success'
      )
    }

    // Refresh data
    await fetchStagingItems(true)
    appStore.fetchApplications()

    // Auto-advance to next item in queue
    const remainingItems = filteredAndSortedItems.value
    if (remainingItems.length > 0) {
      const nextItem =
        currentIndex < remainingItems.length ? remainingItems[currentIndex] : remainingItems[remainingItems.length - 1]
      selectItem(nextItem)
    } else {
      selectedItemId.value = null
    }
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

async function dismissCurrentItem() {
  if (!selectedItem.value) return
  await quickDismissItem(selectedItem.value)
}

function formatDate(isoStr) {
  if (!isoStr) return 'N/A'
  try {
    const d = new Date(isoStr)
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoStr
  }
}

function formatRelativeTime(isoStr) {
  if (!isoStr) return ''
  try {
    const diffMs = Date.now() - new Date(isoStr).getTime()
    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHrs < 1) return 'Just now'
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    return `${diffDays}d ago`
  } catch {
    return ''
  }
}
</script>

<template>
  <div class="page-container staging-workspace-container">
    <!-- Header Bar -->
    <div class="staging-header-wrap">
      <PageHeader
        title="Human-in-the-Loop Staging Queue"
        subtitle="Review unmatched emails, resolve ambiguous job leads into new applications, or link them to existing pipeline records."
        align="center"
      >
        <template #tabs>
          <div class="filter-pills-wrap">
            <div class="filter-pills">
              <button
                class="pill-btn"
                :class="{ active: selectedFilter === 'PENDING' }"
                @click="selectedFilter = 'PENDING'; fetchStagingItems()"
              >
                Pending ({{ pendingCount }})
              </button>
              <button
                class="pill-btn"
                :class="{ active: selectedFilter === 'PROCESSED' }"
                @click="selectedFilter = 'PROCESSED'; fetchStagingItems()"
              >
                Resolved
              </button>
            </div>
          </div>
        </template>
      </PageHeader>
    </div>

    <!-- Workspace Master-Detail Split Pane -->
    <div class="staging-split-workspace">
      <!-- LEFT PANE: Filterable Staging Queue Sidebar -->
      <aside class="staging-sidebar">
        <!-- Sidebar Controls -->
        <div class="sidebar-controls">
          <div class="sidebar-search-box">
            <Search :size="14" class="search-box-icon" />
            <input
              v-model="searchFilterQuery"
              type="text"
              placeholder="Search company, sender, or subject..."
              class="sidebar-search-input"
            />
            <button
              v-if="searchFilterQuery"
              class="btn-clear-input"
              @click="searchFilterQuery = ''"
            >
              <X :size="12" />
            </button>
          </div>

          <!-- FIFO Sort Toggle Header -->
          <div class="sidebar-sort-bar">
            <span class="sort-count-label">
              Showing {{ filteredAndSortedItems.length }} of {{ totalCount }}
            </span>
            <button
              class="btn-sort-toggle"
              :title="sortOrder === 'FIFO' ? 'Switch to Newest Email First' : 'Switch to Oldest Email First'"
              @click="sortOrder = sortOrder === 'FIFO' ? 'LIFO' : 'FIFO'"
            >
              <Clock :size="12" />
              <span>{{ sortOrder === 'FIFO' ? 'Oldest Email' : 'Newest Email' }}</span>
              <ArrowUpDown :size="11" />
            </button>
          </div>

          <!-- Inline Resolved Cleanup Bar -->
          <div v-if="selectedFilter === 'PROCESSED'" class="sidebar-cleanup-bar">
            <div class="cleanup-controls-row">
              <select v-model="clearOlderThanDays" class="cleanup-select">
                <option :value="90">Older than 90 days (Default)</option>
                <option :value="30">Older than 30 days</option>
                <option :value="7">Older than 7 days</option>
                <option :value="null">All Resolved Items</option>
              </select>
              <button
                class="btn-clean-now"
                :disabled="isClearingResolved"
                title="Clean resolved staging items"
                @click="executeClearResolved"
              >
                <Loader2 v-if="isClearingResolved" class="animate-spin" :size="12" />
                <Trash2 v-else :size="12" />
                <span>Clean Now</span>
              </button>
            </div>
            <p class="cleanup-safety-hint">
              Safe to delete: Created applications, timeline events, and notes are preserved independently.
            </p>
          </div>
        </div>

        <!-- Queue Item List -->
        <div ref="itemsListRef" class="sidebar-items-list" @scroll="handleSidebarScroll">
          <div v-if="loading && stagingItems.length === 0" class="sidebar-loading">
            <Loader2 class="animate-spin text-primary" :size="20" />
            <span>Loading queue...</span>
          </div>

          <div v-else-if="filteredAndSortedItems.length === 0" class="sidebar-empty">
            <Inbox :size="32" class="text-muted" />
            <p class="empty-text">No matching staging items</p>
          </div>

          <div
            v-for="item in filteredAndSortedItems"
            :key="item.id"
            class="queue-item-card"
            :class="{
              active: selectedItemId === item.id,
              'has-action': item.extracted_data?.action_required,
              resolved: item.status !== 'PENDING'
            }"
            @click="selectItem(item)"
          >
            <div class="item-header-row">
              <div class="item-company-tag">
                <Building2 :size="14" class="text-primary" />
                <span class="item-company-name">{{ getItemCompany(item) }}</span>
              </div>
              <div class="item-header-right">
                <span class="item-time-tag">{{ formatRelativeTime(item.email_received_at || item.created_at) }}</span>
                <button
                  v-if="item.status === 'PENDING'"
                  class="btn-quick-dismiss"
                  title="Dismiss item"
                  @click.stop="quickDismissItem(item)"
                >
                  <Trash2 :size="12" />
                </button>
              </div>
            </div>

            <div class="item-role-title">{{ getItemPosition(item) }}</div>
            <div class="item-subject-snippet">{{ item.email_subject || 'No Subject' }}</div>

            <div class="item-footer-row">
              <span class="item-event-badge" :class="getEventTypeBadgeClass(getDetectedEventType(item))">
                {{ formatEventTypeLabel(getDetectedEventType(item)) }}
              </span>
              <span v-if="item.extracted_data?.action_required" class="item-action-pill" title="Action required">
                ⚡ Action
              </span>
            </div>
          </div>

          <!-- Infinite Scroll / Load More Footer -->
          <div v-if="hasMore" class="sidebar-load-more-footer">
            <button
              class="btn-load-more"
              :disabled="isLoadingMore"
              @click="loadMoreItems"
            >
              <Loader2 v-if="isLoadingMore" class="animate-spin" :size="13" />
              <span v-else>Load More ({{ totalCount - stagingItems.length }} left)</span>
            </button>
            <button
              class="btn-load-all"
              :disabled="isLoadingMore"
              @click="loadAllItems"
              title="Load all remaining items into the sidebar"
            >
              Load All
            </button>
          </div>
        </div>
      </aside>

      <!-- RIGHT MAIN PANE: Focused Triage Workspace -->
      <main class="staging-main-detail">
        <!-- Empty Selection / All Clear State -->
        <div v-if="!selectedItem" class="workspace-empty-view">
          <div class="empty-box-inner">
            <Inbox :size="56" class="empty-inbox-icon" />
            <h3>Staging Queue is Clear</h3>
            <p>All incoming recruitment emails have been processed and linked to your pipeline.</p>
          </div>
        </div>

        <!-- Active Item Triage Area -->
        <div v-else class="workspace-content-grid">
          <!-- Top Triage Action Navigation Bar -->
          <div class="triage-nav-header">
            <div class="nav-counter">
              <span class="counter-badge">
                Item {{ selectedItemIndex + 1 }} of {{ filteredAndSortedItems.length }}
              </span>
              <span class="nav-hint-text">Use [← / →] or J/K keys to navigate</span>
            </div>

            <div class="nav-actions">
              <div class="chevron-nav-group">
                <button
                  class="btn-nav-chevron"
                  :disabled="!hasPreviousItem"
                  title="Previous Item (Left Arrow / K)"
                  @click="selectPreviousItem"
                >
                  <ChevronLeft :size="16" />
                  <span>Prev</span>
                </button>
                <button
                  class="btn-nav-chevron"
                  :disabled="!hasNextItem"
                  title="Next Item (Right Arrow / J)"
                  @click="selectNextItem"
                >
                  <span>Next</span>
                  <ChevronRight :size="16" />
                </button>
              </div>

              <button
                v-if="selectedItem.status === 'PENDING'"
                class="btn-dismiss-action"
                title="Dismiss and remove this item"
                @click="dismissCurrentItem"
              >
                <Trash2 :size="14" />
                <span>Dismiss</span>
              </button>
              <div v-else class="resolved-status-tag">
                <CheckCircle2 :size="13" class="text-success" />
                <span>Resolved Record</span>
              </div>
            </div>
          </div>

          <!-- Master Triage Area (Single Column when Resolved) -->
          <div class="triage-body-columns" :class="{ 'is-resolved-view': selectedItem.status !== 'PENDING' }">
            <!-- SUB-PANE 1: Full Email Inspector -->
            <section class="email-inspector-panel">
              <!-- Resolved Context Banner (shown when viewing resolved item) -->
              <div v-if="selectedItem.status !== 'PENDING'" class="resolved-context-strip">
                <div class="resolved-context-left">
                  <CheckCircle2 :size="15" class="text-success" />
                  <span><strong>Resolved Lead:</strong> This communication has been processed and saved to your pipeline.</span>
                </div>
                <div class="resolved-context-badges">
                  <span class="badge-mini" :class="getEventTypeBadgeClass(getDetectedEventType(selectedItem))">
                    {{ formatEventTypeLabel(getDetectedEventType(selectedItem)) }}
                  </span>
                  <span class="badge-mini badge-resolved-target">
                    {{ getItemCompany(selectedItem) }} — {{ getItemPosition(selectedItem) }}
                  </span>
                </div>
              </div>

              <div class="inspector-header">
                <div class="email-meta-block">
                  <div class="email-subject-heading">{{ selectedItem.email_subject || '(No Subject)' }}</div>
                  <div class="email-sender-line">
                    <User :size="13" class="text-muted" />
                    <strong>{{ selectedItem.email_sender_name || selectedItem.email_sender }}</strong>
                    <span v-if="selectedItem.email_sender_name && selectedItem.email_sender" class="email-address">
                      &lt;{{ selectedItem.email_sender }}&gt;
                    </span>
                  </div>
                  <div class="email-date-line">
                    <Clock :size="13" class="text-muted" />
                    <span>Received {{ formatDate(selectedItem.email_received_at || selectedItem.created_at) }}</span>
                  </div>
                </div>

                <div class="email-view-toggle">
                  <button
                    class="btn-toggle-view"
                    :class="{ active: emailViewMode === 'formatted' }"
                    @click="emailViewMode = 'formatted'"
                  >
                    Formatted
                  </button>
                  <button
                    class="btn-toggle-view"
                    :class="{ active: emailViewMode === 'raw' }"
                    @click="emailViewMode = 'raw'"
                  >
                    Raw Text
                  </button>
                </div>
              </div>

              <!-- Email Content Body -->
              <div class="inspector-content-body">
                <!-- Formatted Body View -->
                <div v-if="emailViewMode === 'formatted'" class="email-body-formatted">
                  <div
                    class="email-html-render"
                    v-html="renderEmailBody(selectedItem.email_raw_body || selectedItem.raw_payload?.body || '')"
                  ></div>
                </div>

                <!-- Raw JSON / Data View -->
                <div v-else class="email-body-raw">
                  <pre class="raw-code-block">{{ selectedItem.email_raw_body || JSON.stringify(selectedItem, null, 2) }}</pre>
                </div>
              </div>
            </section>

            <!-- SUB-PANE 2: AI Suggestions & Resolution Controls (Only shown for PENDING items) -->
            <section v-if="selectedItem.status === 'PENDING'" class="resolution-panel">
              <!-- AI Extraction Highlights -->
              <div class="ai-extraction-card">
                <div class="ai-card-title">
                  <Sparkles :size="14" class="text-primary" />
                  <span>AI Extracted Intelligence</span>
                </div>

                <div class="ai-tags-grid">
                  <div class="ai-tag-item">
                    <span class="ai-tag-label">Company:</span>
                    <strong class="ai-tag-val">{{ getItemCompany(selectedItem) }}</strong>
                  </div>
                  <div class="ai-tag-item">
                    <span class="ai-tag-label">Position:</span>
                    <strong class="ai-tag-val">{{ getItemPosition(selectedItem) }}</strong>
                  </div>
                  <div class="ai-tag-item">
                    <span class="ai-tag-label">Detected Event:</span>
                    <span class="badge-mini" :class="getEventTypeBadgeClass(getDetectedEventType(selectedItem))">
                      {{ formatEventTypeLabel(getDetectedEventType(selectedItem)) }}
                    </span>
                  </div>
                  <div v-if="selectedItem.extracted_data?.action" class="ai-tag-item full-width">
                    <span class="ai-tag-label">Action Item:</span>
                    <span class="ai-action-text">{{ selectedItem.extracted_data.action }}</span>
                  </div>
                </div>
              </div>

              <!-- Resolution Mode Tabs -->
              <div class="mode-tab-selector">
                <button
                  class="mode-tab-btn"
                  :class="{ active: resolutionMode === 'create' }"
                  @click="resolutionMode = 'create'"
                >
                  <PlusCircle :size="14" />
                  <span>Create as New Application</span>
                </button>
                <button
                  class="mode-tab-btn"
                  :class="{ active: resolutionMode === 'link' }"
                  @click="resolutionMode = 'link'"
                >
                  <LinkIcon :size="14" />
                  <span>Link to Existing Application</span>
                </button>
              </div>

              <!-- FORM: Mode = CREATE NEW APPLICATION -->
              <div v-if="resolutionMode === 'create'" class="triage-form-stack">
                <div class="form-row-2col">
                  <div class="form-group">
                    <label class="form-label">Company Name *</label>
                    <input
                      v-model="resolveForm.company"
                      type="text"
                      class="form-input"
                      placeholder="e.g. Stripe"
                      required
                    />
                  </div>
                  <div class="form-group">
                    <label class="form-label">Position Title *</label>
                    <input
                      v-model="resolveForm.position"
                      type="text"
                      class="form-input"
                      placeholder="e.g. Staff Backend Engineer"
                      required
                    />
                  </div>
                </div>

                <div class="form-row-2col">
                  <div class="form-group">
                    <label class="form-label">Pipeline Stage</label>
                    <select v-model="resolveForm.status" class="form-select">
                      <option value="APPLIED">Applied</option>
                      <option value="TECHNICAL_INTERVIEW">Technical Interview</option>
                      <option value="OFFER">Offer</option>
                      <option value="REJECTED">Rejected</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Timeline Event Type</label>
                    <select v-model="resolveForm.event_type" class="form-select">
                      <option value="APPLICATION_CONFIRMATION">Application Confirmation</option>
                      <option value="INTERVIEW_INVITATION">Interview Invitation</option>
                      <option value="TECHNICAL_ASSESSMENT">Assessment / Take-Home</option>
                      <option value="OFFER_LETTER">Offer Letter</option>
                      <option value="REJECTION">Rejection Notice</option>
                    </select>
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label">Job Posting URL (Optional)</label>
                  <input
                    v-model="resolveForm.job_url"
                    type="url"
                    class="form-input"
                    placeholder="https://..."
                  />
                  <p class="form-helper-text text-muted">
                    ✨ Providing a job URL will automatically trigger an AI fit & match analysis against your profile in the background.
                  </p>
                </div>

                <div class="form-group">
                  <label class="form-label">Event Summary / Timeline Note</label>
                  <textarea
                    v-model="resolveForm.summary"
                    class="form-textarea"
                    rows="2"
                    placeholder="Brief description of this communication..."
                  ></textarea>
                </div>

                <!-- Action Item Toggle -->
                <div class="action-item-section">
                  <label class="checkbox-label">
                    <input v-model="resolveForm.action_required" type="checkbox" />
                    <span>Create follow-up Action Item from this email</span>
                  </label>

                  <div v-if="resolveForm.action_required" class="action-item-details animate-fade-in">
                    <div class="form-group">
                      <label class="form-label">Task Description</label>
                      <input
                        v-model="resolveForm.action"
                        type="text"
                        class="form-input"
                        placeholder="e.g. Schedule coding interview with recruiter"
                      />
                    </div>
                    <div class="form-group">
                      <label class="form-label">Due Date & Urgency: <span class="text-primary">{{ computedUrgencyLabel }}</span></label>
                      <DateTimePicker
                        v-model="resolveForm.due_date"
                        type="date"
                        placeholder="Select deadline..."
                      />
                    </div>
                  </div>
                </div>
              </div>

              <!-- FORM: Mode = LINK TO EXISTING APPLICATION -->
              <div v-else class="triage-form-stack">
                <div class="form-group">
                  <label class="form-label">Search Target Application</label>
                  <div class="app-search-input-wrapper">
                    <Search :size="14" class="search-icon" />
                    <input
                      v-model="appSearchQuery"
                      type="text"
                      placeholder="Search active applications by company or role..."
                      class="form-input search-input-with-icon"
                    />
                  </div>
                </div>

                <div class="app-select-cards-list">
                  <div
                    v-for="app in filteredExistingApps"
                    :key="app.id"
                    class="existing-app-option-card"
                    :class="{ selected: selectedExistingAppId === app.id }"
                    @click="selectedExistingAppId = app.id"
                  >
                    <div class="app-option-main">
                      <CompanyLogo :name="app.company?.name" :domain="app.company?.domain" :size="24" />
                      <div class="app-option-titles">
                        <strong>{{ app.company?.name }}</strong>
                        <span class="app-option-role">{{ app.position }}</span>
                      </div>
                    </div>
                    <div class="app-option-badge">
                      <span class="badge-mini" :class="`badge-${(app.status || 'applied').toLowerCase()}`">
                        {{ app.status?.replace('_', ' ') }}
                      </span>
                    </div>
                  </div>

                  <div v-if="filteredExistingApps.length === 0" class="no-apps-found">
                    <span>No applications found matching "{{ appSearchQuery }}"</span>
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label">Timeline Event Type to Record</label>
                  <select v-model="resolveForm.event_type" class="form-select">
                    <option value="APPLICATION_CONFIRMATION">Application Confirmation</option>
                    <option value="INTERVIEW_INVITATION">Interview Invitation</option>
                    <option value="TECHNICAL_ASSESSMENT">Assessment / Take-Home</option>
                    <option value="OFFER_LETTER">Offer Letter</option>
                    <option value="REJECTION">Rejection Notice</option>
                  </select>
                </div>

                <div class="form-group">
                  <label class="form-label">Timeline Event Summary</label>
                  <textarea
                    v-model="resolveForm.summary"
                    class="form-textarea"
                    rows="2"
                    placeholder="Brief description of this communication..."
                  ></textarea>
                </div>
              </div>

              <!-- Sticky Resolution Bottom Bar -->
              <div class="resolution-footer-bar">
                <button
                  class="btn btn-primary btn-submit-resolve"
                  :disabled="isSubmitting"
                  @click="submitResolution"
                >
                  <Loader2 v-if="isSubmitting" class="animate-spin" :size="16" />
                  <Check v-else :size="16" />
                  <span>
                    {{ resolutionMode === 'create' ? 'Create Application & Resolve' : 'Link Event & Resolve' }}
                  </span>
                  <ChevronRight :size="14" class="btn-advance-icon" />
                </button>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>

  </div>
</template>

<style scoped>
.staging-workspace-container {
  height: calc(100vh - var(--header-height, 60px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  margin: 0;
  max-width: 100%;
}

.staging-header-wrap {
  padding: 24px 24px 16px;
  background-color: var(--bg-app);
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.staging-header-wrap :deep(.page-header) {
  margin-bottom: 0;
}

.filter-pills {
  display: inline-flex;
  align-items: center;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 4px;
}

.pill-btn {
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-xs);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.pill-btn:hover {
  color: var(--text-main);
  background-color: var(--bg-card-hover);
}

.pill-btn.active {
  background-color: var(--primary);
  color: #ffffff;
  box-shadow: var(--shadow-sm);
}

.staging-split-workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 340px 1fr;
  min-height: 0;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-app);
}

/* LEFT SIDEBAR */
.staging-sidebar {
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.sidebar-controls {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-box-icon {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
}

.sidebar-search-input {
  width: 100%;
  padding: 7px 28px 7px 30px;
  font-size: 13px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  outline: none;
  transition: border-color var(--transition-fast);
}

.sidebar-search-input:focus {
  border-color: var(--primary);
}

.btn-clear-input {
  position: absolute;
  right: 8px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
}

.sidebar-sort-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sort-count-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.btn-sort-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  padding: 3px 8px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-sort-toggle:hover {
  color: var(--primary);
  border-color: var(--primary);
}

.sidebar-items-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar-loading,
.sidebar-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 10px;
  color: var(--text-muted);
  font-size: 13px;
}

/* QUEUE ITEM CARD */
.queue-item-card {
  position: relative;
  background-color: var(--bg-card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
  padding: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-quick-dismiss {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px;
  background: transparent;
  border: none;
  border-radius: var(--radius-xs);
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: all var(--transition-fast);
}

.queue-item-card:hover .btn-quick-dismiss,
.btn-quick-dismiss:focus {
  opacity: 1;
}

@media (hover: none) {
  .btn-quick-dismiss {
    opacity: 1;
  }
}

.btn-quick-dismiss:hover {
  color: var(--danger, #ef4444);
  background-color: var(--danger-subtle, rgba(239, 68, 68, 0.1));
}

.queue-item-card:hover {
  background-color: var(--bg-card-hover);
  border-color: var(--card-hover-border);
  transform: translateY(-1px);
}

.queue-item-card.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
  box-shadow: 0 0 0 1px var(--primary);
}

.item-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.item-company-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-time-tag {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.item-role-title {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-subject-snippet {
  font-size: 11px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.item-event-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  text-transform: uppercase;
}

.badge-interview {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
}

.badge-offer {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
}

.badge-rejected {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
}

.badge-applied {
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
}

.item-action-pill {
  font-size: 10px;
  font-weight: 700;
  color: var(--warning);
  background-color: var(--warning-subtle);
  padding: 1px 5px;
  border-radius: var(--radius-xs);
}

/* RIGHT MAIN DETAIL AREA */
.staging-main-detail {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background-color: var(--bg-surface);
  overflow: hidden;
}

.workspace-empty-view {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-box-inner {
  text-align: center;
  max-width: 360px;
  color: var(--text-muted);
}

.empty-inbox-icon {
  margin-bottom: 12px;
  color: var(--primary);
  opacity: 0.8;
}

.workspace-content-grid {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* NAVIGATION HEADER */
.triage-nav-header {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-card);
}

.nav-counter {
  display: flex;
  align-items: center;
  gap: 10px;
}

.counter-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  background-color: var(--bg-surface);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}

.nav-hint-text {
  font-size: 11px;
  color: var(--text-muted);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chevron-nav-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-nav-chevron {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-nav-chevron:hover:not(:disabled) {
  color: var(--primary);
  border-color: var(--primary);
}

.btn-nav-chevron:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-dismiss-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--danger);
  background-color: var(--danger-subtle);
  border: 1px solid var(--danger-subtle);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-dismiss-action:hover {
  background-color: var(--danger);
  color: #ffffff;
}

.resolved-status-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-success);
  background-color: var(--success-subtle);
  border: 1px solid var(--success-subtle);
  border-radius: var(--radius-sm);
}

/* MASTER TRIAGE BODY */
.triage-body-columns {
  flex: 1;
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  min-height: 0;
  overflow: hidden;
}

.triage-body-columns.is-resolved-view {
  grid-template-columns: 1fr;
}

.triage-body-columns.is-resolved-view .email-inspector-panel {
  border-right: none;
}

/* SUB-PANE 1: EMAIL INSPECTOR */
.email-inspector-panel {
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  min-height: 0;
  background-color: var(--bg-surface);
}

.resolved-context-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background-color: var(--success-subtle);
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  gap: 12px;
}

.resolved-context-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-main);
}

.resolved-context-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge-resolved-target {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.inspector-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  background-color: var(--bg-card);
}

.email-meta-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.email-subject-heading {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.email-sender-line,
.email-date-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.email-address {
  color: var(--text-muted);
}

.email-view-toggle {
  display: flex;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  overflow: hidden;
}

.btn-toggle-view {
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  background-color: var(--bg-surface);
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}

.btn-toggle-view.active {
  background-color: var(--primary);
  color: #ffffff;
}

.inspector-content-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  font-size: 13px;
  line-height: 1.6;
}

.email-html-render {
  font-family: inherit;
  color: var(--text-main);
  line-height: 1.6;
  word-break: break-word;
}

.email-html-render :deep(a),
:deep(.email-rendered-link) {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 2px;
  font-weight: 500;
  transition: color var(--transition-fast);
}

.email-html-render :deep(a:hover),
:deep(.email-rendered-link:hover) {
  color: var(--primary-hover, #6366f1);
  text-decoration: underline;
}

.email-html-render :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-xs);
}

.email-html-render :deep(table) {
  max-width: 100%;
}

.raw-code-block {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  white-space: pre-wrap;
  color: var(--text-secondary);
}

/* SUB-PANE 2: RESOLUTION & AI SUGGESTIONS PANEL */
.resolution-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background-color: var(--bg-card);
  padding: 16px 20px;
  overflow-y: auto;
  gap: 14px;
}

.ai-extraction-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ai-tags-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
  font-size: 12px;
}

.ai-tag-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ai-tag-item.full-width {
  grid-column: 1 / -1;
}

.ai-tag-label {
  color: var(--text-muted);
}

.badge-mini {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-xs);
}

.mode-tab-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mode-tab-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mode-tab-btn.active {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--primary);
}

.triage-form-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-helper-text {
  font-size: 11px;
  line-height: 1.4;
  margin-top: 2px;
}

.form-input,
.form-select,
.form-textarea {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text-main);
  outline: none;
  transition: border-color var(--transition-fast);
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: var(--primary);
}

.action-item-section {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  cursor: pointer;
}

.action-item-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

/* LINK APPLICATION LIST */
.app-search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
}

.search-input-with-icon {
  padding-left: 30px;
  width: 100%;
}

.app-select-cards-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 6px;
  background-color: var(--bg-surface);
}

.existing-app-option-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.existing-app-option-card:hover {
  background-color: var(--bg-card-hover);
}

.existing-app-option-card.selected {
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary);
}

.app-option-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-option-titles {
  display: flex;
  flex-direction: column;
  font-size: 12px;
}

.app-option-role {
  font-size: 11px;
  color: var(--text-muted);
}

.no-apps-found {
  padding: 12px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
}

/* RESOLUTION FOOTER BAR */
.resolution-footer-bar {
  margin-top: auto;
  padding-top: 10px;
}

.btn-submit-resolve {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  border-radius: var(--radius-sm);
}

.btn-advance-icon {
  margin-left: 4px;
}

/* SIDEBAR CLEANUP BAR */
.sidebar-cleanup-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-color);
}

.cleanup-controls-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cleanup-select {
  flex: 1;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs);
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-main);
  outline: none;
}

.cleanup-select:focus {
  border-color: var(--primary);
}

.btn-clean-now {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--danger, #ef4444);
  background-color: var(--danger-subtle, rgba(239, 68, 68, 0.1));
  border: 1px solid var(--danger-subtle, rgba(239, 68, 68, 0.2));
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-clean-now:hover:not(:disabled) {
  background-color: var(--danger, #ef4444);
  color: #ffffff;
}

.btn-clean-now:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cleanup-safety-hint {
  font-size: 10px;
  line-height: 1.35;
  color: var(--text-muted);
  margin: 0;
}

/* SIDEBAR LOAD MORE FOOTER */
.sidebar-load-more-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-top: 6px;
  border-top: 1px dashed var(--border-color);
}

.btn-load-more {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-load-more:hover:not(:disabled) {
  background-color: var(--bg-card-hover);
  border-color: var(--primary);
  color: var(--primary);
}

.btn-load-more:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-load-all {
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  background-color: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn-load-all:hover:not(:disabled) {
  background-color: var(--bg-card);
  color: var(--text-main);
  border-color: var(--border-color-focus);
}

/* CLEAR RESOLVED MODAL */
.clear-resolved-dialog {
  max-width: 520px;
  width: 90vw;
}

.icon-circle-danger {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: var(--danger-subtle, rgba(239, 68, 68, 0.12));
  color: var(--danger, #ef4444);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.clear-options-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.retention-radio-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-card);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.retention-radio-card:hover {
  background-color: var(--bg-card-hover);
  border-color: var(--border-color-focus);
}

.retention-radio-card.selected {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.radio-content {
  display: flex;
  flex-direction: column;
}

.radio-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.radio-desc {
  font-size: 11px;
  color: var(--text-muted);
}

@media (max-width: 1024px) {
  .staging-split-workspace {
    grid-template-columns: 300px 1fr;
  }
  .triage-body-columns {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
  .email-inspector-panel {
    border-right: none;
    border-bottom: 1px solid var(--border-color);
  }
}
</style>
