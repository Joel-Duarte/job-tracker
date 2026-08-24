<script setup>
import { ref, watch } from 'vue'
import { ApplicationsAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'
import { useApplicationsStore } from '../../stores/applicationsStore'
import { X, Loader2, Send, MessageSquare, AlertCircle } from 'lucide-vue-next'

const props = defineProps({
  isOpen: Boolean,
  applicationId: Number
})

const emit = defineEmits(['close', 'updated'])
const uiStore = useUIStore()
const appStore = useApplicationsStore()

const isSubmitting = ref(false)
const eventType = ref('CUSTOM_NOTE')
const summary = ref('')
const requiresAction = ref(false)

const EVENT_TYPES = [
  { value: 'CUSTOM_NOTE', label: 'General Note' },
  { value: 'EMAIL_RECEIVED', label: 'Email Received' },
  { value: 'EMAIL_SENT', label: 'Email Sent' },
  { value: 'CALL_LOG', label: 'Phone Call Logged' },
]

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    eventType.value = 'CUSTOM_NOTE'
    summary.value = ''
    requiresAction.value = false
  }
})

async function submitLog() {
  if (!summary.value.trim()) return

  isSubmitting.value = true
  try {
    // We will just do a transition with notes to log the event.
    // ApplicationsAPI.transition actually accepts notes.
    // Wait, transition expects a 'status'. If we don't change status, we just send current status.
    const app = appStore.applications.find(a => String(a.id) === String(props.applicationId)) ||
                appStore.activeApplications.find(a => String(a.id) === String(props.applicationId))
    const currentStatus = app?.status || 'APPLIED'

    await appStore.transitionApplication(props.applicationId, {
      status: currentStatus,
      event_type: eventType.value,
      notes: `${eventType.value === 'CUSTOM_NOTE' ? '' : `[${eventType.value}] `}${summary.value.trim()}`
    })

    uiStore.showToast('Activity logged successfully', 'success')
    emit('updated')
    emit('close')
  } catch (err) {
    uiStore.showToast('Failed to log activity', 'error')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card animate-fade-in log-activity-container">
      <div class="modal-header">
        <h2 class="modal-title"><MessageSquare :size="18" /> Log Activity</h2>
        <button class="btn-close" @click="emit('close')"><X :size="18" /></button>
      </div>

      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Activity Type</label>
          <select v-model="eventType" class="form-select">
            <option v-for="t in EVENT_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Notes / Summary</label>
          <textarea
            v-model="summary"
            rows="4"
            class="form-textarea"
            placeholder="Type your notes here..."
            autofocus
          ></textarea>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="emit('close')">Cancel</button>
        <button class="btn btn-primary" :disabled="isSubmitting || !summary.trim()" @click="submitLog">
          <Loader2 v-if="isSubmitting" class="animate-spin" :size="14" />
          <Send v-else :size="14" />
          <span>Save Activity</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; background-color: var(--bg-backdrop);
  display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px;
}
.log-activity-container {
  width: 100%; max-width: 450px; background-color: var(--bg-surface);
  border: 1px solid var(--border-color); border-radius: var(--radius-lg); box-shadow: var(--shadow-xl);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between; padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}
.modal-title { font-family: var(--font-heading); font-size: 16px; color: var(--text-main); margin: 0; display: flex; align-items: center; gap: 8px; }
.modal-body { padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.modal-footer {
  display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding: 14px 20px;
  border-top: 1px solid var(--border-color); background-color: var(--bg-sidebar);
}
</style>
