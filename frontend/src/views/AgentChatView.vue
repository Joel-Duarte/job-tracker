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
  FileText
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

const starterPrompts = [
  'Which applications currently require urgent action from me?',
  'Find roles involving Python, Distributed Systems, or Staff engineering',
  'What is the current status of my Stripe application?',
  'Move Stripe to OFFER status',
]

// Mock Interview Setup & HUD State
const mockAppId = ref(null)
const mockPersona = ref('TECHNICAL_BAR_RAISER')
const candidateAnswer = ref('')

// Voice dictation (Web Speech API)
const isRecording = ref(false)
const speechSupported = ref(false)
let recognitionInstance = null

const PERSONAS = [
  {
    id: 'TECHNICAL_BAR_RAISER',
    title: 'Technical Bar Raiser',
    icon: Shield,
    desc: 'Deep dives into system design, concurrency, edge cases, distributed tradeoffs, and algorithmic efficiency.'
  },
  {
    id: 'HIRING_MANAGER',
    title: 'Hiring Manager',
    icon: Briefcase,
    desc: 'Focuses on team leadership, project delivery, cross-functional ownership, and engineering impact.'
  },
  {
    id: 'BEHAVIORAL_CULTURE',
    title: 'Behavioral & Culture Fit',
    icon: Users,
    desc: 'Evaluates STAR structure, stakeholder communication, overcoming failure, and culture alignment.'
  },
  {
    id: 'SUPPORTIVE_COACH',
    title: 'Supportive Practice Coach',
    icon: GraduationCap,
    desc: 'Empathetic and encouraging tone suited for initial warmups with constructive STAR suggestions.'
  }
]

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

onMounted(async () => {
  await appStore.fetchApplications()
  await chatStore.fetchChats()

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

watch(() => chatStore.messages.length, () => {
  scrollToBottom()
})

watch(() => route.query, (newQuery) => {
  if (newQuery.mock === 'true' || newQuery.appId) {
    activeMode.value = 'interview'
    if (newQuery.appId) {
      mockAppId.value = parseInt(newQuery.appId)
    }
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
async function handleStartInterviewSession() {
  try {
    await interviewStore.startSession(mockAppId.value, mockPersona.value)
    candidateAnswer.value = ''
    scrollToBottom()
  } catch (err) {
    uiStore.showToast("Failed to start mock interview session", "error")
  }
}

async function handleEvaluateAnswer() {
  if (!candidateAnswer.value.trim() || interviewStore.isEvaluating) return
  const currentTurnIdx = interviewStore.currentTurnIndex
  const text = candidateAnswer.value.trim()
  try {
    await interviewStore.evaluateAnswer(currentTurnIdx, text)
    candidateAnswer.value = ''
    scrollToBottom()
  } catch (err) {
    uiStore.showToast("Failed to evaluate answer", "error")
  }
}

async function handleNextQuestion() {
  try {
    await interviewStore.nextQuestion()
    candidateAnswer.value = ''
    scrollToBottom()
  } catch (err) {
    uiStore.showToast("Failed to generate next question", "error")
  }
}

async function handleDrillDown() {
  try {
    await interviewStore.drillDown()
    candidateAnswer.value = ''
    scrollToBottom()
  } catch (err) {
    uiStore.showToast("Failed to generate drill-down question", "error")
  }
}

function prepareRefineAnswer() {
  if (interviewStore.currentTurn?.user_answer) {
    candidateAnswer.value = interviewStore.currentTurn.user_answer
  }
}

async function handleFinalizeSession() {
  try {
    await interviewStore.finalizeSession()
    uiStore.showToast("Interview simulation completed!", "success")
  } catch (err) {
    uiStore.showToast("Failed to finalize session", "error")
  }
}

async function handleSaveNotes() {
  try {
    await interviewStore.saveNotes()
    uiStore.showToast("Debrief notes saved to Application Notes!", "success")
  } catch (err) {
    uiStore.showToast("Failed to save notes", "error")
  }
}

// Chat Assistant Actions
async function handleSendMessage(textToSend = null) {
  const text = textToSend || inputMessage.value.trim()
  if (!text || chatStore.isSending) return

  inputMessage.value = ''
  await chatStore.sendMessage(text)
  scrollToBottom()
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendMessage()
  }
}

function handleResetChat() {
  chatStore.resetChat()
  scrollToBottom()
}

async function handleLoadChat(id) {
  await chatStore.loadChat(id)
  scrollToBottom()
}

async function handleDeleteChat(id) {
  await chatStore.deleteChat(id)
}

async function handleRetentionChange() {
  isUpdatingRetention.value = true
  try {
    await AIConfigAPI.updateGlobalSettings({
      AGENT_CHAT_RETENTION_DAYS: parseInt(retentionDays.value)
    })
  } catch (err) {
    console.error("Failed to update retention setting", err)
  } finally {
    isUpdatingRetention.value = false
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function renderMarkdown(text) {
  if (!text) return ''

  let html = escapeHtml(text)
  html = html.replace(/```([\s\S]*?)```/g, (match, p1) => `<pre><code>${p1.trim()}</code></pre>`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  const lines = html.split('\n')
  let inTable = false
  let tableHtml = ''
  let newLines = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line.startsWith('|') && line.endsWith('|')) {
      const cells = line.split('|').slice(1, -1).map(c => c.trim())
      if (cells.every(c => /^:?-+:?$/.test(c))) continue
      if (!inTable) {
        inTable = true
        tableHtml = '<table><thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>'
      } else {
        tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>'
      }
    } else {
      if (inTable) {
        tableHtml += '</tbody></table>'
        newLines.push(tableHtml)
        inTable = false
        tableHtml = ''
      }
      newLines.push(lines[i])
    }
  }
  if (inTable) {
    tableHtml += '</tbody></table>'
    newLines.push(tableHtml)
  }
  html = newLines.join('\n')

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
  return `Executed: ${act.action || 'Tool'}`
}

function getReadinessBadgeClass(rating) {
  if (rating === 'STRONG_HIRE') return 'readiness-strong'
  if (rating === 'HIRE') return 'readiness-hire'
  return 'readiness-work'
}
</script>

<template>
  <div class="chat-page-container" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">

    <!-- Sidebar (For Assistant Mode) -->
    <div v-if="activeMode === 'assistant'" class="chat-sidebar" :class="{ 'collapsed': isSidebarCollapsed }">
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

      <div class="chats-list">
        <div v-if="chatStore.isLoadingChats" class="chats-loading">
          <Loader2 class="animate-spin" :size="20" />
        </div>
        <div v-else-if="chatStore.chatsList.length === 0" class="no-chats">
          No previous chats
        </div>
        <div v-else class="chats-list-scroll">
          <div
            v-for="chat in chatStore.chatsList"
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

      <div class="sidebar-footer">
        <div class="retention-setting">
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
      </div>
    </div>

    <!-- Main Workspace Area -->
    <div class="chat-main">
      <!-- Mode Switcher Top Header -->
      <div class="chat-header">
        <div class="header-content-inner">
          <div class="header-left">
            <button
              v-if="activeMode === 'assistant' && isSidebarCollapsed"
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
                    <div v-for="(act, aIdx) in msg.actions" :key="aIdx" class="action-chip">
                      <CheckCircle2 :size="13" class="text-success" />
                      <span>{{ formatActionLabel(act) }}</span>
                    </div>
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
              <h2 class="setup-title">Interactive Real-Time Mock Interview</h2>
              <p class="setup-subtitle">
                Practice realistic interview rounds with AI personas, STAR rubric analysis, and real-time coaching scorecards.
              </p>
            </div>

            <div class="setup-form">
              <!-- Target Application Picker -->
              <div class="form-group">
                <label class="form-label">Target Application (Optional)</label>
                <select v-model="mockAppId" class="form-select">
                  <option :value="null">🎯 General Technical & Behavioral Practice (No Application)</option>
                  <option
                    v-for="app in appStore.applications"
                    :key="app.id"
                    :value="app.id"
                  >
                    {{ app.company?.name || 'Company' }} — {{ app.position || 'Position' }} ({{ app.status }})
                  </option>
                </select>
              </div>

              <!-- Persona Picker -->
              <div class="form-group">
                <label class="form-label">Select Interviewer Persona</label>
                <div class="persona-grid">
                  <div
                    v-for="p in PERSONAS"
                    :key="p.id"
                    class="persona-card"
                    :class="{ active: mockPersona === p.id }"
                    @click="mockPersona = p.id"
                  >
                    <div class="persona-card-header">
                      <component :is="p.icon" :size="18" class="persona-icon" />
                      <span class="persona-card-title">{{ p.title }}</span>
                    </div>
                    <p class="persona-card-desc">{{ p.desc }}</p>
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

        <!-- ACTIVE SESSION HUD & SPLIT PANE -->
        <div v-else-if="interviewStore.currentSession.status === 'IN_PROGRESS'" class="simulator-split-pane">
          <!-- LEFT PANE: INTERVIEW FLOOR -->
          <div class="interview-floor">
            <!-- Questions & Answers Thread -->
            <div ref="chatContainer" class="floor-thread">
              <div
                v-for="turn in interviewStore.turns"
                :key="turn.turn_index"
                class="turn-block"
              >
                <!-- Question Bubble -->
                <div class="msg-row interviewer-row">
                  <div class="avatar-icon interviewer-avatar">
                    <Sparkles :size="16" />
                  </div>
                  <div class="msg-bubble interviewer-bubble">
                    <div class="turn-header-tag">
                      <span v-if="turn.is_drill_down" class="badge-drilldown">AI Adaptive Probe</span>
                      <span v-else class="badge-turn">Question #{{ turn.turn_index }}</span>
                    </div>
                    <div class="msg-text">{{ turn.question }}</div>
                  </div>
                </div>

                <!-- User Answer Bubble (if submitted) -->
                <div v-if="turn.user_answer" class="msg-row user-row">
                  <div class="avatar-icon user-avatar">
                    <User :size="16" />
                  </div>
                  <div class="msg-bubble user-bubble">
                    <div v-if="turn.attempt_count > 1" class="attempt-tag">Attempt #{{ turn.attempt_count }}</div>
                    <div class="msg-text">{{ turn.user_answer }}</div>
                  </div>
                </div>
              </div>

              <!-- Loading State for Next Question / Drill Down -->
              <div v-if="interviewStore.isGeneratingQuestion" class="msg-row interviewer-row">
                <div class="avatar-icon interviewer-avatar">
                  <Sparkles :size="16" />
                </div>
                <div class="msg-bubble thinking-bubble">
                  <Loader2 class="animate-spin" :size="16" />
                  <span>Synthesizing next challenge...</span>
                </div>
              </div>
            </div>

            <!-- Bottom Control Floor / Answer Box & HUD Action Bar -->
            <div class="floor-bottom-controls">
              <!-- Evaluation Status & HUD Actions Bar -->
              <div v-if="interviewStore.currentTurn?.evaluation" class="hud-action-bar">
                <button
                  class="btn btn-secondary btn-sm"
                  :disabled="interviewStore.isGeneratingQuestion"
                  @click="handleNextQuestion"
                >
                  <ArrowRight :size="14" />
                  <span>Next Question</span>
                </button>

                <button
                  class="btn btn-secondary btn-sm"
                  :disabled="interviewStore.isGeneratingQuestion"
                  @click="handleDrillDown"
                >
                  <Sparkles :size="14" />
                  <span>Drill Deeper (AI Challenge)</span>
                </button>

                <button
                  class="btn btn-secondary btn-sm"
                  @click="prepareRefineAnswer"
                >
                  <RotateCcw :size="14" />
                  <span>Refine Answer</span>
                </button>

                <button
                  class="btn btn-danger btn-sm text-danger ml-auto"
                  :disabled="interviewStore.isFinalizing"
                  @click="handleFinalizeSession"
                >
                  <Flag :size="14" />
                  <span>End Session</span>
                </button>
              </div>

              <!-- Input Area (Active when question is unevaluated or user is refining) -->
              <div v-else class="answer-input-container">
                <div class="answer-textarea-box">
                  <textarea
                    v-model="candidateAnswer"
                    rows="3"
                    placeholder="Type or dictate your STAR response (Situation, Task, Action, Result)..."
                    class="answer-textarea"
                  ></textarea>

                  <div class="textarea-footer">
                    <div class="char-count">{{ candidateAnswer.length }} chars</div>

                    <div class="input-actions-right">
                      <!-- Voice Transcription Button -->
                      <button
                        type="button"
                        class="btn-voice-dictation"
                        :class="{ recording: isRecording }"
                        :disabled="!speechSupported"
                        :title="speechSupported ? (isRecording ? 'Stop Voice Input' : 'Start Voice Input') : 'Voice input not supported in this browser — please type your answer.'"
                        @click="toggleVoiceInput"
                      >
                        <MicOff v-if="!speechSupported" :size="15" />
                        <Mic v-else :size="15" />
                        <span v-if="isRecording" class="recording-pulse"></span>
                      </button>

                      <button
                        class="btn btn-primary btn-submit-answer"
                        :disabled="interviewStore.isEvaluating || !candidateAnswer.trim()"
                        @click="handleEvaluateAnswer"
                      >
                        <Loader2 v-if="interviewStore.isEvaluating" class="animate-spin" :size="15" />
                        <Send v-else :size="15" />
                        <span>Submit & Evaluate</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- RIGHT PANE: LIVE COACHING & STAR METER -->
          <div class="live-coaching-pane">
            <div class="coaching-header">
              <span class="coaching-title">Live Interview Coaching</span>
              <span class="persona-chip">{{ interviewStore.activePersona }}</span>
            </div>

            <!-- Cumulative Score Gauge -->
            <div class="score-card">
              <div class="score-circle">
                <span class="score-number">{{ interviewStore.overallScore }}</span>
                <span class="score-denom">/100</span>
              </div>
              <div class="score-label">Real-Time Fit Score</div>
            </div>

            <!-- STAR Rubric Meter -->
            <div v-if="interviewStore.latestEvaluation" class="star-meter-card">
              <div class="card-label">STAR Structure Coverage</div>
              <div class="star-badges-grid">
                <div
                  class="star-badge"
                  :class="{ active: interviewStore.latestEvaluation.star_presence?.situation }"
                >
                  <Check v-if="interviewStore.latestEvaluation.star_presence?.situation" :size="12" />
                  <span>Situation</span>
                </div>

                <div
                  class="star-badge"
                  :class="{ active: interviewStore.latestEvaluation.star_presence?.task }"
                >
                  <Check v-if="interviewStore.latestEvaluation.star_presence?.task" :size="12" />
                  <span>Task</span>
                </div>

                <div
                  class="star-badge"
                  :class="{ active: interviewStore.latestEvaluation.star_presence?.action }"
                >
                  <Check v-if="interviewStore.latestEvaluation.star_presence?.action" :size="12" />
                  <span>Action</span>
                </div>

                <div
                  class="star-badge"
                  :class="{ active: interviewStore.latestEvaluation.star_presence?.result }"
                >
                  <Check v-if="interviewStore.latestEvaluation.star_presence?.result" :size="12" />
                  <span>Result</span>
                </div>
              </div>
            </div>

            <!-- Feedback Breakdown -->
            <div v-if="interviewStore.latestEvaluation" class="coaching-details-scroll">
              <!-- Strengths -->
              <div v-if="interviewStore.latestEvaluation.strengths?.length" class="feedback-box strengths-box">
                <div class="feedback-title text-success">
                  <CheckCircle2 :size="14" />
                  <span>Key Strengths Identified</span>
                </div>
                <ul class="feedback-list">
                  <li v-for="(s, i) in interviewStore.latestEvaluation.strengths" :key="i">{{ s }}</li>
                </ul>
              </div>

              <!-- Gaps / Missing Items -->
              <div v-if="interviewStore.latestEvaluation.missing_gaps?.length" class="feedback-box gaps-box">
                <div class="feedback-title text-danger">
                  <AlertCircle :size="14" />
                  <span>Missing Gaps &amp; Opportunities</span>
                </div>
                <ul class="feedback-list">
                  <li v-for="(g, i) in interviewStore.latestEvaluation.missing_gaps" :key="i">{{ g }}</li>
                </ul>
              </div>

              <!-- Critique -->
              <div v-if="interviewStore.latestEvaluation.constructive_critique" class="feedback-box critique-box">
                <div class="feedback-title text-primary">
                  <Sparkles :size="14" />
                  <span>Interviewer Critique</span>
                </div>
                <p class="critique-text">{{ interviewStore.latestEvaluation.constructive_critique }}</p>
              </div>

              <!-- Exemplar STAR Rewrite -->
              <div v-if="interviewStore.latestEvaluation.exemplar_rewrite" class="feedback-box exemplar-box">
                <div class="feedback-title">
                  <Award :size="14" />
                  <span>Exemplar STAR Answer</span>
                </div>
                <p class="exemplar-text">{{ interviewStore.latestEvaluation.exemplar_rewrite }}</p>
              </div>
            </div>

            <div v-else class="empty-coaching">
              Submit an answer on the left floor to view real-time STAR coverage and coaching feedback.
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
                <span class="final-score-val">{{ interviewStore.overallScore }}</span>
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
              <button
                v-if="interviewStore.currentSession.application_id"
                class="btn btn-primary"
                :disabled="interviewStore.isSavingNotes"
                @click="handleSaveNotes"
              >
                <Loader2 v-if="interviewStore.isSavingNotes" class="animate-spin" :size="16" />
                <FileText v-else :size="16" />
                <span>Save to Application Notes</span>
              </button>

              <button
                class="btn btn-secondary"
                @click="interviewStore.resetSession()"
              >
                <RotateCcw :size="16" />
                <span>Start New Simulation</span>
              </button>
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

.chats-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 8px;
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
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  overflow-y: auto;
}

.setup-card {
  max-width: 680px;
  width: 100%;
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

.start-btn {
  width: 100%;
  padding: 12px;
  font-size: 15px;
  font-weight: 600;
}

/* SIMULATOR SPLIT-PANE STYLES */
.simulator-split-pane {
  flex: 1;
  display: flex;
  height: calc(100% - 65px);
  overflow: hidden;
}

.interview-floor {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid var(--border-color);
  background-color: var(--bg-app);
}

.floor-thread {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.turn-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.msg-row {
  display: flex;
  gap: 12px;
  max-width: 90%;
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
  color: var(--primary);
  border-color: var(--primary);
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

.attempt-tag {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.floor-bottom-controls {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-surface);
}

.hud-action-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.answer-input-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.answer-textarea-box {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background-color: var(--bg-app);
  padding: 10px;
}

.answer-textarea {
  width: 100%;
  border: none;
  background: transparent;
  resize: none;
  font-size: 14px;
  color: var(--text-main);
  outline: none;
}

.textarea-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.char-count {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.input-actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-voice-dictation {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  position: relative;
  transition: all var(--transition-fast);
}

.btn-voice-dictation:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.btn-voice-dictation.recording {
  background-color: var(--danger-subtle);
  color: var(--danger);
  border-color: var(--danger);
}

.recording-pulse {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--danger);
  animation: pulse-ring 1.5s infinite;
}

/* RIGHT PANE: LIVE COACHING */
.live-coaching-pane {
  width: 360px;
  height: 100%;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-surface);
  padding: 20px;
  overflow-y: auto;
  gap: 16px;
}

.coaching-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.coaching-title {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.persona-chip {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.score-circle {
  display: flex;
  align-baseline: baseline;
  gap: 2px;
}

.score-number {
  font-size: 36px;
  font-weight: 800;
  color: var(--primary);
  font-family: var(--font-mono);
}

.score-denom {
  font-size: 14px;
  color: var(--text-muted);
}

.score-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.star-meter-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
}

.card-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 10px;
}

.star-badges-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.star-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  font-size: 12px;
  color: var(--text-muted);
}

.star-badge.active {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border-color: var(--status-offer-border);
  font-weight: 600;
}

.coaching-details-scroll {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feedback-box {
  padding: 12px;
  border-radius: var(--radius-md);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
}

.feedback-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.feedback-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.critique-text, .exemplar-text {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin: 0;
}

.exemplar-box {
  border-left: 3px solid var(--primary);
}

.empty-coaching {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  margin-top: 40px;
  line-height: 1.5;
}

/* DEBRIEF SCORECARD STYLES */
.debrief-scorecard-screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  overflow-y: auto;
}

.scorecard-card {
  max-width: 760px;
  width: 100%;
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

.scorecard-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}
</style>
