import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

import { useUIStore } from './stores/uiStore'
import { useApplicationsStore } from './stores/applicationsStore'

import { isDemoModeEnabled } from './demo/demoStorage'

// In Demo Mode only (e.g. GitHub Pages), initialize privacy-friendly analytics
if (typeof document !== 'undefined' && isDemoModeEnabled()) {
  const gcScript = document.createElement('script')
  gcScript.async = true
  gcScript.src = `${import.meta.env.BASE_URL}vendor/count.js`
  gcScript.setAttribute('data-goatcounter', 'https://djodev.goatcounter.com/count')
  document.head.appendChild(gcScript)
}

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

app.mount('#app')

// Expose stores for dev/verification tooling
if (import.meta.env.DEV) {
  window.useUIStore = () => useUIStore(pinia)
  window.useApplicationsStore = () => useApplicationsStore(pinia)
}
