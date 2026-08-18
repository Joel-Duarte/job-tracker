<script setup>
import { computed } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import {
  Sparkles,
  Loader2,
  CheckCircle,
  AlertTriangle,
  X,
  ChevronDown,
  ChevronUp,
  Trash2,
  ExternalLink,
} from 'lucide-vue-next'

const uiStore = useUIStore()

const queue = computed(() => uiStore.intakeQueue)
const activeCount = computed(() => queue.value.filter(t => t.status === 'running').length)
const hasItems = computed(() => queue.value.length > 0)

function toggleOpen() {
  uiStore.isQueueDrawerOpen = !uiStore.isQueueDrawerOpen
}

function dismiss(id) {
  uiStore.removeIntakeTask(id)
}

function clearFinished() {
  uiStore.clearCompletedIntakeTasks()
}

const STAGES = {
  SCRAPING: { label: 'Scraping URL', icon: Loader2, color: 'text-primary' },
  EXTRACTING: { label: 'Extracting Specs', icon: Loader2, color: 'text-primary' },
  MATCHING: { label: 'CV Keyword Overlap', icon: Loader2, color: 'text-primary' },
  ASSESSING: { label: 'AI Assessment', icon: Loader2, color: 'text-primary' },
  GENERATING: { label: 'Generating Content', icon: Loader2, color: 'text-primary' },
  COMPLETE: { label: 'Complete', icon: CheckCircle, color: 'text-success' },
  FAILED: { label: 'Failed', icon: AlertTriangle, color: 'text-danger' },
}
</script>

<template>
  <div v-if="hasItems" class="queue-floating-container animate-fade-in">
    <!-- Header / Ticker Bar -->
    <div class="queue-header" @click="toggleOpen">
      <div class="header-left">
        <div class="pulse-dot" :class="{ 'is-active': activeCount > 0 }"></div>
        <Sparkles :size="15" class="text-primary" />
        <span class="queue-title">
          Intake Stream
          <span v-if="activeCount > 0" class="active-badge font-mono">{{ activeCount }} processing</span>
          <span v-else class="done-badge font-mono">{{ queue.length }} items</span>
        </span>
      </div>

      <div class="header-actions">
        <button
          v-if="queue.length > activeCount"
          class="btn-icon"
          title="Clear completed tasks"
          @click.stop="clearFinished"
        >
          <Trash2 :size="13" />
        </button>
        <button class="btn-icon" @click.stop="toggleOpen">
          <ChevronDown v-if="uiStore.isQueueDrawerOpen" :size="16" />
          <ChevronUp v-else :size="16" />
        </button>
      </div>
    </div>

    <!-- Expanded Drawer Content -->
    <Transition name="expand">
      <div v-if="uiStore.isQueueDrawerOpen" class="queue-body">
      <div v-for="item in queue" :key="item.id" class="queue-item" :class="`item-${item.status}`">
        <div class="item-top">
          <div class="item-title-group">
            <span class="item-title font-semibold">{{ item.title || item.url || 'Job Lead' }}</span>
            <a
              v-if="item.url"
              :href="item.url"
              target="_blank"
              class="item-url-link"
              title="Open URL"
              @click.stop
            >
              <ExternalLink :size="12" />
            </a>
          </div>
          <button class="btn-dismiss" title="Dismiss" @click="dismiss(item.id)">
            <X :size="13" />
          </button>
        </div>

        <!-- Stage Progress Indicator -->
        <div class="item-stage-row">
          <div class="stage-badge" :class="`stage-${item.stage?.toLowerCase()}`">
            <Loader2 v-if="item.status === 'running'" class="animate-spin" :size="11" />
            <CheckCircle v-else-if="item.status === 'success'" :size="11" class="text-success" />
            <AlertTriangle v-else :size="11" class="text-danger" />
            <span>{{ STAGES[item.stage]?.label || item.stage || 'Processing' }}</span>
          </div>

          <span v-if="item.message" class="item-msg text-xs">{{ item.message }}</span>
        </div>

        <!-- Step Progress Dots -->
        <div v-if="item.status === 'running'" class="step-progress-bar">
          <div
            class="progress-fill"
            :style="{
              width: item.stage === 'SCRAPING' ? '25%' :
                     item.stage === 'EXTRACTING' ? '50%' :
                     item.stage === 'MATCHING' ? '75%' :
                     item.stage === 'ASSESSING' ? '90%' : '100%'
            }"
          ></div>
        </div>
      </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.queue-floating-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 360px;
  max-width: calc(100vw - 32px);
  background-color: var(--bg-card);
  border: var(--card-border);
  border-radius: var(--radius-md);
  box-shadow: var(--card-shadow);
  z-index: 550;
  overflow: hidden;
}

.queue-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background-color: var(--bg-card);
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  user-select: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: var(--text-muted);
}

.pulse-dot.is-active {
  background-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-subtle);
  animation: pulse-ring 1.5s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}

@keyframes pulse-ring {
  0% { box-shadow: 0 0 0 0 var(--primary-glow); }
  70% { box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

.queue-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 6px;
}

.active-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background-color: var(--primary-subtle);
  color: var(--primary);
}

.done-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background-color: var(--bg-elevated);
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
}

.queue-body {
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  background-color: var(--bg-surface);
}

.queue-item {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.item-title-group {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.item-title {
  font-size: 12px;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-url-link {
  color: var(--text-muted);
  display: flex;
  align-items: center;
}

.item-url-link:hover {
  color: var(--primary);
}

.btn-dismiss {
  color: var(--text-muted);
  padding: 2px;
}

.btn-dismiss:hover {
  color: var(--text-main);
}

.item-stage-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.stage-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
}

.item-msg {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-progress-bar {
  width: 100%;
  height: 3px;
  background-color: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 2px;
}

.progress-fill {
  height: 100%;
  background-color: var(--primary);
  transition: width 0.4s ease;
}

.expand-enter-active,
.expand-leave-active {
  transition: max-height var(--transition-smooth), padding var(--transition-smooth), opacity var(--transition-smooth);
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  opacity: 0;
}
.expand-enter-to,
.expand-leave-from {
  max-height: 280px;
  padding-top: 10px;
  padding-bottom: 10px;
  opacity: 1;
}
</style>
