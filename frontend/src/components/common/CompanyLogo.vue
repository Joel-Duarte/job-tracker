<script setup>
import { ref, computed, watch } from 'vue'
import { Building2 } from 'lucide-vue-next'
import { getCompanyFaviconUrl } from '../../utils/formatters'

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

const faviconUrl = computed(() => {
  if (!props.name && !props.domain) return null
  return getCompanyFaviconUrl(props.name, props.domain, 64)
})

watch(
  () => [props.name, props.domain],
  () => {
    hasError.value = false
    isLoaded.value = false
  }
)

function handleError() {
  hasError.value = true
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
