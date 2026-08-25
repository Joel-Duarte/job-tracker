<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { useQueueStore } from '../stores/queueStore'
import PageHeader from '../components/common/PageHeader.vue'
import { getFitScores } from '../utils/fitScores'
import {
  Cpu,
  Layers,
  Sparkles,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Trash2,
  RefreshCw,
  ExternalLink,
  Filter,
  FileText,
  Briefcase,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Search,
  UserCheck,
  ArrowRight,
  SlidersHorizontal,
  RotateCcw,
  Edit3,
  Mail,
  ChevronDown,
  ChevronUp,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()
const queueStore = useQueueStore()

const isClearing = ref(false)
const retryingTaskIds = ref(new Set())
const selectedTaskIds = ref(new Set())
const statusFilter = ref('ALL') // 'ALL' | 'FAILED' | 'RUNNING' | 'PENDING' | 'COMPLETED'
const typeFilter = ref('ALL') // 'ALL' | 'JOB_ASSESSMENT' | 'CV_EXTRACTION' | 'EMBEDDING' | 'COVER_LETTER'
const searchQuery = ref('')
const showBulkDeleteConfirm = ref(false)
const isBulkActing = ref(false)

// Cancel Task Modal State
const showCancelConfirm = ref(false)
const activeCancelTask = ref(null)
const isCancelingTask = ref(false)

// Fix JD Modal State
const showFixJDModal = ref(false)
const activeFixJDTask = ref(null)
const fixJDRawText = ref('')
const fixJDJobUrl = ref('')
const isSubmittingFixJD = ref(false)

// Expandable Email Sync details
const expandedEmailDetails = ref(new Set())

function toggleEmailDetails(taskId) {
  const newSet = new Set(expandedEmailDetails.value)
  if (newSet.has(taskId)) {
    newSet.delete(taskId)
  } else {
    newSet.add(taskId)
  }
  expandedEmailDetails.value = newSet
}

const tasks = computed(() => queueStore.tasks)
const loading = computed(() => queueStore.loading)

const filteredTasks = computed(() => {
  return tasks.value.filter((t) => {
    // Status filter
    if (statusFilter.value === 'RUNNING' && t.status !== 'PROCESSING') return false
    if (statusFilter.value === 'PENDING' && t.status !== 'QUEUED') return false
    if (statusFilter.value === 'COMPLETED' && t.status !== 'COMPLETED') return false
    if (statusFilter.value === 'FAILED' && !['FAILED', 'CANCELLED'].includes(t.status)) return false

    // Type filter
    if (typeFilter.value !== 'ALL' && (t.task_type || 'JOB_ASSESSMENT') !== typeFilter.value) return false

    // Search query
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.toLowerCase()
      const titleMatch = (t.title_hint || '').toLowerCase().includes(q)
      const urlMatch = (t.job_url || '').toLowerCase().includes(q)
      const idMatch = String(t.id).includes(q)
      if (!titleMatch && !urlMatch && !idMatch) return false
    }

    return true
  })
})

const runningCount = computed(() => queueStore.runningCount)
const pendingCount = computed(() => queueStore.pendingCount)
const activeCount = computed(() => queueStore.activeCount)
const completedCount = computed(() => queueStore.completedCount)
const failedCount = computed(() => queueStore.failedCount)

const isAllSelected = computed(() => {
  if (filteredTasks.value.length === 0) return false
  return filteredTasks.value.every((t) => selectedTaskIds.value.has(t.id))
})

const isSomeSelected = computed(() => {
  return selectedTaskIds.value.size > 0 && !isAllSelected.value
})

const selectedFailedTasksCount = computed(() => {
  return filteredTasks.value.filter(
    (t) => selectedTaskIds.value.has(t.id) && ['FAILED', 'CANCELLED'].includes(t.status)
  ).length
})

// Auto-clear selection when filter or search changes
watch([statusFilter, typeFilter, searchQuery], () => {
  clearSelection()
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    clearSelection()
  } else {
    const newSet = new Set(selectedTaskIds.value)
    filteredTasks.value.forEach((t) => newSet.add(t.id))
    selectedTaskIds.value = newSet
  }
}

function toggleTaskSelection(taskId) {
  const newSet = new Set(selectedTaskIds.value)
  if (newSet.has(taskId)) {
    newSet.delete(taskId)
  } else {
    newSet.add(taskId)
  }
  selectedTaskIds.value = newSet
}

function clearSelection() {
  selectedTaskIds.value = new Set()
}

async function fetchTasks(silent = false) {
  await queueStore.fetchTasks(silent)
}

async function retryTask(taskId) {
  retryingTaskIds.value.add(taskId)
  try {
    await queueStore.retryTask(taskId)
  } catch (err) {
    // Error handled in store
  } finally {
    retryingTaskIds.value.delete(taskId)
  }
}

function isManualDescriptionEligible(task) {
  if (!task) return false
  if (['CV_EXTRACTION', 'EMBEDDING', 'COVER_LETTER'].includes(task.task_type)) return false
  if (!['FAILED', 'CANCELLED', 'ERROR'].includes(task.status)) return false
  const msg = (task.error_message || '').toUpperCase()
  return (
    msg.startsWith('NO_JOB_FOUND:') ||
    msg.startsWith('SCRAPE_FAILED:') ||
    msg.startsWith('INVALID_JOB_CONTENT:') ||
    task.stage === 'FETCHING' ||
    task.stage === 'SCRAPING' ||
    task.stage === 'EXTRACTING' ||
    !task.raw_text ||
    task.raw_text.trim().length === 0 ||
    Boolean(task.error_message)
  )
}

function openFixJDModal(task) {
  activeFixJDTask.value = task
  fixJDRawText.value = task.raw_text || ''
  fixJDJobUrl.value = task.job_url || ''
  showFixJDModal.value = true
}

async function submitFixJD() {
  if (!activeFixJDTask.value) return
  if (!fixJDRawText.value.trim()) {
    uiStore.showToast('Job description text cannot be empty', 'error')
    return
  }

  const taskId = activeFixJDTask.value.id
  isSubmittingFixJD.value = true
  try {
    await queueStore.fixJDEvaluation(taskId, {
      raw_text: fixJDRawText.value,
      job_url: fixJDJobUrl.value || null,
    })
    showFixJDModal.value = false
    activeFixJDTask.value = null
  } catch (err) {
    // Handled in store
  } finally {
    isSubmittingFixJD.value = false
  }
}

function handleDismissOrCancel(task) {
  if (['PROCESSING', 'QUEUED'].includes(task.status)) {
    activeCancelTask.value = task
    showCancelConfirm.value = true
  } else {
    deleteTask(task.id)
  }
}

async function confirmCancelTask() {
  if (!activeCancelTask.value) return
  const task = activeCancelTask.value
  const taskId = task.id

  isCancelingTask.value = true
  try {
    await queueStore.cancelTask(taskId)
    showCancelConfirm.value = false
    activeCancelTask.value = null
  } catch (err) {
    // Handled in store
  } finally {
    isCancelingTask.value = false
  }
}

async function deleteTask(taskId) {
  try {
    await queueStore.deleteTask(taskId)
    if (selectedTaskIds.value.has(taskId)) {
      const newSet = new Set(selectedTaskIds.value)
      newSet.delete(taskId)
      selectedTaskIds.value = newSet
    }
  } catch (err) {
    // Error handled in store
  }
}

async function bulkRetrySelected() {
  if (selectedTaskIds.value.size === 0) return
  isBulkActing.value = true
  const ids = Array.from(selectedTaskIds.value)
  try {
    await queueStore.bulkRetryTasks(ids)
    clearSelection()
  } catch (err) {
    // Error handled in store
  } finally {
    isBulkActing.value = false
  }
}

async function bulkDeleteSelected() {
  if (selectedTaskIds.value.size === 0) return
  isBulkActing.value = true
  const ids = Array.from(selectedTaskIds.value)
  try {
    await queueStore.bulkDeleteTasks(ids)
    showBulkDeleteConfirm.value = false
    clearSelection()
  } catch (err) {
    // Error handled in store
  } finally {
    isBulkActing.value = false
  }
}

async function clearCompleted() {
  isClearing.value = true
  try {
    await queueStore.clearCompletedTasks()
  } catch (err) {
    // Error handled in store
  } finally {
    isClearing.value = false
  }
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(() => {
  fetchTasks()
})
</script>

<template>
  <div class="page-container queue-page-layout">
    <!-- Standardized Page Header -->
    <PageHeader
      title="AI Processing Queue"
      subtitle="Real-time background execution queue for automated Job Lead evaluations and Candidate CV extractions."
      align="center"
    >
      <template #tabs>
        <!-- Centered Filters & Controls Bar -->
        <div class="header-controls-centered">
          <!-- Status Filter Pills -->
          <div class="tab-bar">
          <button
            class="tab-pill"
            :class="{ active: statusFilter === 'ALL' }"
            @click="statusFilter = 'ALL'"
          >
            <span>All</span>
            <span class="pill-badge">{{ tasks.length }}</span>
          </button>
          <button
            class="tab-pill"
            :class="{ active: statusFilter === 'FAILED' }"
            @click="statusFilter = 'FAILED'"
          >
            <AlertCircle v-if="failedCount > 0" :size="12" class="text-danger flex-shrink-0" />
            <span>Failed</span>
            <span class="pill-badge" :class="{ 'badge-failed-active': failedCount > 0 }">{{ failedCount }}</span>
          </button>
          <button
            class="tab-pill"
            :class="{ active: statusFilter === 'RUNNING' }"
            @click="statusFilter = 'RUNNING'"
          >
            <span class="live-dot" v-if="runningCount > 0"></span>
            <span>Running</span>
            <span class="pill-badge">{{ runningCount }}</span>
          </button>
          <button
            class="tab-pill"
            :class="{ active: statusFilter === 'PENDING' }"
            @click="statusFilter = 'PENDING'"
          >
            <span>Pending</span>
            <span class="pill-badge">{{ pendingCount }}</span>
          </button>
          <button
            class="tab-pill"
            :class="{ active: statusFilter === 'COMPLETED' }"
            @click="statusFilter = 'COMPLETED'"
          >
            <span>Completed</span>
            <span class="pill-badge">{{ completedCount }}</span>
          </button>
        </div>

        <!-- Task Type Switcher -->
        <div class="type-filter-group">
          <button
            class="type-pill"
            :class="{ active: typeFilter === 'ALL' }"
            @click="typeFilter = 'ALL'"
          >
            All Types
          </button>
          <button
            class="type-pill"
            :class="{ active: typeFilter === 'JOB_ASSESSMENT' }"
            @click="typeFilter = 'JOB_ASSESSMENT'"
          >
            <Briefcase :size="12" />
            <span>Job Leads</span>
          </button>
          <button
            class="type-pill"
            :class="{ active: typeFilter === 'CV_EXTRACTION' }"
            @click="typeFilter = 'CV_EXTRACTION'"
          >
            <UserCheck :size="12" />
            <span>CV Extractions</span>
          </button>
          <!-- NEW: Vector Embeddings Filter -->
          <button
            class="type-pill"
            :class="{ active: typeFilter === 'EMBEDDING' }"
            @click="typeFilter = 'EMBEDDING'"
          >
            <Layers :size="12" />
            <span>Vector Embeddings</span>
          </button>
          <button
            class="type-pill"
            :class="{ active: typeFilter === 'COVER_LETTER' }"
            @click="typeFilter = 'COVER_LETTER'"
          >
            <FileText :size="12" />
            <span>Cover Letters</span>
          </button>
          <button
            class="type-pill"
            :class="{ active: typeFilter === 'EMAIL_SYNC' }"
            @click="typeFilter = 'EMAIL_SYNC'"
          >
            <Mail :size="12" />
            <span>Email Sync</span>
          </button>
        </div>

        <!-- Actions: Search, Refresh, Clear Completed -->
        <div class="header-actions-row">
          <div class="search-input-box">
            <Search :size="13" class="search-icon text-muted" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search queue..."
              class="search-input"
            />
          </div>

          <button
            class="btn btn-secondary btn-sm"
            :disabled="loading"
            @click="fetchTasks()"
            title="Refresh Queue"
          >
            <RefreshCw :size="13" :class="{ 'animate-spin': loading }" />
          </button>

          <button
            class="btn btn-secondary btn-sm btn-clear"
            :disabled="isClearing || (completedCount === 0 && failedCount === 0)"
            @click="clearCompleted"
            title="Clear completed & failed tasks"
          >
            <Loader2 v-if="isClearing" class="animate-spin" :size="13" />
            <Trash2 v-else :size="13" />
            <span>Clear Completed</span>
          </button>
        </div>
      </div>
      </template>
    </PageHeader>

    <!-- Selection Control Sub-Bar -->
    <div v-if="filteredTasks.length > 0" class="selection-control-bar">
      <label class="select-all-label">
        <input
          type="checkbox"
          :checked="isAllSelected"
          :indeterminate="isSomeSelected"
          @change="toggleSelectAll"
          class="custom-checkbox"
        />
        <span>Select All Visible ({{ filteredTasks.length }})</span>
      </label>

      <span v-if="selectedTaskIds.size > 0" class="selected-count-badge">
        {{ selectedTaskIds.size }} selected
      </span>
    </div>

    <!-- Dynamic Sticky Bulk Action Toolbar -->
    <Transition name="slide-up">
      <div v-if="selectedTaskIds.size > 0" class="bulk-action-bar">
        <div class="bulk-info">
          <span class="bulk-count-pill">{{ selectedTaskIds.size }}</span>
          <span class="bulk-label">task{{ selectedTaskIds.size > 1 ? 's' : '' }} selected</span>
        </div>

        <div class="bulk-actions-group">
          <!-- Retry Selected -->
          <button
            class="btn btn-secondary btn-sm btn-bulk-retry"
            :disabled="isBulkActing || selectedFailedTasksCount === 0"
            @click="bulkRetrySelected"
            title="Retry failed tasks"
          >
            <Loader2 v-if="isBulkActing" class="animate-spin" :size="13" />
            <RotateCcw v-else :size="13" />
            <span>Retry Selected ({{ selectedFailedTasksCount }})</span>
          </button>

          <!-- Delete Selected -->
          <button
            class="btn btn-danger btn-sm btn-bulk-delete"
            :disabled="isBulkActing"
            @click="showBulkDeleteConfirm = true"
            title="Delete selected tasks"
          >
            <Trash2 :size="13" />
            <span>Delete Selected</span>
          </button>

          <!-- Clear Selection -->
          <button class="btn btn-ghost btn-sm" @click="clearSelection">
            Cancel
          </button>
        </div>
      </div>
    </Transition>

    <!-- Fix JD / Description Error Resolution Modal -->
    <div v-if="showFixJDModal" class="modal-backdrop" @click.self="showFixJDModal = false">
      <div class="modal-card animate-scale-in">
        <div class="modal-header">
          <Edit3 :size="18" class="text-primary flex-shrink-0" />
          <h3 class="modal-title">Provide / Fix Job Description</h3>
        </div>
        <div class="modal-body">
          <p class="modal-desc">
            Automated scraping was protected or incomplete. Paste the job description below to re-run AI evaluation.
          </p>

          <div class="form-group">
            <label class="form-label">Job Posting URL (Optional)</label>
            <input
              v-model="fixJDJobUrl"
              type="url"
              placeholder="https://company.com/careers/job"
              class="form-input"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Job Description Text *</label>
            <textarea
              v-model="fixJDRawText"
              rows="10"
              placeholder="Paste complete job description, requirements, responsibilities, and qualifications here..."
              class="form-textarea"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button
            class="btn btn-secondary btn-sm"
            :disabled="isSubmittingFixJD"
            @click="showFixJDModal = false"
          >
            Cancel
          </button>
          <button
            class="btn btn-primary btn-sm"
            :disabled="isSubmittingFixJD || !fixJDRawText.trim()"
            @click="submitFixJD"
          >
            <Loader2 v-if="isSubmittingFixJD" class="animate-spin" :size="13" />
            <RotateCcw v-else :size="13" />
            <span>Save &amp; Retry Evaluation</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Task Cancellation Confirmation Dialog Modal -->
    <div v-if="showCancelConfirm" class="modal-backdrop" @click.self="showCancelConfirm = false">
      <div class="modal-card animate-scale-in">
        <div class="modal-header">
          <AlertCircle :size="20" class="text-danger flex-shrink-0" />
          <h3 class="modal-title">Stop Running Task?</h3>
        </div>
        <div class="modal-body">
          <p>Are you sure you want to stop active task <strong>#{{ activeCancelTask?.id }}</strong> (<em>{{ activeCancelTask?.title_hint }}</em>)?</p>
          <p class="modal-subtext text-muted">The task will transition to CANCELLED status with error explanation and can be retried later.</p>
        </div>
        <div class="modal-footer">
          <button
            class="btn btn-secondary btn-sm"
            :disabled="isCancelingTask"
            @click="showCancelConfirm = false"
          >
            Cancel
          </button>
          <button
            class="btn btn-danger btn-sm"
            :disabled="isCancelingTask"
            @click="confirmCancelTask"
          >
            <Loader2 v-if="isCancelingTask" class="animate-spin" :size="13" />
            <XCircle v-else :size="13" />
            <span>Confirm Stop</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Bulk Delete Confirmation Dialog Modal -->
    <div v-if="showBulkDeleteConfirm" class="modal-backdrop" @click.self="showBulkDeleteConfirm = false">
      <div class="modal-card animate-scale-in">
        <div class="modal-header">
          <AlertCircle :size="20" class="text-danger flex-shrink-0" />
          <h3 class="modal-title">Confirm Bulk Task Deletion</h3>
        </div>
        <div class="modal-body">
          <p>Are you sure you want to delete <strong>{{ selectedTaskIds.size }}</strong> selected task{{ selectedTaskIds.size > 1 ? 's' : '' }}?</p>
          <p class="modal-subtext text-muted">Running/processing tasks will be safely skipped. This action cannot be undone.</p>
        </div>
        <div class="modal-footer">
          <button
            class="btn btn-secondary btn-sm"
            :disabled="isBulkActing"
            @click="showBulkDeleteConfirm = false"
          >
            Cancel
          </button>
          <button
            class="btn btn-danger btn-sm"
            :disabled="isBulkActing"
            @click="bulkDeleteSelected"
          >
            <Loader2 v-if="isBulkActing" class="animate-spin" :size="13" />
            <Trash2 v-else :size="13" />
            <span>Confirm Delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="queue-content-scroll">
      <!-- Empty State -->
      <div v-if="filteredTasks.length === 0" class="empty-state-box">
        <Clock :size="40" class="empty-state-icon" />
        <h3 class="empty-state-title">No tasks in queue</h3>
        <p class="empty-state-desc">
          {{ tasks.length === 0 ? 'Queue is currently idle. Ingest a job posting, sync an email account, or upload a CV to initiate processing.' : 'No tasks match your active filters.' }}
        </p>
      </div>

      <!-- Task Cards List -->
      <div v-else class="tasks-card-list">
        <div
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-card animate-fade-in"
          :class="[
            `task-card-${task.status.toLowerCase()}`,
            { 'task-card-selected': selectedTaskIds.has(task.id) }
          ]"
        >
          <!-- Task Card Header -->
          <div class="task-card-top">
            <div class="task-header-left">
              <input
                type="checkbox"
                :checked="selectedTaskIds.has(task.id)"
                @change="toggleTaskSelection(task.id)"
                class="custom-checkbox task-checkbox"
              />
              <span class="task-id-tag">#{{ task.id }}</span>
              <span
                class="task-type-tag"
                :class="{
                  'type-cv': task.task_type === 'CV_EXTRACTION',
                  'type-job': task.task_type === 'JOB_ASSESSMENT' || !task.task_type,
                  'type-embedding': task.task_type === 'EMBEDDING',
                  'type-cover-letter': task.task_type === 'COVER_LETTER',
                  'type-email-sync': task.task_type === 'EMAIL_SYNC' || task.task_type === 'EMAIL_INTAKE'
                }"
              >
                <component :is="task.task_type === 'CV_EXTRACTION' ? UserCheck : (task.task_type === 'EMBEDDING' ? Layers : (task.task_type === 'COVER_LETTER' ? FileText : (task.task_type === 'EMAIL_SYNC' || task.task_type === 'EMAIL_INTAKE' ? Mail : Briefcase)))" :size="12" />
                <span>{{ task.task_type === 'CV_EXTRACTION' ? 'CV Profile Extraction' : (task.task_type === 'EMBEDDING' ? 'Vector Embedding' : (task.task_type === 'COVER_LETTER' ? 'Cover Letter Generation' : (task.task_type === 'EMAIL_SYNC' || task.task_type === 'EMAIL_INTAKE' ? 'Email Sync' : 'Job Assessment'))) }}</span>
              </span>
              <span class="task-title-text" :title="task.title_hint || task.job_url">
                {{ task.title_hint || task.job_url || `Task #${task.id}` }}
              </span>
            </div>

            <div class="task-header-right">
              <!-- Retry Action for Failed / Cancelled Tasks -->
              <button
                v-if="['FAILED', 'CANCELLED'].includes(task.status)"
                class="btn btn-secondary btn-xs btn-retry-task"
                :disabled="retryingTaskIds.has(task.id)"
                @click="retryTask(task.id)"
                title="Retry task execution"
              >
                <Loader2 v-if="retryingTaskIds.has(task.id)" class="animate-spin" :size="12" />
                <RotateCcw v-else :size="12" />
                <span>Retry</span>
              </button>

              <!-- Live Status Pill -->
              <div class="status-badge-pill" :class="`pill-${task.status.toLowerCase()}`">
                <Loader2 v-if="task.status === 'PROCESSING'" class="animate-spin" :size="12" />
                <CheckCircle v-else-if="task.status === 'COMPLETED'" :size="12" />
                <AlertCircle v-else-if="['FAILED', 'CANCELLED'].includes(task.status)" :size="12" />
                <Clock v-else :size="12" />
                <span>{{ task.status }}</span>
              </div>

              <!-- Delete/Dismiss or Cancel Button -->
              <button
                class="btn-icon-dismiss"
                :title="['PROCESSING', 'QUEUED'].includes(task.status) ? 'Stop active task' : 'Dismiss task'"
                @click="handleDismissOrCancel(task)"
              >
                <XCircle v-if="['PROCESSING', 'QUEUED'].includes(task.status)" :size="13" class="text-danger" />
                <Trash2 v-else :size="13" />
              </button>
            </div>
          </div>

          <!-- URL / Source Bar if available -->
          <div v-if="task.job_url" class="task-source-row">
            <a :href="task.job_url" target="_blank" rel="noopener noreferrer" class="task-source-link">
              <ExternalLink :size="11" />
              <span>{{ task.job_url }}</span>
            </a>
          </div>

          <!-- DEDICATED PIPELINE STEPPERS -->
          <div class="task-pipeline-container">
            <!-- 1. JOB ASSESSMENT STEPPER (Conditional 5 or 6 Stages based on enableAutoCoverLetter) -->
            <div v-if="!['CV_EXTRACTION', 'EMBEDDING', 'COVER_LETTER', 'EMAIL_SYNC', 'EMAIL_INTAKE'].includes(task.task_type)" class="pipeline-stepper job-stepper">
              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'FETCHING',
                  done: ['EXTRACTING', 'MATCHING', 'ASSESSING', 'COVER_LETTER', 'SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">1</div>
                <span class="node-label">Scrape / Ingest</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'EXTRACTING',
                  done: ['MATCHING', 'ASSESSING', 'COVER_LETTER', 'SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">2</div>
                <span class="node-label">Extract Specs &amp; Skills</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'MATCHING',
                  done: ['ASSESSING', 'COVER_LETTER', 'SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">3</div>
                <span class="node-label">Match CV Overlap</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'ASSESSING',
                  done: ['COVER_LETTER', 'SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">4</div>
                <span class="node-label">Qualitative Fit</span>
              </div>

              <div
                v-if="uiStore.enableAutoCoverLetter"
                class="stepper-node"
                :class="{
                  active: task.stage === 'COVER_LETTER',
                  done: ['SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">5</div>
                <span class="node-label">Cover Letter</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'SAVING',
                  done: task.stage === 'COMPLETE' || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">{{ uiStore.enableAutoCoverLetter ? '6' : '5' }}</div>
                <span class="node-label">Saved</span>
              </div>
            </div>

            <!-- 2. CV EXTRACTION STEPPER (4 Stages) -->
            <div v-else-if="task.task_type === 'CV_EXTRACTION'" class="pipeline-stepper cv-stepper">
              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'SCRUBBING',
                  done: ['EXTRACTING', 'SAVING', 'COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">1</div>
                <span class="node-label">PII Scrubbing</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'EXTRACTING',
                  done: ['SAVING', 'COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">2</div>
                <span class="node-label">Extracting Skills</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'SAVING',
                  done: ['COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">3</div>
                <span class="node-label">Saving Profile</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  done: task.stage === 'COMPLETE' || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">4</div>
                <span class="node-label">CV Profile Ready</span>
              </div>
            </div>

            <!-- 3. EMBEDDING STEPPER (3 Stages) -->
            <div v-else-if="task.task_type === 'EMBEDDING'" class="pipeline-stepper embedding-stepper">
              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'QUEUED',
                  done: ['EMBEDDING', 'COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">1</div>
                <span class="node-label">Queued</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'EMBEDDING',
                  done: ['COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">2</div>
                <span class="node-label">Embedding Generation</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  done: task.stage === 'COMPLETE' || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">3</div>
                <span class="node-label">Vector Saved</span>
              </div>
            </div>

            <!-- 4. COVER LETTER STEPPER (3 Stages) -->
            <div v-else-if="task.task_type === 'COVER_LETTER'" class="pipeline-stepper cover-letter-stepper">
              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'QUEUED',
                  done: ['COVER_LETTER', 'GENERATING', 'COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">1</div>
                <span class="node-label">Queued</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: ['COVER_LETTER', 'GENERATING'].includes(task.stage),
                  done: task.stage === 'COMPLETE' || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">2</div>
                <span class="node-label">Drafting Cover Letter</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  done: task.stage === 'COMPLETE' || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">3</div>
                <span class="node-label">Cover Letter Ready</span>
              </div>
            </div>

            <!-- 5. EMAIL SYNC PROGRESS / SUMMARY -->
            <div v-else-if="task.task_type === 'EMAIL_SYNC' || task.task_type === 'EMAIL_INTAKE'" class="email-sync-progress-box">
              <div v-if="task.status === 'PROCESSING' || task.status === 'QUEUED'" class="email-sync-progress-container">
                <div class="email-sync-progress-header">
                  <span class="email-sync-step-label">
                    {{ task.stage && task.stage !== 'QUEUED' ? task.stage : 'Queued for email extraction...' }}
                  </span>
                  <span class="email-sync-pct-badge font-mono">
                    {{ task.result_json?.progress_pct !== undefined ? task.result_json.progress_pct : 0 }}%
                  </span>
                </div>
                <div class="email-sync-progress-bar-track">
                  <div
                    class="email-sync-progress-bar-fill"
                    :style="{ width: `${task.result_json?.progress_pct !== undefined ? task.result_json.progress_pct : 0}%` }"
                  ></div>
                </div>
                <div v-if="task.result_json?.current_subject" class="email-sync-current-subject">
                  <Mail :size="11" class="flex-shrink-0 text-primary" />
                  <span class="truncate">Current: {{ task.result_json.current_subject }}</span>
                </div>
              </div>

              <!-- Completed Summary Stats -->
              <div v-else-if="(task.status === 'COMPLETED' || task.status === 'FAILED') && task.result_json" class="email-sync-summary-section">
                <div class="email-sync-summary-grid">
                  <div class="email-summary-stat">
                    <span class="stat-num">{{ task.result_json.total_emails || 0 }}</span>
                    <span class="stat-lbl">Emails Processed</span>
                  </div>
                  <div class="email-summary-stat" v-if="task.result_json.applications_count">
                    <span class="stat-num text-success">{{ task.result_json.applications_count }}</span>
                    <span class="stat-lbl">Apps Created/Updated</span>
                  </div>
                  <div class="email-summary-stat" v-if="task.result_json.events_count">
                    <span class="stat-num text-primary">{{ task.result_json.events_count }}</span>
                    <span class="stat-lbl">Events Logged</span>
                  </div>
                  <div class="email-summary-stat" v-if="task.result_json.staged_count">
                    <span class="stat-num text-warning">{{ task.result_json.staged_count }}</span>
                    <span class="stat-lbl">Staged for Review</span>
                  </div>
                  <div class="email-summary-stat" v-if="task.result_json.skipped_duplicates">
                    <span class="stat-num text-muted">{{ task.result_json.skipped_duplicates }}</span>
                    <span class="stat-lbl">Duplicates Skipped</span>
                  </div>
                  <div class="email-summary-stat error-stat" v-if="task.result_json.failed_count">
                    <span class="stat-num text-danger">{{ task.result_json.failed_count }}</span>
                    <span class="stat-lbl">Failed</span>
                  </div>
                </div>

                <!-- Toggle Email Details Button -->
                <div v-if="task.result_json.details && task.result_json.details.length > 0" class="email-details-toggle-row">
                  <button
                    type="button"
                    class="btn btn-secondary btn-xs"
                    @click="toggleEmailDetails(task.id)"
                  >
                    <ChevronDown v-if="!expandedEmailDetails.has(task.id)" :size="12" />
                    <ChevronUp v-else :size="12" />
                    <span>{{ expandedEmailDetails.has(task.id) ? 'Hide' : 'View' }} Processed Emails ({{ task.result_json.details.length }})</span>
                  </button>
                </div>

                <!-- Expandable Details List -->
                <div v-if="expandedEmailDetails.has(task.id) && task.result_json.details" class="email-details-list">
                  <div
                    v-for="(item, idx) in task.result_json.details"
                    :key="idx"
                    class="email-detail-card"
                    :class="`detail-status-${item.status}`"
                  >
                    <div class="detail-top">
                      <span class="detail-badge" :class="`badge-${item.status}`">
                        {{ item.status === 'application_committed' ? 'Application Updated' : (item.status === 'staged' ? 'Staged' : (item.status === 'event_logged' ? 'Event Logged' : (item.status === 'skipped' ? 'Skipped (Duplicate)' : 'Failed'))) }}
                      </span>
                      <span class="detail-subject truncate" :title="item.subject">{{ item.subject || 'No Subject' }}</span>
                    </div>
                    <div class="detail-subtext text-xs">
                      <span v-if="item.company" class="font-medium text-primary">{{ item.company }}</span>
                      <span v-if="item.company && item.position"> • </span>
                      <span v-if="item.position" class="text-secondary">{{ item.position }}</span>
                      <span v-if="item.summary" class="detail-summary text-muted"> — {{ item.summary }}</span>
                      <span v-if="item.error" class="text-danger font-mono text-xs">Error: {{ item.error }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Error Alert Banner with Provide/Edit Description & Retry Actions -->
          <div v-if="task.error_message" class="task-error-box">
            <div class="error-msg-left">
              <AlertCircle :size="14" class="text-danger flex-shrink-0" />
              <span>{{ task.error_message }}</span>
            </div>
            <div class="error-actions-right">
              <!-- Manual Description Action for Scraping/Keyword Failures -->
              <button
                v-if="isManualDescriptionEligible(task)"
                class="btn btn-primary btn-xs btn-fix-jd"
                @click="openFixJDModal(task)"
                :title="task.raw_text && task.raw_text.trim() ? 'Manually edit the job description text' : 'Manually supply the job description text'"
              >
                <Edit3 :size="12" />
                <span>{{ task.raw_text && task.raw_text.trim() ? 'Edit Job Description' : 'Provide Description' }}</span>
              </button>
              <button
                class="btn btn-secondary btn-xs btn-retry-error"
                :disabled="retryingTaskIds.has(task.id)"
                @click="retryTask(task.id)"
              >
                <Loader2 v-if="retryingTaskIds.has(task.id)" class="animate-spin" :size="12" />
                <RotateCcw v-else :size="12" />
                <span>Retry Execution</span>
              </button>
            </div>
          </div>

          <!-- Result Footer & Contextual Actions -->
          <div v-else-if="task.status === 'COMPLETED' && task.result_json" class="task-card-footer">
            <!-- Job Assessment Context -->
            <template v-if="!['CV_EXTRACTION', 'EMBEDDING', 'COVER_LETTER', 'EMAIL_SYNC', 'EMAIL_INTAKE'].includes(task.task_type)">
              <div class="footer-left">
                <span class="score-badge algo-score-badge">
                  Algo: {{ getFitScores(task.result_json).computedText }}
                </span>
                <span class="score-badge ai-score-badge">
                  AI: {{ getFitScores(task.result_json).aiText }}
                </span>
                <span class="footer-meta-text">
                  {{ task.result_json.company || 'Company' }} • {{ task.result_json.position || 'Position' }}
                </span>
              </div>
            </template>

            <!-- CV Extraction Context -->
            <template v-else-if="task.task_type === 'CV_EXTRACTION'">
              <div class="footer-left">
                <span class="badge-cv-ready">
                  <ShieldCheck :size="12" />
                  <span>Profile Scrubbed &amp; Updated</span>
                </span>
                <span v-if="task.result_json.extracted_skills_count" class="footer-meta-text">
                  {{ task.result_json.extracted_skills_count }} skills • {{ task.result_json.years_of_experience || 0 }} yrs exp
                </span>
              </div>

              <div class="footer-right">
                <router-link
                  to="/profile"
                  class="btn btn-primary btn-xs"
                >
                  <UserCheck :size="12" />
                  <span>View Profile &rarr;</span>
                </router-link>
              </div>
            </template>
            <!-- Embedding Context -->
            <template v-else-if="task.task_type === 'EMBEDDING'">
              <div class="footer-left">
                <span class="badge-cv-ready">
                  <Layers :size="12" />
                  <span>Vector Embedding Generated</span>
                </span>
              </div>
            </template>

            <!-- Cover Letter Context -->
            <template v-else-if="task.task_type === 'COVER_LETTER'">
              <div class="footer-left">
                <span class="badge-cv-ready">
                  <FileText :size="12" />
                  <span>Cover Letter {{ task.result_json.cover_letter_status === 'SKIPPED' ? 'Skipped' : 'Drafted' }}</span>
                </span>
                <span v-if="task.result_json.company" class="footer-meta-text">
                  {{ task.result_json.company }} • {{ task.result_json.position || 'Position' }}
                </span>
              </div>
            </template>

            <!-- Email Sync Context -->
            <template v-else-if="task.task_type === 'EMAIL_SYNC' || task.task_type === 'EMAIL_INTAKE'">
              <div class="footer-left">
                <span class="badge-cv-ready">
                  <Mail :size="12" />
                  <span>Email Sync Complete • {{ task.result_json.total_emails || 0 }} emails</span>
                </span>
                <span v-if="task.result_json.applications_count" class="footer-meta-text">
                  {{ task.result_json.applications_count }} application(s) updated
                </span>
              </div>
              <div class="footer-right flex items-center gap-2">
                <router-link
                  v-if="task.result_json.staged_count"
                  to="/staging"
                  class="btn btn-warning btn-xs"
                >
                  <span>Review Staging ({{ task.result_json.staged_count }}) &rarr;</span>
                </router-link>
                <router-link
                  to="/applications"
                  class="btn btn-primary btn-xs"
                >
                  <span>View Board &rarr;</span>
                </router-link>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.queue-page-layout {
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
  min-height: calc(100vh - var(--navbar-height));
  width: 100%;
}

.header-controls-centered {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
  width: 100%;
  max-width: 1100px;
}

/* Status Tab Bar Pills */
.tab-bar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  padding: 3px 4px;
}

.tab-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-pill:hover {
  color: var(--text-main);
}

.tab-pill.active {
  background-color: var(--primary);
  color: #ffffff;
  font-weight: 600;
}

.pill-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: var(--radius-full);
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

.badge-failed-active {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.tab-pill.active .pill-badge {
  background-color: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

/* Selection Control Bar */
.selection-control-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 900px;
  margin: 12px auto 0;
  padding: 0 4px;
}

.select-all-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}

.custom-checkbox {
  width: 15px;
  height: 15px;
  accent-color: var(--primary);
  cursor: pointer;
}

.selected-count-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--primary);
  background-color: var(--primary-subtle);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

/* Floating / Sticky Bulk Action Toolbar */
.bulk-action-bar {
  position: sticky;
  top: 10px;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 900px;
  margin: 12px auto;
  padding: 10px 18px;
  background-color: var(--bg-card);
  border: 1px solid var(--primary-glow);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border-radius: var(--radius-full);
  backdrop-filter: blur(8px);
}

.bulk-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bulk-count-pill {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  background-color: var(--primary);
  color: #ffffff;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.bulk-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.bulk-actions-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-bulk-retry {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-bulk-delete {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-clear-selection {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* Modal Styling */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  backdrop-filter: blur(4px);
}

.modal-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.modal-body {
  font-size: 13px;
  color: var(--text-main);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.modal-subtext {
  font-size: 12px;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.task-card-selected {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.task-checkbox {
  margin-right: 2px;
}

/* Transitions */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.25s ease-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #ffffff;
  box-shadow: 0 0 6px rgba(255, 255, 255, 0.8);
  animation: pulse-ring 1.5s infinite;
}

/* Task Type Switcher */
.type-filter-group {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  padding: 3px;
}

.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.type-pill:hover {
  color: var(--text-main);
}

.type-pill.active {
  background-color: var(--bg-card);
  color: var(--primary);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

/* Header Actions Row */
.header-actions-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.search-input-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 9px;
  pointer-events: none;
}

.search-input {
  padding: 5px 10px 5px 28px;
  font-size: 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  width: 170px;
  transition: all var(--transition-fast);
}

.search-input:focus {
  width: 210px;
  border-color: var(--primary);
  outline: none;
}

.btn-clear {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

/* Content Area */
.queue-content-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  scrollbar-gutter: stable;
}

.tasks-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 900px;
  margin: 0 auto;
}

.task-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all var(--transition-fast);
}

.task-card.task-card-processing {
  border-color: var(--primary-glow);
  box-shadow: 0 0 12px var(--primary-subtle);
}

.task-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-id-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.task-type-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.task-type-tag.type-job {
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
}

.task-type-tag.type-cv {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.task-type-tag.type-embedding {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.task-type-tag.type-cover-letter {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
}

.task-type-tag.type-email-sync {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.email-sync-progress-box {
  width: 100%;
  padding: 4px 0;
}

.email-sync-progress-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.email-sync-progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.email-sync-step-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.email-sync-pct-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.email-sync-progress-bar-track {
  width: 100%;
  height: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.email-sync-progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--primary-hover, var(--primary)));
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.email-sync-current-subject {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.email-sync-summary-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.email-sync-summary-grid {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.email-summary-stat {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 11px;
}

.email-summary-stat.error-stat {
  border-color: rgba(239, 68, 68, 0.4);
  background-color: rgba(239, 68, 68, 0.05);
}

.email-summary-stat .stat-num {
  font-weight: 700;
  font-family: var(--font-mono);
}

.email-summary-stat .stat-lbl {
  color: var(--text-secondary);
}

.email-details-toggle-row {
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.email-details-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 260px;
  overflow-y: auto;
  padding: 10px;
  background-color: var(--bg-base, #0d1117);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-top: 4px;
}

.email-detail-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.detail-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.detail-badge.badge-application_committed {
  background-color: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.detail-badge.badge-staged {
  background-color: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.detail-badge.badge-event_logged {
  background-color: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.detail-badge.badge-skipped {
  background-color: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.detail-badge.badge-error {
  background-color: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.detail-subject {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-main);
}

.detail-subtext {
  color: var(--text-secondary);
  line-height: 1.4;
}

.task-title-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.task-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
}

.pill-processing {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.pill-completed {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.pill-failed, .pill-cancelled {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.pill-queued {
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-icon-dismiss {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-icon-dismiss:hover {
  color: var(--text-danger);
  background-color: var(--status-rejected-bg);
}

.task-source-row {
  display: flex;
  align-items: center;
}

.task-source-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--primary);
  text-decoration: none;
  font-family: var(--font-mono);
}

.task-source-link:hover {
  text-decoration: underline;
}

/* Stepper Component */
.task-pipeline-container {
  padding: 10px 14px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.pipeline-stepper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
}

.pipeline-stepper::before {
  content: '';
  position: absolute;
  top: 11px;
  left: 20px;
  right: 20px;
  height: 2px;
  background-color: var(--border-color);
  z-index: 1;
}

.stepper-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  position: relative;
  z-index: 2;
}

.node-bullet {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: var(--bg-card);
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.node-label {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.stepper-node.active .node-bullet {
  border-color: var(--primary);
  background-color: var(--primary);
  color: #ffffff;
  box-shadow: 0 0 8px var(--primary-glow);
}

.stepper-node.active .node-label {
  color: var(--primary);
  font-weight: 600;
}

.stepper-node.done .node-bullet {
  border-color: var(--status-offer-text);
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
}

.stepper-node.done .node-label {
  color: var(--text-main);
}

/* Error Box */
.task-error-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background-color: var(--status-rejected-bg);
  border: 1px solid var(--status-rejected-border);
  color: var(--status-rejected-text);
  font-size: 12px;
  flex-wrap: wrap;
}

.error-msg-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.error-actions-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-retry-task, .btn-retry-error, .btn-fix-jd {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.modal-card-large {
  max-width: 600px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.form-input, .form-textarea {
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  font-family: inherit;
  transition: border-color var(--transition-fast);
}

.form-input:focus, .form-textarea:focus {
  border-color: var(--primary);
  outline: none;
}

/* Card Footer */
.task-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 6px;
  border-top: 1px solid var(--border-color);
  gap: 12px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-badge {
  padding: 2px 7px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
}

.algo-score-badge {
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.ai-score-badge {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.badge-cv-ready {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 4px;
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  font-size: 11px;
  font-weight: 600;
}

.footer-meta-text {
  font-size: 12px;
  color: var(--text-secondary);
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.8); }
  70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(255, 255, 255, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.8); }
}

@media (max-width: 1023px) {
  .queue-page-layout {
    padding: 16px 12px 60px;
  }

  .header-controls-centered {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    gap: 10px;
  }

  .tab-bar,
  .type-filter-group {
    width: 100%;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
    padding: 4px;
    justify-content: flex-start;
  }

  .tab-pill,
  .type-pill {
    flex-shrink: 0;
    white-space: nowrap;
    min-height: var(--min-touch-target, 44px);
    padding: 8px 12px;
  }

  .header-actions-row {
    width: 100%;
    justify-content: space-between;
  }

  .search-input-box {
    flex: 1;
  }

  .search-input {
    width: 100%;

  }

  .search-input:focus {
    width: 100%;
  }
}

@media (max-width: 767px) {
  .queue-content-scroll {
    padding: 12px 0;
  }

  .task-card-top {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .task-header-right {
    width: 100%;
    justify-content: space-between;
  }

  .task-pipeline-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    touch-action: pan-x;
  }

  .pipeline-stepper {
    min-width: 520px;
    padding: 4px 0;
  }

  .task-error-box {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .error-actions-right {
    width: 100%;
    justify-content: flex-end;
  }

  .btn-retry-task,
  .btn-retry-error,
  .btn-fix-jd,
  .btn-icon-dismiss,
  .btn-clear {
    min-height: 44px;
    padding: 8px 12px;
  }

  .modal-card {
    width: 100vw;
    height: 100vh;
    max-height: 100dvh;
    border-radius: 0;
    margin: 0;
    justify-content: space-between;
  }
}
</style>