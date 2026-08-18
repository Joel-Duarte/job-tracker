<script setup>
import { ref, watch } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import { IntakeAPI } from '../../api/endpoints'
import { exportHTMLToPDF } from '../../utils/pdfExporter'
import { X, Copy, Download, Save, Code, Eye, FileText, FileEdit, Check } from 'lucide-vue-next'

const props = defineProps({
  isOpen: Boolean,
  documentHtml: String,
  documentType: String, // 'cover_letter' or 'tailored_cv'
  taskId: Number
})

const emit = defineEmits(['close', 'saved'])
const uiStore = useUIStore()

const isEditing = ref(false)
const editedHtml = ref('')
const isSaving = ref(false)
const hasCopied = ref(false)

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    editedHtml.value = props.documentHtml || ''
    isEditing.value = false
    hasCopied.value = false
  }
})

function handleCopy() {
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = editedHtml.value
  const plainText = tempDiv.innerText || tempDiv.textContent

  navigator.clipboard.writeText(plainText).then(() => {
    hasCopied.value = true
    uiStore.showToast('Document text copied to clipboard', 'success')
    setTimeout(() => {
      hasCopied.value = false
    }, 2000)
  }).catch(() => {
    uiStore.showToast('Failed to copy text', 'error')
  })
}

function handleDownloadPDF() {
  exportHTMLToPDF(editedHtml.value, `${props.documentType}_export.pdf`)
  uiStore.showToast('PDF Export generated', 'info')
}

async function handleSave() {
  isSaving.value = true
  try {
    const payload = {}
    if (props.documentType === 'cover_letter') {
      payload.cover_letter_markdown = editedHtml.value
    } else {
      payload.tailored_cv_markdown = editedHtml.value
    }

    await IntakeAPI.updateDocuments(props.taskId, payload)
    uiStore.showToast('Document saved successfully', 'success')
    emit('saved', editedHtml.value, props.documentType, props.taskId)
    isEditing.value = false
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save document', 'error')
  } finally {
    isSaving.value = false
  }
}

function close() {
  emit('close')
}
</script>

<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="close">
    <div class="modal-card animate-fade-in">

      <!-- Header -->
      <div class="modal-header">
        <div class="header-left">
          <FileText v-if="documentType === 'cover_letter'" :size="18" class="text-primary" />
          <FileEdit v-else :size="18" class="text-primary" />
          <h2 class="modal-title">{{ documentType === 'cover_letter' ? 'Cover Letter Editor' : 'Tailored CV Editor' }}</h2>
        </div>

        <div class="header-actions">
          <button class="btn btn-secondary btn-sm" @click="isEditing = !isEditing">
            <component :is="isEditing ? Eye : Code" :size="14" />
            <span>{{ isEditing ? 'Preview' : 'Edit Source' }}</span>
          </button>

          <button class="btn btn-secondary btn-sm" @click="handleCopy">
            <component :is="hasCopied ? Check : Copy" :size="14" :class="{'text-success': hasCopied}" />
            <span>{{ hasCopied ? 'Copied' : 'Copy' }}</span>
          </button>

          <button class="btn btn-secondary btn-sm" @click="handleDownloadPDF">
            <Download :size="14" />
            <span>PDF</span>
          </button>

          <button v-if="isEditing" class="btn btn-primary btn-sm" :disabled="isSaving" @click="handleSave">
            <Save :size="14" />
            <span>{{ isSaving ? 'Saving...' : 'Save' }}</span>
          </button>

          <button class="btn-close" @click="close">
            <X :size="18" />
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="modal-body">

        <!-- Editor View -->
        <div v-if="isEditing" class="editor-container">
          <textarea
            v-model="editedHtml"
            class="form-textarea html-editor font-mono"
            placeholder="Edit HTML/Markdown content here..."
          ></textarea>
        </div>

        <!-- Preview View -->
        <div v-else class="preview-container guide-article">
          <div class="document-paper" v-html="editedHtml"></div>
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
  z-index: 1000;
  padding: 24px;
}

.modal-card {
  width: 100%;
  max-width: 900px;
  height: 85vh;
  background-color: var(--bg-card);
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
  background-color: var(--bg-surface);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-app);
}

.editor-container {
  flex: 1;
  padding: 20px;
  display: flex;
}

.html-editor {
  flex: 1;
  resize: none;
  font-size: 13px;
  line-height: 1.6;
  padding: 16px;
}

.preview-container {
  flex: 1;
  overflow-y: auto;
  padding: 32px 40px;
  display: flex;
  justify-content: center;
}

.document-paper {
  background-color: var(--bg-card);
  width: 100%;
  max-width: 800px;
  padding: 40px 50px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
}

/* Styled Article Elements inside Preview */
.guide-article :deep(h1) { font-family: var(--font-heading); font-size: 24px; font-weight: 700; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 16px; }
.guide-article :deep(h2) { font-family: var(--font-heading); font-size: 20px; font-weight: 700; margin-top: 24px; margin-bottom: 12px; }
.guide-article :deep(h3) { font-family: var(--font-heading); font-size: 16px; font-weight: 600; margin-top: 20px; margin-bottom: 10px; }
.guide-article :deep(p) { margin-bottom: 14px; line-height: 1.6; color: var(--text-secondary); }
.guide-article :deep(ul) { margin-bottom: 14px; padding-left: 24px; display: flex; flex-direction: column; gap: 6px; }
.guide-article :deep(li) { line-height: 1.5; color: var(--text-secondary); }
.guide-article :deep(strong) { font-weight: 600; color: var(--text-main); }
</style>
