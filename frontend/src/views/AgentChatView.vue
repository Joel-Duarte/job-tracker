<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DOMPurify from 'dompurify'
import { useAgentChatStore } from '../stores/agentChatStore'
import { useUIStore } from '../stores/uiStore'
import { AIConfigAPI, ApplicationsAPI } from '../api/endpoints'
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
  Briefcase,
  LogOut,
  XCircle
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const uiStore = useUIStore()
const chatStore = useAgentChatStore()
const inputMessage = ref('')
const chatContainer = ref(null)

const isMockInterview = ref(false)
const mockAppId = ref(null)
const isMockEnded = ref(false)
const isEndingInterview = ref(false)

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

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

onMounted(async () => {
  await chatStore.fetchChats()

  if (route.query.mock === 'true' && route.query.appId) {
    const appId = Number(route.query.appId)
    mockAppId.value = appId
    isMockInterview.value = true
    isMockEnded.value = false

    try {
      const res = await ApplicationsAPI.get(appId)
      const appData = res.data
      const companyName = appData.company?.name || 'Target Company'
      const position = appData.position || 'Role'

      chatStore.resetChat()

      const seedText = `Let's start an interactive Mock Interview for the ${position} position at ${companyName}. Please generate a technical or behavioral interview question using my candidate CV and job description.`
      await chatStore.sendMessage(seedText)
    } catch (err) {
      console.error('Failed seeding mock interview context:', err)
    }
  }

  scrollToBottom()

  try {
    const res = await AIConfigAPI.getGlobalSettings()
    retentionDays.value = res.data.AGENT_CHAT_RETENTION_DAYS || 0
  } catch (err) {
    console.error("Failed to load retention settings", err)
  }
})

watch(() => chatStore.messages.length, () => {
  scrollToBottom()
})

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

  // 1. First escape all raw HTML to prevent XSS
  let html = escapeHtml(text)

  // 2. Fenced code blocks ```code```
  html = html.replace(/```([\s\S]*?)```/g, (match, p1) => {
    return `<pre><code>${p1.trim()}</code></pre>`
  })

  // 3. Inline code `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  // 4. Tables
  const lines = html.split('\n')
  let inTable = false
  let tableHtml = ''
  let newLines = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line.startsWith('|') && line.endsWith('|')) {
      const cells = line.split('|').slice(1, -1).map(c => c.trim())
      // Check if separator line
      if (cells.every(c => /^:?-+:?$/.test(c))) {
        continue
      }
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

  // 5. Headings
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>')

  // 6. Blockquotes
  html = html.replace(/^\&gt;\s?(.*$)/gim, '<blockquote>$1</blockquote>')

  // 7. Bold and Italics
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')

  // 8. Unordered / Ordered Lists
  html = html.replace(/^\s*[\-\*]\s+(.*$)/gim, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/gis, '<ul>$1</ul>')
  html = html.replace(/<\/ul>\s*<ul>/g, '')

  // 9. Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, p1, p2) => {
    // Ensure URL is safe (http/https or relative)
    const safeUrl = (p2.startsWith('http://') || p2.startsWith('https://') || p2.startsWith('/')) ? p2 : '#'
    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${p1}</a>`
  })

  // 10. Paragraph breaks for double newlines
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

function getCleanMessageContent(msg) {
  if (!msg || !msg.content) return ''
  let text = msg.content
  const qData = getQuestionData(msg)
  if (qData && qData.question_type === 'multiple_choice' && qData.options?.length) {
    const lines = text.split('\n')
    const cleaned = lines.filter(line => {
      const trimmed = line.trim()
      if (/^[A-D][\.\)\:]\s+/i.test(trimmed)) return false
      if (/^[1-4][\.\)\:]\s+/i.test(trimmed)) return false
      for (const opt of qData.options) {
        if (opt && (trimmed === opt.trim() || trimmed.endsWith(opt.trim()))) return false
      }
      return true
    })
    text = cleaned.join('\n')
  }
  return text
}

function getQuestionData(msg) {
  if (!msg || msg.role !== 'assistant') return null

  if (msg.questionData) return msg.questionData

  if (msg.actions && Array.isArray(msg.actions)) {
    for (const act of msg.actions) {
      if (act.action === 'generate_mock_interview_question' && act.result) {
        let res = act.result
        if (typeof res === 'string') {
          try { res = JSON.parse(res) } catch (e) {}
        }
        if (res && res.question_type) {
          const qData = {
            question_type: res.question_type,
            options: Array.isArray(res.options) ? res.options : [],
            question_text: res.question_text || ''
          }
          msg.questionData = qData
          return qData
        }
      }
    }
  }
  return null
}

function getSelectedOption(msg, idx) {
  if (msg.selectedOption !== undefined) return msg.selectedOption

  if (idx !== undefined && chatStore.messages && idx < chatStore.messages.length - 1) {
    const nextMsg = chatStore.messages[idx + 1]
    if (nextMsg && nextMsg.role === 'user' && nextMsg.content) {
      const qData = getQuestionData(msg)
      if (qData && qData.options) {
        for (const opt of qData.options) {
          if (nextMsg.content.trim() === opt.trim() || nextMsg.content.trim().includes(opt.trim())) {
            msg.selectedOption = opt
            return opt
          }
        }
        msg.selectedOption = nextMsg.content
        return nextMsg.content
      }
    }
  }
  return undefined
}

async function handleSelectOption(msg, optionText) {
  if (msg.selectedOption !== undefined || chatStore.isSending) return
  msg.selectedOption = optionText
  await chatStore.sendMessage(optionText)
  scrollToBottom()
}

async function handleEndInterview() {
  if (isEndingInterview.value || chatStore.isSending) return
  isEndingInterview.value = true

  const summaryPrompt = `The mock interview questioning phase is now complete. Please shift into open debrief and mentoring mode: provide a comprehensive final performance evaluation summarizing my responses, highlight key strengths, identify gap areas, and offer to answer follow-up questions or recommend study resources.`

  await chatStore.sendMessage(summaryPrompt)
  isMockEnded.value = true
  isEndingInterview.value = false
  scrollToBottom()
}

function handleReturnToJobDetails() {
  if (mockAppId.value) {
    uiStore.openDetail(mockAppId.value)
  }
  router.push({ name: 'Applications' })
}

function formatActionLabel(act) {
  if (act.action === 'generate_mock_interview_question') {
    const comp = act.args?.company_name || 'Company'
    const pos = act.args?.position || 'Role'
    return `Generated mock question for ${comp} (${pos})`
  }
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
</script>

<template>
  <div class="chat-page-container" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">

    <!-- Sidebar -->
    <div class="chat-sidebar" :class="{ 'collapsed': isSidebarCollapsed }">
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

    <!-- Main Chat Area -->
    <div class="chat-main">
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
            <div class="agent-avatar">
              <Bot :size="18" />
            </div>
            <div>
              <h2 class="agent-title">
                {{ isMockInterview ? 'Mock Interview Simulator' : 'Agent Assistant' }}
              </h2>
              <div class="agent-subtitle">
                <span class="pulse-dot"></span>
                <span>{{ isMockInterview ? 'Live Interactive Technical & Behavioral Practice Sandbox' : 'Equipped with pgvector semantic search & database mutation tools' }}</span>
              </div>
            </div>
          </div>

          <div class="header-right-actions">
            <button
              v-if="isMockInterview && !isMockEnded"
              class="btn btn-warning btn-sm"
              :disabled="chatStore.isSending || isEndingInterview"
              @click="handleEndInterview"
            >
              <Loader2 v-if="isEndingInterview" class="animate-spin" :size="14" />
              <CheckCircle2 v-else :size="14" />
              <span>End Interview &amp; Debrief</span>
            </button>

            <div v-if="isMockInterview && isMockEnded" class="debrief-header-group">
              <span class="debrief-badge">
                <Sparkles :size="12" />
                <span>Mentoring &amp; Debrief Mode</span>
              </span>
              <button
                class="btn btn-primary btn-sm"
                @click="handleReturnToJobDetails"
              >
                <Briefcase :size="14" />
                <span>Return to Job Details</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Centered Messages Stream -->
      <div ref="chatContainer" class="chat-messages">
        <div class="chat-messages-inner">
          <div
            v-for="(msg, idx) in chatStore.messages"
            :key="idx"
            class="message-row"
            :class="`msg-${msg.role}`"
          >
            <!-- Skip tool messages in UI normally unless needed -->
            <template v-if="msg.role !== 'tool' && msg.role !== 'system'">
              <div class="avatar-icon">
                <Bot v-if="msg.role === 'assistant'" :size="16" />
                <User v-else :size="16" />
              </div>

              <div class="message-bubble">
                <!-- Executed Actions Chips -->
                <div v-if="msg.actions && msg.actions.length > 0" class="actions-chips">
                  <div v-for="(act, aIdx) in msg.actions" :key="aIdx" class="action-chip">
                    <CheckCircle2 :size="13" class="text-success" />
                    <span>{{ formatActionLabel(act) }}</span>
                  </div>
                </div>

                <div
                  v-if="msg.role === 'assistant'"
                  class="message-text markdown-body"
                  v-html="renderMarkdown(getCleanMessageContent(msg))"
                ></div>
                <div v-else class="message-text">{{ msg.content }}</div>

                <!-- Interactive Mock Question Options (Multiple Choice) -->
                <div
                  v-if="getQuestionData(msg) && getQuestionData(msg).question_type === 'multiple_choice' && getQuestionData(msg).options.length > 0"
                  class="mock-options-block"
                >
                  <div class="mock-options-header">Select an option:</div>
                  <div class="mock-options-grid">
                    <button
                      v-for="(opt, optIdx) in getQuestionData(msg).options"
                      :key="optIdx"
                      class="mock-option-btn"
                      :class="{ 'selected': getSelectedOption(msg, idx) === opt }"
                      :disabled="getSelectedOption(msg, idx) !== undefined || chatStore.isSending"
                      @click="handleSelectOption(msg, opt)"
                    >
                      <span>{{ opt }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Thinking Indicator -->
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

      <!-- Bottom Dock: Starters & Input Box Centered Column -->
      <div class="chat-bottom-dock">
        <div class="bottom-dock-inner">
          <!-- Starter Prompts (if chat is short) -->
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

          <!-- Input Bar -->
          <div class="chat-input-bar">
            <textarea
              v-model="inputMessage"
              rows="1"
              :placeholder="isMockEnded ? 'Ask follow-up questions about feedback, study resources, or concepts...' : 'Ask the agent to search applications, check interview dates, or change statuses...'"
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
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.debrief-header-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.debrief-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
  font-size: 11.5px;
  font-weight: 600;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}

.agent-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.agent-subtitle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
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

/* Markdown Styling */
.markdown-body {
  white-space: normal;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--text-main);
}

.markdown-body p {
  margin-bottom: 8px;
}

.markdown-body p:last-child {
  margin-bottom: 0;
}

.markdown-body ul, .markdown-body ol {
  margin: 6px 0 10px 20px;
  padding-left: 4px;
}

.markdown-body li {
  margin-bottom: 4px;
}

.markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
  font-weight: 600;
  color: var(--text-main);
  margin: 12px 0 6px;
}

.markdown-body h1 { font-size: 16px; }
.markdown-body h2 { font-size: 15px; }
.markdown-body h3 { font-size: 14px; }

.markdown-body code {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  padding: 2px 5px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface-hover);
  border: 1px solid var(--border-color);
  color: var(--primary);
}

.markdown-body pre {
  margin: 10px 0;
  padding: 12px;
  border-radius: var(--radius-md);
  background-color: var(--bg-app);
  border: 1px solid var(--border-color);
  overflow-x: auto;
}

.markdown-body pre code {
  padding: 0;
  background: transparent;
  border: none;
  color: var(--text-main);
}

.markdown-body blockquote {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid var(--primary);
  color: var(--text-secondary);
  background: var(--bg-surface-hover);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.markdown-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 12.5px;
}

.markdown-body th, .markdown-body td {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  text-align: left;
}

.markdown-body th {
  background-color: var(--bg-surface-hover);
  font-weight: 600;
  color: var(--text-main);
}

.markdown-body a {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.markdown-body a:hover {
  opacity: 0.85;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  background-color: transparent !important;
  border: 1px dashed var(--border-subtle);
  box-shadow: none;
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
  padding: 6px 8px;
  resize: none;
  border: none;
  background: transparent;
  font-size: 13.5px;
  color: var(--text-main);
  outline: none;
}

.chat-input:focus {
  box-shadow: none;
  border-color: transparent;
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

/* Interactive Mock Question Option Buttons */
.mock-options-block {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mock-options-header {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}

.mock-options-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mock-option-btn {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface-hover);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  font-size: 12.5px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mock-option-btn:hover:not(:disabled) {
  background-color: var(--primary-subtle);
  border-color: var(--primary);
  color: var(--primary);
  transform: translateX(2px);
}

.mock-option-btn.selected {
  background-color: var(--primary);
  color: #ffffff;
  border-color: var(--primary);
  font-weight: 600;
}

.mock-option-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
