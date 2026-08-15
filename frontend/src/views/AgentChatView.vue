<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { AgentAPI } from '../api/endpoints'
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
} from 'lucide-vue-next'

const uiStore = useUIStore()
const appStore = useApplicationsStore()

const messages = ref([
  {
    role: 'assistant',
    content:
      "Hello! I am your Job Tracker Agent. I can search through your applications using 768-dimension vector similarity, check interview timelines, and modify application statuses on demand. How can I help you today?",
    actions: [],
  },
])

const inputMessage = ref('')
const isSending = ref(false)
const chatContainer = ref(null)

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

async function sendMessage(textToSend = null) {
  const text = textToSend || inputMessage.value.trim()
  if (!text || isSending.value) return

  // Push user message
  messages.value.push({
    role: 'user',
    content: text,
  })
  inputMessage.value = ''
  isSending.value = true
  scrollToBottom()

  try {
    const payload = messages.value.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    const res = await AgentAPI.chat(payload)
    messages.value.push({
      role: 'assistant',
      content: res.data.reply,
      actions: res.data.actions_performed || [],
    })

    // If any DB mutations occurred, refresh application store
    if (res.data.actions_performed?.length) {
      appStore.fetchApplications()
      uiStore.showToast('Agent updated pipeline records', 'success')
    }
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: `Sorry, I encountered an error: ${err.message}`,
      actions: [],
    })
  } finally {
    isSending.value = false
    scrollToBottom()
  }
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
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
          <h2 class="agent-title">Agent Assistant</h2>
          <div class="agent-subtitle">
            <span class="pulse-dot"></span>
            <span>Equipped with pgvector semantic search & database mutation tools</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Chat Messages Stream -->
    <div ref="chatContainer" class="chat-messages">
      <div
        v-for="(msg, idx) in messages"
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
            <div v-for="(act, aIdx) in msg.actions" :key="aIdx" class="action-chip">
              <CheckCircle2 :size="13" class="text-success" />
              <span>Action Executed: {{ act.action }} ({{ act.company }} -> {{ act.new_status }})</span>
            </div>
          </div>

          <div class="message-text">{{ msg.content }}</div>
        </div>
      </div>

      <!-- Thinking Indicator -->
      <div v-if="isSending" class="message-row msg-assistant">
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
    <div v-if="messages.length <= 2" class="starters-bar">
      <button
        v-for="prompt in starterPrompts"
        :key="prompt"
        class="starter-chip"
        @click="sendMessage(prompt)"
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
        placeholder="Ask the agent to search applications, check interview dates, or change statuses (e.g. 'move Stripe to Offer')..."
        class="chat-input"
        @keydown="handleKeyDown"
      ></textarea>

      <button
        class="btn btn-primary btn-send"
        :disabled="isSending || !inputMessage.trim()"
        @click="sendMessage()"
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
  height: calc(100vh - 56px);
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-app);
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
  background-color: var(--primary);
  color: #ffffff;
  border: none;
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

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
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
  border-radius: var(--radius-full);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.starter-chip:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
  border-color: var(--border-subtle);
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
}

.btn-send {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  padding: 0;
}
</style>
