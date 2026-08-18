<script setup>
import { ref, onMounted } from 'vue'
import { DiagnosticsAPI } from '../api/endpoints'
import { Activity, AlertCircle, CheckCircle, Search, TerminalSquare, Info, ChevronRight, X } from 'lucide-vue-next'

const stats = ref(null)
const traces = ref([])
const loading = ref(true)
const loadingTraces = ref(false)
const showErrorsOnly = ref(false)
const selectedTrace = ref(null)
const loadingDetail = ref(false)

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
    const resTraces = await DiagnosticsAPI.getTraces({ errors_only: showErrorsOnly.value, limit: 100 })
    traces.value = resTraces.data
  } catch (err) {
    console.error("Failed to load traces", err)
  } finally {
    loadingTraces.value = false
  }
}

function toggleErrorsOnly() {
  showErrorsOnly.value = !showErrorsOnly.value
  loadTraces()
}

async function viewTraceDetails(runId) {
  loadingDetail.value = true
  selectedTrace.value = { id: 'loading' } // placeholder to open modal
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

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-text-center">
        <h1 class="page-title">LangGraph Telemetry Dashboard</h1>
        <p class="page-subtitle">Real-time embedded PostgreSQL tracer diagnostics</p>
      </div>
      <div class="header-actions">
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
      <!-- KPI Metric Cards -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-icon default">
            <Activity :size="20" />
          </div>
          <div class="kpi-info">
            <div class="kpi-label">Total Traces Recorded</div>
            <div class="kpi-value">{{ stats?.total_runs || 0 }}</div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon success">
            <CheckCircle :size="20" />
          </div>
          <div class="kpi-info">
            <div class="kpi-label">Successful Executions</div>
            <div class="kpi-value text-success">{{ stats?.success_count || 0 }}</div>
            <div class="kpi-subtext">Success Rate: {{ stats?.success_rate || 0 }}%</div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-icon danger">
            <AlertCircle :size="20" />
          </div>
          <div class="kpi-info">
            <div class="kpi-label">Failed Invocations</div>
            <div class="kpi-value text-danger">{{ stats?.error_count || 0 }}</div>
          </div>
        </div>
      </div>

      <!-- Tracing Data Table -->
      <div class="section-card mt-6">
        <div class="card-intro flex justify-between items-center mb-4">
          <div>
            <h3>Execution Traces</h3>
            <p class="text-sm text-secondary">Showing recent agent runs and LLM completions.</p>
          </div>

          <div class="filters">
            <label class="toggle-switch">
              <input type="checkbox" v-model="showErrorsOnly" @change="loadTraces" />
              <span class="slider round"></span>
              <span class="toggle-label ml-2 text-sm font-medium">Show Errors Only</span>
            </label>
          </div>
        </div>

        <div v-if="loadingTraces" class="py-6 flex flex-center">
          <div class="spinner"></div>
        </div>

        <div v-else-if="traces.length === 0" class="empty-state py-8 text-center">
          <TerminalSquare :size="32" class="text-secondary mb-3 mx-auto" />
          <h4>No traces found</h4>
          <p class="text-secondary text-sm mt-1">No AI telemetry has been recorded yet.</p>
        </div>

        <div v-else class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th width="15%">Timestamp</th>
                <th width="12%">Run ID</th>
                <th width="10%">Type</th>
                <th width="35%">Task Name</th>
                <th width="15%">Status</th>
                <th width="13%" class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trace in traces" :key="trace.id" class="trace-row" @click="viewTraceDetails(trace.run_id)">
                <td class="text-secondary text-sm">
                  {{ new Date(trace.timestamp).toLocaleTimeString() }}
                  <br>
                  <span style="font-size: 11px;">{{ new Date(trace.timestamp).toLocaleDateString() }}</span>
                </td>
                <td>
                  <span class="badge badge-outline text-xs font-mono">
                    {{ trace.run_id.substring(0, 8) }}
                  </span>
                </td>
                <td>
                  <span class="badge badge-neutral text-xs capitalize">
                    {{ trace.event_type }}
                  </span>
                </td>
                <td class="font-medium text-sm">
                  {{ trace.payload_summary?.name || 'Unknown execution' }}
                </td>
                <td>
                  <div v-if="trace.payload_summary?.error" class="status-indicator error">
                    <span class="dot"></span> Failed
                  </div>
                  <div v-else class="status-indicator success">
                    <span class="dot"></span> Completed
                  </div>
                </td>
                <td class="text-right">
                  <button class="btn btn-icon btn-sm text-secondary hover-primary">
                    <ChevronRight :size="16" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Deep Dive Modal -->
    <div v-if="selectedTrace" class="modal-overlay" @click.self="closeDetails">
      <div class="modal-content large" style="max-width: 900px; width: 90vw;">
        <div class="modal-header">
          <div>
            <h3 class="modal-title flex items-center gap-2">
              <TerminalSquare :size="18" /> Trace Inspector
            </h3>
            <p class="text-xs text-secondary mt-1 font-mono">Run ID: {{ selectedTrace.run_id || '...' }}</p>
          </div>
          <button class="btn-icon" @click="closeDetails">
            <X :size="18" />
          </button>
        </div>

        <div class="modal-body bg-dark" style="background: #0f172a; padding: 20px; max-height: 70vh; overflow-y: auto;">
          <div v-if="loadingDetail" class="flex flex-center py-8">
            <div class="spinner"></div>
          </div>
          <div v-else-if="selectedTrace.id !== 'loading'">
            <div v-if="selectedTrace.payload?.error" class="error-banner mb-4">
              <h4 class="text-danger flex items-center gap-2"><AlertCircle :size="16" /> Exception Caught</h4>
              <p class="text-sm font-mono mt-2" style="white-space: pre-wrap; color: #f87171;">{{ selectedTrace.payload.error }}</p>
            </div>

            <h4 class="text-white mb-2 text-sm font-medium">Raw Payload Data</h4>
            <pre class="json-viewer"><code>{{ JSON.stringify(selectedTrace.payload, null, 2) }}</code></pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 32px 0;
  max-width: 1200px;
  margin: 0 auto;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s, box-shadow 0.2s;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-icon.default { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.kpi-icon.success { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
.kpi-icon.danger { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

.kpi-info { flex: 1; }
.kpi-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 4px; }
.kpi-value { font-size: 28px; font-weight: 700; color: var(--text-main); line-height: 1.2; }
.kpi-subtext { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.text-success { color: var(--status-success-text); }
.text-danger { color: var(--status-danger-text); }

.mt-6 { margin-top: 24px; }
.mb-4 { margin-bottom: 16px; }
.mb-3 { margin-bottom: 12px; }
.py-6 { padding-top: 24px; padding-bottom: 24px; }
.py-8 { padding-top: 32px; padding-bottom: 32px; }
.flex { display: flex; }
.flex-center { align-items: center; justify-content: center; flex-direction: column; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border-color);
  font-weight: 600;
}

.data-table td {
  padding: 12px 16px;
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
.trace-row:hover .hover-primary {
  color: var(--primary);
}

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  display: inline-block;
}
.badge-outline { border: 1px solid var(--border-color); }
.badge-neutral { background: var(--bg-main); border: 1px solid var(--border-color); }
.font-mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; }

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}
.status-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-indicator.success .dot { background: var(--status-success-text); }
.status-indicator.success { color: var(--status-success-text); }
.status-indicator.error .dot { background: var(--status-danger-text); }
.status-indicator.error { color: var(--status-danger-text); }

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: relative;
  width: 36px;
  height: 20px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  transition: .4s;
  border-radius: 34px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 2px;
  bottom: 2px;
  background-color: var(--text-secondary);
  transition: .4s;
  border-radius: 50%;
}
input:checked + .slider { background-color: var(--primary); border-color: var(--primary); }
input:checked + .slider:before {
  transform: translateX(16px);
  background-color: white;
}

/* Modal styling overrides */
.error-banner {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 12px 16px;
  border-radius: 8px;
}
.json-viewer {
  margin: 0;
  color: #a5b4fc;
  font-size: 13px;
  font-family: 'JetBrains Mono', monospace;
  overflow-x: auto;
}
</style>
