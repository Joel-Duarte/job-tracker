<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  Download,
  Edit3,
  FileCode,
  FileImage,
  Globe,
  HelpCircle,
  Layers,
  Lightbulb,
  Loader2,
  Lock,
  MessageSquare,
  Plus,
  RotateCcw,
  Save,
  Send,
  ShieldAlert,
  Sparkles,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
import { SystemDesignAPI } from '../api/endpoints'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useSystemDesignStore } from '../stores/systemDesignStore'
import { useUIStore } from '../stores/uiStore'

defineProps({
  embedded: { type: Boolean, default: false },
})

const store = useSystemDesignStore()
const appStore = useApplicationsStore()
const uiStore = useUIStore()

const STAGES = [
  { id: 'REQUIREMENTS', label: '1. Requirements', shortLabel: 'Requirements' },
  { id: 'DESIGN', label: '2. Diagram', shortLabel: 'Diagram' },
  { id: 'REVIEW', label: '3. Review', shortLabel: 'Review' },
  { id: 'DEFENCE', label: '4. Defence', shortLabel: 'Defence' },
  { id: 'COMPLETED', label: '5. Evaluation', shortLabel: 'Evaluation' },
]

const activeStageTab = ref('REQUIREMENTS')
const evalSubTab = ref('scorecard')

// Custom & AI Challenge modal state
const showCreateChallengeModal = ref(false)
const editingChallengeId = ref(null)
const editingChallengeIsBuiltin = ref(false)
const createModalTab = ref('generate')
const generateForm = ref({
  topic: '',
  applicationId: '',
  difficulty: 'MEDIUM',
  useWebSearch: true,
})
const manualForm = ref({
  title: '',
  category: 'DISTRIBUTED_SYSTEMS',
  difficulty: 'MEDIUM',
  promptSummary: '',
  initialPrompt: '',
  tagsText: '',
  expectedComponentsText: '',
  scaleNotes: '',
})

// Stage 1: Requirements discovery & ledger form state
const reqMessageInput = ref('')
const ledgerForm = ref({
  functionalText: '',
  nonFunctionalText: '',
  scaleText: '',
  outOfScopeText: '',
  notes: '',
  isLocked: false,
})

// Stage 2 & 3: Diagram upload & grounded review state
const stagedDiagramFile = ref(null)
const stagedPreviewUrl = ref('')
const diagramNotesInput = ref('')
const isDraggingFile = ref(false)
const selectedDiagramVersion = ref(null)
const useWebSearchReview = ref(false)

// Stage 4: Defence state
const defenceMessageInput = ref('')
const useWebSearchDefence = ref(false)

// Stage 4 & 5: Frontier Model Packet export/import state
const importEvaluationText = ref('')
const frontierCopied = ref(false)

const activeSession = computed(() => store.activeSession)

const activeStageIndex = computed(() => {
  const idx = STAGES.findIndex((s) => s.id === activeStageTab.value)
  return idx >= 0 ? idx : 0
})

const selectedRevision = computed(() => {
  const revisions = store.activeDiagrams
  if (!revisions.length) return null
  if (selectedDiagramVersion.value !== null) {
    const match = revisions.find(
      (r) => Number(r.version) === Number(selectedDiagramVersion.value)
    )
    if (match) return match
  }
  return revisions[revisions.length - 1]
})

const selectedReview = computed(() => {
  const reviews = store.activeReviews
  if (!reviews.length) return null
  if (selectedDiagramVersion.value !== null) {
    const match = reviews.find(
      (r) => Number(r.diagram_version) === Number(selectedDiagramVersion.value)
    )
    if (match) return match
  }
  return reviews[reviews.length - 1]
})

function syncLedgerFormFromSession(session) {
  const ledger = session?.requirements_ledger || {}
  ledgerForm.value.functionalText = (ledger.functional_requirements || []).join('\n')
  ledgerForm.value.nonFunctionalText = (ledger.non_functional_requirements || []).join('\n')
  ledgerForm.value.scaleText = Object.entries(ledger.scale_estimates || {})
    .map(([k, v]) => `${k}: ${v}`)
    .join('\n')
  ledgerForm.value.outOfScopeText = (ledger.out_of_scope || []).join('\n')
  ledgerForm.value.notes = ledger.notes || ''
  ledgerForm.value.isLocked = Boolean(ledger.is_locked)
}

function parseLines(text) {
  return String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function parseScaleLines(text) {
  const result = {}
  for (const line of parseLines(text)) {
    const sepIdx = line.indexOf(':')
    if (sepIdx > 0) {
      const k = line.slice(0, sepIdx).trim()
      const v = line.slice(sepIdx + 1).trim()
      if (k && v) result[k] = v
    } else {
      result[line] = 'Specified'
    }
  }
  return result
}

watch(
  () => activeSession.value,
  (session, prevSession) => {
    if (!session) return
    syncLedgerFormFromSession(session)

    const diagrams = session.diagrams_metadata || []
    if (diagrams.length) {
      const latestVersion = diagrams[diagrams.length - 1].version
      if (!prevSession || prevSession.id !== session.id || diagrams.length !== (prevSession.diagrams_metadata || []).length) {
        selectedDiagramVersion.value = latestVersion
      }
    } else {
      selectedDiagramVersion.value = null
    }

    if (!prevSession || prevSession.id !== session.id) {
      evalSubTab.value = 'scorecard'
    }

    if (!prevSession || prevSession.id !== session.id || prevSession.stage !== session.stage) {
      activeStageTab.value = session.stage || 'REQUIREMENTS'
    }
  },
  { immediate: true, deep: false }
)

watch(
  () => activeSession.value?.requirements_ledger,
  () => {
    if (activeSession.value) {
      syncLedgerFormFromSession(activeSession.value)
    }
  },
  { deep: true }
)

function getRevisionImageUrl(rev) {
  if (!rev) return ''
  if (rev.data_url) return rev.data_url
  if (!activeSession.value) return ''
  return SystemDesignAPI.getDiagramImageUrl(activeSession.value.id, rev.version)
}

function formatDifficultyLabel(diff) {
  const val = String(diff || 'MEDIUM').toUpperCase()
  return val.charAt(0) + val.slice(1).toLowerCase()
}

function formatCategoryLabel(cat) {
  return String(cat || 'DISTRIBUTED_SYSTEMS')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (ch) => ch.toUpperCase())
}

function formatReadinessLabel(rating) {
  return String(rating || 'DEVELOPING').replace(/_/g, ' ')
}

function getReadinessBadgeClass(rating) {
  if (rating === 'STRONG_HIRE' || rating === 'INTERVIEW_READY') return 'badge-offer'
  if (rating === 'DEVELOPING') return 'badge-interview'
  return 'badge-rejected'
}

function getDifficultyClass(difficulty) {
  const normalized = String(difficulty || 'MEDIUM').toUpperCase()
  if (normalized === 'EASY') return 'diff-easy'
  if (normalized === 'HARD') return 'diff-hard'
  return 'diff-medium'
}

function getRunningSessionForChallenge(challengeId) {
  return (store.sessions || []).find(
    (s) =>
      (s.challenge_id === challengeId || s.challenge?.id === challengeId) &&
      s.status !== 'COMPLETED' &&
      s.stage !== 'COMPLETED'
  )
}

async function handleOpenOrStartChallenge(challenge) {
  const existing = getRunningSessionForChallenge(challenge.id)
  if (existing) {
    await store.loadSession(existing.id)
    return
  }
  await handleStartChallenge(challenge)
}

const assistedTurnCount = computed(() => {
  if (!activeSession.value) return 0
  const req = activeSession.value.requirements_transcript || []
  const def = activeSession.value.defence_transcript || []
  return [...req, ...def].filter((t) => t.role === 'candidate' && t.assisted).length
})

function isStageUnlocked(stageId) {
  if (!activeSession.value) return false
  if (stageId === 'REQUIREMENTS') return true
  if (stageId === 'DESIGN') {
    return (
      Boolean(activeSession.value.requirements_ledger?.is_locked) ||
      store.activeDiagrams.length > 0
    )
  }
  if (stageId === 'REVIEW' || stageId === 'DEFENCE') {
    return store.activeReviews.length > 0
  }
  if (stageId === 'COMPLETED') {
    return (
      (activeSession.value.defence_transcript || []).some((t) => t.role === 'candidate') ||
      Boolean(store.activeFinalEvaluation) ||
      activeSession.value.stage === 'COMPLETED'
    )
  }
  return false
}

function selectStage(stageId) {
  if (!isStageUnlocked(stageId)) return
  activeStageTab.value = stageId
}

async function handleStartChallenge(challenge) {
  try {
    await store.startSession(challenge.id, 'ADAPTIVE')
    activeStageTab.value = 'REQUIREMENTS'
    evalSubTab.value = 'scorecard'
    uiStore.showToast(`Started "${challenge.title}"`, 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to start challenge session', 'error')
  }
}

async function openCreateChallengeModal() {
  editingChallengeId.value = null
  editingChallengeIsBuiltin.value = false
  createModalTab.value = 'generate'
  manualForm.value = {
    title: '',
    category: 'DISTRIBUTED_SYSTEMS',
    difficulty: 'MEDIUM',
    promptSummary: '',
    initialPrompt: '',
    tagsText: '',
    expectedComponentsText: '',
    scaleNotes: '',
  }
  showCreateChallengeModal.value = true
  if (!(appStore.applications || []).length) {
    try {
      await appStore.fetchApplications()
    } catch {
      // Optional app linking works even if applications list is unavailable
    }
  }
}

function openEditChallengeModal(challenge) {
  editingChallengeId.value = challenge.id
  editingChallengeIsBuiltin.value = Boolean(challenge.is_builtin)
  createModalTab.value = 'manual'
  manualForm.value = {
    title: challenge.title || '',
    category: challenge.category || 'DISTRIBUTED_SYSTEMS',
    difficulty: challenge.difficulty || 'MEDIUM',
    promptSummary: challenge.prompt_summary || '',
    initialPrompt: challenge.initial_prompt || '',
    tagsText: (challenge.tags || []).join(', '),
    expectedComponentsText: (challenge.expected_components || []).join('\n'),
    scaleNotes: challenge.scale_notes || '',
  }
  showCreateChallengeModal.value = true
}

async function handleCreateManualChallenge() {
  if (
    !manualForm.value.title.trim() ||
    !manualForm.value.promptSummary.trim() ||
    !manualForm.value.initialPrompt.trim()
  ) {
    uiStore.showToast('Title, summary, and initial interview prompt are required.', 'error')
    return
  }
  const parsedTags = String(manualForm.value.tagsText || '')
    .split(/[,\n]/)
    .map((t) => t.trim())
    .filter(Boolean)
  const includeCustomRubricFields = !editingChallengeId.value || !editingChallengeIsBuiltin.value
  const payload = {
    title: manualForm.value.title.trim(),
    category: manualForm.value.category,
    difficulty: manualForm.value.difficulty,
    prompt_summary: manualForm.value.promptSummary.trim(),
    initial_prompt: manualForm.value.initialPrompt.trim(),
    tags: parsedTags,
    ...(includeCustomRubricFields
      ? {
          expected_components: parseLines(manualForm.value.expectedComponentsText),
          scale_notes: manualForm.value.scaleNotes.trim(),
        }
      : {}),
  }
  try {
    if (editingChallengeId.value) {
      await store.updateChallenge(editingChallengeId.value, payload)
      uiStore.showToast('Challenge updated!', 'success')
    } else {
      await store.createChallenge(payload)
      uiStore.showToast('Custom challenge created!', 'success')
    }
    showCreateChallengeModal.value = false
    editingChallengeId.value = null
    editingChallengeIsBuiltin.value = false
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save challenge', 'error')
  }
}

async function handleResetDefaultChallenges() {
  try {
    await store.resetDefaultChallenges()
    uiStore.showToast('Restored all 8 default System Design challenges.', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to reset default challenges', 'error')
  }
}

async function handleGenerateChallenge() {
  if (!generateForm.value.topic.trim() && !generateForm.value.applicationId) {
    uiStore.showToast('Enter a topic or pick a tracked application to tailor from.', 'error')
    return
  }
  try {
    await store.generateChallenge({
      topic: generateForm.value.topic.trim(),
      application_id: generateForm.value.applicationId
        ? Number(generateForm.value.applicationId)
        : null,
      difficulty: generateForm.value.difficulty,
      use_web_search: Boolean(generateForm.value.useWebSearch),
    })
    showCreateChallengeModal.value = false
    generateForm.value.topic = ''
    uiStore.showToast('Custom challenge generated!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to generate challenge', 'error')
  }
}

async function handleDeleteChallenge(challenge) {
  try {
    await store.deleteChallenge(challenge.id)
    uiStore.showToast(`Removed "${challenge.title}"`, 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to delete challenge', 'error')
  }
}

async function handleSendRequirementsMessage(requestHint = false) {
  const isHint = Boolean(requestHint)
  const msg =
    reqMessageInput.value.trim() ||
    (isHint
      ? 'Can you give me a coaching hint on what requirements or scale assumptions I should ask about next?'
      : '')
  if (!msg || store.sendingRequirements) return
  const draft = reqMessageInput.value
  reqMessageInput.value = ''
  try {
    await store.sendRequirementsMessage(msg, isHint)
  } catch (err) {
    reqMessageInput.value = draft
    uiStore.showToast(err.message || 'Failed to send clarifying question', 'error')
  }
}

async function handleExtractLedger() {
  try {
    await store.extractRequirementsLedger()
    uiStore.showToast('Extracted discussed requirements into the ledger', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to extract requirements ledger', 'error')
  }
}

async function handleSaveLedger(lock = false) {
  const payload = {
    functional_requirements: parseLines(ledgerForm.value.functionalText),
    non_functional_requirements: parseLines(ledgerForm.value.nonFunctionalText),
    scale_estimates: parseScaleLines(ledgerForm.value.scaleText),
    out_of_scope: parseLines(ledgerForm.value.outOfScopeText),
    notes: ledgerForm.value.notes.trim(),
    is_locked: Boolean(lock),
  }
  try {
    await store.updateRequirementsLedger(payload)
    if (lock) {
      activeStageTab.value = 'DESIGN'
      uiStore.showToast('Requirements locked! Ready for architecture diagram upload.', 'success')
    } else {
      uiStore.showToast('Requirements draft saved.', 'success')
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to update requirements ledger', 'error')
  }
}

function stageFileForUpload(file) {
  if (!file) return
  const validTypes = ['image/png', 'image/jpeg', 'image/webp']
  if (file.type && !validTypes.includes(file.type)) {
    uiStore.showToast('Unsupported image type. Please upload PNG, JPEG, or WebP.', 'error')
    return
  }
  stagedDiagramFile.value = file
  if (stagedPreviewUrl.value) {
    URL.revokeObjectURL(stagedPreviewUrl.value)
  }
  stagedPreviewUrl.value = URL.createObjectURL(file)
}

function handleFileInputChange(event) {
  const file = event.target?.files?.[0]
  if (file) {
    stageFileForUpload(file)
  }
}

function handleDrop(event) {
  isDraggingFile.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    stageFileForUpload(file)
  }
}

function handlePaste(event) {
  if (!activeSession.value || activeStageTab.value !== 'DESIGN') return
  const items = event.clipboardData?.items || []
  for (const item of items) {
    if (item.type && item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        stageFileForUpload(file)
        uiStore.showToast('Diagram image pasted from clipboard!', 'info')
        break
      }
    }
  }
}

async function handleUploadDiagram() {
  if (!stagedDiagramFile.value || store.uploadingDiagram) return
  try {
    await store.uploadDiagram(stagedDiagramFile.value, diagramNotesInput.value)
    stagedDiagramFile.value = null
    if (stagedPreviewUrl.value) {
      URL.revokeObjectURL(stagedPreviewUrl.value)
      stagedPreviewUrl.value = ''
    }
    diagramNotesInput.value = ''
    uiStore.showToast('Architecture diagram uploaded!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to upload diagram', 'error')
  }
}

async function handleAnalyzeArchitecture(version = null) {
  if (store.reviewingDiagram) return
  try {
    const targetVersion = version ?? selectedRevision.value?.version ?? null
    await store.reviewDiagram(targetVersion, useWebSearchReview.value)
    activeStageTab.value = 'REVIEW'
    uiStore.showToast('Architecture review completed!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to analyze architecture', 'error')
  }
}

async function handleSendDefenceMessage(requestHint = false) {
  const isHint = Boolean(requestHint)
  const msg =
    defenceMessageInput.value.trim() ||
    (isHint
      ? 'Could you give me a coaching hint on which trade-off or failure scenario I should focus on defending?'
      : '')
  if (!msg || store.sendingDefence) return
  const draft = defenceMessageInput.value
  defenceMessageInput.value = ''
  try {
    await store.sendDefenceMessage(msg, {
      requestHint: isHint,
      useWebSearch: useWebSearchDefence.value,
    })
  } catch (err) {
    defenceMessageInput.value = draft
    uiStore.showToast(err.message || 'Failed to submit defence response', 'error')
  }
}

async function handleEvaluateSession() {
  if (store.evaluatingSession) return
  try {
    await store.evaluateSession()
    activeStageTab.value = 'COMPLETED'
    evalSubTab.value = 'scorecard'
    uiStore.showToast('Final evaluation scorecard ready!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to generate final evaluation', 'error')
  }
}

async function handleCancelActiveTask() {
  try {
    await store.cancelActiveTask()
    uiStore.showToast('Background task cancelled.', 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to cancel background task', 'error')
  }
}

async function handleRetryActiveTask() {
  const wasEval = store.activeSession?.active_task_type === 'SYSTEM_DESIGN_EVALUATION'
  try {
    await store.retryActiveTask()
    if (wasEval && store.activeFinalEvaluation) {
      activeStageTab.value = 'COMPLETED'
      evalSubTab.value = 'scorecard'
    } else if (!wasEval && store.activeReviews.length) {
      activeStageTab.value = 'REVIEW'
    }
    uiStore.showToast('Background task completed!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Retry failed', 'error')
  }
}

async function handlePrepareFrontierPacket() {
  try {
    await store.fetchFrontierPacket()
    frontierCopied.value = false
    uiStore.showToast('Frontier Evaluation Packet prepared!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to generate frontier packet', 'error')
  }
}

async function handleCopyFrontierPacket() {
  const text = store.frontierPacket?.markdown_packet
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    frontierCopied.value = true
    uiStore.showToast('Copied packet to clipboard! Paste into Claude, ChatGPT, or Gemini with your diagram.', 'success')
  } catch {
    uiStore.showToast('Clipboard write blocked; use Download .md Packet instead.', 'info')
  }
}

function handleDownloadFrontierPacket() {
  const packet = store.frontierPacket
  if (!packet?.markdown_packet) return
  const blob = new Blob([packet.markdown_packet], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = packet.filename || 'system-design-frontier-packet.md'
  link.click()
  URL.revokeObjectURL(url)
}

async function handleImportFrontierEvaluation() {
  const raw = importEvaluationText.value.trim()
  if (!raw || store.importingEvaluation) return
  try {
    await store.importEvaluation(raw)
    importEvaluationText.value = ''
    activeStageTab.value = 'COMPLETED'
    evalSubTab.value = 'scorecard'
    uiStore.showToast('Frontier model evaluation scorecard imported!', 'success')
  } catch (err) {
    uiStore.showToast(
      err.message || 'Could not parse JSON scorecard. Make sure a valid JSON evaluation block is included.',
      'error'
    )
  }
}

onMounted(async () => {
  window.addEventListener('paste', handlePaste)
  await Promise.allSettled([store.fetchChallenges(), store.fetchSessions()])
})

onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
  if (stagedPreviewUrl.value) {
    URL.revokeObjectURL(stagedPreviewUrl.value)
  }
})
</script>

<template>
  <div class="page-container system-design-view">
    <!-- ================================================================
         LOBBY VIEW: Curated & Custom Challenges Grid
         ================================================================ -->
    <template v-if="!activeSession">
      <section class="sd-section">
        <div class="sd-section-header">
          <div class="sd-header-title-group">
            <h2>Interview Challenge Scenarios</h2>
            <span class="sd-muted">{{ store.challenges.length }} scenarios available</span>
          </div>
          <div class="sd-header-actions">
            <button
              type="button"
              class="btn btn-secondary"
              data-testid="reset-default-challenges-btn"
              :disabled="store.resettingChallenges"
              @click="handleResetDefaultChallenges"
            >
              <Loader2 v-if="store.resettingChallenges" :size="15" class="spin" />
              <RotateCcw v-else :size="15" />
              <span>Reset Default Challenges</span>
            </button>
            <button
              type="button"
              class="btn btn-primary"
              data-testid="open-new-challenge-modal-btn"
              @click="openCreateChallengeModal"
            >
              <Plus :size="15" />
              <span>New Challenge</span>
            </button>
          </div>
        </div>

        <div v-if="store.loadingChallenges" class="sd-loading-box">
          <Loader2 :size="20" class="spin" />
          <span>Loading system design challenges...</span>
        </div>

        <div v-else class="sd-challenges-grid">
          <article
            v-for="challenge in store.challenges"
            :key="challenge.id"
            class="sd-card challenge-card"
            :data-testid="`challenge-card-${challenge.slug}`"
          >
            <div class="challenge-card-top">
              <span class="challenge-category-label">{{ formatCategoryLabel(challenge.category) }}</span>
              <div class="challenge-badges-right">
                <span v-if="!challenge.is_builtin" class="sd-tag">Custom</span>
                <span class="sd-difficulty-pill" :class="getDifficultyClass(challenge.difficulty)">
                  {{ formatDifficultyLabel(challenge.difficulty) }}
                </span>
              </div>
            </div>
            <h3 class="challenge-title">{{ challenge.title }}</h3>
            <p class="challenge-summary">{{ challenge.prompt_summary }}</p>
            <div v-if="challenge.tags?.length" class="challenge-tags">
              <span v-for="tag in challenge.tags" :key="tag" class="sd-tag">{{ tag }}</span>
            </div>
            <div class="challenge-actions">
              <button
                type="button"
                class="btn btn-primary challenge-start-btn"
                data-testid="start-challenge-btn"
                :disabled="store.startingSession || store.loadingSession"
                @click="handleOpenOrStartChallenge(challenge)"
              >
                <Loader2 v-if="store.startingSession || store.loadingSession" :size="14" class="spin" />
                <ArrowRight v-else-if="getRunningSessionForChallenge(challenge.id)" :size="14" />
                <Sparkles v-else :size="14" />
                <span>{{ getRunningSessionForChallenge(challenge.id) ? 'Resume Session' : 'Start Challenge' }}</span>
              </button>
              <button
                v-if="getRunningSessionForChallenge(challenge.id)"
                type="button"
                class="btn btn-ghost challenge-action-icon-btn"
                title="Start a fresh session"
                aria-label="Start a fresh session"
                data-testid="new-session-btn"
                :disabled="store.startingSession || store.loadingSession"
                @click="handleStartChallenge(challenge)"
              >
                <Plus :size="14" />
              </button>
              <div class="challenge-manage-btns">
                <button
                  type="button"
                  class="btn btn-ghost challenge-action-icon-btn"
                  title="Edit challenge"
                  aria-label="Edit challenge"
                  data-testid="edit-challenge-btn"
                  @click="openEditChallengeModal(challenge)"
                >
                  <Edit3 :size="14" />
                </button>
                <button
                  type="button"
                  class="btn btn-ghost challenge-action-icon-btn sd-icon-danger-btn"
                  title="Delete challenge"
                  aria-label="Delete challenge"
                  data-testid="delete-challenge-btn"
                  @click="handleDeleteChallenge(challenge)"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- Custom / AI-Generated / Edit Challenge Modal -->
      <div
        v-if="showCreateChallengeModal"
        class="sd-modal-overlay"
        data-testid="new-challenge-modal"
        @click.self="showCreateChallengeModal = false"
      >
        <div class="sd-card sd-modal-dialog">
          <div class="sd-card-header">
            <h3>
              <Edit3 v-if="editingChallengeId" :size="16" class="sd-primary-icon" />
              <Sparkles v-else :size="16" class="sd-primary-icon" />
              <span>{{ editingChallengeId ? 'Edit Challenge Scenario' : 'Create System Design Challenge' }}</span>
            </h3>
            <button
              type="button"
              class="btn btn-ghost"
              @click="showCreateChallengeModal = false"
              aria-label="Close modal"
            >
              <X :size="16" />
            </button>
          </div>

          <div v-if="!editingChallengeId" class="mode-toggle-compact">
            <button
              type="button"
              class="mode-pill"
              :class="{ active: createModalTab === 'generate' }"
              data-testid="tab-generate-challenge"
              @click="createModalTab = 'generate'"
            >
              <Sparkles :size="13" />
              <span>AI Generate</span>
            </button>
            <button
              type="button"
              class="mode-pill"
              :class="{ active: createModalTab === 'manual' }"
              data-testid="tab-manual-challenge"
              @click="createModalTab = 'manual'"
            >
              <Plus :size="13" />
              <span>Manual Entry</span>
            </button>
          </div>

          <form
            v-if="createModalTab === 'generate' && !editingChallengeId"
            class="sd-form-stack"
            @submit.prevent="handleGenerateChallenge"
          >
            <label class="sd-field">
              <span>Topic / Scenario Description</span>
              <input
                v-model="generateForm.topic"
                type="text"
                class="form-input"
                data-testid="generate-topic-input"
                placeholder="e.g., Design a multi-tenant real-time fraud scoring pipeline"
              />
            </label>

            <label class="sd-field">
              <span>Optional: Tailor to Tracked Job Application</span>
              <select v-model="generateForm.applicationId" class="form-input">
                <option value="">None (Use topic only)</option>
                <option
                  v-for="app in (appStore.applications || [])"
                  :key="app.id"
                  :value="String(app.id)"
                >
                  {{ app.company?.name || 'Company' }} — {{ app.position || 'Role' }}
                </option>
              </select>
            </label>

            <label class="sd-field">
              <span>Target Difficulty</span>
              <select v-model="generateForm.difficulty" class="form-input">
                <option value="EASY">Easy</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard</option>
              </select>
            </label>

            <label class="sd-checkbox-row">
              <input v-model="generateForm.useWebSearch" type="checkbox" />
              <Globe :size="14" class="sd-primary-icon" />
              <span>Ground scenario with Web Search references</span>
            </label>

            <div class="sd-modal-actions">
              <button
                type="button"
                class="btn btn-secondary"
                @click="showCreateChallengeModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                data-testid="submit-generate-challenge-btn"
                :disabled="store.generatingChallenge"
              >
                <Loader2 v-if="store.generatingChallenge" :size="14" class="spin" />
                <Sparkles v-else :size="14" />
                <span>Generate Challenge</span>
              </button>
            </div>
          </form>

          <form
            v-else
            class="sd-form-stack"
            @submit.prevent="handleCreateManualChallenge"
          >
            <label class="sd-field">
              <span>Challenge Title</span>
              <input
                v-model="manualForm.title"
                type="text"
                class="form-input"
                data-testid="manual-title-input"
                placeholder="e.g., Design a Webhook Delivery Engine"
              />
            </label>

            <div class="sd-two-col-compact">
              <label class="sd-field">
                <span>Category</span>
                <select v-model="manualForm.category" class="form-input">
                  <option value="DISTRIBUTED_SYSTEMS">Distributed Systems</option>
                  <option value="DATA_INFRASTRUCTURE">Data Infrastructure</option>
                  <option value="REALTIME_COMMUNICATION">Realtime Communication</option>
                  <option value="MEDIA_STREAMING">Media Streaming</option>
                  <option value="REALTIME_MESSAGING">Realtime Messaging</option>
                  <option value="GEOSPATIAL">Geospatial</option>
                  <option value="INFRASTRUCTURE">Infrastructure</option>
                  <option value="STORAGE_SYSTEMS">Storage Systems</option>
                  <option value="AI_PLATFORM">AI Platform</option>
                </select>
              </label>

              <label class="sd-field">
                <span>Difficulty</span>
                <select v-model="manualForm.difficulty" class="form-input">
                  <option value="EASY">Easy</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HARD">Hard</option>
                </select>
              </label>
            </div>

            <label class="sd-field">
              <span>Card Summary</span>
              <input
                v-model="manualForm.promptSummary"
                type="text"
                class="form-input"
                data-testid="manual-summary-input"
                placeholder="1-2 sentence scenario overview shown on the challenge card"
              />
            </label>

            <label class="sd-field">
              <span>Opening Interviewer Prompt</span>
              <textarea
                v-model="manualForm.initialPrompt"
                class="form-textarea"
                rows="3"
                data-testid="manual-prompt-input"
                placeholder="Intentionally broad prompt without giving away scale targets..."
              />
            </label>

            <label class="sd-field">
              <span>Tags (comma-separated)</span>
              <input
                v-model="manualForm.tagsText"
                type="text"
                class="form-input"
                data-testid="manual-tags-input"
                placeholder="e.g., webhooks, queues, retries"
              />
            </label>

            <template v-if="!editingChallengeId || !editingChallengeIsBuiltin">
              <label class="sd-field">
                <span>Expected Core Components (one per line, optional hidden rubric)</span>
                <textarea
                  v-model="manualForm.expectedComponentsText"
                  class="form-textarea"
                  rows="2"
                  data-testid="manual-expected-components-input"
                  placeholder="API Gateway&#10;Retry Queue&#10;Dead-Letter Store"
                />
              </label>

              <label class="sd-field">
                <span>Hidden Scale Targets (revealed only when candidate asks)</span>
                <input
                  v-model="manualForm.scaleNotes"
                  type="text"
                  class="form-input"
                  data-testid="manual-scale-notes-input"
                  placeholder="e.g., 5,000 events/sec peak, 10k tenants, 99.95% delivery SLA"
                />
              </label>
            </template>

            <div class="sd-modal-actions">
              <button
                type="button"
                class="btn btn-secondary"
                @click="showCreateChallengeModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                data-testid="submit-manual-challenge-btn"
                :disabled="store.creatingChallenge || store.updatingChallenge"
              >
                <Loader2 v-if="store.creatingChallenge || store.updatingChallenge" :size="14" class="spin" />
                <Save v-else-if="editingChallengeId" :size="14" />
                <Plus v-else :size="14" />
                <span>{{ editingChallengeId ? 'Save Changes' : 'Create Challenge' }}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </template>

    <!-- ================================================================
         ACTIVE SESSION WORKSPACE
         ================================================================ -->
    <template v-else>
      <!-- Compact Session Header & Strict 5-Stage Stepper -->
      <div class="sd-card sd-workspace-header">
        <div class="workspace-compact-top">
          <button
            type="button"
            class="btn btn-ghost sd-back-icon-btn"
            data-testid="back-to-challenges-btn"
            title="Back to Challenge Scenarios"
            @click="store.clearActiveSession()"
          >
            <ArrowLeft :size="16" />
            <span>Challenges</span>
          </button>

          <div class="workspace-title-block">
            <h1>{{ activeSession.challenge?.title || 'System Design Session' }}</h1>
            <p class="sd-muted">{{ activeSession.challenge?.initial_prompt }}</p>
          </div>
        </div>

        <!-- 5-Stage Progress Stepper (Strictly Gated) -->
        <nav class="stage-stepper" aria-label="Session stages">
          <button
            v-for="(st, idx) in STAGES"
            :key="st.id"
            type="button"
            class="stage-step-btn"
            :data-testid="`stage-step-${st.id}`"
            :disabled="!isStageUnlocked(st.id)"
            :class="{
              active: activeStageTab === st.id,
              current: activeSession.stage === st.id,
              completed: idx < activeStageIndex,
              locked: !isStageUnlocked(st.id),
            }"
            @click="selectStage(st.id)"
          >
            <Lock v-if="!isStageUnlocked(st.id)" :size="12" />
            <span>{{ st.label }}</span>
          </button>
        </nav>

        <!-- Background Queue Task Banner (F-04) -->
        <div
          v-if="['QUEUED', 'RUNNING', 'PROCESSING', 'FAILED', 'CANCELLED'].includes(activeSession.active_task_status)"
          class="sd-task-banner"
          :class="{
            'is-failed': ['FAILED', 'CANCELLED'].includes(activeSession.active_task_status),
          }"
          data-testid="sd-active-task-banner"
        >
          <div class="sd-task-banner-info">
            <Loader2
              v-if="['QUEUED', 'RUNNING', 'PROCESSING'].includes(activeSession.active_task_status)"
              :size="15"
              class="spin"
            />
            <AlertTriangle v-else :size="15" />
            <div>
              <strong>
                {{
                  activeSession.active_task_type === 'SYSTEM_DESIGN_EVALUATION'
                    ? 'Final Evaluation Task'
                    : 'Architecture Review Task'
                }}
                • {{ activeSession.active_task_status }}
                <span v-if="activeSession.active_task_stage">({{ activeSession.active_task_stage }})</span>
              </strong>
              <p v-if="activeSession.active_task_error" class="sd-task-banner-error">
                {{ activeSession.active_task_error }}
              </p>
            </div>
          </div>
          <div class="sd-task-banner-actions">
            <button
              v-if="['QUEUED', 'RUNNING', 'PROCESSING'].includes(activeSession.active_task_status)"
              type="button"
              class="btn btn-secondary btn-xs"
              data-testid="sd-cancel-task-btn"
              @click="handleCancelActiveTask"
            >
              <X :size="12" />
              <span>Cancel Task</span>
            </button>
            <button
              v-else
              type="button"
              class="btn btn-primary btn-xs"
              data-testid="sd-retry-task-btn"
              @click="handleRetryActiveTask"
            >
              <RotateCcw :size="12" />
              <span>Retry Task</span>
            </button>
          </div>
        </div>
      </div>

      <!-- ==============================================================
           STAGE 1: REQUIREMENTS DISCOVERY & EDITABLE LEDGER
           ============================================================== -->
      <div v-if="activeStageTab === 'REQUIREMENTS'" class="sd-two-col">
        <!-- Interview Chat -->
        <section class="sd-card sd-chat-panel">
          <div class="sd-card-header">
            <h3>
              <MessageSquare :size="16" />
              <span>Requirements Clarification Interview</span>
            </h3>
            <span class="sd-tag">Adaptive</span>
          </div>

          <div class="sd-transcript-list">
            <div
              v-for="turn in (activeSession.requirements_transcript || [])"
              :key="`req-${turn.turn_index}`"
              class="sd-turn-bubble"
              :class="turn.role === 'candidate' ? 'turn-candidate' : 'turn-interviewer'"
            >
              <div class="turn-meta">
                <Bot v-if="turn.role === 'interviewer'" :size="13" />
                <span>{{ turn.role === 'interviewer' ? 'AI Interviewer' : 'You' }}</span>
                <span v-if="turn.assisted" class="sd-tag sd-hint-tag">Coaching Hint</span>
              </div>
              <p class="turn-content">{{ turn.content }}</p>
            </div>
          </div>

          <form class="sd-chat-input-bar" @submit.prevent="handleSendRequirementsMessage(false)">
            <textarea
              v-model="reqMessageInput"
              class="sd-chat-input"
              rows="2"
              data-testid="req-chat-input"
              placeholder="Ask a clarifying question (e.g., What is our expected read/write ratio and p99 latency?)..."
              @keydown.enter.exact.prevent="handleSendRequirementsMessage(false)"
            />
            <div class="sd-input-actions">
              <button
                type="button"
                class="btn-input-icon"
                data-testid="req-hint-btn"
                :disabled="store.sendingRequirements"
                @click="handleSendRequirementsMessage(true)"
                title="Ask for a Coaching Hint"
              >
                <Lightbulb :size="16" />
              </button>
              <button
                type="submit"
                class="btn btn-primary btn-input-send"
                data-testid="req-send-btn"
                :disabled="store.sendingRequirements || !reqMessageInput.trim()"
                title="Send question"
              >
                <Loader2 v-if="store.sendingRequirements" :size="15" class="spin" />
                <Send v-else :size="15" />
              </button>
            </div>
          </form>
        </section>

        <!-- Editable Requirements Ledger -->
        <section class="sd-card sd-ledger-panel">
          <div class="sd-card-header">
            <h3>
              <ClipboardCheck :size="16" />
              <span>Requirements Ledger</span>
            </h3>
            <button
              type="button"
              class="btn btn-secondary"
              :disabled="store.extractingLedger"
              @click="handleExtractLedger"
            >
              <Loader2 v-if="store.extractingLedger" :size="14" class="spin" />
              <Sparkles v-else :size="14" />
              <span>Auto-Extract from Chat</span>
            </button>
          </div>

          <div class="sd-form-stack">
            <label class="sd-field">
              <span>Functional Requirements (one per line)</span>
              <textarea
                v-model="ledgerForm.functionalText"
                class="form-textarea"
                rows="3"
                placeholder="e.g., Create short links&#10;Redirect short code with 302"
              />
            </label>

            <label class="sd-field">
              <span>Non-Functional Requirements & SLAs (one per line)</span>
              <textarea
                v-model="ledgerForm.nonFunctionalText"
                class="form-textarea"
                rows="3"
                placeholder="e.g., 99.95% availability&#10;p99 redirect latency < 50ms"
              />
            </label>

            <label class="sd-field">
              <span>Scale & Capacity Estimates (`metric: value` per line)</span>
              <textarea
                v-model="ledgerForm.scaleText"
                class="form-textarea"
                rows="2"
                placeholder="e.g., read_write_ratio: 100:1&#10;mau: 50M users"
              />
            </label>

            <label class="sd-field">
              <span>Out of Scope (one per line)</span>
              <textarea
                v-model="ledgerForm.outOfScopeText"
                class="form-textarea"
                rows="2"
                placeholder="e.g., Custom billing dashboards"
              />
            </label>

            <label class="sd-field">
              <span>Notes & Key APIs</span>
              <textarea
                v-model="ledgerForm.notes"
                class="form-textarea"
                rows="2"
                placeholder="Any agreed assumptions or constraints..."
              />
            </label>
          </div>

          <div class="sd-ledger-actions">
            <button
              type="button"
              class="btn btn-secondary"
              :disabled="store.savingLedger"
              @click="handleSaveLedger(false)"
            >
              <Save :size="14" />
              <span>Save Draft</span>
            </button>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="store.savingLedger"
              @click="handleSaveLedger(true)"
            >
              <Loader2 v-if="store.savingLedger" :size="14" class="spin" />
              <Lock v-else :size="14" />
              <span>Lock Requirements & Proceed to Diagram</span>
            </button>
          </div>
        </section>
      </div>

      <!-- ==============================================================
           STAGE 2: EXTERNAL DIAGRAM UPLOAD (v1..vN)
           ============================================================== -->
      <div v-else-if="activeStageTab === 'DESIGN'" class="sd-two-col">
        <!-- Upload & Paste Box -->
        <section class="sd-card">
          <div class="sd-card-header">
            <h3>
              <Upload :size="16" />
              <span>Upload Architecture Diagram</span>
            </h3>
            <span class="sd-muted">PNG, JPEG, or WebP (max 10 MB)</span>
          </div>

          <p class="sd-muted sd-helper-copy">
            Design your architecture in Excalidraw, Draw.io, Miro, or on paper, then upload the exported image or press <strong>Ctrl+V</strong> to paste it directly from your clipboard.
          </p>

          <div
            class="sd-dropzone"
            :class="{ dragging: isDraggingFile }"
            @dragover.prevent="isDraggingFile = true"
            @dragleave.prevent="isDraggingFile = false"
            @drop.prevent="handleDrop"
          >
            <FileImage :size="28" class="sd-primary-icon" />
            <p>Drop a diagram image here, paste with Ctrl+V, or choose a file:</p>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              class="diagram-file-input"
              aria-label="Upload diagram image"
              @change="handleFileInputChange"
            />
          </div>

          <div v-if="stagedPreviewUrl" class="sd-staged-preview">
            <span class="sd-muted">Ready to upload: {{ stagedDiagramFile?.name || 'pasted-diagram.png' }}</span>
            <img :src="stagedPreviewUrl" alt="Staged architecture diagram preview" class="sd-preview-img" />
          </div>

          <div class="sd-form-stack">
            <label class="sd-field">
              <span>Revision Notes (optional)</span>
              <input
                v-model="diagramNotesInput"
                type="text"
                class="form-input"
                placeholder="e.g., Added Redis read cache and standby PostgreSQL replica"
              />
            </label>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!stagedDiagramFile || store.uploadingDiagram"
              @click="handleUploadDiagram"
            >
              <Loader2 v-if="store.uploadingDiagram" :size="14" class="spin" />
              <Upload v-else :size="14" />
              <span>Upload Diagram Revision</span>
            </button>
          </div>
        </section>

        <!-- Uploaded Revisions Preview & Analyze Action -->
        <section class="sd-card">
          <div class="sd-card-header">
            <h3>
              <Layers :size="16" />
              <span>Submitted Diagram Revisions</span>
            </h3>
            <span class="sd-muted">{{ store.activeDiagrams.length }} version(s)</span>
          </div>

          <div v-if="!store.activeDiagrams.length" class="sd-empty-box">
            <FileImage :size="24" />
            <p>No diagram uploaded yet. Upload v1 on the left to submit it for multimodal architecture review.</p>
          </div>

          <template v-else>
            <div class="sd-revision-tabs">
              <button
                v-for="rev in store.activeDiagrams"
                :key="rev.version"
                type="button"
                class="mode-pill"
                :class="{ active: selectedRevision?.version === rev.version }"
                @click="selectedDiagramVersion = rev.version"
              >
                <span>v{{ rev.version }}</span>
              </button>
            </div>

            <div v-if="selectedRevision" class="sd-revision-viewer">
              <img
                :src="getRevisionImageUrl(selectedRevision)"
                :alt="`Diagram revision v${selectedRevision.version}`"
                class="sd-preview-img"
              />
              <p v-if="selectedRevision.notes" class="sd-muted">
                <strong>Notes:</strong> {{ selectedRevision.notes }}
              </p>

              <div
                v-if="selectedReview && Number(selectedReview.diagram_version) === Number(selectedRevision.version)"
                class="sd-diagram-review-summary"
                data-testid="diagram-review-summary"
              >
                <div class="sd-review-summary-head">
                  <span class="sd-review-status-pill">
                    <CheckCircle2 :size="13" class="sd-success-icon" />
                    <strong>Reviewed (v{{ selectedReview.diagram_version }})</strong>
                  </span>
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    @click="selectStage('REVIEW')"
                  >
                    <span>Open Full Critique</span>
                    <ArrowRight :size="13" />
                  </button>
                </div>
                <p class="sd-review-summary-copy">{{ selectedReview.overall_impression }}</p>
                <div class="challenge-tags">
                  <span class="sd-tag">{{ (selectedReview.strengths || []).length }} strengths</span>
                  <span class="sd-tag">{{ (selectedReview.bottlenecks_and_spofs || []).length }} bottlenecks</span>
                  <span class="sd-tag">{{ (selectedReview.missing_components || []).length }} missing</span>
                </div>
              </div>
              <p v-else class="sd-muted">
                Not yet reviewed — click Analyze Architecture below to generate multimodal critique.
              </p>

              <label class="sd-checkbox-row">
                <input
                  v-model="useWebSearchReview"
                  type="checkbox"
                  data-testid="review-web-search-checkbox"
                />
                <Globe :size="14" class="sd-primary-icon" />
                <span>Ground critique with Web Search (benchmarks &amp; failure modes)</span>
              </label>

              <button
                type="button"
                class="btn btn-primary w-full"
                :disabled="store.reviewingDiagram"
                @click="handleAnalyzeArchitecture(selectedRevision.version)"
              >
                <Loader2 v-if="store.reviewingDiagram" :size="14" class="spin" />
                <Sparkles v-else :size="14" />
                <span>Analyze Architecture (v{{ selectedRevision.version }})</span>
              </button>
            </div>
          </template>
        </section>
      </div>

      <!-- ==============================================================
           STAGE 3: ARCHITECTURE REVIEW FINDINGS
           ============================================================== -->
      <div v-else-if="activeStageTab === 'REVIEW'" class="sd-review-stage">
        <div v-if="!selectedReview" class="sd-card sd-empty-box">
          <Sparkles :size="24" />
          <p>No architecture review has been generated yet.</p>
          <label v-if="store.activeDiagrams.length" class="sd-checkbox-row">
            <input v-model="useWebSearchReview" type="checkbox" />
            <Globe :size="14" class="sd-primary-icon" />
            <span>Ground critique with Web Search</span>
          </label>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="!store.activeDiagrams.length || store.reviewingDiagram"
            @click="store.activeDiagrams.length ? handleAnalyzeArchitecture() : (activeStageTab = 'DESIGN')"
          >
            <Loader2 v-if="store.reviewingDiagram" :size="14" class="spin" />
            <span>{{ store.activeDiagrams.length ? 'Analyze Latest Diagram' : 'Go Upload a Diagram' }}</span>
          </button>
        </div>

        <template v-else>
          <div class="sd-card review-banner">
            <div class="review-banner-text">
              <div class="session-row-title-row">
                <span class="badge badge-assessment">Revision v{{ selectedReview.diagram_version }}</span>
                <h3>Architecture Critique</h3>
              </div>
              <p>{{ selectedReview.overall_impression }}</p>
            </div>
            <div class="review-banner-actions">
              <button
                type="button"
                class="btn btn-secondary"
                @click="selectStage('DESIGN')"
              >
                <Upload :size="14" />
                <span>Upload Revised Diagram</span>
              </button>
              <button
                type="button"
                class="btn btn-primary"
                @click="selectStage('DEFENCE')"
              >
                <span>Proceed to Architecture Defence</span>
                <ArrowRight :size="14" />
              </button>
            </div>
          </div>

          <!-- Visual Clarifications Needed (Explicitly Separated From Design Flaws) -->
          <div
            v-if="selectedReview.visual_clarifications_needed?.length"
            class="sd-card sd-clarification-card"
          >
            <div class="sd-card-header">
              <h3>
                <HelpCircle :size="16" />
                <span>Visual Clarifications Needed</span>
              </h3>
              <span class="badge badge-interview">Clarify, Not Penalized</span>
            </div>
            <ul class="sd-bullet-list">
              <li v-for="item in selectedReview.visual_clarifications_needed" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div class="sd-review-grid">
            <article class="sd-card">
              <div class="sd-card-header">
                <h3>
                  <CheckCircle2 :size="16" class="sd-success-icon" />
                  <span>Strengths</span>
                </h3>
              </div>
              <ul class="sd-bullet-list">
                <li v-for="item in selectedReview.strengths" :key="item">{{ item }}</li>
                <li v-if="!selectedReview.strengths?.length" class="sd-muted">None highlighted yet.</li>
              </ul>
            </article>

            <article class="sd-card">
              <div class="sd-card-header">
                <h3>
                  <AlertTriangle :size="16" class="sd-warning-icon" />
                  <span>Bottlenecks & Single Points of Failure</span>
                </h3>
              </div>
              <ul class="sd-bullet-list">
                <li v-for="item in selectedReview.bottlenecks_and_spofs" :key="item">{{ item }}</li>
                <li v-if="!selectedReview.bottlenecks_and_spofs?.length" class="sd-muted">None detected.</li>
              </ul>
            </article>

            <article class="sd-card">
              <div class="sd-card-header">
                <h3>
                  <ShieldAlert :size="16" />
                  <span>Missing Components & Requirement Gaps</span>
                </h3>
              </div>
              <ul class="sd-bullet-list">
                <li v-for="item in selectedReview.missing_components" :key="`mc-${item}`">
                  <strong>Missing:</strong> {{ item }}
                </li>
                <li v-for="item in selectedReview.requirement_gaps" :key="`rg-${item}`">
                  <strong>Requirement gap:</strong> {{ item }}
                </li>
                <li
                  v-if="!selectedReview.missing_components?.length && !selectedReview.requirement_gaps?.length"
                  class="sd-muted"
                >
                  All locked requirements appear represented.
                </li>
              </ul>
            </article>

            <article class="sd-card">
              <div class="sd-card-header">
                <h3>
                  <Layers :size="16" />
                  <span>Interpreted Components & Complexity Check</span>
                </h3>
              </div>
              <p class="sd-muted sd-sub-heading">Observed components:</p>
              <div class="challenge-tags">
                <span v-for="comp in selectedReview.interpreted_components" :key="comp" class="sd-tag">
                  {{ comp }}
                </span>
              </div>
              <p v-if="selectedReview.unnecessary_complexity?.length" class="sd-muted sd-sub-heading">
                Unnecessary complexity:
              </p>
              <ul v-if="selectedReview.unnecessary_complexity?.length" class="sd-bullet-list">
                <li v-for="item in selectedReview.unnecessary_complexity" :key="item">{{ item }}</li>
              </ul>
            </article>
          </div>
        </template>
      </div>

      <!-- ==============================================================
           STAGE 4: INTERACTIVE ARCHITECTURE DEFENCE
           ============================================================== -->
      <div v-else-if="activeStageTab === 'DEFENCE'" class="sd-two-col">
        <!-- Defence Conversation -->
        <section class="sd-card sd-chat-panel">
          <div class="sd-card-header">
            <h3>
              <ShieldAlert :size="16" />
              <span>Architecture Defence</span>
            </h3>
            <span class="sd-tag">Adaptive</span>
          </div>

          <div class="sd-transcript-list">
            <div
              v-for="turn in (activeSession.defence_transcript || [])"
              :key="`def-${turn.turn_index}`"
              class="sd-turn-bubble"
              :class="turn.role === 'candidate' ? 'turn-candidate' : 'turn-interviewer'"
            >
              <div class="turn-meta">
                <Bot v-if="turn.role === 'interviewer'" :size="13" />
                <span>{{ turn.role === 'interviewer' ? 'AI Interviewer' : 'Your Defence' }}</span>
                <span v-if="turn.assisted" class="sd-tag sd-hint-tag">Coaching Hint</span>
              </div>
              <p class="turn-content">{{ turn.content }}</p>
            </div>
            <div v-if="!(activeSession.defence_transcript || []).length" class="sd-empty-box">
              <p>Run an architecture review on your diagram to seed tailored defence questions, or submit your explanation below.</p>
            </div>
          </div>

          <form class="sd-chat-input-bar" @submit.prevent="handleSendDefenceMessage(false)">
            <textarea
              v-model="defenceMessageInput"
              class="sd-chat-input"
              rows="2"
              data-testid="defence-chat-input"
              placeholder="Justify your architectural trade-offs and failure handling..."
              @keydown.enter.exact.prevent="handleSendDefenceMessage(false)"
            />
            <div class="sd-input-actions">
              <button
                type="button"
                class="btn-input-icon"
                :class="{ active: useWebSearchDefence }"
                data-testid="defence-web-search-toggle"
                :aria-pressed="useWebSearchDefence"
                title="Ground next interviewer probe with Web Search"
                @click="useWebSearchDefence = !useWebSearchDefence"
              >
                <Globe :size="16" />
              </button>
              <button
                type="button"
                class="btn-input-icon"
                data-testid="defence-hint-btn"
                :disabled="store.sendingDefence"
                title="Ask for a Coaching Hint"
                @click="handleSendDefenceMessage(true)"
              >
                <Lightbulb :size="16" />
              </button>
              <button
                type="submit"
                class="btn btn-primary btn-input-send"
                data-testid="defence-send-btn"
                :disabled="store.sendingDefence || !defenceMessageInput.trim()"
                title="Send defence response"
              >
                <Loader2 v-if="store.sendingDefence" :size="15" class="spin" />
                <Send v-else :size="15" />
              </button>
            </div>
          </form>
        </section>

        <!-- Reference Sidebar + Complete Action -->
        <aside class="sd-card sd-defence-sidebar">
          <div class="sd-sidebar-top">
            <div class="sd-card-header">
              <h3>
                <FileImage :size="16" />
                <span>Active Design Reference</span>
              </h3>
              <span v-if="selectedRevision" class="badge badge-assessment">v{{ selectedRevision.version }}</span>
            </div>

            <img
              v-if="selectedRevision"
              :src="getRevisionImageUrl(selectedRevision)"
              :alt="`Diagram revision v${selectedRevision.version}`"
              class="sd-preview-img"
            />

            <div v-if="selectedReview?.bottlenecks_and_spofs?.length" class="sd-sidebar-notes">
              <h4>Open Probing Topics</h4>
              <ul class="sd-bullet-list">
                <li v-for="item in selectedReview.bottlenecks_and_spofs" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>

          <div class="sd-sidebar-actions">
            <button
              type="button"
              class="btn btn-secondary w-full"
              @click="selectStage('DESIGN')"
            >
              <RotateCcw :size="14" />
              <span>Upload Revised Diagram (v{{ (store.activeDiagrams.length || 0) + 1 }})</span>
            </button>
            <button
              type="button"
              class="btn btn-primary w-full"
              data-testid="evaluate-session-btn"
              :disabled="store.evaluatingSession"
              @click="handleEvaluateSession"
            >
              <Loader2 v-if="store.evaluatingSession" :size="14" class="spin" />
              <ClipboardCheck v-else :size="14" />
              <span>Complete &amp; Evaluate with Local AI</span>
            </button>
          </div>
        </aside>
      </div>

      <!-- ==============================================================
           STAGE 5: EVIDENCE-BASED FINAL EVALUATION REPORT
           ============================================================== -->
      <div v-else class="sd-evaluation-stage">
        <div class="sd-eval-subnav">
          <button
            type="button"
            class="mode-pill"
            :class="{ active: evalSubTab === 'scorecard' }"
            data-testid="eval-scorecard-tab-btn"
            @click="evalSubTab = 'scorecard'"
          >
            <ClipboardCheck :size="14" />
            <span>Local AI Scorecard</span>
          </button>
          <button
            type="button"
            class="mode-pill"
            :class="{ active: evalSubTab === 'frontier' }"
            data-testid="toggle-frontier-panel-btn"
            @click="evalSubTab = evalSubTab === 'frontier' ? 'scorecard' : 'frontier'"
          >
            <FileCode :size="14" />
            <span>Frontier Second Opinion (Claude / GPT / Gemini)</span>
          </button>
        </div>

        <template v-if="evalSubTab === 'scorecard'">
          <div v-if="!store.activeFinalEvaluation" class="sd-card sd-empty-box">
            <ClipboardCheck :size="26" />
            <p>Ready to score your session across all 12 system design rubric dimensions using concrete evidence.</p>
            <button
              type="button"
              class="btn btn-primary"
              data-testid="generate-local-eval-btn"
              :disabled="store.evaluatingSession"
              @click="handleEvaluateSession"
            >
              <Loader2 v-if="store.evaluatingSession" :size="14" class="spin" />
              <Sparkles v-else :size="14" />
              <span>Generate Final Evaluation (Local AI)</span>
            </button>
          </div>

          <template v-else>
            <!-- Hero Scorecard -->
            <section class="sd-card sd-eval-hero">
              <div class="eval-score-box">
                <span class="eval-score-value">{{ Math.round(store.activeFinalEvaluation.overall_score) }}</span>
                <span class="eval-score-max">/ 100</span>
              </div>
              <div class="eval-summary-block">
                <div class="session-row-title-row">
                  <span
                    class="badge"
                    :class="getReadinessBadgeClass(store.activeFinalEvaluation.readiness_rating)"
                  >
                    {{ formatReadinessLabel(store.activeFinalEvaluation.readiness_rating) }}
                  </span>
                  <h2>Final Interview Scorecard</h2>
                  <span v-if="assistedTurnCount > 0" class="sd-tag">
                    {{ assistedTurnCount }} coaching hint(s) used
                  </span>
                </div>
                <p>{{ store.activeFinalEvaluation.executive_summary }}</p>
              </div>
            </section>

            <!-- Key Takeaways -->
            <section class="sd-eval-highlights">
              <article class="sd-card">
                <h3>Top Strengths</h3>
                <ul class="sd-bullet-list">
                  <li v-for="item in store.activeFinalEvaluation.key_strengths" :key="item">{{ item }}</li>
                </ul>
              </article>
              <article class="sd-card">
                <h3>Critical Gaps</h3>
                <ul class="sd-bullet-list">
                  <li v-for="item in store.activeFinalEvaluation.critical_gaps" :key="item">{{ item }}</li>
                </ul>
              </article>
              <article class="sd-card">
                <h3>Recommended Next Steps</h3>
                <ul class="sd-bullet-list">
                  <li v-for="item in store.activeFinalEvaluation.recommended_next_steps" :key="item">{{ item }}</li>
                </ul>
              </article>
            </section>

            <!-- Evidence-Backed Rubric Table -->
            <section class="sd-card">
              <div class="sd-card-header">
                <h3>Evidence-Based Rubric Breakdown</h3>
                <span class="sd-muted">{{ (store.activeFinalEvaluation.rubric_scores || []).length }} dimensions</span>
              </div>
              <div class="sd-rubric-table-wrap">
                <table class="sd-rubric-table">
                  <thead>
                    <tr>
                      <th>Dimension</th>
                      <th>Score</th>
                      <th>Observed Evidence</th>
                      <th>Assessment Critique</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="row in (store.activeFinalEvaluation.rubric_scores || [])"
                      :key="row.dimension"
                    >
                      <td><strong>{{ row.dimension }}</strong></td>
                      <td>
                        <span class="badge badge-applied">{{ row.score }} / 5</span>
                      </td>
                      <td class="sd-evidence-cell">{{ row.evidence }}</td>
                      <td>{{ row.critique }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </template>
        </template>

        <!-- Clean Tabbed Frontier Model Second Opinion (Export / Import) -->
        <section
          v-else
          class="sd-card sd-frontier-card"
          data-testid="frontier-packet-card"
        >
          <div class="sd-card-header">
            <div>
              <h3>
                <FileCode :size="16" class="sd-primary-icon" />
                <span>Frontier Model Second Opinion (Claude / ChatGPT / Gemini)</span>
              </h3>
              <p class="sd-muted">
                Export a complete Markdown evaluation dossier (with hidden ground-truth rubric, transcripts, and diagram review notes), upload it with your diagram image to any frontier model, then paste the returned JSON scorecard below.
              </p>
            </div>
            <button
              type="button"
              class="btn btn-secondary"
              data-testid="prepare-frontier-packet-btn"
              :disabled="store.loadingFrontierPacket"
              @click="handlePrepareFrontierPacket"
            >
              <Loader2 v-if="store.loadingFrontierPacket" :size="14" class="spin" />
              <FileCode v-else :size="14" />
              <span>Prepare Frontier Evaluation Packet</span>
            </button>
          </div>

          <div class="sd-frontier-grid">
            <div class="sd-form-stack">
              <div v-if="store.frontierPacket" class="sd-form-stack">
                <div class="sd-packet-actions">
                  <button
                    type="button"
                    class="btn btn-secondary"
                    data-testid="copy-frontier-packet-btn"
                    @click="handleCopyFrontierPacket"
                  >
                    <Copy :size="14" />
                    <span>{{ frontierCopied ? 'Copied!' : 'Copy Markdown Prompt' }}</span>
                  </button>
                  <button
                    type="button"
                    class="btn btn-secondary"
                    data-testid="download-frontier-packet-btn"
                    @click="handleDownloadFrontierPacket"
                  >
                    <Download :size="14" />
                    <span>Download .md Packet</span>
                  </button>
                </div>
                <textarea
                  :value="store.frontierPacket.markdown_packet"
                  readonly
                  rows="9"
                  class="form-textarea sd-packet-preview"
                  data-testid="frontier-packet-textarea"
                />
              </div>
              <p v-else class="sd-muted">
                Click <strong>Prepare Frontier Evaluation Packet</strong> to assemble your self-contained prompt + JSON rubric schema. Remember to attach your diagram image file if pasting into an external chat!
              </p>
            </div>

            <div class="sd-form-stack">
              <label class="sd-field">
                <span>Import External Frontier Scorecard (paste raw JSON or Markdown response)</span>
                <textarea
                  v-model="importEvaluationText"
                  class="form-textarea"
                  rows="9"
                  data-testid="import-frontier-textarea"
                  placeholder='Paste the JSON block returned by Claude, ChatGPT, or Gemini (e.g., ```json { "overall_score": 88, ... } ```)'
                />
              </label>
              <button
                type="button"
                class="btn btn-primary"
                data-testid="import-frontier-submit-btn"
                :disabled="store.importingEvaluation || !importEvaluationText.trim()"
                @click="handleImportFrontierEvaluation"
              >
                <Loader2 v-if="store.importingEvaluation" :size="14" class="spin" />
                <ClipboardCheck v-else :size="14" />
                <span>Import Scorecard</span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.system-design-view {
  max-width: 100%;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sd-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sd-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sd-section-header h2 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.sd-muted {
  color: var(--text-muted);
  font-size: 13px;
}

.sd-card {
  background-color: var(--bg-card);
  border: var(--card-border, 1px solid var(--border-color));
  border-radius: var(--radius-md);
  box-shadow: var(--card-shadow);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sd-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.sd-card-header h3 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
}

.mode-selector-bar,
.mode-toggle-compact {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.mode-selector-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}

.mode-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  transition: all var(--transition-fast);
}

.mode-pill:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
}

.mode-pill.active {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--text-primary);
}

.sd-challenges-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

@media (min-width: 1500px) {
  .sd-challenges-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.challenge-card {
  justify-content: space-between;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.challenge-card:hover {
  border-color: var(--border-subtle);
  box-shadow: var(--card-hover-shadow);
}

.sd-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.challenge-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.challenge-category-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.challenge-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.challenge-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.challenge-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sd-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-input);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.sd-sessions-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.session-row-card {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}

.session-row-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.session-row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sd-workspace-header {
  gap: 10px;
  padding: 14px 18px;
}

.workspace-compact-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.sd-back-icon-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.sd-back-icon-btn:hover {
  color: var(--text-main);
  border-color: var(--border-focus);
  background-color: var(--bg-surface-hover);
}

.workspace-title-block {
  flex: 1;
  min-width: 240px;
}

.workspace-title-block h1 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 2px;
}

.stage-stepper {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.stage-step-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  transition: all var(--transition-fast);
}

.stage-step-btn.completed {
  border-color: var(--border-subtle);
  color: var(--text-main);
}

.stage-step-btn.active {
  background-color: var(--primary);
  border-color: var(--primary);
  color: var(--primary-contrast);
}

.stage-step-btn.locked,
.stage-step-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sd-two-col {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.95fr);
  gap: 16px;
  align-items: stretch;
}

@media (min-width: 901px) {
  .sd-two-col > .sd-card {
    height: 100%;
    min-height: 540px;
    justify-content: space-between;
  }
}

.sd-chat-panel {
  min-height: 540px;
  justify-content: space-between;
}

.sd-transcript-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 320px;
  max-height: 520px;
  overflow-y: auto;
  padding-right: 4px;
}

.sd-turn-bubble {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.turn-interviewer {
  background-color: var(--bg-elevated);
}

.turn-candidate {
  background-color: var(--primary-subtle);
  border-color: var(--border-focus);
}

.turn-meta {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
}

.turn-content {
  font-size: 13px;
  color: var(--text-main);
  white-space: pre-wrap;
}

.sd-chat-input-bar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-lg);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
}

.sd-chat-input-bar:focus-within {
  border-color: var(--border-focus);
}

.sd-chat-input {
  flex: 1;
  min-height: 56px;
  padding: 6px 8px;
  resize: vertical;
  border: none;
  background-color: transparent;
  color: var(--text-main);
  font-size: 13px;
  line-height: 1.45;
  outline: none;
}

.sd-input-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding-bottom: 2px;
}

.btn-input-icon {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background-color: var(--bg-input);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-input-icon:hover:not(:disabled) {
  color: var(--text-main);
  border-color: var(--border-focus);
  background-color: var(--bg-surface-hover);
}

.btn-input-icon.active {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--text-primary);
}

.btn-input-send {
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: var(--radius-md);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.sd-diagram-review-summary {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sd-review-summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.sd-review-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-main);
}

.sd-review-summary-copy {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.45;
}

.sd-defence-sidebar {
  justify-content: space-between;
}

.sd-sidebar-top {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sd-eval-subnav {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sd-form-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sd-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.sd-ledger-actions {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.sd-dropzone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-md);
  background-color: var(--bg-input);
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  transition: border-color var(--transition-fast);
}

.sd-dropzone.dragging {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.sd-preview-img {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-app);
}

.sd-revision-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sd-revision-viewer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sd-review-stage,
.sd-evaluation-stage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.review-banner {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}

.review-banner-text {
  flex: 1;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.review-banner-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sd-clarification-card {
  border-color: var(--status-interview-border);
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
}

.sd-clarification-card h3,
.sd-clarification-card .sd-bullet-list {
  color: var(--status-interview-text);
}

.sd-review-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.sd-bullet-list {
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-main);
}

.sd-ledger-summary-grid,
.sd-eval-highlights {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.sd-eval-hero {
  flex-direction: row;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.eval-score-box {
  padding: 14px 20px;
  border-radius: var(--radius-md);
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary);
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.eval-score-value {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
}

.eval-score-max {
  font-size: 14px;
  color: var(--text-secondary);
}

.eval-summary-block {
  flex: 1;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sd-rubric-table-wrap {
  width: 100%;
  overflow-x: auto;
}

.sd-rubric-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.sd-rubric-table th,
.sd-rubric-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  vertical-align: top;
}

.sd-rubric-table th {
  color: var(--text-secondary);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sd-evidence-cell {
  color: var(--text-primary);
  font-style: italic;
}

.sd-loading-box,
.sd-empty-box {
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 10px;
  color: var(--text-muted);
}

.sd-sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sd-primary-icon {
  color: var(--text-primary);
}

.sd-success-icon {
  color: var(--text-success);
}

.sd-warning-icon {
  color: var(--text-warning);
}

.sd-sub-heading {
  font-weight: 600;
}

.w-full {
  width: 100%;
}

.spin {
  animation: sd-spin 1s linear infinite;
}

@keyframes sd-spin {
  to {
    transform: rotate(360deg);
  }
}

.sd-adaptive-banner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 13px;
  max-width: 780px;
}

.sd-adaptive-pill {
  gap: 5px;
  padding: 4px 10px;
}

.sd-header-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.challenge-badges-right {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  flex-shrink: 0;
}

.sd-difficulty-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid var(--border-subtle);
  white-space: nowrap;
}

.sd-difficulty-pill.diff-easy {
  background: var(--status-offer-bg);
  color: var(--status-offer-text);
  border-color: var(--status-offer-border);
}

.sd-difficulty-pill.diff-medium {
  background: var(--status-interview-bg);
  color: var(--status-interview-text);
  border-color: var(--status-interview-border);
}

.sd-difficulty-pill.diff-hard {
  background: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.challenge-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.challenge-start-btn {
  flex: 1;
  min-width: 0;
  justify-content: center;
}

.challenge-manage-btns {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.challenge-action-icon-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--text-muted);
  flex-shrink: 0;
}

.challenge-action-icon-btn:hover:not(:disabled) {
  background: var(--bg-surface-hover);
  color: var(--text-main);
  border-color: var(--border-focus);
}

.challenge-action-icon-btn.sd-icon-danger-btn:hover:not(:disabled) {
  color: var(--text-danger);
  border-color: var(--status-rejected-border);
  background: var(--status-rejected-bg);
}

.sd-icon-btn,
.sd-icon-danger-btn {
  padding: 4px 6px;
  color: var(--text-muted);
}

.sd-icon-btn:hover {
  color: var(--text-primary);
}

.sd-icon-danger-btn:hover {
  color: var(--text-danger);
}

.sd-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background-color: color-mix(in srgb, var(--bg-app) 82%, transparent);
  backdrop-filter: blur(4px);
}

.sd-modal-dialog {
  width: 100%;
  max-width: 580px;
  max-height: 90vh;
  overflow-y: auto;
}

.sd-two-col-compact {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.sd-checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
}

.sd-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.sd-composer-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.sd-hint-tag {
  background-color: var(--primary-subtle);
  color: var(--text-primary);
  border-color: var(--primary);
}

.sd-frontier-card {
  gap: 16px;
}

.sd-frontier-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.sd-packet-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sd-packet-preview {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
}

.sd-task-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
  font-size: 13px;
}

.sd-task-banner.is-failed {
  background: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.sd-task-banner-info {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.sd-task-banner-error {
  margin: 4px 0 0;
  font-size: 12px;
  opacity: 0.92;
}

.sd-task-banner-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .sd-two-col,
  .sd-frontier-grid {
    grid-template-columns: 1fr;
  }

  .stage-stepper {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
