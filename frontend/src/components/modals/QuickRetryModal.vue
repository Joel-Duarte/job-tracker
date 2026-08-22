<script setup>
import { useRouter } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import {
  AlertTriangle,
  RefreshCw,
  Settings,
  X,
  Server,
  Globe,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()

async function handleRetry() {
  await uiStore.checkAIHealth()
  if (uiStore.aiStatus === 'healthy' || uiStore.aiStatus === 'degraded' || uiStore.aiFallbackProviderName) {
    uiStore.closeRetryModal()
    uiStore.showToast('AI Provider connection restored!', 'success')
  }
}

function handleOpenSettings() {
  uiStore.closeRetryModal()
  uiStore.setLastNonSettingsRoute(router.currentRoute.value.fullPath)
  router.push('/settings')
}
</script>

<template>
  <div v-if="uiStore.isRetryModalOpen" class="modal-backdrop" @click.self="uiStore.closeRetryModal">
    <div class="modal-container">
      <div class="modal-header">
        <div class="header-title">
          <div class="alert-icon">
            <AlertTriangle :size="20" class="text-danger" />
          </div>
          <h3>AI Provider Unreachable</h3>
        </div>
        <button class="btn-icon-ghost" @click="uiStore.closeRetryModal">
          <X :size="18" />
        </button>
      </div>

      <div class="modal-body">
        <p class="description">
          The requested action requires AI processing, but the active AI Provider is currently unreachable and no secondary fallback provider is available.
        </p>

        <div class="details-card">
          <div class="detail-row">
            <div class="label"><Server :size="14" /> Failing Provider:</div>
            <div class="value font-medium">{{ uiStore.aiActiveProviderName || 'Primary Provider' }}</div>
          </div>
          <div class="detail-row" v-if="uiStore.aiBaseUrl">
            <div class="label"><Globe :size="14" /> Endpoint Base URL:</div>
            <div class="value font-mono text-xs">{{ uiStore.aiBaseUrl }}</div>
          </div>
          <div class="error-msg-box" v-if="uiStore.aiErrorMessage">
            <span class="error-title">Error Details:</span>
            <span>{{ uiStore.aiErrorMessage }}</span>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="uiStore.closeRetryModal">
          Cancel
        </button>
        <button class="btn btn-outline" @click="handleOpenSettings">
          <Settings :size="14" />
          <span>Open Settings</span>
        </button>
        <button class="btn btn-primary" @click="handleRetry" :disabled="uiStore.isCheckingAIHealth">
          <RefreshCw :size="14" :class="{ spin: uiStore.isCheckingAIHealth }" />
          <span>{{ uiStore.isCheckingAIHealth ? 'Testing...' : 'Ping Now / Retry' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 9990;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-container {
  width: 100%;
  max-width: 480px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modal-slide-in 0.2s ease-out;
}

@keyframes modal-slide-in {
  from { opacity: 0; transform: translateY(12px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.alert-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: rgba(239, 68, 68, 0.12);
}

.header-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.description {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.details-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background-color: var(--bg-main, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 8px);
}

.detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.detail-row .label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.detail-row .value {
  color: var(--text-main);
}

.error-msg-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  background-color: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-sm, 4px);
  font-size: 11px;
  color: var(--danger, #ef4444);
  word-break: break-word;
}

.error-title {
  font-weight: 700;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  background-color: var(--bg-surface-hover, rgba(0, 0, 0, 0.02));
  border-top: 1px solid var(--border-subtle);
}

.btn-icon-ghost {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
}

.btn-icon-ghost:hover {
  color: var(--text-main);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
