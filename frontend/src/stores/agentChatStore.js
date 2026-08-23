import { defineStore } from 'pinia'
import { ref } from 'vue'
import { AgentAPI } from '../api/endpoints'
import { useApplicationsStore } from './applicationsStore'
import { useUIStore } from './uiStore'

const DEFAULT_WELCOME_MESSAGE = {
  role: 'assistant',
  content:
    "Hello! I am your Job Tracker Agent. I can search through your applications, check interview timelines, and modify application statuses on demand. How can I help you today?",
  actions: [],
}

export const useAgentChatStore = defineStore('agentChat', () => {
  const chatId = ref(null)
  const chatsList = ref([])
  const messages = ref([{ ...DEFAULT_WELCOME_MESSAGE }])
  const isSending = ref(false)
  const isLoadingChats = ref(false)

  async function fetchChats(silent = false) {
    if (!silent && !chatsList.value.length) {
      isLoadingChats.value = true
    }
    try {
      const res = await AgentAPI.listChats()
      const list = res.data || []
      // Preserve optimistic placeholder if present during initial creation
      if (chatId.value && String(chatId.value).startsWith('temp-')) {
        const optimistic = chatsList.value.find(c => c.id === chatId.value)
        if (optimistic) {
          chatsList.value = [optimistic, ...list.filter(c => c.id !== chatId.value)]
        } else {
          chatsList.value = list
        }
      } else {
        chatsList.value = list
      }
    } catch (e) {
      console.error('Failed to load chats:', e)
    } finally {
      isLoadingChats.value = false
    }
  }

  async function loadChat(id) {
    if (!id) return
    if (String(id).startsWith('temp-')) {
      if (chatId.value === id) return
      return
    }
    if (chatId.value === id) return
    isLoadingChats.value = true
    try {
      const res = await AgentAPI.getChat(id)
      chatId.value = res.data.id
      messages.value = res.data.messages || []
      if (messages.value.length === 0) {
        messages.value = [{ ...DEFAULT_WELCOME_MESSAGE }]
      }
    } catch (e) {
      console.error('Failed to load chat:', e)
      const uiStore = useUIStore()
      uiStore.showToast('Failed to load chat', 'error')
    } finally {
      isLoadingChats.value = false
    }
  }

  async function deleteChat(id) {
    if (!id) return
    if (String(id).startsWith('temp-')) {
      chatsList.value = chatsList.value.filter((c) => c.id !== id)
      if (chatId.value === id) {
        resetChat()
      }
      return
    }
    try {
      await AgentAPI.deleteChat(id)
      chatsList.value = chatsList.value.filter((c) => c.id !== id)
      if (chatId.value === id) {
        resetChat()
      }
      const uiStore = useUIStore()
      uiStore.showToast('Chat deleted', 'success')
    } catch (e) {
      console.error('Failed to delete chat:', e)
      const uiStore = useUIStore()
      uiStore.showToast('Failed to delete chat', 'error')
    }
  }

  function resetChat() {
    chatId.value = null
    messages.value = [{ ...DEFAULT_WELCOME_MESSAGE }]
  }

  async function sendMessage(text) {
    const trimmed = (text || '').trim()
    if (!trimmed || isSending.value) return

    const isNewChat = !chatId.value
    const tempId = `temp-${Date.now()}`
    if (isNewChat) {
      const optimisticChat = {
        id: tempId,
        title: trimmed.slice(0, 40) + (trimmed.length > 40 ? '...' : ''),
        created_at: new Date().toISOString(),
      }
      chatId.value = tempId
      chatsList.value = [optimisticChat, ...chatsList.value.filter(c => c.id !== tempId)]
    }

    messages.value.push({
      role: 'user',
      content: trimmed,
    })
    isSending.value = true

    try {
      const payload = messages.value.map((m) => ({
        role: m.role,
        content: m.content,
      }))

      const targetChatId = isNewChat ? null : chatId.value
      const res = await AgentAPI.chat(payload, targetChatId)

      chatId.value = res.data.chat_id

      messages.value.push({
        role: 'assistant',
        content: res.data.reply,
        actions: res.data.actions_performed || [],
      })

      // Refresh chats list so the real title and id show up
      fetchChats()

      // If any DB mutations occurred, refresh application store
      if (res.data.actions_performed?.length) {
        appStore.fetchApplications()
        uiStore.showToast('Agent updated pipeline records', 'success')
      }
    } catch (err) {
      messages.value.push({
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message || 'Unknown error'}`,
        actions: [],
      })
    } finally {
      isSending.value = false
    }
  }

  return {
    chatId,
    chatsList,
    messages,
    isSending,
    isLoadingChats,
    fetchChats,
    loadChat,
    deleteChat,
    sendMessage,
    resetChat,
  }
})
