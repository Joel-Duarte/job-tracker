<script setup>
import { ref } from 'vue'
import { FileCode, RotateCcw } from 'lucide-vue-next'

const props = defineProps({
  taskDef: {
    type: Object,
    required: true,
  },
  template: {
    type: String,
    default: '',
  },
  isResetting: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:template', 'reset', 'change'])

function onInput(e) {
  emit('update:template', e.target.value)
  emit('change')
}
</script>

<template>
  <div v-if="taskDef.hasPrompt" class="studio-card">
    <div class="studio-card-header">
      <div class="studio-card-title">
        <FileCode :size="16" class="text-primary" />
        <span>Prompt Template</span>
      </div>

      <button
        class="btn btn-ghost btn-xs text-secondary"
        :disabled="isResetting"
        @click="emit('reset')"
        title="Reset to default seeded template"
      >
        <RotateCcw :size="12" />
        <span>Reset to Default</span>
      </button>
    </div>

    <!-- Injected Placeholders -->
    <div v-if="taskDef.variables?.length" class="placeholders-box">
      <span class="placeholder-label">Injected Variables:</span>
      <span
        v-for="v in taskDef.variables"
        :key="v"
        class="placeholder-tag font-mono"
      >
        {{ v }}
      </span>
    </div>

    <!-- Monospace Editor -->
    <textarea
      :value="template"
      rows="12"
      class="prompt-textarea font-mono"
      placeholder="Enter prompt template instructions..."
      @input="onInput"
    ></textarea>
  </div>
</template>

<style scoped>
.studio-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.studio-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.studio-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.placeholders-box {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
}

.placeholder-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.placeholder-tag {
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--primary);
}

.prompt-textarea {
  width: 100%;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 12px;
  color: var(--text-main);
  line-height: 1.5;
  resize: vertical;
}

.prompt-textarea:focus {
  outline: none;
  border-color: var(--primary);
}
</style>
