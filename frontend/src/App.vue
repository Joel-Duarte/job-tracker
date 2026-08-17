<script setup>
import { onMounted } from 'vue'
import { AIConfigAPI } from './api/endpoints'
import { useUIStore } from './stores/uiStore'
import AppNavbar from './components/layout/AppNavbar.vue'
import ApplicationDetailDrawer from './components/drawers/ApplicationDetailDrawer.vue'
import IngestModal from './components/modals/IngestModal.vue'
import JobIntakeModal from './components/modals/JobIntakeModal.vue'
import IntakeQueueDrawer from './components/layout/IntakeQueueDrawer.vue'
import ToastNotification from './components/common/ToastNotification.vue'

const uiStore = useUIStore()

onMounted(async () => {
  try {
    const res = await AIConfigAPI.getGlobalSettings()
    if (res && res.data) {
      uiStore.setEnableEmbeddings(res.data.ENABLE_EMBEDDINGS)
    }
  } catch (error) {
    console.warn("Could not load global settings", error)
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
    <IntakeQueueDrawer />
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
