<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import {
  Building2,
  Search,
  Check,
  Plus,
  Loader2,
  Globe,
  X,
  ChevronDown,
} from 'lucide-vue-next'
import CompanyLogo from './CompanyLogo.vue'
import AddCompanyModal from '../modals/AddCompanyModal.vue'
import { CompaniesAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'

const props = defineProps({
  currentCompanyId: {
    type: [Number, String],
    default: null,
  },
  currentCompanyName: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  buttonTitle: {
    type: String,
    default: 'Change company',
  },
  buttonClass: {
    type: String,
    default: '',
  },
  placement: {
    type: String,
    default: 'bottom-start', // 'bottom-start' | 'bottom-end'
  },
})

const emit = defineEmits(['select', 'change'])

const uiStore = useUIStore()

const isOpen = ref(false)
const triggerRef = ref(null)
const popoverRef = ref(null)
const searchInput = ref(null)
const popoverStyle = ref({})

const searchQuery = ref('')
const companies = ref([])
const isLoading = ref(false)
const isCreating = ref(false)
const isAddModalOpen = ref(false)
const companyNameToCreate = ref('')
const highlightedIndex = ref(0)
let debounceTimer = null

function updatePosition() {
  if (!triggerRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()
  const popoverWidth = Math.min(320, window.innerWidth - 24)
  const popoverEstimatedHeight = 360

  let top = rect.bottom + 6
  let left = props.placement === 'bottom-end' ? rect.right - popoverWidth : rect.left

  // Clamp within viewport horizontally
  if (left + popoverWidth > window.innerWidth - 12) {
    left = Math.max(12, window.innerWidth - popoverWidth - 12)
  }
  if (left < 12) {
    left = 12
  }

  // Flip vertically if overflow bottom
  if (top + popoverEstimatedHeight > window.innerHeight && rect.top - popoverEstimatedHeight - 6 > 0) {
    top = Math.max(8, rect.top - popoverEstimatedHeight - 6)
  }

  popoverStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    width: `${popoverWidth}px`,
    zIndex: 99999,
  }
}

async function fetchCompanies(query = '') {
  isLoading.value = true
  try {
    const params = query ? { q: query } : {}
    const res = await CompaniesAPI.list(params)
    const list = res.data || []
    companies.value = list
    highlightedIndex.value = 0
  } catch (err) {
    console.error('Failed to search companies:', err)
  } finally {
    isLoading.value = false
  }
}

function onSearchInput() {
  highlightedIndex.value = 0
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchCompanies(searchQuery.value.trim())
  }, 180)
}

function clearSearch() {
  searchQuery.value = ''
  fetchCompanies('')
  highlightedIndex.value = 0
  nextTick(() => searchInput.value?.focus({ preventScroll: true }))
}

function scoreFuzzyMatch(text, pattern) {
  if (!pattern) return { match: true, score: 0 }
  if (!text) return { match: false, score: 0 }
  const t = text.toLowerCase()
  const p = pattern.toLowerCase()

  // Exact match
  if (t === p) return { match: true, score: 100 }
  // Starts with pattern
  if (t.startsWith(p)) return { match: true, score: 80 }
  // Substring match
  const subIdx = t.indexOf(p)
  if (subIdx !== -1) return { match: true, score: 60 - subIdx }

  // Fuzzy subsequence match
  let tIdx = 0
  let pIdx = 0
  let score = 20
  while (tIdx < t.length && pIdx < p.length) {
    if (t[tIdx] === p[pIdx]) {
      pIdx++
      score += 2
    }
    tIdx++
  }
  return { match: pIdx === p.length, score: pIdx === p.length ? score : 0 }
}

const filteredCompanies = computed(() => {
  const q = searchQuery.value.trim()
  if (!q) return companies.value

  const scored = []
  for (const comp of companies.value) {
    const nameResult = scoreFuzzyMatch(comp.name, q)
    const domainResult = scoreFuzzyMatch(comp.domain, q)
    if (nameResult.match || domainResult.match) {
      scored.push({
        comp,
        score: Math.max(nameResult.score, domainResult.score),
      })
    }
  }
  scored.sort((a, b) => b.score - a.score)
  return scored.map((item) => item.comp)
})

const showCreateOption = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return false
  return !companies.value.some((c) => c.name?.trim().toLowerCase() === query)
})

// Total selectable items count (filtered companies + create option if visible)
const totalItemsCount = computed(() => {
  return filteredCompanies.value.length + (showCreateOption.value ? 1 : 0)
})

function toggleDropdown(event) {
  if (props.disabled) return
  if (event) {
    event.stopPropagation()
    event.preventDefault()
  }
  if (!isOpen.value) {
    updatePosition()
    isOpen.value = true
  } else {
    closeDropdown()
  }
}

function closeDropdown() {
  isOpen.value = false
  searchQuery.value = ''
  highlightedIndex.value = 0
  if (debounceTimer) clearTimeout(debounceTimer)
}

function handleSelectCompany(company) {
  emit('select', company)
  emit('change', company)
  closeDropdown()
}

function handleCreateNewCompany() {
  const name = searchQuery.value.trim()
  if (!name) return

  companyNameToCreate.value = name
  closeDropdown()
  isAddModalOpen.value = true
}

function onCompanyCreated(newCompany) {
  if (!newCompany) return
  // Add to local companies list if not already present
  if (!companies.value.some((c) => String(c.id) === String(newCompany.id))) {
    companies.value.unshift(newCompany)
  }
  handleSelectCompany(newCompany)
}

function onKeydown(e) {
  if (!isOpen.value) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (totalItemsCount.value > 0) {
      highlightedIndex.value = (highlightedIndex.value + 1) % totalItemsCount.value
      scrollToHighlighted()
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (totalItemsCount.value > 0) {
      highlightedIndex.value = (highlightedIndex.value - 1 + totalItemsCount.value) % totalItemsCount.value
      scrollToHighlighted()
    }
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (highlightedIndex.value < filteredCompanies.value.length) {
      const selected = filteredCompanies.value[highlightedIndex.value]
      if (selected) handleSelectCompany(selected)
    } else if (showCreateOption.value) {
      handleCreateNewCompany()
    }
  } else if (e.key === 'Escape') {
    e.preventDefault()
    closeDropdown()
  }
}

function scrollToHighlighted() {
  nextTick(() => {
    const el = popoverRef.value?.querySelector('.company-option.highlighted')
    if (el) el.scrollIntoView({ block: 'nearest' })
  })
}

function handleClickOutside(e) {
  if (!isOpen.value) return
  if (triggerRef.value?.contains(e.target) || popoverRef.value?.contains(e.target)) {
    return
  }
  closeDropdown()
}

watch(isOpen, (val) => {
  if (val) {
    updatePosition()
    fetchCompanies('')
    nextTick(() => {
      updatePosition()
      searchInput.value?.focus({ preventScroll: true })
      window.addEventListener('scroll', updatePosition, true)
      window.addEventListener('resize', updatePosition)
    })
  } else {
    window.removeEventListener('scroll', updatePosition, true)
    window.removeEventListener('resize', updatePosition)
  }
})

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <div ref="triggerRef" class="company-picker-wrapper" @click.stop>
    <!-- Customizable Trigger Slot or Default Icon Button -->
    <slot name="trigger" :toggle="toggleDropdown" :is-open="isOpen">
      <button
        type="button"
        class="btn-switch-company"
        :class="[buttonClass, { active: isOpen }]"
        :disabled="disabled"
        :title="buttonTitle"
        @click="toggleDropdown"
      >
        <Building2 :size="13" class="switch-icon" />
        <ChevronDown :size="11" class="chevron-indicator" />
      </button>
    </slot>

    <!-- Floating Teleported Dropdown Popover -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="popoverRef"
        class="company-picker-popover"
        :style="popoverStyle"
        @click.stop
        @keydown="onKeydown"
      >
        <!-- Header / Search Box -->
        <div class="popover-search-row">
          <Search :size="14" class="search-icon" />
          <input
            ref="searchInput"
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search or add company..."
            :disabled="isCreating"
            @input="onSearchInput"
          />
          <button
            v-if="searchQuery"
            type="button"
            class="clear-btn"
            title="Clear search"
            @click="clearSearch"
          >
            <X :size="13" />
          </button>
        </div>

        <!-- List Content -->
        <div class="popover-list-container">
          <div v-if="isLoading && !filteredCompanies.length" class="list-loading-state">
            <Loader2 :size="16" class="animate-spin" />
            <span>Finding companies...</span>
          </div>

          <div v-else-if="!filteredCompanies.length && !showCreateOption" class="list-empty-state">
            <span>No companies found.</span>
          </div>

          <div v-else class="company-options-list">
            <button
              v-for="(comp, idx) in filteredCompanies"
              :key="comp.id"
              type="button"
              class="company-option"
              :class="{
                highlighted: highlightedIndex === idx,
                selected: String(comp.id) === String(currentCompanyId),
              }"
              @mouseenter="highlightedIndex = idx"
              @click="handleSelectCompany(comp)"
            >
              <CompanyLogo
                :name="comp.name"
                :domain="comp.domain"
                :size="24"
                class="option-logo"
              />
              <div class="option-info">
                <span class="option-name">{{ comp.name }}</span>
                <span v-if="comp.domain" class="option-domain">
                  <Globe :size="10" />
                  <span>{{ comp.domain }}</span>
                </span>
              </div>
              <Check
                v-if="String(comp.id) === String(currentCompanyId)"
                :size="14"
                class="check-icon"
              />
            </button>
          </div>

          <!-- Create New Company Option -->
          <div v-if="showCreateOption" class="create-option-wrapper">
            <button
              type="button"
              class="create-company-btn"
              :class="{
                highlighted: highlightedIndex === filteredCompanies.length,
              }"
              @mouseenter="highlightedIndex = filteredCompanies.length"
              @click="handleCreateNewCompany"
            >
              <Plus :size="14" />
              <span>Create "<strong>{{ searchQuery.trim() }}</strong>"</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Modal for adding/creating company with full domain & research options -->
    <AddCompanyModal
      v-model="isAddModalOpen"
      :initial-name="companyNameToCreate"
      @created="onCompanyCreated"
    />
  </div>
</template>

<style scoped>
.company-picker-wrapper {
  display: inline-flex;
  align-items: center;
  position: relative;
}

.btn-switch-company {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-switch-company:hover,
.btn-switch-company.active {
  color: var(--text-main);
  background: var(--bg-surface-hover);
  border-color: var(--border-subtle);
}

.switch-icon {
  flex-shrink: 0;
}

.chevron-indicator {
  opacity: 0.7;
  transition: transform var(--transition-fast);
}

.btn-switch-company.active .chevron-indicator {
  transform: rotate(180deg);
}

.company-picker-popover {
  position: fixed;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--font-sans);
  z-index: 99999;
}

.popover-search-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-input);
}

.search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-main);
  font-size: 12px;
  font-family: inherit;
  outline: none;
  min-width: 0;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.clear-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  border-radius: var(--radius-xs);
  transition: color var(--transition-fast), background var(--transition-fast);
}

.clear-btn:hover {
  color: var(--text-main);
  background: var(--bg-surface-hover);
}

.popover-list-container {
  max-height: 280px;
  overflow-y: auto;
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.list-loading-state,
.list-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.company-options-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.company-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 6px 8px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  text-align: left;
  cursor: pointer;
  color: var(--text-main);
  transition: background var(--transition-fast);
}

.company-option.highlighted,
.company-option:hover {
  background: var(--bg-surface-hover);
}

.company-option.selected {
  color: var(--primary);
  font-weight: 500;
}

.option-logo {
  flex-shrink: 0;
}

.option-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.option-name {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-domain {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.check-icon {
  color: var(--primary);
  flex-shrink: 0;
}

.create-option-wrapper {
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid var(--border-subtle);
}

.create-company-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  background: var(--primary-subtle);
  border: 1px dashed var(--primary);
  border-radius: var(--radius-sm);
  color: var(--primary);
  font-size: 12px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.create-company-btn:hover,
.create-company-btn.highlighted {
  background: var(--primary-glow);
  color: var(--primary-hover);
  border-color: var(--primary-hover);
}

.create-company-btn strong {
  color: var(--text-main);
}
</style>
