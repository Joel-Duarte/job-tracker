<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DOMPurify from 'dompurify'
import { useAgentChatStore } from '../stores/agentChatStore'
import { useInterviewStore } from '../stores/interviewStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { useUIStore } from '../stores/uiStore'
import { AIConfigAPI } from '../api/endpoints'
import {
  Bot,
  User,
  Send,
  Loader2,
  CheckCircle2,
  ArrowRight,
  Plus,
  MessageSquare,
  Trash2,
  Settings,
  PanelLeftClose,
  PanelLeftOpen,
  Mic,
  MicOff,
  Sparkles,
  Shield,
  Briefcase,
  Users,
  GraduationCap,
  Play,
  RotateCcw,
  Flag,
  Award,
  BookOpen,
  Check,
  AlertCircle,
  TrendingUp,
  FileText,
  Search,
  Circle,
  Layers,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const chatStore = useAgentChatStore()
const interviewStore = useInterviewStore()
const appStore = useApplicationsStore()
const uiStore = useUIStore()

// Mode toggle: 'assistant' | 'interview'
const activeMode = ref('assistant')

// Assistant Chat State
const inputMessage = ref('')
const chatContainer = ref(null)
const retentionDays = ref(0)
const isUpdatingRetention = ref(false)
const isSidebarCollapsed = ref(localStorage.getItem('agentChatSidebarCollapsed') === 'true')

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
  localStorage.setItem('agentChatSidebarCollapsed', isSidebarCollapsed.value ? 'true' : 'false')
}

function closeSidebarOnMobile() {
  if (window.innerWidth < 768) {
    isSidebarCollapsed.value = true
  }
}

const starterPrompts = [
  '🛠️ What tools can you use?',
  'Which applications currently require urgent action from me?',
  'Find roles involving Python, Distributed Systems, or Staff engineering',
  'What is the current status of my Stripe application?',
  'Move Stripe to OFFER status',
]

const mockAppId = ref(null)
const mockQuestionMode = ref('TEXT_CONVERSATIONAL')
const appSearchQuery = ref('')
const sidebarSearchQuery = ref('')
const selectedOptionKey = ref(null)
const candidateAnswer = ref('')
const interviewInputRef = ref(null)
const isRefining = ref(false)

const shouldShowMCChoices = computed(() => {
  if (interviewStore.isEvaluating || interviewStore.isGeneratingQuestion || interviewStore.isInitializing) return false
  const turn = interviewStore.currentTurn
  if (!turn || !turn.options || !turn.options.length) return false
  if (turn.evaluation && !isRefining.value) return false
  if ((turn.user_answer || turn.selected_option) && !isRefining.value) return false
  return true
})

// Filtered sidebar items
const filteredChats = computed(() => {
  const q = sidebarSearchQuery.value.trim().toLowerCase()
  if (!q) return chatStore.chatsList || []
  return (chatStore.chatsList || []).filter(c => (c.title || '').toLowerCase().includes(q))
})

const filteredInterviewSessions = computed(() => {
  const q = sidebarSearchQuery.value.trim().toLowerCase()
  let list = [...(interviewStore.sessionsList || [])]

  // Pin active in-progress simulation to the top of the sidebar list
  const activeId = interviewStore.currentSession?.id
  if (activeId && interviewStore.currentSession?.status === 'IN_PROGRESS') {
    const activeIndex = list.findIndex(s => s.id === activeId)
    if (activeIndex > -1) {
      const [activeItem] = list.splice(activeIndex, 1)
      list.unshift(activeItem)
    } else {
      list.unshift(interviewStore.currentSession)
    }
  }

  if (!q) return list
  return list.filter(s => formatSessionTitle(s).toLowerCase().includes(q))
})

// Voice dictation (Web Speech API)
const isRecording = ref(false)
const speechSupported = ref(false)
let recognitionInstance = null

const QUESTION_MODES = [
  {
    id: 'TEXT_CONVERSATIONAL',
    title: 'Conversational',
    icon: MessageSquare,
    desc: 'Practice realistic open-ended behavioral and architectural questions with in-depth rubric scoring.'
  },
  {
    id: 'MULTIPLE_CHOICE',
    title: 'Multiple Choice',
    icon: CheckCircle2,
    desc: 'Objective scenario and architecture challenges with immediate tradeoff evaluations.'
  },
  {
    id: 'HYBRID',
    title: 'Hybrid',
    icon: Layers,
    desc: 'Alternates between objective multiple choice challenges and open-ended STAR deep dives.'
  }
]

// Eligible Applications (Only APPLIED, ONLINE_ASSESSMENT, TECHNICAL_INTERVIEW)
const eligibleApplications = computed(() => {
  return (appStore.applications || []).filter(app =>
    ['APPLIED', 'ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW'].includes(app.status)
  )
})

const filteredApplications = computed(() => {
  const q = appSearchQuery.value.trim().toLowerCase()
  if (!q) return eligibleApplications.value
  return eligibleApplications.value.filter(app => {
    const comp = (app.company?.name || '').toLowerCase()
    const pos = (app.position || '').toLowerCase()
    return comp.includes(q) || pos.includes(q)
  })
})

function handleSelectApp(id) {
  mockAppId.value = mockAppId.value === id ? null : id
}

// Assistant Chat Handlers
async function handleSendMessage(customPrompt = null) {
  const text = (customPrompt || inputMessage.value).trim()
  if (!text || chatStore.isSending) return
  if (!(await uiStore.ensureAIReady())) return

  inputMessage.value = ''
  try {
    await chatStore.sendMessage(text)
    scrollToBottom()
  } catch (err) {
    uiStore.showToast("Failed to send message", "error")
  }
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendMessage()
  }
}

async function handleLoadChat(id) {
  closeSidebarOnMobile()
  if (!id) return
  if (chatStore.chatId === id || String(id).startsWith('temp-')) {
    scrollToBottom()
    return
  }
  try {
    await chatStore.loadChat(id)
    scrollToBottom()
  } catch (err) {
    uiStore.showToast("Failed to load chat", "error")
  }
}

function handleResetChat() {
  chatStore.resetChat()
  inputMessage.value = ''
  closeSidebarOnMobile()
}

async function handleDeleteChat(id) {
  try {
    await chatStore.deleteChat(id)
    uiStore.showToast("Chat deleted", "success")
  } catch (err) {
    uiStore.showToast("Failed to delete chat", "error")
  }
}

async function handleRetentionChange() {
  isUpdatingRetention.value = true
  try {
    await AIConfigAPI.updateGlobalSettings({ AGENT_CHAT_RETENTION_DAYS: retentionDays.value })
    uiStore.showToast("Auto-delete setting updated", "success")
  } catch (err) {
    uiStore.showToast("Failed to update retention setting", "error")
  } finally {
    isUpdatingRetention.value = false
  }
}

onMounted(async () => {
  if (window.innerWidth < 768) {
    isSidebarCollapsed.value = true
  }
  await appStore.fetchApplications()
  await chatStore.fetchChats()
  await interviewStore.fetchSessions()

  // Handle URL deep-linking (?appId=X&mock=true)
  if (route.query.mock === 'true' || route.query.appId) {
    activeMode.value = 'interview'
    if (route.query.appId) {
      mockAppId.value = parseInt(route.query.appId)
    }
  }

  // Setup Web Speech API if supported
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (SpeechRecognition) {
    speechSupported.value = true
    recognitionInstance = new SpeechRecognition()
    recognitionInstance.continuous = true
    recognitionInstance.interimResults = true

    recognitionInstance.onresult = (event) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript
      }
      candidateAnswer.value = (candidateAnswer.value + ' ' + transcript).trim()
    }

    recognitionInstance.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
      isRecording.value = false
    }

    recognitionInstance.onend = () => {
      isRecording.value = false
    }
  }

  try {
    const res = await AIConfigAPI.getGlobalSettings()
    retentionDays.value = res.data.AGENT_CHAT_RETENTION_DAYS || 0
  } catch (err) {
    console.error("Failed to load retention settings", err)
  }

  scrollToBottom()
})

// Auto-scroll watchers for all mode switches, message updates, and session loads
watch(activeMode, () => {
  scrollToBottom()
})

watch(() => chatStore.chatId, () => {
  scrollToBottom()
})

watch(() => chatStore.messages, () => {
  scrollToBottom()
}, { deep: true })

watch(() => interviewStore.currentSession?.id, () => {
  scrollToBottom()
})

watch(() => interviewStore.turns, () => {
  scrollToBottom()
}, { deep: true })

watch([() => chatStore.isSending, () => interviewStore.isEvaluating, () => interviewStore.isGeneratingQuestion], () => {
  scrollToBottom()
})

watch(() => route.query, (newQuery) => {
  if (newQuery.mock === 'true' || newQuery.appId) {
    activeMode.value = 'interview'
    if (newQuery.appId) {
      mockAppId.value = parseInt(newQuery.appId)
    }
    scrollToBottom()
  }
})

function toggleVoiceInput() {
  if (!speechSupported.value || !recognitionInstance) return
  if (isRecording.value) {
    recognitionInstance.stop()
    isRecording.value = false
  } else {
    try {
      recognitionInstance.start()
      isRecording.value = true
    } catch (err) {
      console.error("Failed to start speech recognition:", err)
    }
  }
}

// Interview Session Actions
function handleNewSimulation() {
  interviewStore.resetSession()
  candidateAnswer.value = ''
  selectedOptionKey.value = null
  closeSidebarOnMobile()
}

async function handleLoadInterviewSession(id) {
  closeSidebarOnMobile()
  if (!id) return
  if (interviewStore.currentSession?.id === id || String(id).startsWith('temp-')) {
    scrollToBottom()
    return
  }
  try {
    await interviewStore.loadSession(id)
    candidateAnswer.value = ''
    selectedOptionKey.value = null
    scrollToBottom()
  } catch (err) {
    uiStore.showToast("Failed to load interview session", "error")
  }
}

async function handleDeleteInterviewSession(id) {
  try {
    await interviewStore.deleteSession(id)
    uiStore.showToast("Simulation session deleted", "success")
  } catch (err) {
    uiStore.showToast("Failed to delete interview session", "error")
  }
}async function handleStartInterviewSession() {
  if (!(await uiStore.ensureAIReady())) return
  try {
    await interviewStore.startSession(mockAppId.value, 'TECHNICAL_BAR_RAISER', mockQuestionMode.value)
    candidateAnswer.value = ''
    selectedOptionKey.value = null
    scrollToBottom()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to start mock interview session"
    uiStore.showToast(msg, "error")
  }
}

async function handleRestartSameSimulation() {
  if (!(await uiStore.ensureAIReady())) return
  try {
    const appId = interviewStore.selectedApplicationId
    const qMode = interviewStore.activeQuestionMode || 'TEXT_CONVERSATIONAL'
    await interviewStore.startSession(appId, 'TECHNICAL_BAR_RAISER', qMode)
    candidateAnswer.value = ''
    selectedOptionKey.value = null
    scrollToBottom()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to restart simulation"
    uiStore.showToast(msg, "error")
  }
}

async function handleStartAnotherSimulation(questionMode) {
  if (!(await uiStore.ensureAIReady())) return
  try {
    const appId = interviewStore.selectedApplicationId
    await interviewStore.startSession(appId, 'TECHNICAL_BAR_RAISER', questionMode)
    candidateAnswer.value = ''
    selectedOptionKey.value = null
    scrollToBottom()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to start simulation"
    uiStore.showToast(msg, "error")
  }
}

async function handleFinalizeSession() {
  try {
    await interviewStore.finalizeSession()
    scrollToBottom()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to finalize session"
    uiStore.showToast(msg, "error")
  }
}

async function handleSaveNotes() {
  try {
    await interviewStore.saveNotes()
    uiStore.showToast("Saved simulation scorecard to Application Notes", "success")
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to save notes"
    uiStore.showToast(msg, "error")
  }
}

const isConversationalOrHybrid = computed(() => {
  const mode = interviewStore.currentSession?.question_mode || mockQuestionMode.value
  return mode === 'TEXT_CONVERSATIONAL' || mode === 'HYBRID'
})

function handleAutoResize(e) {
  const target = e?.target || interviewInputRef.value
  if (!target) return
  target.style.height = 'auto'
  const newHeight = Math.min(Math.max(target.scrollHeight, 44), 180)
  target.style.height = `${newHeight}px`
}

async function enterInterviewFromChat(sessionId) {
  activeMode.value = 'interview'
  await handleLoadInterviewSession(sessionId)
}

async function handleEvaluateAnswer() {
  const currentTurn = interviewStore.currentTurn
  const isMC = currentTurn?.question_type === 'MULTIPLE_CHOICE' || (currentTurn?.options && currentTurn.options.length)
  if (isMC && !selectedOptionKey.value) {
    uiStore.showToast("Please select an option first", "warning")
    return
  }
  if (!isMC && !candidateAnswer.value.trim()) return
  if (interviewStore.isEvaluating) return
  if (!(await uiStore.ensureAIReady())) return

  const currentTurnIdx = interviewStore.currentTurnIndex
  const text = candidateAnswer.value.trim()
  const opt = selectedOptionKey.value
  isRefining.value = false
  candidateAnswer.value = ''
  selectedOptionKey.value = null
  try {
    await interviewStore.evaluateAnswer(currentTurnIdx, text, opt)
    scrollToBottom()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to evaluate answer"
    uiStore.showToast(msg, "error")
  }
}

async function handleNextQuestion() {
  if (!(await uiStore.ensureAIReady())) return
  try {
    isRefining.value = false
    selectedOptionKey.value = null
    candidateAnswer.value = ''
    await interviewStore.nextQuestion()
    scrollToBottom()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to generate next question"
    uiStore.showToast(msg, "error")
  }
}

async function handleDrillDown() {
  if (!(await uiStore.ensureAIReady())) return
  try {
    isRefining.value = false
    selectedOptionKey.value = null
    candidateAnswer.value = ''
    await interviewStore.drillDown()
    scrollToBottom()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || "Failed to generate drill-down question"
    uiStore.showToast(msg, "error")
  }
}

function prepareRefineAnswer() {
  isRefining.value = true
  if (interviewStore.currentTurn?.user_answer) {
    candidateAnswer.value = interviewStore.currentTurn.user_answer
  }
  if (interviewStore.currentTurn?.selected_option) {
    selectedOptionKey.value = interviewStore.currentTurn.selected_option
  }
  nextTick(() => {
    if (interviewInputRef.value) {
      interviewInputRef.value.focus()
    }
  })
}

function formatSessionTitle(session) {
  if (!session) return 'Interview Simulation'
  const modeLabel = session.question_mode === 'MULTIPLE_CHOICE' ? 'Multiple Choice' : session.question_mode === 'HYBRID' ? 'Hybrid' : 'Conversational'
  const dateStr = session.created_at ? new Date(session.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''
  if (session.application_id) {
    const app = appStore.applications.find(a => String(a.id) === String(session.application_id))
    if (app) {
      return `${app.company?.name || 'Company'} (${modeLabel})`
    }
  }
  return `General Practice (${modeLabel}) · ${dateStr}`
}

function formatSessionDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function formatStatus(status) {
  if (!status) return ''
  return status.replace(/_/g, ' ')
}

function isCompletedSession(session) {
  if (!session) return false
  if (session.id === interviewStore.currentSession?.id && interviewStore.currentSession?.status === 'COMPLETED') {
    return true
  }
  return session.status === 'COMPLETED' || session.status === 'completed'
}

function getSessionScore(session) {
  if (session.id === interviewStore.currentSession?.id && interviewStore.currentSession?.overall_score !== undefined && interviewStore.currentSession?.overall_score !== null) {
    return interviewStore.currentSession.overall_score
  }
  return session.overall_score
}

function getSessionReadiness(session) {
  if (session.id === interviewStore.currentSession?.id && interviewStore.currentSession?.readiness_rating) {
    return interviewStore.currentSession.readiness_rating
  }
  return session.readiness_rating
}

function handleSelectChoice(optKey) {
  selectedOptionKey.value = optKey
}

function scrollToBottom(smooth = false) {
  const doScroll = () => {
    if (chatContainer.value) {
      chatContainer.value.scrollTo({
        top: chatContainer.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      })
    }
  }
  nextTick(() => {
    doScroll()
    setTimeout(doScroll, 50)
    setTimeout(doScroll, 150)
    setTimeout(doScroll, 300)
  })
}

function renderMarkdown(content) {
  if (!content) return ''
  let html = content
  html = html.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`
  })
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>')
  html = html.replace(/^\&gt;\s?(.*$)/gim, '<blockquote>$1</blockquote>')
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
  html = html.replace(/^\s*[\-\*]\s+(.*$)/gim, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/gis, '<ul>$1</ul>')
  html = html.replace(/<\/ul>\s*<ul>/g, '')

  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, p1, p2) => {
    const safeUrl = (p2.startsWith('http://') || p2.startsWith('https://') || p2.startsWith('/')) ? p2 : '#'
    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${p1}</a>`
  })

  html = html.replace(/\n\n+/g, '</p><p>')
  html = `<p>${html}</p>`
  html = html.replace(/<p>\s*<\/p>/g, '')
  html = html.replace(/<p>(<h[1-3]>.*?<\/h[1-3]>)<\/p>/g, '$1')
  html = html.replace(/<p>(<pre>.*?<\/pre>)<\/p>/gs, '$1')
  html = html.replace(/<p>(<table>.*?<\/table>)<\/p>/gs, '$1')
  html = html.replace(/<p>(<ul>.*?<\/ul>)<\/p>/gs, '$1')
  html = html.replace(/<p>(<blockquote>.*?<\/blockquote>)<\/p>/gs, '$1')

  return DOMPurify.sanitize(html)
}

function formatActionLabel(act) {
  if (act.action === 'UPDATE_STATUS' || act.action === 'update_application_status') {
    const comp = act.args?.company_name || act.company || 'Application'
    const st = act.args?.new_status || act.new_status || 'Updated'
    return `Updated ${comp} status to ${st}`
  }
  if (act.action === 'semantic_vector_search') {
    const q = act.args?.query ? `"${act.args.query}"` : 'records'
    return `Searched vector database for ${q}`
  }
  if (act.action === 'list_applications') {
    const st = act.args?.status ? `(${act.args.status})` : ''
    return `Queried database applications ${st}`.trim()
  }
  if (act.action === 'get_application_details') {
    const comp = act.args?.company_or_id || 'Company'
    return `Retrieved full event timeline for ${comp}`
  }
  if (act.action === 'get_action_items') {
    return `Queried pending action items & deadlines`
  }
  if (act.action === 'start_mock_interview') {
    const comp = act.args?.company_or_id || 'Practice'
    return `Launched live mock interview for ${comp}`
  }
  return `Executed: ${act.action || 'Tool'}`
}

function getReadinessBadgeClass(rating) {
  if (!rating) return ''
  const r = rating.toLowerCase()
  if (r.includes('strong')) return 'readiness-strong'
  if (r.includes('hire')) return 'readiness-hire'
  if (r.includes('incomplete')) return 'readiness-incomplete'
  return 'readiness-work'
}

function getScoreBadgeClass(score) {
  if (score >= 80) return 'score-pill-high'
  if (score >= 65) return 'score-pill-med'
  return 'score-pill-low'
}
</script>

<template>
  <div class="chat-page-container" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">

    <!-- Mobile Sidebar Backdrop -->
    <div
      v-if="!isSidebarCollapsed"
      class="sidebar-backdrop"
      @click="isSidebarCollapsed = true"
    ></div>

    <!-- Unified Sidebar (For Both Assistant & Interview Simulation Modes) -->
    <div class="chat-sidebar" :class="{ 'collapsed': isSidebarCollapsed }">
      <!-- ASSISTANT MODE SIDEBAR HEADER & LIST -->
      <template v-if="activeMode === 'assistant'">
        <div class="sidebar-header">
          <button
            class="btn-new-chat-sidebar"
            @click="handleResetChat"
          >
            <Plus :size="16" />
            <span>New Chat</span>
          </button>
          <button
            class="btn-icon-sidebar"
            @click="toggleSidebar"
            title="Collapse Sidebar"
          >
            <PanelLeftClose :size="18" />
          </button>
        </div>

        <!-- Sidebar Filter Input -->
        <div class="sidebar-search-box">
          <Search :size="13" class="sidebar-search-icon" />
          <input
            v-model="sidebarSearchQuery"
            type="text"
            placeholder="Filter chats by title..."
            class="sidebar-search-input"
          />
        </div>

        <div class="chats-list">
          <div v-if="chatStore.isLoadingChats" class="chats-loading">
            <Loader2 class="animate-spin" :size="20" />
          </div>
          <div v-else-if="filteredChats.length === 0" class="no-chats">
            {{ sidebarSearchQuery ? 'No matching chats' : 'No previous chats' }}
          </div>
          <div v-else class="chats-list-scroll">
            <div
              v-for="chat in filteredChats"
              :key="chat.id"
              class="chat-list-item"
              :class="{ active: chatStore.chatId === chat.id }"
              @click="handleLoadChat(chat.id)"
            >
              <div class="chat-item-content">
                <MessageSquare :size="14" class="chat-icon" />
                <span class="chat-title">{{ chat.title }}</span>
              </div>
              <button class="btn-delete-chat" @click.stop="handleDeleteChat(chat.id)" title="Delete Chat">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- INTERVIEW SIMULATOR MODE SIDEBAR HEADER & LIST -->
      <template v-else-if="activeMode === 'interview'">
        <div class="sidebar-header">
          <button
            class="btn-new-chat-sidebar"
            @click="handleNewSimulation"
          >
            <Plus :size="16" />
            <span>New Simulation</span>
          </button>
          <button
            class="btn-icon-sidebar"
            @click="toggleSidebar"
            title="Collapse Sidebar"
          >
            <PanelLeftClose :size="18" />
          </button>
        </div>

        <!-- Sidebar Filter Input -->
        <div class="sidebar-search-box">
          <Search :size="13" class="sidebar-search-icon" />
          <input
            v-model="sidebarSearchQuery"
            type="text"
            placeholder="Filter simulations by title..."
            class="sidebar-search-input"
          />
        </div>

        <div class="chats-list">
          <div v-if="interviewStore.isLoadingSessions" class="chats-loading">
            <Loader2 class="animate-spin" :size="20" />
          </div>
          <div v-else-if="filteredInterviewSessions.length === 0" class="no-chats">
            {{ sidebarSearchQuery ? 'No matching simulations' : 'No previous simulations' }}
          </div>
          <div v-else class="chats-list-scroll">
            <div
              v-for="session in filteredInterviewSessions"
              :key="session.id"
              class="chat-list-item interview-session-item"
              :class="{
                active: interviewStore.currentSession?.id === session.id,
                'active-session-pinned': session.id === interviewStore.currentSession?.id && interviewStore.currentSession?.status === 'IN_PROGRESS'
              }"
              @click="handleLoadInterviewSession(session.id)"
            >
              <div class="chat-item-content">
                <Sparkles :size="14" class="chat-icon text-primary" />
                <div class="session-sidebar-info">
                  <span class="session-sidebar-title">{{ formatSessionTitle(session) }}</span>
                  <div class="session-sidebar-meta">
                    <template v-if="isCompletedSession(session)">
                      <span class="session-status-tag session-status-closed">Closed</span>
                      <span
                        v-if="getSessionScore(session) !== null && getSessionScore(session) !== undefined"
                        class="session-score-tag"
                        :class="getReadinessBadgeClass(getSessionReadiness(session))"
                      >
                        {{ Math.round(getSessionScore(session)) }}%
                      </span>
                    </template>
                    <span v-else-if="session.id === interviewStore.currentSession?.id && interviewStore.currentSession?.status === 'IN_PROGRESS'" class="session-status-tag session-status-live">
                      <span class="live-dot"></span> Live
                    </span>
                    <span v-else class="session-status-tag">In Progress</span>
                    <span class="session-date-tag">{{ formatSessionDate(session.created_at) }}</span>
                  </div>
                </div>
              </div>
              <button class="btn-delete-chat" @click.stop="handleDeleteInterviewSession(session.id)" title="Delete Simulation">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- Sidebar Footer -->
      <div class="sidebar-footer">
        <div v-if="activeMode === 'assistant'" class="retention-setting">
          <label class="retention-label">
            <Settings :size="12" />
            Auto-delete chats
          </label>
          <select
            v-model="retentionDays"
            @change="handleRetentionChange"
            :disabled="isUpdatingRetention"
            class="retention-select"
          >
            <option :value="0">Never</option>
            <option :value="7">After 7 days</option>
            <option :value="14">After 14 days</option>
            <option :value="30">After 30 days</option>
          </select>
        </div>
        <div v-else class="interview-sidebar-hint">
          <span>Simulation history preserved</span>
        </div>
      </div>
    </div>

    <!-- Main Workspace Area -->
    <div class="chat-main">
      <!-- Mode Switcher Top Header -->
      <div class="chat-header">
        <div class="header-content-inner">
          <div class="header-left">
            <button
              v-if="isSidebarCollapsed"
              class="btn-icon-sidebar btn-expand-sidebar"
              @click="toggleSidebar"
              title="Expand Sidebar"
            >
              <PanelLeftOpen :size="18" />
            </button>

            <!-- Mode Switcher Segment Buttons -->
            <div class="mode-switcher-pill">
              <button
                class="mode-btn"
                :class="{ active: activeMode === 'assistant' }"
                @click="activeMode = 'assistant'"
              >
                <Bot :size="15" />
                <span>AI Assistant</span>
              </button>
              <button
                class="mode-btn"
                :class="{ active: activeMode === 'interview' }"
                @click="activeMode = 'interview'"
              >
                <Sparkles :size="15" />
                <span>Live Mock Interview Simulator</span>
              </button>
            </div>
          </div>

          <div v-if="activeMode === 'interview' && interviewStore.currentSession?.status === 'IN_PROGRESS'" class="header-right">
            <button
              class="btn btn-danger btn-sm text-danger header-end-btn"
              :disabled="interviewStore.isFinalizing"
              @click="handleFinalizeSession"
              title="Finish interview and view scorecard"
            >
              <Flag :size="14" />
              <span>End Session</span>
            </button>
          </div>
        </div>
      </div>

      <!-- MODE 1: STANDARD AI ASSISTANT CHAT -->
      <template v-if="activeMode === 'assistant'">
        <div ref="chatContainer" class="chat-messages">
          <div class="chat-messages-inner">
            <div
              v-for="(msg, idx) in chatStore.messages"
              :key="idx"
              class="message-row"
              :class="`msg-${msg.role}`"
            >
              <template v-if="msg.role !== 'tool' && msg.role !== 'system'">
                <div class="avatar-icon">
                  <Bot v-if="msg.role === 'assistant'" :size="16" />
                  <User v-else :size="16" />
                </div>

                <div class="message-bubble">
                  <div v-if="msg.actions && msg.actions.length > 0" class="actions-chips">
                    <template v-for="(act, aIdx) in msg.actions" :key="aIdx">
                      <button
                        v-if="act.action === 'start_mock_interview' && (act.result?.session_id || act.session_id)"
                        class="action-chip action-chip-interactive"
                        @click="enterInterviewFromChat(act.result?.session_id || act.session_id)"
                        title="Click to jump into this live interview simulation"
                      >
                        <Sparkles :size="13" class="text-primary" />
                        <span>Enter Mock Interview (#{{ act.result?.session_id || act.session_id }})</span>
                        <ArrowRight :size="12" />
                      </button>
                      <div v-else class="action-chip">
                        <CheckCircle2 :size="13" class="text-success" />
                        <span>{{ formatActionLabel(act) }}</span>
                      </div>
                    </template>
                  </div>

                  <div
                    v-if="msg.role === 'assistant'"
                    class="message-text markdown-body"
                    v-html="renderMarkdown(msg.content)"
                  ></div>
                  <div v-else class="message-text">{{ msg.content }}</div>
                </div>
              </template>
            </div>

            <div v-if="chatStore.isSending" class="message-row msg-assistant">
              <div class="avatar-icon">
                <Bot :size="16" />
              </div>
              <div class="message-bubble thinking-bubble">
                <Loader2 class="animate-spin" :size="16" />
                <span>Agent is reasoning & searching records...</span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-bottom-dock">
          <div class="bottom-dock-inner">
            <div v-if="chatStore.messages.length <= 2" class="starters-bar">
              <button
                v-for="prompt in starterPrompts"
                :key="prompt"
                class="starter-chip"
                @click="handleSendMessage(prompt)"
              >
                <span>{{ prompt }}</span>
                <ArrowRight :size="12" />
              </button>
            </div>

            <div class="chat-input-bar">
              <textarea
                v-model="inputMessage"
                rows="1"
                placeholder="Ask the agent to search applications, check interview dates, or change statuses..."
                class="chat-input"
                @keydown="handleKeyDown"
              ></textarea>

              <button
                class="btn btn-primary btn-send"
                :disabled="chatStore.isSending || !inputMessage.trim()"
                @click="handleSendMessage()"
              >
                <Send :size="15" />
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- MODE 2: MOCK INTERVIEW SIMULATOR -->
      <template v-else-if="activeMode === 'interview'">
        <!-- PRE-SESSION SETUP SCREEN -->
        <div v-if="!interviewStore.currentSession" class="interview-setup-screen">
          <div class="setup-card animate-fade-in">
            <div class="setup-header">
              <div class="setup-icon-box">
                <Sparkles :size="28" class="text-primary" />
              </div>
              <h2 class="setup-title">Interactive Live Mock Interview</h2>
              <p class="setup-subtitle">
                Practice realistic interview rounds with AI evaluation, in-thread feedback, and a comprehensive debrief scorecard.
              </p>
            </div>

            <div class="setup-form">
              <!-- Searchable Target Application Picker -->
              <div class="form-group">
                <div class="target-app-header">
                  <label class="form-label">Target Application</label>
                  <span class="target-app-subtitle">Showing Applied &amp; Interview stage positions</span>
                </div>

                <div class="app-search-wrapper">
                  <Search :size="15" class="app-search-icon" />
                  <input
                    v-model="appSearchQuery"
                    type="text"
                    placeholder="Search by company or position name..."
                    class="app-search-input"
                  />
                </div>

                <div class="app-selectable-list-container">
                  <!-- General Practice Option -->
                  <div
                    class="app-selectable-card"
                    :class="{ 'card-active': mockAppId === null }"
                    @click="mockAppId = null"
                    role="button"
                    tabindex="0"
                  >
                    <div class="card-check-icon">
                      <CheckCircle2 v-if="mockAppId === null" class="icon-active" :size="18" />
                      <Circle v-else class="icon-inactive" :size="18" />
                    </div>
                    <div class="app-card-details">
                      <div class="app-card-title">🎯 General Technical &amp; Behavioral Practice</div>
                      <div class="app-card-desc">No specific application linked. Evaluates core engineering &amp; STAR competencies.</div>
                    </div>
                  </div>

                  <!-- Filtered Applications -->
                  <div
                    v-for="app in filteredApplications"
                    :key="app.id"
                    class="app-selectable-card"
                    :class="{ 'card-active': mockAppId === app.id }"
                    @click="handleSelectApp(app.id)"
                    role="button"
                    tabindex="0"
                  >
                    <div class="card-check-icon">
                      <CheckCircle2 v-if="mockAppId === app.id" class="icon-active" :size="18" />
                      <Circle v-else class="icon-inactive" :size="18" />
                    </div>
                    <div class="app-card-details">
                      <div class="app-card-title-row">
                        <span class="app-company-name">{{ app.company?.name || 'Company' }}</span>
                        <span class="app-status-badge" :class="'badge-' + app.status?.toLowerCase()">
                          {{ formatStatus(app.status) }}
                        </span>
                      </div>
                      <div class="app-position-title">{{ app.position || 'Position' }}</div>
                    </div>
                  </div>

                  <div v-if="filteredApplications.length === 0 && appSearchQuery" class="app-no-results">
                    No matching applications found in Applied or Interview stages.
                  </div>
                </div>
              </div>

              <!-- Question Format Picker -->
              <div class="form-group">
                <label class="form-label">Select Question Format</label>
                <div class="question-mode-grid">
                  <div
                    v-for="m in QUESTION_MODES"
                    :key="m.id"
                    class="question-mode-card"
                    :class="{ active: mockQuestionMode === m.id }"
                    @click="mockQuestionMode = m.id"
                  >
                    <div class="question-mode-header">
                      <div class="mode-title-wrap">
                        <component :is="m.icon" :size="16" class="mode-icon" />
                        <span class="question-mode-title">{{ m.title }}</span>
                      </div>
                    </div>
                    <p class="question-mode-desc">{{ m.desc }}</p>
                  </div>
                </div>
              </div>

              <div class="setup-actions">
                <button
                  class="btn btn-primary btn-lg start-btn"
                  :disabled="interviewStore.isInitializing"
                  @click="handleStartInterviewSession"
                >
                  <Loader2 v-if="interviewStore.isInitializing" class="animate-spin" :size="18" />
                  <Play v-else :size="18" />
                  <span>Start Interview Simulation</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ACTIVE SESSION FULL-WIDTH FLOOR -->
        <div v-else-if="interviewStore.currentSession.status === 'IN_PROGRESS'" class="interview-floor-full">
          <!-- Questions & Answers Thread -->
          <div ref="chatContainer" class="floor-thread">
            <!-- Initial Session Thinking State (while first question generates) -->
            <div v-if="interviewStore.isInitializing && !interviewStore.turns.length" class="msg-row interviewer-row animate-fade-in">
              <div class="avatar-icon interviewer-avatar">
                <Sparkles :size="16" />
              </div>
              <div class="msg-bubble thinking-bubble">
                <Loader2 class="animate-spin" :size="16" />
                <span>Interviewer is analyzing your application & background to formulate your opening challenge...</span>
              </div>
            </div>

            <!-- Turns List -->
            <div
              v-for="turn in interviewStore.turns"
              :key="turn.turn_index"
              class="turn-block animate-fade-in"
            >
              <!-- Question Bubble -->
              <div class="msg-row interviewer-row">
                <div class="avatar-icon interviewer-avatar">
                  <Sparkles :size="16" />
                </div>
                <div class="msg-bubble interviewer-bubble">
                  <div class="turn-header-tag">
                    <span v-if="turn.is_drill_down" class="badge-drilldown">AI Adaptive Probe</span>
                    <span v-else-if="turn.question_type === 'MULTIPLE_CHOICE'" class="badge-mc">Multiple Choice Challenge</span>
                    <span v-else class="badge-turn">Question #{{ turn.turn_index }}</span>
                  </div>
                  <div class="msg-text">{{ turn.question }}</div>
                </div>
              </div>

              <!-- Candidate Answer Bubble (optimistically updated or loaded) -->
              <div v-if="turn.user_answer || turn.selected_option" class="msg-row user-row">
                <div class="avatar-icon user-avatar">
                  <User :size="16" />
                </div>
                <div class="msg-bubble user-bubble">
                  <div v-if="turn.attempt_count > 1" class="attempt-tag">Attempt #{{ turn.attempt_count }}</div>
                  <div v-if="turn.selected_option" class="selected-option-pill">
                    Selected Option: <strong>{{ turn.selected_option }}</strong>
                  </div>
                  <div v-if="turn.user_answer" class="msg-text">{{ turn.user_answer }}</div>
                </div>
              </div>

              <!-- Turn Evaluation Loader (visible right below user's response while evaluation generates) -->
              <div v-if="interviewStore.isEvaluating && interviewStore.currentTurnIndex === turn.turn_index" class="msg-row interviewer-row animate-fade-in">
                <div class="avatar-icon interviewer-avatar">
                  <Sparkles :size="16" />
                </div>
                <div class="msg-bubble thinking-bubble">
                  <Loader2 class="animate-spin" :size="16" />
                  <span>Interviewer is evaluating your response...</span>
                </div>
              </div>

              <!-- Conversational Interviewer Response Bubble (Natural In-Thread Dialogue) -->
              <div v-if="turn.evaluation" class="msg-row interviewer-row animate-fade-in">
                <div class="avatar-icon interviewer-avatar">
                  <Sparkles :size="16" />
                </div>
                <div class="msg-bubble interviewer-bubble interviewer-feedback-bubble">
                  <div class="turn-header-tag">
                    <span class="badge-feedback">Interviewer Feedback</span>
                  </div>
                  <div class="msg-text">
                    {{ turn.evaluation.constructive_critique || turn.evaluation.interviewer_feedback || 'Thank you for sharing that experience.' }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Loading State for Next Question / Drill Down -->
            <div v-if="interviewStore.isGeneratingQuestion" class="msg-row interviewer-row animate-fade-in">
              <div class="avatar-icon interviewer-avatar">
                <Sparkles :size="16" />
              </div>
              <div class="msg-bubble thinking-bubble">
                <Loader2 class="animate-spin" :size="16" />
                <span>Synthesizing next challenge tailored to your background...</span>
              </div>
            </div>
          </div>

          <!-- Bottom Control Floor (Unified chat-bottom-dock style) -->
          <div class="chat-bottom-dock">
            <div class="bottom-dock-inner">
              <!-- Choices Bar (When answering Multiple Choice question) -->
              <div
                v-if="shouldShowMCChoices"
                class="starters-bar mc-choices-bar"
              >
                <button
                  v-for="opt in interviewStore.currentTurn.options"
                  :key="opt.key"
                  class="starter-chip mc-choice-chip"
                  :class="{ active: selectedOptionKey === opt.key }"
                  @click="handleSelectChoice(opt.key)"
                >
                  <span class="mc-chip-key">{{ opt.key }}</span>
                  <span class="mc-chip-text">{{ opt.text }}</span>
                </button>
              </div>

              <!-- Progression Bar (When turn is evaluated and not actively refining) -->
              <div
                v-else-if="interviewStore.currentTurn?.evaluation && !isRefining && !interviewStore.isGeneratingQuestion && !interviewStore.isEvaluating"
                class="starters-bar progression-bar"
              >
                <button
                  class="starter-chip starter-chip-primary"
                  :disabled="interviewStore.isGeneratingQuestion"
                  @click="handleNextQuestion"
                >
                  <ArrowRight :size="13" />
                  <span>Next Question</span>
                </button>

                <button
                  class="starter-chip"
                  :disabled="interviewStore.isGeneratingQuestion"
                  @click="handleDrillDown"
                >
                  <Sparkles :size="13" />
                  <span>Drill Deeper</span>
                </button>

                <button
                  class="starter-chip"
                  @click="prepareRefineAnswer"
                >
                  <RotateCcw :size="13" />
                  <span>Refine Answer</span>
                </button>
              </div>

              <!-- Single-line Input Bar -->
              <div class="chat-input-bar">
                <textarea
                  ref="interviewInputRef"
                  v-model="candidateAnswer"
                  :rows="isConversationalOrHybrid ? 2 : 1"
                  :disabled="interviewStore.isEvaluating || interviewStore.isGeneratingQuestion"
                  :placeholder="interviewStore.isEvaluating ? 'Interviewer is evaluating your response...' : (interviewStore.isGeneratingQuestion ? 'Synthesizing next challenge...' : (interviewStore.currentTurn?.options?.length ? '(Optional) Add technical rationale or click Send / press Enter...' : 'Type your response (Situation, Task, Action, Result)...'))"
                  class="chat-input interview-chat-input"
                  :class="{ 'chat-input-expanded': isConversationalOrHybrid }"
                  @input="handleAutoResize"
                  @keydown.enter.exact.prevent="handleEvaluateAnswer"
                ></textarea>

                <button
                  class="btn btn-primary btn-send"
                  :disabled="interviewStore.isEvaluating || interviewStore.isGeneratingQuestion || (interviewStore.currentTurn?.options?.length && !interviewStore.currentTurn?.evaluation ? !selectedOptionKey : !candidateAnswer.trim())"
                  @click="handleEvaluateAnswer"
                >
                  <Loader2 v-if="interviewStore.isEvaluating" class="animate-spin" :size="15" />
                  <Send v-else :size="15" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- POST-SESSION DEBRIEF SCORECARD -->
        <div v-else-if="interviewStore.currentSession.status === 'COMPLETED'" class="debrief-scorecard-screen">
          <div class="scorecard-card animate-fade-in">
            <div class="scorecard-header">
              <div class="badge-readiness" :class="getReadinessBadgeClass(interviewStore.currentSession.readiness_rating)">
                {{ interviewStore.currentSession.readiness_rating?.replace('_', ' ') }}
              </div>
              <h2 class="scorecard-title">Interview Simulation Scorecard</h2>
              <div class="scorecard-score-banner">
                <span class="final-score-val">{{ interviewStore.overallScore !== null && interviewStore.overallScore !== undefined ? interviewStore.overallScore : '--' }}</span>
                <span class="final-score-max">/ 100 Overall Score</span>
              </div>
            </div>

            <div class="scorecard-body">
              <!-- Top Strengths & Focus Areas Grid -->
              <div class="summary-grid">
                <div class="summary-card">
                  <div class="summary-card-title text-success">
                    <CheckCircle2 :size="16" />
                    <span>Key Standout Strengths</span>
                  </div>
                  <ul class="summary-list">
                    <li v-for="(s, i) in interviewStore.currentSession.summary_feedback?.key_strengths || []" :key="i">{{ s }}</li>
                  </ul>
                </div>

                <div class="summary-card">
                  <div class="summary-card-title text-danger">
                    <TrendingUp :size="16" />
                    <span>Top Priority Focus Areas</span>
                  </div>
                  <ul class="summary-list">
                    <li v-for="(g, i) in interviewStore.currentSession.summary_feedback?.top_improvement_areas || []" :key="i">{{ g }}</li>
                  </ul>
                </div>
              </div>

              <!-- Per-Question Performance Breakdown -->
              <div class="turns-breakdown-section">
                <h4 class="section-subtitle">Performance Breakdown</h4>
                <div class="turns-list">
                  <div
                    v-for="turn in interviewStore.turns"
                    :key="turn.turn_index"
                    class="turn-summary-card"
                  >
                    <div class="turn-summary-top">
                      <span class="turn-idx">Question #{{ turn.turn_index }}</span>
                      <span v-if="turn.evaluation" class="turn-score">{{ turn.evaluation.score }}/100</span>
                    </div>
                    <div class="turn-q-text">{{ turn.question }}</div>
                    <div v-if="turn.evaluation?.constructive_critique" class="turn-critique">
                      {{ turn.evaluation.constructive_critique }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="scorecard-footer">
              <div class="scorecard-continuation-banner">
                <span class="continuation-label">Practice More with this Role:</span>
                <div class="continuation-modes-btn-group">
                  <button
                    class="btn btn-secondary btn-sm"
                    :disabled="interviewStore.isInitializing"
                    @click="handleStartAnotherSimulation('TEXT_CONVERSATIONAL')"
                  >
                    <MessageSquare :size="13" />
                    <span>Conversational</span>
                  </button>
                  <button
                    class="btn btn-secondary btn-sm"
                    :disabled="interviewStore.isInitializing"
                    @click="handleStartAnotherSimulation('MULTIPLE_CHOICE')"
                  >
                    <CheckCircle2 :size="13" />
                    <span>Multiple Choice</span>
                  </button>
                  <button
                    class="btn btn-secondary btn-sm"
                    :disabled="interviewStore.isInitializing"
                    @click="handleStartAnotherSimulation('HYBRID')"
                  >
                    <Layers :size="13" />
                    <span>Hybrid</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.chat-page-container {
  display: flex;
  height: calc(100vh - var(--navbar-height));
  width: 100%;
  background-color: var(--bg-app);
  position: relative;
  overflow: hidden;
}

.chat-sidebar {
  width: 260px;
  height: 100%;
  flex-shrink: 0;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background-color: var(--bg-surface);
  transition: width var(--transition-smooth), margin-left var(--transition-smooth), opacity var(--transition-smooth);
  overflow: hidden;
  white-space: nowrap;
}

.chat-sidebar.collapsed {
  width: 0;
  border-right-color: transparent;
  opacity: 0;
  pointer-events: none;
}

.sidebar-header {
  height: 65px;
  box-sizing: border-box;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-new-chat-sidebar {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  border: none;
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-new-chat-sidebar:hover {
  opacity: 0.9;
}

.btn-icon-sidebar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.btn-icon-sidebar:hover {
  color: var(--text-main);
  background-color: var(--bg-hover);
  border-color: var(--border-color);
}

.btn-expand-sidebar {
  margin-right: 4px;
}

.sidebar-search-box {
  position: relative;
  padding: 10px 12px 4px;
  flex-shrink: 0;
}

.sidebar-search-icon {
  position: absolute;
  left: 22px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.sidebar-search-input {
  width: 100%;
  padding: 7px 10px 7px 30px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-main);
  font-size: 12.5px;
  box-sizing: border-box;
  transition: border-color var(--transition-fast);
}

.sidebar-search-input:focus {
  outline: none;
  border-color: var(--primary);
}

.chats-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chats-loading, .no-chats {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60px;
  color: var(--text-secondary);
  font-size: 13px;
}

.chat-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  margin-bottom: 4px;
  transition: background-color var(--transition-fast);
  color: var(--text-main);
}

.chat-list-item:hover {
  background-color: var(--bg-hover);
}

.chat-list-item.active {
  background-color: var(--bg-active);
  font-weight: 500;
}

.chat-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.chat-icon {
  color: var(--text-secondary);
  flex-shrink: 0;
}

.chat-title {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-delete-chat {
  opacity: 0;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
}

.chat-list-item:hover .btn-delete-chat {
  opacity: 1;
}

.btn-delete-chat:hover {
  color: var(--danger);
  background-color: var(--danger-subtle);
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-surface-alt);
}

.retention-setting {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.retention-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.retention-select {
  width: 100%;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-main);
  font-size: 13px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  margin-left: 0;
  position: relative;
  background-color: var(--bg-app);
}

.chat-header {
  height: 65px;
  box-sizing: border-box;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-app);
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.header-content-inner {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-switcher-pill {
  display: flex;
  align-items: center;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  padding: 4px;
  gap: 4px;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mode-btn.active {
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  font-weight: 600;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 24px 16px;
}

.chat-messages-inner {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.message-row {
  display: flex;
  gap: 14px;
  width: 100%;
  max-width: 100%;
}

.msg-user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.avatar-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--text-secondary);
}

.msg-user .avatar-icon {
  background-color: var(--primary);
  color: #fff;
  border: none;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-main);
}

.msg-user .message-bubble {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary);
}

.actions-chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.action-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
  font-size: 11px;
  font-weight: 600;
}

.message-text {
  white-space: pre-wrap;
}

.markdown-body {
  white-space: normal;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text-main);
}

.chat-bottom-dock {
  flex-shrink: 0;
  padding: 0 24px 24px;
  background-color: var(--bg-app);
}

.bottom-dock-inner {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.starters-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.starter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.starter-chip:hover {
  background-color: var(--bg-hover);
  color: var(--text-main);
  border-color: var(--primary);
}

.chat-input-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 8px 12px;
  box-shadow: var(--shadow-sm);
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  resize: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
}

.btn-send {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  padding: 0;
}

/* INTERVIEW SETUP SCREEN STYLES */
.interview-setup-screen {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 36px 24px 60px;
  overflow-y: auto;
}

.setup-card {
  max-width: 680px;
  width: 100%;
  margin: 0 auto;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 36px;
  box-shadow: var(--shadow-md);
}

.setup-header {
  text-align: center;
  margin-bottom: 28px;
}

.setup-icon-box {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  background-color: var(--primary-subtle);
  border: 1px solid var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.setup-title {
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}

.setup-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.setup-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 6px;
}

.persona-card {
  padding: 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.persona-card:hover {
  border-color: var(--primary);
}

.persona-card.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.persona-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.persona-icon {
  color: var(--primary);
}

.persona-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.persona-card-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 0;
}

.setup-actions {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

/* HEADER & SIDEBAR STYLES */
.header-end-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 14px;
}

.active-session-pinned {
  border-left: 3px solid var(--primary) !important;
  background-color: var(--primary-subtle);
}

.session-status-live {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--status-interview-text);
  font-weight: 700;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--status-interview-text);
  animation: pulse-ring 1.5s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.9); opacity: 0.8; }
  50% { transform: scale(1.4); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.8; }
}

/* FULL-WIDTH INTERVIEW FLOOR STYLES */
.interview-floor-full {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: calc(100% - 65px);
  overflow: hidden;
  background-color: var(--bg-app);
}

.floor-thread {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.turn-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
}

.msg-row {
  display: flex;
  gap: 12px;
  max-width: 88%;
}

.interviewer-row {
  margin-right: auto;
}

.user-row {
  margin-left: auto;
  flex-direction: row-reverse;
}

.interviewer-avatar {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border-color: var(--primary-glow);
}

.user-avatar {
  background-color: var(--primary);
  color: #fff;
}

.msg-bubble {
  padding: 14px 18px;
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.55;
  color: var(--text-main);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-xs);
}

.user-bubble {
  background-color: var(--primary-subtle);
  color: var(--text-main);
  border-color: var(--primary);
}

.interviewer-feedback-bubble {
  border-left: 3px solid var(--primary);
}

.turn-header-tag {
  margin-bottom: 6px;
}

.badge-turn {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
  text-transform: uppercase;
}

.badge-drilldown {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
}

.badge-mc {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary);
}

.badge-feedback {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
}

.attempt-tag {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.selected-option-pill {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  margin-bottom: 6px;
}

/* BOTTOM DOCK ACTION CHIPS */
.mc-choices-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
  width: 100%;
}

.mc-choice-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-main);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
}

.mc-choice-chip:hover {
  border-color: var(--primary);
  background-color: var(--bg-hover);
}

.mc-choice-chip.active {
  background-color: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.mc-chip-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  font-weight: 700;
  font-size: 11px;
  flex-shrink: 0;
}

.mc-choice-chip.active .mc-chip-key {
  background-color: rgba(255, 255, 255, 0.25);
  color: #fff;
}

.mc-chip-text {
  flex: 1;
  line-height: 1.4;
}

.progression-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.starter-chip-primary {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border-color: var(--primary-glow);
  font-weight: 600;
}

.starter-chip-primary:hover {
  background-color: var(--primary);
  color: #fff;
}

.action-chip-interactive {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-chip-interactive:hover {
  background-color: var(--primary);
  color: #fff;
}

/* DEBRIEF SCORECARD STYLES */
.debrief-scorecard-screen {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 36px 24px 60px;
  overflow-y: auto;
}

.scorecard-card {
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 36px;
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.scorecard-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.badge-readiness {
  font-size: 12px;
  font-weight: 800;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.readiness-strong { background-color: var(--status-offer-bg); color: var(--status-offer-text); border: 1px solid var(--status-offer-border); }
.readiness-hire { background-color: var(--status-interview-bg); color: var(--status-interview-text); border: 1px solid var(--status-interview-border); }
.readiness-work { background-color: var(--status-rejected-bg); color: var(--status-rejected-text); border: 1px solid var(--status-rejected-border); }
.readiness-incomplete { background-color: var(--bg-surface-hover); color: var(--text-muted); border: 1px solid var(--border-color); }

.scorecard-title {
  font-family: var(--font-heading);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.scorecard-score-banner {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.final-score-val {
  font-size: 42px;
  font-weight: 800;
  color: var(--primary);
  font-family: var(--font-mono);
}

.final-score-max {
  font-size: 14px;
  color: var(--text-muted);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.summary-card {
  padding: 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
}

.summary-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}

.summary-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.turns-breakdown-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-subtitle {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.turns-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.turn-summary-card {
  padding: 14px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
}

.turn-summary-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.turn-idx {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
}

.turn-score {
  font-size: 12px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-main);
}

.turn-q-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 4px;
}

.turn-critique {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.interview-chat-input.chat-input-expanded {
  min-height: 52px;
  max-height: 180px;
  resize: vertical;
  line-height: 1.5;
}

.scorecard-footer {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.scorecard-continuation-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  flex-wrap: wrap;
}

.continuation-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.continuation-modes-btn-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.scorecard-actions-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

/* INTERVIEW SIDEBAR STYLES */
.interview-session-item {
  padding: 10px 12px;
}

.session-sidebar-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.session-sidebar-title {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-main);
}

.session-sidebar-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.session-score-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.session-status-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background-color: var(--status-assessment-bg);
  color: var(--status-assessment-text);
  border: 1px solid var(--status-assessment-border);
}

.session-status-tag.session-status-closed {
  background-color: var(--bg-surface-hover);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}

.session-date-tag {
  font-size: 11px;
  color: var(--text-muted);
}

.interview-sidebar-hint {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}

/* TARGET APPLICATION SEARCHABLE PICKER STYLES */
.target-app-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}

.target-app-subtitle {
  font-size: 11px;
  color: var(--text-muted);
}

.app-search-wrapper {
  position: relative;
  margin-bottom: 8px;
}

.app-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.app-search-input {
  width: 100%;
  padding: 9px 12px 9px 34px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  color: var(--text-main);
  font-size: 13px;
  transition: border-color var(--transition-fast);
}

.app-search-input:focus {
  outline: none;
  border-color: var(--primary);
}

.app-selectable-list-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 226px;
  overflow-y: auto;
  padding-right: 4px;
}

.app-selectable-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.app-selectable-card:hover {
  border-color: var(--primary);
  background-color: var(--bg-hover);
}

.app-selectable-card.card-active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.card-check-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.icon-active {
  color: var(--primary);
}

.icon-inactive {
  color: var(--text-muted);
}

.app-card-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.app-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.app-card-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.35;
}

.app-card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.app-company-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.app-position-title {
  font-size: 12px;
  color: var(--text-secondary);
}

.app-status-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.badge-applied { background-color: var(--status-applied-bg); color: var(--status-applied-text); border: 1px solid var(--status-applied-border); }
.badge-online_assessment { background-color: var(--status-assessment-bg); color: var(--status-assessment-text); border: 1px solid var(--status-assessment-border); }
.badge-technical_interview { background-color: var(--status-interview-bg); color: var(--status-interview-text); border: 1px solid var(--status-interview-border); }

.app-no-results {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  background-color: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-color);
}

/* QUESTION FORMAT / MODE STYLES */
.question-mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 6px;
}

.question-mode-card {
  padding: 14px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.question-mode-card:hover {
  border-color: var(--primary);
}

.question-mode-card.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.question-mode-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.mode-title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-icon {
  color: var(--primary);
  flex-shrink: 0;
}

.question-mode-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.question-mode-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-full);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.question-mode-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.35;
  margin: 0;
}

/* MULTIPLE CHOICE FLOOR & PICKER STYLES */
.badge-mc {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.mc-options-display {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.mc-option-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mc-option-card:hover:not(.evaluated-choice) {
  border-color: var(--primary);
  background-color: var(--bg-hover);
}

.mc-option-card.selected-choice {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.mc-option-key-badge {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
  flex-shrink: 0;
}

.mc-option-card.selected-choice .mc-option-key-badge {
  background-color: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.mc-option-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mc-option-text {
  font-size: 13px;
  color: var(--text-main);
  line-height: 1.4;
}

.mc-option-explanation {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.35;
  padding-top: 4px;
  border-top: 1px dashed var(--border-color);
}

.selected-option-pill {
  font-size: 12px;
  color: var(--primary);
  margin-bottom: 4px;
}

.mc-quick-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.mc-picker-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.mc-picker-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.mc-picker-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
}

.mc-picker-btn:hover {
  border-color: var(--primary);
}

.mc-picker-btn.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
  color: var(--primary);
}

.btn-opt-key {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-full);
  background-color: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.mc-picker-btn.active .btn-opt-key {
  background-color: var(--primary);
  color: #fff;
}

.btn-opt-text {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* RESPONSIVE ADAPTATIONS */
@media (max-width: 767px) {
  .sidebar-backdrop {
    position: fixed;
    inset: 0;
    top: var(--navbar-height, 65px);
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 940;
  }

  .chat-sidebar {
    position: fixed;
    top: var(--navbar-height, 65px);
    left: 0;
    bottom: 0;
    z-index: 950;
    width: 280px;
    max-width: 85vw;
    box-shadow: var(--shadow-xl);
    transform: translateX(0);
    transition: transform var(--transition-smooth, 0.25s ease), opacity var(--transition-smooth, 0.25s ease);
  }

  .chat-sidebar.collapsed {
    transform: translateX(-100%);
    width: 280px;
    opacity: 0;
    pointer-events: none;
  }

  .chat-header {
    padding: 0 12px;
    height: 56px;
  }

  .mode-switcher-pill {
    padding: 2px;
    gap: 2px;
  }

  .mode-btn {
    padding: 5px 10px;
    font-size: 11.5px;
    gap: 4px;
    min-height: 36px;
  }

  .mode-btn span {
    font-size: 11px;
  }

  .chat-messages {
    padding: 16px 12px 12px;
  }

  .message-row, .msg-row {
    max-width: 95%;
  }

  .message-bubble, .msg-bubble {
    padding: 10px 14px;
    font-size: 13px;
  }

  .markdown-body pre,
  .markdown-body :deep(pre) {
    overflow-x: auto;
    max-width: 100%;
  }

  .markdown-body table,
  .markdown-body :deep(table) {
    display: block;
    overflow-x: auto;
    max-width: 100%;
  }

  .chat-bottom-dock {
    padding: 0 12px 12px;
    padding-bottom: max(12px, env(safe-area-inset-bottom));
  }

  .chat-input {
    font-size: 16px; /* Prevents auto-zoom on iOS safari */
    min-height: 44px;
  }

  .btn-send {
    width: 44px;
    height: 44px;
    min-width: 44px;
  }

  .interview-setup-screen {
    padding: 16px 12px 32px;
  }

  .setup-card {
    padding: 20px 16px;
  }

  .question-mode-grid {
    grid-template-columns: 1fr;
  }

  .persona-grid {
    grid-template-columns: 1fr;
  }

  .app-selectable-card {
    padding: 10px 12px;
    min-height: 48px;
  }

  .floor-thread {
    padding: 16px 12px;
  }

  .debrief-scorecard-screen {
    padding: 16px 12px 32px;
  }

  .scorecard-card {
    padding: 20px 16px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .scorecard-continuation-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .continuation-modes-btn-group {
    width: 100%;
  }

  .continuation-modes-btn-group .btn {
    flex: 1;
    min-height: 44px;
  }
}
</style>
