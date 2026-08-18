<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useAgentChatStore } from '../stores/agentChatStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import {
  Bot,
  User,
  Send,
  Sparkles,
  Loader2,
  CheckCircle2,
  HelpCircle,
  Building2,
  ArrowRight,
  RotateCcw,
  Plus,
  MonitorPlay,
  X
} from 'lucide-vue-next'

const chatStore = useAgentChatStore()
const appStore = useApplicationsStore()
const inputMessage = ref('')
const chatContainer = ref(null)

const showConfig = ref(false)
const selectedInterviewType = ref('Mixed')
const selectedAppId = ref('')

onMounted(() => {
  if (appStore.applications.length === 0) {
    appStore.fetchApplications()
  }
  scrollToBottom()
})

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

onMounted(() => {
  scrollToBottom()
})

watch(() => chatStore.messages.length, () => {
  scrollToBottom()
})

async function handleSendMessage(textToSend = null) {
  const text = (typeof textToSend === 'string' ? textToSend : inputMessage.value.trim())
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
  chatStore.isMockInterview = false
  chatStore.resetChat()
  scrollToBottom()
}

function startMockInterview() {
  chatStore.configureMockInterview(
    selectedInterviewType.value,
    selectedAppId.value ? parseInt(selectedAppId.value) : null
  )
  showConfig.value = false
  scrollToBottom()
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
  if (act.action === 'SubmitEvaluation') {
    const s = act.args?.score || 0
    return `Evaluated Answers (Score: ${s})`
  }
  return `Executed: ${act.action || 'Tool'}`
}
</script>

<template>
  <div class="chat-page">
    <!-- Chat Header -->
    <div class="chat-header">
      <div class="header-left">
        <div class="agent-avatar">
          <Bot :size="18" />
        </div>
        <div>
          <h2 class="agent-title">Agent Assistant <span v-if="chatStore.isMockInterview" class="mock-badge">Mock Interview</span></h2>
          <div class="agent-subtitle">
            <span class="pulse-dot"></span>
            <span v-if="!chatStore.isMockInterview">Equipped with pgvector semantic search & database mutation tools</span>
            <span v-else>Acting as Technical Hiring Manager</span>
          </div>
        </div>
      </div>

      <div class="header-actions">
        <button
          class="btn-new-chat"
          title="Start mock interview"
          @click="showConfig = !showConfig"
        >
          <MonitorPlay :size="14" />
          <span>Mock Interview</span>
        </button>
        <button
          class="btn-new-chat"
          title="Start fresh conversation"
          @click="handleResetChat"
        >
          <Plus :size="14" />
          <span>New Chat</span>
        </button>
      </div>
    </div>

    <!-- Mock Interview Config Bar -->
    <div v-if="showConfig" class="mock-config-bar">
      <div class="config-header">
        <h4>Mock Interview Setup</h4>
        <button class="btn-close" @click="showConfig = false"><X :size="14"/></button>
      </div>
      <div class="config-fields">
        <select v-model="selectedInterviewType" class="select-input">
          <option value="Multiple Choice Only">Multiple Choice Only</option>
          <option value="Open Ended Only">Open Ended Only</option>
          <option value="Mixed">Mixed (Both)</option>
        </select>
        <select v-model="selectedAppId" class="select-input">
          <option value="">General (No Context)</option>
          <option v-for="app in appStore.applications.filter(a => ['TECHNICAL_INTERVIEW', 'OFFER', 'APPLIED'].includes(a.status))" :key="app.id" :value="app.id">
            {{ app.company?.name }} - {{ app.position }} ({{ app.status }})
          </option>
        </select>
        <button class="btn btn-primary" @click="startMockInterview">Start</button>
      </div>
    </div>

    <!-- Chat Messages Stream -->
    <div ref="chatContainer" class="chat-messages">
      <div
        v-for="(msg, idx) in chatStore.messages"
        :key="idx"
        class="message-row"
        :class="`msg-${msg.role}`"
      >
        <div class="avatar-icon">
          <Bot v-if="msg.role === 'assistant'" :size="16" />
          <User v-else :size="16" />
        </div>

        <div class="message-bubble">
          <!-- Executed Actions Chips -->
          <div v-if="msg.actions && msg.actions.length > 0" class="actions-chips">
            <template v-for="(act, aIdx) in msg.actions" :key="aIdx">
              <div v-if="act.action !== 'PresentMultipleChoiceQuestion' && act.action !== 'PresentOpenEndedQuestion'" class="action-chip">
                <CheckCircle2 :size="13" class="text-success" />
                <span>{{ formatActionLabel(act) }}</span>
              </div>
            </template>
          </div>

          <div class="message-text">{{ msg.content }}</div>

          <!-- Render Options for Multiple Choice Questions -->
          <template v-if="msg.actions && msg.actions.length > 0">
            <div v-for="(act, aIdx) in msg.actions" :key="aIdx">
              <div v-if="act.action === 'PresentMultipleChoiceQuestion' && act.args?.options" class="mcq-options">
                <button
                  v-for="(opt, oIdx) in act.args.options"
                  :key="oIdx"
                  class="mcq-btn"
                  :disabled="chatStore.isSending || idx !== chatStore.messages.length - 1"
                  @click="handleSendMessage(opt)"
                >
                  {{ opt }}
                </button>
              </div>
            </div>
          </template>
        </div>
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

    <!-- Starter Prompts (if chat is short) -->
    <div v-if="chatStore.messages.length <= 2 && !chatStore.isMockInterview" class="starters-bar">
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
        :placeholder="chatStore.isMockInterview ? 'Type your answer to the interview question...' : 'Ask the agent to search applications, check interview dates, or change statuses...'"
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
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--navbar-height));
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.chat-header {
  padding: 14px 24px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-app);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-new-chat {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-new-chat:hover {
  background-color: var(--bg-hover);
  border-color: var(--border-color);
  color: var(--text-primary);
}

.mock-badge {
  font-size: 10px;
  background-color: var(--status-assessment-bg);
  color: var(--status-assessment-text);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  margin-left: 8px;
  vertical-align: middle;
}

.mock-config-bar {
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  padding: 12px 24px;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.config-header h4 {
  font-size: 13px;
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
}

.config-fields {
  display: flex;
  gap: 12px;
}

.select-input {
  flex: 1;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background-color: var(--bg-app);
  color: var(--text-main);
  font-size: 13px;
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
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.message-row {
  display: flex;
  gap: 12px;
  max-width: 85%;
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

.mcq-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.mcq-btn {
  text-align: left;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background-color: var(--bg-app);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mcq-btn:hover:not(:disabled) {
  background-color: var(--bg-hover);
  border-color: var(--primary);
  color: var(--text-primary);
}

.mcq-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
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

.starters-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 24px 12px;
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
  padding: 16px 24px 24px;
  background-color: var(--bg-app);
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
</style>
