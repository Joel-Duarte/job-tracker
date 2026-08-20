<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { ApplicationsAPI } from '../../api/endpoints'
import DOMPurify from 'dompurify'
import {
  X,
  FileText,
  Sparkles,
  RotateCcw,
  Check,
  Loader2,
  Copy,
  Edit3,
  Eye,
  Sliders,
  ChevronDown,
  ChevronUp,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const { isCoverLetterModalOpen, coverLetterAppId } = storeToRefs(uiStore)

const application = ref(null)
const isLoadingApp = ref(false)
const isGenerating = ref(false)

// Editor state
const editableText = ref('')
const tone = ref('professional')
const length = ref(uiStore.coverLetterLength || 'standard')
const customInstructions = ref('')
const isPreviewMode = ref(false)
const isOptionsExpanded = ref(false)

// Auto-save state
const autoSaveStatus = ref('saved') // 'saved' | 'saving' | 'error' | 'unsaved'
let autoSaveTimer = null

const COVER_LETTER_TONES = [
  { code: 'professional', label: 'Professional & Confident' },
  { code: 'enthusiastic', label: 'Enthusiastic & Passionate' },
  { code: 'concise', label: 'Concise & Direct' },
  { code: 'executive', label: 'Executive Leadership' },
  { code: 'technical', label: 'Technical & Systems Focused' },
]

const COVER_LETTER_LENGTHS = [
  { code: 'concise', label: 'Concise (~150 words)' },
  { code: 'standard', label: 'Standard (~300 words)' },
  { code: 'detailed', label: 'Detailed (~450 words)' },
]

const charCount = computed(() => editableText.value.length)
const wordCount = computed(() => {
  const trimmed = editableText.value.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
})

const currentToneLabel = computed(() => {
  const found = COVER_LETTER_TONES.find((t) => t.code === tone.value)
  return found ? found.label : 'Professional & Confident'
})

const currentLengthLabel = computed(() => {
  const found = COVER_LETTER_LENGTHS.find((l) => l.code === length.value)
  return found ? found.label : 'Standard (~300 words)'
})

const renderedMarkdown = computed(() => {
  if (!editableText.value) return ''
  let html = editableText.value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')

  const lines = html.split('\n')
  let inList = false
  const out = []

  for (const line of lines) {
    const bulletMatch = line.match(/^[\-\*]\s+(.*)$/)
    if (bulletMatch) {
      if (!inList) {
        inList = true
        out.push('<ul class="cl-preview-list">')
      }
      out.push(`<li>${bulletMatch[1]}</li>`)
    } else {
      if (inList) {
        inList = false
        out.push('</ul>')
      }
      out.push(line)
    }
  }
  if (inList) out.push('</ul>')

  const fullHtml = out.join('\n').replace(/\n/g, '<br>').replace(/<br><ul/g, '<ul').replace(/<\/ul><br>/g, '</ul>')
  return DOMPurify.sanitize(fullHtml)
})

watch(
  [isCoverLetterModalOpen, coverLetterAppId],
  async ([isOpen, appId]) => {
    if (isOpen && appId) {
      isLoadingApp.value = true
      autoSaveStatus.value = 'saved'
      length.value = uiStore.coverLetterLength || 'standard'
      try {
        const res = await ApplicationsAPI.getCoverLetter(appId)
        application.value = res.data
        editableText.value = res.data.cover_letter_text || ''
      } catch (err) {
        // Fallback to appStore if detailed endpoint fails or app object in store
        const found = appStore.applications.find((a) => a.id === appId)
        if (found) {
          application.value = found
          editableText.value = found.cover_letter_text || ''
        } else {
          uiStore.showToast('Failed to load application cover letter', 'error')
        }
      } finally {
        isLoadingApp.value = false
        // Collapsed if letter exists, expanded if empty draft
        isOptionsExpanded.value = !editableText.value && !application.value?.cover_letter_text
      }
    } else {
      application.value = null
      editableText.value = ''
      customInstructions.value = ''
      tone.value = 'professional'
      length.value = uiStore.coverLetterLength || 'standard'
      isPreviewMode.value = false
      isOptionsExpanded.value = false
    }
  },
  { immediate: true }
)

function toggleOptionsPanel() {
  isOptionsExpanded.value = !isOptionsExpanded.value
}

function onTextChange() {
  autoSaveStatus.value = 'unsaved'
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    saveCoverLetterChanges()
  }, 600)
}

async function saveCoverLetterChanges() {
  if (!coverLetterAppId.value) return
  autoSaveStatus.value = 'saving'
  try {
    const res = await ApplicationsAPI.updateCoverLetter(coverLetterAppId.value, {
      cover_letter_text: editableText.value,
      cover_letter_status: editableText.value ? 'DRAFTED' : application.value?.cover_letter_status,
    })
    if (application.value) {
      application.value.cover_letter_text = res.data.cover_letter_text
      application.value.cover_letter_status = res.data.cover_letter_status
    }
    const storeApp = appStore.applications.find((a) => a.id === coverLetterAppId.value)
    if (storeApp) {
      storeApp.cover_letter_text = res.data.cover_letter_text
      storeApp.cover_letter_status = res.data.cover_letter_status
    }
    autoSaveStatus.value = 'saved'
  } catch (err) {
    autoSaveStatus.value = 'error'
    uiStore.showToast('Failed to auto-save cover letter edits', 'error')
  }
}

async function handleGenerateCoverLetter() {
  if (!coverLetterAppId.value) return
  isGenerating.value = true
  try {
    const res = await ApplicationsAPI.generateCoverLetter(coverLetterAppId.value, {
      tone: tone.value,
      length: length.value,
      custom_instructions: customInstructions.value,
    })
    if (application.value) {
      application.value.cover_letter_text = res.data.cover_letter_text
      application.value.cover_letter_status = res.data.cover_letter_status || 'QUEUED'
      application.value.cover_letter_generated_at = res.data.cover_letter_generated_at
    }
    editableText.value = res.data.cover_letter_text || ''
    autoSaveStatus.value = 'saved'
    uiStore.showToast('Cover letter queued for background generation!', 'success')
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to generate cover letter', 'error')
  } finally {
    isGenerating.value = false
  }
}

async function handleRegenerateCoverLetter() {
  if (!coverLetterAppId.value) return
  isGenerating.value = true
  try {
    const res = await ApplicationsAPI.regenerateCoverLetter(coverLetterAppId.value, {
      tone: tone.value,
      length: length.value,
      custom_instructions: customInstructions.value,
    })
    if (application.value) {
      application.value.cover_letter_text = res.data.cover_letter_text
      application.value.cover_letter_status = res.data.cover_letter_status || 'QUEUED'
      application.value.cover_letter_generated_at = res.data.cover_letter_generated_at
    }
    editableText.value = res.data.cover_letter_text || ''
    autoSaveStatus.value = 'saved'
    uiStore.showToast('Cover letter regeneration queued!', 'success')
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to regenerate cover letter', 'error')
  } finally {
    isGenerating.value = false
  }
}

function copyToClipboard() {
  if (!editableText.value) return
  navigator.clipboard.writeText(editableText.value)
  uiStore.showToast('Cover letter copied to clipboard!', 'success')
}

function close() {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
    saveCoverLetterChanges()
  }
  uiStore.closeCoverLetterModal()
}

onUnmounted(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
})
</script>

<template>
  <Transition name="fade">
    <div
      v-if="isCoverLetterModalOpen"
      class="cover-letter-modal-backdrop"
      @click.self="close"
    >
      <div class="cover-letter-modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-title-group">
            <div class="modal-icon">
              <FileText :size="20" class="text-primary" />
            </div>
            <div>
              <h3 class="modal-title">
                Cover Letter — {{ application?.company_name || application?.company?.name || 'Application' }}
              </h3>
              <p class="modal-subtitle">
                {{ application?.position || 'Tailored Application Document' }}
              </p>
            </div>
          </div>
          <button class="btn-close" @click="close">
            <X :size="18" />
          </button>
        </div>

        <!-- Body -->
        <div class="modal-body">
          <div v-if="isLoadingApp" class="loading-state">
            <Loader2 class="animate-spin text-primary" :size="28" />
            <span>Loading cover letter document...</span>
          </div>

          <div v-else-if="isGenerating" class="loading-state">
            <div class="pulse-ring">
              <Sparkles :size="32" class="text-primary animate-pulse" />
            </div>
            <h4>Generating Tailored Cover Letter</h4>
            <p class="text-muted text-xs">
              AI is mapping candidate profile experiences to job requirements...
            </p>
          </div>

          <div v-else class="modal-content-layout">
            <!-- Collapsible Regenerate & Tone Options Panel -->
            <div class="options-accordion" :class="{ expanded: isOptionsExpanded }">
              <button
                type="button"
                class="options-header-btn"
                @click="toggleOptionsPanel"
                :aria-expanded="isOptionsExpanded"
              >
                <div class="options-header-left">
                  <Sliders :size="14" class="text-primary" />
                  <span class="options-title">Regenerate & Tone Options</span>
                  <span v-if="!isOptionsExpanded" class="options-tone-badge">
                    {{ currentToneLabel }} • {{ currentLengthLabel }}
                  </span>
                </div>
                <div class="options-header-right">
                  <span class="options-toggle-label">
                    {{ isOptionsExpanded ? 'Hide Options' : 'Customize Tone & Prompt' }}
                  </span>
                  <ChevronUp v-if="isOptionsExpanded" :size="16" class="accordion-chevron" />
                  <ChevronDown v-else :size="16" class="accordion-chevron" />
                </div>
              </button>

              <Transition name="accordion">
                <div v-if="isOptionsExpanded" class="options-body">
                  <div class="controls-grid">
                    <div class="form-group">
                      <label class="form-label text-xs">Desired Tone</label>
                      <select v-model="tone" class="form-select form-select-sm">
                        <option v-for="t in COVER_LETTER_TONES" :key="t.code" :value="t.code">
                          {{ t.label }}
                        </option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label class="form-label text-xs">Length Target</label>
                      <select v-model="length" class="form-select form-select-sm">
                        <option v-for="l in COVER_LETTER_LENGTHS" :key="l.code" :value="l.code">
                          {{ l.label }}
                        </option>
                      </select>
                    </div>
                    <div class="form-group form-group-wide">
                      <label class="form-label text-xs">Custom Instructions (Optional)</label>
                      <input
                        v-model="customInstructions"
                        type="text"
                        placeholder="e.g. Focus on distributed systems & leadership..."
                        class="form-input form-input-sm"
                      />
                    </div>
                  </div>

                  <div class="options-action-row">
                    <button
                      class="btn btn-primary btn-sm btn-generate-new"
                      @click="editableText || application?.cover_letter_text ? handleRegenerateCoverLetter() : handleGenerateCoverLetter()"
                    >
                      <RotateCcw :size="14" />
                      <span>Generate New Version</span>
                    </button>
                  </div>
                </div>
              </Transition>
            </div>
            <!-- Editor Section -->
            <div class="editor-container">
              <div class="editor-toolbar">
                <div class="mode-toggle-group">
                  <button
                    class="mode-btn"
                    :class="{ active: !isPreviewMode }"
                    @click="isPreviewMode = false"
                  >
                    <Edit3 :size="13" />
                    <span>Edit Text</span>
                  </button>
                  <button
                    class="mode-btn"
                    :class="{ active: isPreviewMode }"
                    @click="isPreviewMode = true"
                  >
                    <Eye :size="13" />
                    <span>Formatted Preview</span>
                  </button>
                </div>

                <div class="toolbar-actions">
                  <!-- Auto-save indicator -->
                  <div class="autosave-badge" :class="`status-${autoSaveStatus}`">
                    <Loader2 v-if="autoSaveStatus === 'saving'" class="animate-spin" :size="12" />
                    <Check v-else-if="autoSaveStatus === 'saved'" :size="12" />
                    <span>
                      {{
                        autoSaveStatus === 'saving'
                          ? 'Saving...'
                          : autoSaveStatus === 'saved'
                          ? 'Saved'
                          : autoSaveStatus === 'unsaved'
                          ? 'Unsaved changes'
                          : 'Save error'
                      }}
                    </span>
                  </div>

                  <button
                    class="btn btn-secondary btn-xs"
                    title="Copy to clipboard"
                    :disabled="!editableText"
                    @click="copyToClipboard"
                  >
                    <Copy :size="13" />
                    <span>Copy</span>
                  </button>
                </div>
              </div>

              <!-- Textarea Editor -->
              <div v-if="!isPreviewMode" class="textarea-wrapper">
                <textarea
                  v-model="editableText"
                  rows="14"
                  placeholder="Type or paste your cover letter here..."
                  class="cl-textarea"
                  @input="onTextChange"
                ></textarea>
              </div>

              <!-- Formatted Preview -->
              <div
                v-else
                class="cl-formatted-preview font-mono text-xs whitespace-pre-wrap"
                v-html="renderedMarkdown"
              ></div>

              <!-- Word & Character Count Footer Bar -->
              <div class="editor-footer">
                <div class="count-stats">
                  <span>{{ wordCount }} words</span>
                  <span class="dot-sep">•</span>
                  <span>{{ charCount }} characters</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="close">Close</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.cover-letter-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 600;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.cover-letter-modal-box {
  width: 100%;
  max-width: 720px;
  max-height: 90vh;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-sidebar);
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
}

.modal-title {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 16px;
  color: var(--text-main);
  margin: 0;
  line-height: 1.2;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  text-align: center;
}

.pulse-ring {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Accordion Options Panel */
.options-accordion {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color var(--transition-fast);
}

.options-accordion.expanded {
  border-color: var(--primary-glow);
}

.options-header-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-main);
  text-align: left;
  transition: background-color var(--transition-fast);
}

.options-header-btn:hover {
  background-color: var(--bg-elevated);
}

.options-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.options-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.options-tone-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.options-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.options-toggle-label {
  font-size: 12px;
  font-weight: 500;
}

.accordion-chevron {
  color: var(--text-muted);
}

.options-body {
  padding: 12px 14px 14px 14px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.controls-grid {
  display: grid;
  grid-template-columns: 180px 180px 1fr;
  gap: 12px;
}

@media (max-width: 640px) {
  .controls-grid {
    grid-template-columns: 1fr;
  }
}

.options-action-row {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

.btn-generate-new {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.empty-draft-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
  background-color: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  gap: 8px;
}

.empty-draft-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: var(--primary-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.empty-draft-title {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.empty-draft-desc {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 420px;
  margin: 0;
}

.btn-generate {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-weight: 600;
}

.editor-container {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
}

.mode-toggle-group {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-xs);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mode-btn.active {
  background-color: var(--primary);
  color: #ffffff;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.autosave-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.autosave-badge.status-saved {
  color: var(--text-success, #10b981);
  background-color: rgba(16, 185, 129, 0.1);
}

.autosave-badge.status-saving {
  color: var(--primary);
  background-color: var(--primary-subtle);
}

.autosave-badge.status-unsaved {
  color: var(--text-secondary);
  background-color: var(--bg-elevated);
}

.autosave-badge.status-error {
  color: var(--status-rejected-text);
  background-color: var(--status-rejected-bg);
}

.textarea-wrapper {
  padding: 12px;
}

.cl-textarea {
  width: 100%;
  min-height: 280px;
  padding: 10px;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-main);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  resize: vertical;
  outline: none;
}

.cl-textarea:focus {
  border-color: var(--primary);
}

.cl-formatted-preview {
  padding: 16px;
  min-height: 280px;
  max-height: 420px;
  overflow-y: auto;
  line-height: 1.6;
  color: var(--text-main);
  background-color: var(--bg-surface);
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 8px 14px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.count-stats {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot-sep {
  opacity: 0.5;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 12px 20px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.accordion-enter-active,
.accordion-leave-active {
  transition: all 0.2s ease;
}

.accordion-enter-from,
.accordion-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
