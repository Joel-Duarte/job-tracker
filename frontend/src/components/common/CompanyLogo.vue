<script setup>
import { unref, ref, computed, watch } from 'vue'
import { Building2 } from 'lucide-vue-next'
import { getCompanyDomain } from '../../utils/formatters'

const props = defineProps({
  name: {
    type: String,
    default: ''
  },
  domain: {
    type: String,
    default: null
  },
  size: {
    type: Number,
    default: 20
  },
  rounded: {
    type: Boolean,
    default: true
  }
})

const hasError = ref(false)
const isLoaded = ref(false)
const attemptIndex = ref(0)

const candidateDomains = computed(() => {
  const list = []
  const rawDomain = getCompanyDomain(props.name, props.domain)
  const clean = String(unref(rawDomain) || '')
  if (clean) {
    list.push(clean)
    if (!clean.startsWith('www.')) {
      list.push(`www.${clean}`)
    } else {
      list.push(clean.replace(/^www\./, ''))
    }
  }
  return Array.from(new Set(list))
})

const faviconUrl = computed(() => {
  if (attemptIndex.value >= candidateDomains.value.length) return null
  const domain = candidateDomains.value[attemptIndex.value]
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`
})

watch(
  () => [props.name, props.domain],
  () => {
    hasError.value = false
    isLoaded.value = false
    attemptIndex.value = 0
  }
)

function handleError() {
  if (attemptIndex.value + 1 < candidateDomains.value.length) {
    attemptIndex.value += 1
    isLoaded.value = false
  } else {
    hasError.value = true
  }
}

function handleLoad() {
  isLoaded.value = true
}

const fallbackInitial = computed(() => {
  if (!props.name) return ''
  return props.name.trim().charAt(0).toUpperCase()
})
</script>

<template>
  <div
    class="company-logo-badge"
    :class="{ 'is-rounded': rounded }"
    :style="{
      width: `${size}px`,
      height: `${size}px`,
      minWidth: `${size}px`,
      minHeight: `${size}px`
    }"
  >
    <img
      v-if="faviconUrl && !hasError"
      :src="faviconUrl"
      :alt="name"
      class="company-favicon-img"
      :class="{ 'opacity-0': !isLoaded }"
      @load="handleLoad"
      @error="handleError"
    />
    <div v-else class="company-logo-fallback">
      <span v-if="fallbackInitial" class="fallback-char" :style="{ fontSize: `${Math.max(9, Math.round(size * 0.55))}px` }">
        {{ fallbackInitial }}
      </span>
      <Building2 v-else :size="Math.round(size * 0.65)" class="fallback-icon" />
    </div>
  </div>
</template>

<style scoped>
.company-logo-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.company-logo-badge.is-rounded {
  border-radius: 6px;
}

.company-favicon-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 2px;
  transition: opacity var(--transition-fast);
}

.company-logo-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-elevated);
  color: var(--text-secondary);
}

.fallback-char {
  font-family: var(--font-heading);
  font-weight: 700;
  line-height: 1;
  color: var(--primary);
}

.fallback-icon {
  color: var(--text-muted);
}
</style>
