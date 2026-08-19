<script setup>
import { ref } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import { AIConfigAPI } from '../../api/endpoints'
import {
  Server,
  Plus,
  Trash2,
  Edit3,
  Zap,
  Loader2,
  CheckCircle,
  AlertCircle,
} from 'lucide-vue-next'

const props = defineProps({
  providers: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['refresh'])
const uiStore = useUIStore()

const isProviderModalOpen = ref(false)
const editingProvider = ref(null)
const testingProviderId = ref(null)
const providerTestResults = ref({})

const providerForm = ref({
  name: '',
  provider_type: 'openai',
  base_url: 'http://192.168.1.187:1234/v1',
  api_key: '',
  max_concurrency: 1,
  is_active: true,
})

function openCreateProvider() {
  editingProvider.value = null
  providerForm.value = {
    name: '',
    provider_type: 'openai',
    base_url: 'http://192.168.1.187:1234/v1',
    api_key: '',
    max_concurrency: 1,
    is_active: true,
  }
  isProviderModalOpen.value = true
}

function openEditProvider(p) {
  editingProvider.value = p
  providerForm.value = {
    name: p.name,
    provider_type: p.provider_type,
    base_url: p.base_url || '',
    api_key: '',
    max_concurrency: p.max_concurrency || 1,
    is_active: p.is_active,
  }
  isProviderModalOpen.value = true
}

async function saveProvider() {
  try {
    if (editingProvider.value) {
      await AIConfigAPI.updateProvider(editingProvider.value.id, providerForm.value)
      uiStore.showToast('Provider updated successfully', 'success')
    } else {
      await AIConfigAPI.createProvider(providerForm.value)
      uiStore.showToast('Provider registered successfully', 'success')
    }
    isProviderModalOpen.value = false
    emit('refresh')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function deleteProvider(id) {
  if (!confirm('Are you sure you want to delete this provider?')) return
  try {
    await AIConfigAPI.deleteProvider(id)
    uiStore.showToast('Provider deleted', 'info')
    emit('refresh')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function testProviderDirect(provider) {
  testingProviderId.value = provider.id
  providerTestResults.value[provider.id] = null
  try {
    const res = await AIConfigAPI.testProvider(provider.id)
    const isWarning = res.data?.status === 'warning'
    providerTestResults.value[provider.id] = {
      status: isWarning ? 'warning' : 'success',
      message: isWarning ? res.data.response : 'Success (Connected)',
    }
    uiStore.showToast(
      isWarning ? res.data.response : `Provider '${provider.name}' connection verified!`,
      isWarning ? 'warning' : 'success'
    )
  } catch (err) {
    const errMsg = err.response?.data?.detail || err.message || 'Connection failed'
    providerTestResults.value[provider.id] = {
      status: 'error',
      message: errMsg,
    }
    uiStore.showToast(errMsg, 'error')
  } finally {
    testingProviderId.value = null
  }
}
</script>

<template>
  <div class="section-card">
    <div class="section-header-row">
      <div>
        <h3>Configured AI Providers</h3>
        <p>Connect local endpoints (LM Studio, Ollama, vLLM) or Cloud APIs (OpenAI, Anthropic, Gemini, OpenRouter).</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="openCreateProvider">
        <Plus :size="15" />
        <span>Add Provider</span>
      </button>
    </div>

    <div class="providers-grid">
      <div v-for="p in providers" :key="p.id" class="provider-card">
        <div class="provider-header">
          <div class="provider-title-group">
            <Server :size="16" class="text-primary" />
            <span class="provider-name">{{ p.name }}</span>
          </div>
          <span class="badge badge-applied font-mono">{{ p.provider_type }}</span>
        </div>

        <div class="provider-body">
          <div class="meta-row">
            <span class="meta-k">Endpoint:</span>
            <span class="meta-v font-mono">{{ p.base_url || 'Default Cloud Endpoint' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-k">API Key:</span>
            <span class="meta-v font-mono">{{ p.api_key_masked || 'Not Required / Local' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-k">Max Concurrency:</span>
            <span class="meta-v font-mono font-semibold">{{ p.max_concurrency || 1 }} parallel</span>
          </div>
        </div>

        <div class="provider-actions">
          <button
            class="btn btn-secondary btn-sm"
            :disabled="testingProviderId === p.id"
            @click="testProviderDirect(p)"
            title="Ping endpoint to verify connectivity"
          >
            <Loader2 v-if="testingProviderId === p.id" class="animate-spin" :size="14" />
            <Zap v-else :size="14" />
            <span>Ping Provider</span>
          </button>

          <button class="btn btn-secondary btn-sm" @click="openEditProvider(p)">
            <Edit3 :size="14" />
            <span>Edit</span>
          </button>

          <button class="btn btn-danger btn-sm" @click="deleteProvider(p.id)">
            <Trash2 :size="14" />
          </button>
        </div>

        <!-- Provider Test Result -->
        <div
          v-if="providerTestResults[p.id]"
          class="provider-test-pill animate-fade-in"
          :class="`is-${providerTestResults[p.id].status}`"
        >
          <CheckCircle v-if="providerTestResults[p.id].status === 'success'" :size="13" class="text-success" />
          <AlertCircle v-else-if="providerTestResults[p.id].status === 'warning'" :size="13" class="text-warning" />
          <AlertCircle v-else :size="13" class="text-danger" />
          <span class="font-mono text-xs">{{ providerTestResults[p.id].message }}</span>
        </div>
      </div>

      <div v-if="providers.length === 0" class="empty-state">
        No AI providers configured in DB. System using `.env` fallback.
      </div>
    </div>

    <!-- PROVIDER MODAL -->
    <div v-if="isProviderModalOpen" class="modal-backdrop" @click.self="isProviderModalOpen = false">
      <div class="modal-card animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingProvider ? 'Edit Provider: ' + editingProvider.name : 'Add AI Provider' }}</h3>
          <button class="btn-close" @click="isProviderModalOpen = false">×</button>
        </div>

        <div class="modal-body">
          <div class="input-group">
            <label class="input-label">Provider Name *</label>
            <input v-model="providerForm.name" type="text" placeholder="e.g. Local LM Studio, Anthropic Work" class="form-input" required />
          </div>

          <div class="input-group">
            <label class="input-label">Provider Type *</label>
            <select v-model="providerForm.provider_type" class="form-input">
              <option value="openai">OpenAI / LM Studio / vLLM (OpenAI-compatible)</option>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="ollama">Ollama</option>
              <option value="google_genai">Google Gemini (GenAI)</option>
              <option value="openrouter">OpenRouter</option>
              <option value="custom">Custom Endpoint</option>
            </select>
          </div>

          <div class="input-group">
            <label class="input-label">Base URL</label>
            <input v-model="providerForm.base_url" type="text" placeholder="http://192.168.1.187:1234/v1" class="form-input" />
          </div>

          <div class="input-group">
            <label class="input-label">{{ editingProvider ? 'New API Key (Leave blank to keep unchanged)' : 'API Key (Optional for local)' }}</label>
            <input v-model="providerForm.api_key" type="password" placeholder="lm-studio / sk-..." class="form-input" />
          </div>

          <div class="input-group">
            <div class="label-with-hint">
              <label class="input-label">Max Concurrency Limit</label>
              <span class="text-xs text-muted">Local: 1 | Cloud: 5-10</span>
            </div>
            <input
              v-model.number="providerForm.max_concurrency"
              type="number"
              min="1"
              max="50"
              placeholder="1"
              class="form-input font-mono"
              required
            />
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="isProviderModalOpen = false">Cancel</button>
            <button class="btn btn-primary" @click="saveProvider">{{ editingProvider ? 'Update Provider' : 'Save Provider' }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.section-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.section-header-row > div {
  flex: 1;
  min-width: 260px;
}

.section-header-row h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.section-header-row p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.section-header-row .btn {
  flex-shrink: 0;
  margin-top: 2px;
}

.providers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.provider-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.provider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.provider-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.provider-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.meta-k {
  color: var(--text-muted);
}

.meta-v {
  color: var(--text-main);
  text-align: right;
  word-break: break-all;
}

.provider-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 4px;
}

.provider-test-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
  color: var(--status-offer-text);
  font-size: 12px;
}

.provider-test-pill.is-error {
  background-color: var(--status-rejected-bg);
  border-color: var(--status-rejected-border);
  color: var(--status-rejected-text);
}

.provider-test-pill.is-warning {
  background-color: var(--status-interview-bg);
  border-color: var(--status-interview-border);
  color: var(--status-interview-text);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 13px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.btn-close {
  border: none;
  background: transparent;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.input-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.label-with-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-input {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text-main);
}

.form-input:focus {
  outline: none;
  border-color: var(--primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}
</style>
