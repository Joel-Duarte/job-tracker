import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

import { useUIStore } from './stores/uiStore'
import { useApplicationsStore } from './stores/applicationsStore'

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
