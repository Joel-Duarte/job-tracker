<script setup>
import { onMounted } from 'vue'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useUIStore } from '../stores/uiStore'
import {
  Search,
  Kanban,
  Table as TableIcon,
  Filter,
  Building2,
  Calendar,
  AlertCircle,
  ChevronRight,
  Sparkles,
  Layers,
  ArrowUpDown,
} from 'lucide-vue-next'

const appStore = useApplicationsStore()
const uiStore = useUIStore()

onMounted(() => {
  appStore.fetchApplications()
})

function handleSearch(e) {
  appStore.searchQuery = e.target.value
  appStore.fetchApplications()
}

function handleStatusFilter(e) {
  appStore.selectedStatus = e.target.value
  appStore.fetchApplications()
}

function toggleActionRequired() {
  appStore.actionRequiredOnly = !appStore.actionRequiredOnly
  appStore.fetchApplications()
}

function formatDate(isoStr) {
  if (!isoStr) return '—'
  try {
    return new Date(isoStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return isoStr
  }
}
</script>

<template>
  <div class="page-container">
    <!-- Header & Controls Bar -->
    <div class="controls-bar">
      <!-- Search & Filters -->
      <div class="search-filter-group">
        <div class="search-input-wrapper">
          <Search :size="15" class="search-icon" />
          <input
            type="text"
            placeholder="Search company, position, or keywords..."
            :value="appStore.searchQuery"
            class="search-input"
            @input="handleSearch"
          />
        </div>

        <select
          :value="appStore.selectedStatus"
          class="filter-select"
          @change="handleStatusFilter"
        >
          <option value="">All Statuses</option>
          <option v-for="s in appStore.STATUSES" :key="s.key" :value="s.key">
            {{ s.label }}
          </option>
        </select>

        <button
          class="btn btn-secondary filter-toggle-btn"
          :class="{ active: appStore.actionRequiredOnly }"
          @click="toggleActionRequired"
        >
          <AlertCircle :size="14" />
          <span>Action Required</span>
        </button>
      </div>

      <!-- View Switcher & Total Count -->
      <div class="view-switch-group">
        <div class="total-counter">
          <span class="count-num">{{ appStore.total }}</span>
          <span class="count-label">Applications</span>
        </div>

        <div class="view-toggle">
          <button
            class="view-btn"
            :class="{ active: uiStore.viewMode === 'kanban' }"
            @click="uiStore.setViewMode('kanban')"
            title="Kanban Board View"
          >
            <Kanban :size="15" />
          </button>
          <button
            class="view-btn"
            :class="{ active: uiStore.viewMode === 'table' }"
            @click="uiStore.setViewMode('table')"
            title="Data Table View"
          >
            <TableIcon :size="15" />
          </button>
        </div>
      </div>
    </div>

    <!-- MAIN VIEW AREA -->
    <div class="content-wrapper">
      <!-- 1. KANBAN VIEW -->
      <div v-if="uiStore.viewMode === 'kanban'" class="kanban-board">
        <div
          v-for="col in appStore.STATUSES"
          :key="col.key"
          class="kanban-column"
        >
          <div class="column-header">
            <div class="column-title-group">
              <span class="column-dot" :class="`dot-${col.color}`"></span>
              <span class="column-title">{{ col.label }}</span>
            </div>
            <span class="column-count">
              {{ appStore.kanbanColumns[col.key]?.length || 0 }}
            </span>
          </div>

          <div class="column-cards">
            <div
              v-for="app in appStore.kanbanColumns[col.key] || []"
              :key="app.id"
              class="application-card"
              @click="uiStore.openDetail(app.id)"
            >
              <div class="card-header">
                <div class="company-name-tag">
                  <Building2 :size="14" class="company-icon" />
                  <span>{{ app.company?.name || 'Company' }}</span>
                </div>
                <span class="card-date">{{ formatDate(app.last_activity_at || app.application_date) }}</span>
              </div>

              <div class="card-position">
                {{ app.position || 'Position Not Specified' }}
              </div>

              <div v-if="app.latest_event?.email_summary" class="card-summary">
                {{ app.latest_event.email_summary }}
              </div>

              <div class="card-footer">
                <div v-if="app.has_action_required" class="card-action-badge">
                  <AlertCircle :size="12" />
                  <span>Action Needed</span>
                </div>
                <div class="card-arrow">
                  <ChevronRight :size="14" />
                </div>
              </div>
            </div>

            <!-- Empty Column State -->
            <div
              v-if="!appStore.kanbanColumns[col.key]?.length"
              class="column-empty"
            >
              No applications
            </div>
          </div>
        </div>
      </div>

      <!-- 2. DATA TABLE VIEW -->
      <div v-else class="table-container animate-fade-in">
        <table class="data-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Position</th>
              <th>Status</th>
              <th>Last Activity</th>
              <th>Action Needed</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="app in appStore.applications"
              :key="app.id"
              class="table-row"
              @click="uiStore.openDetail(app.id)"
            >
              <td class="cell-company">
                <div class="company-cell-wrapper">
                  <div class="company-logo-mini">
                    <Building2 :size="14" />
                  </div>
                  <span class="company-name-bold">{{ app.company?.name || 'Company' }}</span>
                </div>
              </td>

              <td class="cell-position">
                {{ app.position || '—' }}
              </td>

              <td>
                <span class="badge" :class="`badge-${(app.status || 'applied').toLowerCase()}`">
                  {{ app.status }}
                </span>
              </td>

              <td class="cell-date">
                {{ formatDate(app.last_activity_at || app.application_date) }}
              </td>

              <td>
                <span
                  v-if="app.has_action_required"
                  class="table-action-pill"
                >
                  <AlertCircle :size="12" />
                  <span>Required</span>
                </span>
                <span v-else class="text-muted text-xs">—</span>
              </td>

              <td class="text-right" @click.stop>
                <button
                  class="btn btn-secondary btn-sm"
                  @click="uiStore.openDetail(app.id)"
                >
                  View Details
                </button>
              </td>
            </tr>

            <tr v-if="appStore.applications.length === 0">
              <td colspan="6" class="table-empty">
                No matching job applications found.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  overflow: hidden;
}

.controls-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background-color: var(--bg-app);
  border-bottom: 1px solid var(--border-color);
  gap: 16px;
}

.search-filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.search-input-wrapper {
  position: relative;
  width: 100%;
  max-width: 360px;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
}

.search-input {
  width: 100%;
  padding-left: 32px;
  height: 34px;
}

.filter-select {
  height: 34px;
  padding: 0 10px;
  font-size: 13px;
}

.filter-toggle-btn {
  height: 34px;
}
.filter-toggle-btn.active {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border-color: var(--status-interview-border);
}

.view-switch-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-counter {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.count-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.count-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.view-toggle {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.view-btn:hover {
  color: var(--text-main);
}

.view-btn.active {
  background-color: var(--bg-elevated);
  color: var(--primary);
}

.content-wrapper {
  flex: 1;
  overflow-x: auto;
  overflow-y: auto;
  padding: 20px 24px;
}

/* KANBAN BOARD */
.kanban-board {
  display: grid;
  grid-template-columns: repeat(5, minmax(280px, 1fr));
  gap: 16px;
  height: 100%;
  align-items: start;
}

.kanban-column {
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 170px);
  overflow: hidden;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
}

.column-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-applied { background-color: var(--status-applied-text); }
.dot-assessment { background-color: var(--status-assessment-text); }
.dot-interview { background-color: var(--status-interview-text); }
.dot-offer { background-color: var(--status-offer-text); }
.dot-rejected { background-color: var(--status-rejected-text); }

.column-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.column-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background-color: var(--bg-surface);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.column-cards {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}

.application-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.application-card:hover {
  background-color: var(--bg-card-hover);
  border-color: var(--border-subtle);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.company-name-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.company-icon {
  color: var(--primary);
}

.card-date {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.card-position {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
  margin-bottom: 6px;
  line-height: 1.3;
}

.card-summary {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.3;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.card-action-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  color: var(--status-interview-text);
  background-color: var(--status-interview-bg);
  padding: 2px 6px;
  border-radius: var(--radius-full);
}

.card-arrow {
  color: var(--text-muted);
  margin-left: auto;
}

.column-empty {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  padding: 24px 0;
}

/* DATA TABLE */
.table-container {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

.data-table th {
  background-color: var(--bg-sidebar);
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
}

.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-main);
}

.table-row {
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.table-row:hover {
  background-color: var(--bg-surface-hover);
}

.company-cell-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-logo-mini {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  color: var(--primary);
}

.company-name-bold {
  font-weight: 600;
}

.cell-position {
  font-weight: 500;
}

.cell-date {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

.table-action-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  font-size: 11px;
  font-weight: 600;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

.text-right {
  text-align: right;
}

.table-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
</style>
