<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import { IntakeAPI } from '../../api/endpoints'
import {
  Cpu,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock,
  RotateCcw,
  ExternalLink,
  X,
  RefreshCw,
  Trash2,
  Briefcase,
  UserCheck,
  Layers,
  ChevronUp,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()

const isOpen = ref(false)
const tasks = ref([])
const loading = ref(false)
const retryingTaskIds = ref(new Set())
const widgetContainerRef = ref(null)

let pollTimer = null

const activeTasks = computed(() =>
  tasks.value.filter((t) => ['QUEUED', 'PROCESSING'].includes(t.status))
)
const failedTasks = computed(() =>
  tasks.value.filter((t) => ['FAILED', 'CANCELLED'].includes(t.status))
)
const completedTasks = computed(() =>
  tasks.value.filter((t) => t.status === 'COMPLETED')
)

const activeCount = computed(() => activeTasks.value.length)
const failedCount = computed(() => failedTasks.value.length)
const completedCount = computed(() => completedTasks.value.length)

// Determine state status for styling
const widgetState = computed(() => {
  if (failedCount.value > 0) return 'failed'
  if (activeCount.value > 0) return 'active'
  return 'healthy'
})

async function pollQueueStatus(silent = true) {
  if (!silent) loading.value = true
  try {
    const res = await IntakeAPI.getEvaluations(50)
    if (Array.isArray(res.data)) {
      tasks.value = res.data
    }
  } catch (err) {
    // Ignore silent errors during background polling
    if (!silent) {
      uiStore.showToast(err.message || 'Failed to update queue', 'error')
    }
  } finally {
    if (!silent) loading.value = false
  }
}

function toggleMenu() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    pollQueueStatus(false)
  }
}

function closeMenu() {
  isOpen.value = false
}

function handleClickOutside(event) {
  if (widgetContainerRef.value && !widgetContainerRef.value.contains(event.target)) {
    closeMenu()
  }
}

function navigateToQueue() {
  closeMenu()
  router.push('/queue')
}

async function retryTask(taskId) {
  const newSet = new Set(retryingTaskIds.value)
  newSet.add(taskId)
  retryingTaskIds.value = newSet

  try {
    await IntakeAPI.retryEvaluation(taskId)
    uiStore.showToast(`Task #${taskId} re-queued for execution!`, 'success')
    await pollQueueStatus(true)
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to retry task', 'error')
  } finally {
    const s = new Set(retryingTaskIds.value)
    s.delete(taskId)
    retryingTaskIds.value = s
  }
}

async function deleteTask(taskId) {
  try {
    await IntakeAPI.deleteEvaluation(taskId)
    tasks.value = tasks.value.filter((t) => t.id !== taskId)
    uiStore.showToast(`Task #${taskId} dismissed`, 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to dismiss task', 'error')
  }
}

function getTaskTypeIcon(type) {
  if (type === 'CV_EXTRACTION') return UserCheck
  if (type === 'EMBEDDING') return Layers
  return Briefcase
}

function getTaskTypeLabel(type) {
  if (type === 'CV_EXTRACTION') return 'CV Extract'
  if (type === 'EMBEDDING') return 'Embedding'
  return 'Job Lead'
}

onMounted(() => {
  pollQueueStatus(true)
  pollTimer = setInterval(() => {
    pollQueueStatus(true)
  }, activeCount.value > 0 ? 2500 : 6000)

  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div
    v-if="route.path !== '/queue'"
    ref="widgetContainerRef"
    class="floating-queue-widget"
  >
    <!-- Interactive Overlay Dropdown Menu (Positioned directly above status pill) -->
    <Transition name="popover-fade">
      <div v-if="isOpen" class="queue-popover-menu">
        <!-- Menu Header -->
        <div class="popover-header">
          <div class="header-title-group">
            <Cpu :size="16" class="text-primary" />
            <span class="header-title">AI Processing Queue</span>
            <span v-if="loading" class="loading-indicator">
              <Loader2 :size="12" class="animate-spin text-muted" />
            </span>
          </div>

          <div class="header-actions">
            <button
              class="btn-icon-subtle"
              :disabled="loading"
              @click="pollQueueStatus(false)"
              title="Refresh queue items"
            >
              <RefreshCw :size="13" :class="{ 'animate-spin': loading }" />
            </button>

            <button
              class="btn-icon-subtle"
              @click="navigateToQueue"
              title="Open full Queue management view"
            >
              <ExternalLink :size="13" />
            </button>

            <button
              class="btn-icon-subtle"
              @click="closeMenu"
              title="Close overlay menu"
            >
              <X :size="14" />
            </button>
          </div>
        </div>

        <!-- Summary Status Counter Bar -->
        <div class="popover-stats-bar">
          <div class="stat-badge" :class="{ 'active-stat': activeCount > 0 }">
            <Loader2 v-if="activeCount > 0" class="animate-spin" :size="11" />
            <Clock v-else :size="11" />
            <span>{{ activeCount }} Active</span>
          </div>

          <div class="stat-badge" :class="{ 'failed-stat': failedCount > 0 }">
            <AlertCircle :size="11" />
            <span>{{ failedCount }} Failed</span>
          </div>

          <div class="stat-badge completed-stat">
            <CheckCircle2 :size="11" />
            <span>{{ completedCount }} Done</span>
          </div>
        </div>

        <!-- Task List Content Area -->
        <div class="popover-body">
          <div v-if="tasks.length === 0" class="empty-queue-state">
            <Cpu :size="28" class="text-muted opacity-50" />
            <p class="empty-title">Queue is idle</p>
            <p class="empty-subtext">No active background tasks or failed items.</p>
          </div>

          <div v-else class="popover-task-list">
            <div
              v-for="task in tasks"
              :key="task.id"
              class="popover-task-item"
              :class="`task-state-${task.status.toLowerCase()}`"
            >
              <div class="task-item-header">
                <div class="task-meta-left">
                  <span
                    class="task-type-badge"
                    :class="`type-${(task.task_type || 'JOB_ASSESSMENT').toLowerCase()}`"
                  >
                    <component :is="getTaskTypeIcon(task.task_type)" :size="11" />
                    <span>{{ getTaskTypeLabel(task.task_type) }}</span>
                  </span>
                  <span class="task-id">#{{ task.id }}</span>
                </div>

                <div class="task-status-pill" :class="`pill-${task.status.toLowerCase()}`">
                  <Loader2 v-if="task.status === 'PROCESSING'" class="animate-spin" :size="10" />
                  <AlertCircle v-else-if="['FAILED', 'CANCELLED'].includes(task.status)" :size="10" />
                  <CheckCircle2 v-else-if="task.status === 'COMPLETED'" :size="10" />
                  <Clock v-else :size="10" />
                  <span>{{ task.status }}</span>
                </div>
              </div>

              <!-- Task Title -->
              <div class="task-item-title font-medium" :title="task.title_hint || task.job_url">
                {{ task.title_hint || task.job_url || `Task #${task.id}` }}
              </div>

              <!-- Stage indicator for running task -->
              <div v-if="task.status === 'PROCESSING' && task.stage" class="task-stage-line">
                <span class="stage-dot"></span>
                <span>Stage: {{ task.stage }}</span>
              </div>

              <!-- Specific Error Message & Actionable Inline Retry Button -->
              <div v-if="['FAILED', 'CANCELLED'].includes(task.status)" class="task-failed-box">
                <div class="error-text-row">
                  <AlertCircle :size="12" class="text-danger flex-shrink-0" />
                  <span class="error-msg">{{ task.error_message || 'Task failed during AI execution' }}</span>
                </div>

                <div class="failed-action-row">
                  <button
                    class="btn-inline-retry"
                    :disabled="retryingTaskIds.has(task.id)"
                    @click.stop="retryTask(task.id)"
                  >
                    <Loader2 v-if="retryingTaskIds.has(task.id)" class="animate-spin" :size="12" />
                    <RotateCcw v-else :size="12" />
                    <span>{{ retryingTaskIds.has(task.id) ? 'Retrying...' : 'Retry' }}</span>
                  </button>

                  <button
                    class="btn-inline-dismiss"
                    title="Dismiss task"
                    @click.stop="deleteTask(task.id)"
                  >
                    <Trash2 :size="12" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Popover Footer -->
        <div class="popover-footer">
          <button class="btn-full-queue" @click="navigateToQueue">
            <span>View Full Execution Queue</span>
            <ExternalLink :size="12" />
          </button>
        </div>
      </div>
    </Transition>

    <!-- Compact Floating Status Pill (Always visible) -->
    <div
      class="queue-status-pill-button"
      :class="[
        `state-${widgetState}`,
        { 'is-expanded': isOpen }
      ]"
      @click="toggleMenu"
      :title="failedCount > 0 ? `${failedCount} task(s) failed. Click to inspect & retry.` : 'AI Execution Queue Tracker'"
    >
      <div class="pill-left">
        <!-- Processor SVG Icon -->
        <div class="icon-wrapper">
          <Loader2 v-if="activeCount > 0" :size="15" class="animate-spin icon-active" />
          <AlertCircle v-else-if="failedCount > 0" :size="15" class="icon-failed" />
          <Cpu v-else :size="15" class="icon-healthy" />
        </div>

        <!-- Status Text -->
        <span class="pill-status-text">
          <template v-if="failedCount > 0">
            {{ failedCount }} task{{ failedCount > 1 ? 's' : '' }} failed
          </template>
          <template v-else-if="activeCount > 0">
            {{ activeCount }} active task{{ activeCount > 1 ? 's' : '' }}
          </template>
          <template v-else>
            AI Queue
          </template>
        </span>
      </div>

      <!-- State Counters & Dynamic Badges -->
      <div class="pill-right">
        <!-- Active Count Badge -->
        <span
          v-if="activeCount > 0"
          class="count-badge badge-active-count"
          title="Active running or queued tasks"
        >
          {{ activeCount }}
        </span>

        <!-- Failed Count Badge -->
        <span
          v-if="failedCount > 0"
          class="count-badge badge-failed-count"
          title="Failed tasks needing attention"
        >
          {{ failedCount }}
        </span>

        <!-- Chevron Toggle Indicator -->
        <ChevronUp
          :size="14"
          class="chevron-indicator"
          :class="{ 'is-rotated': isOpen }"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.floating-queue-widget {
  position: fixed;
  bottom: 24px;
  right: 84px;
  z-index: 520;
  user-select: none;
}

/* Compact Floating Status Pill Button */
.queue-status-pill-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 14px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(12px);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 140px;
}

.queue-status-pill-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-xl);
}

/* Dynamic State Styling */
.queue-status-pill-button.state-healthy {
  border-color: var(--status-offer-border, #22c55e);
}

.queue-status-pill-button.state-healthy:hover {
  border-color: var(--primary);
}

.queue-status-pill-button.state-active {
  border-color: var(--primary);
  box-shadow: 0 0 12px var(--primary-glow);
}

.queue-status-pill-button.state-failed {
  border-color: var(--danger, #ef4444);
  background-color: rgba(239, 68, 68, 0.05);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.2);
}

.queue-status-pill-button.is-expanded {
  border-color: var(--primary);
  background-color: var(--bg-elevated);
}

.pill-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-healthy {
  color: var(--status-offer-text, #22c55e);
}

.icon-active {
  color: var(--primary);
}

.icon-failed {
  color: var(--danger, #ef4444);
}

.pill-status-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.pill-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.count-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  line-height: 1.3;
}

.badge-active-count {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.badge-failed-count {
  background-color: var(--danger, #ef4444);
  color: #ffffff;
}

.chevron-indicator {
  color: var(--text-muted);
  transition: transform 0.2s ease;
}

.chevron-indicator.is-rotated {
  transform: rotate(180deg);
}

/* Dropdown Popover Overlay Menu */
.queue-popover-menu {
  position: absolute;
  bottom: calc(100% + 12px);
  right: 0;
  width: 370px;
  max-width: calc(100vw - 32px);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  backdrop-filter: blur(16px);
  z-index: 530;
}

/* Popover Header */
.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.loading-indicator {
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-icon-subtle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-icon-subtle:hover:not(:disabled) {
  background-color: var(--bg-elevated);
  color: var(--text-main);
}

/* Popover Stats Bar */
.popover-stats-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background-color: var(--bg-elevated);
  border-bottom: 1px solid var(--border-color);
}

.stat-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
}

.stat-badge.active-stat {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border-color: var(--primary-glow);
  font-weight: 600;
}

.stat-badge.failed-stat {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
  font-weight: 600;
}

.stat-badge.completed-stat {
  color: var(--status-offer-text);
}

/* Popover Body & Task List */
.popover-body {
  max-height: 300px;
  overflow-y: auto;
  padding: 10px;
  background-color: var(--bg-surface);
  scrollbar-gutter: stable;
}

.empty-queue-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 16px;
  text-align: center;
  gap: 6px;
}

.empty-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.empty-subtext {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0;
}

.popover-task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.popover-task-item {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color var(--transition-fast);
}

.popover-task-item.task-state-failed,
.popover-task-item.task-state-cancelled {
  border-color: var(--status-rejected-border);
  background-color: var(--status-rejected-bg);
}

.popover-task-item.task-state-processing {
  border-color: var(--primary-glow);
}

.task-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.task-meta-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.task-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

.task-id {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 600;
}

.task-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  font-size: 10px;
  font-family: var(--font-mono);
  font-weight: 600;
}

.pill-processing {
  background-color: var(--primary-subtle);
  color: var(--primary);
}

.pill-failed, .pill-cancelled {
  background-color: rgba(239, 68, 68, 0.15);
  color: var(--danger, #ef4444);
}

.pill-completed {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
}

.pill-queued {
  background-color: var(--bg-elevated);
  color: var(--text-muted);
}

.task-item-title {
  font-size: 12px;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-stage-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--primary);
  font-weight: 500;
}

.stage-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--primary);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.4; }
  50% { opacity: 1; }
  100% { opacity: 0.4; }
}

/* Failed Task Box & Inline Retry */
.task-failed-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 2px;
  padding: 8px;
  background-color: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-sm);
}

.error-text-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.error-msg {
  font-size: 11px;
  color: var(--status-rejected-text);
  line-height: 1.3;
  word-break: break-word;
}

.failed-action-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.btn-inline-retry {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--primary);
  color: #ffffff;
  border: none;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-inline-retry:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-inline-retry:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-inline-dismiss {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 6px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-inline-dismiss:hover {
  color: var(--danger, #ef4444);
  background-color: var(--status-rejected-bg);
}

/* Popover Footer */
.popover-footer {
  padding: 8px 12px;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
}

.btn-full-queue {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background-color: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-main);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  justify-content: center;
  transition: all var(--transition-fast);
}

.btn-full-queue:hover {
  background-color: var(--bg-elevated);
  border-color: var(--primary);
  color: var(--primary);
}

/* Popover Animation */
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}
</style>
