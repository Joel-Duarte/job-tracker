<script setup>
import { ref, watch, computed } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import {
  X,
  Building2,
  ExternalLink,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  DollarSign,
  MapPin,
  Sparkles,
  Layers,
  CheckSquare,
  Trash2,
  Send,
  Loader2,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const activeTab = ref('timeline') // 'timeline' | 'job_spec' | 'actions' | 'embedding'
const showDeleteConfirm = ref(false)
const isDeleting = ref(false)

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

const INTERVIEW_STAGES = [
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
  () => uiStore.activeDetailId,
  (newId) => {
    if (newId) {
      appStore.fetchApplicationDetail(newId)
    }
  },
  { immediate: true }
)

const latestEvent = computed(() => {
  const events = appStore.selectedApplication?.events
  if (!events || events.length === 0) return null
  return events[events.length - 1]
})

function close() {
  uiStore.closeDetail()
}

function handleStatusSelect(e) {
  const newStatus = e.target.value
  if (!appStore.selectedApplication || newStatus === appStore.selectedApplication.status) return

  if (['TECHNICAL_INTERVIEW', 'OFFER', 'REJECTED'].includes(newStatus)) {
    transitionTargetStatus.value = newStatus
    const today = new Date().toISOString().substring(0, 10)
    transitionForm.value = {
      interview_stage: 'Technical Round 1',
      scheduled_at: '',
      offered_salary: appStore.selectedApplication.job_posting?.salary_max || null,
      currency: appStore.selectedApplication.job_posting?.currency || 'USD',
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
            <div class="status-control">
              <label class="status-label">Status</label>
              <select
                :value="appStore.selectedApplication.status"
                class="status-select"
                :class="`status-${appStore.selectedApplication.status?.toLowerCase()}`"
                @change="handleStatusSelect"
              >
                <option value="ASSESSMENT">AI Assessment</option>
                <option value="APPLIED">Applied</option>
                <option value="ONLINE_ASSESSMENT">Online Assessment</option>
                <option value="TECHNICAL_INTERVIEW">Technical Interview</option>
                <option value="OFFER">Offer</option>
                <option value="REJECTED">Rejected</option>
              </select>
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
              v-if="appStore.selectedApplication.action_items?.length"
              class="tab-item"
              :class="{ active: activeTab === 'actions' }"
              @click="activeTab = 'actions'"
            >
              <CheckSquare :size="15" />
              <span>Action Items</span>
            </button>

            <button
              class="tab-item"
              :class="{ active: activeTab === 'embedding' }"
              @click="activeTab = 'embedding'"
            >
              <Sparkles :size="15" />
              <span>AI Snapshot</span>
            </button>
          </div>

          <!-- Tab Panels -->
          <div class="drawer-body">
            <!-- 1. TIMELINE STREAM -->
            <div v-if="activeTab === 'timeline'" class="timeline-stream">
              <div
                v-for="(event, idx) in appStore.selectedApplication.events || []"
                :key="event.id || idx"
                class="timeline-item"
              >
                <div class="timeline-bullet"></div>
                <div class="timeline-card">
                  <div class="event-header">
                    <span class="badge" :class="`badge-${(event.email_status_after_event || 'applied').toLowerCase()}`">
                      {{ event.email_event_type }}
                    </span>
                    <span class="event-date">{{ formatDate(event.email_received_at || event.created_at) }}</span>
                  </div>

                  <div v-if="event.email_subject" class="event-subject">
                    {{ event.email_subject }}
                  </div>

                  <div v-if="event.email_summary" class="event-summary">
                    {{ event.email_summary }}
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

              <!-- Job Markdown Text -->
              <div
                v-if="appStore.selectedApplication.job_posting?.description_markdown"
                class="job-description-raw"
              >
                {{ appStore.selectedApplication.job_posting.description_markdown }}
              </div>
            </div>

            <!-- 3. ACTION ITEMS -->
            <div v-else-if="activeTab === 'actions'" class="action-items-panel">
              <div
                v-for="action in appStore.selectedApplication.action_items || []"
                :key="action.id"
                class="action-item-card"
              >
                <div class="action-header">
                  <span
                    class="urgency-badge"
                    :class="`urgency-${action.urgency?.toLowerCase() || 'medium'}`"
                  >
                    {{ action.urgency || 'MEDIUM' }}
                  </span>
                  <span class="action-status">{{ action.status }}</span>
                </div>
                <div class="action-title">{{ action.title }}</div>
                <div v-if="action.due_date" class="action-due">
                  <Calendar :size="13" />
                  <span>Due: {{ formatDate(action.due_date) }}</span>
                </div>
              </div>
            </div>

            <!-- 4. AI SNAPSHOT / EMBEDDING -->
            <div v-else-if="activeTab === 'embedding'" class="ai-snapshot-panel">
              <div class="snapshot-header">
                <Sparkles :size="16" class="text-primary" />
                <span class="snapshot-title">Synthesized Narrative Snapshot</span>
              </div>
              <p class="snapshot-description">
                This narrative snapshot is embedded as a 768-dimension vector in pgvector for semantic vector search.
              </p>
              <div class="snapshot-content">
                {{ appStore.selectedApplication.embedding_record?.content || 'No vector embedding narrative generated yet.' }}
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
              <input
                v-model="transitionForm.scheduled_at"
                type="datetime-local"
                class="form-input"
              />
            </div>
          </div>

          <!-- Offer Compensation & Deadlines -->
          <div v-if="transitionTargetStatus === 'OFFER'" class="form-group-stack">
            <div class="form-group">
              <label class="form-label">Offered Compensation / Salary</label>
              <div class="salary-input-row">
                <input
                  v-model="transitionForm.offered_salary"
                  type="number"
                  placeholder="e.g. 185000"
                  class="form-input"
                />
                <select v-model="transitionForm.currency" class="form-select currency-select">
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="CAD">CAD ($)</option>
                  <option value="CHF">CHF</option>
                </select>
              </div>
            </div>

            <div class="form-row-2">
              <div class="form-group">
                <label class="form-label">Offer Received Date</label>
                <input
                  v-model="transitionForm.offer_received_date"
                  type="date"
                  class="form-input"
                />
              </div>

              <div class="form-group">
                <label class="form-label">Decision Deadline (Limit Date)</label>
                <input
                  v-model="transitionForm.decision_deadline"
                  type="date"
                  class="form-input"
                />
              </div>
            </div>
          </div>

          <!-- Rejection Reason & Date -->
          <div v-if="transitionTargetStatus === 'REJECTED'" class="form-group-stack">
            <div class="form-group">
              <label class="form-label">Rejection Notice Date</label>
              <input
                v-model="transitionForm.rejection_date"
                type="date"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label class="form-label">Rejection Reason</label>
              <select v-model="transitionForm.rejection_reason" class="form-select">
                <option v-for="reason in REJECTION_REASONS" :key="reason" :value="reason">
                  {{ reason }}
                </option>
              </select>
            </div>
          </div>

          <!-- Optional Notes -->
          <div class="form-group">
            <label class="form-label">Additional Context / Notes (Optional)</label>
            <textarea
              v-model="transitionForm.notes"
              rows="3"
              placeholder="Add quick notes about feedback, interviewers, or timeline..."
              class="form-textarea text-xs"
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
</template>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 400;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 100%;
  max-width: 620px;
  height: 100vh;
  background-color: var(--bg-surface);
  border-left: 1px solid var(--border-color);
  box-shadow: var(--shadow-lg);
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
  font-size: 18px;
  font-weight: 700;
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
  gap: 16px;
  padding: 12px 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
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
}

.status-select.status-applied { color: var(--status-applied-text); }
.status-select.status-interview, .status-select.status-technical_interview { color: var(--status-interview-text); }
.status-select.status-offer { color: var(--status-offer-text); }
.status-select.status-rejected { color: var(--status-rejected-text); }

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
  color: var(--text-main);
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
  gap: 20px;
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
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
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

.action-item-card {
  padding: 14px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 10px;
}

.action-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
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

.action-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.action-due {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.ai-snapshot-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.snapshot-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.snapshot-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.snapshot-description {
  font-size: 12px;
  color: var(--text-muted);
}

.snapshot-content {
  padding: 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-main);
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
  margin: 16px 24px 0 24px;
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
  box-shadow: 0 0 0 rgba(99, 102, 241, 0.4);
  animation: pulse-ring 2s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(99, 102, 241, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
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
  background-color: rgba(0, 0, 0, 0.6);
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
  font-size: 15px;
  font-weight: 700;
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
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
