<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { AIConfigAPI, EmailAccountsAPI, IntakeAPI, PromptsAPI, DiagnosticsAPI, SystemSettingsAPI } from '../api/endpoints'
import { getStorageMode, setStorageMode, isLocalOrDemoMode } from '../services/storageAdapter'
import { initAndSeedDatabase, exportLocalDatabaseJSON, importLocalDatabaseJSON } from '../db/localDatabase'
import CandidateProfileView from './CandidateProfileView.vue'
import PageHeader from '../components/common/PageHeader.vue'
import {
  Activity,
  Cpu,
  Layers,
  Mail,
  Plus,
  Trash2,
  Edit3,
  Play,
  Check,
  CheckCircle,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Server,
  FileCode,
  RotateCcw,
  Save,
  ShieldCheck,
  Thermometer,
  Zap,
  SlidersHorizontal,
  DollarSign,
  Globe,
  Palette,
  Clock,
  Key,
  RefreshCw,
  X,
  ExternalLink,
  Lock,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  BrainCircuit,
  Bot,
  Briefcase,
  Archive,
  Copy,
  Eye,
  EyeOff,
  Info,
  BookOpen,
  UserCheck,
  FileText,
  ArrowLeft,
  ArrowRight,
  Database,
  Download,
  Upload
} from 'lucide-vue-next'

const route = useRoute()
const uiStore = useUIStore()

const activeTab = ref(route.query.tab || 'studio') // 'studio' | 'providers' | 'email_accounts' | 'profile' | 'preferences'

watch(() => route.query.tab, (newTab) => {
  if (newTab) activeTab.value = newTab
})

// Local / Demo Mode State
const currentStorageMode = ref(getStorageMode())
const isResettingDemo = ref(false)
const isExportingJSON = ref(false)
const isImportingJSON = ref(false)
const jsonFileInput = ref(null)

async function changeStorageMode(mode) {
  setStorageMode(mode)
  currentStorageMode.value = mode
  uiStore.showToast(`Switched storage mode to '${mode}'. Reloading data...`, 'success')
  setTimeout(() => window.location.reload(), 600)
}

async function handleResetDemoData() {
  if (!confirm('Are you sure you want to reset demo data? This will overwrite all IndexedDB tables with the initial Staff Engineer mock dataset.')) return
  isResettingDemo.value = true
  try {
    await initAndSeedDatabase(true)
    uiStore.showToast('Demo dataset reset successfully!', 'success')
    setTimeout(() => window.location.reload(), 500)
  } catch (err) {
    uiStore.showToast(`Failed to reset demo data: ${err.message}`, 'error')
  } finally {
    isResettingDemo.value = false
  }
}

async function handleExportJSON() {
  isExportingJSON.value = true
  try {
    const jsonStr = await exportLocalDatabaseJSON()
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `job-tracker-backup-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(link)
    link.click()
    link.remove()
    uiStore.showToast('IndexedDB backup exported successfully!', 'success')
  } catch (err) {
    uiStore.showToast(`Export failed: ${err.message}`, 'error')
  } finally {
    isExportingJSON.value = false
  }
}

function triggerImportJSON() {
  jsonFileInput.value?.click()
}

async function handleImportFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  isImportingJSON.value = true
  try {
    const text = await file.text()
    await importLocalDatabaseJSON(text)
    uiStore.showToast('IndexedDB database restored successfully!', 'success')
    setTimeout(() => window.location.reload(), 600)
  } catch (err) {
    uiStore.showToast(`Import failed: ${err.message}`, 'error')
  } finally {
    isImportingJSON.value = false
  }
}

// AI Providers state
const providers = ref([])
const loadingProviders = ref(false)
const isProviderModalOpen = ref(false)
const editingProvider = ref(null)
const testingProviderId = ref(null)
const providerTestResults = ref({})
const providerForm = ref({
  name: '',
  provider_type: 'openai',
  base_url: 'http://127.0.0.1:11434',
  api_key: '',
  max_concurrency: 1,
  is_active: true,
})

// Unified Task Studio State
const bindings = ref([])
const promptsList = ref([])
const loadingStudio = ref(false)
const selectedTaskKey = ref('JD_EXTRACTION')
const studioProviderModels = ref([])
const providerModelsCache = ref({})
const loadingStudioModels = ref(false)
const isSavingStudio = ref(false)
const isResettingPrompt = ref(false)

const globalBinding = computed(() => {
  return bindings.value.find((b) => b.task_type === 'GLOBAL_DEFAULT') || null
})
const isAdvancedOpen = ref(false)

// Global Default Model Form State
const globalForm = ref({
  provider_id: null,
  model_name: '',
})
const globalProviderModels = ref([])
const loadingGlobalModels = ref(false)
const isSavingGlobal = ref(false)
const isSyncingGlobal = ref(false)
let globalAutoSaveTimer = null

const isExporting = ref(false)

async function exportDiagnostics() {
  if (isExporting.value) return
  isExporting.value = true
  try {
    const res = await DiagnosticsAPI.export()
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'diagnostics.zip')
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (err) {
    console.error('Failed to export diagnostics', err)
  } finally {
    isExporting.value = false
  }
}

function scheduleGlobalAutoSave(delay = 500) {
  if (isSyncingGlobal.value) return
  if (globalAutoSaveTimer) clearTimeout(globalAutoSaveTimer)
  globalAutoSaveTimer = setTimeout(() => {
    saveGlobalDefault(true)
  }, delay)
}

function syncGlobalForm() {
  isSyncingGlobal.value = true
  if (globalAutoSaveTimer) clearTimeout(globalAutoSaveTimer)
  const gb = globalBinding.value
  const chosenProviderId = gb?.provider_id || (providers.value[0]?.id || null)
  globalForm.value.provider_id = chosenProviderId
  globalForm.value.model_name = gb?.model_name || 'qwen/qwen3.5-9b'
  fetchGlobalModels(chosenProviderId)
  setTimeout(() => {
    isSyncingGlobal.value = false
  }, 150)
}

async function fetchGlobalModels(providerId, forceRefresh = false) {
  if (!providerId) {
    globalProviderModels.value = []
    return
  }
  if (!forceRefresh && providerModelsCache.value[providerId]) {
    globalProviderModels.value = providerModelsCache.value[providerId]
    return
  }
  loadingGlobalModels.value = true
  try {
    const res = await AIConfigAPI.getProviderModels(providerId)
    const models = res.data?.models || []
    providerModelsCache.value[providerId] = models
    globalProviderModels.value = models
  } catch (err) {
    globalProviderModels.value = []
  } finally {
    loadingGlobalModels.value = false
  }
}

function onGlobalProviderChange() {
  fetchGlobalModels(globalForm.value.provider_id)
  scheduleGlobalAutoSave(100)
}

function selectGlobalSuggestedModel(modelId) {
  globalForm.value.model_name = modelId
  scheduleGlobalAutoSave(50)
}

async function saveGlobalDefault(isAutoSave = false) {
  if (!globalForm.value.provider_id || !globalForm.value.model_name?.trim()) {
    if (!isAutoSave) {
      uiStore.showToast('Please select a provider and specify a model name.', 'warning')
    }
    return
  }
  isSavingGlobal.value = true
  const existingGb = globalBinding.value
  try {
    await AIConfigAPI.setBinding('GLOBAL_DEFAULT', {
      provider_id: globalForm.value.provider_id,
      model_name: globalForm.value.model_name.trim(),
      temperature: existingGb?.temperature !== undefined ? existingGb.temperature : 0.2,
      reasoning_effort: existingGb?.reasoning_effort || existingGb?.extra_kwargs?.reasoning_effort || 'none',
      max_tokens: existingGb?.max_tokens || undefined,
      extra_kwargs: existingGb?.extra_kwargs || {},
    })
    uiStore.showToast('Global default model updated', 'success')
    await loadBindings()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to set global model', 'error')
  } finally {
    isSavingGlobal.value = false
  }
}

const isResettingGlobal = ref(false)

async function resetGlobalDefaultToDefaults() {
  if (
    !confirm(
      'Reset ALL AI models, pipeline task settings, and prompt templates back to recommended factory defaults?'
    )
  ) {
    return
  }
  isResettingGlobal.value = true
  try {
    const firstProviderId = providers.value[0]?.id || null

    globalForm.value.provider_id = firstProviderId
    globalForm.value.model_name = 'qwen/qwen3.5-9b'
    await AIConfigAPI.setBinding('GLOBAL_DEFAULT', {
      provider_id: firstProviderId,
      model_name: 'qwen/qwen3.5-9b',
      temperature: 0.2,
      reasoning_effort: 'none',
      max_tokens: undefined,
      extra_kwargs: {},
    })

    for (const t of TASKS) {
      if (t.key === 'EMBEDDING') {
        await AIConfigAPI.setBinding('EMBEDDING', {
          provider_id: firstProviderId,
          model_name: 'nomic-embed-text',
          embedding_dimensions: 768,
          extra_kwargs: {},
        })
      } else {
        const defaultTemp = typeof t.recommendedTemp === 'number' ? t.recommendedTemp : 0.2
        const defaultReasoning = t.recommendedReasoning || 'none'
        await AIConfigAPI.setBinding(t.key, {
          provider_id: firstProviderId,
          model_name: 'qwen/qwen3.5-9b',
          temperature: defaultTemp,
          reasoning_effort: defaultReasoning,
          max_tokens: undefined,
          extra_kwargs: {
            use_global_default: true,
            reasoning_effort: defaultReasoning,
          },
        })
      }

      if (t.hasPrompt && t.promptKey) {
        try {
          await PromptsAPI.reset(t.promptKey)
        } catch {
          // ignore
        }
      }
    }

    uiStore.showToast('All AI models, task settings, and prompts reset to factory defaults!', 'success')
    await loadBindings()
    await loadPrompts()
    syncStudioForm()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to reset global defaults', 'error')
  } finally {
    isResettingGlobal.value = false
  }
}

function isTaskCustomized(taskKey) {
  const taskDef = TASKS.find((t) => t.key === taskKey)
  if (!taskDef) return false

  const b = bindings.value.find(
    (x) => x.task_type.toUpperCase() === taskKey.toUpperCase()
  )

  if (taskKey === 'EMBEDDING') {
    if (!b) return false
    const isCustomModel = b.model_name && b.model_name !== 'nomic-embed-text'
    const isCustomDims = b.embedding_dimensions && Number(b.embedding_dimensions) !== 768
    return Boolean(isCustomModel || isCustomDims)
  }

  if (b) {
    if (b.extra_kwargs?.use_global_default === false) {
      return true
    }
    if (
      typeof taskDef.recommendedTemp === 'number' &&
      b.temperature !== undefined &&
      b.temperature !== null &&
      Math.abs(Number(b.temperature) - taskDef.recommendedTemp) > 0.001
    ) {
      return true
    }
    const recReasoning = taskDef.recommendedReasoning || 'none'
    const actualReasoning = b.reasoning_effort || b.extra_kwargs?.reasoning_effort || 'none'
    if (actualReasoning !== recReasoning) {
      return true
    }
    if (b.max_tokens !== undefined && b.max_tokens !== null && b.max_tokens !== '') {
      return true
    }
  }

  return false
}

const enableEmbeddings = ref(true)
const isUpdatingEmbeddings = ref(false)
const isReindexingEmbeddings = ref(false)

const enableAutoCoverLetter = ref(false)
const coverLetterMatchThreshold = ref(70)
const coverLetterLength = ref('standard')
const isUpdatingCoverLetterSettings = ref(false)

async function loadGlobalSettings() {
  try {
    const res = await AIConfigAPI.getGlobalSettings()
    enableEmbeddings.value = res.data.ENABLE_EMBEDDINGS ?? true
    uiStore.enableEmbeddings = enableEmbeddings.value

    enableAutoCoverLetter.value = res.data.ENABLE_AUTO_COVER_LETTER ?? false
    coverLetterMatchThreshold.value = res.data.COVER_LETTER_MATCH_THRESHOLD ?? 70
    coverLetterLength.value = res.data.COVER_LETTER_LENGTH ?? 'standard'
    uiStore.enableAutoCoverLetter = enableAutoCoverLetter.value
    uiStore.coverLetterMatchThreshold = coverLetterMatchThreshold.value
    uiStore.coverLetterLength = coverLetterLength.value
  } catch (err) {
    console.error('Failed to load global settings', err)
  }
}

async function toggleAutoCoverLetter() {
  isUpdatingCoverLetterSettings.value = true
  try {
    const newVal = !enableAutoCoverLetter.value
    const res = await AIConfigAPI.updateGlobalSettings({ ENABLE_AUTO_COVER_LETTER: newVal })
    enableAutoCoverLetter.value = res.data.ENABLE_AUTO_COVER_LETTER
    uiStore.enableAutoCoverLetter = enableAutoCoverLetter.value
    uiStore.showToast(
      enableAutoCoverLetter.value
        ? 'Automatic cover letter generation enabled.'
        : 'Automatic cover letter generation disabled.',
      'success'
    )
  } catch (err) {
    uiStore.showToast('Failed to update cover letter setting', 'error')
  } finally {
    isUpdatingCoverLetterSettings.value = false
  }
}

async function updateCoverLetterLength(event) {
  const val = event.target.value
  coverLetterLength.value = val
  isUpdatingCoverLetterSettings.value = true
  try {
    const res = await AIConfigAPI.updateGlobalSettings({ COVER_LETTER_LENGTH: val })
    coverLetterLength.value = res.data.COVER_LETTER_LENGTH
    uiStore.coverLetterLength = res.data.COVER_LETTER_LENGTH
    uiStore.showToast(`Default cover letter length updated to ${val}.`, 'success')
  } catch (err) {
    uiStore.showToast('Failed to update cover letter length setting', 'error')
  } finally {
    isUpdatingCoverLetterSettings.value = false
  }
}

async function updateCoverLetterThreshold(event) {
  const val = Number(event.target.value)
  coverLetterMatchThreshold.value = val
  isUpdatingCoverLetterSettings.value = true
  try {
    const res = await AIConfigAPI.updateGlobalSettings({ COVER_LETTER_MATCH_THRESHOLD: val })
    coverLetterMatchThreshold.value = res.data.COVER_LETTER_MATCH_THRESHOLD
    uiStore.coverLetterMatchThreshold = coverLetterMatchThreshold.value
    uiStore.showToast(`Cover letter match threshold updated to ${val}%.`, 'success')
  } catch (err) {
    uiStore.showToast('Failed to update cover letter threshold', 'error')
  } finally {
    isUpdatingCoverLetterSettings.value = false
  }
}

async function toggleEmbeddings() {
  isUpdatingEmbeddings.value = true
  try {
    const newVal = !enableEmbeddings.value
    const res = await AIConfigAPI.updateGlobalSettings({ ENABLE_EMBEDDINGS: newVal })
    enableEmbeddings.value = res.data.ENABLE_EMBEDDINGS
    uiStore.enableEmbeddings = enableEmbeddings.value
    uiStore.showToast(
      enableEmbeddings.value
        ? 'Vector embeddings enabled.'
        : 'Vector embeddings disabled. Intake will run faster without embeddings.',
      'success'
    )
  } catch (err) {
    uiStore.showToast('Failed to update embeddings setting', 'error')
  } finally {
    isUpdatingEmbeddings.value = false
  }
}

async function toggleEmailIntake() {
  try {
    const newVal = !uiStore.enableEmailIntake
    await SystemSettingsAPI.update({ enable_email_intake: newVal })
    uiStore.enableEmailIntake = newVal
    uiStore.showToast(
      newVal ? 'Email Auto-Sync enabled.' : 'Email Auto-Sync disabled.',
      'success'
    )
    if (newVal && emailAccounts.value.length === 0) {
      openAddEmailAccountModal()
    }
  } catch (err) {
    uiStore.showToast('Failed to update email intake setting', 'error')
  }
}

async function reindexMissingEmbeddings() {
  isReindexingEmbeddings.value = true
  try {
    const res = await AIConfigAPI.reindexEmbeddings()
    uiStore.showToast(res.data.message || 'Embeddings backfill enqueued!', 'success')
  } catch (err) {
    uiStore.showToast('Failed to reindex embeddings: ' + (err.response?.data?.detail || err.message), 'error')
  } finally {
    isReindexingEmbeddings.value = false
  }
}

const TASKS = [
  {
    key: 'JD_EXTRACTION',
    promptKey: 'jd_extraction',
    label: 'Job Spec Web Extraction',
    icon: 'Briefcase',
    recommendedTemp: 0.0,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Local & Cloud: None (Fast) — Schema fact extraction runs 10x faster without reasoning tokens.',
    hasPrompt: true,
    desc: 'Extracts structured job title, company, salary, and requirements from scraped web HTML / markdown.',
    variables: ['{raw_webpage_data}'],
  },
  {
    key: 'EXTRACTION',
    promptKey: 'email_extraction',
    label: 'Email Metadata Extraction',
    icon: 'Mail',
    recommendedTemp: 0.0,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Local & Cloud: None (Fast) — Deterministic parsing of email dates, companies, and interview stages.',
    hasPrompt: true,
    desc: 'Parses job details, dates, companies, and roles from emails into structured Pydantic schemas.',
    variables: ['{email_content}'],
  },
  {
    key: 'ASSESSMENT',
    promptKey: 'assessment',
    label: 'Pre-Screen Match Audit & Tips',
    icon: 'Sparkles',
    recommendedTemp: 0.1,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Local: None (~35s intake) | Cloud: None or Low/Medium on Claude 3.7 / o3-mini for nuanced strategic gap analysis.',
    hasPrompt: true,
    desc: 'Computes deep semantic fit score, keyword matches/gaps, and strategic resume improvement suggestions.',
    variables: ['{job_description}', '{candidate_cv}', '{programmatic_baseline}'],
  },
  {
    key: 'cv_anonymization',
    promptKey: 'cv_anonymization',
    label: 'CV De-Identification & Skills',
    icon: 'ShieldCheck',
    recommendedTemp: 0.0,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Local & Cloud: None (Fast) — Strips PII and parses canonical skill taxonomy directly.',
    hasPrompt: true,
    desc: 'Replaces companies with scale tags, transforms date windows into durations, and extracts canonical technical skills.',
    variables: ['{resume_text}'],
  },
  {
    key: 'AGENT_REASONING',
    promptKey: 'agent_system',
    label: 'LangGraph Reasoning & Assistant',
    icon: 'Bot',
    recommendedTemp: 0.3,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Local & Cloud: None (<3s message turn latency) | Cloud: Low if executing complex multi-agent planning.',
    hasPrompt: true,
    desc: 'Evaluates fuzzy deduplication confidence and powers the interactive chat assistant & interview simulation.',
    variables: [],
  },
  {
    key: 'INTERVIEW_GUIDE',
    promptKey: 'interview_guide',
    label: 'Interview Prep Guide',
    icon: 'BookOpen',
    recommendedTemp: 0.3,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Local: None (~25s) | Cloud: Medium/High on Claude 3.7 / o3-mini for deeper strategic STAR scenario planning.',
    hasPrompt: true,
    desc: 'Generates tailored interview preparation guides, STAR stories, and strategic question defenses.',
    variables: ['{language}', '{company_name}', '{position}', '{company_context}', '{jd_text}', '{cv_text}', '{target_section}'],
  },
  {
    key: 'COVER_LETTER',
    promptKey: 'cover_letter',
    label: 'Cover Letter Generation',
    icon: 'FileText',
    recommendedTemp: 0.3,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Local & Cloud: None — Standard direct generation produces more natural, persuasive writing without analytical stiffness.',
    hasPrompt: true,
    desc: 'Generates tailored cover letters referencing candidate experiences against target role and company requirements.',
    variables: ['{company_name}', '{position}', '{job_description}', '{candidate_cv}', '{tone}', '{length}'],
  },
  {
    key: 'EMBEDDING',
    promptKey: null,
    label: 'Vector Embeddings (pgvector)',
    hidden: computed(() => !uiStore.enableEmbeddings),
    icon: 'Cpu',
    recommendedTemp: null,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    reasoningTip: '💡 Embedding Model: Fixed vector embeddings (nomic-embed-text, text-embedding-3-small).',
    hasPrompt: false,
    desc: 'Generates 768-dimension dense vector representations for pgvector cosine similarity search.',
    variables: [],
  },
]

const activeTaskDef = computed(() => {
  return TASKS.find((t) => t.key === selectedTaskKey.value) || TASKS[0]
})

const filteredStudioModels = computed(() => {
  const isEmbeddingTask = selectedTaskKey.value === 'EMBEDDING'
  const allModels = studioProviderModels.value
  if (!allModels || allModels.length === 0) return []

  if (isEmbeddingTask) {
    const embeddingModels = allModels.filter(
      (m) => m.is_embedding || /embed|bge|nomic|minilm|gte|e5|bert|mxbai/i.test(m.id || m.name)
    )
    if (embeddingModels.length > 0) return embeddingModels
    return [
      { id: 'text-embedding-3-small', name: 'text-embedding-3-small', is_discovered: false, is_embedding: true },
      { id: 'text-embedding-004', name: 'text-embedding-004', is_discovered: false, is_embedding: true },
      { id: 'nomic-embed-text', name: 'nomic-embed-text', is_discovered: false, is_embedding: true },
      { id: 'bge-m3', name: 'bge-m3', is_discovered: false, is_embedding: true },
    ]
  } else {
    return allModels.filter(
      (m) => !m.is_embedding && !/embed|bge|nomic|minilm|gte|e5|bert|mxbai/i.test(m.id || m.name)
    )
  }
})

const studioForm = ref({
  use_global_default: false,
  provider_id: null,
  model_name: '',
  temperature: 0.2,
  reasoning_effort: 'none',
  custom_extra_body_json: '',
  max_tokens: null,
  embedding_dimensions: 768,
  prompt_template: '',
})
const isSyncingStudio = ref(false)
let studioAutoSaveTimer = null

const probeLoading = ref(false)
const probeResult = ref(null)
const probeError = ref(null)

const customExtraBodyError = computed(() => {
  if (!studioForm.value.custom_extra_body_json?.trim()) return null
  try {
    const parsed = JSON.parse(studioForm.value.custom_extra_body_json.trim())
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return 'Must be a valid JSON object e.g. {"chat_template_kwargs": {"thinking": false}}'
    }
    return null
  } catch (e) {
    return `Invalid JSON: ${e.message}`
  }
})

async function runModelProbe() {
  if (!studioForm.value.provider_id || !studioForm.value.model_name.trim()) {
    uiStore.showToast('Please select a provider and specify a model name first.', 'warning')
    return
  }

  probeLoading.value = true
  probeResult.value = null
  probeError.value = null
  try {
    const res = await AIConfigAPI.probeModel(
      studioForm.value.provider_id,
      studioForm.value.model_name.trim()
    )
    probeResult.value = res.data
    uiStore.showToast(`Probe completed for '${studioForm.value.model_name}'!`, 'success')
  } catch (err) {
    probeError.value = err.message || 'Model probe failed'
    uiStore.showToast(`Model probe error: ${err.message}`, 'error')
  } finally {
    probeLoading.value = false
  }
}

function applyProbeRecommendations() {
  if (!probeResult.value) return
  if (probeResult.value.recommended_reasoning_effort) {
    studioForm.value.reasoning_effort = probeResult.value.recommended_reasoning_effort
  }
  if (probeResult.value.recommended_extra_body) {
    studioForm.value.reasoning_effort = 'custom'
    studioForm.value.custom_extra_body_json = JSON.stringify(
      probeResult.value.recommended_extra_body,
      null,
      2
    )
  }
  scheduleStudioAutoSave(50)
  uiStore.showToast('Applied recommended reasoning configuration!', 'success')
}

function scheduleStudioAutoSave(delay = 500) {
  if (isSyncingStudio.value || loadingStudio.value) return
  if (studioAutoSaveTimer) clearTimeout(studioAutoSaveTimer)
  studioAutoSaveTimer = setTimeout(() => {
    saveStudioTask(true)
  }, delay)
}

function syncStudioForm() {
  isSyncingStudio.value = true
  if (studioAutoSaveTimer) clearTimeout(studioAutoSaveTimer)
  probeResult.value = null
  probeError.value = null

  const taskKey = selectedTaskKey.value
  const taskDef = activeTaskDef.value

  const existingBinding = bindings.value.find(
    (b) => b.task_type.toUpperCase() === taskKey.toUpperCase()
  )

  if (taskKey !== 'GLOBAL_DEFAULT' && taskKey !== 'EMBEDDING' && !existingBinding) {
    studioForm.value.use_global_default = true
  } else if (existingBinding?.extra_kwargs?.use_global_default !== undefined) {
    studioForm.value.use_global_default = existingBinding.extra_kwargs.use_global_default
  } else {
    studioForm.value.use_global_default = false
  }

  const defaultTemp = typeof taskDef.recommendedTemp === 'number' ? taskDef.recommendedTemp : 0.2
  const chosenProviderId = existingBinding?.provider_id || (providers.value[0]?.id || null)

  studioForm.value.provider_id = chosenProviderId
  studioForm.value.model_name = existingBinding?.model_name || (taskKey === 'EMBEDDING' ? 'nomic-embed-text' : 'qwen3.5-4b')
  studioForm.value.temperature = existingBinding?.temperature !== undefined ? existingBinding.temperature : defaultTemp
  studioForm.value.reasoning_effort = existingBinding?.reasoning_effort || existingBinding?.extra_kwargs?.reasoning_effort || taskDef.recommendedReasoning || 'none'
  const customExtra = existingBinding?.custom_extra_body || existingBinding?.extra_kwargs?.custom_extra_body || null
  studioForm.value.custom_extra_body_json = customExtra ? JSON.stringify(customExtra, null, 2) : ''
  studioForm.value.max_tokens = existingBinding?.max_tokens || null
  studioForm.value.embedding_dimensions = existingBinding?.embedding_dimensions || (taskKey === 'EMBEDDING' ? 768 : null)

  if (taskDef.promptKey) {
    const promptRecord = promptsList.value.find((p) => p.name.toLowerCase() === taskDef.promptKey.toLowerCase())
    studioForm.value.prompt_template = promptRecord?.template || ''
  } else {
    studioForm.value.prompt_template = ''
  }

  fetchStudioModels(chosenProviderId)

  setTimeout(() => {
    isSyncingStudio.value = false
  }, 150)
}

function selectStudioTask(taskKey) {
  selectedTaskKey.value = taskKey
  syncStudioForm()
}

async function fetchStudioModels(providerId, forceRefresh = false) {
  if (!providerId) {
    studioProviderModels.value = []
    return
  }
  if (!forceRefresh && providerModelsCache.value[providerId]) {
    studioProviderModels.value = providerModelsCache.value[providerId]
    return
  }

  loadingStudioModels.value = true
  try {
    const res = await AIConfigAPI.getProviderModels(providerId)
    const models = res.data?.models || []
    providerModelsCache.value[providerId] = models
    studioProviderModels.value = models
  } catch (err) {
    studioProviderModels.value = []
  } finally {
    loadingStudioModels.value = false
  }
}

function onStudioProviderChange() {
  fetchStudioModels(studioForm.value.provider_id)
  scheduleStudioAutoSave(100)
}

function selectStudioSuggestedModel(modelId) {
  studioForm.value.model_name = modelId
  scheduleStudioAutoSave(50)
}

function setStudioReasoningEffort(effort) {
  studioForm.value.reasoning_effort = effort
  scheduleStudioAutoSave(50)
}

async function saveStudioTask(isAutoSave = false) {
  isSavingStudio.value = true
  const taskKey = selectedTaskKey.value
  const taskDef = activeTaskDef.value

  try {
    let customExtraParsed = undefined
    if (studioForm.value.custom_extra_body_json?.trim()) {
      try {
        customExtraParsed = JSON.parse(studioForm.value.custom_extra_body_json.trim())
      } catch (jsonErr) {
        if (!isAutoSave) {
          uiStore.showToast(`Invalid Custom Extra Body JSON: ${jsonErr.message}`, 'error')
        }
        isSavingStudio.value = false
        return
      }
    }

    const useGlobal = studioForm.value.use_global_default && taskKey !== 'EMBEDDING'
    await AIConfigAPI.setBinding(taskKey, {
      provider_id: useGlobal
        ? (globalBinding.value?.provider_id || studioForm.value.provider_id)
        : studioForm.value.provider_id,
      model_name: useGlobal
        ? (globalBinding.value?.model_name || studioForm.value.model_name.trim())
        : studioForm.value.model_name.trim(),
      temperature: studioForm.value.temperature,
      reasoning_effort: studioForm.value.reasoning_effort,
      custom_extra_body: customExtraParsed,
      max_tokens: studioForm.value.max_tokens ? Number(studioForm.value.max_tokens) : undefined,
      embedding_dimensions: taskKey === 'EMBEDDING' ? studioForm.value.embedding_dimensions : undefined,
      extra_kwargs: {
        use_global_default: useGlobal,
        reasoning_effort: studioForm.value.reasoning_effort,
        custom_extra_body: customExtraParsed,
      },
    })

    if (taskDef.hasPrompt && taskDef.promptKey && studioForm.value.prompt_template !== undefined) {
      await PromptsAPI.update(taskDef.promptKey, studioForm.value.prompt_template)
    }

    if (!isAutoSave) {
      uiStore.showToast(`Task '${taskDef.label}' configuration saved!`, 'success')
    }
    await loadBindings()
    await loadPrompts()
  } catch (err) {
    if (!isAutoSave) {
      uiStore.showToast(err.message || 'Failed to save task configuration', 'error')
    }
  } finally {
    isSavingStudio.value = false
  }
}

async function resetStudioTaskToDefaults() {
  const taskDef = activeTaskDef.value
  const taskKey = selectedTaskKey.value

  if (!confirm(`Reset '${taskDef.label}' parameters and prompt back to recommended factory defaults?`)) {
    return
  }

  isResettingPrompt.value = true
  try {
    if (taskKey === 'EMBEDDING') {
      studioForm.value.embedding_dimensions = 768
      studioForm.value.model_name = 'nomic-embed-text'
    } else {
      studioForm.value.use_global_default = true
      studioForm.value.temperature = typeof taskDef.recommendedTemp === 'number' ? taskDef.recommendedTemp : 0.2
      studioForm.value.reasoning_effort = taskDef.recommendedReasoning || 'none'
      studioForm.value.max_tokens = null
    }

    if (taskDef.hasPrompt && taskDef.promptKey) {
      const res = await PromptsAPI.reset(taskDef.promptKey)
      studioForm.value.prompt_template = res.data.template
      await loadPrompts()
    }

    await saveStudioTask(false)
    uiStore.showToast(`Task '${taskDef.label}' reset to recommended defaults!`, 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to reset task defaults', 'error')
  } finally {
    isResettingPrompt.value = false
  }
}

async function resetStudioPrompt() {
  const taskDef = activeTaskDef.value
  if (!taskDef.promptKey) return

  if (!confirm(`Reset '${taskDef.label}' prompt back to factory defaults?`)) return
  isResettingPrompt.value = true
  try {
    const res = await PromptsAPI.reset(taskDef.promptKey)
    studioForm.value.prompt_template = res.data.template
    await PromptsAPI.update(taskDef.promptKey, res.data.template)
    uiStore.showToast(`Prompt '${taskDef.label}' reset to factory defaults!`, 'success')
    await loadPrompts()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isResettingPrompt.value = false
  }
}

watch(
  () => [
    studioForm.value.model_name,
    studioForm.value.temperature,
    studioForm.value.max_tokens,
    studioForm.value.embedding_dimensions,
    studioForm.value.prompt_template,
  ],
  () => {
    if (!isSyncingStudio.value && !loadingStudio.value) {
      scheduleStudioAutoSave(600)
    }
  }
)

watch(
  () => [globalForm.value.model_name],
  () => {
    if (!isSyncingGlobal.value && !loadingGlobalModels.value) {
      scheduleGlobalAutoSave(600)
    }
  }
)

async function loadProviders() {
  loadingProviders.value = true
  try {
    const res = await AIConfigAPI.listProviders()
    providers.value = res.data || []
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    loadingProviders.value = false
  }
}

async function loadBindings() {
  try {
    const res = await AIConfigAPI.listBindings()
    bindings.value = res.data || []
    syncGlobalForm()
  } catch (err) {
    // ignore
  }
}

async function loadPrompts() {
  try {
    const res = await PromptsAPI.list()
    promptsList.value = res.data || []
  } catch (err) {
    // ignore
  }
}

function openCreateProvider() {
  editingProvider.value = null
  providerForm.value = {
    name: '',
    provider_type: 'openai',
    base_url: 'http://127.0.0.1:11434',
    api_key: '',
    max_concurrency: 1,
    is_active: true,
  }
  isProviderModalOpen.value = true
}

function openEditProvider(p) {
  editingProvider.value = p
  providerForm.value = {
    name: p.name,
    provider_type: p.provider_type,
    base_url: p.base_url || '',
    api_key: '',
    max_concurrency: p.max_concurrency || 1,
    is_active: p.is_active,
  }
  isProviderModalOpen.value = true
}

async function saveProvider() {
  try {
    if (editingProvider.value) {
      await AIConfigAPI.updateProvider(editingProvider.value.id, providerForm.value)
      uiStore.showToast('Provider updated successfully', 'success')
    } else {
      await AIConfigAPI.createProvider(providerForm.value)
      uiStore.showToast('Provider registered successfully', 'success')
    }
    isProviderModalOpen.value = false
    await loadProviders()
    syncStudioForm()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function deleteProvider(id) {
  if (!confirm('Are you sure you want to delete this provider?')) return
  try {
    await AIConfigAPI.deleteProvider(id)
    uiStore.showToast('Provider deleted', 'info')
    await loadProviders()
    syncStudioForm()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function testProviderDirect(provider) {
  testingProviderId.value = provider.id
  providerTestResults.value[provider.id] = null
  try {
    const res = await AIConfigAPI.testProvider(provider.id)
    const isWarning = res.data?.status === 'warning'
    providerTestResults.value[provider.id] = {
      status: isWarning ? 'warning' : 'success',
      message: isWarning ? res.data.response : 'Success (Connected)',
    }
    uiStore.showToast(isWarning ? res.data.response : `Provider '${provider.name}' connection verified!`, isWarning ? 'warning' : 'success')
  } catch (err) {
    const errMsg = err.response?.data?.detail || err.message || 'Connection failed'
    providerTestResults.value[provider.id] = {
      status: 'error',
      message: errMsg,
    }
    uiStore.showToast(errMsg, 'error')
  } finally {
    testingProviderId.value = null
  }
}

const emailAccounts = ref([])
const loadingAccounts = ref(false)
const isEmailAccountModalOpen = ref(false)
const editingAccount = ref(null)
const syncingAccount = ref(null)

async function loadEmailAccounts() {
  loadingAccounts.value = true
  try {
    const res = await EmailAccountsAPI.list()
    emailAccounts.value = res.data || []
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    loadingAccounts.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    loadProviders(),
    loadBindings(),
    loadPrompts(),
    loadEmailAccounts(),
    loadGlobalSettings(),
  ])
  syncGlobalForm()
  syncStudioForm()
})
</script>

<template>
  <div class="page-container">
    <PageHeader
      title="Settings & Preferences"
      subtitle="Configure local vs. backend storage modes, BYOK AI provider keys, system preferences, and JSON backups."
      align="center"
    >
      <template #tabs>
        <div class="tab-bar">
          <button
            class="tab-pill"
            :class="{ active: activeTab === 'studio' }"
            @click="activeTab = 'studio'"
          >
            <Sparkles :size="15" />
            <span>Unified Task Studio</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'providers' }"
            @click="activeTab = 'providers'"
          >
            <Server :size="15" />
            <span>AI Providers ({{ providers.length }})</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'email_accounts' }"
            @click="activeTab = 'email_accounts'"
          >
            <Mail :size="15" />
            <span>Email Accounts</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'profile' }"
            @click="activeTab = 'profile'"
          >
            <UserCheck :size="15" />
            <span>My Profile / CV</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'preferences' }"
            @click="activeTab = 'preferences'"
          >
            <SlidersHorizontal :size="15" />
            <span>Preferences &amp; Backup</span>
          </button>
        </div>
      </template>
    </PageHeader>

    <div class="settings-content-area">
      <div class="settings-inner-container">
        <!-- TAB 1: UNIFIED TASK STUDIO -->
        <div v-if="activeTab === 'studio'" class="tab-content animate-fade-in">
          <div class="global-hero-card">
            <div class="global-hero-header">
              <div class="hero-title-group">
                <Globe class="text-primary" :size="22" />
                <div>
                  <h2 class="hero-title">Global Default Model</h2>
                  <p class="hero-desc">The primary AI provider and model used across all standard pipeline tasks.</p>
                </div>
              </div>
              <div class="hero-actions-group flex items-center gap-2">
                <button
                  class="btn btn-ghost btn-sm text-secondary"
                  :disabled="isResettingGlobal"
                  @click="resetGlobalDefaultToDefaults"
                >
                  <RotateCcw :size="14" />
                  <span>Reset to Defaults</span>
                </button>
              </div>
            </div>

            <div class="global-hero-form">
              <div class="form-grid-2">
                <div class="input-group">
                  <label class="input-label">AI Provider *</label>
                  <select
                    v-model="globalForm.provider_id"
                    class="form-input"
                    @change="onGlobalProviderChange"
                  >
                    <option v-for="p in providers" :key="p.id" :value="p.id">
                      {{ p.name }} ({{ p.provider_type }})
                    </option>
                  </select>
                </div>

                <div class="input-group">
                  <label class="input-label">Model Identifier *</label>
                  <input
                    v-model="globalForm.model_name"
                    type="text"
                    placeholder="e.g. gpt-4o, claude-3-7-sonnet, llama3"
                    class="form-input font-mono"
                    required
                    @input="scheduleGlobalAutoSave(600)"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 2: AI PROVIDERS (BYOK) -->
        <div v-else-if="activeTab === 'providers'" class="tab-content animate-fade-in">
          <div class="section-card mb-4">
            <div class="section-header-row">
              <div class="section-header-text">
                <h3>Bring-Your-Own-Key (BYOK) &amp; Local Runners</h3>
                <p>Configure client-side browser direct API keys (OpenAI, Anthropic, Gemini) or local runner URLs (Ollama, LM Studio).</p>
              </div>
              <button class="btn btn-primary btn-sm" @click="openCreateProvider">
                <Plus :size="15" />
                <span>Add Provider</span>
              </button>
            </div>

            <div class="providers-grid">
              <div v-for="p in providers" :key="p.id" class="provider-card">
                <div class="provider-header">
                  <div class="provider-title-group">
                    <Server :size="16" class="text-primary" />
                    <span class="provider-name">{{ p.name }}</span>
                  </div>
                  <span class="badge badge-applied font-mono">{{ p.provider_type }}</span>
                </div>

                <div class="provider-body">
                  <div class="meta-row">
                    <span class="meta-k">Endpoint:</span>
                    <span class="meta-v font-mono">{{ p.base_url || 'Cloud Direct API' }}</span>
                  </div>
                  <div class="meta-row">
                    <span class="meta-k">API Key:</span>
                    <span class="meta-v font-mono">{{ p.api_key ? '••••••••' + p.api_key.slice(-4) : 'Local / Public' }}</span>
                  </div>
                </div>

                <div class="provider-actions">
                  <button class="btn btn-secondary btn-sm" @click="openEditProvider(p)">
                    <Edit3 :size="14" />
                    <span>Edit</span>
                  </button>
                  <button class="btn btn-danger btn-sm" @click="deleteProvider(p.id)">
                    <Trash2 :size="14" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 3: EMAIL ACCOUNTS -->
        <div v-else-if="activeTab === 'email_accounts'" class="tab-content animate-fade-in">
          <div class="section-card">
            <div class="section-header-row">
              <div class="section-header-text">
                <h3>Connected Mailboxes</h3>
                <p v-if="isLocalOrDemoMode()" class="text-warning">
                  ⚠️ Email sync is disabled in client-first local mode. Timeline history can be managed via manual JSON imports.
                </p>
                <p v-else>Connect recruitment mailboxes for automated inbox sweeps.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 4: PROFILE -->
        <div v-else-if="activeTab === 'profile'" class="tab-content animate-fade-in">
          <CandidateProfileView :is-embedded="true" />
        </div>

        <!-- TAB 5: PREFERENCES & BACKUP -->
        <div v-else-if="activeTab === 'preferences'" class="tab-content animate-fade-in">
          <div class="section-card mb-4">
            <div class="card-intro mb-4">
              <h3>Storage Architecture &amp; Data Portability</h3>
              <p>Switch runtime execution mode between local IndexedDB and live FastAPI server backend.</p>
            </div>

            <div class="preferences-grid">
              <!-- Storage Mode Switcher -->
              <div class="preference-card">
                <div class="preference-header">
                  <div class="preference-icon text-primary">
                    <Database :size="18" />
                  </div>
                  <div class="preference-header-text">
                    <h4 class="preference-title">Runtime Storage Mode</h4>
                    <p class="preference-desc">Select where application data and AI evaluations execute.</p>
                  </div>
                </div>
                <div class="preference-body">
                  <div class="input-group">
                    <label class="input-label">Storage Engine</label>
                    <select
                      :value="currentStorageMode"
                      class="form-input font-mono"
                      @change="e => changeStorageMode(e.target.value)"
                    >
                      <option value="demo">Demo Mode (Client-First Mock Dataset)</option>
                      <option value="local">Local Mode (Offline IndexedDB + BYOK AI)</option>
                      <option value="backend">Backend Mode (FastAPI REST Server)</option>
                    </select>
                    <span class="preference-field-hint">
                      Current Active: <strong class="text-primary">{{ currentStorageMode.toUpperCase() }}</strong>
                    </span>
                  </div>
                </div>
              </div>

              <!-- Backup / Export Import Card -->
              <div class="preference-card">
                <div class="preference-header">
                  <div class="preference-icon text-primary">
                    <Download :size="18" />
                  </div>
                  <div class="preference-header-text">
                    <h4 class="preference-title">JSON Data Backup &amp; Portability</h4>
                    <p class="preference-desc">Export your entire local IndexedDB database to a JSON file or restore from a backup.</p>
                  </div>
                </div>
                <div class="preference-body">
                  <div class="flex items-center gap-2">
                    <button class="btn btn-primary btn-sm flex-1" :disabled="isExportingJSON" @click="handleExportJSON">
                      <Download :size="14" />
                      <span>Export JSON Backup</span>
                    </button>
                    <button class="btn btn-secondary btn-sm flex-1" :disabled="isImportingJSON" @click="triggerImportJSON">
                      <Upload :size="14" />
                      <span>Import JSON</span>
                    </button>
                    <input ref="jsonFileInput" type="file" accept=".json" class="hidden" @change="handleImportFile" />
                  </div>
                </div>
              </div>

              <!-- Reset Demo Data Card -->
              <div class="preference-card">
                <div class="preference-header">
                  <div class="preference-icon text-danger">
                    <RotateCcw :size="18" />
                  </div>
                  <div class="preference-header-text">
                    <h4 class="preference-title">Reset Demo Dataset</h4>
                    <p class="preference-desc">Completely clear local tables and re-seed initial Staff Engineer dataset.</p>
                  </div>
                </div>
                <div class="preference-body">
                  <button class="btn btn-danger btn-sm w-full" :disabled="isResettingDemo" @click="handleResetDemoData">
                    <RotateCcw :size="14" />
                    <span>Reset Demo Data</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- PROVIDER MODAL -->
    <div v-if="isProviderModalOpen" class="modal-backdrop" @click.self="isProviderModalOpen = false">
      <div class="modal-card animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingProvider ? 'Edit Provider' : 'Add AI Provider' }}</h3>
          <button class="btn-close" @click="isProviderModalOpen = false">×</button>
        </div>

        <div class="modal-body">
          <div class="input-group">
            <label class="input-label">Provider Name *</label>
            <input v-model="providerForm.name" type="text" placeholder="e.g. Local Ollama, OpenAI BYOK" class="form-input" required />
          </div>

          <div class="input-group">
            <label class="input-label">Provider Type *</label>
            <select v-model="providerForm.provider_type" class="form-input">
              <option value="openai">OpenAI (sk-...)</option>
              <option value="anthropic">Anthropic (sk-ant-...)</option>
              <option value="ollama">Ollama (Local Runner)</option>
              <option value="lm_studio">LM Studio (Local Runner)</option>
              <option value="openrouter">OpenRouter</option>
            </select>
          </div>

          <div class="input-group">
            <label class="input-label">Base URL</label>
            <input v-model="providerForm.base_url" type="text" placeholder="http://127.0.0.1:11434" class="form-input" />
          </div>

          <div class="input-group">
            <label class="input-label">API Key (Optional for local)</label>
            <input v-model="providerForm.api_key" type="password" placeholder="sk-..." class="form-input" />
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="isProviderModalOpen = false">Cancel</button>
            <button class="btn btn-primary" @click="saveProvider">Save Provider</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
}
.tab-bar {
  display: flex;
  gap: 4px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 4px;
  border-radius: var(--radius-sm);
}
.tab-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}
.tab-pill.active {
  background-color: var(--bg-elevated);
  color: var(--primary);
  font-weight: 600;
}
.section-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
}
.providers-grid, .preferences-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.provider-card, .preference-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form-input {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-main);
}
.hidden {
  display: none;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  width: 100%;
  max-width: 480px;
  padding: 20px;
}
</style>
