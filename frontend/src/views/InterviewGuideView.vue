<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApplicationsAPI } from '../api/endpoints'
import {
  Globe,
  Printer,
  Copy,
  Check,
  Building2,
  Briefcase,
  Loader2,
  AlertCircle,
  Sparkles
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const applicationId = route.params.id

const isLoading = ref(true)
const application = ref(null)
const error = ref(null)
const hasCopied = ref(false)

onMounted(async () => {
  if (!applicationId) {
    error.value = 'No application ID provided.'
    isLoading.value = false
    return
  }

  try {
    const res = await ApplicationsAPI.get(applicationId)
    application.value = res.data
    if (!application.value.interview_guide_html) {
      error.value = 'No interview guide generated for this application.'
    }
  } catch (err) {
    error.value = 'Failed to load application details.'
  } finally {
    isLoading.value = false
  }
})



function handleCopy() {
  if (!application.value?.interview_guide_html) return
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = application.value.interview_guide_html
  const plainText = tempDiv.innerText || tempDiv.textContent

  navigator.clipboard.writeText(plainText).then(() => {
    hasCopied.value = true
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
    en: 'English',
    pt: 'Português',
    es: 'Español',
    de: 'Deutsch',
    fr: 'Français',
    it: 'Italiano',
    nl: 'Nederlands',
  }
  return LANGUAGES[code] || code?.toUpperCase() || 'EN'
}

</script>

<template>
  <div class="interview-guide-page">
    <div v-if="isLoading" class="loading-state">
      <Loader2 class="animate-spin text-primary" :size="32" />
      <span>Loading Interview Guide...</span>
    </div>

    <div v-else-if="error" class="error-state">
      <AlertCircle :size="48" class="text-danger" />
      <h2>{{ error }}</h2>
      <p>Please generate the interview guide from the application details drawer first.</p>
    </div>

    <div v-else-if="application && application.interview_guide_html" class="guide-container">
      <div class="guide-header print-hide">
        <div class="header-main-info">
          <div class="header-title-row">
            <h1 class="page-title">Interview Prep Guide</h1>
            <span v-if="application.company?.name" class="company-tag">
              <Building2 :size="14" />
              <span>{{ application.company.name }}</span>
            </span>
            <span v-if="application.position" class="position-tag">
              <Briefcase :size="14" />
              <span>{{ application.position }}</span>
            </span>
          </div>
        </div>

        <div class="header-actions">
          <button class="btn btn-primary" @click="router.push(`/chat?appId=${applicationId}&mock=true`)">
            <Sparkles :size="16" />
            <span>Practice Interview</span>
          </button>
          <button class="btn btn-secondary" @click="handleCopy">
            <component :is="hasCopied ? Check : Copy" :size="16" :class="{ 'text-success': hasCopied }" />
            <span>{{ hasCopied ? 'Copied' : 'Copy' }}</span>
          </button>
        </div>
      </div>

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
        <div
          class="guide-article"
          v-html="application.interview_guide_html"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.interview-guide-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
}

.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
  text-align: center;
  color: var(--text-secondary);
}

.error-state h2 {
  font-family: var(--font-heading);
  color: var(--text-main);
  margin: 0;
}

.guide-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 28px;
  color: var(--text-main);
  margin: 0;
}

.company-tag, .position-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  font-size: 14px;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
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
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
  font-size: 13px;
  font-weight: 600;
}

.timestamp-label {
  font-size: 13px;
  color: var(--text-muted);
}

.guide-paper {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 48px 56px;
  box-shadow: var(--shadow-sm);
}

/* Clean Formatted Article Styling */
.guide-article :deep(h1) {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 24px;
  color: var(--text-main);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  margin-top: 32px;
  margin-bottom: 16px;
}

.guide-article :deep(h1:first-child) {
  margin-top: 0;
}

.guide-article :deep(h2) {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 20px;
  color: var(--text-main);
  margin-top: 32px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-article :deep(h3) {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin-top: 20px;
  margin-bottom: 10px;
}

.guide-article :deep(p) {
  font-size: 15px;
  line-height: 1.65;
  color: var(--text-main);
  margin-bottom: 14px;
}

.guide-article :deep(strong) {
  color: var(--text-main);
  font-weight: 600;
}

.guide-article :deep(ul) {
  margin-bottom: 18px;
  padding-left: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guide-article :deep(li) {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.guide-article :deep(li strong) {
  color: var(--text-main);
}

.guide-article :deep(blockquote) {
  margin: 20px 0;
  padding: 16px 20px;
  border-left: 4px solid var(--primary);
  background-color: var(--bg-surface);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.55;
}

/* Print Overrides */

</style>
