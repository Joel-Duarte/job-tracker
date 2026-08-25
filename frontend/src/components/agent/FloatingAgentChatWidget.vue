<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAgentChatStore } from '../../stores/agentChatStore'
import {
  Bot,
  User,
  Send,
  Sparkles,
  Loader2,
  CheckCircle2,
  ArrowRight,
  RotateCcw,
  Maximize2,
  X,
  MessageSquare,
  ChevronDown,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const chatStore = useAgentChatStore()

const isOpen = ref(false)
const inputMessage = ref('')
const chatMessagesContainer = ref(null)

const starterPrompts = [
  'Which applications need urgent attention?',
  'Find roles matching Python or Distributed Systems',
  'What is the status of my active applications?',
]

function toggleChat() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatMessagesContainer.value) {
      chatMessagesContainer.value.scrollTop = chatMessagesContainer.value.scrollHeight
    }
  })
}

watch(() => chatStore.messages.length, () => {
  if (isOpen.value) {
    scrollToBottom()
  }
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

function openFullPage() {
  isOpen.value = false
  router.push('/chat')
}

function formatActionLabel(act) {
  if (act.action === 'UPDATE_STATUS' || act.action === 'update_application_status') {
    const comp = act.args?.company_name || act.company || 'Application'
    const st = act.args?.new_status || act.new_status || 'Updated'
    return `Updated ${comp} to ${st}`
  }
  if (act.action === 'semantic_vector_search') {
    const q = act.args?.query ? `"${act.args.query}"` : 'records'
    return `Vector search: ${q}`
  }
  if (act.action === 'list_applications') {
    return 'Queried active pipeline'
  }
  if (act.action === 'get_application_details') {
    const comp = act.args?.company_or_id || 'Company'
    return `Loaded details for ${comp}`
  }
  if (act.action === 'get_action_items') {
    return 'Checked pending action items'
  }
  return `Executed tool: ${act.action}`
}
</script>

<template>
  <!-- Don't render floating drawer when user is already on the dedicated /chat page -->
  <div v-if="route.path !== '/chat'" class="floating-agent-wrapper">
    <!-- Floating Trigger Bubble -->
    <button
      class="floating-chat-bubble"
      :class="{ active: isOpen }"
      @click="toggleChat"
      title="Ask AI Assistant"
    >
      <Bot v-if="!isOpen" :size="22" class="bubble-icon" />
      <X v-else :size="20" class="bubble-icon" />
      <span class="live-status-ping" v-if="!isOpen"></span>
    </button>

    <!-- Slide-Over Popover Chat Window -->
    <Transition name="chat-pop">
      <div v-if="isOpen" class="agent-chat-popover">
        <!-- Header -->
        <div class="popover-header">
          <div class="popover-title-group">
            <div class="agent-avatar-sm">
              <Bot :size="16" />
            </div>
            <div>
              <div class="popover-title">Agent Assistant</div>
              <div class="popover-sub">
                <span class="pulse-dot"></span>
                <span>Ready with pgvector search</span>
              </div>
            </div>
          </div>

          <div class="popover-header-actions">
            <button
              class="btn-icon-sm"
              title="Reset conversation"
              @click="chatStore.resetChat()"
            >
              <RotateCcw :size="13" />
            </button>
            <button
              class="btn-icon-sm"
              title="Open full page view"
              @click="openFullPage"
            >
              <Maximize2 :size="13" />
            </button>
            <button
              class="btn-icon-sm"
              title="Minimize chat"
              @click="isOpen = false"
            >
              <ChevronDown :size="15" />
            </button>
          </div>
        </div>

        <!-- Messages Stream -->
        <div ref="chatMessagesContainer" class="popover-body">
          <div
            v-for="(msg, idx) in chatStore.messages"
            :key="idx"
            class="chat-msg-row"
            :class="`msg-${msg.role}`"
          >
            <div class="msg-avatar">
              <Bot v-if="msg.role === 'assistant'" :size="14" />
              <User v-else :size="14" />
            </div>

            <div class="msg-bubble">
              <!-- Actions Chips -->
              <div v-if="msg.actions && msg.actions.length > 0" class="msg-actions">
                <div v-for="(act, aIdx) in msg.actions" :key="aIdx" class="action-tag">
                  <CheckCircle2 :size="11" class="text-success" />
                  <span>{{ formatActionLabel(act) }}</span>
                </div>
              </div>
              <div class="msg-text">{{ msg.content }}</div>
            </div>
          </div>

          <!-- Thinking Spinner -->
          <div v-if="chatStore.isSending" class="chat-msg-row msg-assistant">
            <div class="msg-avatar">
              <Bot :size="14" />
            </div>
            <div class="msg-bubble thinking-bubble">
              <Loader2 class="animate-spin" :size="14" />
              <span>Reasoning & searching pipeline...</span>
            </div>
          </div>
        </div>

        <!-- Starter Prompts (if chat is fresh) -->
        <div v-if="chatStore.messages.length <= 2" class="popover-starters">
          <button
            v-for="prompt in starterPrompts"
            :key="prompt"
            class="starter-btn"
            @click="handleSendMessage(prompt)"
          >
            <span>{{ prompt }}</span>
            <ArrowRight :size="11" />
          </button>
        </div>

        <!-- Input Bar -->
        <div class="popover-footer">
          <textarea
            v-model="inputMessage"
            rows="1"
            placeholder="Ask about applications, skills, interview prep..."
            class="popover-input"
            @keydown="handleKeyDown"
          ></textarea>

          <button
            class="btn-send-mini"
            :disabled="chatStore.isSending || !inputMessage.trim()"
            @click="handleSendMessage()"
          >
            <Send :size="14" />
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.floating-agent-wrapper {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

/* Floating Trigger Bubble */
.floating-chat-bubble {
  position: relative;
  width: 50px;
  height: 50px;
  border-radius: var(--radius-full);
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  border: 1px solid var(--primary-glow);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.28), 0 0 12px var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.floating-chat-bubble:hover {
  transform: scale(1.06);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35), 0 0 16px var(--primary);
}

.floating-chat-bubble.active {
  background-color: var(--bg-surface);
  color: var(--text-main);
  border-color: var(--border-color);
  box-shadow: var(--shadow-md);
}

.bubble-icon {
  transition: transform var(--transition-fast);
}

.live-status-ping {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background-color: var(--status-applied-text, #10b981);
  border: 2px solid var(--bg-app);
}

/* Popover Chat Window */
.agent-chat-popover {
  position: absolute;
  bottom: 64px;
  right: 0;
  width: 390px;
  max-width: calc(100vw - 32px);
  height: 540px;
  max-height: calc(100vh - 120px);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.32), 0 0 0 1px var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Popover Header */
.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
}

.popover-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-avatar-sm {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background-color: var(--primary-subtle);
  color: var(--primary);
  border: 1px solid var(--primary-glow);
  display: flex;
  align-items: center;
  justify-content: center;
}

.popover-title {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 13px;
  color: var(--text-main);
  line-height: 1.2;
}

.popover-sub {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-secondary);
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--text-success, #10b981);
  box-shadow: 0 0 6px var(--text-success, #10b981);
}

.popover-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-icon-sm {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  border-radius: 4px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-icon-sm:hover {
  background-color: var(--bg-hover);
  border-color: var(--border-subtle);
  color: var(--text-main);
}

/* Messages Body */
.popover-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-msg-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.chat-msg-row.msg-user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.msg-assistant .msg-avatar {
  background-color: var(--primary-subtle);
  color: var(--primary);
  border-color: var(--primary-glow);
}

.msg-bubble {
  max-width: 82%;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 12.5px;
  line-height: 1.5;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-user .msg-bubble {
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  border-color: var(--primary);
  border-bottom-right-radius: 2px;
}

.msg-assistant .msg-bubble {
  border-bottom-left-radius: 2px;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.msg-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 6px;
}

.action-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 6px;
  border-radius: 3px;
  background-color: var(--status-applied-bg);
  border: 1px solid var(--status-applied-border);
  font-size: 10.5px;
  font-weight: 500;
  color: var(--text-main);
}

/* Starters */
.popover-starters {
  padding: 0 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.starter-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background-color: var(--bg-main);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 11.5px;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.starter-btn:hover {
  background-color: var(--bg-hover);
  border-color: var(--primary);
  color: var(--text-main);
}

/* Footer Input Bar */
.popover-footer {
  padding: 10px 12px;
  background-color: var(--bg-sidebar);
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
}

.popover-input {
  flex: 1;
  resize: none;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text-main);
  outline: none;
  font-family: inherit;
  line-height: 1.4;
  max-height: 80px;
}

.popover-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-subtle);
}

.btn-send-mini {
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  border-radius: var(--radius-sm);
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.btn-send-mini:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-send-mini:not(:disabled):hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

/* Transition */
.chat-pop-enter-active,
.chat-pop-leave-active {
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: bottom right;
}

.chat-pop-enter-from,
.chat-pop-leave-to {
  opacity: 0;
  transform: scale(0.85) translateY(16px);
}

/* Mobile Responsive Adjustments for Floating Agent Chat Widget */
@media (max-width: 767px) {
  .floating-agent-wrapper {
    bottom: 16px;
    right: 16px;
  }

  .floating-chat-bubble {
    width: 52px;
    height: 52px;
    min-width: 48px;
    min-height: 48px;
  }

  .agent-chat-popover {
    position: fixed;
    inset: 0;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    max-width: 100vw;
    max-height: 100dvh;
    border-radius: 0;
    border: none;
    z-index: 1000;
  }

  .btn-icon-sm {
    width: 44px;
    height: 44px;
    min-width: 44px;
    min-height: 44px;
  }

  .popover-header {
    padding: 12px 16px;
  }

  .popover-footer {
    padding: 12px 16px;
    padding-bottom: max(12px, env(safe-area-inset-bottom));
  }

  .popover-input {
    min-height: 44px;
    font-size: 14px;
  }

  .starter-btn {
    min-height: 44px;
    padding: 10px 12px;
  }
}
</style>
