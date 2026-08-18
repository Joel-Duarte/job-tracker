import { defineStore } from 'pinia'
import { ref } from 'vue'
import { AgentAPI } from '../api/endpoints'
import { useApplicationsStore } from './applicationsStore'
import { useUIStore } from './uiStore'

const STORAGE_KEY = 'job_tracker_agent_chat_messages'

const DEFAULT_WELCOME_MESSAGE = {
  role: 'assistant',
  content:
    "Hello! I am your Job Tracker Agent. I can search through your applications, check interview timelines, and modify application statuses on demand. How can I help you today?",
  actions: [],
}

export const useAgentChatStore = defineStore('agentChat', () => {
  const messages = ref(loadPersistedMessages())
  const isSending = ref(false)

  function loadPersistedMessages() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed
        }
      }
    } catch (e) {
      console.warn('Failed to load persisted agent messages:', e)
    }
    return [{ ...DEFAULT_WELCOME_MESSAGE }]
  }

  function savePersistedMessages() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.value))
    } catch (e) {
      console.warn('Failed to persist agent messages:', e)
    }
  }

  function resetChat() {
    messages.value = [{ ...DEFAULT_WELCOME_MESSAGE }]
    savePersistedMessages()
  }

  async function sendMessage(text) {
    const trimmed = (text || '').trim()
    if (!trimmed || isSending.value) return

    const uiStore = useUIStore()
    const appStore = useApplicationsStore()

    messages.value.push({
      role: 'user',
      content: trimmed,
    })
    savePersistedMessages()
    isSending.value = true

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
      savePersistedMessages()

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
      savePersistedMessages()
    } finally {
      isSending.value = false
    }
  }

  return {
    messages,
    isSending,
    sendMessage,
    resetChat,
  }
})
