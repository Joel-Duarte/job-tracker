import { ref } from 'vue'

export const displayTimezone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC')

export function formatEmailInstant(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Time requires review'
  return new Intl.DateTimeFormat(undefined, {
    timeZone: displayTimezone.value, dateStyle: 'medium', timeStyle: 'short', hourCycle: 'h23',
  }).format(date)
}

export function toEmailLocalDatetime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: displayTimezone.value, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date).map(({ type, value: part }) => [type, part]))
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`
}
