<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { AIConfigAPI, EmailAccountsAPI, IntakeAPI, PromptsAPI, DiagnosticsAPI, SystemSettingsAPI } from '../api/endpoints'
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
  ArrowDown,
  ArrowUp,
  BarChart3,
} from 'lucide-vue-next'

const route = useRoute()
const uiStore = useUIStore()

const activeTab = ref(route.query.tab || 'studio') // 'studio' | 'providers' | 'email_accounts' | 'profile' | 'preferences'

watch(() => route.query.tab, (newTab) => {
  if (newTab) activeTab.value = newTab
})

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
  base_url: 'http://192.168.1.187:1234/v1',
  api_key: '',
  max_concurrency: 1,
  is_active: true,
  input_cost_per_million: 0.15,
  output_cost_per_million: 0.60,
})

// Token Usage & What-If Provider Cost Comparison
const usageOverview = ref({
  monthly_tokens: 0,
  monthly_spend_usd: 0,
  monthly_savings_usd: 0,
  all_time_tokens: 0,
  all_time_spend_usd: 0,
  all_time_savings_usd: 0,
  local_inference_percentage: 100,
  total_llm_calls: 0,
  avg_cost_per_assessment: 0,
  task_breakdown: {},
  comparative_costs: [],
})
const loadingUsage = ref(false)
const isComparisonOpen = ref(false)

// Benchmark Rates Modal State
const isPricingModalOpen = ref(false)
const pricingRates = ref([])
const loadingPricing = ref(false)
const isSavingPricing = ref(false)
const pricingSearchQuery = ref('')

const filteredPricingRates = computed(() => {
  if (!pricingSearchQuery.value.trim()) return pricingRates.value
  const q = pricingSearchQuery.value.toLowerCase()
  return pricingRates.value.filter(
    (r) =>
      r.key.toLowerCase().includes(q) ||
      (r.display_name && r.display_name.toLowerCase().includes(q)) ||
      (r.provider && r.provider.toLowerCase().includes(q))
  )
})

async function loadPricingRates() {
  loadingPricing.value = true
  try {
    const res = await AIConfigAPI.getPricingRates()
    pricingRates.value = res.data || []
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to load benchmark rates', 'error')
  } finally {
    loadingPricing.value = false
  }
}

async function openPricingModal() {
  isPricingModalOpen.value = true
  await loadPricingRates()
}

async function savePricingRates() {
  isSavingPricing.value = true
  try {
    const payload = pricingRates.value.map((r) => ({
      key: r.key,
      input_cost_per_million: Number(r.input_cost_per_million) || 0.0,
      output_cost_per_million: Number(r.output_cost_per_million) || 0.0,
    }))
    await AIConfigAPI.updatePricingRates(payload)
    uiStore.showToast('Benchmark rates saved successfully', 'success')
    isPricingModalOpen.value = false
    await loadUsageOverview()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save benchmark rates', 'error')
  } finally {
    isSavingPricing.value = false
  }
}

async function resetPricingRatesToDefaults() {
  loadingPricing.value = true
  try {
    const res = await AIConfigAPI.resetPricingRates()
    pricingRates.value = res.data || []
    uiStore.showToast('Benchmark rates reset to published defaults', 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to reset benchmark rates', 'error')
  } finally {
    loadingPricing.value = false
  }
}

// Rate Guide in Provider Modal
const isRateGuideOpen = ref(false)
const showAllRateGuideProviders = ref(false)

const STANDARD_MODEL_RATES = [
  { provider: 'openai', model: 'gpt-4o-mini', name: 'OpenAI GPT-4o Mini', inCost: 0.15, outCost: 0.60, note: 'Recommended default for intake & assessments' },
  { provider: 'openai', model: 'gpt-4o', name: 'OpenAI GPT-4o', inCost: 2.50, outCost: 10.00, note: 'Flagship multimodal reasoning' },
  { provider: 'openai', model: 'o3-mini', name: 'OpenAI o3-mini', inCost: 1.10, outCost: 4.40, note: 'Fast reasoning & STEM' },
  { provider: 'anthropic', model: 'claude-3-5-sonnet', name: 'Claude 3.5 Sonnet', inCost: 3.00, outCost: 15.00, note: 'State-of-the-art coding & nuances' },
  { provider: 'anthropic', model: 'claude-3-5-haiku', name: 'Claude 3.5 Haiku', inCost: 0.80, outCost: 4.00, note: 'Lightweight & ultra-fast' },
  { provider: 'google_genai', model: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', inCost: 0.10, outCost: 0.40, note: 'High speed workhorse' },
  { provider: 'google_genai', model: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', inCost: 1.25, outCost: 5.00, note: 'Long context multimodal' },
  { provider: 'deepseek', model: 'deepseek-chat', name: 'DeepSeek V3', inCost: 0.14, outCost: 0.28, note: 'Ultra-low cost general intelligence' },
  { provider: 'ollama', model: 'local-models', name: 'Local Ollama / LM Studio', inCost: 0.00, outCost: 0.00, note: '100% Free on-device inference' },
]

const filteredRateGuidePresets = computed(() => {
  if (showAllRateGuideProviders.value) return STANDARD_MODEL_RATES
  const currentType = (providerForm.value.provider_type || '').toLowerCase()
  if (currentType === 'openai') {
    return STANDARD_MODEL_RATES.filter(p => p.provider === 'openai')
  }
  if (currentType === 'anthropic') {
    return STANDARD_MODEL_RATES.filter(p => p.provider === 'anthropic')
  }
  if (currentType === 'google_genai' || currentType === 'gemini') {
    return STANDARD_MODEL_RATES.filter(p => p.provider === 'google_genai')
  }
  if (currentType === 'deepseek') {
    return STANDARD_MODEL_RATES.filter(p => p.provider === 'deepseek')
  }
  if (currentType === 'ollama') {
    return STANDARD_MODEL_RATES.filter(p => p.provider === 'ollama')
  }
  return STANDARD_MODEL_RATES
})

function applyRateGuidePreset(preset) {
  providerForm.value.input_cost_per_million = preset.inCost
  providerForm.value.output_cost_per_million = preset.outCost
  uiStore.showToast(`Applied rates from ${preset.name}`, 'info')
}

function onProviderTypeChange() {
  const type = providerForm.value.provider_type
  if (type === 'openai') {
    providerForm.value.input_cost_per_million = 0.15
    providerForm.value.output_cost_per_million = 0.60
    if (!providerForm.value.base_url || providerForm.value.base_url.includes('11434')) {
      providerForm.value.base_url = 'http://192.168.1.187:1234/v1'
    }
  } else if (type === 'anthropic') {
    providerForm.value.input_cost_per_million = 3.00
    providerForm.value.output_cost_per_million = 15.00
  } else if (type === 'google_genai' || type === 'gemini') {
    providerForm.value.input_cost_per_million = 0.10
    providerForm.value.output_cost_per_million = 0.40
  } else if (type === 'deepseek') {
    providerForm.value.input_cost_per_million = 0.14
    providerForm.value.output_cost_per_million = 0.28
  } else if (type === 'ollama') {
    providerForm.value.input_cost_per_million = 0.00
    providerForm.value.output_cost_per_million = 0.00
    providerForm.value.base_url = 'http://localhost:11434'
  } else if (type === 'openrouter') {
    providerForm.value.input_cost_per_million = 0.15
    providerForm.value.output_cost_per_million = 0.60
    providerForm.value.base_url = 'https://openrouter.ai/api/v1'
  } else {
    providerForm.value.input_cost_per_million = 0.00
    providerForm.value.output_cost_per_million = 0.00
  }
}

async function loadUsageOverview() {
  loadingUsage.value = true
  try {
    const res = await AIConfigAPI.getUsageOverview()
    if (res.data) {
      usageOverview.value = res.data
    }
  } catch (err) {
    console.error('Failed to load usage overview:', err)
  } finally {
    loadingUsage.value = false
  }
}

function formatTokens(val) {
  if (!val) return '0'
  if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M'
  if (val >= 1_000) return (val / 1_000).toFixed(1) + 'k'
  return String(val)
}

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
      // Preserve existing parameters without resetting temperature etc.
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

    // 1. Reset Global Default Model
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

    // 2. Reset every individual pipeline task to factory recommendations
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
          // ignore if prompt doesn't exist
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
    // Custom model override (not inheriting global default)
    if (b.extra_kwargs?.use_global_default === false) {
      return true
    }
    // Custom temperature override
    if (
      typeof taskDef.recommendedTemp === 'number' &&
      b.temperature !== undefined &&
      b.temperature !== null &&
      Math.abs(Number(b.temperature) - taskDef.recommendedTemp) > 0.001
    ) {
      return true
    }
    // Custom reasoning override
    const recReasoning = taskDef.recommendedReasoning || 'none'
    const actualReasoning = b.reasoning_effort || b.extra_kwargs?.reasoning_effort || 'none'
    if (actualReasoning !== recReasoning) {
      return true
    }
    // Custom max tokens
    if (b.max_tokens !== undefined && b.max_tokens !== null && b.max_tokens !== '') {
      return true
    }
  }

  return false
}

// Vector Embeddings Settings State
const enableEmbeddings = ref(true)
const isUpdatingEmbeddings = ref(false)
const isReindexingEmbeddings = ref(false)

// Cover Letter Automation Settings State
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

// Current active task definition
const activeTaskDef = computed(() => {
  return TASKS.find((t) => t.key === selectedTaskKey.value) || TASKS[0]
})

// Filtered models for current task (embedding models for EMBEDDING task, chat models for others)
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

// Unified form for currently selected task
const studioForm = ref({
  use_global_default: false,
  provider_id: null,
  model_name: '',
  temperature: 0.2,
  reasoning_effort: 'none', // 'none' | 'low' | 'medium' | 'high' | 'custom'
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

// Sync studio form with selected task
function syncStudioForm() {
  isSyncingStudio.value = true
  if (studioAutoSaveTimer) clearTimeout(studioAutoSaveTimer)
  probeResult.value = null
  probeError.value = null

  const taskKey = selectedTaskKey.value
  const taskDef = activeTaskDef.value

  // 1. Find existing binding
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

  // 2. Find prompt template if task supports prompts
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

    // 1. Save Model Binding
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

    // 2. Save Prompt Template if applicable
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

// --------------------------------------------------------------------------
// AI Providers State & CRUD
// --------------------------------------------------------------------------
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
  isRateGuideOpen.value = false
  providerForm.value = {
    name: '',
    provider_type: 'openai',
    base_url: 'http://192.168.1.187:1234/v1',
    api_key: '',
    max_concurrency: 1,
    is_active: true,
    input_cost_per_million: 0.15,
    output_cost_per_million: 0.60,
  }
  isProviderModalOpen.value = true
}

function openEditProvider(p) {
  editingProvider.value = p
  isRateGuideOpen.value = false
  providerForm.value = {
    name: p.name,
    provider_type: p.provider_type,
    base_url: p.base_url || '',
    api_key: '',
    max_concurrency: p.max_concurrency || 1,
    is_active: p.is_active,
    input_cost_per_million: p.input_cost_per_million !== undefined && p.input_cost_per_million !== null ? p.input_cost_per_million : 0.0,
    output_cost_per_million: p.output_cost_per_million !== undefined && p.output_cost_per_million !== null ? p.output_cost_per_million : 0.0,
  }
  isProviderModalOpen.value = true
}

async function saveProvider() {
  try {
    const rawIn = providerForm.value.input_cost_per_million
    const rawOut = providerForm.value.output_cost_per_million

    const parsedIn =
      rawIn === '' || rawIn === null || rawIn === undefined || isNaN(Number(rawIn))
        ? 0.0
        : Math.max(0, Number(rawIn))
    const parsedOut =
      rawOut === '' || rawOut === null || rawOut === undefined || isNaN(Number(rawOut))
        ? 0.0
        : Math.max(0, Number(rawOut))

    const payload = {
      ...providerForm.value,
      input_cost_per_million: parsedIn,
      output_cost_per_million: parsedOut,
    }

    if (editingProvider.value) {
      await AIConfigAPI.updateProvider(editingProvider.value.id, payload)
      uiStore.showToast('Provider updated successfully', 'success')
    } else {
      await AIConfigAPI.createProvider(payload)
      uiStore.showToast('Provider registered successfully', 'success')
    }
    isProviderModalOpen.value = false
    await loadProviders()
    syncStudioForm()
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : detail || err.message
    uiStore.showToast(msg, 'error')
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

// --------------------------------------------------------------------------
// Email Accounts State & OAuth
// --------------------------------------------------------------------------
const emailAccounts = ref([])
const loadingAccounts = ref(false)
const isEmailAccountModalOpen = ref(false)
const editingAccount = ref(null)
const syncingAccount = ref(null)
const showConnectionGuide = ref(false)
const showDeleteAccountModal = ref(false)
const accountToDelete = ref(null)
const isSavingAccount = ref(false)
const isDeletingAccount = ref(false)

const showClearAccountModal = ref(false)
const accountToClear = ref(null)
const isClearingAccount = ref(false)

const showClearAllModal = ref(false)
const isClearingAll = ref(false)

function formatFolderDisplay(folder) {
  if (!folder) return 'INBOX'
  if (folder.length > 24) {
    return folder.slice(0, 10) + '…' + folder.slice(-6)
  }
  return folder
}

const emailAccountForm = ref({
  name: '',
  provider_preset: 'gmail',
  auth_type: 'GMAIL_OAUTH',
  auth_method: 'oauth',
  username: '',
  app_password: '',
  imap_host: 'imap.gmail.com',
  imap_port: 993,
  folder: 'INBOX',
  client_id: '',
  client_secret: '',
  sync_interval: '1h',
  sync_schedule_hour: '09',
  sync_schedule_min: '00',
  sync_schedule_day: 'MON',
  is_active: true,
})

const oauthConfig = ref({
  google_redirect_uri: '',
  microsoft_redirect_uri: '',
})

const showOAuthGuide = ref(false)
const showClientSecret = ref(false)
const copiedRedirectUri = ref(false)
const availableMailFolders = ref([])
const isLoadingFolders = ref(false)
const isCustomFolderMode = ref(false)

async function fetchEmailFolders(accountId) {
  const id = accountId || editingAccount.value?.id
  if (!id) return
  isLoadingFolders.value = true
  try {
    const res = await EmailAccountsAPI.getFolders(id)
    if (res.data?.folders && res.data.folders.length > 0) {
      availableMailFolders.value = res.data.folders
      const folderIds = availableMailFolders.value.map((f) => (typeof f === 'object' ? f.id : f))
      if (!emailAccountForm.value.folder || !folderIds.includes(emailAccountForm.value.folder)) {
        const first = availableMailFolders.value[0]
        emailAccountForm.value.folder = typeof first === 'object' ? first.id : first
      }
    }
  } catch (err) {
    console.warn('Could not fetch folders:', err)
  } finally {
    isLoadingFolders.value = false
  }
}

const emailModalStep = ref(1)
const createdEmailAccountId = ref(null)

const EMAIL_PROVIDER_PRESETS = [
  {
    key: 'gmail',
    name: 'Google / Gmail',
    desc: 'Personal Gmail or Google Workspace accounts',
    auth_type: 'GMAIL_OAUTH',
    auth_method: 'oauth',
    defaultName: 'Gmail Inbox',
    host: 'imap.gmail.com',
    port: 993,
    supportsOAuth: true,
    badge: 'OAuth2 & App Password',
  },
  {
    key: 'outlook',
    name: 'Microsoft Outlook / 365',
    desc: 'Personal Outlook.com, Hotmail, or Microsoft 365',
    auth_type: 'MS_GRAPH_OAUTH',
    auth_method: 'oauth',
    defaultName: 'Outlook Inbox',
    host: 'outlook.office365.com',
    port: 993,
    supportsOAuth: true,
    badge: 'OAuth2 & App Password',
  },
  {
    key: 'icloud',
    name: 'Apple iCloud Mail',
    desc: 'iCloud.com / me.com accounts with App-Specific Password',
    auth_type: 'IMAP',
    auth_method: 'app_password',
    defaultName: 'iCloud Mail',
    host: 'imap.mail.me.com',
    port: 993,
    supportsOAuth: false,
    badge: 'App-Specific Password',
  },
  {
    key: 'popular',
    name: 'Fastmail / Yahoo / Proton',
    desc: 'Fastmail, Yahoo Mail, Proton Mail Bridge, Zoho Mail',
    auth_type: 'IMAP',
    auth_method: 'app_password',
    defaultName: 'Personal Mailbox',
    host: 'imap.fastmail.com',
    port: 993,
    supportsOAuth: false,
    badge: 'Direct IMAP SSL',
  },
  {
    key: 'custom',
    name: 'Custom IMAP Server',
    desc: 'Any standard private, self-hosted, or corporate IMAP server',
    auth_type: 'IMAP',
    auth_method: 'app_password',
    defaultName: 'Work Mailbox',
    host: '',
    port: 993,
    supportsOAuth: false,
    badge: 'Manual Server Setup',
  },
]

function canNavigateToEmailStep(step) {
  if (editingAccount.value) return true
  if (step === 1) return true
  if (step === 2) return true
  if (step === 3) return !!createdEmailAccountId.value || availableMailFolders.value.length > 0
  return false
}

function goToEmailStep(step) {
  if (canNavigateToEmailStep(step)) {
    emailModalStep.value = step
  }
}

function onSelectProviderPreset(presetKey) {
  const preset = EMAIL_PROVIDER_PRESETS.find((p) => p.key === presetKey) || EMAIL_PROVIDER_PRESETS[0]
  emailAccountForm.value.provider_preset = preset.key
  emailAccountForm.value.name = emailAccountForm.value.name || preset.defaultName
  emailAccountForm.value.imap_host = preset.host || ''
  emailAccountForm.value.imap_port = preset.port || 993
  emailAccountForm.value.auth_method = preset.auth_method
  emailAccountForm.value.auth_type = preset.auth_type
  emailModalStep.value = 2
}

async function copyRedirectUri(uri) {
  if (!uri) return
  try {
    await navigator.clipboard.writeText(uri)
    copiedRedirectUri.value = true
    uiStore.showToast('Redirect URI copied to clipboard!', 'success')
    setTimeout(() => {
      copiedRedirectUri.value = false
    }, 2500)
  } catch {
    uiStore.showToast('Could not copy to clipboard', 'error')
  }
}

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

async function loadOAuthConfig() {
  const origin = window.location.origin
  try {
    const res = await EmailAccountsAPI.getOAuthConfig()
    if (res.data?.base_url && !res.data.base_url.includes(':8000')) {
      oauthConfig.value = res.data
      return
    }
  } catch {
    // fallback
  }

  oauthConfig.value = {
    google_redirect_uri: `${origin}/api/v1/email_accounts/oauth/callback/google`,
    microsoft_redirect_uri: `${origin}/api/v1/email_accounts/oauth/callback/microsoft`,
  }
}

function onProviderPresetChange(preset) {
  emailAccountForm.value.provider_preset = preset
  if (preset === 'gmail') {
    emailAccountForm.value.name = emailAccountForm.value.name || 'Gmail Inbox'
    emailAccountForm.value.imap_host = 'imap.gmail.com'
    emailAccountForm.value.imap_port = 993
    emailAccountForm.value.auth_type = emailAccountForm.value.auth_method === 'oauth' ? 'GMAIL_OAUTH' : 'IMAP'
  } else if (preset === 'outlook') {
    emailAccountForm.value.name = emailAccountForm.value.name || 'Outlook Inbox'
    emailAccountForm.value.imap_host = 'outlook.office365.com'
    emailAccountForm.value.imap_port = 993
    emailAccountForm.value.auth_type = emailAccountForm.value.auth_method === 'oauth' ? 'MS_GRAPH_OAUTH' : 'IMAP'
  } else {
    emailAccountForm.value.name = emailAccountForm.value.name || 'Work IMAP'
    emailAccountForm.value.auth_type = 'IMAP'
    emailAccountForm.value.auth_method = 'app_password'
  }
}

function onAuthMethodChange(method) {
  emailAccountForm.value.auth_method = method
  if (method === 'oauth') {
    if (emailAccountForm.value.provider_preset === 'gmail') {
      emailAccountForm.value.auth_type = 'GMAIL_OAUTH'
    } else if (emailAccountForm.value.provider_preset === 'outlook') {
      emailAccountForm.value.auth_type = 'MS_GRAPH_OAUTH'
    }
  } else {
    emailAccountForm.value.auth_type = 'IMAP'
  }
}

function buildEmailAccountPayload() {
  const isOAuth = emailAccountForm.value.auth_type === 'GMAIL_OAUTH' || emailAccountForm.value.auth_type === 'MS_GRAPH_OAUTH'
  const fallbackUsername = isOAuth ? (editingAccount.value?.username || 'oauth_pending') : ''
  return {
    name: emailAccountForm.value.name.trim() || 'Recruitment Inbox',
    auth_type: emailAccountForm.value.auth_type,
    username: emailAccountForm.value.username.trim() || fallbackUsername,
    app_password: emailAccountForm.value.app_password || undefined,
    imap_host: emailAccountForm.value.imap_host.trim(),
    imap_port: Number(emailAccountForm.value.imap_port),
    folder: emailAccountForm.value.folder.trim() || 'INBOX',
    client_id: emailAccountForm.value.client_id.trim() || undefined,
    client_secret: emailAccountForm.value.client_secret.trim() || undefined,
    sync_interval: emailAccountForm.value.sync_interval,
    sync_schedule_time: `${emailAccountForm.value.sync_schedule_hour}:${emailAccountForm.value.sync_schedule_min}`,
    sync_schedule_day: emailAccountForm.value.sync_schedule_day,
    is_active: emailAccountForm.value.is_active,
  }
}

async function startOAuthLogin(providerName) {
  if (!emailAccountForm.value.client_id?.trim() || !emailAccountForm.value.client_secret?.trim()) {
    uiStore.showToast('Please enter both OAuth Client ID and Client Secret before authorizing.', 'error')
    return
  }

  isSavingAccount.value = true
  try {
    const payload = buildEmailAccountPayload()
    if (createdEmailAccountId.value) {
      await EmailAccountsAPI.update(createdEmailAccountId.value, payload)
    } else if (!editingAccount.value) {
      const res = await EmailAccountsAPI.create(payload)
      if (res.data?.id) createdEmailAccountId.value = res.data.id
    } else {
      await EmailAccountsAPI.update(editingAccount.value.id, payload)
    }

    const prov = providerName || emailAccountForm.value.provider_preset
    const redirectUri = prov === 'outlook'
      ? oauthConfig.value.microsoft_redirect_uri
      : oauthConfig.value.google_redirect_uri

    const res = await EmailAccountsAPI.getOAuthUrl({
      provider: prov === 'outlook' ? 'microsoft' : 'google',
      client_id: emailAccountForm.value.client_id || undefined,
      redirect_uri: redirectUri || undefined,
    })
    if (res.data.auth_url) {
      window.open(res.data.auth_url, '_blank', 'width=600,height=700')
      uiStore.showToast('Authorization window opened. Please sign in to connect.', 'info')
    } else {
      uiStore.showToast(res.data.message || 'No OAuth credentials configured.', 'info')
    }
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to initiate OAuth', 'error')
  } finally {
    isSavingAccount.value = false
  }
}

function openAddEmailAccountModal() {
  loadOAuthConfig()
  editingAccount.value = null
  createdEmailAccountId.value = null
  emailModalStep.value = 1
  availableMailFolders.value = []
  isCustomFolderMode.value = false
  emailAccountForm.value = {
    name: 'Gmail Inbox',
    provider_preset: 'gmail',
    auth_type: 'GMAIL_OAUTH',
    auth_method: 'oauth',
    username: '',
    app_password: '',
    imap_host: 'imap.gmail.com',
    imap_port: 993,
    folder: 'INBOX',
    client_id: '',
    client_secret: '',
    sync_interval: '1h',
    sync_schedule_hour: '09',
    sync_schedule_min: '00',
    sync_schedule_day: 'MON',
    is_active: true,
  }
  isEmailAccountModalOpen.value = true
}

function openEditEmailAccountModal(acc) {
  editingAccount.value = acc
  createdEmailAccountId.value = acc.id
  emailModalStep.value = 3
  availableMailFolders.value = []
  isCustomFolderMode.value = false
  let preset = 'custom'
  let method = 'app_password'
  if (acc.auth_type === 'GMAIL_OAUTH') {
    preset = 'gmail'
    method = 'oauth'
  } else if (acc.auth_type === 'MS_GRAPH_OAUTH') {
    preset = 'outlook'
    method = 'oauth'
  } else if (acc.imap_host?.includes('gmail')) {
    preset = 'gmail'
    method = 'app_password'
  } else if (acc.imap_host?.includes('office365') || acc.imap_host?.includes('outlook')) {
    preset = 'outlook'
    method = 'app_password'
  }

  const [rawH, rawM] = (acc.sync_schedule_time || '09:00').split(':')

  emailAccountForm.value = {
    name: acc.name,
    provider_preset: preset,
    auth_type: acc.auth_type || 'IMAP',
    auth_method: method,
    username: acc.username,
    app_password: '',
    imap_host: acc.imap_host || '',
    imap_port: acc.imap_port || 993,
    folder: acc.folder || 'INBOX',
    client_id: acc.client_id || '',
    client_secret: '',
    sync_interval: acc.sync_interval || '1h',
    sync_schedule_hour: rawH || '09',
    sync_schedule_min: rawM || '00',
    sync_schedule_day: acc.sync_schedule_day || 'MON',
    is_active: acc.is_active !== false,
  }
  isEmailAccountModalOpen.value = true
  fetchEmailFolders(acc.id)
}

async function handleStep2NextIMAP() {
  if (!emailAccountForm.value.username?.trim()) {
    uiStore.showToast('Please enter your email address / login.', 'error')
    return
  }
  if (!emailAccountForm.value.app_password?.trim() && !editingAccount.value) {
    uiStore.showToast('Please enter your App Password.', 'error')
    return
  }
  if (!emailAccountForm.value.imap_host?.trim()) {
    uiStore.showToast('Please enter your IMAP host.', 'error')
    return
  }

  isSavingAccount.value = true
  try {
    const payload = buildEmailAccountPayload()
    if (editingAccount.value) {
      await EmailAccountsAPI.update(editingAccount.value.id, payload)
      fetchEmailFolders(editingAccount.value.id)
    } else if (createdEmailAccountId.value) {
      await EmailAccountsAPI.update(createdEmailAccountId.value, payload)
      fetchEmailFolders(createdEmailAccountId.value)
    } else {
      const res = await EmailAccountsAPI.create(payload)
      if (res.data?.id) {
        createdEmailAccountId.value = res.data.id
        fetchEmailFolders(res.data.id)
      }
    }
    emailModalStep.value = 3
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to save credentials', 'error')
  } finally {
    isSavingAccount.value = false
  }
}

async function saveEmailAccount() {
  isSavingAccount.value = true
  try {
    const payload = buildEmailAccountPayload()
    const targetId = editingAccount.value?.id || createdEmailAccountId.value

    if (targetId) {
      await EmailAccountsAPI.update(targetId, payload)
      uiStore.showToast('Email account updated successfully', 'success')
    } else {
      await EmailAccountsAPI.create(payload)
      uiStore.showToast('Email account connected successfully', 'success')
    }
    isEmailAccountModalOpen.value = false
    loadEmailAccounts()
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to save email account', 'error')
  } finally {
    isSavingAccount.value = false
  }
}

async function triggerSync(acc) {
  syncingAccount.value = acc.id
  try {
    const res = await IntakeAPI.syncAccount({
      account_id: acc.id,
      since_date: '2024-01-01',
      max_results: 500,
    })
    uiStore.showToast(res.data.message || `Mailbox sync initiated for ${acc.name}!`, 'success')
    await loadEmailAccounts()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to sync mailbox', 'error')
  } finally {
    syncingAccount.value = null
  }
}

function openDeleteAccountModal(acc) {
  accountToDelete.value = acc
  showDeleteAccountModal.value = true
}

async function confirmDeleteAccount() {
  if (!accountToDelete.value) return
  isDeletingAccount.value = true
  try {
    await EmailAccountsAPI.delete(accountToDelete.value.id)
    uiStore.showToast('Email account removed', 'info')
    showDeleteAccountModal.value = false
    accountToDelete.value = null
    loadEmailAccounts()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to delete account', 'error')
  } finally {
    isDeletingAccount.value = false
  }
}

function openClearAccountModal(acc) {
  accountToClear.value = acc
  showClearAccountModal.value = true
}

async function confirmClearAccountHistory() {
  if (!accountToClear.value) return
  isClearingAccount.value = true
  try {
    const res = await EmailAccountsAPI.clearHistory(accountToClear.value.id)
    uiStore.showToast(res.data?.message || `Email sync history cleared for ${accountToClear.value.name}`, 'success')
    showClearAccountModal.value = false
    accountToClear.value = null
    loadEmailAccounts()
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to clear sync history', 'error')
  } finally {
    isClearingAccount.value = false
  }
}

function openClearAllModal() {
  showClearAllModal.value = true
}

async function confirmClearAllHistory() {
  isClearingAll.value = true
  try {
    const res = await EmailAccountsAPI.clearAllHistory()
    uiStore.showToast(res.data?.message || 'All email sync history cleared across accounts', 'success')
    showClearAllModal.value = false
    loadEmailAccounts()
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to clear all sync history', 'error')
  } finally {
    isClearingAll.value = false
  }
}

let settingsOAuthBroadcastChannel = null

async function handleOAuthSuccessMessage() {
  uiStore.showToast('Mailbox OAuth connected successfully!', 'success')
  await loadEmailAccounts()
  if (isEmailAccountModalOpen.value) {
    const match = emailAccounts.value.find((a) => a.id === createdEmailAccountId.value) || emailAccounts.value[emailAccounts.value.length - 1]
    if (match) {
      editingAccount.value = match
      createdEmailAccountId.value = match.id
      emailModalStep.value = 3
      await fetchEmailFolders(match.id)
    }
  }
}

function onWindowOAuthMessage(event) {
  if (event.data?.type === 'oauth_success') {
    handleOAuthSuccessMessage()
  }
}

function onWindowStorageMessage(event) {
  if (event.key === 'jobtracker_oauth_success' && event.newValue) {
    handleOAuthSuccessMessage()
  }
}

onMounted(async () => {
  window.addEventListener('message', onWindowOAuthMessage)
  window.addEventListener('storage', onWindowStorageMessage)
  try {
    settingsOAuthBroadcastChannel = new BroadcastChannel('jobtracker_oauth_channel')
    settingsOAuthBroadcastChannel.onmessage = (event) => {
      if (event.data?.type === 'oauth_success') {
        handleOAuthSuccessMessage()
      }
    }
  } catch {
    // BroadcastChannel unsupported fallback
  }

  await Promise.all([
    loadProviders(),
    loadBindings(),
    loadPrompts(),
    loadEmailAccounts(),
    loadOAuthConfig(),
    loadGlobalSettings(),
    loadUsageOverview(),
  ])
  syncGlobalForm()
  syncStudioForm()
})

onUnmounted(() => {
  window.removeEventListener('message', onWindowOAuthMessage)
  window.removeEventListener('storage', onWindowStorageMessage)
  if (settingsOAuthBroadcastChannel) {
    try {
      settingsOAuthBroadcastChannel.close()
    } catch {}
    settingsOAuthBroadcastChannel = null
  }
})
</script>

<template>
  <div class="page-container">
    <!-- Standardized Page Header -->
    <PageHeader
      title="Settings & Preferences"
      subtitle="Configure model bindings, thinking/reasoning parameters, custom prompt templates, AI providers, and email integrations."
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
            <span>Email Accounts ({{ emailAccounts.length }})</span>
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
            <span>Preferences</span>
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Scrollable Content Area with Stable Gutter -->
    <div class="settings-content-area">
      <div class="settings-inner-container">
        <!-- TAB 1: UNIFIED TASK STUDIO -->
        <div v-if="activeTab === 'studio'" class="tab-content animate-fade-in">

          <!-- GLOBAL DEFAULT HERO -->
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
                  title="Reset Global Default model back to factory recommended default"
                >
                  <RotateCcw :size="14" />
                  <span>Reset to Defaults</span>
                </button>
              </div>
            </div>

            <div class="global-hero-form">
              <div class="form-grid-2">
                <div class="input-group">
                  <div class="label-with-hint">
                    <label class="input-label">AI Provider *</label>
                  </div>
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
                  <div class="label-with-hint">
                    <label class="input-label">Model Identifier *</label>
                    <button
                      v-if="globalForm.provider_id"
                      type="button"
                      class="btn-refresh-models"
                      :disabled="loadingGlobalModels"
                      @click="fetchGlobalModels(globalForm.provider_id, true)"
                      title="Auto-discover models from live endpoint"
                    >
                      <RefreshCw :class="{ 'animate-spin': loadingGlobalModels }" :size="12" />
                      <span>{{ loadingGlobalModels ? 'Discovering...' : 'Auto-Discover' }}</span>
                    </button>
                  </div>
                  <input
                    v-model="globalForm.model_name"
                    type="text"
                    placeholder="e.g. gpt-4o, claude-3-7-sonnet, qwen/qwen3.5-9b"
                    class="form-input font-mono"
                    required
                    @input="scheduleGlobalAutoSave(600)"
                  />
                </div>
              </div>

              <!-- Quick Pick Discovered Chips -->
              <div v-if="globalProviderModels.length" class="model-suggestions-box mt-3">
                <span class="suggestions-label">Discovered Models on Provider:</span>
                <div class="suggestions-list">
                  <button
                    v-for="m in globalProviderModels"
                    :key="m.id"
                    type="button"
                    class="model-chip font-mono"
                    :class="{ active: globalForm.model_name === m.id }"
                    @click="selectGlobalSuggestedModel(m.id)"
                  >
                    <Check v-if="globalForm.model_name === m.id" :size="11" />
                    <span>{{ m.id }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- ADVANCED OVERRIDES ACCORDION -->
          <div class="advanced-overrides-section">
            <button class="advanced-toggle-btn" @click="isAdvancedOpen = !isAdvancedOpen">
              <div class="advanced-toggle-left">
                <SlidersHorizontal :size="16" />
                <span>Advanced: Task-Specific Overrides</span>
              </div>
              <ChevronDown :size="16" class="accordion-icon" :class="{ 'rotated': isAdvancedOpen }" />
            </button>

            <transition name="accordion-fade">
              <div v-show="isAdvancedOpen" class="advanced-overrides-content">
                <div class="studio-layout">
        <!-- Studio Task Selector Sidebar -->
        <div class="studio-sidebar">
          <div class="sidebar-header">
            <span class="sidebar-title">Pipeline Tasks</span>
            <span class="sidebar-badge">{{ TASKS.length }} Tasks</span>
          </div>

          <div class="task-nav-list">
            <button
              v-for="t in TASKS"
              :key="t.key"
              v-show="!t.hidden?.value"
              class="task-nav-item"
              :class="{ active: selectedTaskKey === t.key }"
              @click="selectStudioTask(t.key)"
            >
              <div class="task-nav-left">
                <span class="task-nav-name">{{ t.label }}</span>
              </div>
              <div class="task-nav-right">
                <span
                  v-if="isTaskCustomized(t.key)"
                  class="task-bound-indicator"
                  title="Customized parameters"
                >
                  <CheckCircle2 :size="12" class="text-primary" />
                </span>
              </div>
            </button>
          </div>
        </div>

        <!-- Studio Workspace Pane -->
        <div class="studio-workspace">
          <!-- Active Task Overview Header -->
          <div class="studio-task-header">
            <div class="task-header-info">
              <div class="task-badge-row">
                <span v-if="activeTaskDef.recommendedTemp !== null && typeof activeTaskDef.recommendedTemp === 'number'" class="rec-temp-chip">
                  <Thermometer :size="11" />
                  <span>Recommended Temp: {{ activeTaskDef.recommendedTemp }}</span>
                </span>
                <span v-else-if="activeTaskDef.key === 'EMBEDDING'" class="rec-temp-chip">
                  <Cpu :size="11" />
                  <span>Dense Vectors: 768 dimensions</span>
                </span>
                <span v-if="activeTaskDef.recommendedReasoning && activeTaskDef.recommendedReasoning !== 'none'" class="rec-reasoning-chip">
                  <Zap :size="11" />
                  <span>Recommended Reasoning: {{ activeTaskDef.recommendedReasoning }}</span>
                </span>
              </div>
              <h2 class="task-header-title">{{ activeTaskDef.label }}</h2>
              <p class="task-header-desc">{{ activeTaskDef.desc }}</p>
            </div>

            <div class="studio-header-actions flex items-center gap-2">
              <button
                class="btn btn-ghost btn-sm text-secondary"
                :disabled="isResettingPrompt"
                @click="resetStudioTaskToDefaults"
                title="Reset parameters and prompt back to task recommendations"
              >
                <RotateCcw :size="14" />
                <span>Reset to Defaults</span>
              </button>
            </div>
          </div>

          <!-- Section 1: Model & Execution Binding -->
          <div class="studio-card">
            <div class="studio-card-title">
              <BrainCircuit :size="16" class="text-primary" />
              <span>Model &amp; Execution Binding</span>
            </div>

            <div v-if="selectedTaskKey !== 'EMBEDDING'" class="use-global-checkbox mb-4">
              <label class="custom-checkbox">
                <input
                  type="checkbox"
                  v-model="studioForm.use_global_default"
                  @change="scheduleStudioAutoSave(50)"
                />
                <span class="checkmark"></span>
                <span class="checkbox-label">Use Global Default Model ({{ globalBinding?.model_name || 'qwen/qwen3.5-9b' }})</span>
              </label>
              <p class="checkbox-hint">When checked, this task inherits the global provider and model while keeping its own execution parameters.</p>
            </div>

            <div v-if="studioForm.use_global_default && selectedTaskKey !== 'EMBEDDING'" class="inherited-model-banner mb-4">
              <span class="inherited-icon">ℹ️</span>
              <span>Inheriting Global Default Model: <strong>{{ globalBinding?.model_name || 'qwen/qwen3.5-9b' }}</strong>. You can still customize temperature, thinking mode, and max tokens below.</span>
            </div>

            <div class="form-grid-2" :class="{ 'opacity-50 pointer-events-none': studioForm.use_global_default && selectedTaskKey !== 'EMBEDDING' }">
              <div class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">AI Provider *</label>
                </div>
                <select
                  v-model="studioForm.provider_id"
                  class="form-input"
                  @change="onStudioProviderChange"
                >
                  <option v-for="p in providers" :key="p.id" :value="p.id">
                    {{ p.name }} ({{ p.provider_type }})
                  </option>
                </select>
              </div>

              <div class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">Model Identifier *</label>
                  <div class="flex items-center gap-2">
                    <button
                      v-if="studioForm.provider_id && studioForm.model_name"
                      type="button"
                      class="btn-refresh-models"
                      :disabled="probeLoading"
                      @click="runModelProbe"
                      title="Probe model capabilities, thinking flags, and parameters"
                    >
                      <Zap :class="{ 'animate-spin': probeLoading }" :size="12" />
                      <span>{{ probeLoading ? 'Probing...' : 'Probe Capabilities' }}</span>
                    </button>
                    <button
                      v-if="studioForm.provider_id"
                      type="button"
                      class="btn-refresh-models"
                      :disabled="loadingStudioModels"
                      @click="fetchStudioModels(studioForm.provider_id, true)"
                      title="Auto-discover models from live endpoint"
                    >
                      <RefreshCw :class="{ 'animate-spin': loadingStudioModels }" :size="12" />
                      <span>{{ loadingStudioModels ? 'Discovering...' : 'Auto-Discover' }}</span>
                    </button>
                  </div>
                </div>

                <input
                  v-model="studioForm.model_name"
                  type="text"
                  placeholder="e.g. gpt-4o, claude-3-7-sonnet, deepseek-r1"
                  class="form-input font-mono"
                  required
                  @input="scheduleStudioAutoSave(600)"
                />
              </div>
            </div>

            <!-- Model Probe Insights Banner -->
            <div v-if="probeResult" class="probe-result-box mt-3 mb-2 animate-fade-in">
              <div class="probe-result-header">
                <div class="probe-result-title">
                  <Sparkles :size="14" class="text-primary" />
                  <span>Model Capability Insights: <strong>{{ probeResult.model_name }}</strong></span>
                </div>
                <button
                  type="button"
                  class="btn btn-primary btn-xs"
                  @click="applyProbeRecommendations"
                >
                  <Check :size="12" />
                  <span>Apply Recommended Settings</span>
                </button>
              </div>

              <div class="probe-details-grid">
                <div class="probe-detail-item">
                  <span class="probe-detail-label">Architecture:</span>
                  <span class="probe-detail-val font-mono" :class="probeResult.is_reasoning_model ? 'text-warning' : 'text-success'">
                    {{ probeResult.is_reasoning_model ? '🧠 Reasoning Architecture' : '⚡ Standard Fast LLM' }}
                  </span>
                </div>

                <div v-if="probeResult.detected_tags?.length" class="probe-detail-item">
                  <span class="probe-detail-label">Tags:</span>
                  <span class="probe-detail-val font-mono text-info">{{ probeResult.detected_tags.join(', ') }}</span>
                </div>

                <div class="probe-detail-item">
                  <span class="probe-detail-label">Reasoning Effort:</span>
                  <span class="probe-detail-val font-mono text-primary">{{ probeResult.supports_reasoning_effort ? 'Supported' : 'Standard' }}</span>
                </div>
              </div>

              <p v-if="probeResult.notes" class="probe-notes mt-1.5">{{ probeResult.notes }}</p>
            </div>

            <!-- Curated / Discovered Models Quick Pick Chips -->
            <div
              v-if="studioProviderModels.length"
              class="model-suggestions-box"
              :class="{ 'opacity-50 pointer-events-none': studioForm.use_global_default && selectedTaskKey !== 'EMBEDDING' }"
            >
              <span class="suggestions-label">Discovered / Available Models on Provider:</span>
              <div class="suggestions-list">
                <button
                  v-for="m in studioProviderModels"
                  :key="m.id"
                  type="button"
                  class="model-chip font-mono"
                  :disabled="studioForm.use_global_default && selectedTaskKey !== 'EMBEDDING'"
                  :class="{ active: studioForm.model_name === m.id }"
                  @click="selectStudioSuggestedModel(m.id)"
                >
                  <Check v-if="studioForm.model_name === m.id" :size="11" />
                  <span>{{ m.id }}</span>
                </button>
              </div>
            </div>

            <!-- Parameters Grid (Temperature, Thinking Mode, Max Tokens) -->
            <div v-if="selectedTaskKey === 'EMBEDDING'" class="form-grid-2 mt-4">
              <div class="input-group">
                <label class="input-label">Embedding Dimensions</label>
                <input
                  v-model.number="studioForm.embedding_dimensions"
                  type="number"
                  placeholder="768"
                  class="form-input font-mono"
                  @input="scheduleStudioAutoSave(600)"
                />
              </div>
              <div class="input-group flex flex-col justify-end">
                <span class="text-xs text-muted leading-relaxed">
                  Vector representation size for <code>pgvector</code> similarity search (standard: 768 dimensions).
                </span>
              </div>
            </div>

            <template v-else>
              <div class="form-grid-2 mt-4">
                <!-- Thinking / Reasoning Mode Segmented Control -->
                <div class="input-group">
                  <div class="label-with-hint">
                    <label class="input-label">Thinking / Reasoning Mode</label>
                  </div>
                  <div class="reasoning-pills">
                    <button
                      v-for="effort in ['none', 'low', 'medium', 'high', 'custom']"
                      :key="effort"
                      type="button"
                      class="reasoning-pill font-mono"
                      :class="{ active: studioForm.reasoning_effort === effort }"
                      @click="setStudioReasoningEffort(effort)"
                    >
                      {{ effort === 'none' ? 'None (Fast)' : (effort === 'custom' ? 'Custom JSON' : effort) }}
                    </button>
                  </div>
                  <div v-if="activeTaskDef?.reasoningTip" class="reasoning-task-guidance mt-2 animate-fade-in">
                    <span>{{ activeTaskDef.reasoningTip }}</span>
                  </div>
                </div>

                <!-- Max Tokens -->
                <div class="input-group">
                  <div class="label-with-hint">
                    <label class="input-label">Max Generation Tokens</label>
                  </div>
                  <input
                    v-model.number="studioForm.max_tokens"
                    type="number"
                    step="256"
                    min="256"
                    max="64000"
                    placeholder="Optional (Default unconstrained)"
                    class="form-input font-mono"
                    @input="scheduleStudioAutoSave(600)"
                  />
                </div>
              </div>

              <!-- Custom Extra Body JSON (Expandable Editor) -->
              <div v-if="studioForm.reasoning_effort === 'custom'" class="input-group mt-3 animate-fade-in">
                <div class="label-with-hint">
                  <label class="input-label">Custom Request Extra Body (JSON)</label>
                  <span class="text-xs text-muted">Pass engine-specific parameters like <code>chat_template_kwargs</code> or <code>thinking</code></span>
                </div>
                <textarea
                  v-model="studioForm.custom_extra_body_json"
                  rows="3"
                  class="form-input font-mono text-xs"
                  placeholder='{\n  "chat_template_kwargs": { "thinking": false }\n}'
                  @input="scheduleStudioAutoSave(800)"
                ></textarea>
                <span v-if="customExtraBodyError" class="text-xs text-danger mt-1">
                  {{ customExtraBodyError }}
                </span>
              </div>

              <!-- Sampling Temperature Slider -->
              <div class="input-group mt-3">
                <div class="label-with-hint">
                  <label class="input-label">Sampling Temperature</label>
                  <span class="font-mono text-xs font-semibold text-primary">{{ studioForm.temperature }}</span>
                </div>
                <div class="form-range-container">
                  <input
                    v-model.number="studioForm.temperature"
                    type="range"
                    step="0.05"
                    min="0.0"
                    max="1.0"
                    class="form-range"
                    @input="scheduleStudioAutoSave(300)"
                    @change="scheduleStudioAutoSave(50)"
                  />
                </div>
              </div>
            </template>

            <div v-if="selectedTaskKey !== 'EMBEDDING'" class="reasoning-info-callout">
              <Zap :size="13" class="text-primary flex-shrink-0" />
              <span>
                <strong>Thinking Mode &amp; Token Limits:</strong> Instructs reasoning models (e.g. DeepSeek-R1, OpenAI o1/o3-mini, Claude 3.7 Thinking, Gemini Thinking) to execute extended chain-of-thought verification. Leaving Max Tokens as <em>Optional (Default unconstrained)</em> ensures reasoning chains don't get truncated before output generation.
              </span>
            </div>
          </div>

          <!-- Section 2: Prompt Template Editor (If task has prompt) -->
          <div v-if="activeTaskDef.hasPrompt" class="studio-card">
            <div class="studio-card-header">
              <div class="studio-card-title">
                <FileCode :size="16" class="text-primary" />
                <span>Prompt Template</span>
              </div>

              <button
                class="btn btn-ghost btn-xs text-secondary"
                :disabled="isResettingPrompt"
                @click="resetStudioPrompt"
                title="Reset to default seeded template"
              >
                <RotateCcw :size="12" />
                <span>Reset to Default</span>
              </button>
            </div>

            <!-- Injected Placeholders -->
            <div v-if="activeTaskDef.variables.length" class="placeholders-box">
              <span class="placeholder-label">Injected Variables:</span>
              <span
                v-for="v in activeTaskDef.variables"
                :key="v"
                class="placeholder-tag font-mono"
              >
                {{ v }}
              </span>
            </div>

            <!-- Monospace Editor -->
            <textarea
              v-model="studioForm.prompt_template"
              rows="12"
              class="prompt-textarea font-mono"
              placeholder="Enter prompt template instructions..."
              @input="scheduleStudioAutoSave(800)"
              @change="scheduleStudioAutoSave(50)"
            ></textarea>
          </div>
        </div>
                </div>
              </div>
            </transition>
          </div>
    </div>

    <!-- TAB 2: AI PROVIDERS -->
    <div v-else-if="activeTab === 'providers'" class="tab-content animate-fade-in">
      <!-- USAGE & COST / CLOUD SAVINGS OVERVIEW CARD -->
      <div class="section-card usage-overview-card">
        <div class="section-header-row">
          <div class="section-header-text">
            <div class="usage-title-badge-row">
              <h3>Token Usage &amp; Cost Overview</h3>
              <span
                v-if="usageOverview.local_inference_percentage >= 100"
                class="badge badge-success font-mono flex items-center gap-1"
              >
                <span class="pulse-dot-green"></span> 100% Local Inference
              </span>
              <span
                v-else-if="usageOverview.local_inference_percentage <= 0"
                class="badge badge-applied font-mono flex items-center gap-1"
              >
                <Sparkles :size="12" /> Cloud API Spend
              </span>
              <span
                v-else
                class="badge badge-purple font-mono flex items-center gap-1"
              >
                <Zap :size="12" /> {{ usageOverview.local_inference_percentage }}% Local • Hybrid
              </span>
            </div>
            <p>Financial transparency and tracking for both Cloud API keys and local on-device LLMs.</p>
          </div>
          <div class="section-header-actions">
            <button
              class="btn btn-secondary btn-sm"
              @click="openPricingModal"
              title="Configure benchmark rates for comparative provider calculations"
            >
              <SlidersHorizontal :size="14" />
              <span>Benchmark Rates</span>
            </button>
            <button
              class="btn btn-secondary btn-sm"
              :class="{ 'btn-active': isComparisonOpen }"
              @click="isComparisonOpen = !isComparisonOpen"
            >
              <BarChart3 :size="14" />
              <span>{{ isComparisonOpen ? 'Hide Cost Comparison' : 'Compare Provider Costs' }}</span>
              <ChevronUp v-if="isComparisonOpen" :size="13" />
              <ChevronDown v-else :size="13" />
            </button>
            <button
              class="btn btn-secondary btn-sm"
              :disabled="loadingUsage"
              @click="loadUsageOverview"
              title="Refresh usage statistics"
            >
              <RefreshCw :size="14" :class="{ 'animate-spin': loadingUsage }" />
            </button>
          </div>
        </div>

        <!-- Usage Metrics Grid -->
        <div class="usage-metrics-grid">
          <!-- Metric 1: Monthly Usage & Spend / Savings -->
          <div class="usage-metric-box">
            <span class="usage-metric-label">
              <Clock :size="14" class="text-muted" />
              This Month's Tokens
            </span>
            <div class="usage-metric-val font-mono">
              {{ formatTokens(usageOverview.monthly_tokens) }}
              <span class="usage-sub-tokens text-muted font-mono">({{ usageOverview.monthly_tokens.toLocaleString() }})</span>
            </div>
            <div class="usage-metric-footer">
              <template v-if="usageOverview.local_inference_percentage >= 100">
                <span class="text-success font-medium">Estimated Cloud Savings: ~${{ usageOverview.monthly_savings_usd.toFixed(2) }}</span>
              </template>
              <template v-else-if="usageOverview.local_inference_percentage <= 0">
                <span class="text-primary font-medium">Estimated Spend: ${{ usageOverview.monthly_spend_usd.toFixed(2) }}</span>
              </template>
              <template v-else>
                <span class="text-primary font-medium">Spend: ${{ usageOverview.monthly_spend_usd.toFixed(2) }}</span>
                <span class="text-muted">•</span>
                <span class="text-success font-medium">Saved: ~${{ usageOverview.monthly_savings_usd.toFixed(2) }}</span>
              </template>
            </div>
          </div>

          <!-- Metric 2: All-Time Financial Overview -->
          <div class="usage-metric-box">
            <span class="usage-metric-label">
              <DollarSign :size="14" class="text-muted" />
              All-Time Value
            </span>
            <div class="usage-metric-val font-mono">
              <template v-if="usageOverview.local_inference_percentage >= 100">
                <span class="text-success font-semibold">~${{ usageOverview.all_time_savings_usd.toFixed(2) }}</span>
                <span class="usage-sub-tokens text-muted">saved</span>
              </template>
              <template v-else-if="usageOverview.local_inference_percentage <= 0">
                <span class="text-primary font-semibold">${{ usageOverview.all_time_spend_usd.toFixed(2) }}</span>
                <span class="usage-sub-tokens text-muted">spent</span>
              </template>
              <template v-else>
                <span class="text-primary font-semibold">${{ usageOverview.all_time_spend_usd.toFixed(2) }}</span>
                <span class="usage-sub-tokens text-success font-medium">(~${{ usageOverview.all_time_savings_usd.toFixed(2) }} saved)</span>
              </template>
            </div>
            <div class="usage-metric-footer text-muted font-mono">
              All-time tokens: {{ formatTokens(usageOverview.all_time_tokens) }} • {{ usageOverview.total_llm_calls }} LLM calls
            </div>
          </div>

          <!-- Metric 3: Cost Efficiency / Avg per Action -->
          <div class="usage-metric-box">
            <span class="usage-metric-label">
              <Activity :size="14" class="text-muted" />
              Cost Efficiency &amp; Average
            </span>
            <div class="usage-metric-val font-mono">
              <template v-if="usageOverview.local_inference_percentage >= 100">
                <span class="text-success font-semibold">$0.0000</span>
                <span class="usage-sub-tokens text-muted">/ assessment</span>
              </template>
              <template v-else>
                <span class="text-primary font-semibold">${{ usageOverview.avg_cost_per_assessment.toFixed(4) }}</span>
                <span class="usage-sub-tokens text-muted">/ assessment</span>
              </template>
            </div>
            <div class="usage-metric-footer text-muted">
              <template v-if="usageOverview.local_inference_percentage >= 100">
                🟢 100% on-device private inference
              </template>
              <template v-else>
                Benchmark local rate: $0.15/1M in, $0.60/1M out
              </template>
            </div>
          </div>
        </div>

        <!-- Expandable What-If Provider Cost Comparison Drawer -->
        <div v-if="isComparisonOpen" class="provider-comparison-drawer animate-fade-in">
          <div class="comparison-drawer-header">
            <div class="comparison-title-wrap">
              <h4 class="comparison-heading">
                <BarChart3 :size="15" class="text-primary" />
                <span>What-If Provider Cost Comparison</span>
              </h4>
              <p class="comparison-sub">
                Estimated cost for this month's token volume ({{ formatTokens(usageOverview.monthly_tokens) }} tokens) if run across alternative model APIs.
              </p>
            </div>
          </div>

          <div class="comparison-table-wrapper">
            <table class="comparison-table">
              <thead>
                <tr>
                  <th>Provider / Benchmark Model</th>
                  <th>Rates ($/1M in / out)</th>
                  <th>Simulated Monthly Cost</th>
                  <th>vs Current Setup</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, idx) in usageOverview.comparative_costs || []"
                  :key="idx"
                  :class="{ 'highlight-active-row': item.is_local && usageOverview.local_inference_percentage >= 50 }"
                >
                  <td class="font-medium">
                    <div class="provider-cell flex items-center gap-1.5">
                      <span class="provider-brand font-semibold">{{ item.provider_name }}</span>
                      <span class="model-sub text-muted">({{ item.model_name }})</span>
                      <span
                        v-if="item.is_local && usageOverview.local_inference_percentage >= 50"
                        class="badge badge-success font-mono text-[10px] py-0 px-1"
                      >
                        Your Active Setup
                      </span>
                    </div>
                  </td>
                  <td class="font-mono text-muted">
                    ${{ item.input_cost_per_million.toFixed(2) }} / ${{ item.output_cost_per_million.toFixed(2) }}
                  </td>
                  <td class="font-mono font-semibold">
                    <span v-if="item.is_local" class="text-success">$0.00 (Free)</span>
                    <span v-else class="text-main">${{ item.simulated_cost_usd.toFixed(4) }}</span>
                  </td>
                  <td>
                    <span
                      v-if="item.status === 'cheaper'"
                      class="badge badge-success font-mono flex items-center gap-1 w-fit"
                    >
                      <ArrowDown :size="11" /> -${{ Math.abs(item.diff_usd).toFixed(4) }} ({{ item.diff_percentage }}%)
                    </span>
                    <span
                      v-else-if="item.status === 'more_expensive'"
                      class="badge badge-danger font-mono flex items-center gap-1 w-fit"
                    >
                      <ArrowUp :size="11" /> +${{ item.diff_usd.toFixed(4) }} (+{{ item.diff_percentage }}%)
                    </span>
                    <span
                      v-else
                      class="badge badge-applied font-mono text-muted w-fit"
                    >
                      Active Plan
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="section-card">
        <div class="section-header-row">
          <div class="section-header-text">
            <h3>Configured AI Providers</h3>
            <p>Connect local endpoints (LM Studio, Ollama, vLLM) or Cloud APIs (OpenAI, Anthropic, Gemini, OpenRouter).</p>
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
                <span class="meta-v font-mono">{{ p.base_url || 'Default Cloud Endpoint' }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-k">API Key:</span>
                <span class="meta-v font-mono">{{ p.api_key_masked || 'Not Required / Local' }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-k">Token Rate ($/1M):</span>
                <span v-if="(p.input_cost_per_million || 0) === 0 && (p.output_cost_per_million || 0) === 0" class="meta-v font-mono text-success font-semibold">
                  Local / Free ($0.00)
                </span>
                <span v-else class="meta-v font-mono font-semibold">
                  ${{ (p.input_cost_per_million || 0).toFixed(2) }} in / ${{ (p.output_cost_per_million || 0).toFixed(2) }} out
                </span>
              </div>
              <div class="meta-row">
                <span class="meta-k">Max Concurrency:</span>
                <span class="meta-v font-mono font-semibold">{{ p.max_concurrency || 1 }} parallel</span>
              </div>
            </div>

            <div class="provider-actions">
              <button
                class="btn btn-secondary btn-sm"
                :disabled="testingProviderId === p.id"
                @click="testProviderDirect(p)"
                title="Ping endpoint to verify connectivity"
              >
                <Loader2 v-if="testingProviderId === p.id" class="animate-spin" :size="14" />
                <Zap v-else :size="14" />
                <span>Ping Provider</span>
              </button>

              <button class="btn btn-secondary btn-sm" @click="openEditProvider(p)">
                <Edit3 :size="14" />
                <span>Edit</span>
              </button>

              <button class="btn btn-danger btn-sm" @click="deleteProvider(p.id)">
                <Trash2 :size="14" />
              </button>
            </div>

            <!-- Provider Test Result -->
            <div
              v-if="providerTestResults[p.id]"
              class="provider-test-pill animate-fade-in"
              :class="`is-${providerTestResults[p.id].status}`"
            >
              <CheckCircle v-if="providerTestResults[p.id].status === 'success'" :size="13" class="text-success" />
              <AlertCircle v-else-if="providerTestResults[p.id].status === 'warning'" :size="13" class="text-warning" />
              <AlertCircle v-else :size="13" class="text-danger" />
              <span class="font-mono text-xs">{{ providerTestResults[p.id].message }}</span>
            </div>
          </div>

          <div v-if="providers.length === 0" class="empty-state">
            No AI providers configured in DB. System using `.env` fallback.
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: EMAIL ACCOUNTS -->
    <div v-else-if="activeTab === 'email_accounts'" class="tab-content animate-fade-in">
      <div class="section-card">
        <div v-if="uiStore.isDemoMode" class="email-disabled-banner mb-4">
          <div class="banner-left">
            <Info :size="16" class="text-primary" />
            <span><strong>Email sync disabled in client demo mode.</strong> Mailbox background polling and IMAP fetches require a live backend.</span>
          </div>
        </div>

        <div class="section-header-row">
          <div class="section-header-text">
            <h3>Connected Mailboxes &amp; Sync Schedule</h3>
            <p>Connect mailboxes via 1-Click OAuth (Google / Microsoft) or IMAP, and configure automated background sync schedules.</p>
          </div>
          <div class="section-header-actions">
            <button
              v-if="emailAccounts.length > 0 && uiStore.enableEmailIntake"
              class="btn btn-secondary btn-sm"
              @click="openClearAllModal"
              title="Clear all email deduplication history across accounts"
            >
              <RotateCcw :size="14" />
              <span>Clear All Sync History</span>
            </button>
            <div class="email-sync-toggle-pill">
              <span class="sync-status-label">
                Auto-Sync:
                <strong :class="uiStore.enableEmailIntake ? 'text-success' : 'text-muted'">
                  {{ uiStore.enableEmailIntake ? 'Active' : 'Paused' }}
                </strong>
              </span>
              <label class="switch-toggle" title="Toggle automatic email syncing">
                <input
                  type="checkbox"
                  :checked="uiStore.enableEmailIntake"
                  @change="toggleEmailIntake"
                />
                <span class="slider round"></span>
              </label>
            </div>
            <button class="btn btn-primary btn-sm" @click="openAddEmailAccountModal">
              <Plus :size="15" />
              <span>Connect Account</span>
            </button>
          </div>
        </div>

        <!-- Accounts Grid (Collapsed when auto-sync is off) -->
        <div v-if="uiStore.enableEmailIntake" class="accounts-grid animate-fade-in">
          <div v-for="acc in emailAccounts" :key="acc.id" class="account-card">
            <div class="account-card-header">
              <div class="account-title-row">
                <div class="account-icon-wrap">
                  <Mail :size="15" class="text-primary" />
                </div>
                <div class="account-name-group">
                  <span class="account-name">{{ acc.name }}</span>
                </div>
              </div>
              <span class="badge badge-applied font-mono">{{ acc.auth_type }}</span>
            </div>

            <div class="account-card-body">
              <div class="meta-row">
                <span class="meta-k">Username</span>
                <span class="meta-v font-mono" :title="acc.username">{{ acc.username }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-k">Folder</span>
                <span class="meta-v font-mono" :title="acc.folder">{{ formatFolderDisplay(acc.folder) }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-k">Sync Interval</span>
                <span class="meta-v font-mono">{{ acc.sync_interval || '1h' }}</span>
              </div>
              <div v-if="acc.last_synced_at" class="meta-row">
                <span class="meta-k">Last Synced</span>
                <span class="meta-v text-muted">{{ new Date(acc.last_synced_at).toLocaleDateString() }} {{ new Date(acc.last_synced_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</span>
              </div>
            </div>

            <div class="account-actions">
              <button
                class="btn btn-primary btn-sm btn-sync-action"
                :disabled="syncingAccount === acc.id"
                @click="triggerSync(acc)"
              >
                <Loader2 v-if="syncingAccount === acc.id" class="animate-spin" :size="14" />
                <RefreshCw v-else :size="14" />
                <span>{{ syncingAccount === acc.id ? 'Syncing...' : 'Sync Now' }}</span>
              </button>

              <button class="btn btn-secondary btn-sm btn-icon" title="Edit mailbox settings" @click="openEditEmailAccountModal(acc)">
                <Edit3 :size="14" />
              </button>

              <button class="btn btn-danger btn-sm btn-icon" title="Remove mailbox" @click="openDeleteAccountModal(acc)">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>

          <div v-if="emailAccounts.length === 0" class="empty-state">
            <Mail :size="36" class="empty-icon text-muted mb-2" />
            <h4 class="empty-title">No Mailboxes Connected</h4>
            <p class="empty-desc">
              Connect your Gmail, Outlook, or IMAP account using the <strong>Connect Account</strong> button above to automatically scan incoming recruitment communications and update your application pipeline.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: PREFERENCES -->
    <div v-else-if="activeTab === 'preferences'" class="tab-content animate-fade-in">
      <div class="section-card">
        <div class="card-intro">
          <h3>System &amp; Workspace Preferences</h3>
          <p>Configure global defaults, intake automations, telemetry, and background indexing.</p>
        </div>

        <div class="preferences-grid">
          <!-- 0. Client Demo Mode & Dataset Card -->
          <div v-if="uiStore.isDemoMode" class="preference-card preference-card-wide border-primary">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <Sparkles :size="18" />
              </div>
              <div class="preference-header-text">
                <div class="preference-header-between">
                  <h4 class="preference-title">Client-First Demo Mode Active</h4>
                  <span class="badge badge-applied font-mono">STANDALONE DEMO</span>
                </div>
                <p class="preference-desc">Running standalone against browser <code>localStorage</code> and Pinia stores without requiring a live FastAPI backend server.</p>
              </div>
            </div>
            <div class="preference-body">
              <div class="flex items-center justify-between gap-4 flex-wrap">
                <div class="flex flex-col gap-1">
                  <span class="text-xs font-semibold text-main">Local Dataset Hydration</span>
                  <span class="text-xs text-secondary">Instantly restore pristine candidate profile, 5 applications, action items, staging tasks, and telemetry logs.</span>
                </div>
                <button
                  class="btn btn-primary btn-sm"
                  @click="uiStore.resetDemoData"
                  title="Reset localStorage demo keys and re-hydrate Pinia stores reactively"
                >
                  <RotateCcw :size="14" />
                  <span>Reset Demo Data</span>
                </button>
              </div>
            </div>
          </div>

          <!-- 1. Default System Currency Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <DollarSign :size="18" />
              </div>
              <div class="preference-header-text">
                <h4 class="preference-title">Default Currency</h4>
                <p class="preference-desc">Standard currency unit for compensation ranges, salary inputs, and offer packages.</p>
              </div>
            </div>
            <div class="preference-body">
              <div class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">Base Currency</label>
                </div>
                <select
                  class="form-input"
                  :value="uiStore.defaultCurrency"
                  @change="e => uiStore.setDefaultCurrency(e.target.value)"
                >
                  <option
                    v-for="c in uiStore.SUPPORTED_CURRENCIES"
                    :key="c.code"
                    :value="c.code"
                  >
                    {{ c.code }} ({{ c.symbol }})
                  </option>
                </select>
                <span class="preference-field-hint">
                  Used for automatic currency normalization during job intake.
                </span>
              </div>
            </div>
          </div>

          <!-- 2. Automated Cover Letter Generation Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <FileText :size="18" />
              </div>
              <div class="preference-header-text">
                <div class="preference-header-between">
                  <h4 class="preference-title">Automated Cover Letters</h4>
                  <label class="switch-toggle" title="Toggle automatic cover letter generation">
                    <input
                      type="checkbox"
                      :checked="enableAutoCoverLetter"
                      :disabled="isUpdatingCoverLetterSettings"
                      @change="toggleAutoCoverLetter"
                    />
                    <span class="slider round"></span>
                  </label>
                </div>
                <p class="preference-desc">Automatically drafts tailored cover letters during intake when fit score meets your threshold.</p>
              </div>
            </div>

            <div class="preference-body" :class="{ 'is-disabled': !enableAutoCoverLetter }">
              <div class="cover-letter-pref-grid">
                <!-- Minimum Match Score Threshold -->
                <div class="input-group">
                  <div class="label-with-hint">
                    <label class="input-label">Match Threshold</label>
                  </div>
                  <div class="threshold-slider-control">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="1"
                      :value="coverLetterMatchThreshold"
                      :disabled="!enableAutoCoverLetter || isUpdatingCoverLetterSettings"
                      class="form-range cover-letter-slider"
                      @input="coverLetterMatchThreshold = Number($event.target.value)"
                      @change="updateCoverLetterThreshold"
                    />
                    <span class="threshold-badge">{{ coverLetterMatchThreshold }}%</span>
                  </div>
                  <span class="preference-field-hint">
                    Minimum score to trigger drafting.
                  </span>
                </div>

                <!-- Default Cover Letter Length -->
                <div class="input-group">
                  <div class="label-with-hint">
                    <label class="input-label">Target Length</label>
                  </div>
                  <select
                    :value="coverLetterLength"
                    :disabled="!enableAutoCoverLetter || isUpdatingCoverLetterSettings"
                    class="form-input"
                    @change="updateCoverLetterLength"
                  >
                    <option value="concise">Concise (~150w)</option>
                    <option value="standard">Standard (~300w)</option>
                    <option value="detailed">Detailed (~450w)</option>
                  </select>
                  <span class="preference-field-hint">
                    Word count passed to generation prompt.
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. Application Auto-Archiver Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <Archive :size="18" />
              </div>
              <div class="preference-header-text">
                <div class="preference-header-between">
                  <h4 class="preference-title">Application Auto-Archiver</h4>
                  <label class="switch-toggle" title="Toggle application auto-archiving">
                    <input
                      type="checkbox"
                      :checked="uiStore.autoArchiveEnabled"
                      @change="e => uiStore.setAutoArchiveEnabled(e.target.checked)"
                    />
                    <span class="slider round"></span>
                  </label>
                </div>
                <p class="preference-desc">Moves stale applications in the Applied stage to the Archived tab after a period of inactivity.</p>
              </div>
            </div>

            <div class="preference-body" :class="{ 'is-disabled': !uiStore.autoArchiveEnabled }">
              <div class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">Inactivity Window</label>
                </div>
                <select
                  class="form-input"
                  :value="uiStore.autoArchiveDays"
                  :disabled="!uiStore.autoArchiveEnabled"
                  @change="e => uiStore.setAutoArchiveDays(parseInt(e.target.value))"
                >
                  <option :value="14">14 days</option>
                  <option :value="30">30 days (Recommended)</option>
                  <option :value="45">45 days</option>
                  <option :value="60">60 days</option>
                  <option :value="90">90 days</option>
                </select>
                <span class="preference-field-hint">
                  Active applications with scheduled interviews or pending tasks are never archived.
                </span>
              </div>
            </div>
          </div>

          <!-- 4. Vector Knowledge & Embeddings Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <Cpu :size="18" />
              </div>
              <div class="preference-header-text">
                <div class="preference-header-between">
                  <h4 class="preference-title">Vector Embeddings</h4>
                  <label class="switch-toggle" title="Toggle Vector Embeddings generation">
                    <input
                      type="checkbox"
                      :checked="enableEmbeddings"
                      :disabled="isUpdatingEmbeddings"
                      @change="toggleEmbeddings"
                    />
                    <span class="slider round"></span>
                  </label>
                </div>
                <p class="preference-desc">Dense vector indexing for semantic job matching and search. Disable to speed up intake.</p>
              </div>
            </div>

            <div class="preference-body" :class="{ 'is-disabled': !enableEmbeddings }">
              <div class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">pgvector Index</label>
                </div>
                <button
                  class="btn btn-secondary btn-sm w-full"
                  :disabled="!enableEmbeddings || isReindexingEmbeddings"
                  @click="reindexMissingEmbeddings"
                >
                  <RefreshCw :size="13" :class="{ 'animate-spin': isReindexingEmbeddings }" />
                  <span>{{ isReindexingEmbeddings ? 'Re-indexing Embeddings...' : 'Rebuild Missing Embeddings' }}</span>
                </button>
                <span class="preference-field-hint">
                  Backfills vector embeddings across all existing applications.
                </span>
              </div>
            </div>
          </div>

          <!-- 5. Diagnostics & Telemetry Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <Activity :size="18" />
              </div>
              <div class="preference-header-text">
                <h4 class="preference-title">Diagnostics &amp; Telemetry</h4>
                <p class="preference-desc">Real-time AI pipeline traces, API latency logs, and system execution diagnostics.</p>
              </div>
            </div>
            <div class="preference-body">
              <div class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">System Telemetry</label>
                </div>
                <div class="flex items-center gap-2">
                  <button class="btn btn-primary btn-sm flex-1" @click="$router.push('/diagnostics')">
                    View Dashboard
                  </button>
                  <button class="btn btn-outline btn-sm flex-1" @click="exportDiagnostics" :disabled="isExporting">
                    <Loader2 v-if="isExporting" class="animate-spin" :size="14" />
                    <span v-else>Download Logs</span>
                  </button>
                </div>
                <span class="preference-field-hint">
                  Export bundled JSON logs for offline inspection or troubleshooting.
                </span>
              </div>
            </div>
          </div>

          <!-- 6. Guided Setup & Onboarding Wizard Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <Sparkles :size="18" />
              </div>
              <div class="preference-header-text">
                <h4 class="preference-title">Guided Setup Wizard</h4>
                <p class="preference-desc">Step-by-step assistant for configuring AI providers, candidate CV profile, and system feature flags.</p>
              </div>
            </div>
            <div class="preference-body">
              <div class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">Onboarding Assistant</label>
                </div>
                <button class="btn btn-primary btn-sm w-full" @click="uiStore.openOnboardingWizard()">
                  <Sparkles :size="14" />
                  <span>Launch Setup Wizard</span>
                </button>
                <span class="preference-field-hint">
                  Safely reconfigures preferences without modifying existing application records.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 5: CANDIDATE PROFILE / CV -->
    <div v-else-if="activeTab === 'profile'" class="tab-content animate-fade-in">
      <CandidateProfileView :is-embedded="true" />
    </div>
      </div>
    </div>

    <!-- PROVIDER MODAL -->
    <div v-if="isProviderModalOpen" class="modal-backdrop" @click.self="isProviderModalOpen = false">
      <div class="modal-card animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingProvider ? 'Edit Provider: ' + editingProvider.name : 'Add AI Provider' }}</h3>
          <button class="btn-close" @click="isProviderModalOpen = false">×</button>
        </div>

        <div class="modal-body">
          <div class="input-group">
            <label class="input-label">Provider Name *</label>
            <input v-model="providerForm.name" type="text" placeholder="e.g. Local LM Studio, Anthropic Work" class="form-input" required />
          </div>

          <div class="input-group">
            <label class="input-label">Provider Type *</label>
            <select v-model="providerForm.provider_type" class="form-input" @change="onProviderTypeChange">
              <option value="openai">OpenAI / LM Studio / vLLM (OpenAI-compatible)</option>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="ollama">Ollama</option>
              <option value="google_genai">Google Gemini (GenAI)</option>
              <option value="openrouter">OpenRouter</option>
              <option value="deepseek">DeepSeek</option>
              <option value="custom">Custom Endpoint</option>
            </select>
          </div>

          <div class="input-group">
            <label class="input-label">Base URL</label>
            <input v-model="providerForm.base_url" type="text" placeholder="http://192.168.1.187:1234/v1" class="form-input" />
          </div>

          <div class="input-group">
            <label class="input-label">{{ editingProvider ? 'New API Key (Leave blank to keep unchanged)' : 'API Key (Optional for local)' }}</label>
            <input v-model="providerForm.api_key" type="password" placeholder="lm-studio / sk-..." class="form-input" />
          </div>

          <div class="input-row-2col">
            <div class="input-group">
              <label class="input-label">Input Cost ($ / 1M)</label>
              <div class="rate-input-wrap">
                <span class="rate-prefix">$</span>
                <input
                  v-model.number="providerForm.input_cost_per_million"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  class="form-input rate-input font-mono"
                />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">Output Cost ($ / 1M)</label>
              <div class="rate-input-wrap">
                <span class="rate-prefix">$</span>
                <input
                  v-model.number="providerForm.output_cost_per_million"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  class="form-input rate-input font-mono"
                />
              </div>
            </div>
          </div>

          <!-- Collapsible Standard Model Rates Guide -->
          <div class="rate-guide-accordion mb-3">
            <button
              type="button"
              class="rate-guide-toggle-btn"
              @click="isRateGuideOpen = !isRateGuideOpen"
            >
              <div class="flex items-center gap-1.5 text-xs text-primary font-medium">
                <Sparkles :size="13" />
                <span>Standard Model Rates Reference Guide</span>
              </div>
              <ChevronUp v-if="isRateGuideOpen" :size="13" class="text-muted" />
              <ChevronDown v-else :size="13" class="text-muted" />
            </button>

            <div v-if="isRateGuideOpen" class="rate-guide-content animate-fade-in mt-2">
              <div class="rate-guide-filter-row mb-2 flex items-center justify-between">
                <span class="text-[11px] text-muted">Click any preset to apply $/1M rates:</span>
                <label class="show-all-toggle text-[11px] text-muted flex items-center gap-1 cursor-pointer">
                  <input type="checkbox" v-model="showAllRateGuideProviders" />
                  <span>Show all providers</span>
                </label>
              </div>

              <div class="rate-presets-list">
                <div
                  v-for="(preset, pIdx) in filteredRateGuidePresets"
                  :key="pIdx"
                  class="rate-preset-card"
                  @click="applyRateGuidePreset(preset)"
                >
                  <div class="preset-top">
                    <span class="preset-name font-semibold">{{ preset.name }}</span>
                    <span class="badge badge-applied font-mono text-[10px]">{{ preset.provider }}</span>
                  </div>
                  <div class="preset-bottom font-mono text-xs">
                    <span class="text-primary">${{ preset.inCost.toFixed(2) }} in</span>
                    <span class="text-muted">/</span>
                    <span class="text-primary">${{ preset.outCost.toFixed(2) }} out</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="input-group">
            <div class="label-with-hint">
              <label class="input-label">Max Concurrency Limit</label>
              <span class="text-xs text-muted">Local: 1 | Cloud: 5-10</span>
            </div>
            <input
              v-model.number="providerForm.max_concurrency"
              type="number"
              min="1"
              max="50"
              placeholder="1"
              class="form-input font-mono"
              required
            />
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="isProviderModalOpen = false">Cancel</button>
            <button class="btn btn-primary" @click="saveProvider">{{ editingProvider ? 'Update Provider' : 'Save Provider' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODEL PRICING & BENCHMARK RATES MODAL -->
    <div v-if="isPricingModalOpen" class="modal-backdrop" @click.self="isPricingModalOpen = false">
      <div class="modal-card modal-lg animate-fade-in">
        <div class="modal-header">
          <div class="modal-title-group">
            <h3 class="modal-title flex items-center gap-2">
              <SlidersHorizontal :size="18" class="text-primary" />
              <span>Model Pricing &amp; Benchmark Rates ($ / 1M Tokens)</span>
            </h3>
            <p class="text-xs text-muted mt-1">Configure standard comparison rates used for What-If provider simulations and cloud savings calculations.</p>
          </div>
          <button class="btn-close" @click="isPricingModalOpen = false">×</button>
        </div>

        <div class="modal-body">
          <div class="pricing-modal-toolbar mb-3 flex items-center justify-between gap-3">
            <input
              v-model="pricingSearchQuery"
              type="text"
              placeholder="Search model or provider (e.g. gpt-4o, claude, gemini, local)..."
              class="form-input search-input"
            />
            <button
              class="btn btn-secondary btn-sm flex-shrink-0"
              @click="resetPricingRatesToDefaults"
              :disabled="loadingPricing"
              title="Reset all benchmark rates to standard published defaults"
            >
              <RotateCcw :size="14" />
              <span>Reset Defaults</span>
            </button>
          </div>

          <div class="pricing-table-container">
            <table class="pricing-table">
              <thead>
                <tr>
                  <th>Model / Key</th>
                  <th>Provider</th>
                  <th>Input Cost ($/1M)</th>
                  <th>Output Cost ($/1M)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rate in filteredPricingRates" :key="rate.key">
                  <td class="rate-model-cell">
                    <div class="rate-name font-semibold text-main">{{ rate.display_name || rate.key }}</div>
                    <div class="rate-key font-mono text-xs text-muted">{{ rate.key }}</div>
                  </td>
                  <td>
                    <span class="badge badge-applied font-mono text-xs">{{ rate.provider }}</span>
                  </td>
                  <td>
                    <div class="rate-input-wrap">
                      <span class="rate-prefix">$</span>
                      <input
                        v-model.number="rate.input_cost_per_million"
                        type="number"
                        step="0.01"
                        min="0"
                        class="form-input rate-input font-mono"
                      />
                    </div>
                  </td>
                  <td>
                    <div class="rate-input-wrap">
                      <span class="rate-prefix">$</span>
                      <input
                        v-model.number="rate.output_cost_per_million"
                        type="number"
                        step="0.01"
                        min="0"
                        class="form-input rate-input font-mono"
                      />
                    </div>
                  </td>
                </tr>
                <tr v-if="filteredPricingRates.length === 0">
                  <td colspan="4" class="text-center py-4 text-muted">
                    No models match your search query.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="modal-actions mt-4">
            <button class="btn btn-secondary" @click="isPricingModalOpen = false">Cancel</button>
            <button
              class="btn btn-primary"
              :disabled="isSavingPricing"
              @click="savePricingRates"
            >
              <Loader2 v-if="isSavingPricing" class="animate-spin" :size="14" />
              <Save v-else :size="14" />
              <span>Save Benchmark Rates</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- EMAIL ACCOUNT MODAL (3-STEP WIZARD) -->
    <div v-if="isEmailAccountModalOpen" class="modal-backdrop" @click.self="isEmailAccountModalOpen = false">
      <div class="modal-card modal-lg animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingAccount ? 'Edit Account: ' + editingAccount.name : 'Connect Email Account' }}</h3>
          <button class="btn-close" @click="isEmailAccountModalOpen = false">×</button>
        </div>

        <!-- Stepper Header -->
        <div class="modal-stepper-header">
          <div class="stepper-track">
            <button
              type="button"
              class="stepper-item"
              :class="{
                active: emailModalStep === 1,
                completed: emailModalStep > 1,
                clickable: canNavigateToEmailStep(1)
              }"
              :disabled="!canNavigateToEmailStep(1)"
              @click="goToEmailStep(1)"
            >
              <div class="stepper-circle">
                <Check v-if="emailModalStep > 1" :size="12" />
                <span v-else>1</span>
              </div>
              <span class="stepper-label">1. Provider</span>
            </button>

            <div class="stepper-line" :class="{ completed: emailModalStep > 1 }"></div>

            <button
              type="button"
              class="stepper-item"
              :class="{
                active: emailModalStep === 2,
                completed: emailModalStep > 2,
                clickable: canNavigateToEmailStep(2)
              }"
              :disabled="!canNavigateToEmailStep(2)"
              @click="goToEmailStep(2)"
            >
              <div class="stepper-circle">
                <Check v-if="emailModalStep > 2" :size="12" />
                <span v-else>2</span>
              </div>
              <span class="stepper-label">2. Credentials</span>
            </button>

            <div class="stepper-line" :class="{ completed: emailModalStep > 2 }"></div>

            <button
              type="button"
              class="stepper-item"
              :class="{
                active: emailModalStep === 3,
                completed: emailModalStep === 3 && editingAccount,
                clickable: canNavigateToEmailStep(3)
              }"
              :disabled="!canNavigateToEmailStep(3)"
              @click="goToEmailStep(3)"
            >
              <div class="stepper-circle">
                <span>3</span>
              </div>
              <span class="stepper-label">3. Sync &amp; Folders</span>
            </button>
          </div>
        </div>

        <div class="modal-body">
          <!-- STEP 1: SELECT PROVIDER -->
          <div v-if="emailModalStep === 1" class="step-content animate-fade-in">
            <div class="step-intro-text mb-3">
              <h4 class="text-sm font-semibold text-main mb-0.5">Select Email Service Provider</h4>
              <p class="text-xs text-secondary mb-0">Choose your mail host to automatically load recommended connection settings.</p>
            </div>

            <!-- Provider Presets Grid (5 Cards) -->
            <div class="provider-presets-grid-5 mt-4">
              <button
                v-for="provider in EMAIL_PROVIDER_PRESETS"
                :key="provider.key"
                type="button"
                class="email-provider-card"
                :class="{ active: emailAccountForm.provider_preset === provider.key }"
                @click="onSelectProviderPreset(provider.key)"
              >
                <div class="provider-card-header">
                  <div class="provider-icon-badge">
                    <Mail v-if="provider.key === 'gmail' || provider.key === 'outlook'" :size="20" class="text-primary" />
                    <Server v-else :size="20" class="text-primary" />
                  </div>
                  <span class="provider-auth-badge">{{ provider.badge }}</span>
                </div>

                <div class="provider-card-body">
                  <h4 class="provider-card-title">{{ provider.name }}</h4>
                  <p class="provider-card-desc">{{ provider.desc }}</p>
                </div>

                <div class="provider-card-footer">
                  <div class="selection-radio" :class="{ 'radio-checked': emailAccountForm.provider_preset === provider.key }">
                    <div v-if="emailAccountForm.provider_preset === provider.key" class="radio-inner" />
                  </div>
                  <span class="text-xs font-semibold" :class="emailAccountForm.provider_preset === provider.key ? 'text-primary' : 'text-secondary'">
                    {{ emailAccountForm.provider_preset === provider.key ? 'Selected' : 'Select' }}
                  </span>
                </div>
              </button>
            </div>

            <div class="modal-actions mt-5 flex justify-between">
              <button type="button" class="btn btn-secondary" @click="isEmailAccountModalOpen = false">Cancel</button>
              <button type="button" class="btn btn-primary" @click="emailModalStep = 2">
                <span>Continue to Credentials</span>
                <ArrowRight :size="14" />
              </button>
            </div>
          </div>

          <!-- STEP 2: CREDENTIALS & AUTHENTICATION -->
          <div v-else-if="emailModalStep === 2" class="step-content animate-fade-in">
            <!-- Auth Method Toggle (if Gmail or Outlook) -->
            <div v-if="emailAccountForm.provider_preset === 'gmail' || emailAccountForm.provider_preset === 'outlook'" class="input-group">
              <label class="input-label">Authentication Method</label>
              <div class="auth-method-toggle">
                <button
                  type="button"
                  class="auth-toggle-btn"
                  :class="{ active: emailAccountForm.auth_method === 'oauth' }"
                  @click="onAuthMethodChange('oauth')"
                >
                  <Lock :size="14" />
                  <span>OAuth2 Connect <span class="auth-badge recommended">Recommended</span></span>
                </button>
                <button
                  type="button"
                  class="auth-toggle-btn"
                  :class="{ active: emailAccountForm.auth_method === 'app_password' }"
                  @click="onAuthMethodChange('app_password')"
                >
                  <Key :size="14" />
                  <span>Email &amp; App Password</span>
                </button>
              </div>
            </div>

            <!-- OAuth2 Mode -->
            <template v-if="emailAccountForm.auth_method === 'oauth' && (emailAccountForm.provider_preset === 'gmail' || emailAccountForm.provider_preset === 'outlook')">
              <!-- Authorized Redirect URI Box -->
              <div class="oauth-redirect-box">
                <div class="label-with-hint mb-1">
                  <span class="redirect-uri-label">Authorized Redirect URI (Copy to Console)</span>
                  <button
                    type="button"
                    class="btn-copy-uri"
                    @click="copyRedirectUri(emailAccountForm.provider_preset === 'outlook' ? oauthConfig.microsoft_redirect_uri : oauthConfig.google_redirect_uri)"
                  >
                    <Check v-if="copiedRedirectUri" :size="12" class="text-success" />
                    <Copy v-else :size="12" />
                    <span>{{ copiedRedirectUri ? 'Copied!' : 'Copy URI' }}</span>
                  </button>
                </div>
                <div class="uri-display font-mono">
                  {{ emailAccountForm.provider_preset === 'outlook' ? oauthConfig.microsoft_redirect_uri : oauthConfig.google_redirect_uri }}
                </div>
              </div>

              <!-- Collapsible OAuth Setup Guide -->
              <div class="oauth-guide-card">
                <button
                  type="button"
                  class="guide-toggle-header"
                  @click="showOAuthGuide = !showOAuthGuide"
                >
                  <div class="flex items-center gap-2">
                    <Info :size="14" class="text-primary" />
                    <span class="font-semibold text-xs text-main">
                      {{ emailAccountForm.provider_preset === 'gmail' ? 'Google Cloud OAuth Setup Guide' : 'Microsoft Entra ID / Azure OAuth Setup Guide' }}
                    </span>
                  </div>
                  <component :is="showOAuthGuide ? ChevronUp : ChevronDown" :size="14" class="text-muted" />
                </button>

                <div v-if="showOAuthGuide" class="guide-content animate-fade-in">
                  <ol v-if="emailAccountForm.provider_preset === 'gmail'" class="guide-steps-list">
                    <li>Go to the <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener" class="guide-link">Google Cloud Console <ExternalLink :size="10" /></a> and create or select a project.</li>
                    <li>Enable the <strong>Gmail API</strong> in APIs &amp; Services &gt; Library.</li>
                    <li>In <strong>OAuth consent screen</strong>, select User Type: <em>External</em>, and add the scopes: <code>https://www.googleapis.com/auth/gmail.readonly</code> and <code>https://www.googleapis.com/auth/userinfo.email</code>.</li>
                    <li>In <strong>Credentials</strong>, click <em>Create Credentials</em> &gt; <em>OAuth Client ID</em> (Application type: <strong>Web application</strong>).</li>
                    <li>Add the <strong>Authorized Redirect URI</strong> displayed above, then copy your Client ID and Client Secret below.</li>
                  </ol>

                  <ol v-else class="guide-steps-list">
                    <li>Open the <a href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade" target="_blank" rel="noopener" class="guide-link">Azure Portal / Entra ID <ExternalLink :size="10" /></a> &gt; <strong>App registrations</strong> &gt; <strong>New registration</strong>.</li>
                    <li>Set Supported account types to <em>Accounts in any organizational directory and personal Microsoft accounts</em>.</li>
                    <li>Set Redirect URI Platform to <strong>Web</strong> and paste the Authorized Redirect URI shown above.</li>
                    <li>Under <strong>API permissions</strong>, add Delegated permissions: <code>Mail.Read</code>, <code>User.Read</code>, and <code>offline_access</code>.</li>
                    <li>Under <strong>Certificates &amp; secrets</strong>, generate a new Client Secret and paste the value below.</li>
                  </ol>
                </div>
              </div>

              <!-- OAuth Form Fields -->
              <div class="input-group">
                <label class="input-label">Account Label *</label>
                <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Personal Gmail" class="form-input" required />
              </div>

              <div class="input-group">
                <label class="input-label">OAuth Client ID *</label>
                <input
                  v-model="emailAccountForm.client_id"
                  type="text"
                  :placeholder="emailAccountForm.provider_preset === 'gmail' ? 'e.g. 12345-abc.apps.googleusercontent.com' : 'e.g. 00000000-0000-0000-0000-000000000000'"
                  class="form-input font-mono"
                  required
                />
              </div>

              <div class="input-group">
                <label class="input-label">OAuth Client Secret *</label>
                <div class="input-with-action">
                  <input
                    v-model="emailAccountForm.client_secret"
                    :type="showClientSecret ? 'text' : 'password'"
                    placeholder="Enter client secret"
                    class="form-input font-mono flex-1"
                    required
                  />
                  <button
                    type="button"
                    class="btn-input-action"
                    @click="showClientSecret = !showClientSecret"
                    tabindex="-1"
                  >
                    <component :is="showClientSecret ? EyeOff : Eye" :size="14" />
                  </button>
                </div>
              </div>

              <div class="modal-actions mt-4 flex justify-between">
                <button type="button" class="btn btn-secondary" @click="emailModalStep = 1">
                  <ArrowLeft :size="14" />
                  <span>Back to Providers</span>
                </button>

                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="btn btn-primary"
                    :disabled="isSavingAccount"
                    @click="startOAuthLogin(emailAccountForm.provider_preset)"
                  >
                    <Loader2 v-if="isSavingAccount" class="animate-spin" :size="14" />
                    <Lock v-else :size="14" />
                    <span>Authorize &amp; Set Preferences</span>
                  </button>
                </div>
              </div>
            </template>

            <!-- App Password / Direct IMAP Mode -->
            <template v-else>
              <!-- App Password Callout only for 2FA Gmail / Outlook -->
              <div v-if="emailAccountForm.provider_preset === 'gmail' || emailAccountForm.provider_preset === 'outlook'" class="app-password-callout">
                <Info :size="14" class="text-primary flex-shrink-0 mt-0.5" />
                <div class="text-xs text-secondary leading-relaxed">
                  <span v-if="emailAccountForm.provider_preset === 'gmail'">
                    Google requires an <strong>App Password</strong> if 2-Step Verification is enabled. Generate one at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" class="guide-link">Google Account Security <ExternalLink :size="10" /></a>.
                  </span>
                  <span v-else-if="emailAccountForm.provider_preset === 'outlook'">
                    Microsoft accounts with 2FA require generating an App Password in your Microsoft Account Security settings.
                  </span>
                </div>
              </div>

              <div class="form-grid-2">
                <div class="input-group">
                  <label class="input-label">Account Label *</label>
                  <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Work Mailbox" class="form-input" required />
                </div>

                <div class="input-group">
                  <label class="input-label">Email Address / Login *</label>
                  <input v-model="emailAccountForm.username" type="email" placeholder="user@domain.com" class="form-input" required />
                </div>
              </div>

              <div class="input-group">
                <label class="input-label">App Password / Password *</label>
                <div class="input-with-action">
                  <input
                    v-model="emailAccountForm.app_password"
                    :type="showClientSecret ? 'text' : 'password'"
                    placeholder="••••••••••••••••"
                    class="form-input font-mono flex-1"
                    required
                  />
                  <button
                    type="button"
                    class="btn-input-action"
                    @click="showClientSecret = !showClientSecret"
                    tabindex="-1"
                  >
                    <component :is="showClientSecret ? EyeOff : Eye" :size="14" />
                  </button>
                </div>
              </div>

              <div class="form-grid-2">
                <div class="input-group">
                  <label class="input-label">IMAP Host *</label>
                  <input v-model="emailAccountForm.imap_host" type="text" placeholder="imap.gmail.com" class="form-input font-mono" required />
                </div>

                <div class="input-group">
                  <label class="input-label">IMAP Port *</label>
                  <input v-model.number="emailAccountForm.imap_port" type="number" placeholder="993" class="form-input font-mono" required />
                </div>
              </div>

              <div class="modal-actions mt-4 flex justify-between">
                <button type="button" class="btn btn-secondary" @click="emailModalStep = 1">
                  <ArrowLeft :size="14" />
                  <span>Back to Providers</span>
                </button>
                <button type="button" class="btn btn-primary" :disabled="isSavingAccount" @click="handleStep2NextIMAP">
                  <Loader2 v-if="isSavingAccount" class="animate-spin" :size="14" />
                  <span>Next: Sync &amp; Folders</span>
                  <ArrowRight v-if="!isSavingAccount" :size="14" />
                </button>
              </div>
            </template>
          </div>

          <!-- STEP 3: FOLDER & SYNC PREFERENCES -->
          <div v-else-if="emailModalStep === 3" class="step-content animate-fade-in">
            <!-- Account Connected Banner -->
            <div v-if="editingAccount || createdEmailAccountId" class="account-connected-banner">
              <div class="flex items-center gap-2">
                <CheckCircle2 class="text-success flex-shrink-0" :size="16" />
                <span class="text-xs font-semibold text-main">
                  Connected: {{ emailAccountForm.name }}
                  <span v-if="emailAccountForm.username && emailAccountForm.username !== 'oauth_pending'" class="text-muted font-normal">({{ emailAccountForm.username }})</span>
                </span>
              </div>
              <span class="auth-badge-connected">Ready for Sync</span>
            </div>

            <!-- Target Mailbox Folder -->
            <div class="input-group">
              <div class="label-with-hint mb-1">
                <label class="input-label">Target Mailbox Folder *</label>
                <span class="folder-tip-text">
                  (Tip: Dedicated folder or email prefiltering recommended)
                </span>
              </div>

              <!-- Discovered Folders Dropdown / Custom Input Row -->
              <div class="folder-selection-row">
                <div class="folder-input-wrapper">
                  <select
                    v-if="availableMailFolders.length > 0 && !isCustomFolderMode"
                    v-model="emailAccountForm.folder"
                    class="form-input font-mono w-full"
                  >
                    <option
                      v-for="folder in availableMailFolders"
                      :key="typeof folder === 'object' ? folder.id : folder"
                      :value="typeof folder === 'object' ? folder.id : folder"
                    >
                      {{ typeof folder === 'object' ? folder.path : folder }}
                    </option>
                  </select>

                  <input
                    v-else
                    v-model="emailAccountForm.folder"
                    type="text"
                    placeholder="e.g. INBOX or Jobs"
                    class="form-input font-mono w-full"
                    required
                  />
                </div>

                <button
                  v-if="availableMailFolders.length > 0"
                  type="button"
                  class="btn btn-secondary btn-sm flex-shrink-0"
                  @click="isCustomFolderMode = !isCustomFolderMode; if (!isCustomFolderMode && availableMailFolders.length > 0) emailAccountForm.folder = typeof availableMailFolders[0] === 'object' ? availableMailFolders[0].id : availableMailFolders[0]"
                >
                  <span>{{ isCustomFolderMode ? 'Choose from List' : 'Custom Path' }}</span>
                </button>

                <button
                  type="button"
                  class="btn btn-ghost btn-sm text-secondary flex-shrink-0"
                  :disabled="isLoadingFolders || (!editingAccount && !createdEmailAccountId)"
                  title="Re-scan mailbox folders"
                  @click="fetchEmailFolders(editingAccount?.id || createdEmailAccountId)"
                >
                  <Loader2 v-if="isLoadingFolders" class="animate-spin" :size="14" />
                  <RefreshCw v-else :size="14" />
                </button>
              </div>

              <div v-if="isLoadingFolders" class="flex items-center gap-1.5 text-xs text-primary mt-1">
                <Loader2 class="animate-spin" :size="12" />
                <span>Scanning available mailbox folders...</span>
              </div>

              <p class="field-help-text">
                JobTracker will scan this folder for job application confirmations, interview invitations, and recruiter messages.
              </p>
            </div>

            <!-- Sync Schedule & Frequency Section -->
            <div class="form-grid-2 pt-2 border-t border-subtle">
              <div class="input-group">
                <label class="input-label">Sync Frequency</label>
                <select v-model="emailAccountForm.sync_interval" class="form-input">
                  <option value="15m">Every 15 minutes</option>
                  <option value="30m">Every 30 minutes</option>
                  <option value="1h">Every hour (Recommended)</option>
                  <option value="6h">Every 6 hours</option>
                  <option value="24h">Once a day (Scheduled Time)</option>
                  <option value="WEEKLY">Weekly (Scheduled Day &amp; Time)</option>
                  <option value="MANUAL">Manual Sync Only</option>
                </select>
              </div>

              <!-- Scheduled Day (if weekly) -->
              <div v-if="emailAccountForm.sync_interval === 'WEEKLY'" class="input-group">
                <label class="input-label">Sync Day</label>
                <select v-model="emailAccountForm.sync_schedule_day" class="form-input">
                  <option value="MON">Every Monday</option>
                  <option value="TUE">Every Tuesday</option>
                  <option value="WED">Every Wednesday</option>
                  <option value="THU">Every Thursday</option>
                  <option value="FRI">Every Friday</option>
                  <option value="SAT">Every Saturday</option>
                  <option value="SUN">Every Sunday</option>
                </select>
              </div>

              <!-- Preferred Time (if 24h or WEEKLY) -->
              <div v-if="emailAccountForm.sync_interval === '24h' || emailAccountForm.sync_interval === 'WEEKLY'" class="input-group">
                <label class="input-label">Preferred Sync Time</label>
                <div class="schedule-time-row">
                  <select v-model="emailAccountForm.sync_schedule_hour" class="form-input font-mono flex-1">
                    <option v-for="h in 24" :key="h" :value="String(h - 1).padStart(2, '0')">
                      {{ String(h - 1).padStart(2, '0') }}:00
                    </option>
                  </select>
                  <span class="text-muted font-bold">:</span>
                  <select v-model="emailAccountForm.sync_schedule_min" class="form-input font-mono flex-1">
                    <option value="00">00</option>
                    <option value="15">15</option>
                    <option value="30">30</option>
                    <option value="45">45</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="modal-actions mt-4 flex justify-between">
              <button type="button" class="btn btn-secondary" @click="emailModalStep = 2">
                <ArrowLeft :size="14" />
                <span>Back to Credentials</span>
              </button>
              <button type="button" class="btn btn-primary" :disabled="isSavingAccount" @click="saveEmailAccount">
                <Loader2 v-if="isSavingAccount" class="animate-spin" :size="14" />
                <Save v-else :size="14" />
                <span>{{ editingAccount ? 'Update & Save Settings' : 'Complete Setup & Save' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- DELETE EMAIL ACCOUNT CONFIRMATION MODAL -->
    <div v-if="showDeleteAccountModal" class="modal-backdrop" @click.self="showDeleteAccountModal = false">
      <div class="modal-card modal-sm animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">Remove Mailbox Account</h3>
          <button class="btn-close" @click="showDeleteAccountModal = false">×</button>
        </div>
        <div class="modal-body">
          <p class="text-sm text-main">
            Are you sure you want to remove mailbox <strong>{{ accountToDelete?.name }}</strong>
            <span v-if="accountToDelete?.username" class="text-muted font-normal"> ({{ accountToDelete?.username }})</span>?
          </p>
          <p class="text-xs text-secondary">
            Automated intake and scheduled background syncing for this mailbox will stop immediately.
          </p>
          <div class="modal-actions mt-3">
            <button class="btn btn-secondary" @click="showDeleteAccountModal = false">Cancel</button>
            <button class="btn btn-danger" :disabled="isDeletingAccount" @click="confirmDeleteAccount">
              <Loader2 v-if="isDeletingAccount" class="animate-spin" :size="14" />
              <Trash2 v-else :size="14" />
              <span>{{ isDeletingAccount ? 'Removing...' : 'Remove Mailbox' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- CLEAR ACCOUNT SYNC HISTORY MODAL -->
    <div v-if="showClearAccountModal" class="modal-backdrop" @click.self="showClearAccountModal = false">
      <div class="modal-card modal-sm animate-fade-in">
        <div class="modal-header">
          <div class="modal-title-group">
            <RotateCcw :size="16" class="text-warning flex-shrink-0" />
            <h3 class="modal-title">Clear Email Sync History</h3>
          </div>
          <button class="btn-close" @click="showClearAccountModal = false">×</button>
        </div>
        <div class="modal-body">
          <p class="text-sm text-main">
            Are you sure you want to clear sync history for <strong>{{ accountToClear?.name }}</strong>?
          </p>
          <p class="text-xs text-secondary">
            This removes all recorded deduplication IDs for this mailbox and resets its sync cursor. Subsequent syncs will re-fetch and re-evaluate emails from the mailbox. Existing job applications and timeline events remain untouched.
          </p>
          <div class="modal-actions mt-3">
            <button class="btn btn-secondary" :disabled="isClearingAccount" @click="showClearAccountModal = false">Cancel</button>
            <button class="btn btn-warning" :disabled="isClearingAccount" @click="confirmClearAccountHistory">
              <Loader2 v-if="isClearingAccount" class="animate-spin" :size="14" />
              <RotateCcw v-else :size="14" />
              <span>{{ isClearingAccount ? 'Clearing...' : 'Clear History' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- CLEAR ALL SYNC HISTORY MODAL -->
    <div v-if="showClearAllModal" class="modal-backdrop" @click.self="showClearAllModal = false">
      <div class="modal-card modal-sm animate-fade-in">
        <div class="modal-header">
          <div class="modal-title-group">
            <RotateCcw :size="16" class="text-warning flex-shrink-0" />
            <h3 class="modal-title">Clear All Email Sync History</h3>
          </div>
          <button class="btn-close" @click="showClearAllModal = false">×</button>
        </div>
        <div class="modal-body">
          <p class="text-sm text-main">
            Are you sure you want to clear all email sync history across <strong>all accounts</strong>?
          </p>
          <p class="text-xs text-secondary">
            This removes all email deduplication records from the database and resets sync cursors for all connected mailboxes. Existing applications, notes, and timeline events will not be deleted.
          </p>
          <div class="modal-actions mt-3">
            <button class="btn btn-secondary" :disabled="isClearingAll" @click="showClearAllModal = false">Cancel</button>
            <button class="btn btn-warning" :disabled="isClearingAll" @click="confirmClearAllHistory">
              <Loader2 v-if="isClearingAll" class="animate-spin" :size="14" />
              <RotateCcw v-else :size="14" />
              <span>{{ isClearingAll ? 'Clearing All...' : 'Clear All' }}</span>
            </button>
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
  min-height: calc(100vh - var(--navbar-height));
  background-color: transparent;
  display: block;
}

.page-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 28px;
  gap: 16px;
  padding: 0;
  background-color: transparent;
  border-bottom: none;
}

.header-text-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.page-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 24px;
  color: var(--text-main);
  letter-spacing: var(--font-tracking);
  margin: 0;
  text-align: center;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
  line-height: 1.5;
  max-width: 680px;
  text-align: center;
}

.tab-bar {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 3px;
  margin-top: 0;
  flex-shrink: 0;
  justify-content: center;
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
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-pill:hover {
  color: var(--text-main);
}

.tab-pill.active {
  background-color: var(--bg-elevated);
  color: var(--primary);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.settings-content-area {
  padding: 0;
  width: 100%;
}

.settings-inner-container {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
}

.tab-content {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Studio Layout */
.studio-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
  width: 100%;
}

@media (max-width: 900px) {
  .studio-layout {
    grid-template-columns: 1fr;
  }
}

.studio-sidebar {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
  box-shadow: var(--shadow-sm);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 8px;
}

.sidebar-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
}

.sidebar-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

.task-nav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.task-nav-item:hover {
  background-color: var(--bg-surface-hover);
}

.task-nav-item.active {
  background-color: var(--bg-elevated);
  border-color: var(--border-color);
}

.task-nav-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.task-nav-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.task-nav-key {
  font-size: 10px;
  color: var(--text-muted);
}

/* Studio Workspace */
.studio-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.studio-task-header {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  box-shadow: var(--shadow-sm);
  flex-wrap: nowrap;
}

.task-header-info {
  flex: 1;
  min-width: 0;
}

.studio-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  white-space: nowrap;
}

.autosave-status {
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 9px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  user-select: none;
}

.task-badge-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rec-temp-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-main);
  background-color: var(--bg-main);
  padding: 3px 9px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.rec-reasoning-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--primary);
  background-color: var(--primary-subtle);
  padding: 3px 9px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--primary-glow);
}

.btn-refresh-models {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 11px;
  height: 22px;
  padding: 0 8px;
  line-height: 20px;
  box-sizing: border-box;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-refresh-models:hover:not(:disabled) {
  background-color: var(--bg-elevated);
  color: var(--text-main);
  border-color: var(--border-subtle);
}

.btn-refresh-models:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.task-header-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.task-header-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  max-width: 600px;
}

.studio-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.studio-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.studio-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.studio-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1.3fr 1fr;
  gap: 16px;
  align-items: start;
}

@media (max-width: 900px) {
  .form-grid-3 {
    grid-template-columns: 1fr;
  }
}

.label-with-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 24px;
  min-height: 24px;
  margin-bottom: 6px;
}

.label-with-hint .input-label {
  margin-bottom: 0;
  line-height: 24px;
}

.form-range-container {
  height: 38px;
  display: flex;
  align-items: center;
  width: 100%;
}

.form-grid-2 .form-input,
.form-grid-2 select.form-input {
  height: 38px;
  min-height: 38px;
  max-height: 38px;
  box-sizing: border-box;
}

.reasoning-pills {
  display: flex;
  align-items: center;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 3px;
  height: 38px;
  min-height: 38px;
  max-height: 38px;
  box-sizing: border-box;
  width: 100%;
}

.reasoning-pill {
  flex: 1;
  height: 100%;
  border: none;
  background: transparent;
  padding: 0 4px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  text-transform: capitalize;
  text-align: center;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.reasoning-pill.active {
  background-color: var(--primary);
  color: #fff;
  font-weight: 600;
}

.reasoning-task-guidance {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: var(--radius-xs, 4px);
  padding: 6px 10px;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.reasoning-info-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background-color: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.18);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.model-suggestions-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.suggestions-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
}

.suggestions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.model-chip {
  border: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.model-chip.active {
  border-color: var(--primary);
  background-color: rgba(59, 130, 246, 0.12);
  color: var(--primary);
  font-weight: 600;
}

.placeholders-box {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
}

.placeholder-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.placeholder-tag {
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--primary);
}

.prompt-textarea {
  width: 100%;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 12px;
  color: var(--text-main);
  line-height: 1.5;
  resize: vertical;
}

.prompt-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.studio-test-feedback {
  background-color: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.test-feedback-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-success);
}

.test-feedback-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--text-secondary);
}

/* Providers & Accounts Grid Styles */
.section-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.section-header-text {
  flex: 1;
  min-width: 260px;
}

.section-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.email-sync-toggle-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  padding: 5px 12px;
  border-radius: var(--radius-sm);
}

.sync-status-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.section-header-row h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.section-header-row p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.section-header-row .btn {
  flex-shrink: 0;
}

.providers-grid, .accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.provider-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.account-card:hover {
  border-color: var(--border-color-hover);
}

.provider-header, .account-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.provider-title-group, .account-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.account-icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background-color: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.account-name-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.account-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.provider-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.account-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  background-color: var(--bg-main);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.meta-k {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
}

.meta-v {
  color: var(--text-main);
  text-align: right;
  font-size: 11px;
  word-break: break-all;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.provider-actions, .account-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: auto;
}

.btn-sync-action {
  flex: 1;
  justify-content: center;
}

.provider-test-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
  color: var(--status-offer-text);
  font-size: 12px;
}

.provider-test-pill.is-error {
  background-color: var(--status-rejected-bg);
  border-color: var(--status-rejected-border);
  color: var(--status-rejected-text);
}

.provider-test-pill.is-warning {
  background-color: var(--status-interview-bg);
  border-color: var(--status-interview-border);
  color: var(--status-interview-text);
}

/* Preferences Grid & Background Customizer */
.preferences-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
  margin-top: 16px;
  align-items: stretch;
}

.swatches-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.swatches-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.swatches-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.swatch-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.swatch-btn:hover {
  border-color: var(--border-focus);
}

.swatch-btn.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-subtle);
}

.swatch-preview {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid var(--border-subtle);
}

.swatch-name {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
  text-align: center;
}

.custom-color-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

.color-input-picker {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: transparent;
  cursor: pointer;
  padding: 2px;
  box-sizing: border-box;
}

.color-input-picker::-webkit-color-swatch-wrapper {
  padding: 0;
}

.color-input-picker::-webkit-color-swatch {
  border-radius: 3px;
  border: none;
}

.preference-card-wide {
  grid-column: 1 / -1;
}

.preference-header-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 24px;
}

.preference-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-sizing: border-box;
}

.preference-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 64px;
}

.preference-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle);
  flex-shrink: 0;
  margin-top: 1px;
}

.preference-header-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.preference-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 24px;
}

.preference-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-top: 4px;
  margin-bottom: 0;
}

.preference-body {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  flex: 1;
  transition: opacity 0.2s ease, filter 0.2s ease;
}

.preference-body .input-group {
  margin-bottom: 0;
}

.cover-letter-pref-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

@media (max-width: 480px) {
  .cover-letter-pref-grid {
    grid-template-columns: 1fr;
  }
}

.preference-body.is-disabled {
  opacity: 0.42;
  pointer-events: none;
  filter: grayscale(0.5);
  user-select: none;
}

.preference-field-hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 6px;
  display: block;
  line-height: 1.4;
}

.btn-xs {
  padding: 3px 8px;
  font-size: 11px;
  height: 24px;
  gap: 4px;
}

.view-mode-toggle-row {
  display: flex;
  gap: 8px;
}

.view-mode-option {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
}

.view-mode-option.active {
  border-color: var(--primary);
  background-color: rgba(59, 130, 246, 0.12);
  color: var(--primary);
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
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
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
}

.modal-card.modal-lg {
  max-width: 580px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.btn-close {
  border: none;
  background: transparent;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.label-with-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-input {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 9px 12px;
  font-size: 13px;
  color: var(--text-main);
}

.form-input:focus {
  outline: none;
  border-color: var(--primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.provider-presets-grid-5 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

@media (max-width: 600px) {
  .provider-presets-grid-5 {
    grid-template-columns: 1fr;
  }
}

.email-provider-card {
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  border-radius: var(--radius-md);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast, 0.15s ease);
}

.email-provider-card:hover {
  border-color: var(--border-focus);
  background-color: var(--bg-surface);
}

.email-provider-card.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
  box-shadow: 0 0 0 1px var(--primary-glow);
}

.provider-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.provider-icon-badge {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.provider-auth-badge {
  font-size: 9px;
  font-weight: 700;
  color: var(--primary);
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  padding: 2px 6px;
  border-radius: 4px;
}

.provider-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.provider-card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.3;
}

.provider-card-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 0;
}

.provider-card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.selection-radio {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast, 0.15s ease);
}

.selection-radio.radio-checked {
  border-color: var(--primary);
}

.radio-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--primary);
}

.auth-method-toggle {
  display: flex;
  gap: 6px;
}

.auth-toggle-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
}

.auth-toggle-btn.active {
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}

.auth-badge.recommended {
  background-color: var(--status-interview-text);
  color: #000;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
}

/* Email Modal Stepper Bar */
.modal-stepper-header {
  padding: 14px 20px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

.stepper-track {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 440px;
  margin: 0 auto;
}

.stepper-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: none;
  padding: 0;
  cursor: default;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.stepper-item.clickable {
  cursor: pointer;
}

.stepper-item.clickable:hover .stepper-label {
  color: var(--text-main);
}

.stepper-circle {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.stepper-item.active .stepper-circle {
  background-color: var(--primary);
  border-color: var(--primary);
  color: #fff;
  box-shadow: 0 0 8px var(--primary-glow);
}

.stepper-item.completed .stepper-circle {
  background-color: rgba(16, 185, 129, 0.15);
  border-color: var(--success, #10b981);
  color: var(--success, #10b981);
}

.stepper-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.stepper-item.active .stepper-label {
  color: var(--text-main);
  font-weight: 700;
}

.stepper-item.completed .stepper-label {
  color: var(--text-secondary);
}

.stepper-line {
  flex: 1;
  height: 2px;
  background-color: var(--border-color);
  margin: 0 12px;
  transition: all var(--transition-fast);
}

.stepper-line.completed {
  background-color: var(--success, #10b981);
}

.account-connected-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}

.auth-badge-connected {
  font-size: 10px;
  font-weight: 700;
  color: var(--success, #10b981);
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 1px 6px;
  border-radius: 4px;
}

.folder-tip-text {
  font-size: 10px;
  color: var(--text-muted);
  font-style: italic;
}

.folder-selection-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.folder-input-wrapper {
  flex: 1;
  min-width: 0;
}

.schedule-time-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-help-text {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 2px 0 0 0;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 13px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.empty-desc {
  max-width: 480px;
  line-height: 1.5;
  color: var(--text-secondary);
  font-size: 12px;
}

/* OAuth & Modal Specific Controls */
.oauth-redirect-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.redirect-uri-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.btn-copy-uri {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-copy-uri:hover {
  background-color: var(--bg-elevated);
  border-color: var(--primary);
  color: var(--primary);
}

.uri-display {
  font-size: 11px;
  color: var(--primary);
  word-break: break-all;
  user-select: all;
  background-color: var(--bg-surface);
  padding: 6px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  margin-top: 4px;
}

.oauth-guide-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-main);
  overflow: hidden;
}

.guide-toggle-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.guide-toggle-header:hover {
  background-color: var(--bg-surface);
}

.guide-content {
  padding: 10px 14px 14px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--bg-surface);
}

.guide-steps-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.guide-steps-list code {
  font-family: monospace;
  font-size: 10px;
  background-color: var(--bg-main);
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--text-main);
  border: 1px solid var(--border-color);
}

.guide-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.guide-link:hover {
  color: var(--primary-hover, #60a5fa);
}

.input-with-action {
  display: flex;
  align-items: center;
  position: relative;
}

.btn-input-action {
  position: absolute;
  right: 6px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
}

.btn-input-action:hover {
  color: var(--text-main);
  background-color: var(--bg-surface);
}

.app-password-callout {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background-color: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 10px;
}

@media (max-width: 600px) {
  .form-grid-2, .form-grid-3 {
    grid-template-columns: 1fr;
  }
}

.global-hero-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 0;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  width: 100%;
}

.global-hero-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.hero-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.hero-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.global-hero-content {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.global-hero-content.empty {
  color: var(--text-muted);
  font-style: italic;
  font-size: 13px;
}

.global-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-val {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.stat-val.highlight {
  color: var(--primary);
}

.advanced-overrides-section {
  margin-top: 0;
  margin-bottom: 0;
}

.advanced-toggle-btn {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
}

.advanced-toggle-btn:hover {
  background-color: var(--bg-surface);
  border-color: var(--primary-subtle);
}

.advanced-toggle-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.accordion-icon {
  transition: transform 0.3s ease;
}

.accordion-icon.rotated {
  transform: rotate(180deg);
}

.accordion-fade-enter-active,
.accordion-fade-leave-active {
  transition: all 0.3s ease;
  max-height: 2000px;
  overflow: hidden;
}

.accordion-fade-enter-from,
.accordion-fade-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
}

.advanced-overrides-content {
  margin-top: 16px;
}

.use-global-checkbox {
  background-color: rgba(59, 130, 246, 0.05);
  border: 1px solid var(--primary-subtle);
  border-radius: var(--radius-sm);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.custom-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.checkbox-hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin-left: 24px;
}

.global-hero-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.threshold-slider-control {
  height: 38px;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.cover-letter-control-card,
.embeddings-control-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 24px;
  width: 100%;
}

.advanced-overrides-section {
  margin-top: 0;
  margin-bottom: 0;
  width: 100%;
}

.cover-letter-control-header,
.embeddings-control-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.cover-letter-title-group,
.embeddings-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 38px;
  width: 100%;
}

.cover-letter-slider {
  flex: 1;
  min-width: 0;
}

.threshold-badge {
  font-family: var(--font-mono, monospace);
  font-size: 13px;
  font-weight: 600;
  color: var(--primary);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  min-width: 48px;
  text-align: center;
  flex-shrink: 0;
  box-sizing: border-box;
}

.pref-status-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  width: 100%;
  box-sizing: border-box;
}

.pref-status-text {
  font-size: 11.5px;
  line-height: 1.4;
  color: var(--text-secondary);
}

/* Switch Toggle Component */
.switch-toggle {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  transition: 0.3s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: var(--text-muted);
  transition: 0.3s;
}

input:checked + .slider {
  background-color: var(--primary);
  border-color: var(--primary);
}

input:checked + .slider:before {
  transform: translateX(20px);
  background-color: #ffffff;
}

.slider.round {
  border-radius: 24px;
}

.slider.round:before {
  border-radius: 50%;
}

.inherited-model-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-main);
}

.email-disabled-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background-color: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 12px;
  color: var(--text-secondary);
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.opacity-50 {
  opacity: 0.5;
}
.pointer-events-none {
  pointer-events: none;
}
.mt-3 {
  margin-top: 16px;
}
.mb-4 {
  margin-bottom: 20px;
}

/* Probe Result Box */
.probe-result-box {
  background-color: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}

.probe-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.probe-result-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.probe-details-grid {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.probe-detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.probe-detail-label {
  color: var(--text-muted);
}

.probe-detail-val {
  font-weight: 600;
}

.probe-notes {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* RESPONSIVE ADAPTATIONS */
@media (max-width: 767px) {
  .page-container {
    padding: 16px 12px 60px;
  }

  .tab-bar {
    overflow-x: auto;
    white-space: nowrap;
    flex-wrap: nowrap;
    justify-content: flex-start;
    width: 100%;
    max-width: 100vw;
    padding: 4px;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }

  .tab-bar::-webkit-scrollbar {
    display: none;
  }

  .tab-pill {
    flex-shrink: 0;
    min-height: 40px;
    padding: 8px 12px;
  }

  .global-hero-card {
    padding: 16px 12px;
  }

  .global-hero-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .studio-task-header {
    flex-direction: column;
    align-items: flex-start;
    padding: 14px 12px;
    gap: 12px;
  }

  .form-grid-2, .form-grid-3 {
    grid-template-columns: 1fr;
  }

  .reasoning-pills {
    overflow-x: auto;
    white-space: nowrap;
    justify-content: flex-start;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 2px;
  }

  .reasoning-pills::-webkit-scrollbar {
    display: none;
  }

  .reasoning-pill {
    flex-shrink: 0;
    min-width: 68px;
    padding: 0 8px;
  }

  .providers-grid, .accounts-grid, .preferences-grid {
    grid-template-columns: 1fr;
  }

  .section-header-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .section-header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .modal-card, .modal-card.modal-lg {
    max-width: 95vw;
    width: 95vw;
    max-height: 90dvh;
    overflow-y: auto;
  }

  .stepper-track {
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .stepper-item {
    flex-shrink: 0;
  }

  .switch-toggle {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
  }

  .form-input, select.form-input {
    font-size: 16px; /* Prevents auto-zoom on iOS */
    min-height: 44px;
  }

  .btn {
    min-height: 44px;
  }

  .btn-sm, .btn-xs {
    min-height: 38px;
  }
}

/* Token Usage & Cost Overview Styles */
.usage-overview-card {
  background: var(--bg-card, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}

.usage-title-badge-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.pulse-dot-green {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10b981;
  display: inline-block;
  box-shadow: 0 0 8px #10b981;
}

.usage-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.usage-metric-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
  border-radius: var(--radius-md, 8px);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.usage-metric-label {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-muted, #94a3b8);
  display: flex;
  align-items: center;
  gap: 6px;
}

.usage-metric-val {
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--text-main, #f8fafc);
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.usage-sub-tokens {
  font-size: 0.85rem;
  font-weight: normal;
}

.usage-metric-footer {
  font-size: 0.78rem;
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Provider Cost Comparison Drawer Styles */
.provider-comparison-drawer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}

.comparison-drawer-header {
  margin-bottom: 12px;
}

.comparison-heading {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-main, #f8fafc);
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.comparison-sub {
  font-size: 0.8rem;
  color: var(--text-muted, #94a3b8);
  margin-top: 4px;
}

.comparison-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 8px);
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.comparison-table th {
  background: var(--bg-surface, #0f172a);
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: var(--text-muted, #94a3b8);
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
}

.comparison-table td {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.comparison-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.highlight-active-row {
  background: rgba(16, 185, 129, 0.06) !important;
}

/* Rate Guide Accordion in Provider Modal */
.rate-guide-accordion {
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--border-color, rgba(255, 255, 255, 0.12));
  border-radius: var(--radius-md, 8px);
  padding: 10px 12px;
}

.rate-guide-toggle-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}

.rate-presets-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin-top: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.rate-preset-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-sm, 6px);
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rate-preset-card:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}

.preset-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.preset-name {
  font-size: 0.78rem;
  color: var(--text-main, #f8fafc);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preset-bottom {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
}

.rate-input-wrap {
  display: flex;
  align-items: center;
  position: relative;
  width: 100%;
}

.rate-prefix {
  position: absolute;
  left: 10px;
  color: var(--text-muted, #94a3b8);
  font-family: monospace;
  font-size: 0.85rem;
  pointer-events: none;
}

.rate-input {
  padding-left: 22px !important;
}

/* Pricing & Benchmark Rates Modal Styles */
.pricing-table-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 8px);
}

.pricing-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
}

.pricing-table th {
  background: var(--bg-surface, #0f172a);
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: var(--text-muted, #94a3b8);
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  position: sticky;
  top: 0;
  z-index: 1;
}

.pricing-table td {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.pricing-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.rate-model-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
