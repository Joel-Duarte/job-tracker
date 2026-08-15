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
  Clock,
  ChevronDown,
  ChevronUp,
  Trash2,
  CheckCircle,
  Inbox,
  RefreshCw,
  Search,
  Filter,
  SlidersHorizontal,
  Briefcase,
  Zap,
  ArrowUpRight,
  Archive,
  RotateCcw,
  CheckSquare,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()
const appStore = useApplicationsStore()

// Active Tab
const activeTab = ref('ready') // 'ready' | 'intake' | 'queue' | 'passed'

// Search & Filtering in Ready Reviews
const searchQuery = ref('')
const minFitFilter = ref(null) // null or number (0-100)
const sortBy = ref('match_score') // 'match_score' | 'date_desc' | 'company'
const passedTaskIds = ref(new Set(JSON.parse(localStorage.getItem('job_tracker_passed_assessments') || '[]')))

// Form State for Intake
const jobUrl = ref('')
const jobText = ref('')
const isEnqueuing = ref(false)
const jdTextareaRef = ref(null)

// LinkedIn Detection State
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

// Queue & Tasks State
const evaluationTasks = ref([])
const loadingEvaluations = ref(false)
const expandedTaskIds = ref(new Set())
const processingTaskIds = ref(new Set())
let pollTimer = null

// Extension Config State
const copiedUrl = ref(false)
const copiedJd = ref(false)
const urlEndpoint = ref('Loading...')
const jdEndpoint = ref('Loading...')

// Computed Lists
const activeQueueTasks = computed(() =>
  evaluationTasks.value.filter((t) => ['QUEUED', 'PROCESSING'].includes(t.status))
)

const allCompletedTasks = computed(() =>
  evaluationTasks.value.filter((t) => t.status === 'COMPLETED' && t.result_json)
)

const readyEvaluations = computed(() => {
  return allCompletedTasks.value.filter((t) => !passedTaskIds.value.has(String(t.id)))
})

const passedEvaluations = computed(() => {
  return allCompletedTasks.value.filter((t) => passedTaskIds.value.has(String(t.id)))
})

const filteredReadyEvaluations = computed(() => {
  let list = [...readyEvaluations.value]

  // Search filter (company, position, skills)
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter((t) => {
      const res = t.result_json || {}
      const comp = (res.company || t.title_hint || '').toLowerCase()
      const pos = (res.position || '').toLowerCase()
      const skills = (res.matching_skills || []).concat(res.missing_skills || []).join(' ').toLowerCase()
      return comp.includes(q) || pos.includes(q) || skills.includes(q)
    })
  }

  // Min Fit % filter
  if (minFitFilter.value !== null && minFitFilter.value > 0) {
    const targetMin = Number(minFitFilter.value)
    list = list.filter((t) => {
      const score = t.result_json?.match_score ?? t.result_json?.fit_score ?? 0
      return Number(score) >= targetMin
    })
  }

  // Sorting
  list.sort((a, b) => {
    if (sortBy.value === 'match_score') {
      const scoreA = Number(a.result_json?.match_score ?? a.result_json?.fit_score ?? 0)
      const scoreB = Number(b.result_json?.match_score ?? b.result_json?.fit_score ?? 0)
      return scoreB - scoreA
    } else if (sortBy.value === 'company') {
      const compA = (a.result_json?.company || a.title_hint || '').toLowerCase()
      const compB = (b.result_json?.company || b.title_hint || '').toLowerCase()
      return compA.localeCompare(compB)
    } else {
      // Date desc
      return new Date(b.created_at || 0) - new Date(a.created_at || 0)
    }
  })

  return list
})

const averageFitScore = computed(() => {
  if (readyEvaluations.value.length === 0) return 0
  const total = readyEvaluations.value.reduce((acc, t) => {
    return acc + Number(t.result_json?.match_score ?? t.result_json?.fit_score ?? 0)
  }, 0)
  return Math.round(total / readyEvaluations.value.length)
})

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

async function loadEvaluations(silent = false) {
  if (!silent) loadingEvaluations.value = true
  try {
    const res = await IntakeAPI.getEvaluations(100)
    evaluationTasks.value = res.data || []
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
    uiStore.showToast('Please enter a Job URL or paste job description text.', 'warning')
    return
  }

  isEnqueuing.value = true
  try {
    const res = await IntakeAPI.enqueueAssessment({
      url: urlVal || null,
      text: textVal || null,
    })

    jobUrl.value = ''
    jobText.value = ''

    uiStore.showToast(`Lead '${res.data.title_hint}' enqueued for evaluation!`, 'success')
    activeTab.value = 'queue'
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

async function markAsApplied(task) {
  if (!task.result_json) return
  const result = task.result_json
  processingTaskIds.value.add(task.id)

  try {
    const res = await IntakeAPI.confirmAssessment({
      company: result.company || task.title_hint || 'Company',
      position: result.position || 'Software Engineer',
      status: 'APPLIED',
      job_url: task.job_url || null,
      description_markdown: task.raw_text || result.summary || '',
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

    uiStore.showToast(`'${res.data.company}' successfully added to Applications (Applied)!`, 'success')
    appStore.fetchApplications()

    // Dismiss evaluated task
    await IntakeAPI.deleteEvaluation(task.id)
    await loadEvaluations(true)
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to mark as applied', 'error')
  } finally {
    processingTaskIds.value.delete(task.id)
  }
}

function passAndArchive(task) {
  passedTaskIds.value.add(String(task.id))
  localStorage.setItem('job_tracker_passed_assessments', JSON.stringify(Array.from(passedTaskIds.value)))
  uiStore.showToast(`Archived '${task.result_json?.company || task.title_hint}' as passed`, 'info')
}

function restorePassed(task) {
  passedTaskIds.value.delete(String(task.id))
  localStorage.setItem('job_tracker_passed_assessments', JSON.stringify(Array.from(passedTaskIds.value)))
  uiStore.showToast(`Restored '${task.result_json?.company || task.title_hint}' to Ready Reviews`, 'success')
}

async function deleteEvaluation(taskId) {
  try {
    await IntakeAPI.deleteEvaluation(taskId)
    evaluationTasks.value = evaluationTasks.value.filter((t) => t.id !== taskId)
    passedTaskIds.value.delete(String(taskId))
    localStorage.setItem('job_tracker_passed_assessments', JSON.stringify(Array.from(passedTaskIds.value)))
    uiStore.showToast('Evaluation dismissed', 'info')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function clearCompleted() {
  try {
    const res = await IntakeAPI.clearCompletedEvaluations()
    uiStore.showToast(`Cleared ${res.data.cleared_count || 0} completed evaluations`, 'success')
    await loadEvaluations(true)
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

function getFitBadgeClass(score) {
  const num = Number(score)
  if (num >= 85) return 'fit-elite'
  if (num >= 70) return 'fit-high'
  if (num >= 50) return 'fit-medium'
  return 'fit-low'
}

function getFitLabel(score) {
  const num = Number(score)
  if (num >= 85) return 'Elite Match'
  if (num >= 70) return 'Strong Fit'
  if (num >= 50) return 'Moderate Fit'
  return 'Low Fit'
}

function formatStageLabel(stage) {
  switch (stage) {
    case 'FETCHING':
      return 'Fetching URL / Scraping'
    case 'EXTRACTING':
      return 'Extracting Specs & Roles'
    case 'MATCHING':
      return 'Matching Canonical Skills'
    case 'ASSESSING':
      return 'Running Qualitative AI Assessment'
    case 'SAVING':
      return 'Saving Evaluation Results'
    default:
      return stage || 'Queued'
  }
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  try {
    return new Date(isoStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return isoStr
  }
}

onMounted(() => {
  loadEvaluations()
  fetchExtensionConfig()
  pollTimer = setInterval(() => loadEvaluations(true), 4000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="assessments-page">
    <!-- Header -->
    <div class="assessments-header">
      <div>
        <h1 class="page-title">Assessments &amp; Lead Intake</h1>
        <p class="page-subtitle">
          Pre-screen opportunities with AI qualification, review match insights, and choose which leads enter your active pipeline.
        </p>
      </div>

      <div class="header-actions">
        <button
          class="btn btn-secondary btn-sm"
          :disabled="loadingEvaluations"
          @click="loadEvaluations(false)"
          title="Refresh evaluations"
        >
          <RefreshCw :class="{ 'animate-spin': loadingEvaluations }" :size="14" />
          <span>Refresh</span>
        </button>

        <button class="btn btn-primary btn-sm" @click="activeTab = 'intake'">
          <Sparkles :size="14" />
          <span>+ Ingest Job Lead</span>
        </button>
      </div>
    </div>

    <!-- Overview Stats Bar -->
    <div class="stats-grid">
      <div
        class="stat-card"
        :class="{ active: activeTab === 'ready' }"
        @click="activeTab = 'ready'"
      >
        <div class="stat-icon ready-icon">
          <CheckCircle2 :size="18" />
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ readyEvaluations.length }}</span>
          <span class="stat-lbl">Ready for Decision</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon fit-icon">
          <Sparkles :size="18" />
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ averageFitScore }}%</span>
          <span class="stat-lbl">Average Match Fit</span>
        </div>
      </div>

      <div
        class="stat-card"
        :class="{ active: activeTab === 'queue' }"
        @click="activeTab = 'queue'"
      >
        <div class="stat-icon queue-icon">
          <Clock :size="18" />
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ activeQueueTasks.length }}</span>
          <span class="stat-lbl">Processing in Queue</span>
        </div>
      </div>

      <div
        class="stat-card"
        :class="{ active: activeTab === 'passed' }"
        @click="activeTab = 'passed'"
      >
        <div class="stat-icon archive-icon">
          <Archive :size="18" />
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ passedEvaluations.length }}</span>
          <span class="stat-lbl">Passed / Archived</span>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="sub-nav-bar">
      <div class="sub-nav-tabs">
        <button
          class="sub-nav-tab"
          :class="{ active: activeTab === 'ready' }"
          @click="activeTab = 'ready'"
        >
          <Sparkles :size="15" />
          <span>Ready for Review</span>
          <span class="tab-counter-badge">{{ readyEvaluations.length }}</span>
        </button>

        <button
          class="sub-nav-tab"
          :class="{ active: activeTab === 'intake' }"
          @click="activeTab = 'intake'"
        >
          <FileText :size="15" />
          <span>New Job Intake</span>
        </button>

        <button
          class="sub-nav-tab"
          :class="{ active: activeTab === 'queue' }"
          @click="activeTab = 'queue'"
        >
          <Clock :size="15" />
          <span>AI Queue</span>
          <span v-if="activeQueueTasks.length > 0" class="tab-counter-badge pulse-badge">
            {{ activeQueueTasks.length }}
          </span>
        </button>

        <button
          class="sub-nav-tab"
          :class="{ active: activeTab === 'passed' }"
          @click="activeTab = 'passed'"
        >
          <Archive :size="15" />
          <span>Passed / Not Applied</span>
          <span v-if="passedEvaluations.length > 0" class="tab-counter-badge">
            {{ passedEvaluations.length }}
          </span>
        </button>
      </div>
    </div>

    <!-- TAB 1: READY EVALUATIONS -->
    <div v-if="activeTab === 'ready'" class="tab-view animate-fade-in">
      <!-- Toolbar Filter Bar -->
      <div class="eval-filter-toolbar">
        <div class="search-box">
          <Search :size="15" class="text-muted" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search company, role, or required skill..."
            class="search-input"
          />
          <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''">
            <X :size="13" />
          </button>
        </div>

        <!-- Match Score Quick Filter Chips -->
        <div class="fit-chips-group">
          <span class="fit-filter-label">Min Fit:</span>
          <button
            class="fit-chip"
            :class="{ active: minFitFilter === null }"
            @click="minFitFilter = null"
          >
            All
          </button>
          <button
            class="fit-chip"
            :class="{ active: minFitFilter === 85 }"
            @click="minFitFilter = minFitFilter === 85 ? null : 85"
          >
            Elite 85%+
          </button>
          <button
            class="fit-chip"
            :class="{ active: minFitFilter === 70 }"
            @click="minFitFilter = minFitFilter === 70 ? null : 70"
          >
            Strong 70%+
          </button>
        </div>

        <div class="sort-select-wrapper">
          <span class="sort-label">Sort:</span>
          <select v-model="sortBy" class="sort-select">
            <option value="match_score">Highest Fit %</option>
            <option value="date_desc">Newest First</option>
            <option value="company">Company A-Z</option>
          </select>
        </div>
      </div>

      <!-- Evaluations Grid -->
      <div v-if="filteredReadyEvaluations.length === 0" class="empty-state-box">
        <Sparkles :size="40" class="empty-state-icon" />
        <h3 class="empty-state-title">No assessments ready for review</h3>
        <p class="empty-state-desc">
          Ingest a job URL or paste a spec to receive a structured AI qualification assessment.
        </p>
        <button class="btn btn-primary mt-3" @click="activeTab = 'intake'">
          <Sparkles :size="14" />
          <span>Ingest New Job</span>
        </button>
      </div>

      <div v-else class="eval-cards-grid">
        <div
          v-for="task in filteredReadyEvaluations"
          :key="task.id"
          class="eval-card"
          :class="{ expanded: expandedTaskIds.has(task.id) }"
        >
          <!-- Card Header Row -->
          <div class="eval-card-header">
            <div class="eval-title-group">
              <div class="company-badge-line">
                <span class="eval-company">{{ task.result_json?.company || task.title_hint || 'Target Company' }}</span>
                <span v-if="task.job_url" class="eval-url-link">
                  <a :href="task.job_url" target="_blank" rel="noopener noreferrer" title="Open original job posting">
                    <Globe :size="12" />
                    <span>External Posting</span>
                    <ArrowUpRight :size="11" />
                  </a>
                </span>
              </div>
              <h2 class="eval-role">{{ task.result_json?.position || 'Software Engineer' }}</h2>
            </div>

            <!-- Fit Score Gauge -->
            <div class="eval-fit-container">
              <div class="fit-gauge" :class="getFitBadgeClass(task.result_json?.match_score ?? task.result_json?.fit_score ?? 0)">
                <span class="fit-val">{{ task.result_json?.match_score ?? task.result_json?.fit_score ?? 0 }}%</span>
                <span class="fit-lbl">{{ getFitLabel(task.result_json?.match_score ?? task.result_json?.fit_score ?? 0) }}</span>
              </div>
            </div>
          </div>

          <!-- Metadata Tags Row (Salary, Location, Work Mode) -->
          <div class="eval-meta-chips">
            <span v-if="task.result_json?.salary_min || task.result_json?.salary_max" class="meta-chip">
              <DollarSign :size="12" />
              <span>
                {{ task.result_json.currency || '$' }}{{ task.result_json.salary_min ? task.result_json.salary_min.toLocaleString() : '' }}
                {{ task.result_json.salary_max ? ' - ' + task.result_json.salary_max.toLocaleString() : '+' }}
              </span>
            </span>

            <span v-if="task.result_json?.location" class="meta-chip">
              <MapPin :size="12" />
              <span>{{ task.result_json.location }}</span>
            </span>

            <span v-if="task.result_json?.work_model" class="meta-chip font-mono">
              <Building2 :size="12" />
              <span>{{ task.result_json.work_model }}</span>
            </span>

            <span class="meta-chip date-chip text-muted">
              <Clock :size="11" />
              <span>Assessed {{ formatDate(task.created_at) }}</span>
            </span>
          </div>

          <!-- AI Qualitative Highlights -->
          <div v-if="task.result_json?.summary" class="eval-summary-box">
            <p>{{ task.result_json.summary }}</p>
          </div>

          <!-- Expandable Deep-Dive Dossier -->
          <div v-if="expandedTaskIds.has(task.id)" class="eval-deep-dive animate-fade-in">
            <!-- Pros & Cons Grid -->
            <div v-if="task.result_json?.pros?.length || task.result_json?.cons?.length" class="pros-cons-grid">
              <div class="pro-column">
                <div class="column-header text-success">
                  <Check :size="13" />
                  <span>Strategic Match Pros</span>
                </div>
                <ul class="dossier-list">
                  <li v-for="(pro, idx) in task.result_json.pros" :key="idx">{{ pro }}</li>
                </ul>
              </div>

              <div class="con-column">
                <div class="column-header text-warning">
                  <AlertTriangle :size="13" />
                  <span>Missing Gaps &amp; Considerations</span>
                </div>
                <ul class="dossier-list">
                  <li v-for="(con, idx) in task.result_json.cons" :key="idx">{{ con }}</li>
                </ul>
              </div>
            </div>

            <!-- Skills Matrix -->
            <div class="skills-matrix">
              <div v-if="task.result_json?.matching_skills?.length" class="skills-group">
                <span class="group-title text-success">Matching CV Skills ({{ task.result_json.matching_skills.length }}):</span>
                <div class="skill-tags">
                  <span v-for="s in task.result_json.matching_skills" :key="s" class="skill-tag match-tag">
                    <Check :size="11" />
                    <span>{{ s }}</span>
                  </span>
                </div>
              </div>

              <div v-if="task.result_json?.missing_skills?.length" class="skills-group">
                <span class="group-title text-warning">Missing / Required Skills ({{ task.result_json.missing_skills.length }}):</span>
                <div class="skill-tags">
                  <span v-for="s in task.result_json.missing_skills" :key="s" class="skill-tag gap-tag">
                    <span>{{ s }}</span>
                  </span>
                </div>
              </div>
            </div>

            <!-- Resume Tailoring Strategy -->
            <div v-if="task.result_json?.tailoring_strategy" class="tailoring-card">
              <div class="tailoring-header">
                <Sparkles :size="14" class="text-primary" />
                <span>Recommended Resume Tailoring Strategy</span>
              </div>
              <p class="tailoring-text">{{ task.result_json.tailoring_strategy }}</p>
            </div>
          </div>

          <!-- Decision Action Footer -->
          <div class="eval-card-footer">
            <button
              class="expand-toggle-btn"
              @click="toggleExpandTask(task.id)"
            >
              <span>{{ expandedTaskIds.has(task.id) ? 'Collapse Dossier' : 'View Full Assessment Dossier' }}</span>
              <ChevronUp v-if="expandedTaskIds.has(task.id)" :size="14" />
              <ChevronDown v-else :size="14" />
            </button>

            <div class="action-buttons-group">
              <button
                class="btn btn-ghost btn-sm text-muted"
                title="Dismiss and delete evaluation"
                @click="deleteEvaluation(task.id)"
              >
                <Trash2 :size="14" />
              </button>

              <button
                class="btn btn-secondary btn-sm"
                title="Archive as passed / not applying"
                @click="passAndArchive(task)"
              >
                <Archive :size="14" />
                <span>Pass &amp; Archive</span>
              </button>

              <button
                class="btn btn-primary btn-sm"
                :disabled="processingTaskIds.has(task.id)"
                @click="markAsApplied(task)"
                title="Promote to active pipeline in APPLIED status"
              >
                <Loader2 v-if="processingTaskIds.has(task.id)" class="animate-spin" :size="14" />
                <ArrowRight v-else :size="14" />
                <span>Mark as Applied &rarr;</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: NEW JOB INTAKE -->
    <div v-else-if="activeTab === 'intake'" class="tab-view animate-fade-in">
      <div class="intake-form-card">
        <div class="form-section-header">
          <Sparkles :size="18" class="text-primary" />
          <div>
            <h2 class="section-title">Submit Job Lead for AI Pre-Screening</h2>
            <p class="section-desc">
              Paste a URL, copy/paste raw job requirements, or drop an email file. The AI de-identifies requirements, matches your candidate CV, and produces a complete fit dossier.
            </p>
          </div>
        </div>

        <form @submit.prevent="enqueueLead" class="intake-form">
          <!-- Job URL Input -->
          <div class="input-group">
            <label class="input-label">Job Posting URL (Optional)</label>
            <div class="input-with-icon">
              <LinkIcon :size="16" class="field-icon" />
              <input
                v-model="jobUrl"
                type="url"
                placeholder="https://jobs.lever.co/... or https://boards.greenhouse.io/..."
                class="form-input"
              />
            </div>
          </div>

          <!-- LinkedIn Anti-Scrape Warning Alert -->
          <div v-if="isLinkedInUrl" class="advisory-box animate-fade-in">
            <div class="advisory-icon text-warning">
              <AlertTriangle :size="16" />
            </div>
            <div class="advisory-content">
              <span class="advisory-title">LinkedIn Anti-Bot Wall Detected</span>
              <p class="advisory-desc">
                LinkedIn blocks automated scrapers without user authentication. For best results, <strong>copy the job text</strong> directly from LinkedIn and paste it into the box below.
              </p>
              <div class="advisory-actions">
                <button type="button" class="btn btn-secondary btn-xs" @click="handlePasteTextInstead">
                  Paste Text Instead
                </button>
                <button type="button" class="btn btn-ghost btn-xs text-muted" @click="dismissLinkedInWarning">
                  Dismiss
                </button>
              </div>
            </div>
          </div>

          <!-- Raw Description Textarea -->
          <div class="input-group mt-3">
            <label class="input-label">Job Specification / Requirements Text</label>
            <textarea
              ref="jdTextareaRef"
              v-model="jobText"
              rows="7"
              placeholder="Paste full job spec, responsibilities, required skills, and qualification text here..."
              class="form-textarea font-mono"
            ></textarea>
          </div>

          <div class="form-submit-row mt-4">
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="isEnqueuing || (!jobUrl.trim() && !jobText.trim())"
            >
              <Loader2 v-if="isEnqueuing" class="animate-spin" :size="16" />
              <Sparkles v-else :size="16" />
              <span>{{ isEnqueuing ? 'Enqueuing...' : 'Enqueue for AI Evaluation' }}</span>
            </button>
          </div>
        </form>
      </div>

      <!-- Extension & API Sync Helper Box -->
      <div class="extension-helper-card mt-4">
        <div class="helper-header">
          <Puzzle :size="16" class="text-primary" />
          <span class="helper-title">1-Click Browser Extension Ingestion</span>
        </div>
        <p class="helper-desc">
          Send active job specs directly from Chrome/Firefox with our companion browser extension.
        </p>

        <div class="endpoints-grid mt-3">
          <div class="endpoint-box">
            <span class="endpoint-lbl">URL Ingest Endpoint:</span>
            <div class="endpoint-val-row">
              <code class="endpoint-code">{{ urlEndpoint }}</code>
              <button class="btn btn-secondary btn-xs" @click="copyToClipboard(urlEndpoint, 'url')">
                <Check v-if="copiedUrl" :size="12" class="text-success" />
                <Copy v-else :size="12" />
                <span>{{ copiedUrl ? 'Copied' : 'Copy' }}</span>
              </button>
            </div>
          </div>

          <div class="endpoint-box">
            <span class="endpoint-lbl">DOM / Card Ingest Endpoint:</span>
            <div class="endpoint-val-row">
              <code class="endpoint-code">{{ jdEndpoint }}</code>
              <button class="btn btn-secondary btn-xs" @click="copyToClipboard(jdEndpoint, 'jd')">
                <Check v-if="copiedJd" :size="12" class="text-success" />
                <Copy v-else :size="12" />
                <span>{{ copiedJd ? 'Copied' : 'Copy' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: BACKGROUND AI QUEUE -->
    <div v-else-if="activeTab === 'queue'" class="tab-view animate-fade-in">
      <div class="queue-card">
        <div class="queue-card-header">
          <div>
            <h2 class="section-title">Asynchronous Background Queue</h2>
            <p class="section-desc">Live multi-stage execution pipeline for job scraping, CV de-identification, and AI qualification.</p>
          </div>

          <button
            class="btn btn-ghost btn-sm text-secondary"
            @click="clearCompleted"
            title="Clear completed evaluation records"
          >
            <Trash2 :size="14" />
            <span>Clear Completed</span>
          </button>
        </div>

        <div v-if="evaluationTasks.length === 0" class="empty-state-box">
          <Clock :size="40" class="empty-state-icon" />
          <h3 class="empty-state-title">Queue is idle</h3>
          <p class="empty-state-desc">No tasks currently processing. Ingest a job posting to trigger background evaluation.</p>
        </div>

        <div v-else class="queue-tasks-list">
          <div
            v-for="task in evaluationTasks"
            :key="task.id"
            class="queue-item"
            :class="`status-${task.status.toLowerCase()}`"
          >
            <div class="queue-item-header">
              <div class="queue-title-line">
                <span class="queue-task-type font-mono text-xs">{{ task.task_type || 'JOB_ASSESSMENT' }}</span>
                <span class="queue-task-title">{{ task.title_hint || task.job_url || `Evaluation #${task.id}` }}</span>
              </div>

              <div class="queue-status-pill font-mono" :class="`pill-${task.status.toLowerCase()}`">
                <Loader2 v-if="task.status === 'PROCESSING'" class="animate-spin" :size="12" />
                <CheckCircle v-else-if="task.status === 'COMPLETED'" :size="12" />
                <AlertTriangle v-else-if="task.status === 'FAILED'" :size="12" />
                <span>{{ task.status }}</span>
              </div>
            </div>

            <!-- Stepper Progress -->
            <div class="stepper-track">
              <div class="stepper-step" :class="{ done: ['EXTRACTING', 'MATCHING', 'ASSESSING', 'SAVING', 'COMPLETED'].includes(task.stage) || task.status === 'COMPLETED' }">
                <div class="step-dot"></div>
                <span class="step-lbl">Scrape / Ingest</span>
              </div>
              <div class="stepper-step" :class="{ done: ['MATCHING', 'ASSESSING', 'SAVING', 'COMPLETED'].includes(task.stage) || task.status === 'COMPLETED' }">
                <div class="step-dot"></div>
                <span class="step-lbl">Extract Roles</span>
              </div>
              <div class="stepper-step" :class="{ done: ['ASSESSING', 'SAVING', 'COMPLETED'].includes(task.stage) || task.status === 'COMPLETED' }">
                <div class="step-dot"></div>
                <span class="step-lbl">Match CV</span>
              </div>
              <div class="stepper-step" :class="{ done: ['SAVING', 'COMPLETED'].includes(task.stage) || task.status === 'COMPLETED' }">
                <div class="step-dot"></div>
                <span class="step-lbl">Qualitative Fit</span>
              </div>
              <div class="stepper-step" :class="{ done: task.status === 'COMPLETED' }">
                <div class="step-dot"></div>
                <span class="step-lbl">Complete</span>
              </div>
            </div>

            <div class="queue-item-footer">
              <span class="stage-info-text text-muted">
                Current Stage: <strong>{{ formatStageLabel(task.stage) }}</strong>
              </span>

              <div class="queue-actions">
                <button
                  v-if="task.status === 'COMPLETED'"
                  class="btn btn-primary btn-xs"
                  @click="activeTab = 'ready'"
                >
                  <span>Review Dossier &rarr;</span>
                </button>

                <button
                  class="btn btn-ghost btn-xs text-muted"
                  @click="deleteEvaluation(task.id)"
                  title="Dismiss task"
                >
                  <Trash2 :size="12" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: PASSED / ARCHIVED -->
    <div v-else-if="activeTab === 'passed'" class="tab-view animate-fade-in">
      <div class="passed-list-container">
        <div class="passed-header">
          <div>
            <h2 class="section-title">Passed Opportunities</h2>
            <p class="section-desc">Evaluations you chose not to apply for. You can restore them to Ready Reviews or apply anytime.</p>
          </div>
        </div>

        <div v-if="passedEvaluations.length === 0" class="empty-state-box">
          <Archive :size="40" class="empty-state-icon" />
          <h3 class="empty-state-title">No passed evaluations</h3>
          <p class="empty-state-desc">Evaluations you archive as 'Passed' will be safely stored here without cluttering your active pipeline.</p>
        </div>

        <div v-else class="passed-cards-list">
          <div v-for="task in passedEvaluations" :key="task.id" class="passed-card">
            <div class="passed-card-main">
              <div class="passed-title-group">
                <span class="passed-company font-semibold">{{ task.result_json?.company || task.title_hint }}</span>
                <span class="passed-role text-secondary">{{ task.result_json?.position || 'Role' }}</span>
              </div>
              <div class="passed-meta font-mono text-xs text-muted">
                <span>Fit Score: {{ task.result_json?.match_score ?? task.result_json?.fit_score ?? 0 }}%</span>
                <span v-if="task.result_json?.location">&bull; {{ task.result_json.location }}</span>
              </div>
            </div>

            <div class="passed-card-actions">
              <button class="btn btn-secondary btn-sm" @click="restorePassed(task)">
                <RotateCcw :size="13" />
                <span>Restore to Ready</span>
              </button>

              <button class="btn btn-primary btn-sm" @click="markAsApplied(task)">
                <ArrowRight :size="13" />
                <span>Apply Anyway</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.assessments-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.assessments-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.assessments-header > div:first-child {
  flex: 1;
  min-width: 260px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.page-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 24px;
  color: var(--text-main);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* Stats Overview Bar */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}

@media (max-width: 800px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.stat-card:hover {
  border-color: var(--border-focus);
}

.stat-card.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary-subtle);
}

.stat-icon {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ready-icon {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.fit-icon {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.queue-icon {
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
}

.archive-icon {
  background-color: var(--bg-main);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-val {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.stat-lbl {
  font-size: 11px;
  color: var(--text-secondary);
}

/* Sub-Nav Bar */
.sub-nav-bar {
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 24px;
}

.sub-nav-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.sub-nav-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sub-nav-tab:hover {
  color: var(--text-main);
}

.sub-nav-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}

.tab-counter-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.pulse-badge {
  background-color: var(--primary);
  color: #fff;
  animation: pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Tab 1: Toolbar */
.eval-filter-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0 12px;
  height: 36px;
  flex: 1;
  min-width: 260px;
  max-width: 420px;
}

.search-input {
  border: none;
  background: transparent;
  color: var(--text-main);
  font-size: 13px;
  width: 100%;
  outline: none;
}

.clear-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}

.fit-chips-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.fit-filter-label, .sort-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.fit-chip {
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.fit-chip:hover {
  border-color: var(--border-focus);
}

.fit-chip.active {
  background-color: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.sort-select-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sort-select {
  height: 34px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  font-size: 12px;
}

/* Evaluations Cards Grid */
.eval-cards-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.eval-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: border-color var(--transition-fast);
}

.eval-card:hover {
  border-color: var(--border-focus);
}

.eval-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.eval-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.company-badge-line {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eval-company {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.eval-url-link a {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--primary);
  text-decoration: none;
}

.eval-role {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-main);
}

.fit-gauge {
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 90px;
}

.fit-val {
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
}

.fit-lbl {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.fit-elite {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.fit-high {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.fit-medium {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
}

.fit-low {
  background-color: var(--bg-main);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}

.eval-meta-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-secondary);
}

.eval-summary-box {
  background-color: var(--bg-main);
  border-left: 3px solid var(--primary);
  padding: 10px 14px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-main);
}

/* Deep Dive Dossier */
.eval-deep-dive {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

.pros-cons-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 768px) {
  .pros-cons-grid {
    grid-template-columns: 1fr;
  }
}

.pro-column, .con-column {
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}

.column-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
}

.dossier-list {
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.skills-matrix {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}

.group-title {
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 6px;
  display: block;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-family: var(--font-mono);
}

.match-tag {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.gap-tag {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
}

.tailoring-card {
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}

.tailoring-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 6px;
}

.tailoring-text {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-main);
}

.eval-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
  flex-wrap: wrap;
  gap: 12px;
}

.expand-toggle-btn {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.action-buttons-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Tab 2: Intake Form */
.intake-form-card, .extension-helper-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  box-shadow: var(--shadow-sm);
}

.form-section-header, .helper-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.section-title, .helper-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.section-desc, .helper-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.field-icon {
  position: absolute;
  left: 12px;
  color: var(--text-muted);
}

.input-with-icon .form-input {
  padding-left: 36px;
}

.form-textarea {
  width: 100%;
  padding: 10px 12px;
  font-size: 12px;
  background-color: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  outline: none;
  resize: vertical;
}

.advisory-box {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  background-color: var(--status-interview-bg);
  border: 1px solid var(--status-interview-border);
  border-radius: var(--radius-sm);
  margin-top: 10px;
}

.advisory-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--status-interview-text);
  display: block;
  margin-bottom: 2px;
}

.advisory-desc {
  font-size: 11px;
  color: var(--status-interview-text);
  line-height: 1.4;
  margin-bottom: 6px;
}

.advisory-actions {
  display: flex;
  gap: 8px;
}

.endpoints-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 768px) {
  .endpoints-grid {
    grid-template-columns: 1fr;
  }
}

.endpoint-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.endpoint-lbl {
  font-size: 11px;
  color: var(--text-secondary);
  display: block;
  margin-bottom: 4px;
}

.endpoint-val-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.endpoint-code {
  font-size: 11px;
  color: var(--text-main);
  word-break: break-all;
}

/* Tab 3: Queue */
.queue-card, .passed-list-container {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  box-shadow: var(--shadow-sm);
}

.queue-card-header, .passed-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 16px;
  flex-wrap: wrap;
}

.queue-tasks-list, .passed-cards-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-item, .passed-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.passed-card {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.queue-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.queue-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.queue-task-type {
  background-color: var(--bg-elevated);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--text-muted);
}

.queue-task-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.queue-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: var(--radius-full);
}

.pill-processing, .pill-queued {
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

.stepper-track {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  padding: 8px 0;
}

.stepper-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  z-index: 1;
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--border-color);
}

.stepper-step.done .step-dot {
  background-color: var(--primary);
  box-shadow: 0 0 6px var(--primary-glow);
}

.step-lbl {
  font-size: 10px;
  color: var(--text-muted);
}

.stepper-step.done .step-lbl {
  color: var(--text-main);
  font-weight: 600;
}

.queue-item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
  font-size: 11px;
}

.queue-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
