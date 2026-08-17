<script setup>
import { ref, onMounted, computed } from 'vue'
import { ActionItemsAPI, ApplicationsAPI } from '../api/endpoints'
import { useUIStore } from '../stores/uiStore'
import DateTimePicker from '../components/common/DateTimePicker.vue'
import {
  CheckSquare,
  Square,
  AlertCircle,
  Clock,
  Calendar,
  Plus,
  Trash2,
  Edit2,
  Building2,
  ExternalLink,
  Loader2,
  X,
  Sparkles,
  Filter,
  CheckCircle2,
  Layers,
  Copy,
  Wand2,
} from 'lucide-vue-next'

const uiStore = useUIStore()

const isLoading = ref(true)
const actionItems = ref([])
const metrics = ref({
  total: 0,
  pending: 0,
  high_urgency: 0,
  completed: 0,
})

const filterTab = ref('PENDING') // 'ALL' | 'PENDING' | 'URGENCY' | 'COMPLETED'
const applicationsList = ref([])

// Filters for Urgency tab
const urgencyFilters = ref({
  HIGH: false,
  MEDIUM: false,
  LOW: false
})

const activeUrgencyDropdown = ref(null)

// Modal state
const showModal = ref(false)
const isEditing = ref(false)
const isSubmitting = ref(false)
const currentEditId = ref(null)

const taskForm = ref({
  application_id: null,
  title: '',
  due_date: '',
  urgency: 'MEDIUM',
  status: 'PENDING',
  action_url: '',
})

async function fetchActionItems() {
  isLoading.value = true
  try {
    const params = {}
    if (filterTab.value === 'PENDING') {
      params.status = 'PENDING'
    } else if (filterTab.value === 'COMPLETED') {
      params.status = 'COMPLETED'
    } else if (filterTab.value === 'URGENCY') {
      params.status = 'PENDING'
    }

    const res = await ActionItemsAPI.list(params)
    actionItems.value = res.data.items || []
    metrics.value = {
      total: res.data.total,
      pending: res.data.pending_count,
      high_urgency: res.data.high_urgency_count,
      completed: res.data.completed_count,
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to load action items', 'error')
  } finally {
    isLoading.value = false
  }
}

async function fetchApplicationsForSelector() {
  try {
    const res = await ApplicationsAPI.list({ limit: 100 })
    applicationsList.value = res.data.items || []
  } catch (err) {
    console.error('Failed to load applications for selector', err)
  }
}

function openCreateModal(appId = null) {
  isEditing.value = false
  currentEditId.value = null
  taskForm.value = {
    application_id: appId,
    title: '',
    due_date: '',
    urgency: 'MEDIUM',
    status: 'PENDING',
    action_url: '',
  }
  showModal.value = true
}

function openEditModal(item) {
  isEditing.value = true
  currentEditId.value = item.id
  taskForm.value = {
    application_id: item.application_id,
    title: item.title,
    due_date: item.due_date ? item.due_date.substring(0, 16) : '',
    urgency: item.urgency || 'MEDIUM',
    status: item.status || 'PENDING',
    action_url: item.action_url || '',
  }
  showModal.value = true
}

async function handleSaveTask() {
  if (!taskForm.value.title.trim()) {
    uiStore.showToast('Please enter a task title', 'warning')
    return
  }

  isSubmitting.value = true
  try {
    const payload = {
      title: taskForm.value.title.trim(),
      urgency: taskForm.value.urgency,
      status: taskForm.value.status,
      due_date: taskForm.value.due_date ? new Date(taskForm.value.due_date).toISOString() : null,
      action_url: taskForm.value.action_url || null,
      application_id: taskForm.value.application_id || null,
    }

    if (isEditing.value && currentEditId.value) {
      await ActionItemsAPI.update(currentEditId.value, payload)
      uiStore.showToast('Task updated successfully', 'success')
    } else {
      await ActionItemsAPI.create(payload)
      uiStore.showToast('Task created successfully', 'success')
    }

    showModal.value = false
    await fetchActionItems()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save task', 'error')
  } finally {
    isSubmitting.value = false
  }
}

async function toggleTaskStatus(item) {
  const newStatus = item.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED'
  // Optimistic update
  const prevStatus = item.status
  item.status = newStatus
  if (newStatus === 'COMPLETED') {
    metrics.value.completed += 1
    metrics.value.pending = Math.max(0, metrics.value.pending - 1)
  } else {
    metrics.value.completed = Math.max(0, metrics.value.completed - 1)
    metrics.value.pending += 1
  }

  try {
    await ActionItemsAPI.update(item.id, { status: newStatus })
    uiStore.showToast(
      newStatus === 'COMPLETED' ? 'Marked task as completed' : 'Task moved back to pending',
      'info'
    )
    if (filterTab.value !== 'ALL') {
      await fetchActionItems()
    }
  } catch (err) {
    item.status = prevStatus
    uiStore.showToast('Failed to update task status', 'error')
  }
}

async function deleteTask(item) {
  if (!confirm(`Are you sure you want to delete "${item.title}"?`)) return

  try {
    await ActionItemsAPI.delete(item.id)
    uiStore.showToast('Task deleted', 'info')
    await fetchActionItems()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to delete task', 'error')
  }
}

function openApplicationDrawer(appId) {
  if (appId) {
    uiStore.openDetail(appId)
  }
}

function formatDate(isoStr) {
  if (!isoStr) return null
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return isoStr
  }
}

function isOverdue(isoStr, status) {
  if (!isoStr || status === 'COMPLETED') return false
  return new Date(isoStr) < new Date()
}

async function setManualUrgency(item, level) {
  try {
    const res = await ActionItemsAPI.updateUrgency(item.id, level)
    const updated = res.data
    item.urgency = updated.urgency
    item.manual_urgency_override = updated.manual_urgency_override
    activeUrgencyDropdown.value = null

    // Re-fetch to update metrics and potentially re-sort
    await fetchActionItems()
    uiStore.showToast(`Urgency updated to ${level || 'Auto'}`, 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to update urgency', 'error')
  }
}

function toggleUrgencyFilter(level) {
  urgencyFilters.value[level] = !urgencyFilters.value[level]
}

async function draftEmail(item) {
  item.isDrafting = true;
  try {
    const res = await ActionItemsAPI.draftReply(item.id);
    item.draft_email = res.data.draft_email;
    uiStore.showToast('Draft generated successfully', 'success');
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to generate draft', 'error');
  } finally {
    item.isDrafting = false;
  }
}

async function copyDraft(text) {
  try {
    await navigator.clipboard.writeText(text);
    uiStore.showToast('Draft copied to clipboard', 'success');
  } catch (err) {
    uiStore.showToast('Failed to copy text', 'error');
  }
}

const displayedTasks = computed(() => {
  let tasks = actionItems.value

  if (filterTab.value === 'URGENCY') {
    const activeFilters = Object.entries(urgencyFilters.value)
      .filter(([_, isActive]) => isActive)
      .map(([level, _]) => level)

    if (activeFilters.length > 0) {
      tasks = tasks.filter(t => activeFilters.includes(t.urgency))
    }
  }

  return tasks
})

// Close dropdowns when clicking outside
function closeDropdowns(e) {
  if (!e.target.closest('.urgency-dropdown-wrapper')) {
    activeUrgencyDropdown.value = null
  }
}

onMounted(() => {
  document.addEventListener('click', closeDropdowns)
  fetchActionItems()
  fetchApplicationsForSelector()
})

import { onUnmounted } from 'vue'
onUnmounted(() => {
  document.removeEventListener('click', closeDropdowns)
})
</script>

<template>
  <div class="tasks-page">
    <!-- Header -->
    <div class="tasks-header">
      <div>
        <h1 class="page-title">Action Items & Reminders</h1>
        <p class="page-subtitle">Track follow-ups, scheduled interview deadlines, and qualification tasks across all applications.</p>
      </div>

      <button class="btn btn-secondary" @click="openCreateModal()">
        <Plus :size="16" />
        <span>New Action Item</span>
      </button>
    </div>

    <!-- Metrics Bar -->
    <div class="metrics-grid">
      <div
        class="metric-card"
        :class="{ active: filterTab === 'PENDING' }"
        @click="filterTab = 'PENDING'; fetchActionItems()"
      >
        <div class="metric-icon pending-icon">
          <Clock :size="20" />
        </div>
        <div class="metric-info">
          <span class="metric-val">{{ metrics.pending }}</span>
          <span class="metric-lbl">Pending Tasks</span>
        </div>
      </div>

      <div
        class="metric-card"
        :class="{ active: filterTab === 'URGENCY' }"
        @click="filterTab = 'URGENCY'; fetchActionItems()"
      >
        <div class="metric-icon high-icon">
          <AlertCircle :size="20" />
        </div>
        <div class="metric-info">
          <span class="metric-val">{{ metrics.high_urgency }}</span>
          <span class="metric-lbl">Urgency</span>
        </div>
      </div>

      <div
        class="metric-card"
        :class="{ active: filterTab === 'COMPLETED' }"
        @click="filterTab = 'COMPLETED'; fetchActionItems()"
      >
        <div class="metric-icon completed-icon">
          <CheckCircle2 :size="20" />
        </div>
        <div class="metric-info">
          <span class="metric-val">{{ metrics.completed }}</span>
          <span class="metric-lbl">Completed</span>
        </div>
      </div>
    </div>

    <!-- Filter Tabs Bar -->
    <div class="filter-tabs-bar">
      <div class="filter-tabs">
        <button
          class="filter-tab"
          :class="{ active: filterTab === 'PENDING' }"
          @click="filterTab = 'PENDING'; fetchActionItems()"
        >
          Pending
        </button>
        <button
          class="filter-tab"
          :class="{ active: filterTab === 'URGENCY' }"
          @click="filterTab = 'URGENCY'; fetchActionItems()"
        >
          Urgency
        </button>
        <button
          class="filter-tab"
          :class="{ active: filterTab === 'COMPLETED' }"
          @click="filterTab = 'COMPLETED'; fetchActionItems()"
        >
          Completed
        </button>
        <button
          class="filter-tab"
          :class="{ active: filterTab === 'ALL' }"
          @click="filterTab = 'ALL'; fetchActionItems()"
        >
          All Tasks
        </button>
      </div>
    </div>

    <!-- Task List -->
    <div class="tasks-container">
      <div v-if="filterTab === 'URGENCY'" class="urgency-filters">
        <span class="filter-label">Filter:</span>
        <button class="chip" :class="{ active: urgencyFilters.LOW }" @click="toggleUrgencyFilter('LOW')">🟢 Low</button>
        <button class="chip" :class="{ active: urgencyFilters.MEDIUM }" @click="toggleUrgencyFilter('MEDIUM')">🟡 Medium</button>
        <button class="chip" :class="{ active: urgencyFilters.HIGH }" @click="toggleUrgencyFilter('HIGH')">🔴 High</button>
      </div>

      <div v-if="isLoading" class="loading-state">
        <Loader2 class="animate-spin" :size="24" />
        <span>Loading action items...</span>
      </div>

      <div v-else-if="displayedTasks.length === 0" class="empty-tasks empty-state-box">
        <CheckCircle2 :size="44" class="empty-state-icon" />
        <h3 class="empty-state-title">No action items in this view</h3>
        <p class="empty-state-desc">All caught up! Create a new action item or link one from your application pipeline.</p>
        <button class="btn btn-secondary mt-3" @click="openCreateModal()">
          <Plus :size="15" />
          <span>Add Task</span>
        </button>
      </div>

      <div v-else class="task-list">
        <div v-for="item in displayedTasks" :key="item.id" class="task-row-container">
        <div
          class="task-row"
          :class="[
            { 'is-completed': item.status === 'COMPLETED' },
            `urgency-border-${item.urgency?.toLowerCase() || 'medium'}`
          ]"
        >
          <!-- Complete Checkbox -->
          <button
            class="checkbox-btn"
            :class="{ checked: item.status === 'COMPLETED' }"
            @click="toggleTaskStatus(item)"
            title="Toggle task completion"
          >
            <CheckSquare v-if="item.status === 'COMPLETED'" :size="20" class="text-primary" />
            <Square v-else :size="20" class="text-muted" />
          </button>

          <!-- Main Task Info -->
          <div class="task-main">
            <div class="task-title-line">
              <span class="task-title" :class="{ completed: item.status === 'COMPLETED' }">
                {{ item.title }}
              </span>

              <!-- Urgency Dropdown -->
              <div class="urgency-dropdown-wrapper" @click.stop>
                <button
                  class="urgency-pill dropdown-trigger"
                  :class="`urgency-${item.urgency?.toLowerCase() || 'medium'}`"
                  @click="activeUrgencyDropdown === item.id ? activeUrgencyDropdown = null : activeUrgencyDropdown = item.id"
                >
                  {{ item.urgency || 'MEDIUM' }}
                  <span v-if="item.manual_urgency_override" class="override-indicator">*</span>
                </button>

                <div v-if="activeUrgencyDropdown === item.id" class="urgency-dropdown">
                  <button class="dropdown-item" @click="setManualUrgency(item, 'HIGH')">High</button>
                  <button class="dropdown-item" @click="setManualUrgency(item, 'MEDIUM')">Medium</button>
                  <button class="dropdown-item" @click="setManualUrgency(item, 'LOW')">Low</button>
                  <div class="dropdown-divider"></div>
                  <button class="dropdown-item text-muted" @click="setManualUrgency(item, null)">Reset to Auto</button>
                </div>
              </div>
            </div>

            <!-- Meta details (Company, Application, Due Date) -->
            <div class="task-meta">
              <!-- Linked Application Pill -->
              <button
                v-if="item.application_id"
                class="app-link-btn"
                @click="openApplicationDrawer(item.application_id)"
                title="Open Application in Detail Drawer"
              >
                <Building2 :size="13" />
                <span class="app-link-text">
                  <strong>{{ item.company_name || 'Application' }}</strong>
                  <span v-if="item.position"> • {{ item.position }}</span>
                </span>
                <ExternalLink :size="11" class="ml-1 opacity-70" />
              </button>

              <!-- Due Date Pill -->
              <div
                v-if="item.due_date"
                class="due-date-pill"
                :class="{ overdue: isOverdue(item.due_date, item.status) }"
              >
                <Calendar :size="12" />
                <span>{{ isOverdue(item.due_date, item.status) ? 'Overdue: ' : 'Due: ' }}{{ formatDate(item.due_date) }}</span>
              </div>

              <!-- Action Link -->
              <a
                v-if="item.action_url"
                :href="item.action_url"
                target="_blank"
                rel="noopener noreferrer"
                class="external-action-link"
              >
                <ExternalLink :size="12" />
                <span>Link</span>
              </a>
            </div>
          </div>

          <!-- Actions (Edit, Delete, Draft) -->
          <div class="task-actions">
            <button v-if="item.application_id && !item.draft_email" class="btn-icon text-primary" @click="draftEmail(item)" title="Auto-Draft Reply" :disabled="item.isDrafting">
              <Loader2 v-if="item.isDrafting" class="animate-spin" :size="14" />
              <Wand2 v-else :size="14" />
            </button>
            <button class="btn-icon" @click="openEditModal(item)" title="Edit task">
              <Edit2 :size="14" />
            </button>
            <button class="btn-icon text-danger" @click="deleteTask(item)" title="Delete task">
              <Trash2 :size="14" />
            </button>
          </div>
        </div>

        <!-- Draft Email Block -->
        <div v-if="item.draft_email" class="task-draft-box">
          <div class="draft-header">
            <span class="draft-title"><Wand2 :size="12" style="margin-right: 4px;" /> AI Drafted Reply</span>
            <button class="btn-icon" @click="copyDraft(item.draft_email)" title="Copy to clipboard">
              <Copy :size="14" />
            </button>
          </div>
          <textarea class="draft-textarea" v-model="item.draft_email" rows="4"></textarea>
        </div>
        </div>
      </div>
    </div>

    <!-- Create / Edit Modal -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-backdrop" @click.self="showModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3 class="modal-title">{{ isEditing ? 'Edit Action Item' : 'New Action Item' }}</h3>
            <button class="btn-close" @click="showModal = false">
              <X :size="18" />
            </button>
          </div>

          <form @submit.prevent="handleSaveTask" class="modal-body">
            <div class="form-group">
              <label class="form-label">Task Title / Action Description *</label>
              <input
                v-model="taskForm.title"
                type="text"
                class="form-input"
                placeholder="e.g. Complete Take-Home Assignment, Prep for Live Coding..."
                required
              />
            </div>

            <div class="form-group">
              <label class="form-label">Associated Job Application</label>
              <select v-model="taskForm.application_id" class="form-select">
                <option :value="null">-- None (Standalone Task) --</option>
                <option
                  v-for="app in applicationsList"
                  :key="app.id"
                  :value="app.id"
                >
                  {{ app.company?.name }} — {{ app.position }} ({{ app.status }})
                </option>
              </select>
            </div>

            <div class="form-grid-2">
              <div class="form-group">
                <label class="form-label">Urgency Level</label>
                <select v-model="taskForm.urgency" class="form-select">
                  <option value="HIGH">High Urgency</option>
                  <option value="MEDIUM">Medium Urgency</option>
                  <option value="LOW">Low Urgency</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Status</label>
                <select v-model="taskForm.status" class="form-select">
                  <option value="PENDING">Pending</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="DISMISSED">Dismissed</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Due Date & Time (Optional)</label>
              <DateTimePicker
                v-model="taskForm.due_date"
                type="datetime"
                placeholder="Select due date & time..."
              />
            </div>

            <div class="form-group">
              <label class="form-label">Action URL (Optional)</label>
              <input
                v-model="taskForm.action_url"
                type="url"
                class="form-input"
                placeholder="https://..."
              />
            </div>

            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" @click="showModal = false">
                Cancel
              </button>
              <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
                <Loader2 v-if="isSubmitting" class="animate-spin" :size="15" />
                <span>{{ isEditing ? 'Save Changes' : 'Create Task' }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tasks-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px;
}

.tasks-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.tasks-header > div {
  flex: 1;
  min-width: 260px;
}

.tasks-header .btn {
  flex-shrink: 0;
  margin-top: 2px;
}

.page-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 24px;
  color: var(--text-main);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background-color: var(--bg-surface);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  box-shadow: var(--card-shadow);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.metric-card:hover {
  border-color: var(--card-hover-border);
  transform: translateY(-2px);
  box-shadow: var(--card-hover-shadow);
}

.metric-card.active {
  border-color: var(--primary);
  background-color: var(--bg-elevated);
}

.metric-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-sm);
}

.pending-icon { background-color: var(--primary-subtle); color: var(--primary); }
.high-icon { background-color: var(--status-rejected-bg); color: var(--status-rejected-text); }
.completed-icon { background-color: var(--status-offer-bg); color: var(--status-offer-text); }
.all-icon { background-color: var(--status-applied-bg); color: var(--status-applied-text); }

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.metric-lbl {
  font-size: 12px;
  color: var(--text-secondary);
}

.filter-tabs-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  background-color: var(--bg-sidebar);
  padding: 4px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.filter-tab {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.filter-tab:hover {
  color: var(--text-main);
}

.filter-tab.active {
  background-color: var(--bg-surface);
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
}

.tasks-container {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.loading-state, .empty-tasks {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-secondary);
  text-align: center;
}

.task-list {
  display: flex;
  flex-direction: column;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  border-left: 4px solid transparent;
  transition: background-color var(--transition-fast);
}

.urgency-border-high {
  border-left-color: var(--status-rejected-border);
}

.urgency-border-medium {
  border-left-color: var(--status-interview-border);
}

.urgency-border-low {
  border-left-color: var(--status-applied-border);
}

.task-row:last-child {
  border-bottom: none;
}

.task-row:hover {
  background-color: var(--bg-card);
}

.task-row.is-completed {
  opacity: 0.65;
}

.checkbox-btn {
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
}

.task-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.task-title-line {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.task-title.completed {
  text-decoration: line-through;
  color: var(--text-muted);
}

.urgency-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.urgency-high {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.urgency-medium {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
}

.urgency-low {
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
}

.urgency-dropdown-wrapper {
  position: relative;
}

.dropdown-trigger {
  cursor: pointer;
  background: none;
}

.dropdown-trigger:hover {
  opacity: 0.8;
}

.override-indicator {
  margin-left: 2px;
  font-weight: bold;
}

.urgency-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  z-index: 10;
  min-width: 120px;
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.dropdown-item {
  padding: 6px 12px;
  font-size: 12px;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-main);
  transition: background-color var(--transition-fast);
}

.dropdown-item:hover {
  background-color: var(--bg-card);
}

.dropdown-divider {
  height: 1px;
  background-color: var(--border-color);
  margin: 4px 0;
}

.urgency-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-surface);
}

.filter-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.chip {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.chip:hover {
  border-color: var(--text-secondary);
}

.chip.active {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}

.task-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
}

.app-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  font-size: 11px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.app-link-btn:hover {
  color: var(--primary);
  border-color: var(--primary);
}

.app-link-text {
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.due-date-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 11px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.due-date-pill.overdue {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.external-action-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--primary);
  font-size: 11px;
}

.external-action-link:hover {
  text-decoration: underline;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-icon {
  background: none;
  border: 1px solid transparent;
  padding: 6px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  color: var(--text-main);
  background-color: var(--bg-elevated);
  border-color: var(--border-color);
}

.btn-icon.text-danger:hover {
  color: var(--danger);
  border-color: rgba(239, 68, 68, 0.3);
}

/* Modal styles */
.modal-backdrop {
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

.modal-card {
  width: 100%;
  max-width: 520px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  position: relative;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input, .form-select {
  padding: 8px 12px;
  font-size: 13px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-main);
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: var(--primary);
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}


.task-row-container {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--border-color);
}

.task-row-container:last-child {
  border-bottom: none;
}

.task-row {
  border-bottom: none !important;
}

.text-primary {
  color: var(--primary) !important;
}

.task-draft-box {
  margin: 0 20px 14px 44px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px;
}

.draft-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.draft-title {
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
}

.draft-textarea {
  width: 100%;
  padding: 10px;
  font-size: 13px;
  color: var(--text-main);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  resize: vertical;
}

.draft-textarea:focus {
  outline: none;
  border-color: var(--primary);
}
</style>
