<script setup>
import { ref, onMounted } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { IntakeAPI, EmailAccountsAPI } from '../../api/endpoints'
import {
  X,
  FileText,
  UploadCloud,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Inbox,
  Sparkles,
  Mail,
  Calendar,
  Filter,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

// ── tab state ────────────────────────────────────────────────
const activeTab = ref('sync') // 'sync' | 'paste' | 'upload'

// ── paste tab ────────────────────────────────────────────────
const pasteText = ref('')
const pasteSubject = ref('')

// ── upload tab ───────────────────────────────
const selectedFiles = ref([])
const isDragging = ref(false)

// ── email sync tab ───────────────────────────────────────────
const emailAccounts = ref([])
const loadingAccounts = ref(false)
const syncAccountId = ref(null)
const syncWindow = ref(null)          // 'today' | '3d' | '7d' | '30d' | 'custom'
const syncCustomDate = ref('')
const syncKeywords = ref('')
const syncResult = ref(null)

// ── shared ───────────────────────────────────────────────────
const isSubmitting = ref(false)
const ingestResult = ref(null)

// ── time window presets ──────────────────────────────────────
const TIME_WINDOWS = [
  { key: 'today',  label: 'Today' },
  { key: '3d',     label: 'Last 3 days' },
  { key: '7d',     label: 'Last 7 days' },
  { key: '30d',    label: 'Last 30 days' },
  { key: 'custom', label: 'Custom date…' },
]

function resolveSinceDate(window, customDate) {
  const now = new Date()
  if (window === 'today') {
    const d = new Date(now)
    d.setHours(0, 0, 0, 0)
    return d.toISOString()
  }
  if (window === '3d')  { const d = new Date(now); d.setDate(d.getDate() - 3);  return d.toISOString() }
  if (window === '7d')  { const d = new Date(now); d.setDate(d.getDate() - 7);  return d.toISOString() }
  if (window === '30d') { const d = new Date(now); d.setDate(d.getDate() - 30); return d.toISOString() }
  if (window === 'custom' && customDate) return new Date(customDate).toISOString()
  return null
}

async function loadEmailAccounts() {
  if (emailAccounts.value.length > 0) return
  loadingAccounts.value = true
  try {
    const res = await EmailAccountsAPI.list()
    emailAccounts.value = res.data || []
    if (emailAccounts.value.length === 1) {
      syncAccountId.value = emailAccounts.value[0].id
    }
  } catch {
    emailAccounts.value = []
  } finally {
    loadingAccounts.value = false
  }
}

onMounted(() => {
  loadEmailAccounts()
})

function onTabChange(tab) {
  activeTab.value = tab
  if (tab === 'sync') loadEmailAccounts()
}

// ── actions ───────────────────────────────────────────────────
function close() {
  uiStore.closeIngestModal()
  setTimeout(() => {
    pasteText.value = ''
    pasteSubject.value = ''
    selectedFiles.value = []
    ingestResult.value = null
    syncResult.value = null
    syncWindow.value = null
    syncCustomDate.value = ''
    syncKeywords.value = ''
  }, 200)
}

async function handlePasteSubmit() {
  if (!pasteText.value.trim()) return
  isSubmitting.value = true
  ingestResult.value = null

  const textToSubmit = pasteText.value
  const subjectToSubmit = pasteSubject.value

  try {
    const res = await IntakeAPI.paste({
      text: textToSubmit,
      subject: subjectToSubmit || null,
    })
    ingestResult.value = res.data
    pasteText.value = ''
    pasteSubject.value = ''
    uiStore.showToast('Pasted email queued for AI extraction', 'success')
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

function handleFileSelect(e) {
  selectedFiles.value = Array.from(e.target.files || [])
}

function handleFileDrop(e) {
  isDragging.value = false
  selectedFiles.value = Array.from(e.dataTransfer.files || [])
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
    ingestResult.value = res.data
    const count = selectedFiles.value.length
    selectedFiles.value = []
    uiStore.showToast(`Queued ${count} email file(s) for AI processing`, 'success')
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

async function handleEmailSync() {
  if (!syncAccountId.value || !syncWindow.value) return
  if (syncWindow.value === 'custom' && !syncCustomDate.value) return

  isSubmitting.value = true
  syncResult.value = null

  const sinceDate = resolveSinceDate(syncWindow.value, syncCustomDate.value)
  const keywords = syncKeywords.value
    .split(',')
    .map(k => k.trim())
    .filter(Boolean)

  try {
    const res = await IntakeAPI.syncAccount({
      account_id: syncAccountId.value,
      since_date: sinceDate,
      keyword_filter: keywords,
    })
    syncResult.value = res.data
    uiStore.showToast(res.data.message || 'Email sync queued for AI extraction', 'success')
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.detail || err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

const syncButtonLabel = computed => {
  if (!syncWindow.value || syncWindow.value === 'custom') return 'Sync Emails'
  const map = { today: 'Sync Today\'s Emails', '3d': 'Sync Last 3 Days', '7d': 'Sync Last 7 Days', '30d': 'Sync Last 30 Days' }
  return map[syncWindow.value] || 'Sync Emails'
}
</script>

<template>
  <div v-if="uiStore.isIngestModalOpen" class="modal-backdrop" @click.self="close">
    <div class="modal-card animate-fade-in">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="modal-title-group">
          <div class="title-icon">
            <Mail :size="18" />
          </div>
          <div>
            <h2 class="modal-title">Email Intake</h2>
            <p class="modal-subtitle">Sync connected mailboxes, paste recruiter threads, or upload message files</p>
          </div>
        </div>
        <button class="btn-close" @click="close">
          <X :size="18" />
        </button>
      </div>

      <!-- Tab Switcher -->
      <div class="tab-bar">
        <button class="tab-btn" :class="{ active: activeTab === 'sync' }" @click="onTabChange('sync')">
          <Mail :size="15" />
          <span>Email Sync</span>
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'paste' }" @click="onTabChange('paste')">
          <FileText :size="15" />
          <span>Paste Text</span>
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'upload' }" @click="onTabChange('upload')">
          <UploadCloud :size="15" />
          <span>Upload Files</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">

        <!-- ── TAB 1: PASTE ─────────────────────────────── -->
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
            <button class="btn btn-secondary" @click="close" :disabled="isSubmitting">Cancel</button>
            <button
              class="btn btn-primary"
              @click="handlePasteSubmit"
              :disabled="isSubmitting || !pasteText.trim()"
            >
              <Loader2 v-if="isSubmitting" class="animate-spin" :size="16" />
              <span>{{ isSubmitting ? 'Analyzing with LangGraph…' : 'Parse & Ingest' }}</span>
            </button>
          </div>
        </div>

        <!-- ── TAB 2: UPLOAD ────────────────────────────── -->
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
            <button class="btn btn-secondary" @click="close" :disabled="isSubmitting">Cancel</button>
            <button
              class="btn btn-primary"
              @click="handleUploadSubmit"
              :disabled="isSubmitting || selectedFiles.length === 0"
            >
              <Loader2 v-if="isSubmitting" class="animate-spin" :size="16" />
              <span>{{ isSubmitting ? 'Ingesting Batch…' : `Upload & Process (${selectedFiles.length})` }}</span>
            </button>
          </div>
        </div>

        <!-- ── TAB 3: EMAIL SYNC ────────────────────────── -->
        <div v-else-if="activeTab === 'sync'" class="tab-content">

          <!-- Account selector -->
          <div class="input-group">
            <label class="input-label">Email Account</label>
            <div v-if="loadingAccounts" class="sync-loading">
              <Loader2 class="animate-spin" :size="14" />
              <span>Loading accounts…</span>
            </div>
            <div v-else-if="emailAccounts.length === 0" class="sync-empty">
              No email accounts configured. Add one in <strong>Settings → Email Accounts</strong>.
            </div>
            <select
              v-else
              v-model="syncAccountId"
              class="form-select"
            >
              <option :value="null" disabled>Select account…</option>
              <option v-for="acct in emailAccounts" :key="acct.id" :value="acct.id">
                {{ acct.name }} ({{ acct.auth_type }})
              </option>
            </select>
          </div>

          <!-- Time window chips -->
          <div class="input-group">
            <label class="input-label">
              <Calendar :size="12" class="inline-icon" />
              Time Window
            </label>
            <div class="time-chips">
              <button
                v-for="w in TIME_WINDOWS"
                :key="w.key"
                type="button"
                class="time-chip"
                :class="{ active: syncWindow === w.key }"
                @click="syncWindow = w.key"
              >
                {{ w.label }}
              </button>
            </div>
            <!-- Custom date picker -->
            <input
              v-if="syncWindow === 'custom'"
              v-model="syncCustomDate"
              type="date"
              class="form-input mt-2"
              :max="new Date().toISOString().split('T')[0]"
            />
          </div>

          <!-- Keyword filter -->
          <div class="input-group">
            <label class="input-label">
              <Filter :size="12" class="inline-icon" />
              Extra Keywords <span class="label-optional">(optional)</span>
            </label>
            <input
              v-model="syncKeywords"
              type="text"
              placeholder="e.g. assessment, onsite, take-home"
              class="form-input"
            />
            <p class="field-hint">Smart defaults always active: <em>application, interview, offer, hiring…</em> Add comma-separated extras above.</p>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="close" :disabled="isSubmitting">Cancel</button>
            <button
              class="btn btn-primary"
              @click="handleEmailSync"
              :disabled="isSubmitting || !syncAccountId || !syncWindow || (syncWindow === 'custom' && !syncCustomDate) || emailAccounts.length === 0"
            >
              <Loader2 v-if="isSubmitting" class="animate-spin" :size="16" />
              <span>{{ isSubmitting ? 'Syncing…' : 'Sync Emails' }}</span>
            </button>
          </div>

          <!-- Sync result card -->
          <div v-if="syncResult" class="result-box animate-fade-in">
            <div class="result-header">
              <CheckCircle :size="18" class="text-success" />
              <span class="result-title">Sync queued — processing in background</span>
            </div>
            <div class="sync-stats">
              <div class="stat-item">
                <span class="stat-val">{{ syncResult.scanned_count }}</span>
                <span class="stat-key">scanned</span>
              </div>
              <div class="stat-divider">·</div>
              <div class="stat-item">
                <span class="stat-val text-primary">{{ syncResult.matched_count }}</span>
                <span class="stat-key">queued for AI</span>
              </div>
              <div class="stat-divider">·</div>
              <div class="stat-item">
                <span class="stat-val">{{ syncResult.filtered_out_count }}</span>
                <span class="stat-key">filtered out</span>
              </div>
              <div class="stat-divider">·</div>
              <div class="stat-item">
                <span class="stat-val">{{ syncResult.skipped_duplicates }}</span>
                <span class="stat-key">already seen</span>
              </div>
            </div>
            <p v-if="syncResult.task_id" class="task-id-hint">Task: {{ syncResult.task_id }}</p>
          </div>
        </div>

        <!-- ── PASTE/UPLOAD INGEST RESULT ──────────────── -->
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
  max-height: 92vh;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
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
  flex-shrink: 0;
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

.tab-btn:hover { color: var(--text-main); }

.tab-btn.active {
  color: var(--primary);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 4px;
}

.input-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.label-optional {
  font-weight: 400;
  color: var(--text-muted);
}

.form-input, .form-textarea, .form-select {
  width: 100%;
}

.inline-icon {
  display: inline;
  vertical-align: middle;
  margin-right: 4px;
}

.form-textarea {
  resize: vertical;
  min-height: 120px;
}

.mt-2 { margin-top: 8px; }

/* ── Time window chips ─────────────────────────── */
.time-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.time-chip {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-input);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.time-chip:hover {
  border-color: var(--border-subtle);
  color: var(--text-main);
}

.time-chip.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
  color: var(--primary);
  font-weight: 600;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-top: 2px;
}

/* ── Sync result stats ─────────────────────────── */
.sync-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-val {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.stat-key {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-divider {
  font-size: 18px;
  color: var(--border-subtle);
  line-height: 1;
}

.text-primary { color: var(--primary); }

.task-id-hint {
  margin-top: 8px;
  font-size: 10px;
  color: var(--text-muted);
  font-family: monospace;
}

/* ── Sync empty/loading states ─────────────────── */
.sync-loading,
.sync-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 8px 0;
}

/* ── Dropzone ──────────────────────────────────── */
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
  background-color: var(--primary-subtle);
}

.dropzone-icon { color: var(--primary); margin-bottom: 8px; }
.dropzone-text { font-size: 13px; color: var(--text-main); margin-bottom: 4px; }
.dropzone-highlight { color: var(--primary); font-weight: 600; }
.dropzone-hint { font-size: 11px; color: var(--text-muted); }
.dropzone-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }

.files-preview {
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}

.files-preview-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.file-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-main); padding: 3px 0; }
.file-name { font-family: var(--font-mono); }
.file-size { color: var(--text-muted); }

/* ── Modal actions ─────────────────────────────── */
.modal-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

/* ── Result box ────────────────────────────────── */
.result-box {
  padding: 14px 18px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.result-title { font-size: 13px; font-weight: 600; color: var(--text-main); }
.result-meta { display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.meta-row { display: flex; gap: 8px; }
.meta-key { color: var(--text-muted); width: 70px; }
.meta-val { color: var(--text-main); }

.text-success { color: var(--status-offer-text); }
.text-warning { color: var(--status-interview-text); }
.text-danger  { color: var(--status-rejected-text); }

.batch-list { display: flex; flex-direction: column; gap: 4px; }
.batch-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.batch-msg { color: var(--text-secondary); }

.animate-spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.animate-fade-in { animation: fadeIn 0.15s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
</style>
