<script setup>
import { ref, watch, computed } from 'vue'
import { ApplicationsAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'
import {
  X,
  Sparkles,
  Building2,
  Briefcase,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  FileText
} from 'lucide-vue-next'

const props = defineProps({
  isOpen: Boolean,
  applicationId: Number
})

const emit = defineEmits(['close'])
const uiStore = useUIStore()

const isLoading = ref(true)
const application = ref(null)
const error = ref(null)

watch(() => props.isOpen, async (newVal) => {
  if (newVal && props.applicationId) {
    await loadApplication()
  } else {
    application.value = null
    error.value = null
  }
})

async function loadApplication() {
  isLoading.value = true
  error.value = null
  try {
    const res = await ApplicationsAPI.get(props.applicationId)
    application.value = res.data
    if (!application.value.latest_event || !application.value.latest_event.raw_payload) {
      // Look through events to find the assessment payload if latest is not assessment
      let found = false
      for (const ev of application.value.events) {
        if (ev.email_event_type === 'PRE_APPLICATION_ASSESSMENT' && ev.raw_payload) {
          application.value.latest_event = ev
          found = true
          break
        }
      }
      if (!found && !application.value.match_score) {
          error.value = 'No structured match analysis data found for this application.'
      }
    }
  } catch (err) {
    error.value = 'Failed to load application details.'
    uiStore.showToast(error.value, 'error')
  } finally {
    isLoading.value = false
  }
}

const analysisData = computed(() => {
  if (!application.value) return null
  return application.value.latest_event?.raw_payload || {}
})

const matchScore = computed(() => {
  return application.value?.match_score ?? analysisData.value?.match_score ?? analysisData.value?.fit_score ?? 0
})

function getFitBadgeClass(score) {
  const num = Number(score)
  if (num >= 80) return 'fit-elite'
  if (num >= 60) return 'fit-high'
  if (num >= 40) return 'fit-medium'
  return 'fit-low'
}
</script>

<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card animate-fade-in analysis-modal-container">
      <div class="modal-header">
        <div class="header-main-info">
          <div class="header-title-row">
            <h2 class="modal-title">AI Match Assessment</h2>
            <span v-if="application?.company?.name" class="company-tag">
              <Building2 :size="12" />
              <span>{{ application.company.name }}</span>
            </span>
            <span v-if="application?.position" class="position-tag">
              <Briefcase :size="12" />
              <span>{{ application.position }}</span>
            </span>
          </div>
        </div>
        <button class="btn-close" @click="emit('close')"><X :size="18" /></button>
      </div>

      <div class="modal-body-scroll">
        <div v-if="isLoading" class="state-container">
          <Loader2 class="animate-spin text-primary" :size="32" />
          <span>Loading analysis...</span>
        </div>

        <div v-else-if="error" class="state-container text-danger">
          <AlertTriangle :size="32" />
          <span>{{ error }}</span>
        </div>

        <div v-else-if="analysisData" class="analysis-content">
          <!-- Overall Match Score -->
          <div class="score-card" :class="getFitBadgeClass(matchScore)">
            <div class="score-header">
              <Sparkles :size="24" />
              <div class="score-number">{{ matchScore }}%</div>
            </div>
            <div class="score-label">Overall Match Fit</div>
          </div>

          <div class="analysis-grid">
            <div class="analysis-section" v-if="analysisData.summary">
               <h3 class="section-title"><FileText :size="15" /> Executive Summary</h3>
               <p class="section-text">{{ analysisData.summary }}</p>
            </div>
            <div class="analysis-section" v-if="analysisData.tailoring_strategy">
               <h3 class="section-title"><Sparkles :size="15" /> Tailoring Strategy</h3>
               <p class="section-text">{{ analysisData.tailoring_strategy }}</p>
            </div>
          </div>

          <div class="skills-grid">
            <div class="skills-card matching" v-if="analysisData.matching_skills?.length">
               <h3 class="skills-title"><CheckCircle2 :size="15" /> Matching Skills</h3>
               <div class="skills-list">
                 <span v-for="skill in analysisData.matching_skills" :key="skill" class="skill-tag match">{{ skill }}</span>
               </div>
            </div>
            <div class="skills-card missing" v-if="analysisData.missing_skills?.length">
               <h3 class="skills-title"><AlertTriangle :size="15" /> Missing Skills / Gaps</h3>
               <div class="skills-list">
                 <span v-for="skill in analysisData.missing_skills" :key="skill" class="skill-tag miss">{{ skill }}</span>
               </div>
            </div>
          </div>

          <div class="analysis-section" v-if="analysisData.gap_mitigation" style="margin-top: 16px;">
             <h3 class="section-title text-warning"><AlertTriangle :size="15" /> Gap Mitigation Plan</h3>
             <p class="section-text">{{ analysisData.gap_mitigation }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; background-color: var(--bg-backdrop);
  display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px;
}
.analysis-modal-container {
  width: 100%; max-width: 800px; max-height: 85vh; background-color: var(--bg-card);
  border: 1px solid var(--border-color); border-radius: var(--radius-lg); box-shadow: var(--shadow-xl);
  display: flex; flex-direction: column; overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between; padding: 16px 24px;
  border-bottom: 1px solid var(--border-color); background-color: var(--bg-surface); flex-shrink: 0;
}
.header-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.modal-title { font-family: var(--font-heading); font-size: 18px; color: var(--text-main); margin: 0; font-weight: 700; }
.company-tag, .position-tag {
  display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: var(--radius-sm);
  background-color: var(--bg-elevated); border: 1px solid var(--border-color); font-size: 12px; color: var(--text-secondary);
}
.modal-body-scroll { flex: 1; overflow-y: auto; padding: 24px; background-color: var(--bg-app); }
.state-container { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; gap: 16px; }

.analysis-content { display: flex; flex-direction: column; gap: 20px; }

.score-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 20px; border-radius: var(--radius-md); border: 1px solid var(--border-color);
  background-color: var(--bg-surface); gap: 8px; width: 100%; max-width: 250px; margin: 0 auto;
}
.score-card.fit-elite { background-color: var(--status-offer-bg); color: var(--status-offer-text); border-color: var(--status-offer-border); }
.score-card.fit-high { background-color: var(--status-applied-bg); color: var(--status-applied-text); border-color: var(--status-applied-border); }
.score-card.fit-medium { background-color: var(--status-interview-bg); color: var(--status-interview-text); border-color: var(--status-interview-border); }
.score-card.fit-low { background-color: var(--bg-surface); color: var(--text-muted); }
.score-header { display: flex; align-items: center; gap: 10px; }
.score-number { font-size: 36px; font-weight: 800; font-family: var(--font-heading); }
.score-label { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }

.analysis-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
@media (min-width: 640px) { .analysis-grid { grid-template-columns: 1fr 1fr; } }
.analysis-section { background-color: var(--bg-surface); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); }
.section-title { font-size: 14px; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 6px; margin: 0 0 8px 0; }
.section-text { font-size: 13px; line-height: 1.5; color: var(--text-secondary); margin: 0; }

.skills-grid { display: grid; grid-template-columns: 1fr; gap: 16px; margin-top: 16px; }
@media (min-width: 640px) { .skills-grid { grid-template-columns: 1fr 1fr; } }
.skills-card { background-color: var(--bg-surface); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); }
.skills-title { font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 6px; margin: 0 0 12px 0; }
.skills-card.matching .skills-title { color: var(--status-offer-text); }
.skills-card.missing .skills-title { color: var(--status-rejected-text); }
.skills-list { display: flex; flex-wrap: wrap; gap: 6px; }
.skill-tag { padding: 4px 8px; font-size: 12px; font-weight: 500; border-radius: var(--radius-sm); border: 1px solid var(--border-color); }
.skill-tag.match { background-color: var(--status-offer-bg); color: var(--status-offer-text); border-color: var(--status-offer-border); }
.skill-tag.miss { background-color: var(--status-rejected-bg); color: var(--status-rejected-text); border-color: var(--status-rejected-border); }
</style>
