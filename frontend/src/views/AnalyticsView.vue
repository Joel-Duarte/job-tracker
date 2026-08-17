<script setup>
import { ref, onMounted, computed } from 'vue'
import { AnalyticsAPI } from '../api/endpoints'
import {
  BarChart3,
  RefreshCw,
  TrendingUp,
  Target,
  Briefcase,
  CheckCircle2,
  Building2,
  Monitor,
  CalendarDays,
  ArrowDownRight,
  ChevronDown
} from 'lucide-vue-next'
import { useUIStore } from '../stores/uiStore'

const uiStore = useUIStore()

const loading = ref(true)
const analyticsData = ref(null)

const filters = ref({
  days: null, // null for all time
  work_model: 'all',
  top_n: 15
})

const dateOptions = [
  { label: 'All Time', value: null },
  { label: 'Last 90 Days', value: 90 },
  { label: 'Last 30 Days', value: 30 }
]

const workModelOptions = [
  { label: 'All Models', value: 'all' },
  { label: 'Remote', value: 'remote' },
  { label: 'Hybrid', value: 'hybrid' },
  { label: 'Onsite', value: 'onsite' }
]

async function fetchAnalytics() {
  loading.value = true
  try {
    const params = { top_n: filters.value.top_n }
    if (filters.value.days) params.days = filters.value.days
    if (filters.value.work_model !== 'all') params.work_model = filters.value.work_model

    const res = await AnalyticsAPI.getOverview(params)
    analyticsData.value = res.data
  } catch (err) {
    uiStore.addToast('Failed to load analytics', 'error')
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAnalytics()
})

const maxSkillCount = computed(() => {
  if (!analyticsData.value?.top_in_demand_skills.length) return 1
  return Math.max(...analyticsData.value.top_in_demand_skills.map(s => s.count))
})

const maxGapScore = computed(() => {
  if (!analyticsData.value?.priority_skill_gaps.length) return 1
  return Math.max(...analyticsData.value.priority_skill_gaps.map(g => g.priority_score))
})

const totalWorkModelCount = computed(() => {
  if (!analyticsData.value?.work_model_distribution) return 0;
  const dist = analyticsData.value.work_model_distribution;
  return dist.remote_count + dist.hybrid_count + dist.onsite_count + dist.unknown_count;
});

function formatSalary(value) {
  if (!value) return '';
  return `$${(value / 1000).toFixed(0)}k`;
}

function getFunnelStageColor(stage) {
    if(stage === 'Applied') return 'var(--status-applied-bg)';
    if(stage === 'Assessment') return 'var(--status-assessment-bg)';
    if(stage === 'Interview') return 'var(--status-interview-bg)';
    if(stage === 'Offer') return 'var(--status-offer-bg)';
    return 'var(--primary)';
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-text">
        <h1 class="page-title">
          <BarChart3 class="text-primary title-icon" :size="24" />
          Market Intelligence & Analytics
        </h1>
        <p class="page-subtitle">
          Aggregate skill demand, compensation benchmarks, and pipeline conversion trends across your tracked job applications.
        </p>
      </div>

      <div class="header-filters">
        <div class="filter-pill">
          <CalendarDays :size="14" class="filter-icon" />
          <div class="select-wrapper">
             <select v-model="filters.days" @change="fetchAnalytics">
                <option v-for="opt in dateOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <ChevronDown :size="14" class="select-chevron" />
          </div>
        </div>

        <div class="filter-pill">
          <Monitor :size="14" class="filter-icon" />
          <div class="select-wrapper">
             <select v-model="filters.work_model" @change="fetchAnalytics">
                <option v-for="opt in workModelOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <ChevronDown :size="14" class="select-chevron" />
          </div>
        </div>

        <div class="filter-pill">
          <Target :size="14" class="filter-icon" />
          <div class="select-wrapper">
             <select v-model="filters.top_n" @change="fetchAnalytics">
                <option :value="10">Top 10</option>
                <option :value="15">Top 15</option>
                <option :value="20">Top 20</option>
              </select>
              <ChevronDown :size="14" class="select-chevron" />
          </div>
        </div>

        <button class="btn btn-secondary btn-icon" @click="fetchAnalytics" :disabled="loading" title="Refresh Data">
          <RefreshCw :size="16" :class="{ 'spin': loading }" />
        </button>
      </div>
    </div>

    <div class="analytics-content">
      <div v-if="loading && !analyticsData" class="loading-state">
        <RefreshCw class="spin text-primary" :size="32" />
        <p>Crunching pipeline data...</p>
      </div>

      <div v-else-if="analyticsData" class="dashboard-layout">

        <!-- Compact 5-Card KPI Row -->
        <div class="kpi-banner">
          <div class="kpi-card">
            <div class="kpi-icon-badge"><Briefcase :size="16" /></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData.total_applications }}</div>
              <div class="kpi-label">Total Tracked</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon-badge badge-blue"><TrendingUp :size="16" /></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData.active_pipeline_count }}</div>
              <div class="kpi-label">Active Pipeline</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon-badge badge-green"><Target :size="16" /></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData.interview_rate.toFixed(1) }}%</div>
              <div class="kpi-label">Interview Rate</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon-badge badge-orange"><CheckCircle2 :size="16" /></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData.average_fit_score ? analyticsData.average_fit_score.toFixed(0) + '%' : 'N/A' }}</div>
              <div class="kpi-label">Avg Fit Score</div>
            </div>
          </div>

          <div class="kpi-card wm-kpi-card">
             <div class="wm-kpi-header">
                <span class="kpi-label">Work Model Split</span>
                <span class="wm-total">{{ totalWorkModelCount }} jobs</span>
             </div>
             <div class="wm-mini-meter">
                <div class="wm-segment remote" :style="{ flex: analyticsData.work_model_distribution.remote_count || 0.01 }" :title="`Remote: ${analyticsData.work_model_distribution.remote_count}`"></div>
                <div class="wm-segment hybrid" :style="{ flex: analyticsData.work_model_distribution.hybrid_count || 0.01 }" :title="`Hybrid: ${analyticsData.work_model_distribution.hybrid_count}`"></div>
                <div class="wm-segment onsite" :style="{ flex: analyticsData.work_model_distribution.onsite_count || 0.01 }" :title="`Onsite: ${analyticsData.work_model_distribution.onsite_count}`"></div>
             </div>
             <div class="wm-mini-legend">
                <span class="wm-legend-item"><span class="wm-dot remote"></span>Rem</span>
                <span class="wm-legend-item"><span class="wm-dot hybrid"></span>Hyb</span>
                <span class="wm-legend-item"><span class="wm-dot onsite"></span>Ons</span>
             </div>
          </div>
        </div>

        <!-- 2x2 Quadrant Grid -->
        <div class="quadrant-grid">

          <!-- Quadrant 1: In-Demand Skills -->
          <div class="card quadrant">
            <div class="card-header">
              <h3>Top In-Demand Market Skills</h3>
              <p class="subtitle">Based on required skills across your pipeline</p>
            </div>

            <div v-if="analyticsData.top_in_demand_skills.length === 0" class="empty-state">
              No skill data extracted yet.
            </div>
            <div v-else class="skill-list">
              <div v-for="skill in analyticsData.top_in_demand_skills" :key="skill.skill" class="skill-item">
                <div class="skill-main">
                  <div class="skill-name-row">
                    <span class="skill-name">{{ skill.skill }}</span>
                    <span v-if="skill.is_in_candidate_cv" class="pill-badge has-skill">
                      <CheckCircle2 :size="12" /> Has Skill
                    </span>
                    <span v-else class="pill-badge missing-skill">Missing</span>
                  </div>
                  <div class="skill-track">
                    <div class="skill-fill" :style="{ width: `${(skill.count / maxSkillCount) * 100}%` }"></div>
                  </div>
                </div>
                <div class="skill-meta">
                  <span class="skill-count-chip">{{ skill.count }} jobs</span>
                  <span class="skill-salary-tag" v-if="skill.avg_salary_min || skill.avg_salary_max">
                    ~{{ formatSalary((skill.avg_salary_min || skill.avg_salary_max)) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Quadrant 2: Conversion Funnel -->
          <div class="card quadrant">
            <div class="card-header">
              <h3>Pipeline Conversion Funnel</h3>
              <p class="subtitle">Progression and drop-off rates across stages</p>
            </div>
            <div class="funnel-chart">
              <div v-for="(stage, idx) in analyticsData.pipeline_funnel" :key="stage.stage" class="funnel-stage-card" :style="{ '--stage-bg': getFunnelStageColor(stage.stage) }">
                <div class="stage-info">
                  <span class="stage-name">{{ stage.stage }}</span>
                  <span class="stage-count">{{ stage.count }} applications</span>
                </div>
                <div class="stage-metrics">
                   <div class="conversion-pill" title="Conversion Rate">
                     {{ stage.conversion_rate.toFixed(1) }}%
                   </div>
                   <div v-if="idx > 0 && stage.dropoff_rate > 0" class="dropoff-pill">
                     <ArrowDownRight :size="12" />
                     {{ stage.dropoff_rate.toFixed(1) }}% drop
                   </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Quadrant 3: Salary Insights -->
          <div class="card quadrant">
            <div class="card-header">
              <h3>Compensation Benchmarks</h3>
              <p class="subtitle">Average salary ranges by top technologies</p>
            </div>
            <div v-if="analyticsData.salary_insights.length === 0" class="empty-state">
              No salary data available.
            </div>
            <div v-else class="salary-list">
              <div v-for="item in analyticsData.salary_insights.slice(0, 8)" :key="item.skill" class="salary-row">
                <span class="salary-skill-name">{{ item.skill }}</span>
                <div class="salary-spectrum">
                   <div class="spectrum-bar">
                      <div class="spectrum-fill" style="left: 10%; right: 10%;"></div>
                   </div>
                </div>
                <span class="salary-range-text">
                  {{ formatSalary(item.avg_min) || 'N/A' }}
                  <span class="range-sep">-</span>
                  {{ formatSalary(item.avg_max) || 'N/A' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Quadrant 4: Skill Gap Matrix -->
          <div class="card quadrant">
            <div class="card-header">
              <h3>Personal Skill Gap Matrix</h3>
              <p class="subtitle">High priority missing skills to learn next</p>
            </div>

            <div v-if="analyticsData.priority_skill_gaps.length === 0" class="empty-state">
              No significant skill gaps identified!
            </div>
            <div v-else class="gap-list">
              <div v-for="gap in analyticsData.priority_skill_gaps" :key="gap.skill" class="gap-card">
                <div class="gap-top">
                  <span class="gap-skill-name">{{ gap.skill }}</span>
                  <span class="gap-priority-pill">
                    Priority: {{ gap.priority_score.toFixed(1) }}
                  </span>
                </div>
                <div class="gap-track">
                  <div class="gap-fill" :style="{ width: `${(gap.priority_score / maxGapScore) * 100}%` }"></div>
                </div>
                <div class="gap-bottom">
                  <span class="gap-freq">Missing in {{ gap.missing_frequency }} active jobs</span>
                  <div v-if="gap.sample_companies.length" class="gap-companies-tags">
                    <span v-for="comp in gap.sample_companies" :key="comp" class="company-tag">
                      <Building2 :size="10" /> {{ comp }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Page Layout */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-app);
}

/* Header matched to StagingView / SettingsView pattern */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 24px 22px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 16px;
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: var(--text-main);
  letter-spacing: -0.02em;
}

.title-icon {
  color: var(--primary);
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

/* Theme-Aware Filter Bar */
.header-filters {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  border-radius: var(--radius-full);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.filter-pill:hover {
  border-color: var(--border-subtle);
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.1);
}

.filter-icon {
  color: var(--text-secondary);
}

.select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.filter-pill select {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--text-main);
  font-size: 13px;
  font-weight: 500;
  padding-right: 20px;
  cursor: pointer;
  outline: none;
}

.filter-pill select option {
  background-color: var(--bg-card);
  color: var(--text-main);
}

.select-chevron {
  position: absolute;
  right: 0;
  pointer-events: none;
  color: var(--text-secondary);
}


/* Main Content Area */
.analytics-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.dashboard-layout {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px;
  color: var(--text-secondary);
  gap: 16px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

/* Compact 5-Card KPI Banner */
.kpi-banner {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .kpi-banner {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 768px) {
  .kpi-banner {
    grid-template-columns: repeat(2, 1fr);
  }
}

.kpi-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: var(--shadow-sm);
}

.kpi-icon-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
}

.kpi-icon-badge.badge-blue { background-color: rgba(59, 130, 246, 0.1); color: var(--primary); }
.kpi-icon-badge.badge-green { background-color: rgba(34, 197, 94, 0.1); color: var(--status-offer-text); }
.kpi-icon-badge.badge-orange { background-color: rgba(249, 115, 22, 0.1); color: var(--text-warning); }

.kpi-info {
  display: flex;
  flex-direction: column;
}

.kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.kpi-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Work Model Mini-Meter KPI */
.wm-kpi-card {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  padding: 12px 16px;
}

.wm-kpi-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.wm-total {
  font-size: 11px;
  color: var(--text-tertiary);
}

.wm-mini-meter {
  display: flex;
  height: 8px;
  border-radius: var(--radius-full);
  overflow: hidden;
  background-color: var(--bg-surface-hover);
}

.wm-segment { transition: flex 0.3s ease; }
.wm-segment.remote { background-color: var(--primary); }
.wm-segment.hybrid { background-color: var(--status-interview-text); }
.wm-segment.onsite { background-color: var(--text-secondary); }

.wm-mini-legend {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-secondary);
}
.wm-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.wm-dot {
  width: 6px; height: 6px; border-radius: 50%;
}
.wm-dot.remote { background-color: var(--primary); }
.wm-dot.hybrid { background-color: var(--status-interview-text); }
.wm-dot.onsite { background-color: var(--text-secondary); }


/* 2x2 Quadrant Grid */
.quadrant-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 1024px) {
  .quadrant-grid {
    grid-template-columns: 1fr;
  }
}

.card.quadrant {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
}

.card-header {
  margin-bottom: 20px;
}

.card-header h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.empty-state {
  padding: 32px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 14px;
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-color);
}

/* Quadrant 1: In-Demand Skills */
.skill-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skill-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.skill-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skill-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.skill-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-main);
}

.pill-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.pill-badge.has-skill {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.pill-badge.missing-skill {
  background-color: var(--bg-surface-hover);
  color: var(--text-secondary);
}

.skill-track {
  width: 100%;
  height: 6px;
  background-color: var(--bg-surface-hover);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.skill-fill {
  height: 100%;
  background-color: var(--primary);
  border-radius: var(--radius-full);
  transition: width 0.5s ease-out;
}

.skill-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  min-width: 60px;
}

.skill-count-chip {
  font-size: 11px;
  font-weight: 600;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
}

.skill-salary-tag {
  font-size: 11px;
  color: var(--text-tertiary);
}

/* Quadrant 2: Conversion Funnel */
.funnel-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.funnel-stage-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--stage-bg) 0%, var(--bg-card) 100%);
  border: 1px solid var(--border-color);
  position: relative;
  overflow: hidden;
}

.funnel-stage-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background-color: var(--stage-bg);
}

.stage-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 8px;
}

.stage-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-main);
}

.stage-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.stage-metrics {
  display: flex;
  align-items: center;
  gap: 8px;
}

.conversion-pill {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
  background-color: var(--bg-surface);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}

.dropoff-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--status-rejected-text);
  background-color: var(--status-rejected-bg);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  border: 1px solid var(--status-rejected-border);
}


/* Quadrant 3: Salary Insights */
.salary-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.salary-row {
  display: grid;
  grid-template-columns: 120px 1fr 120px;
  align-items: center;
  gap: 16px;
}

.salary-skill-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.salary-spectrum {
  width: 100%;
  height: 8px;
  background-color: var(--bg-surface-hover);
  border-radius: var(--radius-full);
  position: relative;
}

.spectrum-fill {
  position: absolute;
  top: 0; bottom: 0;
  background-color: var(--primary);
  opacity: 0.3;
  border-radius: var(--radius-full);
}
.spectrum-fill::before, .spectrum-fill::after {
    content: '';
    position: absolute;
    top: -2px; width: 4px; bottom: -2px;
    background-color: var(--primary);
    border-radius: 2px;
}
.spectrum-fill::before { left: 0; }
.spectrum-fill::after { right: 0; }


.salary-range-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  text-align: right;
}
.range-sep {
  color: var(--text-tertiary);
  margin: 0 4px;
}


/* Quadrant 4: Skill Gap Matrix */
.gap-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.gap-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.gap-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.gap-skill-name {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 14px;
  color: var(--text-main);
}

.gap-priority-pill {
  font-size: 11px;
  font-weight: 600;
  background-color: var(--bg-card);
  color: var(--text-warning);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  border: 1px solid var(--status-interview-border);
}

.gap-track {
  width: 100%;
  height: 4px;
  background-color: var(--bg-surface-hover);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.gap-fill {
  height: 100%;
  background-color: var(--text-warning);
  border-radius: var(--radius-full);
}

.gap-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.gap-freq {
  color: var(--text-secondary);
}

.gap-companies-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.company-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  background-color: var(--bg-surface-hover);
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

</style>
