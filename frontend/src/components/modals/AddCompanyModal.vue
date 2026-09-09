<script setup>
import { ref, watch, nextTick } from 'vue'
import {
  Building2,
  Globe,
  Sparkles,
  X,
  Loader2,
} from 'lucide-vue-next'
import { CompaniesAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  initialName: {
    type: String,
    default: '',
  },
  initialUrl: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'close', 'created'])

const uiStore = useUIStore()

const nameInputRef = ref(null)
const companyName = ref('')
const companyUrl = ref('')
const companyAboutUrl = ref('')
const isSubmitting = ref(false)

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      companyName.value = props.initialName || ''
      companyUrl.value = props.initialUrl || ''
      companyAboutUrl.value = ''
      nextTick(() => {
        nameInputRef.value?.focus()
      })
    }
  }
)

function closeModal() {
  if (isSubmitting.value) return
  emit('update:modelValue', false)
  emit('close')
}

async function handleCreate(queueResearch = false) {
  const name = companyName.value.trim()
  if (!name) {
    uiStore.showToast('Please enter a company name', 'warning')
    return
  }

  isSubmitting.value = true
  try {
    const payload = {
      name,
      domain: companyUrl.value.trim() || null,
      about_url: companyAboutUrl.value.trim() || null,
      queue_research: queueResearch,
    }

    const res = await CompaniesAPI.create(payload)
    const createdCompany = res.data

    uiStore.showToast(
      queueResearch
        ? `Company '${createdCompany.name}' created and web research queued!`
        : `Company '${createdCompany.name}' created successfully!`,
      'success'
    )

    emit('created', createdCompany)
    closeModal()
  } catch (err) {
    const errorMsg = err.response?.data?.detail || err.message || 'Failed to create company'
    uiStore.showToast(errorMsg, 'error')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="modelValue"
        class="modal-backdrop"
        @click.self="closeModal"
      >
        <div class="modal-card animate-fade-in add-company-modal">
          <div class="modal-header">
            <div class="modal-header-title-wrap">
              <div class="modal-header-icon-wrap">
                <Building2 :size="18" class="text-primary" />
              </div>
              <div>
                <h3 class="modal-title">Add Company</h3>
                <p class="modal-subtitle">Create an employer entity to track applications and live intelligence.</p>
              </div>
            </div>
            <button
              type="button"
              class="btn-close"
              :disabled="isSubmitting"
              @click="closeModal"
              title="Close modal"
            >
              <X :size="18" />
            </button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label required">Company Name</label>
              <input
                ref="nameInputRef"
                v-model="companyName"
                type="text"
                class="form-input"
                placeholder="e.g. Stripe, Acme Corp, Linear"
                :disabled="isSubmitting"
                @keydown.enter.prevent="handleCreate(false)"
              />
            </div>

            <div class="form-group">
              <label class="form-label">
                <span>Website or Careers URL</span>
                <span class="text-muted font-normal">(Optional)</span>
              </label>
              <div class="input-with-icon">
                <Globe :size="15" class="input-icon text-muted" />
                <input
                  v-model="companyUrl"
                  type="text"
                  class="form-input"
                  placeholder="e.g. stripe.com or https://stripe.com/jobs"
                  :disabled="isSubmitting"
                  @keydown.enter.prevent="handleCreate(false)"
                />
              </div>
              <p class="form-hint">
                ATS URLs like Greenhouse or Lever and path prefixes are automatically cleaned into root domains.
              </p>
            </div>

            <div class="form-group">
              <label class="form-label">
                <span>"About Us" or Info Page URL</span>
                <span class="text-muted font-normal">(Optional)</span>
              </label>
              <input
                v-model="companyAboutUrl"
                type="text"
                class="form-input"
                placeholder="e.g. https://company.com/about or /company"
                :disabled="isSubmitting"
              />
              <p class="form-hint">
                Direct link to help the web scraper pinpoint corporate mission and engineering culture.
              </p>
            </div>

            <div class="research-recommendation-box">
              <div class="box-icon">
                <Sparkles :size="18" class="text-primary" />
              </div>
              <div class="box-content">
                <h5 class="box-title">AI Live Web Intelligence</h5>
                <p class="box-desc">
                  Queueing web research will search DuckDuckGo/SearXNG and synthesize corporate culture, public reviews, and strategic overview in the background AI Queue.
                </p>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="isSubmitting"
              @click="closeModal"
            >
              Cancel
            </button>

            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="isSubmitting || !companyName.trim()"
              @click="handleCreate(false)"
              title="Create company without running background research"
            >
              <Loader2 v-if="isSubmitting" :size="14" class="animate-spin" />
              <span>Create Only</span>
            </button>

            <button
              type="button"
              class="btn btn-primary btn-sm btn-create-research"
              :disabled="isSubmitting || !companyName.trim()"
              @click="handleCreate(true)"
              title="Create company and immediately enqueue AI web research"
            >
              <Loader2 v-if="isSubmitting" :size="14" class="animate-spin" />
              <Sparkles v-else :size="14" />
              <span>Create & Queue Research</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: var(--bg-backdrop, rgba(0, 0, 0, 0.75));
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100000;
  padding: 16px;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-card {
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-fade-enter-from .modal-card {
  transform: scale(0.96) translateY(8px);
}

.add-company-modal {
  width: 100%;
  max-width: 520px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg, 8px);
  box-shadow: var(--shadow-xl, 0 20px 25px -5px rgba(0, 0, 0, 0.4));
  overflow: hidden;
  position: relative;
  font-family: var(--font-sans);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.modal-header-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md, 6px);
  background: var(--primary-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.btn-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xs);
  transition: color var(--transition-fast), background var(--transition-fast);
}

.btn-close:hover {
  color: var(--text-main);
  background: var(--bg-surface-hover);
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 6px;
}

.form-label.required::after {
  content: "*";
  color: var(--text-danger, #ef4444);
  margin-left: 2px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  font-size: 13px;
  font-family: inherit;
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--transition-fast);
}

.form-input:focus {
  border-color: var(--border-focus);
}

.form-input::placeholder {
  color: var(--text-muted);
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 10px;
  pointer-events: none;
  color: var(--text-muted);
}

.input-with-icon .form-input {
  padding-left: 32px;
}

.form-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin: 2px 0 0 0;
  line-height: 1.4;
}

.research-recommendation-box {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  background: var(--primary-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.box-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.box-content {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.box-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.box-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 0;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--bg-card);
}

.btn-create-research {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
