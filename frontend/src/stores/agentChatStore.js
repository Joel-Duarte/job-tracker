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
  const uiStore = useUIStore()
  const appStore = useApplicationsStore()

  const chatId = ref(null)
  const chatsList = ref([])
  const messages = ref([{ ...DEFAULT_WELCOME_MESSAGE }])
  const isSending = ref(false)
  const isLoadingChats = ref(false)
  const isLoadingMessages = ref(false)

  async function fetchChats(silent = false) {
    if (!silent && !chatsList.value.length) {
      isLoadingChats.value = true
    }
    try {
      const res = await AgentAPI.listChats()
      const list = res.data || []
      chatsList.value = list
      if (!chatId.value && list.length > 0) {
        await loadChat(list[0].id)
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
    isLoadingMessages.value = true
    try {
      const res = await AgentAPI.getChat(id)
      chatId.value = res.data.id
      messages.value = res.data.messages || []
      if (messages.value.length === 0) {
        messages.value = [{ ...DEFAULT_WELCOME_MESSAGE }]
      }
    } catch (e) {
      console.error('Failed to load chat:', e)
      uiStore.showToast('Failed to load chat', 'error')
    } finally {
      isLoadingMessages.value = false
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
      uiStore.showToast('Chat deleted', 'success')
    } catch (e) {
      console.error('Failed to delete chat:', e)
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

      fetchChats(true)

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
    isLoadingMessages,
    fetchChats,
    loadChat,
    deleteChat,
    sendMessage,
    resetChat,
  }
})
