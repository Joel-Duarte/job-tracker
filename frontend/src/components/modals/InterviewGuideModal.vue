<script setup>
import { ref, computed, watch } from 'vue'
import {
  X,
  Sparkles,
  BookOpen,
  Printer,
  Copy,
  Check,
  RotateCcw,
  Sliders,
  ChevronDown,
  ChevronUp,
  Globe,
  Loader2,
  Trash2,
  Building2,
  Briefcase,
  Layers,
  FileCheck,
} from 'lucide-vue-next'
import { ApplicationsAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  applicationId: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['close', 'updated'])

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const isLoading = ref(false)
const isGenerating = ref(false)
const application = ref(null)
const showConfigPanel = ref(false)
const showAdvanced = ref(false)
const hasCopied = ref(false)

// Config Form State
const selectedLanguage = ref('en')
const recursionLimit = ref(25)
const selectedSections = ref([
  'role_company_brief',
  'strategic_fit_pitch',
  'star_stories',
  'question_defenses',
  'interviewer_questions',
  'prep_checklist',
])

const ALL_SECTIONS = [
  { id: 'role_company_brief', label: 'Role & Company Brief', desc: 'Culture signals, engineering priorities & team context' },
  { id: 'strategic_fit_pitch', label: 'Strategic Fit & Elevator Pitch', desc: '60-90s tailored introduction hook & overlap highlights' },
  { id: 'star_stories', label: 'Tailored STAR Stories', desc: '3-4 metric-driven STAR stories tailored to job requirements' },
  { id: 'question_defenses', label: 'Behavioral & Technical Question Defenses', desc: 'Top domain questions & gap mitigation talking points' },
  { id: 'interviewer_questions', label: 'High-Leverage Questions to Ask', desc: 'Smart questions for recruiter & technical hiring rounds' },
  { id: 'prep_checklist', label: 'Final Pre-Interview Checklist', desc: 'Critical morning-of review items & strategy recap' },
]

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
  () => props.applicationId,
  async (newId) => {
    if (newId && props.isOpen) {
      await loadApplicationData(newId)
    }
  },
  { immediate: true }
)

watch(
  () => props.isOpen,
  async (open) => {
    if (open && props.applicationId) {
      await loadApplicationData(props.applicationId)
    }
  }
)

async function loadApplicationData(id) {
  isLoading.value = true
  try {
    const res = await ApplicationsAPI.get(id)
    application.value = res.data
    if (application.value.interview_guide_language) {
      selectedLanguage.value = application.value.interview_guide_language
    }
    if (application.value.interview_guide_preferences?.selected_sections) {
      selectedSections.value = application.value.interview_guide_preferences.selected_sections
    }
    if (application.value.interview_guide_preferences?.recursion_limit) {
      recursionLimit.value = application.value.interview_guide_preferences.recursion_limit
    }
    showConfigPanel.value = !application.value.interview_guide_html
  } catch (err) {
    uiStore.showToast('Failed to load application details', 'error')
  } finally {
    isLoading.value = false
  }
}

function toggleSection(sectionId) {
  const idx = selectedSections.value.indexOf(sectionId)
  if (idx > -1) {
    if (selectedSections.value.length === 1) {
      uiStore.showToast('At least one section must be selected', 'warning')
      return
    }
    selectedSections.value.splice(idx, 1)
  } else {
    selectedSections.value.push(sectionId)
  }
}

function selectAllSections() {
  selectedSections.value = ALL_SECTIONS.map((s) => s.id)
}

async function handleGenerate() {
  if (selectedSections.value.length === 0) {
    uiStore.showToast('Please select at least one section to generate', 'warning')
    return
  }

  isGenerating.value = true
  try {
    const payload = {
      language: selectedLanguage.value,
      selected_sections: selectedSections.value,
      recursion_limit: Number(recursionLimit.value) || 25,
    }
    const res = await ApplicationsAPI.generateInterviewGuide(props.applicationId, payload)
    application.value = res.data
    showConfigPanel.value = false
    uiStore.showToast('Interview Preparation Guide generated successfully!', 'success')
    emit('updated', res.data)
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to generate interview guide', 'error')
  } finally {
    isGenerating.value = false
  }
}

async function handleClearGuide() {
  if (!confirm('Are you sure you want to clear this interview preparation guide?')) return
  try {
    const res = await ApplicationsAPI.clearInterviewGuide(props.applicationId)
    application.value = res.data
    showConfigPanel.value = true
    uiStore.showToast('Interview guide cleared', 'info')
    emit('updated', res.data)
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast('Failed to clear interview guide', 'error')
  }
}

function handleCopy() {
  if (!application.value?.interview_guide_html) return
  // Create plain text extraction or copy rich text
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = application.value.interview_guide_html
  const plainText = tempDiv.innerText || tempDiv.textContent

  navigator.clipboard.writeText(plainText).then(() => {
    hasCopied.value = true
    uiStore.showToast('Guide copied to clipboard!', 'info')
    setTimeout(() => {
      hasCopied.value = false
    }, 2000)
  })
}

function handlePrint() {
  window.print()
}

function formatLanguageName(code) {
  const found = LANGUAGES.find((l) => l.code === code)
  return found ? found.label.split(' ')[0] : code?.toUpperCase() || 'EN'
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div v-if="isOpen" class="modal-backdrop print-hide" @click.self="emit('close')">
    <div class="modal-card animate-fade-in interview-modal-container">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-main-info">
          <div class="company-badge-icon">
            <BookOpen :size="18" class="text-primary" />
          </div>
          <div>
            <div class="header-title-row">
              <h2 class="modal-title">
                Interview Prep Guide
              </h2>
              <span v-if="application?.company?.name" class="company-tag">
                <Building2 :size="12" />
                <span>{{ application.company.name }}</span>
              </span>
              <span v-if="application?.position" class="position-tag">
                <Briefcase :size="12" />
                <span>{{ application.position }}</span>
              </span>
            </div>
            <p class="modal-subtitle">
              Tailored tactical playbook cross-referencing your candidate profile, role spec, and AI company research.
            </p>
          </div>
        </div>

        <button class="btn-close" @click="emit('close')">
          <X :size="18" />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body-scroll">
        <!-- 1. LOADING STATE -->
        <div v-if="isLoading" class="state-container">
          <Loader2 class="animate-spin text-primary" :size="32" />
          <span class="loading-label">Loading preparation dossier...</span>
        </div>

        <!-- 2. GENERATION RUNNING STATE -->
        <div v-else-if="isGenerating" class="state-container generating-state">
          <div class="pulse-glow-ring">
            <Sparkles :size="36" class="text-primary animate-pulse" />
          </div>
          <h3 class="generating-title">Synthesizing Interview Guide</h3>
          <p class="generating-desc">
            LangGraph agent is cross-referencing your CV skills, analyzing job requirements, and formulating tailored STAR defenses...
          </p>
          <div class="generating-steps">
            <div class="gen-step complete">
              <Check :size="14" />
              <span>Extracted role &amp; candidate baseline</span>
            </div>
            <div class="gen-step active">
              <Loader2 :size="14" class="animate-spin" />
              <span>Compiling company signals &amp; domain questions</span>
            </div>
            <div class="gen-step pending">
              <Layers :size="14" />
              <span>Drafting STAR story blueprints &amp; checklist</span>
            </div>
          </div>
        </div>

        <!-- 3. CONFIGURATION PANEL (If no guide or user clicked Re-configure) -->
        <div v-else-if="showConfigPanel" class="config-panel animate-fade-in">
          <div class="config-card">
            <div class="config-header">
              <div class="config-title">
                <Sparkles :size="16" class="text-primary" />
                <span>Configure Guide Generation</span>
              </div>
              <button
                v-if="application?.interview_guide_html"
                class="btn btn-ghost btn-xs text-secondary"
                @click="showConfigPanel = false"
              >
                Back to Generated Guide
              </button>
            </div>

            <!-- Language & Target Controls -->
            <div class="config-grid">
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
                <span class="input-hint">AI generates natural phrasing in target language while preserving technical terms.</span>
              </div>
            </div>

            <!-- Modular Section Checkboxes -->
            <div class="sections-picker-group">
              <div class="sections-picker-header">
                <label class="input-label">Select Guide Modules ({{ selectedSections.length }}/{{ ALL_SECTIONS.length }})</label>
                <button type="button" class="btn-text-link" @click="selectAllSections">
                  Select All
                </button>
              </div>

              <div class="sections-grid">
                <div
                  v-for="sec in ALL_SECTIONS"
                  :key="sec.id"
                  class="section-checkbox-card"
                  :class="{ active: selectedSections.includes(sec.id) }"
                  @click="toggleSection(sec.id)"
                >
                  <div class="checkbox-indicator">
                    <Check v-if="selectedSections.includes(sec.id)" :size="12" />
                  </div>
                  <div class="section-info">
                    <span class="sec-label">{{ sec.label }}</span>
                    <span class="sec-desc">{{ sec.desc }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Advanced Accordion -->
            <div class="advanced-accordion">
              <button
                type="button"
                class="accordion-toggle"
                @click="showAdvanced = !showAdvanced"
              >
                <div class="toggle-left">
                  <Sliders :size="14" />
                  <span>Advanced Agent Settings</span>
                </div>
                <component :is="showAdvanced ? ChevronUp : ChevronDown" :size="14" />
              </button>

              <div v-if="showAdvanced" class="accordion-body animate-fade-in">
                <div class="input-group">
                  <label class="input-label">LangGraph Recursion Limit</label>
                  <input
                    v-model.number="recursionLimit"
                    type="number"
                    min="5"
                    max="100"
                    class="form-input font-mono"
                    style="max-width: 140px;"
                  />
                  <span class="input-hint">Maximum state execution cycles. Default: 25.</span>
                </div>
              </div>
            </div>

            <!-- Generate Button -->
            <div class="config-actions">
              <button
                class="btn btn-primary btn-generate"
                :disabled="selectedSections.length === 0"
                @click="handleGenerate"
              >
                <Sparkles :size="16" />
                <span>{{ application?.interview_guide_html ? 'Regenerate Interview Guide' : 'Generate Interview Guide' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 4. GUIDE READER (When guide exists) -->
        <div v-else-if="application?.interview_guide_html" class="guide-reader-layout animate-fade-in">
          <!-- Reader Action Toolbar -->
          <div class="reader-toolbar">
            <div class="toolbar-left">
              <span class="badge-lang">
                <Globe :size="12" />
                <span>{{ formatLanguageName(application.interview_guide_language) }}</span>
              </span>
              <span v-if="application.interview_guide_generated_at" class="timestamp-label">
                Generated {{ formatDate(application.interview_guide_generated_at) }}
              </span>
            </div>

            <div class="toolbar-right">
              <button
                class="btn btn-secondary btn-sm"
                title="Print or Save as PDF"
                @click="handlePrint"
              >
                <Printer :size="14" />
                <span>Print / PDF</span>
              </button>

              <button
                class="btn btn-secondary btn-sm"
                :title="hasCopied ? 'Copied!' : 'Copy to Clipboard'"
                @click="handleCopy"
              >
                <component :is="hasCopied ? Check : Copy" :size="14" :class="{ 'text-success': hasCopied }" />
                <span>{{ hasCopied ? 'Copied' : 'Copy' }}</span>
              </button>

              <button
                class="btn btn-secondary btn-sm"
                title="Configure sections or language"
                @click="showConfigPanel = true"
              >
                <RotateCcw :size="14" />
                <span>Re-Configure</span>
              </button>

              <button
                class="btn btn-ghost btn-sm text-danger"
                title="Clear Guide"
                @click="handleClearGuide"
              >
                <Trash2 :size="14" />
              </button>
            </div>
          </div>

          <!-- Formatted Document Article -->
          <div class="guide-paper">
            <div
              class="guide-article"
              v-html="application.interview_guide_html"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.interview-modal-container {
  max-width: 960px;
  width: 95vw;
  height: 88vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}

.header-main-info {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.company-badge-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
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
  font-weight: var(--font-heading-weight);
  font-size: 20px;
  color: var(--text-main);
  margin: 0;
}

.company-tag, .position-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-secondary);
}

.modal-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 3px 0 0 0;
  line-height: 1.4;
}

.modal-body-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  scrollbar-gutter: stable;
  background-color: var(--bg-app);
}

/* States */
.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 380px;
  gap: 16px;
  text-align: center;
}

.loading-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.generating-state {
  max-width: 520px;
  margin: 0 auto;
}

.pulse-glow-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background-color: var(--primary-subtle);
  border: 2px solid var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 24px var(--primary-glow);
}

.generating-title {
  font-family: var(--font-heading);
  font-size: 20px;
  color: var(--text-main);
  margin: 0;
}

.generating-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.generating-steps {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.gen-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--text-secondary);
}

.gen-step.complete {
  color: var(--text-success);
  border-color: var(--status-offer-border);
}

.gen-step.active {
  color: var(--primary);
  border-color: var(--primary-glow);
  font-weight: 500;
}

/* Config Panel */
.config-panel {
  max-width: 740px;
  margin: 0 auto;
}

.config-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.config-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.sections-picker-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sections-picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.btn-text-link {
  font-size: 12px;
  color: var(--primary);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}

.btn-text-link:hover {
  text-decoration: underline;
}

.sections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 10px;
}

.section-checkbox-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.section-checkbox-card:hover {
  border-color: var(--border-focus);
}

.section-checkbox-card.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.checkbox-indicator {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  flex-shrink: 0;
  margin-top: 2px;
}

.section-checkbox-card.active .checkbox-indicator {
  border-color: var(--primary);
  background-color: var(--primary);
  color: #fff;
}

.section-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sec-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.sec-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.advanced-accordion {
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
}

.accordion-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px 0;
}

.accordion-toggle:hover {
  color: var(--text-main);
}

.toggle-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.accordion-body {
  margin-top: 10px;
  padding-left: 20px;
}

.config-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.btn-generate {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-weight: 600;
}

/* Guide Reader Layout */
.guide-reader-layout {
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reader-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge-lang {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
  font-size: 11px;
  font-weight: 600;
}

.timestamp-label {
  font-size: 12px;
  color: var(--text-muted);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-paper {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 36px 40px;
  box-shadow: var(--shadow-sm);
}

/* Clean Formatted Article Styling */
.guide-article :deep(h1) {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 22px;
  color: var(--text-main);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
  margin-top: 24px;
  margin-bottom: 14px;
}

.guide-article :deep(h1:first-child) {
  margin-top: 0;
}

.guide-article :deep(h2) {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 18px;
  color: var(--text-main);
  margin-top: 28px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-article :deep(h3) {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin-top: 18px;
  margin-bottom: 8px;
}

.guide-article :deep(p) {
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-main);
  margin-bottom: 12px;
}

.guide-article :deep(strong) {
  color: var(--text-main);
  font-weight: 600;
}

.guide-article :deep(ul) {
  margin-bottom: 16px;
  padding-left: 22px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.guide-article :deep(li) {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.guide-article :deep(li strong) {
  color: var(--text-main);
}

.guide-article :deep(blockquote) {
  margin: 16px 0;
  padding: 12px 16px;
  border-left: 3px solid var(--primary);
  background-color: var(--bg-surface);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.55;
}

/* Print Overrides */
@media print {
  body * {
    visibility: hidden;
  }
  .print-hide {
    display: none !important;
  }
  .interview-modal-container,
  .interview-modal-container * {
    visibility: visible;
  }
  .interview-modal-container {
    position: absolute;
    left: 0;
    top: 0;
    width: 100% !important;
    height: auto !important;
    border: none !important;
    box-shadow: none !important;
    background: #ffffff !important;
    color: #000000 !important;
  }
  .guide-paper {
    border: none !important;
    padding: 0 !important;
  }
  .guide-article :deep(*) {
    color: #000000 !important;
  }
}
</style>
