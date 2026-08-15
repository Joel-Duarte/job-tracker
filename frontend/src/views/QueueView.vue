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
  UserCheck,
  ArrowRight,
  SlidersHorizontal,
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
    fetchTasks(true)
  }, activeCount.value > 0 ? 1500 : 4000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  fetchTasks()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="page-container queue-page-layout">
    <!-- Header Area -->
    <div class="queue-header-section">
      <div class="header-titles">
        <h1 class="page-title">AI Processing Queue</h1>
        <p class="page-subtitle">
          Real-time background execution queue for automated Job Lead evaluations and Candidate CV extractions.
        </p>
      </div>

      <!-- Quick Metrics Grid -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon-box active-box">
            <Cpu :size="18" class="text-primary" />
          </div>
          <div class="metric-data">
            <span class="metric-val">{{ activeCount }}</span>
            <span class="metric-lbl">Actively Processing</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-box complete-box">
            <CheckCircle :size="18" class="text-success" />
          </div>
          <div class="metric-data">
            <span class="metric-val">{{ completedCount }}</span>
            <span class="metric-lbl">Completed</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-box failed-box">
            <AlertCircle :size="18" class="text-danger" />
          </div>
          <div class="metric-data">
            <span class="metric-val">{{ failedCount }}</span>
            <span class="metric-lbl">Failed / Cancelled</span>
          </div>
        </div>

        <div class="metric-card action-card">
          <button
            class="btn btn-secondary btn-sm btn-clear-all"
            :disabled="isClearing || (completedCount === 0 && failedCount === 0)"
            @click="clearCompleted"
          >
            <Loader2 v-if="isClearing" class="animate-spin" :size="14" />
            <Trash2 v-else :size="14" />
            <span>Clear Completed</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Filter & Search Toolbar -->
    <div class="queue-toolbar">
      <div class="toolbar-left">
        <!-- Status Filter Pills -->
        <div class="filter-pills-group">
          <button
            class="filter-pill"
            :class="{ active: statusFilter === 'ALL' }"
            @click="statusFilter = 'ALL'"
          >
            <span>All Status</span>
            <span class="pill-badge">{{ tasks.length }}</span>
          </button>
          <button
            class="filter-pill"
            :class="{ active: statusFilter === 'ACTIVE' }"
            @click="statusFilter = 'ACTIVE'"
          >
            <span class="live-dot" v-if="activeCount > 0"></span>
            <span>Processing</span>
            <span class="pill-badge">{{ activeCount }}</span>
          </button>
          <button
            class="filter-pill"
            :class="{ active: statusFilter === 'COMPLETED' }"
            @click="statusFilter = 'COMPLETED'"
          >
            <span>Completed</span>
            <span class="pill-badge">{{ completedCount }}</span>
          </button>
          <button
            v-if="failedCount > 0"
            class="filter-pill"
            :class="{ active: statusFilter === 'FAILED' }"
            @click="statusFilter = 'FAILED'"
          >
            <span>Failed</span>
            <span class="pill-badge">{{ failedCount }}</span>
          </button>
        </div>

        <!-- Task Type Selector -->
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
        </div>
      </div>

      <div class="toolbar-right">
        <div class="search-input-box">
          <Search :size="14" class="search-icon text-muted" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by title or URL..."
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
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="queue-content-scroll">
      <!-- Empty State -->
      <div v-if="filteredTasks.length === 0" class="empty-state-box">
        <Clock :size="40" class="empty-state-icon" />
        <h3 class="empty-state-title">No tasks in queue</h3>
        <p class="empty-state-desc">
          {{ tasks.length === 0 ? 'Queue is currently idle. Ingest a job posting or upload a CV to initiate processing.' : 'No tasks match your active filters.' }}
        </p>
      </div>

      <!-- Task Cards List -->
      <div v-else class="tasks-card-list">
        <div
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-card animate-fade-in"
          :class="`task-card-${task.status.toLowerCase()}`"
        >
          <!-- Task Card Header -->
          <div class="task-card-top">
            <div class="task-header-left">
              <span class="task-id-tag">#{{ task.id }}</span>
              <span
                class="task-type-tag"
                :class="task.task_type === 'CV_EXTRACTION' ? 'type-cv' : 'type-job'"
              >
                <component :is="task.task_type === 'CV_EXTRACTION' ? UserCheck : Briefcase" :size="12" />
                <span>{{ task.task_type === 'CV_EXTRACTION' ? 'CV Profile Extraction' : 'Job Assessment' }}</span>
              </span>
              <span class="task-title-text" :title="task.title_hint || task.job_url">
                {{ task.title_hint || task.job_url || `Task #${task.id}` }}
              </span>
            </div>

            <div class="task-header-right">
              <!-- Live Status Pill -->
              <div class="status-badge-pill" :class="`pill-${task.status.toLowerCase()}`">
                <Loader2 v-if="task.status === 'PROCESSING'" class="animate-spin" :size="12" />
                <CheckCircle v-else-if="task.status === 'COMPLETED'" :size="12" />
                <AlertCircle v-else-if="['FAILED', 'CANCELLED'].includes(task.status)" :size="12" />
                <Clock v-else :size="12" />
                <span>{{ task.status }}</span>
              </div>

              <!-- Delete/Dismiss Button -->
              <button
                class="btn-icon-dismiss"
                title="Dismiss task"
                @click="deleteTask(task.id)"
              >
                <Trash2 :size="13" />
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
            <!-- 1. JOB ASSESSMENT STEPPER (5 Stages) -->
            <div v-if="task.task_type !== 'CV_EXTRACTION'" class="pipeline-stepper job-stepper">
              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'FETCHING',
                  done: ['EXTRACTING', 'MATCHING', 'ASSESSING', 'SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">1</div>
                <span class="node-label">Scrape / Ingest</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'EXTRACTING',
                  done: ['MATCHING', 'ASSESSING', 'SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">2</div>
                <span class="node-label">Extract Specs &amp; Skills</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'MATCHING',
                  done: ['ASSESSING', 'SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">3</div>
                <span class="node-label">Match CV Overlap</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'ASSESSING',
                  done: ['SAVING', 'COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">4</div>
                <span class="node-label">Qualitative Fit &amp; Tips</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  done: ['COMPLETE', 'STAGED_DUPLICATE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">5</div>
                <span class="node-label">{{ task.stage === 'STAGED_DUPLICATE' ? 'Staged' : 'Complete' }}</span>
              </div>
            </div>

            <!-- 2. CV EXTRACTION STEPPER (4 Stages) -->
            <div v-else class="pipeline-stepper cv-stepper">
              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'SCRUBBING',
                  done: ['EXTRACTING', 'SAVING', 'COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">1</div>
                <span class="node-label">Privacy Scrubbing</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'EXTRACTING',
                  done: ['SAVING', 'COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">2</div>
                <span class="node-label">Skills &amp; Domain Extraction</span>
              </div>

              <div
                class="stepper-node"
                :class="{
                  active: task.stage === 'SAVING',
                  done: ['COMPLETE'].includes(task.stage) || task.status === 'COMPLETED',
                }"
              >
                <div class="node-bullet">3</div>
                <span class="node-label">Update Candidate Profile</span>
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
          </div>

          <!-- Error Alert Banner -->
          <div v-if="task.error_message" class="task-error-box">
            <AlertCircle :size="14" class="text-danger flex-shrink-0" />
            <span>{{ task.error_message }}</span>
          </div>

          <!-- Result Footer & Contextual Actions -->
          <div v-else-if="task.status === 'COMPLETED' && task.result_json" class="task-card-footer">
            <!-- Job Assessment Context -->
            <template v-if="task.task_type !== 'CV_EXTRACTION'">
              <div class="footer-left">
                <span v-if="task.result_json.match_score !== undefined || task.result_json.fit_score !== undefined" class="score-badge">
                  {{ task.result_json.match_score ?? task.result_json.fit_score }}% Match
                </span>
                <span class="footer-meta-text">
                  {{ task.result_json.company || 'Company' }} • {{ task.result_json.position || 'Position' }}
                </span>
              </div>

              <div class="footer-right">
                <router-link
                  to="/assessments"
                  class="btn btn-primary btn-xs"
                >
                  <span>Review Dossier</span>
                  <ArrowRight :size="12" />
                </router-link>
              </div>
            </template>

            <!-- CV Extraction Context -->
            <template v-else>
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
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.queue-page-layout {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--navbar-height));
  overflow: hidden;
  background-color: var(--bg-app);
}

/* Header Section */
.queue-header-section {
  padding: 20px 24px 16px 24px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0;
}

.header-titles {
  text-align: center;
}

.page-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 22px;
  color: var(--text-main);
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.metric-card.action-card {
  justify-content: center;
}

.btn-clear-all {
  width: 100%;
  justify-content: center;
}

.metric-icon-box {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.active-box {
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
}

.complete-box {
  background-color: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
}

.failed-box {
  background-color: var(--status-rejected-bg);
  border: 1px solid var(--status-rejected-border);
}

.metric-data {
  display: flex;
  flex-direction: column;
}

.metric-val {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.metric-lbl {
  font-size: 11px;
  color: var(--text-secondary);
}

/* Toolbar */
.queue-toolbar {
  padding: 12px 24px;
  background-color: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-pills-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.filter-pill:hover {
  border-color: var(--border-focus);
  color: var(--text-main);
}

.filter-pill.active {
  background-color: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
}

.pill-badge {
  font-size: 10px;
  font-weight: 700;
  background-color: rgba(255, 255, 255, 0.2);
  padding: 1px 5px;
  border-radius: var(--radius-full);
}

.filter-pill:not(.active) .pill-badge {
  background-color: var(--bg-elevated);
  color: var(--text-muted);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--primary);
  box-shadow: 0 0 6px var(--primary-glow);
  animation: pulse-ring 1.5s infinite;
}

.type-filter-group {
  display: flex;
  align-items: center;
  gap: 4px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border-radius: 4px;
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

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-input-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
}

.search-input {
  padding: 6px 12px 6px 30px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  width: 220px;
}

.search-input:focus {
  border-color: var(--primary);
  outline: none;
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
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background-color: var(--status-rejected-bg);
  border: 1px solid var(--status-rejected-border);
  color: var(--status-rejected-text);
  font-size: 12px;
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
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
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
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 var(--primary-glow); }
  70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr 1fr;
  }
  .pipeline-stepper {
    overflow-x: auto;
  }
}
</style>
