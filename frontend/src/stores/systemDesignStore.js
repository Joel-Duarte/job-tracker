import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { SystemDesignAPI } from '../api/endpoints'

export const useSystemDesignStore = defineStore('systemDesign', () => {
  const challenges = ref([])
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
  const savingLedger = ref(false)
  const uploadingDiagram = ref(false)
  const reviewingDiagram = ref(false)
  const sendingDefence = ref(false)
  const evaluatingSession = ref(false)
  const loadingFrontierPacket = ref(false)
  const importingEvaluation = ref(false)
  const frontierPacket = ref(null)
  const error = ref(null)

  const activeLedger = computed(() => activeSession.value?.requirements_ledger || {})
  const activeDiagrams = computed(() => activeSession.value?.diagrams_metadata || [])
  const activeReviews = computed(() => activeSession.value?.architecture_reviews || [])
  const activeFinalEvaluation = computed(() => activeSession.value?.final_evaluation || null)

  function _syncSessionInList(session) {
    if (!session || !session.id) return
    if (activeSession.value?.id !== session.id) {
      frontierPacket.value = null
    }
    activeSession.value = session
    const idx = sessions.value.findIndex((s) => s.id === session.id)
    if (idx !== -1) {
      const updated = [...sessions.value]
      updated[idx] = session
      sessions.value = updated
    } else {
      sessions.value = [session, ...sessions.value]
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
      sessions.value = sessions.value.filter((s) => s.challenge_id !== challengeId)
      if (activeSession.value?.challenge_id === challengeId) {
        activeSession.value = null
        frontierPacket.value = null
      }
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

  async function startSession(challengeId, mode = 'ADAPTIVE', applicationId = null) {
    startingSession.value = true
    error.value = null
    try {
      const payload = {
        challenge_id: challengeId,
        mode,
        ...(applicationId ? { application_id: applicationId } : {}),
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

  async function loadSession(sessionId) {
    loadingSession.value = true
    error.value = null
    try {
      const res = await SystemDesignAPI.getSession(sessionId)
      _syncSessionInList(res.data)
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
        activeSession.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  function clearActiveSession() {
    activeSession.value = null
    frontierPacket.value = null
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
      return res.data
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
      return res.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      evaluatingSession.value = false
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

  return {
    challenges,
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
    savingLedger,
    uploadingDiagram,
    reviewingDiagram,
    sendingDefence,
    evaluatingSession,
    loadingFrontierPacket,
    importingEvaluation,
    frontierPacket,
    error,
    activeLedger,
    activeDiagrams,
    activeReviews,
    activeFinalEvaluation,
    fetchChallenges,
    createChallenge,
    generateChallenge,
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
    updateRequirementsLedger,
    uploadDiagram,
    reviewDiagram,
    sendDefenceMessage,
    evaluateSession,
    fetchFrontierPacket,
    importEvaluation,
  }
})
