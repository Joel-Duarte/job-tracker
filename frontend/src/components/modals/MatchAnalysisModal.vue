<script setup>
import { ref, watch, computed } from 'vue'
import { ApplicationsAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'
import CompanyLogo from '../common/CompanyLogo.vue'
import { getFitScores } from '../../utils/fitScores'
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
  AlertOctagon,
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

const criticalRisks = computed(() => {
  if (!analysisData.value) return []
  if (Array.isArray(analysisData.value.critical_risks) && analysisData.value.critical_risks.length) {
    return analysisData.value.critical_risks
  }
  return []
})

const seniorityFit = computed(() => {
  return analysisData.value?.seniority_fit || null
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

const scores = computed(() => {
  return getFitScores(application.value || analysisData.value)
})

const matchScore = computed(() => {
  return scores.value.aiScore ?? 0
})

const computedScoreText = computed(() => {
  return scores.value.computedText
})

const computedRatioText = computed(() => {
  return scores.value.computedRatioText || ''
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

const languageMatch = computed(() => {
  return analysisData.value?.language_match || null
})

const hasLanguageWarning = computed(() => {
  if (!languageMatch.value) return false
  if (languageMatch.value.is_matched === false) return true
  if (Array.isArray(languageMatch.value.missing_mandatory) && languageMatch.value.missing_mandatory.length > 0) return true
  if (languageMatch.value.warning) return true
  return false
})

const languageWarningText = computed(() => {
  if (!languageMatch.value) return ''
  if (languageMatch.value.warning) return languageMatch.value.warning
  if (languageMatch.value.missing_mandatory?.length) {
    const langs = languageMatch.value.missing_mandatory.join(', ')
    const jdLang = languageMatch.value.detected_jd_language || 'target language'
    return `Role requires mandatory spoken language: ${langs} (Posting written in ${jdLang}), which is not listed on your profile.`
  }
  return ''
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
          <!-- Language Mismatch Warning Banner -->
          <div v-if="hasLanguageWarning" class="language-warning-banner animate-fade-in">
            <div class="lang-banner-icon">
              <AlertTriangle :size="20" class="text-warning" />
            </div>
            <div class="lang-banner-content">
              <div class="lang-banner-title">
                <span>Spoken Language Requirement Mismatch</span>
                <span class="lang-badge" v-if="languageMatch?.detected_jd_language">
                  JD Language: {{ languageMatch.detected_jd_language }}
                </span>
              </div>
              <p class="lang-banner-desc">
                {{ languageWarningText }}
              </p>
              <p class="lang-banner-sub">
                * Note: The fit score below reflects pure technical &amp; domain qualification. Verify you meet language requirements before applying.
              </p>
            </div>
          </div>

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

            <!-- Side-by-Side Fit Score Badges: Programmatic Overlap + AI Score Badge Card -->
            <div class="eval-fit-container">
              <div class="scores-side-by-side">
                <div class="score-badge-card algo-card">
                  <span class="score-badge-val font-mono">{{ computedScoreText }}</span>
                  <span class="score-badge-lbl">Algo Overlap</span>
                  <span v-if="computedRatioText" class="score-badge-sub">{{ computedRatioText }}</span>
                </div>
                <div class="score-badge-card ai-card" :class="getFitBadgeClass(matchScore)">
                  <span class="score-badge-val font-mono">{{ matchScore }}%</span>
                  <span class="score-badge-lbl">{{ getFitLabel(matchScore) }}</span>
                </div>
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

          <!-- Critical Hiring Risks & Recruiter Hesitations Warning Card -->
          <div class="critical-risks-card" v-if="criticalRisks.length">
            <div class="critical-risks-header">
              <div class="risk-header-left">
                <AlertOctagon :size="16" class="risk-icon" />
                <span class="risk-title">Critical Risks &amp; Recruiter Hesitations</span>
              </div>
              <span class="seniority-tag" v-if="seniorityFit" :class="seniorityFit.toLowerCase()">
                Seniority: {{ seniorityFit }}
              </span>
            </div>
            <p class="risk-subtitle">
              Skeptical hiring screener audit identified potential deal-breakers or friction points:
            </p>
            <ul class="risk-list">
              <li v-for="(risk, idx) in criticalRisks" :key="idx">
                <span class="risk-bullet"></span>
                <span>{{ risk }}</span>
              </li>
            </ul>
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

@media (max-width: 767px) {
  .modal-backdrop {
    padding: 0;
    align-items: stretch;
    justify-content: stretch;
  }

  .analysis-modal-container {
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    max-height: 100dvh;
    max-width: 100vw;
    border-radius: 0;
    border: none;
  }

  .modal-header {
    padding: 14px 16px;
  }

  .btn-close {
    min-width: 48px;
    min-height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-body-scroll {
    padding: 16px;
    padding-bottom: max(16px, env(safe-area-inset-bottom));
  }

  .eval-hero-card {
    flex-direction: column;
    align-items: flex-start;
    padding: 16px;
  }

  .eval-fit-container {
    width: 100%;
    margin-top: 8px;
  }

  .scores-side-by-side {
    width: 100%;
  }

  .score-badge-card {
    flex: 1;
    min-width: 0;
  }

  .pros-cons-grid,
  .skills-matrix {
    grid-template-columns: 1fr;
  }
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

/* Language Warning Banner */
.language-warning-banner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 18px;
  background-color: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: var(--radius-md);
}

.lang-banner-icon {
  flex-shrink: 0;
  padding-top: 2px;
}

.lang-banner-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.lang-banner-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-warning);
}

.lang-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  background-color: var(--bg-surface);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 4px;
  color: var(--text-main);
}

.lang-banner-desc {
  font-size: 13px;
  color: var(--text-main);
  line-height: 1.45;
  margin: 0;
}

.lang-banner-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0;
  font-style: italic;
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

/* Circular Gauge Container & Side-by-Side Scores */
.eval-fit-container {
  flex-shrink: 0;
  padding: 4px;
}

.scores-side-by-side {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-badge-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background-color: var(--bg-card);
  min-width: 80px;
}

.algo-card {
  background-color: var(--bg-surface);
  border-color: var(--border-color);
}

.score-badge-sub {
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
}

.ai-card.fit-elite {
  border-color: var(--status-offer-border);
  color: var(--status-offer-text);
  background-color: var(--status-offer-bg);
}

.ai-card.fit-high {
  border-color: var(--status-applied-border);
  color: var(--status-applied-text);
  background-color: var(--status-applied-bg);
}

.ai-card.fit-medium {
  border-color: var(--status-interview-border);
  color: var(--status-interview-text);
  background-color: var(--status-interview-bg);
}

.ai-card.fit-low {
  border-color: var(--border-subtle);
  color: var(--text-muted);
  background-color: var(--bg-surface);
}

.ai-card.fit-elite .score-badge-val { color: var(--status-offer-text); }
.ai-card.fit-high .score-badge-val { color: var(--status-applied-text); }
.ai-card.fit-medium .score-badge-val { color: var(--status-interview-text); }
.ai-card.fit-low .score-badge-val { color: var(--text-muted); }

.ai-card.fit-elite .score-badge-lbl { color: var(--status-offer-text); opacity: 0.9; }
.ai-card.fit-high .score-badge-lbl { color: var(--status-applied-text); opacity: 0.9; }
.ai-card.fit-medium .score-badge-lbl { color: var(--status-interview-text); opacity: 0.9; }
.ai-card.fit-low .score-badge-lbl { color: var(--text-muted); opacity: 0.9; }

.score-badge-val {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-main);
  line-height: 1;
}

.score-badge-lbl {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-top: 4px;
  letter-spacing: 0.3px;
  white-space: nowrap;
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

/* Critical Risks Warning Card */
.critical-risks-card {
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.critical-risks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.risk-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-icon {
  color: #ef4444;
  flex-shrink: 0;
}

.risk-title {
  font-size: 13px;
  font-weight: 700;
  color: #ef4444;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.seniority-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.seniority-tag.matches {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.3);
}

.seniority-tag.overqualified {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.3);
}

.risk-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.4;
}

.risk-list {
  margin: 4px 0 0 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.risk-list li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-main);
}

.risk-bullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
  margin-top: 6px;
  flex-shrink: 0;
}
</style>
