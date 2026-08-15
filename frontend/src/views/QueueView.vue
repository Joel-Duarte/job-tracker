<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { IntakeAPI } from '../api/endpoints'
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
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()

const tasks = ref([])
const loading = ref(false)
const isClearing = ref(false)
const statusFilter = ref('ALL') // 'ALL' | 'ACTIVE' | 'COMPLETED' | 'FAILED'
const typeFilter = ref('ALL') // 'ALL' | 'JOB_ASSESSMENT' | 'CV_EXTRACTION'
const searchQuery = ref('')

let pollTimer = null

const filteredTasks = computed(() => {
  return tasks.value.filter((t) => {
    // Status filter
    if (statusFilter.value === 'ACTIVE' && !['QUEUED', 'PROCESSING'].includes(t.status)) return false
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

const activeCount = computed(() => tasks.value.filter((t) => ['QUEUED', 'PROCESSING'].includes(t.status)).length)
const completedCount = computed(() => tasks.value.filter((t) => t.status === 'COMPLETED').length)
const failedCount = computed(() => tasks.value.filter((t) => ['FAILED', 'CANCELLED'].includes(t.status)).length)

async function fetchTasks(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await IntakeAPI.getEvaluations(100)
    tasks.value = res.data || []
  } catch (err) {
    if (!silent) uiStore.showToast(err.message, 'error')
  } finally {
    if (!silent) loading.value = false
  }
}

async function deleteTask(taskId) {
  try {
    await IntakeAPI.deleteEvaluation(taskId)
    tasks.value = tasks.value.filter((t) => t.id !== taskId)
    uiStore.showToast(`Task #${taskId} dismissed`, 'info')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function clearCompleted() {
  isClearing.value = true
  try {
    const res = await IntakeAPI.clearCompletedEvaluations()
    uiStore.showToast(`Cleared ${res.data.cleared_count || 0} completed/failed tasks`, 'success')
    await fetchTasks(true)
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isClearing.value = false
  }
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    // Poll fast if tasks are active, slower if idle
    fetchTasks(true)
  }, activeCount.value > 0 ? 1500 : 4000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  await fetchTasks()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="page-container">
    <!-- Header -->
    <div class="queue-header">
      <div>
        <div class="header-badge">
          <Cpu :size="14" />
          <span>AI Background Processing Queue</span>
        </div>
        <h1 class="page-title">Task Execution Queue</h1>
        <p class="page-subtitle">
          Real-time pipeline monitoring for asynchronous Job Intake assessments, CV profile extractions, and model tasks bounded by provider concurrency limits.
        </p>
      </div>

      <div class="header-actions">
        <button
          v-if="completedCount > 0 || failedCount > 0"
          class="btn btn-secondary btn-sm"
          :disabled="isClearing"
          @click="clearCompleted"
        >
          <Trash2 :size="14" />
          <span>Clear Finished</span>
        </button>
        <button class="btn btn-primary btn-sm" :disabled="loading" @click="fetchTasks(false)">
          <RefreshCw :class="{ 'animate-spin': loading }" :size="14" />
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Summary Metrics Cards -->
    <div class="metrics-row">
      <div class="metric-card" :class="{ highlight: activeCount > 0 }">
        <div class="metric-icon active">
          <Loader2 v-if="activeCount > 0" class="animate-spin" :size="18" />
          <Clock v-else :size="18" />
        </div>
        <div class="metric-content">
          <span class="metric-val">{{ activeCount }}</span>
          <span class="metric-label">Active / Queued</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon success">
          <CheckCircle2 :size="18" />
        </div>
        <div class="metric-content">
          <span class="metric-val">{{ completedCount }}</span>
          <span class="metric-label">Completed</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon danger">
          <AlertCircle :size="18" />
        </div>
        <div class="metric-content">
          <span class="metric-val">{{ failedCount }}</span>
          <span class="metric-label">Failed / Cancelled</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon neutral">
          <Layers :size="18" />
        </div>
        <div class="metric-content">
          <span class="metric-val">{{ tasks.length }}</span>
          <span class="metric-label">Total Recorded</span>
        </div>
      </div>
    </div>

    <!-- Filters & Search Bar -->
    <div class="filter-toolbar">
      <div class="filter-pills">
        <button
          class="filter-pill"
          :class="{ active: statusFilter === 'ALL' }"
          @click="statusFilter = 'ALL'"
        >
          All ({{ tasks.length }})
        </button>
        <button
          class="filter-pill"
          :class="{ active: statusFilter === 'ACTIVE' }"
          @click="statusFilter = 'ACTIVE'"
        >
          Active ({{ activeCount }})
        </button>
        <button
          class="filter-pill"
          :class="{ active: statusFilter === 'COMPLETED' }"
          @click="statusFilter = 'COMPLETED'"
        >
          Completed ({{ completedCount }})
        </button>
        <button
          class="filter-pill"
          :class="{ active: statusFilter === 'FAILED' }"
          @click="statusFilter = 'FAILED'"
        >
          Failed ({{ failedCount }})
        </button>
      </div>

      <div class="type-filter-group">
        <select v-model="typeFilter" class="form-select-sm">
          <option value="ALL">All Task Types</option>
          <option value="JOB_ASSESSMENT">Job Assessment</option>
          <option value="CV_EXTRACTION">CV Extraction</option>
        </select>

        <div class="search-box">
          <Search :size="13" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by title or URL..."
            class="search-input"
          />
        </div>
      </div>
    </div>

    <!-- Task List Cards -->
    <div v-if="filteredTasks.length" class="task-list-grid">
      <div
        v-for="task in filteredTasks"
        :key="task.id"
        class="queue-task-card animate-fade-in"
        :class="{
          'is-active': ['QUEUED', 'PROCESSING'].includes(task.status),
          'is-failed': ['FAILED', 'CANCELLED'].includes(task.status),
          'is-complete': task.status === 'COMPLETED',
        }"
      >
        <div class="task-card-header">
          <div class="task-identity">
            <span class="task-id-badge">#{{ task.id }}</span>
            <span
              class="task-type-badge"
              :class="task.task_type === 'CV_EXTRACTION' ? 'type-cv' : 'type-job'"
            >
              {{ task.task_type === 'CV_EXTRACTION' ? 'CV Extraction' : 'Job Assessment' }}
            </span>
            <span class="task-title-text" :title="task.title_hint">{{ task.title_hint }}</span>
          </div>

          <div class="task-status-actions">
            <!-- Status Badge -->
            <span
              class="status-pill"
              :class="{
                'status-processing': task.status === 'PROCESSING',
                'status-queued': task.status === 'QUEUED',
                'status-completed': task.status === 'COMPLETED',
                'status-failed': ['FAILED', 'CANCELLED'].includes(task.status),
              }"
            >
              <Loader2 v-if="task.status === 'PROCESSING'" class="animate-spin" :size="12" />
              <CheckCircle v-else-if="task.status === 'COMPLETED'" :size="12" />
              <AlertCircle v-else-if="['FAILED', 'CANCELLED'].includes(task.status)" :size="12" />
              <Clock v-else :size="12" />
              <span>{{ task.status }}</span>
            </span>

            <button
              class="btn btn-ghost btn-xs text-danger"
              title="Dismiss Task"
              @click="deleteTask(task.id)"
            >
              <Trash2 :size="13" />
            </button>
          </div>
        </div>

        <!-- URL or Info Line -->
        <div v-if="task.job_url" class="task-url-row">
          <a :href="task.job_url" target="_blank" rel="noopener noreferrer" class="task-url-link">
            <ExternalLink :size="11" />
            <span>{{ task.job_url }}</span>
          </a>
        </div>

        <!-- Animated Execution Stepper -->
        <div class="task-stepper-box">
          <!-- Stepper for Job Assessment -->
          <div v-if="task.task_type !== 'CV_EXTRACTION'" class="pipeline-stepper">
            <div
              class="pipe-step"
              :class="{
                active: task.stage === 'FETCHING',
                complete: ['EXTRACTING', 'MATCHING', 'ASSESSING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage),
              }"
            >
              <div class="step-num">1</div>
              <span>Fetch/Scrape</span>
            </div>

            <div
              class="pipe-step"
              :class="{
                active: task.stage === 'EXTRACTING',
                complete: ['MATCHING', 'ASSESSING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage),
              }"
            >
              <div class="step-num">2</div>
              <span>Extract Spec</span>
            </div>

            <div
              class="pipe-step"
              :class="{
                active: task.stage === 'MATCHING',
                complete: ['ASSESSING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage),
              }"
            >
              <div class="step-num">3</div>
              <span>Fuzzy Match</span>
            </div>

            <div
              class="pipe-step"
              :class="{
                active: task.stage === 'ASSESSING',
                complete: ['COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage),
              }"
            >
              <div class="step-num">4</div>
              <span>AI Audit & Score</span>
            </div>

            <div
              class="pipe-step"
              :class="{
                complete: ['COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage),
              }"
            >
              <div class="step-num">5</div>
              <span>Saved</span>
            </div>
          </div>

          <!-- Stepper for CV Extraction -->
          <div v-else class="pipeline-stepper">
            <div
              class="pipe-step"
              :class="{
                active: task.stage === 'SCRUBBING',
                complete: ['EXTRACTING', 'SAVING', 'COMPLETE'].includes(task.stage),
              }"
            >
              <div class="step-num">1</div>
              <span>PII Scrub</span>
            </div>

            <div
              class="pipe-step"
              :class="{
                active: task.stage === 'EXTRACTING',
                complete: ['SAVING', 'COMPLETE'].includes(task.stage),
              }"
            >
              <div class="step-num">2</div>
              <span>AI Extract</span>
            </div>

            <div
              class="pipe-step"
              :class="{
                active: task.stage === 'SAVING',
                complete: task.stage === 'COMPLETE',
              }"
            >
              <div class="step-num">3</div>
              <span>Save Profile</span>
            </div>
          </div>
        </div>

        <!-- Result Overview or Error Message -->
        <div v-if="task.error_message" class="task-error-box">
          <AlertCircle :size="14" class="text-danger flex-shrink-0" />
          <span>{{ task.error_message }}</span>
        </div>

        <div v-else-if="task.result_json" class="task-result-box">
          <!-- Job Assessment Result Preview -->
          <template v-if="task.task_type !== 'CV_EXTRACTION'">
            <div class="result-left">
              <span v-if="task.result_json.fit_score !== undefined" class="score-badge">
                {{ task.result_json.fit_score }}% Fit Score
              </span>
              <span v-if="task.result_json.company" class="text-xs text-muted">
                {{ task.result_json.company }} • {{ task.result_json.position }}
              </span>
            </div>
            <div class="result-actions">
              <router-link
                v-if="task.result_json.application_id"
                :to="'/'"
                class="btn btn-ghost btn-xs text-primary"
              >
                <span>View Application</span>
                <ExternalLink :size="11" />
              </router-link>
              <router-link
                v-else-if="task.result_json.staging_item_id"
                :to="'/staging'"
                class="btn btn-ghost btn-xs text-warning"
              >
                <span>View in Staging</span>
                <ExternalLink :size="11" />
              </router-link>
            </div>
          </template>

          <!-- CV Extraction Result Preview -->
          <template v-else>
            <div class="result-left">
              <span class="score-badge type-cv">
                Profile Active
              </span>
              <span class="text-xs text-muted">
                {{ task.result_json.extracted_skills_count || 0 }} skills extracted • {{ task.result_json.years_of_experience || 0 }} yrs exp
              </span>
            </div>
            <div class="result-actions">
              <router-link
                :to="'/profile'"
                class="btn btn-ghost btn-xs text-primary"
              >
                <span>View Profile</span>
                <ExternalLink :size="11" />
              </router-link>
            </div>
          </template>
        </div>

        <!-- Footer timestamps -->
        <div class="task-card-footer">
          <span class="time-meta">
            Created at {{ formatDate(task.created_at) }}
            <template v-if="task.completed_at">
              • Completed at {{ formatDate(task.completed_at) }}
            </template>
          </span>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-queue-box">
      <Cpu :size="36" class="text-muted" />
      <div class="empty-title">No Tasks in Queue</div>
      <p class="empty-sub">
        Asynchronous job qualification assessments and CV extractions will appear here in real time as they are processed.
      </p>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.queue-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background-color: var(--status-assessment-bg);
  color: var(--status-assessment-text);
  border: 1px solid var(--status-assessment-border);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 680px;
  margin-top: 4px;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}

@media (max-width: 768px) {
  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

.metric-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
}

.metric-card.highlight {
  border-color: var(--primary);
  background-color: rgba(59, 130, 246, 0.04);
}

.metric-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon.active {
  background-color: rgba(59, 130, 246, 0.12);
  color: var(--primary);
}

.metric-icon.success {
  background-color: rgba(16, 185, 129, 0.12);
  color: var(--text-success);
}

.metric-icon.danger {
  background-color: rgba(239, 68, 68, 0.12);
  color: var(--text-danger);
}

.metric-icon.neutral {
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

.metric-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-pills {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}

.filter-pill {
  border: none;
  background: transparent;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
}

.filter-pill:hover {
  color: var(--text-main);
}

.filter-pill.active {
  background-color: var(--bg-elevated);
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
}

.type-filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-select-sm {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 5px 8px;
  font-size: 11px;
  color: var(--text-main);
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 8px;
  color: var(--text-muted);
}

.search-input {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 5px 8px 5px 26px;
  font-size: 11px;
  color: var(--text-main);
  width: 180px;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary);
  width: 220px;
}

.task-list-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.queue-task-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all var(--transition-fast);
}

.queue-task-card.is-active {
  border-left: 3px solid var(--primary);
}

.queue-task-card.is-complete {
  border-left: 3px solid var(--text-success);
}

.queue-task-card.is-failed {
  border-left: 3px solid var(--text-danger);
}

.task-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.task-identity {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-id-badge {
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-tertiary);
}

.task-type-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.type-job {
  background-color: rgba(59, 130, 246, 0.08);
  color: var(--primary);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.type-cv {
  background-color: rgba(16, 185, 129, 0.08);
  color: var(--text-success);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.task-title-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  max-width: 480px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-status-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.status-processing {
  background-color: rgba(59, 130, 246, 0.12);
  color: var(--primary);
}

.status-queued {
  background-color: rgba(245, 158, 11, 0.12);
  color: var(--text-warning);
}

.status-completed {
  background-color: rgba(16, 185, 129, 0.12);
  color: var(--text-success);
}

.status-failed {
  background-color: rgba(239, 68, 68, 0.12);
  color: var(--text-danger);
}

.task-url-row {
  font-size: 11px;
}

.task-url-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  text-decoration: none;
  word-break: break-all;
}

.task-url-link:hover {
  color: var(--primary);
}

.task-stepper-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}

.pipeline-stepper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.pipe-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.5;
  transition: all var(--transition-fast);
}

.pipe-step.active {
  opacity: 1;
  color: var(--primary);
  font-weight: 600;
}

.pipe-step.complete {
  opacity: 0.9;
  color: var(--text-success);
}

.step-num {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
}

.pipe-step.active .step-num {
  background-color: var(--primary);
  color: white;
  border-color: var(--primary);
}

.pipe-step.complete .step-num {
  background-color: var(--text-success);
  color: white;
  border-color: var(--text-success);
}

.task-error-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background-color: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-danger);
}

.task-result-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: rgba(16, 185, 129, 0.04);
  border: 1px solid rgba(16, 185, 129, 0.18);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.result-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.score-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: rgba(16, 185, 129, 0.12);
  color: var(--text-success);
}

.score-badge.type-cv {
  background-color: rgba(59, 130, 246, 0.12);
  color: var(--primary);
}

.task-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
}

.empty-queue-box {
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  padding: 48px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.empty-sub {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 400px;
  line-height: 1.5;
}
</style>
