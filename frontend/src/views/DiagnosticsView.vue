<script setup>
import { ref, onMounted, computed } from 'vue'
import { DiagnosticsAPI } from '../api/endpoints'
import {
  Activity,
  AlertCircle,
  CheckCircle,
  TerminalSquare,
  ChevronRight,
  X,
  Sparkles,
  Globe,
  Mail,
  Cpu,
  Database,
  Trash2,
  Clock,
  Code,
  Layers,
  Copy,
  Check,
  DollarSign,
  Zap,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  BarChart3,
} from 'lucide-vue-next'

function formatTokens(val) {
  if (!val) return '0'
  if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M'
  if (val >= 1_000) return (val / 1_000).toFixed(1) + 'k'
  return String(val)
}

const stats = ref(null)
const traces = ref([])
const loading = ref(true)
const loadingTraces = ref(false)
const showErrorsOnly = ref(false)
const isTaskBreakdownCollapsed = ref(false)
const activeCategory = ref('all')
const selectedStatus = ref('all') // 'all' | 'success' | 'error'
const selectedTrace = ref(null)
const loadingDetail = ref(false)
const modalTab = ref('overview') // 'overview' or 'raw'
const copied = ref(false)

const categories = [
  { id: 'all', label: 'All Telemetry', icon: Layers },
  { id: 'llm', label: 'AI & LLM', icon: Sparkles },
  { id: 'scraper', label: 'Web Scraper', icon: Globe },
  { id: 'email_sync', label: 'Email Sync', icon: Mail },
  { id: 'worker', label: 'Workers', icon: Cpu },
  { id: 'embedding', label: 'Embeddings', icon: Database },
]

async function loadData() {
  loading.value = true
  try {
    const resStats = await DiagnosticsAPI.getStats()
    stats.value = resStats.data

    await loadTraces()
  } catch (err) {
    console.error("Failed to load diagnostic data", err)
  } finally {
    loading.value = false
  }
}

async function loadTraces() {
  loadingTraces.value = true
  try {
    const params = {
      limit: 100
    }
    if (activeCategory.value && activeCategory.value !== 'all') {
      params.category = activeCategory.value
    }
    if (selectedStatus.value && selectedStatus.value !== 'all') {
      params.status = selectedStatus.value
    }
    if (showErrorsOnly.value) {
      params.errors_only = true
    }
    const resTraces = await DiagnosticsAPI.getTraces(params)
    traces.value = resTraces.data
  } catch (err) {
    console.error("Failed to load traces", err)
  } finally {
    loadingTraces.value = false
  }
}

function selectCategory(catId) {
  activeCategory.value = catId
  loadTraces()
}

function onStatusChange() {
  if (selectedStatus.value === 'error') {
    showErrorsOnly.value = true
  } else if (selectedStatus.value === 'all' || selectedStatus.value === 'success') {
    showErrorsOnly.value = false
  }
  loadTraces()
}

function toggleErrorsOnly() {
  if (showErrorsOnly.value) {
    selectedStatus.value = 'error'
  } else {
    selectedStatus.value = 'all'
  }
  loadTraces()
}

async function viewTraceDetails(runId) {
  loadingDetail.value = true
  modalTab.value = 'overview'
  selectedTrace.value = { id: 'loading', run_id: runId }
  try {
    const res = await DiagnosticsAPI.getTrace(runId)
    selectedTrace.value = res.data
  } catch (err) {
    console.error(err)
    selectedTrace.value = null
  } finally {
    loadingDetail.value = false
  }
}

function closeDetails() {
  selectedTrace.value = null
}

async function purgeAllTraces() {
  if (!confirm("Are you sure you want to purge all telemetry traces? This action cannot be undone.")) {
    return
  }
  try {
    await DiagnosticsAPI.purge()
    await loadData()
  } catch (err) {
    console.error("Failed to purge traces", err)
  }
}

function copyRawJson() {
  if (!selectedTrace.value?.payload) return
  navigator.clipboard.writeText(JSON.stringify(selectedTrace.value.payload, null, 2))
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
}

function getCategoryBadgeClass(category) {
  switch (category) {
    case 'llm': return 'badge-cat-llm'
    case 'scraper': return 'badge-cat-scraper'
    case 'email_sync': return 'badge-cat-email'
    case 'worker': return 'badge-cat-worker'
    case 'embedding': return 'badge-cat-embedding'
    default: return 'badge-cat-default'
  }
}

function getCategoryIcon(category) {
  switch (category) {
    case 'llm': return Sparkles
    case 'scraper': return Globe
    case 'email_sync': return Mail
    case 'worker': return Cpu
    case 'embedding': return Database
    default: return Activity
  }
}

function formatDuration(ms) {
  if (ms == null) return '--'
  if (ms < 1000) return `${Math.round(ms)} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-text-center">
        <h1 class="page-title">System Diagnostics & Telemetry</h1>
        <p class="page-subtitle">Real-time execution traces across AI pipelines, web scrapers, email sync, and background workers</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-outline" @click="purgeAllTraces" title="Purge telemetry records">
          <Trash2 :size="15" /> Purge Logs
        </button>
        <button class="btn btn-primary" @click="loadData">
          <Activity :size="16" /> Refresh Telemetry
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state flex flex-center py-8">
      <div class="spinner"></div>
      <span>Initializing tracer metrics...</span>
    </div>

    <div v-else class="settings-content-area">
      <div class="diagnostics-inner-container">
        <!-- KPI Metric Cards -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-icon default">
              <Activity :size="20" />
            </div>
            <div class="kpi-info">
              <div class="kpi-label">Total Telemetry Traces</div>
              <div class="kpi-value">{{ stats?.total_runs || 0 }}</div>
              <div class="kpi-subtext">Success Rate: {{ stats?.success_rate || 0 }}% ({{ stats?.error_count || 0 }} errors)</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon info">
              <Zap :size="20" class="text-primary" />
            </div>
            <div class="kpi-info">
              <div class="kpi-label">Total LLM Tokens</div>
              <div class="kpi-value font-mono">{{ formatTokens(stats?.total_tokens || 0) }}</div>
              <div class="kpi-subtext font-mono">{{ (stats?.total_tokens || 0).toLocaleString() }} tokens tracked</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon primary">
              <DollarSign :size="20" class="text-primary" />
            </div>
            <div class="kpi-info">
              <div class="kpi-label">Estimated Cloud API Spend</div>
              <div class="kpi-value text-primary font-mono">${{ (stats?.total_spend_usd || 0).toFixed(4) }}</div>
              <div class="kpi-subtext">Paid cloud API tokens</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon success">
              <CheckCircle :size="20" class="text-success" />
            </div>
            <div class="kpi-info">
              <div class="kpi-label">Estimated Local Savings</div>
              <div class="kpi-value text-success font-mono">~${{ (stats?.total_savings_usd || 0).toFixed(4) }}</div>
              <div class="kpi-subtext">Ollama / LM Studio inference</div>
            </div>
          </div>
        </div>

        <!-- Task Token & Cost Distribution Card -->
        <div v-if="stats?.task_token_breakdown && Object.keys(stats.task_token_breakdown).length > 0" class="section-card mb-6">
          <div class="section-header-row mb-3 flex items-center justify-between">
            <div class="section-header-text">
              <h3 class="flex items-center gap-2">
                <BarChart3 :size="16" class="text-primary flex-shrink-0" />
                <span>Token &amp; Cost Distribution by Task</span>
              </h3>
              <p class="text-xs text-muted">Telemetry breakdown across specialized AI pipelines and scrapers.</p>
            </div>
            <button
              class="btn btn-secondary btn-xs flex items-center gap-1.5"
              @click="isTaskBreakdownCollapsed = !isTaskBreakdownCollapsed"
            >
              <span>{{ isTaskBreakdownCollapsed ? 'Show Breakdown' : 'Hide Breakdown' }}</span>
              <ChevronDown v-if="isTaskBreakdownCollapsed" :size="13" />
              <ChevronUp v-else :size="13" />
            </button>
          </div>

          <transition name="accordion-fade">
            <div v-show="!isTaskBreakdownCollapsed" class="task-breakdown-grid animate-fade-in">
              <div
                v-for="(taskData, taskKey) in stats.task_token_breakdown"
                :key="taskKey"
                class="task-breakdown-pill"
              >
                <div class="task-pill-header">
                  <span class="task-pill-name font-medium" :title="taskKey">{{ taskKey }}</span>
                  <span class="badge badge-applied font-mono text-xs flex-shrink-0">{{ taskData.calls }} runs</span>
                </div>
                <div class="task-pill-body font-mono text-xs text-muted flex justify-between items-center mt-2">
                  <span class="token-count text-secondary font-medium">{{ formatTokens(taskData.tokens) }} tokens</span>
                  <span v-if="taskData.cost_usd > 0" class="text-primary font-semibold">${{ taskData.cost_usd.toFixed(4) }}</span>
                  <span v-else-if="taskData.savings_usd > 0" class="text-success font-semibold">Saved ~${{ taskData.savings_usd.toFixed(4) }}</span>
                  <span v-else class="text-muted font-medium">$0.0000</span>
                </div>
              </div>
            </div>
          </transition>
        </div>

        <!-- Tracing Data Section -->
        <div class="section-card">
          <!-- Category Tabs Bar -->
          <div class="category-tabs-container">
            <div class="category-tabs">
              <button
                v-for="cat in categories"
                :key="cat.id"
                class="category-tab"
                :class="{ active: activeCategory === cat.id }"
                @click="selectCategory(cat.id)"
              >
                <component :is="cat.icon" :size="15" />
                <span>{{ cat.label }}</span>
                <span class="tab-badge">
                  {{ cat.id === 'all' ? (stats?.total_runs || 0) : (stats?.category_counts?.[cat.id] || 0) }}
                </span>
              </button>
            </div>

            <div class="filters-actions">
              <!-- Errors Only Toggle -->
              <label class="toggle-switch ml-2">
                <input type="checkbox" v-model="showErrorsOnly" @change="toggleErrorsOnly" />
                <span class="slider round"></span>
                <span class="toggle-label ml-2 text-sm font-medium">Errors Only</span>
              </label>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="loadingTraces" class="py-8 flex flex-center">
            <div class="spinner"></div>
            <span class="mt-2 text-secondary text-sm">Filtering traces...</span>
          </div>

          <!-- Empty State -->
          <div v-else-if="traces.length === 0" class="empty-state py-12 text-center">
            <TerminalSquare :size="36" class="text-secondary mb-3 mx-auto opacity-70" />
            <h4>No traces recorded</h4>
            <p class="text-secondary text-sm mt-1">
              {{ showErrorsOnly ? 'No error traces found for this category.' : 'No operations have been recorded in this category yet.' }}
            </p>
          </div>

          <!-- Traces Table -->
          <div v-else class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th width="15%">Timestamp</th>
                  <th width="12%">Category</th>
                  <th width="35%">Task / Operation</th>
                  <th width="12%">Duration</th>
                  <th width="14%">Status</th>
                  <th width="12%" class="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="trace in traces"
                  :key="trace.id"
                  class="trace-row"
                  @click="viewTraceDetails(trace.run_id)"
                >
                  <td class="text-secondary text-xs">
                    <span class="font-medium text-main">{{ new Date(trace.timestamp).toLocaleTimeString() }}</span>
                    <br />
                    <span class="opacity-75">{{ new Date(trace.timestamp).toLocaleDateString() }}</span>
                  </td>
                  <td>
                    <span class="category-badge" :class="getCategoryBadgeClass(trace.category)">
                      <component :is="getCategoryIcon(trace.category)" :size="12" />
                      {{ trace.category }}
                    </span>
                  </td>
                  <td>
                    <div class="task-cell">
                      <span class="task-name">{{ trace.payload_summary?.name || trace.event_type }}</span>
                      <span class="run-id-pill font-mono">{{ trace.run_id.substring(0, 8) }}</span>
                    </div>
                  </td>
                  <td class="text-secondary text-sm font-mono">
                    {{ formatDuration(trace.payload_summary?.duration_ms) }}
                  </td>
                  <td>
                    <div v-if="trace.payload_summary?.error || trace.status === 'error'" class="status-indicator error">
                      <span class="dot"></span> Failed
                    </div>
                    <div v-else class="status-indicator success">
                      <span class="dot"></span> Completed
                    </div>
                  </td>
                  <td class="text-right">
                    <button class="btn-inspect" @click.stop="viewTraceDetails(trace.run_id)">
                      <span>Inspect</span>
                      <ChevronRight :size="14" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Inspector Modal -->
    <div v-if="selectedTrace" class="modal-backdrop" @click.self="closeDetails">
      <div class="modal-card animate-fade-in" style="max-width: 880px; width: 92vw;">
        <div class="modal-header">
          <div class="modal-title-group">
            <div class="modal-icon text-primary">
              <component :is="getCategoryIcon(selectedTrace.category)" :size="20" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="modal-title">{{ selectedTrace.payload?.name || 'Trace Inspector' }}</h3>
                <span class="category-badge" :class="getCategoryBadgeClass(selectedTrace.category)">
                  {{ selectedTrace.category || 'telemetry' }}
                </span>
              </div>
              <p class="text-xs text-secondary mt-1 font-mono">Run ID: {{ selectedTrace.run_id }}</p>
            </div>
          </div>
          <button class="btn-icon" @click="closeDetails">
            <X :size="18" />
          </button>
        </div>

        <!-- Modal Tabs -->
        <div class="modal-nav">
          <button
            class="modal-nav-tab"
            :class="{ active: modalTab === 'overview' }"
            @click="modalTab = 'overview'"
          >
            <Activity :size="14" /> Structured Overview
          </button>
          <button
            class="modal-nav-tab"
            :class="{ active: modalTab === 'raw' }"
            @click="modalTab = 'raw'"
          >
            <Code :size="14" /> Raw Payload JSON
          </button>
        </div>

        <div class="modal-body">
          <div v-if="loadingDetail" class="flex flex-center py-12">
            <div class="spinner"></div>
            <span class="mt-2 text-secondary text-sm">Loading trace details...</span>
          </div>

          <div v-else-if="selectedTrace.id !== 'loading'">
            <!-- Overview Tab -->
            <div v-if="modalTab === 'overview'" class="overview-content">
              <!-- Exception Banner if failed -->
              <div v-if="selectedTrace.payload?.error" class="error-banner mb-4">
                <h4 class="text-danger flex items-center gap-2 font-semibold">
                  <AlertCircle :size="16" /> Execution Error
                </h4>
                <pre class="error-trace font-mono">{{ selectedTrace.payload.error }}</pre>
              </div>

              <!-- Metadata Summary Grid -->
              <div class="meta-grid mb-4">
                <div class="meta-item">
                  <span class="meta-label">Status</span>
                  <span class="meta-value">
                    <span v-if="selectedTrace.payload?.error" class="text-danger font-semibold">Failed</span>
                    <span v-else class="text-success font-semibold">Success</span>
                  </span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">Duration</span>
                  <span class="meta-value font-mono">{{ formatDuration(selectedTrace.payload?.duration_ms) }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">Timestamp</span>
                  <span class="meta-value text-xs">{{ new Date(selectedTrace.timestamp).toLocaleString() }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">Category</span>
                  <span class="meta-value capitalize">{{ selectedTrace.category }}</span>
                </div>
              </div>

              <!-- Operation Inputs -->
              <div v-if="selectedTrace.payload?.inputs && Object.keys(selectedTrace.payload.inputs).length > 0" class="payload-box mb-4">
                <h5 class="box-title">Inputs</h5>
                <pre class="json-code"><code>{{ JSON.stringify(selectedTrace.payload.inputs, null, 2) }}</code></pre>
              </div>

              <!-- Operation Outputs -->
              <div v-if="selectedTrace.payload?.outputs && Object.keys(selectedTrace.payload.outputs).length > 0" class="payload-box mb-4">
                <h5 class="box-title">Outputs</h5>
                <pre class="json-code"><code>{{ JSON.stringify(selectedTrace.payload.outputs, null, 2) }}</code></pre>
              </div>

              <!-- Extra Metadata -->
              <div v-if="selectedTrace.payload?.extra && Object.keys(selectedTrace.payload.extra).length > 0" class="payload-box">
                <h5 class="box-title">Operational Context</h5>
                <pre class="json-code"><code>{{ JSON.stringify(selectedTrace.payload.extra, null, 2) }}</code></pre>
              </div>
            </div>

            <!-- Raw JSON Tab -->
            <div v-else class="raw-content">
              <div class="raw-header">
                <span class="text-xs text-secondary">Complete JSON Payload</span>
                <button class="btn btn-xs btn-outline" @click="copyRawJson">
                  <component :is="copied ? Check : Copy" :size="13" />
                  {{ copied ? 'Copied!' : 'Copy JSON' }}
                </button>
              </div>
              <pre class="raw-viewer font-mono"><code>{{ JSON.stringify(selectedTrace.payload, null, 2) }}</code></pre>
            </div>
          </div>
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
  min-height: 0;
  background-color: var(--bg-app);
  overflow: hidden;
  padding: 0;
  max-width: none;
  margin: 0;
}

.page-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 16px;
}

.header-text-center {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
  letter-spacing: -0.01em;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 650px;
  line-height: 1.4;
}

.settings-content-area {
  flex: 1 1 0%;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 32px 48px 32px;
  background-color: var(--bg-app);
  display: flex;
  justify-content: center;
}

.diagnostics-inner-container {
  width: 100%;
  max-width: 1180px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
}

/* KPI Cards */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  flex-shrink: 0;
}

.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s, box-shadow 0.2s;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-icon.default { background: rgba(99, 102, 241, 0.12); color: #6366f1; }
.kpi-icon.primary { background: rgba(59, 130, 246, 0.12); color: #3b82f6; }
.kpi-icon.info { background: rgba(168, 85, 247, 0.12); color: #a855f7; }
.kpi-icon.success { background: rgba(34, 197, 94, 0.12); color: #22c55e; }
.kpi-icon.danger { background: rgba(239, 68, 68, 0.12); color: #ef4444; }

.kpi-info { flex: 1; }
.kpi-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.kpi-value { font-size: 24px; font-weight: 700; color: var(--text-main); line-height: 1.2; }
.kpi-subtext { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.text-success { color: var(--status-success-text); }
.text-danger { color: var(--status-danger-text); }

/* Task Breakdown Styles */
.task-breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 12px;
  padding: 0 20px 20px 20px;
}

.task-breakdown-pill {
  background: var(--bg-card, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: var(--radius-md, 8px);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: all 0.2s ease;
}

.task-breakdown-pill:hover {
  border-color: var(--primary);
  background: rgba(59, 130, 246, 0.04);
}

.task-pill-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.task-pill-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-main, #f8fafc);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.token-count {
  font-size: 0.78rem;
  letter-spacing: -0.01em;
}

/* Section Card */
.section-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* Category Tabs Bar */
.category-tabs-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-sidebar);
  gap: 12px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.category-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.category-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 12px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.category-tab:hover {
  background: var(--bg-surface-hover);
  color: var(--text-main);
}

.category-tab.active {
  background: var(--bg-surface);
  color: var(--primary);
  border-color: var(--border-color);
  box-shadow: var(--shadow-xs);
  font-weight: 600;
}

.tab-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--bg-main);
  color: var(--text-secondary);
  font-weight: 600;
}

.category-tab.active .tab-badge {
  background: rgba(99, 102, 241, 0.12);
  color: var(--primary);
}

.filters-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.filter-select {
  padding: 4px 8px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  outline: none;
}

.filter-select:focus {
  border-color: var(--primary);
}

/* Data Table */
.table-responsive {
  position: relative;
  overflow-x: auto;
  overflow-y: auto;
  max-height: 60vh;
  min-height: 280px;
}

.table-responsive::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.table-responsive::-webkit-scrollbar-track {
  background: var(--bg-surface);
}

.table-responsive::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}

.table-responsive::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.data-table {
  width: 100%;
  min-width: 750px;
  border-collapse: separate;
  border-spacing: 0;
}

.data-table th {
  position: sticky;
  top: 0;
  z-index: 10;
  text-align: left;
  padding: 12px 18px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  background: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
}

.data-table td {
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.trace-row {
  cursor: pointer;
  transition: background-color 0.15s;
}

.trace-row:hover {
  background-color: var(--bg-surface-hover);
}

.task-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-main);
}

.run-id-pill {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-main);
  border: 1px solid var(--border-color);
  color: var(--text-tertiary);
}

/* Category Badges */
.category-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
}

.badge-cat-llm { background: rgba(168, 85, 247, 0.12); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.25); }
.badge-cat-scraper { background: rgba(20, 184, 166, 0.12); color: #0d9488; border: 1px solid rgba(20, 184, 166, 0.25); }
.badge-cat-email { background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.25); }
.badge-cat-worker { background: rgba(59, 130, 246, 0.12); color: #2563eb; border: 1px solid rgba(59, 130, 246, 0.25); }
.badge-cat-embedding { background: rgba(99, 102, 241, 0.12); color: #4f46e5; border: 1px solid rgba(99, 102, 241, 0.25); }
.badge-cat-default { background: var(--bg-main); color: var(--text-secondary); border: 1px solid var(--border-color); }

/* Status Indicator */
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
}

.status-indicator .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-indicator.success .dot { background: #22c55e; }
.status-indicator.success { color: #16a34a; }
.status-indicator.error .dot { background: #ef4444; }
.status-indicator.error { color: #dc2626; }

.btn-inspect {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.trace-row:hover .btn-inspect {
  background: var(--bg-surface);
  color: var(--primary);
  border-color: var(--primary);
}

/* Modal Styling */
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
  width: 100%;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background-color: var(--bg-surface);
}

.modal-title-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.modal-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.modal-nav {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-sidebar);
  padding: 0 16px;
}

.modal-nav-tab {
  display: inline-flex;
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
  transition: all 0.15s;
}

.modal-nav-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}

.modal-body {
  padding: 20px 24px;
  max-height: 72vh;
  overflow-y: auto;
  background: var(--bg-surface);
}

/* Modal Content Components */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.meta-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.meta-value {
  font-size: 13px;
  color: var(--text-main);
}

.error-banner {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  padding: 14px 18px;
  border-radius: var(--radius-md);
}

.error-trace {
  margin-top: 8px;
  font-size: 12px;
  color: #f87171;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  overflow-y: auto;
}

.payload-box {
  background: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px 16px;
}

.box-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.json-code {
  margin: 0;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: #6366f1;
  max-height: 220px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.raw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.raw-viewer {
  margin: 0;
  background: #0f172a;
  color: #a5b4fc;
  font-size: 12px;
  padding: 16px;
  border-radius: var(--radius-md);
  max-height: 55vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Helpers */
.flex { display: flex; }
.flex-center { align-items: center; justify-content: center; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.mb-4 { margin-bottom: 16px; }
.mb-3 { margin-bottom: 12px; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.py-8 { padding-top: 32px; padding-bottom: 32px; }
.py-12 { padding-top: 48px; padding-bottom: 48px; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.btn-xs { padding: 4px 8px; font-size: 11px; }

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  gap: 8px;
}
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: relative;
  width: 34px;
  height: 18px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  transition: .3s;
  border-radius: 34px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 12px;
  width: 12px;
  left: 2px;
  bottom: 2px;
  background-color: var(--text-secondary);
  transition: .3s;
  border-radius: 50%;
}
input:checked + .slider { background-color: var(--primary); border-color: var(--primary); }
input:checked + .slider:before {
  transform: translateX(16px);
  background-color: white;
}

/* RESPONSIVE ADAPTATIONS */
@media (max-width: 767px) {
  .page-header {
    padding: 16px 16px;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
    gap: 8px;
  }

  .header-actions .btn {
    flex: 1;
    min-height: 44px;
    justify-content: center;
  }

  .settings-content-area {
    padding: 16px 12px 48px;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .category-tabs-container {
    flex-direction: column;
    align-items: flex-start;
    padding: 10px 12px;
    gap: 10px;
  }

  .category-tabs {
    overflow-x: auto;
    white-space: nowrap;
    flex-wrap: nowrap;
    width: 100%;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }

  .category-tabs::-webkit-scrollbar {
    display: none;
  }

  .category-tab {
    flex-shrink: 0;
    min-height: 40px;
  }

  .filters-actions {
    width: 100%;
    justify-content: flex-between;
  }

  .meta-grid {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .btn-inspect {
    min-height: 38px;
  }
}

@media (max-width: 480px) {
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
