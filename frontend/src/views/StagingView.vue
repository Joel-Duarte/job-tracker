<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { StagingAPI } from '../api/endpoints'
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

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const stagingItems = ref([])
const loading = ref(false)
const isSubmitting = ref(false)
const selectedFilter = ref('PENDING')

// Modal State
const resolvingItem = ref(null)
const resolutionMode = ref('create') // 'create' | 'link'
const selectedExistingAppId = ref(null)
const appSearchQuery = ref('')

const resolveForm = ref({
  company: '',
  position: '',
  status: 'APPLIED',
  job_url: '',
  event_type: 'APPLICATION_CONFIRMATION',
  summary: '',
  action_required: false,
  action: '',
})

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

const filteredExistingApps = computed(() => {
  const apps = appStore.applications || []
  if (!appSearchQuery.value.trim()) return apps
  const q = appSearchQuery.value.toLowerCase()
  return apps.filter(
    (a) =>
      (a.company?.name || '').toLowerCase().includes(q) ||
      (a.position || '').toLowerCase().includes(q)
  )
})

async function fetchStagingItems() {
  loading.value = true
  try {
    const res = await StagingAPI.list({
      status: selectedFilter.value,
      limit: 50,
    })
    stagingItems.value = res.data.items || []
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStagingItems()
  if (appStore.applications.length === 0) {
    appStore.fetchApplications()
  }
})

function openResolveModal(item) {
  resolvingItem.value = item
  resolutionMode.value = 'create'
  selectedExistingAppId.value = null
  appSearchQuery.value = ''

  const extracted = item.extracted_data || {}
  const autoStatus = getAutoDetectedStatus(item)
  const eventType = getDetectedEventType(item)

  resolveForm.value = {
    company: getItemCompany(item),
    position: getItemPosition(item),
    status: autoStatus,
    job_url: extracted.job_url || '',
    event_type: eventType,
    summary:
      extracted.summary ||
      item.email_subject ||
      `Received ${formatEventTypeLabel(eventType)} from ${getItemCompany(item)}`,
    action_required: Boolean(extracted.action_required),
    action: extracted.action || '',
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
    if (resolutionMode.value === 'create') {
      if (!resolveForm.value.company.trim() || !resolveForm.value.position.trim()) {
        uiStore.showToast('Company and Position are required.', 'warning')
        isSubmitting.value = false
        return
      }

      await StagingAPI.resolve(resolvingItem.value.id, {
        company: resolveForm.value.company.trim(),
        position: resolveForm.value.position.trim(),
        status: resolveForm.value.status,
        job_url: resolveForm.value.job_url.trim() || null,
        event_type: resolveForm.value.event_type,
        summary: resolveForm.value.summary.trim() || null,
        action_required: resolveForm.value.action_required,
        action: resolveForm.value.action?.trim() || null,
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
        application_id: selectedExistingAppId.value,
        company: matchedApp?.company?.name || resolveForm.value.company,
        position: matchedApp?.position || resolveForm.value.position,
        status: resolveForm.value.status || matchedApp?.status,
        event_type: resolveForm.value.event_type,
        summary: resolveForm.value.summary.trim() || null,
        action_required: resolveForm.value.action_required,
        action: resolveForm.value.action?.trim() || null,
        create_new: false,
      })

      uiStore.showToast(
        `Linked email event to '${matchedApp?.company?.name || 'application'}'!`,
        'success'
      )
    }

    resolvingItem.value = null
    fetchStagingItems()
    appStore.fetchApplications()
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
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Human-in-the-Loop Staging Queue</h1>
        <p class="page-subtitle">
          Review unmatched emails, resolve ambiguous job leads into new applications, or link them to existing pipeline records.
        </p>
      </div>

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
    </div>

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
            
            <div class="match-meta">
              <span
                v-if="item.match_reason === 'DUPLICATE_APPLICATION_FOUND'"
                class="badge badge-warning text-xs font-semibold"
              >
                Duplicate Match
              </span>
              <span v-else class="confidence-badge">
                <span class="confidence-lbl">Match Score:</span>
                <span class="confidence-val">{{ ((item.match_score || 0) * 100).toFixed(0) }}%</span>
              </span>
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

    <!-- RESOLUTION MODAL -->
    <div v-if="resolvingItem" class="modal-backdrop" @click.self="resolvingItem = null">
      <div class="modal-card modal-lg animate-fade-in">
        <div class="modal-header">
          <div class="modal-title-group">
            <Sparkles :size="18" class="text-primary" />
            <div>
              <h3 class="modal-title">Resolve Staging Item</h3>
              <p class="modal-subtitle">Turn this incoming email into a new job application or link to an existing one.</p>
            </div>
          </div>
          <button class="btn-close" @click="resolvingItem = null">×</button>
        </div>

        <!-- Mode Selector Tabs -->
        <div class="tab-bar">
          <button
            class="tab-btn"
            :class="{ active: resolutionMode === 'create' }"
            @click="resolutionMode = 'create'"
          >
            <Sparkles :size="14" />
            <span>Quick Create Application</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: resolutionMode === 'link' }"
            @click="resolutionMode = 'link'"
          >
            <LinkIcon :size="14" />
            <span>Link to Existing Application</span>
          </button>
        </div>

        <div class="modal-body">
          <!-- MODE 1: CREATE APPLICATION -->
          <div v-if="resolutionMode === 'create'" class="space-y-4">
            <div class="form-grid-2">
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

            <div class="form-grid-2">
              <div class="input-group">
                <label class="input-label">Target Pipeline Status</label>
                <select v-model="resolveForm.status" class="form-input">
                  <option value="APPLIED">Applied (Default)</option>
                  <option value="TECHNICAL_INTERVIEW">Technical Interview / OA</option>
                  <option value="OFFER">Offer</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="ASSESSMENT">AI Assessment Studio</option>
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

            <!-- Optional Job URL Scraping Field -->
            <div class="input-group">
              <label class="input-label flex items-center justify-between">
                <span>Job Posting URL (Optional)</span>
                <span class="text-xs text-muted">Paste to auto-scrape full job specs &amp; skills</span>
              </label>
              <div class="input-with-icon">
                <LinkIcon :size="15" class="field-icon" />
                <input
                  v-model="resolveForm.job_url"
                  type="url"
                  placeholder="https://jobs.lever.co/... or https://boards.greenhouse.io/..."
                  class="form-input"
                />
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

            <!-- Action Required Toggle -->
            <div class="action-required-card">
              <label class="flex items-center gap-2 cursor-pointer">
                <input v-model="resolveForm.action_required" type="checkbox" />
                <span class="text-xs font-semibold text-main">Requires Follow-up / Action Item</span>
              </label>
              <div v-if="resolveForm.action_required" class="mt-2">
                <input
                  v-model="resolveForm.action"
                  type="text"
                  class="form-input text-xs"
                  placeholder="e.g. Schedule recruiter screen by Friday 5 PM"
                />
              </div>
            </div>
          </div>

          <!-- MODE 2: LINK TO EXISTING APPLICATION -->
          <div v-else class="space-y-4">
            <div class="search-box">
              <Search :size="15" class="text-muted" />
              <input
                v-model="appSearchQuery"
                type="text"
                placeholder="Search active applications by company or position..."
                class="search-input"
              />
            </div>

            <div class="existing-apps-list">
              <div
                v-for="app in filteredExistingApps"
                :key="app.id"
                class="existing-app-row"
                :class="{ active: selectedExistingAppId === app.id }"
                @click="selectedExistingAppId = app.id"
              >
                <div class="app-info">
                  <span class="app-company">{{ app.company?.name || 'Unknown' }}</span>
                  <span class="app-position">{{ app.position }}</span>
                </div>
                <div class="app-meta">
                  <span class="stage-pill" :class="getStatusBadgeClass(app.status)">
                    {{ formatStatusLabel(app.status) }}
                  </span>
                  <div class="radio-circle" :class="{ checked: selectedExistingAppId === app.id }">
                    <Check v-if="selectedExistingAppId === app.id" :size="12" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="resolvingItem = null" :disabled="isSubmitting">
            Cancel
          </button>
          <button
            class="btn btn-primary"
            :disabled="isSubmitting || (resolutionMode === 'link' && !selectedExistingAppId)"
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
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--navbar-height));
  background-color: var(--bg-app);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
}

.page-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  letter-spacing: var(--font-tracking);
  font-size: 20px;
  color: var(--text-main);
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.filter-pills {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
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
.modal-lg {
  max-width: 640px;
  width: 90%;
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tab-bar {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  padding: 0 16px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--text-main);
}

.tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
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

.action-required-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
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
