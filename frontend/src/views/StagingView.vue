<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useQueueStore } from '../stores/queueStore'
import { StagingAPI } from '../api/endpoints'
import { getFitScores } from '../utils/fitScores'
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Edit3,
  Mail,
  AlertTriangle,
  Building2,
  Loader2,
  Sparkles,
  Link as LinkIcon,
  Search,
  Check,
  Calendar,
  Layers,
  ArrowRight,
  ExternalLink,
  ChevronDown,
} from 'lucide-vue-next'
import PageHeader from '../components/common/PageHeader.vue'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const stagingItems = ref([])
const loading = ref(false)
const isSubmitting = ref(false)
const selectedFilter = ref('PENDING')

// Modal State (2-Step Resolution Wizard)
const resolvingItem = ref(null)
const currentStep = ref(1) // 1 = Select Target, 2 = Configure Details
const resolutionMode = ref('create') // 'create' | 'link'
const selectedExistingAppId = ref(null)
const appSearchQuery = ref('')

const resolveForm = ref({
  company: '',
  position: '',
  status: 'APPLIED',
  job_url: '',
  description_markdown: '',
  event_type: 'APPLICATION_CONFIRMATION',
  summary: '',
  action_required: false,
  action: '',
  urgency: 'MEDIUM',
  due_date: '',
})

function getSelectedExistingApp() {
  if (!selectedExistingAppId.value) return null
  return appStore.applications.find((a) => a.id === selectedExistingAppId.value)
}

function handleSelectExistingApp(appId) {
  resolutionMode.value = 'link'
  selectedExistingAppId.value = appId
}

function handleSelectCreateNew() {
  resolutionMode.value = 'create'
  selectedExistingAppId.value = null
}

function proceedToStep2() {
  if (resolutionMode.value === 'link' && !selectedExistingAppId.value) {
    uiStore.showToast(
      'Please select an existing application to link with, or choose Create as New Application.',
      'warning'
    )
    return
  }
  currentStep.value = 2
}

function getItemCompany(item) {
  return (
    item.extracted_data?.company ||
    item.extracted_data?.company_name ||
    item.suggested_company ||
    'Unknown Company'
  )
}

function getItemPosition(item) {
  return (
    item.extracted_data?.position ||
    item.suggested_position ||
    'Software Engineer'
  )
}

function getDetectedEventType(item) {
  const extracted = item.extracted_data || {}
  return extracted.event_type || extracted.email_event_type || 'APPLICATION_CONFIRMATION'
}

function getAutoDetectedStatus(item) {
  const eventType = (getDetectedEventType(item) || '').toUpperCase()
  if (
    eventType.includes('INTERVIEW') ||
    eventType.includes('ASSESSMENT') ||
    eventType.includes('OA') ||
    eventType.includes('SCREEN')
  ) {
    return 'TECHNICAL_INTERVIEW'
  }
  if (eventType.includes('REJECT') || eventType.includes('NOT_MOVING_FORWARD')) {
    return 'REJECTED'
  }
  if (eventType.includes('OFFER')) {
    return 'OFFER'
  }
  return 'APPLIED'
}

function formatEventTypeLabel(eventType) {
  const t = (eventType || '').toUpperCase()
  if (t.includes('INTERVIEW')) return 'Interview Invitation'
  if (t.includes('REJECT')) return 'Rejection Notice'
  if (t.includes('OFFER')) return 'Offer Letter'
  if (t.includes('OA') || t.includes('ASSESSMENT')) return 'Assessment / Test'
  return 'Application Confirmation'
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'APPLIED':
      return 'status-applied'
    case 'TECHNICAL_INTERVIEW':
      return 'status-interview'
    case 'OFFER':
      return 'status-offer'
    case 'REJECTED':
      return 'status-rejected'
    default:
      return 'status-neutral'
  }
}

function formatStatusLabel(status) {
  switch (status) {
    case 'APPLIED':
      return 'Applied'
    case 'TECHNICAL_INTERVIEW':
      return 'Technical Interview'
    case 'OFFER':
      return 'Offer'
    case 'REJECTED':
      return 'Rejected'
    case 'ASSESSMENT':
      return 'AI Assessment'
    default:
      return status
  }
}

const includeArchivedApps = ref(false)

const filteredExistingApps = computed(() => {
  let apps = appStore.applications || []
  if (!includeArchivedApps.value) {
    apps = apps.filter((a) => !['REJECTED', 'ARCHIVED'].includes(a.status))
  }
  if (!appSearchQuery.value.trim()) return apps
  const q = appSearchQuery.value.toLowerCase()
  return apps.filter(
    (a) =>
      (a.company?.name || '').toLowerCase().includes(q) ||
      (a.position || '').toLowerCase().includes(q)
  )
})

async function fetchStagingItems(silent = false) {
  if (!silent) {
    loading.value = true
  }
  try {
    const res = await StagingAPI.list({
      status: selectedFilter.value,
      limit: 50,
    })
    stagingItems.value = res.data.items || []
  } catch (err) {
    if (!silent) {
      uiStore.showToast(err.message, 'error')
    }
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

let stagingPollInterval = null

onMounted(() => {
  fetchStagingItems()
  if (appStore.applications.length === 0) {
    appStore.fetchApplications()
  }

  // Poll for newly staged items in real-time
  stagingPollInterval = setInterval(() => {
    if (!resolvingItem.value) {
      fetchStagingItems(true)
    }
  }, 2500)
})

onUnmounted(() => {
  if (stagingPollInterval) {
    clearInterval(stagingPollInterval)
  }
})

function openResolveModal(item) {
  resolvingItem.value = item
  currentStep.value = 1
  resolutionMode.value = 'create'
  selectedExistingAppId.value = null
  includeArchivedApps.value = false
  appSearchQuery.value = getItemCompany(item) || ''

  const extracted = item.extracted_data || {}
  const autoStatus = getAutoDetectedStatus(item)
  const eventType = getDetectedEventType(item)

  resolveForm.value = {
    company: getItemCompany(item),
    position: getItemPosition(item),
    status: autoStatus,
    job_url: extracted.job_url || '',
    description_markdown: '',
    event_type: eventType,
    summary:
      extracted.summary ||
      item.email_subject ||
      `Received ${formatEventTypeLabel(eventType)} from ${getItemCompany(item)}`,
    action_required: Boolean(extracted.action_required),
    action: extracted.action || '',
    urgency: 'MEDIUM',
    due_date: '',
  }
}

async function quickApproveAsDetected(item) {
  const autoStatus = getAutoDetectedStatus(item)
  const eventType = getDetectedEventType(item)
  const extracted = item.extracted_data || {}

  isSubmitting.value = true
  try {
    await StagingAPI.resolve(item.id, {
      company: getItemCompany(item),
      position: getItemPosition(item),
      status: autoStatus,
      event_type: eventType,
      job_url: extracted.job_url || null,
      summary:
        extracted.summary ||
        item.email_subject ||
        `Received ${formatEventTypeLabel(eventType)} from ${getItemCompany(item)}`,
      action_required: Boolean(extracted.action_required),
      action: extracted.action || null,
      create_new: true,
    })

    uiStore.showToast(
      `Created '${getItemCompany(item)}' in ${formatStatusLabel(autoStatus)} stage!`,
      'success'
    )
    fetchStagingItems()
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

async function submitResolution() {
  if (!resolvingItem.value) return
  isSubmitting.value = true

  try {
    const payload = {
      status: resolveForm.value.status,
      event_type: resolveForm.value.event_type,
      summary: resolveForm.value.summary.trim() || null,
      action_required: resolveForm.value.action_required,
      action: resolveForm.value.action?.trim() || null,
      urgency: resolveForm.value.action_required ? resolveForm.value.urgency : null,
      due_date:
        resolveForm.value.action_required && resolveForm.value.due_date
          ? new Date(resolveForm.value.due_date).toISOString()
          : null,
    }

    if (resolutionMode.value === 'create') {
      if (!resolveForm.value.company.trim() || !resolveForm.value.position.trim()) {
        uiStore.showToast('Company and Position are required.', 'warning')
        isSubmitting.value = false
        return
      }

      await StagingAPI.resolve(resolvingItem.value.id, {
        ...payload,
        company: resolveForm.value.company.trim(),
        position: resolveForm.value.position.trim(),
        job_url: resolveForm.value.job_url.trim() || null,
        description_markdown: resolveForm.value.description_markdown.trim() || null,
        create_new: true,
      })

      uiStore.showToast(
        `Created '${resolveForm.value.company}' application & recorded timeline event!`,
        'success'
      )
    } else {
      // Link to existing application
      if (!selectedExistingAppId.value) {
        uiStore.showToast('Please select an existing application to link with.', 'warning')
        isSubmitting.value = false
        return
      }

      const matchedApp = appStore.applications.find((a) => a.id === selectedExistingAppId.value)
      await StagingAPI.resolve(resolvingItem.value.id, {
        ...payload,
        application_id: selectedExistingAppId.value,
        company: matchedApp?.company?.name || resolveForm.value.company,
        position: matchedApp?.position || resolveForm.value.position,
        create_new: false,
      })

      uiStore.showToast(
        `Linked email event to '${matchedApp?.company?.name || 'application'}'!`,
        'success'
      )
    }

    const resolvedMode = resolutionMode.value
    const resolvedAppId = selectedExistingAppId.value

    resolvingItem.value = null
    fetchStagingItems()
    appStore.fetchApplications()
    if (resolvedMode === 'link' && resolvedAppId) {
      appStore.fetchApplicationDetail(resolvedAppId)
    }
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

async function dismissItem(item) {
  try {
    await StagingAPI.delete(item.id)
    uiStore.showToast('Staged communication dismissed', 'info')
    fetchStagingItems()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}
</script>

<template>
  <div class="page-container">
    <!-- Standardized Page Header -->
    <PageHeader
      title="Human-in-the-Loop Staging Queue"
      subtitle="Review unmatched emails, resolve ambiguous job leads into new applications, or link them to existing pipeline records."
      align="center"
    >
      <template #tabs>
        <div class="filter-pills">
          <button
            class="pill-btn"
            :class="{ active: selectedFilter === 'PENDING' }"
            @click="selectedFilter = 'PENDING'; fetchStagingItems()"
          >
            Pending Review
          </button>
          <button
            class="pill-btn"
            :class="{ active: selectedFilter === 'PROCESSED' }"
            @click="selectedFilter = 'PROCESSED'; fetchStagingItems()"
          >
            Resolved
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Main Content -->
    <div class="content-area">
      <div v-if="loading" class="loading-state">
        <Loader2 class="animate-spin text-primary" :size="28" />
        <span>Loading staging items...</span>
      </div>

      <div v-else-if="stagingItems.length === 0" class="empty-state-box">
        <Inbox :size="48" class="empty-state-icon" />
        <h3 class="empty-state-title">Staging Queue is Clear</h3>
        <p class="empty-state-desc">All incoming recruiter communications have been matched and routed to your pipeline.</p>
      </div>

      <div v-else class="staging-grid">
        <div
          v-for="item in stagingItems"
          :key="item.id"
          class="staging-card animate-fade-in"
        >
          <!-- Card Top Bar -->
          <div class="card-top">
            <div class="company-tag">
              <Building2 :size="16" class="text-primary" />
              <span class="company-name">{{ getItemCompany(item) }}</span>
            </div>
          </div>

          <!-- Position & Detected Event -->
          <div class="role-row">
            <span class="role-title">{{ getItemPosition(item) }}</span>
            <span class="event-pill" :class="getStatusBadgeClass(getAutoDetectedStatus(item))">
              {{ formatEventTypeLabel(getDetectedEventType(item)) }}
            </span>
          </div>

          <!-- Email Preview Snippet -->
          <div class="email-details-box">
            <div class="detail-row">
              <Mail :size="13" class="text-muted" />
              <span class="detail-subject">{{ item.email_subject || 'No Subject Line' }}</span>
            </div>
            <div v-if="item.email_raw_body" class="detail-body-snippet font-mono text-xs">
              {{ item.email_raw_body }}
            </div>
          </div>

          <!-- Recommendation Banner -->
          <div v-if="selectedFilter === 'PENDING'" class="recommendation-bar">
            <Sparkles :size="13" class="text-primary" />
            <span>
              Target Stage: <strong>{{ formatStatusLabel(getAutoDetectedStatus(item)) }}</strong>
            </span>
          </div>

          <!-- Action Buttons -->
          <div v-if="selectedFilter === 'PENDING'" class="card-actions">
            <button
              class="btn btn-ghost btn-xs text-danger"
              @click="dismissItem(item)"
              title="Dismiss non-job email"
            >
              <XCircle :size="14" />
              <span>Dismiss</span>
            </button>

            <div class="actions-right">
              <button
                class="btn btn-secondary btn-sm"
                @click="openResolveModal(item)"
                title="Configure company, status, or optional job URL"
              >
                <Edit3 :size="13" />
                <span>Configure &amp; Link</span>
              </button>

              <button
                class="btn btn-primary btn-sm"
                :disabled="isSubmitting"
                @click="quickApproveAsDetected(item)"
                title="1-Click Create with auto-detected settings"
              >
                <CheckCircle2 :size="14" />
                <span>Quick Create</span>
              </button>
            </div>
          </div>

          <!-- Resolved State Footer -->
          <div v-else class="resolved-footer">
            <Check :size="14" class="text-success" />
            <span>Processed and committed to Application Pipeline</span>
          </div>
        </div>
      </div>
    </div>

    <!-- RESOLUTION MODAL (2-STEP WIZARD) -->
    <div v-if="resolvingItem" class="modal-backdrop" @click.self="resolvingItem = null">
      <div class="modal-card modal-lg animate-fade-in">
        <div class="modal-header">
          <div class="modal-title-group">
            <Sparkles :size="18" class="text-primary" />
            <div>
              <h3 class="modal-title">Resolve Staging Item</h3>
              <p class="modal-subtitle">
                {{ currentStep === 1 ? 'Step 1 of 2: Select Target Application' : 'Step 2 of 2: Configure Event & Actions' }}
              </p>
            </div>
          </div>
          <button class="btn-close" @click="resolvingItem = null">×</button>
        </div>

        <!-- Step Indicator Bar -->
        <div class="step-indicator-bar">
          <div
            class="step-badge"
            :class="{ active: currentStep === 1, done: currentStep > 1 }"
            @click="currentStep = 1"
          >
            <span class="step-num">1</span>
            <span>Select Target</span>
          </div>
          <div class="step-divider"></div>
          <div
            class="step-badge"
            :class="{ active: currentStep === 2, disabled: resolutionMode === 'link' && !selectedExistingAppId }"
            @click="proceedToStep2"
          >
            <span class="step-num">2</span>
            <span>Configure Event &amp; Actions</span>
          </div>
        </div>

        <!-- STEP 1: SELECT DESTINATION -->
        <div v-if="currentStep === 1" class="modal-body space-y-4">
          <!-- Option A: Create New Application Card -->
          <div
            class="destination-card new-app-card"
            :class="{ selected: resolutionMode === 'create' }"
            @click="handleSelectCreateNew"
          >
            <div class="destination-card-header">
              <div class="dest-icon-circle">
                <Sparkles :size="16" />
              </div>
              <div class="dest-info">
                <span class="dest-title">Create as New Application</span>
                <span class="dest-desc">
                  Start a new pipeline application for <strong>{{ getItemCompany(resolvingItem) }}</strong> — <em>{{ getItemPosition(resolvingItem) }}</em>
                </span>
              </div>
              <div class="circle-checkbox" :class="{ checked: resolutionMode === 'create' }">
                <Check v-if="resolutionMode === 'create'" :size="11" :stroke-width="3" />
              </div>
            </div>
          </div>

          <div class="divider-with-text">
            <span>OR LINK TO AN EXISTING APPLICATION</span>
          </div>

          <!-- Option B: Search & List Existing Applications -->
          <div class="link-search-bar-row">
            <div class="search-box">
              <Search :size="16" class="search-icon" />
              <input
                v-model="appSearchQuery"
                type="text"
                placeholder="Search applications by company or position..."
                class="search-input"
              />
            </div>

            <div
              class="include-archived-toggle"
              @click="includeArchivedApps = !includeArchivedApps"
            >
              <div class="circle-checkbox" :class="{ checked: includeArchivedApps }">
                <Check v-if="includeArchivedApps" :size="11" :stroke-width="3" />
              </div>
              <span class="include-archived-text">Include Rejected / Archived</span>
            </div>
          </div>

          <div class="existing-apps-list">
            <div
              v-if="filteredExistingApps.length === 0"
              class="empty-apps-notice"
            >
              No existing applications match your search.
            </div>
            <div
              v-for="app in filteredExistingApps"
              :key="app.id"
              class="existing-app-row"
              :class="{ active: resolutionMode === 'link' && selectedExistingAppId === app.id }"
              @click="handleSelectExistingApp(app.id)"
            >
              <div class="app-info">
                <span class="app-company">{{ app.company?.name || 'Unknown' }}</span>
                <span class="app-position">{{ app.position }}</span>
              </div>
              <div class="app-meta">
                <span class="stage-pill" :class="getStatusBadgeClass(app.status)">
                  {{ formatStatusLabel(app.status) }}
                </span>
                <div
                  class="circle-checkbox"
                  :class="{ checked: resolutionMode === 'link' && selectedExistingAppId === app.id }"
                >
                  <Check
                    v-if="resolutionMode === 'link' && selectedExistingAppId === app.id"
                    :size="11"
                    :stroke-width="3"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- STEP 2: CONFIGURE DETAILS & ACTION ITEMS -->
        <div v-else-if="currentStep === 2" class="modal-body space-y-4">
          <!-- Target Application Context Banner -->
          <div class="target-context-banner">
            <div v-if="resolutionMode === 'create'" class="target-badge-new">
              <Sparkles :size="14" class="text-primary" />
              <span>Creating New Application: <strong>{{ resolveForm.company }}</strong> ({{ resolveForm.position }})</span>
            </div>
            <div v-else class="target-badge-link">
              <LinkIcon :size="14" class="text-primary" />
              <span>Linking Event to: <strong>{{ getSelectedExistingApp()?.company?.name || 'Selected Company' }}</strong> — <em>{{ getSelectedExistingApp()?.position || 'Application' }}</em></span>
            </div>
          </div>

          <!-- If New Application: Show Company & Position edit fields -->
          <div v-if="resolutionMode === 'create'" class="form-grid-2">
            <div class="input-group">
              <label class="input-label">Company Name *</label>
              <div class="input-with-icon">
                <Building2 :size="15" class="field-icon" />
                <input
                  v-model="resolveForm.company"
                  type="text"
                  placeholder="e.g. Stripe, OpenAI, Datadog"
                  class="form-input"
                  required
                />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">Position / Job Title *</label>
              <input
                v-model="resolveForm.position"
                type="text"
                placeholder="e.g. Senior Backend Engineer"
                class="form-input"
                required
              />
            </div>
          </div>

          <!-- Stage and Event Type Dropdowns (NO Assessment Studio) -->
          <div class="form-grid-2">
            <div class="input-group">
              <label class="input-label">Target Pipeline Status</label>
              <select v-model="resolveForm.status" class="form-input">
                <option value="APPLIED">Applied (Default)</option>
                <option value="ONLINE_ASSESSMENT">Online Assessment (OA)</option>
                <option value="TECHNICAL_INTERVIEW">Technical Interview</option>
                <option value="OFFER">Offer</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>

            <div class="input-group">
              <label class="input-label">Email Event Type</label>
              <select v-model="resolveForm.event_type" class="form-input">
                <option value="APPLICATION_CONFIRMATION">Application Confirmation</option>
                <option value="INTERVIEW_INVITATION">Interview Invitation</option>
                <option value="ONLINE_ASSESSMENT">Online Assessment (OA)</option>
                <option value="REJECTION">Rejection Notice</option>
                <option value="OFFER_LETTER">Offer Letter</option>
                <option value="STATUS_UPDATE">General Status Update</option>
              </select>
            </div>
          </div>

          <!-- URL and Description (only in create mode) -->
          <div v-if="resolutionMode === 'create'" class="form-grid-2">
            <div class="input-group">
              <label class="input-label">Job Posting URL</label>
              <div class="input-with-icon">
                <LinkIcon :size="15" class="field-icon" />
                <input
                  v-model="resolveForm.job_url"
                  type="url"
                  placeholder="https://jobs.lever.co/..."
                  class="form-input"
                />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">Raw Job Description</label>
              <textarea
                v-model="resolveForm.description_markdown"
                class="form-input"
                rows="2"
                placeholder="Paste full text or markdown job specs..."
                style="resize: vertical; min-height: 36px;"
              ></textarea>
            </div>
          </div>

          <!-- Event Summary -->
          <div class="input-group">
            <label class="input-label">Timeline Event Summary</label>
            <input
              v-model="resolveForm.summary"
              type="text"
              class="form-input"
              placeholder="Brief snapshot of what this communication conveyed..."
            />
          </div>

          <!-- Action Required Card with Urgency & Due Date -->
          <div
            class="action-required-card"
            :class="{ active: resolveForm.action_required }"
          >
            <div
              class="action-required-header"
              @click="resolveForm.action_required = !resolveForm.action_required"
            >
              <div class="circle-checkbox action-circle" :class="{ checked: resolveForm.action_required }">
                <Check v-if="resolveForm.action_required" :size="11" :stroke-width="3" />
              </div>
              <span class="action-required-label">Requires Follow-up / Action Item</span>
            </div>

            <div v-if="resolveForm.action_required" class="action-expanded-fields mt-3">
              <div class="input-group mb-2">
                <label class="input-label">Action Description *</label>
                <input
                  v-model="resolveForm.action"
                  type="text"
                  class="form-input text-xs"
                  placeholder="e.g. Schedule recruiter screen via Calendly link"
                  required
                />
              </div>

              <div class="form-grid-2">
                <div class="input-group">
                  <label class="input-label">Urgency Level</label>
                  <div class="urgency-pill-selector">
                    <button
                      type="button"
                      class="urgency-choice-btn high"
                      :class="{ active: resolveForm.urgency === 'HIGH' }"
                      @click="resolveForm.urgency = 'HIGH'"
                    >
                      High
                    </button>
                    <button
                      type="button"
                      class="urgency-choice-btn medium"
                      :class="{ active: resolveForm.urgency === 'MEDIUM' }"
                      @click="resolveForm.urgency = 'MEDIUM'"
                    >
                      Medium
                    </button>
                    <button
                      type="button"
                      class="urgency-choice-btn low"
                      :class="{ active: resolveForm.urgency === 'LOW' }"
                      @click="resolveForm.urgency = 'LOW'"
                    >
                      Low
                    </button>
                  </div>
                </div>

                <div class="input-group">
                  <label class="input-label">Due Date (Optional)</label>
                  <input
                    v-model="resolveForm.due_date"
                    type="date"
                    class="form-input text-xs"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-actions">
          <button
            v-if="currentStep === 1"
            class="btn btn-secondary"
            @click="resolvingItem = null"
            :disabled="isSubmitting"
          >
            Cancel
          </button>
          <button
            v-else
            class="btn btn-secondary"
            @click="currentStep = 1"
            :disabled="isSubmitting"
          >
            ← Back
          </button>

          <button
            v-if="currentStep === 1"
            class="btn btn-primary"
            :disabled="resolutionMode === 'link' && !selectedExistingAppId"
            @click="proceedToStep2"
          >
            <span>Next: Configure Event Details →</span>
          </button>
          <button
            v-else
            class="btn btn-primary"
            :disabled="isSubmitting"
            @click="submitResolution"
          >
            <Loader2 v-if="isSubmitting" class="animate-spin" :size="15" />
            <span v-else>
              {{ resolutionMode === 'create' ? 'Create & Link Application' : 'Link to Selected Application' }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
  min-height: calc(100vh - var(--navbar-height));
  width: 100%;
}

.filter-pills {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 3px;
  justify-content: center;
}

.pill-btn {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.pill-btn:hover {
  color: var(--text-main);
}

.pill-btn.active {
  background-color: var(--bg-elevated);
  color: var(--primary);
  font-weight: 600;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 240px;
  color: var(--text-secondary);
  font-size: 14px;
}

.staging-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.staging-card {
  background-color: var(--bg-card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  box-shadow: var(--card-shadow);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.staging-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-hover-shadow);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.company-tag {
  display: flex;
  align-items: center;
  gap: 6px;
}

.company-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.confidence-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  background-color: var(--bg-surface);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.confidence-lbl {
  color: var(--text-muted);
}

.confidence-val {
  color: var(--primary);
  font-weight: 600;
}

.role-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.role-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.event-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}

.status-applied {
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border-color: var(--status-applied-border);
}

.status-interview {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border-color: var(--status-interview-border);
}

.status-offer {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border-color: var(--status-offer-border);
}

.status-rejected {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.status-neutral {
  background-color: var(--bg-surface);
  color: var(--text-muted);
  border-color: var(--border-color);
}

.email-details-box {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-subject {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-body-snippet {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.recommendation-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  background-color: var(--primary-subtle);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
}

.card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.resolved-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-success);
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

/* MODAL STYLES */
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
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.modal-lg {
  max-width: 640px;
  width: 90%;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-card);
  flex-shrink: 0;
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Step Indicator Bar */
.step-indicator-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

.step-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.step-badge.active {
  color: var(--primary);
  font-weight: 600;
}

.step-badge.done {
  color: var(--text-secondary);
}

.step-badge.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background-color: var(--bg-card);
  border: 1.5px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.step-badge.active .step-num {
  background-color: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.step-badge.done .step-num {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--primary);
}

.step-divider {
  width: 36px;
  height: 1px;
  background-color: var(--border-color);
}

/* Destination Cards (Step 1) */
.destination-card {
  background-color: var(--bg-surface);
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.destination-card:hover {
  border-color: var(--primary);
  background-color: var(--bg-hover);
}

.destination-card.selected {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.destination-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dest-icon-circle {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  flex-shrink: 0;
}

.dest-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dest-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.dest-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

.divider-with-text {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 12px 0 6px;
}

.divider-with-text::before,
.divider-with-text::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--border-color);
}

.divider-with-text span {
  padding: 0 10px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.empty-apps-notice {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
}

/* Target Context Banner (Step 2) */
.target-context-banner {
  padding: 10px 14px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 13px;
  display: flex;
  align-items: center;
}

.target-badge-new,
.target-badge-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-main);
}

/* Urgency Selector Pills */
.urgency-pill-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.urgency-choice-btn {
  flex: 1;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.urgency-choice-btn:hover {
  color: var(--text-main);
  border-color: var(--text-muted);
}

.urgency-choice-btn.high.active {
  background-color: rgba(239, 68, 68, 0.15);
  border-color: #ef4444;
  color: #ef4444;
}

.urgency-choice-btn.medium.active {
  background-color: rgba(234, 179, 8, 0.15);
  border-color: #eab308;
  color: #eab308;
}

.urgency-choice-btn.low.active {
  background-color: rgba(59, 130, 246, 0.15);
  border-color: #3b82f6;
  color: #3b82f6;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.field-icon {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
}

.input-with-icon .form-input {
  padding-left: 32px;
}

/* Circle Checkbox */
.circle-checkbox {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid var(--border-color);
  background-color: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.circle-checkbox:hover {
  border-color: var(--primary);
}

.circle-checkbox.checked {
  background-color: var(--primary);
  border-color: var(--primary);
}

/* Action Required Card with Yellow Glow */
.action-required-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  transition: all var(--transition-fast);
  cursor: pointer;
}

.action-required-card:hover {
  border-color: rgba(234, 179, 8, 0.4);
}

.action-required-card.active {
  border-color: rgba(234, 179, 8, 0.6);
  background-color: rgba(234, 179, 8, 0.06);
  box-shadow: 0 0 14px rgba(234, 179, 8, 0.16);
}

.action-required-card.active .circle-checkbox.action-circle.checked {
  background-color: #eab308;
  border-color: #eab308;
  color: #1c1917;
}

.action-required-header {
  display: flex;
  align-items: center;
  gap: 10px;
  user-select: none;
}

.action-required-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

/* Search bar & Include Archived Row */
.link-search-bar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.search-box {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  width: 17px;
  height: 17px;
  color: var(--text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  height: 38px;
  padding: 0 14px 0 38px;
  font-size: 13px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  transition: all var(--transition-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--primary);
  background-color: var(--bg-card);
  box-shadow: 0 0 0 2px var(--primary-subtle);
}

.include-archived-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  flex-shrink: 0;
}

.include-archived-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}

.include-archived-toggle:hover .include-archived-text {
  color: var(--text-main);
}

.existing-apps-list {
  max-height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.existing-app-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.existing-app-row:hover {
  border-color: var(--primary);
  background-color: var(--bg-hover);
}

.existing-app-row.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.app-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.app-company {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.app-position {
  font-size: 12px;
  color: var(--text-secondary);
}

.app-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stage-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  font-weight: 500;
}

.radio-circle {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background-color: var(--bg-app);
}

.radio-circle.checked {
  background-color: var(--primary);
  border-color: var(--primary);
}

.space-y-4 > * + * {
  margin-top: 12px;
}
</style>
