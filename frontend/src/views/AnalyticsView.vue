<script setup>
import { ref, onMounted, computed } from 'vue'
import { AnalyticsAPI } from '../api/endpoints'
import {
  BarChart3,
  RefreshCw,
  TrendingUp,
  Target,
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  Building,
  Monitor,
  CalendarDays
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
</script>

<template>
  <div class="analytics-container">
    <!-- Header & Filters -->
    <div class="header-section">
      <div class="header-title">
        <BarChart3 class="text-primary" :size="24" />
        <h1>Market Intelligence & Analytics</h1>
      </div>

      <div class="filters">
        <div class="filter-group">
          <CalendarDays :size="16" class="text-secondary" />
          <select v-model="filters.days" @change="fetchAnalytics" class="filter-select">
            <option v-for="opt in dateOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="filter-group">
          <Target :size="16" class="text-secondary" />
          <select v-model="filters.top_n" @change="fetchAnalytics" class="filter-select">
            <option :value="10">Top 10</option>
            <option :value="15">Top 15</option>
            <option :value="20">Top 20</option>
          </select>
        </div>

        <div class="filter-group">
          <Monitor :size="16" class="text-secondary" />
          <select v-model="filters.work_model" @change="fetchAnalytics" class="filter-select">
            <option v-for="opt in workModelOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <button class="btn btn-secondary btn-icon" @click="fetchAnalytics" :disabled="loading" title="Refresh Data">
          <RefreshCw :size="16" :class="{ 'spin': loading }" />
        </button>
      </div>
    </div>

    <div v-if="loading && !analyticsData" class="loading-state">
      <RefreshCw class="spin text-primary" :size="32" />
      <p>Crunching pipeline data...</p>
    </div>

    <div v-else-if="analyticsData" class="dashboard-grid">

      <!-- KPI Cards -->
      <div class="kpi-row">
        <div class="card kpi-card">
          <div class="kpi-icon"><Briefcase :size="20" /></div>
          <div class="kpi-content">
            <div class="kpi-label">Total Tracked</div>
            <div class="kpi-value">{{ analyticsData.total_applications }}</div>
          </div>
        </div>

        <div class="card kpi-card">
          <div class="kpi-icon bg-blue"><TrendingUp :size="20" /></div>
          <div class="kpi-content">
            <div class="kpi-label">Active Pipeline</div>
            <div class="kpi-value">{{ analyticsData.active_pipeline_count }}</div>
          </div>
        </div>

        <div class="card kpi-card">
          <div class="kpi-icon bg-green"><Target :size="20" /></div>
          <div class="kpi-content">
            <div class="kpi-label">Interview Rate</div>
            <div class="kpi-value">{{ analyticsData.interview_rate.toFixed(1) }}%</div>
          </div>
        </div>

        <div class="card kpi-card">
          <div class="kpi-icon bg-orange"><CheckCircle2 :size="20" /></div>
          <div class="kpi-content">
            <div class="kpi-label">Avg Fit Score</div>
            <div class="kpi-value">{{ analyticsData.average_fit_score ? analyticsData.average_fit_score.toFixed(0) + '%' : 'N/A' }}</div>
          </div>
        </div>
      </div>

      <!-- Main Layout Grid -->
      <div class="main-content-grid">

        <!-- Column 1: Market Intelligence -->
        <div class="col-left">
          <div class="card">
            <div class="card-header">
              <h3>Top In-Demand Market Skills</h3>
              <p class="subtitle">Based on your tracked job descriptions</p>
            </div>

            <div v-if="analyticsData.top_in_demand_skills.length === 0" class="empty-state">
              No skill data extracted yet.
            </div>
            <div v-else class="skill-list">
              <div v-for="skill in analyticsData.top_in_demand_skills" :key="skill.skill" class="skill-item">
                <div class="skill-info">
                  <span class="skill-name">{{ skill.skill }}</span>
                  <div class="badges">
                    <span v-if="skill.is_in_candidate_cv" class="badge badge-green" title="You have this skill!">
                      <CheckCircle2 :size="12" /> Has Skill
                    </span>
                    <span v-else class="badge badge-gray">Missing</span>
                  </div>
                </div>
                <div class="skill-bar-container">
                  <div class="skill-bar" :style="{ width: `${(skill.count / maxSkillCount) * 100}%` }"></div>
                  <span class="skill-count">{{ skill.count }} jobs</span>
                </div>
                <div class="salary-hint" v-if="skill.avg_salary_min">
                  ~${{ (skill.avg_salary_min/1000).toFixed(0) }}k
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Column 2: Personal Gaps & Funnel -->
        <div class="col-right">

          <!-- Funnel -->
          <div class="card">
            <div class="card-header">
              <h3>Conversion Funnel</h3>
            </div>
            <div class="funnel-chart">
              <div v-for="(stage, idx) in analyticsData.pipeline_funnel" :key="stage.stage" class="funnel-stage">
                <div class="stage-label">{{ stage.stage }} ({{ stage.count }})</div>
                <div class="stage-bar-wrapper">
                  <div class="stage-bar" :style="{ width: `${stage.conversion_rate}%`, opacity: 1 - (idx * 0.2) }"></div>
                </div>
                <div class="stage-rate" v-if="idx > 0 && stage.dropoff_rate > 0">
                  <AlertTriangle :size="12" class="text-orange" />
                  {{ stage.dropoff_rate.toFixed(1) }}% drop
                </div>
              </div>
            </div>
          </div>

          <!-- Skill Gaps -->
          <div class="card mt-24">
            <div class="card-header">
              <h3>Personal Skill Gap Matrix</h3>
              <p class="subtitle">High priority skills missing from your profile</p>
            </div>

            <div v-if="analyticsData.priority_skill_gaps.length === 0" class="empty-state">
              No significant skill gaps identified!
            </div>
            <div v-else class="gap-list">
              <div v-for="gap in analyticsData.priority_skill_gaps" :key="gap.skill" class="gap-item">
                <div class="gap-header">
                  <span class="gap-name">{{ gap.skill }}</span>
                  <span class="gap-score" title="Priority Score">
                    Priority: {{ gap.priority_score.toFixed(1) }}
                  </span>
                </div>
                <div class="gap-bar-container">
                  <div class="gap-bar" :style="{ width: `${(gap.priority_score / maxGapScore) * 100}%` }"></div>
                </div>
                <div class="gap-meta">
                  <span>Missing in {{ gap.missing_frequency }} jobs</span>
                  <span v-if="gap.sample_companies.length" class="gap-companies">
                    <Building :size="12" /> {{ gap.sample_companies.join(', ') }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Salary Insights Card -->
          <div class="card mt-24">
            <div class="card-header">
              <h3>Salary Insights (Top Skills)</h3>
            </div>
            <div v-if="analyticsData.salary_insights.length === 0" class="empty-state">
              No salary data available.
            </div>
            <div v-else class="salary-list">
              <div v-for="item in analyticsData.salary_insights.slice(0, 5)" :key="item.skill" class="salary-item">
                <span class="salary-skill">{{ item.skill }}</span>
                <span class="salary-range">
                  {{ item.avg_min ? '$' + (item.avg_min / 1000).toFixed(0) + 'k' : 'N/A' }}
                  -
                  {{ item.avg_max ? '$' + (item.avg_max / 1000).toFixed(0) + 'k' : 'N/A' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Work Model Distribution -->
          <div class="card mt-24">
             <div class="card-header">
              <h3>Work Model Distribution</h3>
            </div>
            <div class="work-model-bar">
              <div class="wm-segment remote" :style="{ flex: analyticsData.work_model_distribution.remote_count || 0.01 }" title="Remote">
                {{ analyticsData.work_model_distribution.remote_count }}
              </div>
              <div class="wm-segment hybrid" :style="{ flex: analyticsData.work_model_distribution.hybrid_count || 0.01 }" title="Hybrid">
                {{ analyticsData.work_model_distribution.hybrid_count }}
              </div>
              <div class="wm-segment onsite" :style="{ flex: analyticsData.work_model_distribution.onsite_count || 0.01 }" title="Onsite">
                {{ analyticsData.work_model_distribution.onsite_count }}
              </div>
            </div>
            <div class="wm-legend">
              <span class="wm-dot remote"></span> Remote
              <span class="wm-dot hybrid"></span> Hybrid
              <span class="wm-dot onsite"></span> Onsite
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analytics-container {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: var(--text-main);
}

.filters {
  display: flex;
  gap: 16px;
  align-items: center;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 6px 12px;
  border-radius: var(--radius-md);
}

.filter-select {
  background: transparent;
  border: none;
  color: var(--text-main);
  font-size: 14px;
  outline: none;
  cursor: pointer;
}

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

.dashboard-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
}

.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--bg-surface-hover);
  color: var(--text-main);
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-icon.bg-blue { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.kpi-icon.bg-green { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
.kpi-icon.bg-orange { background: rgba(249, 115, 22, 0.1); color: #f97316; }

.kpi-content {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-main);
}

.main-content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 1024px) {
  .main-content-grid {
    grid-template-columns: 1fr;
  }
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.card-header {
  margin-bottom: 20px;
}

.card-header h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
}

.subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.mt-24 {
  margin-top: 24px;
}

/* Skill List */
.skill-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skill-item {
  display: grid;
  grid-template-columns: 200px 1fr 60px;
  align-items: center;
  gap: 16px;
}

.skill-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.skill-name {
  font-weight: 500;
  font-size: 14px;
}

.badges {
  display: flex;
  gap: 6px;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.badge-green {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.badge-gray {
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
}

.skill-bar-container {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.skill-bar {
  height: 8px;
  background: var(--primary);
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.skill-count {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 45px;
}

.salary-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  text-align: right;
}

/* Gap List */
.gap-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.gap-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gap-header {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.gap-name {
  font-weight: 600;
}

.gap-score {
  font-size: 12px;
  color: #f97316;
  font-weight: 600;
}

.gap-bar-container {
  width: 100%;
  height: 6px;
  background: var(--bg-surface-hover);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.gap-bar {
  height: 100%;
  background: #f97316; /* Orange for warning/gap */
  border-radius: var(--radius-full);
}

.gap-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
}

.gap-companies {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

/* Funnel */
.funnel-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.funnel-stage {
  display: grid;
  grid-template-columns: 120px 1fr 80px;
  align-items: center;
  gap: 12px;
}

.stage-label {
  font-size: 13px;
  font-weight: 500;
}

.stage-bar-wrapper {
  width: 100%;
  height: 24px;
  background: var(--bg-surface-hover);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.stage-bar {
  height: 100%;
  background: var(--primary);
  border-radius: var(--radius-sm);
  transition: width 0.5s ease;
}

.stage-rate {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.text-orange {
  color: #f97316;
}

/* Work Model */
.work-model-bar {
  display: flex;
  height: 24px;
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-bottom: 12px;
}

.wm-segment {
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 600;
  transition: flex 0.3s ease;
}

.wm-segment.remote { background: #3b82f6; }
.wm-segment.hybrid { background: #a855f7; }
.wm-segment.onsite { background: #64748b; }

.wm-legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
}

.wm-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.wm-dot.remote { background: #3b82f6; }
.wm-dot.hybrid { background: #a855f7; }
.wm-dot.onsite { background: #64748b; }

.empty-state {
  padding: 32px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 14px;
}

/* Salary List */
.salary-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.salary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-surface-hover);
  border-radius: var(--radius-sm);
  font-size: 14px;
}

.salary-skill {
  font-weight: 500;
}

.salary-range {
  color: var(--text-secondary);
}
</style>
