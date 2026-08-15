<script setup>
import { ref } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { IntakeAPI } from '../../api/endpoints'
import {
  X,
  FileText,
  UploadCloud,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Inbox,
  Sparkles,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const activeTab = ref('paste') // 'paste' | 'upload'
const pasteText = ref('')
const pasteSubject = ref('')
const selectedFiles = ref([])
const isDragging = ref(false)
const isSubmitting = ref(false)
const ingestResult = ref(null)

function close() {
  uiStore.closeIngestModal()
  // Reset state after transition
  setTimeout(() => {
    pasteText.value = ''
    pasteSubject.value = ''
    selectedFiles.value = []
    ingestResult.value = null
  }, 200)
}

async function handlePasteSubmit() {
  if (!pasteText.value.trim()) return
  isSubmitting.value = true
  ingestResult.value = null

  try {
    const res = await IntakeAPI.paste({
      text: pasteText.value,
      subject: pasteSubject.value || null,
    })
    ingestResult.value = res.data
    uiStore.showToast('Intake processed successfully', 'success')
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files || [])
  selectedFiles.value = files
}

function handleFileDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files || [])
  selectedFiles.value = files
}

async function handleUploadSubmit() {
  if (selectedFiles.value.length === 0) return
  isSubmitting.value = true
  ingestResult.value = null

  try {
    const formData = new FormData()
    for (const file of selectedFiles.value) {
      formData.append('files', file)
    }

    const res = await IntakeAPI.upload(formData)
    ingestResult.value = {
      isBatch: true,
      items: res.data,
    }
    uiStore.showToast(`Uploaded ${res.data.length} files`, 'success')
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="uiStore.isIngestModalOpen" class="modal-backdrop" @click.self="close">
    <div class="modal-card animate-fade-in">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="modal-title-group">
          <div class="title-icon">
            <Sparkles :size="18" />
          </div>
          <div>
            <h2 class="modal-title">Quick Ingest</h2>
            <p class="modal-subtitle">Feed raw email text or files to the LangGraph pipeline</p>
          </div>
        </div>
        <button class="btn-close" @click="close">
          <X :size="18" />
        </button>
      </div>

      <!-- Tab Switcher -->
      <div class="tab-bar">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'paste' }"
          @click="activeTab = 'paste'"
        >
          <FileText :size="15" />
          <span>Paste Text</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'upload' }"
          @click="activeTab = 'upload'"
        >
          <UploadCloud :size="15" />
          <span>Upload Files (.eml, .msg)</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        <!-- TAB 1: PASTE -->
        <div v-if="activeTab === 'paste'" class="tab-content">
          <div class="input-group">
            <label class="input-label">Subject Line (Optional)</label>
            <input
              v-model="pasteSubject"
              type="text"
              placeholder="e.g. Thanks for applying to Stripe"
              class="form-input"
            />
          </div>

          <div class="input-group">
            <label class="input-label">Email / Thread Body Text *</label>
            <textarea
              v-model="pasteText"
              rows="7"
              placeholder="Paste email content, rejection note, interview invite, or job posting text here..."
              class="form-textarea"
              required
            ></textarea>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="close" :disabled="isSubmitting">
              Cancel
            </button>
            <button
              class="btn btn-primary"
              @click="handlePasteSubmit"
              :disabled="isSubmitting || !pasteText.trim()"
            >
              <Loader2 v-if="isSubmitting" class="animate-spin" :size="16" />
              <span>{{ isSubmitting ? 'Analyzing with LangGraph...' : 'Parse & Ingest' }}</span>
            </button>
          </div>
        </div>

        <!-- TAB 2: UPLOAD -->
        <div v-else-if="activeTab === 'upload'" class="tab-content">
          <div
            class="dropzone"
            :class="{ active: isDragging, 'has-files': selectedFiles.length > 0 }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleFileDrop"
          >
            <UploadCloud :size="32" class="dropzone-icon" />
            <div class="dropzone-text">
              <span class="dropzone-highlight">Click to browse</span> or drag and drop email files
            </div>
            <span class="dropzone-hint">Supports .eml (RFC 822), .msg (Outlook), .txt</span>
            <input
              type="file"
              multiple
              accept=".eml,.msg,.txt,.ics"
              class="dropzone-input"
              @change="handleFileSelect"
            />
          </div>

          <!-- Selected Files List -->
          <div v-if="selectedFiles.length > 0" class="files-preview">
            <div class="files-preview-title">Ready for upload ({{ selectedFiles.length }})</div>
            <div class="files-list">
              <div v-for="file in selectedFiles" :key="file.name" class="file-item">
                <FileText :size="14" />
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">({{ (file.size / 1024).toFixed(1) }} KB)</span>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="close" :disabled="isSubmitting">
              Cancel
            </button>
            <button
              class="btn btn-primary"
              @click="handleUploadSubmit"
              :disabled="isSubmitting || selectedFiles.length === 0"
            >
              <Loader2 v-if="isSubmitting" class="animate-spin" :size="16" />
              <span>{{ isSubmitting ? 'Ingesting Batch...' : `Upload & Process (${selectedFiles.length})` }}</span>
            </button>
          </div>
        </div>

        <!-- INGEST RESULT CARD -->
        <div v-if="ingestResult" class="result-box animate-fade-in">
          <div v-if="!ingestResult.isBatch">
            <div class="result-header">
              <CheckCircle v-if="ingestResult.status === 'success'" :size="18" class="text-success" />
              <Inbox v-else-if="ingestResult.status === 'staged'" :size="18" class="text-warning" />
              <AlertTriangle v-else :size="18" class="text-danger" />
              <span class="result-title">{{ ingestResult.message }}</span>
            </div>

            <div v-if="ingestResult.company" class="result-meta">
              <div class="meta-row">
                <span class="meta-key">Company:</span>
                <span class="meta-val font-semibold">{{ ingestResult.company }}</span>
              </div>
              <div v-if="ingestResult.position" class="meta-row">
                <span class="meta-key">Position:</span>
                <span class="meta-val">{{ ingestResult.position }}</span>
              </div>
              <div v-if="ingestResult.route" class="meta-row">
                <span class="meta-key">Route:</span>
                <span class="meta-val font-mono text-xs">{{ ingestResult.route }}</span>
              </div>
            </div>
          </div>

          <!-- Batch Results Summary -->
          <div v-else>
            <div class="result-header">
              <CheckCircle :size="18" class="text-success" />
              <span class="result-title">Batch Ingestion Completed ({{ ingestResult.items.length }} files)</span>
            </div>
            <div class="batch-list">
              <div v-for="(item, idx) in ingestResult.items" :key="idx" class="batch-row">
                <span class="badge" :class="`badge-${item.status}`">{{ item.status }}</span>
                <span class="batch-msg">{{ item.company || 'Unknown' }} - {{ item.position || item.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 500;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 580px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  color: var(--primary);
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-close {
  color: var(--text-muted);
  padding: 4px;
  border-radius: var(--radius-sm);
}

.btn-close:hover {
  background: var(--bg-surface-hover);
  color: var(--text-main);
}

.tab-bar {
  display: flex;
  padding: 8px 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  gap: 8px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--text-main);
}

.tab-btn.active {
  color: var(--text-main);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.input-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-input, .form-textarea {
  width: 100%;
}

.form-textarea {
  resize: vertical;
  min-height: 120px;
}

.dropzone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 16px;
  border: 2px dashed var(--border-subtle);
  border-radius: var(--radius-md);
  background-color: var(--bg-input);
  text-align: center;
  transition: all var(--transition-fast);
  cursor: pointer;
}

.dropzone.active {
  border-color: var(--primary);
  background-color: var(--bg-elevated);
}

.dropzone-icon {
  color: var(--primary);
  margin-bottom: 8px;
}

.dropzone-text {
  font-size: 13px;
  color: var(--text-main);
  margin-bottom: 4px;
}

.dropzone-highlight {
  color: var(--primary);
  font-weight: 600;
}

.dropzone-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.dropzone-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.files-preview {
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}

.files-preview-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-main);
  padding: 3px 0;
}

.file-name {
  font-family: var(--font-mono);
}

.file-size {
  color: var(--text-muted);
}

.modal-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.result-box {
  padding: 14px 18px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.result-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.result-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.meta-row {
  display: flex;
  gap: 8px;
}

.meta-key {
  color: var(--text-muted);
  width: 70px;
}

.meta-val {
  color: var(--text-main);
}

.text-success { color: var(--status-offer-text); }
.text-warning { color: var(--status-interview-text); }
.text-danger { color: var(--status-rejected-text); }

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
