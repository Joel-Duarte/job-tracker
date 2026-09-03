<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { useQueueStore } from '../../stores/queueStore'
import { ApplicationsAPI, CompaniesAPI } from '../../api/endpoints'
import {
  X,
  HelpCircle,
  Sparkles,
  RotateCcw,
  Check,
  Loader2,
  Copy,
  Plus,
  Trash2,
  Sliders,
  ChevronDown,
  ChevronUp,
  Clock,
  AlertCircle,
  FileText,
  Layers,
  ArrowRight,
  Globe,
  RefreshCw,
  ExternalLink,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()
const queueStore = useQueueStore()

const { isAppQuestionsModalOpen, appQuestionsAppId } = storeToRefs(uiStore)

const application = ref(null)
const isLoadingApp = ref(false)
const isGenerating = ref(false)
const generationError = ref(null)

let pollTimer = null

// Question List State
const questions = ref([])
const tone = ref('professional')
const customInstructions = ref('')
const isOptionsExpanded = ref(false)
const showBulkPaste = ref(false)
const bulkPasteText = ref('')

// Company Research State
const includeCompanyResearch = ref(true)
const companyResearch = ref(null)
const isRefreshingResearch = ref(false)
const isResearchExpanded = ref(false)

// Auto-save state
const autoSaveStatus = ref('saved') // 'saved' | 'saving' | 'error' | 'unsaved'
let autoSaveTimer = null

const QA_TONES = [
  { code: 'professional', label: 'Professional & Confident' },
  { code: 'enthusiastic', label: 'Enthusiastic & Passionate' },
  { code: 'concise', label: 'Concise & Direct' },
  { code: 'executive', label: 'Executive Leadership' },
  { code: 'technical', label: 'Technical & Systems Focused' },
]

const PRESET_CHIPS = [
  { label: 'Why this company & role?', text: 'Why are you interested in joining our team and working at our company?', wordLimit: 150 },
  { label: 'Challenging problem solved', text: 'Describe a complex technical problem or system challenge you diagnosed and resolved.', wordLimit: 250 },
  { label: 'Experience with tech stack', text: 'What is your background and experience with our primary technologies and architecture?', wordLimit: 150 },
  { label: 'Why looking for a new role?', text: 'Why are you currently exploring new opportunities and looking to transition?', wordLimit: 100 },
  { label: 'Handling feedback / conflict', text: 'Tell us about a time you received critical feedback or had a technical disagreement with a colleague.', wordLimit: 200 },
]

const activeQATask = computed(() => {
  if (!appQuestionsAppId.value) return null
  return (
    queueStore.tasks.find(
      (t) =>
        t.task_type === 'APPLICATION_QA' &&
        (t.result_json?.application_id === appQuestionsAppId.value || t.raw_text === String(appQuestionsAppId.value)) &&
        ['QUEUED', 'PROCESSING'].includes(t.status)
    ) || null
  )
})

const failedQATask = computed(() => {
  if (!appQuestionsAppId.value) return null
  return (
    queueStore.tasks.find(
      (t) =>
        t.task_type === 'APPLICATION_QA' &&
        (t.result_json?.application_id === appQuestionsAppId.value || t.raw_text === String(appQuestionsAppId.value)) &&
        ['FAILED', 'CANCELLED'].includes(t.status)
    ) || null
  )
})

const queuePositionInfo = computed(() => {
  if (!activeQATask.value) {
    if (isGenerating.value) {
      return {
        statusText: 'AI Generating...',
        stageText: 'Synthesizing tailored answers from candidate profile & JD',
        isProcessing: true,
        position: null,
      }
    }
    return null
  }
  const task = activeQATask.value
  if (task.status === 'PROCESSING') {
    return {
      statusText: 'Synthesizing with AI...',
      stageText: task.stage === 'ANSWERING' ? 'Drafting grounded answers from CV & company data' : 'Processing in AI Engine',
      isProcessing: true,
      position: null,
    }
  }
  const activeQueued = queueStore.activeTasks.filter((t) => t.status === 'QUEUED')
  const pos = activeQueued.findIndex((t) => t.id === task.id)
  const positionNumber = pos >= 0 ? pos + 1 : 1
  return {
    statusText: `Position #${positionNumber} in AI Queue`,
    stageText: `Waiting in queue (${positionNumber} of ${queueStore.pendingCount || activeQueued.length})`,
    isProcessing: false,
    position: positionNumber,
  }
})

const isCurrentlyGenerating = computed(() => isGenerating.value || !!activeQATask.value)

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!appQuestionsAppId.value) return
    await queueStore.fetchTasks(true)
    const active = activeQATask.value
    if (!active) {
      stopPolling()
      isGenerating.value = false
      await loadApplicationData(appQuestionsAppId.value)
    }
  }, 2500)
}

watch(
  isAppQuestionsModalOpen,
  async (isOpen) => {
    if (isOpen && appQuestionsAppId.value) {
      generationError.value = null
      await loadApplicationData(appQuestionsAppId.value)
      if (activeQATask.value) {
        startPolling()
      }
    } else {
      stopPolling()
      application.value = null
      questions.value = []
      showBulkPaste.value = false
      bulkPasteText.value = ''
    }
  },
  { immediate: true }
)

watch(
  activeQATask,
  (newTask, oldTask) => {
    if (newTask && !oldTask) {
      startPolling()
    } else if (!newTask && oldTask) {
      stopPolling()
      isGenerating.value = false
      if (appQuestionsAppId.value) {
        loadApplicationData(appQuestionsAppId.value)
      }
    }
  }
)

async function loadApplicationData(appId) {
  isLoadingApp.value = true
  try {
    const res = await ApplicationsAPI.get(appId)
    application.value = res.data

    companyResearch.value = application.value.company?.company_research
      ? { ...application.value.company.company_research }
      : null

    const qRes = await ApplicationsAPI.getApplicationQuestions(appId)
    const rawQs = qRes.data?.questions || []
    if (rawQs.length > 0) {
      questions.value = rawQs.map(q => ({
        id: q.id || `q_${Math.random().toString(36).substring(2, 9)}`,
        question: q.question || '',
        word_limit: q.word_limit || null,
        answer: q.answer || '',
        status: q.status || 'DRAFT',
      }))
    } else if (questions.value.length === 0) {
      // Default initial question if empty
      questions.value = [
        {
          id: `q_${Math.random().toString(36).substring(2, 9)}`,
          question: `Why are you interested in joining ${application.value.company?.name || 'our company'}?`,
          word_limit: 150,
          answer: '',
          status: 'DRAFT',
        },
      ]
    }
    autoSaveStatus.value = 'saved'
  } catch (err) {
    console.error('Failed to load application questions:', err)
    uiStore.showToast('Failed to load application questions', 'error')
  } finally {
    isLoadingApp.value = false
  }
}

async function handleRefreshCompanyResearch() {
  if (!application.value?.company?.id) return
  isRefreshingResearch.value = true
  try {
    const res = await CompaniesAPI.refreshResearch(application.value.company.id)
    if (res.data?.company_research) {
      companyResearch.value = { ...res.data.company_research }
      uiStore.showToast('Company intelligence refreshed from web!', 'success')
    } else {
      uiStore.showToast('No company web results found', 'info')
    }
  } catch (err) {
    console.error('Failed to refresh company research:', err)
    uiStore.showToast('Failed to refresh company research', 'error')
  } finally {
    isRefreshingResearch.value = false
  }
}

function addQuestion(preset = null) {
  const newQ = {
    id: `q_${Math.random().toString(36).substring(2, 9)}`,
    question: preset?.text || '',
    word_limit: preset?.wordLimit || null,
    answer: '',
    status: 'DRAFT',
  }
  questions.value.push(newQ)
  triggerAutoSave()
}

function removeQuestion(index) {
  questions.value.splice(index, 1)
  triggerAutoSave()
}

function parseBulkQuestions() {
  if (!bulkPasteText.value.trim()) return
  const lines = bulkPasteText.value.split(/\n+/).map(l => l.trim()).filter(Boolean)
  const parsed = []

  for (const line of lines) {
    // Strip bullet numbers e.g. "1. ", "1) ", "- "
    const cleaned = line.replace(/^(\d+[\.\)]\s*|[-*•]\s*)/, '').trim()
    if (cleaned.length > 5) {
      parsed.push({
        id: `q_${Math.random().toString(36).substring(2, 9)}`,
        question: cleaned,
        word_limit: null,
        answer: '',
        status: 'DRAFT',
      })
    }
  }

  if (parsed.length > 0) {
    questions.value.push(...parsed)
    showBulkPaste.value = false
    bulkPasteText.value = ''
    uiStore.showToast(`Added ${parsed.length} questions from pasted text`, 'success')
    triggerAutoSave()
  } else {
    uiStore.showToast('Could not identify questions in pasted text', 'warning')
  }
}

function triggerAutoSave() {
  autoSaveStatus.value = 'unsaved'
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(async () => {
    await saveQuestionsToServer()
  }, 1200)
}

async function saveQuestionsToServer() {
  if (!appQuestionsAppId.value || questions.value.length === 0) return
  autoSaveStatus.value = 'saving'
  try {
    await ApplicationsAPI.updateApplicationQuestions(appQuestionsAppId.value, {
      questions: questions.value,
    })
    autoSaveStatus.value = 'saved'
  } catch (err) {
    console.error('Failed to auto-save application questions:', err)
    autoSaveStatus.value = 'error'
  }
}

async function handleGenerate() {
  if (!(await uiStore.ensureAIReady())) return
  if (!appQuestionsAppId.value) return

  const validQuestions = questions.value.filter(q => q.question.trim().length > 0)
  if (validQuestions.length === 0) {
    uiStore.showToast('Please enter at least one question to answer', 'warning')
    return
  }

  isGenerating.value = true
  generationError.value = null

  try {
    const payload = {
      questions: validQuestions,
      tone: tone.value,
      custom_instructions: customInstructions.value.trim() || null,
      include_company_research: includeCompanyResearch.value,
      company_research: includeCompanyResearch.value ? companyResearch.value : null,
    }

    const res = await ApplicationsAPI.generateApplicationQuestions(appQuestionsAppId.value, payload)

    questions.value = (res.data?.questions || validQuestions).map(q => ({
      id: q.id,
      question: q.question,
      word_limit: q.word_limit,
      answer: q.answer || '',
      status: 'QUEUED',
    }))

    uiStore.showToast('✨ Form Q&A generation queued in AI Engine', 'info')
    await queueStore.fetchTasks(true)
    startPolling()
  } catch (err) {
    console.error('Failed to generate answers:', err)
    generationError.value = err.response?.data?.detail || err.message || 'Failed to queue generation'
    uiStore.showToast(generationError.value, 'error')
    isGenerating.value = false
  }
}

function getWordCount(text) {
  if (!text) return 0
  const trimmed = text.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
}

const copySuccessMap = ref({})
function copySingleAnswer(q) {
  if (!q.answer) return
  navigator.clipboard.writeText(q.answer)
  copySuccessMap.value[q.id] = true
  uiStore.showToast('Copied answer to clipboard!', 'success')
  setTimeout(() => {
    delete copySuccessMap.value[q.id]
  }, 2000)
}

function copyAllQA() {
  const answered = questions.value.filter(q => q.answer && q.answer.trim())
  if (answered.length === 0) {
    uiStore.showToast('No answers to copy', 'warning')
    return
  }
  const formatted = answered
    .map((q, i) => `Question ${i + 1}: ${q.question}\nAnswer: ${q.answer}`)
    .join('\n\n')
  navigator.clipboard.writeText(formatted)
  uiStore.showToast(`Copied ${answered.length} answers to clipboard!`, 'success')
}

function handleClose() {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
    saveQuestionsToServer()
  }
  uiStore.closeAppQuestionsModal()
}

onUnmounted(() => {
  stopPolling()
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
})
</script>

<template>
  <div v-if="isAppQuestionsModalOpen" class="modal-backdrop" @click.self="handleClose">
    <div class="modal-card animate-fade-in qa-modal-container">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-left">
          <div class="header-icon-badge">
            <HelpCircle :size="18" class="text-primary" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h2 class="modal-title">Application Form Q&A Generator</h2>
              <span v-if="application?.company?.name" class="company-badge">
                {{ application.company.name }}
              </span>
            </div>
            <p class="modal-subtitle">
              {{ application?.position || 'Target Role' }} • Grounded strictly in candidate CV profile
            </p>
          </div>
        </div>

        <div class="header-right">
          <!-- Auto-save Status Indicator -->
          <div class="auto-save-indicator" :class="autoSaveStatus">
            <span v-if="autoSaveStatus === 'saving'" class="flex items-center gap-1">
              <Loader2 :size="12" class="animate-spin" /> Saving...
            </span>
            <span v-else-if="autoSaveStatus === 'saved'" class="flex items-center gap-1 text-muted">
              <Check :size="12" class="text-success" /> Auto-saved
            </span>
            <span v-else-if="autoSaveStatus === 'unsaved'" class="text-muted">
              Unsaved changes
            </span>
            <span v-else-if="autoSaveStatus === 'error'" class="text-danger">
              Save error
            </span>
          </div>

          <button class="btn-close" @click="handleClose" title="Close Q&A Modal">
            <X :size="18" />
          </button>
        </div>
      </div>

      <!-- Live AI Queue Banner -->
      <div v-if="queuePositionInfo" class="queue-status-banner animate-fade-in">
        <div class="flex items-center gap-3">
          <Loader2 class="animate-spin text-primary" :size="18" />
          <div>
            <span class="font-semibold text-primary block text-sm">{{ queuePositionInfo.statusText }}</span>
            <span class="text-xs text-muted">{{ queuePositionInfo.stageText }}</span>
          </div>
        </div>
        <div class="queue-pulse-badge">
          <span class="pulse-dot"></span>
          <span>Live Processing</span>
        </div>
      </div>

      <!-- Failed Task Banner -->
      <div v-if="failedQATask && !isCurrentlyGenerating" class="failure-banner animate-fade-in">
        <div class="flex items-center gap-2 text-danger">
          <AlertCircle :size="16" />
          <span class="text-sm font-medium">Generation task failed: {{ failedQATask.error_message || 'AI Engine error' }}</span>
        </div>
        <button class="btn btn-sm btn-secondary" @click="handleGenerate">
          <RotateCcw :size="13" />
          <span>Retry Generation</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body-scroll">
        <div v-if="isLoadingApp" class="state-container">
          <Loader2 class="animate-spin text-primary" :size="32" />
          <span>Loading questions & application data...</span>
        </div>

        <div v-else class="qa-content-layout">
          <!-- Preset Quick-Add Chips -->
          <div class="preset-chips-section">
            <div class="preset-header">
              <Sparkles :size="14" class="text-primary" />
              <span class="text-xs font-semibold text-muted uppercase tracking-wider">Quick-Add Common ATS Questions:</span>
            </div>
            <div class="chips-container">
              <button
                v-for="(chip, idx) in PRESET_CHIPS"
                :key="idx"
                class="chip-btn"
                @click="addQuestion(chip)"
                title="Add this question to your list"
              >
                <Plus :size="12" />
                <span>{{ chip.label }}</span>
              </button>
              <button
                class="chip-btn chip-bulk"
                :class="{ active: showBulkPaste }"
                @click="showBulkPaste = !showBulkPaste"
              >
                <Layers :size="12" />
                <span>{{ showBulkPaste ? 'Hide Bulk Paste' : 'Paste Questionnaire' }}</span>
              </button>
            </div>
          </div>

          <!-- Bulk Questionnaire Input Drawer -->
          <div v-if="showBulkPaste" class="bulk-paste-card animate-fade-in">
            <div class="flex items-center justify-between mb-2">
              <label class="font-medium text-xs text-main">Paste Application Form Questions (One per line)</label>
              <button class="btn btn-xs btn-ghost" @click="showBulkPaste = false">
                <X :size="13" />
              </button>
            </div>
            <textarea
              v-model="bulkPasteText"
              class="form-textarea bulk-textarea font-sans"
              rows="4"
              placeholder="1. Why are you interested in this role?&#10;2. What experience do you have with distributed databases?&#10;3. Describe a time you resolved an outage."
            ></textarea>
            <div class="flex justify-end gap-2 mt-2">
              <button class="btn btn-secondary btn-xs" @click="bulkPasteText = ''; showBulkPaste = false">Cancel</button>
              <button class="btn btn-primary btn-xs" :disabled="!bulkPasteText.trim()" @click="parseBulkQuestions">
                <Plus :size="12" />
                <span>Parse &amp; Add Questions</span>
              </button>
            </div>
          </div>

          <!-- Questions List -->
          <div class="questions-list">
            <div
              v-for="(q, index) in questions"
              :key="q.id"
              class="question-card"
              :class="{ 'is-queued': q.status === 'QUEUED', 'has-answer': !!q.answer }"
            >
              <!-- Question Card Header -->
              <div class="question-header">
                <div class="q-badge">Q{{ index + 1 }}</div>
                <div class="q-input-wrap">
                  <input
                    v-model="q.question"
                    type="text"
                    class="q-input"
                    placeholder="Enter application question..."
                    @input="triggerAutoSave"
                  />
                </div>
                <div class="q-actions">
                  <div class="limit-input-wrap" title="Optional word count constraint">
                    <span class="limit-label">Limit:</span>
                    <input
                      v-model.number="q.word_limit"
                      type="number"
                      min="20"
                      max="1000"
                      step="10"
                      placeholder="No limit"
                      class="limit-input"
                      @change="triggerAutoSave"
                    />
                    <span class="limit-unit">words</span>
                  </div>
                  <button
                    class="btn-icon-danger"
                    title="Remove question"
                    @click="removeQuestion(index)"
                  >
                    <Trash2 :size="14" />
                  </button>
                </div>
              </div>

              <!-- Answer Area -->
              <div class="answer-container">
                <div v-if="q.status === 'QUEUED' && isCurrentlyGenerating" class="answer-generating-state">
                  <Loader2 class="animate-spin text-primary" :size="20" />
                  <span class="text-xs text-muted">Drafting grounded response with AI...</span>
                </div>

                <div v-else class="answer-editor-wrap">
                  <textarea
                    v-model="q.answer"
                    class="answer-textarea"
                    rows="4"
                    :placeholder="`AI response will appear here. You can also manually type or edit answers...`"
                    @input="triggerAutoSave"
                  ></textarea>

                  <!-- Answer Footer Meta -->
                  <div class="answer-footer">
                    <div class="meta-left">
                      <span
                        class="word-count-badge"
                        :class="{
                          'over-limit': q.word_limit && getWordCount(q.answer) > q.word_limit,
                          'near-limit': q.word_limit && getWordCount(q.answer) >= q.word_limit * 0.9 && getWordCount(q.answer) <= q.word_limit
                        }"
                      >
                        {{ getWordCount(q.answer) }} words
                        <span v-if="q.word_limit"> / {{ q.word_limit }} max</span>
                      </span>
                      <span v-if="q.answer" class="grounding-tag">
                        <Check :size="11" class="text-success" /> Strictly grounded in CV
                      </span>
                    </div>

                    <div class="meta-right">
                      <button
                        v-if="q.answer"
                        class="btn-copy-small"
                        :class="{ copied: copySuccessMap[q.id] }"
                        @click="copySingleAnswer(q)"
                        title="Copy this answer to clipboard"
                      >
                        <Check v-if="copySuccessMap[q.id]" :size="12" class="text-success" />
                        <Copy v-else :size="12" />
                        <span>{{ copySuccessMap[q.id] ? 'Copied!' : 'Copy Answer' }}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Add Question Bottom Row -->
            <button class="btn-add-question" @click="addQuestion()">
              <Plus :size="15" />
              <span>Add Another Question</span>
            </button>
          </div>

          <!-- Advanced Drafting Options Accordion -->
          <div class="options-accordion">
            <button class="options-toggle" @click="isOptionsExpanded = !isOptionsExpanded">
              <div class="flex items-center gap-2">
                <Sliders :size="14" class="text-primary" />
                <span class="text-xs font-semibold text-main">AI Drafting Settings &amp; Tone</span>
                <span class="text-xs text-muted font-normal">• Tone: {{ QA_TONES.find(t => t.code === tone)?.label }}</span>
              </div>
              <component :is="isOptionsExpanded ? ChevronUp : ChevronDown" :size="15" class="text-muted" />
            </button>

            <div v-show="isOptionsExpanded" class="options-body animate-fade-in">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="form-label text-xs">Response Tone &amp; Style</label>
                  <select v-model="tone" class="form-select text-xs">
                    <option v-for="t in QA_TONES" :key="t.code" :value="t.code">
                      {{ t.label }}
                    </option>
                  </select>
                </div>
                <div>
                  <label class="form-label text-xs">Custom Directives / Specific Topics</label>
                  <input
                    v-model="customInstructions"
                    type="text"
                    class="form-input text-xs"
                    placeholder="e.g. Focus on high throughput Kafka pipelines &amp; mentoring"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Live Company Research Section -->
          <div class="company-research-card">
            <div class="research-card-header">
              <div class="research-header-left">
                <Globe :size="14" class="text-primary" />
                <span class="research-card-title">Live Company Research</span>
                <label class="research-toggle-label">
                  <input type="checkbox" v-model="includeCompanyResearch" />
                  <span>Include in answer generation</span>
                </label>
              </div>
              <div class="research-header-right">
                <button
                  type="button"
                  class="btn-refresh-research"
                  :disabled="isRefreshingResearch"
                  @click="handleRefreshCompanyResearch"
                  title="Refresh research from web"
                >
                  <Loader2 v-if="isRefreshingResearch" :size="12" class="animate-spin" />
                  <RefreshCw v-else :size="12" />
                  <span>{{ isRefreshingResearch ? 'Researching...' : 'Refresh from Web' }}</span>
                </button>
                <button
                  type="button"
                  class="btn-toggle-expand"
                  @click="isResearchExpanded = !isResearchExpanded"
                >
                  {{ isResearchExpanded ? 'Hide Details' : 'Preview & Edit' }}
                </button>
              </div>
            </div>

            <!-- Expandable Research Editor -->
            <div v-if="isResearchExpanded && includeCompanyResearch" class="research-card-body">
              <div v-if="companyResearch" class="research-fields-grid">
                <div class="research-field">
                  <label class="form-label text-xs">Mission & Focus</label>
                  <textarea
                    v-model="companyResearch.summary"
                    rows="2"
                    class="form-input form-input-sm"
                    placeholder="What does the company build and value..."
                  ></textarea>
                </div>
                <div class="research-field">
                  <label class="form-label text-xs">Engineering Culture</label>
                  <textarea
                    v-model="companyResearch.engineering_culture"
                    rows="2"
                    class="form-input form-input-sm"
                    placeholder="Engineering culture, tech stack focus..."
                  ></textarea>
                </div>
                <div class="research-field">
                  <label class="form-label text-xs">Recent Initiatives</label>
                  <input
                    v-model="companyResearch.recent_initiatives"
                    type="text"
                    class="form-input form-input-sm"
                    placeholder="Recent product launches, open source..."
                  />
                </div>
                <div v-if="companyResearch.sources?.length" class="research-sources">
                  <span class="text-xs text-muted">Sources:</span>
                  <a
                    v-for="(src, idx) in companyResearch.sources"
                    :key="idx"
                    :href="src"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="source-link"
                  >
                    <span>{{ src }}</span>
                    <ExternalLink :size="10" />
                  </a>
                </div>
              </div>
              <div v-else class="research-empty-state">
                <p class="text-xs text-muted">
                  No company intelligence found yet. Click <strong>"Refresh from Web"</strong> to pull live mission and culture data for {{ application?.company?.name || 'this company' }}.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <div class="footer-left">
          <button
            class="btn btn-secondary btn-sm"
            :disabled="!questions.some(q => q.answer && q.answer.trim())"
            @click="copyAllQA"
            title="Copy all questions and answers formatted for pasting"
          >
            <Copy :size="14" />
            <span>Copy All Answers</span>
          </button>
        </div>

        <div class="footer-right">
          <button class="btn btn-secondary btn-sm" @click="handleClose">Close</button>
          <button
            class="btn btn-primary btn-sm btn-generate"
            :disabled="isCurrentlyGenerating || questions.filter(q => q.question.trim()).length === 0"
            @click="handleGenerate"
          >
            <Loader2 v-if="isCurrentlyGenerating" class="animate-spin" :size="14" />
            <Sparkles v-else :size="14" />
            <span>{{ isCurrentlyGenerating ? 'Generating with AI...' : 'Generate Answers' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: var(--bg-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.qa-modal-container {
  width: 100%;
  max-width: 860px;
  max-height: 90vh;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon-badge {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background-color: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.company-badge {
  font-size: 11px;
  padding: 2px 7px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  font-weight: 600;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 2px 0 0 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.auto-save-indicator {
  font-size: 11px;
  font-family: var(--font-mono);
}

.btn-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-close:hover {
  color: var(--text-main);
  background-color: var(--bg-elevated);
}

.queue-status-banner {
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.12), rgba(99, 102, 241, 0.12));
  border-bottom: 1px solid rgba(56, 189, 248, 0.25);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.queue-pulse-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  background: rgba(56, 189, 248, 0.15);
  padding: 3px 8px;
  border-radius: 999px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--color-primary);
  animation: pulse 1.5s infinite;
}

.failure-banner {
  background-color: rgba(239, 68, 68, 0.1);
  border-bottom: 1px solid rgba(239, 68, 68, 0.2);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-body-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 18px 20px 24px 20px;
  background-color: var(--bg-app);
}

.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-muted);
}

.preset-chips-section {
  margin-bottom: 16px;
}

.preset-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-main);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.chip-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background-color: var(--bg-elevated);
}

.chip-bulk {
  border-style: dashed;
}

.chip-bulk.active {
  background-color: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.bulk-paste-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 16px;
}

.bulk-textarea {
  width: 100%;
  font-size: 12px;
  padding: 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-app);
  color: var(--text-main);
  resize: vertical;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.question-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color var(--transition-fast);
}

.question-card:hover {
  border-color: var(--border-color-hover, var(--border-color));
}

.question-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background-color: var(--bg-elevated);
  border-bottom: 1px solid var(--border-color);
}

.q-badge {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--color-primary);
  background: rgba(56, 189, 248, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.q-input-wrap {
  flex: 1;
}

.q-input {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.q-input::placeholder {
  color: var(--text-muted);
  font-weight: 400;
}

.q-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.limit-input-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.limit-label {
  font-size: 11px;
}

.limit-input {
  width: 55px;
  font-size: 11px;
  padding: 2px 4px;
  background-color: var(--bg-app);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-main);
  text-align: right;
}

.limit-unit {
  font-size: 11px;
}

.btn-icon-danger {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.btn-icon-danger:hover {
  color: var(--color-danger, #ef4444);
  background-color: rgba(239, 68, 68, 0.1);
}

.answer-container {
  padding: 12px 14px;
}

.answer-generating-state {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
}

.answer-textarea {
  width: 100%;
  background-color: var(--bg-app);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-main);
  resize: vertical;
  font-family: inherit;
  outline: none;
  transition: border-color var(--transition-fast);
}

.answer-textarea:focus {
  border-color: var(--color-primary);
}

.answer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.word-count-badge {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.word-count-badge.over-limit {
  color: var(--color-danger, #ef4444);
  font-weight: 700;
}

.word-count-badge.near-limit {
  color: var(--color-warning, #f59e0b);
}

.grounding-tag {
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 3px;
}

.btn-copy-small {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 3px 8px;
  color: var(--text-main);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-copy-small:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-add-question {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 10px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-add-question:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background-color: var(--bg-elevated);
}

.options-accordion {
  margin-top: 18px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.options-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: transparent;
  border: none;
  cursor: pointer;
}

.options-body {
  padding: 12px 14px 14px 14px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  flex-shrink: 0;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-research-card {
  margin-top: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.research-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.research-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.research-card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.research-toggle-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  margin-left: 6px;
}

.research-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-refresh-research,
.btn-toggle-expand {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 11px;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.btn-refresh-research:hover,
.btn-toggle-expand:hover {
  background: var(--bg-card-hover, var(--bg-card));
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.btn-refresh-research:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.research-card-body {
  border-top: 1px solid var(--border-color);
  padding-top: 10px;
}

.research-fields-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.research-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.research-sources {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.source-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--primary-color);
  text-decoration: none;
  background: var(--primary-light, rgba(99, 102, 241, 0.12));
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-link:hover {
  text-decoration: underline;
}

.research-empty-state {
  padding: 8px 0;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}
</style>
