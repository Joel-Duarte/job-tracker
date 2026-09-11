<script setup>
import { ref, watch, computed } from 'vue'
import {
  X,
  Sparkles,
  Loader2,
  CheckCircle2,
  AlertCircle,
  BookOpen,
  Globe,
  RefreshCw,
  ExternalLink,
  Layers,
  ChevronRight,
  Maximize2,
  Minimize2,
  Copy,
  Check,
} from 'lucide-vue-next'
import { ApplicationsAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'

const props = defineProps({
  isOpen: Boolean,
  applicationId: Number,
  position: String,
  companyName: String,
})

const emit = defineEmits(['close', 'generated'])

const uiStore = useUIStore()
const appStore = useApplicationsStore()

// View / UI state
const isFullScreen = ref(false)
const hasCopied = ref(false)
const activeTab = ref('generate') // 'generate' | 'preview'

// Stream / Generation state
const isStreaming = ref(false)
const progressCompleted = ref(0)
const progressTotal = ref(6)
const progressPercent = ref(0)
const currentStepName = ref('')
const generationError = ref(null)
const generatedGuideHtml = ref('')
const guideLanguage = ref('en')

// Configuration parameters
const selectedLanguage = ref('en')
const recursionLimit = ref(25)
const includeCompanyResearch = ref(true)
const companyResearch = ref(null)
const isResearchExpanded = ref(false)
const isRefreshingResearch = ref(false)

const ALL_SECTIONS = [
  { id: 'role_company_brief', label: 'Role & Company Brief', desc: 'Culture signals, engineering priorities & team context' },
  { id: 'strategic_fit_pitch', label: 'Strategic Fit & Elevator Pitch', desc: '60-90s tailored introduction hook & overlap highlights' },
  { id: 'star_stories', label: 'Tailored STAR Stories', desc: '3-4 metric-driven STAR stories tailored to job requirements' },
  { id: 'question_defenses', label: 'Behavioral & Technical Question Defenses', desc: 'Top domain questions & gap mitigation talking points' },
  { id: 'interviewer_questions', label: 'High-Leverage Questions to Ask', desc: 'Smart questions for recruiter & technical hiring rounds' },
  { id: 'prep_checklist', label: 'Final Pre-Interview Checklist', desc: 'Critical morning-of review items & strategy recap' },
]

const selectedSections = ref(ALL_SECTIONS.map((s) => s.id))

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'pt', label: 'Português (Portuguese)' },
  { code: 'es', label: 'Español (Spanish)' },
  { code: 'de', label: 'Deutsch (German)' },
  { code: 'fr', label: 'Français (French)' },
  { code: 'it', label: 'Italiano (Italian)' },
  { code: 'nl', label: 'Nederlands (Dutch)' },
]

watch(
  () => props.isOpen,
  async (open) => {
    if (open && props.applicationId) {
      resetState()
      await loadInitialData()
    } else {
      isStreaming.value = false
    }
  }
)

function resetState() {
  isStreaming.value = false
  progressCompleted.value = 0
  progressTotal.value = selectedSections.value.length || 6
  progressPercent.value = 0
  currentStepName.value = ''
  generationError.value = null
  generatedGuideHtml.value = ''
}

async function loadInitialData() {
  try {
    const res = await ApplicationsAPI.get(props.applicationId)
    const app = res.data
    if (app.interview_guide_html) {
      generatedGuideHtml.value = app.interview_guide_html
      guideLanguage.value = app.interview_guide_language || 'en'
      activeTab.value = 'preview'
    } else {
      activeTab.value = 'generate'
    }

    if (app.company?.company_research) {
      companyResearch.value = app.company.company_research
    }
  } catch (err) {
    console.warn('Failed to load application for interview guide:', err)
  }
}

function toggleSection(id) {
  if (selectedSections.value.includes(id)) {
    if (selectedSections.value.length === 1) {
      uiStore.showToast('At least one section must be selected', 'warning')
      return
    }
    selectedSections.value = selectedSections.value.filter((s) => s !== id)
  } else {
    selectedSections.value.push(id)
  }
  progressTotal.value = selectedSections.value.length
}

function selectAllSections() {
  selectedSections.value = ALL_SECTIONS.map((s) => s.id)
  progressTotal.value = selectedSections.value.length
}

async function handleGenerateStream() {
  if (!(await uiStore.ensureAIReady())) return

  if (selectedSections.value.length === 0) {
    uiStore.showToast('Please select at least one section', 'warning')
    return
  }

  isStreaming.value = true
  generationError.value = null
  progressCompleted.value = 0
  progressTotal.value = selectedSections.value.length
  progressPercent.value = 0
  currentStepName.value = 'Initializing LangGraph pipeline...'

  const payload = {
    language: selectedLanguage.value,
    selected_sections: selectedSections.value,
    recursion_limit: Number(recursionLimit.value) || 25,
    include_company_research: includeCompanyResearch.value,
    company_research: includeCompanyResearch.value ? companyResearch.value : null,
  }

  try {
    const response = await fetch(`/api/v1/applications/${props.applicationId}/interview-guide/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const errJson = await response.json().catch(() => null)
      throw new Error(errJson?.detail || errJson?.error || `HTTP ${response.status} error`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // keep the last incomplete chunk

      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('data:')) {
          const rawData = trimmed.slice(5).trim()
          if (!rawData) continue
          try {
            const data = JSON.parse(rawData)
            handleStreamChunk(data)
          } catch (e) {
            console.warn('Could not parse SSE JSON chunk:', rawData, e)
          }
        }
      }
    }

    if (buffer.trim().startsWith('data:')) {
      try {
        const data = JSON.parse(buffer.trim().slice(5).trim())
        handleStreamChunk(data)
      } catch (e) {
        // ignore
      }
    }
  } catch (err) {
    console.error('SSE guide stream failed:', err)
    generationError.value = err.message || 'Guide generation stream encountered an error.'
    uiStore.showToast(generationError.value, 'error')
  } finally {
    isStreaming.value = false
    await appStore.fetchApplications()
    if (appStore.selectedApplication?.id === props.applicationId) {
      try {
        const updated = await ApplicationsAPI.get(props.applicationId)
        appStore.selectedApplication = updated.data
      } catch (e) {
        // ignore
      }
    }
  }
}

function handleStreamChunk(data) {
  if (data.type === 'progress') {
    if (data.completed !== undefined) {
      progressCompleted.value = Number(data.completed)
    }
    if (data.total !== undefined) {
      progressTotal.value = Number(data.total)
    }
    if (data.percent !== undefined) {
      progressPercent.value = Number(data.percent)
    }
    if (data.step) {
      currentStepName.value = formatStepName(data.step)
    }
  } else if (data.type === 'complete') {
    progressCompleted.value = progressTotal.value
    progressPercent.value = 100
    currentStepName.value = 'Generation Complete'
    if (data.interview_guide_html) {
      generatedGuideHtml.value = data.interview_guide_html
      guideLanguage.value = data.interview_guide_language || selectedLanguage.value
      activeTab.value = 'preview'
      uiStore.showToast('Interview Preparation Guide generated successfully!', 'success')
      emit('generated', data)
    }
  } else if (data.error) {
    generationError.value = data.error
    uiStore.showToast(data.error, 'error')
  }
}

function formatStepName(nodeName) {
  switch (nodeName) {
    case 'extract_baseline':
      return 'Extracting candidate & role baseline...'
    case 'gather_company_intelligence':
      return 'Analyzing company intelligence & culture signals...'
    case 'generate_section_node':
      return `Synthesizing section ${progressCompleted.value + 1} of ${progressTotal.value}...`
    case 'finalize_guide':
      return 'Consolidating and formatting final playbook...'
    default:
      return `Processing step: ${nodeName}`
  }
}

function handleCopy() {
  if (!generatedGuideHtml.value) return
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = generatedGuideHtml.value
  const plainText = tempDiv.innerText || tempDiv.textContent

  navigator.clipboard.writeText(plainText).then(() => {
    hasCopied.value = true
    uiStore.showToast('Guide copied to clipboard!', 'info')
    setTimeout(() => {
      hasCopied.value = false
    }, 2000)
  })
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <div v-if="isOpen" class="modal-backdrop print-hide" :class="{ 'full-screen-backdrop': isFullScreen }" @click.self="handleClose">
    <div class="modal-card interview-guide-modal-container animate-fade-in" :class="{ 'full-screen-mode': isFullScreen }">
      <!-- Header -->
      <div class="modal-header">
        <div class="header-main-info">
          <div class="header-title-row">
            <Sparkles :size="20" class="text-primary" />
            <h2 class="modal-title">Interview Preparation Guide</h2>
            <span v-if="companyName" class="meta-pill company-pill">{{ companyName }}</span>
            <span v-if="position" class="meta-pill position-pill">{{ position }}</span>
          </div>
        </div>

        <div class="header-actions">
          <div v-if="generatedGuideHtml" class="tab-toggle-group">
            <button
              class="btn-tab"
              :class="{ active: activeTab === 'generate' }"
              @click="activeTab = 'generate'"
            >
              Configure
            </button>
            <button
              class="btn-tab"
              :class="{ active: activeTab === 'preview' }"
              @click="activeTab = 'preview'"
            >
              View Guide
            </button>
          </div>

          <button
            v-if="generatedGuideHtml && activeTab === 'preview'"
            class="btn btn-secondary btn-sm"
            @click="handleCopy"
          >
            <component :is="hasCopied ? Check : Copy" :size="14" :class="{ 'text-success': hasCopied }" />
            <span>{{ hasCopied ? 'Copied' : 'Copy' }}</span>
          </button>

          <button
            class="btn btn-secondary btn-sm"
            @click="isFullScreen = !isFullScreen"
            :title="isFullScreen ? 'Exit Full Screen' : 'Full Screen'"
          >
            <component :is="isFullScreen ? Minimize2 : Maximize2" :size="14" />
          </button>

          <button class="btn-close" @click="handleClose">
            <X :size="18" />
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="modal-body-scroll">
        <!-- Progress Bar banner when generating or streaming -->
        <div v-if="isStreaming" class="stream-progress-card animate-fade-in">
          <div class="stream-progress-header">
            <div class="stream-progress-label">
              <Loader2 class="animate-spin text-primary" :size="16" />
              <span class="stream-progress-title">
                Generating interview guide: {{ progressCompleted }} of {{ progressTotal }} sections completed ({{ progressPercent }}%)
              </span>
            </div>
            <span class="stream-progress-step-text">{{ currentStepName }}</span>
          </div>

          <!-- Aggregate Progress Bar Track -->
          <div class="progress-bar-track">
            <div
              class="progress-bar-fill"
              :style="{ width: `${Math.min(100, Math.max(5, progressPercent))}%` }"
            ></div>
          </div>
        </div>

        <!-- Configuration View -->
        <div v-if="activeTab === 'generate' && !isStreaming" class="config-view-layout animate-fade-in">
          <div class="config-section">
            <h3 class="section-title">Guide Modules</h3>
            <p class="section-desc">Select which tactical dossiers the LangGraph agent should synthesize for this interview.</p>

            <div class="sections-picker-header">
              <span class="selected-count">{{ selectedSections.length }} of {{ ALL_SECTIONS.length }} selected</span>
              <button type="button" class="btn-text-link" @click="selectAllSections">Select All</button>
            </div>

            <div class="sections-grid">
              <div
                v-for="sec in ALL_SECTIONS"
                :key="sec.id"
                class="section-card"
                :class="{ active: selectedSections.includes(sec.id) }"
                @click="toggleSection(sec.id)"
              >
                <div class="section-check-circle">
                  <CheckCircle2 v-if="selectedSections.includes(sec.id)" :size="16" class="text-primary" />
                  <div v-else class="check-empty"></div>
                </div>
                <div class="section-text">
                  <span class="section-name">{{ sec.label }}</span>
                  <span class="section-sub">{{ sec.desc }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="config-row-group">
            <div class="input-group">
              <label class="input-label">
                <Globe :size="13" />
                <span>Output Language</span>
              </label>
              <select v-model="selectedLanguage" class="form-input">
                <option v-for="lang in LANGUAGES" :key="lang.code" :value="lang.code">
                  {{ lang.label }}
                </option>
              </select>
            </div>

            <div class="input-group">
              <label class="input-label">
                <Layers :size="13" />
                <span>Agent Recursion Limit</span>
              </label>
              <input
                v-model.number="recursionLimit"
                type="number"
                min="10"
                max="100"
                class="form-input"
              />
            </div>
          </div>

          <div v-if="generationError" class="generation-error-box">
            <AlertCircle :size="16" class="text-danger" />
            <span>{{ generationError }}</span>
          </div>
        </div>

        <!-- Preview View (When Guide Exists) -->
        <div v-else-if="activeTab === 'preview' && !isStreaming" class="preview-view-layout animate-fade-in">
          <div class="guide-paper">
            <div class="guide-article" v-html="generatedGuideHtml"></div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <div class="footer-left">
          <span v-if="isStreaming" class="text-xs text-muted">
            Executing sub-tasks in parallel...
          </span>
          <span v-else-if="generatedGuideHtml" class="text-xs text-muted">
            Dossier generated and synchronized with application timeline.
          </span>
        </div>

        <div class="footer-actions">
          <button class="btn btn-secondary" :disabled="isStreaming" @click="handleClose">
            Close
          </button>
          <button
            v-if="activeTab === 'generate' || !generatedGuideHtml"
            class="btn btn-primary"
            :disabled="isStreaming || selectedSections.length === 0"
            @click="handleGenerateStream"
          >
            <Loader2 v-if="isStreaming" class="animate-spin" :size="15" />
            <Sparkles v-else :size="15" />
            <span>{{ isStreaming ? 'Synthesizing...' : 'Generate Playbook (Stream)' }}</span>
          </button>
          <button
            v-else
            class="btn btn-secondary"
            @click="activeTab = 'generate'"
          >
            <RefreshCw :size="14" />
            <span>Re-configure & Regenerate</span>
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
  z-index: 1050;
  padding: 20px;
}

.modal-backdrop.full-screen-backdrop {
  padding: 0;
}

.interview-guide-modal-container {
  width: 100%;
  max-width: 920px;
  height: 85vh;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all var(--transition-fast, 0.15s ease);
}

.interview-guide-modal-container.full-screen-mode {
  width: 100vw;
  max-width: 100vw;
  height: 100vh;
  border-radius: 0;
  border: none;
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

.header-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 1.1rem;
  color: var(--text-main);
  margin: 0;
  font-weight: 700;
}

.meta-pill {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.company-pill {
  font-weight: 600;
  color: var(--text-main);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-toggle-group {
  display: flex;
  background: var(--bg-elevated);
  padding: 2px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.btn-tab {
  background: transparent;
  border: none;
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: var(--radius-xs);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.btn-tab.active {
  background: var(--bg-surface);
  color: var(--text-main);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.modal-body-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Aggregate Progress Bar */
.stream-progress-card {
  padding: 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stream-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stream-progress-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stream-progress-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-main);
}

.stream-progress-step-text {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.progress-bar-track {
  width: 100%;
  height: 8px;
  background: var(--bg-elevated);
  border-radius: var(--radius-xs);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.progress-bar-fill {
  height: 100%;
  background: var(--primary);
  border-radius: var(--radius-xs);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Sections Grid */
.config-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.section-desc {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 0 0 8px 0;
}

.sections-picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.78rem;
}

.selected-count {
  color: var(--text-secondary);
  font-weight: 500;
}

.btn-text-link {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-text-link:hover {
  text-decoration: underline;
}

.sections-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.section-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.section-card:hover {
  border-color: var(--primary);
  background: var(--bg-surface-hover);
}

.section-card.active {
  border-color: var(--primary);
  background: var(--primary-subtle);
}

.section-check-circle {
  flex-shrink: 0;
  margin-top: 2px;
}

.check-empty {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid var(--border-color);
}

.section-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.section-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-main);
}

.section-sub {
  font-size: 0.72rem;
  color: var(--text-muted);
  line-height: 1.3;
}

.config-row-group {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 10px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.generation-error-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  font-size: 0.82rem;
}

/* Guide Paper Preview */
.guide-paper {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 32px 36px;
  box-shadow: var(--shadow-sm);
}

.guide-article :deep(h1) {
  font-family: var(--font-heading);
  font-size: 1.25rem;
  color: var(--text-main);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
  margin-top: 20px;
  margin-bottom: 12px;
}
.guide-article :deep(h1:first-child) { margin-top: 0; }
.guide-article :deep(h2) {
  font-family: var(--font-heading);
  font-size: 1.1rem;
  color: var(--text-main);
  margin-top: 24px;
  margin-bottom: 10px;
}
.guide-article :deep(h3) { font-size: 0.92rem; font-weight: 700; color: var(--text-main); margin-top: 16px; margin-bottom: 6px; }
.guide-article :deep(p) { font-size: 0.88rem; line-height: 1.6; color: var(--text-main); margin-bottom: 12px; }
.guide-article :deep(ul) { margin-bottom: 14px; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; }
.guide-article :deep(li) { font-size: 0.86rem; line-height: 1.5; color: var(--text-secondary); }

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  flex-shrink: 0;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
