<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="visible" class="post-hire-overlay" @click.self="handleDecideLater">
        <div class="post-hire-modal" role="dialog" aria-labelledby="post-hire-title">
          <div class="modal-confetti-header">
            <span class="modal-emoji" aria-hidden="true">&#x1F389;</span>
            <h2 id="post-hire-title" class="modal-title">You got the job!</h2>
            <p class="modal-subtitle">Congratulations! What would you like to do with your other open applications?</p>
          </div>

          <div class="modal-options">
            <div
              class="selection-card"
              :class="{ 'card-active': actions.archiveAll }"
              @click="actions.archiveAll = !actions.archiveAll"
              role="button"
              tabindex="0"
              @keydown.space.prevent="actions.archiveAll = !actions.archiveAll"
              @keydown.enter.prevent="actions.archiveAll = !actions.archiveAll"
            >
              <div class="card-icon-wrapper">
                <CheckCircle2 v-if="actions.archiveAll" class="icon-active" :size="20" />
                <Circle v-else class="icon-inactive" :size="20" />
              </div>
              <div class="option-content">
                <span class="option-label">Archive early-stage applications</span>
                <span class="option-description">Moves Applied and Assessment cards to Archived.</span>
              </div>
            </div>

            <div
              class="selection-card"
              :class="{ 'card-active': actions.withdrawInterviews }"
              @click="actions.withdrawInterviews = !actions.withdrawInterviews"
              role="button"
              tabindex="0"
              @keydown.space.prevent="actions.withdrawInterviews = !actions.withdrawInterviews"
              @keydown.enter.prevent="actions.withdrawInterviews = !actions.withdrawInterviews"
            >
              <div class="card-icon-wrapper">
                <CheckCircle2 v-if="actions.withdrawInterviews" class="icon-active" :size="20" />
                <Circle v-else class="icon-inactive" :size="20" />
              </div>
              <div class="option-content">
                <span class="option-label">Withdraw outstanding interviews &amp; offers</span>
                <span class="option-description">Marks Interview and Offer stage cards as Withdrawn.</span>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="handleDecideLater" :disabled="submitting">Decide later</button>
            <button class="btn-primary" :disabled="submitting" @click="handleConfirm">
              <span v-if="submitting">Working&#x2026;</span>
              <span v-else>Confirm</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { CheckCircle2, Circle } from 'lucide-vue-next'
import { useApplicationsStore } from '../../stores/applicationsStore'

const props = defineProps({
  visible: { type: Boolean, required: true },
  hiredApplicationId: { type: Number, required: true },
})
const emit = defineEmits(['close'])

const appStore = useApplicationsStore()
const submitting = ref(false)

const actions = reactive({
  archiveAll: true,
  withdrawInterviews: true,
})

async function handleConfirm() {
  if (!actions.archiveAll && !actions.withdrawInterviews) {
    emit('close')
    return
  }

  submitting.value = true
  try {
    const excludeIds = [props.hiredApplicationId]

    if (actions.withdrawInterviews) {
      await appStore.bulkTransition(
        'WITHDRAWN',
        ['TECHNICAL_INTERVIEW', 'OFFER'],
        excludeIds,
        'Withdrawn — position filled elsewhere.',
      )
    }

    if (actions.archiveAll) {
      const fromStatuses = ['APPLIED', 'ONLINE_ASSESSMENT']
      if (!actions.withdrawInterviews) {
        fromStatuses.push('TECHNICAL_INTERVIEW', 'OFFER')
      }
      await appStore.bulkTransition(
        'ARCHIVED',
        fromStatuses,
        excludeIds,
        'Archived — position filled elsewhere.',
      )
    }
  } finally {
    submitting.value = false
    emit('close')
  }
}

function handleDecideLater() {
  if (!submitting.value) emit('close', { decideLater: true })
}
</script>

<style scoped>
.post-hire-overlay {
  position: fixed;
  inset: 0;
  background: hsl(0 0% 0% / 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}
.post-hire-modal {
  background: var(--color-surface, #1c1c1e);
  border: 1px solid hsl(0 0% 100% / 0.08);
  border-radius: 16px;
  padding: 2rem;
  width: min(480px, 92vw);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  box-shadow: 0 24px 64px hsl(0 0% 0% / 0.45);
}
.modal-confetti-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
}
.modal-emoji { font-size: 3rem; line-height: 1; }
.modal-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-text-primary, #f5f5f5);
}
.modal-subtitle {
  font-size: 0.875rem;
  color: var(--color-text-muted, #888);
  margin: 0;
}
.modal-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.selection-card {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  padding: 1rem;
  border-radius: 10px;
  border: 1px solid hsl(0 0% 100% / 0.07);
  background: hsl(0 0% 100% / 0.03);
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  outline: none;
}
.selection-card:hover {
  background: hsl(0 0% 100% / 0.06);
}
.selection-card:focus-visible {
  border-color: hsl(220 80% 55%);
  box-shadow: 0 0 0 2px hsl(220 80% 55% / 0.3);
}
.selection-card.card-active {
  background: hsl(220 80% 55% / 0.12);
  border-color: hsl(220 80% 55% / 0.6);
}
.card-icon-wrapper {
  margin-top: 2px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-active {
  color: hsl(220 80% 55%);
}
.icon-inactive {
  color: hsl(0 0% 100% / 0.2);
}
.option-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.option-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-primary, #f5f5f5);
}
.option-description { font-size: 0.8rem; color: var(--color-text-muted, #888); }
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
.btn-secondary {
  padding: 0.5rem 1.25rem;
  border-radius: 8px;
  border: 1px solid hsl(0 0% 100% / 0.12);
  background: transparent;
  color: var(--color-text-muted, #888);
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.15s;
}
.btn-secondary:hover:not(:disabled) { background: hsl(0 0% 100% / 0.06); }
.btn-secondary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary {
  padding: 0.5rem 1.5rem;
  border-radius: 8px;
  border: none;
  background: hsl(220 80% 55%);
  color: #fff;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: hsl(220 80% 62%); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.modal-fade-enter-active,
.modal-fade-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-fade-enter-from,
.modal-fade-leave-to { opacity: 0; transform: scale(0.96); }
</style>
