<script setup>
import { useUIStore } from '../../stores/uiStore'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-vue-next'

const uiStore = useUIStore()
</script>

<template>
  <Transition name="toast-slide">
    <div
      v-if="uiStore.toast.show"
      class="toast-container"
      :class="`toast-${uiStore.toast.type}`"
    >
      <div class="toast-icon">
        <CheckCircle2 v-if="uiStore.toast.type === 'success'" :size="18" />
        <AlertCircle v-else-if="uiStore.toast.type === 'error'" :size="18" />
        <Info v-else :size="18" />
      </div>
      <div class="toast-message">
        {{ uiStore.toast.message }}
      </div>
      <button class="toast-close" @click="uiStore.hideToast">
        <X :size="14" />
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: var(--card-shadow);
  max-width: 380px;
  font-size: 13px;
  font-weight: 500;
}

.toast-success {
  border-color: var(--status-offer-border);
  color: var(--status-offer-text);
}

.toast-error {
  border-color: var(--status-rejected-border);
  color: var(--status-rejected-text);
}

.toast-info {
  border-color: var(--status-applied-border);
  color: var(--status-applied-text);
}

.toast-message {
  flex: 1;
  color: var(--text-main);
}

.toast-close {
  color: var(--text-muted);
  display: flex;
  align-items: center;
  padding: 2px;
  border-radius: 4px;
}
.toast-close:hover {
  color: var(--text-main);
  background: var(--bg-surface-hover);
}

.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(32px) scale(0.95);
}
</style>
