<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { Calendar, Clock, ChevronLeft, ChevronRight, X, Check } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  type: {
    type: String,
    default: 'date', // 'date' | 'datetime'
  },
  placeholder: {
    type: String,
    default: 'Select date...',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const isOpen = ref(false)
const containerRef = ref(null)

// Current view year & month in calendar
const viewYear = ref(new Date().getFullYear())
const viewMonth = ref(new Date().getMonth()) // 0 - 11

// Temporary selection before confirming
const selectedDate = ref(null) // Date object
const selectedHour = ref('09') // '00' - '23'
const selectedMinute = ref('00') // '00' - '59'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const DAYS_OF_WEEK = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

const TIME_PRESETS_24H = [
  '09:00',
  '10:00',
  '11:30',
  '13:00',
  '14:00',
  '15:30',
  '17:00',
  '18:00',
  '23:59',
]

// Initialize from modelValue
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      const d = new Date(val)
      if (!isNaN(d.getTime())) {
        selectedDate.value = new Date(d.getFullYear(), d.getMonth(), d.getDate())
        viewYear.value = d.getFullYear()
        viewMonth.value = d.getMonth()
        if (props.type === 'datetime') {
          selectedHour.value = String(d.getHours()).padStart(2, '0')
          selectedMinute.value = String(d.getMinutes()).padStart(2, '0')
        }
      }
    } else {
      selectedDate.value = null
    }
  },
  { immediate: true }
)

// Computed display text in 24h format or localized
const displayText = computed(() => {
  if (!props.modelValue) return ''
  try {
    const d = new Date(props.modelValue)
    if (isNaN(d.getTime())) return props.modelValue
    if (props.type === 'datetime') {
      const y = d.getFullYear()
      const m = d.toLocaleString('en-US', { month: 'short' })
      const day = d.getDate()
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${m} ${day}, ${y} ${hh}:${mm}`
    }
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return props.modelValue
  }
})

// Calendar grid calculation
const calendarDays = computed(() => {
  const days = []
  const firstDayOfMonth = new Date(viewYear.value, viewMonth.value, 1).getDay()
  const daysInMonth = new Date(viewYear.value, viewMonth.value + 1, 0).getDate()
  const daysInPrevMonth = new Date(viewYear.value, viewMonth.value, 0).getDate()

  const today = new Date()
  const isCurrentMonth = today.getFullYear() === viewYear.value && today.getMonth() === viewMonth.value

  // Previous month trailing days
  for (let i = firstDayOfMonth - 1; i >= 0; i--) {
    const d = daysInPrevMonth - i
    days.push({
      day: d,
      month: viewMonth.value - 1,
      year: viewMonth.value === 0 ? viewYear.value - 1 : viewYear.value,
      isCurrentMonth: false,
      isToday: false,
      isSelected: false,
    })
  }

  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    const isToday = isCurrentMonth && today.getDate() === i
    const isSelected =
      selectedDate.value &&
      selectedDate.value.getFullYear() === viewYear.value &&
      selectedDate.value.getMonth() === viewMonth.value &&
      selectedDate.value.getDate() === i

    days.push({
      day: i,
      month: viewMonth.value,
      year: viewYear.value,
      isCurrentMonth: true,
      isToday,
      isSelected,
    })
  }

  // Next month leading days to complete grid (42 cells = 6 weeks)
  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    days.push({
      day: i,
      month: viewMonth.value + 1,
      year: viewMonth.value === 11 ? viewYear.value + 1 : viewYear.value,
      isCurrentMonth: false,
      isToday: false,
      isSelected: false,
    })
  }

  return days
})

function prevMonth() {
  if (viewMonth.value === 0) {
    viewMonth.value = 11
    viewYear.value--
  } else {
    viewMonth.value--
  }
}

function nextMonth() {
  if (viewMonth.value === 11) {
    viewMonth.value = 0
    viewYear.value++
  } else {
    viewMonth.value++
  }
}

function selectDay(cell) {
  selectedDate.value = new Date(cell.year, cell.month, cell.day)
  viewYear.value = cell.year
  viewMonth.value = cell.month
}

function applyPresetTime(timeStr) {
  const [hh, mm] = timeStr.split(':')
  selectedHour.value = hh
  selectedMinute.value = mm
}

function clearValue(e) {
  if (e) e.stopPropagation()
  selectedDate.value = null
  emit('update:modelValue', '')
  emit('change', '')
  isOpen.value = false
}

function confirmSelection() {
  if (!selectedDate.value) {
    selectedDate.value = new Date()
  }

  const y = selectedDate.value.getFullYear()
  const m = String(selectedDate.value.getMonth() + 1).padStart(2, '0')
  const d = String(selectedDate.value.getDate()).padStart(2, '0')

  let formattedValue = `${y}-${m}-${d}`

  if (props.type === 'datetime') {
    const hh = String(selectedHour.value).padStart(2, '0')
    const mm = String(selectedMinute.value).padStart(2, '0')
    formattedValue = `${y}-${m}-${d}T${hh}:${mm}`
  }

  emit('update:modelValue', formattedValue)
  emit('change', formattedValue)
  isOpen.value = false
}

function toggleOpen() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (isOpen.value && !selectedDate.value) {
    selectedDate.value = new Date()
    viewYear.value = selectedDate.value.getFullYear()
    viewMonth.value = selectedDate.value.getMonth()
  }
}

function handleClickOutside(e) {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="containerRef" class="custom-datepicker-container" :class="{ disabled }">
    <!-- Trigger Input Box -->
    <div class="datepicker-input-wrapper" @click="toggleOpen">
      <Calendar :size="14" class="input-icon" />
      <span v-if="displayText" class="input-value">{{ displayText }}</span>
      <span v-else class="input-placeholder">{{ placeholder }}</span>

      <button
        v-if="modelValue && !disabled"
        class="btn-clear"
        type="button"
        title="Clear date"
        @click="clearValue"
      >
        <X :size="13" />
      </button>
    </div>

    <!-- Popover Dropdown (Side-by-Side when type === 'datetime') -->
    <div
      v-if="isOpen"
      class="datepicker-popover animate-fade-in"
      :class="{ 'has-time-panel': type === 'datetime' }"
      @click.stop
    >
      <div class="popover-main-content">
        <!-- LEFT PANEL: Calendar Grid -->
        <div class="calendar-panel">
          <!-- Header with Month/Year Navigation -->
          <div class="popover-header">
            <button class="nav-btn" type="button" @click="prevMonth" title="Previous Month">
              <ChevronLeft :size="16" />
            </button>
            <span class="month-year-label">{{ MONTH_NAMES[viewMonth] }} {{ viewYear }}</span>
            <button class="nav-btn" type="button" @click="nextMonth" title="Next Month">
              <ChevronRight :size="16" />
            </button>
          </div>

          <!-- Days of Week Header -->
          <div class="days-header-row">
            <span v-for="d in DAYS_OF_WEEK" :key="d" class="day-name">{{ d }}</span>
          </div>

          <!-- Calendar Days Grid -->
          <div class="calendar-grid">
            <button
              v-for="(cell, idx) in calendarDays"
              :key="idx"
              type="button"
              class="calendar-day-btn"
              :class="{
                'out-of-month': !cell.isCurrentMonth,
                'is-today': cell.isToday,
                'is-selected': cell.isSelected,
              }"
              @click="selectDay(cell)"
            >
              {{ cell.day }}
            </button>
          </div>
        </div>

        <!-- RIGHT PANEL: 24-Hour Time Picker (rendered side-by-side) -->
        <div v-if="type === 'datetime'" class="time-panel">
          <div class="time-panel-header">
            <Clock :size="13" class="time-icon" />
            <span class="time-title">Time (24h)</span>
          </div>

          <!-- Time Spinners / Selectors -->
          <div class="time-selectors-row">
            <div class="time-select-block">
              <span class="time-unit-label">Hour</span>
              <select v-model="selectedHour" class="time-select-24">
                <option v-for="h in 24" :key="h" :value="String(h - 1).padStart(2, '0')">
                  {{ String(h - 1).padStart(2, '0') }}
                </option>
              </select>
            </div>

            <span class="time-separator">:</span>

            <div class="time-select-block">
              <span class="time-unit-label">Min</span>
              <select v-model="selectedMinute" class="time-select-24">
                <option value="00">00</option>
                <option value="05">05</option>
                <option value="10">10</option>
                <option value="15">15</option>
                <option value="20">20</option>
                <option value="25">25</option>
                <option value="30">30</option>
                <option value="35">35</option>
                <option value="40">40</option>
                <option value="45">45</option>
                <option value="50">50</option>
                <option value="55">55</option>
              </select>
            </div>
          </div>

          <!-- Quick Time Presets List -->
          <div class="presets-section">
            <span class="presets-label">Presets</span>
            <div class="presets-grid">
              <button
                v-for="timeStr in TIME_PRESETS_24H"
                :key="timeStr"
                type="button"
                class="preset-time-chip"
                :class="{ active: selectedHour + ':' + selectedMinute === timeStr }"
                @click="applyPresetTime(timeStr)"
              >
                {{ timeStr }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Footer with CONFIRM Button spanning full width -->
      <div class="popover-footer">
        <button
          class="btn-footer-clear"
          type="button"
          @click="clearValue"
        >
          Clear
        </button>
        <button
          class="btn-footer-confirm"
          type="button"
          @click="confirmSelection"
        >
          <Check :size="14" />
          <span>Confirm</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-datepicker-container {
  position: relative;
  width: 100%;
}

.datepicker-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-main);
  transition: all var(--transition-fast);
  min-height: 38px;
}

.datepicker-input-wrapper:hover {
  border-color: var(--primary);
}

.input-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.input-value {
  flex: 1;
  font-weight: 500;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 12px;
}

.input-placeholder {
  flex: 1;
  color: var(--text-muted);
}

.btn-clear {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  border-radius: 4px;
  transition: all var(--transition-fast);
}

.btn-clear:hover {
  color: var(--text-main);
  background-color: var(--bg-elevated);
}

/* Popover Dropdown */
.datepicker-popover {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 9999;
  width: 280px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 14px 35px rgba(0, 0, 0, 0.45);
  padding: 14px;
  box-sizing: border-box;
}

.datepicker-popover.has-time-panel {
  width: 440px;
  max-width: calc(100vw - 32px);
}

.popover-main-content {
  display: flex;
  gap: 14px;
}

/* Left Panel: Calendar */
.calendar-panel {
  flex: 1;
  min-width: 0;
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
  transition: all var(--transition-fast);
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
  gap: 3px;
}

.calendar-day-btn {
  background: none;
  border: 1px solid transparent;
  color: var(--text-main);
  font-size: 12px;
  font-weight: 500;
  height: 30px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.calendar-day-btn:hover {
  background-color: var(--bg-elevated);
  border-color: var(--border-color);
}

.calendar-day-btn.out-of-month {
  color: var(--text-muted);
  opacity: 0.3;
}

.calendar-day-btn.is-today {
  border-color: var(--primary);
  font-weight: 700;
}

.calendar-day-btn.is-selected {
  background-color: var(--primary);
  color: #ffffff;
  font-weight: 700;
  border-color: var(--primary);
}

/* Right Panel: Time (24h Standard) */
.time-panel {
  width: 140px;
  border-left: 1px solid var(--border-color);
  padding-left: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.time-panel-header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.time-icon {
  color: var(--primary);
}

.time-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
}

.time-selectors-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-elevated);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.time-select-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.time-unit-label {
  font-size: 9px;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--text-muted);
}

.time-select-24 {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 3px 5px;
  font-size: 13px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-main);
  cursor: pointer;
}

.time-separator {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-top: 10px;
}

.presets-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.presets-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}

.preset-time-chip {
  padding: 3px 2px;
  font-size: 10px;
  font-weight: 600;
  font-family: var(--font-mono);
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  text-align: center;
  transition: all var(--transition-fast);
}

.preset-time-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.preset-time-chip.active {
  background-color: var(--primary);
  color: #ffffff;
  border-color: var(--primary);
}

/* Popover Footer */
.popover-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

.btn-footer-clear {
  background: none;
  border: none;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all var(--transition-fast);
}

.btn-footer-clear:hover {
  color: var(--text-main);
  background-color: var(--bg-elevated);
}

.btn-footer-confirm {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  background-color: var(--primary);
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-footer-confirm:hover {
  background-color: var(--primary-hover);
  transform: translateY(-1px);
}
</style>
