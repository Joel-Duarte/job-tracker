<script setup>
import { onMounted } from 'vue'
import { AIConfigAPI } from './api/endpoints'
import { useUIStore } from './stores/uiStore'
import AppNavbar from './components/layout/AppNavbar.vue'
import ApplicationDetailDrawer from './components/drawers/ApplicationDetailDrawer.vue'
import CompanyDetailDrawer from './components/drawers/CompanyDetailDrawer.vue'
import IngestModal from './components/modals/IngestModal.vue'
import JobIntakeModal from './components/modals/JobIntakeModal.vue'
import CoverLetterModal from './components/modals/CoverLetterModal.vue'
import ApplicationQuestionModal from './components/modals/ApplicationQuestionModal.vue'
import OnboardingWizardModal from './components/modals/OnboardingWizardModal.vue'
import QuickRetryModal from './components/modals/QuickRetryModal.vue'
import IntakeQueueDrawer from './components/layout/IntakeQueueDrawer.vue'
import FloatingQueueWidget from './components/layout/FloatingQueueWidget.vue'
import FloatingAgentChatWidget from './components/agent/FloatingAgentChatWidget.vue'
import ToastNotification from './components/common/ToastNotification.vue'

const uiStore = useUIStore()

onMounted(async () => {
  try {
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
    <CompanyDetailDrawer />
    <IngestModal />
    <JobIntakeModal />
    <CoverLetterModal />
    <ApplicationQuestionModal />
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
