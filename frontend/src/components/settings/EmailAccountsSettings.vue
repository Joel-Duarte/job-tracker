<script setup>
import { ref, computed } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import { EmailAccountsAPI, IntakeAPI } from '../../api/endpoints'
import {
  Mail,
  Plus,
  Trash2,
  Edit3,
  Loader2,
  Server,
  Lock,
  Key,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  Eye,
  EyeOff,
  Info,
  ChevronDown,
  ChevronUp,
  Save,
} from 'lucide-vue-next'

const props = defineProps({
  emailAccounts: {
    type: Array,
    required: true,
  },
  oauthConfig: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['refresh'])
const uiStore = useUIStore()

const loadingAccounts = ref(false)
const isEmailAccountModalOpen = ref(false)
const editingAccount = ref(null)
const syncingAccount = ref(null)
const showDeleteAccountModal = ref(false)
const accountToDelete = ref(null)
const isSavingAccount = ref(false)
const isDeletingAccount = ref(false)

const emailAccountForm = ref({
  name: '',
  provider_preset: 'gmail',
  auth_type: 'GMAIL_OAUTH',
  auth_method: 'oauth',
  username: '',
  app_password: '',
  imap_host: 'imap.gmail.com',
  imap_port: 993,
  folder: 'INBOX',
  client_id: '',
  client_secret: '',
  sync_interval: '1h',
  sync_schedule_hour: '09',
  sync_schedule_min: '00',
  sync_schedule_day: 'MON',
  is_active: true,
})

const showOAuthGuide = ref(false)
const showClientSecret = ref(false)
const copiedRedirectUri = ref(false)

async function copyRedirectUri(uri) {
  if (!uri) return
  try {
    await navigator.clipboard.writeText(uri)
    copiedRedirectUri.value = true
    uiStore.showToast('Redirect URI copied to clipboard!', 'success')
    setTimeout(() => {
      copiedRedirectUri.value = false
    }, 2500)
  } catch {
    uiStore.showToast('Could not copy to clipboard', 'error')
  }
}

function onProviderPresetChange(preset) {
  emailAccountForm.value.provider_preset = preset
  if (preset === 'gmail') {
    emailAccountForm.value.name = emailAccountForm.value.name || 'Gmail Inbox'
    emailAccountForm.value.imap_host = 'imap.gmail.com'
    emailAccountForm.value.imap_port = 993
    emailAccountForm.value.auth_type = emailAccountForm.value.auth_method === 'oauth' ? 'GMAIL_OAUTH' : 'IMAP'
  } else if (preset === 'outlook') {
    emailAccountForm.value.name = emailAccountForm.value.name || 'Outlook Inbox'
    emailAccountForm.value.imap_host = 'outlook.office365.com'
    emailAccountForm.value.imap_port = 993
    emailAccountForm.value.auth_type = emailAccountForm.value.auth_method === 'oauth' ? 'MS_GRAPH_OAUTH' : 'IMAP'
  } else {
    emailAccountForm.value.name = emailAccountForm.value.name || 'Work IMAP'
    emailAccountForm.value.auth_type = 'IMAP'
    emailAccountForm.value.auth_method = 'app_password'
  }
}

function onAuthMethodChange(method) {
  emailAccountForm.value.auth_method = method
  if (method === 'oauth') {
    if (emailAccountForm.value.provider_preset === 'gmail') {
      emailAccountForm.value.auth_type = 'GMAIL_OAUTH'
    } else if (emailAccountForm.value.provider_preset === 'outlook') {
      emailAccountForm.value.auth_type = 'MS_GRAPH_OAUTH'
    }
  } else {
    emailAccountForm.value.auth_type = 'IMAP'
  }
}

async function startOAuthLogin(providerName) {
  try {
    const prov = providerName || emailAccountForm.value.provider_preset
    const redirectUri = prov === 'outlook'
      ? props.oauthConfig.microsoft_redirect_uri
      : props.oauthConfig.google_redirect_uri

    const res = await EmailAccountsAPI.getOAuthUrl({
      provider: prov === 'outlook' ? 'microsoft' : 'google',
      client_id: emailAccountForm.value.client_id || undefined,
      redirect_uri: redirectUri || undefined,
    })
    if (res.data.auth_url) {
      window.open(res.data.auth_url, '_blank', 'width=600,height=700')
    } else {
      uiStore.showToast(res.data.message || 'No OAuth credentials configured.', 'info')
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to initiate OAuth', 'error')
  }
}

function openAddEmailAccountModal() {
  editingAccount.value = null
  emailAccountForm.value = {
    name: 'Gmail Inbox',
    provider_preset: 'gmail',
    auth_type: 'GMAIL_OAUTH',
    auth_method: 'oauth',
    username: '',
    app_password: '',
    imap_host: 'imap.gmail.com',
    imap_port: 993,
    folder: 'INBOX',
    client_id: '',
    client_secret: '',
    sync_interval: '1h',
    sync_schedule_hour: '09',
    sync_schedule_min: '00',
    sync_schedule_day: 'MON',
    is_active: true,
  }
  isEmailAccountModalOpen.value = true
}

function openEditEmailAccountModal(acc) {
  editingAccount.value = acc
  let preset = 'custom'
  let method = 'app_password'
  if (acc.auth_type === 'GMAIL_OAUTH') {
    preset = 'gmail'
    method = 'oauth'
  } else if (acc.auth_type === 'MS_GRAPH_OAUTH') {
    preset = 'outlook'
    method = 'oauth'
  } else if (acc.imap_host?.includes('gmail')) {
    preset = 'gmail'
    method = 'app_password'
  } else if (acc.imap_host?.includes('office365') || acc.imap_host?.includes('outlook')) {
    preset = 'outlook'
    method = 'app_password'
  }

  const [rawH, rawM] = (acc.sync_schedule_time || '09:00').split(':')

  emailAccountForm.value = {
    name: acc.name,
    provider_preset: preset,
    auth_type: acc.auth_type || 'IMAP',
    auth_method: method,
    username: acc.username,
    app_password: '',
    imap_host: acc.imap_host || '',
    imap_port: acc.imap_port || 993,
    folder: acc.folder || 'INBOX',
    client_id: acc.client_id || '',
    client_secret: '',
    sync_interval: acc.sync_interval || '1h',
    sync_schedule_hour: rawH || '09',
    sync_schedule_min: rawM || '00',
    sync_schedule_day: acc.sync_schedule_day || 'MON',
    is_active: acc.is_active !== false,
  }
  isEmailAccountModalOpen.value = true
}

async function saveEmailAccount() {
  isSavingAccount.value = true
  try {
    const payload = {
      name: emailAccountForm.value.name.trim(),
      auth_type: emailAccountForm.value.auth_type,
      username: emailAccountForm.value.username.trim(),
      app_password: emailAccountForm.value.app_password || undefined,
      imap_host: emailAccountForm.value.imap_host.trim(),
      imap_port: Number(emailAccountForm.value.imap_port),
      folder: emailAccountForm.value.folder.trim() || 'INBOX',
      client_id: emailAccountForm.value.client_id.trim() || undefined,
      client_secret: emailAccountForm.value.client_secret.trim() || undefined,
      sync_interval: emailAccountForm.value.sync_interval,
      sync_schedule_time: `${emailAccountForm.value.sync_schedule_hour}:${emailAccountForm.value.sync_schedule_min}`,
      sync_schedule_day: emailAccountForm.value.sync_schedule_day,
      is_active: emailAccountForm.value.is_active,
    }

    if (editingAccount.value) {
      await EmailAccountsAPI.update(editingAccount.value.id, payload)
      uiStore.showToast('Email account updated successfully', 'success')
    } else {
      await EmailAccountsAPI.create(payload)
      uiStore.showToast('Email account connected successfully', 'success')
    }
    isEmailAccountModalOpen.value = false
    emit('refresh')
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || err.message || 'Failed to save email account', 'error')
  } finally {
    isSavingAccount.value = false
  }
}

async function triggerSync(acc) {
  syncingAccount.value = acc.id
  try {
    const res = await IntakeAPI.syncAccount({
      account_id: acc.id,
      since_date: '2024-01-01',
    })
    uiStore.showToast(res.data.message || `Mailbox sync initiated for ${acc.name}!`, 'success')
    emit('refresh')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to sync mailbox', 'error')
  } finally {
    syncingAccount.value = null
  }
}

function openDeleteAccountModal(acc) {
  accountToDelete.value = acc
  showDeleteAccountModal.value = true
}

async function confirmDeleteAccount() {
  if (!accountToDelete.value) return
  isDeletingAccount.value = true
  try {
    await EmailAccountsAPI.delete(accountToDelete.value.id)
    uiStore.showToast('Email account removed', 'info')
    showDeleteAccountModal.value = false
    accountToDelete.value = null
    emit('refresh')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to delete account', 'error')
  } finally {
    isDeletingAccount.value = false
  }
}
</script>

<template>
  <div class="section-card">
    <div class="section-header-row">
      <div>
        <h3>Connected Mailboxes &amp; Sync Schedule</h3>
        <p>Connect mailboxes via 1-Click OAuth (Google / Microsoft) or IMAP, and configure automated background sync schedules.</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="openAddEmailAccountModal">
        <Plus :size="15" />
        <span>Connect Account</span>
      </button>
    </div>

    <div class="accounts-grid">
      <div v-for="acc in emailAccounts" :key="acc.id" class="account-card">
        <div class="account-card-header">
          <div class="account-title-row">
            <Mail :size="16" class="text-primary" />
            <span class="account-name">{{ acc.name }}</span>
          </div>
          <span class="badge badge-applied font-mono">{{ acc.auth_type }}</span>
        </div>

        <div class="account-card-body">
          <div class="meta-row">
            <span class="meta-k">Username:</span>
            <span class="meta-v font-mono">{{ acc.username }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-k">Folder:</span>
            <span class="meta-v font-mono">{{ acc.folder }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-k">Sync Interval:</span>
            <span class="meta-v font-mono">{{ acc.sync_interval || '1h' }}</span>
          </div>
        </div>

        <div class="account-actions">
          <button
            class="btn btn-primary btn-sm"
            :disabled="syncingAccount === acc.id"
            @click="triggerSync(acc)"
          >
            <Loader2 v-if="syncingAccount === acc.id" class="animate-spin" :size="14" />
            <RefreshCw v-else :size="14" />
            <span>{{ syncingAccount === acc.id ? 'Syncing...' : 'Sync Now' }}</span>
          </button>

          <button class="btn btn-secondary btn-sm" @click="openEditEmailAccountModal(acc)">
            <Edit3 :size="14" />
            <span>Edit</span>
          </button>

          <button class="btn btn-danger btn-sm" @click="openDeleteAccountModal(acc)">
            <Trash2 :size="14" />
          </button>
        </div>
      </div>

      <div v-if="emailAccounts.length === 0" class="empty-state">
        <Mail :size="36" class="empty-icon text-muted mb-2" />
        <h4 class="empty-title">No Mailboxes Connected</h4>
        <p class="empty-desc">
          Connect your Gmail, Outlook, or IMAP account using the <strong>Connect Account</strong> button above to automatically scan incoming recruitment communications and update your application pipeline.
        </p>
      </div>
    </div>

    <!-- EMAIL ACCOUNT MODAL -->
    <div v-if="isEmailAccountModalOpen" class="modal-backdrop" @click.self="isEmailAccountModalOpen = false">
      <div class="modal-card modal-lg animate-fade-in">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingAccount ? 'Edit Account: ' + editingAccount.name : 'Connect Email Account' }}</h3>
          <button class="btn-close" @click="isEmailAccountModalOpen = false">×</button>
        </div>

        <div class="modal-body">
          <!-- Step 1: Provider Presets -->
          <div class="input-group">
            <label class="input-label">Select Email Provider</label>
            <div class="provider-presets-grid">
              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'gmail' }"
                @click="onProviderPresetChange('gmail')"
              >
                <div class="preset-icon gmail-icon"><Mail :size="18" /></div>
                <div class="preset-info">
                  <span class="preset-name">Google Gmail</span>
                  <span class="preset-sub">OAuth2 or App Password</span>
                </div>
              </button>

              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'outlook' }"
                @click="onProviderPresetChange('outlook')"
              >
                <div class="preset-icon outlook-icon"><Mail :size="18" /></div>
                <div class="preset-info">
                  <span class="preset-name">Microsoft Outlook</span>
                  <span class="preset-sub">MS Graph OAuth2 or IMAP</span>
                </div>
              </button>

              <button
                type="button"
                class="provider-preset-card"
                :class="{ active: emailAccountForm.provider_preset === 'custom' }"
                @click="onProviderPresetChange('custom')"
              >
                <div class="preset-icon imap-icon"><Server :size="18" /></div>
                <div class="preset-info">
                  <span class="preset-name">Custom IMAP</span>
                  <span class="preset-sub">iCloud, Fastmail, Yahoo</span>
                </div>
              </button>
            </div>
          </div>

          <!-- Step 2: Auth Method Toggle (if Gmail or Outlook) -->
          <div v-if="emailAccountForm.provider_preset !== 'custom'" class="input-group">
            <label class="input-label">Authentication Method</label>
            <div class="auth-method-toggle">
              <button
                type="button"
                class="auth-toggle-btn"
                :class="{ active: emailAccountForm.auth_method === 'oauth' }"
                @click="onAuthMethodChange('oauth')"
              >
                <Lock :size="14" />
                <span>OAuth2 Connect <span class="auth-badge recommended">Recommended</span></span>
              </button>
              <button
                type="button"
                class="auth-toggle-btn"
                :class="{ active: emailAccountForm.auth_method === 'app_password' }"
                @click="onAuthMethodChange('app_password')"
              >
                <Key :size="14" />
                <span>Email &amp; App Password</span>
              </button>
            </div>
          </div>

          <!-- OAuth2 Mode Fields & Guide -->
          <template v-if="emailAccountForm.auth_method === 'oauth' && emailAccountForm.provider_preset !== 'custom'">
            <!-- Authorized Redirect URI Box -->
            <div class="oauth-redirect-box">
              <div class="label-with-hint mb-1">
                <span class="redirect-uri-label">Authorized Redirect URI (Copy to Console)</span>
                <button
                  type="button"
                  class="btn-copy-uri"
                  @click="copyRedirectUri(emailAccountForm.provider_preset === 'outlook' ? oauthConfig.microsoft_redirect_uri : oauthConfig.google_redirect_uri)"
                >
                  <Check v-if="copiedRedirectUri" :size="12" class="text-success" />
                  <Copy v-else :size="12" />
                  <span>{{ copiedRedirectUri ? 'Copied!' : 'Copy URI' }}</span>
                </button>
              </div>
              <div class="uri-display font-mono">
                {{ emailAccountForm.provider_preset === 'outlook' ? oauthConfig.microsoft_redirect_uri : oauthConfig.google_redirect_uri }}
              </div>
            </div>

            <!-- Collapsible OAuth Setup Guide -->
            <div class="oauth-guide-card">
              <button
                type="button"
                class="guide-toggle-header"
                @click="showOAuthGuide = !showOAuthGuide"
              >
                <div class="flex items-center gap-2">
                  <Info :size="14" class="text-primary" />
                  <span class="font-semibold text-xs text-main">
                    {{ emailAccountForm.provider_preset === 'gmail' ? 'Google Cloud OAuth Setup Guide' : 'Microsoft Entra ID / Azure OAuth Setup Guide' }}
                  </span>
                </div>
                <component :is="showOAuthGuide ? ChevronUp : ChevronDown" :size="14" class="text-muted" />
              </button>

              <div v-if="showOAuthGuide" class="guide-content animate-fade-in">
                <ol v-if="emailAccountForm.provider_preset === 'gmail'" class="guide-steps-list">
                  <li>
                    Go to the <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener" class="guide-link">Google Cloud Console <ExternalLink :size="10" /></a> and create or select a project.
                  </li>
                  <li>Enable the <strong>Gmail API</strong> in APIs &amp; Services &gt; Library.</li>
                  <li>In <strong>OAuth consent screen</strong>, select User Type: <em>External</em>, and add the scopes: <code>https://www.googleapis.com/auth/gmail.readonly</code> and <code>https://www.googleapis.com/auth/userinfo.email</code>.</li>
                  <li>In <strong>Credentials</strong>, click <em>Create Credentials</em> &gt; <em>OAuth Client ID</em> (Application type: <strong>Web application</strong>).</li>
                  <li>Add the <strong>Authorized Redirect URI</strong> displayed above, then copy your Client ID and Client Secret below.</li>
                </ol>

                <ol v-else class="guide-steps-list">
                  <li>
                    Open the <a href="https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade" target="_blank" rel="noopener" class="guide-link">Azure Portal / Entra ID <ExternalLink :size="10" /></a> &gt; <strong>App registrations</strong> &gt; <strong>New registration</strong>.
                  </li>
                  <li>Set Supported account types to <em>Accounts in any organizational directory and personal Microsoft accounts</em>.</li>
                  <li>Set Redirect URI Platform to <strong>Web</strong> and paste the Authorized Redirect URI shown above.</li>
                  <li>Under <strong>API permissions</strong>, add Delegated permissions: <code>Mail.Read</code>, <code>User.Read</code>, and <code>offline_access</code>.</li>
                  <li>Under <strong>Certificates &amp; secrets</strong>, generate a new Client Secret and paste the value below.</li>
                </ol>
              </div>
            </div>

            <!-- OAuth Form Fields -->
            <div class="form-grid-2">
              <div class="input-group">
                <label class="input-label">Account Label *</label>
                <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Personal Gmail" class="form-input" required />
              </div>

              <div class="input-group">
                <label class="input-label">Sync Interval</label>
                <select v-model="emailAccountForm.sync_interval" class="form-input">
                  <option value="15m">Every 15 minutes</option>
                  <option value="30m">Every 30 minutes</option>
                  <option value="1h">Every hour (Recommended)</option>
                  <option value="6h">Every 6 hours</option>
                  <option value="24h">Once a day</option>
                  <option value="MANUAL">Manual Sync Only</option>
                </select>
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">OAuth Client ID *</label>
              <input
                v-model="emailAccountForm.client_id"
                type="text"
                :placeholder="emailAccountForm.provider_preset === 'gmail' ? 'e.g. 12345-abc.apps.googleusercontent.com' : 'e.g. 00000000-0000-0000-0000-000000000000'"
                class="form-input font-mono"
                required
              />
            </div>

            <div class="input-group">
              <label class="input-label">OAuth Client Secret *</label>
              <div class="input-with-action">
                <input
                  v-model="emailAccountForm.client_secret"
                  :type="showClientSecret ? 'text' : 'password'"
                  placeholder="Enter client secret"
                  class="form-input font-mono flex-1"
                  required
                />
                <button
                  type="button"
                  class="btn-input-action"
                  @click="showClientSecret = !showClientSecret"
                  tabindex="-1"
                >
                  <component :is="showClientSecret ? EyeOff : Eye" :size="14" />
                </button>
              </div>
            </div>

            <div class="input-group">
              <div class="label-with-hint">
                <label class="input-label">Email Address</label>
                <span class="text-xs text-muted">Auto-resolved upon OAuth login</span>
              </div>
              <input
                v-model="emailAccountForm.username"
                type="email"
                placeholder="Optional (populated automatically on sign in)"
                class="form-input"
              />
            </div>

            <div class="modal-actions mt-4">
              <button class="btn btn-secondary" @click="isEmailAccountModalOpen = false">Cancel</button>
              <button class="btn btn-secondary" :disabled="isSavingAccount" @click="saveEmailAccount">
                <Save :size="14" />
                <span>Save Credentials</span>
              </button>
              <button class="btn btn-primary" @click="startOAuthLogin(emailAccountForm.provider_preset)">
                <Lock :size="14" />
                <span>Authorize &amp; Connect Mailbox</span>
              </button>
            </div>
          </template>

          <!-- App Password / Direct IMAP Mode -->
          <template v-else>
            <div class="app-password-callout">
              <Info :size="14" class="text-primary flex-shrink-0 mt-0.5" />
              <div class="text-xs text-secondary leading-relaxed">
                <span v-if="emailAccountForm.provider_preset === 'gmail'">
                  Google requires an <strong>App Password</strong> if 2-Step Verification is enabled. Generate one at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" class="guide-link">Google Account Security <ExternalLink :size="10" /></a>.
                </span>
                <span v-else-if="emailAccountForm.provider_preset === 'outlook'">
                  Microsoft accounts with 2FA require generating an App Password in your Microsoft Account Security settings.
                </span>
                <span v-else>
                  Enter your standard IMAP host, port (default 993 SSL), and mailbox credentials.
                </span>
              </div>
            </div>

            <div class="form-grid-2">
              <div class="input-group">
                <label class="input-label">Account Label *</label>
                <input v-model="emailAccountForm.name" type="text" placeholder="e.g. Work Mailbox" class="form-input" required />
              </div>

              <div class="input-group">
                <label class="input-label">Email Address / Login *</label>
                <input v-model="emailAccountForm.username" type="email" placeholder="user@domain.com" class="form-input" required />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">App Password / Password *</label>
              <div class="input-with-action">
                <input
                  v-model="emailAccountForm.app_password"
                  :type="showClientSecret ? 'text' : 'password'"
                  placeholder="••••••••••••••••"
                  class="form-input font-mono flex-1"
                  required
                />
                <button
                  type="button"
                  class="btn-input-action"
                  @click="showClientSecret = !showClientSecret"
                  tabindex="-1"
                >
                  <component :is="showClientSecret ? EyeOff : Eye" :size="14" />
                </button>
              </div>
            </div>

            <div class="form-grid-3">
              <div class="input-group">
                <label class="input-label">IMAP Host *</label>
                <input v-model="emailAccountForm.imap_host" type="text" placeholder="imap.gmail.com" class="form-input font-mono" required />
              </div>

              <div class="input-group">
                <label class="input-label">IMAP Port *</label>
                <input v-model.number="emailAccountForm.imap_port" type="number" placeholder="993" class="form-input font-mono" required />
              </div>

              <div class="input-group">
                <label class="input-label">Mailbox Folder *</label>
                <input v-model="emailAccountForm.folder" type="text" placeholder="INBOX" class="form-input font-mono" required />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">Sync Interval</label>
              <select v-model="emailAccountForm.sync_interval" class="form-input">
                <option value="15m">Every 15 minutes</option>
                <option value="30m">Every 30 minutes</option>
                <option value="1h">Every hour (Recommended)</option>
                <option value="6h">Every 6 hours</option>
                <option value="24h">Once a day</option>
                <option value="MANUAL">Manual Sync Only</option>
              </select>
            </div>

            <div class="modal-actions mt-4">
              <button class="btn btn-secondary" @click="isEmailAccountModalOpen = false">Cancel</button>
              <button class="btn btn-primary" :disabled="isSavingAccount" @click="saveEmailAccount">
                <Save :size="14" />
                <span>{{ editingAccount ? 'Update Account' : 'Save & Connect Account' }}</span>
              </button>
            </div>
          </template>
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

.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.account-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.account-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.account-card-body {
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

.account-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 4px;
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

.empty-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.empty-desc {
  max-width: 480px;
  line-height: 1.5;
  color: var(--text-secondary);
  font-size: 12px;
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

.modal-card.modal-lg {
  max-width: 580px;
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

.provider-presets-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.provider-preset-card {
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  border-radius: var(--radius-sm);
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 6px;
  cursor: pointer;
}

.provider-preset-card.active {
  border-color: var(--primary);
  background-color: rgba(59, 130, 246, 0.08);
}

.preset-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
}

.preset-sub {
  font-size: 9px;
  color: var(--text-muted);
}

.auth-method-toggle {
  display: flex;
  gap: 6px;
}

.auth-toggle-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
}

.auth-toggle-btn.active {
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}

.auth-badge.recommended {
  background-color: var(--status-interview-text);
  color: #000;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
}

.oauth-redirect-box {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.redirect-uri-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.btn-copy-uri {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-copy-uri:hover {
  background-color: var(--bg-elevated);
  border-color: var(--primary);
  color: var(--primary);
}

.uri-display {
  font-size: 11px;
  color: var(--primary);
  word-break: break-all;
  user-select: all;
  background-color: var(--bg-surface);
  padding: 6px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  margin-top: 4px;
}

.oauth-guide-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background-color: var(--bg-main);
  overflow: hidden;
}

.guide-toggle-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.guide-toggle-header:hover {
  background-color: var(--bg-surface);
}

.guide-content {
  padding: 10px 14px 14px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--bg-surface);
}

.guide-steps-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.guide-steps-list code {
  font-family: monospace;
  font-size: 10px;
  background-color: var(--bg-main);
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--text-main);
  border: 1px solid var(--border-color);
}

.guide-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.input-with-action {
  display: flex;
  align-items: center;
  position: relative;
}

.btn-input-action {
  position: absolute;
  right: 6px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
}

.app-password-callout {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background-color: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 10px;
}
</style>
