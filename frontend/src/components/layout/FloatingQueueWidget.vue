<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import { useQueueStore } from '../../stores/queueStore'
import { IntakeAPI } from '../../api/endpoints'
import {
  Cpu,
  Loader2,
  AlertCircle,
  Clock,
  RotateCcw,
  ExternalLink,
  X,
  RefreshCw,
  Trash2,
  Briefcase,
  UserCheck,
  Layers,
  Edit3,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()
const queueStore = useQueueStore()

const isOpen = ref(false)
const retryingTaskIds = ref(new Set())
const widgetContainerRef = ref(null)

// Fix JD Modal State
const showFixJDModal = ref(false)
const activeFixJDTask = ref(null)
const fixJDRawText = ref('')
const fixJDJobUrl = ref('')
const isSubmittingFixJD = ref(false)

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

  isSubmittingFixJD.value = true
  try {
    await queueStore.fixJDEvaluation(activeFixJDTask.value.id, {
      raw_text: fixJDRawText.value,
      job_url: fixJDJobUrl.value || null,
    })
    showFixJDModal.value = false
    activeFixJDTask.value = null
    await pollQueueStatus(true)
  } catch (err) {
    // Handled in queueStore
  } finally {
    isSubmittingFixJD.value = false
  }
}

// Filter tasks strictly to active (running/queued) and failed/error tasks from centralized queue store
const activeTasks = computed(() => queueStore.activeTasks)
const failedTasks = computed(() => queueStore.failedTasks)

// Active and Failed counters directly from store getters
const activeCount = computed(() => queueStore.activeCount)
const failedCount = computed(() => queueStore.failedCount)
const notificationCount = computed(() => queueStore.notificationCount)
const loading = computed(() => queueStore.loading)

// Focus scope list strictly for the popover menu (active + failed tasks only)
const focusedTasks = computed(() => [...activeTasks.value, ...failedTasks.value])

// Determine widget health state for dynamic border & badge coloring
const widgetState = computed(() => {
  if (activeCount.value > 0 && failedCount.value > 0) return 'mixed'
  if (failedCount.value > 0) return 'failed'
  if (activeCount.value > 0) return 'active'
  return 'hidden'
})

function getTaskDisplayTitle(task) {
  if (!task) return 'Task'
  if (task.result_json?.company && task.result_json?.position) {
    return `${task.result_json.company} - ${task.result_json.position}`
  }
  return task.title_hint || task.job_url || `Task #${task.id}`
}

async function pollQueueStatus(silent = true) {
  await queueStore.fetchTasks(silent)
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
    await queueStore.retryTask(taskId)
  } catch (err) {
    // Handled in store with toast & rollback
  } finally {
    const s = new Set(retryingTaskIds.value)
    s.delete(taskId)
    retryingTaskIds.value = s
  }
}

async function deleteTask(taskId) {
  try {
    await queueStore.deleteTask(taskId)
  } catch (err) {
    // Handled in store with toast & rollback
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
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div
    v-if="route.path !== '/queue' && notificationCount > 0"
    ref="widgetContainerRef"
    class="floating-queue-widget"
    :class="{ 'queue-on-chat': route.path === '/chat' }"
  >
    <!-- Interactive Overlay Dropdown Menu (Positioned directly above status pill) -->
    <Transition name="popover-fade">
      <div v-if="isOpen" class="queue-popover-menu">
        <!-- Menu Header -->
        <div class="popover-header">
          <div class="header-title-group">
            <Cpu :size="16" class="text-primary" />
            <span class="header-title">Active AI Execution Queue</span>
            <span v-if="loading" class="loading-indicator">
              <Loader2 :size="12" class="animate-spin text-muted" />
            </span>
          </div>

          <div class="header-actions">
            <button
              class="btn-icon-subtle"
              :disabled="loading"
              @click="pollQueueStatus(false)"
              title="Refresh active tasks"
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

        <!-- Summary Status Counter Bar (Focused: Active & Failed only) -->
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
        </div>

        <!-- Task List Content Area (Focused on Active & Failed Tasks Only) -->
        <div class="popover-body">
          <div v-if="focusedTasks.length === 0" class="empty-queue-state">
            <Cpu :size="28" class="text-muted opacity-50" />
            <p class="empty-title">Queue is idle</p>
            <p class="empty-subtext">No running background tasks or failed items requiring attention.</p>
          </div>

          <div v-else class="popover-task-list">
            <div
              v-for="task in focusedTasks"
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
                  <Clock v-else :size="10" />
                  <span>{{ task.status }}</span>
                </div>
              </div>

              <!-- Task Title -->
              <div class="task-item-title font-medium" :title="getTaskDisplayTitle(task)">
                {{ getTaskDisplayTitle(task) }}
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
                    v-if="isManualDescriptionEligible(task)"
                    class="btn-inline-fix-jd"
                    @click.stop="openFixJDModal(task)"
                    :title="task.raw_text && task.raw_text.trim() ? 'Manually edit the job description text' : 'Manually supply the job description text'"
                  >
                    <Edit3 :size="11" />
                    <span>{{ task.raw_text && task.raw_text.trim() ? 'Edit Description' : 'Provide Description' }}</span>
                  </button>

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

        <!-- Popover Footer with Dedicated View Shortcut -->
        <div class="popover-footer">
          <button class="btn-full-queue" @click="navigateToQueue">
            <span>View Full Queue & History</span>
            <ExternalLink :size="12" />
          </button>
        </div>
      </div>
    </Transition>

    <!-- Manual Job Description Modal Dialog -->
    <Teleport to="body">
      <div v-if="showFixJDModal" class="modal-backdrop" @click.self="showFixJDModal = false">
        <div class="modal-card modal-card-large animate-scale-in">
          <div class="modal-header">
            <Edit3 :size="20" class="text-primary flex-shrink-0" />
            <h3 class="modal-title">
              {{ activeFixJDTask?.raw_text && activeFixJDTask.raw_text.trim() ? 'Edit Job Description' : 'Provide Job Description' }} — Task #{{ activeFixJDTask?.id }}
            </h3>
          </div>
          <div class="modal-body">
            <p class="modal-subtext text-muted">
              Supply or paste the full job description text below to retry evaluation without relying on automated web scraping.
            </p>

            <div class="form-group">
              <label class="form-label">Job URL (Optional)</label>
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
    </Teleport>

    <!-- Floating Queue Trigger -->
    <button
      class="floating-queue-button"
      :class="[`state-${widgetState}`, { 'is-expanded': isOpen }]"
      type="button"
      @click.stop="toggleMenu"
      :title="`${notificationCount} queue task(s) need attention. Click to inspect.`"
    >
      <Cpu v-if="!isOpen" :size="22" class="queue-button-icon" />
      <X v-else :size="20" class="queue-button-icon" />

      <span
        v-if="activeCount > 0 || failedCount > 0"
        class="queue-count-badge"
        :class="widgetState === 'failed' ? 'badge-failed' : widgetState === 'mixed' ? 'badge-mixed' : 'badge-active'"
      >
        {{ notificationCount }}
      </span>
    </button>
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

.floating-queue-widget.queue-on-chat {
  right: 24px;
}

/* Floating Trigger Bubble */
.floating-queue-button {
  position: relative;
  width: 50px;
  height: 50px;
  min-width: 48px;
  min-height: 48px;
  border-radius: var(--radius-full);
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  border: 1px solid var(--primary-glow);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.28), 0 0 12px var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.floating-queue-button:hover {
  transform: scale(1.06);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35), 0 0 16px var(--primary);
}

/* Dynamic State Styling */
.floating-queue-button.state-active {
  background-color: var(--status-applied-text, #10b981);
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.4);
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.32), 0 0 12px rgba(16, 185, 129, 0.28);
}

.floating-queue-button.state-failed {
  background-color: var(--danger, #ef4444);
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.4);
  box-shadow: 0 4px 16px rgba(239, 68, 68, 0.35), 0 0 12px rgba(239, 68, 68, 0.3);
}

.floating-queue-button.state-mixed {
  background-color: var(--status-interview-text, #fbbf24);
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.4);
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.35), 0 0 12px rgba(251, 191, 36, 0.3);
}

.floating-queue-button.is-expanded {
  background-color: var(--bg-surface);
  color: var(--text-main);
  border-color: var(--border-color);
  box-shadow: var(--shadow-md);
}

.queue-button-icon {
  transition: transform var(--transition-fast);
}

.queue-count-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border: 2px solid var(--bg-app);
  border-radius: var(--radius-full);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.queue-count-badge.badge-active {
  background-color: var(--status-applied-text, #10b981);
}

.queue-count-badge.badge-failed {
  background-color: var(--danger, #ef4444);
}

.queue-count-badge.badge-mixed {
  background-color: var(--status-interview-text, #fbbf24);
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

.btn-inline-fix-jd {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  min-height: 36px;
  border-radius: var(--radius-sm);
  background-color: var(--primary);
  color: #ffffff;
  border: none;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-inline-fix-jd:hover {
  opacity: 0.9;
}

.btn-inline-retry {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  min-height: 36px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-inline-retry:hover:not(:disabled) {
  background-color: var(--bg-elevated);
  border-color: var(--primary);
}

.btn-inline-retry:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal Backdrop & Dialog Styles */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
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

.modal-card-large {
  max-width: 600px;
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
  gap: 12px;
}

.modal-subtext {
  font-size: 12px;
  margin: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
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

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
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

/* Mobile Responsive Adjustments for Floating Queue Widget */
@media (max-width: 767px) {
  .floating-queue-widget {
    display: none !important;
  }
}
</style>
