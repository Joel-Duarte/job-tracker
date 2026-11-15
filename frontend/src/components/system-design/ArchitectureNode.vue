<script setup>
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'
import { CATEGORY_ACCENTS, resolveDiagramIcon } from '../../utils/diagramCatalog'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

const iconComponent = computed(() => resolveDiagramIcon(props.data?.icon))
const accentColor = computed(
  () => CATEGORY_ACCENTS[props.data?.category]?.color || '#3b82f6'
)
const categoryLabel = computed(
  () => CATEGORY_ACCENTS[props.data?.category]?.label || 'Custom Block'
)
</script>

<template>
  <div
    class="sd-arch-node"
    :class="{ selected: selected }"
    :style="{ '--node-accent': accentColor }"
    :data-testid="`canvas-node-${data.type_id || 'custom'}`"
  >
    <Handle id="top" type="target" :position="Position.Top" class="sd-node-handle" />
    <Handle id="left" type="target" :position="Position.Left" class="sd-node-handle" />

    <div class="sd-arch-node-head">
      <span class="sd-arch-node-icon">
        <component :is="iconComponent" :size="15" />
      </span>
      <span class="sd-arch-node-cat">{{ categoryLabel }}</span>
    </div>

    <div class="sd-arch-node-title">{{ data.label || 'Component' }}</div>

    <div v-if="data.tech_stack" class="sd-arch-node-tech">
      {{ data.tech_stack }}
    </div>
    <div v-else-if="data.notes" class="sd-arch-node-note">
      {{ data.notes }}
    </div>

    <Handle id="right" type="source" :position="Position.Right" class="sd-node-handle" />
    <Handle id="bottom" type="source" :position="Position.Bottom" class="sd-node-handle" />
  </div>
</template>

<style scoped>
.sd-arch-node {
  min-width: 168px;
  max-width: 224px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1.5px solid var(--border-subtle, #334155);
  border-top: 3px solid var(--node-accent, #3b82f6);
  background: var(--bg-surface, #1e293b);
  color: var(--text-primary, #f8fafc);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.14);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  cursor: grab;
}

.sd-arch-node.selected {
  border-color: var(--node-accent, #3b82f6);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--node-accent, #3b82f6) 35%, transparent);
}

.sd-arch-node-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
}

.sd-arch-node-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--node-accent, #3b82f6) 16%, transparent);
  color: var(--node-accent, #3b82f6);
  flex-shrink: 0;
}

.sd-arch-node-cat {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-secondary, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sd-arch-node-title {
  font-size: 0.86rem;
  font-weight: 650;
  line-height: 1.25;
  word-break: break-word;
}

.sd-arch-node-tech {
  margin-top: 5px;
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--bg-elevated, rgba(148, 163, 184, 0.12));
  color: var(--text-secondary, #cbd5e1);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sd-arch-node-note {
  margin-top: 4px;
  font-size: 0.72rem;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sd-node-handle {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--node-accent, #3b82f6);
  border: 2px solid var(--bg-surface, #1e293b);
}
</style>
