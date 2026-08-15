<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '../stores/uiStore'
import { useApplicationsStore } from '../stores/applicationsStore'
import { IntakeAPI } from '../api/endpoints'
import {
  Sparkles,
  Link as LinkIcon,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Building2,
  DollarSign,
  MapPin,
  Loader2,
  ArrowRight,
  ShieldCheck,
  Check,
  X,
  Info,
  Copy,
  Puzzle,
  Globe,
  Layers,
} from 'lucide-vue-next'

const router = useRouter()
const uiStore = useUIStore()
const appStore = useApplicationsStore()

const jobUrl = ref('')
const jobText = ref('')
const isAnalyzing = ref(false)
const isSaving = ref(false)
const assessmentResult = ref(null)

const copiedUrl = ref(false)
const copiedJd = ref(false)
const urlEndpoint = ref('Loading...')
const jdEndpoint = ref('Loading...')

async function fetchExtensionConfig() {
  try {
    const res = await IntakeAPI.getExtensionConfig()
    if (res.data?.url_endpoint) {
      urlEndpoint.value = res.data.url_endpoint
      jdEndpoint.value = res.data.jd_endpoint
    }
  } catch (err) {
    const host = window.location.hostname || 'localhost'
    const port = window.location.port === '5173' ? '8000' : window.location.port || '8000'
    const proto = window.location.protocol || 'http:'
    urlEndpoint.value = `${proto}//${host}:${port}/api/v1/intake/url`
    jdEndpoint.value = `${proto}//${host}:${port}/api/v1/intake/jd`
  }
}

function copyToClipboard(val, type) {
  navigator.clipboard.writeText(val)
  if (type === 'url') {
    copiedUrl.value = true
    setTimeout(() => { copiedUrl.value = false }, 2000)
  } else {
    copiedJd.value = true
    setTimeout(() => { copiedJd.value = false }, 2000)
  }
  uiStore.showToast('Endpoint URL copied to clipboard!', 'info')
}

async function runAssessment() {
  if (!jobUrl.value.trim() && !jobText.value.trim()) {
    uiStore.showToast('Please provide a job posting URL or paste the job description text.', 'error')
    return
  }

  isAnalyzing.value = true
  assessmentResult.value = null

  try {
    const res = await IntakeAPI.assessJob({
      url: jobUrl.value.trim() || null,
      text: jobText.value.trim() || null,
    })
    assessmentResult.value = res.data
    uiStore.showToast('AI Pre-Application assessment completed!', 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isAnalyzing.value = false
  }
}

async function confirmAndProcess(targetStatus = 'ASSESSMENT') {
  if (!assessmentResult.value) return
  isSaving.value = true

  try {
    const res = await IntakeAPI.confirmAssessment({
      company: assessmentResult.value.company,
      position: assessmentResult.value.position,
      status: targetStatus,
      job_url: jobUrl.value.trim() || null,
      description_markdown: jobText.value.trim() || assessmentResult.value.summary,
      salary_min: assessmentResult.value.salary_min,
      salary_max: assessmentResult.value.salary_max,
      currency: assessmentResult.value.currency,
      location: assessmentResult.value.location,
      work_model: assessmentResult.value.work_model,
      required_skills: [
        ...(assessmentResult.value.matching_skills || []),
        ...(assessmentResult.value.missing_skills || []),
      ],
    })

    uiStore.showToast(`Saved '${assessmentResult.value.company}' to ${targetStatus}!`, 'success')
    appStore.fetchApplications()
    router.push('/')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  fetchExtensionConfig()
})
</script>

<template>
  <div class="page-container">
    <div class="intake-header">
      <div class="header-badge">
        <Sparkles :size="14" />
        <span>Pre-Application Intelligence</span>
      </div>
      <h1 class="page-title">Job Lead Intake & AI Assessment</h1>
      <p class="page-subtitle">
        Paste a career portal URL or job description. Our hybrid engine calculates programmatic keyword overlap against your profile, then runs qualitative AI evaluation before applying.
      </p>
    </div>

    <!-- LinkedIn Advisory Banner -->
    <div class="advisory-banner">
      <Info :size="16" class="text-primary flex-shrink-0" />
      <span>
        <strong>LinkedIn & Protected Portals:</strong> LinkedIn actively blocks automated scrapers. If your posting is from LinkedIn, please copy and paste the job description text below directly for best results.
      </span>
    </div>

    <!-- Browser Extension Endpoints Configuration Bar -->
    <div class="extension-config-card">
      <div class="card-top">
        <div class="card-title">
          <Puzzle :size="15" class="text-primary" />
          <span>Browser Extension Endpoints</span>
        </div>
        <span class="text-xs text-muted">Paste these endpoints in your extension settings</span>
      </div>

      <div class="endpoints-grid">
        <!-- URL Endpoint -->
        <div class="endpoint-item">
          <div class="endpoint-meta">
            <Globe :size="14" class="text-secondary" />
            <span class="endpoint-name">URL Endpoint (Send URL):</span>
          </div>
          <div class="endpoint-input-row">
            <span class="endpoint-val font-mono">{{ urlEndpoint }}</span>
            <button class="btn btn-secondary btn-xs" @click="copyToClipboard(urlEndpoint, 'url')">
              <Check v-if="copiedUrl" :size="12" class="text-success" />
              <Copy v-else :size="12" />
              <span>{{ copiedUrl ? 'Copied' : 'Copy' }}</span>
            </button>
          </div>
        </div>

        <!-- JD Elements Endpoint -->
        <div class="endpoint-item">
          <div class="endpoint-meta">
            <Layers :size="14" class="text-secondary" />
            <span class="endpoint-name">JD Elements Endpoint (Send DOM):</span>
          </div>
          <div class="endpoint-input-row">
            <span class="endpoint-val font-mono">{{ jdEndpoint }}</span>
            <button class="btn btn-secondary btn-xs" @click="copyToClipboard(jdEndpoint, 'jd')">
              <Check v-if="copiedJd" :size="12" class="text-success" />
              <Copy v-else :size="12" />
              <span>{{ copiedJd ? 'Copied' : 'Copy' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Intake Input Card -->
    <div class="intake-card">
      <div class="input-section">
        <label class="section-label">
          <LinkIcon :size="15" />
          <span>Job Posting URL (Greenhouse, Lever, Workday, etc.)</span>
        </label>
        <input
          v-model="jobUrl"
          type="url"
          placeholder="https://boards.greenhouse.io/company/jobs/123456"
          class="form-input"
        />
      </div>

      <div class="input-section">
        <div class="label-row">
          <label class="section-label">
            <FileText :size="15" />
            <span>Job Description & Requirements Text</span>
          </label>
          <span class="text-xs text-primary font-semibold">
            * Please include Company Name and Job Title in the text
          </span>
        </div>
        <textarea
          v-model="jobText"
          rows="7"
          placeholder="e.g. Stripe - Senior Backend Engineer&#10;&#10;About the Role...&#10;Responsibilities...&#10;Requirements: Python, PostgreSQL, Distributed Systems..."
          class="form-textarea font-mono text-xs"
        ></textarea>
      </div>

      <div class="intake-actions">
        <button
          class="btn btn-primary btn-assess"
          :disabled="isAnalyzing || (!jobUrl.trim() && !jobText.trim())"
          @click="runAssessment"
        >
          <Loader2 v-if="isAnalyzing" class="animate-spin" :size="16" />
          <Sparkles v-else :size="16" />
          <span>{{ isAnalyzing ? 'Running Hybrid Match & AI Assessment...' : 'Evaluate Job Fit' }}</span>
        </button>
      </div>
    </div>

    <!-- Real-Time AI Pre-Assessment Result -->
    <div v-if="assessmentResult" class="assessment-dashboard animate-fade-in">
      <div class="dashboard-header">
        <div class="header-left">
          <div class="company-icon-box">
            <Building2 :size="22" />
          </div>
          <div>
            <h2 class="company-title">{{ assessmentResult.company }}</h2>
            <div class="role-title">{{ assessmentResult.position }}</div>
          </div>
        </div>

        <!-- Dual Scores: Programmatic Overlap + AI Fit Score -->
        <div class="scores-group">
          <div class="score-badge-box">
            <div class="score-num font-mono">{{ assessmentResult.programmatic_match_score || 0 }}%</div>
            <div class="score-lbl">Keyword Overlap</div>
          </div>

          <div class="score-badge-box score-ai-box">
            <div class="score-num font-mono">{{ assessmentResult.fit_score }}%</div>
            <div class="score-lbl">AI Qualitative Fit</div>
          </div>
        </div>
      </div>

      <!-- Quick Metrics Grid -->
      <div class="metrics-grid">
        <div class="metric-card">
          <DollarSign :size="16" class="metric-icon" />
          <div>
            <div class="metric-k">Compensation</div>
            <div class="metric-v">
              <span v-if="assessmentResult.salary_min || assessmentResult.salary_max">
                ${{ assessmentResult.salary_min?.toLocaleString() }} - ${{ assessmentResult.salary_max?.toLocaleString() }} {{ assessmentResult.currency || 'USD' }}
              </span>
              <span v-else class="text-muted">Not specified</span>
            </div>
          </div>
        </div>

        <div class="metric-card">
          <MapPin :size="16" class="metric-icon" />
          <div>
            <div class="metric-k">Location & Model</div>
            <div class="metric-v">
              {{ assessmentResult.location || 'Location Unspecified' }}
              <span v-if="assessmentResult.work_model">({{ assessmentResult.work_model }})</span>
            </div>
          </div>
        </div>

        <div class="metric-card">
          <ShieldCheck :size="16" class="metric-icon" />
          <div>
            <div class="metric-k">AI Recommendation</div>
            <div class="metric-v">
              <span class="badge" :class="assessmentResult.recommendation === 'APPLY_STRONGLY' ? 'badge-offer' : 'badge-applied'">
                {{ assessmentResult.recommendation }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Skills Matrix -->
      <div class="skills-matrix">
        <div class="matrix-col">
          <div class="matrix-title text-success">
            <Check :size="15" />
            <span>Matching Strengths & Skills ({{ assessmentResult.matching_skills?.length || 0 }})</span>
          </div>
          <div class="tags-container">
            <span v-for="s in assessmentResult.matching_skills" :key="s" class="tag-chip tag-match">
              {{ s }}
            </span>
          </div>
        </div>

        <div class="matrix-col">
          <div class="matrix-title text-danger">
            <AlertTriangle :size="15" />
            <span>Missing Qualification Keywords ({{ assessmentResult.missing_skills?.length || 0 }})</span>
          </div>
          <div class="tags-container">
            <span v-for="m in assessmentResult.missing_skills" :key="m" class="tag-chip tag-miss">
              {{ m }}
            </span>
          </div>
        </div>
      </div>

      <!-- Pros & Cons -->
      <div class="pros-cons-grid">
        <div v-if="assessmentResult.pros?.length" class="pro-con-box">
          <div class="pro-con-title">Key Advantages / Pros</div>
          <ul class="pro-con-list">
            <li v-for="(p, idx) in assessmentResult.pros" :key="idx">{{ p }}</li>
          </ul>
        </div>

        <div v-if="assessmentResult.cons?.length" class="pro-con-box">
          <div class="pro-con-title">Potential Caveats / Cons</div>
          <ul class="pro-con-list">
            <li v-for="(c, idx) in assessmentResult.cons" :key="idx">{{ c }}</li>
          </ul>
        </div>
      </div>

      <!-- Narrative Evaluation -->
      <div class="evaluation-summary">
        <div class="eval-title">Evaluation Summary</div>
        <p class="eval-text">{{ assessmentResult.summary }}</p>
      </div>

      <!-- Confirmation Execution Bar -->
      <div class="confirmation-bar">
        <div class="confirm-text">
          Confirm and save this lead into your application pipeline:
        </div>
        <div class="confirm-buttons">
          <button
            class="btn btn-secondary"
            :disabled="isSaving"
            @click="confirmAndProcess('ASSESSMENT')"
          >
            <Loader2 v-if="isSaving" class="animate-spin" :size="15" />
            <span>Save to AI Assessment</span>
          </button>

          <button
            class="btn btn-primary"
            :disabled="isSaving"
            @click="confirmAndProcess('APPLIED')"
          >
            <Loader2 v-if="isSaving" class="animate-spin" :size="15" />
            <span>Confirm & Mark as Applied</span>
            <ArrowRight :size="15" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.intake-header {
  text-align: center;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background-color: var(--status-assessment-bg);
  color: var(--status-assessment-text);
  border: 1px solid var(--status-assessment-border);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 10px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 650px;
  margin-top: 4px;
  line-height: 1.5;
}

.advisory-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin-bottom: 14px;
}

.extension-config-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-sm);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.endpoints-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

@media (max-width: 768px) {
  .endpoints-grid {
    grid-template-columns: 1fr;
  }
}

.endpoint-item {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.endpoint-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.endpoint-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.endpoint-input-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  padding: 4px 8px;
}

.endpoint-val {
  font-size: 11px;
  color: var(--primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-xs {
  padding: 3px 8px;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.intake-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-md);
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input, .form-textarea {
  width: 100%;
}

.intake-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.btn-assess {
  padding: 10px 20px;
  font-weight: 600;
}

/* ASSESSMENT DASHBOARD */
.assessment-dashboard {
  margin-top: 32px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 28px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.company-icon-box {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background-color: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  border: 1px solid var(--border-subtle);
}

.company-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
}

.role-title {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.scores-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-badge-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 14px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.score-ai-box {
  background-color: var(--status-offer-bg);
  border-color: var(--status-offer-border);
}

.score-num {
  font-size: 16px;
  font-weight: 800;
  color: var(--text-main);
}

.score-ai-box .score-num {
  color: var(--status-offer-text);
}

.score-lbl {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
  margin-top: 2px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
}

.metric-icon {
  color: var(--primary);
}

.metric-k {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
}

.metric-v {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.skills-matrix {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 18px;
}

.matrix-col {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
}

.matrix-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 12px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
}

.tag-match {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.tag-miss {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.pros-cons-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.pro-con-box {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
}

.pro-con-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.pro-con-list {
  padding-left: 18px;
  font-size: 13px;
  color: var(--text-main);
  line-height: 1.6;
}

.evaluation-summary {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
}

.eval-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.eval-text {
  font-size: 13px;
  color: var(--text-main);
  line-height: 1.5;
}

.confirmation-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.confirm-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.confirm-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
