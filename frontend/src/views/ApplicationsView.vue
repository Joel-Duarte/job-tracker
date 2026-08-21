<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useUIStore } from '../stores/uiStore'
import DateTimePicker from '../components/common/DateTimePicker.vue'
import InterviewReaderModal from '../components/modals/InterviewReaderModal.vue'
import MatchAnalysisModal from '../components/modals/MatchAnalysisModal.vue'
import LogActivityModal from '../components/modals/LogActivityModal.vue'
import PostHireModal from '../components/modals/PostHireModal.vue'
import CompanyLogo from '../components/common/CompanyLogo.vue'
import {
  formatRelativeDate,
  normalizeWorkModel,
  formatSalaryRange,
} from '../utils/formatters'
import { getFitScores } from '../utils/fitScores'
import {
  Search,
  Kanban,
  Table as TableIcon,
  Filter,
  Building2,
  Calendar,
  Clock,
  FileText,
  DollarSign,
  XCircle,
  Award,
  Tag,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  SlidersHorizontal,
  Sparkles,
  Layers,
  ArrowUpDown,
  Trash2,
  X,
  Send,
  Loader2,
  GripVertical,
  Archive,
  RotateCcw,
  Ban,
  Briefcase,
  BookOpen,
  MessageSquare,
  ExternalLink,
  PenLine,
  MapPin,
  MoreHorizontal,
  MoreVertical,
  Trophy,
} from 'lucide-vue-next'

const pipelineCount = computed(() => {
  if (appStore.pipelineViewMode === 'active') return appStore.activeApplications.length
  if (appStore.pipelineViewMode === 'hired') return appStore.hiredApplications.length
  return appStore.archivedApplications.length
})

const pipelineCountLabel = computed(() => {
  if (appStore.pipelineViewMode === 'active') return 'Active'
  if (appStore.pipelineViewMode === 'hired') return 'Hired'
  return 'Archived'
})

const appStore = useApplicationsStore()
const uiStore = useUIStore()

// Dropdown Context Menu State (Teleported Floating Menu)
const activeMenuApp = ref(null)
const menuPosition = ref({ top: 0, left: 0, openUpward: false })

function toggleCardMenu(app, event) {
  if (event) {
    event.stopPropagation()
    event.preventDefault()
  }
  if (activeMenuApp.value?.id === app.id) {
    closeCardMenu()
    return
  }
  activeMenuApp.value = app

  const rect = event.currentTarget.getBoundingClientRect()
  const menuHeight = 230
  const menuWidth = 185
  const spaceBelow = window.innerHeight - rect.bottom
  const openUpward = spaceBelow < menuHeight

  const top = openUpward ? Math.max(10, rect.top - menuHeight - 4) : rect.bottom + 4
  const left = Math.min(window.innerWidth - menuWidth - 10, Math.max(10, rect.right - menuWidth))

  menuPosition.value = { top, left, openUpward }
}

function closeCardMenu() {
  activeMenuApp.value = null
}

function handleGlobalClick(e) {
  if (activeMenuApp.value && !e.target.closest('.card-teleport-menu') && !e.target.closest('.card-menu-trigger')) {
    closeCardMenu()
  }
}

function handleScrollOrResize() {
  if (activeMenuApp.value) {
    closeCardMenu()
  }
}

// Interview Guide Modal State

// Post Hire Modal State
const showPostHireModal = ref(false)
const lastHiredAppId = ref(null)

function handlePostHireClose() {
  showPostHireModal.value = false
  lastHiredAppId.value = null
}

const activeGuideAppId = ref(null)

function openInterviewGuide(appId) {
  uiStore.openDetail(appId, 'guide')
}


// Modal States
const isReaderModalOpen = ref(false)
const readerAppId = ref(null)
function openInterviewReaderModal(appId) {
  readerAppId.value = appId
  isReaderModalOpen.value = true
}

const isAnalysisModalOpen = ref(false)
const analysisAppId = ref(null)
function openMatchAnalysisModal(appId) {
  analysisAppId.value = appId
  isAnalysisModalOpen.value = true
}

const isLogModalOpen = ref(false)
const logAppId = ref(null)
function openLogActivityModal(appId) {
  logAppId.value = appId
  isLogModalOpen.value = true
}

// Drag & Drop State
const draggedApp = ref(null)
const dragOverCol = ref(null)

// Transition Modal State
const showTransitionModal = ref(false)
const transitionApp = ref(null)
const targetStatus = ref('')
const isSubmittingTransition = ref(false)
const transitionForm = ref({
  interview_stage: 'Technical / Coding Round',
  scheduled_at: '',
  offered_salary: null,
  currency: 'USD',
  offer_received_date: '',
  decision_deadline: '',
  rejection_date: '',
  rejection_reason: 'Resume / Initial Screen',
  notes: '',
})

watch(
  () => transitionForm.value.interview_stage,
  (newStage) => {
    if (newStage === 'Task Completed / Awaiting Response') {
      transitionForm.value.scheduled_at = ''
    }
  }
)

// Delete Modal State
const showDeleteModal = ref(false)
const appToDelete = ref(null)
const isDeleting = ref(false)

async function quickRejectApp(app) {
  try {
    await appStore.quickReject(app.id)
    uiStore.showToast(`Moved '${app.company?.name || 'Application'}' to Rejections Archive`, 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to reject application', 'error')
  }
}


async function quickWithdrawApp(app) {
  try {
    await appStore.quickWithdraw(app.id)
    uiStore.showToast(`Moved '${app.company?.name || 'Application'}' to Withdrawn Archive`, 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to withdraw application', 'error')
  }
}
async function restoreApp(app) {
  try {
    await appStore.restoreToActive(app.id, 'APPLIED')
    uiStore.showToast(`Restored '${app.company?.name || 'Application'}' to Active Pipeline`, 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to restore application', 'error')
  }
}

const INTERVIEW_STAGES = [
  'Interview Requested / Scheduling',
  'Recruiter Screen',
  'Technical / Coding Round',
  'Final / Hiring Manager Round',
  'Task Completed / Awaiting Response',
]

const REJECTION_REASONS = [
  'Resume / Initial Screen',
  'Assessment / Take-Home Test',
  'Technical Round Fit',
  'System Design / Culture Fit',
  'Offer Declined by Candidate',
  'Position Closed / Cancelled',
  'Ghosted / No Response',
  'Other',
]

onMounted(() => {
  appStore.fetchApplications()
  window.addEventListener('click', handleGlobalClick)
  window.addEventListener('scroll', handleScrollOrResize, true)
  window.addEventListener('resize', handleScrollOrResize)
})

onUnmounted(() => {
  if (appStore.searchQuery) {
    appStore.searchQuery = ''
  }
  window.removeEventListener('click', handleGlobalClick)
  window.removeEventListener('scroll', handleScrollOrResize, true)
  window.removeEventListener('resize', handleScrollOrResize)
})

function handleSearch(e) {
  appStore.searchQuery = e.target.value
  appStore.fetchApplications()
}

function clearSearch() {
  appStore.searchQuery = ''
  appStore.fetchApplications()
}

function handleStatusFilter(e) {
  appStore.selectedStatus = e.target.value
  appStore.fetchApplications()
}

function toggleActionRequired() {
  appStore.actionRequiredOnly = !appStore.actionRequiredOnly
  appStore.fetchApplications()
}

function formatDate(isoStr) {
  if (!isoStr) return '—'
  try {
    return new Date(isoStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return isoStr
  }
}

function getAppFitScores(app) {
  return getFitScores(app)
}

function getMatchScoreTierClass(score) {
  if (score === null || score === undefined) return ''
  const num = Number(score)
  if (num > 80) return 'match-tier-elite'
  if (num >= 60) return 'match-tier-high'
  if (num >= 40) return 'match-tier-medium'
  return 'match-tier-low'
}

function hasDetailedPhase(app) {
  return ['TECHNICAL_INTERVIEW', 'OFFER', 'REJECTED'].includes(app?.status)
}

function getAppSubPhaseLabel(app) {
  if (!app) return ''
  const status = app.status || 'APPLIED'
  const payload = app.latest_event?.raw_payload || {}

  if (status === 'TECHNICAL_INTERVIEW') {
    return payload.interview_stage || 'Interview Requested / Scheduling'
  }
  if (status === 'OFFER') {
    const sal = payload.offered_salary || app.job_posting?.salary_max || app.job_posting?.salary_min
    const curr = payload.currency || uiStore.defaultCurrency || 'USD'
    return sal ? `$${Number(sal).toLocaleString()} ${curr}` : 'Offer Package'
  }
  if (status === 'REJECTED') {
    return payload.rejection_reason || 'Rejection Notice'
  }
  if (status === 'ASSESSMENT') return 'AI Assessment'
  return 'Applied'
}

function getScheduledInterviewDate(app) {
  if (!app) return null
  if (app.scheduled_interview_at) return app.scheduled_interview_at
  const payload = app.latest_event?.raw_payload || {}
  if (payload.scheduled_at) return payload.scheduled_at
  if (app.status === 'TECHNICAL_INTERVIEW') {
    if (app.nearest_due_date) return app.nearest_due_date
    for (const act of app.action_items || []) {
      if (act.due_date && String(act.title).toLowerCase().includes('interview')) {
        return act.due_date
      }
    }
  }
  return null
}

function getAppMetadataLine(app) {
  if (!app) return ''
  const parts = []
  const salary = formatSalaryRange(app.salary_min, app.salary_max, app.currency)
  if (salary) parts.push(salary)

  const loc = app.location || app.match_analysis_payload?.location
  if (loc) parts.push(loc)

  const wm = normalizeWorkModel(app.work_model || app.match_analysis_payload?.work_model)
  if (wm) parts.push(wm)

  return parts.join(' · ')
}

function formatScheduledDateFriendly(app) {
  const dateStr = getScheduledInterviewDate(app)
  if (!dateStr) return ''
  return formatRelativeDate(dateStr, true)
}

function formatScheduledDate(app) {
  const dateStr = getScheduledInterviewDate(app)
  if (!dateStr) return ''
  return formatRelativeDate(dateStr, true)
}

function getScheduleUrgencyClass(app) {
  const dateStr = getScheduledInterviewDate(app)
  if (!dateStr) return 'date-yellow'
  try {
    const schedTime = new Date(dateStr).getTime()
    const nowTime = Date.now()
    const diffHours = (schedTime - nowTime) / (1000 * 60 * 60)
    if (diffHours >= 72) return 'date-green'
    if (diffHours > 24) return 'date-yellow'
    return 'date-red'
  } catch {
    return 'date-yellow'
  }
}

function formatAppSalary(app) {
  if (!app) return null
  return formatSalaryRange(app.salary_min, app.salary_max, app.currency)
}

function getDueDateStr(app) {
  if (!app) return null
  const payload = app.latest_event?.raw_payload || {}
  return app.nearest_due_date || payload.decision_deadline || payload.due_date || null
}

function formatDueDateFriendly(app) {
  const dateStr = getDueDateStr(app)
  if (!dateStr) return ''
  return formatRelativeDate(dateStr, false)
}

function getDueDate(app) {
  const dateStr = getDueDateStr(app)
  if (!dateStr) return null
  return formatRelativeDate(dateStr, false)
}

function isOverdue(app) {
  const dateStr = getDueDateStr(app)
  if (!dateStr) return false
  try {
    return new Date(dateStr).getTime() < Date.now()
  } catch {
    return false
  }
}

function getNextStatus(status) {
  if (status === 'APPLIED') return 'TECHNICAL_INTERVIEW'
  if (status === 'TECHNICAL_INTERVIEW') return 'OFFER'
  if (status === 'OFFER') return 'HIRED'
  return null
}

function advanceAppStage(app, event) {
  if (event) {
    event.stopPropagation()
    event.preventDefault()
  }
  const nextStatus = getNextStatus(app?.status)
  if (!nextStatus) return
  if (nextStatus === 'HIRED') {
    executeTransition(app.id, { status: 'HIRED' })
  } else {
    openTransitionModal(app, nextStatus)
  }
}

// Drag and Drop Handlers
function onDragStart(app, event) {
  draggedApp.value = app
  event.dataTransfer.setData('text/plain', app.id.toString())
  event.dataTransfer.effectAllowed = 'move'
}

function onDragEnd() {
  draggedApp.value = null
  dragOverCol.value = null
}

function onDragOver(colKey, event) {
  event.preventDefault()
  dragOverCol.value = colKey
}

function onDragLeave(colKey) {
  if (dragOverCol.value === colKey) {
    dragOverCol.value = null
  }
}

function onDrop(colKey, event) {
  event.preventDefault()
  dragOverCol.value = null
  if (!draggedApp.value) return

  const app = draggedApp.value
  if (app.status === colKey) {
    draggedApp.value = null
    return
  }

  if (['TECHNICAL_INTERVIEW', 'OFFER', 'REJECTED'].includes(colKey)) {
    openTransitionModal(app, colKey)
  } else {
    executeTransition(app.id, { status: colKey })
  }
  draggedApp.value = null
}

function openTransitionModal(app, colKey) {
  transitionApp.value = app
  targetStatus.value = colKey || app.status || 'APPLIED'
  const today = new Date().toISOString().substring(0, 10)
  const existingPayload = app.latest_event?.raw_payload || {}

  const isAlreadyOffer = app.status === 'OFFER'
  const initialCurrency = (isAlreadyOffer && existingPayload.currency)
    ? existingPayload.currency
    : (uiStore.defaultCurrency || 'USD')

  transitionForm.value = {
    interview_stage: existingPayload.interview_stage || 'Interview Requested / Scheduling',
    scheduled_at: existingPayload.scheduled_at ? existingPayload.scheduled_at.substring(0, 16) : '',
    offered_salary: existingPayload.offered_salary || app.job_posting?.salary_max || app.job_posting?.salary_min || null,
    currency: initialCurrency,
    offer_received_date: existingPayload.offer_received_date || today,
    decision_deadline: existingPayload.decision_deadline || '',
    rejection_date: existingPayload.rejection_date || today,
    rejection_reason: existingPayload.rejection_reason || 'Resume / Initial Screen',
    notes: '',
  }
  showTransitionModal.value = true
}

function getTransitionModalTitle() {
  const company = transitionApp.value?.company?.name || 'Application'
  const currentStatus = transitionApp.value?.status
  if (currentStatus === targetStatus.value) {
    if (targetStatus.value === 'OFFER') return `Edit Offer for ${company}`
    if (targetStatus.value === 'TECHNICAL_INTERVIEW') return `Update Interview Details for ${company}`
    return `Edit Application Details for ${company}`
  }
  return `Move ${company} to ${targetStatus.value ? targetStatus.value.replace('_', ' ') : 'Stage'}`
}

function handleStatusChange(app, newStatus) {
  if (!newStatus) return
  if (['TECHNICAL_INTERVIEW', 'OFFER', 'REJECTED'].includes(newStatus)) {
    openTransitionModal(app, newStatus)
  } else {
    executeTransition(app.id, { status: newStatus })
  }
}

async function executeTransition(appId, payload) {
  try {
    await appStore.transitionApplication(appId, payload)
    if (payload.status === 'HIRED') {
      lastHiredAppId.value = appId
      showPostHireModal.value = true
    } else {
      uiStore.showToast(`Application moved to ${payload.status}`, 'success')
    }
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function submitTransitionModal() {
  if (!transitionApp.value) return
  isSubmittingTransition.value = true
  try {
    const payload = {
      status: targetStatus.value,
      notes: transitionForm.value.notes || undefined,
    }
    if (targetStatus.value === 'TECHNICAL_INTERVIEW') {
      payload.interview_stage = transitionForm.value.interview_stage
      payload.scheduled_at = transitionForm.value.scheduled_at
        ? new Date(transitionForm.value.scheduled_at).toISOString()
        : undefined
    } else if (targetStatus.value === 'OFFER') {
      payload.offered_salary = transitionForm.value.offered_salary ? Number(transitionForm.value.offered_salary) : undefined
      payload.currency = transitionForm.value.currency
      payload.offer_received_date = transitionForm.value.offer_received_date || undefined
      payload.decision_deadline = transitionForm.value.decision_deadline || undefined
    } else if (targetStatus.value === 'REJECTED') {
      payload.rejection_reason = transitionForm.value.rejection_reason
      payload.rejection_date = transitionForm.value.rejection_date || undefined
    }

    await appStore.transitionApplication(transitionApp.value.id, payload)

    if (targetStatus.value === 'HIRED') {
      lastHiredAppId.value = transitionApp.value.id
      showTransitionModal.value = false
      showPostHireModal.value = true
    } else {
      uiStore.showToast(`Application moved to ${targetStatus.value}`, 'success')
      showTransitionModal.value = false
    }
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmittingTransition.value = false
  }
}

function openDeleteConfirm(app) {
  appToDelete.value = app
  showDeleteModal.value = true
}

async function confirmDelete() {
  if (!appToDelete.value) return
  isDeleting.value = true
  try {
    await appStore.deleteApplication(appToDelete.value.id)
    uiStore.showToast('Application deleted', 'info')
    showDeleteModal.value = false
    appToDelete.value = null
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <!-- Header & Controls Bar -->
    <div class="controls-bar">
      <!-- Search & Filters -->
      <div class="search-filter-group">
        <!-- Pipeline Mode Segmented Toggle -->
        <div class="pipeline-mode-toggle">
          <button
            class="pipeline-mode-btn"
            :class="{ active: appStore.pipelineViewMode === 'active' }"
            @click="appStore.pipelineViewMode = 'active'"
          >
            <Briefcase :size="14" />
            <span>Active Pipeline ({{ appStore.activeApplications.length }})</span>
          </button>
          <button
            class="pipeline-mode-btn"
            :class="{ active: appStore.pipelineViewMode === 'archive' }"
            @click="appStore.pipelineViewMode = 'archive'"
          >
            <Archive :size="14" />
            <span>Archived / Closed ({{ appStore.archivedApplications.length }})</span>
          </button>
          <button
            class="pipeline-mode-btn"
            :class="{ active: appStore.pipelineViewMode === 'hired' }"
            @click="appStore.pipelineViewMode = 'hired'"
          >
            <Trophy :size="14" />
            <span>Past Wins ({{ appStore.hiredApplications.length }})</span>
          </button>
        </div>

        <div class="search-input-wrapper" v-if="uiStore.enableEmbeddings">
          <Search :size="15" class="search-icon" />
          <input
            type="text"
            placeholder="Search company, role, or keywords..."
            :value="appStore.searchQuery"
            class="search-input"
            @input="handleSearch"
          />
          <button
            v-if="appStore.searchQuery"
            class="btn-clear-search"
            @click="clearSearch"
            title="Clear search"
          >
            <X :size="13" />
          </button>
        </div>

        <!-- Status Filter shown in Table view where columns don't separate statuses -->
        <select
          v-if="uiStore.viewMode === 'table' && appStore.pipelineViewMode === 'active'"
          :value="appStore.selectedStatus"
          class="filter-select"
          @change="handleStatusFilter"
        >
          <option value="">All Active Statuses</option>
          <option v-for="s in appStore.ACTIVE_STATUSES" :key="s.key" :value="s.key">
            {{ s.label }}
          </option>
        </select>

        <!-- Work Model Filter (All / Remote / Hybrid / On-site) -->
        <select
          v-model="appStore.selectedWorkModel"
          class="filter-select work-model-select"
          title="Filter by workplace arrangement"
        >
          <option value="">All Workplaces</option>
          <option value="Remote">🌐 Remote</option>
          <option value="Hybrid">🏢 Hybrid</option>
          <option value="On-site">📍 On-site</option>
        </select>

        <button
          v-if="appStore.pipelineViewMode === 'active'"
          class="btn btn-secondary filter-toggle-btn"
          :class="{ active: appStore.actionRequiredOnly }"
          @click="toggleActionRequired"
          title="Filter applications with pending tasks, unscheduled interviews, or deadlines"
        >
          <AlertCircle :size="14" />
          <span>Needs Action</span>
        </button>

        <!-- Match Fit % Filter with Quick Preset Chips 
        <div class="match-filter-container">
          <div class="match-input-box" :class="{ active: appStore.minMatchScore }">
            <Sparkles :size="13" class="match-sparkle-icon" />
            <span class="match-prefix">Min Fit:</span>
            <input
              type="number"
              min="0"
              max="100"
              step="5"
              placeholder="All"
              :value="appStore.minMatchScore ?? ''"
              @input="appStore.minMatchScore = $event.target.value !== '' ? Number($event.target.value) : null"
              class="match-number-input"
            />
            <span v-if="appStore.minMatchScore !== null" class="match-suffix">%</span>
            <button
              v-if="appStore.minMatchScore !== null"
              class="clear-match-btn"
              @click="appStore.minMatchScore = null"
              title="Clear match filter"
            >
              <X :size="11" />
            </button>
          </div>

          <div class="match-presets">
            <button
              v-for="preset in [40, 60, 80]"
              :key="preset"
              class="preset-chip"
              :class="{ active: appStore.minMatchScore === preset }"
              @click="appStore.minMatchScore = appStore.minMatchScore === preset ? null : preset"
              :title="`Filter jobs with >= ${preset}% match fit`"
            >
              {{ preset }}%+
            </button>
          </div>
        </div>
        -->
      </div>
      
      <!-- View Switcher & Total Count -->
      <div class="view-switch-group">
        <div class="total-counter">
          <span class="count-num">{{ pipelineCount }}</span>
          <span class="count-label">{{ pipelineCountLabel }}</span>
        </div>

        <div v-if="appStore.pipelineViewMode === 'active'" class="view-toggle">
          <button
            class="view-btn"
            :class="{ active: uiStore.viewMode === 'kanban' }"
            @click="uiStore.setViewMode('kanban')"
            title="Kanban Board View"
          >
            <Kanban :size="15" />
          </button>
          <button
            class="view-btn"
            :class="{ active: uiStore.viewMode === 'table' }"
            @click="uiStore.setViewMode('table')"
            title="Data Table View"
          >
            <TableIcon :size="15" />
          </button>
        </div>
      </div>
    </div>

    <!-- MAIN VIEW AREA -->
    <div class="content-wrapper">
      <!-- 1. ARCHIVE / REJECTIONS VIEW -->
      <div v-if="appStore.pipelineViewMode === 'archive'" class="archive-view-container animate-fade-in">
        <div v-if="appStore.archivedApplications.length === 0" class="empty-state-box">
          <Archive :size="40" class="empty-state-icon" />
          <h3 class="empty-state-title">No archived or rejected applications</h3>
          <p class="empty-state-desc">
            When you reject or conclude applications, they will be archived here safely without crowding your active board.
          </p>
        </div>

        <div v-else class="archive-table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Position</th>
                <th>Reason / Status</th>
                <th>Archived Date</th>
                <th>Match Fit</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="app in appStore.archivedApplications"
                :key="app.id"
                class="table-row"
                @click="uiStore.openDetail(app.id)"
              >
                <td class="cell-company">
                  <div class="company-cell-wrapper">
                    <CompanyLogo :name="app.company?.name" :domain="app.company?.domain" :size="18" />
                    <span class="company-name-bold">{{ app.company?.name || 'Company' }}</span>
                  </div>
                </td>

                <td class="cell-position">
                  <span class="position-title">{{ app.position || '—' }}</span>
                </td>

                <td class="cell-reason">
                  <span class="archive-reason-pill">
                    <span v-if="app.status === 'ARCHIVED'" class="status-badge status-badge--archived">Archived</span>
                    <span v-else-if="app.status === 'WITHDRAWN'" class="status-badge status-badge--withdrawn">Withdrawn</span>
                    <span v-else class="status-badge status-badge--rejected">Rejected</span>
                    <span class="reason-text">{{ app.latest_event?.raw_payload?.archive_reason || app.latest_event?.raw_payload?.rejection_reason || app.rejection_reason || 'Concluded' }}</span>
                  </span>
                </td>

                <td class="cell-date">
                  {{ formatDate(app.rejection_date || app.last_activity_at) }}
                </td>

                <td class="cell-match">
                  <div
                    class="dual-match-pills table-match-pills"
                    :title="`Algo Overlap: ${getAppFitScores(app).computedText} | AI Fit: ${getAppFitScores(app).aiText}`"
                  >
                    <span class="match-score-pill algo-pill">
                      Algo: {{ getAppFitScores(app).computedText }}
                    </span>
                    <span
                      class="match-score-pill ai-pill"
                      :class="getMatchScoreTierClass(getAppFitScores(app).aiScore)"
                    >
                      <Sparkles :size="10" class="match-pill-icon" />
                      <span>AI: {{ getAppFitScores(app).aiText }}</span>
                    </span>
                  </div>
                </td>

                <td class="text-right cell-actions" @click.stop>
                  <button
                    class="btn btn-secondary btn-sm"
                    title="Restore back to Active Pipeline (Applied)"
                    @click="restoreApp(app)"
                  >
                    <RotateCcw :size="13" />
                    <span>Restore</span>
                  </button>
                  <button
                    class="btn btn-ghost btn-sm"
                    @click="uiStore.openDetail(app.id)"
                  >
                    Details
                  </button>
                  <button
                    class="btn btn-danger-subtle btn-sm"
                    title="Permanently Delete"
                    @click="openDeleteConfirm(app)"
                  >
                    <Trash2 :size="13" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 1b. HIRED / PAST WINS VIEW -->
      <div v-if="appStore.pipelineViewMode === 'hired'" class="hired-view-container animate-fade-in">
        <div v-if="appStore.hiredApplications.length === 0" class="empty-state-box">
          <span class="empty-state-trophy">&#x1F3C6;</span>
          <h3 class="empty-state-title">No hired applications yet</h3>
          <p class="empty-state-desc">
            When you accept an offer and mark it as Hired, it will appear here as a past win.
          </p>
        </div>

        <div v-else class="hired-cards-grid">
          <div
            v-for="app in appStore.hiredApplications"
            :key="app.id"
            class="hired-card"
            @click="uiStore.openDetail(app.id)"
          >
            <div class="hired-card-header">
              <CompanyLogo :name="app.company?.name" :domain="app.company?.domain" :size="32" />
              <div class="hired-card-info">
                <span class="hired-company-name">{{ app.company?.name || 'Company' }}</span>
                <span class="hired-role">{{ app.position || 'Position' }}</span>
              </div>
              <span class="hired-badge">&#x1F3C6; Hired</span>
            </div>
            <div class="hired-card-meta">
              <span v-if="app.salary_min || app.salary_max" class="hired-salary">
                {{ formatSalaryRange(app.salary_min, app.salary_max, app.currency) }}
              </span>
              <span class="hired-date">{{ formatDate(app.last_activity_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. ACTIVE KANBAN VIEW (WITH DRAG & DROP) -->
      <div v-else-if="uiStore.viewMode === 'kanban'" class="kanban-board">
        <div
          v-for="col in appStore.ACTIVE_STATUSES"
          :key="col.key"
          class="kanban-column"
          :class="{ 'drag-over': dragOverCol === col.key }"
          @dragover="onDragOver(col.key, $event)"
          @dragleave="onDragLeave(col.key)"
          @drop="onDrop(col.key, $event)"
        >
          <div class="column-header">
            <div class="column-title-group">
              <span class="column-dot" :class="`dot-${col.color}`"></span>
              <span class="column-title">{{ col.label }}</span>
            </div>
            <span class="column-count">
              {{ appStore.kanbanColumns[col.key]?.length || 0 }}
            </span>
          </div>

          <div class="column-cards">
            <div
              v-for="app in appStore.kanbanColumns[col.key] || []"
              :key="app.id"
              class="application-card"
              :class="[{ 'is-dragging': draggedApp?.id === app.id, 'has-open-menu': activeMenuApp?.id === app.id }, app.has_action_required ? 'action-required-card' : '']"
              draggable="true"
              @dragstart="onDragStart(app, $event)"
              @dragend="onDragEnd"
              @click="uiStore.openDetail(app.id)"
            >
              <div class="card-header">
                <div class="company-name-tag">
                  <CompanyLogo :name="app.company?.name" :domain="app.company?.domain" :size="18" />
                  <span class="company-name-text">{{ app.company?.name || 'Company' }}</span>
                </div>

                <div class="card-header-actions" @click.stop>
                  <div class="card-hover-actions">
                    <!-- Assessment Dual Badges -->
                    <div
                      class="dual-match-pills card-match-pills"
                      :title="`Algo Overlap: ${getAppFitScores(app).computedText} | AI Fit: ${getAppFitScores(app).aiText} - View Assessment`"
                      @click="openMatchAnalysisModal(app.id)"
                    >
                      <span class="match-score-pill algo-pill">
                        Algo: {{ getAppFitScores(app).computedText }}
                      </span>
                      <span
                        class="match-score-pill ai-pill"
                        :class="getMatchScoreTierClass(getAppFitScores(app).aiScore)"
                      >
                        <Sparkles :size="10" class="match-pill-icon" />
                        <span>AI: {{ getAppFitScores(app).aiText }}</span>
                      </span>
                    </div>

                    <!-- Interview Guide Button (Generate / See Generated) -->
                    <button
                      class="card-hover-icon-btn"
                      :class="{ 'has-guide': app.has_interview_guide }"
                      :title="app.has_interview_guide ? 'Open Interview Guide Reader' : 'Generate Interview Guide'"
                      @click="app.has_interview_guide ? openInterviewReaderModal(app.id) : openInterviewGuide(app.id)"
                    >
                      <BookOpen :size="12" />
                    </button>
                  </div>

                  <!-- Card Context Menu Trigger (3-dot menu) -->
                  <div class="card-menu-container">
                    <button
                      class="card-menu-trigger"
                      :class="{ active: activeMenuApp?.id === app.id }"
                      title="More actions"
                      @click="toggleCardMenu(app, $event)"
                    >
                      <MoreHorizontal :size="14" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- Quick One-Click Advance Button (Middle-Right Side) -->
              <button
                v-if="getNextStatus(app.status) && app.status !== 'OFFER'"
                class="card-advance-btn"
                :title="`Advance to ${getNextStatus(app.status).replace('_', ' ')}`"
                @click.stop="advanceAppStage(app, $event)"
              >
                <ChevronRight :size="16" />
              </button>

              <!-- Position Title -->
              <div class="card-position">
                {{ app.position || 'Position Not Specified' }}
              </div>

              <!-- Clean Mid-Dot Metadata Line (No Pill Soup) -->
              <div v-if="getAppMetadataLine(app)" class="card-meta-line" @click.stop>
                {{ getAppMetadataLine(app) }}
              </div>

              <!-- Phase Detail Pill, Interview Date, & Due Date -->
              <div
                v-if="app.status !== 'APPLIED' || getScheduledInterviewDate(app) || getDueDateStr(app)"
                class="card-phase-row"
                @click.stop
              >
                <!-- Only show sub-phase button if not generic applied stage -->
                <button
                  v-if="app.status !== 'APPLIED'"
                  class="phase-detail-btn"
                  :class="`phase-${(app.status || 'applied').toLowerCase()}`"
                  @click="openTransitionModal(app, app.status)"
                  :title="`Click to edit stage: ${getAppSubPhaseLabel(app)}`"
                >
                  <span class="phase-detail-text">{{ getAppSubPhaseLabel(app) }}</span>
                  <SlidersHorizontal :size="11" class="phase-icon" />
                </button>

                <!-- Show Interview Scheduled Date if it exists -->
                <div
                  v-if="getScheduledInterviewDate(app)"
                  class="interview-scheduled-badge"
                  :class="getScheduleUrgencyClass(app)"
                  title="Scheduled Interview Date & Time"
                >
                  <Calendar :size="11" />
                  <span>{{ formatScheduledDateFriendly(app) }}</span>
                </div>

                <!-- Show Awaiting Response badge if task was completed -->
                <div
                  v-else-if="app.status === 'TECHNICAL_INTERVIEW' && getAppSubPhaseLabel(app) === 'Task Completed / Awaiting Response'"
                  class="awaiting-response-tag"
                  title="Action item completed - Awaiting company response"
                >
                  <CheckCircle2 :size="11" />
                  <span>Awaiting Reply</span>
                </div>

                <!-- Show Needs Scheduling Warning if in interview column but no date is set -->
                <button
                  v-else-if="app.status === 'TECHNICAL_INTERVIEW'"
                  class="scheduling-needed-tag"
                  @click="openTransitionModal(app, 'TECHNICAL_INTERVIEW')"
                  title="No interview date scheduled yet - Click to schedule"
                >
                  <Clock :size="11" />
                  <span>⚡ Schedule</span>
                </button>

                <!-- Show Due Date / Deadline ONLY if NO scheduled interview date (prevents duplicate info) -->
                <div
                  v-if="!getScheduledInterviewDate(app) && getDueDateStr(app)"
                  class="due-date-tag"
                  :class="{ overdue: isOverdue(app) }"
                  :title="`Task Deadline: ${getDueDate(app)}`"
                >
                  <Clock :size="11" />
                  <span>Due {{ formatDueDateFriendly(app) }}</span>
                </div>
              </div>

              <!-- Latest Event Summary Note (Compact) -->
              <div v-if="app.latest_event?.email_summary" class="card-summary">
                <span class="summary-prefix">{{ app.latest_event.email_event_type }}:</span>
                {{ app.latest_event.email_summary }}
              </div>

              <!-- Offer Actions (Hired / Withdrawn) -->
              <div v-if="app.status === 'OFFER'" class="offer-actions" @click.stop>
                <button
                  class="offer-action-btn btn-withdrawn"
                  @click="quickWithdrawApp(app)"
                  title="Decline Offer & Withdraw"
                >
                  <Ban :size="12" />
                  <span>Decline</span>
                </button>
                <button
                  class="offer-action-btn btn-hired"
                  @click="executeTransition(app.id, { status: 'HIRED' })"
                  title="Accept Offer & Mark Hired"
                >
                  <Trophy :size="12" />
                  <span>Hired</span>
                </button>
                
              </div>



            </div>

            <!-- Empty Column State -->
            <div
              v-if="!appStore.kanbanColumns[col.key]?.length"
              class="column-empty"
            >
              No applications in {{ col.label }}
            </div>
          </div>
        </div>
      </div>

      <!-- 3. ACTIVE TABLE VIEW -->
      <div v-else class="table-view-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Position</th>
              <th>Status & Phase</th>
              <th>Activity Date</th>
              <th>Action Required</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="app in appStore.activeApplications"
              :key="app.id"
              class="table-row"
              @click="uiStore.openDetail(app.id)"
            >
              <td class="cell-company">
                <div class="company-cell-wrapper">
                  <CompanyLogo :name="app.company?.name" :domain="app.company?.domain" :size="18" />
                  <span class="company-name-bold">{{ app.company?.name || 'Company' }}</span>
                </div>
              </td>

              <td class="cell-position">
                <div class="position-cell-wrapper">
                  <div class="position-title-row">
                    <span class="position-title">{{ app.position || '—' }}</span>
                    <div
                      class="dual-match-pills table-match-pills"
                      :title="`Algo Overlap: ${getAppFitScores(app).computedText} | AI Fit: ${getAppFitScores(app).aiText}`"
                      @click="openMatchAnalysisModal(app.id)"
                    >
                      <span class="match-score-pill algo-pill">
                        Algo: {{ getAppFitScores(app).computedText }}
                      </span>
                      <span
                        class="match-score-pill ai-pill"
                        :class="getMatchScoreTierClass(getAppFitScores(app).aiScore)"
                      >
                        <Sparkles :size="10" class="match-pill-icon" />
                        <span>AI: {{ getAppFitScores(app).aiText }}</span>
                      </span>
                    </div>
                  </div>
                  <div
                    v-if="getAppMetadataLine(app)"
                    class="table-meta-line"
                  >
                    {{ getAppMetadataLine(app) }}
                  </div>
                </div>
              </td>

              <td class="cell-status" @click.stop>
                <div class="table-phase-row">
                  <button
                    class="phase-detail-btn"
                    :class="`phase-${(app.status || 'applied').toLowerCase()}`"
                    @click="openTransitionModal(app, app.status)"
                    :title="`Click to edit stage: ${getAppSubPhaseLabel(app)}`"
                  >
                    <span class="phase-detail-text">{{ getAppSubPhaseLabel(app) }}</span>
                    <SlidersHorizontal :size="11" class="phase-icon" />
                  </button>

                  <div
                    v-if="getScheduledInterviewDate(app)"
                    class="interview-scheduled-badge"
                    :class="getScheduleUrgencyClass(app)"
                    title="Scheduled Interview Date & Time"
                  >
                    <Calendar :size="11" />
                    <span>{{ formatScheduledDateFriendly(app) }}</span>
                  </div>

                  <div
                    v-else-if="app.status === 'TECHNICAL_INTERVIEW' && getAppSubPhaseLabel(app) === 'Task Completed / Awaiting Response'"
                    class="awaiting-response-tag"
                    title="Action item completed - Awaiting company response"
                  >
                    <CheckCircle2 :size="11" />
                    <span>Awaiting Reply</span>
                  </div>

                  <button
                    v-else-if="app.status === 'TECHNICAL_INTERVIEW'"
                    class="scheduling-needed-tag"
                    @click="openTransitionModal(app, 'TECHNICAL_INTERVIEW')"
                    title="No interview date scheduled yet - Click to schedule"
                  >
                    <Clock :size="11" />
                    <span>⚡ Schedule</span>
                  </button>

                  <div
                    v-if="getDueDateStr(app)"
                    class="due-date-tag"
                    :class="{ overdue: isOverdue(app) }"
                    :title="`Task Deadline: ${getDueDate(app)}`"
                  >
                    <Clock :size="11" />
                    <span>Due {{ formatDueDateFriendly(app) }}</span>
                  </div>
                </div>
              </td>

              <td class="cell-date">
                {{ formatDate(app.last_activity_at || app.application_date) }}
              </td>

              <td>
                <span
                  v-if="app.has_action_required"
                  class="table-action-pill"
                >
                  <AlertCircle :size="12" />
                  <span>Required</span>
                </span>
                <span v-else class="text-muted text-xs">—</span>
              </td>

              <td class="text-right cell-actions" @click.stop>
                <button
                  v-if="['TECHNICAL_INTERVIEW', 'ONLINE_ASSESSMENT'].includes(app.status)"
                  class="btn btn-secondary btn-sm"
                  :class="{ 'btn-primary-subtle': app.has_interview_guide }"
                  title="Open AI Interview Preparation Guide"
                  @click="openInterviewGuide(app.id)"
                >
                  <BookOpen :size="13" />
                  <span>Prep</span>
                </button>
                <button
                  class="btn btn-secondary btn-sm"
                  title="Reject / Archive"
                  @click="openTransitionModal(app, 'REJECTED')"
                >
                  <Archive :size="13" />
                  <span>Reject</span>
                </button>
                <button
                  class="btn btn-secondary btn-sm"
                  @click="uiStore.openDetail(app.id)"
                >
                  Details
                </button>

              </td>
            </tr>

            <tr v-if="appStore.activeApplications.length === 0">
              <td colspan="6" class="table-empty">
                No active job applications found.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- DRAG-AND-DROP TRANSITION MODAL -->
    <Transition name="fade">
      <div v-if="showTransitionModal" class="inner-modal-backdrop" @click.self="showTransitionModal = false">
        <div class="inner-modal-box">
          <div class="inner-modal-header">
            <div class="inner-modal-title">
              <span>{{ getTransitionModalTitle() }}</span>
            </div>
            <button class="btn-close" @click="showTransitionModal = false">
              <X :size="16" />
            </button>
          </div>

          <div class="inner-modal-body">
            <!-- Interview Stage & Schedule -->
            <div v-if="targetStatus === 'TECHNICAL_INTERVIEW'" class="form-group-stack">
              <div class="form-group">
                <label class="form-label">Interview Phase / Sub-Stage</label>
                <select v-model="transitionForm.interview_stage" class="form-select">
                  <option v-for="stage in INTERVIEW_STAGES" :key="stage" :value="stage">
                    {{ stage }}
                  </option>
                </select>
              </div>

              <div
                v-if="transitionForm.interview_stage !== 'Task Completed / Awaiting Response'"
                class="form-group"
              >
                <label class="form-label">Scheduled Date & Time (Optional)</label>
                <DateTimePicker
                  v-model="transitionForm.scheduled_at"
                  type="datetime"
                  placeholder="Select scheduled date & time..."
                />
              </div>
              <div v-else class="stage-info-banner">
                <CheckCircle2 :size="15" class="info-icon" />
                <span>Marking as completed will clear scheduled dates and resolve pending action items for this application.</span>
              </div>
            </div>

            <!-- Offer Compensation & Deadlines -->
            <div v-if="targetStatus === 'OFFER'" class="form-group-stack offer-form-box">
              <div class="stage-section-header">
                <div class="stage-section-icon offer-icon">
                  <Award :size="16" />
                </div>
                <div class="stage-section-text">
                  <span class="stage-section-title">Offer Package Details</span>
                  <span class="stage-section-sub">Record compensation package and decision timelines.</span>
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Offered Compensation / Annual Base</label>
                <div class="salary-input-group">

                  <input
                    v-model="transitionForm.offered_salary"
                    type="number"
                    placeholder="e.g. 185000"
                    class="form-input salary-input"
                  />
                  <select v-model="transitionForm.currency" class="form-select currency-select">
                    <option v-for="c in uiStore.SUPPORTED_CURRENCIES" :key="c.code" :value="c.code">
                      {{ c.code }} ({{ c.symbol }})
                    </option>
                  </select>
                </div>
              </div>

              <div class="form-row-2">
                <div class="form-group">
                  <label class="form-label">Offer Received Date</label>
                  <DateTimePicker
                    v-model="transitionForm.offer_received_date"
                    type="date"
                    placeholder="Select received date..."
                  />
                </div>

                <div class="form-group">
                  <label class="form-label">Decision Deadline</label>
                  <DateTimePicker
                    v-model="transitionForm.decision_deadline"
                    type="date"
                    placeholder="Select decision deadline..."
                  />
                </div>
              </div>
            </div>

            <!-- Rejection Reason & Date -->
            <div v-if="targetStatus === 'REJECTED'" class="form-group-stack rejection-form-box">
              <div class="stage-section-header">
                <div class="stage-section-icon rejection-icon">
                  <XCircle :size="16" />
                </div>
                <div class="stage-section-text">
                  <span class="stage-section-title">Rejection Outcome</span>
                  <span class="stage-section-sub">Record the outcome and reason for future analytics.</span>
                </div>
              </div>

              <div class="form-row-2">
                <div class="form-group">
                  <label class="form-label">Rejection Notice Date</label>
                  <DateTimePicker
                    v-model="transitionForm.rejection_date"
                    type="date"
                    placeholder="Select notice date..."
                  />
                </div>

                <div class="form-group">
                  <label class="form-label">Primary Rejection Reason</label>
                  <select v-model="transitionForm.rejection_reason" class="form-select">
                    <option v-for="reason in REJECTION_REASONS" :key="reason" :value="reason">
                      {{ reason }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- Quick Reason Selection Chips -->
              <div class="quick-reasons-chips">
                <span class="chips-label">Quick select:</span>
                <button
                  v-for="r in ['Resume / Initial Screen', 'Technical Round Fit', 'System Design / Culture Fit', 'Offer Declined by Candidate', 'Position Closed / Cancelled', 'Ghosted / No Response']"
                  :key="r"
                  type="button"
                  class="reason-chip-btn"
                  :class="{ active: transitionForm.rejection_reason === r }"
                  @click="transitionForm.rejection_reason = r"
                >
                  {{ r }}
                </button>
              </div>
            </div>

            <!-- Optional Context / Notes -->
            <div class="form-group notes-form-group">
              <div class="notes-header-row">
                <label class="form-label notes-label">
                  <FileText :size="13" class="text-primary" />
                  <span>Context & Stage Notes (Optional)</span>
                </label>
                <span class="notes-char-count">{{ transitionForm.notes?.length || 0 }} chars</span>
              </div>
              <textarea
                v-model="transitionForm.notes"
                rows="3"
                placeholder="Log notes about interviewers, technical feedback, negotiation context, or key takeaways..."
                class="form-textarea"
              ></textarea>
            </div>
          </div>

          <div class="inner-modal-footer">
            <button class="btn btn-secondary" @click="showTransitionModal = false">Cancel</button>
            <button
              class="btn btn-primary"
              :disabled="isSubmittingTransition"
              @click="submitTransitionModal"
            >
              <Loader2 v-if="isSubmittingTransition" class="animate-spin" :size="15" />
              <Send v-else :size="15" />
              <span>Confirm & Record Event</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- DELETE CONFIRMATION MODAL -->
    <Transition name="fade">
      <div v-if="showDeleteModal" class="inner-modal-backdrop" @click.self="showDeleteModal = false">
        <div class="inner-modal-box modal-danger">
          <div class="inner-modal-header">
            <div class="inner-modal-title text-danger">
              <Trash2 :size="18" />
              <span>Delete Job Application?</span>
            </div>
            <button class="btn-close" @click="showDeleteModal = false">
              <X :size="16" />
            </button>
          </div>

          <div class="inner-modal-body">
            <p class="modal-warn-text">
              Are you sure you want to permanently delete the application for
              <strong>{{ appToDelete?.position }}</strong> at
              <strong>{{ appToDelete?.company?.name }}</strong>?
            </p>
            <p class="text-xs text-muted">
              This will permanently remove the application record, timeline events, and vector embeddings.
            </p>
          </div>

          <div class="inner-modal-footer">
            <button class="btn btn-secondary" @click="showDeleteModal = false">Cancel</button>
            <button
              class="btn btn-danger"
              :disabled="isDeleting"
              @click="confirmDelete"
            >
              <Loader2 v-if="isDeleting" class="animate-spin" :size="15" />
              <Trash2 v-else :size="15" />
              <span>{{ isDeleting ? 'Deleting...' : 'Permanently Delete' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
    <!-- NEW MODALS -->
    <InterviewReaderModal
      :is-open="isReaderModalOpen"
      :application-id="readerAppId"
      @close="isReaderModalOpen = false"
    />

    <MatchAnalysisModal
      :is-open="isAnalysisModalOpen"
      :application-id="analysisAppId"
      @close="isAnalysisModalOpen = false"
    />

    <LogActivityModal
      :is-open="isLogModalOpen"
      :application-id="logAppId"
      @close="isLogModalOpen = false"
      @updated="appStore.fetchApplications()"
    />

    <!-- Teleported Floating Card Dropdown Menu -->
    <Teleport to="body">
      <div
        v-if="activeMenuApp"
        class="card-teleport-menu animate-fade-in"
        :style="{ top: `${menuPosition.top}px`, left: `${menuPosition.left}px` }"
        @click.stop
      >
        <button
          v-if="activeMenuApp.match_score !== null || activeMenuApp.match_analysis_payload"
          class="menu-item"
          @click="openMatchAnalysisModal(activeMenuApp.id); closeCardMenu()"
        >
          <Sparkles :size="13" class="text-primary" />
          <span>View Assessment</span>
        </button>

        <button
          v-if="activeMenuApp.cover_letter_text || activeMenuApp.cover_letter_status === 'GENERATED'"
          class="menu-item"
          @click="uiStore.openCoverLetterModal(activeMenuApp.id); closeCardMenu()"
        >
          <FileText :size="13" class="text-primary" />
          <span>See Cover Letter</span>
        </button>
        <button
          v-else
          class="menu-item"
          @click="uiStore.openCoverLetterModal(activeMenuApp.id); closeCardMenu()"
        >
          <Sparkles :size="13" />
          <span>Draft Cover Letter</span>
        </button>

        <button
          v-if="activeMenuApp.has_interview_guide"
          class="menu-item"
          @click="openInterviewReaderModal(activeMenuApp.id); closeCardMenu()"
        >
          <BookOpen :size="13" class="text-primary" />
          <span>Open Guide Reader</span>
        </button>
        <button
          v-else-if="!['REJECTED', 'OFFER'].includes(activeMenuApp.status)"
          class="menu-item"
          @click="openInterviewGuide(activeMenuApp.id); closeCardMenu()"
        >
          <Sparkles :size="13" />
          <span>Generate Guide</span>
        </button>

        <button
          class="menu-item"
          @click="openLogActivityModal(activeMenuApp.id); closeCardMenu()"
        >
          <PenLine :size="13" />
          <span>Log Activity</span>
        </button>

        <button
          class="menu-item"
          @click="openTransitionModal(activeMenuApp, activeMenuApp.status); closeCardMenu()"
        >
          <SlidersHorizontal :size="13" />
          <span>Edit Stage &amp; Details</span>
        </button>

        <a
          v-if="activeMenuApp.job_posting?.source_url || activeMenuApp.job_url"
          :href="activeMenuApp.job_posting?.source_url || activeMenuApp.job_url"
          target="_blank"
          rel="noopener noreferrer"
          class="menu-item"
          @click="closeCardMenu()"
        >
          <ExternalLink :size="13" />
          <span>View Job Listing</span>
        </a>

        <div class="menu-divider"></div>

        <button
          class="menu-item text-warning"
          @click="openTransitionModal(activeMenuApp, 'REJECTED'); closeCardMenu()"
        >
          <Archive :size="13" />
          <span>Reject / Archive</span>
        </button>

      </div>
    </Teleport>

    <PostHireModal
      :visible="showPostHireModal"
      :hired-application-id="lastHiredAppId || 0"
      @close="handlePostHireClose"
    />
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--navbar-height));
  overflow: hidden;
}

.controls-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background-color: var(--bg-app);
  border-bottom: 1px solid var(--border-color);
  gap: 16px;
}

.search-filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

/* Pipeline Mode Segmented Control */
.pipeline-mode-toggle {
  display: flex;
  align-items: center;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}

.pipeline-mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: var(--radius-xs);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.pipeline-mode-btn:hover {
  color: var(--text-main);
  background-color: var(--bg-hover);
}

.pipeline-mode-btn.active {
  background-color: var(--primary);
  color: #fff;
}

/* Quick Reject Action Button */
.quick-reject-btn:hover {
  color: var(--status-rejected-text) !important;
  background-color: var(--status-rejected-bg) !important;
  border-color: var(--status-rejected-border) !important;
}

/* Archive & Rejections View */
.archive-view-container {
  padding: 24px;
  width: 100%;
  height: 100%;
  overflow-y: auto;
}

.archive-table-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.archive-reason-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
  font-size: 11px;
  font-weight: 600;
}

.search-input-wrapper {
  position: relative;
  width: 100%;
  max-width: 360px;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
}

.search-input {
  width: 100%;
  padding-left: 32px;
  padding-right: 30px;
  height: 34px;
}

.btn-clear-search {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: var(--text-muted);
  width: 20px;
  height: 20px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-clear-search:hover {
  color: var(--text-main);
  background-color: var(--bg-hover);
}

.filter-select {
  height: 34px;
  padding: 0 10px;
  font-size: 13px;
}

.filter-toggle-btn {
  height: 34px;
}
.filter-toggle-btn.active {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border-color: var(--status-interview-border);
  font-weight: 600;
  box-shadow: 0 0 0 1px var(--status-interview-border);
}

/* Match Score Filter in Toolbar */
.match-filter-container {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
  height: 34px;
}

.match-input-box {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.match-sparkle-icon {
  color: var(--primary);
}

.match-prefix {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.match-number-input {
  width: 42px;
  height: 24px;
  padding: 0 4px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  background-color: var(--bg-app);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-main);
}

.match-number-input:focus {
  border-color: var(--primary);
  outline: none;
}

.match-suffix {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.clear-match-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--bg-hover);
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  transition: all var(--transition-fast);
}

.clear-match-btn:hover {
  background: var(--status-rejected-bg);
  color: var(--status-rejected-text);
}

.match-presets {
  display: flex;
  align-items: center;
  gap: 4px;
  border-left: 1px solid var(--border-color);
  padding-left: 6px;
}

.preset-chip {
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-app);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.preset-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.preset-chip.active {
  background-color: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
}

/* Dual Match Pills in Cards & Tables */
.dual-match-pills {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.match-score-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  border: 1px solid transparent;
  font-family: var(--font-mono);
  white-space: nowrap;
}

.match-score-pill.algo-pill {
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  border-color: var(--border-color);
}

.position-cell-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-match-pill {
  font-size: 10px;
}

/* Tier 1: > 80% (Special Elite Emerald Glow) */
.match-score-pill.match-tier-elite {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border-color: var(--status-offer-border);
}

/* Tier 2: 60% - 80% (Indigo / Cyan High) */
.match-score-pill.match-tier-high {
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border-color: var(--status-applied-border);
}

/* Tier 3: 40% - 60% (Amber Medium) */
.match-score-pill.match-tier-medium {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border-color: var(--status-interview-border);
}

/* Tier 4: <= 40% (Slate Muted) */
.match-score-pill.match-tier-low {
  background-color: var(--bg-surface);
  color: var(--text-muted);
  border-color: var(--border-color);
}

.view-switch-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-counter {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.count-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.count-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.view-toggle {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.view-btn:hover {
  color: var(--text-main);
}

.view-btn.active {
  background-color: var(--bg-elevated);
  color: var(--primary);
}

.content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 16px 24px;
  min-height: 0;
}

/* KANBAN BOARD (Full-Height Responsive Grid) */
.kanban-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(320px, 1fr));
  gap: 16px;
  flex: 1;
  height: 100%;
  min-height: 0;
  align-items: stretch;
  width: 100%;
}

@media (max-width: 900px) {
  .kanban-board {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 8px;
    gap: 12px;
  }

  .kanban-column {
    flex: 0 0 85vw;
    max-width: 360px;
    scroll-snap-align: start;
  }
}

.kanban-column {
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.column-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-applied { background-color: var(--status-applied-text); }
.dot-assessment { background-color: var(--status-assessment-text); }
.dot-interview { background-color: var(--status-interview-text); }
.dot-offer { background-color: var(--status-offer-text); }
.dot-rejected { background-color: var(--status-rejected-text); }

.column-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 13px;
  color: var(--text-main);
}

.column-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background-color: var(--bg-surface);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.column-cards {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.application-card {
  background-color: var(--bg-card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
  padding: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--card-shadow);
  position: relative;
}

.application-card.has-open-menu {
  z-index: 50;
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
}

.card-advance-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-full);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  opacity: 0.6;
  transition: all var(--transition-fast);
  z-index: 5;
}

.application-card:hover .card-advance-btn {
  opacity: 1;
  border-color: var(--primary);
  color: var(--primary);
  background-color: var(--primary-subtle);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.card-advance-btn:hover {
  transform: translateY(-50%) scale(1.1);
  background-color: var(--primary) !important;
  color: #ffffff !important;
  border-color: var(--primary) !important;
}

.application-card:hover {
  background-color: var(--bg-card-hover);
  border-color: var(--card-hover-border);
  transform: translateY(-2px);
  box-shadow: var(--card-hover-shadow);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  position: relative;
}

.company-name-tag {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  min-width: 0;
  overflow: hidden;
}

.company-name-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.company-icon {
  color: var(--primary);
}

.card-position {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 3px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Single-line clean metadata text (No pill soup) */
.card-meta-line {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.table-meta-line {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Card & Table Phase Row */
.card-phase-row,
.table-phase-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.phase-detail-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  cursor: pointer;
  transition: all var(--transition-fast);
  max-width: 190px;
}

.phase-detail-btn:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.phase-detail-btn.phase-applied { color: var(--status-applied-text); border-color: var(--status-applied-border); background-color: var(--status-applied-bg); }
.phase-detail-btn.phase-interview, .phase-detail-btn.phase-technical_interview { color: var(--status-interview-text); border-color: var(--status-interview-border); background-color: var(--status-interview-bg); }
.phase-detail-btn.phase-offer { color: var(--status-offer-text); border-color: var(--status-offer-border); background-color: var(--status-offer-bg); }
.phase-detail-btn.phase-rejected { color: var(--status-rejected-text); border-color: var(--status-rejected-border); background-color: var(--status-rejected-bg); }
.phase-detail-btn.phase-assessment { color: var(--status-assessment-text); border-color: var(--status-assessment-border); background-color: var(--status-assessment-bg); }

.phase-detail-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.phase-icon {
  opacity: 0.7;
  flex-shrink: 0;
}

.interview-date-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
  font-family: var(--font-mono);
}

.due-date-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
  font-family: var(--font-mono);
}

.due-date-tag.overdue {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.awaiting-response-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
}

.scheduling-needed-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.scheduling-needed-tag:hover {
  background-color: var(--status-interview-border);
  border-color: var(--status-interview-text);
  transform: translateY(-1px);
}

.card-guide-row {
  margin-top: 6px;
  display: flex;
}

.btn-interview-guide-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-interview-guide-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
  background-color: var(--primary-subtle);
  transform: translateY(-1px);
}

.btn-interview-guide-chip.has-guide {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border-color: var(--primary-glow);
}

.btn-interview-guide-chip.has-guide:hover {
  border-color: var(--primary);
  box-shadow: 0 0 8px var(--primary-glow);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.card-action-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  color: var(--status-interview-text);
  background-color: var(--status-interview-bg);
  padding: 2px 6px;
  border-radius: var(--radius-full);
}

.card-arrow {
  color: var(--text-muted);
  margin-left: auto;
}

.column-empty {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  padding: 24px 0;
}

/* DATA TABLE */
.table-container {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.data-table th {
  background-color: var(--bg-sidebar);
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
}

.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-main);
}

.table-row {
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.table-row:hover {
  background-color: var(--bg-surface-hover);
}

.company-cell-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-logo-mini {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  color: var(--primary);
}

.company-name-bold {
  font-weight: 600;
}

.cell-position {
  font-weight: 500;
}

.cell-date {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

.table-action-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  font-size: 11px;
  font-weight: 600;
}

.cell-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.btn-danger-subtle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  background-color: transparent;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.btn-danger-subtle:hover {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.card-header-actions {
  display: flex;
  align-items: center;
  gap: 5px;
}

/* Card quick action buttons */
.card-hover-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 1;
  pointer-events: auto;
}

.card-hover-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.card-hover-icon-btn:hover {
  background-color: var(--bg-surface);
  color: var(--primary);
  border-color: var(--border-subtle);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.card-hover-icon-btn.has-guide {
  color: var(--primary);
}

/* Card Context Menu */
.card-menu-container {
  position: relative;
  display: inline-flex;
}

.card-menu-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0.5;
  transition: all var(--transition-fast);
}

.application-card:hover .card-menu-trigger,
.card-menu-trigger.active {
  opacity: 1;
}

.card-menu-trigger:hover,
.card-menu-trigger.active {
  background-color: var(--bg-surface);
  color: var(--text-main);
  border-color: var(--border-subtle);
}

.card-teleport-menu {
  position: fixed;
  z-index: 9999;
  min-width: 185px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 14px 35px -4px rgba(0, 0, 0, 0.4), 0 6px 14px -2px rgba(0, 0, 0, 0.25);
  padding: 5px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  backdrop-filter: blur(8px);
}

.card-teleport-menu .menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  width: 100%;
  text-decoration: none;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.card-teleport-menu .menu-item:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
}

.card-teleport-menu .menu-item.text-warning:hover {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
}

.card-teleport-menu .menu-item.text-danger:hover {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
}

.card-dropdown-menu .menu-divider {
  height: 1px;
  background-color: var(--border-subtle);
  margin: 3px 0;
}

.card-drag-hint {
  color: var(--text-muted);
  opacity: 0.4;
  margin-left: auto;
  cursor: grab;
}

.application-card {
  cursor: grab;
}

.application-card:active {
  cursor: grabbing;
}

.application-card.is-dragging {
  opacity: 0.4;
  transform: scale(0.98);
  border-style: dashed;
}

.kanban-column.drag-over {
  border-color: var(--primary);
  background-color: var(--bg-surface-hover);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.summary-prefix {
  font-weight: 600;
  color: var(--text-main);
  margin-right: 4px;
}

/* INNER MODALS */
.inner-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 500;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.inner-modal-box {
  width: 100%;
  max-width: 480px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  position: relative;
}

@media (max-width: 600px) {
  .inner-modal-box {
    max-width: 90vw;
  }

  .inner-modal-body {
    overflow-y: auto;
  }

  .controls-bar {
    flex-direction: column;
    align-items: stretch;
    padding: 12px 16px;
    gap: 12px;
  }

  .search-filter-group {
    flex-wrap: wrap;
    width: 100%;
  }

  .pipeline-mode-toggle {
    width: 100%;
    justify-content: space-between;
    overflow-x: auto;
  }

  .pipeline-mode-btn {
    flex: 1;
    justify-content: center;
  }

  .search-input-wrapper {
    max-width: 100%;
  }

  .view-switch-group {
    justify-content: space-between;
    width: 100%;
  }

  .content-wrapper {
    padding: 12px 16px;
  }

  .form-row-2 {
    grid-template-columns: 1fr;
  }
}

.inner-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.inner-modal-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 15px;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.inner-modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.inner-modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
}

.salary-input-row {
  display: flex;
  gap: 8px;
}

.currency-select {
  width: 120px;
}

.modal-warn-text {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-main);
  margin-bottom: 8px;
}

.form-group-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  box-sizing: border-box;
}

.form-row-2 .form-group {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.notes-form-group {
  margin-top: 4px;
}

.notes-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.notes-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.notes-char-count {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

/* Offer & Rejection Boxes */
.offer-form-box {
  background-color: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
  border-radius: var(--radius-md);
  padding: 14px;
}

.rejection-form-box {
  background-color: var(--status-rejected-bg);
  border: 1px solid var(--status-rejected-border);
  border-radius: var(--radius-md);
  padding: 14px;
}

.stage-info-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.stage-info-banner .info-icon {
  color: var(--success);
  flex-shrink: 0;
}

.stage-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.stage-section-icon {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stage-section-icon.offer-icon {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
}

.stage-section-icon.rejection-icon {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
}

.stage-section-text {
  display: flex;
  flex-direction: column;
}

.stage-section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.stage-section-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.salary-input-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.currency-prefix-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.salary-input {
  flex: 1;
}

.currency-select {
  width: 130px;
  flex-shrink: 0;
}

.quick-reasons-chips {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.chips-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.reason-chip-btn {
  padding: 3px 7px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.reason-chip-btn:hover {
  border-color: var(--status-rejected-border);
  color: var(--text-main);
}

.reason-chip-btn.active {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
  font-weight: 600;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.card-actions-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.btn-action-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 10px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.btn-action-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
  background-color: var(--primary-subtle);
  transform: translateY(-1px);
}

.btn-guide-split-group {
  display: inline-flex;
  align-items: stretch;
  border-radius: var(--radius-sm);
  border: 1px solid var(--primary-glow);
  background-color: var(--primary-subtle);
  overflow: hidden;
  transition: all var(--transition-fast);
}

.btn-guide-split-group:hover {
  box-shadow: 0 0 8px var(--primary-glow);
  border-color: var(--primary);
  transform: translateY(-1px);
}

.btn-guide-split-main {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  font-size: 10px;
  font-weight: 600;
  background: transparent;
  color: var(--primary);
  border: none;
  border-right: 1px solid rgba(99, 102, 241, 0.25);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.btn-guide-split-main:hover {
  background-color: rgba(99, 102, 241, 0.15);
}

.btn-guide-split-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 6px;
  background: transparent;
  color: var(--primary);
  border: none;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.btn-guide-split-action:hover {
  background-color: rgba(99, 102, 241, 0.25);
}

.interview-scheduled-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  font-family: var(--font-mono);
  user-select: none;
}

.interview-scheduled-badge.date-green {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.interview-scheduled-badge.date-yellow {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
}

.interview-scheduled-badge.date-red {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.action-required-card {
  border-left: 3px solid var(--status-rejected-border);
}

.work-model-select {
  min-width: 140px;
}

.card-meta-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  margin-bottom: 2px;
}

.table-meta-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.position-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-meta-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  line-height: 1.4;
}

.card-meta-tag.salary-tag {
  color: var(--status-offer-text);
  background-color: var(--status-offer-bg);
  border-color: var(--status-offer-border);
  font-weight: 600;
}

.card-meta-tag.workmodel-tag {
  font-family: var(--font-mono);
  font-size: 9.5px;
  text-transform: uppercase;
}

.card-meta-tag.location-tag {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Hired / Past Wins View */
.hired-view-container { padding: 1.5rem 0; }

.hired-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.hired-card {
  background: var(--color-surface-elevated, hsl(0 0% 14%));
  border: 1px solid hsl(45 90% 50% / 0.2);
  border-radius: 14px;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
}

.hired-card:hover {
  border-color: hsl(45 90% 50% / 0.5);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px hsl(45 90% 50% / 0.1);
}

.hired-card-header {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.hired-card-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.hired-company-name {
  font-weight: 700;
  font-size: 1rem;
  color: var(--color-text-primary, #f5f5f5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hired-role {
  font-size: 0.8rem;
  color: var(--color-text-muted, #888);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hired-badge {
  font-size: 0.75rem;
  font-weight: 600;
  background: hsl(45 90% 50% / 0.15);
  color: hsl(45 90% 60%);
  padding: 0.25rem 0.625rem;
  border-radius: 100px;
  white-space: nowrap;
  border: 1px solid hsl(45 90% 50% / 0.25);
}

.hired-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--color-text-muted, #888);
}

.hired-salary { font-weight: 600; color: hsl(45 90% 60%); }
.empty-state-trophy { font-size: 2.5rem; }

.status-badge {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 100px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-right: 0.35rem;
}
.status-badge--rejected { background: hsl(0 70% 50% / 0.15); color: hsl(0 70% 60%); }
.status-badge--archived { background: hsl(220 40% 50% / 0.15); color: hsl(220 40% 60%); }
.status-badge--withdrawn { background: hsl(40 80% 50% / 0.15); color: hsl(40 80% 60%); }
.reason-text { color: var(--color-text-muted, #888); font-size: 0.8rem; }

/* Offer Actions Styles appended below */
.offer-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-subtle);
}

.offer-action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 0;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.btn-hired {
  background-color: rgba(250, 204, 21, 0.1);
  color: hsl(45 90% 50%);
  border-color: rgba(250, 204, 21, 0.2);
}

.btn-hired:hover {
  background-color: rgba(250, 204, 21, 0.2);
  border-color: rgba(250, 204, 21, 0.4);
}

.btn-withdrawn {
  background-color: rgba(251, 146, 60, 0.1);
  color: hsl(28 90% 60%);
  border-color: rgba(251, 146, 60, 0.2);
}

.btn-withdrawn:hover {
  background-color: rgba(251, 146, 60, 0.2);
  border-color: rgba(251, 146, 60, 0.4);
}

</style>
