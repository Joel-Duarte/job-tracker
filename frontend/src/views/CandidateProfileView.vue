<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { CandidateProfileAPI, IntakeAPI } from '../api/endpoints'
import { scrubCVText } from '../utils/scrubber'
import {
  ShieldCheck,
  Sparkles,
  FileText,
  Clock,
  Briefcase,
  Layers,
  Plus,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  Eye,
  Edit3,
  Save,
  Copy,
  Lock,
  Shield,
  Info,
  Trash2,
  ChevronDown,
  ChevronUp,
  Sliders,
  Check,
  Power,
  RotateCcw,
  Upload,
  AlertTriangle,
} from 'lucide-vue-next'

const props = defineProps({
  isEmbedded: {
    type: Boolean,
    default: false,
  },
})

const uiStore = useUIStore()

const profile = ref(null)
const rawCVInput = ref('')
const activeInputTab = ref('raw') // 'raw' | 'preview'
const isEditingCV = ref(false)
const editedCVText = ref('')
const isEditingSummary = ref(false)
const editedSummaryText = ref('')
const showUpdateDrawer = ref(false)
const isDocExpanded = ref(true)

// File upload & parsing
const fileInput = ref(null)
const isParsingFile = ref(false)

function triggerFileInput() {
  fileInput.value?.click()
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  // 10 MB file size limit check
  const MAX_SIZE = 10 * 1024 * 1024
  if (file.size > MAX_SIZE) {
    uiStore.showToast('File size exceeds the 10 MB limit.', 'error')
    if (event.target) event.target.value = ''
    return
  }

  // File extension check
  const ext = file.name.split('.').pop()?.toLowerCase()
  const allowed = ['pdf', 'docx', 'doc', 'txt']
  if (!ext || !allowed.includes(ext)) {
    uiStore.showToast('Unsupported file format. Please select a .pdf, .docx, .doc, or .txt file.', 'error')
    if (event.target) event.target.value = ''
    return
  }

  isParsingFile.value = true

  try {
    if (ext === 'txt') {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target?.result
        if (typeof text === 'string' && text.trim()) {
          rawCVInput.value = text.trim()
          activeInputTab.value = 'raw'
          uiStore.showToast(`Loaded ${file.name}. Please review text before activating profile.`, 'success')
        } else {
          uiStore.showToast('Uploaded text file is empty.', 'error')
        }
        isParsingFile.value = false
        if (event.target) event.target.value = ''
      }
      reader.onerror = () => {
        uiStore.showToast('Failed to read text file.', 'error')
        isParsingFile.value = false
        if (event.target) event.target.value = ''
      }
      reader.readAsText(file)
    } else {
      const formData = new FormData()
      formData.append('file', file)
      const res = await CandidateProfileAPI.parseFile(formData)
      const text = res.data?.text
      if (text && text.trim()) {
        rawCVInput.value = text.trim()
        activeInputTab.value = 'raw'
        uiStore.showToast(`Extracted text from ${file.name}. Please review text before activating profile.`, 'success')
      } else {
        uiStore.showToast('Could not extract text from document file.', 'error')
      }
      isParsingFile.value = false
      if (event.target) event.target.value = ''
    }
  } catch (err) {
    const errMsg = err.response?.data?.detail || err.message || 'Failed to extract text from file'
    uiStore.showToast(errMsg, 'error')
    isParsingFile.value = false
    if (event.target) event.target.value = ''
  }
}

// Local scrubber preview
const localScrubResult = computed(() => {
  if (!rawCVInput.value) return { scrubbedText: '', stats: { total: 0 } }
  return scrubCVText(rawCVInput.value)
})

// Chips and inputs
const newSkillInput = ref('')
const newCompetencyInput = ref('')
const newDomainName = ref('')
const newDomainYears = ref(2.0)

const isProcessing = ref(false)
const currentTaskId = ref(null)
const currentTaskStage = ref('QUEUED')
const currentTaskStatus = ref('QUEUED')
const isSavingEdits = ref(false)
const isDeleting = ref(false)

async function loadProfile() {
  try {
    const res = await CandidateProfileAPI.get()
    if (res.data) {
      profile.value = res.data
      rawCVInput.value = res.data.raw_text || ''
      // Normalize domain_experience if missing
      if (!profile.value.domain_experience || !profile.value.domain_experience.length) {
        profile.value.domain_experience = (profile.value.domain_expertise || []).map((d) => ({
          domain: d,
          years: Math.max(1.0, Math.round(((profile.value.years_of_experience || 3.0) / Math.max(1, profile.value.domain_expertise.length)) * 10) / 10),
          is_active: true,
        }))
      }
    } else {
      profile.value = null
    }
  } catch (err) {
    uiStore.showToast('Could not load CV profile', 'error')
  }
}

async function pollTaskUntilComplete(taskId) {
  const maxAttempts = 300 // 5 minutes max
  let attempts = 0

  while (attempts < maxAttempts) {
    await new Promise((r) => setTimeout(r, 1000))
    attempts++

    try {
      const res = await CandidateProfileAPI.getTaskStatus(taskId)
      const task = res.data
      currentTaskStatus.value = task.status
      currentTaskStage.value = task.stage

      if (task.status === 'COMPLETED') {
        await loadProfile()
        uiStore.showToast('Resume de-identified and canonical profile activated!', 'success')
        isProcessing.value = false
        currentTaskId.value = null
        showUpdateDrawer.value = false
        return
      }

      if (task.status === 'FAILED') {
        uiStore.showToast(task.error_message || 'CV processing failed', 'error')
        isProcessing.value = false
        currentTaskId.value = null
        return
      }
    } catch (err) {
      console.warn('Polling check anomaly, retrying...', err)
    }
  }

  uiStore.showToast('Task is taking longer than expected. It will continue running in the background.', 'info')
  isProcessing.value = false
}

async function processCV() {
  if (!rawCVInput.value.trim() || rawCVInput.value.trim().length < 20) {
    uiStore.showToast('Please provide a complete resume or CV text.', 'error')
    return
  }

  isProcessing.value = true
  currentTaskStatus.value = 'QUEUED'
  currentTaskStage.value = 'QUEUED'

  try {
    const res = await CandidateProfileAPI.save(rawCVInput.value.trim())
    const taskId = res.data.task_id
    currentTaskId.value = taskId
    await pollTaskUntilComplete(taskId)
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to enqueue CV processing', 'error')
    isProcessing.value = false
  }
}

// --------------------------------------------------------------------------
// Profile Mutations & Inline Steppers
// --------------------------------------------------------------------------

async function adjustTotalYears(delta) {
  if (!profile.value) return
  const current = Number(profile.value.years_of_experience || 0)
  const nextVal = Math.max(0, Math.round((current + delta) * 10) / 10)
  profile.value.years_of_experience = nextVal
  await saveProfileField({ years_of_experience: nextVal })
}

// Domain experience management
async function adjustDomainYears(item, delta) {
  if (!profile.value) return
  const current = Number(item.years || 0)
  item.years = Math.max(0.5, Math.round((current + delta) * 10) / 10)
  await saveProfileField({ domain_experience: profile.value.domain_experience })
}

async function toggleDomainActive(item) {
  if (!profile.value) return
  item.is_active = !item.is_active
  await saveProfileField({ domain_experience: profile.value.domain_experience })
  uiStore.showToast(`Domain '${item.domain}' ${item.is_active ? 'enabled for matching' : 'muted from matching'}`, 'info')
}

async function addDomainArea() {
  const dName = newDomainName.value.trim()
  if (!dName || !profile.value) return

  if (!profile.value.domain_experience) profile.value.domain_experience = []
  const exists = profile.value.domain_experience.some((d) => d.domain.toLowerCase() === dName.toLowerCase())

  if (!exists) {
    profile.value.domain_experience.push({
      domain: dName,
      years: Number(newDomainYears.value) || 1.0,
      is_active: true,
    })
    newDomainName.value = ''
    newDomainYears.value = 2.0
    await saveProfileField({ domain_experience: profile.value.domain_experience })
    uiStore.showToast(`Added domain area '${dName}'`, 'success')
  }
}

async function removeDomainArea(item) {
  if (!profile.value?.domain_experience) return
  profile.value.domain_experience = profile.value.domain_experience.filter((d) => d.domain !== item.domain)
  await saveProfileField({ domain_experience: profile.value.domain_experience })
  uiStore.showToast(`Removed domain '${item.domain}'`, 'info')
}

// Technical skills management
function addSkill() {
  const skill = newSkillInput.value.trim()
  if (skill && profile.value) {
    if (!profile.value.extracted_skills.includes(skill)) {
      profile.value.extracted_skills.push(skill)
      newSkillInput.value = ''
      saveProfileField({ extracted_skills: profile.value.extracted_skills })
    }
  }
}

function removeSkill(skill) {
  if (profile.value) {
    profile.value.extracted_skills = profile.value.extracted_skills.filter((s) => s !== skill)
    saveProfileField({ extracted_skills: profile.value.extracted_skills })
  }
}

// Core competencies management
function addCompetency() {
  const comp = newCompetencyInput.value.trim()
  if (comp && profile.value) {
    if (!profile.value.core_competencies) profile.value.core_competencies = []
    if (!profile.value.core_competencies.includes(comp)) {
      profile.value.core_competencies.push(comp)
      newCompetencyInput.value = ''
      saveProfileField({ core_competencies: profile.value.core_competencies })
    }
  }
}

function removeCompetency(comp) {
  if (profile.value?.core_competencies) {
    profile.value.core_competencies = profile.value.core_competencies.filter((c) => c !== comp)
    saveProfileField({ core_competencies: profile.value.core_competencies })
  }
}

// In-place text editors
function startEditingSummary() {
  editedSummaryText.value = profile.value?.summary || ''
  isEditingSummary.value = true
}

async function saveEditedSummary() {
  if (!profile.value) return
  profile.value.summary = editedSummaryText.value.trim()
  await saveProfileField({ summary: profile.value.summary })
  isEditingSummary.value = false
  uiStore.showToast('Candidate summary updated', 'success')
}

function startEditingCV() {
  editedCVText.value = profile.value?.anonymized_text || ''
  isEditingCV.value = true
}

async function saveEditedCV() {
  if (!profile.value) return
  profile.value.anonymized_text = editedCVText.value
  await saveProfileField({ anonymized_text: editedCVText.value })
  isEditingCV.value = false
  uiStore.showToast('Sanitized resume updated successfully!', 'success')
}

async function copyAnonymizedCV() {
  if (profile.value?.anonymized_text) {
    await navigator.clipboard.writeText(profile.value.anonymized_text)
    uiStore.showToast('Sanitized resume copied to clipboard!', 'info')
  }
}

async function saveProfileField(patchData) {
  if (!profile.value) return
  isSavingEdits.value = true
  try {
    const res = await CandidateProfileAPI.update(profile.value.id, patchData)
    profile.value = res.data
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSavingEdits.value = false
  }
}

async function deleteProfile() {
  if (!profile.value) return
  if (!confirm('Are you sure you want to delete your active candidate profile? All extracted competencies will be reset.')) return

  isDeleting.value = true
  try {
    await CandidateProfileAPI.delete(profile.value.id)
    profile.value = null
    rawCVInput.value = ''
    uiStore.showToast('Candidate profile cleared', 'info')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isDeleting.value = false
  }
}

onMounted(async () => {
  await loadProfile()
  try {
    const res = await IntakeAPI.getEvaluations(20)
    if (Array.isArray(res.data)) {
      const activeCVTask = res.data.find(
        (t) => t.task_type === 'CV_EXTRACTION' && ['QUEUED', 'PROCESSING'].includes(t.status)
      )
      if (activeCVTask) {
        isProcessing.value = true
        currentTaskId.value = activeCVTask.id
        currentTaskStatus.value = activeCVTask.status
        currentTaskStage.value = activeCVTask.stage
        pollTaskUntilComplete(activeCVTask.id)
      }
    }
  } catch (err) {
    // ignore
  }
})
</script>

<template>
  <div class="page-container" :class="{ 'embedded-profile-container': isEmbedded }">
    <!-- Header -->
    <div v-if="!isEmbedded" class="profile-header">
      <div>
        <div class="header-badge">
          <ShieldCheck :size="14" />
          <span>Privacy-First Candidate Profile</span>
        </div>
        <h1 class="page-title">Candidate Profile &amp; Skills</h1>
        <p class="page-subtitle">
          Sanitized locally before AI processing. Powers pre-application qualification audits, keyword gap analysis, and tailored CV guidance.
        </p>
      </div>

      <div v-if="profile" class="header-actions">
        <button
          class="btn btn-secondary btn-sm"
          @click="showUpdateDrawer = !showUpdateDrawer"
        >
          <Edit3 :size="14" />
          <span>{{ showUpdateDrawer ? 'Close Resume Input' : 'Update / Re-Paste Resume' }}</span>
        </button>

        <button
          class="btn btn-ghost btn-sm text-danger"
          :disabled="isDeleting"
          @click="deleteProfile"
          title="Delete profile"
        >
          <Trash2 :size="14" />
          <span>Clear Profile</span>
        </button>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- COLLAPSIBLE RESUME SOURCE & SANITIZATION DRAWER / TOP PANEL        -->
    <!-- =================================================================== -->
    <div v-if="showUpdateDrawer || !profile" class="resume-input-panel animate-fade-in">
      <div class="panel-card">
        <div class="panel-header">
          <div class="panel-title">
            <FileText :size="16" class="text-primary" />
            <span>{{ profile ? 'Update Resume Source Text' : 'Import Candidate Resume / CV' }}</span>
          </div>

          <div class="panel-header-actions">
            <input
              ref="fileInput"
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              class="hidden-file-input"
              @change="handleFileUpload"
            />

            <button
              type="button"
              class="btn btn-secondary btn-xs"
              :disabled="isParsingFile || isProcessing"
              @click="triggerFileInput"
            >
              <Loader2 v-if="isParsingFile" class="animate-spin" :size="13" />
              <Upload v-else :size="13" />
              <span>{{ isParsingFile ? 'Extracting File...' : 'Upload Resume File' }}</span>
            </button>

            <!-- Input Tabs -->
            <div class="input-tabs">
              <button
                class="tab-btn"
                :class="{ active: activeInputTab === 'raw' }"
                @click="activeInputTab = 'raw'"
              >
                Raw Input
              </button>
              <button
                class="tab-btn"
                :class="{ active: activeInputTab === 'preview' }"
                @click="activeInputTab = 'preview'"
              >
                <Lock :size="12" />
                <span>Local Scrubbed Preview</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Cloud vs Local Advisory -->
        <div class="privacy-callout">
          <Info :size="15" class="text-primary flex-shrink-0" />
          <span>
            <strong>Zero-Cloud Contact Sanitization:</strong> Real names, emails, phone numbers, addresses, and personal links are redacted client-side via regex before AI dispatch.
          </span>
        </div>

        <!-- Live Redaction Stats -->
        <div v-if="localScrubResult.stats.total > 0" class="redaction-stats-pill font-mono">
          🛡️ <strong>{{ localScrubResult.stats.total }}</strong> PII item(s) sanitized locally:
          <span v-if="localScrubResult.stats.emails">{{ localScrubResult.stats.emails }} email(s) </span>
          <span v-if="localScrubResult.stats.phones">{{ localScrubResult.stats.phones }} phone(s) </span>
          <span v-if="localScrubResult.stats.urls">{{ localScrubResult.stats.urls }} link(s) </span>
          <span v-if="localScrubResult.stats.addresses">{{ localScrubResult.stats.addresses }} address(es)</span>
        </div>

        <!-- Privacy Review Advisory Banner -->
        <div v-if="activeInputTab === 'raw'" class="privacy-review-banner animate-fade-in">
          <AlertTriangle :size="16" class="banner-icon flex-shrink-0" />
          <div class="banner-content">
            <strong class="banner-title">Manual Privacy Review Recommended</strong>
            <p class="banner-desc">
              Please review and edit the loaded text below to scan for any phone numbers, home addresses, personal email addresses, or specific former company names before submitting. You can edit the text directly in the raw input box to scrub any missed details prior to triggering the de-anonymization and profile activation pipeline.
            </p>
          </div>
        </div>

        <!-- Raw Textarea -->
        <textarea
          v-if="activeInputTab === 'raw'"
          v-model="rawCVInput"
          rows="10"
          class="form-textarea font-mono text-xs"
          placeholder="Paste your complete resume or CV text here or use the 'Upload Resume File' button above..."
        ></textarea>

        <!-- Local Preview -->
        <div
          v-else
          class="local-preview-box font-mono text-xs"
        >
          {{ localScrubResult.scrubbedText || 'Paste resume text to see live local sanitization preview...' }}
        </div>

        <!-- Queue Processing Stepper Card -->
        <div v-if="isProcessing" class="queue-progress-card animate-fade-in">
          <div class="queue-progress-header">
            <div class="queue-status-title">
              <Loader2 class="animate-spin text-primary" :size="16" />
              <span>Processing in AI Queue (Task #{{ currentTaskId || '...' }})</span>
            </div>
            <span class="queue-stage-badge">{{ currentTaskStage }}</span>
          </div>

          <div class="stepper-track">
            <div
              class="stepper-step"
              :class="{
                active: currentTaskStage === 'SCRUBBING',
                complete: ['EXTRACTING', 'SAVING', 'COMPLETE'].includes(currentTaskStage),
              }"
            >
              <div class="step-dot">1</div>
              <span class="step-label">Local PII Scrubbing</span>
            </div>

            <div
              class="stepper-step"
              :class="{
                active: currentTaskStage === 'EXTRACTING',
                complete: ['SAVING', 'COMPLETE'].includes(currentTaskStage),
              }"
            >
              <div class="step-dot">2</div>
              <span class="step-label">AI Extraction</span>
            </div>

            <div
              class="stepper-step"
              :class="{
                active: currentTaskStage === 'SAVING',
                complete: currentTaskStage === 'COMPLETE',
              }"
            >
              <div class="step-dot">3</div>
              <span class="step-label">Profile Activation</span>
            </div>
          </div>
        </div>

        <div class="panel-actions">
          <button
            class="btn btn-primary"
            :disabled="isProcessing || !rawCVInput.trim()"
            @click="processCV"
          >
            <Loader2 v-if="isProcessing" class="animate-spin" :size="16" />
            <Sparkles v-else :size="16" />
            <span>{{ isProcessing ? 'Processing in Queue...' : (profile ? 'Re-Analyze & Update Profile' : 'De-Identify & Activate Profile') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- ACTIVE PROFILE MAIN WORKSPACE (FULL WIDTH SPACIOUS LAYOUT)          -->
    <!-- =================================================================== -->
    <div v-if="profile" class="profile-main-layout animate-fade-in">
      <!-- 1. Top Hero Overview Card -->
      <div class="hero-overview-card">
        <div class="hero-top-row">
          <div class="hero-identity">
            <div class="profile-avatar">
              <ShieldCheck :size="24" class="text-success" />
            </div>
            <div>
              <div class="hero-title-row">
                <span class="hero-name">Candidate Active Profile</span>
                <span class="badge badge-applied">Verified &amp; De-Identified</span>
              </div>
              <span class="hero-meta text-xs text-muted">
                Created {{ new Date(profile.created_at).toLocaleDateString() }} • Ready for job match evaluations
              </span>
            </div>
          </div>

          <!-- Overall Years Stepper -->
          <div class="experience-counter-box">
            <span class="counter-label">Cumulative Experience</span>
            <div class="stepper-controls">
              <button
                type="button"
                class="step-btn"
                title="Decrease overall experience by 0.5 yrs"
                @click="adjustTotalYears(-0.5)"
              >
                -
              </button>
              <span class="counter-val font-mono font-bold">
                {{ profile.years_of_experience || 0 }} <span class="counter-unit">yrs</span>
              </span>
              <button
                type="button"
                class="step-btn"
                title="Increase overall experience by 0.5 yrs"
                @click="adjustTotalYears(0.5)"
              >
                +
              </button>
            </div>
          </div>
        </div>

        <!-- Executive Summary -->
        <div class="summary-section">
          <div class="section-sub-header">
            <span class="section-title">Executive Candidate Summary</span>
            <button
              v-if="!isEditingSummary"
              class="btn btn-ghost btn-xs text-secondary"
              @click="startEditingSummary"
            >
              <Edit3 :size="12" />
              <span>Edit</span>
            </button>
          </div>

          <p v-if="!isEditingSummary" class="summary-text">
            {{ profile.summary || 'No summary generated.' }}
          </p>

          <div v-else class="summary-editor-box">
            <textarea
              v-model="editedSummaryText"
              rows="3"
              class="form-textarea text-xs"
            ></textarea>
            <div class="editor-actions-row">
              <button class="btn btn-ghost btn-xs" @click="isEditingSummary = false">Cancel</button>
              <button class="btn btn-primary btn-xs" @click="saveEditedSummary">Save Summary</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Specialized Domain / Area Experience Breakdown -->
      <div class="content-card">
        <div class="card-header-clean">
          <div>
            <h3 class="card-title">Domain &amp; Area Experience Breakdown</h3>
            <p class="card-sub">
              Granular durations across your core industry specializations. Muted domains are preserved on your profile but automatically excluded from AI match qualifications.
            </p>
          </div>
        </div>

        <!-- Domain Cards Grid -->
        <div class="domains-grid">
          <div
            v-for="item in (profile.domain_experience || [])"
            :key="item.domain"
            class="domain-card"
            :class="{ 'is-muted': !item.is_active }"
          >
            <div class="domain-card-top">
              <span class="domain-name" :title="item.domain">{{ item.domain }}</span>
              <button
                class="btn-icon-xs text-danger"
                title="Remove domain area"
                @click="removeDomainArea(item)"
              >
                <Trash2 :size="12" />
              </button>
            </div>

            <!-- Years Stepper -->
            <div class="domain-stepper-row">
              <button
                type="button"
                class="step-btn-sm"
                title="Decrease years"
                @click="adjustDomainYears(item, -0.5)"
              >
                -
              </button>
              <span class="domain-years-val font-mono">
                {{ item.years }} <span class="text-xs text-muted">years</span>
              </span>
              <button
                type="button"
                class="step-btn-sm"
                title="Increase years"
                @click="adjustDomainYears(item, 0.5)"
              >
                +
              </button>
            </div>

            <!-- Active / Mute Toggle -->
            <div class="domain-toggle-footer">
              <button
                type="button"
                class="domain-toggle-btn"
                :class="{ active: item.is_active, muted: !item.is_active }"
                @click="toggleDomainActive(item)"
              >
                <span class="toggle-dot"></span>
                <span>{{ item.is_active ? 'Active for Matching' : 'Muted (Ignored)' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Add New Domain Bar -->
        <div class="add-domain-bar">
          <input
            v-model="newDomainName"
            type="text"
            placeholder="Add new specialization (e.g. Distributed Systems, FinTech)..."
            class="form-input flex-1 text-xs"
            @keyup.enter="addDomainArea"
          />
          <div class="domain-years-input-group">
            <span class="text-xs text-muted">Years:</span>
            <input
              v-model.number="newDomainYears"
              type="number"
              step="0.5"
              min="0.5"
              max="50"
              class="form-input font-mono text-xs w-16"
            />
          </div>
          <button
            class="btn btn-secondary btn-sm"
            :disabled="!newDomainName.trim()"
            @click="addDomainArea"
          >
            <Plus :size="14" />
            <span>Add Area</span>
          </button>
        </div>
      </div>

      <!-- 3. Technical Skills & Core Competencies Split -->
      <div class="skills-competencies-grid">
        <!-- Core Competencies -->
        <div class="content-card">
          <div class="card-header-clean">
            <div>
              <h3 class="card-title">Core Competencies</h3>
              <p class="card-sub">Top standout technical and leadership strengths.</p>
            </div>
          </div>

          <div class="chip-cloud">
            <span
              v-for="comp in (profile.core_competencies || [])"
              :key="comp"
              class="tag-chip comp-chip"
            >
              <span>{{ comp }}</span>
              <button class="chip-remove-btn" @click="removeCompetency(comp)">
                <X :size="11" />
              </button>
            </span>
          </div>

          <div class="add-chip-row">
            <input
              v-model="newCompetencyInput"
              type="text"
              placeholder="+ Add competency..."
              class="form-input text-xs flex-1"
              @keyup.enter="addCompetency"
            />
            <button class="btn btn-ghost btn-xs" :disabled="!newCompetencyInput.trim()" @click="addCompetency">
              <Plus :size="12" />
            </button>
          </div>
        </div>

        <!-- Canonical Skills Cloud -->
        <div class="content-card">
          <div class="card-header-clean">
            <div>
              <h3 class="card-title">Canonical Technical Skills ({{ (profile.extracted_skills || []).length }})</h3>
              <p class="card-sub">Languages, frameworks, databases, and ATS keywords.</p>
            </div>
          </div>

          <div class="chip-cloud skills-scroll-box">
            <span
              v-for="skill in (profile.extracted_skills || [])"
              :key="skill"
              class="tag-chip skill-chip"
            >
              <span>{{ skill }}</span>
              <button class="chip-remove-btn" @click="removeSkill(skill)">
                <X :size="11" />
              </button>
            </span>
          </div>

          <div class="add-chip-row">
            <input
              v-model="newSkillInput"
              type="text"
              placeholder="+ Add canonical skill..."
              class="form-input text-xs flex-1"
              @keyup.enter="addSkill"
            />
            <button class="btn btn-ghost btn-xs" :disabled="!newSkillInput.trim()" @click="addSkill">
              <Plus :size="12" />
            </button>
          </div>
        </div>
      </div>

      <!-- 4. Sanitized Resume Document Viewer / Editor -->
      <div class="content-card">
        <div class="card-header-clean">
          <div>
            <h3 class="card-title">Sanitized Resume Document</h3>
            <p class="card-sub">
              Clean markdown document with contact info stripped and dates converted to duration windows. Used for AI qualification audits.
            </p>
          </div>

          <div class="header-actions-group">
            <button
              v-if="!isEditingCV"
              class="btn btn-ghost btn-xs"
              title="Edit sanitized resume text"
              @click="startEditingCV"
            >
              <Edit3 :size="13" />
              <span>Edit Document</span>
            </button>

            <button
              v-if="!isEditingCV"
              class="btn btn-ghost btn-xs"
              title="Copy sanitized resume text"
              @click="copyAnonymizedCV"
            >
              <Copy :size="13" />
              <span>Copy</span>
            </button>

            <button
              class="btn btn-ghost btn-xs"
              @click="isDocExpanded = !isDocExpanded"
            >
              <component :is="isDocExpanded ? ChevronUp : ChevronDown" :size="14" />
              <span>{{ isDocExpanded ? 'Collapse' : 'Expand' }}</span>
            </button>
          </div>
        </div>

        <div v-if="isDocExpanded" class="doc-container animate-fade-in">
          <!-- Read-only Document View -->
          <div v-if="!isEditingCV" class="sanitized-doc-body font-mono text-xs">
            {{ profile.anonymized_text || 'No anonymized text generated yet.' }}
          </div>

          <!-- In-place Markdown Editor -->
          <div v-else class="doc-editor-box">
            <textarea
              v-model="editedCVText"
              rows="16"
              class="form-textarea font-mono text-xs"
            ></textarea>
            <div class="editor-actions-row">
              <button class="btn btn-secondary btn-sm" @click="isEditingCV = false">Cancel</button>
              <button class="btn btn-primary btn-sm" @click="saveEditedCV">
                <Save :size="14" />
                <span>Save Sanitized Document</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- EMPTY STATE (NO PROFILE YET)                                       -->
    <!-- =================================================================== -->
    <div v-else-if="!isProcessing" class="empty-profile-layout">
      <div class="empty-card">
        <ShieldCheck :size="42" class="text-primary" />
        <h2 class="empty-title">No Candidate Profile Active</h2>
        <p class="empty-sub">
          Paste your resume or CV in the form above to activate your privacy-first profile. The system scrubs PII locally and extracts skills for AI job matching.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.profile-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background-color: var(--status-offer-bg);
  color: var(--text-success);
  border: 1px solid var(--status-offer-border);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 8px;
}

.page-title {
  font-family: var(--font-heading);
  font-size: 24px;
  font-weight: var(--font-heading-weight);
  color: var(--text-main);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 680px;
  margin-top: 4px;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Resume Source Drawer / Panel */
.resume-input-panel {
  margin-bottom: 24px;
}

.panel-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.hidden-file-input {
  display: none;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.privacy-review-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background-color: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.35);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  color: var(--text-main);
  font-size: 12px;
  line-height: 1.5;
}

.banner-icon {
  color: #eab308;
  margin-top: 1px;
}

.banner-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.banner-title {
  font-weight: 700;
  color: var(--text-main);
}

.banner-desc {
  color: var(--text-secondary);
}

.input-tabs {
  display: flex;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: transparent;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
}

.tab-btn.active {
  background-color: var(--bg-elevated);
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
}

.privacy-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.redaction-stats-pill {
  font-size: 11px;
  color: var(--text-success);
  background-color: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
}

.local-preview-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
  max-height: 220px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  line-height: 1.5;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

/* Queue Progress Stepper */
.queue-progress-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.queue-status-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.queue-stage-badge {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--primary);
}

.stepper-track {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stepper-step {
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0.4;
  transition: all var(--transition-fast);
}

.stepper-step.active {
  opacity: 1;
  font-weight: 600;
  color: var(--primary);
}

.stepper-step.complete {
  opacity: 0.9;
  color: var(--text-success);
}

.step-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
}

.stepper-step.active .step-dot {
  background-color: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.stepper-step.complete .step-dot {
  background-color: var(--text-success);
  color: #fff;
  border-color: var(--text-success);
}

.step-label {
  font-size: 11px;
}

/* =================================================================== */
/* Main Active Profile Styles                                          */
/* =================================================================== */
.profile-main-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-overview-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  padding: 24px;
  box-shadow: var(--card-shadow);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.hero-identity {
  display: flex;
  align-items: center;
  gap: 14px;
}

.profile-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background-color: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.hero-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
}

.experience-counter-box {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.counter-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
}

.stepper-controls {
  display: flex;
  align-items: center;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px 4px;
  gap: 8px;
}

.step-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  background-color: var(--bg-elevated);
  color: var(--text-main);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.step-btn:hover {
  background-color: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.counter-val {
  font-size: 15px;
  color: var(--text-main);
}

.counter-unit {
  font-size: 11px;
  color: var(--text-muted);
}

.summary-section {
  border-top: 1px solid var(--border-subtle);
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-sub-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
}

.summary-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.summary-editor-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.editor-actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* Content Cards */
.content-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--card-shadow);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header-clean {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.card-sub {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
  line-height: 1.4;
}

.header-actions-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Domains Grid */
.domains-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.domain-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all var(--transition-fast);
}

.domain-card.is-muted {
  opacity: 0.6;
  background-color: var(--bg-hover);
  border-style: dashed;
}

.domain-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.domain-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-icon-xs {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
}

.domain-stepper-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  padding: 4px 8px;
}

.step-btn-sm {
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  color: var(--text-main);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.step-btn-sm:hover {
  background-color: var(--primary);
  color: #fff;
}

.domain-years-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.domain-toggle-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid var(--border-subtle);
  background-color: var(--bg-elevated);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.domain-toggle-btn.active {
  color: var(--text-success);
  border-color: var(--status-offer-border);
}

.domain-toggle-btn.muted {
  color: var(--text-muted);
}

.toggle-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
}

.add-domain-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  flex-wrap: wrap;
}

.domain-years-input-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Skills & Competencies Grid */
.skills-competencies-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 768px) {
  .skills-competencies-grid {
    grid-template-columns: 1fr;
  }
}

.chip-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 48px;
}

.skills-scroll-box {
  max-height: 160px;
  overflow-y: auto;
  padding-right: 4px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.comp-chip {
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary);
  color: var(--primary);
  font-weight: 500;
}

.skill-chip {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  color: var(--text-main);
}

.chip-remove-btn {
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 0;
}

.chip-remove-btn:hover {
  color: var(--text-danger);
}

.add-chip-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Document View */
.sanitized-doc-body {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
  max-height: 480px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  line-height: 1.6;
}

.doc-editor-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-profile-layout {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.empty-card {
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  padding: 48px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 480px;
}

.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.empty-sub {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.embedded-profile-container {
  padding: 0 0 80px 0 !important;
  max-width: 100% !important;
}
</style>
