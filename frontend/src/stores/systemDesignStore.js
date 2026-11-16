import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { IntakeAPI, SystemDesignAPI } from '../api/endpoints'
import { useQueueStore } from './queueStore'

export const useSystemDesignStore = defineStore('systemDesign', () => {
  const challenges = ref([])
  const diagramCatalog = ref({ categories: [], blocks: [] })
  const sessions = ref([])
  const activeSession = ref(null)

  const loadingChallenges = ref(false)
  const loadingSessions = ref(false)
  const loadingSession = ref(false)
  const startingSession = ref(false)
  const creatingChallenge = ref(false)
  const generatingChallenge = ref(false)
  const updatingChallenge = ref(false)
  const resettingChallenges = ref(false)
  const sendingRequirements = ref(false)
  const extractingLedger = ref(false)
  const revealingRequirements = ref(false)
  const savingLedger = ref(false)
  const uploadingDiagram = ref(false)
  const loadingDiagramHint = ref(false)
  const sendingCoachChat = ref(false)
  const reviewingDiagram = ref(false)
  const sendingDefence = ref(false)
  const evaluatingSession = ref(false)
  const loadingFrontierPacket = ref(false)
  const importingEvaluation = ref(false)
  const frontierPacket = ref(null)
  const loadingChallengePrompt = ref(false)
  const importingChallenge = ref(false)
  const challengeFrontierPrompt = ref(null)
  const lastTopologyFeedback = ref(null)
  const expectedPaths = ref([])
  const referenceActions = ref([])
  const studyNotes = ref({})
  const frontierCoachPrompt = ref(null)
  const frontierReviewPrompt = ref(null)
  const frontierDefencePrompt = ref(null)
  const nextConnectionHint = ref(null)
  const coachMessages = ref([])
  const suggestedCoachActions = ref([])
  const error = ref(null)

  const activeLedger = computed(() => activeSession.value?.requirements_ledger || {})
  const activeDiagrams = computed(() => activeSession.value?.diagrams_metadata || [])
  const activeReviews = computed(() => activeSession.value?.architecture_reviews || [])
  const activeFinalEvaluation = computed(() => activeSession.value?.final_evaluation || null)
  const capabilitiesChecklist = computed(
    () =>
      activeSession.value?.capabilities_checklist ||
      lastTopologyFeedback.value?.capability_checks ||
      []
  )
  const isActiveSessionCoached = computed(() => {
    const s = activeSession.value
    if (!s) return false
    const guidance = s.diagram_guidance || {}
    if (s.final_evaluation?.assistance_mode === 'COACHED') return true
    if (s.final_evaluation?.assistance_mode === 'SOLO') return false
    return Boolean(
      guidance.is_coached ||
        guidance.revealed_all_bank ||
        guidance.requirements_revealed ||
        Number(guidance.hints_used_count || 0) > 0 ||
        (Array.isArray(guidance.coach_messages) && guidance.coach_messages.length > 0) ||
        (s.requirements_transcript || []).some((t) => t?.assisted) ||
        (s.defence_transcript || []).some((t) => t?.assisted)
    )
  })
  const sessionGamificationStats = computed(() => {
    const list = sessions.value || []
    const completed = list.filter((s) => s.stage === 'COMPLETED')
    let totalXp = 0
    let soloCount = 0
    for (const s of completed) {
      const ev = s.final_evaluation || {}
      const coached =
        ev.assistance_mode === 'COACHED' ||
        Boolean(
          s.diagram_guidance?.is_coached ||
            s.diagram_guidance?.revealed_all_bank ||
            s.diagram_guidance?.requirements_revealed
        )
      if (!coached && ev.assistance_mode !== 'COACHED') soloCount += 1
      totalXp += Number(ev.xp_earned ?? (coached ? 100 : 150))
    }
    const sortedCompleted = [...completed].sort((a, b) =>
      String(b.updated_at || b.created_at || '').localeCompare(
        String(a.updated_at || a.created_at || '')
      )
    )
    return {
      totalXp,
      completedCount: sortedCompleted.length,
      soloCount,
      streakCount: sortedCompleted.length,
    }
  })
  const reviewFixChecklist = computed(() => {
    const reviews = activeReviews.value || []
    if (!reviews.length) return []
    const latest = reviews[reviews.length - 1] || {}
    const items = []
    for (const text of latest.missing_components || []) {
      items.push({ id: `missing-${items.length}`, category: 'Missing', severity: 'error', text })
    }
    for (const text of latest.requirement_gaps || []) {
      items.push({ id: `gap-${items.length}`, category: 'Requirement Gap', severity: 'warning', text })
    }
    for (const text of latest.bottlenecks_and_spofs || []) {
      items.push({ id: `spof-${items.length}`, category: 'SPOF / Bottleneck', severity: 'warning', text })
    }
    for (const text of latest.unnecessary_complexity || []) {
      items.push({ id: `complexity-${items.length}`, category: 'Complexity', severity: 'info', text })
    }
    return items
  })

  function _syncCoachStateFromSession(session) {
    const guidance = session?.diagram_guidance || {}
    if (Array.isArray(guidance.expected_paths)) {
      expectedPaths.value = guidance.expected_paths
    } else if (!session) {
      expectedPaths.value = []
    }
    if (session?.study_notes && Object.keys(session.study_notes).length) {
      studyNotes.value = session.study_notes
    } else if (!session) {
      studyNotes.value = {}
    }
    if (guidance.last_topology_feedback) {
      lastTopologyFeedback.value = guidance.last_topology_feedback
    } else if (!session) {
      lastTopologyFeedback.value = null
    }
    if (Array.isArray(guidance.coach_messages)) {
      coachMessages.value = guidance.coach_messages
      const lastCoach = [...guidance.coach_messages]
        .reverse()
        .find((m) => m?.role === 'coach' && Array.isArray(m?.actions))
      if (lastCoach) {
        suggestedCoachActions.value = lastCoach.actions
      }
    } else if (!session) {
      coachMessages.value = []
      suggestedCoachActions.value = []
    }
  }

  function _syncSessionInList(session) {
    if (!session || !session.id) return
    if (activeSession.value?.id !== session.id) {
      frontierPacket.value = null
      frontierCoachPrompt.value = null
      frontierReviewPrompt.value = null
      frontierDefencePrompt.value = null
      lastTopologyFeedback.value = null
      expectedPaths.value = []
      referenceActions.value = []
      studyNotes.value = {}
      nextConnectionHint.value = null
      coachMessages.value = []
      suggestedCoachActions.value = []
    }
    activeSession.value = session
    _syncCoachStateFromSession(session)
    const idx = sessions.value.findIndex((s) => s.id === session.id)
    if (idx !== -1) {
      const updated = [...sessions.value]
      updated[idx] = session
      sessions.value = updated
    } else {
      sessions.value = [session, ...sessions.value]
    }
  }

  async function fetchDiagramCatalog() {
    try {
      const res = await SystemDesignAPI.getDiagramCatalog()
      if (res?.data?.blocks?.length) {
        diagramCatalog.value = res.data
      }
      return diagramCatalog.value
    } catch {
      return diagramCatalog.value
    }
  }

  async function fetchChallenges(params = {}) {
    loadingChallenges.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.listChallenges(params)
      challenges.value = res.data || []
      return challenges.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingChallenges.value = false
    }
  }

  async function createChallenge(payload) {
    creatingChallenge.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.createChallenge(payload)
      const created = res.data
      challenges.value = [...challenges.value, created]
      return created
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      creatingChallenge.value = false
    }
  }

  async function generateChallenge(payload) {
    generatingChallenge.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.generateChallenge(payload)
      const created = res.data
      challenges.value = [...challenges.value, created]
      return created
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      generatingChallenge.value = false
    }
  }

  async function prepareChallengeFrontierPrompt(payload) {
    loadingChallengePrompt.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.prepareFrontierChallengePrompt(payload)
      challengeFrontierPrompt.value = res.data
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingChallengePrompt.value = false
    }
  }

  async function importFrontierChallenge(payload) {
    importingChallenge.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.importFrontierChallenge(payload)
      const created = res.data
      challenges.value = [...challenges.value, created]
      return created
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      importingChallenge.value = false
    }
  }

  async function updateChallenge(challengeId, payload) {
    updatingChallenge.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.updateChallenge(challengeId, payload)
      const updated = res.data
      challenges.value = challenges.value.map((c) => (c.id === challengeId ? updated : c))
      if (activeSession.value?.challenge?.id === challengeId) {
        activeSession.value = {
          ...activeSession.value,
          challenge: updated,
        }
      }
      return updated
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      updatingChallenge.value = false
    }
  }

  async function resetDefaultChallenges() {
    resettingChallenges.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.resetDefaultChallenges()
      challenges.value = res.data || []
      return challenges.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      resettingChallenges.value = false
    }
  }

  async function deleteChallenge(challengeId) {
    error.value = null
    try {
      await SystemDesignAPI.deleteChallenge(challengeId)
      challenges.value = challenges.value.filter((c) => c.id !== challengeId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchSessions(params = {}) {
    loadingSessions.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.listSessions(params)
      sessions.value = res.data || []
      return sessions.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingSessions.value = false
    }
  }

  async function startSession(
    challengeId,
    mode = 'ADAPTIVE',
    applicationId = null,
    options = {}
  ) {
    startingSession.value = true
    error.value = null
    try {
      const cleanedSeed = options?.briefSeed ? String(options.briefSeed).trim() : ''
      const cleanedVariant = options?.variantId ? String(options.variantId).trim() : ''
      const payload = {
        challenge_id: challengeId,
        mode,
        ...(applicationId ? { application_id: applicationId } : {}),
        ...(cleanedSeed ? { brief_seed: cleanedSeed } : {}),
        ...(cleanedVariant ? { variant_id: cleanedVariant } : {}),
      }
      const res = await SystemDesignAPI.startSession(payload)
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      startingSession.value = false
    }
  }

  let _pollToken = 0
  const ACTIVE_QUEUE_STATUSES = new Set(['QUEUED', 'RUNNING', 'PROCESSING'])

  function _refreshQueueStore() {
    try {
      const queueStore = useQueueStore()
      Promise.resolve(queueStore.fetchTasks()).catch(() => {})
    } catch {
      // Queue store may not be mounted in isolated unit tests
    }
  }

  async function _awaitActiveTaskCompletion(session, { silent = false } = {}) {
    if (!session?.active_task_id || !ACTIVE_QUEUE_STATUSES.has(session.active_task_status)) {
      return session
    }
    const taskId = session.active_task_id
    const sessionId = session.id
    const token = ++_pollToken
    _refreshQueueStore()

    for (let attempt = 0; attempt < 600; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 450))
      if (token !== _pollToken || activeSession.value?.id !== sessionId) {
        return activeSession.value
      }
      let task = null
      try {
        const taskRes = await IntakeAPI.getEvaluation(taskId)
        task = taskRes?.data
      } catch {
        continue
      }
      if (!task) continue
      if (activeSession.value?.id === sessionId) {
        const cp = task.result_json?._checkpoint || {}
        const telemetry = cp.provider_telemetry || {}
        const providerLabel =
          telemetry.last_used_provider || telemetry.primary_provider || null
        activeSession.value = {
          ...activeSession.value,
          active_task_id: task.id,
          active_task_status: task.status,
          active_task_stage: task.stage,
          active_task_type: task.task_type,
          active_task_error: task.error_message || null,
          active_task_attempt_count: Number(cp.attempt_count || 0),
          active_task_completed_steps: Array.isArray(cp.completed_steps)
            ? cp.completed_steps
            : [],
          active_task_provider: providerLabel,
        }
      }
      if (task.status === 'COMPLETED') {
        const fresh = await SystemDesignAPI.getSession(sessionId)
        _syncSessionInList(fresh.data)
        _refreshQueueStore()
        return fresh.data
      }
      if (task.status === 'FAILED' || task.status === 'CANCELLED') {
        const fresh = await SystemDesignAPI.getSession(sessionId)
        _syncSessionInList(fresh.data)
        _refreshQueueStore()
        const msg = task.error_message || `Background task ${task.status.toLowerCase()}`
        error.value = msg
        if (!silent) {
          throw new Error(msg)
        }
        return fresh.data
      }
    }
    const timeoutMsg = 'Background AI task timed out waiting for completion. Check the Queue view for progress.'
    error.value = timeoutMsg
    if (!silent) throw new Error(timeoutMsg)
    return activeSession.value
  }

  async function loadSession(sessionId) {
    _pollToken++
    reviewingDiagram.value = false
    evaluatingSession.value = false
    loadingSession.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.getSession(sessionId)
      _syncSessionInList(res.data)
      if (res.data?.active_task_id && ACTIVE_QUEUE_STATUSES.has(res.data.active_task_status)) {
        const isReview = res.data.active_task_type === 'SYSTEM_DESIGN_REVIEW'
        const isEval = res.data.active_task_type === 'SYSTEM_DESIGN_EVALUATION'
        if (isReview) reviewingDiagram.value = true
        if (isEval) evaluatingSession.value = true
        _awaitActiveTaskCompletion(res.data, { silent: true })
          .catch(() => {})
          .finally(() => {
            if (isReview) reviewingDiagram.value = false
            if (isEval) evaluatingSession.value = false
          })
      }
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingSession.value = false
    }
  }

  async function deleteSession(sessionId) {
    error.value = null
    try {
      await SystemDesignAPI.deleteSession(sessionId)
      sessions.value = sessions.value.filter((s) => s.id !== sessionId)
      if (activeSession.value?.id === sessionId) {
        _pollToken++
        activeSession.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  function clearActiveSession() {
    _pollToken++
    reviewingDiagram.value = false
    evaluatingSession.value = false
    activeSession.value = null
    frontierPacket.value = null
    lastTopologyFeedback.value = null
    expectedPaths.value = []
    nextConnectionHint.value = null
    coachMessages.value = []
    suggestedCoachActions.value = []
  }

  async function updateMode(mode) {
    if (!activeSession.value) return null
    error.value = null
    try {
      const res = await SystemDesignAPI.updateMode(activeSession.value.id, mode)
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function sendRequirementsMessage(message, requestHint = false) {
    if (!activeSession.value) return null
    sendingRequirements.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.sendRequirementsMessage(
        activeSession.value.id,
        message,
        requestHint
      )
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      sendingRequirements.value = false
    }
  }

  async function extractRequirementsLedger() {
    if (!activeSession.value) return null
    extractingLedger.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.extractRequirementsLedger(activeSession.value.id)
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      extractingLedger.value = false
    }
  }

  async function revealRequirementsLedger(lockAndProceed = false) {
    if (!activeSession.value) return null
    revealingRequirements.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.revealRequirementsLedger(
        activeSession.value.id,
        lockAndProceed
      )
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      revealingRequirements.value = false
    }
  }

  async function updateRequirementsLedger(ledgerPayload) {
    if (!activeSession.value) return null
    savingLedger.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.updateRequirementsLedger(
        activeSession.value.id,
        ledgerPayload
      )
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      savingLedger.value = false
    }
  }

  async function uploadDiagram(file, notes = '') {
    if (!activeSession.value) return null
    uploadingDiagram.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('notes', notes || '')
      const res = await SystemDesignAPI.uploadDiagram(activeSession.value.id, formData)
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      uploadingDiagram.value = false
    }
  }

  async function submitCanvasDiagram(payload) {
    if (!activeSession.value) return null
    uploadingDiagram.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.submitCanvasDiagram(activeSession.value.id, payload)
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      uploadingDiagram.value = false
    }
  }

  async function loadDiagramFlow(version) {
    if (!activeSession.value) return null
    error.value = null
    try {
      const res = await SystemDesignAPI.getDiagramFlow(activeSession.value.id, version)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function requestDiagramHint(
    hintMode = 'next_component',
    currentNodes = [],
    currentEdges = [],
    currentNotes = '',
    cloudProvider = 'generic'
  ) {
    if (!activeSession.value) return null
    loadingDiagramHint.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.requestDiagramHint(activeSession.value.id, {
        hint_mode: hintMode,
        cloud_provider: cloudProvider || 'generic',
        current_nodes: currentNodes,
        current_edges: currentEdges,
        current_notes: currentNotes || '',
      })
      if (Array.isArray(res.data?.expected_paths)) {
        expectedPaths.value = res.data.expected_paths
      }
      if (Array.isArray(res.data?.reference_actions)) {
        referenceActions.value = res.data.reference_actions
      }
      if (res.data?.study_notes && Object.keys(res.data.study_notes).length) {
        studyNotes.value = res.data.study_notes
      }
      if (res.data?.topology_feedback) {
        lastTopologyFeedback.value = res.data.topology_feedback
      }
      if (res.data?.next_connection_hint) {
        nextConnectionHint.value = res.data.next_connection_hint
      } else if (hintMode !== 'next_connection' && hintMode !== 'check_topology') {
        nextConnectionHint.value = null
      }
      if (res.data?.session) {
        _syncSessionInList(res.data.session)
      }
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingDiagramHint.value = false
    }
  }

  async function sendDiagramCoachMessage(
    message,
    currentNodes = [],
    currentEdges = [],
    currentNotes = '',
    cloudProvider = 'generic'
  ) {
    if (!activeSession.value) return null
    sendingCoachChat.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.sendDiagramCoachMessage(activeSession.value.id, {
        message,
        cloud_provider: cloudProvider || 'generic',
        current_nodes: currentNodes,
        current_edges: currentEdges,
        current_notes: currentNotes || '',
      })
      if (Array.isArray(res.data?.expected_paths)) {
        expectedPaths.value = res.data.expected_paths
      }
      if (Array.isArray(res.data?.reference_actions)) {
        referenceActions.value = res.data.reference_actions
      }
      if (res.data?.study_notes && Object.keys(res.data.study_notes).length) {
        studyNotes.value = res.data.study_notes
      }
      if (res.data?.topology_feedback) {
        lastTopologyFeedback.value = res.data.topology_feedback
      }
      if (Array.isArray(res.data?.suggested_actions)) {
        suggestedCoachActions.value = res.data.suggested_actions
      }
      if (res.data?.session) {
        _syncSessionInList(res.data.session)
      }
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      sendingCoachChat.value = false
    }
  }

  async function reviewDiagram(diagramVersion = null, useWebSearch = false) {
    if (!activeSession.value) return null
    reviewingDiagram.value = true
    error.value = null
    try {
      const payload = {
        ...(diagramVersion ? { diagram_version: diagramVersion } : {}),
        use_web_search: Boolean(useWebSearch),
      }
      const res = await SystemDesignAPI.reviewDiagram(activeSession.value.id, payload)
      _syncSessionInList(res.data)
      return await _awaitActiveTaskCompletion(res.data)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      reviewingDiagram.value = false
    }
  }

  async function sendDefenceMessage(message, options = {}) {
    if (!activeSession.value) return null
    sendingDefence.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.sendDefenceMessage(activeSession.value.id, message, options)
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      sendingDefence.value = false
    }
  }

  async function evaluateSession() {
    if (!activeSession.value) return null
    evaluatingSession.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.evaluateSession(activeSession.value.id)
      _syncSessionInList(res.data)
      return await _awaitActiveTaskCompletion(res.data)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      evaluatingSession.value = false
    }
  }

  async function cancelActiveTask() {
    const taskId = activeSession.value?.active_task_id
    const sessionId = activeSession.value?.id
    if (!taskId || !sessionId) return null
    error.value = null
    _pollToken++
    await IntakeAPI.cancelEvaluation(taskId)
    reviewingDiagram.value = false
    evaluatingSession.value = false
    _refreshQueueStore()
    return await loadSession(sessionId)
  }

  async function retryActiveTask() {
    const taskId = activeSession.value?.active_task_id
    const sessionId = activeSession.value?.id
    const taskType = activeSession.value?.active_task_type
    if (!taskId || !sessionId) return null
    error.value = null
    const isReview = taskType === 'SYSTEM_DESIGN_REVIEW'
    const isEval = taskType === 'SYSTEM_DESIGN_EVALUATION'
    if (isReview) reviewingDiagram.value = true
    if (isEval) evaluatingSession.value = true
    try {
      await IntakeAPI.retryEvaluation(taskId)
      const fresh = await SystemDesignAPI.getSession(sessionId)
      _syncSessionInList(fresh.data)
      return await _awaitActiveTaskCompletion(fresh.data)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      if (isReview) reviewingDiagram.value = false
      if (isEval) evaluatingSession.value = false
    }
  }

  async function fetchFrontierPacket() {
    if (!activeSession.value) return null
    loadingFrontierPacket.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.getFrontierPacket(activeSession.value.id)
      frontierPacket.value = res.data
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingFrontierPacket.value = false
    }
  }

  async function importEvaluation(rawResponse) {
    if (!activeSession.value) return null
    importingEvaluation.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.importEvaluation(activeSession.value.id, rawResponse)
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      importingEvaluation.value = false
    }
  }

  async function prepareFrontierCoachPrompt(
    promptKind = 'initial',
    currentNodes = [],
    currentEdges = [],
    currentNotes = '',
    cloudProvider = 'generic',
    question = ''
  ) {
    if (!activeSession.value) return null
    loadingChallengePrompt.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.prepareFrontierCoachPrompt(activeSession.value.id, {
        prompt_kind: promptKind,
        cloud_provider: cloudProvider || 'generic',
        current_nodes: currentNodes,
        current_edges: currentEdges,
        current_notes: currentNotes || '',
        question: question || '',
      })
      frontierCoachPrompt.value = res.data
      if (res.data?.session) {
        _syncSessionInList(res.data.session)
      }
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingChallengePrompt.value = false
    }
  }

  async function prepareFrontierReviewPrompt(diagramVersion = null) {
    if (!activeSession.value) return null
    loadingFrontierPacket.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.prepareFrontierReviewPrompt(
        activeSession.value.id,
        diagramVersion
      )
      frontierReviewPrompt.value = res.data
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingFrontierPacket.value = false
    }
  }

  async function importFrontierReview(rawResponse, diagramVersion = null) {
    if (!activeSession.value) return null
    reviewingDiagram.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.importFrontierReview(
        activeSession.value.id,
        rawResponse,
        diagramVersion
      )
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      reviewingDiagram.value = false
    }
  }

  async function prepareFrontierDefencePrompt() {
    if (!activeSession.value) return null
    loadingFrontierPacket.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.prepareFrontierDefencePrompt(activeSession.value.id)
      frontierDefencePrompt.value = res.data
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loadingFrontierPacket.value = false
    }
  }

  async function importFrontierDefence(summaryOrTranscript) {
    if (!activeSession.value) return null
    sendingDefence.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.importFrontierDefence(
        activeSession.value.id,
        summaryOrTranscript
      )
      _syncSessionInList(res.data)
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      sendingDefence.value = false
    }
  }

  return {
    challenges,
    diagramCatalog,
    sessions,
    activeSession,
    loadingChallenges,
    loadingSessions,
    loadingSession,
    startingSession,
    creatingChallenge,
    generatingChallenge,
    updatingChallenge,
    resettingChallenges,
    sendingRequirements,
    extractingLedger,
    revealingRequirements,
    savingLedger,
    uploadingDiagram,
    loadingDiagramHint,
    sendingCoachChat,
    reviewingDiagram,
    sendingDefence,
    evaluatingSession,
    loadingFrontierPacket,
    importingEvaluation,
    frontierPacket,
    loadingChallengePrompt,
    importingChallenge,
    challengeFrontierPrompt,
    lastTopologyFeedback,
    expectedPaths,
    referenceActions,
    studyNotes,
    frontierCoachPrompt,
    frontierReviewPrompt,
    frontierDefencePrompt,
    capabilitiesChecklist,
    nextConnectionHint,
    coachMessages,
    suggestedCoachActions,
    error,
    activeLedger,
    activeDiagrams,
    activeReviews,
    activeFinalEvaluation,
    isActiveSessionCoached,
    sessionGamificationStats,
    reviewFixChecklist,
    fetchDiagramCatalog,
    fetchChallenges,
    createChallenge,
    generateChallenge,
    prepareChallengeFrontierPrompt,
    importFrontierChallenge,
    updateChallenge,
    resetDefaultChallenges,
    deleteChallenge,
    fetchSessions,
    startSession,
    loadSession,
    deleteSession,
    clearActiveSession,
    updateMode,
    sendRequirementsMessage,
    extractRequirementsLedger,
    revealRequirementsLedger,
    updateRequirementsLedger,
    uploadDiagram,
    submitCanvasDiagram,
    loadDiagramFlow,
    requestDiagramHint,
    sendDiagramCoachMessage,
    reviewDiagram,
    sendDefenceMessage,
    evaluateSession,
    cancelActiveTask,
    retryActiveTask,
    fetchFrontierPacket,
    importEvaluation,
    prepareFrontierCoachPrompt,
    prepareFrontierReviewPrompt,
    importFrontierReview,
    prepareFrontierDefencePrompt,
    importFrontierDefence,
  }
})
