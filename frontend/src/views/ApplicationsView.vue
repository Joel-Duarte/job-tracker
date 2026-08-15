<script setup>
import { ref, onMounted } from 'vue'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useUIStore } from '../stores/uiStore'
import {
  Search,
  Kanban,
  Table as TableIcon,
  Filter,
  Building2,
  Calendar,
  AlertCircle,
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
} from 'lucide-vue-next'

const appStore = useApplicationsStore()
const uiStore = useUIStore()

// Drag & Drop State
const draggedApp = ref(null)
const dragOverCol = ref(null)

// Transition Modal State
const showTransitionModal = ref(false)
const transitionApp = ref(null)
const targetStatus = ref('')
const isSubmittingTransition = ref(false)
const transitionForm = ref({
  interview_stage: 'Technical Round 1',
  scheduled_at: '',
  offered_salary: null,
  currency: 'USD',
  offer_received_date: '',
  decision_deadline: '',
  rejection_date: '',
  rejection_reason: 'Resume / Initial Screen',
  notes: '',
})

// Delete Modal State
const showDeleteModal = ref(false)
const appToDelete = ref(null)
const isDeleting = ref(false)

const INTERVIEW_STAGES = [
  'Recruiter Screen / Initial Chat',
  'Online Assessment / Take-Home',
  'Technical Round 1',
  'System Design / Live Coding',
  'Hiring Manager / Final Round',
  'Custom / Other',
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
})

function handleSearch(e) {
  appStore.searchQuery = e.target.value
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

function hasDetailedPhase(app) {
  return ['TECHNICAL_INTERVIEW', 'OFFER', 'REJECTED'].includes(app?.status)
}

function getAppSubPhaseLabel(app) {
  if (!app) return ''
  const status = app.status || 'APPLIED'
  const payload = app.latest_event?.raw_payload || {}

  if (status === 'TECHNICAL_INTERVIEW') {
    return payload.interview_stage || 'Technical Round 1'
  }
  if (status === 'OFFER') {
    const sal = payload.offered_salary || app.job_posting?.salary_max || app.job_posting?.salary_min
    const curr = payload.currency || app.job_posting?.currency || 'USD'
    return sal ? `$${Number(sal).toLocaleString()} ${curr}` : 'Offer Package'
  }
  if (status === 'REJECTED') {
    return payload.rejection_reason || 'Rejection Notice'
  }
  if (status === 'ASSESSMENT') return 'AI Assessment'
  return 'Applied'
}

function getInterviewDate(app) {
  if (!app) return null
  const payload = app.latest_event?.raw_payload || {}
  const dateStr = payload.scheduled_at
  if (!dateStr) return null
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

// Drag and Drop Handlers
function onDragStart(app, event) {
  draggedApp.value = app
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', app.id.toString())
}

function onDragEnd() {
  draggedApp.value = null
  dragOverCol.value = null
}

function onDragOver(colKey, event) {
  event.preventDefault()
  dragOverCol.value = colKey
  event.dataTransfer.dropEffect = 'move'
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

  transitionForm.value = {
    interview_stage: existingPayload.interview_stage || 'Technical Round 1',
    scheduled_at: existingPayload.scheduled_at ? existingPayload.scheduled_at.substring(0, 16) : '',
    offered_salary: existingPayload.offered_salary || app.job_posting?.salary_max || app.job_posting?.salary_min || null,
    currency: existingPayload.currency || app.job_posting?.currency || 'USD',
    offer_received_date: existingPayload.offer_received_date || today,
    decision_deadline: existingPayload.decision_deadline || '',
    rejection_date: existingPayload.rejection_date || today,
    rejection_reason: existingPayload.rejection_reason || 'Resume / Initial Screen',
    notes: '',
  }
  showTransitionModal.value = true
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
    uiStore.showToast(`Application moved to ${payload.status}`, 'success')
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
    uiStore.showToast(`Application moved to ${targetStatus.value}`, 'success')
    showTransitionModal.value = false
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
        <div class="search-input-wrapper">
          <Search :size="15" class="search-icon" />
          <input
            type="text"
            placeholder="Search company, position, or keywords..."
            :value="appStore.searchQuery"
            class="search-input"
            @input="handleSearch"
          />
        </div>

        <select
          :value="appStore.selectedStatus"
          class="filter-select"
          @change="handleStatusFilter"
        >
          <option value="">All Statuses</option>
          <option v-for="s in appStore.STATUSES" :key="s.key" :value="s.key">
            {{ s.label }}
          </option>
        </select>

        <button
          class="btn btn-secondary filter-toggle-btn"
          :class="{ active: appStore.actionRequiredOnly }"
          @click="toggleActionRequired"
        >
          <AlertCircle :size="14" />
          <span>Action Required</span>
        </button>
      </div>

      <!-- View Switcher & Total Count -->
      <div class="view-switch-group">
        <div class="total-counter">
          <span class="count-num">{{ appStore.total }}</span>
          <span class="count-label">Applications</span>
        </div>

        <div class="view-toggle">
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
      <!-- 1. KANBAN VIEW (WITH DRAG & DROP) -->
      <div v-if="uiStore.viewMode === 'kanban'" class="kanban-board">
        <div
          v-for="col in appStore.STATUSES"
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
              :class="{ 'is-dragging': draggedApp?.id === app.id }"
              draggable="true"
              @dragstart="onDragStart(app, $event)"
              @dragend="onDragEnd"
              @click="uiStore.openDetail(app.id)"
            >
              <div class="card-header">
                <div class="company-name-tag">
                  <Building2 :size="14" class="company-icon" />
                  <span>{{ app.company?.name || 'Company' }}</span>
                </div>
                <div class="card-header-actions" @click.stop>
                  <span class="card-date">{{ formatDate(app.last_activity_at || app.application_date) }}</span>
                  <button
                    class="card-action-btn"
                    title="Delete application"
                    @click="openDeleteConfirm(app)"
                  >
                    <Trash2 :size="13" />
                  </button>
                </div>
              </div>

              <div class="card-position">
                {{ app.position || 'Position Not Specified' }}
              </div>

              <!-- Phase Detail Pill & Interview Date -->
              <div class="card-phase-row" @click.stop>
                <button
                  class="phase-detail-btn"
                  :class="`phase-${(app.status || 'applied').toLowerCase()}`"
                  @click="openTransitionModal(app, app.status)"
                  title="Click to edit phase details, dates, or status"
                >
                  <span class="phase-detail-text">{{ getAppSubPhaseLabel(app) }}</span>
                  <SlidersHorizontal :size="11" class="phase-icon" />
                </button>

                <!-- Show Interview Scheduled Date if it exists -->
                <div v-if="getInterviewDate(app)" class="interview-date-tag" title="Scheduled Interview Date & Time">
                  <Calendar :size="11" />
                  <span>{{ getInterviewDate(app) }}</span>
                </div>
              </div>

              <!-- Latest Event Summary Pill -->
              <div v-if="app.latest_event?.email_summary" class="card-summary">
                <span class="summary-prefix">{{ app.latest_event.email_event_type }}:</span>
                {{ app.latest_event.email_summary }}
              </div>

              <div class="card-footer">
                <div v-if="app.has_action_required" class="card-action-badge">
                  <AlertCircle :size="12" />
                  <span>Action Needed</span>
                </div>
                <div class="card-drag-hint">
                  <GripVertical :size="14" />
                </div>
              </div>
            </div>

            <!-- Empty Column State -->
            <div
              v-if="!appStore.kanbanColumns[col.key]?.length"
              class="column-empty"
            >
              Drop applications here
            </div>
          </div>
        </div>
      </div>

      <!-- 2. DATA TABLE VIEW -->
      <div v-else class="table-container animate-fade-in">
        <table class="data-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Position</th>
              <th>Status / Phase</th>
              <th>Last Activity</th>
              <th>Action Needed</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="app in appStore.applications"
              :key="app.id"
              class="table-row"
              @click="uiStore.openDetail(app.id)"
            >
              <td class="cell-company">
                <div class="company-cell-wrapper">
                  <div class="company-logo-mini">
                    <Building2 :size="14" />
                  </div>
                  <span class="company-name-bold">{{ app.company?.name || 'Company' }}</span>
                </div>
              </td>

              <td class="cell-position">
                {{ app.position || '—' }}
              </td>

              <td class="cell-status" @click.stop>
                <div class="table-phase-row">
                  <button
                    class="phase-detail-btn"
                    :class="`phase-${(app.status || 'applied').toLowerCase()}`"
                    @click="openTransitionModal(app, app.status)"
                    title="Click to edit phase details, dates, or status"
                  >
                    <span class="phase-detail-text">{{ getAppSubPhaseLabel(app) }}</span>
                    <SlidersHorizontal :size="11" class="phase-icon" />
                  </button>

                  <div v-if="getInterviewDate(app)" class="interview-date-tag" title="Scheduled Interview Date & Time">
                    <Calendar :size="11" />
                    <span>{{ getInterviewDate(app) }}</span>
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
                  class="btn btn-secondary btn-sm"
                  @click="uiStore.openDetail(app.id)"
                >
                  View Details
                </button>
                <button
                  class="btn btn-danger-subtle btn-sm"
                  title="Delete Application"
                  @click="openDeleteConfirm(app)"
                >
                  <Trash2 :size="13" />
                </button>
              </td>
            </tr>

            <tr v-if="appStore.applications.length === 0">
              <td colspan="6" class="table-empty">
                No matching job applications found.
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
              <span>Move {{ transitionApp?.company?.name }} to {{ targetStatus.replace('_', ' ') }}</span>
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

              <div class="form-group">
                <label class="form-label">Scheduled Date & Time (Optional)</label>
                <input
                  v-model="transitionForm.scheduled_at"
                  type="datetime-local"
                  class="form-input"
                />
              </div>
            </div>

            <!-- Offer Compensation & Deadlines -->
            <div v-if="targetStatus === 'OFFER'" class="form-group-stack">
              <div class="form-group">
                <label class="form-label">Offered Compensation / Salary</label>
                <div class="salary-input-row">
                  <input
                    v-model="transitionForm.offered_salary"
                    type="number"
                    placeholder="e.g. 185000"
                    class="form-input"
                  />
                  <select v-model="transitionForm.currency" class="form-select currency-select">
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                    <option value="CAD">CAD ($)</option>
                    <option value="CHF">CHF</option>
                  </select>
                </div>
              </div>

              <div class="form-row-2">
                <div class="form-group">
                  <label class="form-label">Offer Received Date</label>
                  <input
                    v-model="transitionForm.offer_received_date"
                    type="date"
                    class="form-input"
                  />
                </div>

                <div class="form-group">
                  <label class="form-label">Decision Deadline (Limit Date)</label>
                  <input
                    v-model="transitionForm.decision_deadline"
                    type="date"
                    class="form-input"
                  />
                </div>
              </div>
            </div>

            <!-- Rejection Reason & Date -->
            <div v-if="targetStatus === 'REJECTED'" class="form-group-stack">
              <div class="form-group">
                <label class="form-label">Rejection Notice Date</label>
                <input
                  v-model="transitionForm.rejection_date"
                  type="date"
                  class="form-input"
                />
              </div>

              <div class="form-group">
                <label class="form-label">Rejection Reason</label>
                <select v-model="transitionForm.rejection_reason" class="form-select">
                  <option v-for="reason in REJECTION_REASONS" :key="reason" :value="reason">
                    {{ reason }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Optional Notes -->
            <div class="form-group">
              <label class="form-label">Context / Notes (Optional)</label>
              <textarea
                v-model="transitionForm.notes"
                rows="3"
                placeholder="Add quick notes about feedback, interviewers, or timeline..."
                class="form-textarea text-xs"
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
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
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
  height: 34px;
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
  overflow-x: auto;
  overflow-y: auto;
  padding: 20px 24px;
}

/* KANBAN BOARD */
.kanban-board {
  display: grid;
  grid-template-columns: repeat(5, minmax(280px, 1fr));
  gap: 16px;
  height: 100%;
  align-items: start;
}

.kanban-column {
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 170px);
  overflow: hidden;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
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
  font-size: 13px;
  font-weight: 600;
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
}

.application-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.application-card:hover {
  background-color: var(--bg-card-hover);
  border-color: var(--border-subtle);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.company-name-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.company-icon {
  color: var(--primary);
}

.card-date {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.card-position {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
  margin-bottom: 6px;
  line-height: 1.3;
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
  background-color: rgba(99, 102, 241, 0.12);
  color: #6366f1;
  border: 1px solid rgba(99, 102, 241, 0.25);
  font-family: var(--font-mono);
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
  gap: 6px;
}

.card-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  color: var(--text-muted);
  opacity: 0;
  transition: all var(--transition-fast);
}

.application-card:hover .card-action-btn {
  opacity: 1;
}

.card-action-btn:hover {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
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
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.inner-modal-box {
  width: 100%;
  max-width: 440px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.inner-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.inner-modal-title {
  font-size: 15px;
  font-weight: 700;
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
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
