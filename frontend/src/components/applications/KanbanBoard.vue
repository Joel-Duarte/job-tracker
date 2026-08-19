<script setup>
import ApplicationCard from './ApplicationCard.vue'

const props = defineProps({
  columns: {
    type: Array,
    required: true,
  },
  kanbanColumns: {
    type: Object,
    required: true,
  },
  draggedApp: {
    type: Object,
    default: null,
  },
  dragOverCol: {
    type: String,
    default: null,
  },
  activeMenuApp: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits([
  'dragover',
  'dragleave',
  'drop',
  'card-dragstart',
  'card-dragend',
  'card-click',
  'match-click',
  'guide-click',
  'reader-click',
  'toggle-menu',
  'transition-modal',
  'execute-transition',
  'quick-withdraw',
])
</script>

<template>
  <div class="kanban-board">
    <div
      v-for="col in columns"
      :key="col.key"
      class="kanban-column"
      :class="{ 'drag-over': dragOverCol === col.key }"
      @dragover="emit('dragover', col.key, $event)"
      @dragleave="emit('dragleave', col.key)"
      @drop="emit('drop', col.key, $event)"
    >
      <div class="column-header">
        <div class="column-title-group">
          <span class="column-dot" :class="`dot-${col.color}`"></span>
          <span class="column-title">{{ col.label }}</span>
        </div>
        <span class="column-count">
          {{ kanbanColumns[col.key]?.length || 0 }}
        </span>
      </div>

      <div class="column-cards">
        <ApplicationCard
          v-for="app in kanbanColumns[col.key] || []"
          :key="app.id"
          :app="app"
          :dragged-app="draggedApp"
          :active-menu-app="activeMenuApp"
          @dragstart="(a, e) => emit('card-dragstart', a, e)"
          @dragend="emit('card-dragend')"
          @click="(id) => emit('card-click', id)"
          @match-click="(id) => emit('match-click', id)"
          @guide-click="(id) => emit('guide-click', id)"
          @reader-click="(id) => emit('reader-click', id)"
          @toggle-menu="(a, e) => emit('toggle-menu', a, e)"
          @transition-modal="(a, st) => emit('transition-modal', a, st)"
          @execute-transition="(id, payload) => emit('execute-transition', id, payload)"
          @quick-withdraw="(a) => emit('quick-withdraw', a)"
        />

        <!-- Empty Column State -->
        <div
          v-if="!kanbanColumns[col.key]?.length"
          class="column-empty"
        >
          No applications in {{ col.label }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kanban-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(320px, 1fr));
  gap: 16px;
  flex: 1;
  height: 100%;
  min-height: 0;
  align-items: stretch;
  width: 100%;
}

.kanban-column {
  background-color: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.kanban-column.drag-over {
  border-color: var(--primary);
  background-color: var(--bg-surface-hover);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.column-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-applied { background-color: var(--status-applied-text); }
.dot-assessment { background-color: var(--status-assessment-text); }
.dot-interview { background-color: var(--status-interview-text); }
.dot-offer { background-color: var(--status-offer-text); }
.dot-rejected { background-color: var(--status-rejected-text); }

.column-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 13px;
  color: var(--text-main);
}

.column-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background-color: var(--bg-surface);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.column-cards {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.column-empty {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  padding: 24px 0;
}
</style>
