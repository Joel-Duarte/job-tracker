<script setup>
import { ref, computed, watch } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import { AIConfigAPI, PromptsAPI } from '../../api/endpoints'
import PromptSettings from './PromptSettings.vue'
import {
  Globe,
  RotateCcw,
  RefreshCw,
  Check,
  Cpu,
  SlidersHorizontal,
  ChevronDown,
  CheckCircle2,
  Thermometer,
  Zap,
  BrainCircuit,
} from 'lucide-vue-next'

const props = defineProps({
  providers: {
    type: Array,
    required: true,
  },
  bindings: {
    type: Array,
    required: true,
  },
  promptsList: {
    type: Array,
    required: true,
  },
  globalBinding: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['refresh'])
const uiStore = useUIStore()

// Global Default Model Form State
const globalForm = ref({
  provider_id: null,
  model_name: '',
})
const globalProviderModels = ref([])
const providerModelsCache = ref({})
const loadingGlobalModels = ref(false)
const isSavingGlobal = ref(false)
const isSyncingGlobal = ref(false)
let globalAutoSaveTimer = null

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
  const gb = props.globalBinding
  const chosenProviderId = gb?.provider_id || (props.providers[0]?.id || null)
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
  const existingGb = props.globalBinding
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
    emit('refresh')
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
    const firstProviderId = props.providers[0]?.id || null

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
    emit('refresh')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to reset global defaults', 'error')
  } finally {
    isResettingGlobal.value = false
  }
}

// Vector Embeddings Settings State
const enableEmbeddings = ref(true)
const isUpdatingEmbeddings = ref(false)
const isReindexingEmbeddings = ref(false)

async function loadGlobalSettings() {
  try {
    const res = await AIConfigAPI.getGlobalSettings()
    enableEmbeddings.value = res.data.ENABLE_EMBEDDINGS ?? true
    uiStore.enableEmbeddings = enableEmbeddings.value
  } catch (err) {
    console.error('Failed to load global settings', err)
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

const selectedTaskKey = ref('JD_EXTRACTION')
const isAdvancedOpen = ref(false)
const studioProviderModels = ref([])
const loadingStudioModels = ref(false)
const isSavingStudio = ref(false)
const isResettingPrompt = ref(false)

const activeTaskDef = computed(() => {
  return TASKS.find((t) => t.key === selectedTaskKey.value) || TASKS[0]
})

const studioForm = ref({
  use_global_default: false,
  provider_id: null,
  model_name: '',
  temperature: 0.2,
  reasoning_effort: 'none',
  max_tokens: null,
  embedding_dimensions: 768,
  prompt_template: '',
})
const isSyncingStudio = ref(false)
let studioAutoSaveTimer = null

function scheduleStudioAutoSave(delay = 500) {
  if (isSyncingStudio.value) return
  if (studioAutoSaveTimer) clearTimeout(studioAutoSaveTimer)
  studioAutoSaveTimer = setTimeout(() => {
    saveStudioTask(true)
  }, delay)
}

function syncStudioForm() {
  isSyncingStudio.value = true
  if (studioAutoSaveTimer) clearTimeout(studioAutoSaveTimer)

  const taskKey = selectedTaskKey.value
  const taskDef = activeTaskDef.value

  const existingBinding = props.bindings.find(
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
  const chosenProviderId = existingBinding?.provider_id || (props.providers[0]?.id || null)

  studioForm.value.provider_id = chosenProviderId
  studioForm.value.model_name = existingBinding?.model_name || (taskKey === 'EMBEDDING' ? 'nomic-embed-text' : 'qwen3.5-4b')
  studioForm.value.temperature = existingBinding?.temperature !== undefined ? existingBinding.temperature : defaultTemp
  studioForm.value.reasoning_effort = existingBinding?.reasoning_effort || existingBinding?.extra_kwargs?.reasoning_effort || taskDef.recommendedReasoning || 'none'
  studioForm.value.max_tokens = existingBinding?.max_tokens || null
  studioForm.value.embedding_dimensions = existingBinding?.embedding_dimensions || (taskKey === 'EMBEDDING' ? 768 : null)

  if (taskDef.promptKey) {
    const promptRecord = props.promptsList.find((p) => p.name.toLowerCase() === taskDef.promptKey.toLowerCase())
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
    const useGlobal = studioForm.value.use_global_default && taskKey !== 'EMBEDDING'
    await AIConfigAPI.setBinding(taskKey, {
      provider_id: useGlobal
        ? (props.globalBinding?.provider_id || studioForm.value.provider_id)
        : studioForm.value.provider_id,
      model_name: useGlobal
        ? (props.globalBinding?.model_name || studioForm.value.model_name.trim())
        : studioForm.value.model_name.trim(),
      temperature: studioForm.value.temperature,
      reasoning_effort: studioForm.value.reasoning_effort,
      max_tokens: studioForm.value.max_tokens ? Number(studioForm.value.max_tokens) : undefined,
      embedding_dimensions: taskKey === 'EMBEDDING' ? studioForm.value.embedding_dimensions : undefined,
      extra_kwargs: {
        use_global_default: useGlobal,
        reasoning_effort: studioForm.value.reasoning_effort,
      },
    })

    if (taskDef.hasPrompt && taskDef.promptKey && studioForm.value.prompt_template !== undefined) {
      await PromptsAPI.update(taskDef.promptKey, studioForm.value.prompt_template)
    }

    uiStore.showToast(`Task '${taskDef.label}' configuration saved!`, 'success')
    emit('refresh')
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
    emit('refresh')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isResettingPrompt.value = false
  }
}

function isTaskCustomized(taskKey) {
  const taskDef = TASKS.find((t) => t.key === taskKey)
  if (!taskDef) return false

  const b = props.bindings.find(
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

watch(
  () => [props.globalBinding, props.providers],
  () => {
    syncGlobalForm()
    syncStudioForm()
  },
  { immediate: true }
)

loadGlobalSettings()
</script>

<template>
  <div class="tab-content animate-fade-in">
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

    <!-- VECTOR KNOWLEDGE & EMBEDDINGS CARD -->
    <div class="embeddings-control-card">
      <div class="embeddings-control-header">
        <div class="embeddings-title-group">
          <Cpu class="text-primary" :size="20" />
          <div>
            <h3 class="embeddings-title">Vector Knowledge &amp; Embeddings</h3>
            <p class="embeddings-desc">
              Enable dense vector indexing for AI natural language search. Disable to make application intake significantly faster.
            </p>
          </div>
        </div>

        <div class="embeddings-actions">
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
      </div>

      <div v-if="enableEmbeddings" class="embeddings-control-body">
        <div class="embeddings-info-box">
          <span class="embeddings-status-text">
            Vector Knowledge is <strong>ACTIVE</strong> — new applications automatically generate embeddings for semantic search.
          </span>
          <button
            class="btn btn-outline btn-xs"
            :disabled="isReindexingEmbeddings"
            @click="reindexMissingEmbeddings"
          >
            <RefreshCw :size="12" :class="{ 'animate-spin': isReindexingEmbeddings }" />
            <span>{{ isReindexingEmbeddings ? 'Re-indexing...' : 'Rebuild Missing Embeddings' }}</span>
          </button>
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

            <div class="studio-workspace">
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
                      @input="scheduleStudioAutoSave(600)"
                    />
                  </div>
                </div>

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
                          @click="setStudioReasoningEffort(effort)"
                        >
                          {{ effort === 'none' ? 'None (Fast)' : effort }}
                        </button>
                      </div>
                    </div>

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
                    <strong>Thinking Mode &amp; Token Limits:</strong> Instructs reasoning models (e.g. DeepSeek-R1, OpenAI o1/o3-mini, Claude 3.7 Thinking, Gemini Thinking) to execute extended chain-of-thought verification.
                  </span>
                </div>
              </div>

              <!-- Prompt Settings Child Component -->
              <PromptSettings
                v-if="activeTaskDef.hasPrompt"
                :task-def="activeTaskDef"
                v-model:template="studioForm.prompt_template"
                :is-resetting="isResettingPrompt"
                @reset="resetStudioPrompt"
                @change="scheduleStudioAutoSave(800)"
              />
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

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

.global-hero-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.embeddings-control-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 24px;
}

.embeddings-control-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.embeddings-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.embeddings-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.embeddings-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.embeddings-control-body {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.embeddings-info-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
}

.embeddings-status-text {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.advanced-overrides-section {
  margin-top: 0;
  margin-bottom: 24px;
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

.advanced-overrides-content {
  margin-top: 16px;
}

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

.task-nav-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

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
}

.task-badge-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rec-temp-chip, .rec-reasoning-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.rec-temp-chip {
  color: var(--text-main);
  background-color: var(--bg-main);
}

.rec-reasoning-chip {
  color: var(--primary);
  background-color: var(--primary-subtle);
  border-color: var(--primary-glow);
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

.studio-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
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

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.label-with-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 24px;
  margin-bottom: 6px;
}

.btn-refresh-models {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 11px;
  height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
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

.reasoning-pills {
  display: flex;
  align-items: center;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 3px;
  height: 38px;
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
}

.reasoning-pill.active {
  background-color: var(--primary);
  color: #fff;
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

.opacity-50 { opacity: 0.5; }
.pointer-events-none { pointer-events: none; }
.mt-3 { margin-top: 16px; }
.mt-4 { margin-top: 16px; }
.mb-4 { margin-bottom: 20px; }
</style>
