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
} from 'lucide-vue-next'

const uiStore = useUIStore()

const activeTab = ref('bindings') // 'bindings' | 'providers' | 'prompts' | 'email_accounts'

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
const bindingForm = ref({
  provider_id: null,
  model_name: 'qwen3.5-4b',
  temperature: 0.2,
  max_tokens: 2000,
  embedding_dimensions: 768,
})
const testResult = ref(null)
const testingTask = ref(null)

// Prompts Management state
const promptsList = ref([])
const loadingPrompts = ref(false)
const selectedPromptName = ref('extraction')
const currentPromptTemplate = ref('')
const isSavingPrompt = ref(false)
const isResettingPrompt = ref(false)

// Email Accounts state
const emailAccounts = ref([])
const loadingAccounts = ref(false)
const syncingAccount = ref(null)

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
            <h3>Connected Mailboxes & OAuth Sync</h3>
            <p>Sync recruitment inboxes using Google Workspace OAuth2, Microsoft Graph, or basic IMAP.</p>
          </div>
        </div>

        <div class="accounts-list">
          <div v-for="acc in emailAccounts" :key="acc.id" class="account-card">
            <div class="account-info">
              <div class="account-title-row">
                <Mail :size="16" class="text-primary" />
                <span class="account-name">{{ acc.name }}</span>
                <span class="badge badge-applied font-mono">{{ acc.auth_type || 'IMAP' }}</span>
              </div>
              <div class="account-user text-xs text-secondary">{{ acc.username }} (Folder: {{ acc.folder }})</div>
            </div>

            <div class="account-actions">
              <button
                class="btn btn-primary btn-sm"
                :disabled="syncingAccount === acc.id"
                @click="triggerSync(acc)"
              >
                <Loader2 v-if="syncingAccount === acc.id" class="animate-spin" :size="14" />
                <span>{{ syncingAccount === acc.id ? 'Syncing...' : 'Sync Now' }}</span>
              </button>
            </div>
          </div>

          <div v-if="emailAccounts.length === 0" class="empty-state">
            No email accounts registered. Use Quick Ingest for drag-and-drop or paste!
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
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
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
</style>
