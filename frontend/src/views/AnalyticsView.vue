<script setup>
import { ref, onMounted, computed } from 'vue'
import { AnalyticsAPI } from '../api/endpoints'
import {
  BarChart3,
  Activity,
  PieChart,
  Clock,
  RefreshCw,
  TrendingUp,
  Target,
  Briefcase,
  CheckCircle2,
  Building2,
  Monitor,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Globe,
  MapPin,
  Flame,
  DollarSign,
  Layers,
  Sparkles,
} from 'lucide-vue-next'
import { useUIStore } from '../stores/uiStore'
import PageHeader from '../components/common/PageHeader.vue'

const uiStore = useUIStore()

const currentTab = ref('velocity')
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


const activityData = ref(null)
const activityHistory = ref([])
const velocityLoading = ref(false)

const velocityPeriod = ref('this_week')
const velocityCustomStart = ref(null)
const velocityCustomEnd = ref(null)

// Custom Date Range Picker state
const isCustomPickerOpen = ref(false)
const customPickerRef = ref(null)

const calendarViewYear = ref(new Date().getFullYear())
const calendarViewMonth = ref(new Date().getMonth())

const tempRangeStart = ref(null)
const tempRangeEnd = ref(null)

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]
const DAYS_OF_WEEK = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

function toggleCustomPicker() {
  velocityPeriod.value = 'custom'
  isCustomPickerOpen.value = !isCustomPickerOpen.value
  if (isCustomPickerOpen.value) {
    if (velocityCustomStart.value) {
      const d = new Date(velocityCustomStart.value + 'T00:00:00')
      if (!isNaN(d.getTime())) {
        calendarViewYear.value = d.getFullYear()
        calendarViewMonth.value = d.getMonth()
      }
    }
  }
}

function prevPickerMonth() {
  if (calendarViewMonth.value === 0) {
    calendarViewMonth.value = 11
    calendarViewYear.value--
  } else {
    calendarViewMonth.value--
  }
}

function nextPickerMonth() {
  if (calendarViewMonth.value === 11) {
    calendarViewMonth.value = 0
    calendarViewYear.value++
  } else {
    calendarViewMonth.value++
  }
}

function toYMD(year, month, day) {
  const m = String(month + 1).padStart(2, '0')
  const d = String(day).padStart(2, '0')
  return `${year}-${m}-${d}`
}

const pickerCalendarDays = computed(() => {
  const days = []
  const firstDayOfMonth = new Date(calendarViewYear.value, calendarViewMonth.value, 1).getDay()
  const daysInMonth = new Date(calendarViewYear.value, calendarViewMonth.value + 1, 0).getDate()
  const daysInPrevMonth = new Date(calendarViewYear.value, calendarViewMonth.value, 0).getDate()

  const todayStr = toYMD(new Date().getFullYear(), new Date().getMonth(), new Date().getDate())

  for (let i = firstDayOfMonth - 1; i >= 0; i--) {
    const d = daysInPrevMonth - i
    const m = calendarViewMonth.value === 0 ? 11 : calendarViewMonth.value - 1
    const y = calendarViewMonth.value === 0 ? calendarViewYear.value - 1 : calendarViewYear.value
    const ymd = toYMD(y, m, d)
    days.push({ day: d, month: m, year: y, ymd, isCurrentMonth: false, isToday: ymd === todayStr })
  }

  for (let i = 1; i <= daysInMonth; i++) {
    const ymd = toYMD(calendarViewYear.value, calendarViewMonth.value, i)
    days.push({ day: i, month: calendarViewMonth.value, year: calendarViewYear.value, ymd, isCurrentMonth: true, isToday: ymd === todayStr })
  }

  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    const m = calendarViewMonth.value === 11 ? 0 : calendarViewMonth.value + 1
    const y = calendarViewMonth.value === 11 ? calendarViewYear.value + 1 : calendarViewYear.value
    const ymd = toYMD(y, m, i)
    days.push({ day: i, month: m, year: y, ymd, isCurrentMonth: false, isToday: ymd === todayStr })
  }

  return days
})

function onDateClick(ymd) {
  if (!tempRangeStart.value || (tempRangeStart.value && tempRangeEnd.value)) {
    tempRangeStart.value = ymd
    tempRangeEnd.value = null
  } else {
    tempRangeEnd.value = ymd
    let start = tempRangeStart.value
    let end = tempRangeEnd.value
    if (start > end) {
      const tmp = start
      start = end
      end = tmp
    }
    velocityCustomStart.value = start
    velocityCustomEnd.value = end
    fetchActivity()
    setTimeout(() => {
      isCustomPickerOpen.value = false
    }, 200)
  }
}

function isDateSelectedStart(ymd) {
  if (tempRangeStart.value && !tempRangeEnd.value) {
    return tempRangeStart.value === ymd
  }
  if (velocityCustomStart.value && velocityCustomEnd.value) {
    const start = velocityCustomStart.value < velocityCustomEnd.value ? velocityCustomStart.value : velocityCustomEnd.value
    return ymd === start
  }
  return false
}

function isDateSelectedEnd(ymd) {
  if (tempRangeStart.value && tempRangeEnd.value) {
    const end = tempRangeStart.value > tempRangeEnd.value ? tempRangeStart.value : tempRangeEnd.value
    return ymd === end
  }
  if (velocityCustomStart.value && velocityCustomEnd.value) {
    const end = velocityCustomStart.value > velocityCustomEnd.value ? velocityCustomStart.value : velocityCustomEnd.value
    return ymd === end
  }
  return false
}

function isDateInRange(ymd) {
  let start, end
  if (tempRangeStart.value && tempRangeEnd.value) {
    start = tempRangeStart.value < tempRangeEnd.value ? tempRangeStart.value : tempRangeEnd.value
    end = tempRangeStart.value > tempRangeEnd.value ? tempRangeStart.value : tempRangeEnd.value
  } else if (velocityCustomStart.value && velocityCustomEnd.value) {
    start = velocityCustomStart.value < velocityCustomEnd.value ? velocityCustomStart.value : velocityCustomEnd.value
    end = velocityCustomStart.value > velocityCustomEnd.value ? velocityCustomEnd.value : velocityCustomStart.value
  } else {
    return false
  }
  return ymd > start && ymd < end
}

const formattedCustomRange = computed(() => {
  if (!velocityCustomStart.value || !velocityCustomEnd.value) return 'Custom Range'
  const d1 = new Date(velocityCustomStart.value + 'T00:00:00')
  const d2 = new Date(velocityCustomEnd.value + 'T00:00:00')
  if (isNaN(d1.getTime()) || isNaN(d2.getTime())) return 'Custom Range'

  const f1 = d1.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const f2 = d2.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  return `${f1} – ${f2}`
})

async function fetchActivity() {
  velocityLoading.value = true
  try {
    const params = { period: velocityPeriod.value }
    if (velocityPeriod.value === 'custom') {
      if (!velocityCustomStart.value || !velocityCustomEnd.value) {
        velocityLoading.value = false
        return
      }
      params.start_date = new Date(velocityCustomStart.value + 'T00:00:00').toISOString()
      params.end_date = new Date(velocityCustomEnd.value + 'T23:59:59').toISOString()
    }
    const res = await AnalyticsAPI.getActivity(params)
    activityData.value = res.data
  } catch (err) {
    uiStore.addToast('Failed to load activity data', 'error')
    console.error(err)
  } finally {
    velocityLoading.value = false
  }
}

async function fetchHistory() {
  try {
    const res = await AnalyticsAPI.getActivityHistory()
    activityHistory.value = res.data.history
  } catch (err) {
    console.error(err)
  }
}

const isHistoryEmpty = computed(() => {
  if (!activityHistory.value?.length) return true
  return activityHistory.value.every(
    (b) => (b.applications || 0) + (b.tasks || 0) + (b.replies || 0) === 0
  )
})

const isDailyBreakdownEmpty = computed(() => {
  if (!activityData.value?.daily_breakdown?.length) return true
  return activityData.value.daily_breakdown.every(
    (d) => (d.applications || 0) + (d.replies || 0) + (d.tasks || 0) === 0
  )
})

function setPeriod(period) {
  velocityPeriod.value = period
  isCustomPickerOpen.value = false
  fetchActivity()
}

function setWeekFromHistory(weekStart, weekEnd) {
  velocityPeriod.value = 'custom'
  velocityCustomStart.value = weekStart.split('T')[0]
  velocityCustomEnd.value = weekEnd.split('T')[0]
  tempRangeStart.value = velocityCustomStart.value
  tempRangeEnd.value = velocityCustomEnd.value
  fetchActivity()
}

function handleClickOutside(event) {
  if (customPickerRef.value && !customPickerRef.value.contains(event.target)) {
    isCustomPickerOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  fetchAnalytics()
  fetchActivity()
  fetchHistory()
})

import { onBeforeUnmount } from 'vue'

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
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
    <!-- Standardized Page Header (Centered) -->
    <PageHeader
      title="Market Intelligence & Analytics"
      subtitle="Comprehensive skill demand, salary benchmarks, and pipeline conversion metrics across your tracked applications."
      :icon="BarChart3"
      align="center"
    >
      <template #tabs>
        <div class="tab-switcher">
          <button
            :class="['tab-btn', currentTab === 'velocity' ? 'active' : '']"
            @click="currentTab = 'velocity'"
          >
            <Activity class="w-4 h-4" />
            Search Velocity & Activity
          </button>
          <button
            :class="['tab-btn', currentTab === 'market' ? 'active' : '']"
            @click="currentTab = 'market'"
          >
            <PieChart class="w-4 h-4" />
            Market Intelligence & Skills
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Main Content Area -->
    <div class="analytics-content">
      <div v-if="currentTab === 'velocity'" class="velocity-tab-container">
        <!-- Velocity Controls -->
        <div class="velocity-controls-card flex justify-between items-center mb-6">
          <div class="flex items-center gap-4">
            <span class="text-sm font-semibold text-secondary">Timeframe:</span>
            <div class="btn-group relative" ref="customPickerRef">
              <button :class="['btn-toggle', velocityPeriod === 'this_week' ? 'active' : '']" @click="setPeriod('this_week')">This Week</button>
              <button :class="['btn-toggle', velocityPeriod === 'last_week' ? 'active' : '']" @click="setPeriod('last_week')">Last Week</button>
              <button :class="['btn-toggle', velocityPeriod === 'this_month' ? 'active' : '']" @click="setPeriod('this_month')">This Month</button>
              <button :class="['btn-toggle', velocityPeriod === 'last_month' ? 'active' : '']" @click="setPeriod('last_month')">Last Month</button>
              <button
                :class="['btn-toggle', velocityPeriod === 'custom' ? 'active' : '']"
                @click="toggleCustomPicker"
              >
                <CalendarDays class="w-3.5 h-3.5 inline mr-1" />
                <span>{{ formattedCustomRange }}</span>
                <ChevronDown class="w-3.5 h-3.5 inline ml-1 opacity-70" />
              </button>

              <!-- Custom Range Calendar Popover -->
              <div v-if="isCustomPickerOpen" class="custom-range-popover animate-fade-in" @click.stop>
                <div class="popover-header">
                  <button class="nav-btn" type="button" @click="prevPickerMonth" title="Previous Month">
                    <ChevronLeft :size="16" />
                  </button>
                  <span class="month-year-label">{{ MONTH_NAMES[calendarViewMonth] }} {{ calendarViewYear }}</span>
                  <button class="nav-btn" type="button" @click="nextPickerMonth" title="Next Month">
                    <ChevronRight :size="16" />
                  </button>
                </div>

                <div class="days-header-row">
                  <span v-for="d in DAYS_OF_WEEK" :key="d" class="day-name">{{ d }}</span>
                </div>

                <div class="calendar-grid">
                  <button
                    v-for="(cell, idx) in pickerCalendarDays"
                    :key="idx"
                    type="button"
                    class="calendar-day-btn"
                    :class="{
                      'out-of-month': !cell.isCurrentMonth,
                      'is-today': cell.isToday,
                      'is-range-start': isDateSelectedStart(cell.ymd),
                      'is-range-end': isDateSelectedEnd(cell.ymd),
                      'in-range': isDateInRange(cell.ymd)
                    }"
                    @click="onDateClick(cell.ymd)"
                  >
                    {{ cell.day }}
                  </button>
                </div>

                <div class="popover-hint">
                  <span v-if="!tempRangeStart">Select start date</span>
                  <span v-else-if="!tempRangeEnd">Select end date</span>
                  <span v-else class="text-primary font-medium">{{ formattedCustomRange }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- History Ribbon -->
        <div class="history-ribbon-widget mb-6 relative overflow-hidden">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-sm font-bold text-main">12-Week Velocity History</h3>
            <span class="text-xs text-muted">Click a week to drill down</span>
          </div>
          <div v-if="isHistoryEmpty" class="flex flex-col items-center justify-center py-6 text-muted text-xs">
            <Activity :size="24" class="mb-2 opacity-40 text-secondary" />
            <span>No velocity activity recorded over the past 12 weeks.</span>
          </div>
          <div v-else class="ribbon-chart flex items-end gap-1 relative overflow-hidden">
            <div
              v-for="(bucket, idx) in activityHistory"
              :key="idx"
              class="ribbon-bar-container group cursor-pointer min-w-0"
              @click="setWeekFromHistory(bucket.week_start, bucket.week_end)"
            >
              <div class="ribbon-tooltip">
                <div class="font-bold mb-1">{{ bucket.week_start.split('T')[0] }}</div>
                <div>Apps: {{ bucket.applications || 0 }}</div>
                <div>Tasks: {{ bucket.tasks || 0 }}</div>
                <div>Replies: {{ bucket.replies || 0 }}</div>
              </div>
              <div class="ribbon-bar bg-primary" :style="{ height: `${Math.max(4, Math.min(50, ((bucket.applications || 0) + (bucket.tasks || 0) + (bucket.replies || 0)) * 2))}px` }"></div>
              <div class="ribbon-label font-mono text-[9px] text-muted mt-1 truncate max-w-full text-center leading-none">{{ bucket.week_start.split('-')[1] }}/{{ bucket.week_start.split('-')[2].substring(0,2) }}</div>
            </div>
          </div>
        </div>

        <div v-if="velocityLoading" class="loading-state py-10">
          <RefreshCw class="spin text-primary" :size="32" />
        </div>

        <div v-else-if="activityData">
          <!-- Metric Cards -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div class="velocity-kpi-card">
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs font-bold text-secondary uppercase tracking-wider">Applications</span>
                <div class="w-8 h-8 rounded-md bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
                  <Activity :size="16" />
                </div>
              </div>
              <div class="text-3xl font-extrabold text-main tracking-tight font-mono">{{ activityData.applications_submitted || 0 }}</div>
            </div>

            <div class="velocity-kpi-card">
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs font-bold text-secondary uppercase tracking-wider">Inbound Replies</span>
                <div class="w-8 h-8 rounded-md bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                  <Clock :size="16" />
                </div>
              </div>
              <div class="text-3xl font-extrabold text-main tracking-tight font-mono">{{ activityData.replies_received || 0 }}</div>
            </div>

            <div class="velocity-kpi-card">
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs font-bold text-secondary uppercase tracking-wider">Interviews Scheduled</span>
                <div class="w-8 h-8 rounded-md bg-purple-500/10 text-purple-500 flex items-center justify-center shrink-0">
                  <Target :size="16" />
                </div>
              </div>
              <div class="text-3xl font-extrabold text-main tracking-tight font-mono">{{ activityData.interviews_scheduled || 0 }}</div>
            </div>

            <div class="velocity-kpi-card">
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs font-bold text-secondary uppercase tracking-wider">Tasks Completed</span>
                <div class="w-8 h-8 rounded-md bg-amber-500/10 text-amber-500 flex items-center justify-center shrink-0">
                  <CheckCircle2 :size="16" />
                </div>
              </div>
              <div class="text-3xl font-extrabold text-main tracking-tight font-mono">{{ activityData.tasks_completed || 0 }}</div>
            </div>
          </div>

          <!-- Charts -->
          <div class="bento-grid" style="grid-template-columns: 2fr 1fr;">
            <!-- Daily Breakdown Chart -->
            <div class="bento-card relative overflow-hidden flex flex-col">
              <div class="bento-header flex items-center justify-between border-b border-border-color pb-3 mb-2">
                <h3 class="bento-title flex items-center gap-2 text-sm font-bold text-main">
                  <BarChart3 :size="16" class="text-primary" />
                  Activity Throughput
                </h3>
              </div>
              <div class="bento-body p-2 flex flex-col justify-between h-full">
                <div v-if="!activityData.daily_breakdown || activityData.daily_breakdown.length === 0 || isDailyBreakdownEmpty" class="flex flex-col items-center justify-center h-48 text-muted py-10">
                  <Activity :size="32" class="mb-3 opacity-40 text-secondary" />
                  <p class="text-xs font-medium">No activity recorded for this period.</p>
                </div>
                <div v-else class="h-full flex flex-col justify-between">
                  <div class="daily-chart-container flex items-end justify-between gap-1.5 h-44 px-2 relative overflow-hidden">
                    <div v-for="day in activityData.daily_breakdown" :key="day.date" class="daily-bar-wrap flex-1 flex flex-col justify-end items-center relative group min-w-0">
                      <div class="daily-tooltip">
                        <div class="font-bold border-b border-border-color mb-1 pb-1">{{ day.date }}</div>
                        <div class="text-blue-400">Apps: {{ day.applications || 0 }}</div>
                        <div class="text-emerald-400">Replies: {{ day.replies || 0 }}</div>
                        <div class="text-amber-400">Tasks: {{ day.tasks || 0 }}</div>
                      </div>

                      <div class="w-full max-w-[14px] flex flex-col items-center gap-[1px]">
                        <div class="w-full bg-blue-500 rounded-t-sm transition-all duration-200" :style="{ height: `${Math.min(70, (day.applications || 0) * 8)}px`, minHeight: day.applications ? '4px' : '0' }"></div>
                        <div class="w-full bg-emerald-500 rounded-sm transition-all duration-200" :style="{ height: `${Math.min(70, (day.replies || 0) * 8)}px`, minHeight: day.replies ? '4px' : '0' }"></div>
                        <div class="w-full bg-amber-500 rounded-sm transition-all duration-200" :style="{ height: `${Math.min(70, (day.tasks || 0) * 8)}px`, minHeight: day.tasks ? '4px' : '0' }"></div>
                      </div>

                      <span class="text-[9px] font-mono text-muted mt-2 truncate max-w-full text-center block leading-none">{{ day.date.substring(5) }}</span>
                    </div>
                  </div>

                  <div class="flex items-center justify-center gap-6 mt-4 pt-3 border-t border-border-color">
                    <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-blue-500"></span><span class="text-xs font-semibold text-secondary">Applications</span></div>
                    <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span><span class="text-xs font-semibold text-secondary">Replies</span></div>
                    <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span><span class="text-xs font-semibold text-secondary">Tasks</span></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Terminal Outcomes -->
            <div class="bento-card relative overflow-hidden flex flex-col">
              <div class="bento-header flex items-center justify-between border-b border-border-color pb-3 mb-2">
                <h3 class="bento-title flex items-center gap-2 text-sm font-bold text-main">
                  <Target :size="16" class="text-primary" />
                  Terminal Outcomes
                </h3>
              </div>
              <div class="bento-body p-2 flex flex-col justify-center h-full gap-3">
                <div class="flex items-center justify-between p-3 rounded-md bg-emerald-500/10 border border-emerald-500/20">
                  <span class="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                    <span class="w-2.5 h-2.5 bg-emerald-500 rounded-full shrink-0"></span>
                    Offer / Hired
                  </span>
                  <span class="px-2.5 py-1 rounded-full text-xs font-extrabold bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-mono min-w-[32px] text-center">
                    {{ (activityData.terminal_outcomes?.OFFER || 0) + (activityData.terminal_outcomes?.HIRED || 0) }}
                  </span>
                </div>

                <div class="flex items-center justify-between p-3 rounded-md bg-red-500/10 border border-red-500/20">
                  <span class="text-xs font-semibold text-red-600 dark:text-red-400 flex items-center gap-2">
                    <span class="w-2.5 h-2.5 bg-red-500 rounded-full shrink-0"></span>
                    Rejected
                  </span>
                  <span class="px-2.5 py-1 rounded-full text-xs font-extrabold bg-red-500/20 text-red-700 dark:text-red-300 font-mono min-w-[32px] text-center">
                    {{ activityData.terminal_outcomes?.REJECTED || 0 }}
                  </span>
                </div>

                <div class="flex items-center justify-between p-3 rounded-md bg-slate-500/10 border border-slate-500/20">
                  <span class="text-xs font-semibold text-slate-600 dark:text-slate-400 flex items-center gap-2">
                    <span class="w-2.5 h-2.5 bg-slate-500 rounded-full shrink-0"></span>
                    Withdrawn
                  </span>
                  <span class="px-2.5 py-1 rounded-full text-xs font-extrabold bg-slate-500/20 text-slate-700 dark:text-slate-300 font-mono min-w-[32px] text-center">
                    {{ activityData.terminal_outcomes?.WITHDRAWN || 0 }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="currentTab === 'market'">
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
  </div>
</template>

<style scoped>

/* Tab Switcher */
.tab-switcher {
  display: inline-flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  padding: 4px;
}
.tab-btn {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}
.tab-btn:hover:not(.active) {
  color: var(--text-main);
  background-color: var(--bg-elevated);
}
.tab-btn.active {
  background-color: var(--primary);
  color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Velocity Tab Specific Styles */
.velocity-controls-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.btn-group {
  display: inline-flex;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  overflow: hidden;
  padding: 2px;
}
.btn-toggle {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  background: transparent;
  border: none;
  border-radius: var(--radius-full);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}
.btn-toggle:hover {
  color: var(--text-main);
}
.btn-toggle.active {
  background-color: var(--primary);
  color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Custom Range Calendar Popover */
.custom-range-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 999;
  width: 280px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl, 0 10px 25px -5px rgba(0, 0, 0, 0.2));
  padding: 14px;
  box-sizing: border-box;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.month-year-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.nav-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast, 0.15s ease);
}

.nav-btn:hover {
  background-color: var(--bg-elevated);
  color: var(--text-main);
}

.days-header-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  margin-bottom: 6px;
}

.day-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.calendar-day-btn {
  background: none;
  border: 1px solid transparent;
  color: var(--text-main);
  font-size: 12px;
  font-weight: 500;
  height: 32px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast, 0.15s ease);
}

.calendar-day-btn:hover {
  background-color: var(--bg-elevated);
  border-color: var(--border-color);
}

.calendar-day-btn.out-of-month {
  color: var(--text-muted);
  opacity: 0.35;
}

.calendar-day-btn.is-today {
  font-weight: 700;
  border-color: var(--border-focus, var(--primary));
}

.calendar-day-btn.is-range-start,
.calendar-day-btn.is-range-end {
  background-color: var(--primary);
  color: #fff !important;
  font-weight: 700;
  border-color: var(--primary);
  border-radius: var(--radius-sm);
}

.calendar-day-btn.in-range {
  background-color: var(--primary-subtle, rgba(59, 130, 246, 0.15));
  color: var(--primary);
  border-radius: 0;
}

.popover-hint {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  text-align: center;
  color: var(--text-muted);
}

.animate-fade-in {
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.history-ribbon-widget {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  position: relative;
  overflow: hidden;
}
.ribbon-chart {
  height: 80px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 4px;
  position: relative;
  overflow: hidden;
}

.velocity-kpi-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  transition: transform var(--transition-fast, 0.15s ease), border-color var(--transition-fast, 0.15s ease);
}
.velocity-kpi-card:hover {
  border-color: var(--border-focus);
}
.ribbon-bar-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  position: relative;
  height: 100%;
}
.ribbon-bar {
  width: 100%;
  max-width: 24px;
  border-radius: 3px 3px 0 0;
  opacity: 0.7;
  transition: opacity 0.2s, background-color 0.2s;
}
.ribbon-bar-container:hover .ribbon-bar {
  opacity: 1;
  background-color: var(--primary-hover, var(--primary));
}
.ribbon-label {
  font-size: 9px;
  color: var(--text-muted);
  margin-top: 4px;
}
.ribbon-tooltip, .daily-tooltip {
  position: absolute;
  bottom: 100%;
  margin-bottom: 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px;
  font-size: 10px;
  color: var(--text-main);
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s;
  z-index: 10;
  white-space: nowrap;
}
.ribbon-bar-container:hover .ribbon-tooltip, .daily-bar-wrap:hover .daily-tooltip {
  opacity: 1;
  visibility: visible;
}


/* Velocity Charts */
.daily-chart-container {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}
.daily-bar-wrap {
  cursor: pointer;
  transition: opacity 0.2s;
}
.daily-bar-wrap:hover {
  opacity: 0.8;
}
/* Page Layout */
.page-container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 80px;
  min-height: calc(100vh - var(--navbar-height));
  width: 100%;
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
