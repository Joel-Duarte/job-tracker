<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import {
  X,
  Sparkles,
  Copy,
  Check,
  Save,
  RotateCcw,
  Loader2,
  FileText,
  AlertCircle,
  Bold,
  Italic,
  List,
  Heading,
} from 'lucide-vue-next'
import { CoverLettersAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  applicationId: {
    type: [Number, String],
    default: null,
  },
  applicationTitle: {
    type: String,
    default: 'Cover Letter',
  },
  companyName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close', 'saved', 'generated'])

const uiStore = useUIStore()

const content = ref('')
const status = ref('PENDING')
const highlightedSkills = ref([])
const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const copied = ref(false)
const showPromptOverride = ref(false)
const customPrompt = ref('')
const isEditing = ref(true)

async function fetchCoverLetter() {
  if (!props.applicationId) return
  loading.value = true
  try {
    const res = await CoverLettersAPI.get(props.applicationId)
    const data = res.data || {}
    content.value = data.cover_letter_markdown || ''
    status.value = data.cover_letter_status || 'PENDING'
    highlightedSkills.value = data.highlighted_skills || []
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to load cover letter', 'error')
  } finally {
    loading.value = false
  }
}

async function saveChanges() {
  if (!props.applicationId) return
  saving.value = true
  try {
    await CoverLettersAPI.update(props.applicationId, { content: content.value })
    uiStore.showToast('Cover letter saved successfully!', 'success')
    emit('saved', content.value)
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save cover letter', 'error')
  } finally {
    saving.value = false
  }
}

async function triggerGenerate() {
  if (!props.applicationId) return
  generating.value = true
  status.value = 'GENERATING'
  try {
    const payload = customPrompt.value.trim() ? { custom_instructions: customPrompt.value.trim() } : {}
    await CoverLettersAPI.generate(props.applicationId, payload)
    uiStore.showToast('Cover letter generation task queued!', 'success')
    showPromptOverride.value = false
    emit('generated')
    // Poll status briefly
    setTimeout(fetchCoverLetter, 2000)
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to trigger cover letter generation', 'error')
    status.value = 'FAILED'
  } finally {
    generating.value = false
  }
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(content.value)
    copied.value = true
    uiStore.showToast('Cover letter copied to clipboard!', 'success')
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    uiStore.showToast('Failed to copy to clipboard', 'error')
  }
}

function handleClose() {
  emit('close')
}

function handleKeyDown(e) {
  if (e.key === 'Escape' && props.isOpen) {
    handleClose()
  }
}

function insertFormatting(prefix, suffix = '') {
  const textarea = document.getElementById('cover-letter-textarea')
  if (!textarea) return
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const selected = content.value.substring(start, end)
  const replacement = prefix + selected + suffix
  content.value = content.value.substring(0, start) + replacement + content.value.substring(end)
}

watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal && props.applicationId) {
      fetchCoverLetter()
    }
  }
)

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="modal-backdrop animate-fade-in"
      @click.self="handleClose"
    >
      <div class="modal-card animate-scale-up" @click.stop>
        <!-- Modal Header -->
        <div class="modal-header">
          <div class="modal-title-group">
            <Sparkles :size="20" class="text-primary" />
            <div>
              <h2 class="modal-title">
                Cover Letter {{ companyName ? '• ' + companyName : '' }}
              </h2>
              <p class="modal-subtitle">{{ applicationTitle }}</p>
            </div>
          </div>

          <div class="modal-header-actions">
            <div class="status-chip" :class="`chip-${status.toLowerCase()}`">
              <Loader2 v-if="status === 'GENERATING'" class="animate-spin" :size="12" />
              <span>{{ status }}</span>
            </div>
            <button class="btn-close" @click="handleClose" title="Close Modal">
              <X :size="18" />
            </button>
          </div>
        </div>

        <!-- Highlighted Skills Bar -->
        <div v-if="highlightedSkills.length > 0" class="skills-bar">
          <span class="skills-label">Highlighted Skills:</span>
          <div class="skills-list">
            <span v-for="skill in highlightedSkills" :key="skill" class="skill-badge">
              {{ skill }}
            </span>
          </div>
        </div>

        <!-- Editor Controls Toolbar -->
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <button
              class="tb-btn"
              title="Bold"
              @click="insertFormatting('**', '**')"
            >
              <Bold :size="14" />
            </button>
            <button
              class="tb-btn"
              title="Italic"
              @click="insertFormatting('*', '*')"
            >
              <Italic :size="14" />
            </button>

            <button
              class="tb-btn"
              title="Heading"
              @click="insertFormatting('### ')"
            >
              <Heading :size="14" />
            </button>

            <button
              class="tb-btn"
              title="Bullet List"
              @click="insertFormatting('- ')"
            >
              <List :size="14" />
            </button>
          </div>

          <div class="toolbar-right">
            <button class="btn btn-secondary btn-xs" @click="copyToClipboard">
              <Check v-if="copied" :size="13" class="text-success" />
              <Copy v-else :size="13" />
              <span>{{ copied ? 'Copied' : 'Copy Text' }}</span>
            </button>

            <button
              class="btn btn-secondary btn-xs"
              @click="showPromptOverride = !showPromptOverride"
            >
              <Sparkles :size="13" />
              <span>{{ showPromptOverride ? 'Hide Custom Prompt' : 'Custom Prompt' }}</span>
            </button>
          </div>
        </div>

        <!-- Custom Prompt Override Section -->
        <div v-if="showPromptOverride" class="prompt-override-box animate-fade-in">
          <label class="prompt-label">Custom Generation Instructions / Tone Override:</label>
          <textarea
            v-model="customPrompt"
            class="prompt-textarea"
            placeholder="e.g. Emphasize senior engineering leadership experience, keep tone energetic and concise..."
            rows="2"
          ></textarea>
        </div>

        <!-- Main Body Editor -->
        <div class="modal-body">
          <div v-if="loading" class="loading-state">
            <Loader2 class="animate-spin text-primary" :size="32" />
            <span>Fetching cover letter...</span>
          </div>

          <div v-else-if="status === 'GENERATING'" class="generating-state">
            <Loader2 class="animate-spin text-primary" :size="36" />
            <h3>Generating Cover Letter with AI</h3>
            <p>Analyzing job requirements, matching canonical CV skills, and crafting tailored draft...</p>
          </div>

          <div v-else class="editor-container">
            <textarea
              id="cover-letter-textarea"
              v-model="content"
              class="cover-letter-textarea"
              placeholder="Your cover letter content will appear here..."
            ></textarea>
          </div>
        </div>

        <!-- Modal Footer Actions -->
        <div class="modal-footer">
          <div class="footer-left">
            <button
              class="btn btn-secondary btn-sm"
              :disabled="generating || status === 'GENERATING'"
              @click="triggerGenerate"
            >
              <Loader2 v-if="generating" class="animate-spin" :size="14" />
              <RotateCcw v-else :size="14" />
              <span>Regenerate Draft</span>
            </button>
          </div>

          <div class="footer-right">
            <button class="btn btn-ghost btn-sm" @click="handleClose">Cancel</button>
            <button
              class="btn btn-primary btn-sm"
              :disabled="saving || loading"
              @click="saveChanges"
            >
              <Loader2 v-if="saving" class="animate-spin" :size="14" />
              <Save v-else :size="14" />
              <span>Save Changes</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  padding: 24px;
}

.modal-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: 100%;
  max-width: 780px;
  max-height: 90vh;
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
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.chip-completed {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.chip-generating, .chip-pending {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
}

.chip-failed {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.chip-skipped {
  background-color: var(--bg-elevated);
  color: var(--text-muted);
}

.btn-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-close:hover {
  color: var(--text-main);
  background-color: var(--bg-surface-hover);
}

.skills-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background-color: var(--bg-main);
  border-bottom: 1px solid var(--border-subtle);
}

.skills-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.skill-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
  font-family: var(--font-mono);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tb-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tb-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.prompt-override-box {
  padding: 12px 20px;
  background-color: var(--bg-main);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.prompt-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.prompt-textarea {
  width: 100%;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  font-size: 12px;
  outline: none;
  resize: vertical;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  min-height: 280px;
  display: flex;
  flex-direction: column;
}

.loading-state, .generating-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
  color: var(--text-secondary);
}

.generating-state h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.generating-state p {
  font-size: 12px;
  max-width: 400px;
}

.editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.cover-letter-textarea {
  width: 100%;
  min-height: 320px;
  padding: 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
  outline: none;
  resize: vertical;
}

.cover-letter-textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 1px var(--primary-glow);
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-surface);
}

.footer-left, .footer-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
