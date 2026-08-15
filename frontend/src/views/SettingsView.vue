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
const loadingStudioModels = ref(false)
const isSavingStudio = ref(false)
const isResettingPrompt = ref(false)
const testingStudioTask = ref(false)
const studioTestResult = ref(null)

const TASKS = [
  {
    key: 'JD_EXTRACTION',
    promptKey: 'jd_extraction',
    label: 'Job Spec Web Extraction',
    icon: 'Briefcase',
    recommendedTemp: 0.0,
    hasPrompt: true,
    desc: 'Extracts structured job title, company, salary, and requirements from scraped web HTML / markdown.',
    variables: ['{raw_webpage_data}']
  },
  {
    key: 'EXTRACTION',
    promptKey: 'email_extraction',
    label: 'Email Metadata Extraction',
    icon: 'Mail',
    recommendedTemp: 0.2,
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
    hasPrompt: true,
    desc: 'Replaces companies with scale tags, transforms date windows into durations, and extracts canonical technical skills.',
    variables: ['{resume_text}']
  },
  {
    key: 'AGENT_REASONING',
    promptKey: 'agent_system',
    label: 'LangGraph Reasoning & Assistant',
    icon: 'Bot',
    recommendedTemp: 0.2,
    hasPrompt: true,
    desc: 'Evaluates fuzzy deduplication confidence and powers the interactive chat assistant.',
    variables: []
  },
  {
    key: 'SUMMARIZATION',
    promptKey: 'summarization',
    label: 'Timeline Narrative Synthesizer',
    icon: 'Layers',
    recommendedTemp: 0.1,
    hasPrompt: true,
    desc: 'Synthesizes chronologies and status updates into cohesive narrative snapshots for semantic vector search.',
    variables: ['{events_str}']
  },
  {
    key: 'SCRAPER_PARSER',
    promptKey: null,
    label: 'Stealth Scraper DOM Parser',
    icon: 'Globe',
    recommendedTemp: 0.0,
    hasPrompt: false,
    desc: 'Parses raw Camoufox DOM captures into structured job spec markdown.',
    variables: []
  },
  {
    key: 'EMBEDDING',
    promptKey: null,
    label: 'Vector Embeddings (pgvector)',
    icon: 'Cpu',
    recommendedTemp: '768 dims',
    hasPrompt: false,
    desc: 'Generates 768-dimension dense vector representations for pgvector cosine similarity search.',
    variables: []
  },
]

// Current active task definition
const activeTaskDef = computed(() => {
  return TASKS.find((t) => t.key === selectedTaskKey.value) || TASKS[0]
})

// Unified form for currently selected task
const studioForm = ref({
  provider_id: null,
  model_name: '',
  temperature: 0.2,
  reasoning_effort: 'none', // 'none' | 'low' | 'medium' | 'high'
  max_tokens: 2000,
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

  const defaultTemp = typeof taskDef.recommendedTemp === 'number' ? taskDef.recommendedTemp : 0.2
  const chosenProviderId = existingBinding?.provider_id || (providers.value[0]?.id || null)

  studioForm.value.provider_id = chosenProviderId
  studioForm.value.model_name = existingBinding?.model_name || (taskKey === 'EMBEDDING' ? 'nomic-embed-text' : 'qwen3.5-4b')
  studioForm.value.temperature = existingBinding?.temperature !== undefined ? existingBinding.temperature : defaultTemp
  studioForm.value.reasoning_effort = existingBinding?.reasoning_effort || existingBinding?.extra_kwargs?.reasoning_effort || 'none'
  studioForm.value.max_tokens = existingBinding?.max_tokens || 2000
  studioForm.value.embedding_dimensions = existingBinding?.embedding_dimensions || (taskKey === 'EMBEDDING' ? 768 : null)

  // 2. Find prompt template if task supports prompts
  if (taskDef.promptKey) {
    const promptRecord = promptsList.value.find((p) => p.name.toLowerCase() === taskDef.promptKey.toLowerCase())
    studioForm.value.prompt_template = promptRecord?.template || ''
  } else {
    studioForm.value.prompt_template = ''
  }

  studioTestResult.value = null
  fetchStudioModels(chosenProviderId)
}

function selectStudioTask(taskKey) {
  selectedTaskKey.value = taskKey
  syncStudioForm()
}

async function fetchStudioModels(providerId) {
  if (!providerId) {
    studioProviderModels.value = []
    return
  }
  loadingStudioModels.value = true
  try {
    const res = await AIConfigAPI.getProviderModels(providerId)
    studioProviderModels.value = res.data?.models || []
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
      max_tokens: studioForm.value.max_tokens || undefined,
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

async function testStudioTask() {
  testingStudioTask.value = true
  studioTestResult.value = null
  const taskKey = selectedTaskKey.value

  try {
    const res = await AIConfigAPI.testBinding(taskKey)
    studioTestResult.value = res.data
    uiStore.showToast(`Task connectivity probe verified for '${activeTaskDef.value.label}'!`, 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Probe execution failed', 'error')
  } finally {
    testingStudioTask.value = false
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
    providerTestResults.value[provider.id] = res.data
    uiStore.showToast(`Provider '${provider.name}' connection verified!`, 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
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
      <div>
        <h1 class="page-title">AI & System Settings</h1>
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

    <!-- TAB 1: UNIFIED TASK STUDIO -->
    <div v-if="activeTab === 'studio'" class="tab-content animate-fade-in">
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
              class="task-nav-item"
              :class="{ active: selectedTaskKey === t.key }"
              @click="selectStudioTask(t.key)"
            >
              <div class="task-nav-left">
                <span class="task-nav-name">{{ t.label }}</span>
                <span class="task-nav-key font-mono">{{ t.key }}</span>
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
                <span class="badge badge-applied font-mono">{{ activeTaskDef.key }}</span>
                <span class="rec-temp-chip">
                  <Thermometer :size="11" />
                  <span>Recommended: {{ activeTaskDef.recommendedTemp }}</span>
                </span>
              </div>
              <h2 class="task-header-title">{{ activeTaskDef.label }}</h2>
              <p class="task-header-desc">{{ activeTaskDef.desc }}</p>
            </div>

            <div class="studio-header-actions">
              <button
                class="btn btn-secondary btn-sm"
                :disabled="testingStudioTask"
                @click="testStudioTask"
                title="Test current model binding and probe response"
              >
                <Loader2 v-if="testingStudioTask" class="animate-spin" :size="14" />
                <Play v-else :size="14" />
                <span>Test Probe</span>
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

            <div class="form-grid-2">
              <div class="input-group">
                <label class="input-label">AI Provider *</label>
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
                  <span v-if="loadingStudioModels" class="text-xs text-muted font-mono flex items-center gap-1">
                    <Loader2 class="animate-spin" :size="11" /> Discovering models...
                  </span>
                </div>
                <input
                  v-model="studioForm.model_name"
                  type="text"
                  placeholder="e.g. qwen3.5-4b, claude-3-5-sonnet-20241022"
                  class="form-input font-mono"
                  required
                />
              </div>
            </div>

            <!-- Discovered Model Suggestions Chips -->
            <div v-if="studioProviderModels.length > 0" class="model-suggestions-box">
              <span class="suggestions-label">Auto-Discovered Provider Models:</span>
              <div class="suggestions-list">
                <button
                  v-for="m in studioProviderModels"
                  :key="m.id"
                  type="button"
                  class="model-chip font-mono"
                  :class="{ active: studioForm.model_name === m.id, discovered: m.is_discovered }"
                  @click="selectStudioSuggestedModel(m.id)"
                >
                  <Sparkles v-if="m.is_discovered" :size="10" />
                  <span>{{ m.name }}</span>
                </button>
              </div>
            </div>

            <!-- Parameters Grid (Temperature, Thinking Mode, Max Tokens) -->
            <div class="form-grid-3 mt-4">
              <!-- Temperature (if not EMBEDDING) -->
              <div v-if="selectedTaskKey !== 'EMBEDDING'" class="input-group">
                <div class="label-with-hint">
                  <label class="input-label">Sampling Temperature</label>
                  <span class="font-mono text-xs font-semibold text-primary">{{ studioForm.temperature }}</span>
                </div>
                <input
                  v-model.number="studioForm.temperature"
                  type="range"
                  step="0.05"
                  min="0.0"
                  max="1.0"
                  class="form-range"
                />
              </div>

              <!-- Embedding Dimensions (if EMBEDDING) -->
              <div v-else class="input-group">
                <label class="input-label">Embedding Dimensions</label>
                <input
                  v-model.number="studioForm.embedding_dimensions"
                  type="number"
                  placeholder="768"
                  class="form-input font-mono"
                />
              </div>

              <!-- Thinking / Reasoning Mode Segmented Control -->
              <div class="input-group">
                <label class="input-label">Thinking / Reasoning Mode</label>
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
                <label class="input-label">Max Generation Tokens</label>
                <input
                  v-model.number="studioForm.max_tokens"
                  type="number"
                  step="256"
                  min="256"
                  max="32000"
                  class="form-input font-mono"
                />
              </div>
            </div>

            <div class="reasoning-info-callout">
              <Zap :size="13" class="text-primary flex-shrink-0" />
              <span>
                <strong>Thinking Mode:</strong> Instructs reasoning models (e.g. DeepSeek-R1, OpenAI o1/o3-mini, Claude 3.7 Thinking) to execute extended chain-of-thought verification before answering. For high-speed structured extraction, leave as <code>None (Fast)</code>.
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

          <!-- Section 3: Probe Test Result -->
          <div v-if="studioTestResult" class="studio-test-feedback animate-fade-in">
            <div class="test-feedback-header">
              <CheckCircle :size="16" class="text-success" />
              <span class="font-semibold">Connectivity Probe Verified for {{ studioTestResult.task_type }}</span>
            </div>
            <div class="test-feedback-body font-mono text-xs">
              <div><strong>Provider:</strong> {{ studioTestResult.provider_name }} ({{ studioTestResult.provider_type }})</div>
              <div><strong>Model:</strong> {{ studioTestResult.model_name }}</div>
              <div><strong>Probe Output:</strong> {{ studioTestResult.response }}</div>
            </div>
          </div>
        </div>
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
              >
                <Loader2 v-if="testingProviderId === p.id" class="animate-spin" :size="14" />
                <Play v-else :size="14" />
                <span>Test Probe</span>
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
            <div v-if="providerTestResults[p.id]" class="provider-test-pill animate-fade-in">
              <CheckCircle :size="13" class="text-success" />
              <span class="font-mono text-xs">{{ providerTestResults[p.id].response }}</span>
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
            <Mail :size="32" class="empty-icon" />
            <p>No email accounts connected yet.</p>
            <button class="btn btn-primary btn-sm mt-2" @click="openAddEmailAccountModal">
              <Plus :size="14" />
              <span>Connect First Account</span>
            </button>
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
                  <span class="preset-sub">iCloud, Fastmail, Yahoo, etc.</span>
                </div>
              </button>
            </div>
          </div>

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

          <div class="input-group">
            <label class="input-label">Account Label *</label>
            <input v-model="emailAccountForm.name" type="text" class="form-input" required />
          </div>

          <div class="input-group">
            <label class="input-label">Email Address *</label>
            <input v-model="emailAccountForm.username" type="email" placeholder="user@domain.com" class="form-input" required />
          </div>

          <div v-if="emailAccountForm.auth_method === 'app_password'" class="input-group">
            <label class="input-label">App Password *</label>
            <input v-model="emailAccountForm.app_password" type="password" placeholder="••••••••••••••••" class="form-input" />
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="isEmailAccountModalOpen = false">Cancel</button>
            <button class="btn btn-primary" @click="saveEmailAccount">{{ editingAccount ? 'Update Account' : 'Connect Account' }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.page-header {
  margin-bottom: 24px;
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

.tab-bar {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 3px;
  margin-top: 16px;
  width: fit-content;
  flex-wrap: wrap;
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
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-pill:hover {
  color: var(--text-main);
}

.tab-pill.active {
  background-color: var(--bg-elevated);
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
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
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  background-color: var(--bg-elevated);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
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
  grid-template-columns: 1fr 1.4fr 1fr;
  gap: 14px;
}

@media (max-width: 768px) {
  .form-grid-2, .form-grid-3 {
    grid-template-columns: 1fr;
  }
}

.form-range {
  width: 100%;
  accent-color: var(--primary);
  margin-top: 6px;
}

.reasoning-pills {
  display: flex;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}

.reasoning-pill {
  flex: 1;
  border: none;
  background: transparent;
  padding: 4px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  text-transform: capitalize;
  text-align: center;
}

.reasoning-pill.active {
  background-color: var(--primary);
  color: white;
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
  margin-bottom: 20px;
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
  border-radius: 4px;
  background-color: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: var(--text-success);
}

/* Preferences Grid */
.preferences-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-top: 16px;
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
  padding: 32px 16px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
