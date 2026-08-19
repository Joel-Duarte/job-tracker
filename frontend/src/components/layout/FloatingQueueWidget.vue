<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { IntakeAPI } from '../../api/endpoints'
import { Cpu, Loader2, AlertCircle } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

const activeCount = ref(0)
const failedCount = ref(0)
let pollTimer = null

async function pollQueueStatus() {
  try {
    const res = await IntakeAPI.getEvaluations(100)
    if (Array.isArray(res.data)) {
      activeCount.value = res.data.filter((t) => ['QUEUED', 'PROCESSING'].includes(t.status)).length
      failedCount.value = res.data.filter((t) => t.status === 'FAILED').length
    }
  } catch (err) {
    // ignore
  }
}

function navigateToQueue() {
  router.push('/queue')
}

onMounted(() => {
  pollQueueStatus()
  pollTimer = setInterval(pollQueueStatus, 6000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <Transition name="fade-slide">
    <div
      v-if="(activeCount > 0 || failedCount > 0) && route.path !== '/queue'"
      class="floating-queue-widget"
      @click="navigateToQueue"
      title="View AI Evaluation Queue & Background Tasks"
    >
      <div class="queue-widget-inner" :class="{ 'has-error': failedCount > 0 }">
        <div class="queue-icon-wrapper">
          <Loader2 v-if="activeCount > 0" :size="16" class="spin-icon text-primary" />
          <AlertCircle v-else-if="failedCount > 0" :size="16" class="text-danger" />
          <Cpu v-else :size="16" />
        </div>

        <div class="queue-labels">
          <span v-if="activeCount > 0" class="queue-status-text">
            {{ activeCount }} AI Task{{ activeCount > 1 ? 's' : '' }} running
          </span>
          <span v-else-if="failedCount > 0" class="queue-status-text text-danger">
            {{ failedCount }} Task{{ failedCount > 1 ? 's' : '' }} failed
          </span>
        </div>

        <div v-if="failedCount > 0" class="error-badge-pill" title="Needs user attention">
          {{ failedCount }}
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.floating-queue-widget {
  position: fixed;
  bottom: 24px;
  right: 84px;
  z-index: 999;
  cursor: pointer;
  user-select: none;
}

.queue-widget-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(12px);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.queue-widget-inner:hover {
  transform: translateY(-2px);
  border-color: var(--primary);
  box-shadow: var(--shadow-xl);
}

.queue-widget-inner.has-error {
  border-color: var(--danger, #ef4444);
}

.queue-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spin-icon {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.queue-labels {
  display: flex;
  flex-direction: column;
}

.queue-status-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  letter-spacing: -0.01em;
}

.error-badge-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background-color: var(--danger, #ef4444);
  color: #ffffff;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(16px) scale(0.95);
}
</style>
