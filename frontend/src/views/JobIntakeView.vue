<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useQueueStore } from '../stores/queueStore'
import { IntakeAPI } from '../api/endpoints'
import { getFitScores } from '../utils/fitScores'
import { isLocalOrDemoMode } from '../services/storageAdapter'
import { parseJobDescriptionWithBYOK } from '../services/byokAiClient'
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
const queueStore = useQueueStore()

// Input Form State
const jobUrl = ref('')
const jobText = ref('')
const isEnqueuing = ref(false)
const isParsingSmartPaste = ref(false)
const smartPasteResult = ref(null)
const jdTextareaRef = ref(null)

const isLocal = computed(() => isLocalOrDemoMode())

// LinkedIn Detection & Advisory State
const dismissedLinkedInUrl = ref('')
const isLinkedInUrl = computed(() => {
  if (!jobUrl.value) return false
  const trimmed = jobUrl.value.trim().toLowerCase()
  return trimmed.includes('linkedin.com') && dismissedLinkedInUrl.value !== trimmed
})

function dismissLinkedInWarning() {
  dismissedLinkedInUrl.value = jobUrl.value.trim().toLowerCase()
}

function handlePasteTextInstead() {
  dismissLinkedInWarning()
  nextTick(() => {
    if (jdTextareaRef.value) {
      jdTextareaRef.value.focus()
    }
  })
}

// Queue & Evaluations State
const evaluationTasks = computed(() => queueStore.tasks)
const loadingEvaluations = computed(() => queueStore.loading)
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
  smartPasteResult.value = null
}

async function handleSmartPasteParse() {
  if (!jobText.value.trim()) {
    uiStore.showToast('Please paste a job description text first.', 'warning')
    return
  }

  isParsingSmartPaste.value = true
  try {
    const parsed = await parseJobDescriptionWithBYOK(jobText.value.trim())
    smartPasteResult.value = parsed
    uiStore.showToast('Parsed job description into structured specs!', 'success')
  } catch (err) {
    uiStore.showToast(`Parsing failed: ${err.message}`, 'error')
  } finally {
    isParsingSmartPaste.value = false
  }
}

async function loadEvaluations(silent = false) {
  await queueStore.fetchTasks(silent)
  if (expandedTaskIds.value.size === 0 && completedTasks.value.length > 0) {
    expandedTaskIds.value.add(completedTasks.value[0].id)
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
    await IntakeAPI.paste({ raw_text: textVal || urlVal, url: urlVal })
    uiStore.showToast('Job Lead enqueued & parsed into local database!', 'success')
    clearForm()
    appStore.fetchApplications()
    loadEvaluations(true)
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

async function deleteTask(taskId) {
  try {
    await queueStore.deleteTask(taskId)
  } catch (err) {
    //
  }
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
    case 'COVER_LETTER':
      return 'Generating Cover Letter'
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
      <h1 class="page-title">Job Lead Intake &amp; Smart Paste Parser</h1>
      <p class="page-subtitle">
        Paste a career URL or raw job description text. Use client-first Smart Paste AI extraction or background evaluations to extract structured job specs into IndexedDB.
      </p>
    </div>

    <!-- Client-First Local Mode Banner -->
    <div v-if="isLocal" class="advisory-banner">
      <Info :size="16" class="text-primary flex-shrink-0" />
      <span>
        <strong>Client-First Local Mode Active:</strong> Direct web scraping is replaced with browser Smart Paste Extraction using your configured BYOK AI provider keys.
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
          <span>Job Posting URL (Optional in Local Mode)</span>
        </label>
        <input
          v-model="jobUrl"
          type="url"
          placeholder="https://company.com/careers/job/123"
          class="form-input"
        />
      </div>

      <div class="input-section">
        <div class="label-row">
          <label class="section-label">
            <FileText :size="15" />
            <span>Raw Job Description Text</span>
          </label>
          <span class="field-hint text-xs text-muted">Paste raw text for client-side Smart Paste AI extraction</span>
        </div>
        <textarea
          ref="jdTextareaRef"
          v-model="jobText"
          rows="6"
          placeholder="Paste raw job description text here..."
          class="form-textarea font-mono text-xs"
        ></textarea>
      </div>

      <!-- Smart Paste Parsed Specs Preview -->
      <div v-if="smartPasteResult" class="smart-paste-preview animate-fade-in">
        <div class="preview-header">
          <Sparkles :size="14" class="text-primary" />
          <span class="font-bold text-xs">Smart Paste Parsed Specs</span>
        </div>
        <div class="preview-grid text-xs">
          <div><strong>Company:</strong> {{ smartPasteResult.company_name }}</div>
          <div><strong>Title:</strong> {{ smartPasteResult.title }}</div>
          <div><strong>Location:</strong> {{ smartPasteResult.location }} ({{ smartPasteResult.work_model }})</div>
          <div><strong>Salary:</strong> {{ smartPasteResult.salary_range }}</div>
        </div>
      </div>

      <div class="intake-actions flex items-center justify-between">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="isParsingSmartPaste || !jobText.trim()"
          @click="handleSmartPasteParse"
        >
          <Loader2 v-if="isParsingSmartPaste" class="animate-spin" :size="14" />
          <Sparkles v-else :size="14" />
          <span>Smart Paste Parse (BYOK AI)</span>
        </button>

        <div class="flex items-center gap-2">
          <button v-if="jobUrl || jobText" class="btn btn-secondary btn-sm" @click="clearForm">
            <X :size="14" />
            <span>Clear</span>
          </button>
          <button
            class="btn btn-primary btn-sm"
            :disabled="isEnqueuing || (!jobUrl.trim() && !jobText.trim())"
            @click="enqueueLead"
          >
            <Loader2 v-if="isEnqueuing" class="animate-spin" :size="14" />
            <CheckCircle2 v-else :size="14" />
            <span>{{ isEnqueuing ? 'Saving...' : 'Add Application to Local DB' }}</span>
          </button>
        </div>
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
}
.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background-color: var(--status-assessment-bg);
  color: var(--status-assessment-text);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 10px;
}
.page-title {
  font-size: 24px;
  color: var(--text-main);
}
.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 650px;
  margin: 4px auto 0;
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
  margin-bottom: 14px;
}
.extension-config-card, .intake-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.endpoints-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.endpoint-item {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px;
}
.endpoint-input-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.endpoint-val {
  font-size: 11px;
  color: var(--primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.smart-paste-preview {
  background-color: var(--bg-main);
  border: 1px solid var(--primary-glow);
  border-radius: var(--radius-sm);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  color: var(--text-main);
}
.form-input, .form-textarea {
  width: 100%;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-main);
}
</style>
