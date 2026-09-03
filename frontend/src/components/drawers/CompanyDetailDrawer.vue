<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { CompaniesAPI } from '../../api/endpoints'
import CompanyLogo from '../common/CompanyLogo.vue'
import {
  X,
  Star,
  Globe,
  RefreshCw,
  ExternalLink,
  Briefcase,
  Edit3,
  Plus,
  Trash2,
  AlertTriangle,
  Check,
  Loader2,
  Building2,
  FileText,
  ThumbsUp,
  AlertOctagon,
  Search,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()
const { isCompanyDrawerOpen, selectedCompanyId } = storeToRefs(uiStore)

const company = ref(null)
const isLoading = ref(false)
const isSaving = ref(false)
const isRefreshing = ref(false)
const isMerging = ref(false)
const activeTab = ref('intel') // 'intel' | 'notes' | 'applications' | 'merge'
const applicationFilter = ref('all')

// Header edit state
const isEditingHeader = ref(false)
const isSavingHeader = ref(false)
const isDeletingCompany = ref(false)
const headerEditForm = ref({ name: '', domain: '', about_url: '' })

// Form states
const notes = ref('')
const pros = ref([])
const redFlags = ref([])
const newProInput = ref('')
const newRedFlagInput = ref('')
const researchSummary = ref('')
const researchCulture = ref('')
const researchInitiatives = ref('')

// Merge state
const allCompanies = ref([])
const selectedSourceIds = ref([])
const mergeSearchQuery = ref('')

const applicationFilters = [
  { key: 'all', label: 'All' },
  { key: 'ASSESSMENT', label: 'Assessments' },
  { key: 'APPLIED', label: 'Applied' },
  { key: 'TECHNICAL_INTERVIEW', label: 'Interview' },
  { key: 'OFFER', label: 'Offers' },
  { key: 'ARCHIVED', label: 'Archived' },
]

const filteredCompanyApplications = computed(() => {
  const applications = [...(company.value?.applications || [])]
  const filtered = applications.filter((app) => {
    if (applicationFilter.value === 'all') return true
    if (applicationFilter.value === 'ASSESSMENT') {
      return app.is_assessment || app.status === 'ASSESSMENT'
    }
    if (applicationFilter.value === 'ARCHIVED') {
      return app.status === 'ARCHIVED' && !app.is_assessment
    }
    return app.status === applicationFilter.value && !app.is_assessment
  })
  return filtered.sort((a, b) => {
    const dateA = new Date(a.latest_event_at || a.created_at || 0).getTime()
    const dateB = new Date(b.latest_event_at || b.created_at || 0).getTime()
    return dateB - dateA
  })
})

const filteredMergeCompanies = computed(() => {
  const query = mergeSearchQuery.value.trim().toLowerCase()
  if (!query) return allCompanies.value
  return allCompanies.value.filter((c) => {
    const nameMatch = c.name?.toLowerCase().includes(query)
    const domainMatch = c.domain?.toLowerCase().includes(query)
    return nameMatch || domainMatch
  })
})

watch(selectedCompanyId, async (newId) => {
  if (newId && isCompanyDrawerOpen.value) {
    activeTab.value = uiStore.companyDrawerInitialTab || 'intel'
    await fetchCompany(newId)
    if (activeTab.value === 'merge') {
      await loadAllCompaniesForMerge()
    }
  } else {
    company.value = null
  }
})

watch(isCompanyDrawerOpen, async (isOpen) => {
  if (isOpen && selectedCompanyId.value) {
    activeTab.value = uiStore.companyDrawerInitialTab || 'intel'
    await fetchCompany(selectedCompanyId.value)
    if (activeTab.value === 'merge') {
      await loadAllCompaniesForMerge()
    }
  }
})

async function fetchCompany(id) {
  isLoading.value = true
  try {
    const res = await CompaniesAPI.get(id)
    company.value = res.data
    notes.value = res.data.notes || ''
    pros.value = [...(res.data.pros || [])]
    redFlags.value = [...(res.data.red_flags || [])]
    researchSummary.value = res.data.company_research?.summary || ''
    researchCulture.value = res.data.company_research?.engineering_culture || ''
    researchInitiatives.value = res.data.company_research?.recent_initiatives || ''
  } catch (err) {
    uiStore.showToast('Failed to load company details', 'error')
    closeDrawer()
  } finally {
    isLoading.value = false
  }
}

function startEditHeader() {
  if (!company.value) return
  headerEditForm.value = {
    name: company.value.name || '',
    domain: company.value.domain || '',
    about_url: company.value.about_url || '',
  }
  isEditingHeader.value = true
}

function cancelEditHeader() {
  isEditingHeader.value = false
}

async function saveEditHeader() {
  if (!company.value) return
  const cleanName = headerEditForm.value.name.trim()
  if (!cleanName) {
    uiStore.showToast('Company name cannot be empty', 'warning')
    return
  }
  isSavingHeader.value = true
  try {
    const cleanDomain = headerEditForm.value.domain.trim().toLowerCase() || null
    const cleanAboutUrl = headerEditForm.value.about_url.trim() || null
    await saveQuickUpdate({ name: cleanName, domain: cleanDomain, about_url: cleanAboutUrl })
    isEditingHeader.value = false
  } finally {
    isSavingHeader.value = false
  }
}

async function loadAllCompaniesForMerge() {
  mergeSearchQuery.value = ''
  selectedSourceIds.value = []
  try {
    const res = await CompaniesAPI.list()
    allCompanies.value = res.data.filter((c) => c.id !== company.value?.id)
  } catch {
    allCompanies.value = []
  }
}

function toggleSourceCandidate(id) {
  const numId = Number(id)
  const idx = selectedSourceIds.value.indexOf(numId)
  if (idx > -1) {
    selectedSourceIds.value.splice(idx, 1)
  } else {
    selectedSourceIds.value.push(numId)
  }
}

function closeDrawer() {
  uiStore.closeCompanyDrawer()
}

async function deleteCompany() {
  if (!company.value || isDeletingCompany.value) return
  const hasApplications = (company.value.applications || []).length > 0
  const message = hasApplications
    ? `Delete ${company.value.name} and all ${company.value.applications.length} linked applications? This cannot be undone.`
    : `Delete ${company.value.name}? This cannot be undone.`
  if (!window.confirm(message)) return

  isDeletingCompany.value = true
  try {
    await CompaniesAPI.delete(company.value.id, hasApplications)
    window.dispatchEvent(new CustomEvent('company:deleted', { detail: { companyId: company.value.id } }))
    uiStore.showToast('Company deleted', 'success')
    closeDrawer()
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to delete company', 'error')
  } finally {
    isDeletingCompany.value = false
  }
}

async function saveQuickUpdate(payload) {
  if (!company.value) return
  try {
    const res = await CompaniesAPI.update(company.value.id, payload)
    company.value = res.data
    window.dispatchEvent(new CustomEvent('company:updated', { detail: res.data }))
    uiStore.showToast('Company updated', 'success')
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to update company', 'error')
  }
}

async function saveAllDetails() {
  if (!company.value) return
  isSaving.value = true
  try {
    const updatedResearch = {
      ...(company.value.company_research || {}),
      summary: researchSummary.value,
      engineering_culture: researchCulture.value,
      recent_initiatives: researchInitiatives.value,
    }

    const payload = {
      notes: notes.value,
      pros: pros.value,
      red_flags: redFlags.value,
      company_research: updatedResearch,
    }
    const res = await CompaniesAPI.update(company.value.id, payload)
    company.value = res.data
    window.dispatchEvent(new CustomEvent('company:updated', { detail: res.data }))
    uiStore.showToast('Company saved successfully', 'success')
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to save company', 'error')
  } finally {
    isSaving.value = false
  }
}

async function handleRefreshResearch() {
  if (!company.value) return
  isRefreshing.value = true
  try {
    const res = await CompaniesAPI.refreshResearch(company.value.id)
    if (res.data?.queued || res.data?.status?.toUpperCase() === 'QUEUED') {
      company.value.research_status = 'QUEUED'
      uiStore.showToast('Company intelligence research queued', 'success')
    } else if (res.data?.company_research) {
      company.value.company_research = res.data.company_research
      researchSummary.value = res.data.company_research.summary || ''
      researchCulture.value = res.data.company_research.engineering_culture || ''
      researchInitiatives.value = res.data.company_research.recent_initiatives || ''
      uiStore.showToast('Company intelligence refreshed from web!', 'success')
    } else {
      uiStore.showToast('No company web results found', 'info')
    }
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to refresh research', 'error')
  } finally {
    isRefreshing.value = false
  }
}

function addPro() {
  const clean = newProInput.value.trim()
  if (clean && !pros.value.includes(clean)) {
    pros.value.push(clean)
    newProInput.value = ''
  }
}

function removePro(idx) {
  pros.value.splice(idx, 1)
}

function addRedFlag() {
  const clean = newRedFlagInput.value.trim()
  if (clean && !redFlags.value.includes(clean)) {
    redFlags.value.push(clean)
    newRedFlagInput.value = ''
  }
}

function removeRedFlag(idx) {
  redFlags.value.splice(idx, 1)
}

function openApplication(appId) {
  closeDrawer()
  uiStore.openDetail(appId)
}

async function handleMerge() {
  if (!selectedSourceIds.value.length || !company.value) return
  const count = selectedSourceIds.value.length
  const confirmed = window.confirm(
    `Are you sure you want to merge ${count} duplicate company/companies into "${company.value.name}"? All applications from the selected duplicates will be reassigned to "${company.value.name}", and the duplicate records will be deleted.`
  )
  if (!confirmed) return

  isMerging.value = true
  try {
    const res = await CompaniesAPI.merge({
      target_company_id: company.value.id,
      source_company_ids: selectedSourceIds.value,
    })
    uiStore.showToast(res.data.message || 'Companies merged successfully', 'success')
    window.dispatchEvent(new CustomEvent('company:merged', { detail: res.data }))
    selectedSourceIds.value = []
    await fetchCompany(company.value.id)
    await loadAllCompaniesForMerge()
    await appStore.fetchApplications()
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Merge failed', 'error')
  } finally {
    isMerging.value = false
  }
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'ASSESSMENT':
      return 'badge-info'
    case 'OFFER':
    case 'HIRED':
      return 'badge-success'
    case 'TECHNICAL_INTERVIEW':
    case 'ONLINE_ASSESSMENT':
      return 'badge-warning'
    case 'REJECTED':
      return 'badge-danger'
    case 'ARCHIVED':
    case 'WITHDRAWN':
      return 'badge-neutral'
    default:
      return 'badge-primary'
  }
}
</script>

<template>
  <Transition name="fade">
    <div
      v-if="isCompanyDrawerOpen"
      class="drawer-backdrop"
      @click="closeDrawer"
      role="presentation"
    ></div>
  </Transition>

  <Transition name="slide">
    <div
      v-if="isCompanyDrawerOpen"
      class="company-drawer-panel"
      role="dialog"
      aria-modal="true"
      aria-label="Company Details"
    >
      <!-- Header -->
      <div class="drawer-header">
        <div v-if="!isEditingHeader" class="company-brand-row">
          <CompanyLogo
            :name="company?.name || ''"
            :domain="company?.domain || null"
            :size="40"
            class="header-logo"
          />
          <div class="company-title-info">
            <div class="title-with-edit">
              <h3 class="company-name">{{ company?.name || 'Company Profile' }}</h3>
              <button
                v-if="company"
                type="button"
                class="btn-edit-inline"
                title="Edit Company Name & Domain"
                @click="startEditHeader"
              >
                <Edit3 :size="13" />
              </button>
            </div>
            <div v-if="company?.domain" class="company-domain-link">
              <a
                :href="`https://${company.domain}`"
                target="_blank"
                rel="noopener noreferrer"
                class="domain-anchor"
              >
                <Globe :size="12" />
                <span>{{ company.domain }}</span>
                <ExternalLink :size="10" />
              </a>
            </div>
          </div>
        </div>

        <!-- Inline Editing Header Form -->
        <div v-else class="header-edit-form">
          <div class="edit-inputs-col">
            <input
              v-model="headerEditForm.name"
              type="text"
              placeholder="Company Name"
              class="edit-input-field edit-input-company"
              :disabled="isSavingHeader"
              @keyup.enter="saveEditHeader"
              @keyup.esc="cancelEditHeader"
              autofocus
            />
            <div class="input-with-icon">
              <Globe :size="13" class="input-globe-icon" />
              <input
                v-model="headerEditForm.domain"
                type="text"
                placeholder="Company Domain (e.g. stripe.com)"
                class="edit-input-field edit-input-domain"
                :disabled="isSavingHeader"
                @keyup.enter="saveEditHeader"
                @keyup.esc="cancelEditHeader"
              />
            </div>
            <div class="input-with-icon">
              <Globe :size="13" class="input-globe-icon" />
              <input
                v-model="headerEditForm.about_url"
                type="url"
                placeholder="About URL (optional)"
                class="edit-input-field edit-input-domain"
                :disabled="isSavingHeader"
                @keyup.enter="saveEditHeader"
                @keyup.esc="cancelEditHeader"
              />
            </div>
          </div>
          <div class="edit-actions-row">
            <button
              class="btn btn-primary btn-xs"
              :disabled="isSavingHeader"
              title="Save changes"
              @click="saveEditHeader"
            >
              <Loader2 v-if="isSavingHeader" class="animate-spin" :size="12" />
              <Check v-else :size="12" />
              <span>Save</span>
            </button>
            <button
              class="btn btn-secondary btn-xs"
              :disabled="isSavingHeader"
              title="Cancel"
              @click="cancelEditHeader"
            >
              <X :size="12" />
              <span>Cancel</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="drawer-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'intel' }"
          @click="activeTab = 'intel'"
        >
          <Globe :size="14" />
          <span>Intelligence</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'notes' }"
          @click="activeTab = 'notes'"
        >
          <Edit3 :size="14" />
          <span>Notes & Tags</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'applications' }"
          @click="activeTab = 'applications'"
        >
          <Briefcase :size="14" />
          <span>Applications ({{ company?.applications_count || 0 }})</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'merge' }"
          @click="() => { activeTab = 'merge'; loadAllCompaniesForMerge(); }"
        >
          <Building2 :size="14" />
          <span>Merge</span>
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="drawer-loading">
        <Loader2 :size="28" class="animate-spin text-primary" />
        <p class="text-xs text-muted mt-2">Loading company intelligence...</p>
      </div>

      <!-- Body Content -->
      <div v-else-if="company" class="drawer-body">
        <!-- Tab 1: Intelligence -->
        <div v-if="activeTab === 'intel'" class="tab-pane">
          <div class="intel-header-row">
            <h4 class="pane-title">Company Intelligence</h4>
            <span :class="['research-status-badge', `research-status-${(company.research_status || 'NONE').toLowerCase()}`]">
              {{ company.research_status || 'NONE' }}
            </span>
            <button
              class="btn btn-secondary btn-sm"
              :disabled="isRefreshing"
              @click="handleRefreshResearch"
            >
              <Loader2 v-if="isRefreshing" :size="12" class="animate-spin" />
              <RefreshCw v-else :size="12" />
              <span>{{ isRefreshing ? 'Searching...' : 'Refresh from Web' }}</span>
            </button>
          </div>

          <div v-if="company.research_status === 'FAILED'" class="research-failed-callout">
            <AlertTriangle :size="15" />
            <span>Company intelligence research failed.</span>
            <button
              type="button"
              class="btn btn-secondary btn-xs"
              :disabled="isRefreshing"
              @click="handleRefreshResearch"
            >
              <RefreshCw :size="11" />
              <span>Retry</span>
            </button>
          </div>

          <div v-if="company.company_research?.public_rating_snippet" class="public-score-badge">
            <Star :size="13" class="text-warning" />
            <span>{{ company.company_research.public_rating_snippet }}</span>
          </div>

          <div class="form-group mt-3">
            <label class="form-label text-xs">Mission & Core Products</label>
            <textarea
              v-model="researchSummary"
              rows="3"
              class="form-input form-input-sm"
              placeholder="What this company builds and its core values..."
            ></textarea>
          </div>

          <div v-if="company.company_research?.company_mission_and_customer" class="research-detail-section">
            <label class="form-label text-xs">Customers & Problem Space</label>
            <p class="research-detail-copy">{{ company.company_research.company_mission_and_customer }}</p>
          </div>

          <div class="form-group mt-3">
            <label class="form-label text-xs">Engineering Culture & Tech Stack</label>
            <textarea
              v-model="researchCulture"
              rows="3"
              class="form-input form-input-sm"
              placeholder="Engineering standards, remote culture, stack..."
            ></textarea>
          </div>

          <div class="form-group mt-3">
            <label class="form-label text-xs">Recent Initiatives & Public Milestones</label>
            <input
              v-model="researchInitiatives"
              type="text"
              class="form-input form-input-sm"
              placeholder="Recent product launches, open source, investments..."
            />
          </div>

          <div v-if="company.company_research?.products_and_technical_domain?.length" class="research-detail-section">
            <label class="form-label text-xs">Products & Technical Domains</label>
            <div class="research-chip-list">
              <span v-for="domain in company.company_research.products_and_technical_domain" :key="domain" class="research-chip">
                {{ domain }}
              </span>
            </div>
          </div>

          <div v-if="company.company_research?.strategic_priorities?.length" class="research-detail-section">
            <label class="form-label text-xs">Strategic Priorities</label>
            <ul class="research-list">
              <li v-for="priority in company.company_research.strategic_priorities" :key="priority">{{ priority }}</li>
            </ul>
          </div>

          <div v-if="company.company_research?.language_to_mirror?.length" class="research-detail-section">
            <label class="form-label text-xs">Company Language</label>
            <div class="research-chip-list">
              <span v-for="phrase in company.company_research.language_to_mirror" :key="phrase" class="research-chip">
                {{ phrase }}
              </span>
            </div>
          </div>

          <div v-if="company.company_research?.candidate_alignment_angles?.length" class="research-detail-section alignment-section">
            <label class="form-label text-xs">Candidate Alignment Guidance</label>
            <ul class="research-list">
              <li v-for="angle in company.company_research.candidate_alignment_angles" :key="angle">{{ angle }}</li>
            </ul>
          </div>

          <div v-if="company.company_research?.verified_facts?.length" class="research-detail-section">
            <label class="form-label text-xs">Verified Facts</label>
            <ul class="research-list">
              <li v-for="fact in company.company_research.verified_facts" :key="fact.fact">
                {{ fact.fact }}
                <span v-if="fact.confidence" class="research-confidence">{{ fact.confidence }} confidence</span>
                <a
                  v-if="fact.source_url"
                  :href="fact.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="fact-source-link"
                  title="Open fact source"
                  @click.stop
                >
                  <ExternalLink :size="10" />
                </a>
              </li>
            </ul>
          </div>

          <div v-if="company.company_research?.employee_signals?.length" class="research-detail-section private-signals-section">
            <label class="form-label text-xs">Private Interview Signals</label>
            <ul class="research-list">
              <li v-for="signal in company.company_research.employee_signals" :key="signal.signal">{{ signal.signal }}</li>
            </ul>
          </div>

          <div v-if="company.company_research?.sources?.length" class="sources-box mt-3">
            <label class="form-label text-xs">Sources & References</label>
            <div class="sources-list">
              <a
                v-for="(src, idx) in company.company_research.sources"
                :key="idx"
                :href="src"
                target="_blank"
                rel="noopener noreferrer"
                class="source-chip"
              >
                <ExternalLink :size="11" />
                <span>{{ src }}</span>
              </a>
            </div>
          </div>
        </div>

        <!-- Tab 2: Notes & Tags -->
        <div v-else-if="activeTab === 'notes'" class="tab-pane">
          <div class="form-group">
            <label class="form-label text-xs">Private Candidate Notes</label>
            <textarea
              v-model="notes"
              rows="4"
              class="form-input form-input-sm"
              placeholder="Private notes (e.g. compensation ranges, interviewer impressions, referral contacts)..."
            ></textarea>
          </div>

          <!-- Pros Section -->
          <div class="tag-section mt-4">
            <div class="tag-section-header">
              <ThumbsUp :size="14" class="text-success" />
              <span class="tag-section-title">Pros & Advantages</span>
            </div>
            <div class="tag-chips-wrap">
              <span v-for="(pro, idx) in pros" :key="idx" class="tag-chip tag-pro">
                <span>{{ pro }}</span>
                <button type="button" class="chip-delete" @click="removePro(idx)">
                  <X :size="11" />
                </button>
              </span>
            </div>
            <div class="tag-input-row mt-2">
              <input
                v-model="newProInput"
                type="text"
                class="form-input form-input-sm"
                placeholder="Add pro (e.g. 100% Remote, Great Equity)..."
                @keyup.enter="addPro"
              />
              <button class="btn btn-secondary btn-sm" @click="addPro">
                <Plus :size="13" />
                <span>Add</span>
              </button>
            </div>
          </div>

          <!-- Red Flags Section -->
          <div class="tag-section mt-4">
            <div class="tag-section-header">
              <AlertOctagon :size="14" class="text-danger" />
              <span class="tag-section-title">Red Flags & Concerns</span>
            </div>
            <div class="tag-chips-wrap">
              <span v-for="(flag, idx) in redFlags" :key="idx" class="tag-chip tag-red-flag">
                <span>{{ flag }}</span>
                <button type="button" class="chip-delete" @click="removeRedFlag(idx)">
                  <X :size="11" />
                </button>
              </span>
            </div>
            <div class="tag-input-row mt-2">
              <input
                v-model="newRedFlagInput"
                type="text"
                class="form-input form-input-sm"
                placeholder="Add concern (e.g. 5 days in office, Low 401k match)..."
                @keyup.enter="addRedFlag"
              />
              <button class="btn btn-secondary btn-sm" @click="addRedFlag">
                <Plus :size="13" />
                <span>Add</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Tab 3: Applications History -->
        <div v-else-if="activeTab === 'applications'" class="tab-pane">
          <h4 class="pane-title">Application History</h4>
          <p class="text-xs text-muted mb-3">
            All roles and interviews tracked at {{ company.name }}.
          </p>

          <div class="application-filter-tabs" role="tablist" aria-label="Filter company applications">
            <button
              v-for="filter in applicationFilters"
              :key="filter.key"
              type="button"
              class="application-filter-tab"
              :class="{ active: applicationFilter === filter.key }"
              @click="applicationFilter = filter.key"
            >
              {{ filter.label }}
            </button>
          </div>

          <div v-if="!filteredCompanyApplications.length" class="empty-applications">
            <Briefcase :size="24" class="text-muted" />
            <p class="text-xs text-muted mt-1">No applications in this category.</p>
          </div>

          <div v-else class="applications-history-list">
            <div
              v-for="app in filteredCompanyApplications"
              :key="app.id"
              class="app-history-card"
              @click="openApplication(app.id)"
            >
              <div class="app-card-top">
                <span class="app-position">{{ app.position || 'Untitled application' }}</span>
                <span :class="['badge badge-sm', getStatusBadgeClass(app.status)]">
                  {{ app.is_assessment ? 'ASSESSMENT' : app.status }}
                </span>
              </div>
              <div class="app-card-meta">
                <div class="app-card-actions">
                  <span class="view-app-link">View in Drawer →</span>
                  <a
                    v-if="app.job_url"
                    :href="app.job_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="app-url-link"
                    title="Open application URL"
                    @click.stop
                  >
                    <ExternalLink :size="12" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 4: Merge Duplicate -->
        <div v-else-if="activeTab === 'merge'" class="tab-pane">
          <div class="merge-alert">
            <AlertTriangle :size="18" class="text-warning" />
            <div>
              <h5 class="merge-alert-title">Merge Duplicates into {{ company.name }}</h5>
              <p class="merge-alert-desc">
                Select one or more duplicate company records to merge into <strong>{{ company.name }}</strong>. All applications will be safely reassigned to this profile, and the duplicate records will be permanently deleted.
              </p>
            </div>
          </div>

          <div class="merge-search-section mt-4">
            <div class="merge-section-header">
              <label class="section-label">Select Duplicates to Merge ({{ selectedSourceIds.length }} selected)</label>
              <button
                v-if="selectedSourceIds.length"
                type="button"
                class="btn-clear-selection"
                @click="selectedSourceIds = []"
              >
                Deselect All
              </button>
            </div>
            <div class="input-with-icon">
              <Search :size="14" class="search-input-icon" />
              <input
                v-model="mergeSearchQuery"
                type="text"
                class="form-input form-input-sm search-company-input"
                placeholder="Filter duplicates by name or domain..."
              />
            </div>

            <!-- Filtered Candidates Cards List -->
            <div class="merge-candidates-wrap mt-3">
              <div v-if="!filteredMergeCompanies.length" class="empty-candidates-box">
                <p class="text-xs text-muted">No matching company records found.</p>
              </div>
              <div v-else class="merge-candidates-list">
                <div
                  v-for="c in filteredMergeCompanies"
                  :key="c.id"
                  class="merge-candidate-card"
                  :class="{ selected: selectedSourceIds.includes(c.id) }"
                  @click="toggleSourceCandidate(c.id)"
                >
                  <div class="candidate-radio-col">
                    <div class="custom-checkbox-square" :class="{ checked: selectedSourceIds.includes(c.id) }">
                      <Check v-if="selectedSourceIds.includes(c.id)" :size="11" class="check-icon" />
                    </div>
                  </div>
                  <CompanyLogo
                    :name="c.name"
                    :domain="c.domain"
                    :size="28"
                    class="candidate-logo"
                  />
                  <div class="candidate-info-col">
                    <span class="candidate-name">{{ c.name }}</span>
                    <span class="candidate-domain text-xs text-muted">{{ c.domain || 'no domain' }}</span>
                  </div>
                  <div class="candidate-apps-col">
                    <span class="badge badge-sm badge-neutral">
                      {{ c.applications_count || 0 }} apps
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-4">
            <button
              class="btn btn-primary btn-sm"
              :disabled="!selectedSourceIds.length || isMerging"
              @click="handleMerge"
            >
              <Loader2 v-if="isMerging" :size="14" class="animate-spin" />
              <Building2 v-else :size="14" />
              <span>{{ selectedSourceIds.length ? `Merge ${selectedSourceIds.length} into ${company.name}` : 'Select Duplicates to Merge' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Drawer Footer -->
      <div v-if="company && activeTab !== 'merge'" class="drawer-footer">
        <button
          class="btn btn-danger btn-sm drawer-delete-company"
          :disabled="isDeletingCompany || isSaving"
          @click="deleteCompany"
        >
          <Loader2 v-if="isDeletingCompany" :size="14" class="animate-spin" />
          <Trash2 v-else :size="14" />
          <span>Delete Company</span>
        </button>
        <button class="btn btn-secondary btn-sm" @click="closeDrawer">
          Cancel
        </button>
        <button
          class="btn btn-primary btn-sm"
          :disabled="isSaving"
          @click="saveAllDetails"
        >
          <Loader2 v-if="isSaving" :size="14" class="animate-spin" />
          <Check v-else :size="14" />
          <span>Save Changes</span>
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(2px);
  z-index: 1000;
}

.company-drawer-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 680px;
  max-width: 100vw;
  background: var(--bg-surface);
  border-left: 1px solid var(--card-border, var(--border-color));
  box-shadow: var(--shadow-xl, -8px 0 32px rgba(0, 0, 0, 0.4));
  z-index: 1001;
  display: flex;
  flex-direction: column;
}

.drawer-header {
  padding: 16px 20px;
  background-color: var(--bg-surface);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
}

.company-brand-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-with-edit {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-edit-inline {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 3px 5px;
  border-radius: var(--radius-xs, 4px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast, 0.15s ease);
  opacity: 0.7;
}

.btn-edit-inline:hover {
  opacity: 1;
  color: var(--primary);
  background-color: var(--primary-light, rgba(99, 102, 241, 0.12));
  border-color: var(--primary);
}

.header-edit-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  max-width: 360px;
}

.edit-inputs-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.edit-input-field {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xs, 4px);
  padding: 4px 8px;
  font-size: 13px;
  color: var(--text-main);
  outline: none;
  transition: border-color var(--transition-fast, 0.15s ease);
  width: 100%;
  min-height: 30px;
  box-sizing: border-box;
}

textarea.form-input,
textarea.edit-input-field {
  resize: vertical;
  min-height: 76px;
}

.form-input,
.form-select {
  box-sizing: border-box;
}

.edit-input-field:focus {
  border-color: var(--primary);
}

.edit-input-company {
  font-weight: 700;
  font-size: 15px;
}

.edit-input-domain {
  padding-left: 28px;
  font-size: 12px;
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.input-globe-icon,
.search-input-icon {
  position: absolute;
  left: 8px;
  color: var(--text-muted);
  pointer-events: none;
}

.search-company-input {
  padding-left: 28px;
}

.edit-actions-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.btn-xs {
  padding: 3px 8px;
  font-size: 11px;
  gap: 4px;
}

.merge-candidates-wrap {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-surface);
  max-height: 240px;
  overflow-y: auto;
}

.empty-candidates-box {
  padding: 16px;
  text-align: center;
}

.merge-candidates-list {
  display: flex;
  flex-direction: column;
}

.merge-candidate-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.merge-candidate-card:last-child {
  border-bottom: none;
}

.merge-candidate-card:hover {
  background-color: var(--bg-card-hover, var(--bg-card));
}

.merge-candidate-card.selected {
  background-color: var(--primary-light, rgba(99, 102, 241, 0.12));
  border-left: 3px solid var(--primary);
}

.candidate-radio-col {
  display: flex;
  align-items: center;
}

.custom-checkbox-square {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1.5px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast, 0.15s ease);
  background: var(--bg-surface);
}

.custom-checkbox-square.checked {
  border-color: var(--primary);
  background-color: var(--primary);
  color: #ffffff;
}

.custom-checkbox-square .check-icon {
  color: #ffffff;
}

.merge-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.btn-clear-selection {
  background: transparent;
  border: none;
  font-size: 11px;
  color: var(--primary);
  cursor: pointer;
  padding: 0;
}

.btn-clear-selection:hover {
  text-decoration: underline;
}

.merge-alert-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 2px 0;
}

.merge-alert-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
  margin: 0;
}

.candidate-info-col {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.candidate-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.candidate-domain {
  font-size: 11px;
}

.candidate-apps-col {
  display: flex;
  align-items: center;
}

.company-name {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 18px;
  color: var(--text-main);
  margin: 0;
  line-height: 1.2;
}

.domain-anchor {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--primary);
  text-decoration: none;
}

.domain-anchor:hover {
  text-decoration: underline;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-main);
}

.drawer-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-sidebar);
  padding: 0 16px;
  gap: 6px;
}

.tab-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 8px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
  min-height: 48px;
}

.tab-btn:hover {
  color: var(--text-main);
}

.tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.drawer-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.pane-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 4px 0;
}

.intel-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.intel-header-row .pane-title {
  flex: 1;
  margin: 0;
}

.intel-header-row .btn {
  height: 32px;
  padding-top: 0;
  padding-bottom: 0;
  font-size: 12px;
}

.research-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  height: 32px;
  box-sizing: border-box;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.research-status-completed {
  color: var(--text-success, #4ade80);
  background: var(--status-success-bg, rgba(34, 197, 94, 0.12));
}

.research-status-failed {
  color: var(--text-danger, #f87171);
  background: var(--status-rejected-bg, rgba(239, 68, 68, 0.12));
}

.research-status-queued,
.research-status-in_progress {
  color: var(--text-warning, #fbbf24);
  background: var(--status-warning-bg, rgba(245, 158, 11, 0.12));
}

.research-failed-callout {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 12px;
  color: var(--text-danger, #f87171);
  background: var(--status-rejected-bg, rgba(239, 68, 68, 0.12));
  border: 1px solid var(--status-rejected-border, rgba(239, 68, 68, 0.2));
  border-radius: 6px;
  font-size: 12px;
}

.research-failed-callout span {
  flex: 1;
}

.public-score-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--status-warning-bg, rgba(245, 158, 11, 0.1));
  border: 1px solid var(--status-warning-border, rgba(245, 158, 11, 0.2));
  color: var(--text-warning, #fbbf24);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 8px;
}

.research-detail-section {
  margin-top: 16px;
}

.research-detail-copy {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.research-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.research-chip {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  color: var(--text-secondary);
  background: var(--bg-elevated, var(--bg-surface-hover));
  font-size: 11px;
}

.research-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.research-confidence {
  color: var(--text-muted);
  font-size: 10px;
  text-transform: uppercase;
}

.fact-source-link {
  display: inline-flex;
  margin-left: 5px;
  color: var(--primary);
  vertical-align: middle;
}

.fact-source-link:hover {
  color: var(--text-main);
}

.alignment-section {
  padding: 10px;
  border-left: 3px solid var(--primary);
  background: var(--primary-light, rgba(99, 102, 241, 0.08));
}

.private-signals-section {
  padding: 10px;
  border-left: 3px solid var(--status-warning-border, rgba(245, 158, 11, 0.4));
  background: var(--status-warning-bg, rgba(245, 158, 11, 0.08));
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.source-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--primary);
  background: var(--primary-light, rgba(99, 102, 241, 0.1));
  padding: 3px 8px;
  border-radius: 4px;
  text-decoration: none;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-chip:hover {
  text-decoration: underline;
}

.tag-section-header,
.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.tag-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
}

.tag-pro {
  background: var(--status-success-bg, rgba(34, 197, 94, 0.12));
  color: var(--text-success, #4ade80);
  border: 1px solid var(--status-success-border, rgba(34, 197, 94, 0.2));
}

.tag-red-flag {
  background: var(--status-rejected-bg, rgba(239, 68, 68, 0.12));
  color: var(--text-danger, #f87171);
  border: 1px solid var(--status-rejected-border, rgba(239, 68, 68, 0.2));
}

.chip-delete {
  background: transparent;
  border: none;
  color: currentColor;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  opacity: 0.7;
}

.chip-delete:hover {
  opacity: 1;
}

.tag-input-row {
  display: flex;
  gap: 8px;
}

.applications-history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.application-filter-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.application-filter-tab {
  padding: 5px 9px;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}

.application-filter-tab:hover,
.application-filter-tab.active {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-light, rgba(99, 102, 241, 0.1));
}

.app-history-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.app-history-card:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
}

.app-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-position {
  font-weight: 600;
  color: var(--text-main);
  font-size: 14px;
}

.app-card-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.app-card-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.app-url-link {
  display: inline-flex;
  align-items: center;
  color: var(--primary);
}

.app-url-link:hover {
  color: var(--text-main);
}

.view-app-link {
  font-size: 12px;
  color: var(--primary);
}

.empty-applications {
  text-align: center;
  padding: 40px 20px;
}

.merge-alert {
  display: flex;
  gap: 12px;
  background: var(--status-warning-bg, rgba(245, 158, 11, 0.08));
  border: 1px solid var(--status-warning-border, rgba(245, 158, 11, 0.2));
  border-radius: 8px;
  padding: 14px;
}

.drawer-footer {
  padding: 14px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.drawer-delete-company {
  margin-right: auto;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
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
