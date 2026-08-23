<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import {
  AIConfigAPI,
  CandidateProfileAPI,
  SystemSettingsAPI,
  EmailAccountsAPI,
} from '../../api/endpoints'
import { scrubCVText } from '../../utils/scrubber'
import {
  Sparkles,
  Server,
  UserCheck,
  SlidersHorizontal,
  Rocket,
  CheckCircle2,
  Circle,
  Check,
  Zap,
  Shield,
  Upload,
  FileText,
  Loader2,
  X,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Cpu,
  Mail,
  DollarSign,
  AlertTriangle,
  FileCode,
  ArrowRight,
  ArrowLeft,
  Info,
  Lock,
  Key,
  Eye,
  EyeOff,
  Copy,
  Save,
  Folder,
  Clock,
  Calendar,
  RefreshCw,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()

const currentStep = ref(1) // 1: Provider, 2: CV, 3: Features, 4: Launch
const isPrivacyExpanded = ref(false)

// Step 1: AI Provider State
const providerSubStep = ref(1) // 1: Select Preset Card, 2: Configure Endpoint & Verify
const hasFetchedModels = ref(false)
const selectedPresetKey = ref('lmstudio') // 'lmstudio' | 'ollama' | 'openai' | 'anthropic' | 'google' | 'openrouter' | 'custom'
const providerForm = ref({
  id: null,
  name: 'Local LM Studio',
  provider_type: 'openai',
  base_url: 'http://192.168.1.187:1234/v1',
  api_key: '',
  model_name: 'qwen/qwen3.5-9b',
  max_concurrency: 1,
})
const testingProvider = ref(false)
const providerTestResult = ref(null) // { status: 'success'|'warning'|'error', message: '' }
const isSavingProvider = ref(false)
const availableModels = ref([])
const loadingModels = ref(false)
const customModelMode = ref(false)

const PRESETS = [
  {
    key: 'lmstudio',
    name: 'Local LM Studio',
    type: 'openai',
    baseUrl: 'http://192.168.1.187:1234/v1',
    defaultModel: 'qwen/qwen3.5-9b',
    suggestedModels: ['qwen/qwen3.5-9b', 'qwen2.5-coder-7b-instruct', 'deepseek-r1-distill-qwen-7b', 'llama-3.2-3b-instruct'],
    isPrivate: true,
    badge: '100% Private / Offline',
    desc: 'Run Qwen, Llama, or DeepSeek locally on your LAN. Zero telemetry or internet transmission.',
  },
  {
    key: 'ollama',
    name: 'Local Ollama',
    type: 'ollama',
    baseUrl: 'http://localhost:11434/v1',
    defaultModel: 'qwen2.5',
    suggestedModels: ['qwen2.5', 'llama3.2', 'mistral', 'deepseek-r1:8b', 'phi4'],
    isPrivate: true,
    badge: '100% Private / Offline',
    desc: 'Local Ollama instance running on localhost. Keeps all candidate CV data 100% on-premise.',
  },
  {
    key: 'openai',
    name: 'OpenAI',
    type: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    defaultModel: 'gpt-4o-mini',
    suggestedModels: ['gpt-4o-mini', 'gpt-4o', 'o3-mini', 'gpt-3.5-turbo'],
    isPrivate: false,
    badge: 'Zero Data Retention',
    pricingLink: 'https://openai.com/api/pricing',
    desc: 'Industry-standard cloud models (GPT-4o, o3-mini). Enterprise API guarantees zero model training on your data.',
  },
  {
    key: 'anthropic',
    name: 'Anthropic',
    type: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    defaultModel: 'claude-3-5-haiku-20241022',
    suggestedModels: ['claude-3-5-haiku-20241022', 'claude-3-7-sonnet-20250219', 'claude-3-5-sonnet-20241022'],
    isPrivate: false,
    badge: 'Zero Data Retention',
    pricingLink: 'https://www.anthropic.com/pricing',
    desc: 'Claude 3.7 & 3.5 Sonnet / Haiku models with advanced reasoning and analysis capabilities.',
  },
  {
    key: 'google',
    name: 'Google Gemini',
    type: 'google_genai',
    baseUrl: 'https://generativelanguage.googleapis.com',
    defaultModel: 'gemini-2.0-flash',
    suggestedModels: ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-1.5-flash', 'gemini-1.5-pro'],
    isPrivate: false,
    badge: 'Generous Free Tier',
    pricingLink: 'https://ai.google.dev/pricing',
    desc: 'High-speed Google AI Studio API key with generous free tier rates.',
  },
  {
    key: 'openrouter',
    name: 'OpenRouter',
    type: 'openrouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    defaultModel: 'meta-llama/llama-3.3-70b-instruct',
    suggestedModels: ['meta-llama/llama-3.3-70b-instruct', 'deepseek/deepseek-r1', 'google/gemini-2.0-flash-001', 'anthropic/claude-3.5-haiku'],
    isPrivate: false,
    badge: 'Aggregator API',
    pricingLink: 'https://openrouter.ai/models',
    desc: 'Unified gateway providing access to DeepSeek-R1, Llama 3.3 70B, and 100+ open-source models.',
  },
  {
    key: 'custom',
    name: 'Custom / Other Endpoint',
    type: 'openai',
    baseUrl: 'http://localhost:8000/v1',
    defaultModel: 'default',
    suggestedModels: [],
    isPrivate: false,
    badge: 'OpenAI-Compatible',
    desc: 'Connect to vLLM, Groq, Mistral, Together, or any custom OpenAI-compatible inference server.',
  },
]

function selectPreset(preset, autoAdvance = true) {
  selectedPresetKey.value = preset.key
  providerForm.value.name = preset.name
  providerForm.value.provider_type = preset.type
  providerForm.value.base_url = preset.baseUrl
  providerForm.value.model_name = preset.defaultModel
  availableModels.value = []
  customModelMode.value = false
  hasFetchedModels.value = false
  providerTestResult.value = null
  if (autoAdvance) {
    providerSubStep.value = 2
  }
}

async function testConnection() {
  testingProvider.value = true
  providerTestResult.value = null
  try {
    let activeProviderId = providerForm.value.id
    if (!activeProviderId) {
      const res = await AIConfigAPI.createProvider({
        name: providerForm.value.name,
        provider_type: providerForm.value.provider_type,
        base_url: providerForm.value.base_url,
        api_key: providerForm.value.api_key || undefined,
        max_concurrency: providerForm.value.max_concurrency || 1,
        is_active: true,
      })
      activeProviderId = res.data.id
      providerForm.value.id = activeProviderId
    } else {
      await AIConfigAPI.updateProvider(activeProviderId, {
        name: providerForm.value.name,
        provider_type: providerForm.value.provider_type,
        base_url: providerForm.value.base_url,
        api_key: providerForm.value.api_key || undefined,
        max_concurrency: providerForm.value.max_concurrency || 1,
        is_active: true,
      })
    }

    const testRes = await AIConfigAPI.testProvider(activeProviderId)
    const isWarn = testRes.data?.status === 'warning'

    // Fetch discovered models from endpoint
    try {
      loadingModels.value = true
      const modelsRes = await AIConfigAPI.getProviderModels(activeProviderId)
      const models = modelsRes.data?.models || []
      if (models.length > 0) {
        const modelNames = models.map((m) => (typeof m === 'string' ? m : m.id || m.name))
        availableModels.value = modelNames
        if (!modelNames.includes(providerForm.value.model_name)) {
          providerForm.value.model_name = modelNames[0]
        }
      }
    } catch {
      // Model discovery fallback
    } finally {
      loadingModels.value = false
    }

    hasFetchedModels.value = true
    const modelCountText = availableModels.value.length > 0 ? ` (${availableModels.value.length} models discovered)` : ''
    providerTestResult.value = {
      status: isWarn ? 'warning' : 'success',
      message: isWarn
        ? testRes.data.response
        : `Connected successfully!${modelCountText}`,
    }
  } catch (err) {
    providerTestResult.value = {
      status: 'error',
      message: err.response?.data?.detail || err.message || 'Unable to connect to AI provider endpoint.',
    }
  } finally {
    testingProvider.value = false
  }
}

async function handleStep1Next() {
  isSavingProvider.value = true
  try {
    // 1. Create or update provider in DB
    let activeProviderId = providerForm.value.id
    if (!activeProviderId) {
      const res = await AIConfigAPI.createProvider({
        name: providerForm.value.name,
        provider_type: providerForm.value.provider_type,
        base_url: providerForm.value.base_url,
        api_key: providerForm.value.api_key || undefined,
        max_concurrency: providerForm.value.max_concurrency || 1,
        is_active: true,
      })
      activeProviderId = res.data.id
      providerForm.value.id = activeProviderId
    } else {
      await AIConfigAPI.updateProvider(activeProviderId, {
        name: providerForm.value.name,
        provider_type: providerForm.value.provider_type,
        base_url: providerForm.value.base_url,
        api_key: providerForm.value.api_key || undefined,
        max_concurrency: providerForm.value.max_concurrency || 1,
        is_active: true,
      })
    }

    // 2. Set as GLOBAL_DEFAULT binding
    await AIConfigAPI.setBinding('GLOBAL_DEFAULT', {
      provider_id: activeProviderId,
      model_name: providerForm.value.model_name.trim(),
      temperature: 0.2,
      reasoning_effort: 'none',
      extra_kwargs: {},
    })

    uiStore.showToast(`AI Provider '${providerForm.value.name}' configured as Global Default!`, 'success')
    currentStep.value = 2
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save AI provider configuration', 'error')
  } finally {
    isSavingProvider.value = false
  }
}

// Step 2: Candidate CV State
const cvStep = ref('input') // 'input' | 'warning'
const rawCvText = ref('')
const isParsingCv = ref(false)
const isSavingCv = ref(false)
const cvFileRef = ref(null)

function triggerFileInput() {
  cvFileRef.value?.click()
}

async function handleFileUpload(file) {
  if (!file) return
  isParsingCv.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await CandidateProfileAPI.parseFile(formData)
    if (res.data) {
      rawCvText.value = res.data.raw_text || res.data.text || ''
      uiStore.showToast(`CV document '${file.name}' imported successfully!`, 'success')
    }
  } catch (err) {
    uiStore.showToast('Failed to parse uploaded CV file', 'error')
  } finally {
    isParsingCv.value = false
  }
}

function handleFileInput(e) {
  const files = e.target.files
  if (files && files.length > 0) {
    handleFileUpload(files[0])
  }
}

function handleStep2Proceed() {
  if (!rawCvText.value.trim()) {
    currentStep.value = 3
    return
  }
  cvStep.value = 'warning'
}

function handleStep2ConfirmSave() {
  currentStep.value = 3
}

function handleStep2Skip() {
  currentStep.value = 3
}

// Step 3: Feature Toggles & Currency State
const selectedCurrency = ref(uiStore.defaultCurrency || 'USD')
const featureEmailIntake = ref(false)
const featureEmbeddings = ref(true)
const featureAutoCoverLetter = ref(false)
const featureCoverLetterThreshold = ref(70)
const isSavingFeatures = ref(false)

async function handleStep3Save() {
  isSavingFeatures.value = true
  try {
    uiStore.setDefaultCurrency(selectedCurrency.value)
    await SystemSettingsAPI.update({
      enable_email_intake: featureEmailIntake.value,
      enable_embeddings: featureEmbeddings.value,
      enable_auto_cover_letter: featureAutoCoverLetter.value,
      cover_letter_match_threshold: featureCoverLetterThreshold.value,
    })

    uiStore.enableEmailIntake = featureEmailIntake.value
    uiStore.enableEmbeddings = featureEmbeddings.value
    uiStore.enableAutoCoverLetter = featureAutoCoverLetter.value
    uiStore.coverLetterMatchThreshold = featureCoverLetterThreshold.value

    uiStore.showToast('Workspace settings saved!', 'success')
    if (featureEmailIntake.value) {
      emailSubStep.value = 1
      currentStep.value = 4
    } else {
      currentStep.value = readyStepNumber.value
    }
  } catch (err) {
    uiStore.showToast('Failed to save workspace settings', 'error')
  } finally {
    isSavingFeatures.value = false
  }
}

// Dynamic Steps: Step 4 (Conditional Email Setup) & Final Ready Step
const readyStepNumber = computed(() => (featureEmailIntake.value ? 5 : 4))

// Step 4: Email Connection State (Sub-step 1: Choose Provider, Sub-step 2: Configure Credentials)
const emailSubStep = ref(1) // 1: Select Provider, 2: Configure Connection

const oauthConfig = ref({
  google_redirect_uri: `${typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173'}/api/v1/email_accounts/oauth/callback/google`,
  microsoft_redirect_uri: `${typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173'}/api/v1/email_accounts/oauth/callback/microsoft`,
})

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

const selectedEmailProviderKey = ref('gmail')

const IMAP_SUB_PRESETS = [
  { key: 'fastmail', label: 'Fastmail', defaultName: 'Fastmail', host: 'imap.fastmail.com', port: 993 },
  { key: 'yahoo', label: 'Yahoo Mail', defaultName: 'Yahoo Mail', host: 'imap.mail.yahoo.com', port: 993 },
  { key: 'proton', label: 'Proton Mail (Bridge)', defaultName: 'Proton Mail', host: '127.0.0.1', port: 1143 },
  { key: 'zoho', label: 'Zoho Mail', defaultName: 'Zoho Mail', host: 'imap.zoho.com', port: 993 },
  { key: 'aol', label: 'AOL Mail', defaultName: 'AOL Mail', host: 'imap.aol.com', port: 993 },
]
const selectedImapSubPreset = ref('fastmail')

const emailAccountForm = ref({
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
})

const showOAuthGuide = ref(false)
const showClientSecret = ref(false)
const copiedRedirectUri = ref(false)
const isSavingEmail = ref(false)
const emailConnected = ref(false)
const createdEmailAccountId = ref(null)

const QUICK_FOLDERS = ['INBOX', '[Gmail]/All Mail', 'Archive', 'Jobs', 'Recruitment']

const currentEmailProvider = computed(() => {
  return EMAIL_PROVIDER_PRESETS.find((p) => p.key === selectedEmailProviderKey.value) || EMAIL_PROVIDER_PRESETS[0]
})

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

function selectEmailProviderCard(key) {
  selectedEmailProviderKey.value = key
  const p = EMAIL_PROVIDER_PRESETS.find((x) => x.key === key)
  if (!p) return

  emailAccountForm.value.provider_preset = key
  emailAccountForm.value.name = p.defaultName
  emailAccountForm.value.auth_type = p.auth_type
  emailAccountForm.value.auth_method = p.auth_method
  emailAccountForm.value.imap_host = p.host
  emailAccountForm.value.imap_port = p.port

  if (key === 'popular') {
    const sub = IMAP_SUB_PRESETS.find((x) => x.key === selectedImapSubPreset.value) || IMAP_SUB_PRESETS[0]
    emailAccountForm.value.name = sub.defaultName
    emailAccountForm.value.imap_host = sub.host
    emailAccountForm.value.imap_port = sub.port
  }
}

function onEmailAuthMethodToggle(method) {
  emailAccountForm.value.auth_method = method
  if (method === 'oauth') {
    if (selectedEmailProviderKey.value === 'gmail') {
      emailAccountForm.value.auth_type = 'GMAIL_OAUTH'
      emailAccountForm.value.name = 'Gmail Inbox'
    } else if (selectedEmailProviderKey.value === 'outlook') {
      emailAccountForm.value.auth_type = 'MS_GRAPH_OAUTH'
      emailAccountForm.value.name = 'Outlook Inbox'
    }
  } else {
    emailAccountForm.value.auth_type = 'IMAP'
    if (selectedEmailProviderKey.value === 'gmail') {
      emailAccountForm.value.name = 'Gmail (App Password)'
      emailAccountForm.value.imap_host = 'imap.gmail.com'
      emailAccountForm.value.imap_port = 993
    } else if (selectedEmailProviderKey.value === 'outlook') {
      emailAccountForm.value.name = 'Outlook (App Password)'
      emailAccountForm.value.imap_host = 'outlook.office365.com'
      emailAccountForm.value.imap_port = 993
    }
  }
}

function onImapSubPresetChange(presetKey) {
  selectedImapSubPreset.value = presetKey
  const p = IMAP_SUB_PRESETS.find((x) => x.key === presetKey)
  if (p) {
    emailAccountForm.value.name = p.defaultName || p.label
    emailAccountForm.value.imap_host = p.host || ''
    emailAccountForm.value.imap_port = p.port || 993
  }
}

const availableMailFolders = ref([])
const isLoadingFolders = ref(false)
const isCustomFolderMode = ref(false)

async function fetchUserFolders(accountId) {
  let id = accountId || createdEmailAccountId.value
  isLoadingFolders.value = true
  try {
    const listRes = await EmailAccountsAPI.list()
    const accounts = listRes.data || []
    if (accounts.length > 0) {
      const matchingAccount = accounts.slice().reverse().find((a) =>
        (emailAccountForm.value.username && a.username && a.username.toLowerCase() === emailAccountForm.value.username.toLowerCase()) ||
        (emailAccountForm.value.client_id && a.client_id === emailAccountForm.value.client_id) ||
        (a.auth_type === emailAccountForm.value.auth_type && (a.access_token || a.app_password))
      ) || accounts[accounts.length - 1]

      if (matchingAccount) {
        id = matchingAccount.id
        createdEmailAccountId.value = id
        if (matchingAccount.username) emailAccountForm.value.username = matchingAccount.username
        if (matchingAccount.name) emailAccountForm.value.name = matchingAccount.name
      }
    }

    if (!id) return

    const res = await EmailAccountsAPI.getFolders(id)
    if (res.data?.folders && res.data.folders.length > 0) {
      availableMailFolders.value = res.data.folders
      const folderIds = availableMailFolders.value.map((f) => (typeof f === 'object' ? f.id : f))
      if (!emailAccountForm.value.folder || !folderIds.includes(emailAccountForm.value.folder)) {
        const firstFolder = availableMailFolders.value[0]
        emailAccountForm.value.folder = typeof firstFolder === 'object' ? firstFolder.id : firstFolder
      }
      uiStore.showToast(`Discovered ${res.data.folders.length} mailbox folders!`, 'success')
    }
  } catch (err) {
    console.warn('Could not fetch folders:', err)
  } finally {
    isLoadingFolders.value = false
  }
}

let oauthPollInterval = null
let oauthBroadcastChannel = null
const isCheckingOAuthStatus = ref(false)

function stopOAuthWatcher() {
  if (oauthPollInterval) {
    clearInterval(oauthPollInterval)
    oauthPollInterval = null
  }
}

async function handleOAuthSuccess(matchingAccount = null) {
  stopOAuthWatcher()
  emailConnected.value = true
  emailSubStep.value = 3

  try {
    let target = matchingAccount
    if (!target) {
      const listRes = await EmailAccountsAPI.list()
      const accounts = listRes.data || []
      target = accounts.slice().reverse().find((a) =>
        (createdEmailAccountId.value && a.id === createdEmailAccountId.value) ||
        (emailAccountForm.value.client_id && a.client_id === emailAccountForm.value.client_id) ||
        (a.auth_type === emailAccountForm.value.auth_type && (a.access_token || a.app_password))
      ) || accounts[accounts.length - 1]
    }

    if (target) {
      createdEmailAccountId.value = target.id
      if (target.username && target.username !== 'oauth_pending') emailAccountForm.value.username = target.username
      if (target.name) emailAccountForm.value.name = target.name
      if (target.folder) emailAccountForm.value.folder = target.folder
      await fetchUserFolders(target.id)
    }
  } catch (err) {
    console.warn('Error post-oauth account sync:', err)
  }
  uiStore.showToast('Mailbox connected successfully! Please select your mailbox folder & sync schedule.', 'success')
}

async function checkOAuthStatusManually() {
  isCheckingOAuthStatus.value = true
  try {
    const listRes = await EmailAccountsAPI.list()
    const accounts = listRes.data || []
    const match = accounts.slice().reverse().find((a) =>
      (createdEmailAccountId.value && a.id === createdEmailAccountId.value) ||
      (emailAccountForm.value.client_id && a.client_id === emailAccountForm.value.client_id) ||
      (a.auth_type === emailAccountForm.value.auth_type && Boolean(a.access_token))
    )
    if (match && Boolean(match.access_token)) {
      await handleOAuthSuccess(match)
    } else {
      uiStore.showToast('No active OAuth connection detected yet. Please complete sign-in in the popup window.', 'info')
    }
  } catch (err) {
    uiStore.showToast('Failed to verify OAuth status', 'error')
  } finally {
    isCheckingOAuthStatus.value = false
  }
}

async function startOAuthLogin(providerName) {
  if (!emailAccountForm.value.client_id?.trim() || !emailAccountForm.value.client_secret?.trim()) {
    uiStore.showToast('Please enter both OAuth Client ID and Client Secret before authorizing.', 'error')
    return
  }

  isSavingEmail.value = true
  stopOAuthWatcher()
  try {
    const saved = await saveEmailCredentials()
    if (saved?.id) createdEmailAccountId.value = saved.id

    const prov = providerName || selectedEmailProviderKey.value
    const redirectUri = prov === 'outlook'
      ? oauthConfig.value.microsoft_redirect_uri
      : oauthConfig.value.google_redirect_uri

    const res = await EmailAccountsAPI.getOAuthUrl({
      provider: prov === 'outlook' ? 'microsoft' : 'google',
      client_id: emailAccountForm.value.client_id || undefined,
      redirect_uri: redirectUri || undefined,
    })
    if (res.data?.auth_url) {
      const popup = window.open(res.data.auth_url, '_blank', 'width=600,height=700')
      uiStore.showToast('Authorization popup opened. Please sign in to complete connection.', 'info')

      // Start active background poll watching for completion or popup close
      let attempts = 0
      const maxAttempts = 120 // 2 minutes (120 * 1000ms)
      oauthPollInterval = setInterval(async () => {
        attempts++
        if (attempts > maxAttempts) {
          stopOAuthWatcher()
          return
        }

        try {
          const listRes = await EmailAccountsAPI.list()
          const accounts = listRes.data || []
          const match = accounts.slice().reverse().find((a) =>
            (createdEmailAccountId.value && a.id === createdEmailAccountId.value) ||
            (emailAccountForm.value.client_id && a.client_id === emailAccountForm.value.client_id)
          )

          if (match && Boolean(match.access_token) && match.username !== 'oauth_pending') {
            stopOAuthWatcher()
            if (popup && !popup.closed) {
              try { popup.close() } catch {}
            }
            await handleOAuthSuccess(match)
            return
          }

          if (popup && popup.closed && attempts > 2) {
            if (match && Boolean(match.access_token)) {
              stopOAuthWatcher()
              await handleOAuthSuccess(match)
            }
          }
        } catch {
          // ignore transient polling errors
        }
      }, 1000)
    } else {
      uiStore.showToast(res.data?.message || 'Failed to initialize OAuth authorization flow.', 'error')
    }
  } catch (err) {
    const errorDetail = err.response?.data?.detail || err.message || 'Connection failed. Please verify your OAuth client credentials.'
    uiStore.showToast(errorDetail, 'error')
  } finally {
    isSavingEmail.value = false
  }
}

function buildEmailAccountPayload() {
  const isOAuth = emailAccountForm.value.auth_type === 'GMAIL_OAUTH' || emailAccountForm.value.auth_type === 'MS_GRAPH_OAUTH'
  const fallbackUsername = isOAuth ? 'oauth_pending' : ''
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
    sync_schedule_hour: emailAccountForm.value.sync_schedule_hour,
    sync_schedule_min: emailAccountForm.value.sync_schedule_min,
    sync_schedule_day: emailAccountForm.value.sync_schedule_day,
    is_active: emailAccountForm.value.is_active,
  }
}

async function saveEmailCredentials() {
  const payload = buildEmailAccountPayload()
  if (createdEmailAccountId.value) {
    const res = await EmailAccountsAPI.update(createdEmailAccountId.value, payload)
    return res.data
  }
  const res = await EmailAccountsAPI.create(payload)
  if (res.data?.id) {
    createdEmailAccountId.value = res.data.id
  }
  return res.data
}

async function handleStep4SaveEmail() {
  if (!emailAccountForm.value.username?.trim()) {
    uiStore.showToast('Please enter your email address / username.', 'error')
    return
  }
  if (!emailAccountForm.value.app_password?.trim()) {
    uiStore.showToast('Please enter your app password or account password.', 'error')
    return
  }
  if (!emailAccountForm.value.imap_host?.trim()) {
    uiStore.showToast('Please enter an IMAP server host.', 'error')
    return
  }

  isSavingEmail.value = true
  try {
    const saved = await saveEmailCredentials()
    if (saved?.id) {
      createdEmailAccountId.value = saved.id
      await fetchUserFolders(saved.id)
    }
    emailConnected.value = true
    uiStore.showToast('Credentials saved! Set your mailbox sync preferences.', 'success')
    emailSubStep.value = 3
  } catch (err) {
    const errorDetail = err.response?.data?.detail || err.message || 'Failed to connect email account. Please check your credentials.'
    uiStore.showToast(errorDetail, 'error')
  } finally {
    isSavingEmail.value = false
  }
}

async function handleStep4SaveFinalSettings() {
  isSavingEmail.value = true
  try {
    await saveEmailCredentials()
    uiStore.showToast('Email sync preferences saved!', 'success')
    currentStep.value = readyStepNumber.value
  } catch (err) {
    const errorDetail = err.response?.data?.detail || err.message || 'Failed to update email sync preferences.'
    uiStore.showToast(errorDetail, 'error')
  } finally {
    isSavingEmail.value = false
  }
}

function handleStep4SkipEmail() {
  currentStep.value = readyStepNumber.value
}

// Final Step: Launch
const isCompletingOnboarding = ref(false)

async function handleFinishOnboarding() {
  isCompletingOnboarding.value = true
  try {
    // 1. If CV text was provided, ensure it is submitted and queued for background intake extraction
    const trimmedCv = rawCvText.value?.trim() || ''
    if (trimmedCv.length >= 20) {
      try {
        await CandidateProfileAPI.save(trimmedCv)
      } catch (cvErr) {
        console.warn('Could not enqueue candidate CV on wizard completion:', cvErr)
      }
    }

    // 2. Mark onboarding as complete in system settings
    await SystemSettingsAPI.update({
      has_completed_onboarding: true,
    })
    uiStore.hasCompletedOnboarding = true
    uiStore.closeOnboardingWizard()
    uiStore.showToast('Onboarding complete! Candidate profile intake has been queued.', 'success')
    router.push('/')
  } catch (err) {
    uiStore.showToast('Failed to complete onboarding', 'error')
  } finally {
    isCompletingOnboarding.value = false
  }
}

// Pre-populate existing state on mount / open
async function loadExistingState() {
  try {
    selectedCurrency.value = uiStore.defaultCurrency || 'USD'

    // 1. Fetch system settings
    const sysRes = await SystemSettingsAPI.get()
    if (sysRes.data) {
      featureEmailIntake.value = sysRes.data.enable_email_intake ?? false
      featureEmbeddings.value = sysRes.data.enable_embeddings ?? true
      featureAutoCoverLetter.value = sysRes.data.enable_auto_cover_letter ?? false
      featureCoverLetterThreshold.value = sysRes.data.cover_letter_match_threshold ?? 70
    }

    // 2. Fetch providers to pre-select existing global default or first provider
    const provRes = await AIConfigAPI.listProviders()
    const providers = provRes.data || []
    if (providers.length > 0) {
      const p = providers[0]
      providerForm.value = {
        id: p.id,
        name: p.name,
        provider_type: p.provider_type,
        base_url: p.base_url || '',
        api_key: '',
        model_name: 'qwen/qwen3.5-9b',
        max_concurrency: p.max_concurrency || 1,
      }
      const matchedPreset = PRESETS.find((x) => x.type === p.provider_type)
      if (matchedPreset) selectedPresetKey.value = matchedPreset.key
      hasFetchedModels.value = true
    }

    // Fetch existing bindings to pre-populate model
    const bindRes = await AIConfigAPI.listBindings()
    const globalBind = (bindRes.data || []).find((b) => b.task_type === 'GLOBAL_DEFAULT')
    if (globalBind) {
      providerForm.value.model_name = globalBind.model_name || 'qwen/qwen3.5-9b'
      availableModels.value = [providerForm.value.model_name]
    }

    // 3. Fetch existing CV
    const cvRes = await CandidateProfileAPI.get()
    if (cvRes.data) {
      rawCvText.value = cvRes.data.raw_text || ''
    }

    // 4. Fetch OAuth configuration
    try {
      const oauthRes = await EmailAccountsAPI.getOAuthConfig()
      const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173'
      if (oauthRes.data?.google_redirect_uri && oauthRes.data?.microsoft_redirect_uri) {
        if (oauthRes.data.base_url && !oauthRes.data.base_url.includes(':8000')) {
          oauthConfig.value = {
            google_redirect_uri: oauthRes.data.google_redirect_uri,
            microsoft_redirect_uri: oauthRes.data.microsoft_redirect_uri,
          }
        } else {
          oauthConfig.value = {
            google_redirect_uri: `${origin}/api/v1/email_accounts/oauth/callback/google`,
            microsoft_redirect_uri: `${origin}/api/v1/email_accounts/oauth/callback/microsoft`,
          }
        }
      }
    } catch {
      // ignore
    }
  } catch (err) {
    // ignore
  }
}

function handleOAuthMessage(event) {
  if (event.data?.type === 'oauth_success') {
    handleOAuthSuccess()
  }
}

function handleStorageEvent(event) {
  if (event.key === 'jobtracker_oauth_success' && event.newValue) {
    handleOAuthSuccess()
  }
}

onMounted(() => {
  window.addEventListener('message', handleOAuthMessage)
  window.addEventListener('storage', handleStorageEvent)
  try {
    oauthBroadcastChannel = new BroadcastChannel('jobtracker_oauth_channel')
    oauthBroadcastChannel.onmessage = (event) => {
      if (event.data?.type === 'oauth_success') {
        handleOAuthSuccess()
      }
    }
  } catch {
    // BroadcastChannel unsupported fallback
  }

  if (uiStore.isOnboardingWizardOpen) {
    loadExistingState()
  }
})

onUnmounted(() => {
  stopOAuthWatcher()
  window.removeEventListener('message', handleOAuthMessage)
  window.removeEventListener('storage', handleStorageEvent)
  if (oauthBroadcastChannel) {
    try {
      oauthBroadcastChannel.close()
    } catch {}
    oauthBroadcastChannel = null
  }
})

watch(() => uiStore.isOnboardingWizardOpen, (isOpen) => {
  if (isOpen) {
    currentStep.value = 1
    loadExistingState()
  } else {
    stopOAuthWatcher()
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="uiStore.isOnboardingWizardOpen" class="modal-backdrop">
        <div class="wizard-modal-card animate-fade-in" role="dialog" aria-modal="true" aria-labelledby="wizard-modal-title">
          <!-- Modal Header -->
          <div class="wizard-header">
            <div class="header-brand">
              <div class="brand-badge">
                <Sparkles :size="16" class="text-primary" />
              </div>
              <div class="header-brand-text">
                <h2 id="wizard-modal-title" class="wizard-title">Guided Setup &amp; System Configuration</h2>
                <p class="wizard-subtitle">Configure AI model providers, candidate resume intake, and modular feature toggles.</p>
              </div>
            </div>

            <button
              v-if="uiStore.hasCompletedOnboarding"
              class="btn-close"
              @click="uiStore.closeOnboardingWizard()"
              title="Close Setup Wizard"
            >
              <X :size="18" />
            </button>
          </div>

          <!-- Step Indicator Bar -->
          <div class="wizard-stepper-bar">
            <div
              class="step-item"
              :class="{ active: currentStep === 1, completed: currentStep > 1 }"
              @click="currentStep > 1 ? currentStep = 1 : null"
            >
              <div class="step-dot">
                <Check v-if="currentStep > 1" :size="12" />
                <span v-else>1</span>
              </div>
              <span class="step-label">AI Provider</span>
            </div>

            <div class="step-connector" :class="{ completed: currentStep > 1 }"></div>

            <div
              class="step-item"
              :class="{ active: currentStep === 2, completed: currentStep > 2 }"
              @click="currentStep > 2 ? currentStep = 2 : null"
            >
              <div class="step-dot">
                <Check v-if="currentStep > 2" :size="12" />
                <span v-else>2</span>
              </div>
              <span class="step-label">Candidate CV</span>
            </div>

            <div class="step-connector" :class="{ completed: currentStep > 2 }"></div>

            <div
              class="step-item"
              :class="{ active: currentStep === 3, completed: currentStep > 3 }"
              @click="currentStep > 3 ? currentStep = 3 : null"
            >
              <div class="step-dot">
                <Check v-if="currentStep > 3" :size="12" />
                <span v-else>3</span>
              </div>
              <span class="step-label">Feature Setup</span>
            </div>

            <!-- Optional Step 4: Email Connection (if featureEmailIntake enabled) -->
            <template v-if="featureEmailIntake">
              <div class="step-connector" :class="{ completed: currentStep > 4 }"></div>

              <div
                class="step-item"
                :class="{ active: currentStep === 4, completed: currentStep > 4 }"
                @click="currentStep > 4 ? currentStep = 4 : null"
              >
                <div class="step-dot">
                  <Check v-if="currentStep > 4" :size="12" />
                  <span v-else>4</span>
                </div>
                <span class="step-label">Email Account</span>
              </div>
            </template>

            <div class="step-connector" :class="{ completed: currentStep === readyStepNumber }"></div>

            <div
              class="step-item"
              :class="{ active: currentStep === readyStepNumber, completed: currentStep === readyStepNumber }"
            >
              <div class="step-dot">
                <span>{{ readyStepNumber }}</span>
              </div>
              <span class="step-label">Ready</span>
            </div>
          </div>

          <!-- Modal Body Content -->
          <div class="wizard-body">
            <!-- STEP 1 - SUB-STEP 1: CHOOSE AI PROVIDER PRESET -->
            <div v-if="currentStep === 1 && providerSubStep === 1" class="step-content animate-fade-in">
              <div class="step-intro-box">
                <div class="step-heading-row">
                  <Server class="text-primary flex-shrink-0" :size="18" />
                  <h3 class="step-heading">Step 1: Choose Your AI Execution Provider</h3>
                </div>
                <p class="step-desc">
                  Select an offline private engine (LM Studio, Ollama) or enterprise API key (OpenAI, Anthropic, Gemini, OpenRouter) to power resume extraction and job evaluation.
                </p>
              </div>

              <!-- Presets Grid -->
              <div class="presets-grid">
                <button
                  v-for="p in PRESETS"
                  :key="p.key"
                  type="button"
                  class="preset-card"
                  :class="{ active: selectedPresetKey === p.key }"
                  @click="selectPreset(p, true)"
                >
                  <div class="preset-header">
                    <span class="preset-name">{{ p.name }}</span>
                    <div class="flex items-center gap-1.5">
                      <a
                        v-if="p.pricingLink"
                        :href="p.pricingLink"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="preset-pricing-badge"
                        title="View API Pricing &amp; Documentation"
                        @click.stop
                      >
                        <span>Pricing</span>
                        <ExternalLink :size="10" />
                      </a>
                      <span class="badge" :class="p.isPrivate ? 'badge-private' : 'badge-cloud'">
                        <Shield v-if="p.isPrivate" :size="10" />
                        <span>{{ p.badge }}</span>
                      </span>
                    </div>
                  </div>
                  <p class="preset-desc">{{ p.desc }}</p>
                </button>
              </div>

              <!-- Privacy & Zero-Retention Collapsible Section -->
              <div class="privacy-collapsible-card mt-3">
                <button
                  type="button"
                  class="privacy-toggle-btn"
                  @click="isPrivacyExpanded = !isPrivacyExpanded"
                >
                  <div class="flex items-center gap-2">
                    <Shield class="text-primary" :size="16" />
                    <span class="font-semibold text-xs text-main">Privacy &amp; Zero Data-Retention Guarantees</span>
                  </div>
                  <component :is="isPrivacyExpanded ? ChevronUp : ChevronDown" :size="14" class="text-muted" />
                </button>

                <div v-if="isPrivacyExpanded" class="privacy-content animate-fade-in">
                  <p>
                    <strong>Local LLMs (LM Studio &amp; Ollama):</strong> Process 100% of candidate resumes and job communications on your local hardware or home network with zero internet transmission.
                  </p>
                  <p class="mt-2">
                    <strong>Commercial API Keys (OpenAI, Anthropic, Gemini):</strong> Paid API endpoints enforce strict zero-data-retention terms. Your submitted resumes, job descriptions, and chat conversations are <em>never</em> stored or used for model training.
                  </p>
                </div>
              </div>

              <!-- Step 1-1 Footer Actions -->
              <div class="wizard-footer-actions mt-4">
                <div></div>
                <button
                  type="button"
                  class="btn btn-primary"
                  @click="providerSubStep = 2"
                >
                  <span>Configure Connection &amp; Models</span>
                  <ArrowRight :size="14" />
                </button>
              </div>
            </div>

            <!-- STEP 1 - SUB-STEP 2: CONFIGURE ENDPOINT & DISCOVER MODELS -->
            <div v-else-if="currentStep === 1 && providerSubStep === 2" class="step-content animate-fade-in">
              <div class="step-intro-box">
                <div class="step-heading-row">
                  <Server class="text-primary flex-shrink-0" :size="18" />
                  <h3 class="step-heading">Step 1: Configure &amp; Verify AI Connection</h3>
                </div>
                <p class="step-desc">
                  Enter your endpoint details, test connectivity to discover available models, and select your primary model.
                </p>
              </div>

              <!-- Provider Configuration Form -->
              <div class="provider-config-box">
                <div class="input-group">
                  <label class="input-label">Provider Name *</label>
                  <input v-model="providerForm.name" type="text" class="form-input" required />
                </div>

                <div class="form-grid-2">
                  <div class="input-group">
                    <label class="input-label">Base URL Endpoint *</label>
                    <input v-model="providerForm.base_url" type="text" class="form-input font-mono" placeholder="http://... or https://..." required />
                  </div>

                  <div class="input-group">
                    <label class="input-label">API Key (Optional for local)</label>
                    <input v-model="providerForm.api_key" type="password" placeholder="sk-... (leave blank for local)" class="form-input font-mono" />
                  </div>
                </div>

                <!-- Verification & Model Discovery Section -->
                <div class="model-discovery-box">
                  <div class="model-discovery-header">
                    <div class="flex items-center gap-1.5">
                      <Zap :size="15" class="text-primary" />
                      <span class="font-bold text-xs text-main">Endpoint Verification &amp; Model Selection</span>
                    </div>
                    <button
                      type="button"
                      class="model-toggle-mode-btn"
                      @click="customModelMode = !customModelMode"
                    >
                      {{ customModelMode ? 'Use discovered models' : 'Type custom model ID' }}
                    </button>
                  </div>

                  <div class="form-grid-2 items-end">
                    <div class="input-group mb-0">
                      <label class="input-label">Step A: Verify Endpoint</label>
                      <button
                        type="button"
                        class="btn btn-secondary w-full"
                        :disabled="testingProvider || !providerForm.base_url"
                        @click="testConnection"
                      >
                        <Loader2 v-if="testingProvider" class="animate-spin" :size="14" />
                        <Zap v-else :size="14" />
                        <span>{{ testingProvider ? 'Discovering Models...' : 'Test & Fetch Models' }}</span>
                      </button>
                    </div>

                    <div class="input-group mb-0">
                      <label class="input-label">Step B: Default Model Identifier *</label>

                      <!-- Discovered Models Dropdown (Enabled after fetch or if models exist) -->
                      <select
                        v-if="!customModelMode && (hasFetchedModels || availableModels.length > 0)"
                        v-model="providerForm.model_name"
                        class="form-input font-mono"
                        :disabled="!hasFetchedModels && availableModels.length === 0"
                        required
                      >
                        <option v-for="m in availableModels" :key="m" :value="m">
                          {{ m }}
                        </option>
                      </select>

                      <!-- Disabled prompt if not fetched yet -->
                      <input
                        v-else-if="!customModelMode && !hasFetchedModels"
                        type="text"
                        disabled
                        placeholder="Click 'Test & Fetch Models' first..."
                        class="form-input font-mono opacity-60 cursor-not-allowed"
                      />

                      <!-- Text input fallback when in custom model mode -->
                      <input
                        v-else
                        v-model="providerForm.model_name"
                        type="text"
                        placeholder="e.g. qwen/qwen3.5-9b, gpt-4o-mini"
                        class="form-input font-mono"
                        required
                      />
                    </div>
                  </div>

                  <!-- Connection Ping Status Message -->
                  <div v-if="providerTestResult" class="test-result-badge" :class="`is-${providerTestResult.status}`">
                    <CheckCircle2 v-if="providerTestResult.status === 'success'" :size="14" />
                    <Info v-else :size="14" />
                    <span>{{ providerTestResult.message }}</span>
                  </div>
                </div>
              </div>

              <!-- Step 1-2 Footer Actions -->
              <div class="wizard-footer-actions mt-4">
                <button type="button" class="btn btn-secondary" @click="providerSubStep = 1">
                  <ArrowLeft :size="14" />
                  <span>Back to Providers</span>
                </button>

                <button
                  type="button"
                  class="btn btn-primary"
                  :disabled="isSavingProvider || !providerForm.model_name || (!hasFetchedModels && !customModelMode)"
                  @click="handleStep1Next"
                >
                  <Loader2 v-if="isSavingProvider" class="animate-spin" :size="14" />
                  <span>Save &amp; Continue to CV Intake</span>
                  <ArrowRight :size="14" />
                </button>
              </div>
            </div>

            <!-- STEP 2: CANDIDATE CV INTAKE -->
            <div v-else-if="currentStep === 2" class="step-content animate-fade-in">
              <div class="step-intro-box">
                <div class="step-heading-row">
                  <UserCheck class="text-primary flex-shrink-0" :size="18" />
                  <h3 class="step-heading">Step 2: Candidate Resume &amp; Skills Intake</h3>
                </div>
                <p class="step-desc">
                  Provide your resume to enable AI fit scoring, competency matching, and personalized interview guide generation.
                </p>
              </div>

              <!-- Sub-step 1: Raw Input (Button to import + text field under) -->
              <div v-if="cvStep === 'input'" class="cv-intake-container animate-fade-in mt-3">
                <div class="cv-toolbar">
                  <label class="input-label mb-0">Paste Resume / CV</label>
                  <div>
                    <input
                      ref="cvFileRef"
                      type="file"
                      accept=".pdf,.docx,.doc,.txt"
                      class="hidden-file-input"
                      @change="handleFileInput"
                    />
                    <button
                      type="button"
                      class="btn btn-secondary btn-sm"
                      :disabled="isParsingCv"
                      @click="triggerFileInput"
                    >
                      <Loader2 v-if="isParsingCv" class="animate-spin" :size="13" />
                      <Upload v-else :size="13" />
                      <span>{{ isParsingCv ? 'Extracting File...' : 'Import Document (.pdf, .docx, .txt)' }}</span>
                    </button>
                  </div>
                </div>

                <textarea
                  v-model="rawCvText"
                  rows="11"
                  class="form-textarea font-mono text-xs"
                  placeholder="Paste your complete resume or CV text here or click 'Import Document' above..."
                  required
                ></textarea>

                <!-- Step 2 Input Footer Actions -->
                <div class="wizard-footer-actions mt-4">
                  <button type="button" class="btn btn-secondary" @click="currentStep = 1; providerSubStep = 2">
                    <ArrowLeft :size="14" />
                    <span>Back</span>
                  </button>

                  <button
                    type="button"
                    class="btn btn-primary"
                    :disabled="!rawCvText.trim()"
                    @click="handleStep2Proceed"
                  >
                    <Sparkles :size="14" />
                    <span>Save Profile &amp; Continue</span>
                    <ArrowRight :size="14" />
                  </button>
                </div>
              </div>

              <!-- Sub-step 2: Privacy Notice & Scrubbing Alert -->
              <div v-else-if="cvStep === 'warning'" class="cv-warning-container animate-fade-in mt-3">
                <div class="privacy-warning-box">
                  <div class="warning-icon-wrapper">
                    <AlertTriangle :size="28" class="warning-icon" />
                  </div>
                  <div class="warning-content">
                    <h4 class="warning-title">Privacy Notice: AI Data Transmission</h4>
                    <p class="warning-description">
                      You are about to send this CV text to the AI provider for automated analysis, qualification matching, and skill extraction.
                    </p>
                    <p class="warning-advice">
                      It is strongly advised that you scrub any sensitive personal information (such as full legal names, personal phone numbers, home addresses, private emails, or confidential identifiers) from the input before proceeding.
                    </p>
                  </div>
                </div>

                <!-- Step 2 Warning Footer Actions -->
                <div class="wizard-footer-actions mt-4">
                  <button type="button" class="btn btn-secondary" @click="cvStep = 'input'">
                    <ArrowLeft :size="14" />
                    <span>Back to Edit</span>
                  </button>

                  <button
                    type="button"
                    class="btn btn-primary"
                    @click="handleStep2ConfirmSave"
                  >
                    <Sparkles :size="14" />
                    <span>Confirm &amp; Continue</span>
                    <ArrowRight :size="14" />
                  </button>
                </div>
              </div>
            </div>

            <!-- STEP 3: FEATURE TOGGLES & WORKSPACE SETUP -->
            <div v-else-if="currentStep === 3" class="step-content animate-fade-in">
              <div class="step-intro-box">
                <div class="step-heading-row">
                  <SlidersHorizontal class="text-primary flex-shrink-0" :size="18" />
                  <h3 class="step-heading">Step 3: Workspace Preferences &amp; Automations</h3>
                </div>
                <p class="step-desc">
                  Set your base compensation currency and select automated subsystems to activate.
                </p>
              </div>

              <!-- Default Currency Selection Box as Dropdown -->
              <div class="currency-preference-box">
                <div class="input-group mb-0">
                  <div class="label-with-hint">
                    <div class="flex items-center gap-1.5">
                      <DollarSign :size="15" class="text-primary" />
                      <label class="input-label mb-0">Default System Currency</label>
                    </div>
                    <span class="currency-selected-badge">{{ selectedCurrency }}</span>
                  </div>
                  <select v-model="selectedCurrency" class="form-input">
                    <option
                      v-for="c in uiStore.SUPPORTED_CURRENCIES"
                      :key="c.code"
                      :value="c.code"
                    >
                      {{ c.code }} ({{ c.symbol }}) &mdash; {{ c.label }}
                    </option>
                  </select>
                  <span class="preference-field-hint">
                    Used for salary ranges, offer packages, and automatic currency conversion during job intake.
                  </span>
                </div>
              </div>

              <div class="feature-toggles-list">
                <!-- Email Auto-Sync Selection Card -->
                <div
                  class="selection-card"
                  :class="{ 'card-active': featureEmailIntake }"
                  @click="featureEmailIntake = !featureEmailIntake"
                  role="button"
                  tabindex="0"
                  @keydown.space.prevent="featureEmailIntake = !featureEmailIntake"
                  @keydown.enter.prevent="featureEmailIntake = !featureEmailIntake"
                >
                  <div class="card-icon-wrapper">
                    <CheckCircle2 v-if="featureEmailIntake" class="icon-active" :size="20" />
                    <Circle v-else class="icon-inactive" :size="20" />
                  </div>
                  <div class="option-content">
                    <div class="option-title-row">
                      <Mail :size="16" class="text-primary flex-shrink-0" />
                      <span class="option-label">Email Account Auto-Sync</span>
                    </div>
                    <span class="option-description">Automatically fetch recruitment emails via OAuth or IMAP and extract job updates.</span>
                  </div>
                </div>

                <!-- Vector Knowledge & Embeddings Selection Card -->
                <div
                  class="selection-card"
                  :class="{ 'card-active': featureEmbeddings }"
                  @click="featureEmbeddings = !featureEmbeddings"
                  role="button"
                  tabindex="0"
                  @keydown.space.prevent="featureEmbeddings = !featureEmbeddings"
                  @keydown.enter.prevent="featureEmbeddings = !featureEmbeddings"
                >
                  <div class="card-icon-wrapper">
                    <CheckCircle2 v-if="featureEmbeddings" class="icon-active" :size="20" />
                    <Circle v-else class="icon-inactive" :size="20" />
                  </div>
                  <div class="option-content">
                    <div class="option-title-row">
                      <Cpu :size="16" class="text-primary flex-shrink-0" />
                      <span class="option-label">Vector Knowledge &amp; Embeddings (pgvector)</span>
                    </div>
                    <span class="option-description">Generate dense vector representations for semantic search across applications.</span>
                  </div>
                </div>

                <!-- Automated Cover Letters Selection Card -->
                <div
                  class="selection-card"
                  :class="{ 'card-active': featureAutoCoverLetter }"
                  @click="featureAutoCoverLetter = !featureAutoCoverLetter"
                  role="button"
                  tabindex="0"
                  @keydown.space.prevent="featureAutoCoverLetter = !featureAutoCoverLetter"
                  @keydown.enter.prevent="featureAutoCoverLetter = !featureAutoCoverLetter"
                >
                  <div class="card-icon-wrapper">
                    <CheckCircle2 v-if="featureAutoCoverLetter" class="icon-active" :size="20" />
                    <Circle v-else class="icon-inactive" :size="20" />
                  </div>
                  <div class="option-content">
                    <div class="option-title-row">
                      <FileText :size="16" class="text-primary flex-shrink-0" />
                      <span class="option-label">Automated Cover Letter Generation</span>
                    </div>
                    <span class="option-description">Automatically draft tailored cover letters during intake when fit score passes threshold.</span>

                    <!-- Expandable Minimum Fit Threshold Slider -->
                    <div
                      v-if="featureAutoCoverLetter"
                      class="threshold-config-box mt-3 pt-3 border-t border-subtle w-full"
                      @click.stop
                    >
                      <div class="flex justify-between items-center mb-1.5">
                        <span class="threshold-label text-xs text-secondary font-medium">Minimum Fit Threshold:</span>
                        <span class="threshold-badge font-mono text-xs font-semibold px-2 py-0.5 rounded bg-primary-subtle text-primary border border-primary-glow">
                          {{ featureCoverLetterThreshold }}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        v-model.number="featureCoverLetterThreshold"
                        class="form-range w-full"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 3 Footer Actions -->
              <div class="wizard-footer-actions mt-4">
                <button type="button" class="btn btn-secondary" @click="currentStep = 2">
                  <ArrowLeft :size="14" />
                  <span>Back</span>
                </button>

                <button
                  type="button"
                  class="btn btn-primary"
                  :disabled="isSavingFeatures"
                  @click="handleStep3Save"
                >
                  <Loader2 v-if="isSavingFeatures" class="animate-spin" :size="14" />
                  <span>{{ featureEmailIntake ? 'Continue to Email Connection' : 'Save & Continue to Final Launch' }}</span>
                  <ArrowRight :size="14" />
                </button>
              </div>
            </div>

            <!-- STEP 4: EMAIL ACCOUNT SETUP (CONDITIONAL IF EMAIL SYNC ENABLED) -->
            <div v-else-if="currentStep === 4 && featureEmailIntake" class="step-content animate-fade-in">
              <!-- SUB-STEP 1: SELECT EMAIL PROVIDER CARD -->
              <div v-if="emailSubStep === 1" class="email-substep-container animate-fade-in">
                <div class="step-intro-box">
                  <div class="step-heading-row">
                    <Mail class="text-primary flex-shrink-0" :size="18" />
                    <h3 class="step-heading">Step 4: Select Recruitment Email Provider</h3>
                  </div>
                  <p class="step-desc">
                    Choose your recruitment email service to configure automated mailbox synchronization for applications and recruiter updates.
                  </p>
                </div>

                <!-- Provider Presets Grid (5 Cards) -->
                <div class="provider-presets-grid-5 mt-4">
                  <button
                    v-for="provider in EMAIL_PROVIDER_PRESETS"
                    :key="provider.key"
                    type="button"
                    class="email-provider-card"
                    :class="{ active: selectedEmailProviderKey === provider.key }"
                    @click="selectEmailProviderCard(provider.key)"
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
                      <div class="selection-radio" :class="{ 'radio-checked': selectedEmailProviderKey === provider.key }">
                        <div v-if="selectedEmailProviderKey === provider.key" class="radio-inner" />
                      </div>
                      <span class="text-xs font-semibold" :class="selectedEmailProviderKey === provider.key ? 'text-primary' : 'text-secondary'">
                        {{ selectedEmailProviderKey === provider.key ? 'Selected' : 'Select' }}
                      </span>
                    </div>
                  </button>
                </div>

                <!-- Sub-step 1 Footer Actions -->
                <div class="wizard-footer-actions mt-5">
                  <button type="button" class="btn btn-secondary" @click="currentStep = 3">
                    <ArrowLeft :size="14" />
                    <span>Back</span>
                  </button>

                  <div class="flex items-center gap-2">
                    <button type="button" class="btn btn-ghost text-secondary" @click="handleStep4SkipEmail">
                      Configure Later in Settings
                    </button>

                    <button
                      type="button"
                      class="btn btn-primary"
                      @click="emailSubStep = 2"
                    >
                      <span>Continue to Connection</span>
                      <ArrowRight :size="14" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- SUB-STEP 2: CONFIGURE CONNECTION CREDENTIALS -->
              <div v-else-if="emailSubStep === 2" class="email-substep-container animate-fade-in">
                <div class="step-intro-box">
                  <div class="step-heading-row">
                    <Mail class="text-primary flex-shrink-0" :size="18" />
                    <h3 class="step-heading">Step 4: Enter {{ currentEmailProvider.name }} Credentials</h3>
                  </div>
                  <p class="step-desc">
                    Provide credentials to connect and authenticate your {{ currentEmailProvider.name }} inbox.
                  </p>
                </div>

                <!-- Auth Mode Switch (Only for Gmail & Outlook that support both OAuth2 and IMAP) -->
                <div v-if="currentEmailProvider.supportsOAuth" class="auth-toggle-group mt-4 mb-4">
                  <label class="input-label mb-2 block">Authentication Method</label>
                  <div class="auth-method-toggle">
                    <button
                      type="button"
                      class="auth-toggle-btn"
                      :class="{ active: emailAccountForm.auth_method === 'oauth' }"
                      @click="onEmailAuthMethodToggle('oauth')"
                    >
                      <Lock :size="14" />
                      <span>OAuth2 Connect <span class="auth-badge recommended">Recommended</span></span>
                    </button>
                    <button
                      type="button"
                      class="auth-toggle-btn"
                      :class="{ active: emailAccountForm.auth_method === 'app_password' }"
                      @click="onEmailAuthMethodToggle('app_password')"
                    >
                      <Key :size="14" />
                      <span>Email &amp; App Password</span>
                    </button>
                  </div>
                </div>

                <!-- OAuth2 Mode Box -->
                <div
                  v-if="currentEmailProvider.supportsOAuth && emailAccountForm.auth_method === 'oauth'"
                  class="email-config-box mt-4"
                >
                  <!-- Authorized Redirect URI Box -->
                  <div class="oauth-redirect-box">
                    <div class="label-with-hint mb-1">
                      <span class="redirect-uri-label">Authorized Redirect URI (Copy to Console)</span>
                      <button
                        type="button"
                        class="btn-copy-uri"
                        @click="copyRedirectUri(selectedEmailProviderKey === 'outlook' ? oauthConfig.microsoft_redirect_uri : oauthConfig.google_redirect_uri)"
                      >
                        <Check v-if="copiedRedirectUri" :size="12" class="text-success" />
                        <Copy v-else :size="12" />
                        <span>{{ copiedRedirectUri ? 'Copied!' : 'Copy URI' }}</span>
                      </button>
                    </div>
                    <div class="uri-display font-mono">
                      {{ selectedEmailProviderKey === 'outlook' ? oauthConfig.microsoft_redirect_uri : oauthConfig.google_redirect_uri }}
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
                          {{ selectedEmailProviderKey === 'gmail' ? 'Google Cloud OAuth Setup Guide' : 'Microsoft Entra ID / Azure OAuth Setup Guide' }}
                        </span>
                      </div>
                      <component :is="showOAuthGuide ? ChevronUp : ChevronDown" :size="14" class="text-muted" />
                    </button>

                    <div v-if="showOAuthGuide" class="guide-content animate-fade-in">
                      <ol v-if="selectedEmailProviderKey === 'gmail'" class="guide-steps-list">
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
                  <div class="input-group">
                    <label class="input-label">Account Label *</label>
                    <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Personal Gmail" class="form-input" required />
                  </div>

                  <div class="input-group">
                    <label class="input-label">OAuth Client ID *</label>
                    <input
                      v-model="emailAccountForm.client_id"
                      type="text"
                      :placeholder="selectedEmailProviderKey === 'gmail' ? 'e.g. 12345-abc.apps.googleusercontent.com' : 'e.g. 00000000-0000-0000-0000-000000000000'"
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
                </div>

                <!-- App Password / Direct IMAP Mode Box -->
                <div v-else class="email-config-box mt-4">
                  <!-- App Password Callout for Gmail / Outlook -->
                  <div v-if="selectedEmailProviderKey === 'gmail' || selectedEmailProviderKey === 'outlook'" class="app-password-callout">
                    <Info :size="14" class="text-primary flex-shrink-0 mt-0.5" />
                    <div class="text-xs text-secondary leading-relaxed">
                      <span v-if="selectedEmailProviderKey === 'gmail'">
                        Google requires an <strong>App Password</strong> if 2-Step Verification is enabled. Generate one at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" class="guide-link">Google Account Security <ExternalLink :size="10" /></a>.
                      </span>
                      <span v-else>
                        Microsoft accounts with 2FA require generating an App Password in your Microsoft Account Security settings.
                      </span>
                    </div>
                  </div>

                  <!-- Popular IMAP Provider Dropdown (if popular group chosen) -->
                  <div v-if="selectedEmailProviderKey === 'popular'" class="form-grid-2">
                    <div class="input-group">
                      <label class="input-label">Select Service Provider</label>
                      <select
                        v-model="selectedImapSubPreset"
                        class="form-input"
                        @change="onImapSubPresetChange(selectedImapSubPreset)"
                      >
                        <option v-for="p in IMAP_SUB_PRESETS" :key="p.key" :value="p.key">
                          {{ p.label }}
                        </option>
                      </select>
                    </div>

                    <div class="input-group">
                      <label class="input-label">Account Label *</label>
                      <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Work Mailbox" class="form-input" required />
                    </div>
                  </div>

                  <!-- Standard Account Label (if not popular group) -->
                  <div v-else class="input-group">
                    <label class="input-label">Account Label *</label>
                    <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Work Mailbox" class="form-input" required />
                  </div>

                  <div class="form-grid-2">
                    <div class="input-group">
                      <label class="input-label">Email Address / Login *</label>
                      <input v-model="emailAccountForm.username" type="email" placeholder="user@domain.com" class="form-input font-mono" required />
                    </div>

                    <div class="input-group">
                      <label class="input-label">
                        {{ (selectedEmailProviderKey === 'gmail' || selectedEmailProviderKey === 'outlook' || selectedEmailProviderKey === 'icloud') ? 'App Password / Password *' : 'Password / App Password *' }}
                      </label>
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
                  </div>

                  <div class="form-grid-2">
                    <div class="input-group">
                      <label class="input-label">IMAP Host *</label>
                      <input
                        v-model="emailAccountForm.imap_host"
                        type="text"
                        :disabled="selectedEmailProviderKey === 'gmail' || selectedEmailProviderKey === 'outlook' || selectedEmailProviderKey === 'icloud'"
                        placeholder="imap.mail.com"
                        class="form-input font-mono"
                        required
                      />
                    </div>

                    <div class="input-group">
                      <label class="input-label">IMAP Port *</label>
                      <input
                        v-model.number="emailAccountForm.imap_port"
                        type="number"
                        :disabled="selectedEmailProviderKey === 'gmail' || selectedEmailProviderKey === 'outlook' || selectedEmailProviderKey === 'icloud'"
                        placeholder="993"
                        class="form-input font-mono"
                        required
                      />
                    </div>
                  </div>
                </div>

                <!-- Sub-step 2 Footer Actions -->
                <div class="wizard-footer-actions mt-4">
                  <button type="button" class="btn btn-secondary" @click="emailSubStep = 1">
                    <ArrowLeft :size="14" />
                    <span>Back to Providers</span>
                  </button>

                  <div class="flex items-center gap-2">
                    <button type="button" class="btn btn-ghost text-secondary" @click="handleStep4SkipEmail">
                      Configure Later in Settings
                    </button>

                    <button
                      v-if="currentEmailProvider.supportsOAuth && emailAccountForm.auth_method === 'oauth'"
                      type="button"
                      class="btn btn-primary"
                      :disabled="isSavingEmail || !emailAccountForm.client_id?.trim() || !emailAccountForm.client_secret?.trim()"
                      @click="startOAuthLogin(selectedEmailProviderKey)"
                    >
                      <Loader2 v-if="isSavingEmail" class="animate-spin" :size="14" />
                      <Lock v-else :size="14" />
                      <span>Authorize &amp; Set Preferences</span>
                      <ArrowRight :size="14" />
                    </button>

                    <button
                      v-else
                      type="button"
                      class="btn btn-primary"
                      :disabled="isSavingEmail || !emailAccountForm.username?.trim() || !emailAccountForm.app_password?.trim() || !emailAccountForm.imap_host?.trim()"
                      @click="handleStep4SaveEmail"
                    >
                      <Loader2 v-if="isSavingEmail" class="animate-spin" :size="14" />
                      <Save v-else :size="14" />
                      <span>Save &amp; Set Preferences</span>
                      <ArrowRight :size="14" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- SUB-STEP 3: MAILBOX FOLDER & SYNC PREFERENCES -->
              <div v-else-if="emailSubStep === 3" class="email-substep-container animate-fade-in">
                <div class="step-intro-box">
                  <div class="step-heading-row">
                    <Folder class="text-primary flex-shrink-0" :size="18" />
                    <h3 class="step-heading">Step 4: Mailbox Folder &amp; Sync Preferences</h3>
                  </div>
                  <p class="step-desc">
                    Choose which mailbox folder to monitor for job applications and configure automated sync timing for <strong>{{ emailAccountForm.name }}</strong>.
                  </p>
                </div>

                <!-- Account Status Banner -->
                <div class="account-connected-banner mt-4 mb-4">
                  <div class="flex items-center gap-2">
                    <CheckCircle2 class="text-success flex-shrink-0" :size="16" />
                    <span class="text-xs font-semibold text-main">
                      Connected: {{ emailAccountForm.name }}
                      <span v-if="emailAccountForm.username && emailAccountForm.username !== 'oauth_pending'" class="text-muted font-normal">({{ emailAccountForm.username }})</span>
                    </span>
                  </div>
                  <span class="auth-badge-connected">Ready for Sync</span>
                </div>

                <!-- Sync & Folder Config Box -->
                <div class="email-config-box mt-4">
                  <!-- Mailbox Folder Section -->
                  <div class="input-group">
                    <div class="label-with-hint mb-1.5">
                      <label class="input-label">Target Mailbox Folder *</label>
                      <span class="folder-tip-text">
                        (Tip: Dedicated folder or email prefiltering recommended)
                      </span>
                    </div>

                    <!-- Discovered Folders Dropdown / Custom Input Row -->
                    <div class="folder-selection-row">
                      <div class="flex-1 relative">
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
                        class="btn btn-secondary btn-sm"
                        @click="isCustomFolderMode = !isCustomFolderMode; if (!isCustomFolderMode && availableMailFolders.length > 0) emailAccountForm.folder = typeof availableMailFolders[0] === 'object' ? availableMailFolders[0].id : availableMailFolders[0]"
                      >
                        <span>{{ isCustomFolderMode ? 'Choose from List' : 'Custom Path' }}</span>
                      </button>

                      <button
                        type="button"
                        class="btn btn-ghost btn-sm text-secondary"
                        :disabled="isLoadingFolders || !createdEmailAccountId"
                        title="Re-scan mailbox folders"
                        @click="fetchUserFolders()"
                      >
                        <Loader2 v-if="isLoadingFolders" class="animate-spin" :size="14" />
                        <RefreshCw v-else :size="14" />
                      </button>
                    </div>

                    <div v-if="isLoadingFolders" class="flex items-center gap-1.5 text-xs text-primary mt-1.5">
                      <Loader2 class="animate-spin" :size="12" />
                      <span>Scanning available mailbox folders from {{ currentEmailProvider.name }}...</span>
                    </div>

                    <p class="field-help-text mt-1.5">
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
                        <select v-model="emailAccountForm.sync_schedule_hour" class="form-input font-mono">
                          <option v-for="h in 24" :key="h" :value="String(h - 1).padStart(2, '0')">
                            {{ String(h - 1).padStart(2, '0') }}:00
                          </option>
                        </select>
                        <span class="text-muted font-bold">:</span>
                        <select v-model="emailAccountForm.sync_schedule_min" class="form-input font-mono">
                          <option value="00">00</option>
                          <option value="15">15</option>
                          <option value="30">30</option>
                          <option value="45">45</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Sub-step 3 Footer Actions -->
                <div class="wizard-footer-actions mt-4">
                  <button type="button" class="btn btn-secondary" @click="emailSubStep = 2">
                    <ArrowLeft :size="14" />
                    <span>Back to Credentials</span>
                  </button>

                  <div class="flex items-center gap-2">
                    <button type="button" class="btn btn-ghost text-secondary" @click="handleStep4SkipEmail">
                      Skip &amp; Use Defaults
                    </button>

                    <button
                      type="button"
                      class="btn btn-primary"
                      :disabled="isSavingEmail || !emailAccountForm.folder?.trim()"
                      @click="handleStep4SaveFinalSettings"
                    >
                      <Loader2 v-if="isSavingEmail" class="animate-spin" :size="14" />
                      <Check v-else :size="14" />
                      <span>Save &amp; Complete Setup</span>
                      <ArrowRight :size="14" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- FINAL STEP: COMPLETION & LAUNCH -->
            <div v-else-if="currentStep === readyStepNumber" class="step-content animate-fade-in">
              <div class="ready-hero-box">
                <div class="hero-success-icon">
                  <Rocket class="text-primary" :size="26" />
                </div>
                <div class="ready-hero-text">
                  <h3 class="step-heading">Setup Complete &amp; System Ready!</h3>
                  <p class="step-desc">
                    Your JobTracker application environment is fully configured and ready for tracking job leads.
                  </p>
                </div>
              </div>

              <!-- Summary Card -->
              <div class="summary-card mt-4">
                <h4 class="summary-card-title">Configured Environment Summary</h4>

                <div class="summary-grid">
                  <div class="summary-item">
                    <span class="summary-label">AI Execution Provider:</span>
                    <span class="summary-value font-mono">{{ providerForm.name }} ({{ providerForm.model_name }})</span>
                  </div>

                  <div class="summary-item">
                    <span class="summary-label">Candidate Profile:</span>
                    <span class="summary-value">{{ rawCvText.trim() ? 'CV Uploaded & Saved' : 'Skipped (Can add later in Settings)' }}</span>
                  </div>

                  <div class="summary-item">
                    <span class="summary-label">Default Currency:</span>
                    <span class="summary-value font-mono font-bold text-primary">{{ selectedCurrency }}</span>
                  </div>

                  <div class="summary-item">
                    <span class="summary-label">Email Account Sync:</span>
                    <span
                      class="summary-value"
                      :class="featureEmailIntake ? (emailConnected ? 'text-success' : 'text-primary') : 'text-muted'"
                    >
                      {{ featureEmailIntake ? (emailConnected ? 'Connected & Active' : 'Enabled (Configure in Settings)') : 'Disabled' }}
                    </span>
                  </div>

                  <div class="summary-item">
                    <span class="summary-label">Vector Embeddings:</span>
                    <span class="summary-value" :class="featureEmbeddings ? 'text-success' : 'text-muted'">
                      {{ featureEmbeddings ? 'Enabled' : 'Disabled' }}
                    </span>
                  </div>

                  <div class="summary-item">
                    <span class="summary-label">Automated Cover Letters:</span>
                    <span class="summary-value" :class="featureAutoCoverLetter ? 'text-success' : 'text-muted'">
                      {{ featureAutoCoverLetter ? `Enabled (≥ ${featureCoverLetterThreshold}%)` : 'Disabled' }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Launch Button -->
              <div class="ready-footer-actions">
                <button
                  type="button"
                  class="btn btn-primary btn-lg shadow-glow"
                  :disabled="isCompletingOnboarding"
                  @click="handleFinishOnboarding"
                >
                  <Loader2 v-if="isCompletingOnboarding" class="animate-spin" :size="18" />
                  <Rocket v-else :size="18" />
                  <span>Start Tracking Jobs Now</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: var(--bg-backdrop, rgba(0, 0, 0, 0.75));
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.97);
}

.wizard-modal-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  width: 100%;
  max-width: 760px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: 90vh;
}

.wizard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-subtle);
  background-color: var(--bg-sidebar);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-badge {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header-brand-text {
  display: flex;
  flex-direction: column;
}

.wizard-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.2;
}

.wizard-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
  line-height: 1.3;
}

.wizard-stepper-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background-color: var(--bg-main);
  border-bottom: 1px solid var(--border-subtle);
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: default;
}

.step-item.completed, .step-item.active {
  cursor: pointer;
}

.step-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-item.active .step-dot {
  background-color: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
}

.step-item.completed .step-dot {
  background-color: var(--bg-surface);
  border-color: var(--primary);
  color: var(--primary);
}

.step-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.step-item.active .step-label {
  color: var(--text-main);
  font-weight: 700;
}

.step-connector {
  flex: 1;
  height: 2px;
  background-color: var(--border-color);
  margin: 0 12px;
}

.step-connector.completed {
  background-color: var(--primary);
}

.wizard-body {
  padding: 24px;
  overflow-y: auto;
  max-height: calc(90vh - 140px);
}

.step-heading-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.step-heading {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.2;
}

.step-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 16px;
}

@media (max-width: 600px) {
  .presets-grid {
    grid-template-columns: 1fr;
  }
}

.preset-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.preset-card:hover {
  border-color: var(--border-focus);
}

.preset-card.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.preset-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 6px;
}

.preset-pricing-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 9px;
  font-weight: 600;
  color: var(--primary);
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  padding: 1px 5px;
  border-radius: 3px;
  text-decoration: none;
  transition: all var(--transition-fast, 0.15s ease);
}

.preset-pricing-badge:hover {
  background-color: var(--primary);
  color: white;
}

.preset-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.preset-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 0;
}

.model-toggle-mode-btn {
  font-size: 11px;
  color: var(--primary);
  text-decoration: underline;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  font-weight: 500;
}

.model-toggle-mode-btn:hover {
  color: var(--primary-hover, #6366f1);
}

.badge-private {
  background-color: rgba(16, 185, 129, 0.12);
  color: var(--success, #10b981);
  border: 1px solid rgba(16, 185, 129, 0.3);
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-cloud {
  background-color: rgba(59, 130, 246, 0.12);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.2;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 600px) {
  .form-grid-2 {
    grid-template-columns: 1fr;
  }
}

.label-with-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.provider-config-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.model-discovery-box {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-discovery-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.test-ping-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
}

.test-result-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
}

.test-result-badge.is-success {
  background-color: rgba(16, 185, 129, 0.12);
  color: var(--success, #10b981);
}

.test-result-badge.is-error {
  background-color: rgba(239, 68, 68, 0.12);
  color: var(--danger, #ef4444);
}

.privacy-collapsible-card {
  margin-top: 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-main);
  overflow: hidden;
}

.privacy-toggle-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: transparent;
  border: none;
  cursor: pointer;
}

.privacy-content {
  padding: 12px 14px;
  border-top: 1px solid var(--border-subtle);
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
  background-color: var(--bg-surface);
}

.wizard-footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
}

.ready-footer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 24px;
}

.cv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.hidden-file-input {
  display: none;
}

.form-textarea {
  width: 100%;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 12px;
  color: var(--text-main);
  resize: vertical;
  line-height: 1.5;
}

.privacy-warning-box {
  display: flex;
  gap: 16px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-left: 4px solid #eab308;
  border-radius: var(--radius-sm);
  padding: 20px;
  align-items: flex-start;
}

.warning-icon-wrapper {
  background-color: rgba(234, 179, 8, 0.12);
  border-radius: var(--radius-sm);
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.warning-icon {
  color: #eab308;
}

.warning-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.warning-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.warning-description {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.warning-advice {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.currency-preference-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-top: 16px;
}

.currency-selected-badge {
  font-size: 11px;
  font-weight: 700;
  font-family: monospace;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.preference-field-hint {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-top: 4px;
}

.feature-toggles-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.selection-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  cursor: pointer;
  transition: all var(--transition-fast, 0.2s ease);
  outline: none;
  user-select: none;
}

.selection-card:hover {
  background-color: var(--bg-surface-hover, var(--bg-elevated));
  border-color: var(--border-focus, var(--primary));
}

.selection-card:focus-visible {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-glow);
}

.selection-card.card-active {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
}

.card-icon-wrapper {
  margin-top: 2px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-active {
  color: var(--primary);
}

.icon-inactive {
  color: var(--text-muted);
  opacity: 0.6;
}

.option-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.option-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 2px;
}

.option-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.option-description {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.threshold-config-box {
  cursor: default;
}

.threshold-label {
  font-size: 12px;
}

.threshold-badge {
  font-size: 12px;
  line-height: 1.2;
}

.provider-presets-grid-5 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
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

.auth-method-toggle {
  display: flex;
  gap: 8px;
}

.auth-toggle-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.auth-toggle-btn:hover {
  border-color: var(--border-focus);
  background-color: var(--bg-surface);
}

.auth-toggle-btn.active {
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
  background-color: var(--primary-subtle);
}

.auth-badge.recommended {
  background-color: var(--status-interview-text, #f59e0b);
  color: #000;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
}

.email-config-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.oauth-redirect-box {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
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
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
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
  background-color: var(--bg-main);
  padding: 8px 10px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  margin-top: 6px;
}

.oauth-guide-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
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
  background-color: var(--bg-elevated);
}

.guide-content {
  padding: 12px 16px 16px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--bg-main);
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
  background-color: var(--bg-surface);
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

.app-password-callout {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background-color: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 14px;
}

@media (max-width: 600px) {
  .form-grid-3 {
    grid-template-columns: 1fr;
  }
}

.email-preset-buttons-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 18px;
}

.summary-card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.summary-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.summary-label {
  color: var(--text-muted);
}

.summary-value {
  color: var(--text-main);
  font-weight: 600;
}

.ready-hero-box {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
  background: transparent;
  border: none;
  padding: 4px 0 8px 0;
  text-align: left;
}

.ready-hero-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.ready-hero-text .step-heading {
  margin: 0;
  text-align: left;
  font-size: 17px;
  font-weight: 700;
  color: var(--text-main);
}

.ready-hero-text .step-desc {
  margin: 0;
  text-align: left;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.hero-success-icon {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 50%;
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.auth-toggle-group {
  margin-top: 16px;
  margin-bottom: 20px;
}

.account-connected-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin: 18px 0 24px 0;
}

.auth-badge-connected {
  font-size: 10px;
  font-weight: 700;
  color: var(--success, #10b981);
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 2px 8px;
  border-radius: 4px;
}

.folder-selection-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.folder-tip-text {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  font-style: italic;
}

.field-help-text {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 4px 0 0 0;
}

.schedule-time-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shadow-glow {
  box-shadow: 0 0 20px var(--primary-glow);
}
</style>
