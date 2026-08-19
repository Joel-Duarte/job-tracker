<script setup>
import { ref, watch, computed } from 'vue'
import DOMPurify from 'dompurify'
import { ApplicationsAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'
import {
  X,
  Printer,
  Copy,
  Check,
  Globe,
  Building2,
  Briefcase,
  Loader2,
  AlertCircle,
  Maximize2,
  Minimize2,
  ExternalLink
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const props = defineProps({
  isOpen: Boolean,
  applicationId: Number
})

const emit = defineEmits(['close'])
const uiStore = useUIStore()
const router = useRouter()

const isLoading = ref(true)
const application = ref(null)
const error = ref(null)
const hasCopied = ref(false)
const isFullScreen = ref(false)

const sanitizedGuideHtml = computed(() => {
  return application.value?.interview_guide_html
    ? DOMPurify.sanitize(application.value.interview_guide_html)
    : ''
})

watch(() => props.isOpen, async (newVal) => {
  if (newVal && props.applicationId) {
    await loadApplication()
  } else {
    application.value = null
    error.value = null
    isFullScreen.value = false
  }
})

async function loadApplication() {
  isLoading.value = true
  error.value = null
  try {
    const res = await ApplicationsAPI.get(props.applicationId)
    application.value = res.data
    if (!application.value.interview_guide_html) {
      error.value = 'No interview guide generated for this application.'
    }
  } catch (err) {
    error.value = 'Failed to load application details.'
    uiStore.showToast(error.value, 'error')
  } finally {
    isLoading.value = false
  }
}

function openInDedicatedTab() {
  if (!application.value?.id) return
  const routeData = router.resolve({ name: 'InterviewGuide', params: { id: application.value.id } })
  window.open(routeData.href, '_blank')
}

function handleCopy() {
  if (!application.value?.interview_guide_html) return
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

function formatLanguageName(code) {
  const LANGUAGES = {
    en: 'English', pt: 'Português', es: 'Español', de: 'Deutsch',
    fr: 'Français', it: 'Italiano', nl: 'Nederlands',
  }
  return LANGUAGES[code] || code?.toUpperCase() || 'EN'
}
</script>

<template>
  <div v-if="isOpen" class="modal-backdrop print-hide" :class="{ 'full-screen-backdrop': isFullScreen }" @click.self="emit('close')">
    <div class="modal-card animate-fade-in interview-reader-container" :class="{ 'full-screen-mode': isFullScreen }">
      <!-- Header -->
      <div class="modal-header">
        <div class="header-main-info">
          <div class="header-title-row">
            <h2 class="modal-title">Interview Prep Guide</h2>
            <span v-if="application?.company?.name" class="company-tag">
              <Building2 :size="12" />
              <span>{{ application.company.name }}</span>
            </span>
            <span v-if="application?.position" class="position-tag">
              <Briefcase :size="12" />
              <span>{{ application.position }}</span>
            </span>
          </div>
        </div>

        <div class="header-actions">
          <button
            class="btn btn-secondary btn-sm"
            @click="isFullScreen = !isFullScreen"
            :title="isFullScreen ? 'Exit Full Reader' : 'Full Reader Mode'"
          >
            <component :is="isFullScreen ? Minimize2 : Maximize2" :size="14" />
            <span>{{ isFullScreen ? 'Compact' : 'Full Reader' }}</span>
          </button>

          <button
            v-if="application?.id"
            class="btn btn-secondary btn-sm"
            @click="openInDedicatedTab"
            title="Open in New Tab"
          >
            <ExternalLink :size="14" />
          </button>

          <button class="btn btn-secondary btn-sm" @click="handleCopy" :disabled="!application?.interview_guide_html">
            <component :is="hasCopied ? Check : Copy" :size="14" :class="{ 'text-success': hasCopied }" />
            <span>{{ hasCopied ? 'Copied' : 'Copy' }}</span>
          </button>
          <button class="btn-close" @click="emit('close')">
            <X :size="18" />
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="modal-body-scroll">
        <div v-if="isLoading" class="state-container">
          <Loader2 class="animate-spin text-primary" :size="32" />
          <span class="loading-label">Loading preparation dossier...</span>
        </div>

        <div v-else-if="error" class="state-container">
          <AlertCircle :size="32" class="text-danger" />
          <span class="loading-label">{{ error }}</span>
        </div>

        <div v-else-if="application?.interview_guide_html" class="guide-reader-layout">
          <div class="guide-meta print-hide">
            <span class="badge-lang">
              <Globe :size="12" />
              <span>{{ formatLanguageName(application.interview_guide_language) }}</span>
            </span>
            <span v-if="application.interview_guide_generated_at" class="timestamp-label">
              Generated {{ formatDate(application.interview_guide_generated_at) }}
            </span>
          </div>

          <div class="guide-paper">
            <div class="guide-article" v-html="sanitizedGuideHtml"></div>
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
  background-color: var(--bg-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-backdrop.full-screen-backdrop {
  padding: 0;
}

.interview-reader-container {
  width: 100%;
  max-width: 960px;
  height: 90vh;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.2s ease-in-out;
}

.interview-reader-container.full-screen-mode {
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
  padding: 16px 24px;
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
  font-size: 18px;
  color: var(--text-main);
  margin: 0;
  font-weight: 700;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-body-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background-color: var(--bg-app);
}

.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 16px;
  text-align: center;
}

.loading-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.guide-reader-layout {
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-meta {
  display: flex;
  align-items: center;
  gap: 12px;
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
  font-size: 20px;
  color: var(--text-main);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
  margin-top: 24px;
  margin-bottom: 14px;
}
.guide-article :deep(h1:first-child) { margin-top: 0; }
.guide-article :deep(h2) {
  font-family: var(--font-heading);
  font-size: 18px;
  color: var(--text-main);
  margin-top: 28px;
  margin-bottom: 12px;
}
.guide-article :deep(h3) { font-size: 15px; font-weight: 700; color: var(--text-main); margin-top: 18px; margin-bottom: 8px; }
.guide-article :deep(p) { font-size: 14px; line-height: 1.65; color: var(--text-main); margin-bottom: 12px; }
.guide-article :deep(strong) { color: var(--text-main); font-weight: 600; }
.guide-article :deep(ul) { margin-bottom: 16px; padding-left: 22px; display: flex; flex-direction: column; gap: 6px; }
.guide-article :deep(li) { font-size: 14px; line-height: 1.6; color: var(--text-secondary); }
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


</style>
