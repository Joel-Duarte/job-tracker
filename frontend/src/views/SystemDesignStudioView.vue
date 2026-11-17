<script setup>
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  Code2,
  Compass,
  Copy,
  ExternalLink,
  FileImage,
  FileText,
  GitBranch,
  Globe,
  Layers,
  Lightbulb,
  ListChecks,
  Loader2,
  MessageSquare,
  MoreHorizontal,
  Save,
  Send,
  Sparkles,
  Undo2,
  Upload,
  Wand2,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DiagramCanvasBuilder from '../components/system-design/DiagramCanvasBuilder.vue'
import {
  DEFAULT_CLOUD_PROVIDERS,
  DEFAULT_DIAGRAM_BLOCKS,
  evaluateDrawnWireFeedback,
  getBlockEquivalents,
  resolveBlockCloudDisplay,
  resolveDiagramIcon,
} from '../utils/diagramCatalog'
import { renderChatMarkdown } from '../utils/markdownRenderer'
import { useSystemDesignStore } from '../stores/systemDesignStore'
import { useUIStore } from '../stores/uiStore'

const route = useRoute()
const router = useRouter()
const store = useSystemDesignStore()
const uiStore = useUIStore()

const canvasBuilderRef = ref(null)
const canvasNotes = ref('')
const loadedFlow = ref(null)
const activeRevisionVersion = ref(null)
const flowSnapshot = ref({ nodes: [], edges: [], notes: '' })

const activeSidebarTab = ref('reqs')
const showMoreMenu = ref(false)
const showFlowJsonModal = ref(false)
const showImageUploadModal = ref(false)
const useWebSearchReview = ref(false)
const stagedDiagramFile = ref(null)
const stagedPreviewUrl = ref('')
const imageNotesInput = ref('')
const checkedFixIds = ref({})
const coachChatInput = ref('')
const showExternalCoach = ref(false)
const externalActionJsonInput = ref('')
const externalPromptCopied = ref(false)
const moreMenuRef = ref(null)
const pendingCoachAction = ref(null)
const coachActionTrigger = ref(null)
const coachActionApplyButton = ref(null)

const coachActionPreviewRows = computed(() => buildCoachActionPreview(pendingCoachAction.value))

watch(pendingCoachAction, (action) => {
  if (action) nextTick(() => coachActionApplyButton.value?.focus())
})

const sessionId = computed(() => Number(route.params.sessionId))
const session = computed(() => store.activeSession)
const challengeTitle = computed(() => session.value?.challenge?.title || 'Architecture Design Studio')
const isCoached = computed(() => store.isActiveSessionCoached)
const canUndoCanvas = computed(() => Boolean(canvasBuilderRef.value?.canUndo))
const sessionLedger = computed(() => session.value?.requirements_ledger || {})
const activeStudyNotes = computed(() => {
  const sn = store.studyNotes || session.value?.study_notes || {}
  return {
    bottlenecks: Array.isArray(sn.common_bottlenecks_and_spofs) ? sn.common_bottlenecks_and_spofs : [],
    traps: Array.isArray(sn.over_engineering_traps) ? sn.over_engineering_traps : [],
    questions: Array.isArray(sn.defence_questions) ? sn.defence_questions : [],
  }
})
const hasStudyNotes = computed(
  () =>
    activeStudyNotes.value.bottlenecks.length > 0 ||
    activeStudyNotes.value.traps.length > 0 ||
    activeStudyNotes.value.questions.length > 0
)
const scaleMathSummary = computed(() => {
  const estimates = sessionLedger.value?.scale_estimates || {}
  const entries = Object.entries(estimates).filter(([, v]) => String(v || '').trim())
  const nfrs = sessionLedger.value?.non_functional_requirements || []
  const latencyLine = nfrs.find((n) => /ms|latency|p99|p95|sla|availability|%/i.test(n)) || ''
  return {
    items: entries.slice(0, 4).map(([k, v]) => ({
      label: k.replace(/_/g, ' '),
      value: String(v),
    })),
    latencyLine,
  }
})
const placedNodeTypeSet = computed(
  () => new Set((flowSnapshot.value?.nodes || []).map((n) => n.type_id))
)
const drawnEdgePairs = computed(() => {
  const nodesById = new Map((flowSnapshot.value?.nodes || []).map((n) => [String(n.id), n]))
  const pairs = new Set()
  for (const edge of flowSnapshot.value?.edges || []) {
    const srcNode = nodesById.get(String(edge.source))
    const tgtNode = nodesById.get(String(edge.target))
    const srcType = String(srcNode?.type_id || srcNode?.data?.type_id || '').trim()
    const tgtType = String(tgtNode?.type_id || tgtNode?.data?.type_id || '').trim()
    if (srcType && tgtType) {
      pairs.add(`${srcType}->${tgtType}`)
    }
  }
  return pairs
})

const normalizedExpectedPaths = computed(() => {
  const satisfiedIds = new Set(store.lastTopologyFeedback?.satisfied_paths || [])
  return (store.expectedPaths || []).map((path, pIdx) => {
    const id = path?.id || path?.name || `path-${pIdx}`
    const title = path?.title || path?.name || `Path ${pIdx + 1}`
    const steps = (path?.steps || []).map((step, sIdx) => {
      if (typeof step === 'string') {
        const clean = step.replace(/_/g, ' ')
        return {
          key: `${id}-${step}-${sIdx}`,
          label: clean,
          sublabel: '',
          satisfied: placedNodeTypeSet.value.has(step),
          placedBoth: placedNodeTypeSet.value.has(step),
        }
      }
      if (step && typeof step === 'object') {
        const src = step.source_label || step.source_type_id || 'Source'
        const tgt = step.target_label || step.target_type_id || 'Target'
        const liveWired = Boolean(
          step.source_type_id &&
            step.target_type_id &&
            drawnEdgePairs.value.has(`${step.source_type_id}->${step.target_type_id}`)
        )
        const livePlacedBoth = Boolean(
          step.source_type_id &&
            step.target_type_id &&
            placedNodeTypeSet.value.has(step.source_type_id) &&
            placedNodeTypeSet.value.has(step.target_type_id)
        )
        return {
          key: `${id}-${step.source_type_id || src}-${step.target_type_id || tgt}-${sIdx}`,
          source_type_id: step.source_type_id || '',
          target_type_id: step.target_type_id || '',
          delivery_mode: step.delivery_mode || 'sync',
          label: `${src} → ${tgt}`,
          sublabel: step.suggested_label || '',
          satisfied: Boolean(step.satisfied) || liveWired,
          placedBoth: Boolean(step.placed_both) || livePlacedBoth,
        }
      }
      return {
        key: `${id}-step-${sIdx}`,
        label: String(step || ''),
        sublabel: '',
        satisfied: false,
        placedBoth: false,
      }
    })
    const liveCompleted = steps.filter((s) => s.satisfied).length
    const completed =
      typeof path?.completed === 'number' ? Math.max(path.completed, liveCompleted) : liveCompleted
    const total = typeof path?.total === 'number' ? path.total : steps.length
    const satisfied =
      typeof path?.satisfied === 'boolean'
        ? path.satisfied || (total > 0 && completed >= total)
        : satisfiedIds.has(id) || satisfiedIds.has(title) || (total > 0 && completed >= total)
    return {
      id,
      title,
      description: path?.description || '',
      completed,
      total,
      satisfied,
      steps,
    }
  })
})

const liveWireChecks = computed(() => {
  const nodesById = new Map((flowSnapshot.value?.nodes || []).map((n) => [String(n.id), n]))
  const items = []
  const seen = new Set()
  for (const edge of flowSnapshot.value?.edges || []) {
    const srcNode = nodesById.get(String(edge.source))
    const tgtNode = nodesById.get(String(edge.target))
    if (!srcNode || !tgtNode) continue
    const verdict = evaluateDrawnWireFeedback(srcNode, tgtNode, store.expectedPaths || [])
    if (!verdict) continue
    const srcKey = String(srcNode?.type_id || srcNode?.data?.type_id || srcNode?.label || srcNode.id)
    const tgtKey = String(tgtNode?.type_id || tgtNode?.data?.type_id || tgtNode?.label || tgtNode.id)
    const dedupKey = `${verdict.status}:${srcKey}->${tgtKey}`
    if (seen.has(dedupKey)) continue
    seen.add(dedupKey)
    items.push({
      key: edge.id || dedupKey,
      ...verdict,
    })
  }
  return items
})

const verifiedConnections = computed(() =>
  liveWireChecks.value.filter((item) => item.status === 'correct')
)

const liveWireWarnings = computed(() =>
  liveWireChecks.value.filter((item) => item.status === 'warning')
)

const liveCapabilityChecks = computed(() => {
  const sourceCaps =
    store.capabilitiesChecklist?.length
      ? store.capabilitiesChecklist
      : store.lastTopologyFeedback?.capability_checks || []
  const placedNodes = flowSnapshot.value?.nodes || []
  const edges = flowSnapshot.value?.edges || []
  const wiredNodeIds = new Set()
  for (const e of edges) {
    wiredNodeIds.add(String(e.source))
    wiredNodeIds.add(String(e.target))
  }
  const backendMap = new Map(
    (store.lastTopologyFeedback?.capability_checks || []).map((c) => [c.id, c])
  )

  return sourceCaps.map((cap, idx) => {
    const groups = cap.accepted_type_groups || cap.accepted_types || []
    let matchedNodes = []
    for (const grp of groups) {
      const grpArr = Array.isArray(grp) ? grp : [grp]
      const scopes = Array.from(
        new Set(placedNodes.map((node) => String(node.parent_node_id || '')))
      )
      for (const scope of scopes) {
        const scopeNodes = placedNodes.filter(
          (node) => String(node.parent_node_id || '') === scope
        )
        if (
          grpArr.length &&
          grpArr.every((typeId) =>
            scopeNodes.some((node) => String(node.type_id || '') === String(typeId))
          )
        ) {
          matchedNodes = scopeNodes.filter((node) =>
            grpArr.includes(String(node.type_id || ''))
          )
          break
        }
      }
      if (matchedNodes.length) break
    }
    const backendItem = backendMap.get(cap.id)
    let status = 'pending'
    let satisfiedBy = ''
    if (matchedNodes.length) {
      const allWired =
        placedNodes.length === 1 || matchedNodes.every((n) => wiredNodeIds.has(String(n.id)))
      status = allWired ? 'met' : 'partial'
      satisfiedBy = Array.from(
        new Set(matchedNodes.map((n) => n?.label || n?.data?.label || n?.type_id))
      ).join(', ')
    } else if (backendItem?.status && backendItem.status !== 'pending') {
      status = backendItem.status
      satisfiedBy = backendItem.satisfied_by || ''
    }
    return {
      id: cap.id || `cap-${idx}`,
      title: cap.title,
      goal: cap.goal,
      status,
      satisfied_by: satisfiedBy,
    }
  })
})

const metCapabilitiesCount = computed(
  () => liveCapabilityChecks.value.filter((c) => c.status === 'met').length
)

const liveBonusChecks = computed(() => {
  const source =
    session.value?.bonus_capabilities_checklist?.length
      ? session.value.bonus_capabilities_checklist
      : store.lastTopologyFeedback?.bonus_capability_checks || []
  const placedNodes = flowSnapshot.value?.nodes || []
  const edges = flowSnapshot.value?.edges || []
  const wiredNodeIds = new Set(
    edges.flatMap((edge) => [String(edge.source), String(edge.target)])
  )

  return source.map((capability, index) => {
    let matchedNodes = []
    for (const rawGroup of capability.accepted_type_groups || []) {
      const group = Array.isArray(rawGroup) ? rawGroup : [rawGroup]
      const scopes = Array.from(
        new Set(placedNodes.map((node) => String(node.parent_node_id || '')))
      )
      for (const scope of scopes) {
        const scopeNodes = placedNodes.filter(
          (node) => String(node.parent_node_id || '') === scope
        )
        if (
          group.length &&
          group.every((typeId) =>
            scopeNodes.some((node) => String(node.type_id || '') === String(typeId))
          )
        ) {
          matchedNodes = scopeNodes.filter((node) =>
            group.includes(String(node.type_id || ''))
          )
          break
        }
      }
      if (matchedNodes.length) break
    }

    const allWired =
      matchedNodes.length > 0 &&
      matchedNodes.every((node) => wiredNodeIds.has(String(node.id)))
    const status = allWired ? 'met' : matchedNodes.length ? 'partial' : 'pending'
    return {
      id: capability.id || `bonus-${index}`,
      title: capability.title,
      goal: capability.goal,
      status,
      points: Number(capability.points || 1),
      earned_points: allWired ? Number(capability.points || 1) : 0,
      satisfied_by: Array.from(
        new Set(matchedNodes.map((node) => node.label || node.type_id))
      ).join(', '),
    }
  })
})
const earnedBonusPoints = computed(() =>
  liveBonusChecks.value.reduce((sum, check) => sum + check.earned_points, 0)
)
const maximumBonusPoints = computed(() =>
  liveBonusChecks.value.reduce((sum, check) => sum + check.points, 0)
)

const revealedComponents = computed(
  () => session.value?.diagram_guidance?.revealed_components || []
)
const nextReferenceStep = computed(() =>
  normalizedExpectedPaths.value.flatMap((path) => path.steps).find((step) => !step.satisfied)
)
const nextGuidanceMode = computed(() => {
  if (!normalizedExpectedPaths.value.length) return 'next_component'
  if (!nextReferenceStep.value) return 'check_topology'
  return nextReferenceStep.value.placedBoth ? 'next_connection' : 'next_component'
})
const nextGuidanceLabel = computed(() =>
  nextGuidanceMode.value === 'check_topology' ? 'Run Topology Check' : 'Reveal Next Step'
)
const featuredGuidedComponent = computed(
  () =>
    revealedComponents.value.find((item) => !isGuidedComponentPlaced(item)) || null
)
const otherRevealedComponents = computed(() =>
  revealedComponents.value.filter((item) => item !== featuredGuidedComponent.value)
)
const placedGuidedComponentCount = computed(
  () => revealedComponents.value.filter((item) => isGuidedComponentPlaced(item)).length
)
const pendingReviewFixCount = computed(
  () => store.reviewFixChecklist.filter((item) => !checkedFixIds.value[item.id]).length
)

function isGuidedComponentPlaced(item) {
  const targetName = String(item?.name || item?.label || '').toLowerCase()
  const targetType = String(item?.type_id || '')
  return (flowSnapshot.value?.nodes || []).some((node) => {
    const nodeType = String(node.type_id || node.data?.type_id || '')
    if (targetType && targetType !== 'custom' && nodeType === targetType) return true
    const combined = `${node.label || node.data?.label || ''} ${node.tech_stack || node.data?.tech_stack || ''}`.toLowerCase()
    return targetName && combined.includes(targetName)
  })
}

function getGuidedComponentMeta(item) {
  const blocks = store.diagramCatalog?.blocks || DEFAULT_DIAGRAM_BLOCKS
  const providers = store.diagramCatalog?.providers || DEFAULT_CLOUD_PROVIDERS
  return resolveBlockCloudDisplay(
    item,
    flowSnapshot.value?.cloud_provider || 'generic',
    blocks,
    providers
  )
}

function getGuidedComponentEquivalents(item) {
  const blocks = store.diagramCatalog?.blocks || DEFAULT_DIAGRAM_BLOCKS
  return getBlockEquivalents(item?.type_id, blocks)
}

function handleWireFeedback(verdict) {
  if (!verdict) return
  if (verdict.status === 'correct') {
    uiStore.showToast(`${verdict.title} — ${verdict.detail}`, 'success')
  } else if (verdict.status === 'warning') {
    uiStore.showToast(`${verdict.title} — ${verdict.detail}`, 'warning')
  }
}

const coachBadgeCount = computed(() => {
  const findingsCount = (store.lastTopologyFeedback?.findings || []).filter(
    (f) => f.severity !== 'info'
  ).length
  const pendingFixes = (store.reviewFixChecklist || []).filter(
    (item) => !checkedFixIds.value[item.id]
  ).length
  return findingsCount + pendingFixes + liveWireWarnings.value.length
})
const revisions = computed(() => session.value?.diagrams_metadata || [])
const canvasRevisions = computed(() =>
  revisions.value.filter((d) => d.diagram_kind === 'canvas')
)
const nextVersionNumber = computed(() => revisions.value.length + 1)

function returnToSession(stage = 'DESIGN') {
  router.push({
    path: '/chat',
    query: {
      mode: 'system_design',
      sessionId: String(sessionId.value),
      stage,
    },
  })
}

async function handleSelectRevision(ver) {
  const rev = revisions.value.find((r) => Number(r.version) === Number(ver))
  if (!rev || rev.diagram_kind !== 'canvas') return
  try {
    const flow = await store.loadDiagramFlow(rev.version)
    loadedFlow.value = flow
    activeRevisionVersion.value = rev.version
    canvasNotes.value = flow.notes || ''
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to load canvas revision', 'error')
  }
}

function handleStartBlankCanvas() {
  loadedFlow.value = null
  activeRevisionVersion.value = null
  canvasBuilderRef.value?.clearCanvas(true)
}

function toggleFixChecklistItem(id) {
  checkedFixIds.value = {
    ...checkedFixIds.value,
    [id]: !checkedFixIds.value[id],
  }
}

function openFlowJsonModalFromMore() {
  showMoreMenu.value = false
  showFlowJsonModal.value = true
}

function openImageModalFromMore() {
  showMoreMenu.value = false
  showImageUploadModal.value = true
}

function handleUndoCanvas() {
  const ok = canvasBuilderRef.value?.undoLastChange?.()
  if (ok) {
    uiStore.showToast('Undid last canvas change.', 'info')
  }
}

async function handleRequestHint(hintMode) {
  if (store.loadingDiagramHint) return
  if (hintMode === 'reveal_all' || hintMode === 'next_connection' || hintMode === 'next_component') {
    activeSidebarTab.value = 'bank'
  } else if (hintMode === 'check_topology') {
    activeSidebarTab.value = 'checks'
  }
  try {
    const currentNodes = canvasBuilderRef.value?.getCurrentNodes?.() || flowSnapshot.value.nodes || []
    const currentEdges = canvasBuilderRef.value?.getCurrentEdges?.() || flowSnapshot.value.edges || []
    const cloudProv = flowSnapshot.value?.cloud_provider || 'generic'
    const res = await store.requestDiagramHint(
      hintMode,
      currentNodes,
      currentEdges,
      canvasNotes.value,
      cloudProv
    )
    uiStore.showToast(res?.message || 'Coaching updated!', 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Unable to unlock diagram guidance', 'error')
  }
}

function handleRevealNextStep() {
  return handleRequestHint(nextGuidanceMode.value)
}

async function handleSendCoachChat(overridePrompt = null) {
  const msg = String(overridePrompt ?? coachChatInput.value).trim()
  if (!msg || store.sendingCoachChat) return
  if (overridePrompt === null) {
    coachChatInput.value = ''
  }
  try {
    const currentNodes = canvasBuilderRef.value?.getCurrentNodes?.() || flowSnapshot.value.nodes || []
    const currentEdges = canvasBuilderRef.value?.getCurrentEdges?.() || flowSnapshot.value.edges || []
    const cloudProv = flowSnapshot.value?.cloud_provider || 'generic'
    await store.sendDiagramCoachMessage(msg, currentNodes, currentEdges, canvasNotes.value, cloudProv)
  } catch (err) {
    uiStore.showToast(err.message || 'Coach chat failed', 'error')
  }
}

function formatCoachPreviewFields(item, fields) {
  return fields
    .map(([key, label]) => {
      const value = String(item?.[key] || '').trim() || (key === 'delivery_mode' ? 'sync' : 'Not set')
      return `${label}: ${value}`
    })
    .join(' · ')
}

function buildCoachActionPreview(action) {
  if (!action) return []
  const nodes = canvasBuilderRef.value?.getCurrentNodes?.() || []
  const edges = canvasBuilderRef.value?.getCurrentEdges?.() || []
  const nodesById = new Map(nodes.map((node) => [String(node.id), node]))
  const rows = []

  for (const block of Array.isArray(action.blocks) ? action.blocks : []) {
    if (!block || typeof block !== 'object') continue
    const typeId = String(block.type_id || '')
    const label = String(block.label || block.name || '').trim()
    const alreadyPlaced = nodes.some(
      (node) =>
        (typeId && typeId !== 'custom' && node.type_id === typeId) ||
        (label && String(node.label || '').toLowerCase().includes(label.toLowerCase()))
    )
    if (alreadyPlaced) continue
    rows.push({
      target: 'Block',
      name: label || 'New block',
      before: 'Not on canvas',
      after: [label, block.tech_stack].filter(Boolean).join(' · ') || 'Add block',
    })
  }

  for (const edge of Array.isArray(action.edges) ? action.edges : []) {
    if (!edge || typeof edge !== 'object') continue
    const source = nodes.find((node) => node.type_id === edge.source_type_id)
    const target = nodes.find((node) => node.type_id === edge.target_type_id)
    if (!source || !target) continue
    const alreadyConnected = edges.some(
      (current) => current.source === source.id && current.target === target.id
    )
    if (alreadyConnected) continue
    rows.push({
      target: 'Connection',
      name: `${edge.source_label || source.label} → ${edge.target_label || target.label}`,
      before: 'Not connected',
      after: [edge.label, edge.delivery_mode].filter(Boolean).join(' · ') || 'Add connection',
    })
  }

  for (const update of Array.isArray(action.node_updates) ? action.node_updates : []) {
    const node = nodesById.get(String(update.node_id || ''))
    if (!node || !update.changes || typeof update.changes !== 'object') continue
    const fields = Object.entries(update.changes).filter(([key]) =>
      ['label', 'tech_stack'].includes(key)
    )
    if (!fields.length) continue
    const labels = fields.map(([key]) => [key, key === 'tech_stack' ? 'Technology' : 'Label'])
    rows.push({
      target: 'Block',
      name: node.label || node.generic_label || node.type_id || 'Existing block',
      before: formatCoachPreviewFields(node, labels),
      after: formatCoachPreviewFields({ ...node, ...update.changes }, labels),
    })
  }

  for (const update of Array.isArray(action.edge_updates) ? action.edge_updates : []) {
    const edge = edges.find((item) => item.id === String(update.edge_id || ''))
    if (!edge || !update.changes || typeof update.changes !== 'object') continue
    const fields = Object.entries(update.changes).filter(([key]) =>
      ['label', 'protocol', 'delivery_mode'].includes(key)
    )
    if (!fields.length) continue
    const labels = fields.map(([key]) => [
      key,
      key === 'delivery_mode' ? 'Delivery' : key === 'protocol' ? 'Protocol' : 'Label',
    ])
    const source = nodesById.get(String(edge.source))
    const target = nodesById.get(String(edge.target))
    rows.push({
      target: 'Connection',
      name: `${source?.label || 'Block'} → ${target?.label || 'Block'}`,
      before: formatCoachPreviewFields(edge, labels),
      after: formatCoachPreviewFields({ ...edge, ...update.changes }, labels),
    })
  }

  return rows
}

function handleApplyCoachAction(action) {
  if (!action || pendingCoachAction.value) return
  coachActionTrigger.value = typeof document === 'undefined' ? null : document.activeElement
  pendingCoachAction.value = action
}

function closeCoachActionPreview() {
  pendingCoachAction.value = null
  nextTick(() => coachActionTrigger.value?.focus?.())
}

function confirmCoachAction() {
  const action = pendingCoachAction.value
  if (!action) return
  pendingCoachAction.value = null
  const applied = canvasBuilderRef.value?.applyCoachAction?.(action)
  const actionName = action.title || action.label || 'Coach suggestion'
  if (applied) {
    uiStore.showToast(`Applied "${actionName}" to canvas (Undo available).`, 'success')
  } else {
    uiStore.showToast(`"${actionName}" no longer has applicable canvas changes.`, 'info')
  }
  nextTick(() => coachActionTrigger.value?.focus?.())
}

function buildActionFromPaths(actionTitle, pathItems) {
  const cloudProv = flowSnapshot.value?.cloud_provider || 'generic'
  const catalogBlocks = store.diagramCatalog?.blocks || DEFAULT_DIAGRAM_BLOCKS
  const providers = store.diagramCatalog?.providers || DEFAULT_CLOUD_PROVIDERS
  const blocks = []
  const edges = []
  const seenBlocks = new Set()
  const seenEdges = new Set()

  for (const pathObj of pathItems || []) {
    for (const step of pathObj?.steps || []) {
      const srcTid = step.source_type_id
      const dstTid = step.target_type_id
      for (const tid of [srcTid, dstTid]) {
        if (!tid || seenBlocks.has(tid)) continue
        seenBlocks.add(tid)
        const base =
          catalogBlocks.find((b) => b.type_id === tid) ||
          DEFAULT_DIAGRAM_BLOCKS.find((b) => b.type_id === tid) || {
            type_id: tid,
            label: tid,
            category: 'compute_services',
            icon: 'box',
          }
        const resolved = resolveBlockCloudDisplay(base, cloudProv, catalogBlocks, providers)
        blocks.push({
          ...base,
          label: resolved.displayTitle,
          generic_label: resolved.genericLabel,
          cloud_provider: resolved.cloudProvider,
          tech_stack: resolved.cloudService || base.tech_stack || '',
        })
      }
      if (srcTid && dstTid) {
        const edgeKey = `${srcTid}->${dstTid}`
        if (!seenEdges.has(edgeKey)) {
          seenEdges.add(edgeKey)
          edges.push({
            source_type_id: srcTid,
            target_type_id: dstTid,
            label: step.sublabel || step.suggested_label || '',
            delivery_mode: step.delivery_mode || 'sync',
          })
        }
      }
    }
  }
  return { id: actionTitle, title: actionTitle, blocks, edges }
}

async function handleBuildPathFlow(pathObj) {
  if (!pathObj) return
  const matchingBackend = (store.referenceActions || []).find(
    (act) => act.id === `apply_${pathObj.id}`
  )
  const rawPath =
    (store.expectedPaths || []).find((p) => (p.id || p.name) === pathObj.id) || pathObj
  const action =
    matchingBackend || buildActionFromPaths(pathObj.title || 'Reference Flow', [rawPath])
  handleApplyCoachAction(action)
}

async function handleBuildFullReference() {
  if (store.loadingDiagramHint) return
  try {
    if (!store.expectedPaths.length) {
      await handleRequestHint('reveal_all')
    }
    const matchingFull = (store.referenceActions || []).find(
      (act) => act.id === 'build_full_reference'
    )
    const action =
      matchingFull ||
      buildActionFromPaths('Full Reference Blueprint', store.expectedPaths || [])
    handleApplyCoachAction(action)
  } catch (err) {
    uiStore.showToast(err.message || 'Unable to build reference blueprint', 'error')
  }
}

async function handleExportExternalCoach(promptKind = 'initial') {
  try {
    const currentNodes = canvasBuilderRef.value?.getCurrentNodes?.() || flowSnapshot.value.nodes || []
    const currentEdges = canvasBuilderRef.value?.getCurrentEdges?.() || flowSnapshot.value.edges || []
    const cloudProv = flowSnapshot.value?.cloud_provider || 'generic'
    const res = await store.prepareFrontierCoachPrompt(
      promptKind,
      currentNodes,
      currentEdges,
      canvasNotes.value,
      cloudProv,
      coachChatInput.value.trim()
    )
    if (res?.markdown_prompt) {
      try {
        await navigator.clipboard?.writeText(res.markdown_prompt)
        externalPromptCopied.value = true
        setTimeout(() => {
          externalPromptCopied.value = false
        }, 2500)
      } catch {
        // Preview textarea still displays prompt cleanly
      }
      uiStore.showToast(
        promptKind === 'delta'
          ? 'Updated canvas snapshot ready! Paste into your external ChatGPT/Claude thread.'
          : 'External Coach prompt ready! Paste into ChatGPT, Claude, or Gemini.',
        'success'
      )
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Unable to prepare external Coach prompt', 'error')
  }
}

function handleApplyExternalActionJson() {
  const raw = String(externalActionJsonInput.value || '').trim()
  if (!raw) return
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i)
  const candidates = [fenced ? fenced[1].trim() : null, raw].filter(Boolean)
  const first = raw.indexOf('{')
  const last = raw.lastIndexOf('}')
  if (first !== -1 && last > first) {
    candidates.push(raw.slice(first, last + 1))
  }
  let parsed = null
  for (const cand of candidates) {
    try {
      const obj = JSON.parse(cand)
      const actionKeys = ['blocks', 'edges', 'node_updates', 'edge_updates']
      if (
        obj &&
        typeof obj === 'object' &&
        actionKeys.some((key) => Array.isArray(obj[key])) &&
        actionKeys.every((key) => obj[key] === undefined || Array.isArray(obj[key]))
      ) {
        parsed = obj
        break
      }
    } catch {
      // try next candidate
    }
  }
  if (!parsed) {
    uiStore.showToast(
      'Paste a valid JSON object containing blocks, edges, node_updates, or edge_updates.',
      'error'
    )
    return
  }
  handleApplyCoachAction(parsed)
  externalActionJsonInput.value = ''
}

async function handleSaveCanvas() {
  const snapshot = canvasBuilderRef.value?.getFlowSnapshot?.() || flowSnapshot.value
  if (!snapshot?.nodes?.length || store.uploadingDiagram) {
    if (!snapshot?.nodes?.length) {
      uiStore.showToast('Add at least one component block before saving.', 'warning')
    }
    return null
  }
  try {
    const updated = await store.submitCanvasDiagram({
      ...snapshot,
      notes: canvasNotes.value.trim(),
    })
    const latest = (updated?.diagrams_metadata || []).slice(-1)[0]
    if (latest) {
      activeRevisionVersion.value = latest.version
    }
    uiStore.showToast(`Saved canvas revision v${latest?.version || nextVersionNumber.value}!`, 'success')
    return updated
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save canvas diagram', 'error')
    return null
  }
}

async function handleAnalyzeArchitecture() {
  if (store.reviewingDiagram) return
  const snapshot = canvasBuilderRef.value?.getFlowSnapshot?.() || flowSnapshot.value
  let targetVersion = revisions.value.length ? revisions.value[revisions.value.length - 1].version : null

  if (snapshot?.nodes?.length) {
    const saved = await handleSaveCanvas()
    if (!saved) return
    const latest = (saved.diagrams_metadata || []).slice(-1)[0]
    targetVersion = latest?.version ?? targetVersion
  }
  if (!targetVersion) {
    uiStore.showToast('Build a canvas diagram or upload an image first.', 'warning')
    return
  }

  try {
    await store.reviewDiagram(targetVersion, useWebSearchReview.value)
    uiStore.showToast('Architecture review completed!', 'success')
    returnToSession('REVIEW')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to analyze architecture', 'error')
  }
}

function stageImageFile(file) {
  if (!file) return
  const validTypes = ['image/png', 'image/jpeg', 'image/webp']
  if (file.type && !validTypes.includes(file.type)) {
    uiStore.showToast('Unsupported image format. Use PNG, JPEG, or WebP.', 'error')
    return
  }
  stagedDiagramFile.value = file
  if (stagedPreviewUrl.value) URL.revokeObjectURL(stagedPreviewUrl.value)
  stagedPreviewUrl.value = URL.createObjectURL(file)
}

function handleStudioPaste(event) {
  if (!showImageUploadModal.value) return
  const items = event.clipboardData?.items || []
  for (const item of items) {
    if (item.type?.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        stageImageFile(file)
        uiStore.showToast('Diagram image pasted!', 'info')
        break
      }
    }
  }
}

async function handleUploadImage() {
  if (!stagedDiagramFile.value || store.uploadingDiagram) return
  try {
    await store.uploadDiagram(stagedDiagramFile.value, imageNotesInput.value)
    stagedDiagramFile.value = null
    if (stagedPreviewUrl.value) {
      URL.revokeObjectURL(stagedPreviewUrl.value)
      stagedPreviewUrl.value = ''
    }
    imageNotesInput.value = ''
    showImageUploadModal.value = false
    uiStore.showToast('Uploaded architecture image revision!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to upload image', 'error')
  }
}

watch(
  () => sessionId.value,
  async (id) => {
    if (!id) return
    await Promise.allSettled([store.loadSession(id), store.fetchDiagramCatalog()])
    const requestedVersion = route.query?.version ? Number(route.query.version) : null
    const targetCanvas =
      (requestedVersion
        ? canvasRevisions.value.find((d) => Number(d.version) === requestedVersion)
        : null) || [...canvasRevisions.value].reverse()[0]
    if (targetCanvas) {
      await handleSelectRevision(targetCanvas.version)
    }
    if (String(route.query?.fixReview || '') === '1' && store.reviewFixChecklist?.length) {
      activeSidebarTab.value = 'checks'
    }
  },
  { immediate: true }
)

function handleDocumentClick(event) {
  if (showMoreMenu.value && moreMenuRef.value && !moreMenuRef.value.contains(event.target)) {
    showMoreMenu.value = false
  }
}

onMounted(() => {
  window.addEventListener('paste', handleStudioPaste)
  document.addEventListener('click', handleDocumentClick)
})

onUnmounted(() => {
  window.removeEventListener('paste', handleStudioPaste)
  document.removeEventListener('click', handleDocumentClick)
  if (stagedPreviewUrl.value) URL.revokeObjectURL(stagedPreviewUrl.value)
})
</script>

<template>
  <div class="sd-studio-page" data-testid="design-studio-page">
    <!-- Minimal 6-Control Top Header -->
    <header class="sd-studio-header" data-testid="design-studio-header">
      <div class="sd-studio-header-left">
        <button
          type="button"
          class="btn btn-secondary btn-sm sd-studio-back-btn"
          data-testid="studio-back-btn"
          aria-label="Back"
          title="Back"
          @click="returnToSession('DESIGN')"
        >
          <ArrowLeft :size="14" />
        </button>

        <div class="sd-studio-title-wrap">
          <h1 class="sd-studio-title">{{ challengeTitle }}</h1>
          <span
            v-if="session"
            class="sd-assistance-pill"
            :class="{ coached: isCoached }"
            data-testid="studio-assistance-pill"
            :title="
              isCoached
                ? 'Coached Run: You used AI Coach / Bank guidance (100 XP on completion).'
                : 'Solo Run: Designing unassisted so far (150 XP bonus on completion).'
            "
          >
            {{ isCoached ? 'Coached (100 XP)' : 'Solo (150 XP)' }}
          </span>
        </div>

      </div>

      <div class="sd-studio-header-right">
        <div ref="moreMenuRef" class="sd-more-menu-wrap">
          <button
            type="button"
            class="btn btn-secondary btn-sm"
            data-testid="studio-more-btn"
            aria-label="More actions"
            title="More actions"
            :aria-expanded="showMoreMenu"
            @click.stop="showMoreMenu = !showMoreMenu"
          >
            <MoreHorizontal :size="14" />
          </button>
          <div v-if="showMoreMenu" class="sd-more-dropdown" data-testid="studio-more-dropdown">
            <label v-if="canvasRevisions.length" class="sd-more-revision">
              <span>Load canvas revision</span>
              <select
                :value="activeRevisionVersion || ''"
                class="form-select sd-rev-select"
                aria-label="Load canvas revision"
                @change="$event.target.value ? handleSelectRevision($event.target.value) : handleStartBlankCanvas()"
              >
                <option value="">+ New Canvas</option>
                <option
                  v-for="rev in canvasRevisions"
                  :key="rev.version"
                  :value="rev.version"
                >
                  v{{ rev.version }} ({{ rev.node_count || 0 }} blocks)
                </option>
              </select>
            </label>
            <button
              v-if="canUndoCanvas"
              type="button"
              class="sd-more-item"
              data-testid="studio-undo-btn"
              @click="showMoreMenu = false; handleUndoCanvas()"
            >
              <Undo2 :size="14" />
              <span>Undo</span>
            </button>
            <button
              type="button"
              class="sd-more-item"
              data-testid="open-flow-json-modal-btn"
              @click="openFlowJsonModalFromMore"
            >
              <Code2 :size="14" />
              <span>View Flow JSON</span>
            </button>
            <button
              type="button"
              class="sd-more-item"
              data-testid="open-image-upload-modal-btn"
              @click="openImageModalFromMore"
            >
              <Upload :size="14" />
              <span>Upload External Image</span>
            </button>
            <label class="sd-more-checkbox" @click.stop>
              <input
                v-model="useWebSearchReview"
                type="checkbox"
                data-testid="review-web-search-checkbox"
              />
              <Globe :size="13" />
              <span>Ground Critique w/ Web Search</span>
            </label>
          </div>
        </div>

        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="save-canvas-btn"
          :disabled="store.uploadingDiagram"
          @click="handleSaveCanvas"
        >
          <Loader2 v-if="store.uploadingDiagram" :size="14" class="spin" />
          <Save v-else :size="14" />
          <span>Save v{{ nextVersionNumber }}</span>
        </button>

        <button
          type="button"
          class="btn btn-primary btn-sm"
          data-testid="analyze-canvas-btn"
          :disabled="store.reviewingDiagram || store.uploadingDiagram"
          @click="handleAnalyzeArchitecture"
        >
          <Loader2 v-if="store.reviewingDiagram" :size="14" class="spin" />
          <Sparkles v-else :size="14" />
          <span>Analyze</span>
        </button>
      </div>
    </header>

    <!-- Main Full-Viewport Canvas Body -->
    <div class="sd-studio-body">
      <DiagramCanvasBuilder
        ref="canvasBuilderRef"
        v-model:notes="canvasNotes"
        :session="session"
        :catalog="store.diagramCatalog"
        :loaded-flow="loadedFlow"
        :expected-paths="store.expectedPaths"
        @flow-change="flowSnapshot = $event"
        @wire-feedback="handleWireFeedback"
      />

      <!-- Docked 4-Tab Studio Assistant Sidebar (Reqs | Coach | Bank | Checks) -->
      <aside class="sd-studio-sidebar" data-testid="learning-coach-drawer">
        <div class="sd-drawer-head">
          <h3>
            <Compass :size="15" />
            <span>Studio Assistant</span>
          </h3>
        </div>

        <div class="sd-coach-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            class="sd-coach-tab"
            :class="{ active: activeSidebarTab === 'reqs' }"
            data-testid="studio-tab-reqs"
            @click="activeSidebarTab = 'reqs'"
          >
            <FileText :size="13" />
            <span>Reqs</span>
          </button>
          <button
            type="button"
            role="tab"
            class="sd-coach-tab"
            :class="{ active: activeSidebarTab === 'coach' }"
            data-testid="coach-tab-chat"
            @click="activeSidebarTab = 'coach'"
          >
            <MessageSquare :size="13" />
            <span>Coach</span>
          </button>
          <button
            type="button"
            role="tab"
            class="sd-coach-tab"
            :class="{ active: activeSidebarTab === 'bank' }"
            data-testid="coach-tab-bank"
            @click="activeSidebarTab = 'bank'"
          >
            <Layers :size="13" />
            <span>Bank</span>
          </button>
          <button
            type="button"
            role="tab"
            class="sd-coach-tab"
            :class="{ active: activeSidebarTab === 'checks' }"
            data-testid="coach-tab-checks"
            @click="activeSidebarTab = 'checks'"
          >
            <ListChecks :size="13" />
            <span>Checks</span>
            <span v-if="coachBadgeCount > 0" class="sd-tab-badge">{{ coachBadgeCount }}</span>
          </button>
        </div>

        <!-- TAB 1: Session Requirements & Architecture Notes -->
        <div v-if="activeSidebarTab === 'reqs'" class="sd-coach-tab-body sd-reqs-tab-body" data-testid="studio-reqs-panel">
          <section class="sd-practice-progression" data-testid="practice-progression">
            <strong>Build in stages</strong>
            <ol>
              <li><b>Baseline:</b> make the core user flow correct and measurable.</li>
              <li><b>Harden:</b> add only the security, recovery, and observability controls the risks justify.</li>
              <li><b>Explore:</b> open a service’s internals only when it clarifies a real bottleneck.</li>
            </ol>
            <span>Optional robustness checks earn separate points; they never reduce the core score.</span>
          </section>
          <details
            v-if="scaleMathSummary.items.length || scaleMathSummary.latencyLine"
            class="sd-scale-math-card"
            data-testid="studio-scale-math-card"
          >
            <summary class="sd-scale-math-head">
              <strong>Back-of-the-Envelope</strong>
              <span class="sd-scale-ratio-chip">
                {{ scaleMathSummary.items.find((item) => /read.?write/i.test(item.label))?.value || '10:1' }}
                read/write
              </span>
              <span class="sd-scale-summary-preview">
                {{
                  [
                    ...scaleMathSummary.items.slice(0, 2).map((i) => `${i.label}: ${i.value}`),
                    scaleMathSummary.latencyLine ? `SLA: ${scaleMathSummary.latencyLine}` : '',
                  ]
                    .filter(Boolean)
                    .join(' · ')
                }}
              </span>
            </summary>
            <dl class="sd-scale-kv-list">
              <div v-for="item in scaleMathSummary.items" :key="item.label" class="sd-scale-kv-row">
                <dt class="sd-scale-kv-key">{{ item.label }}</dt>
                <dd class="sd-scale-kv-val">{{ item.value }}</dd>
              </div>
              <div v-if="scaleMathSummary.latencyLine" class="sd-scale-kv-row">
                <dt class="sd-scale-kv-key">SLA</dt>
                <dd class="sd-scale-kv-val">{{ scaleMathSummary.latencyLine }}</dd>
              </div>
            </dl>
          </details>

          <section
            v-if="
              sessionLedger.functional_requirements?.length ||
              sessionLedger.non_functional_requirements?.length ||
              (Object.keys(sessionLedger.scale_estimates || {}).length && !scaleMathSummary.items.length) ||
              sessionLedger.out_of_scope?.length ||
              sessionLedger.assumptions?.length
            "
            class="sd-notes-ledger-box"
            data-testid="studio-requirements-reference"
          >
            <strong>Session Requirements</strong>
            <div v-if="sessionLedger.functional_requirements?.length" class="sd-ledger-ref-group">
              <span class="sd-ledger-ref-label">Functional</span>
              <ul>
                <li v-for="fr in sessionLedger.functional_requirements" :key="fr">{{ fr }}</li>
              </ul>
            </div>
            <div v-if="sessionLedger.non_functional_requirements?.length" class="sd-ledger-ref-group">
              <span class="sd-ledger-ref-label">Non-Functional</span>
              <ul>
                <li v-for="nfr in sessionLedger.non_functional_requirements" :key="nfr">{{ nfr }}</li>
              </ul>
            </div>
            <div
              v-if="Object.keys(sessionLedger.scale_estimates || {}).length && !scaleMathSummary.items.length"
              class="sd-ledger-ref-group"
            >
              <span class="sd-ledger-ref-label">Scale Estimates</span>
              <dl class="sd-scale-kv-list">
                <div v-for="(val, key) in sessionLedger.scale_estimates" :key="key" class="sd-scale-kv-row">
                  <dt class="sd-scale-kv-key">{{ key }}</dt>
                  <dd class="sd-scale-kv-val">{{ val }}</dd>
                </div>
              </dl>
            </div>
            <div v-if="sessionLedger.assumptions?.length" class="sd-ledger-ref-group">
              <span class="sd-ledger-ref-label">Assumptions &amp; Constraints</span>
              <ul>
                <li v-for="assump in sessionLedger.assumptions" :key="assump">{{ assump }}</li>
              </ul>
            </div>
            <div v-if="sessionLedger.out_of_scope?.length" class="sd-ledger-ref-group">
              <span class="sd-ledger-ref-label">Out of Scope</span>
              <ul>
                <li v-for="oos in sessionLedger.out_of_scope" :key="oos">{{ oos }}</li>
              </ul>
            </div>
          </section>
          <p v-else class="sd-muted sd-coach-empty" data-testid="studio-requirements-empty">
            No structured requirements recorded yet. Go back to Stage 1 to clarify or click Reveal Requirements, or start designing directly.
          </p>

          <label class="sd-field-label">
            <span>Architecture Summary Notes</span>
            <textarea
              v-model="canvasNotes"
              class="form-textarea"
              rows="4"
              data-testid="canvas-notes-input"
              placeholder="Summarize read/write paths, sharding keys, TTL, or trade-offs..."
            />
          </label>
        </div>

        <!-- TAB 2: Interactive Coach Chat + Apply to Canvas -->
        <div v-else-if="activeSidebarTab === 'coach'" class="sd-coach-tab-body" data-testid="coach-chat-panel">
          <div class="sd-coach-starter-chips">
            <button
              type="button"
              class="sd-starter-chip"
              data-testid="coach-starter-missing"
              :disabled="store.sendingCoachChat"
              @click="handleSendCoachChat('Am I missing anything on my canvas right now?')"
            >
              Am I missing anything?
            </button>
            <button
              type="button"
              class="sd-starter-chip"
              data-testid="coach-starter-write-path"
              :disabled="store.sendingCoachChat"
              @click="handleSendCoachChat('Walk me through the core Write Path step by step.')"
            >
              Walk through Write Path
            </button>
            <button
              type="button"
              class="sd-starter-chip"
              data-testid="coach-starter-guide"
              :disabled="store.sendingCoachChat"
              @click="
                handleSendCoachChat(
                  'Using my current canvas and reference path, explain the next missing block or connection, why it is next, and offer one small change I can review and apply.'
                )
              "
            >
              Guide my next step
            </button>
            <button
              type="button"
              class="sd-starter-chip sd-external-coach-toggle"
              :class="{ active: showExternalCoach }"
              data-testid="toggle-external-coach-btn"
              @click="showExternalCoach = !showExternalCoach"
            >
              <ExternalLink :size="11" />
              <span>{{ showExternalCoach ? 'Hide External AI' : 'Use External AI (ChatGPT/Claude)' }}</span>
            </button>
          </div>

          <section
            v-if="showExternalCoach"
            class="sd-external-coach-box"
            data-testid="external-coach-panel"
          >
            <div class="sd-external-coach-head">
              <strong>Coach Externally (Free Browser AI)</strong>
              <span class="sd-muted">Copy canvas context → chat in Claude/ChatGPT</span>
            </div>
            <div class="sd-external-coach-btns">
              <button
                type="button"
                class="btn btn-secondary btn-xs"
                data-testid="copy-external-coach-initial-btn"
                :disabled="store.loadingChallengePrompt"
                @click="handleExportExternalCoach('initial')"
              >
                <Copy :size="11" />
                <span>{{ externalPromptCopied ? 'Copied!' : 'Copy Full Coach Prompt' }}</span>
              </button>
              <button
                type="button"
                class="btn btn-secondary btn-xs"
                data-testid="copy-external-coach-delta-btn"
                :disabled="store.loadingChallengePrompt"
                @click="handleExportExternalCoach('delta')"
              >
                <Copy :size="11" />
                <span>Copy Canvas Update</span>
              </button>
            </div>
            <textarea
              v-if="store.frontierCoachPrompt?.markdown_prompt"
              :value="store.frontierCoachPrompt.markdown_prompt"
              readonly
              rows="4"
              class="form-textarea sd-external-preview"
              data-testid="frontier-coach-prompt-preview"
            />
            <div class="sd-external-import-row">
              <input
                v-model="externalActionJsonInput"
                type="text"
                class="form-input"
                data-testid="external-coach-action-input"
                placeholder="Optional: paste a canvas action with additions or element updates"
              />
              <button
                type="button"
                class="btn btn-secondary btn-xs"
                data-testid="apply-external-coach-action-btn"
                :disabled="!externalActionJsonInput.trim()"
                @click="handleApplyExternalActionJson"
              >
                Review JSON
              </button>
            </div>
          </section>

          <div class="sd-coach-thread" data-testid="coach-chat-thread">
            <div v-if="!store.coachMessages.length" class="sd-coach-welcome">
              <strong>Ask your Coach anything</strong>
              <p>
                The Coach sees your canvas and reference path, explains the next step, and can propose blocks or wires. Changes wait for your approval and can be undone.
              </p>
            </div>
            <div
              v-for="(turn, idx) in store.coachMessages"
              :key="`${turn.timestamp || idx}-${turn.role}`"
              class="sd-coach-msg"
              :class="turn.role"
            >
              <div class="sd-coach-msg-role">
                {{ turn.role === 'user' ? 'You' : 'Coach' }}
              </div>
              <div
                class="sd-coach-msg-text sd-markdown-body"
                v-html="renderChatMarkdown(turn.content)"
              />
              <div
                v-if="turn.role === 'coach' && turn.actions?.length"
                class="sd-coach-actions-list"
              >
                <button
                  v-for="act in turn.actions"
                  :key="act.id"
                  type="button"
                  class="sd-apply-action-btn"
                  data-testid="coach-apply-action-btn"
                  :title="act.description"
                  @click="handleApplyCoachAction(act)"
                >
                  <Wand2 :size="12" />
                  <span>{{ act.title || act.label }}</span>
                </button>
              </div>
            </div>
          </div>

          <div v-if="store.suggestedCoachActions.length && !store.coachMessages.length" class="sd-coach-actions-list">
            <button
              v-for="act in store.suggestedCoachActions"
              :key="act.id"
              type="button"
              class="sd-apply-action-btn"
              data-testid="coach-apply-action-btn"
              @click="handleApplyCoachAction(act)"
            >
              <Wand2 :size="12" />
              <span>{{ act.title || act.label }}</span>
            </button>
          </div>

          <form class="sd-coach-composer" @submit.prevent="handleSendCoachChat()">
            <input
              v-model="coachChatInput"
              type="text"
              class="form-input sd-coach-input"
              data-testid="coach-chat-input"
              placeholder="Ask Coach for guidance or a flow suggestion..."
              :disabled="store.sendingCoachChat"
            />
            <button
              type="submit"
              class="btn btn-primary btn-sm"
              data-testid="coach-chat-send-btn"
              :disabled="store.sendingCoachChat || !coachChatInput.trim()"
            >
              <Loader2 v-if="store.sendingCoachChat" :size="14" class="spin" />
              <Send v-else :size="14" />
            </button>
          </form>
        </div>

        <!-- TAB 3: Guided Bank + Path Milestones -->
        <div v-else-if="activeSidebarTab === 'bank'" class="sd-coach-tab-body sd-scrollable-tab" data-testid="coach-bank-panel">
          <p class="sd-reference-framing" data-testid="reference-blueprint-framing">
            <strong>Reference Blueprint</strong> — 1 valid end-to-end architecture (alternatives that meet Capabilities are welcomed).
          </p>
          <div class="sd-coach-toolbar sd-guided-actions">
            <button
              type="button"
              class="btn btn-primary btn-sm"
              data-testid="reveal-next-step-btn"
              :disabled="store.loadingDiagramHint"
              @click="handleRevealNextStep"
            >
              <Loader2 v-if="store.loadingDiagramHint" :size="13" class="spin" />
              <Compass v-else-if="nextGuidanceMode === 'check_topology'" :size="13" />
              <Lightbulb v-else :size="13" />
              <span>{{ nextGuidanceLabel }}</span>
            </button>
            <button
              type="button"
              class="btn btn-secondary btn-xs"
              data-testid="reveal-bank-btn"
              :disabled="store.loadingDiagramHint"
              @click="handleRequestHint('reveal_all')"
            >
              <Layers :size="13" />
              <span>Reveal All Required</span>
            </button>
          </div>

          <section
            v-if="featuredGuidedComponent"
            class="sd-guided-next-block"
            data-testid="guided-next-component"
          >
            <div class="sd-guided-next-header">
              <component
                :is="resolveDiagramIcon(featuredGuidedComponent.icon)"
                :size="16"
                class="sd-guided-next-icon"
              />
              <div class="sd-guided-next-title">
                <span>Suggested next block</span>
                <strong>{{ getGuidedComponentMeta(featuredGuidedComponent).displayTitle }}</strong>
              </div>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                data-testid="place-guided-next-btn"
                @click="canvasBuilderRef?.addBlockToCanvas(featuredGuidedComponent)"
              >
                <span>Place</span>
              </button>
            </div>
            <p class="sd-guided-next-reason">
              {{ featuredGuidedComponent.why_required || featuredGuidedComponent.hint_role }}
            </p>
            <details
              v-if="featuredGuidedComponent.config_checklist?.length"
              class="sd-guided-checklist"
            >
              <summary>Configuration checklist ({{ featuredGuidedComponent.config_checklist.length }})</summary>
              <ul>
                <li v-for="checkItem in featuredGuidedComponent.config_checklist" :key="checkItem">
                  {{ checkItem }}
                </li>
              </ul>
            </details>
          </section>
          <p
            v-else-if="revealedComponents.length"
            class="sd-guided-complete-note"
            data-testid="guided-bank-complete"
          >
            All revealed blocks are on the canvas. Reveal the next step to continue the reference path.
          </p>
          <p v-else class="sd-muted sd-coach-empty" data-testid="guided-bank-empty">
            Reveal the next step to see the recommended block, why it belongs, and how to configure it.
          </p>

          <details
            v-if="otherRevealedComponents.length"
            class="sd-revealed-components"
            data-testid="all-revealed-components"
          >
            <summary>
              <span>{{ featuredGuidedComponent ? 'Other revealed blocks' : 'Revealed blocks' }}</span>
              <span class="sd-guided-count">{{ otherRevealedComponents.length }}</span>
              <span class="sd-muted">{{ placedGuidedComponentCount }} placed</span>
            </summary>
            <div class="sd-revealed-component-list">
              <details
                v-for="item in otherRevealedComponents"
                :key="`${item.name}-${item.type_id}`"
                class="sd-revealed-component"
                data-testid="guided-component-details"
              >
                <summary>
                  <component :is="resolveDiagramIcon(item.icon)" :size="14" />
                  <span>{{ getGuidedComponentMeta(item).displayTitle }}</span>
                  <span v-if="isGuidedComponentPlaced(item)" class="sd-guided-count">On canvas</span>
                </summary>
                <p class="sd-guided-component-reason">
                  {{ item.why_required || item.hint_role }}
                </p>
                <details v-if="item.config_checklist?.length" class="sd-guided-checklist">
                  <summary>Configuration checklist ({{ item.config_checklist.length }})</summary>
                  <ul>
                    <li v-for="checkItem in item.config_checklist" :key="checkItem">
                      {{ checkItem }}
                    </li>
                  </ul>
                </details>
                <details
                  v-if="getGuidedComponentEquivalents(item).length"
                  class="sd-guided-equivalents"
                  data-testid="hint-cloud-equivalents"
                >
                  <summary>Cloud equivalents</summary>
                  <div class="sd-cloud-eq-grid">
                    <div
                      v-for="equivalent in getGuidedComponentEquivalents(item)"
                      :key="equivalent.id"
                      class="sd-cloud-eq-chip"
                    >
                      <strong>{{ equivalent.shortLabel }}:</strong> {{ equivalent.serviceName }}
                    </div>
                  </div>
                </details>
                <button
                  type="button"
                  class="btn btn-secondary btn-xs"
                  @click="canvasBuilderRef?.addBlockToCanvas(item)"
                >
                  <span>Place block</span>
                </button>
              </details>
            </div>
          </details>

          <section class="sd-coach-section" data-testid="path-milestones-section">
            <div class="sd-coach-section-head">
              <strong>
                <GitBranch :size="13" />
                <span>Reference Path Milestones</span>
              </strong>
            </div>

            <div
              v-if="store.nextConnectionHint"
              class="sd-next-connection-box"
              data-testid="next-connection-hint-box"
            >
              <strong>
                {{ store.nextConnectionHint.source_label || store.nextConnectionHint.from_label }}
                &rarr;
                {{ store.nextConnectionHint.target_label || store.nextConnectionHint.to_label }}
              </strong>
              <div v-if="store.nextConnectionHint.suggested_label" class="sd-next-wire-proto">
                Label: <code>{{ store.nextConnectionHint.suggested_label }}</code>
              </div>
              <p>{{ store.nextConnectionHint.rationale }}</p>
            </div>

            <div v-if="normalizedExpectedPaths.length" class="sd-path-list">
              <div
                v-for="path in normalizedExpectedPaths"
                :key="path.id"
                class="sd-path-card"
                :class="{ satisfied: path.satisfied }"
              >
                <div class="sd-path-card-head">
                  <strong>{{ path.title }}</strong>
                  <div class="sd-path-head-actions">
                    <span class="sd-path-progress">
                      {{ path.completed }}/{{ path.total }}
                      <CheckCircle2 v-if="path.satisfied" :size="13" class="sd-path-ok" />
                    </span>
                    <button
                      type="button"
                      class="btn btn-secondary btn-xs sd-build-flow-btn"
                      data-testid="build-path-flow-btn"
                      title="Place & wire this reference flow on canvas (Undo available)"
                      @click="handleBuildPathFlow(path)"
                    >
                      <Wand2 :size="11" />
                      <span>Build Flow</span>
                    </button>
                  </div>
                </div>
                <p v-if="path.description" class="sd-path-desc">{{ path.description }}</p>
                <div class="sd-path-steps">
                  <span
                    v-for="step in path.steps"
                    :key="step.key"
                    class="sd-path-step-tag"
                    :class="{ placed: step.satisfied, ready: !step.satisfied && step.placedBoth }"
                    :title="step.sublabel"
                  >
                    {{ step.label }}
                  </span>
                </div>
              </div>
            </div>
            <p v-else class="sd-muted sd-coach-empty">
              Reveal the next step to inspect the reference flow checklist. (Alternative valid architectures are welcomed during Analyze.)
            </p>
          </section>

          <details class="sd-bank-more-actions">
            <summary>More reference actions</summary>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              data-testid="build-full-reference-btn"
              :disabled="store.loadingDiagramHint"
              @click="handleBuildFullReference"
            >
              <Wand2 :size="13" />
              <span>Build Full Reference</span>
            </button>
          </details>

          <details
            v-if="hasStudyNotes"
            class="sd-study-notes-box"
            data-testid="bank-study-notes"
          >
            <summary>
              <strong>Why This Fails at Scale &amp; Defence Traps</strong>
            </summary>
            <div v-if="activeStudyNotes.bottlenecks.length" class="sd-study-group">
              <span>Common Bottlenecks &amp; SPOFs</span>
              <ul>
                <li v-for="b in activeStudyNotes.bottlenecks" :key="b">{{ b }}</li>
              </ul>
            </div>
            <div v-if="activeStudyNotes.traps.length" class="sd-study-group">
              <span>Over-Engineering Traps</span>
              <ul>
                <li v-for="t in activeStudyNotes.traps" :key="t">{{ t }}</li>
              </ul>
            </div>
            <div v-if="activeStudyNotes.questions.length" class="sd-study-group">
              <span>Sample Defence Questions</span>
              <ul>
                <li v-for="q in activeStudyNotes.questions" :key="q">{{ q }}</li>
              </ul>
            </div>
          </details>
        </div>

        <!-- TAB 4: Topology Diagnostics & Stage 3 Critique Fix Checklist -->
        <div v-else class="sd-coach-tab-body sd-scrollable-tab" data-testid="coach-checks-panel">
          <div class="sd-coach-toolbar">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              data-testid="check-topology-btn"
              :disabled="store.loadingDiagramHint"
              @click="handleRequestHint('check_topology')"
            >
              <Loader2 v-if="store.loadingDiagramHint" :size="13" class="spin" />
              <Compass v-else :size="13" />
              <span>Run Topology Check</span>
            </button>
          </div>

          <section
            v-if="store.reviewFixChecklist.length"
            class="sd-coach-section sd-review-fixes"
            data-testid="review-fix-checklist"
          >
            <div class="sd-coach-section-head">
              <strong>Review Fixes ({{ pendingReviewFixCount }} open)</strong>
            </div>
            <div class="sd-fix-list">
              <label
                v-for="item in store.reviewFixChecklist"
                :key="item.id"
                class="sd-fix-item"
                :class="{ done: checkedFixIds[item.id] }"
              >
                <input
                  type="checkbox"
                  :checked="Boolean(checkedFixIds[item.id])"
                  @change="toggleFixChecklistItem(item.id)"
                />
                <div>
                  <span class="sd-fix-cat">{{ item.category }}</span>
                  <p>{{ item.text }}</p>
                </div>
              </label>
            </div>
          </section>

          <section
            v-if="verifiedConnections.length"
            class="sd-coach-section"
            data-testid="verified-connections-checklist"
          >
            <div class="sd-coach-section-head">
              <strong>Verified Connections ({{ verifiedConnections.length }})</strong>
            </div>
            <div class="sd-verified-wire-list">
              <div
                v-for="item in verifiedConnections"
                :key="item.key"
                class="sd-verified-wire-item"
              >
                <span class="sd-verified-wire-title">✓ {{ item.title }}</span>
                <span class="sd-verified-wire-detail">{{ item.detail }}</span>
              </div>
            </div>
          </section>

          <section
            v-if="liveWireWarnings.length"
            class="sd-coach-section"
            data-testid="live-wire-warnings"
          >
            <div class="sd-coach-section-head">
              <strong>Wire Warnings ({{ liveWireWarnings.length }})</strong>
            </div>
            <div class="sd-verified-wire-list">
              <div
                v-for="item in liveWireWarnings"
                :key="item.key"
                class="sd-verified-wire-item warn"
              >
                <span class="sd-verified-wire-title">⚠ {{ item.title }}</span>
                <span class="sd-verified-wire-detail">{{ item.detail }}</span>
              </div>
            </div>
          </section>

          <section
            v-if="liveCapabilityChecks.length"
            class="sd-coach-section"
            data-testid="capability-readiness-section"
          >
            <details :open="(flowSnapshot.nodes || []).length > 0 || Boolean(store.lastTopologyFeedback)">
              <summary class="sd-coach-section-head sd-cap-summary-toggle">
                <strong>
                  Capability Readiness ({{ metCapabilitiesCount }}/{{ liveCapabilityChecks.length }})
                </strong>
                <span v-if="!(flowSnapshot.nodes || []).length && !store.lastTopologyFeedback" class="sd-muted">
                  Activates as you build
                </span>
              </summary>
              <p
                v-if="!(flowSnapshot.nodes || []).length && !store.lastTopologyFeedback"
                class="sd-cap-empty-hint"
              >
                Place and wire components on the canvas (or click Run Topology Check) to light up live readiness.
              </p>
              <div class="sd-cap-list">
                <div
                  v-for="cap in liveCapabilityChecks"
                  :key="cap.id"
                  class="sd-cap-item"
                  :class="`cap-${cap.status}`"
                >
                  <div class="sd-cap-head">
                    <span class="sd-cap-status-icon">
                      {{ cap.status === 'met' ? '✓' : cap.status === 'partial' ? '◐' : '○' }}
                    </span>
                    <strong>{{ cap.title }}</strong>
                  </div>
                  <p class="sd-cap-goal">{{ cap.goal }}</p>
                  <div v-if="cap.satisfied_by" class="sd-cap-satisfied">
                    Covered by: <code>{{ cap.satisfied_by }}</code>
                  </div>
                </div>
              </div>
            </details>
          </section>

          <section
            v-if="store.lastTopologyFeedback"
            class="sd-coach-section"
            data-testid="topology-diagnostics-section"
          >
            <div class="sd-coach-section-head">
              <strong>
                <AlertTriangle :size="13" />
                <span>Topology Diagnostics</span>
              </strong>
            </div>
            <p class="sd-topo-summary">{{ store.lastTopologyFeedback.summary }}</p>
            <div
              v-if="store.lastTopologyFeedback.findings?.length"
              class="sd-finding-list"
            >
              <article
                v-for="(finding, idx) in store.lastTopologyFeedback.findings"
                :key="`${finding.title}-${idx}`"
                class="sd-finding-card"
                :class="`sev-${finding.severity || 'warning'}`"
              >
                <div class="sd-finding-head">
                  <span class="sd-finding-badge">{{ finding.category || finding.severity }}</span>
                  <strong>{{ finding.title }}</strong>
                </div>
                <p>{{ finding.detail }}</p>
              </article>
            </div>
            <p v-else class="sd-topo-clean">No structural or flow gaps detected.</p>
          </section>
          <p
            v-else-if="!store.reviewFixChecklist.length"
            class="sd-muted sd-coach-empty"
          >
            Click <strong>Run Topology Check</strong> to inspect wiring, bottlenecks, and valid alternatives before running Analyze.
          </p>
          <section
            v-if="liveBonusChecks.length"
            class="sd-coach-section"
            data-testid="bonus-capability-readiness"
          >
            <details open>
              <summary class="sd-coach-section-head sd-cap-summary-toggle">
                <strong>
                  Optional hardening bonuses ({{ earnedBonusPoints }}/{{ maximumBonusPoints }} points)
                </strong>
                <span class="sd-muted">Add only when justified</span>
              </summary>
              <div class="sd-cap-list">
                <div
                  v-for="check in liveBonusChecks"
                  :key="check.id"
                  class="sd-cap-item"
                  :class="`cap-${check.status}`"
                  data-testid="bonus-capability-item"
                >
                  <span class="sd-cap-status">
                    <CheckCircle2 v-if="check.status === 'met'" :size="14" />
                    <AlertTriangle v-else-if="check.status === 'partial'" :size="14" />
                    <span v-else class="sd-cap-pending-dot" />
                  </span>
                  <span class="sd-cap-text">
                    <strong>{{ check.title }} <small>+{{ check.points }}</small></strong>
                    <span>{{ check.goal }}</span>
                    <em v-if="check.satisfied_by">Wired: {{ check.satisfied_by }}</em>
                  </span>
                </div>
              </div>
            </details>
          </section>
        </div>
      </aside>
    </div>

    <div
      v-if="pendingCoachAction"
      class="sd-studio-modal-backdrop"
      data-testid="coach-action-preview-modal"
      @click.self="closeCoachActionPreview"
      @keydown.esc.stop.prevent="closeCoachActionPreview"
    >
      <section
        class="sd-studio-modal sd-coach-action-preview"
        role="dialog"
        aria-modal="true"
        aria-labelledby="coach-action-preview-title"
        aria-describedby="coach-action-preview-description"
      >
        <div class="sd-drawer-head">
          <h3 id="coach-action-preview-title">Review proposed canvas changes</h3>
        </div>
        <p id="coach-action-preview-description" class="sd-muted">
          {{ pendingCoachAction.description || 'Review the before-and-after changes before applying them.' }}
        </p>
        <div v-if="coachActionPreviewRows.length" class="sd-action-preview-list">
          <article
            v-for="(row, index) in coachActionPreviewRows"
            :key="`${row.target}-${row.name}-${index}`"
            class="sd-action-preview-row"
          >
            <strong>{{ row.target }} · {{ row.name }}</strong>
            <div class="sd-action-preview-columns">
              <div>
                <span>Before</span>
                <p>{{ row.before }}</p>
              </div>
              <div>
                <span>Proposed</span>
                <p>{{ row.after }}</p>
              </div>
            </div>
          </article>
        </div>
        <p v-else class="sd-muted" data-testid="coach-action-preview-empty">
          These changes no longer apply to the current canvas.
        </p>
        <div class="sd-modal-actions">
          <button
            type="button"
            class="btn btn-secondary"
            data-testid="cancel-coach-action-btn"
            @click="closeCoachActionPreview"
          >
            Cancel
          </button>
          <button
            ref="coachActionApplyButton"
            type="button"
            class="btn btn-primary"
            data-testid="confirm-coach-action-btn"
            :disabled="!coachActionPreviewRows.length"
            @click="confirmCoachAction"
          >
            Apply changes
          </button>
        </div>
      </section>

    </div>

    <!-- Clean Flow JSON Inspection Modal (inside More menu) -->
    <div
      v-if="showFlowJsonModal"
      class="sd-studio-modal-backdrop"
      data-testid="studio-flow-json-modal"
      @click.self="showFlowJsonModal = false"
    >
      <div class="sd-studio-modal sd-json-modal">
        <div class="sd-drawer-head">
          <h3>
            <Code2 :size="16" />
            <span>Canvas Flow JSON ({{ flowSnapshot.nodes?.length || 0 }} blocks, {{ flowSnapshot.edges?.length || 0 }} flows)</span>
          </h3>
          <button type="button" class="sd-icon-close" @click="showFlowJsonModal = false">
            <X :size="16" />
          </button>
        </div>

        <div class="sd-flow-preview-wrap" data-testid="flow-json-preview">
          <pre class="sd-flow-json-pre">{{ JSON.stringify(flowSnapshot, null, 2) }}</pre>
        </div>

        <div class="sd-modal-actions">
          <button type="button" class="btn btn-secondary" @click="showFlowJsonModal = false">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Clean External Image Upload Modal (Excalidraw / PNG / JPEG / WebP) -->
    <div
      v-if="showImageUploadModal"
      class="sd-studio-modal-backdrop"
      data-testid="studio-image-upload-modal"
      @click.self="showImageUploadModal = false"
    >
      <div class="sd-studio-modal">
        <div class="sd-drawer-head">
          <h3>
            <FileImage :size="16" />
            <span>Upload External Architecture Image</span>
          </h3>
          <button type="button" class="sd-icon-close" @click="showImageUploadModal = false">
            <X :size="16" />
          </button>
        </div>

        <p class="sd-muted">
          Prefer Excalidraw, Draw.io, or paper? Upload a PNG, JPEG, or WebP diagram (or press <strong>Ctrl+V</strong> to paste).
        </p>

        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          class="diagram-file-input"
          aria-label="Upload diagram image"
          @change="stageImageFile($event.target?.files?.[0])"
        />

        <img
          v-if="stagedPreviewUrl"
          :src="stagedPreviewUrl"
          alt="Staged diagram preview"
          class="sd-modal-preview-img"
        />

        <input
          v-model="imageNotesInput"
          type="text"
          class="form-input"
          placeholder="Optional revision notes..."
        />

        <div class="sd-modal-actions">
          <button type="button" class="btn btn-secondary" @click="showImageUploadModal = false">
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="!stagedDiagramFile || store.uploadingDiagram"
            @click="handleUploadImage"
          >
            <Loader2 v-if="store.uploadingDiagram" :size="14" class="spin" />
            <Upload v-else :size="14" />
            <span>Upload Image Revision</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sd-studio-page {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  background: var(--bg-app, #0b1120);
  color: var(--text-main, #f8fafc);
  overflow: hidden;
}

.sd-studio-header {
  min-height: 54px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-shrink: 0;
}

.sd-studio-header-left,
.sd-studio-header-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.sd-studio-title-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.sd-assistance-pill {
  padding: 2px 9px;
  border-radius: 999px;
  background: color-mix(in srgb, #10b981 16%, transparent);
  border: 1px solid color-mix(in srgb, #10b981 42%, transparent);
  color: #15803d;
  font-size: 0.72rem;
  font-weight: 700;
}

.sd-assistance-pill.coached {
  background: color-mix(in srgb, var(--accent, #3b82f6) 14%, transparent);
  border-color: color-mix(in srgb, var(--accent, #3b82f6) 40%, transparent);
  color: var(--accent, #2563eb);
}

.sd-more-menu-wrap {
  position: relative;
}

.sd-more-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 40;
  min-width: 225px;
  padding: 6px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.25);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sd-more-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--text-main, #f8fafc);
  font-size: 0.8rem;
  text-align: left;
  cursor: pointer;
}

.sd-more-item:hover {
  background: color-mix(in srgb, var(--accent, #3b82f6) 14%, transparent);
}

.sd-coach-count-pill {
  padding: 0 5px;
  border-radius: 999px;
  background: color-mix(in srgb, #f59e0b 25%, transparent);
  color: #fbbf24;
  font-size: 0.7rem;
  font-weight: 700;
}

.btn.is-coach-open {
  border-color: var(--accent, #3b82f6);
}

.sd-studio-title {
  margin: 0;
  font-size: 0.96rem;
  font-weight: 650;
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sd-rev-select {
  min-width: 145px;
}

.sd-studio-body {
  flex: 1;
  min-height: 0;
  display: flex;
  position: relative;
  overflow: hidden;
}

.sd-studio-sidebar {
  width: 355px;
  max-width: 92vw;
  border-left: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  flex-shrink: 0;
}

@media (max-width: 960px) {
  .sd-studio-body {
    flex-direction: column;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .sd-studio-canvas-shell {
    flex: 0 0 720px;
    width: 100%;
  }

  .sd-studio-sidebar {
    position: static;
    flex: 0 0 360px;
    width: 100%;
    max-width: none;
    border-left: 0;
    border-top: 1px solid var(--border-subtle);
  }
}

.sd-reqs-tab-body,
.sd-scrollable-tab {
  overflow-y: auto;
  padding-right: 2px;
}

.sd-json-modal {
  width: 620px;
  max-height: 82vh;
}

.sd-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sd-drawer-head h3 {
  margin: 0;
  font-size: 0.92rem;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.sd-icon-close {
  border: none;
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
  padding: 4px;
}

.sd-field-label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 0.8rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-drawer-checkbox {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.82rem;
  cursor: pointer;
}

.sd-flow-preview-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px solid var(--border-subtle, #334155);
  border-radius: 8px;
  padding: 10px;
}

.sd-flow-preview-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.sd-flow-json-pre {
  flex: 1;
  margin: 0;
  overflow: auto;
  font-size: 0.72rem;
  line-height: 1.35;
}

.sd-coach-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 3px;
  padding: 3px;
  border-radius: 9px;
  background: var(--bg-elevated, #0f172a);
  border: 1px solid var(--border-subtle, #334155);
  flex-shrink: 0;
}

.sd-coach-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 6px 8px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
}

.sd-coach-tab.active {
  background: var(--bg-surface, #1e293b);
  color: var(--text-main, #f8fafc);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}

.sd-tab-badge {
  padding: 0 5px;
  border-radius: 999px;
  background: color-mix(in srgb, #f59e0b 25%, transparent);
  color: #b45309;
  font-size: 0.68rem;
  font-weight: 700;
}

.sd-coach-tab-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.sd-coach-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sd-guided-actions {
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
}

.sd-guided-actions > .btn {
  min-width: 0;
  min-height: 40px;
  white-space: nowrap;
}

.sd-guided-actions > .btn:first-child {
  flex: 1 1 auto;
  justify-content: center;
}

.sd-guided-next-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background-color: var(--bg-elevated);
}

.sd-guided-next-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sd-guided-next-icon {
  flex: 0 0 auto;
  color: var(--primary);
}

.sd-guided-next-title {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sd-guided-next-title > span {
  color: var(--text-muted);
  font-size: 12px;
}

.sd-guided-next-title > strong {
  overflow: hidden;
  color: var(--text-main);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sd-guided-next-reason,
.sd-guided-component-reason {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.4;
}

.sd-guided-checklist > summary,
.sd-revealed-components > summary,
.sd-revealed-component > summary,
.sd-bank-more-actions > summary {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 12.5px;
}

.sd-guided-checklist > ul {
  margin: 0;
  padding: 0 0 0 18px;
  color: var(--text-secondary);
  font-size: 12.5px;
  line-height: 1.45;
}

.sd-guided-complete-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.sd-revealed-components {
  border-top: 1px solid var(--border-subtle);
}

.sd-revealed-components > summary {
  min-height: 44px;
}

.sd-revealed-components > summary > .sd-muted {
  margin-left: auto;
}

.sd-guided-count {
  min-width: 24px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.sd-revealed-component-list {
  display: flex;
  flex-direction: column;
}

.sd-revealed-component {
  padding: 0 8px;
  border-top: 1px solid var(--border-subtle);
}

.sd-revealed-component > summary {
  min-height: 44px;
}

.sd-revealed-component > summary > span:nth-of-type(1) {
  flex: 1;
}

.sd-guided-equivalents {
  margin: 4px 0 8px;
}

.sd-guided-equivalents .sd-cloud-eq-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sd-guided-equivalents .sd-cloud-eq-chip {
  padding: 4px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
}

.sd-revealed-component > .btn {
  margin: 0 0 8px;
}

.sd-bank-more-actions {
  padding-top: 4px;
  border-top: 1px solid var(--border-subtle);
}

.sd-bank-more-actions > .btn {
  margin-bottom: 8px;
}

.sd-coach-starter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sd-starter-chip {
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  color: var(--text-main, #f8fafc);
  font-size: 0.73rem;
  cursor: pointer;
}

.sd-starter-chip:hover {
  border-color: var(--accent, #3b82f6);
}

.sd-coach-thread {
  flex: 1;
  min-height: 180px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 2px;
}

.sd-coach-welcome {
  padding: 10px 12px;
  border-radius: 9px;
  border: 1px dashed var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  font-size: 0.78rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-coach-welcome strong {
  display: block;
  color: var(--text-main, #f8fafc);
  margin-bottom: 4px;
}

.sd-coach-welcome p {
  margin: 0;
  line-height: 1.4;
}

.sd-coach-msg {
  padding: 9px 11px;
  border-radius: 9px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sd-coach-msg.user {
  border-color: color-mix(in srgb, var(--accent, #3b82f6) 45%, var(--border-subtle, #334155));
  background: color-mix(in srgb, var(--accent, #3b82f6) 10%, var(--bg-elevated, #0f172a));
}

.sd-coach-msg-role {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary, #94a3b8);
}

.sd-coach-msg-text {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.45;
  color: var(--text-main, #f8fafc);
}

.sd-markdown-body :deep(p) {
  margin: 0 0 6px;
}

.sd-markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.sd-markdown-body :deep(ul),
.sd-markdown-body :deep(ol) {
  margin: 4px 0 6px;
  padding-left: 16px;
}

.sd-markdown-body :deep(li) {
  margin-bottom: 2px;
}

.sd-markdown-body :deep(code) {
  font-size: 0.74rem;
  padding: 1px 4px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--border-subtle, #334155) 45%, transparent);
}

.sd-coach-actions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sd-apply-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  border-radius: 7px;
  border: 1px solid color-mix(in srgb, var(--accent, #3b82f6) 50%, var(--border-subtle, #334155));
  background: color-mix(in srgb, var(--accent, #3b82f6) 14%, transparent);
  color: var(--text-main, #f8fafc);
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
}

.sd-apply-action-btn:hover {
  background: color-mix(in srgb, var(--accent, #3b82f6) 24%, transparent);
}

.sd-coach-composer {
  display: flex;
  gap: 6px;
  padding-top: 6px;
  border-top: 1px solid color-mix(in srgb, var(--border-subtle, #334155) 65%, transparent);
}

.sd-coach-input {
  flex: 1;
  font-size: 0.8rem;
}

.sd-next-wire-proto {
  margin-top: 3px;
  font-size: 0.74rem;
}

.sd-path-progress {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-path-step-tag.ready {
  border-color: color-mix(in srgb, var(--accent, #3b82f6) 55%, var(--border-subtle, #334155));
  color: var(--text-main, #f8fafc);
}

.sd-finding-card.sev-info {
  border-color: color-mix(in srgb, var(--accent, #3b82f6) 50%, var(--border-subtle, #334155));
}

.sd-finding-card.sev-info .sd-finding-badge {
  background: color-mix(in srgb, var(--accent, #3b82f6) 18%, transparent);
  color: var(--accent, #2563eb);
}

.sd-notes-ledger-box {
  padding: 10px;
  border-radius: 9px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: 0.76rem;
}

.sd-practice-progression {
  display: grid;
  gap: 7px;
  padding: 10px 11px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 0.78rem;
}

.sd-practice-progression > strong {
  color: var(--text-main);
}

.sd-practice-progression ol {
  display: grid;
  gap: 5px;
  margin: 0;
  padding-left: 18px;
}

.sd-practice-progression b {
  color: var(--text-main);
}

.sd-practice-progression > span {
  color: var(--text-muted);
}

.sd-ledger-ref-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-secondary, #94a3b8);
}

.sd-ledger-ref-group ul {
  margin: 3px 0 0;
  padding-left: 16px;
  line-height: 1.38;
}

.sd-ledger-scale-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 3px;
}

.sd-scale-chip {
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--bg-surface, #1e293b);
  border: 1px solid var(--border-subtle, #334155);
}

.sd-coach-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid color-mix(in srgb, var(--border-subtle, #334155) 65%, transparent);
}

.sd-coach-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.82rem;
}

.sd-coach-section-head strong {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sd-coach-empty {
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.4;
}

.sd-next-connection-box {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--accent, #3b82f6) 50%, var(--border-subtle, #334155));
  background: color-mix(in srgb, var(--accent, #3b82f6) 14%, transparent);
  font-size: 0.78rem;
}

.sd-next-connection-box p {
  margin: 4px 0 0;
  color: var(--text-secondary, #cbd5e1);
}

.sd-path-list,
.sd-finding-list,
.sd-fix-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.sd-path-card {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
}

.sd-path-card.satisfied {
  border-color: #10b981;
}

.sd-path-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8rem;
}

.sd-path-ok {
  color: #10b981;
}

.sd-path-desc {
  margin: 3px 0 6px;
  font-size: 0.73rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-path-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sd-path-step-tag {
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 0.68rem;
  border: 1px solid var(--border-subtle, #334155);
  color: var(--text-secondary, #94a3b8);
}

.sd-path-step-tag.placed {
  border-color: #10b981;
  color: #34d399;
}

.sd-topo-summary {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 600;
}

.sd-topo-clean {
  margin: 0;
  font-size: 0.78rem;
  color: #34d399;
}

.sd-finding-card {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  font-size: 0.77rem;
}

.sd-finding-card.sev-error {
  border-color: color-mix(in srgb, #ef4444 55%, var(--border-subtle, #334155));
}

.sd-finding-card.sev-warning {
  border-color: color-mix(in srgb, #f59e0b 55%, var(--border-subtle, #334155));
}

.sd-finding-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
}

.sd-finding-badge {
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.66rem;
  text-transform: uppercase;
  font-weight: 700;
  background: color-mix(in srgb, #f59e0b 20%, transparent);
  color: #fbbf24;
}

.sd-finding-card.sev-error .sd-finding-badge {
  background: color-mix(in srgb, #ef4444 20%, transparent);
  color: #f87171;
}

.sd-finding-card p {
  margin: 0;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.35;
}

.sd-fix-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 13px;
  cursor: pointer;
}

.sd-fix-item.done {
  opacity: 0.62;
  text-decoration: line-through;
}

.sd-fix-cat {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.sd-fix-item p {
  margin: 0;
  color: var(--text-main);
  line-height: 1.35;
}

.sd-studio-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(15, 23, 42, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.sd-studio-modal {
  width: 480px;
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sd-coach-action-preview {
  width: 620px;
  max-height: min(82dvh, 720px);
  overflow: hidden;
}

.sd-action-preview-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  min-height: 0;
  max-height: min(48dvh, 420px);
}

.sd-action-preview-row {
  padding: 10px 0;
  border-top: 1px solid var(--border-subtle);
}

.sd-action-preview-row > strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-main);
  font-size: 13px;
}

.sd-action-preview-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.sd-action-preview-columns > div {
  min-width: 0;
}

.sd-action-preview-columns span {
  color: var(--text-muted);
  font-size: 12.5px;
}

.sd-action-preview-columns p {
  margin: 3px 0 0;
  color: var(--text-main);
  overflow-wrap: anywhere;
}

.sd-modal-preview-img {
  max-height: 220px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
}

.sd-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.sd-verified-wire-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sd-verified-wire-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 7px 9px;
  border-radius: 7px;
  border: 1px solid rgba(34, 197, 94, 0.35);
  background: rgba(34, 197, 94, 0.08);
  font-size: 0.78rem;
  line-height: 1.35;
}

.sd-verified-wire-item.warn {
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(245, 158, 11, 0.1);
}

.sd-verified-wire-title {
  font-weight: 600;
  color: var(--text-main, #f8fafc);
}

.sd-verified-wire-detail {
  color: var(--text-secondary, #94a3b8);
  font-size: 0.74rem;
}

.sd-reference-framing {
  margin: 0;
  padding: 7px 10px;
  border-radius: 7px;
  background: color-mix(in srgb, var(--accent, #3b82f6) 10%, var(--bg-elevated, #0f172a));
  border: 1px solid color-mix(in srgb, var(--accent, #3b82f6) 28%, var(--border-subtle, #334155));
  font-size: 0.74rem;
  line-height: 1.38;
  color: var(--text-main, #f8fafc);
}

.sd-path-head-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sd-build-flow-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  font-size: 0.7rem;
}

.sd-cap-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sd-cap-item {
  padding: 7px 9px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  font-size: 0.76rem;
  line-height: 1.35;
}

.sd-cap-item.cap-met {
  border-color: rgba(34, 197, 94, 0.45);
  background: rgba(34, 197, 94, 0.08);
}

.sd-cap-item.cap-partial {
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(245, 158, 11, 0.08);
}

.sd-cap-head {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-main, #f8fafc);
  margin-bottom: 2px;
}

.sd-cap-status-icon {
  font-weight: 700;
}

.sd-cap-item.cap-met .sd-cap-status-icon {
  color: #16a34a;
}

.sd-cap-item.cap-partial .sd-cap-status-icon {
  color: #d97706;
}

.sd-cap-goal {
  margin: 0;
  color: var(--text-secondary, #94a3b8);
  font-size: 0.73rem;
}

.sd-cap-satisfied {
  margin-top: 4px;
  font-size: 0.72rem;
  color: var(--text-main, #f8fafc);
}

.sd-finding-card.sev-info {
  border-color: rgba(59, 130, 246, 0.42);
  background: rgba(59, 130, 246, 0.08);
}

.sd-finding-card.sev-info .sd-finding-badge {
  background: rgba(59, 130, 246, 0.18);
  color: #2563eb;
}

.sd-scale-math-card {
  padding: 6px 9px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--accent, #3b82f6) 28%, var(--border-subtle, #334155));
  background: color-mix(in srgb, var(--accent, #3b82f6) 5%, var(--bg-elevated, #0f172a));
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sd-scale-math-head {
  font-size: 0.72rem;
  color: var(--text-main, #f8fafc);
  cursor: pointer;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 6px;
  list-style: none;
}

.sd-scale-math-head::-webkit-details-marker {
  display: none;
}

.sd-scale-math-head::before {
  content: '▸';
  font-size: 0.68rem;
  color: var(--text-secondary, #94a3b8);
  transition: transform 0.15s ease;
}

.sd-scale-math-card[open] .sd-scale-math-head::before {
  content: '▾';
}

.sd-scale-summary-preview {
  color: var(--text-secondary, #94a3b8);
  font-weight: 400;
  font-size: 0.68rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.sd-scale-math-card[open] .sd-scale-summary-preview {
  display: none;
}

.sd-scale-kv-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 4px 0 0;
  padding: 0;
}

.sd-scale-kv-row {
  display: grid;
  grid-template-columns: minmax(76px, auto) 1fr;
  align-items: baseline;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
}

.sd-scale-kv-key {
  margin: 0;
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-main, #f8fafc);
  white-space: nowrap;
}

.sd-scale-kv-val {
  margin: 0;
  font-size: 0.7rem;
  line-height: 1.38;
  color: var(--text-secondary, #94a3b8);
}

.sd-more-checkbox {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 10px;
  border-top: 1px solid var(--border-subtle, #334155);
  font-size: 0.76rem;
  color: var(--text-main, #f8fafc);
  cursor: pointer;
}

.sd-cap-summary-toggle {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.sd-cap-empty-hint {
  margin: 5px 0 6px;
  font-size: 0.73rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-external-coach-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.sd-external-coach-toggle.active {
  border-color: var(--accent, #3b82f6);
  background: color-mix(in srgb, var(--accent, #3b82f6) 16%, transparent);
}

.sd-external-coach-box {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sd-external-coach-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.75rem;
  color: var(--text-main, #f8fafc);
}

.sd-external-coach-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sd-external-preview {
  font-family: ui-monospace, monospace;
  font-size: 0.71rem;
  line-height: 1.35;
}

.sd-external-import-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.sd-study-notes-box {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-elevated, #0f172a);
  font-size: 0.75rem;
  color: var(--text-main, #f8fafc);
}

.sd-study-notes-box summary {
  cursor: pointer;
}

.sd-study-group {
  margin-top: 6px;
}

.sd-study-group span {
  display: block;
  font-weight: 700;
  font-size: 0.7rem;
  text-transform: uppercase;
  color: var(--text-secondary, #94a3b8);
  margin-bottom: 2px;
}

.sd-study-group ul {
  margin: 0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sd-studio-page {
  height: 100dvh;
  width: 100%;
  background: var(--bg-app);
  color: var(--text-main);
  font-size: 14px;
}

.sd-studio-header {
  min-height: 52px;
  padding: 6px 12px;
  flex-wrap: nowrap;
  gap: 12px;
  border-color: var(--border-subtle);
  background: var(--bg-surface);
}

.sd-studio-header-left,
.sd-studio-header-right {
  flex-wrap: nowrap;
  gap: 8px;
}

.sd-studio-header-left {
  min-width: 0;
  flex: 1;
}

.sd-studio-header-right {
  flex-shrink: 0;
}

.sd-studio-back-btn,
.sd-studio-header-right > .btn {
  min-width: 40px;
  min-height: 40px;
}

.sd-studio-back-btn {
  width: 40px;
  padding: 0;
  justify-content: center;
}

.sd-studio-title-wrap {
  min-width: 0;
  flex-wrap: nowrap;
  gap: 10px;
}

.sd-studio-title {
  max-width: min(45vw, 520px);
  font-size: 18px;
}

.sd-assistance-pill {
  flex-shrink: 0;
  padding: 4px 8px;
  background: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--text-primary);
  font-size: 12.5px;
}

.sd-assistance-pill.coached {
  background: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--text-primary);
}

.sd-more-menu-wrap {
  flex: 0 0 auto;
}

.sd-more-menu-wrap > .btn {
  width: 40px;
  min-height: 40px;
  justify-content: center;
  padding: 0;
}

.sd-more-dropdown {
  max-height: min(70dvh, 560px);
  overflow: auto;
  border-color: var(--border-color);
  background: var(--bg-elevated);
  box-shadow: var(--shadow-md);
}

.sd-more-item {
  min-height: 40px;
  color: var(--text-main);
  font-size: 13px;
}

.sd-more-item:hover {
  background: var(--primary-subtle);
}

.sd-more-revision {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  color: var(--text-secondary);
  font-size: 12.5px;
}

.sd-more-revision .form-select {
  min-height: 40px;
  font-size: 13px;
}

.sd-coach-count-pill {
  background: var(--primary-subtle);
  color: var(--text-primary);
}

.sd-studio-body {
  min-height: 0;
  overflow: hidden;
}

.sd-studio-sidebar {
  width: 344px;
  padding: 8px 12px;
  gap: 8px;
  border-color: var(--border-subtle);
  background: var(--bg-card);
}

.sd-drawer-head {
  min-height: 32px;
}

.sd-drawer-head h3 {
  font-size: 13px;
}

.sd-icon-close {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.sd-coach-tabs {
  gap: 3px;
  padding: 3px;
  background: var(--bg-elevated);
  border-color: var(--border-subtle);
}

.sd-coach-tab {
  min-width: 0;
  min-height: 44px;
  padding: 4px 6px;
  font-size: 13px;
}

.sd-coach-tab.active {
  background: var(--bg-surface);
  color: var(--text-main);
  box-shadow: none;
}

.sd-coach-tab-body {
  gap: 8px;
  font-size: 14px;
}

.sd-reqs-tab-body {
  overflow: hidden;
}

.sd-scale-math-card {
  flex: 0 0 auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
}

.sd-scale-math-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 4px 10px;
  cursor: pointer;
  list-style: none;
}

.sd-scale-math-head::-webkit-details-marker,
.sd-scale-math-head::marker {
  display: none;
  content: '';
}

.sd-scale-math-head strong {
  flex: 0 0 auto;
}

.sd-scale-ratio-chip {
  margin-left: auto;
  padding: 3px 7px;
  border-radius: var(--radius-full);
  background: var(--primary-subtle);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.sd-scale-summary-preview {
  display: none;
}

.sd-scale-kv-list {
  padding: 0 10px 8px;
}

.sd-notes-ledger-box {
  flex: 0 1 auto;
  max-height: 38%;
  overflow: auto;
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
}

.sd-notes-ledger-box > strong {
  display: block;
  margin-bottom: 6px;
}

.sd-ledger-ref-group {
  padding: 6px 0;
  border-top: 1px solid var(--border-subtle);
}

.sd-ledger-ref-label {
  color: var(--text-secondary);
  font-size: 12.5px;
  font-weight: 600;
}

.sd-field-label {
  flex: 1;
  min-height: 0;
  font-size: 12.5px;
}

.sd-field-label textarea {
  flex: 1;
  min-height: 80px;
  resize: none;
  font-size: 14px;
}

.sd-coach-thread {
  min-height: 0;
}

.sd-studio-page :is(button, summary, input, textarea, select):focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 2px;
}

@media (max-width: 820px) {
  .sd-studio-header {
    flex-wrap: wrap;
  }

  .sd-studio-header-left,
  .sd-studio-header-right {
    flex-wrap: wrap;
  }

  .sd-studio-sidebar {
    width: 100%;
  }
}
</style>
