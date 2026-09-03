<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import { useQueueStore } from '../../stores/queueStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { StagingAPI, ActionItemsAPI, SystemAPI } from '../../api/endpoints'
import ThemePalettePopover from './ThemePalettePopover.vue'
import {
  Briefcase,
  Building2,
  Layers,
  Bot,
  Settings,
  Plus,
  Palette,
  Inbox,
  Sparkles,
  FileInput,
  UserCheck,
  CheckSquare,
  Cpu,
  Mail,
  BarChart3,
  Activity,
  RefreshCw,
  AlertTriangle,
  Menu,
  X,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()
const queueStore = useQueueStore()
const appStore = useApplicationsStore()

const pendingStagingCount = computed(() => uiStore.pendingStagingCount)
const pendingTasksCount = ref(0)

const readyAssessmentsCount = computed(() => queueStore.readyAssessmentsCount)

const isHealthPopoverOpen = ref(false)
const popoverContainerRef = ref(null)
const isMobileMenuOpen = ref(false)

function toggleMobileMenu() {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

function closeMobileMenu() {
  isMobileMenuOpen.value = false
}

const pillLabel = computed(() => {
  switch (uiStore.aiStatus) {
    case 'healthy':
      return `${uiStore.aiActiveProviderName || 'AI Online'} • ${Math.round(uiStore.aiLatencyMs)}ms`
    case 'degraded':
      return `${uiStore.aiActiveProviderName || 'AI Busy'} • ${Math.round(uiStore.aiLatencyMs)}ms`
    case 'offline':
      return 'AI Offline'
    case 'unconfigured':
    default:
      return 'No AI Configured'
  }
})

const pillTitle = computed(() => {
  if (uiStore.aiStatus === 'healthy') return `AI Provider ${uiStore.aiActiveProviderName} is Healthy (${Math.round(uiStore.aiLatencyMs)}ms)`
  if (uiStore.aiStatus === 'degraded') return `AI Provider ${uiStore.aiActiveProviderName} is Degraded (${Math.round(uiStore.aiLatencyMs)}ms)`
  if (uiStore.aiStatus === 'offline') return `AI Provider Offline: ${uiStore.aiErrorMessage || 'Unreachable'}`
  return 'No AI Provider Configured'
})

async function handlePingNow() {
  await uiStore.checkAIHealth()
}

function goToAISettings() {
  isHealthPopoverOpen.value = false
  uiStore.setLastNonSettingsRoute(route.fullPath)
  router.push('/settings')
}

function handleClickOutside(event) {
  if (popoverContainerRef.value && !popoverContainerRef.value.contains(event.target)) {
    isHealthPopoverOpen.value = false
  }
}

let badgeInterval = null

async function fetchBadgeCounts() {
  try {
    const res = await SystemAPI.getBadgeCounts()
    if (res?.data) {
      uiStore.setPendingStagingCount(res.data.staging_count)
      pendingTasksCount.value = res.data.pending_action_items_count || 0
      if (res.data.active_queue_tasks_count > 0 || queueStore.tasks.length === 0) {
        await queueStore.fetchTasks(true)
      }
      await appStore.checkAndSyncWithBadges(res.data)
    }
  } catch (err) {
    // Fallback: silent ignore network errors
  }
}

function handleVisibilityChange() {
  if (document.hidden) {
    if (badgeInterval) {
      clearInterval(badgeInterval)
      badgeInterval = null
    }
  } else {
    fetchBadgeCounts()
    if (!badgeInterval) {
      badgeInterval = setInterval(fetchBadgeCounts, 10000)
    }
  }
}

function getRouteTitle(path) {
  if (!path || typeof path !== 'string') return 'Applications'
  const cleanPath = path.split('?')[0]
  switch (cleanPath) {
    case '/':
    case '/applications':
      return 'Applications'
    case '/companies':
      return 'Companies'
    case '/assessments':
    case '/intake':
      return 'Assessments'
    case '/tasks':
      return 'Tasks'
    case '/analytics':
      return 'Analytics'
    case '/staging':
      return 'Staging'
    case '/chat':
      return 'Agent'
    case '/diagnostics':
      return 'Diagnostics'
    case '/queue':
      return 'Queue'
    default:
      return 'Applications'
  }
}

const settingsTooltip = computed(() => {
  if (!route.path.startsWith('/settings')) {
    return 'Settings'
  }
  const dest = uiStore.lastNonSettingsRoute || route.query.returnTo
  if (dest && typeof dest === 'string' && !dest.startsWith('/settings')) {
    return `Back to ${getRouteTitle(dest)}`
  }
  return 'Close Settings (Return)'
})

function handleSettingsClick() {
  if (!route.path.startsWith('/settings')) {
    uiStore.setLastNonSettingsRoute(route.fullPath)
    router.push('/settings')
  } else {
    let dest = uiStore.lastNonSettingsRoute || route.query.returnTo
    uiStore.clearLastNonSettingsRoute()
    if (dest && typeof dest === 'string' && !dest.startsWith('/settings')) {
      router.push(dest)
    } else {
      router.push('/')
    }
  }
}

watch(
  () => route.path,
  (newPath, oldPath) => {
    isMobileMenuOpen.value = false
    if (oldPath && oldPath.startsWith('/settings') && !newPath.startsWith('/settings')) {
      uiStore.clearLastNonSettingsRoute()
    }
  }
)

onMounted(() => {
  uiStore.initAIHealthMonitor()
  fetchBadgeCounts()
  badgeInterval = setInterval(fetchBadgeCounts, 10000)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (badgeInterval) {
    clearInterval(badgeInterval)
    badgeInterval = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <header class="navbar">
    <div class="nav-left">
      <!-- Mobile Hamburger Menu Trigger (Far Left on Mobile) -->
      <button
        class="btn-icon mobile-menu-trigger"
        @click="toggleMobileMenu"
        title="Toggle navigation menu"
      >
        <Menu v-if="!isMobileMenuOpen" :size="20" />
        <X v-else :size="20" />
      </button>

      <router-link to="/" class="nav-brand" @click="uiStore.clearLastNonSettingsRoute()">
        <div class="brand-icon">
          <Sparkles :size="18" class="text-primary" />
        </div>
        <span class="brand-title">JobTracker</span>
      </router-link>

      <nav class="nav-links">
        <router-link
          to="/"
          class="nav-link"
          :class="{ active: route.path === '/' }"
          @click="uiStore.clearLastNonSettingsRoute()"
        >
          <Briefcase :size="16" />
          <span>Applications</span>
        </router-link>

        <router-link
          to="/assessments"
          class="nav-link"
          :class="{ active: ['/assessments', '/intake'].includes(route.path) }"
          @click="uiStore.clearLastNonSettingsRoute()"
        >
          <Sparkles :size="16" />
          <span>Assessments</span>
          <span v-if="readyAssessmentsCount > 0" class="nav-badge" title="Ready for review">
            {{ readyAssessmentsCount }}
          </span>
        </router-link>

        <router-link
          to="/tasks"
          class="nav-link"
          :class="{ active: route.path === '/tasks' }"
          @click="uiStore.clearLastNonSettingsRoute()"
        >
          <CheckSquare :size="16" />
          <span>Tasks</span>
          <span v-if="pendingTasksCount > 0" class="nav-badge">
            {{ pendingTasksCount }}
          </span>
        </router-link>

        <router-link
          to="/companies"
          class="nav-link"
          :class="{ active: route.path.startsWith('/companies') }"
          @click="uiStore.clearLastNonSettingsRoute()"
        >
          <Building2 :size="16" />
          <span>Companies</span>
        </router-link>

        

        <router-link
          v-if="uiStore.enableEmailIntake"
          to="/staging"
          class="nav-link"
          :class="{ active: route.path === '/staging' }"
          @click="uiStore.clearLastNonSettingsRoute()"
        >
          <Inbox :size="16" />
          <span>Staging</span>
          <span v-if="pendingStagingCount > 0" class="nav-badge">
            {{ pendingStagingCount }}
          </span>
        </router-link>

        <router-link
          to="/analytics"
          class="nav-link"
          :class="{ active: route.path === '/analytics' }"
          @click="uiStore.clearLastNonSettingsRoute()"
        >
          <BarChart3 :size="16" />
          <span>Analytics</span>
        </router-link>

        <router-link
          to="/chat"
          class="nav-link"
          :class="{ active: route.path === '/chat' }"
          @click="uiStore.clearLastNonSettingsRoute()"
        >
          <Bot :size="16" />
          <span>Agent</span>
        </router-link>

      </nav>
    </div>

    <div class="nav-right">
      <!-- Demo Mode Pill Badge -->
      <button
        v-if="uiStore.isDemoMode"
        class="demo-mode-badge"
        @click="goToAISettings"
        title="Client Demo Mode Active - Running locally in browser. Click to manage in Settings."
      >
        <Sparkles :size="12" class="text-primary" />
        <span>DEMO MODE</span>
      </button>

      <!-- AI Health Monitoring Pill & Diagnostic Popover -->
      <div class="health-pill-container" ref="popoverContainerRef">
        <button
          class="health-pill"
          :class="`status-${uiStore.aiStatus}`"
          @click.stop="isHealthPopoverOpen = !isHealthPopoverOpen"
          :title="pillTitle"
        >
          <span class="status-dot"></span>
          <span class="pill-text">{{ pillLabel }}</span>
        </button>

        <div v-if="isHealthPopoverOpen" class="ai-health-popover" @click.stop>
          <div class="popover-header">
            <div class="popover-title">
              <Activity :size="15" />
              <span>AI Engine Health</span>
            </div>
            <span class="status-badge" :class="`badge-${uiStore.aiStatus}`">
              {{ uiStore.aiStatus.toUpperCase() }}
            </span>
          </div>

          <div class="popover-body">
            <div class="info-row">
              <span class="info-label">Active Provider</span>
              <span class="info-value font-medium">{{ uiStore.aiActiveProviderName || 'None Configured' }}</span>
            </div>
            <div class="info-row" v-if="uiStore.aiProviderType || uiStore.aiModelName">
              <span class="info-label">Type & Model</span>
              <span class="info-value font-mono">{{ uiStore.aiProviderType || '-' }} / {{ uiStore.aiModelName || '-' }}</span>
            </div>
            <div class="info-row" v-if="uiStore.aiBaseUrl">
              <span class="info-label">Base URL</span>
              <span class="info-value font-mono text-xs">{{ uiStore.aiBaseUrl }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Latency</span>
              <span class="info-value font-mono">{{ uiStore.aiLatencyMs > 0 ? `${Math.round(uiStore.aiLatencyMs)} ms` : 'N/A' }}</span>
            </div>
            <div class="info-row highlight-row">
              <span class="info-label">Auto-Failover Target</span>
              <span class="info-value text-primary font-medium">
                {{ uiStore.aiFallbackProviderName ? uiStore.aiFallbackProviderName : 'None Configured' }}
              </span>
            </div>
            <div v-if="uiStore.aiErrorMessage" class="error-box">
              <AlertTriangle :size="14" class="text-danger flex-shrink-0" />
              <span>{{ uiStore.aiErrorMessage }}</span>
            </div>
          </div>

          <div class="popover-footer">
            <button
              class="btn btn-sm btn-secondary"
              @click="handlePingNow"
              :disabled="uiStore.isCheckingAIHealth"
            >
              <RefreshCw :size="13" :class="{ 'spin': uiStore.isCheckingAIHealth }" />
              <span>{{ uiStore.isCheckingAIHealth ? 'Testing...' : 'Ping Now' }}</span>
            </button>
            <button
              class="btn btn-sm btn-outline"
              @click="goToAISettings"
            >
              <Settings :size="13" />
              <span>Configure in Settings</span>
            </button>
          </div>
        </div>
      </div>

      <button
        class="btn btn-primary btn-ingest"
        @click="uiStore.openJobIntakeModal"
        title="Ingest job URL or specification text for AI qualification"
      >
        <Sparkles :size="14" />
        <span>Job Intake</span>
      </button>

      <button
        v-if="uiStore.enableEmailIntake"
        class="btn btn-primary btn-ingest"
        @click="uiStore.openIngestModal"
        title="Sync email accounts, paste threads, or upload message files"
      >
        <Mail :size="14" />
        <span>Email Intake</span>
      </button>

      <button
        class="btn-icon theme-toggle"
        :class="{ active: uiStore.isThemePopoverOpen }"
        @click="uiStore.toggleThemePopover"
        :title="'Theme & Palette Studio (Current: ' + uiStore.theme + ')'"
      >
        <Palette :size="17" />
      </button>

      <button
        class="btn-icon"
        :class="{ active: route.path.startsWith('/settings') }"
        @click="handleSettingsClick"
        :title="settingsTooltip"
      >
        <Settings :size="17" />
      </button>

      <ThemePalettePopover />
    </div>

    <!-- Mobile Slide-out Navigation Drawer -->
    <Teleport to="body">
      <Transition name="drawer-fade">
        <div v-if="isMobileMenuOpen" class="mobile-drawer-backdrop" @click="closeMobileMenu" />
      </Transition>
      <Transition name="drawer-slide-left">
        <div v-if="isMobileMenuOpen" class="mobile-drawer">
          <div class="mobile-drawer-header">
            <router-link to="/" class="nav-brand" @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()">
              <div class="brand-icon">
                <Sparkles :size="18" class="text-primary" />
              </div>
              <span class="brand-title">JobTracker</span>
            </router-link>
            <button class="btn-icon" @click="closeMobileMenu" title="Close menu">
              <X :size="20" />
            </button>
          </div>

          <nav class="mobile-drawer-nav">
            <router-link
              to="/"
              class="mobile-nav-link"
              :class="{ active: route.path === '/' }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <Briefcase :size="18" />
              <span>Applications</span>
            </router-link>

            <router-link
              to="/assessments"
              class="mobile-nav-link"
              :class="{ active: ['/assessments', '/intake'].includes(route.path) }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <Sparkles :size="18" />
              <span>Assessments</span>
              <span v-if="readyAssessmentsCount > 0" class="nav-badge">
                {{ readyAssessmentsCount }}
              </span>
            </router-link>

            <router-link
              to="/tasks"
              class="mobile-nav-link"
              :class="{ active: route.path === '/tasks' }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <CheckSquare :size="18" />
              <span>Tasks</span>
              <span v-if="pendingTasksCount > 0" class="nav-badge">
                {{ pendingTasksCount }}
              </span>
            </router-link>

            <router-link
              to="/companies"
              class="mobile-nav-link"
              :class="{ active: route.path.startsWith('/companies') }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <Building2 :size="18" />
              <span>Companies</span>
            </router-link>

            <router-link
              to="/queue"
              class="mobile-nav-link"
              :class="{ active: route.path === '/queue' }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <Cpu :size="18" />
              <span>Evaluation Queue</span>
              <span v-if="queueStore.notificationCount > 0" class="nav-badge">
                {{ queueStore.notificationCount }}
              </span>
            </router-link>

            <router-link
              v-if="uiStore.enableEmailIntake"
              to="/staging"
              class="mobile-nav-link"
              :class="{ active: route.path === '/staging' }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <Inbox :size="18" />
              <span>Staging</span>
              <span v-if="pendingStagingCount > 0" class="nav-badge">
                {{ pendingStagingCount }}
              </span>
            </router-link>

            <router-link
              to="/analytics"
              class="mobile-nav-link"
              :class="{ active: route.path === '/analytics' }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <BarChart3 :size="18" />
              <span>Analytics</span>
            </router-link>

            <router-link
              to="/chat"
              class="mobile-nav-link"
              :class="{ active: route.path === '/chat' }"
              @click="closeMobileMenu(); uiStore.clearLastNonSettingsRoute()"
            >
              <Bot :size="18" />
              <span>Agent</span>
            </router-link>

            <button
              class="mobile-nav-link btn-settings-mobile"
              :class="{ active: route.path.startsWith('/settings') }"
              @click="closeMobileMenu(); handleSettingsClick()"
            >
              <Settings :size="18" />
              <span>Settings</span>
            </button>
          </nav>

          <div class="mobile-drawer-footer">
            <button
              class="btn btn-primary w-full"
              @click="closeMobileMenu(); uiStore.openJobIntakeModal()"
            >
              <Sparkles :size="16" />
              <span>Job Intake</span>
            </button>
            <button
              v-if="uiStore.enableEmailIntake"
              class="btn btn-secondary w-full"
              @click="closeMobileMenu(); uiStore.openIngestModal()"
            >
              <Mail :size="16" />
              <span>Email Intake</span>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </header>
</template>

<style scoped>
.demo-mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  color: var(--primary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  padding: 3px 8px;
  border-radius: var(--radius-full, 9999px);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.demo-mode-badge:hover {
  background-color: rgba(59, 130, 246, 0.2);
  transform: scale(1.02);
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--navbar-height);
  padding: 0 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: -0.02em;
  color: var(--text-main);
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--primary);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  position: relative;
}

.nav-link:hover {
  color: var(--text-main);
  background-color: var(--bg-surface-hover);
}

.nav-link.active {
  color: var(--text-main);
  background-color: var(--bg-surface);
  border-bottom: 2px solid var(--primary);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.nav-btn-link {
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}

.nav-badge {
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: var(--radius-full);
}

.nav-badge-pulse {
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  animation: pulse-glow 2s infinite ease-in-out;
}

.nav-badge-danger {
  background-color: var(--danger, #ef4444) !important;
  color: #ffffff !important;
}

@keyframes pulse-glow {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 var(--primary-glow);
  }
  50% {
    transform: scale(1.08);
    box-shadow: 0 0 0 4px rgba(0, 0, 0, 0);
  }
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
}

.btn-icon.active {
  background-color: var(--primary);
  border-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  box-shadow: 0 0 0 2px var(--primary-subtle);
}

/* Health Pill & Diagnostic Popover Styling */
.health-pill-container {
  position: relative;
  display: flex;
  align-items: center;
}

.health-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-full, 9999px);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.health-pill:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
  border-color: var(--border-focus, var(--primary));
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

/* Status colors and effects */
.status-healthy .status-dot {
  background-color: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
  animation: pulse-green 2s infinite ease-in-out;
}

.status-degraded .status-dot {
  background-color: #f59e0b;
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.6);
}

.status-offline .status-dot {
  background-color: #ef4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.6);
}

.status-unconfigured .status-dot {
  background-color: #9ca3af;
}

@keyframes pulse-green {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.25);
    opacity: 0.8;
  }
}

.ai-health-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 8px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
}

.popover-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 13px;
  color: var(--text-main);
}

.status-badge {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: var(--radius-sm, 4px);
  letter-spacing: 0.03em;
}

.badge-healthy {
  background-color: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.badge-degraded {
  background-color: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.badge-offline {
  background-color: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.badge-unconfigured {
  background-color: rgba(156, 163, 175, 0.15);
  color: #9ca3af;
}

.popover-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  color: var(--text-main);
}

.highlight-row {
  padding-top: 4px;
  border-top: 1px stroke var(--border-subtle);
}

.error-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 4px;
  padding: 8px;
  background-color: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-sm, 4px);
  font-size: 11px;
  color: var(--danger, #ef4444);
  word-break: break-word;
}

.popover-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.mobile-menu-trigger {
  display: none;
}

/* Mobile Drawer Responsive Styles */
@media (max-width: 767px) {
  .nav-links {
    display: none;
  }

  .nav-brand {
    display: none;
  }

  .mobile-menu-trigger {
    display: flex;
    min-width: 44px;
    min-height: 44px;
  }

  .btn-ingest span {
    display: none;
  }

  .btn-ingest {
    padding: 8px 10px;
    min-width: 44px;
    min-height: 44px;
  }

  .btn-icon {
    min-width: 44px;
    min-height: 44px;
  }

  .health-pill {
    min-height: 36px;
  }

  .health-pill .pill-text {
    max-width: 110px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .navbar {
    padding: 0 12px;
  }

  .nav-left {
    gap: 12px;
  }

  .nav-right {
    gap: 6px;
  }
}

.mobile-drawer-backdrop {
  position: fixed;
  inset: 0;
  background-color: var(--bg-backdrop, rgba(0, 0, 0, 0.6));
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  z-index: 999;
}

.mobile-drawer {
  position: fixed;
  top: 0;
  left: 0;
  width: 280px;
  max-width: 85vw;
  height: 100vh;
  height: 100dvh;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  box-shadow: var(--shadow-xl);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;
}

.mobile-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 16px;
}

.mobile-drawer-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.mobile-nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  min-height: 48px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  background: transparent;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mobile-nav-link:hover,
.mobile-nav-link.active {
  color: var(--text-main);
  background-color: var(--bg-surface-hover);
}

.mobile-nav-link.active {
  color: var(--primary);
  font-weight: 600;
  background-color: var(--primary-subtle);
}

.mobile-drawer-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
  margin-top: auto;
}

.w-full {
  width: 100%;
}

.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

.drawer-slide-left-enter-active,
.drawer-slide-left-leave-active {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-slide-left-enter-from,
.drawer-slide-left-leave-to {
  transform: translateX(-100%);
}
</style>
