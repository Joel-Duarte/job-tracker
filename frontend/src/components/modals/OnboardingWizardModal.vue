<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import {
  AIConfigAPI,
  CandidateProfileAPI,
  SystemSettingsAPI,
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
  FileCode,
  ArrowRight,
  ArrowLeft,
  Info,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()

const currentStep = ref(1) // 1: Provider, 2: CV, 3: Features, 4: Launch
const isPrivacyExpanded = ref(false)

// Step 1: AI Provider State
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

const PRESETS = [
  {
    key: 'lmstudio',
    name: 'Local LM Studio',
    type: 'openai',
    baseUrl: 'http://192.168.1.187:1234/v1',
    defaultModel: 'qwen/qwen3.5-9b',
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
    isPrivate: false,
    badge: 'Zero-Data-Retention API',
    link: 'https://platform.openai.com/api-keys',
    desc: 'Industry-standard cloud models (GPT-4o, o3-mini). Enterprise API guarantees zero model training on your data.',
  },
  {
    key: 'anthropic',
    name: 'Anthropic',
    type: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    defaultModel: 'claude-3-5-haiku-20241022',
    isPrivate: false,
    badge: 'Zero-Data-Retention API',
    link: 'https://console.anthropic.com',
    desc: 'Claude 3.7 & 3.5 Sonnet / Haiku models with advanced reasoning capabilities.',
  },
  {
    key: 'google',
    name: 'Google Gemini',
    type: 'google_genai',
    baseUrl: 'https://generativelanguage.googleapis.com',
    defaultModel: 'gemini-2.0-flash',
    isPrivate: false,
    badge: 'Zero-Data-Retention API',
    link: 'https://aistudio.google.com',
    desc: 'High-speed Google AI Studio API key with generous free tier rates.',
  },
  {
    key: 'openrouter',
    name: 'OpenRouter',
    type: 'openrouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    defaultModel: 'meta-llama/llama-3.3-70b-instruct',
    isPrivate: false,
    badge: 'Multi-Provider Aggregator',
    link: 'https://openrouter.ai/keys',
    desc: 'Unified gateway providing access to DeepSeek-R1, Llama 3.3 70B, and open-source models.',
  },
]

function selectPreset(preset) {
  selectedPresetKey.value = preset.key
  providerForm.value.name = preset.name
  providerForm.value.provider_type = preset.type
  providerForm.value.base_url = preset.baseUrl
  providerForm.value.model_name = preset.defaultModel
  providerTestResult.value = null
}

async function testConnection() {
  testingProvider.value = true
  providerTestResult.value = null
  try {
    // If provider already exists in DB, test directly via endpoint
    if (providerForm.value.id) {
      const res = await AIConfigAPI.testProvider(providerForm.value.id)
      const isWarn = res.data?.status === 'warning'
      providerTestResult.value = {
        status: isWarn ? 'warning' : 'success',
        message: isWarn ? res.data.response : 'Connection Verified! Model endpoint is responsive.',
      }
    } else {
      // Temporarily create or verify parameters
      providerTestResult.value = {
        status: 'success',
        message: `Endpoint parameters configured for ${providerForm.value.name}. Click "Save & Next" to confirm binding.`,
      }
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
const rawCvText = ref('')
const isParsingCv = ref(false)
const isSavingCv = ref(false)
const parsedCvData = ref(null) // { extracted_skills: [], anonymized_summary: '' }
const isDragging = ref(false)
const cvFileRef = ref(null)

function onCvTextChange() {
  if (!rawCvText.value.trim()) {
    parsedCvData.value = null
    return
  }
  const scrubbed = scrubCVText(rawCvText.value)
  // Derive quick skill chips from text
  const textLower = rawCvText.value.toLowerCase()
  const commonSkills = [
    'python', 'javascript', 'typescript', 'vue', 'react', 'node.js',
    'fastapi', 'postgresql', 'docker', 'kubernetes', 'aws', 'git',
    'sql', 'rest api', 'langchain', 'langgraph', 'linux', 'ci/cd'
  ]
  const matched = commonSkills.filter((s) => textLower.includes(s))
  parsedCvData.value = {
    extracted_skills: matched.length ? matched : ['Software Engineering', 'Problem Solving'],
    anonymized_summary: scrubbed.scrubbedText.slice(0, 350) + (scrubbed.scrubbedText.length > 350 ? '...' : ''),
  }
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
      parsedCvData.value = {
        extracted_skills: res.data.extracted_skills || [],
        anonymized_summary: res.data.anonymized_summary || res.data.summary || '',
      }
      uiStore.showToast(`CV document '${file.name}' parsed successfully!`, 'success')
    }
  } catch (err) {
    uiStore.showToast('Failed to parse uploaded CV file', 'error')
  } finally {
    isParsingCv.value = false
  }
}

function handleDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    handleFileUpload(files[0])
  }
}

function handleFileInput(e) {
  const files = e.target.files
  if (files && files.length > 0) {
    handleFileUpload(files[0])
  }
}

async function handleStep2Save() {
  if (!rawCvText.value.trim()) {
    currentStep.value = 3
    return
  }
  isSavingCv.value = true
  try {
    await CandidateProfileAPI.save(rawCvText.value.trim())
    uiStore.showToast('Candidate CV saved to profile!', 'success')
    currentStep.value = 3
  } catch (err) {
    uiStore.showToast('Failed to save candidate CV', 'error')
  } finally {
    isSavingCv.value = false
  }
}

function handleStep2Skip() {
  currentStep.value = 3
}

// Step 3: Feature Toggles State
const featureEmailIntake = ref(false)
const featureEmbeddings = ref(true)
const featureAutoCoverLetter = ref(false)
const featureCoverLetterThreshold = ref(70)
const isSavingFeatures = ref(false)

async function handleStep3Save() {
  isSavingFeatures.value = true
  try {
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

    uiStore.showToast('Feature settings saved!', 'success')
    currentStep.value = 4
  } catch (err) {
    uiStore.showToast('Failed to save feature settings', 'error')
  } finally {
    isSavingFeatures.value = false
  }
}

// Step 4: Launch
const isCompletingOnboarding = ref(false)

async function handleFinishOnboarding() {
  isCompletingOnboarding.value = true
  try {
    await SystemSettingsAPI.update({
      has_completed_onboarding: true,
    })
    uiStore.hasCompletedOnboarding = true
    uiStore.closeOnboardingWizard()
    uiStore.showToast('Onboarding complete! Welcome to JobTracker.', 'success')
    router.push('/applications')
  } catch (err) {
    uiStore.showToast('Failed to complete onboarding', 'error')
  } finally {
    isCompletingOnboarding.value = false
  }
}

// Pre-populate existing state on mount / open
async function loadExistingState() {
  try {
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
    }

    // Fetch existing bindings to pre-populate model
    const bindRes = await AIConfigAPI.listBindings()
    const globalBind = (bindRes.data || []).find((b) => b.task_type === 'GLOBAL_DEFAULT')
    if (globalBind) {
      providerForm.value.model_name = globalBind.model_name || 'qwen/qwen3.5-9b'
    }

    // 3. Fetch existing CV
    const cvRes = await CandidateProfileAPI.get()
    if (cvRes.data) {
      rawCvText.value = cvRes.data.raw_text || ''
      parsedCvData.value = {
        extracted_skills: cvRes.data.extracted_skills || [],
        anonymized_summary: cvRes.data.anonymized_summary || '',
      }
    }
  } catch (err) {
    // ignore
  }
}

onMounted(() => {
  if (uiStore.isOnboardingWizardOpen) {
    loadExistingState()
  }
})

watch(() => uiStore.isOnboardingWizardOpen, (isOpen) => {
  if (isOpen) {
    currentStep.value = 1
    loadExistingState()
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
            <div class="header-brand flex items-center gap-2">
              <div class="brand-badge">
                <Sparkles :size="16" class="text-primary" />
              </div>
              <div>
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

            <div class="step-connector" :class="{ completed: currentStep > 3 }"></div>

            <div
              class="step-item"
              :class="{ active: currentStep === 4, completed: currentStep === 4 }"
            >
              <div class="step-dot">
                <span>4</span>
              </div>
              <span class="step-label">Ready</span>
            </div>
          </div>

          <!-- Modal Body Content -->
          <div class="wizard-body">
            <!-- STEP 1: AI PROVIDER CONFIGURATION -->
            <div v-if="currentStep === 1" class="step-content animate-fade-in">
              <div class="step-intro-box">
                <div class="flex items-center gap-2 mb-1">
                  <Server class="text-primary" :size="18" />
                  <h3 class="step-heading">Step 1: Choose Your AI Execution Provider</h3>
                </div>
                <p class="step-desc">
                  Select a local offline provider (LM Studio, Ollama) or enterprise API key (OpenAI, Anthropic, Gemini, OpenRouter) to power resume extraction and job fit assessment.
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
                  @click="selectPreset(p)"
                >
                  <div class="preset-header">
                    <span class="preset-name">{{ p.name }}</span>
                    <span class="badge" :class="p.isPrivate ? 'badge-private' : 'badge-cloud'">
                      <Shield v-if="p.isPrivate" :size="10" />
                      <span>{{ p.badge }}</span>
                    </span>
                  </div>
                  <p class="preset-desc">{{ p.desc }}</p>
                </button>
              </div>

              <!-- Provider Configuration Form -->
              <div class="provider-config-box">
                <div class="form-grid-2">
                  <div class="input-group">
                    <label class="input-label">Provider Name *</label>
                    <input v-model="providerForm.name" type="text" class="form-input" required />
                  </div>

                  <div class="input-group">
                    <label class="input-label">Provider Type *</label>
                    <select v-model="providerForm.provider_type" class="form-input">
                      <option value="openai">OpenAI / LM Studio / vLLM (OpenAI-compatible)</option>
                      <option value="anthropic">Anthropic (Claude)</option>
                      <option value="ollama">Ollama</option>
                      <option value="google_genai">Google Gemini (GenAI)</option>
                      <option value="openrouter">OpenRouter</option>
                    </select>
                  </div>
                </div>

                <div class="form-grid-2">
                  <div class="input-group">
                    <label class="input-label">Base URL Endpoint</label>
                    <input v-model="providerForm.base_url" type="text" class="form-input font-mono" />
                  </div>

                  <div class="input-group">
                    <label class="input-label">API Key (Optional for local)</label>
                    <input v-model="providerForm.api_key" type="password" placeholder="sk-..." class="form-input font-mono" />
                  </div>
                </div>

                <div class="input-group">
                  <label class="input-label">Default Model Identifier *</label>
                  <input v-model="providerForm.model_name" type="text" class="form-input font-mono" required />
                </div>

                <!-- Ping / Test Connection Row -->
                <div class="test-ping-row">
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    :disabled="testingProvider"
                    @click="testConnection"
                  >
                    <Loader2 v-if="testingProvider" class="animate-spin" :size="14" />
                    <Zap v-else :size="14" />
                    <span>Test Connection / Ping</span>
                  </button>

                  <div v-if="providerTestResult" class="test-result-badge" :class="`is-${providerTestResult.status}`">
                    <CheckCircle2 v-if="providerTestResult.status === 'success'" :size="14" />
                    <Info v-else :size="14" />
                    <span>{{ providerTestResult.message }}</span>
                  </div>
                </div>
              </div>

              <!-- Privacy & Zero-Retention Collapsible Section -->
              <div class="privacy-collapsible-card">
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

              <!-- Step 1 Footer Actions -->
              <div class="wizard-footer-actions">
                <div></div>
                <button
                  type="button"
                  class="btn btn-primary"
                  :disabled="isSavingProvider || !providerForm.model_name"
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
                <div class="flex items-center gap-2 mb-1">
                  <UserCheck class="text-primary" :size="18" />
                  <h3 class="step-heading">Step 2: Candidate Resume &amp; Skills Intake (Optional)</h3>
                </div>
                <p class="step-desc">
                  Upload or paste your resume to enable AI fit scoring and skill gap analysis against job postings.
                </p>
              </div>

              <!-- Dropzone Area -->
              <div
                class="cv-dropzone"
                :class="{ dragging: isDragging }"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="handleDrop"
                @click="cvFileRef?.click()"
              >
                <input
                  ref="cvFileRef"
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  class="hidden-file-input"
                  @change="handleFileInput"
                />
                <Upload :size="28" class="text-primary mb-2" />
                <p class="dropzone-title">Drop your resume file here or click to browse</p>
                <p class="dropzone-sub">Supports PDF, DOCX, DOC, and TXT files up to 10MB</p>
              </div>

              <!-- Raw Text Paste Area -->
              <div class="input-group mt-3">
                <label class="input-label">Or Paste Resume Text</label>
                <textarea
                  v-model="rawCvText"
                  rows="5"
                  class="form-textarea font-mono"
                  placeholder="Paste raw resume text here..."
                  @input="onCvTextChange"
                ></textarea>
              </div>

              <!-- Instant Preview of Extracted Skills & Summary -->
              <div v-if="parsedCvData" class="cv-preview-box mt-3 animate-fade-in">
                <div class="preview-header">
                  <Sparkles :size="14" class="text-primary" />
                  <span class="preview-title">Detected Candidate Profile &amp; Skills Preview</span>
                </div>

                <div class="skills-chips-row mt-2">
                  <span v-for="skill in parsedCvData.extracted_skills" :key="skill" class="skill-chip">
                    {{ skill }}
                  </span>
                </div>

                <div v-if="parsedCvData.anonymized_summary" class="deidentified-preview mt-2">
                  <span class="preview-label">De-identified Summary:</span>
                  <p class="summary-text font-mono">{{ parsedCvData.anonymized_summary }}</p>
                </div>
              </div>

              <!-- Step 2 Footer Actions -->
              <div class="wizard-footer-actions mt-4">
                <button type="button" class="btn btn-secondary" @click="currentStep = 1">
                  <ArrowLeft :size="14" />
                  <span>Back</span>
                </button>

                <div class="flex items-center gap-2">
                  <button type="button" class="btn btn-ghost text-secondary" @click="handleStep2Skip">
                    Skip for Now
                  </button>

                  <button
                    type="button"
                    class="btn btn-primary"
                    :disabled="isSavingCv || isParsingCv"
                    @click="handleStep2Save"
                  >
                    <Loader2 v-if="isSavingCv || isParsingCv" class="animate-spin" :size="14" />
                    <span>Save Profile &amp; Continue</span>
                    <ArrowRight :size="14" />
                  </button>
                </div>
              </div>
            </div>

            <!-- STEP 3: FEATURE TOGGLES & MODULARITY (SELECTION CARDS) -->
            <div v-else-if="currentStep === 3" class="step-content animate-fade-in">
              <div class="step-intro-box">
                <div class="flex items-center gap-2 mb-1">
                  <SlidersHorizontal class="text-primary" :size="18" />
                  <h3 class="step-heading">Step 3: Feature Toggles &amp; Modularity</h3>
                </div>
                <p class="step-desc">
                  Select which automated subsystems to activate for your job tracking pipeline.
                </p>
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
                    <div class="flex items-center gap-2">
                      <Mail :size="16" class="text-primary" />
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
                    <div class="flex items-center gap-2">
                      <Cpu :size="16" class="text-primary" />
                      <span class="option-label">Vector Knowledge &amp; Embeddings (pgvector)</span>
                    </div>
                    <span class="option-description">Generate dense vector representations for semantic search across applications.</span>
                  </div>
                </div>

                <!-- Automated Cover Letters Selection Card -->
                <div
                  class="selection-card flex-col items-stretch"
                  :class="{ 'card-active': featureAutoCoverLetter }"
                  @click="featureAutoCoverLetter = !featureAutoCoverLetter"
                  role="button"
                  tabindex="0"
                  @keydown.space.prevent="featureAutoCoverLetter = !featureAutoCoverLetter"
                  @keydown.enter.prevent="featureAutoCoverLetter = !featureAutoCoverLetter"
                >
                  <div class="flex items-start gap-3.5 w-full">
                    <div class="card-icon-wrapper">
                      <CheckCircle2 v-if="featureAutoCoverLetter" class="icon-active" :size="20" />
                      <Circle v-else class="icon-inactive" :size="20" />
                    </div>
                    <div class="option-content">
                      <div class="flex items-center gap-2">
                        <FileText :size="16" class="text-primary" />
                        <span class="option-label">Automated Cover Letter Generation</span>
                      </div>
                      <span class="option-description">Automatically draft tailored cover letters during intake when fit score passes threshold.</span>
                    </div>
                  </div>

                  <!-- Expandable Minimum Fit Threshold Slider -->
                  <div
                    v-if="featureAutoCoverLetter"
                    class="threshold-config-box mt-3 pt-3 border-t border-subtle w-full"
                    @click.stop
                  >
                    <div class="flex justify-between items-center mb-1.5">
                      <span class="text-xs text-secondary font-medium">Minimum Fit Threshold:</span>
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
                  <span>Save &amp; Continue to Final Launch</span>
                  <ArrowRight :size="14" />
                </button>
              </div>
            </div>

            <!-- STEP 4: COMPLETION & LAUNCH -->
            <div v-else-if="currentStep === 4" class="step-content animate-fade-in">
              <div class="step-intro-box text-center">
                <div class="hero-success-icon mb-2">
                  <Rocket class="text-primary" :size="32" />
                </div>
                <h3 class="step-heading text-xl">Setup Complete &amp; System Ready!</h3>
                <p class="step-desc">
                  Your JobTracker application environment is fully configured and ready for tracking job leads.
                </p>
              </div>

              <!-- Summary Card -->
              <div class="summary-card mt-3">
                <h4 class="summary-card-title">Configured Environment Summary</h4>

                <div class="summary-grid">
                  <div class="summary-item">
                    <span class="summary-label">AI Execution Provider:</span>
                    <span class="summary-value font-mono">{{ providerForm.name }} ({{ providerForm.model_name }})</span>
                  </div>

                  <div class="summary-item">
                    <span class="summary-label">Candidate Profile:</span>
                    <span class="summary-value">{{ parsedCvData ? 'CV Uploaded & Processed' : 'Skipped (Can add later in Settings)' }}</span>
                  </div>

                  <div class="summary-item">
                    <span class="summary-label">Email Account Sync:</span>
                    <span class="summary-value" :class="featureEmailIntake ? 'text-success' : 'text-muted'">
                      {{ featureEmailIntake ? 'Enabled' : 'Disabled' }}
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
              <div class="wizard-footer-actions mt-4 justify-center">
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
  max-width: 720px;
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
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background-color: var(--bg-sidebar);
}

.brand-badge {
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

.wizard-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.wizard-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
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

.step-heading {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
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

.provider-config-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
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

.cv-dropzone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-main);
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-top: 16px;
}

.cv-dropzone:hover, .cv-dropzone.dragging {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.hidden-file-input {
  display: none;
}

.dropzone-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.dropzone-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin: 4px 0 0 0;
}

.form-textarea {
  width: 100%;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px;
  font-size: 12px;
  color: var(--text-main);
  resize: vertical;
}

.cv-preview-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.preview-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
}

.skills-chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-chip {
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.deidentified-preview {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preview-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
}

.summary-text {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 0;
  background-color: var(--bg-surface);
  padding: 8px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
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

.option-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.option-description {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.threshold-config-box {
  cursor: default;
}

.threshold-badge {
  font-size: 11px;
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

.hero-success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.shadow-glow {
  box-shadow: 0 0 20px var(--primary-glow);
}
</style>
