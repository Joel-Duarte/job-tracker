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
  ChevronDown,
  Globe,
  MapPin,
  Flame,
  DollarSign,
  Layers,
  Sparkles,
} from 'lucide-vue-next'
import { useUIStore } from '../stores/uiStore'

const uiStore = useUIStore()

const loading = ref(true)
const analyticsData = ref(null)

const filters = ref({
  days: null, // null for all time
  work_model: 'all',
})

const dateOptions = [
  { label: 'All Time', value: null },
  { label: 'Last 90 Days', value: 90 },
  { label: 'Last 30 Days', value: 30 },
]

function toggleWorkModel(model) {
  if (filters.value.work_model === model) {
    filters.value.work_model = 'all'
  } else {
    filters.value.work_model = model
  }
  fetchAnalytics()
}

async function fetchAnalytics() {
  loading.value = true
  try {
    const params = {}
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
  if (!analyticsData.value?.top_in_demand_skills?.length) return 1
  return Math.max(...analyticsData.value.top_in_demand_skills.map((s) => s.count))
})

const maxGapScore = computed(() => {
  if (!analyticsData.value?.priority_skill_gaps?.length) return 1
  return Math.max(...analyticsData.value.priority_skill_gaps.map((g) => g.priority_score))
})

const salaryBounds = computed(() => {
  if (!analyticsData.value?.salary_insights?.length) {
    return { min: 100000, max: 300000, span: 200000 }
  }
  let globalMin = Infinity
  let globalMax = -Infinity
  for (const item of analyticsData.value.salary_insights) {
    if (item.avg_min && item.avg_min > 0) globalMin = Math.min(globalMin, item.avg_min)
    if (item.avg_max && item.avg_max > 0) globalMax = Math.max(globalMax, item.avg_max)
  }
  if (globalMin === Infinity) globalMin = 100000
  if (globalMax === -Infinity) globalMax = 300000
  if (globalMin === globalMax) globalMax = globalMin + 50000
  return {
    min: globalMin,
    max: globalMax,
    span: globalMax - globalMin || 1,
  }
})

function getSalarySpectrumStyle(avgMin, avgMax) {
  const { min, span } = salaryBounds.value
  const low = avgMin ? Math.max(0, ((avgMin - min) / span) * 100) : 0
  const high = avgMax ? Math.min(100, ((avgMax - min) / span) * 100) : 100
  const width = Math.max(6, high - low)
  return {
    left: `${low}%`,
    width: `${width}%`,
  }
}

const workModelStats = computed(() => {
  if (!analyticsData.value?.work_model_distribution) {
    return {
      total: 0,
      remotePct: 0,
      hybridPct: 0,
      onsitePct: 0,
      unknownPct: 0,
      remoteCount: 0,
      hybridCount: 0,
      onsiteCount: 0,
      unknownCount: 0,
    }
  }
  const dist = analyticsData.value.work_model_distribution
  const total = dist.remote_count + dist.hybrid_count + dist.onsite_count + dist.unknown_count
  if (total === 0) {
    return {
      total: 0,
      remotePct: 0,
      hybridPct: 0,
      onsitePct: 0,
      unknownPct: 0,
      remoteCount: 0,
      hybridCount: 0,
      onsiteCount: 0,
      unknownCount: 0,
    }
  }
  return {
    total,
    remoteCount: dist.remote_count,
    hybridCount: dist.hybrid_count,
    onsiteCount: dist.onsite_count,
    unknownCount: dist.unknown_count,
    remotePct: Math.round((dist.remote_count / total) * 100),
    hybridPct: Math.round((dist.hybrid_count / total) * 100),
    onsitePct: Math.round((dist.onsite_count / total) * 100),
    unknownPct: Math.round((dist.unknown_count / total) * 100),
  }
})

function formatSalary(value) {
  if (!value || isNaN(value)) return ''
  return `$${(value / 1000).toFixed(0)}k`
}

// Sankey Diagram Flow Calculations
const sankeyData = computed(() => {
  if (!analyticsData.value?.pipeline_funnel?.length) return null

  const funnel = analyticsData.value.pipeline_funnel
  const total = funnel[0]?.count || 1

  const isDark = uiStore.theme === 'midnight'
  const stages = [
    { key: 'Applied', label: 'Applied', color: isDark ? '#38bdf8' : '#2563eb', x: 12, count: funnel[0]?.count || 0 },
    { key: 'Assessment', label: 'Assessment', color: isDark ? '#fbbf24' : '#d97706', x: 152, count: funnel[1]?.count || 0 },
    { key: 'Interview', label: 'Interview', color: isDark ? '#c084fc' : '#7c3aed', x: 292, count: funnel[2]?.count || 0 },
    { key: 'Offer', label: 'Offer', color: isDark ? '#34d399' : '#059669', x: 432, count: funnel[3]?.count || 0 },
  ]

  const nodeWidth = 78
  const nodeHeight = 44
  const nodeY = 16

  const nodes = stages.map((s) => ({
    ...s,
    w: nodeWidth,
    h: nodeHeight,
    y: nodeY,
    rate: total > 0 ? ((s.count / total) * 100).toFixed(0) : 0,
  }))

  const flows = []
  const dropoffs = []

  for (let i = 0; i < stages.length - 1; i++) {
    const src = nodes[i]
    const tgt = nodes[i + 1]

    const advancedCount = tgt.count
    const droppedCount = Math.max(0, src.count - tgt.count)

    // Progression flow ribbon
    const maxH = 26
    const ribbonH = src.count > 0 ? Math.max(4, (advancedCount / src.count) * maxH) : 3

    const x1 = src.x + src.w
    const y1 = src.y + src.h / 2
    const x2 = tgt.x
    const y2 = tgt.y + tgt.h / 2
    const dx = (x2 - x1) * 0.45

    const pathD = `M ${x1} ${y1 - ribbonH / 2}
                   C ${x1 + dx} ${y1 - ribbonH / 2}, ${x2 - dx} ${y2 - ribbonH / 2}, ${x2} ${y2 - ribbonH / 2}
                   L ${x2} ${y2 + ribbonH / 2}
                   C ${x2 - dx} ${y2 + ribbonH / 2}, ${x1 + dx} ${y1 + ribbonH / 2}, ${x1} ${y1 + ribbonH / 2} Z`

    flows.push({
      from: src.label,
      to: tgt.label,
      count: advancedCount,
      srcColor: src.color,
      tgtColor: tgt.color,
      pathD,
      gradientId: `sankey-grad-${i}`,
    })

    // Dropoff curve
    if (droppedCount > 0) {
      const dropH = Math.max(3, (droppedCount / (src.count || 1)) * 12)
      const dropX1 = x1
      const dropY1 = src.y + src.h / 2 + ribbonH / 2
      const dropX2 = src.x + src.w + 36
      const dropY2 = 104

      const dropD = `M ${dropX1} ${dropY1}
                     C ${dropX1 + 18} ${dropY1 + 10}, ${dropX2 - 12} ${dropY2 - 8}, ${dropX2} ${dropY2}
                     L ${dropX2 + 6} ${dropY2 + dropH}
                     C ${dropX2 - 8} ${dropY2 + dropH}, ${dropX1 + 14} ${dropY1 + dropH + 4}, ${dropX1} ${dropY1 + dropH} Z`

      dropoffs.push({
        from: src.label,
        count: droppedCount,
        pathD: dropD,
        labelX: dropX2 + 8,
        labelY: dropY2 + 6,
      })
    }
  }

  return { nodes, flows, dropoffs }
})
</script>

<template>
  <div class="page-container">
    <!-- Header -->
    <div class="page-header">
      <div class="header-text">
        <h1 class="page-title">
          <BarChart3 class="text-primary title-icon" :size="22" />
          Market Intelligence &amp; Analytics
        </h1>
        <p class="page-subtitle">
          Comprehensive skill demand, salary benchmarks, and pipeline conversion metrics across your tracked applications.
        </p>
      </div>

      <div class="header-filters">
        <!-- Date Filter -->
        <div class="filter-pill">
          <CalendarDays :size="14" class="filter-icon" />
          <div class="select-wrapper">
            <select v-model="filters.days" @change="fetchAnalytics">
              <option v-for="opt in dateOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
            <ChevronDown :size="13" class="select-chevron" />
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="analytics-content">
      <div v-if="loading && !analyticsData" class="loading-state">
        <RefreshCw class="spin text-primary" :size="32" />
        <p>Crunching pipeline intelligence...</p>
      </div>

      <div v-else-if="analyticsData" class="dashboard-layout">
        <!-- 4-Card Top KPI Banner -->
        <div class="kpi-banner-4">
          <div class="kpi-card">
            <div class="kpi-icon-badge badge-neutral">
              <Briefcase :size="18" />
            </div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData.total_applications }}</div>
              <div class="kpi-label">Total Applications</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon-badge badge-blue">
              <TrendingUp :size="18" />
            </div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData.active_pipeline_count }}</div>
              <div class="kpi-label">Active Pipeline</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon-badge badge-green">
              <Target :size="18" />
            </div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData.interview_rate.toFixed(1) }}%</div>
              <div class="kpi-label">Interview Rate</div>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-icon-badge badge-amber">
              <Sparkles :size="18" />
            </div>
            <div class="kpi-info">
              <div class="kpi-value">
                {{ analyticsData.average_fit_score ? analyticsData.average_fit_score.toFixed(0) + '%' : 'N/A' }}
              </div>
              <div class="kpi-label">Avg Candidate Fit</div>
            </div>
          </div>
        </div>

        <!-- 2x2 Bento Dashboard Grid -->
        <div class="bento-grid">
          <!-- Bento 1: Top In-Demand Market Skills -->
          <div class="bento-card">
            <div class="card-header">
              <div class="header-left">
                <div class="card-title-row">
                  <h3 class="card-title">Top In-Demand Market Skills</h3>
                  <span class="badge-count">{{ analyticsData.top_in_demand_skills.length }} skills</span>
                </div>
                <p class="card-desc">Required competencies extracted across your application pool</p>
              </div>
            </div>

            <div v-if="analyticsData.top_in_demand_skills.length === 0" class="empty-state">
              <Layers :size="24" class="text-muted" />
              <span>No skill data extracted yet. Track jobs to populate market demand.</span>
            </div>

            <div v-else class="compact-list-container">
              <div
                v-for="skill in analyticsData.top_in_demand_skills"
                :key="skill.skill"
                class="skill-row-compact"
              >
                <div class="skill-name-col">
                  <span class="skill-name-text">{{ skill.skill }}</span>
                  <span
                    v-if="skill.is_in_candidate_cv"
                    class="status-chip chip-has-skill"
                    title="Present in your active CV"
                  >
                    <CheckCircle2 :size="11" />
                    <span>Has Skill</span>
                  </span>
                  <span v-else class="status-chip chip-missing" title="Missing from your active CV">
                    <span>Missing</span>
                  </span>
                </div>

                <div class="skill-track-col">
                  <div class="track-bar">
                    <div
                      class="track-fill"
                      :style="{ width: `${(skill.count / maxSkillCount) * 100}%` }"
                    ></div>
                  </div>
                </div>

                <div class="skill-meta-col">
                  <span class="job-count-pill">{{ skill.count }} {{ skill.count === 1 ? 'job' : 'jobs' }}</span>
                  <span
                    v-if="skill.avg_salary_min || skill.avg_salary_max"
                    class="salary-estimate-pill"
                    title="Estimated average salary"
                  >
                    ~{{ formatSalary(skill.avg_salary_min || skill.avg_salary_max) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Bento 2: Pipeline Sankey Flow & Work Models -->
          <div class="bento-card">
            <div class="card-header">
              <div class="header-left">
                <div class="card-title-row">
                  <h3 class="card-title">Pipeline Conversion &amp; Work Models</h3>
                </div>
                <p class="card-desc">Sankey stage flow and workplace distribution</p>
              </div>
            </div>

            <!-- Native SVG Sankey Flow Diagram -->
            <div v-if="sankeyData" class="sankey-container">
              <svg class="sankey-svg" viewBox="0 0 522 128">
                <defs>
                  <linearGradient
                    v-for="flow in sankeyData.flows"
                    :id="flow.gradientId"
                    :key="flow.gradientId"
                    x1="0%"
                    y1="0%"
                    x2="100%"
                    y2="0%"
                  >
                    <stop offset="0%" :stop-color="flow.srcColor" stop-opacity="0.45" />
                    <stop offset="100%" :stop-color="flow.tgtColor" stop-opacity="0.45" />
                  </linearGradient>
                </defs>

                <!-- Drop-off Curved Branches -->
                <g class="sankey-dropoffs-layer">
                  <path
                    v-for="(drop, dIdx) in sankeyData.dropoffs"
                    :key="'drop-' + dIdx"
                    :d="drop.pathD"
                    class="sankey-dropoff"
                  >
                    <title>{{ drop.count }} applications dropped after {{ drop.from }}</title>
                  </path>
                  <text
                    v-for="(drop, dIdx) in sankeyData.dropoffs"
                    :key="'droplbl-' + dIdx"
                    :x="drop.labelX"
                    :y="drop.labelY"
                    class="sankey-dropoff-label"
                  >
                    -{{ drop.count }} drop
                  </text>
                </g>

                <!-- Progression Flow Ribbons -->
                <g class="sankey-flows-layer">
                  <path
                    v-for="(flow, fIdx) in sankeyData.flows"
                    :key="'flow-' + fIdx"
                    :d="flow.pathD"
                    :fill="`url(#${flow.gradientId})`"
                    class="sankey-ribbon"
                  >
                    <title>{{ flow.count }} applications advanced from {{ flow.from }} to {{ flow.to }}</title>
                  </path>
                </g>

                <!-- Stage Nodes (Capsules) -->
                <g class="sankey-nodes-layer">
                  <g
                    v-for="node in sankeyData.nodes"
                    :key="node.key"
                    class="sankey-node-group"
                  >
                    <!-- Capsule Background -->
                    <rect
                      :x="node.x"
                      :y="node.y"
                      :width="node.w"
                      :height="node.h"
                      rx="6"
                      class="sankey-node-rect"
                      :style="{ stroke: node.color, fill: `${node.color}18` }"
                    />
                    <!-- Node Label -->
                    <text
                      :x="node.x + node.w / 2"
                      :y="node.y + 16"
                      text-anchor="middle"
                      class="sankey-node-title"
                    >
                      {{ node.label }}
                    </text>
                    <!-- Node Metrics -->
                    <text
                      :x="node.x + node.w / 2"
                      :y="node.y + 32"
                      text-anchor="middle"
                      class="sankey-node-sub"
                    >
                      {{ node.count }} ({{ node.rate }}%)
                    </text>
                    <title>{{ node.label }}: {{ node.count }} applications ({{ node.rate }}% of total)</title>
                  </g>
                </g>
              </svg>
            </div>

            <!-- Work Model Distribution Widget -->
            <div class="wm-widget-box">
              <div class="wm-widget-header">
                <span class="wm-widget-title">
                  <Monitor :size="13" class="text-primary" />
                  Work Environment Distribution
                </span>
                <span class="wm-widget-count">{{ workModelStats.total }} jobs classified</span>
              </div>

              <!-- Multi-Segment Distribution Bar -->
              <div class="wm-progress-bar">
                <div
                  class="wm-bar-segment seg-remote"
                  :style="{ width: `${workModelStats.remotePct}%` }"
                  :title="`Remote: ${workModelStats.remoteCount} (${workModelStats.remotePct}%)`"
                ></div>
                <div
                  class="wm-bar-segment seg-hybrid"
                  :style="{ width: `${workModelStats.hybridPct}%` }"
                  :title="`Hybrid: ${workModelStats.hybridCount} (${workModelStats.hybridPct}%)`"
                ></div>
                <div
                  class="wm-bar-segment seg-onsite"
                  :style="{ width: `${workModelStats.onsitePct}%` }"
                  :title="`Onsite: ${workModelStats.onsiteCount} (${workModelStats.onsitePct}%)`"
                ></div>
                <div
                  class="wm-bar-segment seg-unknown"
                  :style="{ width: `${workModelStats.unknownPct}%` }"
                  :title="`Unspecified: ${workModelStats.unknownCount} (${workModelStats.unknownPct}%)`"
                ></div>
              </div>

              <!-- Work Model Interactive Toggle Buttons -->
              <div class="wm-pills-row">
                <button
                  type="button"
                  class="wm-pill pill-remote"
                  :class="{ active: filters.work_model === 'remote', 'opacity-50': workModelStats.remoteCount === 0 }"
                  :title="filters.work_model === 'remote' ? 'Active filter: Remote (Click to clear)' : 'Filter by Remote jobs only'"
                  @click="toggleWorkModel('remote')"
                >
                  <div class="wm-pill-left">
                    <Globe :size="12" />
                    <span class="wm-pill-label">Remote</span>
                  </div>
                  <span class="wm-pill-val">{{ workModelStats.remoteCount }} ({{ workModelStats.remotePct }}%)</span>
                </button>

                <button
                  type="button"
                  class="wm-pill pill-hybrid"
                  :class="{ active: filters.work_model === 'hybrid', 'opacity-50': workModelStats.hybridCount === 0 }"
                  :title="filters.work_model === 'hybrid' ? 'Active filter: Hybrid (Click to clear)' : 'Filter by Hybrid jobs only'"
                  @click="toggleWorkModel('hybrid')"
                >
                  <div class="wm-pill-left">
                    <Building2 :size="12" />
                    <span class="wm-pill-label">Hybrid</span>
                  </div>
                  <span class="wm-pill-val">{{ workModelStats.hybridCount }} ({{ workModelStats.hybridPct }}%)</span>
                </button>

                <button
                  type="button"
                  class="wm-pill pill-onsite"
                  :class="{ active: filters.work_model === 'onsite', 'opacity-50': workModelStats.onsiteCount === 0 }"
                  :title="filters.work_model === 'onsite' ? 'Active filter: Onsite (Click to clear)' : 'Filter by Onsite jobs only'"
                  @click="toggleWorkModel('onsite')"
                >
                  <div class="wm-pill-left">
                    <MapPin :size="12" />
                    <span class="wm-pill-label">Onsite</span>
                  </div>
                  <span class="wm-pill-val">{{ workModelStats.onsiteCount }} ({{ workModelStats.onsitePct }}%)</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Bento 3: Compensation Benchmarks -->
          <div class="bento-card">
            <div class="card-header">
              <div class="header-left">
                <div class="card-title-row">
                  <h3 class="card-title">Compensation Benchmarks</h3>
                  <span class="badge-count">{{ analyticsData.salary_insights.length }} tech stacks</span>
                </div>
                <p class="card-desc">Market salary spans across extracted technologies</p>
              </div>
            </div>

            <div v-if="analyticsData.salary_insights.length === 0" class="empty-state">
              <DollarSign :size="24" class="text-muted" />
              <span>No salary compensation data found in tracked postings.</span>
            </div>

            <div v-else class="compact-list-container">
              <div
                v-for="item in analyticsData.salary_insights"
                :key="item.skill"
                class="salary-row-compact"
              >
                <span class="salary-skill-text">{{ item.skill }}</span>

                <div class="salary-spectrum-container">
                  <div class="spectrum-base-track">
                    <div
                      class="spectrum-span-fill"
                      :style="getSalarySpectrumStyle(item.avg_min, item.avg_max)"
                    ></div>
                  </div>
                </div>

                <div class="salary-range-label font-mono">
                  <span class="sal-min">{{ formatSalary(item.avg_min) || 'N/A' }}</span>
                  <span class="sal-sep">–</span>
                  <span class="sal-max">{{ formatSalary(item.avg_max) || 'N/A' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Bento 4: Personal Skill Gap Matrix -->
          <div class="bento-card">
            <div class="card-header">
              <div class="header-left">
                <div class="card-title-row">
                  <h3 class="card-title">Personal Skill Gap Matrix</h3>
                  <span class="badge-count">{{ analyticsData.priority_skill_gaps.length }} gaps</span>
                </div>
                <p class="card-desc">High priority missing skills ranked by frequency &amp; market compensation</p>
              </div>
            </div>

            <div v-if="analyticsData.priority_skill_gaps.length === 0" class="empty-state">
              <Sparkles :size="24" class="text-primary" />
              <span>No critical skill gaps identified! Your profile aligns closely with pipeline requirements.</span>
            </div>

            <div v-else class="compact-list-container">
              <div
                v-for="gap in analyticsData.priority_skill_gaps"
                :key="gap.skill"
                class="gap-row-compact"
              >
                <div class="gap-left-col">
                  <div class="gap-title-row">
                    <span class="gap-name-text">{{ gap.skill }}</span>
                    <span class="priority-score-badge" title="Calculated upskill priority score">
                      <Flame :size="11" class="text-amber" />
                      <span>Priority: {{ gap.priority_score.toFixed(1) }}</span>
                    </span>
                  </div>

                  <div class="gap-bar-wrap">
                    <div
                      class="gap-bar-fill"
                      :style="{ width: `${(gap.priority_score / maxGapScore) * 100}%` }"
                    ></div>
                  </div>
                </div>

                <div class="gap-right-col">
                  <span class="gap-frequency-tag">
                    {{ gap.missing_frequency }} {{ gap.missing_frequency === 1 ? 'job' : 'jobs' }}
                  </span>
                  <div v-if="gap.sample_companies?.length" class="gap-companies-flex">
                    <span
                      v-for="comp in gap.sample_companies"
                      :key="comp"
                      class="company-mini-badge"
                    >
                      <Building2 :size="10" />
                      <span>{{ comp }}</span>
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

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 16px;
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 19px;
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
  gap: 10px;
}

.filter-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 5px 10px;
  border-radius: var(--radius-full);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.filter-pill:hover {
  border-color: var(--border-focus);
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
  font-size: 12px;
  font-weight: 600;
  padding-right: 18px;
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
  padding: 20px 24px 32px;
  overflow-y: auto;
  flex: 1;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 280px;
  gap: 14px;
  color: var(--text-secondary);
  font-size: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.dashboard-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1440px;
  margin: 0 auto;
}

/* 4-Card KPI Banner */
.kpi-banner-4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.kpi-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: transform var(--transition-fast), border-color var(--transition-fast);
}

.kpi-card:hover {
  border-color: var(--border-focus);
}

.kpi-icon-badge {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.badge-neutral {
  background-color: rgba(148, 163, 184, 0.12);
  color: var(--text-main);
}

.badge-blue {
  background-color: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
}

.badge-green {
  background-color: rgba(34, 197, 94, 0.12);
  color: #10b981;
}

.badge-amber {
  background-color: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.kpi-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Bento Grid */
.bento-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.bento-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 2px;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}

.badge-count {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.card-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 3px 0 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  gap: 10px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
}

/* Compact Scrollable List Containers */
.compact-list-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 380px;
  overflow-y: auto;
  padding-right: 4px;
}

.compact-list-container::-webkit-scrollbar {
  width: 4px;
}

.compact-list-container::-webkit-scrollbar-thumb {
  background-color: var(--border-color);
  border-radius: 4px;
}

/* Skill Rows (Quadrant 1) */
.skill-row-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle, var(--border-color));
  gap: 12px;
}

.skill-name-col {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 170px;
  flex-shrink: 0;
}

.skill-name-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.chip-has-skill {
  background-color: rgba(34, 197, 94, 0.12);
  color: #10b981;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.chip-missing {
  background-color: rgba(148, 163, 184, 0.12);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}

.skill-track-col {
  flex: 1;
  min-width: 60px;
}

.track-bar {
  height: 5px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  overflow: hidden;
}

.track-fill {
  height: 100%;
  border-radius: 4px;
  background-color: var(--primary);
  transition: width var(--transition-normal);
}

.skill-meta-col {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.job-count-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

.salary-estimate-pill {
  font-size: 10px;
  font-weight: 600;
  font-family: monospace;
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  background-color: var(--primary-subtle, rgba(45, 212, 191, 0.12));
  color: var(--primary);
}

/* Sankey Flow Diagram (Quadrant 2) */
.sankey-container {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 10px 4px;
  display: flex;
  flex-direction: column;
}

.sankey-svg {
  width: 100%;
  height: auto;
  display: block;
}

.sankey-ribbon {
  opacity: 0.55;
  transition: opacity var(--transition-fast), filter var(--transition-fast);
  cursor: pointer;
}

.sankey-ribbon:hover {
  opacity: 0.9;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.25));
}

.sankey-dropoff {
  fill: rgba(239, 68, 68, 0.28);
  stroke: rgba(239, 68, 68, 0.4);
  stroke-width: 0.5px;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.sankey-dropoff:hover {
  fill: rgba(239, 68, 68, 0.6);
}

.sankey-dropoff-label {
  font-size: 9px;
  font-weight: 700;
  fill: #ef4444;
  dominant-baseline: middle;
}

.sankey-node-group {
  cursor: pointer;
  transition: transform var(--transition-fast);
}

.sankey-node-group:hover {
  filter: brightness(1.1);
}

.sankey-node-rect {
  stroke-width: 1.5px;
  transition: all var(--transition-fast);
}

.sankey-node-title {
  font-size: 11px;
  font-weight: 700;
  fill: var(--text-main);
  dominant-baseline: middle;
}

.sankey-node-sub {
  font-size: 10px;
  font-weight: 600;
  fill: var(--text-secondary);
  dominant-baseline: middle;
}

/* Work Model Split Box */
.wm-widget-box {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.wm-widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.wm-widget-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 6px;
}

.wm-widget-count {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
}

.wm-progress-bar {
  height: 7px;
  border-radius: 5px;
  background-color: var(--bg-elevated);
  display: flex;
  overflow: hidden;
}

.wm-bar-segment {
  height: 100%;
  transition: width var(--transition-normal);
}

.seg-remote {
  background-color: #3b82f6;
}

.seg-hybrid {
  background-color: #f59e0b;
}

.seg-onsite {
  background-color: #ec4899;
}

.seg-unknown {
  background-color: #94a3b8;
}

.wm-pills-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.wm-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 8px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 10px;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
  user-select: none;
}

.wm-pill:hover {
  border-color: var(--border-focus);
  transform: translateY(-1px);
}

.wm-pill-left {
  display: flex;
  align-items: center;
  gap: 5px;
}

.pill-remote {
  border-left: 3px solid #3b82f6;
}

.pill-remote.active {
  background-color: rgba(59, 130, 246, 0.16);
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
}

.pill-hybrid {
  border-left: 3px solid #f59e0b;
}

.pill-hybrid.active {
  background-color: rgba(245, 158, 11, 0.16);
  border-color: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.25);
}

.pill-onsite {
  border-left: 3px solid #ec4899;
}

.pill-onsite.active {
  background-color: rgba(236, 72, 153, 0.16);
  border-color: #ec4899;
  box-shadow: 0 0 0 2px rgba(236, 72, 153, 0.25);
}

.wm-pill-label {
  font-weight: 600;
  color: var(--text-secondary);
}

.wm-pill-val {
  font-weight: 700;
  color: var(--text-main);
}

.opacity-50 {
  opacity: 0.5;
}

/* Compensation Spectrum Rows (Quadrant 3) */
.salary-row-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle, var(--border-color));
  gap: 12px;
}

.salary-skill-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  width: 140px;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.salary-spectrum-container {
  flex: 1;
  min-width: 80px;
}

.spectrum-base-track {
  height: 6px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  position: relative;
  overflow: hidden;
}

/* Refined Harmonic Spectrum Gradient */
.spectrum-span-fill {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 4px;
  background: linear-gradient(90deg, #d97706 0%, #c2410c 50%, #9a3412 100%);
  box-shadow: 0 0 4px rgba(194, 65, 12, 0.25);
  transition: all var(--transition-normal);
}

:global(.midnight) .spectrum-span-fill {
  background: linear-gradient(90deg, #10b981 0%, #2dd4bf 50%, #38bdf8 100%);
  box-shadow: 0 0 4px rgba(45, 212, 191, 0.3);
}

:global(.daylight) .spectrum-span-fill {
  background: linear-gradient(90deg, #d97706 0%, #c2410c 50%, #9a3412 100%);
  box-shadow: 0 0 4px rgba(194, 65, 12, 0.25);
}

.salary-range-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
  width: 115px;
  text-align: right;
  flex-shrink: 0;
}

.sal-sep {
  color: var(--text-muted);
  margin: 0 3px;
}

/* Personal Skill Gap Rows (Quadrant 4) */
.gap-row-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle, var(--border-color));
  gap: 12px;
}

.gap-left-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 190px;
  flex-shrink: 0;
}

.gap-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.gap-name-text {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.priority-score-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: var(--radius-full);
  background-color: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.25);
  flex-shrink: 0;
}

.gap-bar-wrap {
  height: 4px;
  border-radius: 3px;
  background-color: var(--bg-elevated);
  overflow: hidden;
}

.gap-bar-fill {
  height: 100%;
  border-radius: 3px;
  background-color: #f59e0b;
  transition: width var(--transition-normal);
}

.gap-right-col {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.gap-frequency-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

.gap-companies-flex {
  display: flex;
  align-items: center;
  gap: 4px;
}

.company-mini-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 9px;
  font-weight: 600;
  padding: 2px 5px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.text-amber {
  color: #f59e0b;
}

/* Responsive Breakpoints */
@media (max-width: 1100px) {
  .kpi-banner-4 {
    grid-template-columns: repeat(2, 1fr);
  }

  .bento-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .kpi-banner-4 {
    grid-template-columns: 1fr;
  }

  .page-header {
    padding: 14px 16px;
  }

  .analytics-content {
    padding: 14px 16px 24px;
  }

  .wm-pills-row {
    grid-template-columns: 1fr;
  }
}
</style>
