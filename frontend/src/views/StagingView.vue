<script setup>
import { ref, onMounted } from 'vue'
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
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const stagingItems = ref([])
const loading = ref(false)
const selectedFilter = ref('PENDING')
const editingItem = ref(null)
const editForm = ref({
  company: '',
  position: '',
  status: 'ASSESSMENT',
  create_new: false,
})

function getItemCompany(item) {
  return item.extracted_data?.company || item.extracted_data?.company_name || item.suggested_company || 'Unknown Company'
}

function getItemPosition(item) {
  return item.extracted_data?.position || item.suggested_position || 'Position Unspecified'
}

function getItemStatus(item) {
  return item.extracted_data?.status || item.suggested_status || 'ASSESSMENT'
}

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
})

async function resolveItem(item, customData = null) {
  try {
    const payload = customData || {
      company: getItemCompany(item),
      position: getItemPosition(item),
      status: getItemStatus(item),
      create_new: false,
    }
    await StagingAPI.resolve(item.id, payload)
    uiStore.showToast(`Staged item for '${payload.company}' processed & committed!`, 'success')
    editingItem.value = null
    fetchStagingItems()
    appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function resolveAsNew(item) {
  await resolveItem(item, {
    company: getItemCompany(item),
    position: getItemPosition(item),
    status: 'ASSESSMENT',
    create_new: true,
  })
}

async function resolveAsUpdate(item) {
  await resolveItem(item, {
    company: getItemCompany(item),
    position: getItemPosition(item),
    status: getItemStatus(item),
    create_new: false,
  })
}

async function dismissItem(item) {
  try {
    await StagingAPI.delete(item.id)
    uiStore.showToast('Staged item dismissed', 'info')
    fetchStagingItems()
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

function startEdit(item) {
  editingItem.value = item
  editForm.value = {
    company: getItemCompany(item),
    position: getItemPosition(item),
    status: getItemStatus(item),
    create_new: false,
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
          Review incoming communications with low confidence, duplicate applications, or ambiguous multi-role matches.
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
          :class="{ active: selectedFilter === 'RESOLVED' }"
          @click="selectedFilter = 'RESOLVED'; fetchStagingItems()"
        >
          Resolved
        </button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="content-area">
      <div v-if="loading" class="loading-state">
        <Loader2 class="animate-spin" :size="24" />
        <span>Loading staging items...</span>
      </div>

      <div v-else-if="stagingItems.length === 0" class="empty-box">
        <Inbox :size="48" class="empty-icon" />
        <h3 class="empty-title">Staging Queue is Clean</h3>
        <p class="empty-desc">No items currently waiting for manual approval.</p>
      </div>

      <div v-else class="staging-grid">
        <div
          v-for="item in stagingItems"
          :key="item.id"
          class="staging-card animate-fade-in"
        >
          <!-- Card Header -->
          <div class="card-top">
            <div class="company-tag">
              <Building2 :size="16" class="text-primary" />
              <span class="company-name">{{ getItemCompany(item) }}</span>
            </div>
            <div class="match-score">
              <span v-if="item.match_reason === 'DUPLICATE_APPLICATION_FOUND'" class="badge badge-warning text-xs font-semibold">
                Duplicate Detected
              </span>
              <template v-else>
                <span class="score-label">Confidence:</span>
                <span class="score-val">{{ ((item.match_score || 0) * 100).toFixed(0) }}%</span>
              </template>
            </div>
          </div>

          <div class="role-title">
            {{ getItemPosition(item) }}
          </div>

          <!-- Email Info -->
          <div class="email-details-box">
            <div class="detail-row">
              <Mail :size="13" class="text-muted" />
              <span class="detail-subject">{{ item.email_subject || 'No Subject' }}</span>
            </div>
            <div v-if="item.email_raw_body" class="detail-body-snippet">
              {{ item.email_raw_body }}
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="card-actions">
            <button
              class="btn btn-secondary btn-sm"
              @click="startEdit(item)"
            >
              <Edit3 :size="14" />
              <span>Edit</span>
            </button>

            <button
              class="btn btn-danger btn-sm"
              @click="dismissItem(item)"
            >
              <XCircle :size="14" />
              <span>Dismiss</span>
            </button>

            <div class="ml-auto flex items-center gap-2">
              <template v-if="item.match_reason === 'DUPLICATE_APPLICATION_FOUND'">
                <button
                  class="btn btn-secondary btn-sm"
                  title="Create as a new separate application in ASSESSMENT status"
                  @click="resolveAsNew(item)"
                >
                  <Sparkles :size="14" class="text-primary" />
                  <span>Create as New</span>
                </button>
                <button
                  class="btn btn-primary btn-sm"
                  title="Update existing application with this new event"
                  @click="resolveAsUpdate(item)"
                >
                  <CheckCircle2 :size="14" />
                  <span>Update Existing</span>
                </button>
              </template>
              <template v-else>
                <button
                  class="btn btn-primary btn-sm"
                  @click="resolveItem(item)"
                >
                  <CheckCircle2 :size="14" />
                  <span>Approve Match</span>
                </button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit & Approve Modal -->
    <div v-if="editingItem" class="modal-backdrop" @click.self="editingItem = null">
      <div class="modal-card animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">Edit & Approve Staging Item</h3>
          <button class="btn-close" @click="editingItem = null">×</button>
        </div>

        <div class="modal-body">
          <div class="input-group">
            <label class="input-label">Company Name *</label>
            <input v-model="editForm.company" type="text" class="form-input" required />
          </div>

          <div class="input-group">
            <label class="input-label">Position / Job Title *</label>
            <input v-model="editForm.position" type="text" class="form-input" required />
          </div>

          <div class="input-group">
            <label class="input-label">Application Status</label>
            <select v-model="editForm.status" class="form-input">
              <option value="ASSESSMENT">AI Assessment</option>
              <option value="APPLIED">Applied</option>
              <option value="ONLINE_ASSESSMENT">Online Assessment</option>
              <option value="TECHNICAL_INTERVIEW">Technical Interview</option>
              <option value="OFFER">Offer</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <div class="input-group checkbox-group mt-2">
            <label class="flex items-center gap-2 cursor-pointer text-xs text-secondary">
              <input v-model="editForm.create_new" type="checkbox" />
              <span>Create as a new separate Application record (bypass linking to existing)</span>
            </label>
          </div>

          <div class="modal-actions mt-4">
            <button class="btn btn-secondary" @click="editingItem = null">Cancel</button>
            <button
              class="btn btn-primary"
              @click="resolveItem(editingItem, editForm)"
            >
              Save & Commit Application
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.filter-pills {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 4px;
}

.pill-btn {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.pill-btn.active {
  background-color: var(--bg-elevated);
  color: var(--text-main);
}

.loading-state, .empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: var(--text-secondary);
  gap: 12px;
}

.empty-icon {
  color: var(--text-muted);
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.empty-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.staging-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.staging-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.company-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.match-score {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--status-interview-text);
  background-color: var(--status-interview-bg);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.role-title {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.email-details-box {
  background-color: var(--bg-input);
  border: 1px solid var(--border-subtle);
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
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.detail-body-snippet {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  max-height: 70px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.ml-auto {
  margin-left: auto;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 600;
  background-color: var(--bg-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 480px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  font-size: 15px;
  font-weight: 600;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.form-input {
  width: 100%;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.btn-close {
  font-size: 20px;
  color: var(--text-muted);
}
</style>
