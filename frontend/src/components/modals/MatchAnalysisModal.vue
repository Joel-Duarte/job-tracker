<script setup>
import { ref, watch, computed } from 'vue'
import { ApplicationsAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'
import CompanyLogo from '../common/CompanyLogo.vue'
import {
  X,
  Sparkles,
  Building2,
  MapPin,
  DollarSign,
  Loader2,
  CheckCircle2,
  Check,
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

    if (!analysisData.value) {
      error.value = 'No structured match analysis data found for this application.'
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
  if (application.value.match_analysis_payload) return application.value.match_analysis_payload
  for (const evt of application.value.events || []) {
    if (
      evt.raw_payload &&
      (evt.raw_payload.fit_score ||
        evt.raw_payload.match_score ||
        evt.raw_payload.hard_matches ||
        evt.raw_payload.matching_skills ||
        evt.raw_payload.pros)
    ) {
      return evt.raw_payload
    }
  }
  if (
    application.value.latest_event?.raw_payload &&
    (application.value.latest_event.raw_payload.fit_score ||
      application.value.latest_event.raw_payload.match_score ||
      application.value.latest_event.raw_payload.pros)
  ) {
    return application.value.latest_event.raw_payload
  }
  return null
})

const summaryText = computed(() => {
  if (!analysisData.value) return ''
  return (
    analysisData.value.summary ||
    analysisData.value.rationale ||
    analysisData.value.overview ||
    ''
  )
})

const strategicPros = computed(() => {
  if (!analysisData.value) return []
  if (Array.isArray(analysisData.value.pros) && analysisData.value.pros.length) {
    return analysisData.value.pros
  }
  return []
})

const strategicCons = computed(() => {
  if (!analysisData.value) return []
  if (Array.isArray(analysisData.value.cons) && analysisData.value.cons.length) {
    return analysisData.value.cons
  }
  return []
})

const matchingSkills = computed(() => {
  if (!analysisData.value) return []
  return (
    analysisData.value.matching_skills ||
    analysisData.value.hard_matches ||
    []
  )
})

const missingSkills = computed(() => {
  if (!analysisData.value) return []
  return (
    analysisData.value.missing_skills ||
    analysisData.value.missing_keywords ||
    []
  )
})

const gapMitigationText = computed(() => {
  if (!analysisData.value) return ''
  return analysisData.value.gap_mitigation || analysisData.value.mitigation || ''
})

const matchScore = computed(() => {
  return (
    application.value?.match_score ??
    analysisData.value?.match_score ??
    analysisData.value?.fit_score ??
    analysisData.value?.overall_fit_score ??
    0
  )
})

const compensationText = computed(() => {
  const min = application.value?.salary_min ?? analysisData.value?.salary_min
  const max = application.value?.salary_max ?? analysisData.value?.salary_max
  const curr = application.value?.currency ?? analysisData.value?.currency ?? 'USD'
  if (min && max) {
    return `$${Math.round(min / 1000)}k - $${Math.round(max / 1000)}k ${curr}`
  }
  if (min) return `From $${Math.round(min / 1000)}k ${curr}`
  if (max) return `Up to $${Math.round(max / 1000)}k ${curr}`
  return null
})

const locationText = computed(() => {
  return application.value?.location || analysisData.value?.location || null
})

const workModelText = computed(() => {
  return application.value?.work_model || analysisData.value?.work_model || null
})

function getFitBadgeClass(score) {
  const num = Number(score)
  if (num >= 80) return 'fit-elite'
  if (num >= 60) return 'fit-high'
  if (num >= 40) return 'fit-medium'
  return 'fit-low'
}

function getFitLabel(score) {
  const num = Number(score)
  if (num >= 80) return 'Elite Match'
  if (num >= 60) return 'Strong Fit'
  if (num >= 40) return 'Moderate Fit'
  return 'Low Alignment'
}
</script>

<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card animate-fade-in analysis-modal-container">
      <!-- Modal Top Navigation Bar -->
      <div class="modal-header">
        <div class="header-left">
          <Sparkles :size="16" class="text-primary" />
          <h2 class="modal-header-title">Role Match Assessment</h2>
        </div>
        <button class="btn-close" @click="emit('close')" title="Close Assessment Modal">
          <X :size="18" />
        </button>
      </div>

      <div class="modal-body-scroll">
        <div v-if="isLoading" class="state-container">
          <Loader2 class="animate-spin text-primary" :size="32" />
          <span>Loading assessment data...</span>
        </div>

        <div v-else-if="error" class="state-container text-danger">
          <AlertTriangle :size="32" />
          <span>{{ error }}</span>
        </div>

        <div v-else-if="analysisData" class="analysis-content">
          <!-- Hero Header Card -->
          <div class="eval-hero-card">
            <div class="hero-main-info">
              <div class="company-badge-line">
                <CompanyLogo :name="application?.company?.name" :domain="application?.company?.domain" :size="20" />
                <span class="eval-company">{{ application?.company?.name || 'Target Company' }}</span>
              </div>
              <h2 class="eval-role">{{ application?.position || 'Software Engineer' }}</h2>

              <!-- Metadata Chips Row: Compensation, Location, Work Model -->
              <div class="hero-meta-row">
                <span v-if="compensationText" class="meta-chip salary-chip">
                  <DollarSign :size="12" />
                  <span>{{ compensationText }}</span>
                </span>
                <span v-if="locationText" class="meta-chip location-chip">
                  <MapPin :size="12" />
                  <span>{{ locationText }}</span>
                </span>
                <span v-if="workModelText" class="meta-chip workmodel-chip">
                  <Building2 :size="12" />
                  <span>{{ workModelText }}</span>
                </span>
              </div>
            </div>

            <!-- Fit Score Gauge Circle -->
            <div class="eval-fit-container">
              <div class="fit-gauge" :class="getFitBadgeClass(matchScore)">
                <span class="fit-val">{{ matchScore }}%</span>
                <span class="fit-lbl">{{ getFitLabel(matchScore) }}</span>
              </div>
            </div>
          </div>

          <!-- Executive Summary -->
          <div class="analysis-section summary-card" v-if="summaryText">
            <h3 class="section-title">
              <FileText :size="15" />
              <span>Executive Summary</span>
            </h3>
            <p class="section-text">{{ summaryText }}</p>
          </div>

          <!-- Strategic Match Pros & Gaps Grid -->
          <div class="pros-cons-grid" v-if="strategicPros.length || strategicCons.length">
            <div class="pro-column" v-if="strategicPros.length">
              <div class="column-header text-success">
                <CheckCircle2 :size="14" />
                <span>Strategic Match Pros</span>
              </div>
              <ul class="dossier-list">
                <li v-for="(pro, idx) in strategicPros" :key="idx">{{ pro }}</li>
              </ul>
            </div>

            <div class="con-column" v-if="strategicCons.length">
              <div class="column-header text-warning">
                <AlertTriangle :size="14" />
                <span>Missing Gaps &amp; Considerations</span>
              </div>
              <ul class="dossier-list">
                <li v-for="(con, idx) in strategicCons" :key="idx">{{ con }}</li>
              </ul>
            </div>
          </div>

          <!-- Skills Matrix -->
          <div class="skills-matrix" v-if="matchingSkills.length || missingSkills.length">
            <div
              v-if="matchingSkills.length"
              class="skills-group matching-group"
            >
              <span class="group-title text-success">
                Matching CV Skills ({{ matchingSkills.length }}):
              </span>
              <div class="skill-tags">
                <span v-for="s in matchingSkills" :key="s" class="skill-tag match-tag">
                  <Check :size="11" />
                  <span>{{ s }}</span>
                </span>
              </div>
            </div>

            <div
              v-if="missingSkills.length"
              class="skills-group missing-group"
            >
              <span class="group-title text-warning">
                Missing / Required Skills ({{ missingSkills.length }}):
              </span>
              <div class="skill-tags">
                <span v-for="s in missingSkills" :key="s" class="skill-tag gap-tag">
                  <span>{{ s }}</span>
                </span>
              </div>
            </div>
          </div>

          <!-- Gap Mitigation Plan -->
          <div class="analysis-section gap-card" v-if="gapMitigationText">
            <h3 class="section-title text-warning">
              <AlertTriangle :size="15" />
              <span>Gap Mitigation Plan</span>
            </h3>
            <p class="section-text">{{ gapMitigationText }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: var(--bg-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.analysis-modal-container {
  width: 100%;
  max-width: 820px;
  max-height: 88vh;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-header-title {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.btn-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-close:hover {
  color: var(--text-main);
  background-color: var(--bg-elevated);
}

.modal-body-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 28px 24px;
  background-color: var(--bg-app);
}

.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  gap: 14px;
  color: var(--text-secondary);
  font-size: 14px;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* Hero Card */
.eval-hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 24px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.hero-main-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.company-badge-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.eval-company {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.eval-role {
  font-family: var(--font-heading);
  font-size: 21px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.25;
}

.hero-meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.salary-chip {
  color: var(--status-offer-text);
  background-color: var(--status-offer-bg);
  border-color: var(--status-offer-border);
  font-weight: 600;
}

.workmodel-chip {
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
}

/* Circular Gauge Container */
.eval-fit-container {
  flex-shrink: 0;
  padding: 4px;
}

.fit-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 78px;
  height: 78px;
  border-radius: 50%;
  border: 4px solid var(--border-color);
  background-color: var(--bg-card);
  box-shadow: var(--shadow-sm);
}

.fit-gauge.fit-elite {
  border-color: var(--status-offer-border);
  color: var(--status-offer-text);
  background-color: var(--status-offer-bg);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.18);
}

.fit-gauge.fit-high {
  border-color: var(--status-applied-border);
  color: var(--status-applied-text);
  background-color: var(--status-applied-bg);
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.18);
}

.fit-gauge.fit-medium {
  border-color: var(--status-interview-border);
  color: var(--status-interview-text);
  background-color: var(--status-interview-bg);
}

.fit-gauge.fit-low {
  border-color: var(--border-subtle);
  color: var(--text-muted);
  background-color: var(--bg-surface);
}

.fit-val {
  font-size: 22px;
  font-weight: 800;
  font-family: var(--font-heading);
  line-height: 1;
}

.fit-lbl {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  opacity: 0.9;
  margin-top: 3px;
  text-align: center;
}

/* Sections */
.analysis-section {
  background-color: var(--bg-surface);
  padding: 18px 20px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 10px 0;
}

.section-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0;
}

/* Pros & Cons Grid */
.pros-cons-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

@media (min-width: 640px) {
  .pros-cons-grid {
    grid-template-columns: 1fr 1fr;
  }
}

.pro-column,
.con-column {
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.pro-column {
  background-color: var(--status-offer-bg);
  border-color: var(--status-offer-border);
}

.con-column {
  background-color: var(--status-interview-bg);
  border-color: var(--status-interview-border);
}

.column-header {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.dossier-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-main);
}

.dossier-list li {
  margin-bottom: 6px;
}

.dossier-list li:last-child {
  margin-bottom: 0;
}

/* Skills Matrix */
.skills-matrix {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

@media (min-width: 640px) {
  .skills-matrix {
    grid-template-columns: 1fr 1fr;
  }
}

.skills-group {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.matching-group {
  background-color: var(--status-offer-bg);
  border-color: var(--status-offer-border);
}

.missing-group {
  background-color: var(--status-rejected-bg);
  border-color: var(--status-rejected-border);
}

.group-title {
  font-size: 12px;
  font-weight: 700;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.match-tag {
  background-color: var(--bg-card);
  color: var(--status-offer-text);
  border-color: var(--status-offer-border);
}

.gap-tag {
  background-color: var(--bg-card);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.gap-card {
  background-color: var(--status-interview-bg);
  border-color: var(--status-interview-border);
}
</style>
