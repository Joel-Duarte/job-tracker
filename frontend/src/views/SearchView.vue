<script setup>
import { ref } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { SearchAPI } from '../api/endpoints'
import {
  Search,
  Sparkles,
  Building2,
  Calendar,
  ChevronRight,
  Loader2,
  Compass,
} from 'lucide-vue-next'

const uiStore = useUIStore()

const searchQuery = ref('')
const results = ref([])
const hasSearched = ref(false)
const loading = ref(false)

async function executeSearch() {
  if (!searchQuery.value.trim()) return
  loading.value = true
  hasSearched.value = true

  try {
    const res = await SearchAPI.semantic(searchQuery.value.trim(), 15, 0.4)
    results.value = res.data || []
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    loading.value = false
  }
}

function handleKeyDown(e) {
  if (e.key === 'Enter') {
    executeSearch()
  }
}
</script>

<template>
  <div class="page-container">
    <!-- Search Banner -->
    <div class="search-hero">
      <div class="hero-badge">
        <Sparkles :size="14" />
        <span>768-dim pgvector Cosine Search</span>
      </div>
      <h1 class="hero-title">Semantic Vector Explorer</h1>
      <p class="hero-subtitle">
        Search applications by interview topics, skills, recruiters, or contextual milestones across all timelines.
      </p>

      <div class="search-bar-box">
        <Search :size="18" class="search-bar-icon" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="e.g. 'roles where I had system design interviews with Staff engineers' or 'Rust and distributed systems'"
          class="search-bar-input"
          @keydown="handleKeyDown"
        />
        <button
          class="btn btn-primary search-bar-btn"
          :disabled="loading || !searchQuery.trim()"
          @click="executeSearch"
        >
          <Loader2 v-if="loading" class="animate-spin" :size="16" />
          <span>{{ loading ? 'Searching...' : 'Explore' }}</span>
        </button>
      </div>
    </div>

    <!-- Results Section -->
    <div class="results-container">
      <div v-if="loading" class="loading-box">
        <Loader2 class="animate-spin" :size="28" />
        <span>Synthesizing vector similarity...</span>
      </div>

      <div v-else-if="hasSearched && results.length === 0" class="empty-results">
        <Compass :size="40" class="text-muted" />
        <h3>No matching applications found</h3>
        <p>Try refining your query or lowering specificity.</p>
      </div>

      <div v-else-if="results.length > 0" class="results-list">
        <div class="results-header">
          Found {{ results.length }} semantically matching application snapshots
        </div>

        <div
          v-for="item in results"
          :key="item.id"
          class="result-card animate-fade-in"
          @click="uiStore.openDetail(item.application_id)"
        >
          <div class="card-left">
            <div class="card-meta">
              <div class="company-tag">
                <Building2 :size="14" class="text-primary" />
                <span class="company-name">{{ item.company_name || 'Company' }}</span>
              </div>
              <span class="role-name">{{ item.position || 'Position Not Specified' }}</span>
            </div>

            <div class="narrative-summary">
              {{ item.email_summary || 'Snapshot summary available in details.' }}
            </div>
          </div>

          <div class="card-right">
            <div class="similarity-score-pill">
              <Sparkles :size="12" />
              <span>{{ (item.similarity_score || 0).toFixed(1) }}% Match</span>
            </div>
            <ChevronRight :size="16" class="arrow-icon" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
}

.search-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 36px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 12px;
}

.hero-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}

.hero-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 600px;
  margin-bottom: 24px;
  line-height: 1.5;
}

.search-bar-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 740px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 6px 8px 6px 14px;
  box-shadow: var(--shadow-md);
}

.search-bar-icon {
  color: var(--text-muted);
  margin-right: 10px;
}

.search-bar-input {
  flex: 1;
  background: transparent;
  border: none;
  font-size: 14px;
  box-shadow: none !important;
}

.search-bar-btn {
  padding: 8px 18px;
}

.results-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading-box, .empty-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: var(--text-secondary);
  gap: 12px;
}

.results-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  cursor: pointer;
  transition: all var(--transition-fast);
  gap: 20px;
}

.result-card:hover {
  background-color: var(--bg-surface-hover);
  border-color: var(--border-subtle);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.card-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.company-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-main);
}

.role-name {
  font-size: 13px;
  color: var(--text-secondary);
}

.narrative-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.card-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.similarity-score-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.arrow-icon {
  color: var(--text-muted);
}
</style>
