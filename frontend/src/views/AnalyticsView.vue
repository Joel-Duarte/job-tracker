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
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  PieChart,
  Banknote,
  FileEdit,
  Copy,
  Check,
  Search,
  ArrowRight,
  ShieldAlert,
  Zap,
} from 'lucide-vue-next'
import { useUIStore } from '../stores/uiStore'
import { getCurrencySymbol } from '../utils/formatters'
import PageHeader from '../components/common/PageHeader.vue'

const uiStore = useUIStore()

// Active Tab: 'market' | 'funnel' | 'alignment'
const activeTab = ref('market')

// Role Alignment State & Filters
const loadingAlignment = ref(true)
const alignmentData = ref(null)
const selectedTrackKey = ref('all')
const customSearchQuery = ref('')
const copiedItemKey = ref(null)

// Market Intelligence State & Filters
const loadingMarket = ref(true)
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

// Pipeline Funnel Performance State & Filters
const loadingFunnel = ref(true)
const funnelData = ref(null)
const funnelPeriod = ref('weekly') // 'weekly' | 'monthly'

function toggleWorkModel(model) {
  if (filters.value.work_model === model) {
    filters.value.work_model = 'all'
  } else {
    filters.value.work_model = model
  }
  fetchAnalytics()
}

async function fetchAnalytics() {
  loadingMarket.value = true
  try {
    const params = {}
    if (filters.value.days) params.days = filters.value.days
    if (filters.value.work_model !== 'all') params.work_model = filters.value.work_model

    const res = await AnalyticsAPI.getOverview(params)
    analyticsData.value = res.data
  } catch (err) {
    uiStore.showToast('Failed to load market intelligence', 'error')
    console.error(err)
    if (!analyticsData.value) {
      analyticsData.value = {
        total_applications: 0,
        active_pipeline_count: 0,
        interview_rate: 0.0,
        offer_rate: 0.0,
        average_fit_score: null,
        top_in_demand_skills: [],
        priority_skill_gaps: [],
        pipeline_funnel: [
          { stage: 'Applied', count: 0, conversion_rate: 0, dropoff_rate: 0 },
          { stage: 'Assessment', count: 0, conversion_rate: 0, dropoff_rate: 0 },
          { stage: 'Interview', count: 0, conversion_rate: 0, dropoff_rate: 0 },
          { stage: 'Offer', count: 0, conversion_rate: 0, dropoff_rate: 0 },
        ],
        work_model_distribution: { remote_count: 0, hybrid_count: 0, onsite_count: 0, unknown_count: 0 },
        salary_insights: [],
      }
    }
  } finally {
    loadingMarket.value = false
  }
}

async function fetchFunnelMetrics() {
  loadingFunnel.value = true
  try {
    const res = await AnalyticsAPI.getFunnelMetrics({ period: funnelPeriod.value })
    funnelData.value = res.data
  } catch (err) {
    uiStore.showToast('Failed to load pipeline funnel performance', 'error')
    console.error(err)
    if (!funnelData.value) {
      funnelData.value = {
        period_type: funnelPeriod.value,
        summary_kpis: {
          intakes: { label: 'Total Intake Leads', value: 14, trend_percentage: 12.0, is_positive: true },
          applications: { label: 'Submitted Applications', value: 10, trend_percentage: 8.5, is_positive: true },
          interviews: { label: 'Interview Conversions', value: 4, trend_percentage: 25.0, is_positive: true },
          offers: { label: 'Offers Received', value: 2, trend_percentage: 50.0, is_positive: true },
        },
        chart_data: [
          { period_key: 'P1', period_label: 'W01', start_date: '2025-01-01', end_date: '2025-01-07', intakes: 10, applications: 7, interviews: 2, offers: 1, conversion_rate: 28.5 },
          { period_key: 'P2', period_label: 'W02', start_date: '2025-01-08', end_date: '2025-01-14', intakes: 14, applications: 10, interviews: 4, offers: 2, conversion_rate: 40.0 },
        ],
        table_data: [
          { period_key: 'P2', period_label: 'W02', start_date: '2025-01-08', end_date: '2025-01-14', intakes: 14, applications: 10, interviews: 4, offers: 2, conversion_rate: 40.0 },
          { period_key: 'P1', period_label: 'W01', start_date: '2025-01-01', end_date: '2025-01-07', intakes: 10, applications: 7, interviews: 2, offers: 1, conversion_rate: 28.5 },
        ]
      }
    }
  } finally {
    loadingFunnel.value = false
  }
}

async function fetchRoleAlignment() {
  loadingAlignment.value = true
  try {
    const trackParam = customSearchQuery.value.trim() || selectedTrackKey.value
    const params = { role_track: trackParam }
    if (filters.value.days) params.days = filters.value.days

    const res = await AnalyticsAPI.getRoleAlignment(params)
    alignmentData.value = res.data
  } catch (err) {
    uiStore.showToast('Failed to load role alignment analytics', 'error')
    console.error(err)
    if (!alignmentData.value) {
      alignmentData.value = {
        detected_tracks: [
          { key: 'all', label: 'All Tracks', job_count: 0 },
          { key: 'backend', label: 'Backend Engineering', job_count: 0 },
        ],
        selected_track: selectedTrackKey.value,
        total_analyzed_jobs: 0,
        vocabulary_shifts: [],
        bullet_reframes: [],
        missing_prerequisites: [],
      }
    }
  } finally {
    loadingAlignment.value = false
  }
}

function selectTrack(trackKey) {
  selectedTrackKey.value = trackKey
  customSearchQuery.value = ''
  fetchRoleAlignment()
}

function handleSearchInput() {
  if (customSearchQuery.value.trim()) {
    selectedTrackKey.value = ''
  } else if (!selectedTrackKey.value) {
    selectedTrackKey.value = 'all'
  }
  fetchRoleAlignment()
}

function copyToClipboard(text, key) {
  navigator.clipboard.writeText(text)
  copiedItemKey.value = key
  uiStore.showToast('Copied to clipboard!', 'success')
  setTimeout(() => {
    if (copiedItemKey.value === key) {
      copiedItemKey.value = null
    }
  }, 2000)
}

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'market' && !analyticsData.value) {
    fetchAnalytics()
  } else if (tab === 'funnel' && !funnelData.value) {
    fetchFunnelMetrics()
  } else if (tab === 'alignment' && !alignmentData.value) {
    fetchRoleAlignment()
  }
}

function handlePeriodChange() {
  fetchFunnelMetrics()
}

onMounted(() => {
  fetchAnalytics()
  fetchFunnelMetrics()
})

// Tab 1 Computed Metrics
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

function formatSalary(value, currency = null) {
  if (!value || isNaN(value)) return ''
  const curr = currency || uiStore.defaultCurrency || 'EUR'
  const sym = getCurrencySymbol(curr)
  return `${sym}${(value / 1000).toFixed(0)}k`
}

function getSalaryTooltip(item) {
  if (!item) return ''
  const count = item.sample_count || 1
  const countText = `Based on ${count} tracked ${count === 1 ? 'job' : 'jobs'}`
  const midText = item.median_salary
    ? `${formatSalary(item.median_salary)} median`
    : item.avg_min && item.avg_max
    ? `${formatSalary((item.avg_min + item.avg_max) / 2)} avg`
    : ''
  const rangeText = `${formatSalary(item.avg_min) || 'N/A'} – ${formatSalary(item.avg_max) || 'N/A'}`
  return `${countText}${midText ? ' • ' + midText : ''} • Range: ${rangeText}`
}

// Tab 1 Sankey Flow Calculations
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

// Tab 2 Funnel Visualization Max Count
const maxCohortVolume = computed(() => {
  if (!funnelData.value?.chart_data?.length) return 1
  let maxVal = 0
  for (const c of funnelData.value.chart_data) {
    maxVal = Math.max(maxVal, c.intakes, c.applications, c.interviews, c.offers)
  }
  return maxVal || 1
})
</script>

<template>
  <div class="page-container">
    <!-- Standardized Page Header with Centered Nav Tabs -->
    <PageHeader
      title="Market Intelligence & Analytics"
      subtitle="Comprehensive skill demand, salary benchmarks, and pipeline conversion metrics across your tracked applications."
      :icon="BarChart3"
      align="center"
    >
      <template #tabs>
        <div class="nav-tabs-container">
          <button
            type="button"
            class="tab-btn"
            :class="{ active: activeTab === 'market' }"
            @click="switchTab('market')"
          >
            <PieChart :size="15" />
            <span>Market Intelligence &amp; Salaries</span>
          </button>
          <button
            type="button"
            class="tab-btn"
            :class="{ active: activeTab === 'funnel' }"
            @click="switchTab('funnel')"
          >
            <TrendingUp :size="15" />
            <span>Pipeline Funnel Performance</span>
          </button>
          <button
            type="button"
            class="tab-btn"
            :class="{ active: activeTab === 'alignment' }"
            @click="switchTab('alignment')"
          >
            <FileEdit :size="15" />
            <span>Role Alignment &amp; CV Tuning</span>
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Main Content Area -->
    <div class="analytics-content">
      <!-- TAB 1: MARKET INTELLIGENCE & SALARIES -->
      <div v-if="activeTab === 'market'">
        <!-- Sub-Header Area with Time Filter for Tab 1 -->
        <div class="tab-sub-header">
          <div class="sub-header-left">
            <h2 class="sub-header-title">Market Demand &amp; Compensation Insights</h2>
            <p class="sub-header-desc">Analyze required skills, market compensation spans, and workplace model trends.</p>
          </div>
          <div class="sub-header-right">
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

        <div v-if="loadingMarket && !analyticsData" class="loading-state">
          <RefreshCw class="spin text-primary" :size="32" />
          <p>Crunching market intelligence...</p>
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
                      <rect
                        :x="node.x"
                        :y="node.y"
                        :width="node.w"
                        :height="node.h"
                        rx="6"
                        class="sankey-node-rect"
                        :style="{ stroke: node.color, fill: `${node.color}18` }"
                      />
                      <text
                        :x="node.x + node.w / 2"
                        :y="node.y + 16"
                        text-anchor="middle"
                        class="sankey-node-title"
                      >
                        {{ node.label }}
                      </text>
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
                <Banknote :size="24" class="text-muted" />
                <span>No salary compensation data found in tracked postings.</span>
              </div>

              <div v-else class="compact-list-container">
                <div
                  v-for="item in analyticsData.salary_insights"
                  :key="item.skill"
                  class="salary-row-compact"
                  :title="getSalaryTooltip(item)"
                >
                  <span class="salary-skill-text">{{ item.skill }}</span>

                  <div class="salary-spectrum-container">
                    <div class="spectrum-base-track">
                      <div
                        class="spectrum-span-fill"
                        :style="getSalarySpectrumStyle(item.avg_min, item.avg_max)"
                      ></div>
                    </div>

                    <!-- Floating Hover Tooltip -->
                    <div class="salary-hover-tooltip">
                      <div class="tooltip-header font-medium">
                        Based on {{ item.sample_count || 1 }} tracked {{ (item.sample_count || 1) === 1 ? 'job' : 'jobs' }}
                      </div>
                      <div class="tooltip-metrics">
                        <span v-if="item.median_salary" class="tooltip-badge">
                          {{ formatSalary(item.median_salary) }} median
                        </span>
                        <span v-else-if="item.avg_min && item.avg_max" class="tooltip-badge">
                          {{ formatSalary((item.avg_min + item.avg_max) / 2) }} avg
                        </span>
                        <span class="tooltip-range text-muted font-mono">
                          {{ formatSalary(item.avg_min) || 'N/A' }} – {{ formatSalary(item.avg_max) || 'N/A' }}
                        </span>
                      </div>
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
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: PIPELINE FUNNEL PERFORMANCE -->
      <div v-else-if="activeTab === 'funnel'">
        <!-- Sub-Header Area with Granularity Switcher -->
        <div class="tab-sub-header">
          <div class="sub-header-left">
            <h2 class="sub-header-title">Funnel Progression &amp; Conversion Cohorts</h2>
            <p class="sub-header-desc">Track top-of-funnel intake down to interviews and job offers across cohort periods.</p>
          </div>
          <div class="sub-header-right">
            <div class="toggle-pill-group">
              <button
                type="button"
                class="toggle-btn"
                :class="{ active: funnelPeriod === 'weekly' }"
                @click="funnelPeriod = 'weekly'; handlePeriodChange()"
              >
                Weekly
              </button>
              <button
                type="button"
                class="toggle-btn"
                :class="{ active: funnelPeriod === 'monthly' }"
                @click="funnelPeriod = 'monthly'; handlePeriodChange()"
              >
                Monthly
              </button>
            </div>
          </div>
        </div>

        <div v-if="loadingFunnel && !funnelData" class="loading-state">
          <RefreshCw class="spin text-primary" :size="32" />
          <p>Calculating cohort funnel performance...</p>
        </div>

        <div v-else-if="funnelData" class="dashboard-layout">
          <!-- KPI Summary Cards with Trend Deltas -->
          <div class="kpi-banner-4">
            <div class="kpi-card">
              <div class="kpi-icon-badge badge-neutral">
                <Briefcase :size="18" />
              </div>
              <div class="kpi-info">
                <div class="kpi-value-row">
                  <span class="kpi-value">{{ funnelData.summary_kpis.intakes.value }}</span>
                  <span
                    v-if="funnelData.summary_kpis.intakes.trend_percentage !== null"
                    class="trend-chip"
                    :class="funnelData.summary_kpis.intakes.is_positive ? 'trend-up' : 'trend-down'"
                  >
                    <component :is="funnelData.summary_kpis.intakes.is_positive ? ArrowUpRight : ArrowDownRight" :size="12" />
                    <span>{{ Math.abs(funnelData.summary_kpis.intakes.trend_percentage) }}%</span>
                  </span>
                </div>
                <div class="kpi-label">{{ funnelData.summary_kpis.intakes.label }}</div>
              </div>
            </div>

            <div class="kpi-card">
              <div class="kpi-icon-badge badge-blue">
                <Layers :size="18" />
              </div>
              <div class="kpi-info">
                <div class="kpi-value-row">
                  <span class="kpi-value">{{ funnelData.summary_kpis.applications.value }}</span>
                  <span
                    v-if="funnelData.summary_kpis.applications.trend_percentage !== null"
                    class="trend-chip"
                    :class="funnelData.summary_kpis.applications.is_positive ? 'trend-up' : 'trend-down'"
                  >
                    <component :is="funnelData.summary_kpis.applications.is_positive ? ArrowUpRight : ArrowDownRight" :size="12" />
                    <span>{{ Math.abs(funnelData.summary_kpis.applications.trend_percentage) }}%</span>
                  </span>
                </div>
                <div class="kpi-label">{{ funnelData.summary_kpis.applications.label }}</div>
              </div>
            </div>

            <div class="kpi-card">
              <div class="kpi-icon-badge badge-purple">
                <Target :size="18" />
              </div>
              <div class="kpi-info">
                <div class="kpi-value-row">
                  <span class="kpi-value">{{ funnelData.summary_kpis.interviews.value }}</span>
                  <span
                    v-if="funnelData.summary_kpis.interviews.trend_percentage !== null"
                    class="trend-chip"
                    :class="funnelData.summary_kpis.interviews.is_positive ? 'trend-up' : 'trend-down'"
                  >
                    <component :is="funnelData.summary_kpis.interviews.is_positive ? ArrowUpRight : ArrowDownRight" :size="12" />
                    <span>{{ Math.abs(funnelData.summary_kpis.interviews.trend_percentage) }}%</span>
                  </span>
                </div>
                <div class="kpi-label">{{ funnelData.summary_kpis.interviews.label }}</div>
              </div>
            </div>

            <div class="kpi-card">
              <div class="kpi-icon-badge badge-green">
                <Sparkles :size="18" />
              </div>
              <div class="kpi-info">
                <div class="kpi-value-row">
                  <span class="kpi-value">{{ funnelData.summary_kpis.offers.value }}</span>
                  <span
                    v-if="funnelData.summary_kpis.offers.trend_percentage !== null"
                    class="trend-chip"
                    :class="funnelData.summary_kpis.offers.is_positive ? 'trend-up' : 'trend-down'"
                  >
                    <component :is="funnelData.summary_kpis.offers.is_positive ? ArrowUpRight : ArrowDownRight" :size="12" />
                    <span>{{ Math.abs(funnelData.summary_kpis.offers.trend_percentage) }}%</span>
                  </span>
                </div>
                <div class="kpi-label">{{ funnelData.summary_kpis.offers.label }}</div>
              </div>
            </div>
          </div>

          <!-- Visual Funnel Progression Chart Container -->
          <div class="bento-card visual-funnel-card">
            <div class="card-header">
              <div class="header-left">
                <div class="card-title-row">
                  <h3 class="card-title">Visual Funnel Progression across Periods</h3>
                  <span class="badge-count">{{ funnelData.chart_data.length }} {{ funnelPeriod }} cohorts</span>
                </div>
                <p class="card-desc">Volume progression across Intakes, Applications, Interviews, and Offers.</p>
              </div>
              <div class="chart-legend">
                <span class="legend-item"><span class="dot dot-intake"></span> Intakes</span>
                <span class="legend-item"><span class="dot dot-app"></span> Applications</span>
                <span class="legend-item"><span class="dot dot-interview"></span> Interviews</span>
                <span class="legend-item"><span class="dot dot-offer"></span> Offers</span>
              </div>
            </div>

            <!-- Grouped Bar Progression Visualizer -->
            <div class="funnel-chart-container">
              <div
                v-for="cohort in funnelData.chart_data"
                :key="cohort.period_key"
                class="funnel-cohort-column"
              >
                <div class="bars-wrapper">
                  <!-- Intake Bar -->
                  <div
                    class="chart-bar bar-intake"
                    :style="{ height: `${(cohort.intakes / maxCohortVolume) * 100}%` }"
                    :title="`Intakes: ${cohort.intakes}`"
                  >
                    <span v-if="cohort.intakes > 0" class="bar-val">{{ cohort.intakes }}</span>
                  </div>

                  <!-- Applications Bar -->
                  <div
                    class="chart-bar bar-app"
                    :style="{ height: `${(cohort.applications / maxCohortVolume) * 100}%` }"
                    :title="`Applications: ${cohort.applications}`"
                  >
                    <span v-if="cohort.applications > 0" class="bar-val">{{ cohort.applications }}</span>
                  </div>

                  <!-- Interviews Bar -->
                  <div
                    class="chart-bar bar-interview"
                    :style="{ height: `${(cohort.interviews / maxCohortVolume) * 100}%` }"
                    :title="`Interviews: ${cohort.interviews}`"
                  >
                    <span v-if="cohort.interviews > 0" class="bar-val">{{ cohort.interviews }}</span>
                  </div>

                  <!-- Offers Bar -->
                  <div
                    class="chart-bar bar-offer"
                    :style="{ height: `${(cohort.offers / maxCohortVolume) * 100}%` }"
                    :title="`Offers: ${cohort.offers}`"
                  >
                    <span v-if="cohort.offers > 0" class="bar-val">{{ cohort.offers }}</span>
                  </div>
                </div>

                <div class="cohort-label-text">{{ cohort.period_label }}</div>
              </div>
            </div>
          </div>

          <!-- Historical Cohort Data Table -->
          <div class="bento-card">
            <div class="card-header">
              <div class="header-left">
                <div class="card-title-row">
                  <h3 class="card-title">Historical Cohort Performance</h3>
                  <span class="badge-count">{{ funnelData.table_data.length }} periods</span>
                </div>
                <p class="card-desc">Detailed cohort breakdown of volume and interview conversion rates.</p>
              </div>
            </div>

            <div class="table-responsive">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Date Range</th>
                    <th class="text-right">Intakes</th>
                    <th class="text-right">Applications</th>
                    <th class="text-right">Interviews</th>
                    <th class="text-right">Offers</th>
                    <th class="text-right">Interview Conversion</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in funnelData.table_data" :key="row.period_key">
                    <td class="font-bold text-main">{{ row.period_label }}</td>
                    <td class="text-muted font-mono text-xs">{{ row.start_date }} – {{ row.end_date }}</td>
                    <td class="text-right font-mono">{{ row.intakes }}</td>
                    <td class="text-right font-mono">{{ row.applications }}</td>
                    <td class="text-right font-mono">{{ row.interviews }}</td>
                    <td class="text-right font-mono">{{ row.offers }}</td>
                    <td class="text-right">
                      <span class="rate-badge" :class="row.conversion_rate > 0 ? 'rate-active' : 'rate-zero'">
                        {{ row.conversion_rate.toFixed(1) }}%
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: ROLE ALIGNMENT & CV TUNING -->
      <div v-else-if="activeTab === 'alignment'">
        <!-- Sub-Header Area -->
        <div class="tab-sub-header">
          <div class="sub-header-left">
            <h2 class="sub-header-title">Role Alignment &amp; Vocabulary Tuning Studio</h2>
            <p class="sub-header-desc">Aggregate ATS terminology shifts, high-impact bullet reframings, and role-track skill density from evaluated job dossiers.</p>
          </div>
          <div class="sub-header-right">
            <div class="search-input-wrapper">
              <Search :size="14" class="search-icon" />
              <input
                type="text"
                v-model="customSearchQuery"
                placeholder="Filter position title..."
                class="track-search-input"
                @input="handleSearchInput"
              />
            </div>
          </div>
        </div>

        <!-- Interactive Track Selector Bar -->
        <div v-if="alignmentData && alignmentData.detected_tracks.length > 0" class="track-selector-bar">
          <button
            v-for="track in alignmentData.detected_tracks"
            :key="track.key"
            type="button"
            class="track-pill"
            :class="{ active: selectedTrackKey === track.key && !customSearchQuery.trim() }"
            @click="selectTrack(track.key)"
          >
            <span class="track-label">{{ track.label }}</span>
            <span class="track-count-badge">{{ track.job_count }}</span>
          </button>
        </div>

        <div v-if="loadingAlignment && !alignmentData" class="loading-state">
          <RefreshCw class="spin text-primary" :size="32" />
          <p>Analyzing role alignment and vocabulary shifts...</p>
        </div>

        <div v-else-if="alignmentData" class="dashboard-layout">
          <!-- Bento Grid Layout for Role Alignment -->
          <div class="bento-grid alignment-bento-grid">
            <!-- Bento 1: High-Impact Vocabulary Shifts Table -->
            <div class="bento-card full-width-bento">
              <div class="card-header">
                <div class="header-left">
                  <div class="card-title-row">
                    <h3 class="card-title">🔄 High-Impact Vocabulary Shifts</h3>
                    <span class="badge-count">{{ alignmentData.vocabulary_shifts.length }} shifts</span>
                  </div>
                  <p class="card-desc">Translate your candidate CV terminology to employer ATS standards</p>
                </div>
              </div>

              <div v-if="alignmentData.vocabulary_shifts.length === 0" class="empty-state">
                <FileEdit :size="24" class="text-muted" />
                <span>No vocabulary translation shifts detected for this role track.</span>
              </div>

              <div v-else class="table-responsive">
                <table class="data-table vocab-table">
                  <thead>
                    <tr>
                      <th style="width: 20%;">Your CV Term</th>
                      <th style="width: 25%;">Market Standard Term (ATS)</th>
                      <th style="width: 20%;">Target Job Demand</th>
                      <th style="width: 25%;">Employer Rationale</th>
                      <th style="width: 10%;" class="text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(vocab, idx) in alignmentData.vocabulary_shifts" :key="'vocab-' + idx">
                      <td>
                        <span class="cv-term-badge">{{ vocab.cv_term }}</span>
                      </td>
                      <td>
                        <div class="jd-term-row">
                          <ArrowRight :size="13" class="text-muted" />
                          <span class="jd-term-text">{{ vocab.jd_term }}</span>
                        </div>
                      </td>
                      <td>
                        <div class="demand-col">
                          <div class="demand-bar-wrap">
                            <div class="demand-bar-fill" :style="{ width: `${vocab.frequency_pct}%` }"></div>
                          </div>
                          <span class="demand-text">{{ vocab.frequency_count }} jobs ({{ vocab.frequency_pct }}%)</span>
                        </div>
                      </td>
                      <td class="text-secondary text-xs">
                        {{ vocab.rationale }}
                      </td>
                      <td class="text-right">
                        <button
                          type="button"
                          class="action-copy-btn"
                          :title="`Copy '${vocab.jd_term}' to clipboard`"
                          @click="copyToClipboard(vocab.jd_term, 'vocab-' + idx)"
                        >
                          <component :is="copiedItemKey === 'vocab-' + idx ? Check : Copy" :size="13" />
                          <span>{{ copiedItemKey === 'vocab-' + idx ? 'Copied' : 'Copy' }}</span>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Bento 2: Bullet-Point Reframing Studio -->
            <div class="bento-card">
              <div class="card-header">
                <div class="header-left">
                  <div class="card-title-row">
                    <h3 class="card-title">⚡ Bullet-Point Reframing Studio</h3>
                    <span class="badge-count">{{ alignmentData.bullet_reframes.length }} reframes</span>
                  </div>
                  <p class="card-desc">Upgrade CV impact bullets with metric anchors &amp; ATS keywords</p>
                </div>
              </div>

              <div v-if="alignmentData.bullet_reframes.length === 0" class="empty-state">
                <Zap :size="24" class="text-muted" />
                <span>No bullet reframes available for this role track.</span>
              </div>

              <div v-else class="bullet-deck-container">
                <div
                  v-for="(bullet, idx) in alignmentData.bullet_reframes"
                  :key="'bullet-' + idx"
                  class="bullet-card-item"
                >
                  <div class="bullet-comparison-grid">
                    <div class="bullet-box original-box">
                      <div class="box-label">Current CV Bullet</div>
                      <p class="bullet-text">{{ bullet.original_bullet }}</p>
                    </div>

                    <div class="bullet-box upgraded-box">
                      <div class="box-label label-upgrade">
                        <Sparkles :size="12" />
                        <span>Market-Tuned Upgrade</span>
                      </div>
                      <p class="bullet-text font-medium">{{ bullet.suggested_rewrite }}</p>
                    </div>
                  </div>

                  <div class="bullet-card-footer">
                    <div class="bullet-rationale">
                      <span class="rationale-tag">ATS Alignment:</span>
                      <span class="rationale-desc">{{ bullet.reason }}</span>
                    </div>

                    <button
                      type="button"
                      class="copy-bullet-btn"
                      @click="copyToClipboard(bullet.suggested_rewrite, 'bullet-' + idx)"
                    >
                      <component :is="copiedItemKey === 'bullet-' + idx ? Check : Copy" :size="13" />
                      <span>{{ copiedItemKey === 'bullet-' + idx ? 'Copied Tuned Bullet' : 'Copy Tuned Bullet' }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Bento 3: Role Track Skill Density & Missing Prerequisites -->
            <div class="bento-card">
              <div class="card-header">
                <div class="header-left">
                  <div class="card-title-row">
                    <h3 class="card-title">📋 Missing Prerequisites Checklist</h3>
                    <span class="badge-count">{{ alignmentData.missing_prerequisites.length }} missing</span>
                  </div>
                  <p class="card-desc">High-frequency requirements in this track missing from your active CV</p>
                </div>
              </div>

              <div v-if="alignmentData.missing_prerequisites.length === 0" class="empty-state">
                <CheckCircle2 :size="24" class="text-primary" />
                <span>No missing skill prerequisites detected for this role track!</span>
              </div>

              <div v-else class="compact-list-container">
                <div
                  v-for="(item, idx) in alignmentData.missing_prerequisites"
                  :key="'missing-' + idx"
                  class="prereq-row-compact"
                >
                  <div class="prereq-left">
                    <ShieldAlert :size="14" class="text-amber" />
                    <span class="prereq-skill-name">{{ item.skill }}</span>
                  </div>

                  <div class="prereq-right">
                    <div class="prereq-bar-wrap">
                      <div class="prereq-bar-fill" :style="{ width: `${item.frequency_pct}%` }"></div>
                    </div>
                    <span class="prereq-pct-badge">{{ item.job_count }} jobs ({{ item.frequency_pct }}%)</span>
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
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
  min-height: calc(100vh - var(--navbar-height));
  width: 100%;
}

/* Nav Tabs Pill Selector */
.nav-tabs-container {
  display: inline-flex;
  align-items: center;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 4px;
  border-radius: var(--radius-full);
  gap: 4px;
  box-shadow: var(--shadow-sm);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--text-main);
}

.tab-btn.active {
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

/* Tab Sub-Header Area */
.tab-sub-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle, var(--border-color));
}

.sub-header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 2px 0;
}

.sub-header-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

/* Period Toggle Button Group */
.toggle-pill-group {
  display: inline-flex;
  align-items: center;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  padding: 3px;
  border-radius: var(--radius-full);
  gap: 2px;
}

.toggle-btn {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.toggle-btn:hover {
  color: var(--text-main);
}

.toggle-btn.active {
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  border-color: var(--primary);
  box-shadow: var(--shadow-sm);
}

.toggle-btn.active:hover {
  background-color: var(--primary-hover);
  border-color: var(--primary-hover);
  color: var(--primary-contrast, #0a0d14);
}

/* Theme-Aware Filter Bar */
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
  padding: 0;
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

.badge-purple {
  background-color: rgba(168, 85, 247, 0.12);
  color: #a855f7;
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
  width: 100%;
}

.kpi-value-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.trend-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.trend-up {
  background-color: rgba(34, 197, 94, 0.12);
  color: #10b981;
}

.trend-down {
  background-color: rgba(239, 68, 68, 0.12);
  color: #ef4444;
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
  overflow: visible;
}

.spectrum-span-fill {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    rgba(217, 119, 6, 0.25) 0%,
    rgba(194, 65, 12, 0.95) 50%,
    rgba(217, 119, 6, 0.25) 100%
  );
  box-shadow: 0 0 6px rgba(194, 65, 12, 0.35);
  transition: all var(--transition-normal);
}

:global(.midnight) .spectrum-span-fill {
  background: linear-gradient(
    90deg,
    rgba(45, 212, 191, 0.25) 0%,
    rgba(45, 212, 191, 0.95) 50%,
    rgba(45, 212, 191, 0.25) 100%
  );
  box-shadow: 0 0 6px rgba(45, 212, 191, 0.35);
}

:global(.daylight) .spectrum-span-fill {
  background: linear-gradient(
    90deg,
    rgba(217, 119, 6, 0.25) 0%,
    rgba(194, 65, 12, 0.95) 50%,
    rgba(217, 119, 6, 0.25) 100%
  );
  box-shadow: 0 0 6px rgba(194, 65, 12, 0.35);
}

.salary-hover-tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%) translateY(4px);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
  border-radius: var(--radius-sm, 6px);
  padding: 6px 10px;
  white-space: nowrap;
  font-size: 11px;
  color: var(--text-main);
  pointer-events: none;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.15s ease, transform 0.15s ease, visibility 0.15s;
  z-index: 50;
}

.salary-row-compact:hover .salary-hover-tooltip,
.salary-spectrum-container:hover .salary-hover-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(0);
}

.tooltip-header {
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.tooltip-metrics {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tooltip-badge {
  font-weight: 700;
  color: var(--text-amber, #f59e0b);
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

/* Tab 2 Visual Funnel Styling */
.chart-legend {
  display: flex;
  align-items: center;
  gap: 14px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-intake {
  background-color: #64748b;
}

.dot-app {
  background-color: #3b82f6;
}

.dot-interview {
  background-color: #a855f7;
}

.dot-offer {
  background-color: #10b981;
}

.funnel-chart-container {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 220px;
  padding: 20px 10px 10px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  gap: 12px;
}

.funnel-cohort-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  flex: 1;
  gap: 8px;
}

.bars-wrapper {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
  width: 100%;
  flex: 1;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 2px;
}

.chart-bar {
  width: 14px;
  border-radius: 3px 3px 0 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  transition: height var(--transition-normal), opacity var(--transition-fast);
  position: relative;
  min-height: 2px;
}

.chart-bar:hover {
  opacity: 0.85;
}

.bar-intake {
  background-color: #64748b;
}

.bar-app {
  background-color: #3b82f6;
}

.bar-interview {
  background-color: #a855f7;
}

.bar-offer {
  background-color: #10b981;
}

.bar-val {
  font-size: 9px;
  font-weight: 700;
  color: var(--text-main);
  position: absolute;
  top: -14px;
}

.cohort-label-text {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* Data Table Styling */
.table-responsive {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  background-color: var(--bg-card);
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}

.data-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle, var(--border-color));
  color: var(--text-main);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.text-right {
  text-align: right;
}

.font-mono {
  font-family: monospace;
}

.font-bold {
  font-weight: 700;
}

.rate-badge {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 700;
  font-family: monospace;
}

.rate-active {
  background-color: rgba(34, 197, 94, 0.12);
  color: #10b981;
}

.rate-zero {
  background-color: var(--bg-elevated);
  color: var(--text-muted);
}

.text-amber {
  color: #f59e0b;
}

/* Role Alignment & CV Tuning Tab Styles */
.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-secondary);
  pointer-events: none;
}

.track-search-input {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  border-radius: var(--radius-full);
  padding: 5px 12px 5px 30px;
  font-size: 12px;
  font-weight: 500;
  outline: none;
  width: 200px;
  transition: border-color var(--transition-fast), width var(--transition-fast);
}

.track-search-input:focus {
  border-color: var(--border-focus);
  width: 240px;
}

.track-selector-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 8px;
  margin-bottom: 16px;
}

.track-selector-bar::-webkit-scrollbar {
  height: 4px;
}

.track-selector-bar::-webkit-scrollbar-thumb {
  background-color: var(--border-color);
  border-radius: 4px;
}

.track-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.track-pill:hover {
  border-color: var(--border-focus);
  color: var(--text-main);
}

.track-pill.active {
  background-color: var(--primary-subtle, rgba(45, 212, 191, 0.14));
  border-color: var(--primary);
  color: var(--primary);
}

.track-count-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background-color: var(--bg-elevated);
  color: var(--text-main);
}

.track-pill.active .track-count-badge {
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
}

.alignment-bento-grid {
  grid-template-columns: repeat(2, 1fr);
}

.full-width-bento {
  grid-column: 1 / -1;
}

/* Vocabulary Shifts Table */
.vocab-table td {
  vertical-align: middle;
}

.cv-term-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.jd-term-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.jd-term-text {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
}

.demand-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.demand-bar-wrap {
  height: 5px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  overflow: hidden;
  width: 100%;
}

.demand-bar-fill {
  height: 100%;
  border-radius: 4px;
  background-color: var(--primary);
  transition: width var(--transition-normal);
}

.demand-text {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.action-copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-copy-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  background-color: var(--primary-subtle, rgba(45, 212, 191, 0.1));
}

/* Bullet Reframing Studio */
.bullet-deck-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 440px;
  overflow-y: auto;
  padding-right: 4px;
}

.bullet-card-item {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bullet-comparison-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.bullet-box {
  padding: 10px 12px;
  border-radius: var(--radius-xs);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.original-box {
  background-color: rgba(148, 163, 184, 0.08);
  border: 1px solid var(--border-subtle, var(--border-color));
}

.upgraded-box {
  background-color: var(--primary-subtle, rgba(45, 212, 191, 0.08));
  border: 1px solid rgba(45, 212, 191, 0.25);
}

.box-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.label-upgrade {
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.bullet-text {
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-main);
  margin: 0;
}

.bullet-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 6px;
  border-top: 1px dashed var(--border-color);
}

.bullet-rationale {
  font-size: 11px;
  color: var(--text-secondary);
}

.rationale-tag {
  font-weight: 700;
  margin-right: 4px;
}

.copy-bullet-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: var(--radius-xs);
  background-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
  font-size: 11px;
  font-weight: 700;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.copy-bullet-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Missing Prerequisites Checklist */
.prereq-row-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-card);
  border: 1px solid var(--border-subtle, var(--border-color));
  gap: 12px;
}

.prereq-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.prereq-skill-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
}

.prereq-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.prereq-bar-wrap {
  width: 60px;
  height: 5px;
  border-radius: 4px;
  background-color: var(--bg-elevated);
  overflow: hidden;
}

.prereq-bar-fill {
  height: 100%;
  border-radius: 4px;
  background-color: #f59e0b;
}

.prereq-pct-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

/* Responsive Breakpoints */
@media (max-width: 1100px) {
  .kpi-banner-4 {
    grid-template-columns: repeat(2, 1fr);
  }

  .bento-grid {
    grid-template-columns: 1fr;
  }

  .bullet-comparison-grid {
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

  .wm-pills-row {
    grid-template-columns: 1fr;
  }

  .tab-sub-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
