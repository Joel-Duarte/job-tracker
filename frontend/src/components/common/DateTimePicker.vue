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
const selectedHour = ref('12')
const selectedMinute = ref('00')

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const DAYS_OF_WEEK = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

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

// Computed display text
const displayText = computed(() => {
  if (!props.modelValue) return ''
  try {
    const d = new Date(props.modelValue)
    if (isNaN(d.getTime())) return props.modelValue
    if (props.type === 'datetime') {
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
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

function clearValue(e) {
  if (e) e.stopPropagation()
  selectedDate.value = null
  emit('update:modelValue', '')
  emit('change', '')
  isOpen.value = false
}

function confirmSelection() {
  if (!selectedDate.value) {
    // If no date selected, default to today
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
    // Initialize temporary selection with current view date
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

    <!-- Calendar Popover Dropdown -->
    <div v-if="isOpen" class="datepicker-popover animate-fade-in" @click.stop>
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

      <!-- Time Selection (for type='datetime') -->
      <div v-if="type === 'datetime'" class="time-picker-row">
        <div class="time-label">
          <Clock :size="13" />
          <span>Time:</span>
        </div>
        <div class="time-inputs">
          <select v-model="selectedHour" class="time-select">
            <option v-for="h in 24" :key="h" :value="String(h - 1).padStart(2, '0')">
              {{ String(h - 1).padStart(2, '0') }}
            </option>
          </select>
          <span class="time-colon">:</span>
          <select v-model="selectedMinute" class="time-select">
            <option value="00">00</option>
            <option value="15">15</option>
            <option value="30">30</option>
            <option value="45">45</option>
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="40">40</option>
            <option value="50">50</option>
          </select>
        </div>
      </div>

      <!-- Action Footer with CONFIRM Button -->
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
          <Check :size="13" />
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
  z-index: 1050;
  width: 270px;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
  padding: 12px;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
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
  padding: 4px;
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
  margin-bottom: 4px;
}

.day-name {
  font-size: 10px;
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
  height: 30px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.calendar-day-btn:hover {
  background-color: var(--bg-elevated);
}

.calendar-day-btn.out-of-month {
  color: var(--text-muted);
  opacity: 0.35;
}

.calendar-day-btn.is-today {
  border-color: var(--primary);
  font-weight: 700;
}

.calendar-day-btn.is-selected {
  background-color: var(--primary);
  color: #ffffff;
  font-weight: 700;
}

/* Time Picker Section */
.time-picker-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  margin-top: 8px;
  border-top: 1px solid var(--border-color);
}

.time-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.time-inputs {
  display: flex;
  align-items: center;
  gap: 4px;
}

.time-select {
  padding: 3px 6px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  color: var(--text-main);
  font-family: var(--font-mono);
}

.time-colon {
  font-weight: 700;
  color: var(--text-secondary);
}

/* Popover Footer */
.popover-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
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
  padding: 5px 12px;
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
