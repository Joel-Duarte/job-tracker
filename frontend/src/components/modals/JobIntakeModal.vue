<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import { useQueueStore } from '../../stores/queueStore'
import { IntakeAPI } from '../../api/endpoints'
import {
  Sparkles,
  Link as LinkIcon,
  FileText,
  Puzzle,
  AlertTriangle,
  Check,
  Copy,
  X,
  Loader2,
  Globe,
  ArrowRight,
  ShieldCheck,
  Zap,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()
const queueStore = useQueueStore()

const activeTab = ref('url') // 'url' | 'jd' | 'extension'
const jobUrl = ref('')
const jobText = ref('')
const isEnqueuing = ref(false)
const jdTextareaRef = ref(null)

const showBulkLinkedInPrompt = ref(false)
const parsedBulkUrls = ref([])
const linkedInUrlsInBulk = ref([])

function extractUrls(text) {
  const urlRegex = /(https?:\/\/[^\s,]+)/g
  const matches = text.match(urlRegex) || []
  // Remove trailing quotes or common punctuation from urls
  return [...new Set(matches.map(u => u.replace(/[.,;'"]+$/, '')))]
}

function handleBulkPromptDecision(skipLinkedIn) {
  let urlsToProcess = [...parsedBulkUrls.value]

  if (skipLinkedIn) {
    urlsToProcess = urlsToProcess.filter(u => !u.toLowerCase().includes('linkedin.com'))
    const liText = linkedInUrlsInBulk.value.join('\n')
    navigator.clipboard.writeText(liText)
    uiStore.showToast(`${linkedInUrlsInBulk.value.length} LinkedIn URLs copied to clipboard!`, 'info')
  }

  showBulkLinkedInPrompt.value = false
  executeEnqueue(urlsToProcess, null)
}

async function executeEnqueue(urls, textVal) {
  if (!(await uiStore.ensureAIReady())) return

  isEnqueuing.value = true
  let successCount = 0
  let failCount = 0

  try {
    if (urls && urls.length > 0) {
      for (const u of urls) {
        try {
          await queueStore.enqueueAssessment({ url: u, text: null })
          successCount++
        } catch(e) {
          failCount++
        }
      }
    } else if (textVal) {
      await queueStore.enqueueAssessment({ url: null, text: textVal })
    }

    jobUrl.value = ''
    jobText.value = ''
    uiStore.closeJobIntakeModal()
  } catch (err) {
    // Handled in store with toast & rollback
  } finally {
    isEnqueuing.value = false
  }
}

// Extension tokens
const copiedUrl = ref(false)
const copiedJd = ref(false)
const urlEndpoint = ref('Loading...')
const jdEndpoint = ref('Loading...')

// LinkedIn Warning Detection
const dismissedLinkedInUrl = ref('')
const isLinkedInUrl = computed(() => {
  if (!jobUrl.value) return false
  const trimmed = jobUrl.value.trim().toLowerCase()
  return trimmed.includes('linkedin.com') && dismissedLinkedInUrl.value !== trimmed
})

function dismissLinkedInWarning() {
  dismissedLinkedInUrl.value = jobUrl.value.trim().toLowerCase()
}

function handlePasteTextInstead() {
  dismissLinkedInWarning()
  activeTab.value = 'jd'
  nextTick(() => {
    if (jdTextareaRef.value) {
      jdTextareaRef.value.focus()
    }
  })
}

async function fetchExtensionConfig() {
  try {
    const res = await IntakeAPI.getExtensionConfig()
    if (res.data?.url_endpoint) {
      urlEndpoint.value = res.data.url_endpoint
      jdEndpoint.value = res.data.jd_endpoint
    }
  } catch (err) {
    const host = window.location.hostname || 'localhost'
    const port = window.location.port === '5173' ? '8000' : window.location.port || '8000'
    const proto = window.location.protocol || 'http:'
    urlEndpoint.value = `${proto}//${host}:${port}/api/v1/intake/url`
    jdEndpoint.value = `${proto}//${host}:${port}/api/v1/intake/jd`
  }
}

function copyToClipboard(val, type) {
  navigator.clipboard.writeText(val)
  if (type === 'url') {
    copiedUrl.value = true
    setTimeout(() => { copiedUrl.value = false }, 2000)
  } else {
    copiedJd.value = true
    setTimeout(() => { copiedJd.value = false }, 2000)
  }
  uiStore.showToast('Endpoint URL copied to clipboard!', 'info')
}

async function submitJobIntake() {
  const urlVal = jobUrl.value.trim()
  const textVal = jobText.value.trim()

  if (activeTab.value === 'url') {
    if (!urlVal) {
      uiStore.showToast('Please enter valid Job Posting URL(s)', 'warning')
      return
    }

    const urls = extractUrls(urlVal)
    if (urls.length === 0) {
      uiStore.showToast('No valid URLs found in the input.', 'warning')
      return
    }

    if (urls.length > 1) {
      // Bulk submission logic
      const liUrls = urls.filter(u => u.toLowerCase().includes('linkedin.com'))
      if (liUrls.length > 0) {
        parsedBulkUrls.value = urls
        linkedInUrlsInBulk.value = liUrls
        showBulkLinkedInPrompt.value = true
        return // Wait for user decision
      }

      // No LinkedIn urls, proceed bulk
      executeEnqueue(urls, null)
      return
    }

    // Single URL submission
    executeEnqueue([urls[0]], null)

  } else if (activeTab.value === 'jd') {
    if (!textVal) {
      uiStore.showToast('Please paste the job description text', 'warning')
      return
    }
    executeEnqueue(null, textVal)
  }
}

onMounted(() => {
  fetchExtensionConfig()
})
</script>

<template>
  <Transition name="fade">
    <div
      v-if="uiStore.isJobIntakeModalOpen"
      class="modal-backdrop"
      @click.self="uiStore.closeJobIntakeModal"
    >
      <div class="modal-card animate-slide-up">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-title-group">
            <div class="modal-icon">
              <Sparkles :size="18" class="text-primary" />
            </div>
            <div>
              <h2 class="modal-title">Job Lead Intake</h2>
              <p class="modal-subtitle">
                Pre-screen opportunities with AI qualification before adding them to your pipeline.
              </p>
            </div>
          </div>
          <button class="btn-close" @click="uiStore.closeJobIntakeModal">
            <X :size="16" />
          </button>
        </div>

        <!-- 3 Intake Tabs -->
        <div class="modal-tabs">
          <button
            class="modal-tab"
            :class="{ active: activeTab === 'url' }"
            @click="activeTab = 'url'"
          >
            <LinkIcon :size="14" />
            <span>Job URL (Default)</span>
          </button>

          <button
            class="modal-tab"
            :class="{ active: activeTab === 'jd' }"
            @click="activeTab = 'jd'"
          >
            <FileText :size="14" />
            <span>Job Description (JD)</span>
          </button>

          <button
            class="modal-tab"
            :class="{ active: activeTab === 'extension' }"
            @click="activeTab = 'extension'"
          >
            <Puzzle :size="14" />
            <span>Browser Extension Guide</span>
          </button>
        </div>

        <!-- Tab 1: Job URL -->
        <div v-if="activeTab === 'url'" class="tab-content animate-fade-in">
          <div class="input-group">
            <label class="input-label">Job Posting URL(s)</label>
            <div class="input-with-icon-top">
              <LinkIcon :size="16" class="field-icon-top" />
              <textarea
                v-model="jobUrl"
                rows="4"
                placeholder="https://jobs.lever.co/...
Or paste multiple URLs separated by newlines to bulk add!"
                class="form-input form-textarea-top"
                autofocus
                @keydown.enter.ctrl="submitJobIntake"
                @keydown.enter.meta="submitJobIntake"
              ></textarea>
            </div>
            <span class="field-hint">Supports single URLs or bulk lists. Press Ctrl+Enter to submit.</span>
          </div>

          <!-- Bulk LinkedIn Prompt Modal inside Modal -->
          <div v-if="showBulkLinkedInPrompt" class="advisory-box animate-fade-in mt-3" style="background-color: var(--status-rejected-bg); border-color: var(--status-rejected-border); flex-direction: column; gap: 8px;">
            <div style="display: flex; gap: 12px;">
                <div class="advisory-icon text-warning">
                  <AlertTriangle :size="16" />
                </div>
                <div class="advisory-content" style="flex: 1;">
                  <span class="advisory-title" style="color: var(--status-rejected-text);">Bulk Add: LinkedIn Links Detected</span>
                  <p class="advisory-desc" style="color: var(--status-rejected-text);">
                    You are trying to bulk add {{ parsedBulkUrls.length }} URLs, which includes {{ linkedInUrlsInBulk.length }} LinkedIn link(s).
                    LinkedIn aggressively blocks automated scrapers.
                  </p>
                </div>
            </div>
            <div class="advisory-actions" style="justify-content: flex-end; width: 100%;">
              <button type="button" class="btn btn-secondary btn-sm" @click="handleBulkPromptDecision(true)">
                <Copy :size="14" />
                <span>Copy LinkedIn links & Skip them</span>
              </button>
              <button type="button" class="btn btn-danger-subtle btn-sm" style="border-color: var(--status-rejected-border); background-color: var(--bg-surface);" @click="handleBulkPromptDecision(false)">
                <span>Process all anyway</span>
              </button>
            </div>
          </div>

          <!-- LinkedIn Anti-Scrape Warning Alert -->
          <div v-if="isLinkedInUrl" class="advisory-box animate-fade-in mt-3">
            <div class="advisory-icon text-warning">
              <AlertTriangle :size="16" />
            </div>
            <div class="advisory-content">
              <span class="advisory-title">LinkedIn Anti-Bot Protection</span>
              <p class="advisory-desc">
                LinkedIn blocks automated URL scrapers. For accurate extraction, copy the job description text directly from LinkedIn and switch to the JD tab.
              </p>
              <div class="advisory-actions">
                <button type="button" class="btn btn-secondary btn-xs" @click="handlePasteTextInstead">
                  Switch to JD Tab
                </button>
                <button type="button" class="btn btn-ghost btn-xs text-muted" @click="dismissLinkedInWarning">
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 2: Job Description Text -->
        <div v-else-if="activeTab === 'jd'" class="tab-content animate-fade-in">
          <div class="input-group">
            <label class="input-label">Paste Full Job Specification / Requirements</label>
            <textarea
              ref="jdTextareaRef"
              v-model="jobText"
              rows="8"
              placeholder="Paste the full job posting, requirements, qualifications, and role description here..."
              class="form-textarea font-mono"
            ></textarea>
            <span class="field-hint">AI strips privacy details, extracts skills and responsibilities, and compares against your CV profile.</span>
          </div>
        </div>

        <!-- Tab 3: Browser Extension Guide -->
        <div v-else-if="activeTab === 'extension'" class="tab-content animate-fade-in">
          <div class="extension-guide-box">
            <div class="guide-step">
              <div class="step-num">1</div>
              <div class="step-body">
                <h4 class="step-title">Companion Browser Extension</h4>
                <p class="step-text">Install our extension to send any active job posting tab directly to your tracker in 1 click.</p>
              </div>
            </div>

            <div class="guide-step">
              <div class="step-num">2</div>
              <div class="step-body">
                <h4 class="step-title">Configure Endpoints in Extension Options</h4>
                <div class="endpoint-rows mt-2">
                  <div class="endpoint-row">
                    <span class="endpoint-lbl">URL Ingest Endpoint:</span>
                    <div class="endpoint-val">
                      <code>{{ urlEndpoint }}</code>
                      <button class="btn btn-secondary btn-xs" @click="copyToClipboard(urlEndpoint, 'url')">
                        <Check v-if="copiedUrl" :size="12" class="text-success" />
                        <Copy v-else :size="12" />
                        <span>{{ copiedUrl ? 'Copied' : 'Copy' }}</span>
                      </button>
                    </div>
                  </div>

                  <div class="endpoint-row">
                    <span class="endpoint-lbl">DOM / Card Endpoint:</span>
                    <div class="endpoint-val">
                      <code>{{ jdEndpoint }}</code>
                      <button class="btn btn-secondary btn-xs" @click="copyToClipboard(jdEndpoint, 'jd')">
                        <Check v-if="copiedJd" :size="12" class="text-success" />
                        <Copy v-else :size="12" />
                        <span>{{ copiedJd ? 'Copied' : 'Copy' }}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="uiStore.closeJobIntakeModal">
            Cancel
          </button>

          <button
            v-if="activeTab !== 'extension'"
            class="btn btn-primary"
            :disabled="isEnqueuing || (activeTab === 'url' && !jobUrl.trim()) || (activeTab === 'jd' && !jobText.trim())"
            @click="submitJobIntake"
          >
            <Loader2 v-if="isEnqueuing" class="animate-spin" :size="15" />
            <Sparkles v-else :size="15" />
            <span>{{ isEnqueuing ? 'Enqueuing Lead...' : 'Enqueue for AI Assessment' }}</span>
          </button>

          <button
            v-else
            class="btn btn-primary"
            @click="activeTab = 'url'"
          >
            <span>Proceed to Ingest URL &rarr;</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>
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
  padding: 20px;
}

.modal-card {
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
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
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.modal-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background-color: var(--primary-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--primary-glow);
}

.modal-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 17px;
  color: var(--text-main);
  margin-bottom: 2px;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-xs);
  transition: all var(--transition-fast);
}

.btn-close:hover {
  color: var(--text-main);
  background-color: var(--bg-hover);
}

.modal-tabs {
  display: flex;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  padding: 0 16px;
  gap: 6px;
}

.modal-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all var(--transition-fast);
}

.modal-tab:hover {
  color: var(--text-main);
}

.modal-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.tab-content {
  padding: 20px 24px;
  flex: 1;
  overflow-y: auto;
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.field-icon {
  position: absolute;
  left: 12px;
  color: var(--text-muted);
}

.input-with-icon .form-input {
  padding-left: 36px;
  width: 100%;
}

.form-textarea {
  width: 100%;
  padding: 10px 12px;
  font-size: 12px;
  background-color: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  outline: none;
  resize: vertical;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  display: block;
}

.advisory-box {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  background-color: var(--status-interview-bg);
  border: 1px solid var(--status-interview-border);
  border-radius: var(--radius-sm);
}

.advisory-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--status-interview-text);
  display: block;
  margin-bottom: 2px;
}

.advisory-desc {
  font-size: 11px;
  color: var(--status-interview-text);
  line-height: 1.4;
  margin-bottom: 6px;
}

.advisory-actions {
  display: flex;
  gap: 8px;
}

.extension-guide-box {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.guide-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: var(--primary);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 2px;
}

.step-text {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.endpoint-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.endpoint-row {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
}

.endpoint-lbl {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  display: block;
  margin-bottom: 2px;
}

.endpoint-val {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.endpoint-val code {
  font-size: 11px;
  color: var(--text-main);
  word-break: break-all;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  position: sticky;
  bottom: 0;
  z-index: 10;
}

@media (max-width: 767px) {
  .modal-backdrop {
    padding: 0;
    align-items: stretch;
    justify-content: stretch;
  }

  .modal-card {
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    max-height: 100dvh;
    max-width: 100vw;
    border-radius: 0;
    border: none;
  }

  .modal-header {
    padding: 14px 16px;
  }

  .btn-close {
    min-width: 48px;
    min-height: 48px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .modal-tabs {
    overflow-x: auto;
    white-space: nowrap;
    padding: 0 8px;
    -webkit-overflow-scrolling: touch;
  }

  .modal-tab {
    min-height: 48px;
    padding: 12px 14px;
    flex-shrink: 0;
  }

  .tab-content {
    padding: 16px;
  }

  .form-textarea,
  .form-textarea-top {
    font-size: 16px;
  }

  .modal-footer {
    padding: 12px 16px;
    padding-bottom: max(12px, env(safe-area-inset-bottom));
    flex-direction: column-reverse;
    gap: 8px;
  }

  .modal-footer .btn {
    width: 100%;
    min-height: 48px;
    justify-content: center;
  }

  .advisory-actions {
    flex-direction: column;
    width: 100%;
  }

  .advisory-actions .btn {
    min-height: 48px;
    width: 100%;
    justify-content: center;
  }

  .endpoint-val .btn {
    min-height: 44px;
    padding: 8px 12px;
  }
}

.input-with-icon-top {
  position: relative;
  display: flex;
}
.field-icon-top {
  position: absolute;
  left: 12px;
  top: 12px;
  color: var(--text-muted);
}
.form-textarea-top {
  padding-left: 36px;
  width: 100%;
  resize: vertical;
}
.btn-danger-subtle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  background-color: transparent;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}
.btn-danger-subtle:hover {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

</style>
