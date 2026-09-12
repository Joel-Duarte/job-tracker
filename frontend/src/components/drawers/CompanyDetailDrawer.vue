<script setup>
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { useQueueStore } from '../../stores/queueStore'
import { CompaniesAPI } from '../../api/endpoints'
import CompanyLogo from '../common/CompanyLogo.vue'
import {
  X,
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
  Calendar,
  ChevronDown,
  Share2,
  Clock,
  Sparkles,
} from 'lucide-vue-next'
import CompanyIntelModal from '../modals/CompanyIntelModal.vue'
import { formatRelativeDate } from '../../utils/formatters'

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

// Intel export/import modal state
const isIntelModalOpen = ref(false)
const intelModalInitialTab = ref('export')

function openIntelModal(tab = 'export') {
  intelModalInitialTab.value = tab
  isIntelModalOpen.value = true
}

function onResearchImported(updatedCompany) {
  company.value = updatedCompany
  syncResearchState(updatedCompany.company_research)
  window.dispatchEvent(new CustomEvent('company:updated', { detail: updatedCompany }))
}

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

// Intel form states - 8 editable fields
const researchSummary = ref('')
const researchMissionAndCustomer = ref('')
const researchCulture = ref('')
const researchInitiatives = ref('')
const researchProducts = ref([])
const researchPriorities = ref([])
const researchLanguage = ref([])
const researchAlignmentAngles = ref([])

// Temporary input models for chips and lists
const newProductInput = ref('')
const newLanguageInput = ref('')
const newPriorityInput = ref('')
const newAlignmentAngleInput = ref('')

// Dropdown & revealed sections state
const isAddIntelDropdownOpen = ref(false)
const revealedSections = ref(new Set())
const addIntelDropdownRef = ref(null)

// Focus element refs
const summaryInputRef = ref(null)
const missionCustomerInputRef = ref(null)
const cultureInputRef = ref(null)
const initiativesInputRef = ref(null)
const productInputRef = ref(null)
const priorityInputRef = ref(null)
const languageInputRef = ref(null)
const alignmentAngleInputRef = ref(null)

const INTEL_FIELD_DEFS = [
  {
    key: 'summary',
    label: '+ Add Mission & Core Products',
    title: 'Mission & Core Products',
  },
  {
    key: 'company_mission_and_customer',
    label: '+ Add Customers & Problem Space',
    title: 'Customers & Problem Space',
  },
  {
    key: 'engineering_culture',
    label: '+ Add Engineering Culture',
    title: 'Engineering Culture & Tech Stack',
  },
  {
    key: 'recent_initiatives',
    label: '+ Add Recent Initiatives',
    title: 'Recent Initiatives & Milestones',
  },
  {
    key: 'products_and_technical_domain',
    label: '+ Add Products',
    title: 'Products & Technical Domains',
  },
  {
    key: 'strategic_priorities',
    label: '+ Add Strategic Priorities',
    title: 'Strategic Priorities',
  },
  {
    key: 'language_to_mirror',
    label: '+ Add Company Language',
    title: 'Company Language to Mirror',
  },
  {
    key: 'candidate_alignment_angles',
    label: '+ Add Alignment Guidance',
    title: 'Candidate Alignment Guidance',
  },
]

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
  { key: 'REJECTED', label: 'Rejected' },
  { key: 'ARCHIVED', label: 'Archived' },
]

function getAppDate(app) {
  return app?.latest_event_at || app?.applied_at || app?.created_at || null
}

const filteredCompanyApplications = computed(() => {
  const applications = [...(company.value?.applications || [])]
  const filtered = applications.filter((app) => {
    if (applicationFilter.value === 'all') return true
    if (applicationFilter.value === 'ASSESSMENT') {
      return app.is_assessment || app.status === 'ASSESSMENT'
    }
    if (applicationFilter.value === 'REJECTED') {
      return app.status === 'REJECTED' && !app.is_assessment
    }
    if (applicationFilter.value === 'ARCHIVED') {
      return app.status === 'ARCHIVED' && !app.is_assessment
    }
    return app.status === applicationFilter.value && !app.is_assessment
  })
  return filtered.sort((a, b) => {
    const dateA = new Date(getAppDate(a) || 0).getTime()
    const dateB = new Date(getAppDate(b) || 0).getTime()
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

const queueStore = useQueueStore()

const isResearchActive = computed(() => {
  if (isRefreshing.value) return true
  const st = (company.value?.research_status || '').toUpperCase()
  if (st === 'QUEUED' || st === 'IN_PROGRESS') return true

  // Also check if there is an active COMPANY_RESEARCH task in the AI queue for this company
  const compId = company.value?.id || selectedCompanyId.value
  if (compId && queueStore.activeTasks?.length) {
    const hasActiveTask = queueStore.activeTasks.some((t) => {
      if (t.task_type !== 'COMPANY_RESEARCH') return false
      const tid = t.result_json?.company_id || (t.raw_text ? Number(t.raw_text) : null)
      return String(tid) === String(compId)
    })
    if (hasActiveTask) return true
  }

  return false
})

const displayResearchStatus = computed(() => {
  if (isResearchActive.value && (!company.value?.research_status || company.value.research_status === 'NONE')) {
    return 'IN_PROGRESS'
  }
  return company.value?.research_status || 'NONE'
})

function normalizeText(val) {
  if (val == null) return ''
  if (Array.isArray(val)) {
    return val
      .map((item) => (typeof item === 'string' ? item.trim() : JSON.stringify(item)))
      .filter(Boolean)
      .join('\n')
  }
  if (typeof val === 'object') {
    return JSON.stringify(val, null, 2)
  }
  return String(val)
}

function normalizeList(val) {
  if (val == null) return []
  if (Array.isArray(val)) {
    return val
      .map((item) => (typeof item === 'string' ? item.trim() : String(item)))
      .filter(Boolean)
  }
  if (typeof val === 'string') {
    const trimmed = val.trim()
    return trimmed ? [trimmed] : []
  }
  return []
}

function hasIntelContent(key) {
  switch (key) {
    case 'summary':
      return Boolean(typeof researchSummary.value === 'string' ? researchSummary.value.trim() : normalizeText(researchSummary.value).trim())
    case 'company_mission_and_customer':
      return Boolean(typeof researchMissionAndCustomer.value === 'string' ? researchMissionAndCustomer.value.trim() : normalizeText(researchMissionAndCustomer.value).trim())
    case 'engineering_culture':
      return Boolean(typeof researchCulture.value === 'string' ? researchCulture.value.trim() : normalizeText(researchCulture.value).trim())
    case 'recent_initiatives':
      return Boolean(typeof researchInitiatives.value === 'string' ? researchInitiatives.value.trim() : normalizeText(researchInitiatives.value).trim())
    case 'products_and_technical_domain':
      return Array.isArray(researchProducts.value) && researchProducts.value.length > 0
    case 'strategic_priorities':
      return Array.isArray(researchPriorities.value) && researchPriorities.value.length > 0
    case 'language_to_mirror':
      return Array.isArray(researchLanguage.value) && researchLanguage.value.length > 0
    case 'candidate_alignment_angles':
      return Array.isArray(researchAlignmentAngles.value) && researchAlignmentAngles.value.length > 0
    default:
      return false
  }
}

function isSectionVisible(key) {
  return revealedSections.value.has(key) || hasIntelContent(key)
}

const availableIntelFields = computed(() => {
  return INTEL_FIELD_DEFS.filter((f) => !isSectionVisible(f.key))
})

const hasAnyVisibleIntelSection = computed(() => {
  return (
    INTEL_FIELD_DEFS.some((f) => isSectionVisible(f.key)) ||
    Boolean(company.value?.company_research?.verified_facts?.length) ||
    Boolean(company.value?.company_research?.employee_signals?.length) ||
    Boolean(company.value?.company_research?.sources?.length)
  )
})

function syncResearchState(cr) {
  const safeCr = cr && typeof cr === 'object' ? cr : {}
  researchSummary.value = normalizeText(safeCr.summary)
  researchMissionAndCustomer.value = normalizeText(safeCr.company_mission_and_customer)
  researchCulture.value = normalizeText(safeCr.engineering_culture)
  researchInitiatives.value = normalizeText(safeCr.recent_initiatives)
  researchProducts.value = normalizeList(safeCr.products_and_technical_domain)
  researchPriorities.value = normalizeList(safeCr.strategic_priorities)
  researchLanguage.value = normalizeList(safeCr.language_to_mirror)
  researchAlignmentAngles.value = normalizeList(safeCr.candidate_alignment_angles)

  const nextRevealed = new Set()
  INTEL_FIELD_DEFS.forEach((field) => {
    if (hasIntelContent(field.key)) {
      nextRevealed.add(field.key)
    }
  })
  revealedSections.value = nextRevealed
  isAddIntelDropdownOpen.value = false
}

async function addIntelField(key) {
  revealedSections.value.add(key)
  isAddIntelDropdownOpen.value = false
  await nextTick()
  if (key === 'summary' && summaryInputRef.value) {
    summaryInputRef.value.focus()
  } else if (key === 'company_mission_and_customer' && missionCustomerInputRef.value) {
    missionCustomerInputRef.value.focus()
  } else if (key === 'engineering_culture' && cultureInputRef.value) {
    cultureInputRef.value.focus()
  } else if (key === 'recent_initiatives' && initiativesInputRef.value) {
    initiativesInputRef.value.focus()
  } else if (key === 'products_and_technical_domain' && productInputRef.value) {
    productInputRef.value.focus()
  } else if (key === 'strategic_priorities' && priorityInputRef.value) {
    priorityInputRef.value.focus()
  } else if (key === 'language_to_mirror' && languageInputRef.value) {
    languageInputRef.value.focus()
  } else if (key === 'candidate_alignment_angles' && alignmentAngleInputRef.value) {
    alignmentAngleInputRef.value.focus()
  }
}

let drawerPollInterval = null

function checkAndStartDrawerPolling() {
  if (drawerPollInterval) return
  if (!selectedCompanyId.value || !isCompanyDrawerOpen.value || !isResearchActive.value) {
    return
  }

  drawerPollInterval = setInterval(async () => {
    if (!selectedCompanyId.value || !isCompanyDrawerOpen.value) {
      stopDrawerPolling()
      return
    }
    try {
      const res = await CompaniesAPI.get(selectedCompanyId.value)
      if (res.data) {
        const prevStatus = (company.value?.research_status || '').toUpperCase()
        const newStatus = (res.data.research_status || '').toUpperCase()

        company.value = res.data
        if (res.data.company_research) {
          syncResearchState(res.data.company_research)
        }
        window.dispatchEvent(new CustomEvent('company:updated', { detail: res.data }))

        // Check if research is no longer active
        if (!isResearchActive.value) {
          stopDrawerPolling()
          if (prevStatus === 'QUEUED' || prevStatus === 'IN_PROGRESS') {
            if (newStatus === 'COMPLETED') {
              uiStore.showToast(`Company intelligence updated for "${res.data.name}"!`, 'success')
            } else if (newStatus === 'FAILED') {
              uiStore.showToast(`Company intelligence research failed for "${res.data.name}".`, 'error')
            }
          }
        }
      }
    } catch (e) {
      // silent background poll
    }
  }, 2000)
}

function stopDrawerPolling() {
  if (drawerPollInterval) {
    clearInterval(drawerPollInterval)
    drawerPollInterval = null
  }
}

// Reactively start/stop drawer polling whenever the research status is active and drawer is open
watch(
  [isResearchActive, isCompanyDrawerOpen],
  ([isActive, isOpen]) => {
    if (isOpen && isActive) {
      checkAndStartDrawerPolling()
    } else if (!isOpen || !isActive) {
      stopDrawerPolling()
    }
  },
  { immediate: true }
)

watch(
  [selectedCompanyId, isCompanyDrawerOpen],
  async ([newId, isOpen], [oldId, oldOpen]) => {
    if (isOpen && newId) {
      activeTab.value = uiStore.companyDrawerInitialTab || 'intel'
      // If we switched to a different company, clear the old one first
      if (company.value && String(company.value.id) !== String(newId)) {
        company.value = null
      }
      await fetchCompany(newId)
      if (activeTab.value === 'merge') {
        await loadAllCompaniesForMerge()
      }
    } else if (!isOpen) {
      stopDrawerPolling()
      // Keep company.value around temporarily for smooth slide-out transition without resetting to null abruptly
      setTimeout(() => {
        if (!isCompanyDrawerOpen.value) {
          company.value = null
        }
      }, 300)
    }
  },
  { immediate: true }
)

async function fetchCompany(id) {
  // If we already have this company loaded, do a silent background reload to avoid layout jumping
  if (!company.value || String(company.value.id) !== String(id)) {
    isLoading.value = true
  }
  try {
    const res = await CompaniesAPI.get(id)
    company.value = res.data
    notes.value = res.data.notes || ''
    pros.value = [...(res.data.pros || [])]
    redFlags.value = [...(res.data.red_flags || [])]
    syncResearchState(res.data.company_research)

    // Broadcast updated company data so CompaniesView cards immediately reflect latest intel
    window.dispatchEvent(new CustomEvent('company:updated', { detail: res.data }))
    checkAndStartDrawerPolling()
  } catch (err) {
    console.error('Failed to load company details:', err)
    uiStore.showToast(err.response?.data?.detail || 'Failed to load company details', 'error')
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
  stopDrawerPolling()
  if (company.value) {
    window.dispatchEvent(new CustomEvent('company:updated', { detail: company.value }))
  }
  uiStore.closeCompanyDrawer()
}

async function deleteCompany() {
  if (!company.value || isDeletingCompany.value) return
  const companyId = company.value.id
  const hasApplications = (company.value.applications || []).length > 0
  const message = hasApplications
    ? `Delete ${company.value.name} and all ${company.value.applications.length} linked applications? This cannot be undone.`
    : `Delete ${company.value.name}? This cannot be undone.`
  if (!window.confirm(message)) return

  isDeletingCompany.value = true
  try {
    await CompaniesAPI.delete(companyId, hasApplications)
    uiStore.showToast('Company deleted', 'success')
    closeDrawer()

    // Dispatch global event for cross-view synchronization
    window.dispatchEvent(
      new CustomEvent('company:deleted', {
        detail: { companyId, deletedApplications: hasApplications }
      })
    )

    if (hasApplications) {
      appStore.removeApplicationsForCompany(companyId)
      appStore.fetchApplications(true)
    }
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to delete company', 'error')
  } finally {
    isDeletingCompany.value = false
  }
}

function onApplicationDeleted(event) {
  const deletedId = event.detail?.applicationId
  if (!deletedId || !company.value?.applications) return
  const prevLen = company.value.applications.length
  company.value.applications = company.value.applications.filter(
    (a) => String(a.id) !== String(deletedId)
  )
  if (company.value.applications.length !== prevLen) {
    company.value.applications_count = Math.max(0, (company.value.applications_count || 1) - 1)
    company.value.active_applications_count = (company.value.applications || []).filter((a) =>
      ['APPLIED', 'ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW', 'OFFER'].includes(a.status)
    ).length
  }
}

function onCompanyUpdated(event) {
  const updated = event?.detail?.company || event?.detail
  if (!updated || !company.value || String(updated.id) !== String(company.value.id)) return

  const prevStatus = (company.value?.research_status || '').toUpperCase()
  const newStatus = (updated.research_status || '').toUpperCase()

  company.value = {
    ...company.value,
    ...updated,
  }

  if (updated.notes !== undefined && !notes.value) {
    notes.value = updated.notes || ''
  }
  if (updated.pros && (!pros.value || pros.value.length === 0)) {
    pros.value = [...(updated.pros || [])]
  }
  if (updated.red_flags && (!redFlags.value || redFlags.value.length === 0)) {
    redFlags.value = [...(updated.red_flags || [])]
  }

  if (updated.company_research) {
    syncResearchState(updated.company_research)
  }

  if (prevStatus !== newStatus) {
    if (newStatus === 'QUEUED' || newStatus === 'IN_PROGRESS') {
      checkAndStartDrawerPolling()
    } else {
      stopDrawerPolling()
    }
  }
}

onMounted(() => {
  window.addEventListener('application:deleted', onApplicationDeleted)
  window.addEventListener('company:updated', onCompanyUpdated)
  document.addEventListener('click', handleDocumentClick)
})

onUnmounted(() => {
  stopDrawerPolling()
  window.removeEventListener('application:deleted', onApplicationDeleted)
  window.removeEventListener('company:updated', onCompanyUpdated)
  document.removeEventListener('click', handleDocumentClick)
})

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

function safeTrim(val) {
  if (val == null) return ''
  return typeof val === 'string' ? val.trim() : normalizeText(val).trim()
}

const drawerCompanyForIntel = computed(() => {
  if (!company.value) return null
  return {
    ...company.value,
    notes: notes.value,
    pros: [...pros.value],
    red_flags: [...redFlags.value],
    company_research: {
      ...(company.value.company_research || {}),
      summary: researchSummary.value ? safeTrim(researchSummary.value) : (company.value.company_research?.summary || ''),
      company_mission_and_customer: researchMissionAndCustomer.value ? safeTrim(researchMissionAndCustomer.value) : (company.value.company_research?.company_mission_and_customer || ''),
      engineering_culture: researchCulture.value ? safeTrim(researchCulture.value) : (company.value.company_research?.engineering_culture || ''),
      recent_initiatives: researchInitiatives.value ? safeTrim(researchInitiatives.value) : (company.value.company_research?.recent_initiatives || ''),
      products_and_technical_domain: (researchProducts.value && researchProducts.value.length > 0) ? normalizeList(researchProducts.value) : (company.value.company_research?.products_and_technical_domain || []),
      strategic_priorities: (researchPriorities.value && researchPriorities.value.length > 0) ? normalizeList(researchPriorities.value) : (company.value.company_research?.strategic_priorities || []),
      language_to_mirror: (researchLanguage.value && researchLanguage.value.length > 0) ? normalizeList(researchLanguage.value) : (company.value.company_research?.language_to_mirror || []),
      candidate_alignment_angles: (researchAlignmentAngles.value && researchAlignmentAngles.value.length > 0) ? normalizeList(researchAlignmentAngles.value) : (company.value.company_research?.candidate_alignment_angles || []),
      verified_facts: company.value.company_research?.verified_facts || [],
    },
  }
})

async function saveAllDetails() {
  if (!company.value) return
  isSaving.value = true
  try {
    const updatedResearch = {
      ...(company.value.company_research || {}),
      summary: safeTrim(researchSummary.value),
      company_mission_and_customer: safeTrim(researchMissionAndCustomer.value),
      engineering_culture: safeTrim(researchCulture.value),
      recent_initiatives: safeTrim(researchInitiatives.value),
      products_and_technical_domain: normalizeList(researchProducts.value),
      strategic_priorities: normalizeList(researchPriorities.value),
      language_to_mirror: normalizeList(researchLanguage.value),
      candidate_alignment_angles: normalizeList(researchAlignmentAngles.value),
    }

    const payload = {
      notes: notes.value,
      pros: pros.value,
      red_flags: redFlags.value,
      company_research: updatedResearch,
    }
    const res = await CompaniesAPI.update(company.value.id, payload)
    company.value = res.data
    syncResearchState(res.data.company_research)
    window.dispatchEvent(new CustomEvent('company:updated', { detail: res.data }))
    uiStore.showToast('Company saved successfully', 'success')
  } catch (err) {
    console.error('Failed to save company:', err)
    uiStore.showToast(err.response?.data?.detail || 'Failed to save company', 'error')
  } finally {
    isSaving.value = false
  }
}

async function handleRefreshResearch() {
  if (!company.value) return

  const hasExistingResearch = Boolean(
    hasIntelContent('summary') ||
    hasIntelContent('company_mission_and_customer') ||
    hasIntelContent('engineering_culture') ||
    hasIntelContent('recent_initiatives') ||
    hasIntelContent('products_and_technical_domain') ||
    hasIntelContent('strategic_priorities') ||
    hasIntelContent('language_to_mirror') ||
    hasIntelContent('candidate_alignment_angles') ||
    (company.value.company_research && Object.keys(company.value.company_research).length > 0)
  )

  if (hasExistingResearch) {
    const confirmed = window.confirm(
      "Refreshing will re-run web research and overwrite custom edits to this company's intelligence. Continue?"
    )
    if (!confirmed) return
  }

  isRefreshing.value = true
  try {
    const res = await CompaniesAPI.refreshResearch(company.value.id)
    const st = (res.data?.status || '').toUpperCase()
    if (res.data?.queued || st === 'QUEUED' || st === 'ALREADY_QUEUED') {
      company.value.research_status = 'QUEUED'
      window.dispatchEvent(new CustomEvent('company:updated', { detail: company.value }))
      checkAndStartDrawerPolling()
      uiStore.showToast(
        st === 'ALREADY_QUEUED'
          ? 'Company intelligence research is already running in AI queue'
          : 'Company intelligence research queued',
        'success'
      )
    } else if (res.data?.company_research) {
      company.value.company_research = res.data.company_research
      company.value.research_status = 'COMPLETED'
      syncResearchState(res.data.company_research)
      window.dispatchEvent(new CustomEvent('company:updated', { detail: company.value }))
      uiStore.showToast('Company intelligence refreshed from web!', 'success')
    } else {
      uiStore.showToast('No company web results found', 'info')
    }
  } catch (err) {
    console.error('Failed to refresh research:', err)
    uiStore.showToast(err.response?.data?.detail || 'Failed to refresh research', 'error')
  } finally {
    isRefreshing.value = false
  }
}

function addProduct() {
  const clean = newProductInput.value.trim()
  if (clean && !researchProducts.value.includes(clean)) {
    researchProducts.value.push(clean)
    newProductInput.value = ''
  }
}

function removeProduct(idx) {
  researchProducts.value.splice(idx, 1)
}

function addLanguage() {
  const clean = newLanguageInput.value.trim()
  if (clean && !researchLanguage.value.includes(clean)) {
    researchLanguage.value.push(clean)
    newLanguageInput.value = ''
  }
}

function removeLanguage(idx) {
  researchLanguage.value.splice(idx, 1)
}

function addPriority() {
  const clean = newPriorityInput.value.trim()
  if (clean && !researchPriorities.value.includes(clean)) {
    researchPriorities.value.push(clean)
    newPriorityInput.value = ''
  }
}

function removePriority(idx) {
  researchPriorities.value.splice(idx, 1)
}

function addAlignmentAngle() {
  const clean = newAlignmentAngleInput.value.trim()
  if (clean && !researchAlignmentAngles.value.includes(clean)) {
    researchAlignmentAngles.value.push(clean)
    newAlignmentAngleInput.value = ''
  }
}

function removeAlignmentAngle(idx) {
  researchAlignmentAngles.value.splice(idx, 1)
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

function getPositionTextColorClass(app) {
  if (!app) return 'status-text-default'
  if (app.is_assessment || app.status === 'ASSESSMENT') {
    return 'status-text-assessment'
  }
  switch (app.status) {
    case 'OFFER':
    case 'HIRED':
      return 'status-text-offer'
    case 'TECHNICAL_INTERVIEW':
    case 'ONLINE_ASSESSMENT':
      return 'status-text-interview'
    case 'REJECTED':
      return 'status-text-rejected'
    case 'APPLIED':
      return 'status-text-applied'
    case 'ARCHIVED':
    case 'WITHDRAWN':
      return 'status-text-archived'
    default:
      return 'status-text-default'
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

        <!-- Drawer Header Actions -->
        <div class="drawer-header-actions">
          <button
            v-if="company && !isEditingHeader"
            type="button"
            class="btn btn-secondary btn-xs btn-header-intel"
            title="Export Markdown dossier, generate AI prompts, or import JSON"
            @click="openIntelModal('export')"
          >
            <Share2 :size="12" />
            <span>Intel Hub</span>
          </button>
          <button
            type="button"
            class="drawer-header-close-btn"
            title="Close Drawer"
            @click="closeDrawer"
          >
            <X :size="16" />
          </button>
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
            <span :class="['research-status-badge', `research-status-${displayResearchStatus.toLowerCase()}`]">
              <Loader2 v-if="isResearchActive" :size="12" class="animate-spin mr-1" />
              {{ displayResearchStatus }}
            </span>
            <button
              class="btn btn-secondary btn-sm"
              :disabled="isResearchActive"
              @click="handleRefreshResearch"
            >
              <Loader2 v-if="isResearchActive" :size="12" class="animate-spin" />
              <RefreshCw v-else :size="12" />
              <span>{{ isResearchActive ? 'Researching...' : 'Refresh from Web' }}</span>
            </button>
          </div>

          <!-- Active Research Banner -->
          <div v-if="isResearchActive" class="research-active-banner">
            <div class="banner-top">
              <div class="banner-pulse-icon">
                <Sparkles :size="14" class="text-primary animate-pulse" />
              </div>
              <div class="banner-text">
                <span class="banner-title">Live Web Intelligence in Progress</span>
                <span class="banner-sub">Gathering verified facts, culture signals, and tech stack details...</span>
              </div>
            </div>
            <div class="research-progress-bar">
              <div class="research-progress-indeterminate"></div>
            </div>
          </div>

          <div v-if="displayResearchStatus === 'FAILED'" class="research-failed-callout">
            <AlertTriangle :size="15" />
            <span>Company intelligence research failed.</span>
            <button
              type="button"
              class="btn btn-secondary btn-xs"
              :disabled="isResearchActive"
              @click="handleRefreshResearch"
            >
              <RefreshCw :size="11" />
              <span>Retry</span>
            </button>
          </div>

          <!-- Active Research Skeleton (when no sections are populated yet) -->
          <div v-if="isResearchActive && !hasAnyVisibleIntelSection" class="research-skeleton-wrap mt-3">
            <div class="skeleton-card">
              <div class="skeleton-line skeleton-title"></div>
              <div class="skeleton-line skeleton-body"></div>
              <div class="skeleton-line skeleton-body short"></div>
            </div>
            <div class="skeleton-card">
              <div class="skeleton-line skeleton-title"></div>
              <div class="skeleton-line skeleton-body"></div>
            </div>
          </div>

          <!-- 1. Mission & Core Products (Textarea) -->
          <div v-if="isSectionVisible('summary')" class="form-group mt-3">
            <label class="form-label text-xs">Mission & Core Products</label>
            <textarea
              ref="summaryInputRef"
              v-model="researchSummary"
              rows="3"
              class="form-input form-input-sm"
              placeholder="What this company builds and its core values..."
            ></textarea>
          </div>

          <!-- 2. Customers & Problem Space (Textarea) -->
          <div v-if="isSectionVisible('company_mission_and_customer')" class="form-group mt-3">
            <label class="form-label text-xs">Customers & Problem Space</label>
            <textarea
              ref="missionCustomerInputRef"
              v-model="researchMissionAndCustomer"
              rows="3"
              class="form-input form-input-sm"
              placeholder="Who the company serves and what core problem it solves..."
            ></textarea>
          </div>

          <!-- 3. Engineering Culture & Tech Stack (Textarea) -->
          <div v-if="isSectionVisible('engineering_culture')" class="form-group mt-3">
            <label class="form-label text-xs">Engineering Culture & Tech Stack</label>
            <textarea
              ref="cultureInputRef"
              v-model="researchCulture"
              rows="3"
              class="form-input form-input-sm"
              placeholder="Engineering standards, remote culture, stack..."
            ></textarea>
          </div>

          <!-- 4. Recent Initiatives & Public Milestones (Textarea) -->
          <div v-if="isSectionVisible('recent_initiatives')" class="form-group mt-3">
            <label class="form-label text-xs">Recent Initiatives & Milestones</label>
            <textarea
              ref="initiativesInputRef"
              v-model="researchInitiatives"
              rows="3"
              class="form-input form-input-sm"
              placeholder="Recent product launches, open source, investments..."
            ></textarea>
          </div>

          <!-- 5. Products & Technical Domains (Editable Tag Chips) -->
          <div v-if="isSectionVisible('products_and_technical_domain')" class="research-detail-section">
            <label class="form-label text-xs">Products & Technical Domains</label>
            <div v-if="researchProducts.length" class="tag-chips-wrap">
              <span v-for="(domain, idx) in researchProducts" :key="idx" class="tag-chip tag-intel-chip">
                <span>{{ domain }}</span>
                <button
                  type="button"
                  class="chip-delete"
                  title="Remove product"
                  aria-label="Remove product"
                  @click="removeProduct(idx)"
                >
                  <X :size="11" />
                </button>
              </span>
            </div>
            <div class="tag-input-row mt-2">
              <input
                ref="productInputRef"
                v-model="newProductInput"
                type="text"
                class="form-input form-input-sm"
                placeholder="Add product or domain..."
                @keyup.enter="addProduct"
              />
              <button type="button" class="btn btn-secondary btn-sm" @click="addProduct">
                <Plus :size="13" />
                <span>Add</span>
              </button>
            </div>
          </div>

          <!-- 6. Strategic Priorities (Editable Bullet List) -->
          <div v-if="isSectionVisible('strategic_priorities')" class="research-detail-section">
            <label class="form-label text-xs">Strategic Priorities</label>
            <ul v-if="researchPriorities.length" class="editable-bullet-list">
              <li v-for="(priority, idx) in researchPriorities" :key="idx" class="bullet-list-item">
                <span class="bullet-item-text">{{ priority }}</span>
                <button
                  type="button"
                  class="bullet-item-delete"
                  title="Delete priority"
                  aria-label="Delete priority"
                  @click="removePriority(idx)"
                >
                  <Trash2 :size="12" />
                </button>
              </li>
            </ul>
            <div class="tag-input-row mt-2">
              <input
                ref="priorityInputRef"
                v-model="newPriorityInput"
                type="text"
                class="form-input form-input-sm"
                placeholder="Add strategic priority..."
                @keyup.enter="addPriority"
              />
              <button type="button" class="btn btn-secondary btn-sm" @click="addPriority">
                <Plus :size="13" />
                <span>Add item</span>
              </button>
            </div>
          </div>

          <!-- 7. Company Language to Mirror (Editable Tag Chips) -->
          <div v-if="isSectionVisible('language_to_mirror')" class="research-detail-section">
            <label class="form-label text-xs">Company Language to Mirror</label>
            <div v-if="researchLanguage.length" class="tag-chips-wrap">
              <span v-for="(phrase, idx) in researchLanguage" :key="idx" class="tag-chip tag-intel-chip">
                <span>{{ phrase }}</span>
                <button
                  type="button"
                  class="chip-delete"
                  title="Remove company language phrase"
                  aria-label="Remove company language phrase"
                  @click="removeLanguage(idx)"
                >
                  <X :size="11" />
                </button>
              </span>
            </div>
            <div class="tag-input-row mt-2">
              <input
                ref="languageInputRef"
                v-model="newLanguageInput"
                type="text"
                class="form-input form-input-sm"
                placeholder="Add term or phrase to mirror..."
                @keyup.enter="addLanguage"
              />
              <button type="button" class="btn btn-secondary btn-sm" @click="addLanguage">
                <Plus :size="13" />
                <span>Add</span>
              </button>
            </div>
          </div>

          <!-- 8. Candidate Alignment Guidance (Editable Bullet List) -->
          <div v-if="isSectionVisible('candidate_alignment_angles')" class="research-detail-section alignment-section">
            <label class="form-label text-xs">Candidate Alignment Guidance</label>
            <ul v-if="researchAlignmentAngles.length" class="editable-bullet-list">
              <li v-for="(angle, idx) in researchAlignmentAngles" :key="idx" class="bullet-list-item">
                <span class="bullet-item-text">{{ angle }}</span>
                <button
                  type="button"
                  class="bullet-item-delete"
                  title="Delete alignment angle"
                  aria-label="Delete alignment angle"
                  @click="removeAlignmentAngle(idx)"
                >
                  <Trash2 :size="12" />
                </button>
              </li>
            </ul>
            <div class="tag-input-row mt-2">
              <input
                ref="alignmentAngleInputRef"
                v-model="newAlignmentAngleInput"
                type="text"
                class="form-input form-input-sm"
                placeholder="Add alignment guidance talking point..."
                @keyup.enter="addAlignmentAngle"
              />
              <button type="button" class="btn btn-secondary btn-sm" @click="addAlignmentAngle">
                <Plus :size="13" />
                <span>Add item</span>
              </button>
            </div>
          </div>

          <!-- Read-Only Audit Trail: Verified Facts -->
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

          <!-- Read-Only Audit Trail: Private Interview Signals -->
          <div v-if="company.company_research?.employee_signals?.length" class="research-detail-section private-signals-section">
            <label class="form-label text-xs">Private Interview Signals</label>
            <ul class="research-list">
              <li v-for="signal in company.company_research.employee_signals" :key="signal.signal">{{ signal.signal }}</li>
            </ul>
          </div>

          <!-- Read-Only Audit Trail: Sources & References -->
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

          <!-- Empty State -->
          <div v-if="!hasAnyVisibleIntelSection && !isResearchActive" class="empty-intel-box mt-3">
            <p class="text-xs text-muted">No intelligence recorded for this company yet.</p>
          </div>

          <!-- Compact Drawer: "+ Add Intel Field" Dropdown Menu -->
          <div
            v-if="availableIntelFields.length"
            ref="addIntelDropdownRef"
            class="add-intel-dropdown-wrap mt-4"
          >
            <div class="add-intel-dropdown">
              <button
                type="button"
                class="btn btn-secondary btn-sm add-intel-btn"
                :aria-expanded="isAddIntelDropdownOpen"
                @click="isAddIntelDropdownOpen = !isAddIntelDropdownOpen"
              >
                <Plus :size="13" />
                <span>Add Intel Field</span>
                <ChevronDown :size="13" class="dropdown-chevron" :class="{ 'rotate-180': isAddIntelDropdownOpen }" />
              </button>

              <Transition name="dropdown-fade">
                <div v-if="isAddIntelDropdownOpen" class="intel-dropdown-menu">
                  <button
                    v-for="field in availableIntelFields"
                    :key="field.key"
                    type="button"
                    class="intel-dropdown-item"
                    @click="addIntelField(field.key)"
                  >
                    <Plus :size="12" class="item-icon" />
                    <span>{{ field.label }}</span>
                  </button>
                </div>
              </Transition>
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
                <span :class="['app-position', getPositionTextColorClass(app)]">
                  {{ app.position || 'Untitled application' }}
                </span>
                <span :class="['badge badge-sm', getStatusBadgeClass(app.status)]">
                  {{ app.is_assessment ? 'ASSESSMENT' : app.status }}
                </span>
              </div>
              <div class="app-card-meta">
                <div v-if="getAppDate(app)" class="app-card-date">
                  <Calendar :size="12" class="date-icon" />
                  <span>{{ formatRelativeDate(getAppDate(app)) }}</span>
                </div>
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
          type="button"
          class="btn btn-secondary btn-sm drawer-intel-action-btn"
          title="Export Markdown dossier, generate AI prompts, or import JSON"
          @click="openIntelModal('export')"
        >
          <Share2 :size="14" />
          <span>Intel Hub</span>
        </button>
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

  <!-- Company Intelligence Export/Import Modal -->
  <CompanyIntelModal
    v-model="isIntelModalOpen"
    :company="drawerCompanyForIntel || company"
    :initial-tab="intelModalInitialTab"
    @imported="onResearchImported"
  />
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

.app-position.status-text-applied {
  color: var(--status-applied-text);
}

.app-position.status-text-assessment {
  color: var(--status-assessment-text);
}

.app-position.status-text-interview {
  color: var(--status-interview-text);
}

.app-position.status-text-offer {
  color: var(--status-offer-text);
}

.app-position.status-text-rejected {
  color: var(--status-rejected-text);
}

.app-position.status-text-archived {
  color: var(--text-muted);
}

.app-position.status-text-default {
  color: var(--text-main);
}

.app-card-meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.app-card-date {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-muted);
}

.app-card-date .date-icon {
  opacity: 0.7;
}

.app-card-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
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

.tag-intel-chip {
  background: var(--bg-elevated, var(--bg-surface-hover));
  color: var(--text-main);
  border: 1px solid var(--border-color);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
}

.editable-bullet-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bullet-list-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  background: var(--bg-elevated, var(--bg-surface-hover));
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-secondary);
}

.bullet-item-text {
  flex: 1;
  word-break: break-word;
}

.bullet-item-delete {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: color var(--transition-fast, 0.15s ease);
}

.bullet-item-delete:hover {
  color: var(--text-danger, #f87171);
}

.add-intel-dropdown-wrap {
  position: relative;
  display: inline-block;
  margin-top: 16px;
}

.add-intel-dropdown {
  position: relative;
  display: inline-block;
}

.add-intel-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dropdown-chevron {
  transition: transform 0.2s ease;
}

.dropdown-chevron.rotate-180 {
  transform: rotate(180deg);
}

.intel-dropdown-menu {
  position: absolute;
  left: 0;
  bottom: calc(100% + 6px);
  z-index: 20;
  min-width: 250px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: var(--shadow-lg, 0 10px 25px -5px rgba(0, 0, 0, 0.3));
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.intel-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  background: transparent;
  border: none;
  border-radius: 5px;
  color: var(--text-main);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  transition: background var(--transition-fast, 0.15s ease);
}

.intel-dropdown-item:hover {
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.06));
}

.intel-dropdown-item .item-icon {
  color: var(--primary);
  flex-shrink: 0;
}

.empty-intel-box {
  padding: 16px;
  text-align: center;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  background: var(--bg-surface);
}

.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.drawer-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-header-intel {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.btn-header-intel:hover {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--primary);
}

.drawer-header-close-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-xs, 4px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast, 0.15s ease);
}

.drawer-header-close-btn:hover {
  color: var(--text-main);
  background-color: var(--bg-surface-hover);
  border-color: var(--border-subtle);
}

.drawer-intel-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: auto;
}

/* Active Research UI */
.research-active-banner {
  margin-top: 12px;
  margin-bottom: 8px;
  padding: 10px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--primary);
  border-radius: var(--radius-sm, 6px);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.banner-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.banner-pulse-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.banner-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.banner-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.research-progress-bar {
  width: 100%;
  height: 3px;
  background: var(--bg-card, rgba(255, 255, 255, 0.05));
  border-radius: 9999px;
  overflow: hidden;
  position: relative;
}

.research-progress-indeterminate {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  background: var(--primary);
  border-radius: 9999px;
  width: 40%;
  animation: research-slide 1.6s ease-in-out infinite;
}

@keyframes research-slide {
  0% {
    left: -40%;
    width: 40%;
  }
  50% {
    left: 40%;
    width: 60%;
  }
  100% {
    left: 100%;
    width: 40%;
  }
}

/* Skeleton Loading Cards */
.research-skeleton-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-card {
  padding: 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle, var(--border-color));
  border-radius: var(--radius-sm, 6px);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 12px;
  background: linear-gradient(
    90deg,
    var(--bg-elevated, rgba(255, 255, 255, 0.04)) 25%,
    var(--bg-surface-hover, rgba(255, 255, 255, 0.08)) 50%,
    var(--bg-elevated, rgba(255, 255, 255, 0.04)) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-pulse 1.8s ease-in-out infinite;
  border-radius: 4px;
}

.skeleton-title {
  width: 40%;
  height: 14px;
}

.skeleton-body {
  width: 100%;
}

.skeleton-body.short {
  width: 70%;
}

@keyframes skeleton-pulse {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
