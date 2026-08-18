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
import PageHeader from '../components/common/PageHeader.vue'
import CompanyLogo from '../components/common/CompanyLogo.vue'
import CoverLetterModal from '../components/modals/CoverLetterModal.vue'
import { CoverLettersAPI } from '../api/endpoints'
import {
  normalizeWorkModel,
  formatRelativeDate,
} from '../utils/formatters'

const router = useRouter()
const uiStore = useUIStore()
const appStore = useApplicationsStore()

// Active Tab
const activeTab = ref('ready') // 'ready' | 'queue' | 'passed'

// Search & Filtering in Ready Reviews
const searchQuery = ref('')
const minFitFilter = ref(null)
const maxMatchFilter = ref(100)

const tailoringStrategyCache = new Map()
const parsedTailoringStrategy = (task) => {
  if (!task.result_json?.tailoring_strategy) return null
  if (tailoringStrategyCache.has(task.id)) return tailoringStrategyCache.get(task.id)
  try {
    const raw = task.result_json.tailoring_strategy
    let parsed = null
    if (typeof raw === 'object') parsed = raw
    else {
      let cleaned = raw.trim()
      if (cleaned.startsWith('```json')) cleaned = cleaned.replace(/^```json/, '')
      if (cleaned.startsWith('```')) cleaned = cleaned.replace(/^```/, '')
      if (cleaned.endsWith('```')) cleaned = cleaned.replace(/```$/, '')
      parsed = JSON.parse(cleaned)
    }
    tailoringStrategyCache.set(task.id, parsed)
    return parsed
  } catch (err) {
    return null
  }
}
 // null or number (40, 60, 80)
const sortBy = ref('match_score') // 'match_score' | 'date_desc' | 'company'
const passedTaskIds = ref(new Set(JSON.parse(localStorage.getItem('job_tracker_passed_assessments') || '[]')))

// Modal & Cover Letter State
const isCoverLetterModalOpen = ref(false)
const selectedCoverLetterTask = ref(null)
const coverLetterGeneratingTaskIds = ref(new Set())

function openCoverLetterModal(task) {
  selectedCoverLetterTask.value = task
  isCoverLetterModalOpen.value = true
}

async function handleGenerateCoverLetter(task) {
  if (!task.result_json?.application_id) {
    uiStore.showToast('Please mark application as applied first or wait for intake completion.', 'info')
    return
  }
  const appId = task.result_json.application_id
  coverLetterGeneratingTaskIds.value.add(task.id)
  try {
    await CoverLettersAPI.generate(appId)
    uiStore.showToast('Cover letter generation queued in AI Queue!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to generate cover letter', 'error')
  } finally {
    coverLetterGeneratingTaskIds.value.delete(task.id)
  }
}

// Queue & Tasks State
const evaluationTasks = ref([])
const loadingEvaluations = ref(false)
const expandedTaskIds = ref(new Set())
const processingTaskIds = ref(new Set())
let pollTimer = null

// Computed Lists
const selectedTaskIds = ref(new Set())
function toggleTaskSelection(taskId) {
  if (selectedTaskIds.value.has(taskId)) {
    selectedTaskIds.value.delete(taskId)
  } else {
    selectedTaskIds.value.add(taskId)
  }
}
function selectAllVisibleTasks() {
  const currentList = activeTab.value === 'ready' ? filteredReadyEvaluations.value : filteredPassedEvaluations.value
  if (selectedTaskIds.value.size === currentList.length && currentList.length > 0) {
    selectedTaskIds.value.clear()
  } else {
    currentList.forEach(t => selectedTaskIds.value.add(t.id))
  }
}

async function bulkMarkAsApplied() {
  const currentList = activeTab.value === 'ready' ? filteredReadyEvaluations.value : filteredPassedEvaluations.value
  const tasksToApply = currentList.filter(t => selectedTaskIds.value.has(t.id))
  if (!tasksToApply.length) return

  let successCount = 0
  for (const task of tasksToApply) {
    if (!task.result_json) continue
    processingTaskIds.value.add(task.id)
    try {
      const result = task.result_json
      await IntakeAPI.confirmAssessment({
        application_id: result.application_id,
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
        required_skills: [...(result.matching_skills || []), ...(result.missing_skills || [])],
        match_analysis_payload: result,
      })
      await IntakeAPI.deleteEvaluation(task.id)
      passedTaskIds.value.delete(String(task.id))
      successCount++
    } catch (err) {
      console.error("Failed to apply task", task.id, err)
    } finally {
      processingTaskIds.value.delete(task.id)
    }
  }

  localStorage.setItem('job_tracker_passed_assessments', JSON.stringify(Array.from(passedTaskIds.value)))
  uiStore.showToast(`Successfully moved ${successCount} leads to Applications (Applied)`, 'success')
  selectedTaskIds.value.clear()
  appStore.fetchApplications()
  await loadEvaluations(true)
}

async function bulkArchive() {
  if (activeTab.value === 'passed') {
    const tasksToDelete = filteredPassedEvaluations.value.filter(t => selectedTaskIds.value.has(t.id))
    for (const task of tasksToDelete) {
      await IntakeAPI.deleteEvaluation(task.id)
      passedTaskIds.value.delete(String(task.id))
    }
    localStorage.setItem('job_tracker_passed_assessments', JSON.stringify(Array.from(passedTaskIds.value)))
    selectedTaskIds.value.clear()
    await loadEvaluations(true)
    return
  }

  const tasksToArchive = filteredReadyEvaluations.value.filter(t => selectedTaskIds.value.has(t.id))
  if (!tasksToArchive.length) return

  for (const task of tasksToArchive) {
    passedTaskIds.value.add(String(task.id))
  }
  localStorage.setItem('job_tracker_passed_assessments', JSON.stringify(Array.from(passedTaskIds.value)))
  uiStore.showToast(`Archived ${tasksToArchive.length} evaluations.`, 'info')
  selectedTaskIds.value.clear()
}

const activeQueueTasks = computed(() =>
  evaluationTasks.value.filter((t) => ['QUEUED', 'PROCESSING'].includes(t.status))
)

const allCompletedTasks = computed(() =>
  evaluationTasks.value.filter(
    (t) => (t.task_type === 'JOB_ASSESSMENT' || !t.task_type) && t.status === 'COMPLETED' && t.result_json
  )
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

  // Max Fit % filter
  if (maxMatchFilter.value !== null && maxMatchFilter.value < 100) {
    const targetMax = Number(maxMatchFilter.value)
    list = list.filter((t) => {
      const score = t.result_json?.match_score ?? t.result_json?.fit_score ?? 0
      return Number(score) <= targetMax
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

const filteredPassedEvaluations = computed(() => {
  let list = [...passedEvaluations.value]

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

  // Max Fit % filter
  if (maxMatchFilter.value !== null && maxMatchFilter.value < 100) {
    const targetMax = Number(maxMatchFilter.value)
    list = list.filter((t) => {
      const score = t.result_json?.match_score ?? t.result_json?.fit_score ?? 0
      return Number(score) <= targetMax
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
      application_id: result.application_id, // Added application_id to link the record
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
      match_analysis_payload: result,
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
  if (num >= 80) return 'fit-elite'
  if (num >= 60) return 'fit-high'
  if (num >= 40) return 'fit-medium'
  return 'fit-low'
}

function getFitLabel(score) {
  const num = Number(score)
  if (num >= 80) return 'Elite Match'
  if (num >= 60) return 'Strong Fit'
  if (num >= 40) return 'Moderate Fit'
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
  pollTimer = setInterval(() => loadEvaluations(true), 4000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="assessments-page">
    <!-- Standardized Page Header (Centered) -->
    <PageHeader
      title="Job Lead Assessments"
      subtitle="Pre-screen job opportunities with AI qualification, analyze CV keyword overlap, and decide which leads enter your active pipeline."
      align="center"
    />

    <!-- Active Processing Queue Banner (When background tasks are running) -->
    <div v-if="activeQueueTasks.length > 0" class="active-queue-banner animate-fade-in">
      <div class="banner-left">
        <span class="live-pulse-dot"></span>
        <Sparkles :size="15" class="text-primary" />
        <span class="banner-text">
          <strong>{{ activeQueueTasks.length }}</strong> task{{ activeQueueTasks.length > 1 ? 's are' : ' is' }} currently processing in the background AI Queue.
        </span>
      </div>
      <router-link to="/queue" class="btn btn-secondary btn-xs">
        <span>Open AI Queue &rarr;</span>
      </router-link>
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

      <router-link
        to="/queue"
        class="stat-card queue-stat-card"
      >
        <div class="stat-icon queue-icon">
          <Clock :size="18" />
        </div>
        <div class="stat-info">
          <span class="stat-val">{{ activeQueueTasks.length }}</span>
          <span class="stat-lbl">Active in AI Queue &rarr;</span>
        </div>
      </router-link>

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
        <input type="checkbox" class="form-checkbox" style="margin-right: 8px;" @change="selectAllVisibleTasks" :checked="selectedTaskIds.size > 0 && selectedTaskIds.size === filteredReadyEvaluations.length" title="Select All Visible" />
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

        <!-- Match Score Quick Filter Chips matching 40 60 80 from Board -->
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
            :class="{ active: minFitFilter === 40 }"
            @click="minFitFilter = minFitFilter === 40 ? null : 40"
          >
            40%+
          </button>
          <button
            class="fit-chip"
            :class="{ active: minFitFilter === 60 }"
            @click="minFitFilter = minFitFilter === 60 ? null : 60"
          >
            60%+
          </button>
          <button
            class="fit-chip"
            :class="{ active: minFitFilter === 80 }"
            @click="minFitFilter = minFitFilter === 80 ? null : 80"
          >
            80%+
          </button>
        </div>

        <div class="max-fit-group">
          <span class="fit-filter-label">Max Fit:</span>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 100 }" @click="maxMatchFilter = 100">All</button>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 60 }" @click="maxMatchFilter = 60">&lt;60%</button>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 40 }" @click="maxMatchFilter = 40">&lt;40%</button>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 20 }" @click="maxMatchFilter = 20">&lt;20%</button>
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
        <button class="btn btn-primary mt-3" @click="uiStore.openJobIntakeModal">
          <Sparkles :size="14" />
          <span>Ingest Job Lead</span>
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
            <div class="eval-title-group" style="flex-direction: row; align-items: center; gap: 14px;">
              <input type="checkbox" class="form-checkbox" :checked="selectedTaskIds.has(task.id)" @change="toggleTaskSelection(task.id)" />
              <CompanyLogo
                :name="task.result_json?.company || task.title_hint"
                :domain="task.result_json?.company_url || task.result_json?.company_domain"
                :size="44"
              />
              <div>
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
              <span>{{ normalizeWorkModel(task.result_json.work_model) }}</span>
            </span>

            <span class="meta-chip date-chip text-muted">
              <Clock :size="11" />
              <span>Assessed {{ formatRelativeDate(task.created_at, false) }}</span>
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
              <div v-if="task.result_json?.matching_skills?.length" class="skills-group" style="background-color: var(--status-offer-bg); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--status-offer-border);">
                <span class="group-title text-success">Matching CV Skills ({{ task.result_json.matching_skills.length }}):</span>
                <div class="skill-tags">
                  <span v-for="s in task.result_json.matching_skills" :key="s" class="skill-tag match-tag">
                    <Check :size="11" />
                    <span>{{ s }}</span>
                  </span>
                </div>
              </div>

              <div v-if="task.result_json?.missing_skills?.length" class="skills-group" style="background-color: var(--status-rejected-bg); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--status-rejected-border);">
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
              <div class="tailoring-header" style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
                <Sparkles :size="14" class="text-primary" />
                <span>Recommended Resume Tailoring Strategy</span>
              </div>

              <div v-if="parsedTailoringStrategy(task)" class="tailoring-parsed">
                 <!-- Impact Reframing -->
                 <div v-if="parsedTailoringStrategy(task).impact_reframing?.length" class="tailoring-block">
                   <h4 class="tailoring-subtitle">Impact Reframing</h4>
                   <div v-for="(item, i) in parsedTailoringStrategy(task).impact_reframing" :key="i" class="reframing-card">
                     <div class="reframing-reason">{{ item.reason }}</div>
                     <div class="reframing-before">
                       <span class="reframing-label">Before:</span>
                       <span class="reframing-text">{{ item.bullet_point }}</span>
                     </div>
                     <div class="reframing-after">
                       <span class="reframing-label">After:</span>
                       <span class="reframing-text">{{ item.suggested_rewrite }}</span>
                     </div>
                   </div>
                 </div>

                 <!-- Structural Adjustments -->
                 <div v-if="parsedTailoringStrategy(task).structural_adjustments?.length" class="tailoring-block">
                   <h4 class="tailoring-subtitle">Structural Adjustments</h4>
                   <ul class="structural-list">
                     <li v-for="(adj, i) in parsedTailoringStrategy(task).structural_adjustments" :key="i">
                       <CheckCircle2 :size="13" class="text-primary mt-0.5" />
                       <span>{{ adj }}</span>
                     </li>
                   </ul>
                 </div>

                 <!-- Vocabulary Translation -->
                 <div v-if="parsedTailoringStrategy(task).vocabulary_translation?.length" class="tailoring-block">
                   <h4 class="tailoring-subtitle">Vocabulary Mapping</h4>
                   <div class="vocab-grid">
                     <div v-for="(vocab, i) in parsedTailoringStrategy(task).vocabulary_translation" :key="i" class="vocab-card">
                       <div class="vocab-flow">
                         <span class="vocab-cv">{{ vocab.cv_term }}</span>
                         <span class="vocab-arrow">➔</span>
                         <span class="vocab-jd">{{ vocab.jd_term }}</span>
                       </div>
                       <div class="vocab-desc">{{ vocab.replacement_guidance }}</div>
                     </div>
                   </div>
                 </div>
               </div>

              <p v-else class="tailoring-text">{{ task.result_json.tailoring_strategy }}</p>
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

              <!-- Dynamic Cover Letter Action Button -->
              <button
                v-if="task.result_json?.cover_letter_status === 'GENERATING' || coverLetterGeneratingTaskIds.has(task.id)"
                class="btn btn-secondary btn-sm"
                disabled
              >
                <Loader2 class="animate-spin" :size="14" />
                <span>Drafting...</span>
              </button>

              <button
                v-else-if="task.result_json?.cover_letter_markdown || task.result_json?.cover_letter_status === 'COMPLETED'"
                class="btn btn-primary btn-sm"
                title="View and edit tailored cover letter draft"
                @click="openCoverLetterModal(task)"
              >
                <FileText :size="14" />
                <span>View Cover Letter</span>
              </button>

              <button
                v-else
                class="btn btn-secondary btn-sm"
                title="Generate tailored cover letter draft with AI"
                @click="task.result_json?.application_id ? openCoverLetterModal(task) : handleGenerateCoverLetter(task)"
              >
                <Sparkles :size="14" />
                <span>Generate Cover Letter</span>
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
                <span>Mark as Applied</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: PASSED / ARCHIVED (FULL FILTERING & INFORMATION PARITY) -->
    <div v-else-if="activeTab === 'passed'" class="tab-view animate-fade-in">
      <!-- Toolbar Filter Bar matching Ready tab -->
      <div class="eval-filter-toolbar">
        <input
          type="checkbox"
          class="form-checkbox"
          style="margin-right: 8px;"
          @change="selectAllVisibleTasks"
          :checked="selectedTaskIds.size > 0 && selectedTaskIds.size === filteredPassedEvaluations.length"
          title="Select All Visible"
        />
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

        <!-- Match Score Quick Filter Chips matching 40 60 80 -->
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
            :class="{ active: minFitFilter === 40 }"
            @click="minFitFilter = minFitFilter === 40 ? null : 40"
          >
            40%+
          </button>
          <button
            class="fit-chip"
            :class="{ active: minFitFilter === 60 }"
            @click="minFitFilter = minFitFilter === 60 ? null : 60"
          >
            60%+
          </button>
          <button
            class="fit-chip"
            :class="{ active: minFitFilter === 80 }"
            @click="minFitFilter = minFitFilter === 80 ? null : 80"
          >
            80%+
          </button>
        </div>

        <div class="max-fit-group">
          <span class="fit-filter-label">Max Fit:</span>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 100 }" @click="maxMatchFilter = 100">All</button>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 60 }" @click="maxMatchFilter = 60">&lt;60%</button>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 40 }" @click="maxMatchFilter = 40">&lt;40%</button>
          <button class="fit-chip" :class="{ active: maxMatchFilter === 20 }" @click="maxMatchFilter = 20">&lt;20%</button>
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

      <div v-if="filteredPassedEvaluations.length === 0" class="empty-state-box">
        <Archive :size="40" class="empty-state-icon" />
        <h3 class="empty-state-title">No passed evaluations found</h3>
        <p class="empty-state-desc">Evaluations you archive as 'Passed' will be safely stored here with full dossier context.</p>
      </div>

      <div v-else class="eval-cards-grid">
        <div
          v-for="task in filteredPassedEvaluations"
          :key="task.id"
          class="eval-card passed-eval-card"
          :class="{ expanded: expandedTaskIds.has(task.id) }"
        >
          <!-- Card Header Row -->
          <div class="eval-card-header">
            <div class="eval-title-group" style="flex-direction: row; align-items: center; gap: 14px;">
              <input
                type="checkbox"
                class="form-checkbox"
                :checked="selectedTaskIds.has(task.id)"
                @change="toggleTaskSelection(task.id)"
              />
              <CompanyLogo
                :name="task.result_json?.company || task.title_hint"
                :domain="task.result_json?.company_url || task.result_json?.company_domain"
                :size="44"
              />
              <div>
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
              <span>{{ normalizeWorkModel(task.result_json.work_model) }}</span>
            </span>

            <span class="meta-chip date-chip text-muted">
              <Clock :size="11" />
              <span>Assessed {{ formatRelativeDate(task.created_at, false) }}</span>
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
              <div v-if="task.result_json?.matching_skills?.length" class="skills-group" style="background-color: var(--status-offer-bg); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--status-offer-border);">
                <span class="group-title text-success">Matching CV Skills ({{ task.result_json.matching_skills.length }}):</span>
                <div class="skill-tags">
                  <span v-for="s in task.result_json.matching_skills" :key="s" class="skill-tag match-tag">
                    <Check :size="11" />
                    <span>{{ s }}</span>
                  </span>
                </div>
              </div>

              <div v-if="task.result_json?.missing_skills?.length" class="skills-group" style="background-color: var(--status-rejected-bg); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--status-rejected-border);">
                <span class="group-title text-warning">Missing / Required Skills ({{ task.result_json.missing_skills.length }}):</span>
                <div class="skill-tags">
                  <span v-for="s in task.result_json.missing_skills" :key="s" class="skill-tag gap-tag">
                    <span>{{ s }}</span>
                  </span>
                </div>
              </div>
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
                title="Permanently delete evaluation"
                @click="deleteEvaluation(task.id)"
              >
                <Trash2 :size="14" />
              </button>

              <button
                class="btn btn-primary btn-sm"
                title="Convert to active application"
                @click="markAsApplied(task)"
              >
                <CheckCircle2 :size="13" />
                <span>Apply Anyway</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Cover Letter Editor Modal -->
    <CoverLetterModal
      :is-open="isCoverLetterModalOpen"
      :application-id="selectedCoverLetterTask?.result_json?.application_id"
      :application-title="selectedCoverLetterTask?.result_json?.position || 'Software Engineer'"
      :company-name="selectedCoverLetterTask?.result_json?.company || selectedCoverLetterTask?.title_hint"
      @close="isCoverLetterModalOpen = false"
      @saved="loadEvaluations(true)"
      @generated="loadEvaluations(true)"
    />

    <!-- Batch Actions Floating Bar -->
    <Transition name="slide-up">
      <div v-if="selectedTaskIds.size > 0" class="batch-actions-bar">
        <div class="batch-info">
          <span class="batch-count">{{ selectedTaskIds.size }} Selected</span>
          <button class="btn btn-ghost btn-sm" @click="selectedTaskIds.clear()">Clear</button>
        </div>
        <div class="batch-buttons">
          <button class="btn btn-secondary btn-sm" @click="bulkArchive">
            <Archive :size="14" />
            <span>Discard / Archive</span>
          </button>
          <button class="btn btn-primary btn-sm" @click="bulkMarkAsApplied">
            <CheckCircle :size="14" />
            <span>Mark as Applied</span>
          </button>
        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.assessments-page {
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
  min-height: calc(100vh - var(--navbar-height));
  width: 100%;
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

.queue-stat-card {
  text-decoration: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.queue-stat-card:hover {
  border-color: var(--primary-glow);
  box-shadow: 0 0 10px var(--primary-subtle);
  transform: translateY(-1px);
}

.active-queue-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.banner-text {
  font-size: 13px;
  color: var(--text-main);
}

.live-pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--primary);
  box-shadow: 0 0 6px var(--primary-glow);
  animation: pulse-ring 1.5s infinite;
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

.tailoring-parsed { display: flex; flex-direction: column; gap: 16px; margin-top: 4px; }
.tailoring-block { display: flex; flex-direction: column; gap: 8px; }
.tailoring-subtitle { font-size: 13px; font-weight: 700; color: var(--text-main); text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; margin: 0 0 4px 0; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px; }
.reframing-card { background-color: var(--bg-app); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 10px; display: flex; flex-direction: column; gap: 6px; }
.reframing-reason { font-size: 11px; font-weight: 600; color: var(--text-muted); background-color: var(--bg-surface); display: inline-flex; padding: 2px 6px; border-radius: 4px; width: fit-content; margin-bottom: 2px; }
.reframing-before, .reframing-after { font-size: 12px; line-height: 1.4; display: flex; gap: 6px; }
.reframing-before { color: var(--status-rejected-text); opacity: 0.9; }
.reframing-after { color: var(--status-offer-text); font-weight: 500; }
.reframing-label { font-weight: 700; flex-shrink: 0; }
.reframing-before .reframing-text { text-decoration: line-through; }
.structural-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.structural-list li { font-size: 12px; color: var(--text-secondary); line-height: 1.4; display: flex; align-items: flex-start; gap: 6px; }
.vocab-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
.vocab-card { background-color: var(--bg-app); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.vocab-flow { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; }
.vocab-cv { color: var(--text-muted); background-color: var(--bg-surface); padding: 2px 6px; border-radius: 4px; text-decoration: line-through; }
.vocab-arrow { color: var(--text-secondary); font-size: 10px; }
.vocab-jd { color: var(--primary); background-color: var(--primary-subtle); padding: 2px 6px; border-radius: 4px; }
.vocab-desc { font-size: 11px; color: var(--text-secondary); line-height: 1.4; margin-top: 4px; }


.max-fit-group {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.range-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.range-slider {
  width: 80px;
  accent-color: var(--primary);
}

.range-val {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-main);
  min-width: 3ch;
}

.form-checkbox {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  accent-color: var(--primary);
  cursor: pointer;
}

.batch-actions-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  z-index: 100;
}

.batch-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.batch-count {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.batch-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translate(-50%, 100%);
  opacity: 0;
}

</style>
