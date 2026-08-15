<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { IntakeAPI } from '../api/endpoints'
import {
  Sparkles,
  Link as LinkIcon,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Building2,
  DollarSign,
  MapPin,
  Loader2,
  ArrowRight,
  ShieldCheck,
  Check,
  X,
  Info,
  Copy,
  Puzzle,
  Globe,
  Layers,
  ArrowDownCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Trash2,
  CheckCircle,
  Inbox,
  RefreshCw,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()
const appStore = useApplicationsStore()

// Input Form State
const jobUrl = ref('')
const jobText = ref('')
const isEnqueuing = ref(false)
const jdTextareaRef = ref(null)

// Queue & Evaluations State
const evaluationTasks = ref([])
const loadingEvaluations = ref(false)
const expandedTaskIds = ref(new Set())
const processingTaskIds = ref(new Set())
let pollingInterval = null

// Extension Config State
const copiedUrl = ref(false)
const copiedJd = ref(false)
const urlEndpoint = ref('Loading...')
const jdEndpoint = ref('Loading...')

// Computed Lists
const activeTasks = computed(() =>
  evaluationTasks.value.filter((t) => t.status === 'QUEUED' || t.status === 'PROCESSING')
)

const completedTasks = computed(() =>
  evaluationTasks.value.filter((t) => t.status === 'COMPLETED' && t.result_json)
)

const failedTasks = computed(() =>
  evaluationTasks.value.filter((t) => t.status === 'FAILED')
)

async function fetchExtensionConfig() {
  try {
    const res = await IntakeAPI.getExtensionConfig()
    if (res.data?.url_endpoint) {
      urlEndpoint.value = res.data.url_endpoint
      jdEndpoint.value = res.data.jd_endpoint
    }
  } catch (err) {
    const host = window.location.hostname || 'localhost'
    const port = window.location.port === '5173' ? '8000' : window.location.port || '8000'
    const proto = window.location.protocol || 'http:'
    urlEndpoint.value = `${proto}//${host}:${port}/api/v1/intake/url`
    jdEndpoint.value = `${proto}//${host}:${port}/api/v1/intake/jd`
  }
}

function copyToClipboard(val, type) {
  navigator.clipboard.writeText(val)
  if (type === 'url') {
    copiedUrl.value = true
    setTimeout(() => { copiedUrl.value = false }, 2000)
  } else {
    copiedJd.value = true
    setTimeout(() => { copiedJd.value = false }, 2000)
  }
  uiStore.showToast('Endpoint URL copied to clipboard!', 'info')
}

function clearForm() {
  jobUrl.value = ''
  jobText.value = ''
}

async function loadEvaluations(silent = false) {
  if (!silent) loadingEvaluations.value = true
  try {
    const res = await IntakeAPI.getEvaluations(50)
    evaluationTasks.value = res.data || []

    // Auto-expand the latest completed task if none expanded
    if (expandedTaskIds.value.size === 0 && completedTasks.value.length > 0) {
      expandedTaskIds.value.add(completedTasks.value[0].id)
    }
  } catch (err) {
    if (!silent) uiStore.showToast(err.message, 'error')
  } finally {
    if (!silent) loadingEvaluations.value = false
  }
}

async function enqueueLead() {
  const urlVal = jobUrl.value.trim()
  const textVal = jobText.value.trim()

  if (!urlVal && !textVal) {
    uiStore.showToast('Please enter a Job Posting URL or paste the job description text.', 'error')
    return
  }

  isEnqueuing.value = true
  try {
    const res = await IntakeAPI.enqueueAssessment({
      url: urlVal || null,
      text: textVal || null,
    })

    // Immediately clear input fields for continuous workflow
    jobUrl.value = ''
    jobText.value = ''

    uiStore.showToast(`Lead '${res.data.title_hint}' enqueued for AI evaluation!`, 'success')
    await loadEvaluations(true)
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isEnqueuing.value = false
  }
}

function toggleExpandTask(taskId) {
  if (expandedTaskIds.value.has(taskId)) {
    expandedTaskIds.value.delete(taskId)
  } else {
    expandedTaskIds.value.add(taskId)
  }
}

async function confirmAndSaveLead(task, targetStatus = 'ASSESSMENT', forceNew = false) {
  if (!task.result_json) return
  const result = task.result_json
  processingTaskIds.value.add(task.id)

  try {
    const res = await IntakeAPI.confirmAssessment({
      company: result.company,
      position: result.position,
      status: targetStatus,
      job_url: task.job_url || null,
      application_id: !forceNew ? result.application_id : null,
      force_new: forceNew,
      description_markdown: task.raw_text || result.summary,
      salary_min: result.salary_min,
      salary_max: result.salary_max,
      currency: result.currency || 'USD',
      location: result.location,
      work_model: result.work_model,
      required_skills: [
        ...(result.matching_skills || []),
        ...(result.missing_skills || []),
      ],
    })

    uiStore.showToast(`Updated '${res.data.company || 'Job'}' in ${targetStatus}!`, 'success')
    appStore.fetchApplications()

    // Dismiss evaluated task from queue
    await IntakeAPI.deleteEvaluation(task.id)
    await loadEvaluations(true)
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    processingTaskIds.value.delete(task.id)
  }
}

async function deleteTask(taskId) {
  try {
    await IntakeAPI.deleteEvaluation(taskId)
    evaluationTasks.value = evaluationTasks.value.filter((t) => t.id !== taskId)
    uiStore.showToast('Evaluation dismissed', 'info')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

function retryFailedWithPaste(task) {
  if (task.job_url) {
    jobUrl.value = task.job_url
  }
  if (task.raw_text) {
    jobText.value = task.raw_text
  }
  deleteTask(task.id)
  nextTick(() => {
    jdTextareaRef.value?.focus()
  })
}

function formatStageLabel(stage) {
  switch (stage) {
    case 'FETCHING':
      return 'Fetching URL / Scraping'
    case 'EXTRACTING':
      return 'Extracting Specs & Roles'
    case 'MATCHING':
      return 'Matching CV Keyword Overlap'
    case 'ASSESSING':
      return 'Running Qualitative AI Fit'
    case 'COMPLETE':
      return 'Ready for Review'
    case 'FAILED':
      return 'Failed'
    default:
      return stage
  }
}

onMounted(() => {
  fetchExtensionConfig()
  loadEvaluations()

  // Poll active tasks every 2.5s
  pollingInterval = setInterval(() => {
    if (activeTasks.value.length > 0) {
      loadEvaluations(true)
    }
  }, 2500)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})
</script>

<template>
  <div class="page-container">
    <!-- Header -->
    <div class="intake-header">
      <div class="header-badge">
        <Sparkles :size="14" />
        <span>Pre-Application Intelligence</span>
      </div>
      <h1 class="page-title">Job Lead Intake & AI Evaluation Queue</h1>
      <p class="page-subtitle">
        Paste a career URL or job description. Leads are queued and evaluated safely within provider concurrency limits, calculating keyword overlap against your CV profile before applying.
      </p>
    </div>

    <!-- LinkedIn Advisory Banner -->
    <div class="advisory-banner">
      <Info :size="16" class="text-primary flex-shrink-0" />
      <span>
        <strong>Continuous Lead Input:</strong> Input fields clear immediately on submit so you can paste multiple job leads in rapid succession. Track live progress and review completed assessments below.
      </span>
    </div>

    <!-- Browser Extension Endpoints Configuration Bar -->
    <div class="extension-config-card">
      <div class="card-top">
        <div class="card-title">
          <Puzzle :size="15" class="text-primary" />
          <span>Browser Extension Endpoints</span>
        </div>
        <span class="text-xs text-muted">Paste these endpoints in your extension settings</span>
      </div>

      <div class="endpoints-grid">
        <!-- URL Endpoint -->
        <div class="endpoint-item">
          <div class="endpoint-meta">
            <Globe :size="14" class="text-secondary" />
            <span class="endpoint-name">URL Endpoint (Send URL):</span>
          </div>
          <div class="endpoint-input-row">
            <span class="endpoint-val font-mono">{{ urlEndpoint }}</span>
            <button class="btn btn-secondary btn-xs" @click="copyToClipboard(urlEndpoint, 'url')">
              <Check v-if="copiedUrl" :size="12" class="text-success" />
              <Copy v-else :size="12" />
              <span>{{ copiedUrl ? 'Copied' : 'Copy' }}</span>
            </button>
          </div>
        </div>

        <!-- JD Elements Endpoint -->
        <div class="endpoint-item">
          <div class="endpoint-meta">
            <Layers :size="14" class="text-secondary" />
            <span class="endpoint-name">JD Elements Endpoint (Send DOM):</span>
          </div>
          <div class="endpoint-input-row">
            <span class="endpoint-val font-mono">{{ jdEndpoint }}</span>
            <button class="btn btn-secondary btn-xs" @click="copyToClipboard(jdEndpoint, 'jd')">
              <Check v-if="copiedJd" :size="12" class="text-success" />
              <Copy v-else :size="12" />
              <span>{{ copiedJd ? 'Copied' : 'Copy' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Intake Input Card -->
    <div class="intake-card">
      <div class="input-section">
        <label class="section-label">
          <LinkIcon :size="15" />
          <span>Job Posting URL (Greenhouse, Lever, Workday, etc.)</span>
        </label>
        <input
          v-model="jobUrl"
          type="url"
          placeholder="https://boards.greenhouse.io/company/jobs/123456"
          class="form-input"
          @keydown.enter="enqueueLead"
        />
      </div>

      <div class="input-section">
        <div class="label-row">
          <label class="section-label">
            <FileText :size="15" />
            <span>Job Description & Requirements Text</span>
          </label>
          <span class="text-xs text-primary font-semibold">
            * Include Company Name and Role in text if URL is not provided
          </span>
        </div>
        <textarea
          ref="jdTextareaRef"
          v-model="jobText"
          rows="5"
          placeholder="e.g. Stripe - Staff Backend Engineer&#10;&#10;About the Role...&#10;Responsibilities...&#10;Requirements: Python, PostgreSQL, Distributed Systems..."
          class="form-textarea font-mono text-xs"
        ></textarea>
      </div>

      <div class="intake-actions">
        <button
          v-if="jobUrl || jobText"
          class="btn btn-secondary"
          :disabled="isEnqueuing"
          @click="clearForm"
        >
          <X :size="15" />
          <span>Clear</span>
        </button>
        <button
          class="btn btn-primary btn-assess"
          :disabled="isEnqueuing || (!jobUrl.trim() && !jobText.trim())"
          @click="enqueueLead"
        >
          <Loader2 v-if="isEnqueuing" class="animate-spin" :size="16" />
          <Sparkles v-else :size="16" />
          <span>{{ isEnqueuing ? 'Enqueuing Lead...' : 'Evaluate Job Fit (Add to Queue)' }}</span>
        </button>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- EVALUATION QUEUE & REVIEW STACK SECTION -->
    <!-- ================================================================= -->
    <div class="queue-section">
      <div class="queue-section-header">
        <div class="queue-title-group">
          <Clock :size="18" class="text-primary" />
          <h2 class="queue-title">Evaluation Queue & Ready Reviews</h2>
          <span v-if="activeTasks.length > 0" class="badge badge-interview">
            {{ activeTasks.length }} Processing
          </span>
          <span v-if="completedTasks.length > 0" class="badge badge-offer">
            {{ completedTasks.length }} Ready for Review
          </span>
        </div>
        <button class="btn btn-secondary btn-xs" @click="loadEvaluations(false)">
          <RefreshCw :size="12" :class="{ 'animate-spin': loadingEvaluations }" />
          <span>Refresh</span>
        </button>
      </div>

      <!-- 1. Active In-Progress Tasks -->
      <div v-if="activeTasks.length > 0" class="active-tasks-list">
        <div v-for="task in activeTasks" :key="task.id" class="active-task-card animate-fade-in">
          <div class="task-card-main">
            <div class="task-spinner-box">
              <Loader2 class="animate-spin text-primary" :size="18" />
            </div>
            <div class="task-info">
              <div class="task-title font-semibold">{{ task.title_hint }}</div>
              <div class="task-stage-row">
                <span class="badge badge-applied font-mono text-xs">{{ task.status }}</span>
                <span class="task-stage-text">{{ formatStageLabel(task.stage) }}</span>
                <span v-if="task.job_url" class="task-url-text font-mono text-xs">{{ task.job_url.slice(0, 45) }}...</span>
              </div>
            </div>
          </div>
          <button class="btn btn-danger btn-xs" @click="deleteTask(task.id)" title="Cancel Evaluation">
            <X :size="13" />
          </button>
        </div>
      </div>

      <!-- 2. Failed Tasks Alert -->
      <div v-if="failedTasks.length > 0" class="failed-tasks-list">
        <div v-for="task in failedTasks" :key="task.id" class="failed-task-card animate-fade-in">
          <div class="failed-card-main">
            <AlertTriangle :size="18" class="text-danger flex-shrink-0" />
            <div class="failed-info">
              <div class="failed-title font-semibold">{{ task.title_hint }} (Scrape Failed)</div>
              <div class="failed-msg text-xs">{{ task.error_message || 'Unable to extract job specs automatically.' }}</div>
            </div>
          </div>
          <div class="failed-actions">
            <button class="btn btn-secondary btn-xs" @click="retryFailedWithPaste(task)">
              <span>Paste JD & Retry</span>
            </button>
            <button class="btn btn-danger btn-xs" @click="deleteTask(task.id)">
              <Trash2 :size="12" />
            </button>
          </div>
        </div>
      </div>

      <!-- 3. Completed Ready-for-Review Assessments Stack -->
      <div v-if="completedTasks.length > 0" class="completed-tasks-stack">
        <div
          v-for="task in completedTasks"
          :key="task.id"
          class="review-card animate-fade-in"
          :class="{ expanded: expandedTaskIds.has(task.id) }"
        >
          <!-- Review Card Summary Header -->
          <div class="review-header" @click="toggleExpandTask(task.id)">
            <div class="review-header-left">
              <div class="company-icon-box">
                <Building2 :size="20" />
              </div>
              <div>
                <div class="review-company-title">{{ task.result_json.company }}</div>
                <div class="review-role-title">{{ task.result_json.position }}</div>
              </div>
            </div>

            <!-- Scores & Actions -->
            <div class="review-header-right">
              <div class="scores-compact">
                <div class="score-pill">
                  <span class="score-pill-num font-mono">{{ task.result_json.programmatic_match_score || 0 }}%</span>
                  <span class="score-pill-lbl">Overlap</span>
                </div>
                <div class="score-pill score-pill-ai">
                  <span class="score-pill-num font-mono">{{ task.result_json.fit_score }}%</span>
                  <span class="score-pill-lbl">AI Fit</span>
                </div>
              </div>

              <span
                class="badge"
                :class="task.result_json.recommendation === 'APPLY_STRONGLY' ? 'badge-offer' : 'badge-applied'"
              >
                {{ task.result_json.recommendation }}
              </span>

              <button class="btn-icon" @click.stop="toggleExpandTask(task.id)">
                <ChevronUp v-if="expandedTaskIds.has(task.id)" :size="16" />
                <ChevronDown v-else :size="16" />
              </button>
            </div>
          </div>

          <!-- Expanded Assessment Breakdown -->
          <div v-if="expandedTaskIds.has(task.id)" class="review-body animate-fade-in">
            <!-- Quick Metrics Grid -->
            <div class="metrics-grid">
              <div class="metric-card">
                <DollarSign :size="16" class="metric-icon" />
                <div>
                  <div class="metric-k">Compensation</div>
                  <div class="metric-v">
                    <span v-if="task.result_json.salary_min || task.result_json.salary_max">
                      ${{ task.result_json.salary_min?.toLocaleString() }} - ${{ task.result_json.salary_max?.toLocaleString() }} {{ task.result_json.currency || 'USD' }}
                    </span>
                    <span v-else class="text-muted">Not specified</span>
                  </div>
                </div>
              </div>

              <div class="metric-card">
                <MapPin :size="16" class="metric-icon" />
                <div>
                  <div class="metric-k">Location & Model</div>
                  <div class="metric-v">
                    {{ task.result_json.location || 'Location Unspecified' }}
                    <span v-if="task.result_json.work_model">({{ task.result_json.work_model }})</span>
                  </div>
                </div>
              </div>

              <div class="metric-card">
                <ShieldCheck :size="16" class="metric-icon" />
                <div>
                  <div class="metric-k">AI Recommendation</div>
                  <div class="metric-v font-semibold text-primary">
                    {{ task.result_json.recommendation }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Skills Matrix -->
            <div class="skills-matrix">
              <div class="matrix-col">
                <div class="matrix-title text-success">
                  <Check :size="15" />
                  <span>Matching Strengths & Skills ({{ task.result_json.matching_skills?.length || 0 }})</span>
                </div>
                <div class="tags-container">
                  <span v-for="s in task.result_json.matching_skills" :key="s" class="tag-chip tag-match">
                    {{ s }}
                  </span>
                </div>
              </div>

              <div class="matrix-col">
                <div class="matrix-title text-danger">
                  <AlertTriangle :size="15" />
                  <span>Missing Qualification Keywords ({{ task.result_json.missing_skills?.length || 0 }})</span>
                </div>
                <div class="tags-container">
                  <span v-for="m in task.result_json.missing_skills" :key="m" class="tag-chip tag-miss">
                    {{ m }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Pros & Cons -->
            <div class="pros-cons-grid">
              <div v-if="task.result_json.pros?.length" class="pro-con-box">
                <div class="pro-con-title">Key Advantages / Pros</div>
                <ul class="pro-con-list">
                  <li v-for="(p, idx) in task.result_json.pros" :key="idx">{{ p }}</li>
                </ul>
              </div>

              <div v-if="task.result_json.cons?.length" class="pro-con-box">
                <div class="pro-con-title">Potential Caveats / Cons</div>
                <ul class="pro-con-list">
                  <li v-for="(c, idx) in task.result_json.cons" :key="idx">{{ c }}</li>
                </ul>
              </div>
            </div>

            <!-- Narrative Evaluation -->
            <div class="evaluation-summary">
              <div class="eval-title">Evaluation Summary</div>
              <p class="eval-text">{{ task.result_json.summary }}</p>
            </div>

            <!-- Duplicate Advisory Banner if applicable -->
            <div v-if="task.stage === 'STAGED_DUPLICATE' || task.result_json?.is_duplicate" class="advisory-banner mt-3">
              <AlertTriangle :size="16" class="text-warning flex-shrink-0" />
              <span>
                <strong>Existing Application Detected:</strong> A prior application for this role was found in your pipeline. You can choose to create a fresh application or update the existing record.
              </span>
            </div>

            <!-- Confirmation Action Bar -->
            <div class="review-action-bar">
              <button class="btn btn-danger btn-sm" @click="deleteTask(task.id)">
                <Trash2 :size="14" />
                <span>Dismiss Lead</span>
              </button>

              <div v-if="task.stage === 'STAGED_DUPLICATE' || task.result_json?.is_duplicate" class="confirm-buttons">
                <button
                  class="btn btn-secondary btn-sm"
                  :disabled="processingTaskIds.has(task.id)"
                  @click="confirmAndSaveLead(task, 'ASSESSMENT', true)"
                >
                  <Sparkles :size="14" class="text-primary" />
                  <span>Create as New Application</span>
                </button>

                <button
                  class="btn btn-primary btn-sm"
                  :disabled="processingTaskIds.has(task.id)"
                  @click="confirmAndSaveLead(task, 'ASSESSMENT', false)"
                >
                  <CheckCircle2 :size="14" />
                  <span>Update Existing Application</span>
                </button>
              </div>

              <div v-else class="confirm-buttons">
                <span v-if="task.result_json?.application_id" class="badge badge-success text-xs flex items-center gap-1 mr-2">
                  <CheckCircle2 :size="12" />
                  <span>Auto-saved to ASSESSMENT</span>
                </span>

                <button
                  class="btn btn-primary btn-sm"
                  :disabled="processingTaskIds.has(task.id)"
                  @click="confirmAndSaveLead(task, 'APPLIED')"
                >
                  <Loader2 v-if="processingTaskIds.has(task.id)" class="animate-spin" :size="14" />
                  <span>Confirm & Mark as Applied</span>
                  <ArrowRight :size="14" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-if="!loadingEvaluations && activeTasks.length === 0 && completedTasks.length === 0 && failedTasks.length === 0"
        class="queue-empty-state"
      >
        <Inbox :size="32" class="text-muted mb-2" />
        <div class="font-semibold text-main">No Evaluations in Queue</div>
        <p class="text-xs text-secondary max-w-sm mt-1">
          Paste a job posting URL or job description text above to enqueue for real-time qualification assessment.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.intake-header {
  text-align: center;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
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
  margin-bottom: 10px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 650px;
  margin-top: 4px;
  line-height: 1.5;
}

.advisory-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin-bottom: 14px;
}

.extension-config-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-sm);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.endpoints-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

@media (max-width: 768px) {
  .endpoints-grid {
    grid-template-columns: 1fr;
  }
}

.endpoint-item {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.endpoint-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.endpoint-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.endpoint-input-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  padding: 4px 8px;
}

.endpoint-val {
  font-size: 11px;
  color: var(--primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-xs {
  padding: 3px 8px;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.intake-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-md);
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input, .form-textarea {
  width: 100%;
}

.intake-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}

.btn-assess {
  padding: 10px 20px;
  font-weight: 600;
}

/* ========================================================================= */
/* QUEUE & REVIEW STACK STYLING */
/* ========================================================================= */
.queue-section {
  margin-top: 36px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.queue-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.queue-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.queue-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.active-tasks-list, .failed-tasks-list, .completed-tasks-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.active-task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.task-card-main {
  display: flex;
  align-items: center;
  gap: 14px;
}

.task-spinner-box {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background-color: var(--primary-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-title {
  font-size: 13px;
  color: var(--text-main);
}

.task-stage-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-stage-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.task-url-text {
  color: var(--text-muted);
}

/* Failed Tasks Card */
.failed-task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background-color: var(--status-rejected-bg);
  border: 1px solid var(--status-rejected-border);
  border-radius: var(--radius-md);
}

.failed-card-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.failed-title {
  font-size: 13px;
  color: var(--status-rejected-text);
}

.failed-msg {
  color: var(--text-secondary);
}

.failed-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Review Card */
.review-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: all var(--transition-fast);
}

.review-card.expanded {
  box-shadow: var(--shadow-md);
  border-color: var(--primary-subtle);
}

.review-header {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  background-color: var(--bg-surface);
  transition: background-color var(--transition-fast);
}

.review-header:hover {
  background-color: var(--bg-surface-hover);
}

.review-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.company-icon-box {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background-color: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  border: 1px solid var(--border-subtle);
}

.review-company-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.review-role-title {
  font-size: 13px;
  color: var(--text-secondary);
}

.review-header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.scores-compact {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 10px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.score-pill-ai {
  background-color: var(--status-offer-bg);
  border-color: var(--status-offer-border);
}

.score-pill-num {
  font-size: 13px;
  font-weight: 800;
  color: var(--text-main);
}

.score-pill-ai .score-pill-num {
  color: var(--status-offer-text);
}

.score-pill-lbl {
  font-size: 9px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
}

.btn-icon {
  color: var(--text-muted);
  padding: 4px;
}

/* Review Body */
.review-body {
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-card);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.metric-icon {
  color: var(--primary);
}

.metric-k {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
}

.metric-v {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.skills-matrix {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.matrix-col {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
}

.matrix-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 10px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  padding: 3px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 500;
}

.tag-match {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.tag-miss {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.pros-cons-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}

.pro-con-box {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
}

.pro-con-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.pro-con-list {
  padding-left: 16px;
  font-size: 12px;
  color: var(--text-main);
  line-height: 1.5;
}

.evaluation-summary {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
}

.eval-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.eval-text {
  font-size: 12px;
  color: var(--text-main);
  line-height: 1.5;
}

.review-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid var(--border-color);
}

.confirm-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
}

.queue-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-md);
  text-align: center;
}
</style>
