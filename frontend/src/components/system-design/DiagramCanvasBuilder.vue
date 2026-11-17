<script setup>
import { Background } from '@vue-flow/background'
import { ControlButton, Controls } from '@vue-flow/controls'
import { ConnectionMode, MarkerType, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import {
  Cloud,
  Layers,
  Maximize2,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import {
  CLOUD_EQUIVALENTS_BY_TYPE,
  CUSTOM_ICON_OPTIONS,
  DEFAULT_CLOUD_PROVIDERS,
  DEFAULT_DIAGRAM_BLOCKS,
  DEFAULT_DIAGRAM_CATEGORIES,
  formatEdgeDisplayLabel,
  getBlockEquivalents,
  resolveBlockCloudDisplay,
  resolveDiagramIcon,
  evaluateDrawnWireFeedback,
  serializeFlowEdges,
  serializeFlowNodes,
} from '../../utils/diagramCatalog'
import ArchitectureNode from './ArchitectureNode.vue'

const props = defineProps({
  session: { type: Object, default: null },
  catalog: { type: Object, default: null },
  loadedFlow: { type: Object, default: null },
  notes: { type: String, default: '' },
  expectedPaths: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:notes', 'flow-change', 'wire-feedback'])

const { fitView, screenToFlowCoordinate } = useVueFlow({ id: 'sd-canvas-builder' })

const nodes = ref([])
const edges = ref([])
const activeScopeId = ref(null)
const scopedNodes = computed({
  get: () =>
    nodes.value.filter(
      (node) => String(node.data?.parent_node_id || '') === String(activeScopeId.value || '')
    ),
  set: (nextNodes) => {
    const visibleIds = new Set(scopedNodes.value.map((node) => node.id))
    const nextById = new Map((nextNodes || []).map((node) => [node.id, node]))
    nodes.value = [
      ...nodes.value.flatMap((node) => {
        if (!visibleIds.has(node.id)) return [node]
        return nextById.has(node.id) ? [nextById.get(node.id)] : []
      }),
      ...(nextNodes || []).filter((node) => !visibleIds.has(node.id)),
    ]
  },
})
const scopedEdges = computed({
  get: () => {
    const visibleIds = new Set(scopedNodes.value.map((node) => node.id))
    return edges.value.filter(
      (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)
    )
  },
  set: (nextEdges) => {
    const visibleIds = new Set(scopedNodes.value.map((node) => node.id))
    const currentScopeEdges = edges.value.filter(
      (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)
    )
    const currentEdgeIds = new Set(currentScopeEdges.map((edge) => edge.id))
    const nextById = new Map((nextEdges || []).map((edge) => [edge.id, edge]))
    edges.value = [
      ...edges.value.flatMap((edge) => {
        if (!currentEdgeIds.has(edge.id)) return [edge]
        return nextById.has(edge.id) ? [nextById.get(edge.id)] : []
      }),
      ...(nextEdges || []).filter((edge) => !currentEdgeIds.has(edge.id)),
    ]
  },
})

const cloudProvider = ref(props.session?.diagram_guidance?.cloud_provider || 'generic')
const searchQuery = ref('')
const showCustomCreator = ref(false)
const customName = ref('')
const customCategory = ref('compute_services')
const customIcon = ref('box')
const customTech = ref('')
const customNotes = ref('')
const customNameInput = ref(null)
const customBlockTrigger = ref(null)

const selectedNodeId = ref(null)
const selectedEdgeId = ref(null)
const popoverAnchor = ref(null)
const canvasStageEl = ref(null)
const edgeLabelInputEl = ref(null)
const undoStack = ref([])
const canUndo = computed(() => undoStack.value.length > 0)

const categories = computed(() =>
  props.catalog?.categories?.length ? props.catalog.categories : DEFAULT_DIAGRAM_CATEGORIES
)
const catalogBlocks = computed(() =>
  props.catalog?.blocks?.length ? props.catalog.blocks : DEFAULT_DIAGRAM_BLOCKS
)
const providers = computed(() =>
  props.catalog?.providers?.length ? props.catalog.providers : DEFAULT_CLOUD_PROVIDERS
)
const scenarioBlocks = computed(() =>
  Array.isArray(props.session?.palette_extensions) ? props.session.palette_extensions : []
)
function blockCloudMeta(item) {
  return resolveBlockCloudDisplay(item, cloudProvider.value, catalogBlocks.value, providers.value)
}

const selectedNodeEquivalents = computed(() => {
  if (!selectedNode.value?.data?.type_id) return []
  return getBlockEquivalents(selectedNode.value.data.type_id, catalogBlocks.value)
})

const RESILIENCE_CHIPS_BY_TYPE = {
  id_generator: ['Pre-allocated Base62 key ranges', 'Active-active standby KGS nodes', 'ZooKeeper/etcd range leases'],
  relational_db: ['Multi-AZ Primary-Replica failover', 'Sharded partition key + TTL index', 'Connection pool (PgBouncer)'],
  nosql_kv: ['Partitioned for high-QPS key distribution', 'Multi-AZ quorum replication', 'Native item TTL lifecycle'],
  read_replica: ['Absorb cold cache-miss reads', 'Async replication lag tolerated'],
  distributed_cache: ['LRU eviction + bounded TTL', 'Singleflight stampede guard', 'Cluster shard + hot-key replication'],
  local_cache: ['Short 5s in-memory hot-key TTL', 'Caps single-key shard spikes'],
  app_service: ['Stateless horizontal autoscaling', 'Circuit-broken downstream timeouts'],
  serverless_fn: ['Provisioned concurrency for tail SLA', 'Pooled DB / RDS Proxy connections'],
  message_queue: ['At-least-once + idempotency key', 'Dead-Letter Queue + exponential backoff'],
  event_stream: ['Partitioned by entity/tenant ID', 'Consumer checkpoint + lag monitoring'],
  stream_processor: ['Tumbling/sliding state checkpoints', 'GDPR PII anonymization before sink'],
}

const selectedNodeNoteChips = computed(() => {
  const tid = selectedNode.value?.data?.type_id || ''
  return (
    RESILIENCE_CHIPS_BY_TYPE[tid] || [
      'Multi-AZ redundancy & health checks',
      'Bounded timeouts + graceful degradation',
    ]
  )
})

function appendResilienceChip(chipText) {
  if (!selectedNode.value) return
  pushUndoSnapshot()
  const current = String(selectedNode.value.data.notes || '').trim()
  if (current.toLowerCase().includes(chipText.toLowerCase())) return
  selectedNode.value.data.notes = current ? `${current}; ${chipText}` : chipText
}

const filteredScenarioBlocks = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return scenarioBlocks.value.filter((block) => {
    if (!q) return true
    const haystack = `${block.label || ''} ${block.default_role || ''}`.toLowerCase()
    return haystack.includes(q)
  })
})

const filteredBlocks = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return catalogBlocks.value.filter((block) => {
    if (!q) return true
    const eqValues = Object.values(block.cloud_equivalents || CLOUD_EQUIVALENTS_BY_TYPE[block.type_id] || {}).join(' ')
    const haystack = `${block.label} ${block.default_role || ''} ${(block.keywords || []).join(' ')} ${eqValues}`.toLowerCase()
    return haystack.includes(q)
  })
})
const paletteGroups = computed(() =>
  categories.value
    .map((category) => ({
      ...category,
      blocks: filteredBlocks.value.filter((block) => block.category === category.id),
      scenarioBlocks: filteredScenarioBlocks.value.filter(
        (block) => block.category === category.id
      ),
    }))
    .filter((category) => category.blocks.length || category.scenarioBlocks.length)
)

const selectedNode = computed(
  () => nodes.value.find((n) => n.id === selectedNodeId.value) || null
)
const activeScopeNode = computed(
  () => nodes.value.find((node) => node.id === activeScopeId.value) || null
)
const canOpenSelectedService = computed(
  () =>
    Boolean(selectedNode.value) &&
    !selectedNode.value.data?.parent_node_id &&
    ['app_service', 'microservice', 'serverless_fn', 'async_worker', 'llm_gateway', 'media_transcoder', 'realtime_gateway'].includes(
      String(selectedNode.value.data?.type_id || '')
    )
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
    cloud_provider: cloudProvider.value,
    nodes: serializeFlowNodes(nodes.value),
    edges: serializeFlowEdges(edges.value),
    notes: String(props.notes || '').trim(),
  }
}

watch(
  [nodes, edges, cloudProvider],
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

function nextPlacementPosition() {
  const count = scopedNodes.value.length
  const col = count % 3
  const row = Math.floor(count / 3)
  return { x: 90 + col * 245, y: 80 + row * 145 }
}

function pushUndoSnapshot() {
  const snapshot = buildFlowSnapshot()
  undoStack.value = [...undoStack.value.slice(-24), snapshot]
}

function addBlockToCanvas(block, explicitPos = null, skipUndo = false) {
  if (!skipUndo) {
    pushUndoSnapshot()
  }
  const pos = explicitPos || nextPlacementPosition()
  const id = `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`
  const resolved = block.is_custom || block.type_id === 'custom'
    ? {
        displayTitle: block.label || block.name || 'Custom Block',
        genericLabel: '',
        cloudProvider: 'generic',
        cloudService: '',
      }
    : resolveBlockCloudDisplay(block, cloudProvider.value, catalogBlocks.value, providers.value)

  const newNode = {
    id,
    type: 'architecture',
    position: pos,
    data: {
      type_id: block.type_id || 'custom',
      label: block.label && block.cloud_provider && block.cloud_provider !== 'generic' ? block.label : resolved.displayTitle,
      generic_label: resolved.genericLabel,
      cloud_provider: resolved.cloudProvider,
      category: block.category || 'compute_services',
      icon: block.icon || 'box',
      tech_stack: block.tech_stack || resolved.cloudService || '',
      notes: block.notes || '',
      is_custom: Boolean(block.is_custom || block.type_id === 'custom'),
      parent_node_id: activeScopeId.value,
    },
  }
  nodes.value = [...nodes.value, newNode]
  selectedEdgeId.value = null
  selectedNodeId.value = null
  return newNode
}

function handleCloudProviderChange(nextCloud) {
  const prevCloud = cloudProvider.value
  const target = nextCloud || 'generic'
  if (prevCloud === target) return
  if (nodes.value.length) {
    pushUndoSnapshot()
  }
  cloudProvider.value = target
  nodes.value = nodes.value.map((node) => {
    const tid = node.data?.type_id || 'custom'
    if (node.data?.is_custom || tid === 'custom') return node
    const prevDisplay = resolveBlockCloudDisplay(node.data, prevCloud, catalogBlocks.value, providers.value)
    const nextDisplay = resolveBlockCloudDisplay(node.data, target, catalogBlocks.value, providers.value)
    const allKnownNames = new Set([
      prevDisplay.genericLabel,
      ...prevDisplay.equivalentsList.map((e) => e.serviceName),
    ])
    const currentLabel = String(node.data?.label || '').trim()
    const currentTech = String(node.data?.tech_stack || '').trim()
    const shouldTranslateLabel = !currentLabel || allKnownNames.has(currentLabel)
    const shouldTranslateTech = !currentTech || allKnownNames.has(currentTech)
    return {
      ...node,
      data: {
        ...node.data,
        label: shouldTranslateLabel ? nextDisplay.displayTitle : currentLabel,
        generic_label: nextDisplay.genericLabel,
        cloud_provider: nextDisplay.cloudProvider,
        tech_stack: shouldTranslateTech ? (nextDisplay.cloudService || '') : currentTech,
      },
    }
  })
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
  closeCustomCreator()
}

function openCustomCreator() {
  showCustomCreator.value = true
}

function closeCustomCreator() {
  showCustomCreator.value = false
  nextTick(() => customBlockTrigger.value?.focus())
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
  pushUndoSnapshot()
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
  const srcNode = nodes.value.find((n) => n.id === params.source)
  const dstNode = nodes.value.find((n) => n.id === params.target)
  const wireVerdict = evaluateDrawnWireFeedback(srcNode, dstNode, props.expectedPaths)
  if (wireVerdict) {
    emit('wire-feedback', wireVerdict)
  }
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

function syncEdgeMeta(edge) {
  if (!edge) return
  const isAsync = edge.data?.delivery_mode === 'async'
  edge.animated = isAsync
  edge.style = isAsync ? { strokeDasharray: '6 4', strokeWidth: 2 } : { strokeWidth: 2 }
  edge.label = formatEdgeDisplayLabel(
    edge.data?.protocol,
    edge.data?.delivery_mode,
    edge.data?.text_label
  )
}

function syncSelectedEdgeMeta() {
  syncEdgeMeta(selectedEdge.value)
}

function toggleSelectedEdgeAsync(checked) {
  if (!selectedEdge.value) return
  selectedEdge.value.data.delivery_mode = checked ? 'async' : 'sync'
  syncSelectedEdgeMeta()
}

function removeSelectedNode() {
  if (!selectedNodeId.value) return
  pushUndoSnapshot()
  const id = selectedNodeId.value
  const removedIds = new Set([
    id,
    ...nodes.value
      .filter((node) => node.data?.parent_node_id === id)
      .map((node) => node.id),
  ])
  nodes.value = nodes.value.filter((node) => !removedIds.has(node.id))
  edges.value = edges.value.filter(
    (edge) => !removedIds.has(edge.source) && !removedIds.has(edge.target)
  )
  closePopovers()
}

function removeSelectedEdge() {
  if (!selectedEdgeId.value) return
  pushUndoSnapshot()
  edges.value = edges.value.filter((e) => e.id !== selectedEdgeId.value)
  closePopovers()
}

function clearCanvas(clearAll = false) {
  const scopeNodeIds = new Set(
    (clearAll || !activeScopeId.value
      ? nodes.value
      : nodes.value.filter(
          (node) =>
            String(node.data?.parent_node_id || '') ===
            String(activeScopeId.value || '')
        )
    ).map((node) => node.id)
  )
  if (scopeNodeIds.size || edges.value.length || props.notes) {
    pushUndoSnapshot()
  }
  nodes.value = nodes.value.filter((node) => !scopeNodeIds.has(node.id))
  edges.value = edges.value.filter(
    (edge) => !scopeNodeIds.has(edge.source) && !scopeNodeIds.has(edge.target)
  )
  if (clearAll || !activeScopeId.value) {
    emit('update:notes', '')
  }
  if (clearAll) activeScopeId.value = null
  closePopovers()
}

function openServiceScope(node = selectedNode.value) {
  if (!node || node.data?.parent_node_id) return
  activeScopeId.value = node.id
  closePopovers()
  nextTick(() => fitView({ padding: 0.2 }))
}

function closeServiceScope() {
  activeScopeId.value = null
  closePopovers()
  nextTick(() => fitView({ padding: 0.2 }))
}

function _nodeMatchesActionSpec(node, typeId, label) {
  const nType = String(node?.data?.type_id || '')
  const specType = String(typeId || '')
  if (specType && specType !== 'custom' && nType === specType) return true
  const needle = String(label || '').trim().toLowerCase()
  if (!needle) return false
  const haystack = `${node?.data?.label || ''} ${node?.data?.tech_stack || ''}`.toLowerCase()
  return haystack.includes(needle)
}

function applyCoachAction(action) {
  if (!action || typeof action !== 'object') return false
  pushUndoSnapshot()
  let changed = false

  for (const block of Array.isArray(action.blocks) ? action.blocks : []) {
    if (!block || typeof block !== 'object') continue
    const existing = nodes.value.find((n) =>
      _nodeMatchesActionSpec(n, block.type_id, block.label || block.name)
    )
    if (!existing) {
      const catalogMatch = catalogBlocks.value.find((b) => b.type_id === block.type_id)
      addBlockToCanvas(
        {
          ...(catalogMatch || {}),
          ...block,
        },
        null,
        true
      )
      changed = true
    }
  }

  for (const update of Array.isArray(action.node_updates) ? action.node_updates : []) {
    const node = nodes.value.find((item) => item.id === String(update?.node_id || ''))
    if (!update || !node || !update.changes || typeof update.changes !== 'object') continue
    const nextData = { ...node.data }
    let nodeChanged = false
    for (const field of ['label', 'tech_stack']) {
      if (typeof update.changes[field] !== 'string') continue
      if (nextData[field] === update.changes[field]) continue
      nextData[field] = update.changes[field]
      nodeChanged = true
    }
    if (nodeChanged) {
      node.data = nextData
      changed = true
    }
  }

  for (const edgeSpec of Array.isArray(action.edges) ? action.edges : []) {
    if (!edgeSpec || typeof edgeSpec !== 'object') continue
    const srcNode = nodes.value.find((n) =>
      _nodeMatchesActionSpec(n, edgeSpec.source_type_id, edgeSpec.source_label)
    )
    const tgtNode = nodes.value.find((n) =>
      _nodeMatchesActionSpec(n, edgeSpec.target_type_id, edgeSpec.target_label)
    )
    if (!srcNode || !tgtNode || srcNode.id === tgtNode.id) continue
    const alreadyWired = edges.value.some(
      (e) => e.source === srcNode.id && e.target === tgtNode.id
    )
    if (alreadyWired) continue
    const mode = edgeSpec.delivery_mode === 'async' ? 'async' : 'sync'
    const proto = String(edgeSpec.protocol || '')
    const textLabel = String(edgeSpec.label || '')
    const id = `edge-coach-${srcNode.id}-${tgtNode.id}-${Date.now()}-${Math.floor(Math.random() * 1000)}`
    edges.value = [
      ...edges.value,
      {
        id,
        source: srcNode.id,
        target: tgtNode.id,
        sourceHandle: null,
        targetHandle: null,
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
      },
    ]
    changed = true
  }

  for (const update of Array.isArray(action.edge_updates) ? action.edge_updates : []) {
    const edge = edges.value.find((item) => item.id === String(update?.edge_id || ''))
    if (!update || !edge || !update.changes || typeof update.changes !== 'object') continue
    const nextData = { ...edge.data }
    if (['sync', 'async'].includes(update.changes.delivery_mode)) {
      nextData.delivery_mode = update.changes.delivery_mode
    }
    for (const field of ['protocol', 'label']) {
      if (typeof update.changes[field] === 'string') {
        nextData[field === 'label' ? 'text_label' : field] = update.changes[field]
      }
    }
    const edgeChanged = Object.keys(nextData).some((field) => nextData[field] !== edge.data?.[field])
    if (!edgeChanged) continue
    edge.data = nextData
    syncEdgeMeta(edge)
    changed = true
  }

  if (!changed) {
    undoStack.value = undoStack.value.slice(0, -1)
    return false
  }
  nextTick(() => {
    fitView({ padding: 0.2 })
  })
  return true
}

function undoLastChange() {
  if (!undoStack.value.length) return false
  const prev = undoStack.value[undoStack.value.length - 1]
  undoStack.value = undoStack.value.slice(0, -1)
  hydrateFromFlow(prev, false)
  return true
}

function hydrateFromFlow(flow, resetUndo = true) {
  if (resetUndo) {
    undoStack.value = []
    activeScopeId.value = null
  }
  if (!flow || !Array.isArray(flow.nodes)) return
  if (flow.cloud_provider) {
    cloudProvider.value = flow.cloud_provider
  }
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
      generic_label: n.generic_label || '',
      cloud_provider: n.cloud_provider || flow.cloud_provider || 'generic',
      category: n.category || 'compute_services',
      icon: n.icon || 'box',
      tech_stack: n.tech_stack || '',
      notes: n.notes || '',
      is_custom: Boolean(n.is_custom),
      parent_node_id: n.parent_node_id || null,
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

watch(showCustomCreator, async (isOpen) => {
  if (!isOpen) return
  await nextTick()
  customNameInput.value?.focus()
})

defineExpose({
  getCurrentNodes: () => serializeFlowNodes(nodes.value),
  getCurrentEdges: () => serializeFlowEdges(edges.value),
  getFlowSnapshot: buildFlowSnapshot,
  clearCanvas,
  fitCanvas: () => fitView({ padding: 0.2 }),
  addBlockToCanvas,
  applyCoachAction,
  undoLastChange,
  canUndo,
})
</script>

<template>
  <div class="sd-studio-canvas-shell" data-testid="diagram-canvas-builder">
    <!-- Component Palette -->
    <aside class="sd-studio-palette" aria-label="Architecture component palette">
      <div class="sd-palette-top-row">
        <span class="sd-palette-title">
          <Layers :size="14" />
          <span>Components</span>
        </span>
      </div>

        <label class="sd-palette-search">
          <Search :size="14" />
          <input
            v-model="searchQuery"
            type="text"
            class="form-input sd-search-input"
            data-testid="palette-search-input"
            aria-label="Filter components"
            placeholder="Filter components..."
          />
        </label>
        <p class="sd-palette-hint">Drag onto the canvas, or click to add.</p>

        <div class="sd-palette-list">
          <div
            v-for="(category, categoryIndex) in paletteGroups"
            :key="category.id"
            class="sd-palette-category"
          >
            <details class="sd-palette-category-details" :open="categoryIndex === 0">
              <summary>{{ category.label }}</summary>
              <div v-if="category.scenarioBlocks.length" data-testid="scenario-palette-blocks">
                <button
                  v-for="ext in category.scenarioBlocks"
                  :key="`ext-${ext.type_id}-${ext.label}`"
                  type="button"
                  class="sd-palette-item is-scenario"
                  draggable="true"
                  :data-testid="`palette-block-${ext.type_id}`"
                  :title="`${ext.default_role} (Scenario extension block — click or drag)`"
                  @dragstart="handleDragStart($event, ext)"
                  @click="addBlockToCanvas(ext)"
                >
                  <span class="sd-palette-item-icon">
                    <component :is="resolveDiagramIcon(ext.icon)" :size="15" />
                  </span>
                  <span class="sd-palette-item-text">
                    <span class="sd-palette-item-name">{{ ext.label }}</span>
                    <span class="sd-palette-item-role">Domain extension</span>
                  </span>
                </button>
              </div>
              <button
                v-for="block in category.blocks"
                :key="block.type_id"
                type="button"
                class="sd-palette-item"
                draggable="true"
                :data-testid="`palette-block-${block.type_id}`"
                :title="`${block.default_role} (Click or drag onto canvas)`"
                @dragstart="handleDragStart($event, block)"
                @click="addBlockToCanvas(block)"
              >
                <span class="sd-palette-item-icon">
                  <component :is="resolveDiagramIcon(block.icon)" :size="15" />
                </span>
                <span class="sd-palette-item-text">
                  <span class="sd-palette-item-name">{{ blockCloudMeta(block).displayTitle }}</span>
                  <span
                    v-if="blockCloudMeta(block).genericLabel && blockCloudMeta(block).genericLabel !== blockCloudMeta(block).displayTitle"
                    class="sd-palette-item-role"
                  >
                    {{ blockCloudMeta(block).genericLabel }}
                  </span>
                </span>
              </button>
            </details>
          </div>
        </div>

        <div class="sd-palette-footer">
          <button
            type="button"
            class="sd-custom-block-button"
            data-testid="open-custom-block-btn"
            :aria-expanded="showCustomCreator"
            aria-haspopup="dialog"
            ref="customBlockTrigger"
            @click="openCustomCreator"
          >
            Custom Block
          </button>
          <label class="sd-cloud-lens-label">
            <Cloud :size="13" />
            <span>Cloud</span>
            <select
              :value="cloudProvider"
              class="form-select sd-cloud-select"
              data-testid="cloud-provider-select"
              aria-label="Cloud provider lens"
              @change="handleCloudProviderChange($event.target.value)"
            >
              <option v-for="prov in providers" :key="prov.id" :value="prov.id">
                {{ prov.label }}
              </option>
            </select>
          </label>
        </div>
    </aside>

    <!-- Main Full-Height Interactive Canvas -->
    <div class="sd-studio-main">
      <div
        ref="canvasStageEl"
        class="sd-flow-stage"
        @dragover.prevent
        @drop="handleCanvasDrop"
      >
        <div v-if="activeScopeId" class="sd-scope-breadcrumb" data-testid="service-scope-breadcrumb">
          <button type="button" class="btn btn-secondary btn-sm" @click="closeServiceScope">
            System overview
          </button>
          <span aria-hidden="true">/</span>
          <strong>{{ activeScopeNode?.data?.label || 'Service internals' }}</strong>
          <span class="sd-muted">Internal components stay scoped to this service.</span>
        </div>
        <div v-if="!scopedNodes.length" class="sd-canvas-empty-hint">
          <Layers :size="26" />
          <h2>{{ activeScopeId ? 'Design this service internally' : 'Start with your first block' }}</h2>
          <p>
            {{
              activeScopeId
                ? 'Add only the internals that clarify this service’s responsibilities and trade-offs.'
                : 'Drag a component from the left, or click one to drop it onto the canvas.'
            }}
          </p>
          <ol class="sd-canvas-empty-steps">
            <li><span>1</span>Place blocks</li>
            <li><span>2</span>Wire dot to dot</li>
            <li><span>3</span>Click a wire to describe it</li>
          </ol>
        </div>

        <VueFlow
          id="sd-canvas-builder"
          v-model:nodes="scopedNodes"
          v-model:edges="scopedEdges"
          class="sd-vue-flow"
          :connection-mode="ConnectionMode.Loose"
          :default-viewport="{ zoom: 1, x: 40, y: 40 }"
          @connect="handleVueFlowConnect"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
          @pane-click="closePopovers"
        >
          <Background pattern-color="var(--border-subtle)" :gap="20" />
          <Controls
            position="bottom-center"
            :show-zoom="true"
            :show-fit-view="false"
            :show-interactive="true"
            :fit-view-params="{ padding: 0.2 }"
          >
            <ControlButton
              title="Fit"
              aria-label="Fit"
              @click="fitView({ padding: 0.2 })"
            >
              <Maximize2 :size="14" />
            </ControlButton>
            <ControlButton
              title="Clear canvas"
              aria-label="Clear canvas"
              :disabled="!scopedNodes.length"
              @click="clearCanvas"
            >
              <Trash2 :size="14" />
            </ControlButton>
          </Controls>
          <template #node-architecture="nodeProps">
            <ArchitectureNode v-bind="nodeProps" />
          </template>
        </VueFlow>

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
          <div class="sd-resilience-chips" data-testid="node-resilience-chips">
            <button
              v-for="chip in selectedNodeNoteChips"
              :key="chip"
              type="button"
              class="sd-resilience-chip-btn"
              data-testid="node-resilience-chip"
              title="Click to document this trade-off / hardening pattern"
              @click="appendResilienceChip(chip)"
            >
              + {{ chip }}
            </button>
          </div>
          <div v-if="selectedNodeEquivalents.length" class="sd-cloud-eq-section" data-testid="node-cloud-equivalents">
            <span class="sd-cloud-eq-title">Cross-Cloud Equivalents</span>
            <div class="sd-cloud-eq-grid">
              <div v-for="eq in selectedNodeEquivalents" :key="eq.id" class="sd-cloud-eq-chip">
                <strong>{{ eq.shortLabel }}:</strong> {{ eq.serviceName }}
              </div>
            </div>
          </div>
          <button
            v-if="canOpenSelectedService"
            type="button"
            class="btn btn-secondary btn-sm w-full"
            data-testid="open-service-scope-btn"
            @click="openServiceScope()"
          >
            <Layers :size="14" />
            <span>Open service internals</span>
          </button>
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
    <Teleport to="body">
      <div
        v-if="showCustomCreator"
        class="sd-custom-block-backdrop"
        data-testid="custom-block-modal"
        @click.self="closeCustomCreator"
        @keydown.esc.stop.prevent="closeCustomCreator"
      >
        <section
          class="sd-custom-block-dialog"
          data-testid="custom-block-form"
          role="dialog"
          aria-modal="true"
          aria-labelledby="custom-block-title"
        >
          <div class="sd-custom-block-dialog-header">
            <div>
              <span class="sd-custom-block-eyebrow">Canvas component</span>
              <h2 id="custom-block-title">Create Custom Block</h2>
            </div>
            <button
              type="button"
              class="sd-icon-btn"
              aria-label="Close custom block dialog"
              @click="closeCustomCreator"
            >
              <X :size="16" />
            </button>
          </div>
          <div class="sd-custom-block-fields">
            <label>
              <span>Block name</span>
              <input
                ref="customNameInput"
                v-model="customName"
                type="text"
                class="form-input"
                data-testid="custom-block-name-input"
                placeholder="e.g. Base62 Ring"
              />
            </label>
            <label>
              <span>Category</span>
              <select v-model="customCategory" class="form-select">
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                  {{ cat.label }}
                </option>
              </select>
            </label>
            <label>
              <span>Icon</span>
              <select v-model="customIcon" class="form-select">
                <option v-for="opt in CUSTOM_ICON_OPTIONS" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </label>
            <label>
              <span>Technology or engine <span class="sd-muted">(optional)</span></span>
              <input
                v-model="customTech"
                type="text"
                class="form-input"
                data-testid="custom-block-tech-input"
                placeholder="e.g. Go + Etcd Lease"
              />
            </label>
          </div>
          <div class="sd-custom-block-dialog-actions">
            <button type="button" class="btn btn-secondary" @click="closeCustomCreator">
              Cancel
            </button>
            <button
              type="button"
              class="btn btn-primary"
              data-testid="add-custom-block-btn"
              :disabled="!customName.trim()"
              @click="handleAddCustomBlock"
            >
              <Plus :size="14" />
              <span>Add Block</span>
            </button>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.sd-studio-canvas-shell {
  flex: 1;
  min-width: 0;
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
}

.sd-scenario-palette-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-bottom: 6px;
  margin-bottom: 3px;
  border-bottom: 1px dashed color-mix(in srgb, var(--border-subtle, #334155) 75%, transparent);
}

.sd-scenario-group-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--accent, #2563eb);
}

.sd-palette-item.is-scenario {
  border-color: color-mix(in srgb, var(--accent, #3b82f6) 45%, var(--border-subtle, #334155));
}

.sd-cloud-lens-box {
  display: flex;
  flex-direction: column;
}

.sd-cloud-lens-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.74rem;
  font-weight: 650;
  color: var(--text-secondary, #94a3b8);
}

.sd-cloud-select {
  flex: 1;
  font-size: 0.76rem;
  padding: 4px 8px;
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

.sd-custom-block-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background-color: color-mix(in srgb, var(--bg-app) 72%, transparent);
  backdrop-filter: blur(3px);
}

.sd-custom-block-dialog {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: min(100%, 520px);
  max-height: calc(100dvh - 48px);
  overflow: auto;
  padding: 22px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background-color: var(--bg-elevated);
  box-shadow: var(--shadow-lg);
}

.sd-custom-block-dialog-header,
.sd-custom-block-dialog-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sd-custom-block-dialog-header h2 {
  margin: 4px 0 0;
  color: var(--text-main);
  font-size: 18px;
}

.sd-custom-block-eyebrow {
  color: var(--text-muted);
  font-size: 12.5px;
}

.sd-custom-block-fields {
  display: grid;
  gap: 14px;
}

.sd-custom-block-fields label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 13px;
}

.sd-custom-block-dialog-actions {
  justify-content: flex-end;
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
  color: var(--text-main, #f8fafc);
  font-size: 0.78rem;
  cursor: pointer;
}

.sd-palette-item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.sd-palette-item-name {
  font-weight: 600;
  line-height: 1.2;
}

.sd-palette-item-role {
  font-size: 0.67rem;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.15;
}

.sd-cloud-eq-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 6px;
  border-top: 1px solid color-mix(in srgb, var(--border-subtle, #334155) 70%, transparent);
}

.sd-cloud-eq-title {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary, #94a3b8);
}

.sd-cloud-eq-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sd-cloud-eq-chip {
  padding: 2px 6px;
  border-radius: 5px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, rgba(148, 163, 184, 0.08));
  font-size: 0.68rem;
  color: var(--text-main, #f8fafc);
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

.sd-flow-stage {
  position: relative;
  flex: 1;
  min-height: 420px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  overflow: hidden;
}

.sd-scope-breadcrumb {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 6;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: calc(100% - 24px);
  padding: 7px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  color: var(--text-main);
}

.sd-scope-breadcrumb .sd-muted {
  color: var(--text-muted);
  font-size: 0.75rem;
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

  .sd-studio-palette {
    width: 100%;
    max-height: 310px;
    overflow-y: auto;
    flex-shrink: 0;
  }

  .sd-palette-list {
    flex: none;
    max-height: 140px;
  }

  .sd-flow-stage {
    min-height: 460px;
  }
}

.sd-studio-canvas-shell {
  gap: 12px;
  padding: 8px;
}

.sd-studio-palette {
  width: 270px;
  padding: 12px;
  gap: 8px;
  border-radius: var(--radius-md);
  border-color: var(--border-color);
  background: var(--bg-card);
}

.sd-palette-title {
  font-size: 14px;
}

.sd-palette-search {
  min-height: 40px;
  padding: 0 8px;
  border-color: var(--border-color);
  background: var(--bg-input);
}

.sd-palette-search .sd-search-input {
  min-height: 38px;
  font-size: 14px;
}

.sd-palette-hint {
  margin: 0;
  color: var(--text-secondary);
  font-size: 12.5px;
  line-height: 1.35;
}

.sd-palette-list {
  flex: 1;
  min-height: 0;
  gap: 0;
  padding-right: 2px;
}

.sd-palette-category {
  border-bottom: 1px solid var(--border-subtle);
}

.sd-palette-category-details > summary {
  display: flex;
  align-items: center;
  min-height: 44px;
  cursor: pointer;
  list-style: none;
  color: var(--text-main);
  font-size: 13px;
  font-weight: 600;
}

.sd-palette-category-details > summary::-webkit-details-marker,
.sd-palette-category-details > summary::marker {
  display: none;
  content: '';
}

.sd-palette-category-details > summary::before {
  content: '›';
  width: 20px;
  color: var(--text-muted);
}

.sd-palette-category-details[open] > summary::before {
  transform: rotate(90deg);
}

.sd-palette-item {
  min-height: 44px;
  padding: 4px 6px;
  gap: 8px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 14px;
}

.sd-palette-item:hover {
  background: var(--bg-surface-hover);
  border-color: transparent;
}

.sd-palette-item-icon {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--primary-subtle);
  color: var(--text-primary);
}

.sd-palette-item-role,
.sd-palette-plus {
  display: none;
}

.sd-palette-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 0 0 auto;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.sd-custom-block-button {
  min-height: 44px;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  font-size: 14px;
}

.sd-custom-block-button:hover {
  background: var(--bg-surface-hover);
}

.sd-cloud-lens-label {
  min-height: 44px;
  font-size: 12.5px;
}

.sd-cloud-select {
  min-height: 40px;
  font-size: 13px;
}

.sd-studio-main {
  min-height: 0;
  gap: 8px;
}

.sd-flow-stage {
  min-height: 0;
  border-radius: var(--radius-md);
  border-color: var(--border-color);
  background-color: var(--bg-card);
}

.sd-canvas-empty-hint {
  gap: 10px;
  color: var(--text-secondary);
}

.sd-canvas-empty-hint h2 {
  margin: 0;
  color: var(--text-main);
  font-size: 22px;
}

.sd-canvas-empty-hint p {
  max-width: 360px;
  margin: 0;
  font-size: 14px;
}

.sd-canvas-empty-steps {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
}

.sd-canvas-empty-steps li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 40px;
  padding: 4px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  color: var(--text-main);
  font-size: 13px;
}

.sd-canvas-empty-steps li span {
  display: inline-flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: var(--primary);
  color: var(--primary-contrast);
  font-weight: 700;
}

:deep(.vue-flow__controls) {
  display: flex;
  flex-direction: row;
  gap: 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  box-shadow: var(--shadow-sm);
}

:deep(.vue-flow__controls-button) {
  display: inline-flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border: 0;
  border-right: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  color: var(--text-main);
  fill: currentColor;
}

:deep(.vue-flow__controls-button:last-child) {
  border-right: 0;
}

:deep(.vue-flow__controls-button:hover) {
  background: var(--bg-surface-hover);
}

:is(button, summary, input, textarea, select):focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 2px;
}

@media (max-width: 820px) {
  .sd-studio-canvas-shell {
    gap: 8px;
    padding: 8px;
  }

  .sd-studio-palette {
    width: 100%;
  }
}

.sd-resilience-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.sd-resilience-chip-btn {
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px dashed color-mix(in srgb, var(--accent, #3b82f6) 45%, var(--border-subtle, #334155));
  background: color-mix(in srgb, var(--accent, #3b82f6) 8%, transparent);
  color: var(--text-main, #f8fafc);
  font-size: 0.69rem;
  cursor: pointer;
  text-align: left;
}

.sd-resilience-chip-btn:hover {
  background: color-mix(in srgb, var(--accent, #3b82f6) 16%, transparent);
}
</style>
