<script setup>
import { ref, onMounted } from 'vue'
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
} from 'lucide-vue-next'

const uiStore = useUIStore()

const activeTab = ref('preferences') // 'preferences' | 'bindings' | 'providers' | 'prompts' | 'email_accounts'

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


// Task Bindings state
const bindings = ref([])
const loadingBindings = ref(false)
const isBindingModalOpen = ref(false)
const currentBindingTask = ref('EXTRACTION')
const providerModels = ref([])
const loadingModels = ref(false)
const testingTask = ref(null)
const testResult = ref(null)
const bindingForm = ref({
  provider_id: null,
  model_name: '',
  temperature: 0.2,
  embedding_dimensions: 768,
})

// Prompt Templates state
const promptsList = ref([])
const loadingPrompts = ref(false)
const selectedPromptName = ref('EXTRACTION')
const currentPromptTemplate = ref('')
const isSavingPrompt = ref(false)
const isResettingPrompt = ref(false)

const TASKS = [
  {
    key: 'EXTRACTION',
    label: 'Email Metadata Extraction',
    recommendedTemp: 0.2,
    desc: 'Parses job details, dates, companies, and roles into structured Pydantic schemas'
  },
  {
    key: 'AGENT_REASONING',
    label: 'LangGraph Reasoning & Routing',
    recommendedTemp: 0.2,
    desc: 'Evaluates fuzzy deduplication and routes ambiguous items to staging'
  },
  {
    key: 'SUMMARIZATION',
    label: 'Timeline Narrative Synthesizer',
    recommendedTemp: 0.1,
    desc: 'Summarizes chronologies into rich textual snapshots for semantic indexing'
  },
  {
    key: 'EMBEDDING',
    label: 'Vector Embeddings (pgvector)',
    recommendedTemp: '768 dims',
    desc: 'Generates 768-dimension dense vector representations for cosine search'
  },
  {
    key: 'SCRAPER_PARSER',
    label: 'Job Spec & Scraper Parser',
    recommendedTemp: 0.0,
    desc: 'Extracts skills, salary ranges, and markdown from Camoufox DOM captures'
  },
]

const PROMPT_METAS = {
  extraction: {
    title: 'Email Extraction Prompt',
    desc: 'Controls structured metadata parsing from raw email bodies.',
    placeholders: ['{email_content}'],
  },
  assessment: {
    title: 'Pre-Application Assessment Prompt',
    desc: 'Evaluates candidate-job fit score, matching skills, and missing keywords from job descriptions.',
    placeholders: ['{job_description}', '{candidate_skills}', '{programmatic_baseline}'],
  },
  cv_anonymization: {
    title: 'CV De-Identification & Anonymization',
    desc: 'Scrubs real names, addresses, and past employer names, and converts date windows into durations.',
    placeholders: ['{resume_text}'],
  },
  summarization: {
    title: 'Timeline Summarization Prompt',
    desc: 'Synthesizes chronological timeline events into rich narrative snapshots for vector embedding.',
    placeholders: ['{events_str}'],
  },
  agent_system: {
    title: 'Agent Chat Assistant System Prompt',
    desc: 'Instructs the conversational agent on tone, database query tools, and pipeline management.',
    placeholders: [],
  },
}

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
  loadingBindings.value = true
  try {
    const res = await AIConfigAPI.listBindings()
    bindings.value = res.data || []
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    loadingBindings.value = false
  }
}

async function loadPrompts() {
  loadingPrompts.value = true
  try {
    const res = await PromptsAPI.list()
    promptsList.value = res.data || []
    const selected = promptsList.value.find((p) => p.name === selectedPromptName.value)
    if (selected) {
      currentPromptTemplate.value = selected.template
    }
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    loadingPrompts.value = false
  }
}

function selectPrompt(name) {
  selectedPromptName.value = name
  const found = promptsList.value.find((p) => p.name === name)
  currentPromptTemplate.value = found ? found.template : ''
}

async function savePromptTemplate() {
  isSavingPrompt.value = true
  try {
    await PromptsAPI.update(selectedPromptName.value, currentPromptTemplate.value)
    uiStore.showToast(`Prompt '${selectedPromptName.value}' updated successfully!`, 'success')
    loadPrompts()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSavingPrompt.value = false
  }
}

async function resetPromptTemplate() {
  if (!confirm(`Reset '${selectedPromptName.value}' prompt back to factory defaults?`)) return
  isResettingPrompt.value = true
  try {
    const res = await PromptsAPI.reset(selectedPromptName.value)
    currentPromptTemplate.value = res.data.template
    uiStore.showToast(`Prompt '${selectedPromptName.value}' reset to defaults`, 'info')
    loadPrompts()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isResettingPrompt.value = false
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

onMounted(() => {
  loadProviders()
  loadBindings()
  loadPrompts()
  loadEmailAccounts()
})

// Provider CRUD & Direct Probe
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
    loadProviders()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function deleteProvider(id) {
  if (!confirm('Are you sure you want to delete this provider?')) return
  try {
    await AIConfigAPI.deleteProvider(id)
    uiStore.showToast('Provider deleted', 'info')
    loadProviders()
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

// Model Discovery
async function fetchModelsForProvider(providerId) {
  if (!providerId) {
    providerModels.value = []
    return
  }
  loadingModels.value = true
  try {
    const res = await AIConfigAPI.getProviderModels(providerId)
    providerModels.value = res.data?.models || []
  } catch (err) {
    console.warn('Failed to load models for provider', err)
    providerModels.value = []
  } finally {
    loadingModels.value = false
  }
}

function onBindingProviderChange() {
  fetchModelsForProvider(bindingForm.value.provider_id)
}

function selectSuggestedModel(modelId) {
  bindingForm.value.model_name = modelId
}

// Binding CRUD & Test
function openEditBinding(taskKey) {
  currentBindingTask.value = taskKey
  const taskDef = TASKS.find(t => t.key === taskKey)
  const defaultTemp = typeof taskDef?.recommendedTemp === 'number' ? taskDef.recommendedTemp : 0.2

  const existing = bindings.value.find((b) => b.task_type === taskKey)
  const chosenProviderId = existing ? existing.provider_id : (providers.value[0]?.id || null)

  if (existing) {
    bindingForm.value = {
      provider_id: existing.provider_id,
      model_name: existing.model_name,
      temperature: existing.temperature,
      max_tokens: existing.max_tokens || 2000,
      embedding_dimensions: existing.embedding_dimensions || (taskKey === 'EMBEDDING' ? 768 : null),
    }
  } else {
    bindingForm.value = {
      provider_id: chosenProviderId,
      model_name: taskKey === 'EMBEDDING' ? 'nomic-embed-text' : 'qwen3.5-4b',
      temperature: defaultTemp,
      max_tokens: 2000,
      embedding_dimensions: taskKey === 'EMBEDDING' ? 768 : null,
    }
  }
  fetchModelsForProvider(chosenProviderId)
  isBindingModalOpen.value = true
}

async function saveBinding() {
  try {
    await AIConfigAPI.setBinding(currentBindingTask.value, bindingForm.value)
    uiStore.showToast(`Task '${currentBindingTask.value}' bound successfully`, 'success')
    isBindingModalOpen.value = false
    loadBindings()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function testTaskBinding(taskKey) {
  testingTask.value = taskKey
  testResult.value = null
  try {
    const res = await AIConfigAPI.testBinding(taskKey)
    testResult.value = res.data
    uiStore.showToast(`Connectivity test passed for ${taskKey}!`, 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    testingTask.value = null
  }
}

async function triggerSync(account) {
  syncingAccount.value = account.id
  try {
    const res = await IntakeAPI.syncAccount({ account_id: account.id })
    uiStore.showToast(res.data.message, 'success')
    loadEmailAccounts()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    syncingAccount.value = null
  }
}

// Email Account Management State & Handlers
const emailAccounts = ref([])
const loadingAccounts = ref(false)
const syncingAccount = ref(null)
const isEmailAccountModalOpen = ref(false)
const showConnectionGuide = ref(false)
const editingAccount = ref(null)
const accountToDelete = ref(null)
const showDeleteAccountModal = ref(false)
const isSavingAccount = ref(false)
const isDeletingAccount = ref(false)

const emailAccountForm = ref({
  name: '',
  provider_preset: 'gmail', // 'gmail' | 'outlook' | 'custom'
  auth_type: 'GMAIL_OAUTH', // 'GMAIL_OAUTH' | 'MS_GRAPH_OAUTH' | 'IMAP'
  auth_method: 'oauth', // 'app_password' | 'oauth'
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

function onProviderPresetChange(preset) {
  emailAccountForm.value.provider_preset = preset
  if (preset === 'gmail') {
    emailAccountForm.value.auth_type = emailAccountForm.value.auth_method === 'oauth' ? 'GMAIL_OAUTH' : 'IMAP'
    emailAccountForm.value.imap_host = 'imap.gmail.com'
    emailAccountForm.value.imap_port = 993
    if (!emailAccountForm.value.name || emailAccountForm.value.name === 'Outlook 365' || emailAccountForm.value.name === 'Work IMAP') {
      emailAccountForm.value.name = 'Gmail Inbox'
    }
  } else if (preset === 'outlook') {
    emailAccountForm.value.auth_type = emailAccountForm.value.auth_method === 'oauth' ? 'MS_GRAPH_OAUTH' : 'IMAP'
    emailAccountForm.value.imap_host = 'outlook.office365.com'
    emailAccountForm.value.imap_port = 993
    if (!emailAccountForm.value.name || emailAccountForm.value.name === 'Gmail Inbox' || emailAccountForm.value.name === 'Work IMAP') {
      emailAccountForm.value.name = 'Outlook 365'
    }
  } else {
    emailAccountForm.value.auth_type = 'IMAP'
    emailAccountForm.value.auth_method = 'app_password'
    emailAccountForm.value.imap_host = ''
    emailAccountForm.value.imap_port = 993
    if (!emailAccountForm.value.name || emailAccountForm.value.name === 'Gmail Inbox' || emailAccountForm.value.name === 'Outlook 365') {
      emailAccountForm.value.name = 'Work IMAP'
    }
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
    const res = await EmailAccountsAPI.getOAuthUrl({
      provider: prov === 'outlook' ? 'microsoft' : 'google',
      client_id: emailAccountForm.value.client_id || undefined,
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

function applySchedulePreset(timeStr) {
  const [h, m] = timeStr.split(':')
  emailAccountForm.value.sync_schedule_hour = h
  emailAccountForm.value.sync_schedule_min = m
}

function openAddEmailAccountModal() {
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
  if (!emailAccountForm.value.username.trim()) {
    uiStore.showToast('Please enter an email username / address', 'warning')
    return
  }
  isSavingAccount.value = true
  try {
    const scheduleTime = `${String(emailAccountForm.value.sync_schedule_hour).padStart(2, '0')}:${String(emailAccountForm.value.sync_schedule_min).padStart(2, '0')}`
    const resolvedAuthType = emailAccountForm.value.auth_method === 'oauth'
      ? (emailAccountForm.value.provider_preset === 'outlook' ? 'MS_GRAPH_OAUTH' : 'GMAIL_OAUTH')
      : 'IMAP'

    const payload = {
      name: emailAccountForm.value.name.trim() || emailAccountForm.value.username.trim(),
      auth_type: resolvedAuthType,
      username: emailAccountForm.value.username.trim(),
      folder: emailAccountForm.value.folder.trim() || 'INBOX',
      imap_host: emailAccountForm.value.imap_host ? emailAccountForm.value.imap_host.trim() : null,
      imap_port: emailAccountForm.value.imap_port ? Number(emailAccountForm.value.imap_port) : 993,
      is_active: emailAccountForm.value.is_active,
      sync_interval: emailAccountForm.value.sync_interval,
      sync_schedule_time: scheduleTime,
      sync_schedule_day: emailAccountForm.value.sync_schedule_day,
    }

    if (emailAccountForm.value.app_password) {
      payload.app_password = emailAccountForm.value.app_password
    }
    if (emailAccountForm.value.client_id) {
      payload.client_id = emailAccountForm.value.client_id
    }
    if (emailAccountForm.value.client_secret) {
      payload.client_secret = emailAccountForm.value.client_secret
    }

    if (editingAccount.value) {
      await EmailAccountsAPI.update(editingAccount.value.id, payload)
      uiStore.showToast('Email account settings updated successfully', 'success')
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

async function saveAndConnectOAuth() {
  if (!emailAccountForm.value.username.trim()) {
    uiStore.showToast('Please enter your email address first', 'warning')
    return
  }
  await saveEmailAccount()
  // Only launch OAuth if save succeeded (modal would still be open on error)
  if (!isEmailAccountModalOpen.value) return
  startOAuthLogin(emailAccountForm.value.provider_preset)
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

function formatSyncInterval(acc) {
  if (!acc) return 'Manual'
  const interval = acc.sync_interval || '1h'
  if (interval === 'MANUAL') return 'Manual on demand'
  if (interval === '15m') return 'Every 15 minutes'
  if (interval === '1h') return 'Every 1 hour'
  if (interval === '6h') return 'Every 6 hours'
  if (interval === '24h') return `Daily at ${acc.sync_schedule_time || '09:00'}`
  if (interval === 'WEEKLY') return `Weekly (${acc.sync_schedule_day || 'MON'} at ${acc.sync_schedule_time || '09:00'})`
  return interval
}

function formatLastSync(dateStr) {
  if (!dateStr) return 'Never synced'
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">AI Registry & Configuration</h1>
        <p class="page-subtitle">
          Manage multi-provider LLMs, task-based routing with LangChain, structured system prompts, and email sync accounts.
        </p>
      </div>

      <div class="tab-bar">
        <button
          class="tab-pill"
          :class="{ active: activeTab === 'preferences' }"
          @click="activeTab = 'preferences'"
        >
          <SlidersHorizontal :size="15" />
          <span>Preferences & Currency</span>
        </button>
        <button
          class="tab-pill"
          :class="{ active: activeTab === 'bindings' }"
          @click="activeTab = 'bindings'"
        >
          <Cpu :size="15" />
          <span>Task Bindings</span>
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
          :class="{ active: activeTab === 'prompts' }"
          @click="activeTab = 'prompts'"
        >
          <FileCode :size="15" />
          <span>Prompts Editor</span>
        </button>
        <button
          class="tab-pill"
          :class="{ active: activeTab === 'email_accounts' }"
          @click="activeTab = 'email_accounts'"
        >
          <Mail :size="15" />
          <span>Email Accounts ({{ emailAccounts.length }})</span>
        </button>
      </div>
    </div>

    <!-- TAB 0: PREFERENCES & CURRENCY -->
    <div v-if="activeTab === 'preferences'" class="tab-content animate-fade-in">
      <div class="section-card">
        <div class="card-intro">
          <h3>System & Workspace Preferences</h3>
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

    <!-- TAB 1: TASK BINDINGS -->
    <div v-if="activeTab === 'bindings'" class="tab-content animate-fade-in">
      <div class="section-card">
        <div class="card-intro">
          <h3>Task-Based Model Routing</h3>
          <p>Route specific AI subtasks to optimized models with recommended hyperparameter temperatures.</p>
        </div>

        <div class="bindings-list">
          <div v-for="t in TASKS" :key="t.key" class="binding-item">
            <div class="binding-info">
              <div class="binding-top">
                <span class="badge badge-applied font-mono">{{ t.key }}</span>
                <span class="binding-title">{{ t.label }}</span>
                <span class="recommended-badge" title="Recommended temperature for deterministic output">
                  <Thermometer :size="11" />
                  <span>Rec: {{ t.recommendedTemp }}</span>
                </span>
              </div>
              <p class="binding-desc">{{ t.desc }}</p>

              <!-- Resolved Binding Summary -->
              <div class="binding-active-state">
                <span class="text-muted">Bound Model:</span>
                <span class="font-mono text-main font-semibold">
                  {{ bindings.find(b => b.task_type === t.key)?.model_name || 'Cascades to .env default (qwen3.5-4b)' }}
                </span>
                <span v-if="bindings.find(b => b.task_type === t.key)" class="binding-temp">
                  (temp: {{ bindings.find(b => b.task_type === t.key)?.temperature }})
                </span>
              </div>
            </div>

            <div class="binding-actions">
              <button
                class="btn btn-secondary btn-sm"
                @click="openEditBinding(t.key)"
              >
                <Edit3 :size="14" />
                <span>Configure</span>
              </button>

              <button
                v-if="bindings.find(b => b.task_type === t.key)"
                class="btn btn-primary btn-sm"
                :disabled="testingTask === t.key"
                @click="testTaskBinding(t.key)"
              >
                <Loader2 v-if="testingTask === t.key" class="animate-spin" :size="14" />
                <Play v-else :size="14" />
                <span>Test Probe</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Probe Test Result Feedback -->
        <div v-if="testResult" class="probe-result-box animate-fade-in">
          <div class="probe-header">
            <CheckCircle :size="16" class="text-success" />
            <span class="font-semibold">Connectivity Probe Verified for {{ testResult.task_type }}</span>
          </div>
          <div class="probe-body font-mono text-xs">
            <div><strong>Provider:</strong> {{ testResult.provider_name }} ({{ testResult.provider_type }})</div>
            <div><strong>Model:</strong> {{ testResult.model_name }}</div>
            <div><strong>Response:</strong> {{ testResult.response }}</div>
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
            <p>Connect local endpoints (LM Studio, Ollama, vLLM) or Cloud APIs (OpenAI, Anthropic, Gemini).</p>
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


            <!-- Provider Live Probe Result -->
            <div v-if="providerTestResults[p.id]" class="provider-probe-feedback font-mono text-xs">
              <CheckCircle :size="13" class="text-success" />
              <span>Probe OK: {{ providerTestResults[p.id].response }}</span>
            </div>

            <div class="provider-actions">
              <button
                class="btn btn-secondary btn-sm"
                :disabled="testingProviderId === p.id"
                @click="testProviderDirect(p)"
                title="Send a lightweight connectivity probe to this provider"
              >
                <Loader2 v-if="testingProviderId === p.id" class="animate-spin" :size="13" />
                <Zap v-else :size="13" />
                <span>Test Probe</span>
              </button>
              <button class="btn btn-secondary btn-sm" @click="openEditProvider(p)">
                <Edit3 :size="13" />
                <span>Edit</span>
              </button>
              <button class="btn btn-danger btn-sm" @click="deleteProvider(p.id)">
                <Trash2 :size="13" />
                <span>Delete</span>
              </button>
            </div>
          </div>

          <div v-if="providers.length === 0" class="empty-state">
            No AI providers configured in DB. System using `.env` fallback (LM Studio: http://192.168.1.187:1234/v1).
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: PROMPTS EDITOR -->
    <div v-else-if="activeTab === 'prompts'" class="tab-content animate-fade-in">
      <div class="prompts-layout">
        <!-- Sidebar Prompt Selector -->
        <div class="prompts-sidebar">
          <div class="sidebar-title">Prompt Templates</div>
          <div class="prompt-nav">
            <button
              v-for="(meta, pName) in PROMPT_METAS"
              :key="pName"
              class="prompt-nav-item"
              :class="{ active: selectedPromptName === pName }"
              @click="selectPrompt(pName)"
            >
              <div class="nav-item-title">{{ meta.title }}</div>
              <div class="nav-item-sub font-mono text-xs">{{ pName }}</div>
            </button>
          </div>
        </div>

        <!-- Editor Pane -->
        <div class="prompts-editor-pane">
          <div class="editor-header">
            <div>
              <h3>{{ PROMPT_METAS[selectedPromptName]?.title || selectedPromptName }}</h3>
              <p>{{ PROMPT_METAS[selectedPromptName]?.desc }}</p>
            </div>

            <div class="editor-actions">
              <button
                class="btn btn-secondary btn-sm"
                :disabled="isResettingPrompt"
                @click="resetPromptTemplate"
              >
                <RotateCcw :size="14" />
                <span>Reset Default</span>
              </button>

              <button
                class="btn btn-primary btn-sm"
                :disabled="isSavingPrompt"
                @click="savePromptTemplate"
              >
                <Loader2 v-if="isSavingPrompt" class="animate-spin" :size="14" />
                <Save v-else :size="14" />
                <span>Save Prompt</span>
              </button>
            </div>
          </div>

          <!-- Variable Placeholders Chips -->
          <div v-if="PROMPT_METAS[selectedPromptName]?.placeholders.length" class="placeholders-box">
            <span class="placeholder-label">Supported Placeholders:</span>
            <span
              v-for="ph in PROMPT_METAS[selectedPromptName].placeholders"
              :key="ph"
              class="placeholder-tag font-mono"
            >
              {{ ph }}
            </span>
          </div>

          <!-- Prompt Textarea -->
          <div class="editor-body">
            <textarea
              v-model="currentPromptTemplate"
              rows="14"
              class="prompt-textarea font-mono"
              placeholder="Enter prompt template text..."
            ></textarea>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: EMAIL ACCOUNTS -->
    <div v-else-if="activeTab === 'email_accounts'" class="tab-content animate-fade-in">
      <div class="section-card">
        <div class="section-header-row">
          <div>
            <h3>Connected Mailboxes & Sync Schedule</h3>
            <p>Connect mailboxes via 1-Click OAuth (Google / Microsoft) or IMAP, and configure automated background sync schedules.</p>
          </div>

          <button class="btn btn-primary" @click="openAddEmailAccountModal">
            <Plus :size="15" />
            <span>Connect Email Account</span>
          </button>
        </div>

        <div class="accounts-list">
          <div v-for="acc in emailAccounts" :key="acc.id" class="account-card">
            <div class="account-info">
              <div class="account-title-row">
                <Mail :size="16" class="text-primary" />
                <span class="account-name">{{ acc.name }}</span>
                <span class="badge" :class="acc.is_active ? 'badge-applied' : 'badge-rejected'">
                  {{ acc.is_active ? 'Active' : 'Paused' }}
                </span>
                <span class="badge badge-applied font-mono">{{ acc.auth_type || 'IMAP' }}</span>
              </div>
              <div class="account-details-sub">
                <span class="text-xs text-secondary font-mono">{{ acc.username }}</span>
                <span class="text-muted text-xs">•</span>
                <span class="text-xs text-muted">Folder: {{ acc.folder }}</span>
                <span class="text-muted text-xs">•</span>
                <span class="sync-schedule-pill">
                  <Clock :size="11" />
                  <span>{{ formatSyncInterval(acc) }}</span>
                </span>
                <span class="text-muted text-xs">•</span>
                <span class="text-xs text-muted">Last sync: {{ formatLastSync(acc.last_synced_at) }}</span>
              </div>
            </div>

            <div class="account-actions">
              <button
                class="btn btn-primary btn-sm"
                :disabled="syncingAccount === acc.id"
                @click="triggerSync(acc)"
                title="Trigger immediate mailbox sync"
              >
                <Loader2 v-if="syncingAccount === acc.id" class="animate-spin" :size="14" />
                <RefreshCw v-else :size="14" />
                <span>{{ syncingAccount === acc.id ? 'Syncing...' : 'Sync Now' }}</span>
              </button>

              <button
                class="btn btn-secondary btn-sm"
                @click="openEditEmailAccountModal(acc)"
                title="Edit account credentials and sync schedule"
              >
                <Edit3 :size="14" />
                <span>Edit</span>
              </button>

              <button
                class="btn btn-danger btn-sm"
                @click="openDeleteAccountModal(acc)"
                title="Remove email account connection"
              >
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

    <!-- BINDING MODAL -->
    <div v-if="isBindingModalOpen" class="modal-backdrop" @click.self="isBindingModalOpen = false">
      <div class="modal-card animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">Configure Task Binding: {{ currentBindingTask }}</h3>
          <button class="btn-close" @click="isBindingModalOpen = false">×</button>
        </div>

        <div class="modal-body">
          <div class="input-group">
            <label class="input-label">Select AI Provider *</label>
            <select v-model="bindingForm.provider_id" class="form-input" @change="onBindingProviderChange" required>
              <option v-for="p in providers" :key="p.id" :value="p.id">
                {{ p.name }} ({{ p.provider_type }})
              </option>
            </select>
          </div>

          <div class="input-group">
            <div class="label-with-hint">
              <label class="input-label">Model Identifier *</label>
              <span v-if="loadingModels" class="text-xs text-muted font-mono flex items-center gap-1">
                <Loader2 class="animate-spin" :size="11" /> Discovering models...
              </span>
            </div>
            <input
              v-model="bindingForm.model_name"
              type="text"
              placeholder="e.g. qwen3.5-4b, claude-3-5-sonnet-20241022"
              class="form-input font-mono"
              required
            />

            <!-- Discovered / Curated Model Suggestions -->
            <div v-if="providerModels.length > 0" class="model-suggestions-box">
              <span class="suggestions-label">Suggested Models:</span>
              <div class="suggestions-list">
                <button
                  v-for="m in providerModels"
                  :key="m.id"
                  type="button"
                  class="model-chip font-mono"
                  :class="{ active: bindingForm.model_name === m.id, discovered: m.is_discovered }"
                  @click="selectSuggestedModel(m.id)"
                >
                  <Sparkles v-if="m.is_discovered" :size="10" />
                  <span>{{ m.name }}</span>
                </button>
              </div>
            </div>
          </div>

          <div class="input-group" v-if="currentBindingTask === 'EMBEDDING'">
            <label class="input-label">Embedding Dimensions</label>
            <input v-model.number="bindingForm.embedding_dimensions" type="number" placeholder="768" class="form-input font-mono" />
          </div>

          <div class="input-group" v-else>
            <label class="input-label">Sampling Temperature</label>
            <input v-model.number="bindingForm.temperature" type="number" step="0.1" min="0" max="2" class="form-input font-mono" />
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="isBindingModalOpen = false">Cancel</button>
            <button class="btn btn-primary" @click="saveBinding">Bind Task</button>
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
          <!-- Step 1: Provider Selection -->
          <div class="input-group">
            <label class="input-label">Select Email Provider</label>
            <div class="provider-presets-grid">
              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'gmail' }"
                @click="onProviderPresetChange('gmail')"
              >
                <div class="preset-icon gmail-icon">
                  <Mail :size="18" />
                </div>
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
                <div class="preset-icon outlook-icon">
                  <Mail :size="18" />
                </div>
                <div class="preset-info">
                  <span class="preset-name">Microsoft Outlook / 365</span>
                  <span class="preset-sub">MS Graph OAuth2 or IMAP</span>
                </div>
              </button>

              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'custom' }"
                @click="onProviderPresetChange('custom')"
              >
                <div class="preset-icon imap-icon">
                  <Server :size="18" />
                </div>
                <div class="preset-info">
                  <span class="preset-name">Custom IMAP</span>
                  <span class="preset-sub">iCloud, Fastmail, Yahoo, etc.</span>
                </div>
              </button>
            </div>
          </div>

          <!-- Step 2: Auth Method Toggle (for Gmail/Outlook) -->
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

          <!-- Interactive Provider Connection Guide -->
          <div class="connection-guide-accordion">
            <button
              type="button"
              class="guide-toggle-header"
              @click="showConnectionGuide = !showConnectionGuide"
            >
              <div class="guide-header-left">
                <HelpCircle :size="15" class="text-primary" />
                <span class="guide-toggle-title">
                  Setup Guide: How to connect {{ emailAccountForm.provider_preset === 'gmail' ? 'Google Gmail' : emailAccountForm.provider_preset === 'outlook' ? 'Microsoft Outlook / 365' : 'Custom IMAP' }}
                </span>
              </div>
              <component :is="showConnectionGuide ? ChevronUp : ChevronDown" :size="15" class="guide-arrow" />
            </button>

            <div v-if="showConnectionGuide" class="guide-content-body animate-fade-in">
              <!-- Gmail Guide -->
              <div v-if="emailAccountForm.provider_preset === 'gmail'" class="guide-steps-list">
                <!-- Gmail + OAuth selected -->
                <div v-if="emailAccountForm.auth_method === 'oauth'" class="guide-step-card">
                  <span class="step-badge oauth">OAuth2</span>
                  <div class="step-details">
                    <strong>Google Cloud Console — OAuth2 App Setup</strong>
                    <ol class="step-sublist">
                      <li>Open <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener" class="guide-link">Google Cloud Console <ExternalLink :size="10" /></a> and create or select a project.</li>
                      <li>Enable the <strong>Gmail API</strong> under APIs &amp; Services → Library.</li>
                      <li>Configure <strong>OAuth Consent Screen</strong> (External) and add your email as a test user.</li>
                      <li>Create Credentials → <strong>OAuth client ID</strong> → type: <em>Web application</em>.</li>
                      <li>Add Authorized Redirect URI: <code>http://localhost:8000/api/v1/email_accounts/oauth/callback/google</code></li>
                      <li>Copy the <strong>Client ID</strong> and <strong>Client Secret</strong> into the fields in the OAuth card below.</li>
                    </ol>
                  </div>
                </div>
                <!-- Gmail + App Password selected -->
                <div v-else class="guide-step-card">
                  <span class="step-badge">App Password</span>
                  <div class="step-details">
                    <strong>Google App Password — 10 Seconds Setup</strong>
                    <ol class="step-sublist">
                      <li>Go to <a href="https://myaccount.google.com/security" target="_blank" rel="noopener" class="guide-link">Google Account Security <ExternalLink :size="10" /></a> and ensure <em>2-Step Verification</em> is ON.</li>
                      <li>Visit <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" class="guide-link">Google App Passwords <ExternalLink :size="10" /></a>.</li>
                      <li>Enter app name <code>Job Tracker</code> and click <em>Create</em>.</li>
                      <li>Copy the 16-character password and paste it into the <em>App Password</em> field below.</li>
                    </ol>
                  </div>
                </div>
              </div>

              <!-- Outlook Guide -->
              <div v-else-if="emailAccountForm.provider_preset === 'outlook'" class="guide-steps-list">
                <!-- Outlook + OAuth selected -->
                <div v-if="emailAccountForm.auth_method === 'oauth'" class="guide-step-card">
                  <span class="step-badge oauth">OAuth2</span>
                  <div class="step-details">
                    <strong>Azure Portal — Microsoft Graph OAuth2 Setup</strong>
                    <ol class="step-sublist">
                      <li>Open <a href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade" target="_blank" rel="noopener" class="guide-link">Azure App Registrations <ExternalLink :size="10" /></a> and click <strong>New registration</strong>.</li>
                      <li>Add Web Redirect URI: <code>http://localhost:8000/api/v1/email_accounts/oauth/callback/microsoft</code></li>
                      <li>Under <em>API Permissions</em> add <code>Mail.Read</code>, <code>User.Read</code>, <code>offline_access</code> (Delegated).</li>
                      <li>Under <em>Certificates &amp; secrets</em>, create a secret — copy its <strong>Value</strong> immediately (shown once).</li>
                      <li>Copy the <strong>Application (client) ID</strong> from the Overview page.</li>
                      <li>Paste both into the fields in the OAuth card below.</li>
                    </ol>
                  </div>
                </div>
                <!-- Outlook + App Password selected -->
                <div v-else class="guide-step-card">
                  <span class="step-badge">App Password</span>
                  <div class="step-details">
                    <strong>Microsoft App Password / IMAP</strong>
                    <ol class="step-sublist">
                      <li>Go to <a href="https://account.live.com/proofs/manage/additional" target="_blank" rel="noopener" class="guide-link">Microsoft Security Settings <ExternalLink :size="10" /></a>.</li>
                      <li>Under <em>App passwords</em>, click <em>Create a new app password</em>.</li>
                      <li>Paste the generated password into the <em>App Password</em> field below.</li>
                    </ol>
                  </div>
                </div>
              </div>

              <!-- Custom IMAP Guide (no auth method toggle shown for custom) -->
              <div v-else class="guide-steps-list">
                <div class="guide-step-card">
                  <span class="step-badge">iCloud</span>
                  <div class="step-details">
                    <strong>Apple iCloud Mail</strong>
                    <p class="text-xs text-secondary mt-1">
                      Host: <code>imap.mail.me.com</code> (Port 993). Generate an App-Specific Password at <a href="https://appleid.apple.com" target="_blank" rel="noopener" class="guide-link">appleid.apple.com <ExternalLink :size="10" /></a>.
                    </p>
                  </div>
                </div>
                <div class="guide-step-card">
                  <span class="step-badge">IMAP</span>
                  <div class="step-details">
                    <strong>Fastmail / Yahoo / Private Mail Server</strong>
                    <p class="text-xs text-secondary mt-1">
                      Host: <code>imap.fastmail.com</code> or <code>imap.mail.yahoo.com</code> (Port 993). Use your mailbox login or App Password.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Account Name & Username -->
          <div class="form-row-2">
            <div class="input-group">
              <label class="input-label">Account Display Name *</label>
              <input
                v-model="emailAccountForm.name"
                type="text"
                placeholder="e.g. Personal Gmail"
                class="form-input"
                required
              />
            </div>

            <div class="input-group">
              <label class="input-label">Email Address / Username *</label>
              <input
                v-model="emailAccountForm.username"
                type="email"
                placeholder="candidate@gmail.com"
                class="form-input font-mono"
                required
              />
            </div>
          </div>

          <!-- OAuth2 Mode Card -->
          <div v-if="emailAccountForm.auth_method === 'oauth' && emailAccountForm.provider_preset !== 'custom'" class="oauth-fields-card">
            <div class="oauth-card-header">
              <Lock :size="14" class="text-primary" />
              <span>OAuth2 Authorization</span>
            </div>

            <!-- Credentials first -->
            <div class="form-row-2 mb-3">
              <div class="input-group">
                <label class="input-label">Client ID</label>
                <input
                  v-model="emailAccountForm.client_id"
                  type="text"
                  placeholder="Paste your Client ID"
                  class="form-input font-mono text-xs"
                />
              </div>
              <div class="input-group">
                <label class="input-label">Client Secret</label>
                <input
                  v-model="emailAccountForm.client_secret"
                  type="password"
                  placeholder="Paste your Client Secret"
                  class="form-input font-mono text-xs"
                />
              </div>
            </div>

            <!-- Setup guide (open by default, collapsible) -->
            <details class="oauth-guide-details" open>
              <summary class="oauth-guide-summary">
                <HelpCircle :size="12" />
                <span>How to create your OAuth app</span>
                <ChevronDown :size="12" class="oauth-guide-chevron" />
              </summary>

              <div class="oauth-guide-body">
                <!-- Gmail steps -->
                <ol v-if="emailAccountForm.provider_preset === 'gmail'" class="oauth-steps">
                  <li>Open <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener" class="oauth-guide-link">Google Cloud Console <ExternalLink :size="10" /></a> and create or select a project.</li>
                  <li>Enable the <strong>Gmail API</strong> under APIs &amp; Services &rarr; Library.</li>
                  <li>Configure <strong>OAuth Consent Screen</strong> (External) &mdash; add your Gmail as a test user.</li>
                  <li>Create Credentials &rarr; <strong>OAuth client ID</strong> &rarr; type: <em>Web application</em>.</li>
                  <li>Add Authorized Redirect URI:<br /><code class="oauth-redirect-uri">http://localhost:8000/api/v1/email_accounts/oauth/callback/google</code></li>
                  <li>Paste the <strong>Client ID</strong> and <strong>Client Secret</strong> into the fields above.</li>
                </ol>

                <!-- Outlook / MS Graph steps -->
                <ol v-else-if="emailAccountForm.provider_preset === 'outlook'" class="oauth-steps">
                  <li>Open <a href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade" target="_blank" rel="noopener" class="oauth-guide-link">Azure App Registrations <ExternalLink :size="10" /></a> &rarr; <strong>New registration</strong>.</li>
                  <li>Add Web Redirect URI:<br /><code class="oauth-redirect-uri">http://localhost:8000/api/v1/email_accounts/oauth/callback/microsoft</code></li>
                  <li>Under <em>API permissions</em> add <code>Mail.Read</code>, <code>User.Read</code>, <code>offline_access</code> (Delegated).</li>
                  <li>Under <em>Certificates &amp; secrets</em> create a secret &mdash; copy its <strong>Value</strong> immediately (shown once).</li>
                  <li>Copy the <strong>Application (client) ID</strong> from the Overview page.</li>
                  <li>Paste both into the fields above.</li>
                </ol>
              </div>
            </details>

            <!-- Single connect button at bottom -->
            <button
              type="button"
              class="btn btn-primary btn-oauth-action mt-3"
              :disabled="isSavingAccount"
              @click="saveAndConnectOAuth()"
            >
              <Loader2 v-if="isSavingAccount" :size="14" class="spin" />
              <ExternalLink v-else :size="14" />
              <span>Connect with {{ emailAccountForm.provider_preset === 'outlook' ? 'Microsoft' : 'Google' }}</span>
            </button>
          </div>

          <!-- App Password / IMAP Mode Card -->
          <div v-else class="imap-fields-card">
            <div class="input-group">
              <div class="label-with-hint">
                <label class="input-label">App Password / Mail Password *</label>
                <a
                  v-if="emailAccountForm.provider_preset === 'gmail'"
                  href="https://myaccount.google.com/apppasswords"
                  target="_blank"
                  rel="noopener"
                  class="app-pass-hint-link"
                >
                  Create Gmail App Password <ExternalLink :size="11" />
                </a>
              </div>
              <input
                v-model="emailAccountForm.app_password"
                type="password"
                placeholder="xxxx-xxxx-xxxx-xxxx"
                class="form-input font-mono text-xs"
                required
              />
            </div>

            <div class="form-row-2 mt-2">
              <div class="input-group">
                <label class="input-label">IMAP Host Server</label>
                <input
                  v-model="emailAccountForm.imap_host"
                  type="text"
                  placeholder="imap.gmail.com"
                  class="form-input font-mono text-xs"
                  required
                />
              </div>

              <div class="input-group">
                <label class="input-label">IMAP SSL Port</label>
                <input
                  v-model.number="emailAccountForm.imap_port"
                  type="number"
                  placeholder="993"
                  class="form-input font-mono text-xs"
                />
              </div>
            </div>
          </div>

          <!-- Folder & Sync Schedule -->
          <div class="schedule-section-card">
            <div class="schedule-header-row">
              <Clock :size="15" class="text-primary" />
              <span class="schedule-title">Automated Sync Schedule & Folder</span>
            </div>

            <div class="form-row-2">
              <div class="input-group">
                <label class="input-label">Scan Folder</label>
                <input
                  v-model="emailAccountForm.folder"
                  type="text"
                  placeholder="INBOX"
                  class="form-input font-mono text-xs"
                />
                <p class="field-hint">Pre-filter: only emails inside this folder are scanned and ingested by Job Tracker. Use <code class="hint-code">INBOX</code> to monitor your main inbox, or a label like <code class="hint-code">Recruitment</code> to keep intake focused.</p>
              </div>

              <div class="input-group">
                <label class="input-label">Sync Frequency</label>
                <select v-model="emailAccountForm.sync_interval" class="form-select">
                  <option value="MANUAL">Manual Sync Only (On Demand)</option>
                  <option value="15m">Every 15 Minutes</option>
                  <option value="1h">Every 1 Hour (Recommended)</option>
                  <option value="6h">Every 6 Hours</option>
                  <option value="24h">Daily (At specific 24h time)</option>
                  <option value="WEEKLY">Weekly (At specific day & 24h time)</option>
                </select>
              </div>
            </div>

            <!-- Daily / Weekly 24-Hour Time Controls -->
            <div v-if="emailAccountForm.sync_interval === '24h' || emailAccountForm.sync_interval === 'WEEKLY'" class="schedule-24h-box mt-3">
              <div class="form-row-2">
                <div v-if="emailAccountForm.sync_interval === 'WEEKLY'" class="input-group">
                  <label class="input-label">Scheduled Day</label>
                  <select v-model="emailAccountForm.sync_schedule_day" class="form-select">
                    <option value="MON">Monday</option>
                    <option value="TUE">Tuesday</option>
                    <option value="WED">Wednesday</option>
                    <option value="THU">Thursday</option>
                    <option value="FRI">Friday</option>
                    <option value="SAT">Saturday</option>
                    <option value="SUN">Sunday</option>
                  </select>
                </div>

                <div class="input-group">
                  <label class="input-label">Scheduled Time (24h Standard: {{ emailAccountForm.sync_schedule_hour }}:{{ emailAccountForm.sync_schedule_min }})</label>
                  <div class="time-spinners-24h">
                    <select v-model="emailAccountForm.sync_schedule_hour" class="form-select time-dropdown font-mono">
                      <option v-for="h in 24" :key="h" :value="String(h - 1).padStart(2, '0')">
                        {{ String(h - 1).padStart(2, '0') }}:00
                      </option>
                    </select>

                    <span class="time-sep">:</span>

                    <select v-model="emailAccountForm.sync_schedule_min" class="form-select time-dropdown font-mono">
                      <option value="00">00</option>
                      <option value="15">15</option>
                      <option value="30">30</option>
                      <option value="45">45</option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- Quick Presets -->
              <div class="presets-row mt-2">
                <span class="text-xs text-muted">24h Presets:</span>
                <div class="preset-chips-list">
                  <button
                    v-for="p in ['08:00', '09:00', '12:00', '14:00', '18:00', '22:00']"
                    :key="p"
                    type="button"
                    class="time-preset-chip font-mono"
                    :class="{ active: emailAccountForm.sync_schedule_hour + ':' + emailAccountForm.sync_schedule_min === p }"
                    @click="applySchedulePreset(p)"
                  >
                    {{ p }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Active Toggle -->
          <div class="active-toggle-row">
            <label class="checkbox-label">
              <input v-model="emailAccountForm.is_active" type="checkbox" />
              <span>Enable automatic background sync for this account</span>
            </label>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="isEmailAccountModalOpen = false">Cancel</button>
            <button class="btn btn-primary" :disabled="isSavingAccount" @click="saveEmailAccount">
              <Loader2 v-if="isSavingAccount" class="animate-spin" :size="14" />
              <Save v-else :size="14" />
              <span>{{ editingAccount ? 'Update Account' : 'Connect Account' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- DELETE EMAIL ACCOUNT CONFIRMATION MODAL -->
    <div v-if="showDeleteAccountModal" class="modal-backdrop" @click.self="showDeleteAccountModal = false">
      <div class="modal-card animate-fade-in modal-danger">
        <div class="modal-header">
          <h3 class="modal-title text-danger flex items-center gap-2">
            <Trash2 :size="16" />
            <span>Remove Email Account</span>
          </h3>
          <button class="btn-close" @click="showDeleteAccountModal = false">×</button>
        </div>

        <div class="modal-body">
          <p class="modal-warn-text">
            Are you sure you want to disconnect <strong>{{ accountToDelete?.name }}</strong> ({{ accountToDelete?.username }})?
          </p>
          <p class="text-xs text-muted">
            This will stop background email syncing. Existing ingested job applications and timeline events will not be deleted.
          </p>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showDeleteAccountModal = false">Cancel</button>
            <button class="btn btn-danger" :disabled="isDeletingAccount" @click="confirmDeleteAccount">
              <Loader2 v-if="isDeletingAccount" class="animate-spin" :size="14" />
              <Trash2 v-else :size="14" />
              <span>{{ isDeletingAccount ? 'Removing...' : 'Permanently Remove' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<style scoped>
.page-container {
  max-width: 1050px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.tab-bar {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 4px;
}

.tab-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.tab-pill.active {
  background-color: var(--bg-elevated);
  color: var(--text-main);
}

.section-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
}

.card-intro, .section-header-row {
  margin-bottom: 20px;
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-intro h3, .section-header-row h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.card-intro p, .section-header-row p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.bindings-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.binding-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  gap: 16px;
}

.binding-info {
  flex: 1;
}

.binding-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.binding-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.recommended-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.binding-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.binding-active-state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.binding-temp {
  color: var(--text-muted);
}

.binding-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.probe-result-box {
  margin-top: 20px;
  padding: 14px 18px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.probe-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--status-offer-text);
  margin-bottom: 6px;
}

.probe-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--text-main);
}

/* PROMPTS LAYOUT */
.prompts-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  min-height: 480px;
}

.prompts-sidebar {
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}

.prompt-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.prompt-nav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  text-align: left;
  transition: all var(--transition-fast);
  color: var(--text-secondary);
}

.prompt-nav-item:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
}

.prompt-nav-item.active {
  background-color: var(--bg-surface);
  color: var(--text-main);
  border: 1px solid var(--border-subtle);
}

.nav-item-title {
  font-size: 13px;
  font-weight: 600;
}

.nav-item-sub {
  color: var(--text-muted);
}

.prompts-editor-pane {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.editor-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.editor-header p {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.placeholders-box {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.placeholder-label {
  color: var(--text-muted);
}

.placeholder-tag {
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--primary);
  font-size: 11px;
}

.prompt-textarea {
  width: 100%;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  min-height: 280px;
}

.providers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.provider-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.provider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.provider-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.provider-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.meta-row {
  display: flex;
  gap: 6px;
}

.meta-k {
  color: var(--text-muted);
}

.meta-v {
  color: var(--text-main);
}

.provider-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 4px;
}

.provider-probe-feedback {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
}

.label-with-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.model-suggestions-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

.suggestions-label {
  font-size: 11px;
  color: var(--text-muted);
}

.suggestions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 100px;
  overflow-y: auto;
}

.model-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.model-chip:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
  border-color: var(--primary);
}

.model-chip.active {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border-color: var(--primary);
  font-weight: 600;
}

.model-chip.discovered {
  border-color: var(--border-color);
  color: var(--text-main);
}

.accounts-list {

  display: flex;
  flex-direction: column;
  gap: 10px;
}

.account-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.account-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 600;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.form-input {
  width: 100%;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted, var(--text-secondary));
  line-height: 1.5;
  margin-top: 4px;
}

.hint-code {
  font-family: monospace;
  font-size: 10.5px;
  padding: 1px 4px;
  border-radius: 3px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.empty-state {
  padding: 30px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

/* Preferences Grid */
.preferences-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.preference-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preference-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.preference-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.preference-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 2px;
}

.preference-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.currency-chips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
}

.currency-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.currency-chip:hover {
  border-color: var(--primary);
  color: var(--text-main);
  background-color: var(--bg-surface-hover);
}

.currency-chip.active {
  background-color: rgba(99, 102, 241, 0.12);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 700;
}

.chip-code {
  font-size: 13px;
  font-weight: 600;
}

.chip-symbol {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.currency-chip.active .chip-symbol {
  color: var(--primary);
}

.view-mode-toggle-row {
  display: flex;
  gap: 10px;
}

.view-mode-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.view-mode-option:hover {
  border-color: var(--border-subtle);
  color: var(--text-main);
}

.view-mode-option.active {
  background-color: rgba(99, 102, 241, 0.12);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}

/* Email Accounts Management Styles */
.account-details-sub {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.sync-schedule-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  color: var(--primary);
  background-color: rgba(99, 102, 241, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
}

.modal-lg {
  max-width: 620px;
  width: 100%;
}

.provider-presets-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 6px;
}

@media (max-width: 640px) {
  .provider-presets-grid {
    grid-template-columns: 1fr;
  }
}

.provider-preset-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 14px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  cursor: pointer;
  transition: all var(--transition-fast);
  gap: 8px;
}

.provider-preset-card:hover {
  border-color: var(--border-subtle);
  background-color: var(--bg-surface-hover);
}

.provider-preset-card.active {
  border-color: var(--primary);
  background-color: rgba(99, 102, 241, 0.08);
}

.preset-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gmail-icon {
  background-color: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.outlook-icon {
  background-color: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.imap-icon {
  background-color: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.preset-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.preset-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.preset-sub {
  font-size: 10px;
  color: var(--text-muted);
}

.auth-method-toggle {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 6px;
}

.auth-toggle-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.auth-toggle-btn:hover {
  border-color: var(--border-subtle);
  color: var(--text-main);
}

.auth-toggle-btn.active {
  border-color: var(--primary);
  background-color: rgba(99, 102, 241, 0.12);
  color: var(--primary);
  font-weight: 600;
}

.auth-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
  vertical-align: middle;
  margin-left: 2px;
}

.auth-badge.recommended {
  background-color: rgba(34, 197, 94, 0.15);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.oauth-inline-guide {
  padding: 10px 12px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  margin-bottom: 2px;
}

.oauth-inline-guide-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

@media (max-width: 550px) {
  .form-row-2 {
    grid-template-columns: 1fr;
  }
}

.oauth-fields-card,
.imap-fields-card,
.schedule-section-card {
  padding: 12px 14px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  margin-bottom: 14px;
}

.oauth-card-header,
.schedule-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 10px;
}

.form-select {
  width: 100%;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  font-size: 13px;
}

.active-toggle-row {
  margin-top: 6px;
  margin-bottom: 16px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
}

.modal-danger .modal-title {
  color: #ef4444;
}

.modal-warn-text {
  font-size: 14px;
  color: var(--text-main);
  margin-bottom: 8px;
  line-height: 1.5;
}

.oauth-guide-details {
  margin-top: 4px;
  margin-bottom: 2px;
}

.oauth-guide-summary {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  list-style: none;
  user-select: none;
  padding: 4px 0;
  transition: color var(--transition-fast);
}

.oauth-guide-summary::-webkit-details-marker {
  display: none;
}

.oauth-guide-summary:hover {
  color: var(--text-main);
}

.oauth-guide-chevron {
  margin-left: auto;
  transition: transform var(--transition-fast);
}

.oauth-guide-details[open] .oauth-guide-chevron {
  transform: rotate(180deg);
}

.oauth-guide-body {
  margin-top: 8px;
  padding: 10px 12px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.oauth-steps {
  padding-left: 16px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.oauth-steps li {
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.55;
}

.oauth-steps li strong {
  color: var(--text-main);
  font-weight: 600;
}

.oauth-guide-link {
  color: var(--accent);
  text-decoration: none;
}

.oauth-guide-link:hover {
  text-decoration: underline;
}

.oauth-redirect-uri {
  display: inline-block;
  margin-top: 3px;
  font-size: 10.5px;
  padding: 2px 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 3px;
  color: var(--text-main);
  font-family: monospace;
  word-break: break-all;
}

.btn-oauth-action {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  font-weight: 600;
}

.app-pass-hint-link {
  font-size: 11px;
  color: var(--primary);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  text-decoration: none;
}

.app-pass-hint-link:hover {
  text-decoration: underline;
}

.schedule-24h-box {
  background-color: var(--bg-surface-hover);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.time-spinners-24h {
  display: flex;
  align-items: center;
  gap: 6px;
}

.time-dropdown {
  flex: 1;
}

.time-sep {
  font-weight: bold;
  color: var(--text-muted);
}

.presets-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preset-chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.time-preset-chip {
  padding: 3px 8px;
  font-size: 11px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.time-preset-chip:hover {
  border-color: var(--primary);
  color: var(--text-main);
}

.time-preset-chip.active {
  background-color: rgba(99, 102, 241, 0.15);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 700;
}

/* Provider Connection Guide Accordion */
.connection-guide-accordion {
  margin-top: 10px;
  margin-bottom: 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background-color: var(--bg-surface);
  overflow: hidden;
}

.guide-toggle-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  background-color: var(--bg-surface);
  border: none;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.guide-toggle-header:hover {
  background-color: var(--bg-surface-hover);
}

.guide-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-toggle-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.guide-arrow {
  color: var(--text-muted);
}

.guide-content-body {
  padding: 12px 14px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--bg-canvas);
}

.guide-steps-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.guide-step-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
}

.step-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: rgba(16, 185, 129, 0.15);
  color: #10b981;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-badge.oauth {
  background-color: rgba(99, 102, 241, 0.15);
  color: #6366f1;
}

.step-details {
  font-size: 12px;
  color: var(--text-main);
  line-height: 1.4;
}

.step-sublist {
  margin-top: 6px;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.step-sublist code {
  font-family: var(--font-mono);
  font-size: 11px;
  background-color: var(--bg-surface-hover);
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--primary);
}

.guide-link {
  color: var(--primary);
  display: inline-flex;
  align-items: center;
  gap: 2px;
  text-decoration: underline;
}
</style>
