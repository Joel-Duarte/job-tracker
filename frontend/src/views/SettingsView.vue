<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { AIConfigAPI, EmailAccountsAPI, PromptsAPI, DiagnosticsAPI } from '../api/endpoints'
import CandidateProfileView from './CandidateProfileView.vue'
import PageHeader from '../components/common/PageHeader.vue'
import AIProvidersSettings from '../components/settings/AIProvidersSettings.vue'
import EmailAccountsSettings from '../components/settings/EmailAccountsSettings.vue'
import TaskBindingsSettings from '../components/settings/TaskBindingsSettings.vue'

import {
  Sparkles,
  Server,
  Mail,
  UserCheck,
  SlidersHorizontal,
  Save,
  DollarSign,
  Archive,
  Loader2,
} from 'lucide-vue-next'

const route = useRoute()
const uiStore = useUIStore()

const activeTab = ref(route.query.tab || 'studio') // 'studio' | 'providers' | 'email_accounts' | 'profile' | 'preferences'

watch(() => route.query.tab, (newTab) => {
  if (newTab) activeTab.value = newTab
})

// AI Providers state
const providers = ref([])
const loadingProviders = ref(false)

// Task Studio state
const bindings = ref([])
const promptsList = ref([])

const globalBinding = computed(() => {
  return bindings.value.find((b) => b.task_type === 'GLOBAL_DEFAULT') || null
})

// Email Accounts state
const emailAccounts = ref([])
const oauthConfig = ref({
  google_redirect_uri: '',
  microsoft_redirect_uri: '',
})

// Diagnostics state
const isExporting = ref(false)

async function exportDiagnostics() {
  if (isExporting.value) return
  isExporting.value = true
  try {
    const res = await DiagnosticsAPI.export()
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'diagnostics.zip')
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (err) {
    console.error('Failed to export diagnostics', err)
  } finally {
    isExporting.value = false
  }
}

async function loadProviders() {
  loadingProviders.value = true
  try {
    const res = await AIConfigAPI.listProviders()
    providers.value = res.data || []
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    loadingProviders.value = false
  }
}

async function loadBindings() {
  try {
    const res = await AIConfigAPI.listBindings()
    bindings.value = res.data || []
  } catch (err) {
    // ignore
  }
}

async function loadPrompts() {
  try {
    const res = await PromptsAPI.list()
    promptsList.value = res.data || []
  } catch (err) {
    // ignore
  }
}

async function loadEmailAccounts() {
  try {
    const res = await EmailAccountsAPI.list()
    emailAccounts.value = res.data || []
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  }
}

async function loadOAuthConfig() {
  const origin = window.location.origin
  try {
    const res = await EmailAccountsAPI.getOAuthConfig()
    if (res.data?.base_url && !res.data.base_url.includes(':8000')) {
      oauthConfig.value = res.data
      return
    }
  } catch {
    // fallback
  }

  oauthConfig.value = {
    google_redirect_uri: `${origin}/api/v1/email_accounts/oauth/callback/google`,
    microsoft_redirect_uri: `${origin}/api/v1/email_accounts/oauth/callback/microsoft`,
  }
}

async function refreshAll() {
  await Promise.all([
    loadProviders(),
    loadBindings(),
    loadPrompts(),
    loadEmailAccounts(),
  ])
}

onMounted(async () => {
  window.addEventListener('message', async (event) => {
    if (event.data?.type === 'oauth_success') {
      uiStore.showToast('Mailbox OAuth connected successfully!', 'success')
      await loadEmailAccounts()
    }
  })

  await Promise.all([
    loadProviders(),
    loadBindings(),
    loadPrompts(),
    loadEmailAccounts(),
    loadOAuthConfig(),
  ])
})
</script>

<template>
  <div class="page-container">
    <!-- Standardized Page Header -->
    <PageHeader
      title="Settings & Preferences"
      subtitle="Configure model bindings, thinking/reasoning parameters, custom prompt templates, AI providers, and email integrations."
      align="center"
    >
      <template #tabs>
        <div class="tab-bar">
          <button
            class="tab-pill"
            :class="{ active: activeTab === 'studio' }"
            @click="activeTab = 'studio'"
          >
            <Sparkles :size="15" />
            <span>Unified Task Studio</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'providers' }"
            @click="activeTab = 'providers'"
          >
            <Server :size="15" />
            <span>AI Providers ({{ providers.length }})</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'email_accounts' }"
            @click="activeTab = 'email_accounts'"
          >
            <Mail :size="15" />
            <span>Email Accounts ({{ emailAccounts.length }})</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'profile' }"
            @click="activeTab = 'profile'"
          >
            <UserCheck :size="15" />
            <span>My Profile / CV</span>
          </button>

          <button
            class="tab-pill"
            :class="{ active: activeTab === 'preferences' }"
            @click="activeTab = 'preferences'"
          >
            <SlidersHorizontal :size="15" />
            <span>Preferences</span>
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Scrollable Content Area -->
    <div class="settings-content-area">
      <div class="settings-inner-container">
        <!-- TAB 1: UNIFIED TASK STUDIO -->
        <TaskBindingsSettings
          v-if="activeTab === 'studio'"
          :providers="providers"
          :bindings="bindings"
          :prompts-list="promptsList"
          :global-binding="globalBinding"
          @refresh="refreshAll"
        />

        <!-- TAB 2: AI PROVIDERS -->
        <AIProvidersSettings
          v-else-if="activeTab === 'providers'"
          :providers="providers"
          @refresh="loadProviders"
        />

        <!-- TAB 3: EMAIL ACCOUNTS -->
        <EmailAccountsSettings
          v-else-if="activeTab === 'email_accounts'"
          :email-accounts="emailAccounts"
          :oauth-config="oauthConfig"
          @refresh="loadEmailAccounts"
        />

        <!-- TAB 4: PREFERENCES -->
        <div v-else-if="activeTab === 'preferences'" class="tab-content animate-fade-in">
          <div class="section-card">
            <div class="card-intro">
              <h3>System &amp; Workspace Preferences</h3>
              <p>Configure default currency for offers and salaries, interface view mode, and appearance settings.</p>
            </div>

            <div class="preferences-grid">
              <!-- Diagnostics Export Card -->
              <div class="preference-card">
                <div class="preference-header">
                  <div class="preference-icon text-primary">
                    <Save :size="18" />
                  </div>
                  <div>
                    <h4 class="preference-title">Diagnostics &amp; Telemetry</h4>
                    <p class="preference-desc">Monitor LangGraph execution telemetry, trace errors, and export zip logs.</p>
                  </div>
                </div>
                <div style="margin-top: 1rem; display: flex; gap: 8px;">
                  <button class="btn btn-primary" @click="$router.push('/diagnostics')">
                    View Dashboard
                  </button>
                  <button class="btn btn-outline" @click="exportDiagnostics" :disabled="isExporting">
                    <Loader2 v-if="isExporting" class="animate-spin" :size="14" />
                    <span v-else>Download Logs</span>
                  </button>
                </div>
              </div>

              <!-- Currency Setting Card -->
              <div class="preference-card">
                <div class="preference-header">
                  <div class="preference-icon text-primary">
                    <DollarSign :size="18" />
                  </div>
                  <div>
                    <h4 class="preference-title">Default System Currency</h4>
                    <p class="preference-desc">Used as the default currency for salary inputs, offer packages, and compensation ranges.</p>
                  </div>
                </div>

                <div class="currency-chips-grid">
                  <button
                    v-for="c in uiStore.SUPPORTED_CURRENCIES"
                    :key="c.code"
                    type="button"
                    class="currency-chip"
                    :class="{ active: uiStore.defaultCurrency === c.code }"
                    @click="uiStore.setDefaultCurrency(c.code)"
                  >
                    <span class="chip-code">{{ c.code }}</span>
                    <span class="chip-symbol">{{ c.symbol }}</span>
                  </button>
                </div>
              </div>

              <!-- Application Auto-Archiver Card -->
              <div class="preference-card">
                <div class="preference-header">
                  <div class="preference-icon text-primary">
                    <Archive :size="18" />
                  </div>
                  <div style="flex: 1;">
                    <div class="preference-header-between">
                      <h4 class="preference-title">Application Auto-Archiver</h4>
                      <label class="switch-toggle">
                        <input
                          type="checkbox"
                          :checked="uiStore.autoArchiveEnabled"
                          @change="e => uiStore.setAutoArchiveEnabled(e.target.checked)"
                        />
                        <span class="slider round"></span>
                      </label>
                    </div>
                    <p class="preference-desc">Automatically moves inactive applications in the Applied stage to the Archived/Rejected tab.</p>
                  </div>
                </div>

                <div v-if="uiStore.autoArchiveEnabled" style="margin-top: 12px;">
                  <div class="input-group">
                    <label class="input-label">Inactivity Threshold</label>
                    <select
                      class="form-input"
                      :value="uiStore.autoArchiveDays"
                      @change="e => uiStore.setAutoArchiveDays(parseInt(e.target.value))"
                    >
                      <option :value="14">14 days</option>
                      <option :value="30">30 days (Recommended)</option>
                      <option :value="45">45 days</option>
                      <option :value="60">60 days</option>
                      <option :value="90">90 days</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 5: CANDIDATE PROFILE / CV -->
        <div v-else-if="activeTab === 'profile'" class="tab-content animate-fade-in">
          <CandidateProfileView :is-embedded="true" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
  min-height: calc(100vh - var(--navbar-height));
  background-color: transparent;
  display: block;
}

.tab-bar {
  display: flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 3px;
  margin-top: 0;
  flex-shrink: 0;
  justify-content: center;
}

.tab-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-pill:hover {
  color: var(--text-main);
}

.tab-pill.active {
  background-color: var(--bg-elevated);
  color: var(--primary);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.settings-content-area {
  padding: 0;
  width: 100%;
}

.settings-inner-container {
  max-width: 100%;
  margin: 0 auto;
  width: 100%;
}

.section-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.preferences-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.preference-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preference-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.preference-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.preference-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-top: 2px;
}

.currency-chips-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.currency-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  border-radius: 4px;
  cursor: pointer;
}

.currency-chip.active {
  border-color: var(--primary);
  background-color: rgba(59, 130, 246, 0.12);
}

.chip-code {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
}

.chip-symbol {
  font-size: 11px;
  color: var(--primary);
  font-family: monospace;
}

.preference-header-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.switch-toggle {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  transition: 0.3s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: var(--text-muted);
  transition: 0.3s;
}

input:checked + .slider {
  background-color: var(--primary);
  border-color: var(--primary);
}

input:checked + .slider:before {
  transform: translateX(20px);
  background-color: #ffffff;
}

.slider.round {
  border-radius: 24px;
}

.slider.round:before {
  border-radius: 50%;
}
</style>
