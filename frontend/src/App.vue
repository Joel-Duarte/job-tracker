<script setup>
import { onMounted } from 'vue'
import { AIConfigAPI } from './api/endpoints'
import { useUIStore } from './stores/uiStore'
import { isLocalOrDemoMode } from './services/storageAdapter'
import { db, initAndSeedDatabase } from './db/localDatabase'
import AppNavbar from './components/layout/AppNavbar.vue'
import ApplicationDetailDrawer from './components/drawers/ApplicationDetailDrawer.vue'
import IngestModal from './components/modals/IngestModal.vue'
import JobIntakeModal from './components/modals/JobIntakeModal.vue'
import CoverLetterModal from './components/modals/CoverLetterModal.vue'
import OnboardingWizardModal from './components/modals/OnboardingWizardModal.vue'
import QuickRetryModal from './components/modals/QuickRetryModal.vue'
import IntakeQueueDrawer from './components/layout/IntakeQueueDrawer.vue'
import FloatingQueueWidget from './components/layout/FloatingQueueWidget.vue'
import FloatingAgentChatWidget from './components/agent/FloatingAgentChatWidget.vue'
import ToastNotification from './components/common/ToastNotification.vue'

const uiStore = useUIStore()

async function runBootTimeStalenessCheck() {
  if (!isLocalOrDemoMode()) return
  try {
    await initAndSeedDatabase()
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString()
    const apps = await db.applications.toArray()
    let archivedCount = 0
    for (const app of apps) {
      if (app.status === 'APPLIED' && app.created_at < thirtyDaysAgo) {
        app.status = 'ARCHIVED'
        app.updated_at = new Date().toISOString()
        await db.applications.put(app)
        archivedCount++
      }
    }
    if (archivedCount > 0) {
      console.log(`[Boot Check] Auto-archived ${archivedCount} inactive local application(s).`)
    }
  } catch (err) {
    console.warn('[Boot Check Error]', err)
  }
}

onMounted(async () => {
  try {
    await runBootTimeStalenessCheck()
    await uiStore.fetchSystemSettings()
    const provRes = await AIConfigAPI.listProviders()
    const providers = provRes.data || []

    if (!uiStore.hasCompletedOnboarding || providers.length === 0) {
      uiStore.openOnboardingWizard()
    }
  } catch (error) {
    console.warn("Could not initialize system config or check providers", error)
  }
})
</script>

<template>
  <div class="app-layout">
    <AppNavbar />
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="route-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <ApplicationDetailDrawer />
    <IngestModal />
    <JobIntakeModal />
    <CoverLetterModal />
    <OnboardingWizardModal />
    <QuickRetryModal />
    <IntakeQueueDrawer />
    <FloatingQueueWidget />
    <FloatingAgentChatWidget />
    <ToastNotification />
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: var(--bg-app);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
