<script setup>
import { ref, onMounted, computed } from 'vue'
import { ActionItemsAPI, ApplicationsAPI } from '../api/endpoints'
import { useUIStore } from '../stores/uiStore'
import DateTimePicker from '../components/common/DateTimePicker.vue'
import PageHeader from '../components/common/PageHeader.vue'
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
  Search,
  RotateCcw,
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

// Unified Filters & Sorting
const searchQuery = ref('')
const selectedUrgency = ref(null) // null | 'HIGH' | 'MEDIUM' | 'LOW'
const sortBy = ref('due_asc') // 'due_asc' | 'due_desc' | 'urgency' | 'created_desc'

function selectMetricTab(tab) {
  filterTab.value = tab
  searchQuery.value = ''
  if (tab === 'URGENCY') {
    selectedUrgency.value = 'HIGH'
  } else {
    selectedUrgency.value = null
  }
  fetchActionItems()
}

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
    if (filterTab.value === 'PENDING' || filterTab.value === 'URGENCY') {
      params.status = 'PENDING'
    } else if (filterTab.value === 'COMPLETED') {
      params.status = 'COMPLETED'
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
    if (isEditing.value) {
      await ActionItemsAPI.update(currentEditId.value, {
        title: taskForm.value.title.trim(),
        due_date: taskForm.value.due_date ? new Date(taskForm.value.due_date).toISOString() : null,
        urgency: taskForm.value.urgency,
        status: taskForm.value.status,
        action_url: taskForm.value.action_url ? taskForm.value.action_url.trim() : null,
      })
      uiStore.showToast('Action item updated', 'success')
    } else {
      await ActionItemsAPI.create({
        application_id: taskForm.value.application_id,
        title: taskForm.value.title.trim(),
        due_date: taskForm.value.due_date ? new Date(taskForm.value.due_date).toISOString() : null,
        urgency: taskForm.value.urgency,
        status: taskForm.value.status,
        action_url: taskForm.value.action_url ? taskForm.value.action_url.trim() : null,
      })
      uiStore.showToast('Action item created', 'success')
    }
    showModal.value = false
    await fetchActionItems()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save action item', 'error')
  } finally {
    isSubmitting.value = false
  }
}

async function toggleTaskStatus(item) {
  const nextStatus = item.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED'
  const prevStatus = item.status
  item.status = nextStatus

  try {
    await ActionItemsAPI.update(item.id, { status: nextStatus })
    uiStore.showToast(nextStatus === 'COMPLETED' ? 'Task marked as completed! 🎉' : 'Task moved back to Pending', 'info')
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

const displayedTasks = computed(() => {
  let tasks = actionItems.value

  if (filterTab.value === 'URGENCY') {
    tasks = tasks.filter(t => t.urgency === 'HIGH' || isOverdue(t.due_date, t.status))
  }

  // Urgency chip filter
  if (selectedUrgency.value) {
    tasks = tasks.filter(t => t.urgency === selectedUrgency.value)
  }

  // Search filter
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    tasks = tasks.filter(t => 
      (t.title || '').toLowerCase().includes(q) ||
      (t.application?.company?.name || '').toLowerCase().includes(q) ||
      (t.application?.position || '').toLowerCase().includes(q)
    )
  }

  // Sorting
  return [...tasks].sort((a, b) => {
    if (sortBy.value === 'due_asc') {
      if (!a.due_date) return 1
      if (!b.due_date) return -1
      return new Date(a.due_date) - new Date(b.due_date)
    }
    if (sortBy.value === 'due_desc') {
      if (!a.due_date) return 1
      if (!b.due_date) return -1
      return new Date(b.due_date) - new Date(a.due_date)
    }
    if (sortBy.value === 'urgency') {
      const weights = { HIGH: 3, MEDIUM: 2, LOW: 1 }
      return (weights[b.urgency] || 0) - (weights[a.urgency] || 0)
    }
    if (sortBy.value === 'created_desc') {
      return new Date(b.created_at) - new Date(a.created_at)
    }
    return 0
  })
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
    <!-- Standardized Page Header -->
    <PageHeader
      title="Action Items & Reminders"
      subtitle="Track follow-ups, scheduled interview deadlines, and qualification tasks across all applications."
    />

    <!-- Interactive Metrics Filter Bar -->
    <div class="metrics-grid">
      <div
        class="metric-card"
        :class="{ active: filterTab === 'PENDING' }"
        @click="selectMetricTab('PENDING')"
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
        @click="selectMetricTab('URGENCY')"
      >
        <div class="metric-icon high-icon">
          <AlertCircle :size="20" />
        </div>
        <div class="metric-info">
          <span class="metric-val">{{ metrics.high_urgency }}</span>
          <span class="metric-lbl">Urgent / Overdue</span>
        </div>
      </div>

      <div
        class="metric-card"
        :class="{ active: filterTab === 'COMPLETED' }"
        @click="selectMetricTab('COMPLETED')"
      >
        <div class="metric-icon completed-icon">
          <CheckCircle2 :size="20" />
        </div>
        <div class="metric-info">
          <span class="metric-val">{{ metrics.completed }}</span>
          <span class="metric-lbl">Completed</span>
        </div>
      </div>

      <div
        class="metric-card"
        :class="{ active: filterTab === 'ALL' }"
        @click="selectMetricTab('ALL')"
      >
        <div class="metric-icon all-icon">
          <Layers :size="20" />
        </div>
        <div class="metric-info">
          <span class="metric-val">{{ metrics.total }}</span>
          <span class="metric-lbl">All Tasks</span>
        </div>
      </div>
    </div>

    <!-- Unified Filter & Search Toolbar -->
    <div class="tasks-toolbar">
      <div class="search-box">
        <Search :size="15" class="text-muted" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search task title, company, or role..."
          class="search-input"
        />
        <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">
          <X :size="13" />
        </button>
      </div>

      <div class="urgency-chips">
        <span class="filter-label">Urgency:</span>
        <button
          class="urgency-filter-pill"
          :class="{ active: selectedUrgency === null }"
          @click="selectedUrgency = null"
        >
          All
        </button>
        <button
          class="urgency-filter-pill urgency-high"
          :class="{ active: selectedUrgency === 'HIGH' }"
          @click="selectedUrgency = selectedUrgency === 'HIGH' ? null : 'HIGH'"
        >
          High
        </button>
        <button
          class="urgency-filter-pill urgency-medium"
          :class="{ active: selectedUrgency === 'MEDIUM' }"
          @click="selectedUrgency = selectedUrgency === 'MEDIUM' ? null : 'MEDIUM'"
        >
          Medium
        </button>
        <button
          class="urgency-filter-pill urgency-low"
          :class="{ active: selectedUrgency === 'LOW' }"
          @click="selectedUrgency = selectedUrgency === 'LOW' ? null : 'LOW'"
        >
          Low
        </button>
      </div>

      <div class="sort-wrapper">
        <span class="sort-label">Sort:</span>
        <select v-model="sortBy" class="sort-select">
          <option value="due_asc">Due Date (Soonest)</option>
          <option value="due_desc">Due Date (Latest)</option>
          <option value="urgency">Highest Urgency</option>
          <option value="created_desc">Newest Created</option>
        </select>
      </div>
    </div>

    <!-- Task List -->
    <div class="tasks-container">

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
        <div
          v-for="item in displayedTasks"
          :key="item.id"
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
                  :class="[`urgency-${item.urgency?.toLowerCase() || 'medium'}`, { active: activeUrgencyDropdown === item.id }]"
                  @click="activeUrgencyDropdown === item.id ? activeUrgencyDropdown = null : activeUrgencyDropdown = item.id"
                >
                  {{ item.urgency || 'MEDIUM' }}
                  <span v-if="item.manual_urgency_override" class="override-indicator">*</span>
                </button>

                <div v-if="activeUrgencyDropdown === item.id" class="dropdown-menu urgency-dropdown animate-fade-in">
                  <button
                    class="dropdown-item"
                    :class="{ selected: item.urgency === 'HIGH' }"
                    @click="setManualUrgency(item, 'HIGH')"
                  >
                    <span class="urgency-dot urgency-high-dot"></span>
                    <span>High Urgency</span>
                  </button>
                  <button
                    class="dropdown-item"
                    :class="{ selected: item.urgency === 'MEDIUM' }"
                    @click="setManualUrgency(item, 'MEDIUM')"
                  >
                    <span class="urgency-dot urgency-medium-dot"></span>
                    <span>Medium Urgency</span>
                  </button>
                  <button
                    class="dropdown-item"
                    :class="{ selected: item.urgency === 'LOW' }"
                    @click="setManualUrgency(item, 'LOW')"
                  >
                    <span class="urgency-dot urgency-low-dot"></span>
                    <span>Low Urgency</span>
                  </button>
                  <div class="dropdown-divider"></div>
                  <button
                    class="dropdown-item text-muted"
                    @click="setManualUrgency(item, null)"
                  >
                    <RotateCcw :size="12" />
                    <span>Reset to Auto</span>
                  </button>
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

          <!-- Actions (Edit, Delete) -->
          <div class="task-actions">
            <button class="btn-icon" @click="openEditModal(item)" title="Edit task">
              <Edit2 :size="14" />
            </button>
            <button class="btn-icon text-danger" @click="deleteTask(item)" title="Delete task">
              <Trash2 :size="14" />
            </button>
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
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
  min-height: calc(100vh - var(--navbar-height));
  width: 100%;
}



.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 540px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

.all-icon {
  background-color: var(--primary-subtle);
  color: var(--primary);
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

/* Unified Tasks Toolbar */
.tasks-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 10px 16px;
  border-radius: var(--radius-md);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  flex: 1;
  min-width: 220px;
}

.search-input {
  background: transparent;
  border: none;
  outline: none;
  font-size: 13px;
  color: var(--text-main);
  width: 100%;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.clear-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.urgency-chips {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label, .sort-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.urgency-filter-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  opacity: 0.75;
}

.urgency-filter-pill:hover {
  opacity: 1;
}

.urgency-filter-pill.active {
  opacity: 1;
  box-shadow: 0 0 0 2px var(--primary);
  font-weight: 800;
}

.urgency-filter-pill.active:not(.urgency-high):not(.urgency-medium):not(.urgency-low) {
  background-color: var(--primary);
  border-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
}

.sort-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sort-select {
  height: 32px;
  padding: 0 28px 0 10px;
  font-size: 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  cursor: pointer;
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
  opacity: 0.85;
}

.override-indicator {
  margin-left: 2px;
  font-weight: bold;
}

.urgency-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 160px;
  z-index: 50;
}

.urgency-dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  display: inline-block;
  flex-shrink: 0;
}

.urgency-high-dot {
  background-color: var(--status-rejected-text);
  box-shadow: 0 0 6px var(--status-rejected-border);
}

.urgency-medium-dot {
  background-color: var(--status-interview-text);
  box-shadow: 0 0 6px var(--status-interview-border);
}

.urgency-low-dot {
  background-color: var(--status-applied-text);
  box-shadow: 0 0 6px var(--status-applied-border);
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
</style>
