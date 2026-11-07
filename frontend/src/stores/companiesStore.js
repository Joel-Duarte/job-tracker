import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { CompaniesAPI } from '../api/endpoints'
import { useUIStore } from './uiStore'

const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes

export const useCompaniesStore = defineStore('companies', () => {
  const uiStore = useUIStore()

  const companies = ref([])
  const totalCount = ref(0)
  const pageSize = ref(50)
  const isLoading = ref(false)
  const isLoadingMore = ref(false)
  const searchQuery = ref('')
  const sortBy = ref('applications') // 'applications' | 'name' | 'recent'
  const filterWithoutInfo = ref(false)
  const filterDuplicatesOnly = ref(false)

  const statsData = ref({
    total: 0,
    withActive: 0,
    researchedCount: 0,
    totalApplications: 0,
    unresearchedCount: 0,
  })

  const duplicateData = ref({
    total_clusters: 0,
    total_duplicate_companies: 0,
    duplicate_company_ids: [],
    clusters: [],
  })
  const isLoadingDuplicates = ref(false)

  const lastFetchedAt = ref(null)
  const isStale = ref(false)

  const hasMore = computed(() => companies.value.length < totalCount.value)

  const stats = computed(() => {
    if (statsData.value && statsData.value.total > 0) {
      return statsData.value
    }
    const total = totalCount.value || companies.value.length
    const withActive = companies.value.filter((c) => (c.active_applications_count || 0) > 0).length
    const withResearch = companies.value.filter(
      (c) => c.company_research && c.company_research.summary
    ).length
    const totalApps = companies.value.reduce((acc, c) => acc + (c.applications_count || 0), 0)
    return {
      total,
      withActive,
      researchedCount: withResearch,
      totalApplications: totalApps,
      unresearchedCount: Math.max(0, total - withResearch),
    }
  })

  const unresearchedCount = computed(() => {
    if (statsData.value && typeof statsData.value.unresearchedCount === 'number') {
      return statsData.value.unresearchedCount
    }
    return stats.value.unresearchedCount ?? 0
  })

  function invalidateCache() {
    isStale.value = true
  }

  function buildQueryParams(offset = 0, limit = pageSize.value) {
    return {
      limit,
      offset,
      q: searchQuery.value.trim() || undefined,
      sort_by: sortBy.value,
      sort_order: sortBy.value === 'name' ? 'asc' : 'desc',
      without_research: filterWithoutInfo.value ? true : undefined,
      duplicate_ids:
        filterDuplicatesOnly.value && duplicateData.value.duplicate_company_ids?.length
          ? duplicateData.value.duplicate_company_ids.join(',')
          : undefined,
    }
  }

  async function fetchDuplicatesLazy(force = false) {
    if (!force && duplicateData.value.clusters?.length) return
    if (isLoadingDuplicates.value) return

    isLoadingDuplicates.value = true
    try {
      const dupRes = await CompaniesAPI.getDuplicates()
      if (dupRes?.data) {
        duplicateData.value = dupRes.data
      }
    } catch {
      // Background duplicate scan is non-blocking
    } finally {
      isLoadingDuplicates.value = false
    }
  }

  async function fetchCompanies(force = false, silent = false) {
    const isFresh =
      !force &&
      !isStale.value &&
      lastFetchedAt.value !== null &&
      companies.value.length > 0 &&
      Date.now() - lastFetchedAt.value < CACHE_TTL_MS

    if (isFresh) {
      // Lazy background check for duplicates if missing
      if (!duplicateData.value.clusters?.length) {
        fetchDuplicatesLazy()
      }
      return
    }

    if (!silent) {
      isLoading.value = companies.value.length === 0
    }

    try {
      const params = buildQueryParams(0, pageSize.value)
      const res = await CompaniesAPI.list(params)
      const data = res.data

      if (data && Array.isArray(data.items)) {
        companies.value = data.items
        totalCount.value = data.total ?? data.items.length
        if (data.stats) {
          statsData.value = {
            total: data.stats.total,
            withActive: data.stats.with_active,
            researchedCount: data.stats.researched_count,
            totalApplications: data.stats.total_applications,
            unresearchedCount: data.stats.unresearched_count,
          }
        }
      } else if (Array.isArray(data)) {
        companies.value = data
        totalCount.value = data.length
      }

      lastFetchedAt.value = Date.now()
      isStale.value = false

      // Fire lazy duplicate scan in background without awaiting
      fetchDuplicatesLazy()
    } catch (err) {
      if (!silent) {
        uiStore.showToast('Failed to load companies directory', 'error')
      }
    } finally {
      isLoading.value = false
    }
  }

  async function loadMoreCompanies() {
    if (isLoadingMore.value || !hasMore.value) return
    isLoadingMore.value = true
    try {
      const params = buildQueryParams(companies.value.length, pageSize.value)
      const res = await CompaniesAPI.list(params)
      const data = res.data
      const newItems = Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : [])
      const existingIds = new Set(companies.value.map((c) => c.id))
      const uniqueNew = newItems.filter((c) => !existingIds.has(c.id))
      companies.value = [...companies.value, ...uniqueNew]
      totalCount.value = data?.total ?? companies.value.length
    } catch (err) {
      uiStore.showToast('Failed to load more companies', 'error')
    } finally {
      isLoadingMore.value = false
    }
  }

  async function fetchCompaniesSilently() {
    try {
      const currentLimit = Math.max(pageSize.value, companies.value.length)
      const params = buildQueryParams(0, currentLimit)
      const res = await CompaniesAPI.list(params)
      const data = res.data
      if (data && Array.isArray(data.items)) {
        companies.value = data.items
        totalCount.value = data.total ?? data.items.length
        if (data.stats) {
          statsData.value = {
            total: data.stats.total,
            withActive: data.stats.with_active,
            researchedCount: data.stats.researched_count,
            totalApplications: data.stats.total_applications,
            unresearchedCount: data.stats.unresearched_count,
          }
        }
      } else if (Array.isArray(data)) {
        companies.value = data
        totalCount.value = data.length
      }
    } catch {
      // Silent poll
    }
  }

  function updateCompanyInStore(updatedCompany) {
    if (!updatedCompany || !updatedCompany.id) return
    const idx = companies.value.findIndex((c) => String(c.id) === String(updatedCompany.id))
    if (idx > -1) {
      companies.value[idx] = {
        ...companies.value[idx],
        ...updatedCompany,
        applications_count:
          updatedCompany.applications_count ?? companies.value[idx].applications_count,
        active_applications_count:
          updatedCompany.active_applications_count ??
          companies.value[idx].active_applications_count,
      }
    }
  }

  function removeCompanyFromStore(companyId) {
    if (!companyId) return
    companies.value = companies.value.filter((c) => String(c.id) !== String(companyId))
    totalCount.value = Math.max(0, totalCount.value - 1)
  }

  return {
    companies,
    totalCount,
    pageSize,
    isLoading,
    isLoadingMore,
    searchQuery,
    sortBy,
    filterWithoutInfo,
    filterDuplicatesOnly,
    statsData,
    duplicateData,
    isLoadingDuplicates,
    hasMore,
    stats,
    unresearchedCount,
    invalidateCache,
    fetchCompanies,
    loadMoreCompanies,
    fetchCompaniesSilently,
    fetchDuplicatesLazy,
    updateCompanyInStore,
    removeCompanyFromStore,
  }
})
