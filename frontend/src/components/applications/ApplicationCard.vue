<script setup>
import { computed } from 'vue'
import CompanyLogo from '../common/CompanyLogo.vue'
import {
  formatRelativeDate,
  normalizeWorkModel,
  formatSalaryRange,
} from '../../utils/formatters'
import {
  Sparkles,
  BookOpen,
  MoreHorizontal,
  SlidersHorizontal,
  Calendar,
  CheckCircle2,
  Clock,
  Trophy,
  Ban,
} from 'lucide-vue-next'

const props = defineProps({
  app: {
    type: Object,
    required: true,
  },
  draggedApp: {
    type: Object,
    default: null,
  },
  activeMenuApp: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits([
  'dragstart',
  'dragend',
  'click',
  'match-click',
  'guide-click',
  'reader-click',
  'toggle-menu',
  'transition-modal',
  'execute-transition',
  'quick-withdraw',
])

function getAppMatchScore(app) {
  if (!app) return null
  if (app.match_score !== undefined && app.match_score !== null) {
    return Number(app.match_score)
  }
  const payload = app.match_analysis_payload || {}
  const score = payload.match_score ?? payload.fit_score ?? payload.overall_fit_score
  if (score !== undefined && score !== null) {
    return Number(score)
  }
  return null
}

function getMatchScoreTierClass(score) {
  if (score === null || score === undefined) return ''
  const num = Number(score)
  if (num > 80) return 'match-tier-elite'
  if (num >= 60) return 'match-tier-high'
  if (num >= 40) return 'match-tier-medium'
  return 'match-tier-low'
}

function getAppSubPhaseLabel(app) {
  if (!app) return ''
  const status = app.status || 'APPLIED'
  const payload = app.latest_event?.raw_payload || {}

  if (status === 'TECHNICAL_INTERVIEW') {
    return payload.interview_stage || 'Interview Requested / Scheduling'
  }
  if (status === 'OFFER') {
    const sal = payload.offered_salary || app.job_posting?.salary_max || app.job_posting?.salary_min
    const curr = payload.currency || 'USD'
    return sal ? `$${Number(sal).toLocaleString()} ${curr}` : 'Offer Package'
  }
  if (status === 'REJECTED') {
    return payload.rejection_reason || 'Rejection Notice'
  }
  if (status === 'ASSESSMENT') return 'AI Assessment'
  return 'Applied'
}

function getScheduledInterviewDate(app) {
  if (!app) return null
  if (app.scheduled_interview_at) return app.scheduled_interview_at
  const payload = app.latest_event?.raw_payload || {}
  if (payload.scheduled_at) return payload.scheduled_at
  if (app.status === 'TECHNICAL_INTERVIEW') {
    if (app.nearest_due_date) return app.nearest_due_date
    for (const act of app.action_items || []) {
      if (act.due_date && String(act.title).toLowerCase().includes('interview')) {
        return act.due_date
      }
    }
  }
  return null
}

function getAppMetadataLine(app) {
  if (!app) return ''
  const parts = []
  const salary = formatSalaryRange(app.salary_min, app.salary_max, app.currency)
  if (salary) parts.push(salary)

  const loc = app.location || app.match_analysis_payload?.location
  if (loc) parts.push(loc)

  const wm = normalizeWorkModel(app.work_model || app.match_analysis_payload?.work_model)
  if (wm) parts.push(wm)

  return parts.join(' · ')
}

function formatScheduledDateFriendly(app) {
  const dateStr = getScheduledInterviewDate(app)
  if (!dateStr) return ''
  return formatRelativeDate(dateStr, true)
}

function getScheduleUrgencyClass(app) {
  const dateStr = getScheduledInterviewDate(app)
  if (!dateStr) return 'date-yellow'
  try {
    const schedTime = new Date(dateStr).getTime()
    const nowTime = Date.now()
    const diffHours = (schedTime - nowTime) / (1000 * 60 * 60)
    if (diffHours >= 72) return 'date-green'
    if (diffHours > 24) return 'date-yellow'
    return 'date-red'
  } catch {
    return 'date-yellow'
  }
}

function getDueDateStr(app) {
  if (!app) return null
  const payload = app.latest_event?.raw_payload || {}
  return app.nearest_due_date || payload.decision_deadline || payload.due_date || null
}

function formatDueDateFriendly(app) {
  const dateStr = getDueDateStr(app)
  if (!dateStr) return ''
  return formatRelativeDate(dateStr, false)
}

function isOverdue(app) {
  const dateStr = getDueDateStr(app)
  if (!dateStr) return false
  try {
    return new Date(dateStr).getTime() < Date.now()
  } catch {
    return false
  }
}
</script>

<template>
  <div
    class="application-card"
    :class="[{ 'is-dragging': draggedApp?.id === app.id, 'has-open-menu': activeMenuApp?.id === app.id }, app.has_action_required ? 'action-required-card' : '']"
    draggable="true"
    @dragstart="emit('dragstart', app, $event)"
    @dragend="emit('dragend')"
    @click="emit('click', app.id)"
  >
    <div class="card-header">
      <div class="company-name-tag">
        <CompanyLogo :name="app.company?.name" :domain="app.company?.domain" :size="18" />
        <span class="company-name-text">{{ app.company?.name || 'Company' }}</span>
      </div>

      <div class="card-header-actions" @click.stop>
        <div class="card-hover-actions">
          <!-- Assessment Button -->
          <button
            v-if="getAppMatchScore(app) !== null"
            class="match-score-pill"
            :class="getMatchScoreTierClass(getAppMatchScore(app))"
            :title="`Role Match Fit: ${getAppMatchScore(app)}% - View Assessment`"
            @click="emit('match-click', app.id)"
          >
            <Sparkles :size="10" class="match-pill-icon" />
            <span>{{ getAppMatchScore(app) }}%</span>
          </button>
          <button
            v-else
            class="card-hover-icon-btn"
            title="View Assessment"
            @click="emit('match-click', app.id)"
          >
            <Sparkles :size="12" />
          </button>

          <!-- Interview Guide Button -->
          <button
            class="card-hover-icon-btn"
            :class="{ 'has-guide': app.has_interview_guide }"
            :title="app.has_interview_guide ? 'Open Interview Guide Reader' : 'Generate Interview Guide'"
            @click="app.has_interview_guide ? emit('reader-click', app.id) : emit('guide-click', app.id)"
          >
            <BookOpen :size="12" />
          </button>
        </div>

        <!-- Card Context Menu Trigger -->
        <div class="card-menu-container">
          <button
            class="card-menu-trigger"
            :class="{ active: activeMenuApp?.id === app.id }"
            title="More actions"
            @click="emit('toggle-menu', app, $event)"
          >
            <MoreHorizontal :size="14" />
          </button>
        </div>
      </div>
    </div>

    <!-- Position Title -->
    <div class="card-position">
      {{ app.position || 'Position Not Specified' }}
    </div>

    <!-- Mid-Dot Metadata Line -->
    <div v-if="getAppMetadataLine(app)" class="card-meta-line" @click.stop>
      {{ getAppMetadataLine(app) }}
    </div>

    <!-- Phase Detail Pill, Interview Date, & Due Date -->
    <div
      v-if="app.status !== 'APPLIED' || getScheduledInterviewDate(app) || getDueDateStr(app)"
      class="card-phase-row"
      @click.stop
    >
      <button
        v-if="app.status !== 'APPLIED'"
        class="phase-detail-btn"
        :class="`phase-${(app.status || 'applied').toLowerCase()}`"
        @click="emit('transition-modal', app, app.status)"
        :title="`Click to edit stage: ${getAppSubPhaseLabel(app)}`"
      >
        <span class="phase-detail-text">{{ getAppSubPhaseLabel(app) }}</span>
        <SlidersHorizontal :size="11" class="phase-icon" />
      </button>

      <div
        v-if="getScheduledInterviewDate(app)"
        class="interview-scheduled-badge"
        :class="getScheduleUrgencyClass(app)"
        title="Scheduled Interview Date & Time"
      >
        <Calendar :size="11" />
        <span>{{ formatScheduledDateFriendly(app) }}</span>
      </div>

      <div
        v-else-if="app.status === 'TECHNICAL_INTERVIEW' && getAppSubPhaseLabel(app) === 'Task Completed / Awaiting Response'"
        class="awaiting-response-tag"
        title="Action item completed - Awaiting company response"
      >
        <CheckCircle2 :size="11" />
        <span>Awaiting Reply</span>
      </div>

      <button
        v-else-if="app.status === 'TECHNICAL_INTERVIEW'"
        class="scheduling-needed-tag"
        @click="emit('transition-modal', app, 'TECHNICAL_INTERVIEW')"
        title="No interview date scheduled yet - Click to schedule"
      >
        <Clock :size="11" />
        <span>⚡ Schedule</span>
      </button>

      <div
        v-if="!getScheduledInterviewDate(app) && getDueDateStr(app)"
        class="due-date-tag"
        :class="{ overdue: isOverdue(app) }"
        :title="`Task Deadline: ${formatDueDateFriendly(app)}`"
      >
        <Clock :size="11" />
        <span>Due {{ formatDueDateFriendly(app) }}</span>
      </div>
    </div>

    <!-- Latest Event Summary Note -->
    <div v-if="app.latest_event?.email_summary" class="card-summary">
      <span class="summary-prefix">{{ app.latest_event.email_event_type }}:</span>
      {{ app.latest_event.email_summary }}
    </div>

    <!-- Offer Actions -->
    <div v-if="app.status === 'OFFER'" class="offer-actions" @click.stop>
      <button
        class="offer-action-btn btn-hired"
        @click="emit('execute-transition', app.id, { status: 'HIRED' })"
        title="Accept Offer & Mark Hired"
      >
        <Trophy :size="12" />
        <span>Hired</span>
      </button>
      <button
        class="offer-action-btn btn-withdrawn"
        @click="emit('quick-withdraw', app)"
        title="Decline Offer & Withdraw"
      >
        <Ban :size="12" />
        <span>Decline</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.application-card {
  background-color: var(--bg-card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
  padding: 12px;
  cursor: grab;
  transition: all var(--transition-fast);
  box-shadow: var(--card-shadow);
  position: relative;
}

.application-card:active {
  cursor: grabbing;
}

.application-card.has-open-menu {
  z-index: 50;
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
}

.application-card:hover {
  background-color: var(--bg-card-hover);
  border-color: var(--card-hover-border);
  transform: translateY(-2px);
  box-shadow: var(--card-hover-shadow);
}

.application-card.is-dragging {
  opacity: 0.4;
  transform: scale(0.98);
  border-style: dashed;
}

.action-required-card {
  border-left: 3px solid var(--status-rejected-border);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  position: relative;
}

.company-name-tag {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  min-width: 0;
  overflow: hidden;
}

.company-name-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-header-actions {
  display: flex;
  align-items: center;
  gap: 5px;
}

.card-hover-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 1;
  pointer-events: auto;
}

.card-hover-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.card-hover-icon-btn:hover {
  background-color: var(--bg-surface);
  color: var(--primary);
  border-color: var(--border-subtle);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.card-hover-icon-btn.has-guide {
  color: var(--primary);
}

.card-menu-container {
  position: relative;
  display: inline-flex;
}

.card-menu-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0.5;
  transition: all var(--transition-fast);
}

.application-card:hover .card-menu-trigger,
.card-menu-trigger.active {
  opacity: 1;
}

.card-menu-trigger:hover,
.card-menu-trigger.active {
  background-color: var(--bg-surface);
  color: var(--text-main);
  border-color: var(--border-subtle);
}

.card-position {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 3px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta-line {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.card-phase-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.phase-detail-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  cursor: pointer;
  transition: all var(--transition-fast);
  max-width: 190px;
}

.phase-detail-btn:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.phase-detail-btn.phase-applied { color: var(--status-applied-text); border-color: var(--status-applied-border); background-color: var(--status-applied-bg); }
.phase-detail-btn.phase-interview, .phase-detail-btn.phase-technical_interview { color: var(--status-interview-text); border-color: var(--status-interview-border); background-color: var(--status-interview-bg); }
.phase-detail-btn.phase-offer { color: var(--status-offer-text); border-color: var(--status-offer-border); background-color: var(--status-offer-bg); }
.phase-detail-btn.phase-rejected { color: var(--status-rejected-text); border-color: var(--status-rejected-border); background-color: var(--status-rejected-bg); }
.phase-detail-btn.phase-assessment { color: var(--status-assessment-text); border-color: var(--status-assessment-border); background-color: var(--status-assessment-bg); }

.phase-detail-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.phase-icon {
  opacity: 0.7;
  flex-shrink: 0;
}

.interview-scheduled-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  font-family: var(--font-mono);
  user-select: none;
}

.interview-scheduled-badge.date-green {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
}

.interview-scheduled-badge.date-yellow {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
}

.interview-scheduled-badge.date-red {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border: 1px solid var(--status-rejected-border);
}

.awaiting-response-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
}

.scheduling-needed-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.scheduling-needed-tag:hover {
  background-color: var(--status-interview-border);
  border-color: var(--status-interview-text);
  transform: translateY(-1px);
}

.due-date-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border: 1px solid var(--status-interview-border);
  font-family: var(--font-mono);
}

.due-date-tag.overdue {
  background-color: var(--status-rejected-bg);
  color: var(--status-rejected-text);
  border-color: var(--status-rejected-border);
}

.card-summary {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.summary-prefix {
  font-weight: 600;
  color: var(--text-main);
  margin-right: 4px;
}

.offer-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border-subtle);
}

.offer-action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 0;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.btn-hired {
  background-color: rgba(250, 204, 21, 0.1);
  color: hsl(45 90% 50%);
  border-color: rgba(250, 204, 21, 0.2);
}

.btn-hired:hover {
  background-color: rgba(250, 204, 21, 0.2);
  border-color: rgba(250, 204, 21, 0.4);
}

.btn-withdrawn {
  background-color: rgba(251, 146, 60, 0.1);
  color: hsl(28 90% 60%);
  border-color: rgba(251, 146, 60, 0.2);
}

.btn-withdrawn:hover {
  background-color: rgba(251, 146, 60, 0.2);
  border-color: rgba(251, 146, 60, 0.4);
}

.match-score-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  border: 1px solid transparent;
  font-family: var(--font-mono);
  white-space: nowrap;
}

.match-score-pill.match-tier-elite {
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border-color: var(--status-offer-border);
}

.match-score-pill.match-tier-high {
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border-color: var(--status-applied-border);
}

.match-score-pill.match-tier-medium {
  background-color: var(--status-interview-bg);
  color: var(--status-interview-text);
  border-color: var(--status-interview-border);
}

.match-score-pill.match-tier-low {
  background-color: var(--bg-surface);
  color: var(--text-muted);
  border-color: var(--border-color);
}
</style>
