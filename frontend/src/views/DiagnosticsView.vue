<script setup>
import { ref, onMounted } from 'vue'
import { DiagnosticsAPI } from '../api/endpoints'
import { Activity, AlertCircle, CheckCircle, Clock } from 'lucide-vue-next'

const stats = ref(null)
const traces = ref([])
const loading = ref(true)
const loadingTraces = ref(false)
const showErrorsOnly = ref(false)

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
    const resTraces = await DiagnosticsAPI.getTraces({ errors_only: showErrorsOnly.value, limit: 50 })
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

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-text-center">
        <h1 class="page-title">Diagnostic Tracing Dashboard</h1>
        <p class="page-subtitle">Hidden admin view for LLM and LangGraph telemetry</p>
      </div>
    </div>

    <div v-if="loading" class="text-center py-4">
      <span class="text-secondary">Loading telemetry...</span>
    </div>

    <div v-else class="settings-content-area">
      <!-- Stats Overview -->
      <div class="stats-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
        <div class="stat-card" style="background: var(--bg-surface); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; color: var(--text-secondary);">
            <Activity :size="16" />
            <span>Total Runs</span>
          </div>
          <div style="font-size: 24px; font-weight: 700;">{{ stats?.total_runs || 0 }}</div>
        </div>

        <div class="stat-card" style="background: var(--bg-surface); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--status-success-border);">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; color: var(--status-success-text);">
            <CheckCircle :size="16" />
            <span>Success Rate</span>
          </div>
          <div style="font-size: 24px; font-weight: 700;">{{ stats?.success_rate || 0 }}%</div>
        </div>

        <div class="stat-card" style="background: var(--bg-surface); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--status-danger-border);">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; color: var(--status-danger-text);">
            <AlertCircle :size="16" />
            <span>Errors</span>
          </div>
          <div style="font-size: 24px; font-weight: 700;">{{ stats?.error_count || 0 }}</div>
        </div>
      </div>

      <!-- Traces Table -->
      <div class="section-card">
        <div class="card-intro" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3>Recent Traces</h3>
          <button class="btn btn-outline btn-sm" @click="toggleErrorsOnly">
            {{ showErrorsOnly ? 'Show All' : 'Show Errors Only' }}
          </button>
        </div>

        <div v-if="loadingTraces" class="text-center py-4">
          <span class="text-secondary">Loading...</span>
        </div>

        <div v-else-if="traces.length === 0" class="empty-state">
          No traces found.
        </div>

        <div v-else style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
              <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">
                <th style="padding: 12px 8px;">Timestamp</th>
                <th style="padding: 12px 8px;">Run ID</th>
                <th style="padding: 12px 8px;">Event Type</th>
                <th style="padding: 12px 8px;">Task Name</th>
                <th style="padding: 12px 8px;">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trace in traces" :key="trace.id" style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: 12px 8px; font-size: 13px; color: var(--text-secondary);">
                  {{ new Date(trace.timestamp).toLocaleString() }}
                </td>
                <td style="padding: 12px 8px; font-size: 13px; font-family: monospace;">
                  {{ trace.run_id.substring(0, 8) }}...
                </td>
                <td style="padding: 12px 8px; font-size: 13px;">
                  <span style="background: var(--bg-main); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border-color);">
                    {{ trace.event_type }}
                  </span>
                </td>
                <td style="padding: 12px 8px; font-size: 13px;">
                  {{ trace.payload_summary?.name || 'Unknown' }}
                </td>
                <td style="padding: 12px 8px;">
                  <span v-if="trace.payload_summary?.error" style="color: var(--status-danger-text); font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 4px;">
                    <AlertCircle :size="12" /> Error
                  </span>
                  <span v-else style="color: var(--status-success-text); font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 4px;">
                    <CheckCircle :size="12" /> Success
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  padding: 32px 0;
}
</style>
