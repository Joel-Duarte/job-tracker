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

const parsedTailoringStrategy = computed(() => {
  if (!analysisData.value?.tailoring_strategy) return null
  try {
    const raw = analysisData.value.tailoring_strategy
    if (typeof raw === 'object') return raw // already parsed
    // Attempt to parse string to JSON
    // Clean up markdown block format if LLM returned it in ```json blocks
    let cleaned = raw.trim()
    if (cleaned.startsWith('```json')) cleaned = cleaned.replace(/^```json/, '')
    if (cleaned.startsWith('```')) cleaned = cleaned.replace(/^```/, '')
    if (cleaned.endsWith('```')) cleaned = cleaned.replace(/```$/, '')
    return JSON.parse(cleaned)
  } catch (err) {
    console.error("Failed to parse tailoring strategy JSON:", err)
    return null
  }
})

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
      <div class="modal-header" style="justify-content: flex-end; padding: 12px 16px; border-bottom: none;">
        <button class="btn-close" @click="emit('close')"><X :size="18" /></button>
      </div>

      <div class="modal-body-scroll" style="padding-top: 0;">
        <div v-if="isLoading" class="state-container">
          <Loader2 class="animate-spin text-primary" :size="32" />
          <span>Loading analysis...</span>
        </div>

        <div v-else-if="error" class="state-container text-danger">
          <AlertTriangle :size="32" />
          <span>{{ error }}</span>
        </div>

        <div v-else-if="analysisData" class="analysis-content">
          <!-- Hero Header like Dossier -->
          <div class="eval-card-header">
            <div class="eval-title-group">
              <div class="company-badge-line">
                <span class="eval-company">{{ application?.company?.name || 'Target Company' }}</span>
              </div>
              <h2 class="eval-role">{{ application?.position || 'Software Engineer' }}</h2>
            </div>

            <!-- Fit Score Gauge -->
            <div class="eval-fit-container">
              <div class="fit-gauge" :class="getFitBadgeClass(matchScore)">
                <span class="fit-val">{{ matchScore }}%</span>
                <span class="fit-lbl">{{ getFitLabel(matchScore) }}</span>
              </div>
            </div>
          </div>

          <div class="analysis-section" v-if="analysisData.summary">
             <h3 class="section-title"><FileText :size="15" /> Executive Summary</h3>
             <p class="section-text">{{ analysisData.summary }}</p>
          </div>

          <div class="skills-grid">
            <div class="skills-card matching" v-if="analysisData.matching_skills?.length">
               <h3 class="skills-title"><CheckCircle2 :size="15" /> Strategic Match Pros</h3>
               <div class="skills-list">
                 <span v-for="skill in analysisData.matching_skills" :key="skill" class="skill-tag match">{{ skill }}</span>
               </div>
            </div>
            <div class="skills-card missing" v-if="analysisData.missing_skills?.length">
               <h3 class="skills-title"><AlertTriangle :size="15" /> Missing Gaps & Considerations</h3>
               <div class="skills-list">
                 <span v-for="skill in analysisData.missing_skills" :key="skill" class="skill-tag miss">{{ skill }}</span>
               </div>
            </div>
          </div>

          <div class="analysis-section gap-card" v-if="analysisData.gap_mitigation">
             <h3 class="section-title text-warning"><AlertTriangle :size="15" /> Gap Mitigation Plan</h3>
             <p class="section-text">{{ analysisData.gap_mitigation }}</p>
          </div>

          <!-- Tailoring Strategy -->
          <div class="analysis-section" v-if="analysisData.tailoring_strategy">
             <h3 class="section-title"><Sparkles :size="15" /> Recommended Resume Tailoring Strategy</h3>

             <div v-if="parsedTailoringStrategy" class="tailoring-parsed">
               <div v-if="parsedTailoringStrategy.impact_reframing?.length" class="tailoring-block">
                 <h4 class="tailoring-subtitle">Impact Reframing</h4>
                 <div v-for="(item, i) in parsedTailoringStrategy.impact_reframing" :key="i" class="reframing-card">
                   <div class="reframing-reason">{{ item.reason }}</div>
                   <div class="reframing-before">
                     <span class="reframing-label">Before:</span>
                     <span class="reframing-text">{{ item.bullet_point }}</span>
                   </div>
                   <div class="reframing-after">
                     <span class="reframing-label">After:</span>
                     <span class="reframing-text">{{ item.suggested_rewrite }}</span>
                   </div>
                 </div>
               </div>

               <div v-if="parsedTailoringStrategy.structural_adjustments?.length" class="tailoring-block">
                 <h4 class="tailoring-subtitle">Structural Adjustments</h4>
                 <ul class="structural-list">
                   <li v-for="(adj, i) in parsedTailoringStrategy.structural_adjustments" :key="i">
                     <CheckCircle2 :size="13" class="text-primary mt-0.5" />
                     <span>{{ adj }}</span>
                   </li>
                 </ul>
               </div>

               <div v-if="parsedTailoringStrategy.vocabulary_translation?.length" class="tailoring-block">
                 <h4 class="tailoring-subtitle">Vocabulary Mapping</h4>
                 <div class="vocab-grid">
                   <div v-for="(vocab, i) in parsedTailoringStrategy.vocabulary_translation" :key="i" class="vocab-card">
                     <div class="vocab-flow">
                       <span class="vocab-cv">{{ vocab.cv_term }}</span>
                       <span class="vocab-arrow">➔</span>
                       <span class="vocab-jd">{{ vocab.jd_term }}</span>
                     </div>
                     <div class="vocab-desc">{{ vocab.replacement_guidance }}</div>
                   </div>
                 </div>
               </div>
             </div>

             <p v-else class="section-text fallback-text">{{ analysisData.tailoring_strategy }}</p>
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

.tailoring-parsed {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 12px;
}

.tailoring-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tailoring-subtitle {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.8;
  margin: 0 0 4px 0;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 4px;
}

.reframing-card {
  background-color: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reframing-reason {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background-color: var(--bg-surface);
  display: inline-flex;
  padding: 2px 6px;
  border-radius: 4px;
  width: fit-content;
  margin-bottom: 2px;
}

.reframing-before, .reframing-after {
  font-size: 12px;
  line-height: 1.4;
  display: flex;
  gap: 6px;
}

.reframing-before {
  color: var(--status-rejected-text);
  opacity: 0.9;
}

.reframing-after {
  color: var(--status-offer-text);
  font-weight: 500;
}

.reframing-label {
  font-weight: 700;
  flex-shrink: 0;
}

.reframing-before .reframing-text {
  text-decoration: line-through;
}

.structural-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.structural-list li {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.vocab-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.vocab-card {
  background-color: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vocab-flow {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
}

.vocab-cv {
  color: var(--text-muted);
  background-color: var(--bg-surface);
  padding: 2px 6px;
  border-radius: 4px;
  text-decoration: line-through;
}

.vocab-arrow {
  color: var(--text-secondary);
  font-size: 10px;
}

.vocab-jd {
  color: var(--primary);
  background-color: var(--primary-subtle);
  padding: 2px 6px;
  border-radius: 4px;
}

.vocab-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-top: 4px;
}

.fallback-text {
  white-space: pre-wrap;
  font-family: var(--font-mono);
  font-size: 11px;
  background-color: var(--bg-app);
  padding: 10px;
  border-radius: var(--radius-sm);
}


.eval-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid var(--border-subtle);
  background-color: var(--bg-surface);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  margin: -24px -24px 20px -24px;
}

.eval-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.company-badge-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.eval-company {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.eval-role {
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.2;
}

.eval-fit-container {
  flex-shrink: 0;
}

.fit-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 4px solid var(--border-color);
  background-color: var(--bg-card);
}

.fit-gauge.fit-elite { border-color: var(--status-offer-border); color: var(--status-offer-text); background-color: var(--status-offer-bg); }
.fit-gauge.fit-high { border-color: var(--status-applied-border); color: var(--status-applied-text); background-color: var(--status-applied-bg); }
.fit-gauge.fit-medium { border-color: var(--status-interview-border); color: var(--status-interview-text); background-color: var(--status-interview-bg); }
.fit-gauge.fit-low { border-color: var(--border-subtle); color: var(--text-muted); background-color: var(--bg-surface); }

.fit-val {
  font-size: 20px;
  font-weight: 800;
  font-family: var(--font-heading);
  line-height: 1;
}

.fit-lbl {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  opacity: 0.9;
  margin-top: 2px;
  text-align: center;
}

.skills-card.matching {
  background-color: var(--status-offer-bg);
  border-color: var(--status-offer-border);
}

.skills-card.missing {
  background-color: var(--status-rejected-bg);
  border-color: var(--status-rejected-border);
}

.gap-card {
  background-color: var(--status-interview-bg);
  border-color: var(--status-interview-border);
}

</style>
