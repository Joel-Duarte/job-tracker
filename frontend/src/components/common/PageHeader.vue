<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  icon: {
    type: [Object, Function],
    default: null,
  },
  badge: {
    type: String,
    default: '',
  },
  align: {
    type: String,
    default: 'center', // 'left' | 'center'
  },
  borderBottom: {
    type: Boolean,
    default: false,
  },
})
</script>

<template>
  <div
    class="page-header"
    :class="[
      `align-${align}`,
      { 'has-border': borderBottom }
    ]"
  >
    <div class="header-main">
      <div class="header-text-block">
        <!-- Badge -->
        <div v-if="badge || $slots.badge" class="header-badge-row">
          <slot name="badge">
            <span class="header-badge">{{ badge }}</span>
          </slot>
        </div>

        <!-- Title Row -->
        <h1 class="page-title">
          <component :is="icon" v-if="icon" class="title-icon text-primary" :size="22" />
          <span>{{ title }}</span>
        </h1>

        <!-- Subtitle -->
        <p v-if="subtitle || $slots.subtitle" class="page-subtitle">
          <slot name="subtitle">{{ subtitle }}</slot>
        </p>
      </div>

      <!-- Right Actions Slot (if left-aligned) -->
      <div v-if="$slots.actions" class="header-actions">
        <slot name="actions"></slot>
      </div>
    </div>

    <!-- Bottom / Tabs Slot (e.g. Centered Tab Bar) -->
    <div v-if="$slots.tabs || $slots.default" class="header-extra">
      <slot name="tabs"></slot>
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 24px;
  width: 100%;
}

.page-header.has-border {
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.header-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

/* Left Alignment (Default) */
.page-header.align-left .header-text-block {
  flex: 1;
  min-width: 260px;
  text-align: left;
}

.page-header.align-left .page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: flex-start;
}

/* Centered Alignment */
.page-header.align-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.page-header.align-center .header-main {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  text-align: center;
}

.page-header.align-center .header-text-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
}

.page-header.align-center .page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  text-align: center;
  width: 100%;
}

.page-header.align-center .page-subtitle {
  text-align: center;
  width: 100%;
}

.page-header.align-center .header-badge-row {
  display: flex;
  justify-content: center;
  width: 100%;
}

/* Badges */
.header-badge-row {
  margin-bottom: 8px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background-color: var(--status-offer-bg);
  color: var(--text-success);
  border: 1px solid var(--status-offer-border);
  font-size: 11px;
  font-weight: 600;
}

/* Typography */
.page-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 24px;
  color: var(--text-main);
  letter-spacing: var(--font-tracking);
  margin: 0 0 4px 0;
  line-height: 1.25;
}

.title-icon {
  flex-shrink: 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.page-header.align-center .page-subtitle {
  margin-top: 4px;
}

/* Actions Slot */
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Extra / Tabs Slot */
.header-extra {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  width: 100%;
}

.page-header.align-left .header-extra {
  justify-content: flex-start;
}
</style>
