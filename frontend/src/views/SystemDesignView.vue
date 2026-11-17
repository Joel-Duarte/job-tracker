<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  Bot,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  Download,
  Edit3,
  Eye,
  FileCode,
  FileImage,
  Flame,
  Globe,
  HelpCircle,
  Layers,
  Lightbulb,
  Loader2,
  Lock,
  Maximize2,
  MessageSquare,
  Plus,
  RotateCcw,
  Save,
  Search,
  Send,
  ShieldAlert,
  Shuffle,
  Sparkles,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
import { SystemDesignAPI } from '../api/endpoints'
import { fuzzyFilterApplications } from '../utils/fuzzyMatch'
import { renderChatMarkdown } from '../utils/markdownRenderer'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useSystemDesignStore } from '../stores/systemDesignStore'
import { useUIStore } from '../stores/uiStore'
import FrontierPromptBridge from '../components/common/FrontierPromptBridge.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false },
})

const route = useRoute()
const router = useRouter()
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
  extraContext: '',
})
const appFilterStage = ref('ACTIVE')
const appSearchQuery = ref('')
const challengeImportText = ref('')
const challengePromptCopied = ref(false)
const duplicateChallengeWarning = ref(null)
const tailorInputError = ref('')

const ACTIVE_APP_STAGE_PRIORITY = {
  TECHNICAL_INTERVIEW: 0,
  ONLINE_ASSESSMENT: 1,
  APPLIED: 2,
}

const filteredTailorApplications = computed(() => {
  const allowedStatuses =
    appFilterStage.value === 'INTERVIEW'
      ? new Set(['TECHNICAL_INTERVIEW', 'ONLINE_ASSESSMENT'])
      : new Set(['TECHNICAL_INTERVIEW', 'ONLINE_ASSESSMENT', 'APPLIED'])
  const eligible = (appStore.applications || [])
    .filter((app) => allowedStatuses.has(app.status))
    .slice()
    .sort((a, b) => {
      const pa = ACTIVE_APP_STAGE_PRIORITY[a.status] ?? 9
      const pb = ACTIVE_APP_STAGE_PRIORITY[b.status] ?? 9
      if (pa !== pb) return pa - pb
      return Number(b.id || 0) - Number(a.id || 0)
    })
  const query = appSearchQuery.value.trim()
  return query ? fuzzyFilterApplications(eligible, query, 0.25) : eligible
})

const selectedTailorApp = computed(() => {
  if (!generateForm.value.applicationId) return null
  return (
    (appStore.applications || []).find(
      (a) => String(a.id) === String(generateForm.value.applicationId)
    ) || null
  )
})

const detectedTailorSignals = computed(() => {
  const signals = []
  const app = selectedTailorApp.value
  if (app) {
    if (app.notes && String(app.notes).trim()) signals.push('Application Notes')
    if (
      app.job_posting?.description_markdown ||
      app.job_description ||
      (app.job_posting?.required_skills || app.required_skills || []).length
    ) {
      signals.push('Job Posting & Skills')
    }
    if (
      app.company?.notes ||
      (Array.isArray(app.company?.pros) ? app.company.pros.length > 0 : Boolean(app.company?.pros)) ||
      app.company?.company_research ||
      app.company_research
    ) {
      signals.push('Company Research')
    }
    if (app.match_analysis_payload) {
      signals.push('Match Gap Analysis')
    }
    if (Array.isArray(app.events) && app.events.some((e) => e.email_subject || e.email_summary)) {
      signals.push('Interview Email Clues')
    }
  }
  if (generateForm.value.extraContext.trim()) {
    signals.push('Extra Focus Clues')
  }
  if (generateForm.value.useWebSearch) {
    signals.push('Web Search')
  }
  return signals
})

watch(
  () => [
    generateForm.value.topic,
    generateForm.value.applicationId,
    generateForm.value.extraContext,
  ],
  () => {
    duplicateChallengeWarning.value = null
    tailorInputError.value = ''
  }
)

watch(createModalTab, () => {
  duplicateChallengeWarning.value = null
  tailorInputError.value = ''
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
  assumptionsText: '',
  unresolvedQuestionsText: '',
  notes: '',
  isLocked: false,
})

// Stage 2 & 3: Diagram studio / upload & grounded review state
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
const showStage3ExternalReview = ref(false)
const stage3ImportReviewText = ref('')
const stage3ReviewCopied = ref(false)
const showStage4ExternalDefence = ref(false)
const stage4ImportDefenceText = ref('')
const stage4DefenceCopied = ref(false)

// Seed & Variant Launcher modal state
const showSeedModal = ref(false)
const seedForm = ref({
  challengeId: '',
  selectionType: 'random',
  variantId: '',
  briefSeed: '',
})

const selectedSeedChallenge = computed(() =>
  (store.challenges || []).find((c) => Number(c.id) === Number(seedForm.value.challengeId)) || null
)

const selectedChallengeVariants = computed(
  () => selectedSeedChallenge.value?.available_variants || []
)

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
  ledgerForm.value.assumptionsText = (ledger.assumptions || []).join('\n')
  ledgerForm.value.unresolvedQuestionsText = (ledger.unresolved_questions || []).join('\n')
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

    const requestedStage = route.query?.stage ? String(route.query.stage).toUpperCase() : ''
    if (requestedStage && isStageUnlocked(requestedStage)) {
      activeStageTab.value = requestedStage
      const nextQuery = { ...route.query }
      delete nextQuery.stage
      router.replace({ query: nextQuery })
    } else if (!prevSession || prevSession.id !== session.id || prevSession.stage !== session.stage) {
      activeStageTab.value = session.stage || 'REQUIREMENTS'
    }
  },
  { immediate: true, deep: false }
)

watch(
  () => route.query?.stage,
  (nextStage) => {
    if (!nextStage || !activeSession.value) return
    const normalized = String(nextStage).toUpperCase()
    if (isStageUnlocked(normalized)) {
      activeStageTab.value = normalized
      const nextQuery = { ...route.query }
      delete nextQuery.stage
      router.replace({ query: nextQuery })
    }
  }
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
    const started = await store.startSession(challenge.id, 'ADAPTIVE')
    activeStageTab.value = 'REQUIREMENTS'
    evalSubTab.value = 'scorecard'
    const seedSuffix = started?.brief_seed ? ` (Seed #${started.brief_seed})` : ''
    uiStore.showToast(`Started "${challenge.title}"${seedSuffix}`, 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to start challenge session', 'error')
  }
}

function openSeedLauncherModal(challenge = null, prefillSeed = '') {
  const targetChallenge = challenge || (store.challenges || [])[0] || null
  const variants = targetChallenge?.available_variants || []
  const cleanedSeed = String(prefillSeed || '').trim()
  seedForm.value = {
    challengeId: targetChallenge ? String(targetChallenge.id) : '',
    selectionType: cleanedSeed ? 'seed' : variants.length ? 'variant' : 'random',
    variantId: variants[0]?.variant_id || '',
    briefSeed: cleanedSeed,
  }
  showSeedModal.value = true
}

function onSeedChallengeChange() {
  const variants = selectedChallengeVariants.value
  seedForm.value.variantId = variants[0]?.variant_id || ''
  if (!variants.length && seedForm.value.selectionType === 'variant') {
    seedForm.value.selectionType = 'random'
  }
}

async function handleLaunchSeededSession() {
  const challenge = selectedSeedChallenge.value
  if (!challenge || store.startingSession) return
  const options = {}
  if (seedForm.value.selectionType === 'variant' && seedForm.value.variantId) {
    options.variantId = seedForm.value.variantId
  } else if (seedForm.value.selectionType === 'seed') {
    if (!seedForm.value.briefSeed.trim()) {
      uiStore.showToast('Enter a scenario seed or switch to Random / Variant mode.', 'error')
      return
    }
    options.briefSeed = seedForm.value.briefSeed.trim()
  }
  try {
    const started = await store.startSession(challenge.id, 'ADAPTIVE', null, options)
    showSeedModal.value = false
    activeStageTab.value = 'REQUIREMENTS'
    evalSubTab.value = 'scorecard'
    const seedLabel = started?.brief_seed ? `Seed #${started.brief_seed}` : ''
    const variantLabel = started?.variant_title ? ` • ${started.variant_title}` : ''
    uiStore.showToast(
      `Started "${challenge.title}"${seedLabel ? ` (${seedLabel}${variantLabel})` : ''}`,
      'success'
    )
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to start seeded challenge session', 'error')
  }
}

async function openCreateChallengeModal() {
  editingChallengeId.value = null
  editingChallengeIsBuiltin.value = false
  createModalTab.value = 'generate'
  appFilterStage.value = 'ACTIVE'
  appSearchQuery.value = ''
  generateForm.value.extraContext = ''
  challengeImportText.value = ''
  challengePromptCopied.value = false
  duplicateChallengeWarning.value = null
  tailorInputError.value = ''
  store.challengeFrontierPrompt = null
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
  auditFrontierPromptData.value = null
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

const auditFrontierBridgeRef = ref(null)
const auditFrontierPromptData = ref(null)

async function handlePrepareChallengeAuditFrontier() {
  if (!editingChallengeId.value) return
  try {
    const res = await store.prepareChallengeFrontierAuditPrompt(editingChallengeId.value)
    auditFrontierPromptData.value = res
    try {
      await navigator.clipboard?.writeText(res.markdown_prompt)
      uiStore.showToast('Challenge audit prompt copied! Paste into Claude/ChatGPT, then apply upgraded JSON.', 'success')
    } catch {
      uiStore.showToast('Challenge audit prompt ready below! Copy & run in Frontier chat.', 'info')
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to prepare audit prompt', 'error')
  }
}

async function handleImportChallengeAuditFrontier(rawJson) {
  if (!editingChallengeId.value) return
  try {
    const updated = await store.upgradeChallengeFromFrontier(editingChallengeId.value, rawJson)
    auditFrontierBridgeRef.value?.clearImport()
    showCreateChallengeModal.value = false
    editingChallengeId.value = null
    uiStore.showToast(`Upgraded '${updated.title}' from Frontier review!`, 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Invalid upgraded challenge JSON.', 'error')
  }
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

function _buildChallengeTailorPayload(allowDuplicate = false) {
  return {
    topic: generateForm.value.topic.trim(),
    application_id: generateForm.value.applicationId
      ? Number(generateForm.value.applicationId)
      : null,
    difficulty: generateForm.value.difficulty,
    use_web_search: Boolean(generateForm.value.useWebSearch),
    extra_context: generateForm.value.extraContext.trim(),
    allow_duplicate: Boolean(allowDuplicate),
  }
}

function _hasChallengeTailorInput() {
  return Boolean(
    generateForm.value.topic.trim() ||
      generateForm.value.applicationId ||
      generateForm.value.extraContext.trim()
  )
}

async function handleGenerateChallenge(allowDuplicate = false) {
  if (!_hasChallengeTailorInput()) {
    const msg = 'Please enter a Topic / Scenario Focus or select a Tracked Job Application first.'
    tailorInputError.value = msg
    uiStore.showToast(msg, 'error')
    return
  }
  tailorInputError.value = ''
  duplicateChallengeWarning.value = null
  try {
    await store.generateChallenge(_buildChallengeTailorPayload(allowDuplicate))
    showCreateChallengeModal.value = false
    generateForm.value.topic = ''
    generateForm.value.extraContext = ''
    duplicateChallengeWarning.value = null
    uiStore.showToast('Custom challenge generated!', 'success')
  } catch (err) {
    if (err.status === 409) {
      duplicateChallengeWarning.value = {
        message: err.message,
        source: 'generate',
      }
      uiStore.showToast('Similar challenge already exists — review warning or create anyway.', 'info')
      return
    }
    uiStore.showToast(err.message || 'Failed to generate challenge', 'error')
  }
}

async function handlePrepareChallengeFrontierPrompt() {
  if (!_hasChallengeTailorInput()) {
    const msg = 'Please enter a Topic / Scenario Focus or select a Tracked Job Application first.'
    tailorInputError.value = msg
    uiStore.showToast(msg, 'error')
    return
  }
  tailorInputError.value = ''
  duplicateChallengeWarning.value = null
  try {
    const promptData = await store.prepareChallengeFrontierPrompt(_buildChallengeTailorPayload(false))
    challengePromptCopied.value = false
    if (promptData?.markdown_prompt) {
      try {
        await navigator.clipboard.writeText(promptData.markdown_prompt)
        challengePromptCopied.value = true
      } catch {
        // Browser clipboard permissions vary; user can click Copy Prompt or Download .md on the Frontier tab
      }
    }
    createModalTab.value = 'frontier'
    uiStore.showToast(
      challengePromptCopied.value
        ? 'Frontier prompt prepared & copied to clipboard! Paste into Claude, ChatGPT, or Gemini, then import JSON here.'
        : 'Frontier prompt ready! Copy or download it here, then paste the returned JSON below.',
      'success'
    )
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to prepare frontier prompt', 'error')
  }
}

async function handleImportFrontierChallenge(allowDuplicate = false) {
  const raw = challengeImportText.value.trim()
  if (!raw || store.importingChallenge) return
  duplicateChallengeWarning.value = null
  try {
    await store.importFrontierChallenge({
      raw_response: raw,
      application_id: generateForm.value.applicationId
        ? Number(generateForm.value.applicationId)
        : null,
      difficulty: generateForm.value.difficulty,
      allow_duplicate: Boolean(allowDuplicate),
    })
    showCreateChallengeModal.value = false
    challengeImportText.value = ''
    generateForm.value.topic = ''
    generateForm.value.extraContext = ''
    duplicateChallengeWarning.value = null
    uiStore.showToast('Frontier challenge imported!', 'success')
  } catch (err) {
    if (err.status === 409) {
      duplicateChallengeWarning.value = {
        message: err.message,
        source: 'import',
      }
      uiStore.showToast('Similar challenge already exists — click Create Anyway to override.', 'info')
      return
    }
    uiStore.showToast(
      err.message || 'Could not parse challenge JSON. Ensure a valid JSON object was pasted.',
      'error'
    )
  }
}

function handleCreateAnywayDuplicate() {
  if (duplicateChallengeWarning.value?.source === 'import') {
    return handleImportFrontierChallenge(true)
  }
  return handleGenerateChallenge(true)
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

async function handleRevealRequirements(lockAndProceed = false) {
  if (store.revealingRequirements) return
  try {
    const updated = await store.revealRequirementsLedger(lockAndProceed)
    uiStore.showToast(
      lockAndProceed
        ? 'Requirements revealed & locked! Opening Design Studio...'
        : 'Revealed scenario requirements into your ledger.',
      'info'
    )
    if (lockAndProceed && updated?.id) {
      activeStageTab.value = 'DESIGN'
      await router.push({
        name: 'SystemDesignStudio',
        params: { sessionId: updated.id },
      })
    }
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to reveal requirements ledger', 'error')
  }
}

async function handleSaveLedger(lock = false) {
  const payload = {
    functional_requirements: parseLines(ledgerForm.value.functionalText),
    non_functional_requirements: parseLines(ledgerForm.value.nonFunctionalText),
    scale_estimates: parseScaleLines(ledgerForm.value.scaleText),
    out_of_scope: parseLines(ledgerForm.value.outOfScopeText),
    assumptions: parseLines(ledgerForm.value.assumptionsText),
    unresolved_questions: parseLines(ledgerForm.value.unresolvedQuestionsText),
    notes: ledgerForm.value.notes.trim(),
    is_locked: Boolean(lock),
  }
  try {
    await store.updateRequirementsLedger(payload)
    if (lock) {
      activeStageTab.value = 'DESIGN'
      uiStore.showToast('Requirements locked! Opening Design Studio...', 'success')
      if (activeSession.value?.id) {
        await router.push({
          name: 'SystemDesignStudio',
          params: { sessionId: activeSession.value.id },
        })
      }
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

function openDesignStudio(version = null, fixReview = false) {
  if (!activeSession.value?.id) return
  const query = {}
  if (version) query.version = String(version)
  if (fixReview) query.fixReview = '1'
  router.push({
    name: 'SystemDesignStudio',
    params: { sessionId: activeSession.value.id },
    query: Object.keys(query).length ? query : undefined,
  })
}

function handleLoadRevisionIntoCanvas(rev) {
  openDesignStudio(rev?.version || null)
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

async function _copyMarkdownText(text, copiedFlagRef, successMessage) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copiedFlagRef.value = true
    uiStore.showToast(successMessage, 'success')
  } catch {
    uiStore.showToast('Clipboard write blocked; use Download .md instead.', 'info')
  }
}

function _downloadMarkdownFile(text, filename) {
  if (!text) return
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

async function handleCopyChallengePrompt() {
  return _copyMarkdownText(
    store.challengeFrontierPrompt?.markdown_prompt,
    challengePromptCopied,
    'Copied Frontier Challenge Prompt! Paste into Claude, ChatGPT, or Gemini, then paste JSON below.'
  )
}

function handleDownloadChallengePrompt() {
  return _downloadMarkdownFile(
    store.challengeFrontierPrompt?.markdown_prompt,
    store.challengeFrontierPrompt?.filename || 'system-design-challenge-prompt.md'
  )
}

async function handleCopyFrontierPacket() {
  return _copyMarkdownText(
    store.frontierPacket?.markdown_packet,
    frontierCopied,
    'Copied packet to clipboard! Paste into Claude, ChatGPT, or Gemini with your diagram.'
  )
}

function handleDownloadFrontierPacket() {
  return _downloadMarkdownFile(
    store.frontierPacket?.markdown_packet,
    store.frontierPacket?.filename || 'system-design-frontier-packet.md'
  )
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

async function handleCopyStage3ReviewPrompt() {
  try {
    const res = await store.prepareFrontierReviewPrompt(selectedDiagramVersion.value)
    await _copyMarkdownText(
      res?.markdown_prompt,
      stage3ReviewCopied,
      'Stage 3 Review prompt ready! Paste into ChatGPT/Claude (with diagram image if uploaded), then paste the JSON review back below.'
    )
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to prepare Stage 3 review prompt', 'error')
  }
}

async function handleImportStage3Review() {
  const raw = stage3ImportReviewText.value.trim()
  if (!raw || store.reviewingDiagram) return
  try {
    await store.importFrontierReview(raw, selectedDiagramVersion.value)
    stage3ImportReviewText.value = ''
    showStage3ExternalReview.value = false
    uiStore.showToast('External Stage 3 Architecture Review imported!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Could not parse Stage 3 review JSON.', 'error')
  }
}

async function handleCopyStage4DefencePrompt() {
  try {
    const res = await store.prepareFrontierDefencePrompt()
    await _copyMarkdownText(
      res?.markdown_prompt,
      stage4DefenceCopied,
      'Stage 4 Defence sparring prompt ready! Paste into ChatGPT/Claude to practice live, then log your summary below.'
    )
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to prepare Stage 4 defence prompt', 'error')
  }
}

async function handleImportStage4Defence() {
  const raw = stage4ImportDefenceText.value.trim()
  if (!raw || store.sendingDefence) return
  try {
    await store.importFrontierDefence(raw)
    stage4ImportDefenceText.value = ''
    showStage4ExternalDefence.value = false
    uiStore.showToast('External Defence sparring logged for Stage 5 grading!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Unable to log Defence summary.', 'error')
  }
}

onMounted(async () => {
  window.addEventListener('paste', handlePaste)
  await Promise.allSettled([
    store.fetchChallenges(),
    store.fetchSessions(),
    store.fetchDiagramCatalog(),
  ])
})

onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
  if (stagedPreviewUrl.value) {
    URL.revokeObjectURL(stagedPreviewUrl.value)
  }
})
</script>

<template>
  <div
    class="page-container system-design-view"
    :class="{
      'sd-embedded': props.embedded,
      'sd-session-active': props.embedded && activeSession,
    }"
  >
    <!-- ================================================================
         LOBBY VIEW: Curated & Custom Challenges Grid
         ================================================================ -->
    <template v-if="!activeSession">
      <section class="sd-section">
        <div class="sd-section-header">
          <div class="sd-header-title-group">
            <h2>Interview Challenge Scenarios</h2>
            <span class="sd-muted">{{ store.challenges.length }} scenarios available</span>
            <span
              v-if="store.sessionGamificationStats.completedCount > 0"
              class="sd-xp-lobby-pill"
              data-testid="lobby-xp-stats"
            >
              <Award :size="13" />
              <span>{{ store.sessionGamificationStats.totalXp }} XP</span>
              <span class="sd-dot">•</span>
              <Flame :size="13" />
              <span>{{ store.sessionGamificationStats.streakCount }} completed</span>
            </span>
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
              class="btn btn-secondary"
              data-testid="open-seed-modal-lobby-btn"
              :disabled="!(store.challenges || []).length"
              @click="openSeedLauncherModal()"
            >
              <Shuffle :size="15" />
              <span>Start with Seed / Variant</span>
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
              :class="{ active: createModalTab === 'frontier' }"
              data-testid="tab-frontier-challenge"
              @click="createModalTab = 'frontier'"
            >
              <FileCode :size="13" />
              <span>Frontier Chat</span>
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
            @submit.prevent="handleGenerateChallenge(false)"
          >
            <label class="sd-field">
              <span>Topic / Scenario Focus <em class="sd-required-hint">(or select an application below)</em></span>
              <input
                v-model="generateForm.topic"
                type="text"
                class="form-input"
                :class="{ 'is-invalid': Boolean(tailorInputError) }"
                data-testid="generate-topic-input"
                placeholder="e.g., Real-time fraud scoring pipeline (or pick an application below)"
              />
            </label>

            <div class="sd-field">
              <div class="sd-field-header-row">
                <span>Tailor to Ongoing Job Application (Optional)</span>
                <div class="mode-toggle-compact" role="group" aria-label="Filter application stage">
                  <button
                    type="button"
                    class="mode-pill"
                    :class="{ active: appFilterStage === 'ACTIVE' }"
                    data-testid="app-stage-filter-active"
                    @click="appFilterStage = 'ACTIVE'"
                  >
                    Active Ongoing
                  </button>
                  <button
                    type="button"
                    class="mode-pill"
                    :class="{ active: appFilterStage === 'INTERVIEW' }"
                    data-testid="app-stage-filter-interview"
                    @click="appFilterStage = 'INTERVIEW'"
                  >
                    Interview &amp; OA Only
                  </button>
                </div>
              </div>

              <div v-if="selectedTailorApp" class="sd-selected-app-banner" data-testid="selected-tailor-app">
                <div class="sd-selected-app-info">
                  <strong>{{ selectedTailorApp.company?.name || selectedTailorApp.company_name || 'Company' }}</strong>
                  <span>— {{ selectedTailorApp.position || 'Role' }}</span>
                  <span class="sd-stage-chip">{{ selectedTailorApp.status }}</span>
                </div>
                <button
                  type="button"
                  class="btn btn-ghost btn-sm"
                  data-testid="clear-tailor-app-btn"
                  @click="generateForm.applicationId = ''"
                >
                  Clear
                </button>
              </div>

              <div class="sd-app-search-wrap">
                <Search :size="14" class="sd-search-icon" />
                <input
                  v-model="appSearchQuery"
                  type="text"
                  class="form-input sd-app-search-input"
                  data-testid="challenge-app-search-input"
                  placeholder="Fuzzy search ongoing applications by company, role, notes..."
                />
              </div>

              <div class="sd-app-picker-list" data-testid="tailor-app-picker-list">
                <button
                  v-for="app in filteredTailorApplications"
                  :key="app.id"
                  type="button"
                  class="sd-app-picker-item"
                  :class="{ selected: String(generateForm.applicationId) === String(app.id) }"
                  :data-testid="`tailor-app-option-${app.id}`"
                  @click="
                    generateForm.applicationId =
                      String(generateForm.applicationId) === String(app.id) ? '' : String(app.id)
                  "
                >
                  <div class="sd-app-picker-main">
                    <span class="sd-app-picker-title">
                      {{ app.company?.name || app.company_name || 'Company' }} — {{ app.position || 'Role' }}
                    </span>
                    <div class="sd-app-picker-badges">
                      <span class="sd-stage-chip">{{ app.status }}</span>
                      <span v-if="app.notes && String(app.notes).trim()" class="sd-note-chip">
                        Has Notes
                      </span>
                    </div>
                  </div>
                </button>
                <p v-if="!filteredTailorApplications.length" class="sd-muted sd-empty-picker">
                  No matching ongoing applications in this filter.
                </p>
              </div>
            </div>

            <div
              v-if="detectedTailorSignals.length"
              class="sd-signal-row"
              data-testid="challenge-context-signals"
            >
              <span class="sd-signal-label">Context signals:</span>
              <span v-for="sig in detectedTailorSignals" :key="sig" class="sd-signal-pill">
                {{ sig }}
              </span>
            </div>

            <label class="sd-field">
              <span>Extra Focus / Interviewer Clues (Optional)</span>
              <textarea
                v-model="generateForm.extraContext"
                rows="2"
                class="form-input"
                data-testid="generate-extra-context-input"
                placeholder="e.g., Recruiter hinted heavy Kafka event replay, multi-region ledger consistency, or teams on Go + Postgres..."
              ></textarea>
            </label>

            <div class="sd-inline-options">
              <label class="sd-field">
                <span>Target Difficulty</span>
                <select v-model="generateForm.difficulty" class="form-input">
                  <option value="EASY">Easy</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HARD">Hard</option>
                </select>
              </label>

              <label class="sd-checkbox-row sd-checkbox-inline">
                <input v-model="generateForm.useWebSearch" type="checkbox" />
                <Globe :size="14" class="sd-primary-icon" />
                <span>Ground scenario with Web Search</span>
              </label>
            </div>

            <p v-if="tailorInputError" class="sd-inline-error" data-testid="tailor-input-error">
              <AlertTriangle :size="14" />
              <span>{{ tailorInputError }}</span>
            </p>

            <div
              v-if="duplicateChallengeWarning && duplicateChallengeWarning.source === 'generate'"
              class="sd-duplicate-warning"
              data-testid="duplicate-challenge-warning"
            >
              <div class="sd-duplicate-warning-body">
                <AlertTriangle :size="16" />
                <div>
                  <strong>Duplicate / Overlapping Challenge Detected</strong>
                  <p>{{ duplicateChallengeWarning.message }}</p>
                </div>
              </div>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                data-testid="create-anyway-challenge-btn"
                :disabled="store.generatingChallenge"
                @click="handleCreateAnywayDuplicate"
              >
                Create Anyway
              </button>
            </div>

            <p class="sd-muted">
              Generates 3 distinct requirement variants or prepares a Frontier Chat prompt using your role context and anti-duplication guard.
            </p>

            <div class="sd-modal-actions sd-modal-actions-wrap">
              <button
                type="button"
                class="btn btn-secondary"
                @click="showCreateChallengeModal = false"
              >
                Cancel
              </button>
              <button
                type="button"
                class="btn btn-secondary"
                data-testid="prepare-frontier-challenge-prompt-btn"
                :disabled="store.loadingChallengePrompt || store.generatingChallenge"
                @click="handlePrepareChallengeFrontierPrompt"
              >
                <Loader2 v-if="store.loadingChallengePrompt" :size="14" class="spin" />
                <FileCode v-else :size="14" />
                <span>Prepare Frontier Prompt</span>
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                data-testid="submit-generate-challenge-btn"
                :disabled="store.generatingChallenge || store.loadingChallengePrompt"
              >
                <Loader2 v-if="store.generatingChallenge" :size="14" class="spin" />
                <Sparkles v-else :size="14" />
                <span>Generate with Local AI</span>
              </button>
            </div>
          </form>

          <form
            v-else-if="createModalTab === 'frontier' && !editingChallengeId"
            class="sd-form-stack"
            data-testid="frontier-challenge-panel"
            @submit.prevent="handleImportFrontierChallenge(false)"
          >
            <div v-if="store.challengeFrontierPrompt" class="sd-frontier-prompt-ready">
              <div class="sd-frontier-status-row">
                <span class="sd-frontier-ready-badge">
                  <CheckCircle2 v-if="challengePromptCopied" :size="14" />
                  <FileCode v-else :size="14" />
                  <span>
                    {{
                      challengePromptCopied
                        ? 'Prompt copied to clipboard — paste into Claude, ChatGPT, or Gemini'
                        : 'Frontier Challenge Prompt Ready'
                    }}
                  </span>
                </span>
                <div class="sd-packet-actions">
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    data-testid="copy-frontier-challenge-prompt-btn"
                    @click="handleCopyChallengePrompt"
                  >
                    <Copy :size="13" />
                    <span>{{ challengePromptCopied ? 'Copied!' : 'Copy Prompt' }}</span>
                  </button>
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    data-testid="download-frontier-challenge-prompt-btn"
                    @click="handleDownloadChallengePrompt"
                  >
                    <Download :size="13" />
                    <span>Download .md</span>
                  </button>
                </div>
              </div>
              <textarea
                readonly
                rows="6"
                class="form-input sd-packet-preview"
                data-testid="frontier-challenge-prompt-preview"
                :value="store.challengeFrontierPrompt.markdown_prompt"
              ></textarea>
            </div>

            <div v-else class="sd-frontier-callout">
              <div>
                <strong>Need a tailored prompt first?</strong>
                <p class="sd-muted">
                  Configure your Topic and Ongoing Application on the AI Generate tab and click <strong>Prepare Frontier Prompt</strong>, or paste an existing challenge JSON below.
                </p>
              </div>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                data-testid="back-to-generate-setup-btn"
                @click="createModalTab = 'generate'"
              >
                <ArrowLeft :size="13" />
                <span>Setup Prompt</span>
              </button>
            </div>

            <label class="sd-field">
              <span>Paste Frontier Challenge JSON Response</span>
              <textarea
                v-model="challengeImportText"
                rows="6"
                class="form-input sd-packet-preview"
                data-testid="import-frontier-challenge-input"
                placeholder="Paste the JSON object (or ```json fenced block) returned by Claude, ChatGPT, or Gemini..."
              ></textarea>
            </label>

            <div
              v-if="duplicateChallengeWarning && duplicateChallengeWarning.source === 'import'"
              class="sd-duplicate-warning"
              data-testid="duplicate-challenge-warning"
            >
              <div class="sd-duplicate-warning-body">
                <AlertTriangle :size="16" />
                <div>
                  <strong>Duplicate / Overlapping Challenge Detected</strong>
                  <p>{{ duplicateChallengeWarning.message }}</p>
                </div>
              </div>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                data-testid="create-anyway-challenge-btn"
                :disabled="store.importingChallenge"
                @click="handleCreateAnywayDuplicate"
              >
                Create Anyway
              </button>
            </div>

            <div class="sd-modal-actions sd-modal-actions-wrap">
              <button
                type="button"
                class="btn btn-secondary"
                @click="createModalTab = 'generate'"
              >
                <ArrowLeft :size="14" />
                <span>Back to Setup</span>
              </button>
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
                data-testid="import-frontier-challenge-submit-btn"
                :disabled="store.importingChallenge || !challengeImportText.trim()"
              >
                <Loader2 v-if="store.importingChallenge" :size="14" class="spin" />
                <Upload v-else :size="14" />
                <span>Import Challenge JSON</span>
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

              <FrontierPromptBridge
                v-if="editingChallengeId"
                ref="auditFrontierBridgeRef"
                test-id-prefix="challenge-audit-frontier"
                title="Verify or Upgrade Challenge with Frontier (Claude / ChatGPT / Gemini)"
                subtitle="Send this challenge's full JSON & schema rules to a Frontier model so it verifies all 3 variants, Read/Write paths, and defendable capabilities, then paste the upgraded JSON below."
                prepare-label="Prepare & Copy Audit Prompt"
                import-label="Apply Upgraded Challenge JSON"
                paste-placeholder="Paste the upgraded full challenge JSON object here..."
                :loading="store.loadingChallengePrompt || store.importingChallenge"
                :prompt-data="auditFrontierPromptData"
                @prepare="handlePrepareChallengeAuditFrontier"
                @import="handleImportChallengeAuditFrontier"
              />
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
            <div class="workspace-title-meta-row">
              <h1>{{ activeSession.challenge?.title || 'System Design Session' }}</h1>
              <span
                v-if="activeSession.brief_seed"
                class="sd-tag sd-seed-pill"
                data-testid="active-session-seed-badge"
              >
                Seed: #{{ activeSession.brief_seed }}
              </span>
              <span
                v-if="activeSession.variant_title"
                class="sd-tag sd-variant-pill"
                data-testid="active-session-variant-badge"
                :title="activeSession.variant_focus || activeSession.variant_title"
              >
                {{ activeSession.variant_title }}
              </span>
              <span
                v-else
                class="sd-tag sd-blind-pill"
                data-testid="active-session-blind-badge"
                title="Requirement archetype stays hidden during blind discovery until evaluation completes"
              >
                Blind Profile
              </span>
              <span
                class="badge"
                :class="store.isActiveSessionCoached ? 'badge-applied' : 'badge-offer'"
                data-testid="session-assistance-badge"
              >
                {{ store.isActiveSessionCoached ? 'Coached Run · 100 XP' : 'Solo Run · 150 XP' }}
              </span>
            </div>
          </div>

          <button
            type="button"
            class="btn btn-secondary btn-xs sd-header-variant-btn"
            data-testid="open-seed-modal-active-btn"
            @click="openSeedLauncherModal(activeSession.challenge, activeSession.brief_seed || '')"
          >
            <Shuffle :size="13" />
            <span>New Variant / Replay Seed</span>
          </button>
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

      </div>

      <!-- Background Queue Task Banner (F-04) -->
      <div
        v-if="['QUEUED', 'RUNNING', 'PROCESSING', 'FAILED', 'CANCELLED'].includes(activeSession.active_task_status)"
        class="sd-task-banner"
        :class="{
          'is-failed': ['FAILED', 'CANCELLED'].includes(activeSession.active_task_status),
          'is-processing': ['QUEUED', 'RUNNING', 'PROCESSING'].includes(activeSession.active_task_status),
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
          <div class="sd-task-banner-copy">
            <strong>
              {{
                activeSession.active_task_type === 'SYSTEM_DESIGN_EVALUATION'
                  ? 'Final Evaluation Task'
                  : 'Architecture Review Task'
              }}
              • {{ activeSession.active_task_status }}
              <span v-if="activeSession.active_task_stage">({{ activeSession.active_task_stage }})</span>
              <span
                v-if="activeSession.active_task_attempt_count > 1"
                class="sd-task-banner-meta"
              >
                • Attempt #{{ activeSession.active_task_attempt_count }}
              </span>
              <span
                v-if="activeSession.active_task_provider"
                class="sd-task-banner-meta"
              >
                • {{ activeSession.active_task_provider }}
              </span>
              <span
                v-if="(activeSession.active_task_completed_steps || []).length"
                class="sd-task-banner-meta"
              >
                • {{ activeSession.active_task_completed_steps.length }}/3 steps
              </span>
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
              <div
                class="turn-content sd-markdown-body"
                v-html="renderChatMarkdown(turn.content)"
              />
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
                aria-label="Ask for a Coaching Hint"
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
                aria-label="Send question"
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
            <div class="sd-ledger-title-group">
              <h3>
                <ClipboardCheck :size="16" />
                <span>Requirements Ledger</span>
              </h3>
              <span class="sd-live-sync-pill" data-testid="live-sync-pill">
                Live-synced on every turn
              </span>
            </div>
            <div class="sd-ledger-head-actions">
              <button
                type="button"
                class="btn btn-secondary"
                data-testid="reveal-requirements-btn"
                :disabled="store.revealingRequirements"
                title="Reveal all brief requirements into the ledger (switches session to Coached Run, 0 score penalty)"
                @click="handleRevealRequirements(false)"
              >
                <Loader2 v-if="store.revealingRequirements" :size="14" class="spin" />
                <Eye v-else :size="14" />
                <span>Reveal Requirements</span>
              </button>
              <button
                type="button"
                class="btn btn-secondary"
                data-testid="resync-ledger-btn"
                :disabled="store.extractingLedger"
                @click="handleExtractLedger"
              >
                <Loader2 v-if="store.extractingLedger" :size="14" class="spin" />
                <RotateCcw v-else :size="14" />
                <span>Re-sync Ledger</span>
              </button>
            </div>
          </div>

          <div class="sd-form-stack sd-ledger-sections">
            <details class="sd-ledger-section" open>
              <summary>
                <span>Functional Requirements (one per line)</span>
                <span class="sd-ledger-preview">{{ ledgerForm.functionalText.split('\n').filter(line => line.trim()).join(' · ') || 'No requirements recorded' }}</span>
              </summary>
              <label class="sd-field">
                <span>Functional Requirements (one per line)</span>
              <textarea
                v-model="ledgerForm.functionalText"
                class="form-textarea"
                rows="2"
                placeholder="e.g., Create short links&#10;Redirect short code with 302"
              />
              </label>
            </details>

            <details class="sd-ledger-section">
              <summary>
                <span>Non-Functional Requirements &amp; SLAs</span>
                <span class="sd-ledger-preview">{{ ledgerForm.nonFunctionalText.split('\n').filter(line => line.trim()).join(' · ') || 'No requirements recorded' }}</span>
              </summary>
              <label class="sd-field">
                <span>Non-Functional Requirements &amp; SLAs (one per line)</span>
              <textarea
                v-model="ledgerForm.nonFunctionalText"
                class="form-textarea"
                rows="2"
                placeholder="e.g., 99.95% availability&#10;p99 redirect latency < 50ms"
              />
              </label>
            </details>

            <details class="sd-ledger-section">
              <summary>
                <span>Scale &amp; Capacity Estimates</span>
                <span class="sd-ledger-preview">{{ ledgerForm.scaleText.split('\n').filter(line => line.trim()).join(' · ') || 'No estimates recorded' }}</span>
              </summary>
              <label class="sd-field">
                <span>Scale &amp; Capacity Estimates (`metric: value` per line)</span>
              <textarea
                v-model="ledgerForm.scaleText"
                class="form-textarea"
                rows="1"
                placeholder="e.g., read_write_ratio: 100:1&#10;mau: 50M users"
              />
              </label>
            </details>

            <details class="sd-ledger-section">
              <summary>
                <span>Out of Scope</span>
                <span class="sd-ledger-preview">{{ ledgerForm.outOfScopeText.split('\n').filter(line => line.trim()).join(' · ') || 'No items recorded' }}</span>
              </summary>
              <label class="sd-field">
                <span>Out of Scope (one per line)</span>
              <textarea
                v-model="ledgerForm.outOfScopeText"
                class="form-textarea"
                rows="1"
                placeholder="e.g., Custom billing dashboards"
              />
              </label>
            </details>

            <details class="sd-ledger-section">
              <summary>
                <span>Confirmed / Baseline Assumptions</span>
                <span class="sd-ledger-preview">{{ ledgerForm.assumptionsText.split('\n').filter(line => line.trim()).join(' · ') || 'No assumptions recorded' }}</span>
              </summary>
              <label class="sd-field">
                <span>Confirmed / Baseline Assumptions (one per line)</span>
              <textarea
                v-model="ledgerForm.assumptionsText"
                class="form-textarea"
                rows="1"
                placeholder="e.g., Assume single-region writes unless specified otherwise"
              />
              </label>
            </details>

            <details class="sd-ledger-section">
              <summary>
                <span>Unresolved Questions (one per line)</span>
                <span class="sd-count-pill">{{ ledgerForm.unresolvedQuestionsText.split('\n').filter(line => line.trim()).length }} open</span>
                <span class="sd-ledger-preview">{{ ledgerForm.unresolvedQuestionsText.split('\n').filter(line => line.trim()).join(' · ') || 'No open questions' }}</span>
              </summary>
              <label class="sd-field">
                <span>Unresolved Questions (one per line)</span>
              <textarea
                v-model="ledgerForm.unresolvedQuestionsText"
                class="form-textarea"
                rows="1"
                placeholder="e.g., Custom domain SSL provisioning?"
              />
              </label>
            </details>

            <details class="sd-ledger-section">
              <summary>
                <span>Notes &amp; Key APIs</span>
                <span class="sd-ledger-preview">{{ ledgerForm.notes || 'No notes recorded' }}</span>
              </summary>
              <label class="sd-field">
                <span>Notes &amp; Key APIs</span>
              <textarea
                v-model="ledgerForm.notes"
                class="form-textarea"
                rows="1"
                placeholder="Any agreed assumptions or constraints..."
              />
              </label>
            </details>
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
              class="btn btn-secondary"
              data-testid="jump-to-studio-btn"
              :disabled="store.revealingRequirements || store.savingLedger"
              @click="handleRevealRequirements(true)"
            >
              <Loader2 v-if="store.revealingRequirements" :size="14" class="spin" />
              <Maximize2 v-else :size="14" />
              <span>Reveal &amp; Jump to Studio</span>
            </button>
            <button
              type="button"
              class="btn btn-primary"
              data-testid="lock-requirements-btn"
              :disabled="store.savingLedger"
              @click="handleSaveLedger(true)"
            >
              <Loader2 v-if="store.savingLedger" :size="14" class="spin" />
              <Lock v-else :size="14" />
              <span>Lock &amp; continue</span>
            </button>
          </div>
        </section>
      </div>

      <!-- ==============================================================
           STAGE 2: DESIGN STUDIO LAUNCHER & EXTERNAL UPLOAD (v1..vN)
           ============================================================== -->
      <div v-else-if="activeStageTab === 'DESIGN'" class="sd-design-stage">
        <div class="sd-two-col">
          <!-- Interactive Full-Screen Design Studio Launcher & Revisions -->
          <section class="sd-card sd-studio-launch-card">
            <div class="sd-card-header">
              <h3>
                <Layers :size="16" />
                <span>Interactive Design Studio</span>
              </h3>
              <span class="badge badge-assessment">Full-Screen Canvas</span>
            </div>

            <div class="sd-studio-launch-intro">
              <p class="sd-muted sd-helper-copy">
                Open the dedicated full-screen workspace to drag components from the palette, connect handles and label wires inline,
                unlock guided component hints, and save Flow JSON revisions.
              </p>

              <button
                type="button"
                class="btn btn-secondary sd-launch-studio-btn"
                data-testid="open-design-studio-btn"
                @click="openDesignStudio()"
              >
                <Maximize2 :size="15" />
                <span>Open Design Studio</span>
              </button>
            </div>

            <div class="sd-studio-revisions-block">
              <div class="sd-card-header sd-revisions-header">
                <h4>
                  <span>Saved Revisions</span>
                  <span class="badge badge-assessment">{{ store.activeDiagrams.length }}</span>
                </h4>
              </div>

              <div v-if="!store.activeDiagrams.length" class="sd-empty-box">
                <Layers :size="22" />
                <p>No diagram saved yet. Launch the Design Studio or upload an exported image on the right.</p>
              </div>

              <div v-else class="sd-revision-list">
                <article
                  v-for="rev in store.activeDiagrams"
                  :key="rev.version"
                  class="sd-revision-row"
                  :class="{ selected: selectedRevision?.version === rev.version }"
                >
                  <button
                    type="button"
                    class="sd-revision-select"
                    :aria-pressed="selectedRevision?.version === rev.version"
                    @click="selectedDiagramVersion = rev.version"
                  >
                    <strong>v{{ rev.version }} ({{ rev.diagram_kind === 'canvas' ? 'Canvas' : 'Image' }})</strong>
                    <span class="badge badge-assessment">
                      {{ rev.node_count || 0 }} blocks · {{ rev.edge_count || 0 }} flows
                    </span>
                  </button>
                  <details
                    v-if="rev.components_preview?.length || rev.notes || rev.diagram_kind !== 'canvas'"
                    class="sd-revision-disclosure"
                  >
                    <summary>
                      <span>Revision details</span>
                      <span
                        v-if="rev.components_preview?.length || rev.notes"
                        class="sd-revision-preview"
                      >
                        {{ rev.components_preview?.join(' · ') || rev.notes }}
                      </span>
                    </summary>
                    <div v-if="rev.components_preview?.length" class="challenge-tags">
                      <span v-for="comp in rev.components_preview" :key="comp" class="sd-tag">
                        {{ comp }}
                      </span>
                    </div>
                    <p v-if="rev.notes" class="sd-muted"><strong>Notes:</strong> {{ rev.notes }}</p>
                    <img
                      v-if="rev.diagram_kind !== 'canvas'"
                      :src="getRevisionImageUrl(rev)"
                      :alt="`Diagram revision v${rev.version}`"
                      class="sd-preview-img"
                    />
                  </details>
                  <div class="sd-revision-actions">
                    <label
                      v-if="selectedRevision?.version === rev.version"
                      class="sd-checkbox-row sd-web-search-row"
                    >
                      <input
                        v-model="useWebSearchReview"
                        type="checkbox"
                        data-testid="review-web-search-checkbox"
                      />
                      <Globe :size="14" class="sd-primary-icon" />
                      <span>Ground with Web Search</span>
                    </label>
                    <div class="sd-revision-action-buttons">
                      <button
                        v-if="rev.diagram_kind === 'canvas'"
                        type="button"
                        class="btn btn-secondary btn-sm"
                        data-testid="load-canvas-revision-btn"
                        @click="handleLoadRevisionIntoCanvas(rev)"
                      >
                        <Edit3 :size="14" />
                        <span>Edit in Studio</span>
                      </button>
                      <button
                        type="button"
                        class="btn btn-secondary btn-sm"
                        data-testid="analyze-selected-revision-btn"
                        :disabled="store.reviewingDiagram"
                        @click="handleAnalyzeArchitecture(rev.version)"
                      >
                        <Loader2 v-if="store.reviewingDiagram" :size="14" class="spin" />
                        <Sparkles v-else :size="14" />
                        <span>Analyze Architecture (v{{ rev.version }})</span>
                      </button>
                    </div>
                  </div>
                  <div
                    v-if="
                      selectedReview &&
                      Number(selectedReview.diagram_version) === Number(rev.version)
                    "
                    class="sd-diagram-review-summary"
                    data-testid="diagram-review-summary"
                  >
                    <span class="sd-review-status-pill">
                      <CheckCircle2 :size="15" class="sd-success-icon" />
                      <strong>Reviewed (v{{ selectedReview.diagram_version }})</strong>
                    </span>
                    <div class="sd-review-metrics">
                      <span class="sd-review-metric">
                        <CheckCircle2 :size="15" />
                        {{ (selectedReview.strengths || []).length }}
                        {{ (selectedReview.strengths || []).length === 1 ? 'strength' : 'strengths' }}
                      </span>
                      <span class="sd-review-metric">
                        <AlertTriangle :size="15" />
                        {{ (selectedReview.bottlenecks_and_spofs || []).length }}
                        {{ (selectedReview.bottlenecks_and_spofs || []).length === 1 ? 'bottleneck' : 'bottlenecks' }}
                      </span>
                      <span class="sd-review-metric">
                        <ShieldAlert :size="15" />
                        {{ (selectedReview.missing_components || []).length }} missing
                      </span>
                    </div>
                    <button
                      type="button"
                      class="btn btn-primary btn-sm"
                      @click="selectStage('REVIEW')"
                    >
                      <span>Open Full Critique</span>
                      <ArrowRight :size="13" />
                    </button>
                  </div>
                </article>
              </div>
            </div>
          </section>

          <!-- External Image Upload & Paste -->
          <section class="sd-card sd-upload-card">
            <div class="sd-card-header">
              <h3>
                <Upload :size="16" />
                <span>Upload Architecture Diagram</span>
              </h3>
              <span class="sd-muted">PNG, JPEG, or WebP (max 10 MB)</span>
            </div>

            <p class="sd-muted sd-helper-copy">
              Prefer Excalidraw, Draw.io, Miro, or paper sketches? Upload the exported image or press <strong>Ctrl+V</strong> to paste directly from your clipboard.
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
              <label class="btn btn-secondary sd-browse-files">
                <span>Browse files</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  class="diagram-file-input"
                  aria-label="Upload diagram image"
                  @change="handleFileInputChange"
                />
              </label>
            </div>

            <div v-if="stagedPreviewUrl" class="sd-staged-preview">
              <span class="sd-muted">Ready to upload: {{ stagedDiagramFile?.name || 'pasted-diagram.png' }}</span>
              <img :src="stagedPreviewUrl" alt="Staged architecture diagram preview" class="sd-preview-img" />
            </div>

            <div class="sd-upload-footer">
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
        </div>
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
          <div class="sd-empty-review-actions">
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!store.activeDiagrams.length || store.reviewingDiagram"
              @click="store.activeDiagrams.length ? handleAnalyzeArchitecture() : (activeStageTab = 'DESIGN')"
            >
              <Loader2 v-if="store.reviewingDiagram" :size="14" class="spin" />
              <span>{{ store.activeDiagrams.length ? 'Analyze Latest Diagram' : 'Go Upload a Diagram' }}</span>
            </button>
            <button
              v-if="store.activeDiagrams.length"
              type="button"
              class="btn btn-secondary"
              data-testid="toggle-stage3-external-review-btn"
              @click="showStage3ExternalReview = !showStage3ExternalReview"
            >
              <FileCode :size="14" />
              <span>{{ showStage3ExternalReview ? 'Hide External AI Review' : 'Use External AI (ChatGPT/Claude)' }}</span>
            </button>
          </div>
          <div
            v-if="showStage3ExternalReview && store.activeDiagrams.length"
            class="sd-external-bridge-box"
            data-testid="stage3-external-review-panel"
          >
            <div class="sd-external-bridge-actions">
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                data-testid="copy-frontier-review-prompt-btn"
                :disabled="store.loadingFrontierPacket"
                @click="handleCopyStage3ReviewPrompt"
              >
                <Copy :size="13" />
                <span>{{ stage3ReviewCopied ? 'Copied Review Prompt!' : 'Copy Stage 3 Review Prompt' }}</span>
              </button>
            </div>
            <textarea
              v-if="store.frontierReviewPrompt?.markdown_prompt"
              :value="store.frontierReviewPrompt.markdown_prompt"
              readonly
              rows="4"
              class="form-textarea sd-code-textarea"
              data-testid="frontier-review-prompt-preview"
            />
            <textarea
              v-model="stage3ImportReviewText"
              rows="4"
              class="form-textarea"
              data-testid="import-frontier-review-textarea"
              placeholder="Paste the Stage 3 Review JSON object from ChatGPT / Claude / Gemini..."
            />
            <button
              type="button"
              class="btn btn-primary btn-sm"
              data-testid="import-frontier-review-submit-btn"
              :disabled="!stage3ImportReviewText.trim() || store.reviewingDiagram"
              @click="handleImportStage3Review"
            >
              <span>Import External Review JSON</span>
            </button>
          </div>
        </div>

        <template v-else>
          <div class="sd-card review-banner">
            <div class="review-banner-heading">
              <div class="session-row-title-row">
                <span class="badge badge-assessment">Revision v{{ selectedReview.diagram_version }}</span>
                <h3>Architecture Critique</h3>
              </div>
            </div>
            <div class="review-banner-text">
              <p class="sd-critique-copy">{{ selectedReview.overall_impression }}</p>
            </div>
            <div class="review-banner-actions">
              <button
                type="button"
                class="btn btn-secondary"
                data-testid="revise-in-studio-btn"
                @click="openDesignStudio(selectedReview.diagram_version, true)"
              >
                <Layers :size="14" />
                <span>Revise in Design Studio</span>
              </button>
              <button
                type="button"
                class="btn btn-ghost btn-sm"
                data-testid="upload-revised-image-fallback-btn"
                @click="selectStage('DESIGN')"
              >
                <Upload :size="13" />
                <span>Image Upload</span>
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

          <div class="sd-review-grid">
            <div class="sd-review-column sd-review-column-left">
              <section
                v-if="selectedReview.visual_clarifications_needed?.length"
                class="sd-review-group sd-clarification-group"
              >
                <div class="sd-review-group-heading">
                  <h3>
                    <HelpCircle :size="16" />
                    <span>Visual Clarifications Needed</span>
                  </h3>
                  <span class="badge badge-interview">Clarify, Not Penalized</span>
                </div>
                <ul class="sd-bullet-list">
                  <li v-for="item in selectedReview.visual_clarifications_needed" :key="item">{{ item }}</li>
                </ul>
              </section>

              <details class="sd-review-group" open>
                <summary class="sd-review-group-heading">
                  <h3>
                    <CheckCircle2 :size="16" class="sd-success-icon" />
                    <span>Strengths</span>
                  </h3>
                </summary>
                <p class="sd-review-preview">
                  {{ selectedReview.strengths?.[0] || 'None highlighted yet.' }}
                </p>
                <ul class="sd-bullet-list">
                  <li v-for="item in selectedReview.strengths" :key="item">{{ item }}</li>
                  <li v-if="!selectedReview.strengths?.length" class="sd-muted">None highlighted yet.</li>
                </ul>
              </details>

              <details class="sd-review-group">
                <summary class="sd-review-group-heading">
                  <h3>
                    <AlertTriangle :size="16" class="sd-warning-icon" />
                    <span>Bottlenecks & Single Points of Failure</span>
                  </h3>
                </summary>
                <p class="sd-review-preview">
                  {{ selectedReview.bottlenecks_and_spofs?.[0] || 'None detected.' }}
                </p>
                <ul class="sd-bullet-list">
                  <li v-for="item in selectedReview.bottlenecks_and_spofs" :key="item">{{ item }}</li>
                  <li v-if="!selectedReview.bottlenecks_and_spofs?.length" class="sd-muted">None detected.</li>
                </ul>
              </details>

              <details class="sd-review-group">
                <summary class="sd-review-group-heading">
                  <h3>
                    <Layers :size="16" />
                    <span>Interpreted Components & Complexity Check</span>
                  </h3>
                </summary>
                <p class="sd-review-preview">
                  {{ selectedReview.interpreted_components?.join(', ') || 'No components interpreted.' }}
                </p>
                <div class="sd-review-expanded-content">
                  <p class="sd-muted sd-sub-heading">Observed components:</p>
                  <div class="challenge-tags">
                    <span v-for="comp in selectedReview.interpreted_components" :key="comp" class="sd-tag">
                      {{ comp }}
                    </span>
                  </div>
                  <template v-if="selectedReview.unnecessary_complexity?.length">
                    <p class="sd-muted sd-sub-heading">Unnecessary complexity:</p>
                    <ul class="sd-bullet-list">
                      <li v-for="item in selectedReview.unnecessary_complexity" :key="item">{{ item }}</li>
                    </ul>
                  </template>
                </div>
              </details>
            </div>

            <article class="sd-card sd-review-column sd-review-column-right">
              <div class="sd-card-header">
                <h3>
                  <ShieldAlert :size="16" />
                  <span>Missing Components & Requirement Gaps</span>
                </h3>
              </div>
              <details class="sd-review-disclosure" open>
                <summary>
                  <span>Missing components</span>
                  <span class="sd-count-pill">{{ selectedReview.missing_components?.length || 0 }}</span>
                </summary>
                <ul class="sd-bullet-list">
                  <li v-for="item in selectedReview.missing_components" :key="`mc-${item}`">{{ item }}</li>
                </ul>
              </details>
              <details class="sd-review-disclosure">
                <summary>
                  <span>Requirement gaps</span>
                  <span class="sd-count-pill">{{ selectedReview.requirement_gaps?.length || 0 }}</span>
                </summary>
                <ul class="sd-bullet-list">
                  <li v-for="item in selectedReview.requirement_gaps" :key="`rg-${item}`">{{ item }}</li>
                </ul>
              </details>
              <p
                v-if="!selectedReview.missing_components?.length && !selectedReview.requirement_gaps?.length"
                class="sd-muted"
              >
                All locked requirements appear represented.
              </p>
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
              <div
                class="turn-content sd-markdown-body"
                v-html="renderChatMarkdown(turn.content)"
              />
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
                aria-label="Ground next interviewer probe with Web Search"
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
                aria-label="Ask for a Coaching Hint"
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
                aria-label="Send defence response"
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
              <span v-if="selectedRevision" class="sd-reference-version-line">
                <span class="badge badge-assessment">v{{ selectedRevision.version }}</span>
                <span v-if="selectedRevision.diagram_kind === 'canvas'">
                  {{ selectedRevision.node_count || 0 }} blocks · {{ selectedRevision.edge_count || 0 }} flows
                </span>
              </span>
            </div>

            <div v-if="selectedRevision?.diagram_kind === 'canvas'" class="sd-canvas-ref-box">
              <details v-if="selectedRevision.components_preview?.length" class="sd-reference-components">
                <summary>Show component names</summary>
                <div class="challenge-tags">
                  <span v-for="comp in selectedRevision.components_preview" :key="comp" class="sd-tag">
                    {{ comp }}
                  </span>
                </div>
              </details>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                @click="handleLoadRevisionIntoCanvas(selectedRevision)"
              >
                <Edit3 :size="13" />
                <span>Edit in Canvas Builder</span>
              </button>
            </div>
            <img
              v-else-if="selectedRevision"
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
              class="btn btn-primary w-full"
              data-testid="evaluate-session-btn"
              :disabled="store.evaluatingSession"
              @click="handleEvaluateSession"
            >
              <Loader2 v-if="store.evaluatingSession" :size="14" class="spin" />
              <ClipboardCheck v-else :size="14" />
              <span>Complete &amp; Evaluate with Local AI</span>
            </button>
            <button
              type="button"
              class="btn btn-secondary w-full"
              @click="openDesignStudio(selectedRevision?.version || null, true)"
            >
              <RotateCcw :size="14" />
              <span>Revise in Design Studio (v{{ (store.activeDiagrams.length || 0) + 1 }})</span>
            </button>
            <button
              type="button"
              class="btn btn-ghost btn-sm w-full"
              data-testid="toggle-stage4-external-defence-btn"
              aria-haspopup="dialog"
              @click="showStage4ExternalDefence = true"
            >
              <FileCode :size="13" />
              <span>Spar in External AI (ChatGPT/Claude)</span>
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
                  <span
                    class="badge"
                    :class="
                      (store.activeFinalEvaluation.assistance_mode ||
                        (store.isActiveSessionCoached ? 'COACHED' : 'SOLO')) === 'SOLO'
                        ? 'badge-offer'
                        : 'badge-applied'
                    "
                    data-testid="eval-assistance-badge"
                  >
                    {{
                      (store.activeFinalEvaluation.assistance_mode ||
                        (store.isActiveSessionCoached ? 'COACHED' : 'SOLO')) === 'SOLO'
                        ? 'Solo Run'
                        : 'Coached Run'
                    }}
                  </span>
                  <span class="sd-xp-earned-pill" data-testid="eval-xp-badge">
                    <Award :size="13" />
                    <span>
                      +{{
                        store.activeFinalEvaluation.xp_earned ??
                        ((store.activeFinalEvaluation.assistance_mode ||
                          (store.isActiveSessionCoached ? 'COACHED' : 'SOLO')) === 'SOLO'
                          ? 150
                          : 100)
                      }}
                      XP
                    </span>
                  </span>
                  <span v-if="assistedTurnCount > 0" class="sd-tag">
                    {{ assistedTurnCount }} coaching prompt(s) used
                  </span>
                </div>
                <p>{{ store.activeFinalEvaluation.executive_summary }}</p>
              </div>
            </section>

            <div class="sd-evaluation-content">
              <section class="sd-card sd-eval-highlights" data-testid="eval-highlights">
                <div class="sd-card-header">
                  <h3>Key Takeaways</h3>
                </div>
                <details class="sd-eval-takeaway">
                  <summary>
                    <span class="sd-eval-takeaway-title">Top Strengths</span>
                    <span class="sd-eval-preview">
                      {{ store.activeFinalEvaluation.key_strengths?.[0] || 'No strengths recorded.' }}
                    </span>
                  </summary>
                  <ul class="sd-bullet-list">
                    <li v-for="item in store.activeFinalEvaluation.key_strengths" :key="item">{{ item }}</li>
                  </ul>
                </details>
                <details class="sd-eval-takeaway">
                  <summary>
                    <span class="sd-eval-takeaway-title">Critical Gaps</span>
                    <span class="sd-eval-preview">
                      {{ store.activeFinalEvaluation.critical_gaps?.[0] || 'No critical gaps recorded.' }}
                    </span>
                  </summary>
                  <ul class="sd-bullet-list">
                    <li v-for="item in store.activeFinalEvaluation.critical_gaps" :key="item">{{ item }}</li>
                  </ul>
                </details>
                <details class="sd-eval-takeaway">
                  <summary>
                    <span class="sd-eval-takeaway-title">Recommended Next Steps</span>
                    <span class="sd-eval-preview">
                      {{ store.activeFinalEvaluation.recommended_next_steps?.[0] || 'No next steps recorded.' }}
                    </span>
                  </summary>
                  <ul class="sd-bullet-list">
                    <li v-for="item in store.activeFinalEvaluation.recommended_next_steps" :key="item">{{ item }}</li>
                  </ul>
                </details>
              </section>

              <section class="sd-card sd-eval-rubric-panel" data-testid="eval-rubric-panel">
                <div class="sd-card-header">
                  <h3>Evidence-Based Rubric Breakdown</h3>
                  <span class="sd-muted">{{ (store.activeFinalEvaluation.rubric_scores || []).length }} dimensions</span>
                </div>
                <div class="sd-rubric-list">
                  <details
                    v-for="(row, index) in (store.activeFinalEvaluation.rubric_scores || [])"
                    :key="row.dimension"
                    class="sd-rubric-item"
                    :open="index === 0"
                  >
                    <summary>
                      <strong>{{ row.dimension }}</strong>
                      <span class="badge badge-applied">{{ row.score }} / 5</span>
                      <span class="sd-rubric-preview">{{ row.evidence }}</span>
                    </summary>
                    <div class="sd-rubric-evidence">
                      <p><strong>Observed Evidence</strong>{{ row.evidence }}</p>
                      <p><strong>Assessment Critique</strong>{{ row.critique }}</p>
                    </div>
                  </details>
                </div>
              </section>
            </div>
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

    <div
      v-if="showStage4ExternalDefence"
      class="sd-modal-overlay"
      data-testid="stage4-external-defence-modal"
      @click.self="showStage4ExternalDefence = false"
      @keydown.esc="showStage4ExternalDefence = false"
    >
      <section
        class="sd-card sd-modal-dialog sd-external-defence-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="stage4-external-defence-title"
        tabindex="-1"
      >
        <div class="sd-card-header">
          <h2 id="stage4-external-defence-title">Spar in External AI (ChatGPT/Claude)</h2>
          <button
            type="button"
            class="btn-icon"
            aria-label="Close external defence dialog"
            autofocus
            @click="showStage4ExternalDefence = false"
          >
            <X :size="16" />
          </button>
        </div>
        <div class="sd-external-bridge-box" data-testid="stage4-external-defence-panel">
          <button
            type="button"
            class="btn btn-secondary btn-sm w-full"
            data-testid="copy-frontier-defence-prompt-btn"
            :disabled="store.loadingFrontierPacket"
            @click="handleCopyStage4DefencePrompt"
          >
            <Copy :size="13" />
            <span>{{ stage4DefenceCopied ? 'Copied Defence Prompt!' : 'Copy Defence Sparring Prompt' }}</span>
          </button>
          <textarea
            v-if="store.frontierDefencePrompt?.markdown_prompt"
            :value="store.frontierDefencePrompt.markdown_prompt"
            readonly
            rows="3"
            class="form-textarea sd-code-textarea"
            data-testid="frontier-defence-prompt-preview"
          />
          <textarea
            v-model="stage4ImportDefenceText"
            rows="3"
            class="form-textarea"
            data-testid="import-frontier-defence-textarea"
            placeholder="Paste your external Defence Q&A summary for Stage 5 grading..."
          />
          <button
            type="button"
            class="btn btn-primary btn-sm w-full"
            data-testid="import-frontier-defence-submit-btn"
            :disabled="!stage4ImportDefenceText.trim() || store.sendingDefence"
            @click="handleImportStage4Defence"
          >
            <span>Log External Defence</span>
          </button>
        </div>
      </section>
    </div>

    <!-- Seed / Variant Launcher Modal -->
    <div
      v-if="showSeedModal"
      class="sd-modal-overlay"
      data-testid="seed-variant-modal"
      @click.self="showSeedModal = false"
    >
      <div class="sd-card sd-modal-dialog">
        <div class="sd-card-header">
          <h3>
            <Shuffle :size="16" class="sd-primary-icon" />
            <span>Start with Seed or Requirement Variant</span>
          </h3>
          <button
            type="button"
            class="btn btn-ghost btn-xs"
            aria-label="Close seed modal"
            @click="showSeedModal = false"
          >
            <X :size="15" />
          </button>
        </div>

        <form class="sd-form-stack" @submit.prevent="handleLaunchSeededSession">
          <label class="sd-field">
            <span>Challenge Scenario</span>
            <select
              v-model="seedForm.challengeId"
              class="form-input"
              data-testid="seed-modal-challenge-select"
              @change="onSeedChallengeChange"
            >
              <option
                v-for="ch in store.challenges"
                :key="ch.id"
                :value="String(ch.id)"
              >
                {{ ch.title }} ({{ formatDifficultyLabel(ch.difficulty) }})
              </option>
            </select>
          </label>

          <div class="sd-modal-tabs">
            <button
              type="button"
              class="btn btn-xs"
              :class="seedForm.selectionType === 'random' ? 'btn-primary' : 'btn-secondary'"
              data-testid="seed-mode-random-btn"
              @click="seedForm.selectionType = 'random'"
            >
              Random Blind Seed
            </button>
            <button
              v-if="selectedChallengeVariants.length"
              type="button"
              class="btn btn-xs"
              :class="seedForm.selectionType === 'variant' ? 'btn-primary' : 'btn-secondary'"
              data-testid="seed-mode-variant-btn"
              @click="seedForm.selectionType = 'variant'"
            >
              Choose Variant ({{ selectedChallengeVariants.length }})
            </button>
            <button
              type="button"
              class="btn btn-xs"
              :class="seedForm.selectionType === 'seed' ? 'btn-primary' : 'btn-secondary'"
              data-testid="seed-mode-seed-btn"
              @click="seedForm.selectionType = 'seed'"
            >
              Replay Seed
            </button>
          </div>

          <p v-if="seedForm.selectionType === 'random'" class="sd-muted">
            Rolls a fresh random seed avoiding your immediately preceding archetype and keeps the hidden scenario blind until final evaluation completes.
          </p>

          <div v-else-if="seedForm.selectionType === 'variant'" class="sd-variant-picker-list">
            <label
              v-for="v in selectedChallengeVariants"
              :key="v.variant_id"
              class="sd-variant-option"
              :class="{ selected: seedForm.variantId === v.variant_id }"
              :data-testid="`seed-variant-option-${v.variant_id}`"
            >
              <input
                v-model="seedForm.variantId"
                type="radio"
                name="variant_id"
                :value="v.variant_id"
              />
              <div>
                <strong>{{ v.title }}</strong>
                <p v-if="v.focus_summary" class="sd-muted">{{ v.focus_summary }}</p>
              </div>
            </label>
          </div>

          <label v-else class="sd-field">
            <span>Scenario Seed (deterministic replay)</span>
            <input
              v-model="seedForm.briefSeed"
              type="text"
              class="form-input"
              maxlength="64"
              placeholder="e.g. a8f31c90 or any shared seed phrase"
              data-testid="seed-modal-seed-input"
            />
            <span class="sd-muted">
              Same challenge + same seed always picks the exact same hidden requirements profile while keeping the title blind until completion.
            </span>
          </label>

          <div class="sd-modal-actions">
            <button
              type="button"
              class="btn btn-secondary"
              @click="showSeedModal = false"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              data-testid="seed-modal-launch-btn"
              :disabled="store.startingSession || !selectedSeedChallenge"
            >
              <Loader2 v-if="store.startingSession" :size="14" class="spin" />
              <Sparkles v-else :size="14" />
              <span>Start Session</span>
            </button>
          </div>
        </form>
      </div>
    </div>
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
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.workspace-title-meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.sd-header-variant-btn {
  margin-left: auto;
  flex-shrink: 0;
}

.sd-seed-pill {
  font-family: var(--font-mono, monospace);
}

.sd-variant-pill {
  background-color: var(--primary-subtle);
  color: var(--text-primary);
  border-color: var(--primary);
}

.sd-blind-pill {
  font-style: italic;
}

.sd-variant-picker-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sd-variant-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm, 6px);
  background-color: var(--bg-input);
  cursor: pointer;
}

.sd-variant-option.selected {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.sd-variant-option strong {
  display: block;
  font-size: 13px;
  color: var(--text-main);
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
  line-height: 1.48;
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
  padding-left: 18px;
}

.sd-markdown-body :deep(code) {
  font-size: 0.85em;
  padding: 1px 4px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--border-color, #334155) 45%, transparent);
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
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-height: 68px;
  padding: 10px 16px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--primary-subtle);
}

.sd-review-metrics {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.sd-review-metric {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.sd-diagram-review-summary .sd-review-status-pill {
  flex: 0 0 auto;
}

.sd-diagram-review-summary .btn {
  margin-left: auto;
}

.sd-review-status-pill {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  white-space: nowrap;
  font-size: 12.5px;
  color: var(--text-main);
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

.sd-field-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.sd-selected-app-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--primary-subtle);
  border: 1px solid var(--primary);
  font-size: 12.5px;
}

.sd-selected-app-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.sd-app-search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.sd-search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-secondary);
  pointer-events: none;
}

.sd-app-search-input {
  padding-left: 30px;
}

.sd-app-picker-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 148px;
  overflow-y: auto;
  padding: 6px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
}

.sd-app-picker-item {
  width: 100%;
  text-align: left;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: var(--bg-surface);
  color: var(--text-main);
  cursor: pointer;
  transition: border-color var(--transition-fast), background-color var(--transition-fast);
}

.sd-app-picker-item:hover {
  border-color: var(--border-focus);
  background: var(--bg-surface-hover);
}

.sd-app-picker-item.selected {
  border-color: var(--primary);
  background: var(--primary-subtle);
}

.sd-app-picker-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.sd-app-picker-title {
  font-size: 12.5px;
  font-weight: 500;
}

.sd-app-picker-badges {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sd-stage-chip,
.sd-note-chip,
.sd-signal-pill {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--bg-input);
  color: var(--text-secondary);
}

.sd-note-chip {
  background: var(--status-interview-bg);
  color: var(--status-interview-text);
  border-color: var(--status-interview-border);
}

.sd-signal-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.sd-signal-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.sd-signal-pill {
  background: var(--primary-subtle);
  color: var(--text-primary);
  border-color: var(--primary);
}

.sd-inline-options {
  display: grid;
  grid-template-columns: minmax(140px, 190px) 1fr;
  gap: 12px;
  align-items: end;
}

.sd-checkbox-inline {
  padding-bottom: 8px;
}

.sd-duplicate-warning {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
  font-size: 12.5px;
}

.sd-duplicate-warning-body {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.sd-duplicate-warning-body p {
  margin: 4px 0 0;
  opacity: 0.92;
}

.sd-modal-actions-wrap {
  flex-wrap: wrap;
}

.sd-frontier-challenge-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
}

.sd-frontier-box-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12.5px;
}

.sd-frontier-prompt-ready {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sd-required-hint {
  font-style: normal;
  font-weight: 400;
  color: var(--text-secondary);
  font-size: 11.5px;
}

.form-input.is-invalid {
  border-color: var(--status-rejected-border);
}

.sd-inline-error {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
  font-size: 12.5px;
}

.sd-frontier-status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.sd-frontier-ready-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-primary);
}

.sd-frontier-callout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-elevated);
  font-size: 12.5px;
}

.sd-frontier-callout p {
  margin: 3px 0 0;
}

.sd-empty-picker {
  padding: 6px 4px;
  margin: 0;
}

.sd-design-stage {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sd-design-mode-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sd-design-mode-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sd-live-sync-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--status-offer-text);
  background: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
}

.sd-ledger-title-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.sd-studio-launch-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sd-studio-launch-intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.sd-studio-launch-intro .sd-helper-copy {
  flex: 1;
  min-width: 0;
}

.sd-launch-studio-btn {
  width: fit-content;
  flex-shrink: 0;
}

.sd-studio-revisions-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.sd-studio-revisions-block h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.sd-canvas-revisions-card,
.sd-canvas-revision-detail,
.sd-canvas-ref-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sd-canvas-rev-meta,
.sd-canvas-rev-actions,
.sd-ledger-head-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.sd-xp-lobby-pill,
.sd-xp-earned-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: var(--status-offer-text);
  background: var(--status-offer-bg);
  border: 1px solid var(--status-offer-border);
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

.sd-empty-review-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.sd-external-bridge-box {
  width: 100%;
  max-width: 680px;
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}

.sd-external-bridge-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.system-design-view.sd-embedded {
  width: 100%;
  max-width: none;
  height: 100%;
  min-height: 0;
  margin: 0;
  padding: 8px 12px;
  gap: 8px;
  overflow: auto;
  font-size: 14px;
}

.system-design-view.sd-embedded.sd-session-active {
  overflow: hidden;
}

.sd-session-active .sd-card {
  min-height: 0;
  padding: 12px;
  gap: 10px;
}

.sd-session-active .sd-workspace-header {
  flex: 0 0 auto;
  padding: 8px 12px;
  gap: 6px;
}

.sd-session-active .workspace-compact-top {
  align-items: center;
  flex-wrap: nowrap;
  gap: 8px;
}

.sd-session-active .workspace-title-block {
  min-width: 0;
}

.sd-session-active .workspace-title-meta-row {
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}

.sd-session-active .workspace-title-block h1 {
  max-width: min(30vw, 360px);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sd-session-active .sd-tag,
.sd-session-active .badge {
  flex-shrink: 0;
  font-size: 12px;
}

.sd-session-active .sd-header-variant-btn {
  min-height: 40px;
}

.sd-session-active .stage-stepper {
  gap: 6px;
}

.sd-session-active .stage-step-btn {
  min-height: 44px;
  padding: 6px 8px;
}

.sd-session-active .sd-task-banner {
  min-height: 44px;
}

.sd-session-active .sd-task-banner.is-processing {
  flex: 0 0 44px;
  min-height: 44px;
  padding: 4px 10px;
  overflow: hidden;
}

.sd-session-active .sd-task-banner-info,
.sd-session-active .sd-task-banner-copy,
.sd-session-active .sd-task-banner strong {
  min-width: 0;
}

.sd-session-active .sd-task-banner strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sd-session-active .sd-task-banner-actions .btn {
  min-height: 40px;
}

.sd-session-active > .sd-two-col,
.sd-session-active > .sd-design-stage,
.sd-session-active > .sd-review-stage,
.sd-session-active > .sd-evaluation-stage {
  flex: 1;
  min-height: 0;
}

.sd-session-active .sd-two-col {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  overflow: hidden;
}

.sd-session-active .sd-two-col > .sd-card {
  height: 100%;
  min-height: 0;
}

.sd-session-active .sd-chat-panel,
.sd-session-active .sd-ledger-panel {
  overflow: hidden;
}

.sd-session-active .sd-transcript-list {
  min-height: 0;
  max-height: none;
}

.sd-session-active .sd-chat-input-bar {
  flex: 0 0 auto;
}

.sd-session-active .sd-chat-input {
  min-height: 44px;
  font-size: 14px;
}

.sd-session-active .btn-input-icon,
.sd-session-active .btn-input-send {
  width: 44px;
  height: 44px;
}

.sd-session-active .sd-ledger-panel {
  display: flex;
  flex-direction: column;
}

.sd-session-active .sd-ledger-panel > .sd-card-header {
  flex: 0 0 auto;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.sd-session-active .sd-ledger-head-actions .btn {
  min-height: 40px;
}

.sd-session-active .sd-ledger-sections {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  gap: 0;
}

.sd-ledger-section {
  border-bottom: 1px solid var(--border-subtle);
}

.sd-ledger-section summary {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  cursor: pointer;
  list-style: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.sd-ledger-section summary::-webkit-details-marker,
.sd-ledger-section summary::marker {
  display: none;
  content: '';
}

.sd-ledger-section summary::before,
.sd-review-disclosure summary::before {
  content: '›';
  color: var(--text-muted);
}

.sd-ledger-section[open] summary::before,
.sd-review-disclosure[open] summary::before {
  transform: rotate(90deg);
}

.sd-ledger-preview {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-muted);
  font-size: 12.5px;
  font-weight: 400;
}

.sd-count-pill {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: var(--primary-subtle);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
}

.sd-ledger-section .sd-field {
  padding: 0 8px 10px 20px;
  font-size: 12.5px;
}

.sd-ledger-section .form-textarea {
  min-height: 40px;
  field-sizing: content;
  max-height: 150px;
  font-size: 14px;
}

.sd-session-active .sd-ledger-actions {
  flex: 0 0 auto;
  justify-content: flex-end;
  margin-bottom: 80px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.sd-session-active .sd-ledger-actions .btn {
  min-height: 44px;
}

.sd-session-active .sd-design-stage,
.sd-session-active .sd-review-stage {
  overflow: hidden;
}

.sd-session-active .sd-design-stage > .sd-two-col {
  height: 100%;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
}

.sd-session-active .sd-design-stage .sd-card {
  overflow: hidden;
}

.sd-session-active .sd-studio-launch-card,
.sd-session-active .sd-upload-card {
  min-height: 0;
}

.sd-session-active .sd-studio-launch-card .sd-helper-copy {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  margin: 0;
  line-height: 1.4;
}

.sd-session-active .sd-studio-revisions-block {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.sd-session-active .sd-revisions-header {
  flex: 0 0 auto;
}

.sd-revision-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.sd-revision-row {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
}

.sd-revision-select {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
  min-height: 52px;
  padding: 8px 16px;
  text-align: left;
  flex-wrap: wrap;
}

.sd-revision-disclosure {
  min-width: 0;
  border-top: 1px solid var(--border-subtle);
}

.sd-revision-disclosure summary,
.sd-reference-components summary {
  min-height: 48px;
  padding: 12px 16px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 12.5px;
}

.sd-revision-preview {
  display: inline-block;
  max-width: 75%;
  margin-left: 8px;
  overflow: hidden;
  color: var(--text-muted);
  text-overflow: ellipsis;
  vertical-align: bottom;
  white-space: nowrap;
}

.sd-revision-disclosure > .challenge-tags,
.sd-revision-disclosure > p,
.sd-revision-disclosure > .sd-preview-img {
  margin-right: 16px;
  margin-left: 16px;
}

.sd-revision-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  min-height: 68px;
  padding: 8px 16px;
  border-top: 1px solid var(--border-subtle);
}

.sd-revision-action-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.sd-web-search-row {
  flex: 0 1 auto;
  justify-content: flex-start;
  min-height: 40px;
  white-space: nowrap;
  font-size: 12.5px;
}

.sd-web-search-row input {
  width: 16px;
  height: 16px;
}

.sd-session-active .sd-revision-actions .btn,
.sd-session-active .sd-launch-studio-btn {
  min-height: 44px;
}

.sd-session-active .sd-upload-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
}

.sd-session-active .sd-upload-card .sd-helper-copy {
  margin: 0;
  line-height: 1.4;
}

.sd-session-active .sd-dropzone {
  flex: 0 0 108px;
  min-height: 108px;
  padding: 8px;
  gap: 6px;
}

.sd-session-active .sd-dropzone > svg {
  width: 20px;
  height: 20px;
}

.sd-session-active .sd-dropzone p {
  margin: 0;
}

.sd-browse-files {
  position: relative;
  min-height: 40px;
  cursor: pointer;
}

.diagram-file-input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
}

.sd-session-active .sd-staged-preview {
  min-height: 0;
  overflow: auto;
}

.sd-session-active .sd-staged-preview .sd-preview-img {
  max-height: 160px;
}

.sd-upload-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
  margin-bottom: 80px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.sd-upload-footer .sd-field {
  font-size: 12.5px;
}

.sd-upload-footer .form-input {
  min-height: 44px;
  font-size: 14px;
}

.sd-upload-footer > .btn {
  min-height: 44px;
}

.sd-session-active .review-banner {
  flex: 0 0 auto;
  align-items: stretch;
  gap: 8px;
  flex-direction: column;
}

.sd-session-active .review-banner-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sd-session-active .review-banner-text {
  min-width: 0;
  width: 100%;
}

.sd-session-active .review-banner-text h3 {
  margin: 0;
}

.sd-critique-copy {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.5;
}

.sd-session-active .review-banner-actions {
  justify-content: flex-end;
  align-items: center;
  margin-left: 0;
}

.sd-session-active .review-banner-actions .btn {
  min-height: 44px;
}

.sd-session-active .sd-review-grid {
  flex: 1;
  min-height: 0;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 12px;
  overflow: hidden;
}

.sd-review-column {
  min-height: 0;
  overflow-y: auto;
}

.sd-review-column-left {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0 12px;
  border: var(--card-border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.sd-review-group {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.sd-review-group:last-child {
  border-bottom: 0;
}

.sd-session-active .sd-review-group {
  padding: 4px 0;
}

.sd-session-active .sd-review-group > summary {
  position: relative;
  min-height: 44px;
  padding-left: 16px;
  cursor: pointer;
  list-style: none;
}

.sd-session-active .sd-review-group > summary::before,
.sd-review-disclosure summary::before,
.sd-eval-takeaway summary::before,
.sd-rubric-item summary::before {
  position: absolute;
  left: 0;
  color: var(--text-muted);
  content: '›';
  transition: transform var(--transition-fast);
}

.sd-session-active .sd-review-group[open] > summary::before,
.sd-review-disclosure[open] summary::before,
.sd-eval-takeaway[open] summary::before,
.sd-rubric-item[open] summary::before {
  transform: rotate(90deg);
}

.sd-session-active .sd-review-group > summary::-webkit-details-marker,
.sd-session-active .sd-review-group > summary::marker {
  display: none;
  content: '';
}

.sd-session-active .sd-review-preview {
  margin: 0;
  padding: 0 8px 10px 24px;
  overflow: hidden;
  color: var(--text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sd-session-active .sd-review-group[open] > .sd-review-preview {
  display: none;
}

.sd-review-group-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sd-review-group-heading h3 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 14px;
}

.sd-review-group .sd-bullet-list,
.sd-review-column-right .sd-bullet-list {
  margin: 6px 0 0;
  font-size: 14px;
}

.sd-session-active .sd-review-group .sd-bullet-list,
.sd-session-active .sd-review-column-right .sd-bullet-list {
  padding-left: 22px;
  padding-right: 8px;
  line-height: 1.5;
  gap: 8px;
}

.sd-session-active .sd-review-expanded-content {
  padding: 0 8px 8px 24px;
}

.sd-review-column-right {
  gap: 0;
}

.sd-review-column-right .sd-card-header {
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.sd-review-disclosure {
  padding: 0 12px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.sd-review-disclosure summary {
  position: relative;
  padding-left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  cursor: pointer;
  list-style: none;
  font-weight: 600;
}

.sd-review-disclosure summary::-webkit-details-marker,
.sd-review-disclosure summary::marker {
  display: none;
  content: '';
}

.sd-review-disclosure summary span:first-of-type {
  flex: 1;
}

.sd-review-column-right > .sd-muted {
  padding: 10px 12px;
}

.sd-session-active .sd-defence-sidebar {
  overflow: hidden;
}

.sd-session-active .sd-sidebar-top {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  gap: 8px;
}

.sd-reference-version-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12.5px;
  white-space: nowrap;
}

.sd-session-active .sd-canvas-ref-box {
  gap: 4px;
}

.sd-reference-components {
  max-height: 120px;
  overflow: auto;
}

.sd-session-active .sd-sidebar-notes {
  min-height: 0;
}

.sd-session-active .sd-sidebar-notes h4 {
  margin: 0;
}

.sd-session-active .sd-sidebar-notes .sd-bullet-list {
  gap: 0;
  padding: 0;
  list-style: none;
}

.sd-session-active .sd-sidebar-notes .sd-bullet-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.sd-session-active .sd-sidebar-actions {
  flex: 0 0 auto;
  max-height: 42%;
  overflow-y: auto;
  margin-bottom: 80px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
  gap: 6px;
}

.sd-session-active .sd-sidebar-actions > .btn {
  min-height: 44px;
}

.sd-session-active .sd-external-bridge-box {
  margin-top: 0;
}

.sd-session-active :is(button, summary, input, textarea, select):focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 2px;
}

@media (max-width: 900px) {
  .system-design-view.sd-embedded.sd-session-active {
    overflow-y: auto;
  }

  .sd-session-active .sd-studio-launch-intro {
    align-items: flex-start;
    flex-direction: column;
  }

  .sd-session-active .sd-revision-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .sd-session-active .sd-revision-action-buttons {
    flex-wrap: wrap;
  }

  .sd-session-active .sd-diagram-review-summary {
    align-items: flex-start;
    flex-direction: column;
  }

  .sd-session-active .sd-web-search-row {
    flex: 1 1 100%;
    justify-content: flex-start;
  }

  .sd-session-active .sd-diagram-review-summary .btn {
    margin-left: 0;
  }

  .sd-session-active .workspace-compact-top,
  .sd-session-active .workspace-title-meta-row {
    flex-wrap: wrap;
  }

  .sd-session-active > .sd-two-col,
  .sd-session-active .sd-design-stage > .sd-two-col,
  .sd-session-active .sd-review-grid {
    grid-template-columns: minmax(0, 1fr);
    overflow: auto;
  }

  .sd-session-active > .sd-two-col > .sd-card,
  .sd-session-active .sd-design-stage > .sd-two-col > .sd-card {
    min-height: 420px;
  }
}

.sd-session-active .sd-evaluation-stage {
  gap: 8px;
  overflow: hidden;
}

.sd-eval-subnav {
  flex: 0 0 auto;
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.sd-evaluation-content {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  gap: 12px;
}

.sd-evaluation-content > .sd-card {
  min-height: 0;
  overflow-y: auto;
}

.sd-session-active .sd-eval-hero {
  flex: 0 0 auto;
  gap: 12px;
  padding: 10px 12px;
}

.sd-session-active .sd-evaluation-stage > .sd-frontier-card {
  flex: 1;
  min-height: 0;
  padding-bottom: 56px;
  overflow-y: auto;
}

.sd-session-active .sd-eval-rubric-panel {
  padding-bottom: 80px;
  overflow: hidden;
}

.sd-session-active .eval-score-box {
  padding: 8px 14px;
}

.sd-session-active .eval-score-value {
  font-size: 30px;
}

.sd-eval-highlights,
.sd-eval-rubric-panel {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.sd-eval-highlights .sd-card-header,
.sd-eval-rubric-panel .sd-card-header {
  flex: 0 0 auto;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.sd-eval-takeaway,
.sd-rubric-item {
  padding: 0 12px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.sd-eval-takeaway summary,
.sd-rubric-item summary {
  position: relative;
  display: grid;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding-left: 16px;
  cursor: pointer;
  list-style: none;
}

.sd-eval-takeaway summary {
  grid-template-columns: minmax(120px, auto) minmax(0, 1fr);
}

.sd-rubric-item summary {
  grid-template-columns: minmax(0, 1fr) auto;
}

.sd-eval-takeaway summary::-webkit-details-marker,
.sd-eval-takeaway summary::marker,
.sd-rubric-item summary::-webkit-details-marker,
.sd-rubric-item summary::marker {
  display: none;
  content: '';
}

.sd-eval-takeaway-title,
.sd-rubric-item summary > strong {
  color: var(--text-main);
  font-weight: 600;
}

.sd-eval-preview,
.sd-rubric-preview {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sd-eval-takeaway[open] .sd-eval-preview,
.sd-rubric-item[open] .sd-rubric-preview {
  display: none;
}

.sd-eval-takeaway .sd-bullet-list {
  margin: 0;
  padding: 0 8px 4px 22px;
  line-height: 1.5;
}

.sd-rubric-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.sd-rubric-item summary > .badge {
  justify-self: end;
}

.sd-rubric-evidence {
  display: grid;
  gap: 10px;
  padding: 0 8px 8px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.sd-rubric-evidence p {
  margin: 0;
}

.sd-rubric-evidence strong {
  display: block;
  margin-bottom: 2px;
  color: var(--text-main);
  font-size: 12.5px;
}

.sd-external-defence-dialog {
  max-width: 680px;
}

.sd-external-defence-dialog .sd-card-header h2 {
  margin: 0;
  font-size: 18px;
}

.sd-external-defence-dialog .sd-external-bridge-box {
  width: 100%;
  max-width: none;
  margin: 0;
  border: 0;
  background: transparent;
}

.sd-external-defence-dialog :is(textarea, button) {
  min-height: 44px;
}

@media (max-width: 900px) {
  .sd-session-active .review-banner-actions {
    justify-content: flex-start;
  }

  .sd-evaluation-stage {
    overflow-y: auto;
  }

  .sd-evaluation-content {
    flex: 0 0 auto;
    grid-template-columns: minmax(0, 1fr);
  }

  .sd-evaluation-content > .sd-card {
    max-height: 55dvh;
  }
}
</style>
