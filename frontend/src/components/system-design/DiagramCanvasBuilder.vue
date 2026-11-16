<script setup>
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { ConnectionMode, MarkerType, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  Layers,
  Lightbulb,
  Maximize2,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import {
  CATEGORY_ACCENTS,
  CUSTOM_ICON_OPTIONS,
  DEFAULT_DIAGRAM_BLOCKS,
  DEFAULT_DIAGRAM_CATEGORIES,
  formatEdgeDisplayLabel,
  resolveDiagramIcon,
  serializeFlowEdges,
  serializeFlowNodes,
} from '../../utils/diagramCatalog'
import ArchitectureNode from './ArchitectureNode.vue'

const props = defineProps({
  session: { type: Object, default: null },
  catalog: { type: Object, default: null },
  loadedFlow: { type: Object, default: null },
  notes: { type: String, default: '' },
})

const emit = defineEmits(['update:notes', 'flow-change'])

const { fitView, screenToFlowCoordinate } = useVueFlow({ id: 'sd-canvas-builder' })

const nodes = ref([])
const edges = ref([])

const paletteCollapsed = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('all')
const showCustomCreator = ref(false)
const customName = ref('')
const customCategory = ref('compute_services')
const customIcon = ref('box')
const customTech = ref('')
const customNotes = ref('')

const selectedNodeId = ref(null)
const selectedEdgeId = ref(null)
const popoverAnchor = ref(null)
const canvasStageEl = ref(null)
const edgeLabelInputEl = ref(null)

const categories = computed(() =>
  props.catalog?.categories?.length ? props.catalog.categories : DEFAULT_DIAGRAM_CATEGORIES
)
const catalogBlocks = computed(() =>
  props.catalog?.blocks?.length ? props.catalog.blocks : DEFAULT_DIAGRAM_BLOCKS
)

const filteredBlocks = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return catalogBlocks.value.filter((block) => {
    if (selectedCategory.value !== 'all' && block.category !== selectedCategory.value) {
      return false
    }
    if (!q) return true
    const haystack = `${block.label} ${block.default_role || ''} ${(block.keywords || []).join(' ')}`.toLowerCase()
    return haystack.includes(q)
  })
})

const guidance = computed(() => props.session?.diagram_guidance || {})
const revealedComponents = computed(() => guidance.value?.revealed_components || [])
const activeHintDetailName = ref(null)
const activeHintDetail = computed(
  () =>
    revealedComponents.value.find(
      (item) => `${item.name}-${item.type_id}` === activeHintDetailName.value
    ) || null
)
const placedGuidedCount = computed(
  () => revealedComponents.value.filter((item) => isRevealedPlaced(item)).length
)

const selectedNode = computed(
  () => nodes.value.find((n) => n.id === selectedNodeId.value) || null
)
const selectedEdge = computed(
  () => edges.value.find((e) => e.id === selectedEdgeId.value) || null
)

const popoverStyle = computed(() => {
  if (!popoverAnchor.value) return {}
  return {
    left: `${popoverAnchor.value.x}px`,
    top: `${popoverAnchor.value.y}px`,
  }
})

function buildFlowSnapshot() {
  return {
    nodes: serializeFlowNodes(nodes.value),
    edges: serializeFlowEdges(edges.value),
    notes: String(props.notes || '').trim(),
  }
}

watch(
  [nodes, edges],
  () => {
    emit('flow-change', buildFlowSnapshot())
  },
  { deep: true }
)

function computeAnchorFromEvent(nativeEvent) {
  const container = canvasStageEl.value
  if (!container || !nativeEvent) return null
  const rect = container.getBoundingClientRect()
  const clientX = nativeEvent.clientX ?? rect.left + rect.width / 2
  const clientY = nativeEvent.clientY ?? rect.top + rect.height / 2
  const rawX = clientX - rect.left + 14
  const rawY = clientY - rect.top - 16
  const clampedX = Math.max(12, Math.min(rect.width - 310, rawX))
  const clampedY = Math.max(12, Math.min(rect.height - 230, rawY))
  return { x: Math.round(clampedX), y: Math.round(clampedY) }
}

function isRevealedPlaced(item) {
  const targetName = String(item?.name || item?.label || '').toLowerCase()
  const targetType = String(item?.type_id || '')
  return nodes.value.some((n) => {
    if (targetType && targetType !== 'custom' && n.data?.type_id === targetType) return true
    const combined = `${n.data?.label || ''} ${n.data?.tech_stack || ''}`.toLowerCase()
    return targetName && combined.includes(targetName)
  })
}

function nextPlacementPosition() {
  const count = nodes.value.length
  const col = count % 3
  const row = Math.floor(count / 3)
  return { x: 90 + col * 245, y: 80 + row * 145 }
}

function addBlockToCanvas(block, explicitPos = null) {
  const pos = explicitPos || nextPlacementPosition()
  const id = `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`
  const newNode = {
    id,
    type: 'architecture',
    position: pos,
    data: {
      type_id: block.type_id || 'custom',
      label: block.label || block.name || 'Custom Block',
      category: block.category || 'compute_services',
      icon: block.icon || 'box',
      tech_stack: block.tech_stack || '',
      notes: block.notes || '',
      is_custom: Boolean(block.is_custom || block.type_id === 'custom'),
    },
  }
  nodes.value = [...nodes.value, newNode]
  selectedEdgeId.value = null
  selectedNodeId.value = null
}

function handleAddCustomBlock() {
  const name = customName.value.trim()
  if (!name) return
  addBlockToCanvas({
    type_id: 'custom',
    label: name,
    category: customCategory.value,
    icon: customIcon.value,
    tech_stack: customTech.value.trim(),
    notes: customNotes.value.trim(),
    is_custom: true,
  })
  customName.value = ''
  customTech.value = ''
  customNotes.value = ''
  showCustomCreator.value = false
}

function handleDragStart(event, block) {
  if (!event.dataTransfer) return
  event.dataTransfer.setData('application/syslearner-block', JSON.stringify(block))
  event.dataTransfer.effectAllowed = 'move'
}

function handleCanvasDrop(event) {
  const raw = event.dataTransfer?.getData('application/syslearner-block')
  if (!raw) return
  try {
    const block = JSON.parse(raw)
    const position = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
    addBlockToCanvas(block, position)
  } catch {
    // ignore malformed drag payload
  }
}

function handleVueFlowConnect(params) {
  if (!params?.source || !params?.target || params.source === params.target) return
  const id = `edge-${params.source}-${params.target}-${Date.now()}`
  const newEdge = {
    id,
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle || null,
    targetHandle: params.targetHandle || null,
    type: 'smoothstep',
    animated: false,
    label: '',
    markerEnd: MarkerType.ArrowClosed,
    style: { strokeWidth: 2 },
    data: {
      protocol: '',
      delivery_mode: 'sync',
      text_label: '',
    },
  }
  edges.value = [...edges.value, newEdge]
  selectedNodeId.value = null
  selectedEdgeId.value = id
  popoverAnchor.value = { x: 24, y: 24 }
  nextTick(() => {
    edgeLabelInputEl.value?.focus()
  })
}

function handleNodeClick({ node, event }) {
  if (event?.target?.closest?.('.vue-flow__handle')) return
  selectedEdgeId.value = null
  selectedNodeId.value = node.id
  popoverAnchor.value = computeAnchorFromEvent(event) || { x: 24, y: 24 }
}

function handleEdgeClick({ edge, event }) {
  selectedNodeId.value = null
  selectedEdgeId.value = edge.id
  popoverAnchor.value = computeAnchorFromEvent(event) || { x: 24, y: 24 }
  nextTick(() => {
    edgeLabelInputEl.value?.focus()
  })
}

function closePopovers() {
  selectedNodeId.value = null
  selectedEdgeId.value = null
  popoverAnchor.value = null
}

function syncSelectedEdgeMeta() {
  if (!selectedEdge.value) return
  const edge = selectedEdge.value
  const isAsync = edge.data?.delivery_mode === 'async'
  edge.animated = isAsync
  edge.style = isAsync ? { strokeDasharray: '6 4', strokeWidth: 2 } : { strokeWidth: 2 }
  edge.label = formatEdgeDisplayLabel(
    edge.data?.protocol,
    edge.data?.delivery_mode,
    edge.data?.text_label
  )
}

function toggleSelectedEdgeAsync(checked) {
  if (!selectedEdge.value) return
  selectedEdge.value.data.delivery_mode = checked ? 'async' : 'sync'
  syncSelectedEdgeMeta()
}

function removeSelectedNode() {
  if (!selectedNodeId.value) return
  const id = selectedNodeId.value
  nodes.value = nodes.value.filter((n) => n.id !== id)
  edges.value = edges.value.filter((e) => e.source !== id && e.target !== id)
  closePopovers()
}

function removeSelectedEdge() {
  if (!selectedEdgeId.value) return
  edges.value = edges.value.filter((e) => e.id !== selectedEdgeId.value)
  closePopovers()
}

function clearCanvas() {
  nodes.value = []
  edges.value = []
  emit('update:notes', '')
  closePopovers()
}

function hydrateFromFlow(flow) {
  if (!flow || !Array.isArray(flow.nodes)) return
  nodes.value = flow.nodes.map((n, idx) => ({
    id: String(n.id || `node-${idx + 1}`),
    type: 'architecture',
    position: {
      x: Number(n.position?.x ?? (idx % 3) * 240 + 80),
      y: Number(n.position?.y ?? Math.floor(idx / 3) * 145 + 70),
    },
    data: {
      type_id: n.type_id || 'custom',
      label: n.label || `Component ${idx + 1}`,
      category: n.category || 'compute_services',
      icon: n.icon || 'box',
      tech_stack: n.tech_stack || '',
      notes: n.notes || '',
      is_custom: Boolean(n.is_custom),
    },
  }))
  edges.value = (flow.edges || []).map((e, idx) => {
    const mode = e.delivery_mode === 'async' ? 'async' : 'sync'
    const proto = e.protocol || ''
    const textLabel = e.label || ''
    return {
      id: String(e.id || `edge-${idx + 1}`),
      source: String(e.source),
      target: String(e.target),
      sourceHandle: e.source_handle || null,
      targetHandle: e.target_handle || null,
      type: 'smoothstep',
      animated: mode === 'async',
      label: formatEdgeDisplayLabel(proto, mode, textLabel),
      markerEnd: MarkerType.ArrowClosed,
      style: mode === 'async' ? { strokeDasharray: '6 4', strokeWidth: 2 } : { strokeWidth: 2 },
      data: {
        protocol: proto,
        delivery_mode: mode,
        text_label: textLabel,
      },
    }
  })
  emit('update:notes', flow.notes || '')
  closePopovers()
  nextTick(() => {
    fitView({ padding: 0.2 })
  })
}

watch(
  () => props.loadedFlow,
  (val) => {
    if (val) hydrateFromFlow(val)
  },
  { immediate: true }
)

defineExpose({
  getCurrentNodes: () => serializeFlowNodes(nodes.value),
  getCurrentEdges: () => serializeFlowEdges(edges.value),
  getFlowSnapshot: buildFlowSnapshot,
  clearCanvas,
  fitCanvas: () => fitView({ padding: 0.2 }),
  addBlockToCanvas,
})
</script>

<template>
  <div class="sd-studio-canvas-shell" data-testid="diagram-canvas-builder">
    <!-- Collapsible Left Component Palette -->
    <aside
      class="sd-studio-palette"
      :class="{ collapsed: paletteCollapsed }"
      aria-label="Architecture component palette"
    >
      <div class="sd-palette-top-row">
        <span v-if="!paletteCollapsed" class="sd-palette-title">
          <Layers :size="14" />
          <span>Components</span>
        </span>
        <button
          type="button"
          class="sd-palette-collapse-btn"
          :title="paletteCollapsed ? 'Show component palette' : 'Hide component palette'"
          @click="paletteCollapsed = !paletteCollapsed"
        >
          <ChevronRight v-if="paletteCollapsed" :size="15" />
          <ChevronLeft v-else :size="15" />
        </button>
      </div>

      <template v-if="!paletteCollapsed">
        <div class="sd-palette-search">
          <Search :size="14" />
          <input
            v-model="searchQuery"
            type="text"
            class="form-input sd-search-input"
            data-testid="palette-search-input"
            placeholder="Filter components..."
          />
        </div>

        <div class="sd-palette-cats">
          <button
            type="button"
            class="sd-cat-pill"
            :class="{ active: selectedCategory === 'all' }"
            @click="selectedCategory = 'all'"
          >
            All
          </button>
          <button
            v-for="cat in categories"
            :key="cat.id"
            type="button"
            class="sd-cat-pill"
            :class="{ active: selectedCategory === cat.id }"
            @click="selectedCategory = cat.id"
          >
            {{ cat.label }}
          </button>
        </div>

        <button
          type="button"
          class="btn btn-secondary btn-sm w-full"
          data-testid="open-custom-block-btn"
          @click="showCustomCreator = !showCustomCreator"
        >
          <Plus :size="14" />
          <span>{{ showCustomCreator ? 'Close Custom Block' : 'Custom Block' }}</span>
        </button>

        <div v-if="showCustomCreator" class="sd-custom-block-form" data-testid="custom-block-form">
          <input
            v-model="customName"
            type="text"
            class="form-input"
            data-testid="custom-block-name-input"
            placeholder="Block name (e.g. Base62 Ring)"
          />
          <select v-model="customCategory" class="form-select">
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ cat.label }}
            </option>
          </select>
          <select v-model="customIcon" class="form-select">
            <option v-for="opt in CUSTOM_ICON_OPTIONS" :key="opt.value" :value="opt.value">
              Icon: {{ opt.label }}
            </option>
          </select>
          <input
            v-model="customTech"
            type="text"
            class="form-input"
            data-testid="custom-block-tech-input"
            placeholder="Tech / engine (optional)"
          />
          <button
            type="button"
            class="btn btn-primary btn-sm w-full"
            data-testid="add-custom-block-btn"
            :disabled="!customName.trim()"
            @click="handleAddCustomBlock"
          >
            <Plus :size="14" />
            <span>Add Block</span>
          </button>
        </div>

        <div class="sd-palette-list">
          <button
            v-for="block in filteredBlocks"
            :key="block.type_id"
            type="button"
            class="sd-palette-item"
            draggable="true"
            :data-testid="`palette-block-${block.type_id}`"
            :title="`${block.default_role} (Click or drag onto canvas)`"
            @dragstart="handleDragStart($event, block)"
            @click="addBlockToCanvas(block)"
          >
            <span
              class="sd-palette-item-icon"
              :style="{ color: CATEGORY_ACCENTS[block.category]?.color || '#3b82f6' }"
            >
              <component :is="resolveDiagramIcon(block.icon)" :size="15" />
            </span>
            <span class="sd-palette-item-name">{{ block.label }}</span>
            <Plus :size="13" class="sd-palette-plus" />
          </button>
        </div>
      </template>
    </aside>

    <!-- Main Full-Height Interactive Canvas -->
    <div class="sd-studio-main">
      <!-- Guided Hint Tray (shown only once user unlocks component hints) -->
      <div
        v-if="revealedComponents.length"
        class="sd-hint-tray"
        data-testid="diagram-hint-tray"
      >
        <div class="sd-hint-tray-head">
          <strong>
            <Lightbulb :size="14" />
            <span>Guided Bank ({{ placedGuidedCount }}/{{ revealedComponents.length }} placed)</span>
          </strong>
          <span class="sd-muted">Click a block to place it, or ? for why &amp; checklist</span>
        </div>
        <div class="sd-hint-pills">
          <div
            v-for="item in revealedComponents"
            :key="`${item.name}-${item.type_id}`"
            class="sd-hint-chip-group"
            :class="{ placed: isRevealedPlaced(item) }"
          >
            <button
              type="button"
              class="sd-hint-pill"
              :class="{ placed: isRevealedPlaced(item) }"
              :title="item.why_required || item.hint_role"
              @click="addBlockToCanvas(item)"
            >
              <component :is="resolveDiagramIcon(item.icon)" :size="14" />
              <span>{{ item.label }}</span>
              <CheckCircle2 v-if="isRevealedPlaced(item)" :size="13" class="sd-placed-check" />
              <Plus v-else :size="13" />
            </button>
            <button
              type="button"
              class="sd-hint-info-btn"
              :class="{
                active: activeHintDetailName === `${item.name}-${item.type_id}`,
              }"
              data-testid="hint-info-btn"
              :aria-label="`Explain ${item.label}`"
              title="Why this component & configuration checklist"
              @click.stop="
                activeHintDetailName =
                  activeHintDetailName === `${item.name}-${item.type_id}`
                    ? null
                    : `${item.name}-${item.type_id}`
              "
            >
              <HelpCircle :size="12" />
            </button>
          </div>
        </div>

        <div
          v-if="activeHintDetail"
          class="sd-hint-detail-popover"
          data-testid="hint-info-popover"
        >
          <div class="sd-hint-detail-head">
            <strong>{{ activeHintDetail.label }} — Why &amp; Checklist</strong>
            <div class="sd-hint-detail-actions">
              <button
                type="button"
                class="btn btn-secondary btn-xs"
                @click="addBlockToCanvas(activeHintDetail)"
              >
                <Plus :size="12" />
                <span>Place</span>
              </button>
              <button
                type="button"
                class="sd-icon-btn"
                aria-label="Close detail"
                @click="activeHintDetailName = null"
              >
                <X :size="13" />
              </button>
            </div>
          </div>
          <p class="sd-hint-why">
            {{ activeHintDetail.why_required || activeHintDetail.hint_role }}
          </p>
          <ul
            v-if="activeHintDetail.config_checklist?.length"
            class="sd-hint-checklist"
          >
            <li
              v-for="checkItem in activeHintDetail.config_checklist"
              :key="checkItem"
            >
              {{ checkItem }}
            </li>
          </ul>
        </div>
      </div>

      <div
        ref="canvasStageEl"
        class="sd-flow-stage"
        @dragover.prevent
        @drop="handleCanvasDrop"
      >
        <div v-if="!nodes.length" class="sd-canvas-empty-hint">
          <Layers :size="26" />
          <p>Click or drag blocks from the left palette to design your architecture.</p>
          <span class="sd-muted">
            Drag from any dot on a box to another dot to wire them, then click any wire or box to describe it.
          </span>
        </div>

        <VueFlow
          id="sd-canvas-builder"
          v-model:nodes="nodes"
          v-model:edges="edges"
          class="sd-vue-flow"
          :connection-mode="ConnectionMode.Loose"
          :default-viewport="{ zoom: 1, x: 40, y: 40 }"
          @connect="handleVueFlowConnect"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
          @pane-click="closePopovers"
        >
          <Background pattern-color="rgba(148, 163, 184, 0.25)" :gap="20" />
          <Controls />
          <template #node-architecture="nodeProps">
            <ArchitectureNode v-bind="nodeProps" />
          </template>
        </VueFlow>

        <!-- Canvas Quick Utility Pill (Fit / Clear) -->
        <div class="sd-canvas-floating-tools">
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            title="Fit architecture to screen"
            @click="fitView({ padding: 0.2 })"
          >
            <Maximize2 :size="13" />
            <span>Fit</span>
          </button>
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            :disabled="!nodes.length"
            @click="clearCanvas"
          >
            <Trash2 :size="13" />
            <span>Clear</span>
          </button>
        </div>

        <!-- Contextual Node Popover (only appears when clicking a node) -->
        <div
          v-if="selectedNode"
          class="sd-context-popover"
          :style="popoverStyle"
          data-testid="node-popover"
        >
          <div class="sd-popover-head">
            <strong>Edit Component</strong>
            <div class="sd-popover-head-actions">
              <button
                type="button"
                class="btn-icon-danger"
                data-testid="delete-selected-node-btn"
                title="Remove component"
                @click="removeSelectedNode"
              >
                <Trash2 :size="14" />
              </button>
              <button
                type="button"
                class="sd-icon-close"
                title="Close"
                @click="closePopovers"
              >
                <X :size="14" />
              </button>
            </div>
          </div>

          <label class="sd-field-label">
            <span>Name</span>
            <input
              v-model="selectedNode.data.label"
              type="text"
              class="form-input"
              data-testid="inspector-node-label"
            />
          </label>
          <label class="sd-field-label">
            <span>Tech / Engine</span>
            <input
              v-model="selectedNode.data.tech_stack"
              type="text"
              class="form-input"
              data-testid="inspector-node-tech"
              placeholder="e.g. Redis Cluster, Postgres"
            />
          </label>
          <label class="sd-field-label">
            <span>Notes</span>
            <textarea
              v-model="selectedNode.data.notes"
              class="form-textarea"
              rows="2"
              data-testid="inspector-node-notes"
              placeholder="Sharding, TTL, replication..."
            />
          </label>
          <button type="button" class="btn btn-primary btn-sm w-full" @click="closePopovers">
            Done
          </button>
        </div>

        <!-- Lightweight Inline Wire Popover (only appears when drawing or clicking a wire) -->
        <div
          v-if="selectedEdge"
          class="sd-context-popover sd-edge-popover"
          :style="popoverStyle"
          data-testid="edge-popover"
        >
          <div class="sd-popover-head">
            <strong>Connection Flow</strong>
            <div class="sd-popover-head-actions">
              <button
                type="button"
                class="btn-icon-danger"
                data-testid="delete-selected-edge-btn"
                title="Delete wire"
                @click="removeSelectedEdge"
              >
                <Trash2 :size="14" />
              </button>
              <button
                type="button"
                class="sd-icon-close"
                title="Close"
                @click="closePopovers"
              >
                <X :size="14" />
              </button>
            </div>
          </div>

          <label class="sd-field-label">
            <span>What does this wire do?</span>
            <input
              ref="edgeLabelInputEl"
              v-model="selectedEdge.data.text_label"
              type="text"
              class="form-input"
              data-testid="edge-label-input"
              placeholder="e.g. Reads hot short URLs, Enqueues job"
              @input="syncSelectedEdgeMeta"
              @keydown.enter.prevent="closePopovers"
            />
          </label>

          <label class="sd-popover-checkbox">
            <input
              type="checkbox"
              data-testid="edge-async-checkbox"
              :checked="selectedEdge.data.delivery_mode === 'async'"
              @change="toggleSelectedEdgeAsync($event.target.checked)"
            />
            <span>Asynchronous / Queue / Event flow</span>
          </label>

          <button type="button" class="btn btn-primary btn-sm w-full" @click="closePopovers">
            Done
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sd-studio-canvas-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 10px;
  padding: 10px;
  overflow: hidden;
}

.sd-studio-palette {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  overflow: hidden;
  transition: width 0.16s ease;
}

.sd-studio-palette.collapsed {
  width: 44px;
  padding: 8px 6px;
  align-items: center;
}

.sd-palette-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.sd-palette-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  font-weight: 650;
}

.sd-palette-collapse-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle, #334155);
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
}

.sd-palette-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
  border: 1px solid var(--border-subtle, #334155);
  border-radius: 8px;
  background: var(--bg-elevated, rgba(15, 23, 42, 0.45));
}

.sd-search-input {
  border: none !important;
  background: transparent !important;
  padding-left: 2px !important;
}

.sd-palette-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sd-cat-pill {
  padding: 3px 7px;
  border-radius: 999px;
  font-size: 0.7rem;
  border: 1px solid var(--border-subtle, #334155);
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
}

.sd-cat-pill.active {
  background: var(--accent, #3b82f6);
  border-color: var(--accent, #3b82f6);
  color: #ffffff;
}

.sd-custom-block-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  border-radius: 8px;
  border: 1px dashed var(--border-subtle, #475569);
  background: var(--bg-elevated, rgba(15, 23, 42, 0.35));
}

.sd-palette-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
  overflow-y: auto;
  padding-right: 2px;
}

.sd-palette-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, rgba(148, 163, 184, 0.06));
  color: var(--text-primary, #f8fafc);
  font-size: 0.78rem;
  cursor: pointer;
}

.sd-palette-item:hover {
  border-color: var(--accent, #3b82f6);
}

.sd-palette-item-icon {
  display: inline-flex;
  flex-shrink: 0;
}

.sd-palette-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sd-palette-plus {
  opacity: 0.65;
  flex-shrink: 0;
}

.sd-studio-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sd-hint-tray {
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--accent, #3b82f6) 40%, var(--border-subtle, #334155));
  background: color-mix(in srgb, var(--accent, #3b82f6) 8%, var(--bg-surface, #1e293b));
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.sd-hint-tray-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sd-hint-tray-head strong {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
}

.sd-hint-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sd-hint-chip-group {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  overflow: hidden;
}

.sd-hint-chip-group.placed {
  border-color: #10b981;
}

.sd-hint-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: var(--text-primary, #f8fafc);
  font-size: 0.78rem;
  cursor: pointer;
}

.sd-hint-pill.placed {
  color: #10b981;
}

.sd-hint-info-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 7px 4px 4px;
  border: none;
  border-left: 1px solid color-mix(in srgb, var(--border-subtle, #334155) 70%, transparent);
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
}

.sd-hint-info-btn:hover,
.sd-hint-info-btn.active {
  color: var(--accent, #3b82f6);
  background: color-mix(in srgb, var(--accent, #3b82f6) 14%, transparent);
}

.sd-hint-detail-popover {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 0.78rem;
}

.sd-hint-detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sd-hint-detail-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sd-hint-why {
  margin: 0;
  color: var(--text-primary, #f8fafc);
  line-height: 1.35;
}

.sd-hint-checklist {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary, #94a3b8);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sd-placed-check {
  color: #10b981;
}

.sd-flow-stage {
  position: relative;
  flex: 1;
  min-height: 420px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  overflow: hidden;
}

.sd-vue-flow {
  width: 100%;
  height: 100%;
}

.sd-canvas-empty-hint {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px;
  gap: 8px;
  color: var(--text-secondary, #94a3b8);
}

.sd-canvas-floating-tools {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 5;
  display: flex;
  gap: 6px;
}

.sd-context-popover {
  position: absolute;
  z-index: 20;
  width: 286px;
  max-width: calc(100% - 24px);
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #475569);
  background: var(--bg-surface, #1e293b);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.28);
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.sd-popover-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85rem;
}

.sd-popover-head-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-icon-danger,
.sd-icon-close {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
}

.btn-icon-danger {
  color: #ef4444;
}

.sd-icon-close {
  color: var(--text-secondary, #94a3b8);
}

.sd-field-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.78rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-popover-checkbox {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.8rem;
  cursor: pointer;
}

@media (max-width: 820px) {
  .sd-studio-canvas-shell {
    flex-direction: column;
    overflow: auto;
  }

  .sd-studio-palette,
  .sd-studio-palette.collapsed {
    width: 100%;
    max-height: 220px;
  }

  .sd-flow-stage {
    min-height: 460px;
  }
}
</style>
