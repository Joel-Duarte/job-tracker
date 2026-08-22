import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { InterviewSimulatorAPI } from '../api/endpoints'

export const useInterviewStore = defineStore('interview', () => {
  const currentSession = ref(null)
  const isInitializing = ref(false)
  const isEvaluating = ref(false)
  const isGeneratingQuestion = ref(false)
  const isFinalizing = ref(false)
  const isSavingNotes = ref(false)
  const error = ref(null)

  const activePersona = ref('TECHNICAL_BAR_RAISER')
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
    if (!evaluatedTurns.length) return 0
    const sum = evaluatedTurns.reduce((acc, t) => acc + t.evaluation.score, 0)
    return Math.round(sum / evaluatedTurns.length)
  })

  const latestEvaluation = computed(() => {
    const evaluatedTurns = turns.value.filter(t => t.evaluation)
    if (!evaluatedTurns.length) return null
    return evaluatedTurns[evaluatedTurns.length - 1].evaluation
  })

  async function startSession(applicationId = null, persona = 'TECHNICAL_BAR_RAISER') {
    isInitializing.value = true
    error.value = null
    try {
      selectedApplicationId.value = applicationId
      activePersona.value = persona
      const res = await InterviewSimulatorAPI.startSession({
        application_id: applicationId,
        persona: persona
      })
      currentSession.value = res.data
      return res.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      isInitializing.value = false
    }
  }

  async function evaluateAnswer(turnIndex, answerText) {
    if (!currentSession.value) return
    isEvaluating.value = true
    error.value = null
    try {
      const res = await InterviewSimulatorAPI.evaluateAnswer(currentSession.value.id, {
        turn_index: turnIndex,
        answer_text: answerText
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
    isInitializing,
    isEvaluating,
    isGeneratingQuestion,
    isFinalizing,
    isSavingNotes,
    error,
    activePersona,
    selectedApplicationId,
    turns,
    currentTurn,
    currentTurnIndex,
    overallScore,
    latestEvaluation,
    startSession,
    evaluateAnswer,
    nextQuestion,
    drillDown,
    finalizeSession,
    saveNotes,
    resetSession,
  }
})
