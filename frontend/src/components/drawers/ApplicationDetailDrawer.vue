<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { ActionItemsAPI, ApplicationsAPI } from '../../api/endpoints'
import DateTimePicker from '../common/DateTimePicker.vue'
import InterviewReaderModal from '../modals/InterviewReaderModal.vue'

import {
  X, Check,
  Building2,
  ExternalLink,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  DollarSign,
  Award,
  XCircle,
  Tag,
  MapPin,
  Sparkles,
  Layers,
  CheckSquare,
  Square,
  Plus,
  Trash2,
  Send,
  Loader2,
  SlidersHorizontal,
  BookOpen,
  Globe,
  RotateCcw,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const router = useRouter()
const appStore = useApplicationsStore()

const { detailActiveTab: activeTab } = storeToRefs(uiStore) // 'timeline' | 'job_spec' | 'actions' | 'guide'
const showDeleteConfirm = ref(false)
const isDeleting = ref(false)
const isReaderModalOpen = ref(false)


// In-drawer Action Item creation state
const showNewTaskForm = ref(false)
const isCreatingDrawerTask = ref(false)
const newDrawerTask = ref({
  title: '',
  urgency: 'MEDIUM',
  due_date: '',
})

// Transition modal state
const showTransitionModal = ref(false)
const isSubmittingTransition = ref(false)
const transitionTargetStatus = ref('')
const transitionForm = ref({
  interview_stage: 'Technical Round 1',
  scheduled_at: '',
  offered_salary: null,
  currency: 'USD',
  offer_received_date: '',
  decision_deadline: '',
  rejection_date: '',
  rejection_reason: 'Resume / Initial Screen',
  notes: '',
})


// Interview Guide state
const isGenerating = ref(false)
const showConfigPanel = ref(false)
const showAdvanced = ref(false)

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

async function handleGenerateGuide() {
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
    const res = await ApplicationsAPI.generateInterviewGuide(appStore.selectedApplication.id, payload)
    appStore.selectedApplication = res.data
    showConfigPanel.value = false
    uiStore.showToast('Interview Preparation Guide generated successfully!', 'success')
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
    const res = await ApplicationsAPI.clearInterviewGuide(appStore.selectedApplication.id)
    appStore.selectedApplication = res.data
    showConfigPanel.value = true
    uiStore.showToast('Interview guide cleared', 'info')
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast('Failed to clear interview guide', 'error')
  }
}

function openGuideInNewTab() {
  const routeData = router.resolve({ name: 'InterviewGuide', params: { id: appStore.selectedApplication.id } })
  window.open(routeData.href, '_blank')
}

const INTERVIEW_STAGES = [
  'Interview Requested / Scheduling',
  'Recruiter Screen / Initial Chat',
  'Online Assessment / Take-Home',
  'Technical Round 1',
  'System Design / Live Coding',
  'Hiring Manager / Final Round',
  'Custom / Other',
]

const REJECTION_REASONS = [
  'Resume / Initial Screen',
  'Assessment / Take-Home Test',
  'Technical Round Fit',
  'System Design / Culture Fit',
  'Offer Declined by Candidate',
  'Position Closed / Cancelled',
  'Ghosted / No Response',
  'Other',
]


watch(
  () => [activeTab.value, appStore.selectedApplication?.id],
  ([newTab, _]) => {
    if (newTab === 'guide' && appStore.selectedApplication) {
      if (appStore.selectedApplication.interview_guide_language) {
        selectedLanguage.value = appStore.selectedApplication.interview_guide_language
      }
      if (appStore.selectedApplication.interview_guide_preferences?.selected_sections) {
        selectedSections.value = appStore.selectedApplication.interview_guide_preferences.selected_sections
      }
      if (appStore.selectedApplication.interview_guide_preferences?.recursion_limit) {
        recursionLimit.value = appStore.selectedApplication.interview_guide_preferences.recursion_limit
      }
      showConfigPanel.value = !appStore.selectedApplication.interview_guide_html
    }
  },
  { immediate: true }
)

watch(
  () => uiStore.activeDetailId,
  (newId) => {
    if (newId) {
      appStore.fetchApplicationDetail(newId)
    }
  },
  { immediate: true }
)


const parsedJobSpecSections = computed(() => {
  const md = appStore.selectedApplication?.job_posting?.description_markdown || ''
  if (!md) return []

  let cleaned = md.split(/(?:---|\*\*\*)\s*\n*AI Candidate Fit/i)[0]
  cleaned = cleaned.split(/##\s*AI Candidate Fit/i)[0]

  const lines = cleaned.split('\n')
  const sections = []
  let currentSection = { title: 'Overview', content: [] }

  for (const line of lines) {
    const headerMatch = line.match(/^(#{1,3})\s+(.*)$/)
    if (headerMatch) {
      if (currentSection.content.length > 0 || currentSection.title !== 'Overview') {
        sections.push({ title: currentSection.title, content: currentSection.content.join('\n').trim() })
      }
      currentSection = { title: headerMatch[2], content: [] }
    } else {
      currentSection.content.push(line)
    }
  }
  if (currentSection.content.length > 0) {
    sections.push({ title: currentSection.title, content: currentSection.content.join('\n').trim() })
  }

  return sections.filter(s => s.content || s.title !== 'Overview')
})

function renderMarkdownText(text) {
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')

  const lines = html.split('\n')
  let inList = false
  let out = []

  for (const line of lines) {
    const bulletMatch = line.match(/^[\-\*]\s+(.*)$/)
    if (bulletMatch) {
      if (!inList) {
        inList = true
        out.push('<ul class="jd-list">')
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

  return out.join('\n').replace(/\n/g, '<br>').replace(/<br><ul/g, '<ul').replace(/\/ul><br>/g, '</ul>')
}


function handleStatusSelect(e) {
  const newStatus = e.target.value
  if (!appStore.selectedApplication || newStatus === appStore.selectedApplication.status) return

  if (['TECHNICAL_INTERVIEW', 'OFFER', 'REJECTED'].includes(newStatus)) {
    transitionTargetStatus.value = newStatus
    const today = new Date().toISOString().substring(0, 10)
    transitionForm.value = {
      interview_stage: 'Interview Requested / Scheduling',
      scheduled_at: '',
      offered_salary: appStore.selectedApplication.job_posting?.salary_max || null,
      currency: uiStore.defaultCurrency || 'USD',
      offer_received_date: today,
      decision_deadline: '',
      rejection_date: today,
      rejection_reason: 'Resume / Initial Screen',
      notes: '',
    }
    showTransitionModal.value = true
  } else {
    executeDirectTransition(newStatus)
  }
}

const latestEvent = computed(() => {
  const events = appStore.selectedApplication?.events
  if (!events || events.length === 0) return null
  return events[0]
})

function close() {
  uiStore.closeDetail()
}

function getAppSubPhaseLabel(app) {
  if (!app) return ''
  const status = app.status || 'APPLIED'
  const payload = app.latest_event?.raw_payload || app.events?.[0]?.raw_payload || {}

  if (status === 'TECHNICAL_INTERVIEW') {
    return payload.interview_stage || 'Technical Round 1'
  }
  if (status === 'OFFER') {
    const sal = payload.offered_salary || app.job_posting?.salary_max || app.job_posting?.salary_min
    const curr = payload.currency || app.job_posting?.currency || 'USD'
    return sal ? `$${Number(sal).toLocaleString()} ${curr}` : 'Offer Package'
  }
  if (status === 'REJECTED') {
    return payload.rejection_reason || 'Rejection Notice'
  }
  if (status === 'ASSESSMENT') return 'AI Assessment'
  return 'Applied'
}

function getInterviewDate(app) {
  if (!app) return null
  const payload = app.latest_event?.raw_payload || app.events?.[0]?.raw_payload || {}
  const dateStr = payload.scheduled_at
  if (!dateStr) return null
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

function openEditModal() {
  const app = appStore.selectedApplication
  if (!app) return
  transitionTargetStatus.value = app.status || 'APPLIED'
  const today = new Date().toISOString().substring(0, 10)
  const existingPayload = app.latest_event?.raw_payload || app.events?.[0]?.raw_payload || {}

  const isAlreadyOffer = app.status === 'OFFER'
  const initialCurrency = (isAlreadyOffer && existingPayload.currency)
    ? existingPayload.currency
    : (uiStore.defaultCurrency || 'USD')

  transitionForm.value = {
    interview_stage: existingPayload.interview_stage || 'Interview Requested / Scheduling',
    scheduled_at: existingPayload.scheduled_at ? existingPayload.scheduled_at.substring(0, 16) : '',
    offered_salary: existingPayload.offered_salary || app.job_posting?.salary_max || app.job_posting?.salary_min || null,
    currency: initialCurrency,
    offer_received_date: existingPayload.offer_received_date || today,
    decision_deadline: existingPayload.decision_deadline || '',
    rejection_date: existingPayload.rejection_date || today,
    rejection_reason: existingPayload.rejection_reason || 'Resume / Initial Screen',
    notes: '',
  }
  showTransitionModal.value = true
}



async function executeDirectTransition(status) {
  if (!appStore.selectedApplication) return
  try {
    await appStore.transitionApplication(appStore.selectedApplication.id, { status })
    uiStore.showToast(`Updated status to ${status}`, 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function confirmTransitionSubmit() {
  if (!appStore.selectedApplication) return
  isSubmittingTransition.value = true
  try {
    const payload = {
      status: transitionTargetStatus.value,
      notes: transitionForm.value.notes || undefined,
    }
    if (transitionTargetStatus.value === 'TECHNICAL_INTERVIEW') {
      payload.interview_stage = transitionForm.value.interview_stage
      payload.scheduled_at = transitionForm.value.scheduled_at
        ? new Date(transitionForm.value.scheduled_at).toISOString()
        : undefined
    } else if (transitionTargetStatus.value === 'OFFER') {
      payload.offered_salary = transitionForm.value.offered_salary ? Number(transitionForm.value.offered_salary) : undefined
      payload.currency = transitionForm.value.currency
      payload.offer_received_date = transitionForm.value.offer_received_date || undefined
      payload.decision_deadline = transitionForm.value.decision_deadline || undefined
    } else if (transitionTargetStatus.value === 'REJECTED') {
      payload.rejection_reason = transitionForm.value.rejection_reason
      payload.rejection_date = transitionForm.value.rejection_date || undefined
    }

    await appStore.transitionApplication(appStore.selectedApplication.id, payload)
    uiStore.showToast(`Application transitioned to ${transitionTargetStatus.value}`, 'success')
    showTransitionModal.value = false
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmittingTransition.value = false
  }
}

async function handleDeleteApplication() {
  if (!appStore.selectedApplication) return
  isDeleting.value = true
  try {
    await appStore.deleteApplication(appStore.selectedApplication.id)
    uiStore.showToast('Application deleted successfully', 'info')
    showDeleteConfirm.value = false
    close()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isDeleting.value = false
  }
}

async function handleCreateDrawerTask() {
  if (!newDrawerTask.value.title.trim() || !appStore.selectedApplication) return
  isCreatingDrawerTask.value = true
  try {
    const payload = {
      application_id: appStore.selectedApplication.id,
      title: newDrawerTask.value.title.trim(),
      urgency: newDrawerTask.value.urgency,
      status: 'PENDING',
      due_date: newDrawerTask.value.due_date ? new Date(newDrawerTask.value.due_date).toISOString() : null,
    }
    await ActionItemsAPI.create(payload)
    uiStore.showToast('Action item added', 'success')
    newDrawerTask.value = { title: '', urgency: 'MEDIUM', due_date: '' }
    showNewTaskForm.value = false
    await appStore.fetchApplicationDetail(appStore.selectedApplication.id)
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to create action item', 'error')
  } finally {
    isCreatingDrawerTask.value = false
  }
}

async function handleToggleDrawerTask(action) {
  const newStatus = action.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED'
  action.status = newStatus
  try {
    await ActionItemsAPI.update(action.id, { status: newStatus })
    uiStore.showToast(newStatus === 'COMPLETED' ? 'Task completed' : 'Task marked pending', 'info')
  } catch (err) {
    action.status = newStatus === 'COMPLETED' ? 'PENDING' : 'COMPLETED'
    uiStore.showToast('Failed to update task status', 'error')
  }
}

async function handleDeleteDrawerTask(actionId) {
  try {
    await ActionItemsAPI.delete(actionId)
    uiStore.showToast('Task removed', 'info')
    await appStore.fetchApplicationDetail(appStore.selectedApplication.id)
  } catch (err) {
    uiStore.showToast('Failed to delete task', 'error')
  }
}

function formatDate(isoStr) {
  if (!isoStr) return 'N/A'
  try {
    return new Date(isoStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return isoStr
  }
}
</script>

<template>
  <Transition name="drawer-slide">
    <div v-if="uiStore.activeDetailId" class="drawer-overlay" @click.self="close">
      <div class="drawer-panel">
        <!-- Loading State -->
        <div v-if="appStore.loadingDetail" class="drawer-loading">
          <div class="pulse-dot"></div>
          <span>Loading application intelligence...</span>
        </div>

        <!-- Loaded Content -->
        <div v-else-if="appStore.selectedApplication" class="drawer-content">
          <!-- Drawer Header -->
          <div class="drawer-header">
            <div class="header-main">
              <div class="company-badge-large">
                <Building2 :size="20" />
              </div>
              <div class="header-titles">
                <h2 class="company-name">
                  {{ appStore.selectedApplication.company?.name || 'Company' }}
                </h2>
                <div class="position-title">
                  {{ appStore.selectedApplication.position || 'Position Not Specified' }}
                </div>
              </div>
            </div>

            <div class="header-actions">
              <button
                class="btn-icon-danger"
                title="Delete Application"
                @click="showDeleteConfirm = true"
              >
                <Trash2 :size="16" />
              </button>
              <button class="btn-close" @click="close">
                <X :size="18" />
              </button>
            </div>
          </div>

          <!-- Metadata & Status Bar -->
          <div class="status-bar">
            <div class="status-control-group">
              <!-- Interactive Sub-Status Pill with Edit Trigger -->
              <button
                class="phase-detail-btn"
                :class="`phase-${(appStore.selectedApplication.status || 'applied').toLowerCase()}`"
                @click="openEditModal"
                title="Edit phase details, scheduled dates & compensation"
              >
                <span class="phase-detail-text">{{ getAppSubPhaseLabel(appStore.selectedApplication) }}</span>
                <SlidersHorizontal :size="12" class="phase-icon" />
              </button>

              <!-- Interview Scheduled Date Tag -->
              <div
                v-if="getInterviewDate(appStore.selectedApplication)"
                class="interview-date-tag"
                title="Scheduled Interview Date & Time"
              >
                <Calendar :size="12" />
                <span>{{ getInterviewDate(appStore.selectedApplication) }}</span>
              </div>
            </div>

            <div class="meta-item">
              <Calendar :size="14" class="text-muted" />
              <span>Applied {{ formatDate(appStore.selectedApplication.application_date || appStore.selectedApplication.created_at) }}</span>
            </div>

            <a
              v-if="appStore.selectedApplication.job_url"
              :href="appStore.selectedApplication.job_url"
              target="_blank"
              rel="noopener noreferrer"
              class="btn-link"
            >
              <ExternalLink :size="14" />
              <span>Job Link</span>
            </a>
          </div>

          <!-- LATEST EVENT HIGHLIGHT BANNER -->
          <div v-if="latestEvent" class="latest-event-banner">
            <div class="latest-event-header">
              <div class="latest-event-badge">
                <span class="pulsing-dot"></span>
                <span>LATEST ACTIVITY • {{ formatDate(latestEvent.email_received_at || latestEvent.created_at) }}</span>
              </div>
              <span class="badge" :class="`badge-${(latestEvent.email_status_after_event || appStore.selectedApplication.status || 'applied').toLowerCase()}`">
                {{ latestEvent.email_event_type }}
              </span>
            </div>
            <div class="latest-event-desc">
              {{ latestEvent.email_summary || latestEvent.email_subject || 'Application updated.' }}
            </div>
            <div v-if="latestEvent.email_action_required" class="latest-action-badge">
              <AlertCircle :size="13" />
              <span>Action Required: {{ latestEvent.email_action || 'Response pending' }}</span>
            </div>
          </div>

          <!-- Nav Tabs -->
          <div class="drawer-tabs">
            <button
              class="tab-item"
              :class="{ active: activeTab === 'timeline' }"
              @click="activeTab = 'timeline'"
            >
              <Clock :size="15" />
              <span>Timeline ({{ appStore.selectedApplication.events?.length || 0 }})</span>
            </button>

            <button
              v-if="appStore.selectedApplication.job_posting"
              class="tab-item"
              :class="{ active: activeTab === 'job_spec' }"
              @click="activeTab = 'job_spec'"
            >
              <FileText :size="15" />
              <span>Job Spec</span>
            </button>

            <button
              class="tab-item"
              :class="{ active: activeTab === 'actions' }"
              @click="activeTab = 'actions'"
            >
              <CheckSquare :size="15" />
              <span>Action Items ({{ appStore.selectedApplication.action_items?.length || 0 }})</span>
            </button>

            <button
              class="tab-item"
              :class="{ active: activeTab === 'guide' }"
              @click="activeTab = 'guide'"
            >
              <BookOpen :size="15" />
              <span>Interview Guide</span>
              <span v-if="appStore.selectedApplication.has_interview_guide" class="guide-ready-indicator"></span>
            </button>
          </div>

          <!-- Tab Panels -->
          <div class="drawer-body">
            <!-- 1. TIMELINE STREAM (Newest First) -->
            <div v-if="activeTab === 'timeline'" class="timeline-stream">
              <div
                v-for="(event, idx) in appStore.selectedApplication.events || []"
                :key="event.id || idx"
                class="timeline-item"
              >
                <div class="timeline-bullet"></div>
                <div class="timeline-card">
                  <div class="event-header">
                    <div class="event-type-group">
                      <span class="badge" :class="`badge-${(event.email_status_after_event || 'applied').toLowerCase()}`">
                        {{ event.email_event_type }}
                      </span>
                      <span v-if="event.email_sender_name || event.email_sender" class="event-sender">
                        {{ event.email_sender_name || event.email_sender }}
                      </span>
                    </div>
                    <span class="event-date">{{ formatDate(event.email_received_at || event.created_at) }}</span>
                  </div>

                  <div v-if="event.email_subject" class="event-subject">
                    {{ event.email_subject }}
                  </div>

                  <div v-if="event.email_summary" class="event-summary">
                    {{ event.email_summary }}
                  </div>

                  <!-- Recorded Notes Pill / Card -->
                  <div v-if="event.raw_payload?.notes" class="event-notes-card">
                    <div class="notes-header">
                      <FileText :size="12" class="text-primary" />
                      <span>Note / Context</span>
                    </div>
                    <div class="notes-body">{{ event.raw_payload.notes }}</div>
                  </div>

                  <div v-if="event.email_action_required" class="event-action-required">
                    <AlertCircle :size="14" />
                    <span>Action Required: {{ event.email_action || 'Pending response' }}</span>
                  </div>
                </div>
              </div>

              <div
                v-if="!appStore.selectedApplication.events?.length"
                class="empty-state"
              >
                No timeline events recorded yet.
              </div>
            </div>

            <!-- 2. JOB SPEC (Scraped Details) -->
            <div v-else-if="activeTab === 'job_spec'" class="job-spec-panel">
              <div v-if="appStore.selectedApplication.job_posting" class="spec-grid">
                <div v-if="appStore.selectedApplication.job_posting.salary_min || appStore.selectedApplication.job_posting.salary_max" class="spec-card">
                  <DollarSign :size="16" class="spec-icon" />
                  <div>
                    <div class="spec-label">Compensation</div>
                    <div class="spec-val">
                      ${{ appStore.selectedApplication.job_posting.salary_min?.toLocaleString() }} -
                      ${{ appStore.selectedApplication.job_posting.salary_max?.toLocaleString() }}
                      {{ appStore.selectedApplication.job_posting.currency || 'USD' }}
                    </div>
                  </div>
                </div>

                <div v-if="appStore.selectedApplication.job_posting.location" class="spec-card">
                  <MapPin :size="16" class="spec-icon" />
                  <div>
                    <div class="spec-label">Location / Work Model</div>
                    <div class="spec-val">
                      {{ appStore.selectedApplication.job_posting.location }}
                      <span v-if="appStore.selectedApplication.job_posting.work_model">
                        ({{ appStore.selectedApplication.job_posting.work_model }})
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Skills Badges -->
              <div
                v-if="appStore.selectedApplication.job_posting?.required_skills?.length"
                class="skills-box"
              >
                <div class="skills-title">Extracted Skills & Requirements</div>
                <div class="skills-tags">
                  <span
                    v-for="skill in appStore.selectedApplication.job_posting.required_skills"
                    :key="skill"
                    class="skill-tag"
                  >
                    {{ skill }}
                  </span>
                </div>
              </div>

              <!-- Job Structured Spec -->
              <div v-if="parsedJobSpecSections.length > 0" class="job-structured-spec">
                <div v-for="(sec, idx) in parsedJobSpecSections" :key="idx" class="job-spec-section">
                  <h3 class="job-spec-header">{{ sec.title }}</h3>
                  <div class="job-spec-body" v-html="renderMarkdownText(sec.content)"></div>
                </div>
              </div>
            </div>

            <!-- 3. ACTION ITEMS -->
            <div v-else-if="activeTab === 'actions'" class="action-items-panel">
              <!-- Panel Header with Add Button -->
              <div class="panel-header-row">
                <span class="panel-header-title">Application Tasks</span>
                <button
                  class="btn btn-sm btn-secondary"
                  @click="showNewTaskForm = !showNewTaskForm"
                >
                  <Plus :size="13" />
                  <span>{{ showNewTaskForm ? 'Cancel' : 'Add Task' }}</span>
                </button>
              </div>

              <!-- Inline Task Creation Form -->
              <div v-if="showNewTaskForm" class="drawer-task-form">
                <div class="form-group">
                  <input
                    v-model="newDrawerTask.title"
                    type="text"
                    class="form-input form-input-sm"
                    placeholder="Task title (e.g. Prepare architecture notes, send follow-up...)"
                    @keyup.enter="handleCreateDrawerTask"
                  />
                </div>
                <div class="form-grid-2">
                  <select v-model="newDrawerTask.urgency" class="form-select form-select-sm">
                    <option value="HIGH">High Urgency</option>
                    <option value="MEDIUM">Medium Urgency</option>
                    <option value="LOW">Low Urgency</option>
                  </select>
                  <DateTimePicker
                    v-model="newDrawerTask.due_date"
                    type="datetime"
                    placeholder="Due date & time..."
                  />
                </div>
                <div class="form-actions-row">
                  <button
                    class="btn btn-sm btn-primary"
                    :disabled="isCreatingDrawerTask || !newDrawerTask.title.trim()"
                    @click="handleCreateDrawerTask"
                  >
                    <Loader2 v-if="isCreatingDrawerTask" class="animate-spin" :size="13" />
                    <span>Save Task</span>
                  </button>
                </div>
              </div>

              <!-- Task Cards List -->
              <div
                v-for="action in appStore.selectedApplication.action_items || []"
                :key="action.id"
                class="action-item-card"
                :class="{ 'is-completed': action.status === 'COMPLETED' }"
              >
                <!-- Complete Checkbox -->
                <button
                  class="drawer-checkbox-btn"
                  @click="handleToggleDrawerTask(action)"
                  title="Toggle completion"
                >
                  <CheckSquare v-if="action.status === 'COMPLETED'" :size="18" class="text-primary" />
                  <Square v-else :size="18" class="text-muted" />
                </button>

                <div class="drawer-task-info">
                  <div class="action-header">
                    <span
                      class="urgency-badge"
                      :class="`urgency-${action.urgency?.toLowerCase() || 'medium'}`"
                    >
                      {{ action.urgency || 'MEDIUM' }}
                    </span>
                    <span class="action-status">{{ action.status }}</span>
                  </div>
                  <div class="action-title" :class="{ completed: action.status === 'COMPLETED' }">
                    {{ action.title }}
                  </div>
                  <div v-if="action.due_date" class="action-due">
                    <Calendar :size="12" />
                    <span>Due: {{ formatDate(action.due_date) }}</span>
                  </div>
                </div>

                <button
                  class="btn-icon text-danger"
                  @click="handleDeleteDrawerTask(action.id)"
                  title="Delete task"
                >
                  <Trash2 :size="13" />
                </button>
              </div>

              <div
                v-if="!appStore.selectedApplication.action_items?.length && !showNewTaskForm"
                class="empty-state"
              >
                No action items recorded for this application. Click "Add Task" above to create one.
              </div>
            </div>


            <!-- 4. INTERVIEW PREPARATION GUIDE TAB -->
            <div v-if="activeTab === 'guide'" class="guide-tab-panel animate-fade-in">

              <!-- GENERATION RUNNING STATE -->
              <div v-if="isGenerating" class="state-container generating-state">
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

              <!-- CONFIGURATION PANEL (If no guide or user clicked Re-configure) -->
              <div v-else-if="showConfigPanel" class="config-panel animate-fade-in">
                <div class="config-card">
                  <div class="config-header">
                    <div class="config-title">
                      <Sparkles :size="16" class="text-primary" />
                      <span>Configure Guide Generation</span>
                    </div>
                    <button
                      v-if="appStore.selectedApplication.interview_guide_html"
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
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Generate Button -->
                  <div class="config-actions">
                    <button
                      class="btn btn-primary btn-generate"
                      :disabled="selectedSections.length === 0"
                      @click="handleGenerateGuide"
                    >
                      <Sparkles :size="16" />
                      <span>{{ appStore.selectedApplication.interview_guide_html ? 'Regenerate Interview Guide' : 'Generate Interview Guide' }}</span>
                    </button>
                  </div>
                </div>
              </div>

              <!-- GUIDE READER (When guide exists) -->
              <div v-else-if="appStore.selectedApplication.interview_guide_html" class="guide-empty-state animate-fade-in">
                <div class="guide-empty-icon" style="background-color: var(--status-offer-bg); color: var(--status-offer-text); border-color: var(--status-offer-border);">
                  <BookOpen :size="32" />
                </div>
                <h4 class="guide-empty-title">Interview Guide is Ready</h4>
                <div class="guide-meta-left" style="margin-bottom: 8px;">
                    <span class="guide-lang-badge">
                      <Globe :size="12" />
                      <span>{{ appStore.selectedApplication.interview_guide_language?.toUpperCase() || 'EN' }}</span>
                    </span>
                    <span v-if="appStore.selectedApplication.interview_guide_generated_at" class="guide-meta-time">
                      Generated {{ formatDate(appStore.selectedApplication.interview_guide_generated_at) }}
                    </span>
                </div>
                <p class="guide-empty-desc">
                  Your tactical interview playbook is ready. Open it in the full reader to view, print, or copy the content.
                </p>
                <div class="guide-meta-actions" style="display: flex; gap: 8px; margin-top: 8px;">
                  <button
                    class="btn btn-primary"
                    @click="isReaderModalOpen = true"
                  >
                    <BookOpen :size="15" />
                    <span>Open Full Reader</span>
                  </button>
                  <button
                    class="btn btn-secondary"
                    title="Re-configure or regenerate"
                    @click="showConfigPanel = true"
                  >
                    <RotateCcw :size="15" />
                    <span>Regenerate</span>
                  </button>
                </div>
              </div>

              <!-- Empty State / No Guide Yet -->
              <div v-else class="guide-empty-state">
                <div class="guide-empty-icon">
                  <BookOpen :size="32" class="text-primary" />
                </div>
                <h4 class="guide-empty-title">Interview Prep Guide</h4>
                <p class="guide-empty-desc">
                  Generate an AI-powered tactical interview playbook cross-referencing your candidate profile, role spec, and company signals.
                </p>
                <button
                  class="btn btn-primary"
                  @click="showConfigPanel = true"
                >
                  <Sparkles :size="15" />
                  <span>Configure & Generate</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>

  <!-- TRANSITION POPUP MODAL -->
  <Transition name="fade">
    <div v-if="showTransitionModal" class="inner-modal-backdrop" @click.self="showTransitionModal = false">
      <div class="inner-modal-box">
        <div class="inner-modal-header">
          <div class="inner-modal-title">
            <span>Move to {{ transitionTargetStatus.replace('_', ' ') }}</span>
          </div>
          <button class="btn-close" @click="showTransitionModal = false">
            <X :size="16" />
          </button>
        </div>

        <div class="inner-modal-body">
          <!-- Interview Stage & Schedule -->
          <div v-if="transitionTargetStatus === 'TECHNICAL_INTERVIEW'" class="form-group-stack">
            <div class="form-group">
              <label class="form-label">Interview Phase / Sub-Stage</label>
              <select v-model="transitionForm.interview_stage" class="form-select">
                <option v-for="stage in INTERVIEW_STAGES" :key="stage" :value="stage">
                  {{ stage }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Scheduled Date & Time (Optional)</label>
              <DateTimePicker
                v-model="transitionForm.scheduled_at"
                type="datetime"
                placeholder="Select scheduled date & time..."
              />
            </div>
          </div>

          <!-- Offer Compensation & Deadlines -->
          <div v-if="transitionTargetStatus === 'OFFER'" class="form-group-stack offer-form-box">
            <div class="stage-section-header">
              <div class="stage-section-icon offer-icon">
                <Award :size="16" />
              </div>
              <div class="stage-section-text">
                <span class="stage-section-title">Offer Package Details</span>
                <span class="stage-section-sub">Record compensation package and decision timelines.</span>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Offered Compensation / Annual Base</label>
              <div class="salary-input-group">
                <div class="currency-prefix-box">
                  <DollarSign :size="14" class="text-muted" />
                </div>
                <input
                  v-model="transitionForm.offered_salary"
                  type="number"
                  placeholder="e.g. 185000"
                  class="form-input salary-input"
                />
                <select v-model="transitionForm.currency" class="form-select currency-select">
                  <option v-for="c in uiStore.SUPPORTED_CURRENCIES" :key="c.code" :value="c.code">
                    {{ c.code }} ({{ c.symbol }})
                  </option>
                </select>
              </div>
            </div>

            <div class="form-row-2">
              <div class="form-group">
                <label class="form-label">Offer Received Date</label>
                <DateTimePicker
                  v-model="transitionForm.offer_received_date"
                  type="date"
                  placeholder="Select received date..."
                />
              </div>

              <div class="form-group">
                <label class="form-label">Decision Deadline</label>
                <DateTimePicker
                  v-model="transitionForm.decision_deadline"
                  type="date"
                  placeholder="Select decision deadline..."
                />
              </div>
            </div>
          </div>

          <!-- Rejection Reason & Date -->
          <div v-if="transitionTargetStatus === 'REJECTED'" class="form-group-stack rejection-form-box">
            <div class="stage-section-header">
              <div class="stage-section-icon rejection-icon">
                <XCircle :size="16" />
              </div>
              <div class="stage-section-text">
                <span class="stage-section-title">Rejection Outcome</span>
                <span class="stage-section-sub">Record the outcome and reason for future analytics.</span>
              </div>
            </div>

            <div class="form-row-2">
              <div class="form-group">
                <label class="form-label">Rejection Notice Date</label>
                <DateTimePicker
                  v-model="transitionForm.rejection_date"
                  type="date"
                  placeholder="Select notice date..."
                />
              </div>

              <div class="form-group">
                <label class="form-label">Primary Rejection Reason</label>
                <select v-model="transitionForm.rejection_reason" class="form-select">
                  <option v-for="reason in REJECTION_REASONS" :key="reason" :value="reason">
                    {{ reason }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Quick Reason Selection Chips -->
            <div class="quick-reasons-chips">
              <span class="chips-label">Quick select:</span>
              <button
                v-for="r in ['Resume / Initial Screen', 'Technical Round Fit', 'System Design / Culture Fit', 'Offer Declined by Candidate', 'Position Closed / Cancelled', 'Ghosted / No Response']"
                :key="r"
                type="button"
                class="reason-chip-btn"
                :class="{ active: transitionForm.rejection_reason === r }"
                @click="transitionForm.rejection_reason = r"
              >
                {{ r }}
              </button>
            </div>
          </div>

          <!-- Optional Context / Notes -->
          <div class="form-group notes-form-group">
            <div class="notes-header-row">
              <label class="form-label notes-label">
                <FileText :size="13" class="text-primary" />
                <span>Additional Context / Notes (Optional)</span>
              </label>
              <span class="notes-char-count">{{ transitionForm.notes?.length || 0 }} chars</span>
            </div>
            <textarea
              v-model="transitionForm.notes"
              rows="3"
              placeholder="Add notes about feedback, interviewers, compensation details, or timeline context..."
              class="form-textarea"
            ></textarea>
          </div>
        </div>

        <div class="inner-modal-footer">
          <button class="btn btn-secondary" @click="showTransitionModal = false">Cancel</button>
          <button
            class="btn btn-primary"
            :disabled="isSubmittingTransition"
            @click="confirmTransitionSubmit"
          >
            <Loader2 v-if="isSubmittingTransition" class="animate-spin" :size="15" />
            <Send v-else :size="15" />
            <span>Update & Record Event</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>

  <!-- DELETE CONFIRMATION MODAL -->
  <Transition name="fade">
    <div v-if="showDeleteConfirm" class="inner-modal-backdrop" @click.self="showDeleteConfirm = false">
      <div class="inner-modal-box modal-danger">
        <div class="inner-modal-header">
          <div class="inner-modal-title text-danger">
            <Trash2 :size="18" />
            <span>Delete Job Application?</span>
          </div>
          <button class="btn-close" @click="showDeleteConfirm = false">
            <X :size="16" />
          </button>
        </div>

        <div class="inner-modal-body">
          <p class="modal-warn-text">
            Are you sure you want to permanently delete the application for
            <strong>{{ appStore.selectedApplication?.position }}</strong> at
            <strong>{{ appStore.selectedApplication?.company?.name }}</strong>?
          </p>
          <p class="text-xs text-muted">
            This will permanently remove all associated timeline events, job postings, action items, and embeddings from the database.
          </p>
        </div>

        <div class="inner-modal-footer">
          <button class="btn btn-secondary" @click="showDeleteConfirm = false">Cancel</button>
          <button
            class="btn btn-danger"
            :disabled="isDeleting"
            @click="handleDeleteApplication"
          >
            <Loader2 v-if="isDeleting" class="animate-spin" :size="15" />
            <Trash2 v-else :size="15" />
            <span>{{ isDeleting ? 'Deleting...' : 'Permanently Delete' }}</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>

  <InterviewReaderModal
    :is-open="isReaderModalOpen"
    :application-id="appStore.selectedApplication?.id"
    @close="isReaderModalOpen = false"
  />

  </template>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 400;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
  transition: backdrop-filter 0.3s ease;
}

.drawer-panel {
  width: 100%;
  max-width: 620px;
  height: 100vh;
  background-color: var(--bg-surface);
  border-left: 1px solid var(--card-border);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 10px;
  color: var(--text-secondary);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-main {
  display: flex;
  align-items: center;
  gap: 14px;
}

.company-badge-large {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--primary);
}

.company-name {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 18px;
  color: var(--text-main);
  line-height: 1.2;
}

.position-title {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.status-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}

.status-control-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.status-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
}

.status-select {
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  cursor: pointer;
}

.status-select.status-applied { color: var(--status-applied-text); border-color: var(--status-applied-border); background-color: var(--status-applied-bg); }
.status-select.status-interview, .status-select.status-technical_interview { color: var(--status-interview-text); border-color: var(--status-interview-border); background-color: var(--status-interview-bg); }
.status-select.status-offer { color: var(--status-offer-text); border-color: var(--status-offer-border); background-color: var(--status-offer-bg); }
.status-select.status-rejected { color: var(--status-rejected-text); border-color: var(--status-rejected-border); background-color: var(--status-rejected-bg); }
.status-select.status-assessment { color: var(--status-assessment-text); border-color: var(--status-assessment-border); background-color: var(--status-assessment-bg); }

.phase-detail-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  cursor: pointer;
  transition: all var(--transition-fast);
  max-width: 220px;
}

.phase-detail-btn:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.phase-detail-btn.phase-applied { color: var(--status-applied-text); border-color: var(--status-applied-border); background-color: var(--status-applied-bg); }
.phase-detail-btn.phase-interview, .phase-detail-btn.phase-technical_interview { color: var(--status-interview-text); border-color: var(--status-interview-border); background-color: var(--status-interview-bg); }
.phase-detail-btn.phase-offer { color: var(--status-offer-text); border-color: var(--status-offer-border); background-color: var(--status-offer-bg); }
.phase-detail-btn.phase-rejected { color: var(--status-rejected-text); border-color: var(--status-rejected-border); background-color: var(--status-rejected-bg); }
.phase-detail-btn.phase-assessment { color: var(--status-assessment-text); border-color: var(--status-assessment-border); background-color: var(--status-assessment-bg); }

.phase-detail-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.phase-icon {
  opacity: 0.7;
  flex-shrink: 0;
}

.interview-date-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
  font-family: var(--font-mono);
}

.event-type-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.event-sender {
  font-size: 11px;
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.btn-link {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--primary);
  font-weight: 500;
}
.btn-link:hover {
  text-decoration: underline;
}

.drawer-tabs {
  display: flex;
  padding: 0 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  gap: 8px;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  transition: all var(--transition-fast);
}

.tab-item:hover {
  color: var(--text-main);
}

.tab-item.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.drawer-body {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.timeline-stream {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-stream::before {
  content: '';
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 6px;
  width: 2px;
  background-color: var(--border-subtle);
}

.timeline-item {
  position: relative;
  display: flex;
  gap: 16px;
}

.timeline-bullet {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-color: var(--primary);
  border: 3px solid var(--bg-surface);
  z-index: 2;
  margin-top: 4px;
}

.timeline-card {
  flex: 1;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
}

.event-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.event-date {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.event-subject {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}

.event-summary {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.event-action-required {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  font-size: 12px;
  font-weight: 500;
}

.spec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.spec-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.spec-icon {
  color: var(--primary);
  margin-top: 2px;
}

.spec-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
}

.spec-val {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
}

.skills-box {
  margin-bottom: 16px;
}

.skills-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.skills-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  font-size: 12px;
  color: var(--text-main);
}

.job-description-raw {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  background-color: var(--bg-card);
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.panel-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-header-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 14px;
  color: var(--text-main);
}

.drawer-task-form {
  padding: 14px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-input-sm, .form-select-sm {
  padding: 6px 10px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-main);
}

.form-actions-row {
  display: flex;
  justify-content: flex-end;
}

.action-item-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 10px;
  transition: all var(--transition-fast);
}

.action-item-card.is-completed {
  opacity: 0.6;
}

.drawer-checkbox-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.drawer-task-info {
  flex: 1;
  min-width: 0;
}

.action-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.urgency-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-full);
}

.urgency-high { background: var(--status-rejected-bg); color: var(--status-rejected-text); }
.urgency-medium { background: var(--status-interview-bg); color: var(--status-interview-text); }
.urgency-low { background: var(--status-applied-bg); color: var(--status-applied-text); }

.action-status {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.action-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  line-height: 1.3;
}

.action-title.completed {
  text-decoration: line-through;
  color: var(--text-muted);
}

.action-due {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-icon-danger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.btn-icon-danger:hover {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
}

/* LATEST EVENT HIGHLIGHT BANNER */
.latest-event-banner {
  margin: 16px 24px 16px 24px;
  padding: 14px 16px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.latest-event-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.latest-event-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
  letter-spacing: 0.5px;
}

.pulsing-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: var(--primary);
  box-shadow: 0 0 0 var(--primary-glow);
  animation: pulse-ring 2s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 var(--primary-glow); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px transparent; }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 transparent; }
}

.latest-event-desc {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-main);
}

.latest-action-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  font-size: 11px;
  font-weight: 600;
  width: fit-content;
  margin-top: 4px;
}

/* INNER MODALS */
.inner-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 500;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.inner-modal-box {
  width: 100%;
  max-width: 440px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.inner-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.inner-modal-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 15px;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.inner-modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.inner-modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
}

.salary-input-row {
  display: flex;
  gap: 8px;
}

.currency-select {
  width: 120px;
}

.modal-warn-text {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-main);
  margin-bottom: 8px;
}

/* Transitions */
.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: all var(--transition-spring);
}

.drawer-slide-enter-from,
.drawer-slide-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.form-group-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

/* Offer & Rejection Boxes */
.offer-form-box {
  background-color: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
  border-radius: var(--radius-md);
  padding: 14px;
}

.rejection-form-box {
  background-color: var(--status-rejected-bg);
  border: 1px solid var(--status-rejected-border);
  border-radius: var(--radius-md);
  padding: 14px;
}

.stage-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.stage-section-icon {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stage-section-icon.offer-icon {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
}

.stage-section-icon.rejection-icon {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
}

.stage-section-text {
  display: flex;
  flex-direction: column;
}

.stage-section-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 13px;
  color: var(--text-main);
}

.stage-section-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.salary-input-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.currency-prefix-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.salary-input {
  flex: 1;
}

.currency-select {
  width: 130px;
  flex-shrink: 0;
}

.quick-reasons-chips {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.chips-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.reason-chip-btn {
  padding: 3px 7px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.reason-chip-btn:hover {
  border-color: var(--status-rejected-border);
  color: var(--text-main);
}

.reason-chip-btn.active {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
  font-weight: 600;
}

.event-notes-card {
  margin-top: 8px;
  padding: 8px 12px;
  background-color: var(--bg-surface);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-notes-card .notes-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.event-notes-card .notes-body {
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-main);
  white-space: pre-wrap;
}

.notes-form-group {
  margin-top: 4px;
}

.notes-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.notes-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.notes-char-count {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Interview Guide Tab Styles */
.guide-ready-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: var(--primary);
  box-shadow: 0 0 6px var(--primary-glow);
}

.guide-tab-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-preview-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-preview-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
  gap: 10px;
}

.guide-meta-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-lang-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  background-color: var(--primary-subtle);
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
}

.guide-meta-time {
  font-size: 12px;
  color: var(--text-muted);
}

.guide-meta-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-guide-content {
  max-height: 480px;
  overflow-y: auto;
  padding-right: 8px;
  scrollbar-gutter: stable;
}

.guide-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  background-color: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  gap: 12px;
}

.guide-empty-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
}

.guide-empty-title {
  font-family: var(--font-heading);
  font-size: 16px;
  color: var(--text-main);
  margin: 0;
}

.guide-empty-desc {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 380px;
  line-height: 1.5;
  margin: 0 0 8px 0;
}

/* Drawer Guide Styles */
.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 380px;
  gap: 16px;
  text-align: center;
  padding: 24px;
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
.config-panel {
  max-width: 100%;
}
.config-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
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
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
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


.job-structured-spec {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background-color: var(--bg-card);
  padding: 20px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.job-spec-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.job-spec-header {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 4px;
}

.job-spec-body {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.job-spec-body :deep(strong) {
  color: var(--text-main);
  font-weight: 600;
}

.job-spec-body :deep(em) {
  font-style: italic;
}

.job-spec-body :deep(.jd-list) {
  margin: 6px 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.job-spec-body :deep(.jd-list li) {
  list-style-type: disc;
}


</style>
