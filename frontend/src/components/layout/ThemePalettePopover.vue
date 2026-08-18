<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useUIStore } from '../../stores/uiStore'
import {
  Palette,
  Sun,
  Moon,
  RotateCcw,
  X,
  Sparkles,
} from 'lucide-vue-next'

const uiStore = useUIStore()
const popoverRef = ref(null)

function handleClickOutside(event) {
  if (uiStore.isThemePopoverOpen) {
    // If click target is inside popover or inside the navbar theme toggle button, do not close here
    if (
      popoverRef.value &&
      (popoverRef.value.contains(event.target) || event.target.closest('.theme-toggle'))
    ) {
      return
    }
    uiStore.closeThemePopover()
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape' && uiStore.isThemePopoverOpen) {
    uiStore.closeThemePopover()
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <transition name="popover-fade">
    <div
      v-if="uiStore.isThemePopoverOpen"
      ref="popoverRef"
      class="theme-palette-popover"
    >
      <!-- Popover Header -->
      <div class="popover-header">
        <div class="header-title-group">
          <Palette :size="16" class="text-primary" />
          <span class="header-title">Theme &amp; Palette Studio</span>
        </div>
        <button
          type="button"
          class="btn-close-popover"
          @click="uiStore.closeThemePopover"
          title="Close"
        >
          <X :size="14" />
        </button>
      </div>

      <!-- Segmented Mode Switcher -->
      <div class="theme-switch-row">
        <button
          type="button"
          class="theme-mode-btn"
          :class="{ active: uiStore.theme === 'midnight' }"
          @click="uiStore.setTheme('midnight')"
        >
          <Moon :size="14" />
          <span>Midnight (Dark)</span>
        </button>
        <button
          type="button"
          class="theme-mode-btn"
          :class="{ active: uiStore.theme === 'daylight' }"
          @click="uiStore.setTheme('daylight')"
        >
          <Sun :size="14" />
          <span>Daylight (Warm)</span>
        </button>
      </div>

      <!-- Popover Scrollable Customizer Body -->
      <div class="popover-body">
        <!-- 1. Canvas Background -->
        <div class="popover-section">
          <div class="section-label-row">
            <span class="section-label">1. Canvas Background</span>
            <span class="token-name font-mono">--bg-app</span>
          </div>

          <!-- Midnight Swatches -->
          <div v-if="uiStore.theme === 'midnight'" class="swatches-grid">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customDarkBg || uiStore.customDarkBg === '#000000' }"
              title="OLED Pure Black"
              @click="uiStore.resetCustomColor('midnight', 'bg')"
            >
              <span class="swatch-preview" style="background-color: #000000;"></span>
              <span class="swatch-name">OLED Black</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkBg === '#12161f' }"
              title="Slate Gunmetal"
              @click="uiStore.setCustomColor('midnight', 'bg', '#12161f')"
            >
              <span class="swatch-preview" style="background-color: #12161f;"></span>
              <span class="swatch-name">Gunmetal</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkBg === '#0a1120' }"
              title="Midnight Navy"
              @click="uiStore.setCustomColor('midnight', 'bg', '#0a1120')"
            >
              <span class="swatch-preview" style="background-color: #0a1120;"></span>
              <span class="swatch-name">Navy</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkBg === '#0d1117' }"
              title="GitHub Dark"
              @click="uiStore.setCustomColor('midnight', 'bg', '#0d1117')"
            >
              <span class="swatch-preview" style="background-color: #0d1117;"></span>
              <span class="swatch-name">Carbon</span>
            </button>
          </div>

          <!-- Daylight Swatches -->
          <div v-else class="swatches-grid">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customLightBg || uiStore.customLightBg === '#f5ede3' }"
              title="Studio Parchment"
              @click="uiStore.resetCustomColor('daylight', 'bg')"
            >
              <span class="swatch-preview" style="background-color: #f5ede3; border: 1px solid #dcd1c4;"></span>
              <span class="swatch-name">Parchment</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightBg === '#faf8f5' }"
              title="Warm Linen"
              @click="uiStore.setCustomColor('daylight', 'bg', '#faf8f5')"
            >
              <span class="swatch-preview" style="background-color: #faf8f5; border: 1px solid #e0d8ce;"></span>
              <span class="swatch-name">Linen</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightBg === '#f0f4f8' }"
              title="Cool Frost"
              @click="uiStore.setCustomColor('daylight', 'bg', '#f0f4f8')"
            >
              <span class="swatch-preview" style="background-color: #f0f4f8; border: 1px solid #d0dbe5;"></span>
              <span class="swatch-name">Frost</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightBg === '#ffffff' }"
              title="Pure Minimal White"
              @click="uiStore.setCustomColor('daylight', 'bg', '#ffffff')"
            >
              <span class="swatch-preview" style="background-color: #ffffff; border: 1px solid #e5e5e5;"></span>
              <span class="swatch-name">Pure White</span>
            </button>
          </div>

          <!-- Custom Color Picker Input -->
          <div class="custom-picker-row">
            <input
              type="color"
              class="color-input"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBg || '#000000') : (uiStore.customLightBg || '#f5ede3')"
              @input="e => uiStore.setCustomColor(uiStore.theme, 'bg', e.target.value)"
            />
            <input
              type="text"
              class="hex-text-input font-mono"
              placeholder="#HEX"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBg || '#000000') : (uiStore.customLightBg || '#f5ede3')"
              @change="e => uiStore.setCustomColor(uiStore.theme, 'bg', e.target.value)"
            />
            <button
              v-if="(uiStore.theme === 'midnight' && uiStore.customDarkBg) || (uiStore.theme === 'daylight' && uiStore.customLightBg)"
              type="button"
              class="btn-reset-token"
              title="Reset to default"
              @click="uiStore.resetCustomColor(uiStore.theme, 'bg')"
            >
              <RotateCcw :size="11" />
            </button>
          </div>
        </div>

        <!-- 2. Surface & Cards Background -->
        <div class="popover-section">
          <div class="section-label-row">
            <span class="section-label">2. Surface &amp; Cards</span>
            <span class="token-name font-mono">--bg-surface</span>
          </div>

          <!-- Midnight Surface Swatches -->
          <div v-if="uiStore.theme === 'midnight'" class="swatches-grid">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customDarkSurface || uiStore.customDarkSurface === '#080808' }"
              title="Deep Black Surface"
              @click="uiStore.resetCustomColor('midnight', 'surface')"
            >
              <span class="swatch-preview" style="background-color: #080808; border: 1px solid #1a1a1a;"></span>
              <span class="swatch-name">Deep Black</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkSurface === '#1a202c' }"
              title="Slate Gray"
              @click="uiStore.setCustomColor('midnight', 'surface', '#1a202c')"
            >
              <span class="swatch-preview" style="background-color: #1a202c;"></span>
              <span class="swatch-name">Slate</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkSurface === '#131d2e' }"
              title="Navy Card"
              @click="uiStore.setCustomColor('midnight', 'surface', '#131d2e')"
            >
              <span class="swatch-preview" style="background-color: #131d2e;"></span>
              <span class="swatch-name">Navy Card</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkSurface === '#161b22' }"
              title="Charcoal"
              @click="uiStore.setCustomColor('midnight', 'surface', '#161b22')"
            >
              <span class="swatch-preview" style="background-color: #161b22;"></span>
              <span class="swatch-name">Charcoal</span>
            </button>
          </div>

          <!-- Daylight Surface Swatches -->
          <div v-else class="swatches-grid">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customLightSurface || uiStore.customLightSurface === '#ede3d5' }"
              title="Warm Studio Canvas"
              @click="uiStore.resetCustomColor('daylight', 'surface')"
            >
              <span class="swatch-preview" style="background-color: #ede3d5; border: 1px solid #d8cbba;"></span>
              <span class="swatch-name">Studio Sand</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightSurface === '#ffffff' }"
              title="Clean White Card"
              @click="uiStore.setCustomColor('daylight', 'surface', '#ffffff')"
            >
              <span class="swatch-preview" style="background-color: #ffffff; border: 1px solid #e2e8f0;"></span>
              <span class="swatch-name">Clean White</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightSurface === '#f3ece2' }"
              title="Ivory"
              @click="uiStore.setCustomColor('daylight', 'surface', '#f3ece2')"
            >
              <span class="swatch-preview" style="background-color: #f3ece2; border: 1px solid #dfd4c5;"></span>
              <span class="swatch-name">Ivory</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightSurface === '#e8edf3' }"
              title="Soft Slate"
              @click="uiStore.setCustomColor('daylight', 'surface', '#e8edf3')"
            >
              <span class="swatch-preview" style="background-color: #e8edf3; border: 1px solid #c7d2de;"></span>
              <span class="swatch-name">Soft Slate</span>
            </button>
          </div>

          <!-- Custom Color Picker Input -->
          <div class="custom-picker-row">
            <input
              type="color"
              class="color-input"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkSurface || '#080808') : (uiStore.customLightSurface || '#ede3d5')"
              @input="e => uiStore.setCustomColor(uiStore.theme, 'surface', e.target.value)"
            />
            <input
              type="text"
              class="hex-text-input font-mono"
              placeholder="#HEX"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkSurface || '#080808') : (uiStore.customLightSurface || '#ede3d5')"
              @change="e => uiStore.setCustomColor(uiStore.theme, 'surface', e.target.value)"
            />
            <button
              v-if="(uiStore.theme === 'midnight' && uiStore.customDarkSurface) || (uiStore.theme === 'daylight' && uiStore.customLightSurface)"
              type="button"
              class="btn-reset-token"
              title="Reset to default"
              @click="uiStore.resetCustomColor(uiStore.theme, 'surface')"
            >
              <RotateCcw :size="11" />
            </button>
          </div>
        </div>

        <!-- 3. Primary Accent -->
        <div class="popover-section">
          <div class="section-label-row">
            <span class="section-label">3. Primary Accent</span>
            <span class="token-name font-mono">--primary</span>
          </div>

          <!-- Midnight Primary Swatches (5 Curated) -->
          <div v-if="uiStore.theme === 'midnight'" class="swatches-grid swatches-grid-5">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customDarkPrimary || uiStore.customDarkPrimary === '#2dd4bf' }"
              title="Emerald Cyan Theme Default (#2dd4bf)"
              @click="uiStore.resetCustomColor('midnight', 'primary')"
            >
              <span class="swatch-preview" style="background-color: #2dd4bf;"></span>
              <span class="swatch-name">Cyan (Def)</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkPrimary === '#38bdf8' }"
              title="Electric Sky (#38bdf8)"
              @click="uiStore.setCustomColor('midnight', 'primary', '#38bdf8')"
            >
              <span class="swatch-preview" style="background-color: #38bdf8;"></span>
              <span class="swatch-name">Sky Blue</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkPrimary === '#a855f7' }"
              title="Vivid Violet (#a855f7)"
              @click="uiStore.setCustomColor('midnight', 'primary', '#a855f7')"
            >
              <span class="swatch-preview" style="background-color: #a855f7;"></span>
              <span class="swatch-name">Violet</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkPrimary === '#f59e0b' }"
              title="Warm Amber (#f59e0b)"
              @click="uiStore.setCustomColor('midnight', 'primary', '#f59e0b')"
            >
              <span class="swatch-preview" style="background-color: #f59e0b;"></span>
              <span class="swatch-name">Amber</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkPrimary === '#f43f5e' }"
              title="Coral Rose (#f43f5e)"
              @click="uiStore.setCustomColor('midnight', 'primary', '#f43f5e')"
            >
              <span class="swatch-preview" style="background-color: #f43f5e;"></span>
              <span class="swatch-name">Rose</span>
            </button>
          </div>

          <!-- Daylight Primary Swatches (5 Curated) -->
          <div v-else class="swatches-grid swatches-grid-5">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customLightPrimary || uiStore.customLightPrimary === '#854d0e' }"
              title="Saddle Umber Theme Default (#854d0e)"
              @click="uiStore.resetCustomColor('daylight', 'primary')"
            >
              <span class="swatch-preview" style="background-color: #854d0e;"></span>
              <span class="swatch-name">Saddle (Def)</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightPrimary === '#15803d' }"
              title="Forest Green (#15803d)"
              @click="uiStore.setCustomColor('daylight', 'primary', '#15803d')"
            >
              <span class="swatch-preview" style="background-color: #15803d;"></span>
              <span class="swatch-name">Forest</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightPrimary === '#4338ca' }"
              title="Deep Indigo (#4338ca)"
              @click="uiStore.setCustomColor('daylight', 'primary', '#4338ca')"
            >
              <span class="swatch-preview" style="background-color: #4338ca;"></span>
              <span class="swatch-name">Indigo</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightPrimary === '#c2410c' }"
              title="Warm Terracotta (#c2410c)"
              @click="uiStore.setCustomColor('daylight', 'primary', '#c2410c')"
            >
              <span class="swatch-preview" style="background-color: #c2410c;"></span>
              <span class="swatch-name">Terracotta</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightPrimary === '#9f1239' }"
              title="Burgundy Plum (#9f1239)"
              @click="uiStore.setCustomColor('daylight', 'primary', '#9f1239')"
            >
              <span class="swatch-preview" style="background-color: #9f1239;"></span>
              <span class="swatch-name">Plum</span>
            </button>
          </div>

          <!-- Custom Color Picker Input -->
          <div class="custom-picker-row">
            <input
              type="color"
              class="color-input"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkPrimary || '#2dd4bf') : (uiStore.customLightPrimary || '#854d0e')"
              @input="e => uiStore.setCustomColor(uiStore.theme, 'primary', e.target.value)"
            />
            <input
              type="text"
              class="hex-text-input font-mono"
              placeholder="#HEX"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkPrimary || '#2dd4bf') : (uiStore.customLightPrimary || '#854d0e')"
              @change="e => uiStore.setCustomColor(uiStore.theme, 'primary', e.target.value)"
            />
            <button
              v-if="(uiStore.theme === 'midnight' && uiStore.customDarkPrimary) || (uiStore.theme === 'daylight' && uiStore.customLightPrimary)"
              type="button"
              class="btn-reset-token"
              title="Reset to default"
              @click="uiStore.resetCustomColor(uiStore.theme, 'primary')"
            >
              <RotateCcw :size="11" />
            </button>
          </div>
        </div>

        <!-- 4. Border & Divider -->
        <div class="popover-section">
          <div class="section-label-row">
            <span class="section-label">4. Border &amp; Dividers</span>
            <span class="token-name font-mono">--border-color</span>
          </div>

          <!-- Midnight Border Swatches -->
          <div v-if="uiStore.theme === 'midnight'" class="swatches-grid">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customDarkBorder || uiStore.customDarkBorder === '#151515' }"
              title="Subtle Dark Border"
              @click="uiStore.resetCustomColor('midnight', 'border')"
            >
              <span class="swatch-preview" style="background-color: #151515; border: 1px solid #2a2a2a;"></span>
              <span class="swatch-name">Subtle Slate</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkBorder === '#2d3748' }"
              title="Visible Gray"
              @click="uiStore.setCustomColor('midnight', 'border', '#2d3748')"
            >
              <span class="swatch-preview" style="background-color: #2d3748;"></span>
              <span class="swatch-name">Medium Slate</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkBorder === '#1e293b' }"
              title="Navy Border"
              @click="uiStore.setCustomColor('midnight', 'border', '#1e293b')"
            >
              <span class="swatch-preview" style="background-color: #1e293b;"></span>
              <span class="swatch-name">Navy Border</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customDarkBorder === '#334155' }"
              title="High Contrast"
              @click="uiStore.setCustomColor('midnight', 'border', '#334155')"
            >
              <span class="swatch-preview" style="background-color: #334155;"></span>
              <span class="swatch-name">Contrast</span>
            </button>
          </div>

          <!-- Daylight Border Swatches -->
          <div v-else class="swatches-grid">
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: !uiStore.customLightBorder || uiStore.customLightBorder === '#dcd1c4' }"
              title="Parchment Border"
              @click="uiStore.resetCustomColor('daylight', 'border')"
            >
              <span class="swatch-preview" style="background-color: #dcd1c4; border: 1px solid #c8baa9;"></span>
              <span class="swatch-name">Parchment</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightBorder === '#cbd5e1' }"
              title="Cool Slate"
              @click="uiStore.setCustomColor('daylight', 'border', '#cbd5e1')"
            >
              <span class="swatch-preview" style="background-color: #cbd5e1; border: 1px solid #94a3b8;"></span>
              <span class="swatch-name">Cool Slate</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightBorder === '#e2e8f0' }"
              title="Subtle Light"
              @click="uiStore.setCustomColor('daylight', 'border', '#e2e8f0')"
            >
              <span class="swatch-preview" style="background-color: #e2e8f0; border: 1px solid #cbd5e1;"></span>
              <span class="swatch-name">Subtle Light</span>
            </button>
            <button
              type="button"
              class="swatch-btn"
              :class="{ active: uiStore.customLightBorder === '#b8a690' }"
              title="Warm Saddle"
              @click="uiStore.setCustomColor('daylight', 'border', '#b8a690')"
            >
              <span class="swatch-preview" style="background-color: #b8a690; border: 1px solid #9f8c75;"></span>
              <span class="swatch-name">Warm Saddle</span>
            </button>
          </div>

          <!-- Custom Color Picker Input -->
          <div class="custom-picker-row">
            <input
              type="color"
              class="color-input"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBorder || '#151515') : (uiStore.customLightBorder || '#dcd1c4')"
              @input="e => uiStore.setCustomColor(uiStore.theme, 'border', e.target.value)"
            />
            <input
              type="text"
              class="hex-text-input font-mono"
              placeholder="#HEX"
              :value="uiStore.theme === 'midnight' ? (uiStore.customDarkBorder || '#151515') : (uiStore.customLightBorder || '#dcd1c4')"
              @change="e => uiStore.setCustomColor(uiStore.theme, 'border', e.target.value)"
            />
            <button
              v-if="(uiStore.theme === 'midnight' && uiStore.customDarkBorder) || (uiStore.theme === 'daylight' && uiStore.customLightBorder)"
              type="button"
              class="btn-reset-token"
              title="Reset to default"
              @click="uiStore.resetCustomColor(uiStore.theme, 'border')"
            >
              <RotateCcw :size="11" />
            </button>
          </div>
        </div>
      </div>

      <!-- Popover Footer -->
      <div class="popover-footer">
        <button
          type="button"
          class="btn-reset-all"
          @click="uiStore.resetAllCustomColors(uiStore.theme)"
        >
          <RotateCcw :size="12" />
          <span>Reset {{ uiStore.theme === 'midnight' ? 'Midnight' : 'Daylight' }} to Defaults</span>
        </button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.theme-palette-popover {
  position: fixed;
  top: calc(var(--navbar-height) + 10px);
  right: 24px;
  width: 360px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - var(--navbar-height) - 30px);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.35), 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  z-index: 500;
  backdrop-filter: blur(12px);
  overflow: hidden;
}

/* Header */
.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background-color: var(--bg-main);
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.btn-close-popover {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-close-popover:hover {
  background-color: var(--bg-elevated);
  color: var(--text-main);
}

/* Theme Switch Segmented Button */
.theme-switch-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 10px 16px;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.theme-mode-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.theme-mode-btn:hover {
  border-color: var(--primary);
  color: var(--text-main);
}

.theme-mode-btn.active {
  background-color: var(--primary);
  border-color: var(--primary);
  color: var(--primary-contrast, #0a0d14);
}

/* Body */
.popover-body {
  padding: 12px 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.popover-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.token-name {
  font-size: 10px;
  color: var(--text-muted);
}

/* Swatches Grid */
.swatches-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.swatches-grid-5 {
  grid-template-columns: repeat(5, 1fr);
  gap: 5px;
}

.swatch-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 5px 3px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.swatch-btn:hover {
  border-color: var(--primary);
}

.swatch-btn.active {
  border-color: var(--primary);
  background-color: var(--primary-subtle);
}

.swatch-preview {
  width: 100%;
  height: 18px;
  border-radius: 3px;
}

.swatch-name {
  font-size: 9px;
  font-weight: 600;
  color: var(--text-secondary);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* Custom Color Picker Input */
.custom-picker-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.color-input {
  -webkit-appearance: none;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  width: 28px;
  height: 28px;
  cursor: pointer;
  background: transparent;
  padding: 0;
  flex-shrink: 0;
}

.color-input::-webkit-color-swatch-wrapper {
  padding: 2px;
}

.color-input::-webkit-color-swatch {
  border: none;
  border-radius: 2px;
}

.hex-text-input {
  flex: 1;
  height: 28px;
  font-size: 11px;
  padding: 0 8px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-main);
}

.hex-text-input:focus {
  border-color: var(--primary);
  outline: none;
}

.btn-reset-token {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-main);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-reset-token:hover {
  border-color: var(--primary);
  color: var(--primary);
}

/* Footer */
.popover-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--bg-main);
  display: flex;
  justify-content: center;
}

.btn-reset-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  font-size: 11px;
  font-weight: 600;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-reset-all:hover {
  border-color: var(--danger, #ef4444);
  color: var(--danger, #ef4444);
}

/* Transitions */
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.97);
}
</style>
