import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { InterviewSimulatorAPI } from '../api/endpoints'

export const useInterviewStore = defineStore('interview', () => {
  const currentSession = ref(null)
  const sessionsList = ref([])
  const isLoadingSessions = ref(false)
  const isInitializing = ref(false)
  const isEvaluating = ref(false)
  const isGeneratingQuestion = ref(false)
  const isFinalizing = ref(false)
  const isSavingNotes = ref(false)
  const error = ref(null)

  const activePersona = ref('TECHNICAL_BAR_RAISER')
  const activeQuestionMode = ref('TEXT_CONVERSATIONAL')
  const selectedApplicationId = ref(null)

  const turns = computed(() => currentSession.value?.turns_data || [])
  const currentTurn = computed(() => {
    if (!turns.value.length) return null
    return turns.value[turns.value.length - 1]
  })
  const currentTurnIndex = computed(() => currentTurn.value?.turn_index || 1)

  const overallScore = computed(() => {
    if (currentSession.value?.overall_score !== undefined && currentSession.value?.overall_score !== null) {
      return currentSession.value.overall_score
    }
    const evaluatedTurns = turns.value.filter(t => t.evaluation && typeof t.evaluation.score === 'number')
    if (!evaluatedTurns.length) return null
    const sum = evaluatedTurns.reduce((acc, t) => acc + t.evaluation.score, 0)
    return Math.round(sum / evaluatedTurns.length)
  })

  const latestEvaluation = computed(() => {
    const evaluatedTurns = turns.value.filter(t => t.evaluation)
    if (!evaluatedTurns.length) return null
    return evaluatedTurns[evaluatedTurns.length - 1].evaluation
  })

  async function fetchSessions(silent = false) {
    if (!silent && !sessionsList.value.length) {
      isLoadingSessions.value = true
    }
    try {
      const res = await InterviewSimulatorAPI.listSessions({ limit: 50 })
      const list = res.data || []
      // Preserve optimistic placeholder if present during initial creation
      if (currentSession.value?.id && String(currentSession.value.id).startsWith('temp-')) {
        sessionsList.value = [currentSession.value, ...list.filter(s => s.id !== currentSession.value.id)]
      } else {
        sessionsList.value = list
      }
    } catch (err) {
      console.error('Failed to fetch interview sessions:', err)
    } finally {
      isLoadingSessions.value = false
    }
  }

  async function loadSession(id) {
    if (!id) return null
    if (String(id).startsWith('temp-')) {
      if (currentSession.value?.id === id) {
        return currentSession.value
      }
      return null
    }
    if (currentSession.value?.id === id) {
      return currentSession.value
    }
    isLoadingSessions.value = true
    error.value = null
    try {
      const res = await InterviewSimulatorAPI.getSession(id)
      currentSession.value = res.data
      selectedApplicationId.value = res.data.application_id
      activePersona.value = res.data.persona
      activeQuestionMode.value = res.data.question_mode || 'TEXT_CONVERSATIONAL'
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isLoadingSessions.value = false
    }
  }

  async function deleteSession(id) {
    if (!id) return
    if (String(id).startsWith('temp-')) {
      sessionsList.value = sessionsList.value.filter(s => s.id !== id)
      if (currentSession.value?.id === id) {
        resetSession()
      }
      return
    }
    try {
      await InterviewSimulatorAPI.deleteSession(id)
      sessionsList.value = sessionsList.value.filter(s => s.id !== id)
      if (currentSession.value?.id === id) {
        resetSession()
      }
    } catch (err) {
      console.error('Failed to delete interview session:', err)
      throw err
    }
  }

  async function startSession(applicationId = null, persona = 'TECHNICAL_BAR_RAISER', questionMode = 'TEXT_CONVERSATIONAL') {
    isInitializing.value = true
    error.value = null
    selectedApplicationId.value = applicationId
    activePersona.value = persona
    activeQuestionMode.value = questionMode
    const tempId = `temp-${Date.now()}`
    const placeholder = {
      id: tempId,
      application_id: applicationId,
      persona: persona,
      question_mode: questionMode,
      status: 'IN_PROGRESS',
      turns_data: [],
      created_at: new Date().toISOString(),
    }
    currentSession.value = placeholder
    sessionsList.value = [placeholder, ...sessionsList.value.filter(s => s.id !== tempId)]
    try {
      const res = await InterviewSimulatorAPI.startSession({
        application_id: applicationId,
        persona: persona,
        question_mode: questionMode,
      })
      currentSession.value = res.data
      sessionsList.value = [res.data, ...sessionsList.value.filter(s => s.id !== tempId && s.id !== res.data.id)]
      fetchSessions(true)
      return res.data
    } catch (err) {
      sessionsList.value = sessionsList.value.filter(s => s.id !== tempId)
      currentSession.value = null
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isInitializing.value = false
    }
  }

  async function evaluateAnswer(turnIndex, answerText, selectedOption = null) {
    if (!currentSession.value) return
    isEvaluating.value = true
    error.value = null
    // Optimistically update current turn so candidate response appears instantly
    const existingTurns = currentSession.value.turns_data || []
    const targetTurn = existingTurns.find(t => t.turn_index === turnIndex)
    if (targetTurn) {
      targetTurn.user_answer = answerText
      if (selectedOption) targetTurn.selected_option = selectedOption
    }
    try {
      const res = await InterviewSimulatorAPI.evaluateAnswer(currentSession.value.id, {
        turn_index: turnIndex,
        answer_text: answerText,
        selected_option: selectedOption,
      })
      currentSession.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isEvaluating.value = false
    }
  }

  async function nextQuestion() {
    if (!currentSession.value) return
    isGeneratingQuestion.value = true
    error.value = null
    try {
      const res = await InterviewSimulatorAPI.nextQuestion(currentSession.value.id)
      currentSession.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isGeneratingQuestion.value = false
    }
  }

  async function drillDown(turnIndex = null) {
    if (!currentSession.value) return
    isGeneratingQuestion.value = true
    error.value = null
    try {
      const res = await InterviewSimulatorAPI.drillDown(currentSession.value.id, {
        turn_index: turnIndex
      })
      currentSession.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isGeneratingQuestion.value = false
    }
  }

  async function finalizeSession() {
    if (!currentSession.value) return
    isFinalizing.value = true
    error.value = null
    try {
      const res = await InterviewSimulatorAPI.finalizeSession(currentSession.value.id)
      if (currentSession.value) {
        currentSession.value.status = 'COMPLETED'
        currentSession.value.overall_score = res.data.overall_score
        currentSession.value.readiness_rating = res.data.readiness_rating
        currentSession.value.summary_feedback = res.data.summary_feedback
      }
      const target = sessionsList.value.find(s => s.id === currentSession.value?.id)
      if (target) {
        target.status = 'COMPLETED'
        target.overall_score = res.data.overall_score
        target.readiness_rating = res.data.readiness_rating
        target.summary_feedback = res.data.summary_feedback
      }
      fetchSessions(true)
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isFinalizing.value = false
    }
  }

  async function saveNotes(customMarkdown = null) {
    if (!currentSession.value) return
    isSavingNotes.value = true
    error.value = null
    try {
      const res = await InterviewSimulatorAPI.saveNotes(currentSession.value.id, {
        notes_markdown: customMarkdown
      })
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isSavingNotes.value = false
    }
  }

  function resetSession() {
    currentSession.value = null
    error.value = null
  }

  return {
    currentSession,
    sessionsList,
    isLoadingSessions,
    isInitializing,
    isEvaluating,
    isGeneratingQuestion,
    isFinalizing,
    isSavingNotes,
    error,
    activePersona,
    activeQuestionMode,
    selectedApplicationId,
    turns,
    currentTurn,
    currentTurnIndex,
    overallScore,
    latestEvaluation,
    fetchSessions,
    loadSession,
    deleteSession,
    startSession,
    evaluateAnswer,
    nextQuestion,
    drillDown,
    finalizeSession,
    saveNotes,
    resetSession,
  }
})
