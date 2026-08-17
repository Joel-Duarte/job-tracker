<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { AIConfigAPI, EmailAccountsAPI, IntakeAPI, PromptsAPI } from '../api/endpoints'
import {
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
  Sun,
  Moon,
  Palette,
  Kanban,
  Table as TableIcon,
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
  Copy,
  Eye,
  EyeOff,
  Info,
  BookOpen,
} from 'lucide-vue-next'

const uiStore = useUIStore()

const activeTab = ref('studio') // 'studio' | 'providers' | 'email_accounts' | 'preferences'

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
  return bindings.value.find(b => b.task_type === 'GLOBAL_DEFAULT') || null
})
const isAdvancedOpen = ref(false)

const TASKS = [
  {
    key: 'GLOBAL_DEFAULT',
    promptKey: null,
    label: 'Global Default Model',
    icon: 'Globe',
    recommendedTemp: 0.2,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    hasPrompt: false,
    desc: 'The master fallback model used across all standard inference tasks.',
    variables: [],
    hidden: computed(() => true)
  },
  {
    key: 'JD_EXTRACTION',
    promptKey: 'jd_extraction',
    label: 'Job Spec Web Extraction',
    icon: 'Briefcase',
    recommendedTemp: 0.0,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    hasPrompt: true,
    desc: 'Extracts structured job title, company, salary, and requirements from scraped web HTML / markdown.',
    variables: ['{raw_webpage_data}']
  },
  {
    key: 'EXTRACTION',
    promptKey: 'email_extraction',
    label: 'Email Metadata Extraction',
    icon: 'Mail',
    recommendedTemp: 0.1,
    recommendedReasoning: 'none',
    recommendedMaxTokens: null,
    hasPrompt: true,
    desc: 'Parses job details, dates, companies, and roles from emails into structured Pydantic schemas.',
    variables: ['{email_content}']
  },
  {
    key: 'ASSESSMENT',
    promptKey: 'assessment',
    label: 'Pre-Screen Match Audit & Tips',
    icon: 'Sparkles',
    recommendedTemp: 0.2,
    recommendedReasoning: 'medium',
    recommendedMaxTokens: null,
    hasPrompt: true,
    desc: 'Computes deep semantic fit score, keyword matches/gaps, and strategic resume improvement suggestions.',
    variables: ['{job_description}', '{candidate_cv}', '{programmatic_baseline}']
  },
  {
    key: 'cv_anonymization',
    promptKey: 'cv_anonymization',
    label: 'CV De-Identification & Skills',
    icon: 'ShieldCheck',
    recommendedTemp: 0.2,
    recommendedReasoning: 'medium',
    recommendedMaxTokens: null,
    hasPrompt: true,
    desc: 'Replaces companies with scale tags, transforms date windows into durations, and extracts canonical technical skills.',
    variables: ['{resume_text}']
  },
  {
    key: 'AGENT_REASONING',
    promptKey: 'agent_system',
    label: 'LangGraph Reasoning & Assistant',
    icon: 'Bot',
    recommendedTemp: 0.5,
    recommendedReasoning: 'high',
    recommendedMaxTokens: null,
    hasPrompt: true,
    desc: 'Evaluates fuzzy deduplication confidence and powers the interactive chat assistant.',
    variables: []
  },
  {
    key: 'INTERVIEW_GUIDE',
    promptKey: 'interview_guide',
    label: 'Interview Prep Guide',
    icon: 'BookOpen',
    recommendedTemp: 0.4,
    recommendedReasoning: 'high',
    recommendedMaxTokens: null,
    hasPrompt: true,
    desc: 'Generates tailored interview preparation guides, STAR stories, and strategic question defenses.',
    variables: ['{language}', '{company_name}', '{position}', '{company_context}', '{jd_text}', '{cv_text}', '{target_section}']
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
    hasPrompt: false,
    desc: 'Generates 768-dimension dense vector representations for pgvector cosine similarity search.',
    variables: []
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
  reasoning_effort: 'none', // 'none' | 'low' | 'medium' | 'high'
  max_tokens: null,
  embedding_dimensions: 768,
  prompt_template: '',
})

// Sync studio form with selected task
function syncStudioForm() {
  const taskKey = selectedTaskKey.value
  const taskDef = activeTaskDef.value

  // 1. Find existing binding
  const existingBinding = bindings.value.find(
    (b) => b.task_type.toUpperCase() === taskKey.toUpperCase()
  )

  if (taskKey !== 'GLOBAL_DEFAULT' && taskKey !== 'EMBEDDING' && !existingBinding) {
    studioForm.value.use_global_default = true;
  } else {
    studioForm.value.use_global_default = false;
  }

  const defaultTemp = typeof taskDef.recommendedTemp === 'number' ? taskDef.recommendedTemp : 0.2
  const chosenProviderId = existingBinding?.provider_id || (providers.value[0]?.id || null)

  studioForm.value.provider_id = chosenProviderId
  studioForm.value.model_name = existingBinding?.model_name || (taskKey === 'EMBEDDING' ? 'nomic-embed-text' : 'qwen3.5-4b')
  studioForm.value.temperature = existingBinding?.temperature !== undefined ? existingBinding.temperature : defaultTemp
  studioForm.value.reasoning_effort = existingBinding?.reasoning_effort || existingBinding?.extra_kwargs?.reasoning_effort || taskDef.recommendedReasoning || 'none'
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
}

function selectStudioSuggestedModel(modelId) {
  studioForm.value.model_name = modelId
}

async function saveStudioTask() {
  isSavingStudio.value = true
  const taskKey = selectedTaskKey.value
  const taskDef = activeTaskDef.value

  try {
    // 1. Save Model Binding
    await AIConfigAPI.setBinding(taskKey, {
      provider_id: studioForm.value.provider_id,
      model_name: studioForm.value.model_name.trim(),
      temperature: studioForm.value.temperature,
      reasoning_effort: studioForm.value.reasoning_effort,
      max_tokens: studioForm.value.max_tokens ? Number(studioForm.value.max_tokens) : undefined,
      embedding_dimensions: taskKey === 'EMBEDDING' ? studioForm.value.embedding_dimensions : undefined,
      extra_kwargs: {
        reasoning_effort: studioForm.value.reasoning_effort,
      },
    })

    // 2. Save Prompt Template if applicable
    if (taskDef.hasPrompt && taskDef.promptKey && studioForm.value.prompt_template) {
      await PromptsAPI.update(taskDef.promptKey, studioForm.value.prompt_template)
    }

    uiStore.showToast(`Task '${taskDef.label}' configuration saved!`, 'success')
    await loadBindings()
    await loadPrompts()
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save task configuration', 'error')
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
    studioForm.value.temperature = typeof taskDef.recommendedTemp === 'number' ? taskDef.recommendedTemp : 0.2
    studioForm.value.reasoning_effort = taskDef.recommendedReasoning || 'none'
    studioForm.value.max_tokens = null
    if (taskKey === 'EMBEDDING') {
      studioForm.value.embedding_dimensions = 768
      studioForm.value.model_name = 'nomic-embed-text'
    }

    if (taskDef.hasPrompt && taskDef.promptKey) {
      const res = await PromptsAPI.reset(taskDef.promptKey)
      studioForm.value.prompt_template = res.data.template
      await loadPrompts()
    }

    uiStore.showToast(`Task '${taskDef.label}' reset to recommended defaults (click Save to persist)`, 'info')
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
    uiStore.showToast(`Prompt '${taskDef.label}' reset to factory defaults`, 'info')
    await loadPrompts()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isResettingPrompt.value = false
  }
}

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
    base_url: 'http://192.168.1.187:1234/v1',
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

async function startOAuthLogin(providerName) {
  try {
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
    } else {
      uiStore.showToast(res.data.message || 'No OAuth credentials configured.', 'info')
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to initiate OAuth', 'error')
  }
}

function openAddEmailAccountModal() {
  loadOAuthConfig()
  editingAccount.value = null
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
}

async function saveEmailAccount() {
  isSavingAccount.value = true
  try {
    const payload = {
      name: emailAccountForm.value.name.trim(),
      auth_type: emailAccountForm.value.auth_type,
      username: emailAccountForm.value.username.trim(),
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

    if (editingAccount.value) {
      await EmailAccountsAPI.update(editingAccount.value.id, payload)
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

onMounted(async () => {
  window.addEventListener('message', async (event) => {
    if (event.data?.type === 'oauth_success') {
      uiStore.showToast('Mailbox OAuth connected successfully!', 'success')
      isEmailAccountModalOpen.value = false
      await loadEmailAccounts()
    }
  })

  await Promise.all([
    loadProviders(),
    loadBindings(),
    loadPrompts(),
    loadEmailAccounts(),
    loadOAuthConfig(),
  ])
  syncStudioForm()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-text-center">
        <h1 class="page-title">AI &amp; System Settings</h1>
        <p class="page-subtitle">
          Configure model bindings, thinking/reasoning parameters, custom prompt templates, AI providers, and email integrations.
        </p>
      </div>

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
          :class="{ active: activeTab === 'preferences' }"
          @click="activeTab = 'preferences'"
        >
          <SlidersHorizontal :size="15" />
          <span>Preferences</span>
        </button>
      </div>
    </div>

    <!-- Scrollable Content Area with Stable Gutter -->
    <div class="settings-content-area">
      <div class="settings-inner-container">
        <!-- TAB 1: UNIFIED TASK STUDIO -->
        <div v-if="activeTab === 'studio'" class="tab-content animate-fade-in">

          <!-- GLOBAL DEFAULT HERO -->
          <div class="global-hero-card">
            <div class="global-hero-header">
              <div class="hero-title-group">
                <Globe class="text-primary" :size="24" />
                <div>
                  <h2 class="hero-title">Global Default Model</h2>
                  <p class="hero-desc">The primary AI model used across all standard pipelines unless explicitly overridden.</p>
                </div>
              </div>
              <button class="btn btn-outline btn-sm" @click="selectStudioTask('GLOBAL_DEFAULT'); isAdvancedOpen = true">
                <Edit3 :size="14" />
                <span>Change Global Model</span>
              </button>
            </div>

            <div class="global-hero-content" v-if="globalBinding">
              <div class="global-stat">
                <span class="stat-label">Provider</span>
                <span class="stat-val">{{ globalBinding.provider_type }} ({{ globalBinding.provider_name }})</span>
              </div>
              <div class="global-stat">
                <span class="stat-label">Model Name</span>
                <span class="stat-val highlight">{{ globalBinding.model_name }}</span>
              </div>
              <div class="global-stat">
                <span class="stat-label">Temperature</span>
                <span class="stat-val">{{ globalBinding.temperature }}</span>
              </div>
            </div>
            <div class="global-hero-content empty" v-else>
              <span>No global default configured. System will fallback to legacy .env settings.</span>
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
                  v-if="bindings.find(b => b.task_type.toUpperCase() === t.key.toUpperCase())"
                  class="task-bound-indicator"
                  title="Configured in AI Registry"
                >
                  <CheckCircle2 :size="12" class="text-success" />
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

            <div class="studio-header-actions">
              <button
                class="btn btn-ghost btn-sm text-secondary"
                :disabled="isResettingPrompt"
                @click="resetStudioTaskToDefaults"
                title="Reset parameters and prompt back to task recommendations"
              >
                <RotateCcw :size="14" />
                <span>Reset to Defaults</span>
              </button>

              <button
                class="btn btn-primary btn-sm"
                :disabled="isSavingStudio"
                @click="saveStudioTask"
              >
                <Loader2 v-if="isSavingStudio" class="animate-spin" :size="14" />
                <Save v-else :size="14" />
                <span>Save Configuration</span>
              </button>
            </div>
          </div>

          <!-- Section 1: Model & Execution Binding -->
          <div class="studio-card">
            <div class="studio-card-title">
              <BrainCircuit :size="16" class="text-primary" />
              <span>Model &amp; Execution Binding</span>
            </div>

            <div v-if="selectedTaskKey !== 'GLOBAL_DEFAULT' && selectedTaskKey !== 'EMBEDDING'" class="use-global-checkbox mb-4">
              <label class="custom-checkbox">
                <input type="checkbox" v-model="studioForm.use_global_default" />
                <span class="checkmark"></span>
                <span class="checkbox-label">Use Global Default Model</span>
              </label>
              <p class="checkbox-hint">If checked, this task will fall back to the Global Default model configured above.</p>
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

                <input
                  v-model="studioForm.model_name"
                  type="text"
                  placeholder="e.g. gpt-4o, claude-3-7-sonnet, deepseek-r1"
                  class="form-input font-mono"
                  required
                />
              </div>
            </div>

            <!-- Curated / Discovered Models Quick Pick Chips -->
            <div v-if="studioProviderModels.length" class="model-suggestions-box">
              <span class="suggestions-label">Discovered / Available Models on Provider:</span>
              <div class="suggestions-list">
                <button
                  v-for="m in studioProviderModels"
                  :key="m.id"
                  type="button"
                  class="model-chip font-mono"
                  :class="{ active: studioForm.model_name === m.id }"
                  @click="studioForm.model_name = m.id"
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
                      v-for="effort in ['none', 'low', 'medium', 'high']"
                      :key="effort"
                      type="button"
                      class="reasoning-pill font-mono"
                      :class="{ active: studioForm.reasoning_effort === effort }"
                      @click="studioForm.reasoning_effort = effort"
                    >
                      {{ effort === 'none' ? 'None (Fast)' : effort }}
                    </button>
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
                  />
                </div>
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
      <div class="section-card">
        <div class="section-header-row">
          <div>
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
        <div class="section-header-row">
          <div>
            <h3>Connected Mailboxes &amp; Sync Schedule</h3>
            <p>Connect mailboxes via 1-Click OAuth (Google / Microsoft) or IMAP, and configure automated background sync schedules.</p>
          </div>
          <button class="btn btn-primary btn-sm" @click="openAddEmailAccountModal">
            <Plus :size="15" />
            <span>Connect Account</span>
          </button>
        </div>

        <div class="accounts-grid">
          <div v-for="acc in emailAccounts" :key="acc.id" class="account-card">
            <div class="account-card-header">
              <div class="account-title-row">
                <Mail :size="16" class="text-primary" />
                <span class="account-name">{{ acc.name }}</span>
              </div>
              <span class="badge badge-applied font-mono">{{ acc.auth_type }}</span>
            </div>

            <div class="account-card-body">
              <div class="meta-row">
                <span class="meta-k">Username:</span>
                <span class="meta-v font-mono">{{ acc.username }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-k">Folder:</span>
                <span class="meta-v font-mono">{{ acc.folder }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-k">Sync Interval:</span>
                <span class="meta-v font-mono">{{ acc.sync_interval || '1h' }}</span>
              </div>
            </div>

            <div class="account-actions">
              <button
                class="btn btn-primary btn-sm"
                :disabled="syncingAccount === acc.id"
                @click="triggerSync(acc)"
              >
                <Loader2 v-if="syncingAccount === acc.id" class="animate-spin" :size="14" />
                <RefreshCw v-else :size="14" />
                <span>{{ syncingAccount === acc.id ? 'Syncing...' : 'Sync Now' }}</span>
              </button>

              <button class="btn btn-secondary btn-sm" @click="openEditEmailAccountModal(acc)">
                <Edit3 :size="14" />
                <span>Edit</span>
              </button>

              <button class="btn btn-danger btn-sm" @click="openDeleteAccountModal(acc)">
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
          <p>Configure default currency for offers and salaries, interface view mode, and appearance settings.</p>
        </div>

        <div class="preferences-grid">
          <!-- Currency Setting Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <DollarSign :size="18" />
              </div>
              <div>
                <h4 class="preference-title">Default System Currency</h4>
                <p class="preference-desc">Used as the default currency for salary inputs, offer packages, and compensation ranges.</p>
              </div>
            </div>

            <div class="currency-chips-grid">
              <button
                v-for="c in uiStore.SUPPORTED_CURRENCIES"
                :key="c.code"
                type="button"
                class="currency-chip"
                :class="{ active: uiStore.defaultCurrency === c.code }"
                @click="uiStore.setDefaultCurrency(c.code)"
              >
                <span class="chip-code">{{ c.code }}</span>
                <span class="chip-symbol">{{ c.symbol }}</span>
              </button>
            </div>
          </div>

          <!-- View Mode Setting Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <Globe :size="18" />
              </div>
              <div>
                <h4 class="preference-title">Default Pipeline View</h4>
                <p class="preference-desc">Choose whether the pipeline launches in Kanban board or tabular data table view.</p>
              </div>
            </div>

            <div class="view-mode-toggle-row">
              <button
                type="button"
                class="view-mode-option"
                :class="{ active: uiStore.viewMode === 'kanban' }"
                @click="uiStore.setViewMode('kanban')"
              >
                <Kanban :size="16" />
                <span>Kanban Board</span>
              </button>
              <button
                type="button"
                class="view-mode-option"
                :class="{ active: uiStore.viewMode === 'table' }"
                @click="uiStore.setViewMode('table')"
              >
                <TableIcon :size="16" />
                <span>Data Table</span>
              </button>
            </div>
          </div>

          <!-- Appearance Theme Setting Card -->
          <div class="preference-card">
            <div class="preference-header">
              <div class="preference-icon text-primary">
                <Palette :size="18" />
              </div>
              <div>
                <h4 class="preference-title">Interface Appearance Theme</h4>
                <p class="preference-desc">Switch between the refined dark slate Midnight theme and the warm studio Daylight theme.</p>
              </div>
            </div>

            <div class="view-mode-toggle-row">
              <button
                type="button"
                class="view-mode-option"
                :class="{ active: uiStore.theme === 'midnight' }"
                @click="uiStore.setTheme('midnight')"
              >
                <Moon :size="16" />
                <span>Midnight (Dark Slate)</span>
              </button>
              <button
                type="button"
                class="view-mode-option"
                :class="{ active: uiStore.theme === 'daylight' }"
                @click="uiStore.setTheme('daylight')"
              >
                <Sun :size="16" />
                <span>Daylight (Warm Studio)</span>
              </button>
            </div>
          </div>

          <!-- Theme Palette Customizer Studio Card -->
          <div class="preference-card preference-card-wide">
            <div class="preference-header-between">
              <div class="preference-header">
                <div class="preference-icon text-primary">
                  <Palette :size="18" />
                </div>
                <div>
                  <h4 class="preference-title">Theme Palette Customizer Studio</h4>
                  <p class="preference-desc">
                    Customize background, surfaces, primary accents, and border colors for <strong>{{ uiStore.theme === 'midnight' ? 'Midnight (Dark)' : 'Daylight (Light)' }}</strong> theme.
                  </p>
                </div>
              </div>

              <button
                type="button"
                class="btn btn-ghost btn-xs text-secondary"
                title="Reset all colors for active theme to factory defaults"
                @click="uiStore.resetAllCustomColors(uiStore.theme)"
              >
                <RotateCcw :size="13" />
                <span>Reset All Palette Colors</span>
              </button>
            </div>

            <div class="theme-customizer-grid">
              <!-- 1. Canvas Background -->
              <div class="customizer-subcard">
                <div class="subcard-header">
                  <span class="subcard-title">1. Canvas Background</span>
                  <span class="subcard-token font-mono text-xs text-muted">--bg-app</span>
                </div>

                <!-- Swatches -->
                <div v-if="uiStore.theme === 'midnight'" class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customDarkBg || uiStore.customDarkBg === '#000000' }"
                    title="Pure OLED Black (Default)"
                    @click="uiStore.resetCustomColor('midnight', 'bg')"
                  >
                    <span class="swatch-preview" style="background-color: #000000;"></span>
                    <span class="swatch-name">OLED Black (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkBg === '#12161f' }"
                    title="Slate Gunmetal"
                    @click="uiStore.setCustomColor('midnight', 'bg', '#12161f')"
                  >
                    <span class="swatch-preview" style="background-color: #12161f;"></span>
                    <span class="swatch-name">Gunmetal</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkBg === '#0a1120' }"
                    title="Midnight Navy"
                    @click="uiStore.setCustomColor('midnight', 'bg', '#0a1120')"
                  >
                    <span class="swatch-preview" style="background-color: #0a1120;"></span>
                    <span class="swatch-name">Navy</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkBg === '#0b0f19' }"
                    title="Deep Charcoal"
                    @click="uiStore.setCustomColor('midnight', 'bg', '#0b0f19')"
                  >
                    <span class="swatch-preview" style="background-color: #0b0f19;"></span>
                    <span class="swatch-name">Charcoal</span>
                  </button>
                </div>
                <div v-else class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customLightBg || uiStore.customLightBg === '#e5ded1' }"
                    title="Muted Stone (Default)"
                    @click="uiStore.resetCustomColor('daylight', 'bg')"
                  >
                    <span class="swatch-preview" style="background-color: #e5ded1;"></span>
                    <span class="swatch-name">Muted Stone (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightBg === '#ede7dc' }"
                    title="Darker Alabaster"
                    @click="uiStore.setCustomColor('daylight', 'bg', '#ede7dc')"
                  >
                    <span class="swatch-preview" style="background-color: #ede7dc;"></span>
                    <span class="swatch-name">Alabaster</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightBg === '#faf8f5' }"
                    title="Warm Studio Cream"
                    @click="uiStore.setCustomColor('daylight', 'bg', '#faf8f5')"
                  >
                    <span class="swatch-preview" style="background-color: #faf8f5;"></span>
                    <span class="swatch-name">Warm Cream</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightBg === '#ffffff' }"
                    title="Pure Paper White"
                    @click="uiStore.setCustomColor('daylight', 'bg', '#ffffff')"
                  >
                    <span class="swatch-preview" style="background-color: #ffffff;"></span>
                    <span class="swatch-name">Paper White</span>
                  </button>
                </div>

                <!-- Custom Picker Row -->
                <div class="custom-color-row">
                  <input
                    type="color"
                    class="color-input-picker"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBg || '#000000') : (uiStore.customLightBg || '#e5ded1')"
                    @input="e => uiStore.setCustomColor(uiStore.theme, 'bg', e.target.value)"
                  />
                  <input
                    type="text"
                    class="form-input font-mono input-sm"
                    placeholder="#HEX"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBg || '#000000') : (uiStore.customLightBg || '#E5DED1')"
                    @change="e => uiStore.setCustomColor(uiStore.theme, 'bg', e.target.value)"
                  />
                  <button
                    type="button"
                    class="btn btn-ghost btn-xs text-secondary"
                    title="Reset to default"
                    @click="uiStore.resetCustomColor(uiStore.theme, 'bg')"
                  >
                    <RotateCcw :size="12" />
                  </button>
                </div>
              </div>

              <!-- 2. Cards & Menu Surfaces -->
              <div class="customizer-subcard">
                <div class="subcard-header">
                  <span class="subcard-title">2. Card &amp; Menu Surfaces</span>
                  <span class="subcard-token font-mono text-xs text-muted">--bg-card / surface</span>
                </div>

                <!-- Swatches -->
                <div v-if="uiStore.theme === 'midnight'" class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customDarkSurface || uiStore.customDarkSurface === '#11151e' }"
                    title="Deep Obsidian (Default)"
                    @click="uiStore.resetCustomColor('midnight', 'surface')"
                  >
                    <span class="swatch-preview" style="background-color: #11151e;"></span>
                    <span class="swatch-name">Obsidian (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkSurface === '#1a212e' }"
                    title="Slate Gunmetal"
                    @click="uiStore.setCustomColor('midnight', 'surface', '#1a212e')"
                  >
                    <span class="swatch-preview" style="background-color: #1a212e;"></span>
                    <span class="swatch-name">Gunmetal</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkSurface === '#1e2738' }"
                    title="Steel Cavity"
                    @click="uiStore.setCustomColor('midnight', 'surface', '#1e2738')"
                  >
                    <span class="swatch-preview" style="background-color: #1e2738;"></span>
                    <span class="swatch-name">Steel</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkSurface === '#161922' }"
                    title="Solid Onyx"
                    @click="uiStore.setCustomColor('midnight', 'surface', '#161922')"
                  >
                    <span class="swatch-preview" style="background-color: #161922;"></span>
                    <span class="swatch-name">Onyx</span>
                  </button>
                </div>
                <div v-else class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customLightSurface || uiStore.customLightSurface === '#f7f4ee' }"
                    title="Parchment (Default)"
                    @click="uiStore.resetCustomColor('daylight', 'surface')"
                  >
                    <span class="swatch-preview" style="background-color: #f7f4ee;"></span>
                    <span class="swatch-name">Parchment (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightSurface === '#ffffff' }"
                    title="Pastier Crisp White"
                    @click="uiStore.setCustomColor('daylight', 'surface', '#ffffff')"
                  >
                    <span class="swatch-preview" style="background-color: #ffffff;"></span>
                    <span class="swatch-name">White</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightSurface === '#fcfbf8' }"
                    title="Soft Sand"
                    @click="uiStore.setCustomColor('daylight', 'surface', '#fcfbf8')"
                  >
                    <span class="swatch-preview" style="background-color: #fcfbf8;"></span>
                    <span class="swatch-name">Soft Sand</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightSurface === '#f2ede4' }"
                    title="Warm Canvas"
                    @click="uiStore.setCustomColor('daylight', 'surface', '#f2ede4')"
                  >
                    <span class="swatch-preview" style="background-color: #f2ede4;"></span>
                    <span class="swatch-name">Warm Canvas</span>
                  </button>
                </div>

                <!-- Custom Picker Row -->
                <div class="custom-color-row">
                  <input
                    type="color"
                    class="color-input-picker"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkSurface || '#11151e') : (uiStore.customLightSurface || '#f7f4ee')"
                    @input="e => uiStore.setCustomColor(uiStore.theme, 'surface', e.target.value)"
                  />
                  <input
                    type="text"
                    class="form-input font-mono input-sm"
                    placeholder="#HEX"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkSurface || '#11151E') : (uiStore.customLightSurface || '#F7F4EE')"
                    @change="e => uiStore.setCustomColor(uiStore.theme, 'surface', e.target.value)"
                  />
                  <button
                    type="button"
                    class="btn btn-ghost btn-xs text-secondary"
                    title="Reset to default"
                    @click="uiStore.resetCustomColor(uiStore.theme, 'surface')"
                  >
                    <RotateCcw :size="12" />
                  </button>
                </div>
              </div>

              <!-- 3. Primary Accent Color -->
              <div class="customizer-subcard">
                <div class="subcard-header">
                  <span class="subcard-title">3. Primary Accent Color</span>
                  <span class="subcard-token font-mono text-xs text-primary">--primary</span>
                </div>

                <!-- Swatches -->
                <div v-if="uiStore.theme === 'midnight'" class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customDarkPrimary || uiStore.customDarkPrimary === '#2dd4bf' }"
                    title="Emerald Cyan (Default)"
                    @click="uiStore.resetCustomColor('midnight', 'primary')"
                  >
                    <span class="swatch-preview" style="background-color: #2dd4bf;"></span>
                    <span class="swatch-name">Emerald (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkPrimary === '#38bdf8' }"
                    title="Electric Sky Blue"
                    @click="uiStore.setCustomColor('midnight', 'primary', '#38bdf8')"
                  >
                    <span class="swatch-preview" style="background-color: #38bdf8;"></span>
                    <span class="swatch-name">Sky Blue</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkPrimary === '#3b82f6' }"
                    title="Cobalt Blue"
                    @click="uiStore.setCustomColor('midnight', 'primary', '#3b82f6')"
                  >
                    <span class="swatch-preview" style="background-color: #3b82f6;"></span>
                    <span class="swatch-name">Cobalt</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkPrimary === '#fbbf24' }"
                    title="Amber Gold"
                    @click="uiStore.setCustomColor('midnight', 'primary', '#fbbf24')"
                  >
                    <span class="swatch-preview" style="background-color: #fbbf24;"></span>
                    <span class="swatch-name">Amber Gold</span>
                  </button>
                </div>
                <div v-else class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customLightPrimary || uiStore.customLightPrimary === '#854d0e' }"
                    title="Saddle Umber (Default)"
                    @click="uiStore.resetCustomColor('daylight', 'primary')"
                  >
                    <span class="swatch-preview" style="background-color: #854d0e;"></span>
                    <span class="swatch-name">Saddle (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightPrimary === '#b45309' }"
                    title="Warm Cognac"
                    @click="uiStore.setCustomColor('daylight', 'primary', '#b45309')"
                  >
                    <span class="swatch-preview" style="background-color: #b45309;"></span>
                    <span class="swatch-name">Cognac</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightPrimary === '#c2410c' }"
                    title="Terracotta Bronze"
                    @click="uiStore.setCustomColor('daylight', 'primary', '#c2410c')"
                  >
                    <span class="swatch-preview" style="background-color: #c2410c;"></span>
                    <span class="swatch-name">Terracotta</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightPrimary === '#ca8a04' }"
                    title="Rich Ochre"
                    @click="uiStore.setCustomColor('daylight', 'primary', '#ca8a04')"
                  >
                    <span class="swatch-preview" style="background-color: #ca8a04;"></span>
                    <span class="swatch-name">Ochre</span>
                  </button>
                </div>

                <!-- Custom Picker Row -->
                <div class="custom-color-row">
                  <input
                    type="color"
                    class="color-input-picker"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkPrimary || '#2dd4bf') : (uiStore.customLightPrimary || '#854d0e')"
                    @input="e => uiStore.setCustomColor(uiStore.theme, 'primary', e.target.value)"
                  />
                  <input
                    type="text"
                    class="form-input font-mono input-sm"
                    placeholder="#HEX"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkPrimary || '#2DD4BF') : (uiStore.customLightPrimary || '#854D0E')"
                    @change="e => uiStore.setCustomColor(uiStore.theme, 'primary', e.target.value)"
                  />
                  <button
                    type="button"
                    class="btn btn-ghost btn-xs text-secondary"
                    title="Reset to default"
                    @click="uiStore.resetCustomColor(uiStore.theme, 'primary')"
                  >
                    <RotateCcw :size="12" />
                  </button>
                </div>
              </div>

              <!-- 4. Borders & Dividers -->
              <div class="customizer-subcard">
                <div class="subcard-header">
                  <span class="subcard-title">4. Borders &amp; Dividers</span>
                  <span class="subcard-token font-mono text-xs text-muted">--border-color</span>
                </div>

                <!-- Swatches -->
                <div v-if="uiStore.theme === 'midnight'" class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customDarkBorder || uiStore.customDarkBorder === '#1c2534' }"
                    title="Deep Edge (Default)"
                    @click="uiStore.resetCustomColor('midnight', 'border')"
                  >
                    <span class="swatch-preview" style="background-color: #1c2534;"></span>
                    <span class="swatch-name">Deep Edge (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkBorder === '#263245' }"
                    title="Gunmetal Crisp Border"
                    @click="uiStore.setCustomColor('midnight', 'border', '#263245')"
                  >
                    <span class="swatch-preview" style="background-color: #263245;"></span>
                    <span class="swatch-name">Gunmetal</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkBorder === '#303e55' }"
                    title="Subtle Steel"
                    @click="uiStore.setCustomColor('midnight', 'border', '#303e55')"
                  >
                    <span class="swatch-preview" style="background-color: #303e55;"></span>
                    <span class="swatch-name">Subtle Steel</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customDarkBorder === '#334155' }"
                    title="Muted Slate"
                    @click="uiStore.setCustomColor('midnight', 'border', '#334155')"
                  >
                    <span class="swatch-preview" style="background-color: #334155;"></span>
                    <span class="swatch-name">Muted Slate</span>
                  </button>
                </div>
                <div v-else class="swatches-grid">
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: !uiStore.customLightBorder || uiStore.customLightBorder === '#b8aa97' }"
                    title="Soft Ochre (Default)"
                    @click="uiStore.resetCustomColor('daylight', 'border')"
                  >
                    <span class="swatch-preview" style="background-color: #b8aa97;"></span>
                    <span class="swatch-name">Soft Ochre (Def)</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightBorder === '#d8cfc2' }"
                    title="Alabaster Stone"
                    @click="uiStore.setCustomColor('daylight', 'border', '#d8cfc2')"
                  >
                    <span class="swatch-preview" style="background-color: #d8cfc2;"></span>
                    <span class="swatch-name">Stone</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightBorder === '#c7bcaa' }"
                    title="Subtle Umber"
                    @click="uiStore.setCustomColor('daylight', 'border', '#c7bcaa')"
                  >
                    <span class="swatch-preview" style="background-color: #c7bcaa;"></span>
                    <span class="swatch-name">Subtle Umber</span>
                  </button>
                  <button
                    type="button"
                    class="swatch-btn"
                    :class="{ active: uiStore.customLightBorder === '#e4ddd2' }"
                    title="Warm Sand Line"
                    @click="uiStore.setCustomColor('daylight', 'border', '#e4ddd2')"
                  >
                    <span class="swatch-preview" style="background-color: #e4ddd2;"></span>
                    <span class="swatch-name">Warm Sand</span>
                  </button>
                </div>

                <!-- Custom Picker Row -->
                <div class="custom-color-row">
                  <input
                    type="color"
                    class="color-input-picker"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBorder || '#1c2534') : (uiStore.customLightBorder || '#b8aa97')"
                    @input="e => uiStore.setCustomColor(uiStore.theme, 'border', e.target.value)"
                  />
                  <input
                    type="text"
                    class="form-input font-mono input-sm"
                    placeholder="#HEX"
                    :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBorder || '#1C2534') : (uiStore.customLightBorder || '#B8AA97')"
                    @change="e => uiStore.setCustomColor(uiStore.theme, 'border', e.target.value)"
                  />
                  <button
                    type="button"
                    class="btn btn-ghost btn-xs text-secondary"
                    title="Reset to default"
                    @click="uiStore.resetCustomColor(uiStore.theme, 'border')"
                  >
                    <RotateCcw :size="12" />
                  </button>
                </div>
              </div>
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
            <select v-model="providerForm.provider_type" class="form-input">
              <option value="openai">OpenAI / LM Studio / vLLM (OpenAI-compatible)</option>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="ollama">Ollama</option>
              <option value="google_genai">Google Gemini (GenAI)</option>
              <option value="openrouter">OpenRouter</option>
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

    <!-- EMAIL ACCOUNT MODAL -->
    <div v-if="isEmailAccountModalOpen" class="modal-backdrop" @click.self="isEmailAccountModalOpen = false">
      <div class="modal-card modal-lg animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingAccount ? 'Edit Account: ' + editingAccount.name : 'Connect Email Account' }}</h3>
          <button class="btn-close" @click="isEmailAccountModalOpen = false">×</button>
        </div>

        <div class="modal-body">
          <!-- Step 1: Provider Presets -->
          <div class="input-group">
            <label class="input-label">Select Email Provider</label>
            <div class="provider-presets-grid">
              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'gmail' }"
                @click="onProviderPresetChange('gmail')"
              >
                <div class="preset-icon gmail-icon"><Mail :size="18" /></div>
                <div class="preset-info">
                  <span class="preset-name">Google Gmail</span>
                  <span class="preset-sub">OAuth2 or App Password</span>
                </div>
              </button>

              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'outlook' }"
                @click="onProviderPresetChange('outlook')"
              >
                <div class="preset-icon outlook-icon"><Mail :size="18" /></div>
                <div class="preset-info">
                  <span class="preset-name">Microsoft Outlook</span>
                  <span class="preset-sub">MS Graph OAuth2 or IMAP</span>
                </div>
              </button>

              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'custom' }"
                @click="onProviderPresetChange('custom')"
              >
                <div class="preset-icon imap-icon"><Server :size="18" /></div>
                <div class="preset-info">
                  <span class="preset-name">Custom IMAP</span>
                  <span class="preset-sub">iCloud, Fastmail, Yahoo</span>
                </div>
              </button>
            </div>
          </div>

          <!-- Step 2: Auth Method Toggle (if Gmail or Outlook) -->
          <div v-if="emailAccountForm.provider_preset !== 'custom'" class="input-group">
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

          <!-- OAuth2 Mode Fields & Guide -->
          <template v-if="emailAccountForm.auth_method === 'oauth' && emailAccountForm.provider_preset !== 'custom'">
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
                  <li>
                    Go to the <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener" class="guide-link">Google Cloud Console <ExternalLink :size="10" /></a> and create or select a project.
                  </li>
                  <li>Enable the <strong>Gmail API</strong> in APIs &amp; Services &gt; Library.</li>
                  <li>In <strong>OAuth consent screen</strong>, select User Type: <em>External</em>, and add the scopes: <code>https://www.googleapis.com/auth/gmail.readonly</code> and <code>https://www.googleapis.com/auth/userinfo.email</code>.</li>
                  <li>In <strong>Credentials</strong>, click <em>Create Credentials</em> &gt; <em>OAuth Client ID</em> (Application type: <strong>Web application</strong>).</li>
                  <li>Add the <strong>Authorized Redirect URI</strong> displayed above, then copy your Client ID and Client Secret below.</li>
                </ol>

                <ol v-else class="guide-steps-list">
                  <li>
                    Open the <a href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade" target="_blank" rel="noopener" class="guide-link">Azure Portal / Entra ID <ExternalLink :size="10" /></a> &gt; <strong>App registrations</strong> &gt; <strong>New registration</strong>.
                  </li>
                  <li>Set Supported account types to <em>Accounts in any organizational directory and personal Microsoft accounts</em>.</li>
                  <li>Set Redirect URI Platform to <strong>Web</strong> and paste the Authorized Redirect URI shown above.</li>
                  <li>Under <strong>API permissions</strong>, add Delegated permissions: <code>Mail.Read</code>, <code>User.Read</code>, and <code>offline_access</code>.</li>
                  <li>Under <strong>Certificates &amp; secrets</strong>, generate a new Client Secret and paste the value below.</li>
                </ol>
              </div>
            </div>

            <!-- OAuth Form Fields -->
            <div class="form-grid-2">
              <div class="input-group">
                <label class="input-label">Account Label *</label>
                <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Personal Gmail" class="form-input" required />
              </div>

              <div class="input-group">
                <label class="input-label">Sync Interval</label>
                <select v-model="emailAccountForm.sync_interval" class="form-input">
                  <option value="15m">Every 15 minutes</option>
                  <option value="30m">Every 30 minutes</option>
                  <option value="1h">Every hour (Recommended)</option>
                  <option value="6h">Every 6 hours</option>
                  <option value="24h">Once a day</option>
                  <option value="MANUAL">Manual Sync Only</option>
                </select>
              </div>
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

            <div class="input-group">
              <div class="label-with-hint">
                <label class="input-label">Email Address</label>
                <span class="text-xs text-muted">Auto-resolved upon OAuth login</span>
              </div>
              <input
                v-model="emailAccountForm.username"
                type="email"
                placeholder="Optional (populated automatically on sign in)"
                class="form-input"
              />
            </div>

            <div class="modal-actions mt-4">
              <button class="btn btn-secondary" @click="isEmailAccountModalOpen = false">Cancel</button>
              <button class="btn btn-secondary" :disabled="isSavingAccount" @click="saveEmailAccount">
                <Save :size="14" />
                <span>Save Credentials</span>
              </button>
              <button class="btn btn-primary" @click="startOAuthLogin(emailAccountForm.provider_preset)">
                <Lock :size="14" />
                <span>Authorize &amp; Connect Mailbox</span>
              </button>
            </div>
          </template>

          <!-- App Password / Direct IMAP Mode -->
          <template v-else>
            <div class="app-password-callout">
              <Info :size="14" class="text-primary flex-shrink-0 mt-0.5" />
              <div class="text-xs text-secondary leading-relaxed">
                <span v-if="emailAccountForm.provider_preset === 'gmail'">
                  Google requires an <strong>App Password</strong> if 2-Step Verification is enabled. Generate one at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" class="guide-link">Google Account Security <ExternalLink :size="10" /></a>.
                </span>
                <span v-else-if="emailAccountForm.provider_preset === 'outlook'">
                  Microsoft accounts with 2FA require generating an App Password in your Microsoft Account Security settings.
                </span>
                <span v-else>
                  Enter your standard IMAP host, port (default 993 SSL), and mailbox credentials.
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

            <div class="form-grid-3">
              <div class="input-group">
                <label class="input-label">IMAP Host *</label>
                <input v-model="emailAccountForm.imap_host" type="text" placeholder="imap.gmail.com" class="form-input font-mono" required />
              </div>

              <div class="input-group">
                <label class="input-label">IMAP Port *</label>
                <input v-model.number="emailAccountForm.imap_port" type="number" placeholder="993" class="form-input font-mono" required />
              </div>

              <div class="input-group">
                <label class="input-label">Mailbox Folder *</label>
                <input v-model="emailAccountForm.folder" type="text" placeholder="INBOX" class="form-input font-mono" required />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">Sync Interval</label>
              <select v-model="emailAccountForm.sync_interval" class="form-input">
                <option value="15m">Every 15 minutes</option>
                <option value="30m">Every 30 minutes</option>
                <option value="1h">Every hour (Recommended)</option>
                <option value="6h">Every 6 hours</option>
                <option value="24h">Once a day</option>
                <option value="MANUAL">Manual Sync Only</option>
              </select>
            </div>

            <div class="modal-actions mt-4">
              <button class="btn btn-secondary" @click="isEmailAccountModalOpen = false">Cancel</button>
              <button class="btn btn-primary" :disabled="isSavingAccount" @click="saveEmailAccount">
                <Save :size="14" />
                <span>{{ editingAccount ? 'Update Account' : 'Save & Connect Account' }}</span>
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--navbar-height));
  background-color: var(--bg-app);
  overflow: hidden;
  padding: 0;
  max-width: none;
  margin: 0;
}

.page-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 22px 24px 16px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 14px;
  margin-bottom: 0;
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
  font-size: 22px;
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
  padding: 5px 12px;
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
  flex: 1;
  overflow-y: scroll;
  scrollbar-gutter: stable;
  padding: 24px;
}

.settings-inner-container {
  max-width: 1240px;
  margin: 0 auto;
  width: 100%;
}

/* Studio Layout */
.studio-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
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
  gap: 16px;
  box-shadow: var(--shadow-sm);
  flex-wrap: wrap;
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
}

.form-range {
  width: 100%;
  accent-color: var(--primary);
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.section-header-row > div {
  flex: 1;
  min-width: 260px;
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
  margin-top: 2px;
}

.providers-grid, .accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.provider-card, .account-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.provider-body, .account-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.meta-k {
  color: var(--text-muted);
}

.meta-v {
  color: var(--text-main);
  text-align: right;
  word-break: break-all;
}

.provider-actions, .account-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 4px;
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
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-top: 16px;
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
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 4px;
}

.theme-customizer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 4px;
}

.customizer-subcard {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.subcard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.subcard-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
}

.subcard-token {
  font-size: 10px;
}

.input-sm {
  max-width: 120px;
  height: 34px;
  padding: 4px 8px;
  font-size: 12px;
  text-transform: uppercase;
}

.preference-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preference-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.preference-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.preference-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-top: 2px;
}

.currency-chips-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.currency-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  border-radius: 4px;
  cursor: pointer;
}

.currency-chip.active {
  border-color: var(--primary);
  background-color: rgba(59, 130, 246, 0.12);
}

.chip-code {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
}

.chip-symbol {
  font-size: 11px;
  color: var(--primary);
  font-family: monospace;
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

.input-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.input-label {
  font-size: 11px;
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
  padding: 8px 10px;
  font-size: 12px;
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

.provider-presets-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.provider-preset-card {
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  border-radius: var(--radius-sm);
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 6px;
  cursor: pointer;
}

.provider-preset-card.active {
  border-color: var(--primary);
  background-color: rgba(59, 130, 246, 0.08);
}

.preset-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
}

.preset-sub {
  font-size: 9px;
  color: var(--text-muted);
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
</style>

<style scoped>
.global-hero-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
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
  border-left: 2px solid var(--primary-subtle);
  padding-left: 16px;
  margin-left: 4px;
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
</style>
