<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useAgentChatStore } from '../stores/agentChatStore'
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
  PanelLeftOpen
} from 'lucide-vue-next'

const chatStore = useAgentChatStore()
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

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

onMounted(async () => {
  await chatStore.fetchChats()
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

              <div class="message-text">{{ msg.content }}</div>
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
  padding: 16px;
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
}

.chat-header {
  padding: 14px 24px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-app);
  display: flex;
  align-items: center;
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
