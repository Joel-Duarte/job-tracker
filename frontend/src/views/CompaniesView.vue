<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { CompaniesAPI } from '../api/endpoints'
import CompanyLogo from '../components/common/CompanyLogo.vue'
import {
  Building2,
  Search,
  Star,
  Globe,
  Briefcase,
  ExternalLink,
  ThumbsUp,
  AlertOctagon,
  SlidersHorizontal,
  Loader2,
  ChevronRight,
  TrendingUp,
  CheckCircle2,
  Sparkles,
  X,
  Copy,
  GitMerge,
  TriangleAlert,
  RefreshCw,
} from 'lucide-vue-next'

const uiStore = useUIStore()

const companies = ref([])
const isLoading = ref(true)
const searchQuery = ref('')
const sortBy = ref('applications') // 'applications' | 'name' | 'recent'
const filterWithoutInfo = ref(false)

// Duplicate Detection State
const duplicateData = ref({
  total_clusters: 0,
  total_duplicate_companies: 0,
  duplicate_company_ids: [],
  clusters: [],
})
const filterDuplicatesOnly = ref(false)

// Bulk Researching State
const isResearchingBulk = ref(false)
const bulkProgressTotal = ref(0)
const bulkProgressCompleted = ref(0)
const lastFetchedAt = ref(null)
const isStale = ref(false)
const COMPANY_CACHE_KEY = 'jobtracker_companies_cache'
const COMPANY_CACHE_TTL_MS = 5 * 60 * 1000
let pollInterval = null

/** Returns average of all numeric scores across a company's profile_links, or null. */
function computeAvgRating(company) {
  const links = company.company_research?.profile_links || []
  const scores = links
    .map((l) => parseFloat(l.score))
    .filter((s) => !isNaN(s) && s > 0)
  if (!scores.length) return null
  return Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
}

const companiesWithoutInfo = computed(() =>
  companies.value.filter((c) => !c.company_research || !c.company_research.summary)
)

onMounted(async () => {
  hydrateCompanyCache()
  await fetchCompanies()
  window.addEventListener('company:updated', refreshCompaniesFromEvent)
  window.addEventListener('company:merged', refreshCompaniesFromEvent)
  window.addEventListener('company:deleted', refreshCompaniesFromEvent)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
  window.removeEventListener('company:updated', refreshCompaniesFromEvent)
  window.removeEventListener('company:merged', refreshCompaniesFromEvent)
  window.removeEventListener('company:deleted', refreshCompaniesFromEvent)
})

async function fetchCompanies() {
  if (
    !isStale.value &&
    lastFetchedAt.value !== null &&
    Date.now() - lastFetchedAt.value < COMPANY_CACHE_TTL_MS
  ) {
    isLoading.value = false
    return
  }

  isLoading.value = true
  try {
    const [res, dupRes] = await Promise.allSettled([
      CompaniesAPI.list(),
      CompaniesAPI.getDuplicates(),
    ])
    if (res.status === 'fulfilled') {
      companies.value = res.value.data || []
    }
    if (dupRes.status === 'fulfilled') {
      duplicateData.value = dupRes.value.data || {
        total_clusters: 0,
        total_duplicate_companies: 0,
        duplicate_company_ids: [],
        clusters: [],
      }
    }
    lastFetchedAt.value = Date.now()
    isStale.value = false
    persistCompanyCache()
  } catch (err) {
    uiStore.showToast('Failed to load companies directory', 'error')
  } finally {
    isLoading.value = false
  }
}

async function fetchCompaniesSilently() {
  try {
    const [res, dupRes] = await Promise.allSettled([
      CompaniesAPI.list(),
      CompaniesAPI.getDuplicates(),
    ])
    if (res.status === 'fulfilled') {
      companies.value = res.value.data || []
    }
    if (dupRes.status === 'fulfilled') {
      duplicateData.value = dupRes.value.data || {
        total_clusters: 0,
        total_duplicate_companies: 0,
        duplicate_company_ids: [],
        clusters: [],
      }
    }
    lastFetchedAt.value = Date.now()
    isStale.value = false
    persistCompanyCache()
  } catch (err) {
    // Silent background poll
  }
}

function hydrateCompanyCache() {
  try {
    const cached = JSON.parse(localStorage.getItem(COMPANY_CACHE_KEY) || 'null')
    if (!cached || !Array.isArray(cached.companies)) return
    companies.value = cached.companies
    duplicateData.value = cached.duplicateData || duplicateData.value
    lastFetchedAt.value = Number(cached.fetchedAt) || null
  } catch {
    localStorage.removeItem(COMPANY_CACHE_KEY)
  }
}

function persistCompanyCache() {
  try {
    localStorage.setItem(
      COMPANY_CACHE_KEY,
      JSON.stringify({
        companies: companies.value,
        duplicateData: duplicateData.value,
        fetchedAt: lastFetchedAt.value,
      })
    )
  } catch {
    // Browser caching is optional.
  }
}

function refreshCompaniesFromEvent() {
  isStale.value = true
  fetchCompanies()
}

async function triggerBulkResearch() {
  if (!companiesWithoutInfo.value.length || isResearchingBulk.value) return
  isResearchingBulk.value = true
  bulkProgressTotal.value = companiesWithoutInfo.value.length
  bulkProgressCompleted.value = 0

  try {
    const res = await CompaniesAPI.bulkResearch()
    const enqueued = res.data?.enqueued_count || 0
    if (enqueued === 0) {
      uiStore.showToast('All companies already have up-to-date intelligence.', 'info')
      isResearchingBulk.value = false
      return
    }

    uiStore.showToast(
      `Enqueued ${enqueued} company intelligence task${enqueued > 1 ? 's' : ''} in AI Queue`,
      'success'
    )

    const initialMissing = companiesWithoutInfo.value.length
    if (pollInterval) clearInterval(pollInterval)
    pollInterval = setInterval(async () => {
      await fetchCompaniesSilently()
      const currentMissing = companiesWithoutInfo.value.length
      bulkProgressCompleted.value = Math.max(0, initialMissing - currentMissing)
      if (currentMissing === 0 || bulkProgressCompleted.value >= initialMissing) {
        clearInterval(pollInterval)
        pollInterval = null
        isResearchingBulk.value = false
        uiStore.showToast('All company research tasks completed!', 'success')
      }
    }, 3000)
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to trigger bulk research', 'error')
    isResearchingBulk.value = false
  }
}

async function retryCompanyResearch(company) {
  try {
    await CompaniesAPI.refreshResearch(company.id)
    uiStore.showToast(`Research re-queued for ${company.name}`, 'success')
    await fetchCompaniesSilently()
  } catch (err) {
    uiStore.showToast('Failed to queue research retry', 'error')
  }
}

const stats = computed(() => {
  const total = companies.value.length
  const withActive = companies.value.filter((c) => c.active_applications_count > 0).length
  const withRatings = companies.value.filter((c) => computeAvgRating(c) !== null)
  const avgRating =
    withRatings.length
      ? (
          withRatings.reduce((sum, c) => sum + computeAvgRating(c), 0) / withRatings.length
        ).toFixed(1)
      : 'N/A'
  return { total, withActive, ratedCount: withRatings.length, avgRating }
})

const filteredCompanies = computed(() => {
  let list = [...companies.value]

  // 0. Potential Duplicates Filter
  if (filterDuplicatesOnly.value) {
    const dupSet = new Set(duplicateData.value.duplicate_company_ids || [])
    list = list.filter((c) => dupSet.has(c.id))
  }

  // 1. Hide companies that already have intel
  if (filterWithoutInfo.value) {
    list = list.filter((c) => !c.company_research || !c.company_research.summary)
  }

  // 2. Text Search
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.domain && c.domain.toLowerCase().includes(q)) ||
        (c.notes && c.notes.toLowerCase().includes(q)) ||
        (c.company_research?.summary && c.company_research.summary.toLowerCase().includes(q))
    )
  }

  // 3. Sorting
  list.sort((a, b) => {
    if (sortBy.value === 'name') return a.name.localeCompare(b.name)
    if (sortBy.value === 'recent') {
      const dateA = a.last_applied_at ? new Date(a.last_applied_at).getTime() : 0
      const dateB = b.last_applied_at ? new Date(b.last_applied_at).getTime() : 0
      return dateB - dateA
    }
    // Default: 'applications' (descending)
    return (b.applications_count || 0) - (a.applications_count || 0)
  })

  return list
})

function openCompanyDrawer(companyId) {
  uiStore.openCompanyDrawer(companyId)
}

function openCompanyDrawerWithMerge(companyId) {
  uiStore.openCompanyDrawer(companyId, 'merge')
}

</script>

<template>

  <div class="companies-view-container">
    <!-- View Header -->
    <div class="view-header">
      <div>
        <h2 class="view-title">Companies Directory</h2>
        <p class="view-subtitle">
          Manage employer entities, review candidate ratings, view multi-application histories, and explore live company intelligence.
        </p>
      </div>
    </div>

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-icon-wrap bg-primary-soft">
          <Building2 :size="18" class="text-primary" />
        </div>
        <div class="metric-info">
          <span class="metric-num">{{ stats.total }}</span>
          <span class="metric-label">Total Companies</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon-wrap bg-warning-soft">
          <TrendingUp :size="18" class="text-warning" />
        </div>
        <div class="metric-info">
          <span class="metric-num">{{ stats.withActive }}</span>
          <span class="metric-label">Active Application Pipelines</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon-wrap bg-success-soft">
          <CheckCircle2 :size="18" class="text-success" />
        </div>
        <div class="metric-info">
          <span class="metric-num">{{ stats.ratedCount }}</span>
          <span class="metric-label">Rated Companies</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon-wrap bg-amber-soft">
          <Star :size="18" class="text-amber" />
        </div>
        <div class="metric-info">
          <span class="metric-num">{{ stats.avgRating }} <span v-if="stats.avgRating !== 'N/A'" class="text-xs text-muted">/ 5</span></span>
          <span class="metric-label">Average Rating</span>
        </div>
      </div>
    </div>

    <!-- Intelligence Missing Action Banner -->
    <div v-if="companiesWithoutInfo.length > 0 || isResearchingBulk" class="intelligence-banner">
      <div class="banner-content">
        <div class="banner-icon-wrap">
          <Sparkles :size="20" class="text-primary" />
        </div>
        <div class="banner-text">
          <h4 class="banner-title">
            <span v-if="!isResearchingBulk">
              {{ companiesWithoutInfo.length }} {{ companiesWithoutInfo.length === 1 ? 'company has' : 'companies have' }} no web intelligence
            </span>
            <span v-else>
              Researching company intelligence in AI Queue...
            </span>
          </h4>
          <p class="banner-desc">
            Fetch corporate mission, tech culture, and public ratings automatically using live web search.
          </p>

          <div v-if="isResearchingBulk" class="bulk-progress-wrap mt-2">
            <div class="bulk-progress-bar">
              <div
                class="bulk-progress-fill"
                :style="{ width: `${Math.round((bulkProgressCompleted / (bulkProgressTotal || 1)) * 100)}%` }"
              ></div>
            </div>
            <span class="bulk-progress-text">
              {{ bulkProgressCompleted }} of {{ bulkProgressTotal }} completed
            </span>
          </div>
        </div>
      </div>

      <div class="banner-actions-row">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :class="{ active: filterWithoutInfo }"
          @click="filterWithoutInfo = !filterWithoutInfo"
          :title="filterWithoutInfo ? 'Show all companies' : 'Show only companies without intel'"
        >
          <SlidersHorizontal :size="14" />
          <span>{{ filterWithoutInfo ? 'Showing unresearched' : 'Hide with info' }}</span>
        </button>
        <button
          class="btn btn-primary btn-sm btn-bulk-research"
          :disabled="isResearchingBulk || !companiesWithoutInfo.length"
          @click="triggerBulkResearch"
        >
          <Loader2 v-if="isResearchingBulk" :size="14" class="animate-spin" />
          <Globe v-else :size="14" />
          <span>{{ isResearchingBulk ? 'Researching...' : `Research All (${companiesWithoutInfo.length})` }}</span>
        </button>
      </div>
    </div>

    <!-- Filter & Search Controls Bar -->
    <div class="filter-controls-bar">
      <div class="search-input-wrap">
        <Search :size="15" class="search-icon text-muted" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search companies..."
          class="form-input form-input-sm search-input"
        />
        <button
          v-if="searchQuery"
          type="button"
          class="btn-clear-search"
          @click="searchQuery = ''"
          title="Clear search input"
        >
          <X :size="14" />
        </button>
      </div>

      <div class="filter-actions">
        

        <div class="filter-group">
          <span class="text-xs text-muted">Sort By:</span>
          <select v-model="sortBy" class="form-select form-select-sm">
            <option value="applications">Most Applications</option>
            <option value="recent">Recently Applied</option>
            <option value="name">Alphabetical (A–Z)</option>
          </select>
        </div>

        <button
          v-if="duplicateData.total_duplicate_companies > 0"
          type="button"
          class="btn-dupes-filter"
          :class="{ active: filterDuplicatesOnly }"
          @click="filterDuplicatesOnly = !filterDuplicatesOnly"
          :title="filterDuplicatesOnly ? 'Show all companies' : 'Filter to show potential duplicate companies only'"
        >
          <GitMerge :size="13" />
          <span>Potential Duplicates ({{ duplicateData.total_duplicate_companies }})</span>
        </button>

      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state">
      <Loader2 :size="32" class="animate-spin text-primary" />
      <p class="text-sm text-muted mt-2">Loading employer directory...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!filteredCompanies.length" class="empty-state">
      <Building2 :size="40" class="text-muted" />
      <h3 class="mt-2 font-semibold">No Companies Found</h3>
      <p class="text-xs text-muted mt-1">
        {{ searchQuery ? 'Try adjusting your search query or rating filter.' : 'Companies are automatically created when you ingest applications.' }}
      </p>
    </div>

    <!-- Companies Grid -->
    <div v-else class="companies-grid">
      <div
        v-for="company in filteredCompanies"
        :key="company.id"
        class="company-card"
        @click="openCompanyDrawer(company.id)"
      >
        <div class="card-header-row">
          <div class="company-identity">
            <CompanyLogo
              :name="company.name"
              :domain="company.domain"
              :size="36"
              class="company-logo"
            />
            <div>
              <div class="company-title-row">
                <h4 class="company-title">{{ company.name }}</h4>
                <button
                  v-if="duplicateData.duplicate_company_ids.includes(company.id)"
                  type="button"
                  class="badge-potential-duplicate"
                  @click.stop="openCompanyDrawerWithMerge(company.id)"
                  title="Potential duplicate detected. Click to review and merge."
                >
                  <GitMerge :size="10" />
                  <span>Duplicate</span>
                </button>
              </div>
              <div v-if="company.domain" class="domain-row">
                <a
                  :href="`https://${company.domain}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="domain-link"
                  @click.stop
                >
                  <Globe :size="11" />
                  <span>{{ company.domain }}</span>
                  <ExternalLink :size="9" />
                </a>
              </div>
            </div>
          </div>

          <!-- Research FAILED chip -->
          <button
            v-if="company.research_status === 'FAILED'"
            type="button"
            class="badge-research-failed"
            @click.stop="retryCompanyResearch(company)"
            title="Research failed — click to retry"
          >
            <TriangleAlert :size="11" />
            <span>Research Failed</span>
            <RefreshCw :size="10" />
          </button>

          <!-- Public Avg Rating Badge -->
          <div class="rating-badge" @click.stop="openCompanyDrawer(company.id)">
            <Star :size="13" class="text-amber" fill="currentColor" />
            <span v-if="computeAvgRating(company) !== null" class="font-bold text-xs">
              {{ computeAvgRating(company) }}
            </span>
            <span v-else class="text-xs text-muted">N/A</span>
          </div>
        </div>

        <!-- Mission / Notes Snippet -->
        <p class="company-snippet text-muted">
          {{ company.company_research?.summary || company.notes || 'No company overview or notes recorded yet.' }}
        </p>

        <!-- Pros / Red Flags Counts -->
        <div v-if="company.pros?.length || company.red_flags?.length" class="tags-preview-row">
          <span v-if="company.pros?.length" class="badge-pro-count">
            <ThumbsUp :size="11" />
            <span>{{ company.pros.length }} pro{{ company.pros.length > 1 ? 's' : '' }}</span>
          </span>
          <span v-if="company.red_flags?.length" class="badge-flag-count">
            <AlertOctagon :size="11" />
            <span>{{ company.red_flags.length }} concern{{ company.red_flags.length > 1 ? 's' : '' }}</span>
          </span>
        </div>

        <!-- Footer Row -->
        <div class="card-footer-row">
          <div class="app-count-badge">
            <Briefcase :size="12" />
            <span>{{ company.applications_count }} application{{ company.applications_count === 1 ? '' : 's' }}</span>
            <span v-if="company.active_applications_count > 0" class="active-badge">
              ({{ company.active_applications_count }} active)
            </span>
          </div>

          <span class="drawer-trigger-hint">
            <span>Intel & Notes</span>
            <ChevronRight :size="12" />
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.companies-view-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px;
}

.view-header {
  margin-bottom: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.view-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 6px 0;
  text-align: center;
}

.view-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  max-width: 680px;
  text-align: center;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.metric-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.metric-icon-wrap {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.bg-primary-soft { background: var(--primary-light, rgba(99, 102, 241, 0.12)); }
.bg-warning-soft { background: var(--status-warning-bg, rgba(245, 158, 11, 0.12)); }
.bg-success-soft { background: var(--status-success-bg, rgba(34, 197, 94, 0.12)); }
.bg-amber-soft { background: rgba(245, 158, 11, 0.12); }

.text-amber { color: #f59e0b; }

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
}

.metric-label {
  font-size: 11px;
  color: var(--text-secondary);
}

/* Intelligence Missing Action Banner */
.intelligence-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--primary);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 20px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.banner-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--primary-light, rgba(99, 102, 241, 0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.banner-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 2px 0;
}

.banner-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.bulk-progress-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bulk-progress-bar {
  width: 180px;
  height: 6px;
  background: var(--bg-input, rgba(255, 255, 255, 0.1));
  border-radius: 999px;
  overflow: hidden;
}

.bulk-progress-fill {
  height: 100%;
  background: var(--primary);
  transition: width 0.3s ease;
}

.bulk-progress-text {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono, monospace);
}

.btn-bulk-research {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

.banner-actions-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.badge-research-failed {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  font-size: 10px;
  font-weight: 600;
  border-radius: 5px;
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
  flex-shrink: 0;
  white-space: nowrap;
}

.badge-research-failed:hover {
  background: #ef4444;
  color: #ffffff;
  border-color: #ef4444;
}

/* Potential Duplicates Alert Banner */
.duplicates-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--bg-card);
  border: 1px solid var(--status-warning-border, rgba(245, 158, 11, 0.3));
  border-left: 4px solid #f59e0b;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 20px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

.banner-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-dupes-filter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--status-warning-border, rgba(245, 158, 11, 0.3));
  color: #f59e0b;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.btn-dupes-filter:hover {
  background: rgba(245, 158, 11, 0.1);
  border-color: #f59e0b;
}

.btn-dupes-filter.active {
  background: #f59e0b;
  color: #ffffff;
  border-color: #f59e0b;
}

.company-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.badge-potential-duplicate {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #d97706;
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.badge-potential-duplicate:hover {
  background: #f59e0b;
  color: #ffffff;
  border-color: #f59e0b;
  transform: translateY(-1px);
}

.filter-controls-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
}

.search-input-wrap {
  position: relative;
  width: 320px;
  max-width: 100%;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

.search-input {
  padding-left: 32px;
  padding-right: 32px;
  width: 100%;
}

.btn-clear-search {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all var(--transition-fast, 0.15s ease);
}

.btn-clear-search:hover {
  color: var(--text-main);
  background: var(--bg-surface-hover, rgba(255, 255, 255, 0.08));
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group span {
  white-space: nowrap;
}

/* 4-Cards per row responsive grid */
.companies-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}

@media (max-width: 1360px) {
  .companies-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .companies-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .companies-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.company-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  min-width: 0;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
}

.company-card:hover {
  border-color: var(--primary);
  background: var(--bg-card-hover, var(--bg-card));
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18);
}

.card-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.company-identity {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.company-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.domain-row {
  margin-top: 2px;
}

.domain-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--primary);
  text-decoration: none;
  max-width: 180px;
  min-width: 0;
}

.domain-link span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.domain-link:hover {
  text-decoration: underline;
}

.rating-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-elevated, var(--bg-surface-hover));
  border: 1px solid var(--border-color);
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
}

.company-snippet {
  font-size: 10px;
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  height: 40px;
  color: var(--text-secondary);
}

.tags-preview-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.badge-pro-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--status-success-bg, rgba(34, 197, 94, 0.12));
  color: var(--text-success, #4ade80);
}

.badge-flag-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--status-rejected-bg, rgba(239, 68, 68, 0.12));
  color: var(--text-danger, #f87171);
}

.card-footer-row {
  border-top: 1px solid var(--border-color);
  padding-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-count-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-secondary);
}

.active-badge {
  color: #f59e0b;
  font-weight: 600;
}

.drawer-trigger-hint {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: var(--primary);
  font-weight: 500;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
}
</style>
