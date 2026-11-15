<script setup>
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MarkerType, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import {
  CheckCircle2,
  Code2,
  GitBranch,
  Layers,
  Lightbulb,
  Link2,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import {
  CATEGORY_ACCENTS,
  CUSTOM_ICON_OPTIONS,
  DEFAULT_DIAGRAM_BLOCKS,
  DEFAULT_DIAGRAM_CATEGORIES,
  EDGE_PROTOCOL_OPTIONS,
  formatEdgeDisplayLabel,
  resolveDiagramIcon,
  serializeFlowEdges,
  serializeFlowNodes,
} from '../../utils/diagramCatalog'
import ArchitectureNode from './ArchitectureNode.vue'

const props = defineProps({
  session: { type: Object, default: null },
  catalog: { type: Object, default: null },
  saving: { type: Boolean, default: false },
  hintLoading: { type: Boolean, default: false },
  reviewing: { type: Boolean, default: false },
  loadedFlow: { type: Object, default: null },
  loadedRevisionVersion: { type: Number, default: null },
})

const emit = defineEmits([
  'submit-canvas',
  'request-hint',
  'analyze-latest',
  'switch-to-upload',
])

const { fitView, screenToFlowCoordinate } = useVueFlow({ id: 'sd-canvas-builder' })

const nodes = ref([])
const edges = ref([])
const canvasNotes = ref('')

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

// Quick Connect bar controls (drag-free accessible edge builder)
const connectSourceId = ref('')
const connectTargetId = ref('')
const connectProtocol = ref('HTTPS')
const connectDeliveryMode = ref('sync')
const connectLabel = ref('')

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
const guidancePenalty = computed(() => Number(guidance.value?.penalty_points || 0))
const isStrictInterview = computed(
  () => String(props.session?.mode || '').toUpperCase() === 'INTERVIEW'
)
const hasCanvasRevisions = computed(() =>
  (props.session?.diagrams_metadata || []).some((d) => d.diagram_kind === 'canvas')
)
const nextVersionNumber = computed(() => (props.session?.diagrams_metadata?.length || 0) + 1)

const selectedNode = computed(
  () => nodes.value.find((n) => n.id === selectedNodeId.value) || null
)
const selectedEdge = computed(
  () => edges.value.find((e) => e.id === selectedEdgeId.value) || null
)

const flowPreviewPayload = computed(() => ({
  nodes: serializeFlowNodes(nodes.value),
  edges: serializeFlowEdges(edges.value),
  notes: canvasNotes.value.trim(),
}))

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
  return { x: 60 + col * 245, y: 50 + row * 145 }
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
  selectedNodeId.value = id
  selectedEdgeId.value = null

  if (!connectSourceId.value) {
    connectSourceId.value = id
  } else if (!connectTargetId.value && connectSourceId.value !== id) {
    connectTargetId.value = id
  }
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

function createDirectedEdge({
  source,
  target,
  sourceHandle = null,
  targetHandle = null,
  protocol = 'HTTPS',
  deliveryMode = 'sync',
  textLabel = '',
}) {
  if (!source || !target || source === target) return
  const id = `edge-${source}-${target}-${Date.now()}`
  const isAsync = deliveryMode === 'async'
  const newEdge = {
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    type: 'smoothstep',
    animated: isAsync,
    label: formatEdgeDisplayLabel(protocol, deliveryMode, textLabel),
    markerEnd: MarkerType.ArrowClosed,
    style: isAsync ? { strokeDasharray: '6 4', strokeWidth: 2 } : { strokeWidth: 2 },
    data: {
      protocol,
      delivery_mode: deliveryMode,
      text_label: textLabel,
    },
  }
  edges.value = [...edges.value, newEdge]
  selectedEdgeId.value = id
  selectedNodeId.value = null
}

function handleVueFlowConnect(params) {
  createDirectedEdge({
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle,
    targetHandle: params.targetHandle,
    protocol: connectProtocol.value,
    deliveryMode: connectDeliveryMode.value,
    textLabel: connectLabel.value.trim(),
  })
}

function handleQuickConnect() {
  createDirectedEdge({
    source: connectSourceId.value,
    target: connectTargetId.value,
    protocol: connectProtocol.value,
    deliveryMode: connectDeliveryMode.value,
    textLabel: connectLabel.value.trim(),
  })
  connectLabel.value = ''
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

function removeSelectedNode() {
  if (!selectedNodeId.value) return
  const id = selectedNodeId.value
  nodes.value = nodes.value.filter((n) => n.id !== id)
  edges.value = edges.value.filter((e) => e.source !== id && e.target !== id)
  selectedNodeId.value = null
  if (connectSourceId.value === id) connectSourceId.value = ''
  if (connectTargetId.value === id) connectTargetId.value = ''
}

function removeSelectedEdge() {
  if (!selectedEdgeId.value) return
  edges.value = edges.value.filter((e) => e.id !== selectedEdgeId.value)
  selectedEdgeId.value = null
}

function clearCanvas() {
  nodes.value = []
  edges.value = []
  canvasNotes.value = ''
  selectedNodeId.value = null
  selectedEdgeId.value = null
  connectSourceId.value = ''
  connectTargetId.value = ''
}

function handleRequestHint(hintMode) {
  emit('request-hint', {
    hint_mode: hintMode,
    current_nodes: serializeFlowNodes(nodes.value),
  })
}

function handleSaveCanvas() {
  if (!nodes.value.length || props.saving) return
  emit('submit-canvas', flowPreviewPayload.value)
}

function hydrateFromFlow(flow) {
  if (!flow || !Array.isArray(flow.nodes)) return
  nodes.value = flow.nodes.map((n, idx) => ({
    id: String(n.id || `node-${idx + 1}`),
    type: 'architecture',
    position: {
      x: Number(n.position?.x ?? (idx % 3) * 240 + 50),
      y: Number(n.position?.y ?? Math.floor(idx / 3) * 140 + 50),
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
    const proto = e.protocol || 'HTTPS'
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
  canvasNotes.value = flow.notes || ''
  selectedNodeId.value = null
  selectedEdgeId.value = null
  if (nodes.value.length) {
    connectSourceId.value = nodes.value[0].id
    connectTargetId.value = nodes.value[1]?.id || ''
  }
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
</script>

<template>
  <div class="sd-canvas-workspace" data-testid="diagram-canvas-builder">
    <!-- Top Guidance + Quick Connect Toolbar -->
    <div class="sd-canvas-toolbar">
      <div class="sd-toolbar-group">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="hint-next-component-btn"
          :disabled="hintLoading"
          @click="handleRequestHint('next_component')"
        >
          <Loader2 v-if="hintLoading" :size="14" class="spin" />
          <Lightbulb v-else :size="14" />
          <span>Hint Next Block (-3 pts)</span>
        </button>

        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="reveal-bank-btn"
          :disabled="hintLoading || isStrictInterview"
          :title="
            isStrictInterview
              ? 'Full required bank reveal is disabled in strict INTERVIEW mode.'
              : 'Reveal all expected components for this scenario (-18 pts base penalty)'
          "
          @click="handleRequestHint('reveal_all')"
        >
          <Layers :size="14" />
          <span>Show Required Bank (-18 pts)</span>
        </button>

        <span
          v-if="guidancePenalty > 0"
          class="badge badge-interview"
          data-testid="guidance-penalty-badge"
        >
          Hint Penalty: -{{ guidancePenalty }} pts
        </span>
      </div>

      <div class="sd-toolbar-group">
        <span v-if="loadedRevisionVersion" class="sd-muted">
          Loaded v{{ loadedRevisionVersion }}
        </span>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          @click="fitView({ padding: 0.2 })"
        >
          Fit View
        </button>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="!nodes.length"
          @click="clearCanvas"
        >
          Clear Canvas
        </button>
      </div>
    </div>

    <!-- Guided Component Hints Tray -->
    <div
      v-if="revealedComponents.length"
      class="sd-hint-tray"
      data-testid="diagram-hint-tray"
    >
      <div class="sd-hint-tray-head">
        <strong>
          <Lightbulb :size="14" />
          <span>Guided Component Bank ({{ revealedComponents.length }})</span>
        </strong>
        <span class="sd-muted">Click any block to place it on your canvas</span>
      </div>
      <div class="sd-hint-pills">
        <button
          v-for="item in revealedComponents"
          :key="`${item.name}-${item.type_id}`"
          type="button"
          class="sd-hint-pill"
          :class="{ placed: isRevealedPlaced(item) }"
          :title="item.hint_role"
          @click="addBlockToCanvas(item)"
        >
          <component :is="resolveDiagramIcon(item.icon)" :size="14" />
          <span>{{ item.label }}</span>
          <CheckCircle2 v-if="isRevealedPlaced(item)" :size="13" class="sd-placed-check" />
          <Plus v-else :size="13" />
        </button>
      </div>
    </div>

    <!-- Quick Connect Accessible Edge Bar -->
    <div class="sd-quick-connect-bar">
      <span class="sd-qc-label">
        <Link2 :size="14" />
        <span>Wire Flow:</span>
      </span>
      <select
        v-model="connectSourceId"
        class="form-select sd-qc-select"
        data-testid="qc-source-select"
        aria-label="Source component"
      >
        <option value="">From component...</option>
        <option v-for="n in nodes" :key="`src-${n.id}`" :value="n.id">
          {{ n.data.label }}
        </option>
      </select>
      <span class="sd-muted">-></span>
      <select
        v-model="connectTargetId"
        class="form-select sd-qc-select"
        data-testid="qc-target-select"
        aria-label="Target component"
      >
        <option value="">To component...</option>
        <option v-for="n in nodes" :key="`dst-${n.id}`" :value="n.id">
          {{ n.data.label }}
        </option>
      </select>
      <select
        v-model="connectProtocol"
        class="form-select sd-qc-proto"
        data-testid="qc-protocol-select"
        aria-label="Protocol"
      >
        <option v-for="proto in EDGE_PROTOCOL_OPTIONS" :key="proto" :value="proto">
          {{ proto }}
        </option>
      </select>
      <select
        v-model="connectDeliveryMode"
        class="form-select sd-qc-mode"
        aria-label="Sync or async"
      >
        <option value="sync">Sync</option>
        <option value="async">Async</option>
      </select>
      <input
        v-model="connectLabel"
        type="text"
        class="form-input sd-qc-note"
        placeholder="Flow label (e.g. cache miss)"
      />
      <button
        type="button"
        class="btn btn-secondary btn-sm"
        data-testid="quick-connect-btn"
        :disabled="!connectSourceId || !connectTargetId || connectSourceId === connectTargetId"
        @click="handleQuickConnect"
      >
        <GitBranch :size="13" />
        <span>Connect</span>
      </button>
    </div>

    <!-- Main 3-Pane Canvas Grid: Palette | Interactive Graph | Inspector + Save -->
    <div class="sd-canvas-grid">
      <!-- Palette Column -->
      <aside class="sd-palette-pane">
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
          <span>{{ showCustomCreator ? 'Close Custom Block' : '+ Custom Block' }}</span>
        </button>

        <div v-if="showCustomCreator" class="sd-custom-block-form" data-testid="custom-block-form">
          <input
            v-model="customName"
            type="text"
            class="form-input"
            data-testid="custom-block-name-input"
            placeholder="Block name (e.g. Geo Shard Router)"
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
            <span>Add Custom Block</span>
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
      </aside>

      <!-- Vue Flow Canvas -->
      <div
        class="sd-flow-stage"
        @dragover.prevent
        @drop="handleCanvasDrop"
      >
        <div v-if="!nodes.length" class="sd-canvas-empty-hint">
          <Layers :size="24" />
          <p>Click or drag blocks from the left palette to start building your architecture.</p>
          <span class="sd-muted">
            Connect handles by dragging between dots or using the Wire Flow bar above.
          </span>
        </div>

        <VueFlow
          id="sd-canvas-builder"
          v-model:nodes="nodes"
          v-model:edges="edges"
          class="sd-vue-flow"
          :default-viewport="{ zoom: 0.95, x: 20, y: 20 }"
          @connect="handleVueFlowConnect"
          @node-click="({ node }) => { selectedNodeId = node.id; selectedEdgeId = null }"
          @edge-click="({ edge }) => { selectedEdgeId = edge.id; selectedNodeId = null }"
          @pane-click="() => { selectedNodeId = null; selectedEdgeId = null }"
        >
          <Background pattern-color="rgba(148, 163, 184, 0.25)" :gap="20" />
          <Controls />
          <template #node-architecture="nodeProps">
            <ArchitectureNode v-bind="nodeProps" />
          </template>
        </VueFlow>
      </div>

      <!-- Inspector, Flow JSON & Submit Pane -->
      <aside class="sd-inspector-pane">
        <!-- Node Inspector -->
        <div v-if="selectedNode" class="sd-inspector-box" data-testid="node-inspector">
          <div class="sd-inspector-head">
            <h4>Selected Component</h4>
            <button
              type="button"
              class="btn-icon-danger"
              title="Remove block"
              @click="removeSelectedNode"
            >
              <Trash2 :size="14" />
            </button>
          </div>
          <label class="sd-field-label">
            <span>Display Name</span>
            <input
              v-model="selectedNode.data.label"
              type="text"
              class="form-input"
              data-testid="inspector-node-label"
            />
          </label>
          <label class="sd-field-label">
            <span>Technology / Engine</span>
            <input
              v-model="selectedNode.data.tech_stack"
              type="text"
              class="form-input"
              data-testid="inspector-node-tech"
              placeholder="e.g. Redis 7 Cluster, Kafka 12p"
            />
          </label>
          <label class="sd-field-label">
            <span>Role / Scaling Notes</span>
            <textarea
              v-model="selectedNode.data.notes"
              class="form-textarea"
              rows="2"
              data-testid="inspector-node-notes"
              placeholder="Sharding key, TTL, replication factor..."
            />
          </label>
        </div>

        <!-- Edge Inspector -->
        <div v-else-if="selectedEdge" class="sd-inspector-box" data-testid="edge-inspector">
          <div class="sd-inspector-head">
            <h4>Selected Connection</h4>
            <button
              type="button"
              class="btn-icon-danger"
              title="Remove connection"
              @click="removeSelectedEdge"
            >
              <Trash2 :size="14" />
            </button>
          </div>
          <label class="sd-field-label">
            <span>Protocol / Channel</span>
            <select
              v-model="selectedEdge.data.protocol"
              class="form-select"
              @change="syncSelectedEdgeMeta"
            >
              <option v-for="proto in EDGE_PROTOCOL_OPTIONS" :key="proto" :value="proto">
                {{ proto }}
              </option>
            </select>
          </label>
          <label class="sd-field-label">
            <span>Delivery Semantics</span>
            <select
              v-model="selectedEdge.data.delivery_mode"
              class="form-select"
              @change="syncSelectedEdgeMeta"
            >
              <option value="sync">Synchronous</option>
              <option value="async">Asynchronous</option>
            </select>
          </label>
          <label class="sd-field-label">
            <span>Flow Description</span>
            <input
              v-model="selectedEdge.data.text_label"
              type="text"
              class="form-input"
              placeholder="e.g. Read-through lookup"
              @input="syncSelectedEdgeMeta"
            />
          </label>
        </div>

        <div v-else class="sd-inspector-box sd-inspector-idle">
          <p class="sd-muted">
            Click any block or arrow on the canvas to attach technology choices (`Redis`, `Postgres`), notes, or protocol details.
          </p>
        </div>

        <!-- Overall Canvas Notes & Submit -->
        <label class="sd-field-label">
          <span>Architecture Summary Notes</span>
          <textarea
            v-model="canvasNotes"
            class="form-textarea"
            rows="3"
            data-testid="canvas-notes-input"
            placeholder="Summarize read vs write paths, partitioning key, replication, or back-of-envelope numbers..."
          />
        </label>

        <details class="sd-flow-preview-box" data-testid="flow-json-preview">
          <summary>
            <Code2 :size="14" />
            <span>
              Extracted Flow JSON ({{ nodes.length }} blocks, {{ edges.length }} flows)
            </span>
          </summary>
          <pre class="sd-flow-json-pre">{{ JSON.stringify(flowPreviewPayload, null, 2) }}</pre>
        </details>

        <div class="sd-inspector-actions">
          <button
            type="button"
            class="btn btn-primary w-full"
            data-testid="save-canvas-btn"
            :disabled="!nodes.length || saving"
            @click="handleSaveCanvas"
          >
            <Loader2 v-if="saving" :size="14" class="spin" />
            <Layers v-else :size="14" />
            <span>Save Canvas Revision (v{{ nextVersionNumber }})</span>
          </button>

          <button
            v-if="hasCanvasRevisions"
            type="button"
            class="btn btn-secondary w-full"
            data-testid="analyze-canvas-btn"
            :disabled="reviewing"
            @click="emit('analyze-latest')"
          >
            <Loader2 v-if="reviewing" :size="14" class="spin" />
            <Sparkles v-else :size="14" />
            <span>Analyze Architecture with AI</span>
          </button>

          <button
            type="button"
            class="btn btn-ghost btn-sm w-full"
            @click="emit('switch-to-upload')"
          >
            <Upload :size="13" />
            <span>Prefer Excalidraw / PNG? Switch to Image Upload</span>
          </button>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.sd-canvas-workspace {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sd-canvas-toolbar,
.sd-quick-connect-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
}

.sd-toolbar-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.sd-hint-tray {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--accent, #3b82f6) 40%, var(--border-subtle, #334155));
  background: color-mix(in srgb, var(--accent, #3b82f6) 8%, var(--bg-surface, #1e293b));
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  font-size: 0.85rem;
}

.sd-hint-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sd-hint-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  color: var(--text-primary, #f8fafc);
  font-size: 0.8rem;
  cursor: pointer;
}

.sd-hint-pill.placed {
  border-color: #10b981;
  color: #10b981;
}

.sd-placed-check {
  color: #10b981;
}

.sd-quick-connect-bar {
  justify-content: flex-start;
}

.sd-qc-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.82rem;
  font-weight: 600;
}

.sd-qc-select {
  min-width: 145px;
  max-width: 190px;
}

.sd-qc-proto {
  min-width: 120px;
  max-width: 150px;
}

.sd-qc-mode {
  min-width: 90px;
  max-width: 110px;
}

.sd-qc-note {
  min-width: 150px;
  flex: 1;
}

.sd-canvas-grid {
  display: grid;
  grid-template-columns: 245px minmax(340px, 1fr) 285px;
  gap: 12px;
  align-items: stretch;
}

.sd-palette-pane,
.sd-inspector-pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
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
  gap: 5px;
}

.sd-cat-pill {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
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
  gap: 7px;
  padding: 10px;
  border-radius: 8px;
  border: 1px dashed var(--border-subtle, #475569);
  background: var(--bg-elevated, rgba(15, 23, 42, 0.35));
}

.sd-palette-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 410px;
  overflow-y: auto;
  padding-right: 2px;
}

.sd-palette-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 7px 9px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, rgba(148, 163, 184, 0.06));
  color: var(--text-primary, #f8fafc);
  font-size: 0.8rem;
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

.sd-flow-stage {
  position: relative;
  min-height: 540px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  overflow: hidden;
}

.sd-vue-flow {
  width: 100%;
  height: 100%;
  min-height: 540px;
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

.sd-inspector-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, rgba(148, 163, 184, 0.05));
}

.sd-inspector-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sd-inspector-head h4 {
  margin: 0;
  font-size: 0.86rem;
}

.btn-icon-danger {
  border: none;
  background: transparent;
  color: #ef4444;
  cursor: pointer;
  padding: 4px;
}

.sd-field-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.78rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-flow-preview-box {
  border: 1px solid var(--border-subtle, #334155);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 0.78rem;
}

.sd-flow-preview-box summary {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.sd-flow-json-pre {
  margin: 8px 0 0;
  max-height: 180px;
  overflow: auto;
  font-size: 0.7rem;
  line-height: 1.35;
}

.sd-inspector-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
}

@media (max-width: 1120px) {
  .sd-canvas-grid {
    grid-template-columns: 1fr;
  }

  .sd-palette-list {
    max-height: 200px;
  }

  .sd-flow-stage,
  .sd-vue-flow {
    min-height: 420px;
  }
}
</style>
