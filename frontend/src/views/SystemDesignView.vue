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
  extraContext: '',
})
const appFilterStage = ref('ACTIVE')
const appSearchQuery = ref('')
const challengeImportText = ref('')
const challengePromptCopied = ref(false)
const duplicateChallengeWarning = ref(null)

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
  }
)
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
    uiStore.showToast(
      'Enter a topic, extra focus notes, or pick a tracked application to tailor from.',
      'error'
    )
    return
  }
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
    uiStore.showToast(
      'Enter a topic, extra focus notes, or pick a tracked application first.',
      'error'
    )
    return
  }
  try {
    await store.prepareChallengeFrontierPrompt(_buildChallengeTailorPayload(false))
    challengePromptCopied.value = false
    uiStore.showToast(
      'Frontier challenge prompt ready! Copy or download for Claude, ChatGPT, or Gemini.',
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
              <span>Tailored AI / Frontier</span>
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
              <span>Topic / Scenario Focus</span>
              <input
                v-model="generateForm.topic"
                type="text"
                class="form-input"
                data-testid="generate-topic-input"
                placeholder="Optional if an application is selected (e.g., Real-time fraud scoring pipeline)"
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

            <div
              v-if="duplicateChallengeWarning"
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
                :disabled="store.generatingChallenge || store.importingChallenge"
                @click="handleCreateAnywayDuplicate"
              >
                Create Anyway
              </button>
            </div>

            <p class="sd-muted">
              Both Local AI and Frontier Chat generate 3 distinct requirement variants and guard against duplicating existing challenges.
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

            <div class="sd-frontier-challenge-box" data-testid="frontier-challenge-panel">
              <div class="sd-frontier-box-header">
                <strong>Frontier Chat Mode (Claude / ChatGPT / Gemini)</strong>
                <span class="sd-muted">Prepare the prompt above, run it in any chat UI, and paste the JSON response below.</span>
              </div>

              <div v-if="store.challengeFrontierPrompt" class="sd-frontier-prompt-ready">
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
                <textarea
                  readonly
                  rows="5"
                  class="form-input sd-packet-preview"
                  data-testid="frontier-challenge-prompt-preview"
                  :value="store.challengeFrontierPrompt.markdown_prompt"
                ></textarea>
              </div>

              <label class="sd-field">
                <span>Import Challenge JSON from Frontier Chat</span>
                <textarea
                  v-model="challengeImportText"
                  rows="4"
                  class="form-input sd-packet-preview"
                  data-testid="import-frontier-challenge-input"
                  placeholder="Paste the JSON response (or ```json fenced block) from Claude, ChatGPT, or Gemini..."
                ></textarea>
              </label>

              <div class="sd-modal-actions">
                <button
                  type="button"
                  class="btn btn-primary btn-sm"
                  data-testid="import-frontier-challenge-submit-btn"
                  :disabled="store.importingChallenge || !challengeImportText.trim()"
                  @click="handleImportFrontierChallenge(false)"
                >
                  <Loader2 v-if="store.importingChallenge" :size="13" class="spin" />
                  <Upload v-else :size="13" />
                  <span>Import Challenge JSON</span>
                </button>
              </div>
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
            </div>
            <p class="sd-muted">{{ activeSession.challenge?.initial_prompt }}</p>
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
              <span>Confirmed / Baseline Assumptions (one per line)</span>
              <textarea
                v-model="ledgerForm.assumptionsText"
                class="form-textarea"
                rows="2"
                placeholder="e.g., Assume single-region writes unless specified otherwise"
              />
            </label>

            <label class="sd-field">
              <span>Unresolved Questions (one per line)</span>
              <textarea
                v-model="ledgerForm.unresolvedQuestionsText"
                class="form-textarea"
                rows="2"
                placeholder="e.g., Custom domain SSL provisioning?"
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

.sd-empty-picker {
  padding: 6px 4px;
  margin: 0;
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
