# Redesign Blank Page Diagnosis & Remediation Guide

This document provides a comprehensive diagnostic analysis and step-by-step remediation guide for resolving blank page rendering issues in the Vue 3 application following the merge of the redesign branches.

---

## 1. Executive Summary

A comprehensive code and runtime audit was conducted across the application entry points, router definitions, layout shells, Pinia stores, API clients, and global CSS design system tokens.

While the core build succeeds, a combination of subtle architectural vulnerabilities introduced during the redesign branch merge can lead to blank pages under specific runtime conditions (e.g. backend offline states, initial onboarding wizard triggering, circular Pinia store references, transition component state locks, or missing fallback routing).

---

## 2. Comprehensive Task-by-Task Diagnostic Findings

### Task 1: Vue Application Instance Mounting (`frontend/src/main.js`)
- **Mount Verification**: The application entry point `frontend/src/main.js` correctly creates the Vue application instance (`createApp(App)`), initializes Pinia (`createPinia()`), installs plugins, and mounts onto the `#app` element in `index.html`.
- **Plugin Order**: Pinia is correctly installed via `app.use(pinia)` *before* `app.use(router)` and `app.mount('#app')`.
- **Potential Risk**: Exposure of stores on `window` in dev mode (`window.useUIStore = () => useUIStore(pinia)`) relies on `pinia` being passed explicitly, which is correct. However, top-level module code in `uiStore.js` executes DOM manipulation (`applyCustomColors()`, `document.documentElement.className`) at module load time before the DOM or Pinia instance is fully ready.

### Task 2: Primary Layout Shell & Router View (`frontend/src/App.vue`)
- **Layout Shell Structure**: `<router-view />` is placed inside `<main class="main-content">` within `<div class="app-layout">`. The layout is not blocked by top-level `v-if` conditionals.
- **Transition Wrapper**: `<router-view>` uses `<transition name="route-fade" mode="out-in">`. In Vue 3, if a route component throws an unhandled error during its `<script setup>` execution or async setup, the transition wrapper fails to render the incoming component, leaving `<main>` empty (rendering a blank page).
- **Onboarding Modal Overlay**: On initial boot when system settings or AI provider queries fail (e.g., HTTP 502/network error when backend is offline), `uiStore.openOnboardingWizard()` is triggered. If `hasCompletedOnboarding` is `false`, the modal overlay (`OnboardingWizardModal.vue`) opens with a full-viewport backdrop (`position: fixed; inset: 0; z-index: 1050;`). If modal styles or z-index rules collapse or if pointer events fail, the underlying view appears inaccessible or blank.

### Task 3: Route Definitions & Configuration (`frontend/src/router/index.js`)
- **Route Definitions**: All routes use direct static component imports (e.g., `import ApplicationsView from '../views/ApplicationsView.vue'`).
- **History Mode**: Router uses `createWebHistory(import.meta.env.BASE_URL)`. While standard for SPAs, navigating directly to deep paths (e.g., `/analytics` or `/settings`) on production web servers without fallback rewrites (such as Nginx `try_files $uri $uri/ /index.html;`) will return a 404 or blank response from the web server.
- **Navigation Guard**: `router.afterEach` invokes `recordPageView(to.fullPath)` when demo mode is active. An unhandled exception inside an afterEach guard can block route completion in edge cases.

### Task 4: Build Logs, Console Traces & Pinia Circular Dependencies
- **Build Output**: `bun run build` generates assets without Vite syntax errors.
- **Circular Store Dependencies**:
  - `uiStore.js` imports `useApplicationsStore` from `./applicationsStore.js` and `useAgentChatStore` from `./agentChatStore.js`.
  - `applicationsStore.js` imports `useUIStore` from `./uiStore.js`.
  - `agentChatStore.js` imports `useUIStore` from `./uiStore.js`.
  - Calling stores inside setup blocks at module level before active Pinia initialization can trigger `[pinia]: "getActivePinia()"` was called with no active Pinia errors, stopping component lifecycle execution.
- **Backend API Failures**: When the FastAPI backend is offline, Axios requests throw network/502 errors. If view components do not handle initial fetch failures gracefully (e.g., missing catch blocks or unhandled promise rejections during `onMounted`), setup fails and renders an empty container.

### Task 5: Global CSS & Viewport Rules (`frontend/src/style.css`)
- **Viewport Layout**: `body` and `.app-layout` enforce `min-height: 100vh`. `.main-content` uses `flex: 1; display: flex; flex-direction: column;`.
- **Theme Variables**: `:root` and `html.daylight` define complete color token palettes (`--bg-app`, `--bg-surface`, `--text-main`, `--primary`).
- **Custom Color Edge Case**: `applyCustomColors()` in `uiStore.js` modifies CSS variables directly on `document.documentElement.style`. If invalid or empty hex strings exist in `localStorage`, CSS properties are removed (`rootStyle.removeProperty('--bg-app')`), falling back to default CSS tokens. If `--bg-app` or `--text-main` are mismatched, elements can become invisible against the dark background.

---

## 3. Summary of Root Causes

1. **Circular Pinia Store Dependencies**: Mutual imports between `uiStore.js`, `applicationsStore.js`, and `agentChatStore.js` can cause undefined store instances during initial bundle load or store creation.
2. **Unhandled Component Lifecycle Errors Under Transition**: Route components wrapped in `<transition name="route-fade" mode="out-in">` in `App.vue` fail to mount if an unhandled promise rejection occurs during `onMounted` API calls.
3. **API Offline Degradation in Onboarding Flow**: When backend endpoints return 502/connection refused, `App.vue` defaults `hasCompletedOnboarding` to `false` and opens the `OnboardingWizardModal`, blocking view interaction if backend calls stall.
4. **Uncaught Web History Route Navigation**: Direct sub-route access on web servers without SPA index.html rewrites results in blank 404 pages.
5. **DOM Modification Prior to Hydration**: `uiStore.js` executes top-level DOM custom color applications before Pinia and Vue app instances are fully mounted.

---

## 4. Step-by-Step Remediation Instructions

### Step 1: Resolve Circular Pinia Store Dependencies (`frontend/src/stores/uiStore.js`)

**File**: `frontend/src/stores/uiStore.js`

**Remediation**:
Ensure store calls (`useApplicationsStore()`, `useAgentChatStore()`) inside `uiStore.js` are evaluated strictly lazily inside action methods (`toggleDemoMode`, `resetDemoData`) and never at top-level setup scope.

```javascript
// Inside toggleDemoMode(enabled) action in uiStore.js:
function toggleDemoMode(enabled) {
  const val = enabled !== undefined ? enabled : !isDemoMode.value
  isDemoMode.value = val
  setDemoModeEnabled(val)
  showToast(
    val ? 'Client Demo Mode activated (running locally).' : 'Live Backend Mode activated.',
    'info'
  )
  try {
    // Lazily resolve store inside action
    const appStore = useApplicationsStore()
    if (appStore && typeof appStore.fetchApplications === 'function') {
      appStore.fetchApplications()
    }
  } catch (err) {
    console.warn('Applications store re-fetch deferred:', err)
  }
}
```

---

### Step 2: Add Error Boundaries & Fallback Guard to Layout Transition (`frontend/src/App.vue`)

**File**: `frontend/src/App.vue`

**Remediation**:
Wrap component rendering inside `<router-view>` with defensive error handling, and safely catch initialization failures in `onMounted`.

```vue
<script setup>
import { onMounted, onErrorCaptured } from 'vue'
import { AIConfigAPI } from './api/endpoints'
import { useUIStore } from './stores/uiStore'
import AppNavbar from './components/layout/AppNavbar.vue'
import ApplicationDetailDrawer from './components/drawers/ApplicationDetailDrawer.vue'
import IngestModal from './components/modals/IngestModal.vue'
import JobIntakeModal from './components/modals/JobIntakeModal.vue'
import CoverLetterModal from './components/modals/CoverLetterModal.vue'
import OnboardingWizardModal from './components/modals/OnboardingWizardModal.vue'
import QuickRetryModal from './components/modals/QuickRetryModal.vue'
import IntakeQueueDrawer from './components/layout/IntakeQueueDrawer.vue'
import FloatingQueueWidget from './components/layout/FloatingQueueWidget.vue'
import FloatingAgentChatWidget from './components/agent/FloatingAgentChatWidget.vue'
import ToastNotification from './components/common/ToastNotification.vue'

const uiStore = useUIStore()

// Capture child view component runtime errors to prevent blank screen collapse
onErrorCaptured((err, target, info) => {
  console.error('Captured component error in App.vue:', err, info)
  uiStore.showToast('A component rendering error occurred. Please refresh.', 'error')
  return false // Prevent error propagation
})

onMounted(async () => {
  try {
    await uiStore.fetchSystemSettings()
    const provRes = await AIConfigAPI.listProviders()
    const providers = provRes?.data || []

    if (!uiStore.hasCompletedOnboarding && providers.length === 0) {
      uiStore.openOnboardingWizard()
    }
  } catch (error) {
    console.warn("System config initialization note:", error)
  }
})
</script>

<template>
  <div class="app-layout">
    <AppNavbar />
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="route-fade" mode="out-in">
          <component :is="Component" v-if="Component" />
        </transition>
      </router-view>
    </main>
    <ApplicationDetailDrawer />
    <IngestModal />
    <JobIntakeModal />
    <CoverLetterModal />
    <OnboardingWizardModal />
    <QuickRetryModal />
    <IntakeQueueDrawer />
    <FloatingQueueWidget />
    <FloatingAgentChatWidget />
    <ToastNotification />
  </div>
</template>
```

---

### Step 3: Safeguard Router Navigation Guards (`frontend/src/router/index.js`)

**File**: `frontend/src/router/index.js`

**Remediation**:
Wrap `router.afterEach` in a try-catch block to prevent navigation telemetry errors from crashing view routing.

```javascript
// Track client-side page navigation (Demo Mode only)
router.afterEach((to) => {
  try {
    if (isDemoModeEnabled()) {
      recordPageView(to.fullPath)
    }
  } catch (err) {
    console.warn('Navigation telemetry tracking error:', err)
  }
})
```

---

### Step 4: Ensure Robust API Error Handling in View Components

**Files**:
- `frontend/src/views/ApplicationsView.vue`
- `frontend/src/views/AnalyticsView.vue`
- `frontend/src/views/ActionItemsView.vue`
- `frontend/src/views/AssessmentsView.vue`

**Remediation**:
Ensure all `onMounted` network requests wrap store dispatch calls in `try ... catch` blocks to ensure view templates render empty states or skeletons rather than crashing.

Example pattern for view setup:

```javascript
onMounted(async () => {
  try {
    await store.fetchData()
  } catch (err) {
    console.warn('Failed to fetch view data:', err)
  }
})
```

---

### Step 5: Verify CSS Layout Tokens & Custom Color Resets (`frontend/src/style.css`)

**File**: `frontend/src/style.css`

**Remediation**:
Verify that `.main-content` and `.app-layout` maintain flex expansion and fallback background values so views always fill the viewport even if custom theme colors are missing.

```css
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: var(--bg-app, #000000);
  color: var(--text-main, #eef2f8);
}

.main-content {
  flex: 1 0 auto;
  display: flex;
  flex-direction: column;
  width: 100%;
}
```

---

## 5. Verification Checklist

1. **Frontend Compilation**: Run `cd frontend && bun run build` to confirm zero build errors.
2. **Offline Mode Test**: Load application with backend stopped; verify App shell renders with notification toast instead of a blank screen.
3. **Demo Mode Switch**: Activate Client Demo Mode via UI toggle; navigate through all 11 routes (`/`, `/analytics`, `/tasks`, `/assessments`, `/queue`, `/profile`, `/chat`, `/staging`, `/settings`, `/guide/1`, `/diagnostics`) to confirm all views display data cards and navigation bars correctly.
