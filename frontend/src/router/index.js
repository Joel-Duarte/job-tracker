import { createRouter, createWebHistory } from 'vue-router'
import ApplicationsView from '../views/ApplicationsView.vue'
import ActionItemsView from '../views/ActionItemsView.vue'
import AssessmentsView from '../views/AssessmentsView.vue'
import QueueView from '../views/QueueView.vue'
import CandidateProfileView from '../views/CandidateProfileView.vue'
import AgentChatView from '../views/AgentChatView.vue'
import StagingView from '../views/StagingView.vue'
import SettingsView from '../views/SettingsView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import InterviewGuideView from '../views/InterviewGuideView.vue'
import DiagnosticsView from '../views/DiagnosticsView.vue'

const routes = [
  {
    path: '/',
    name: 'Applications',
    component: ApplicationsView,
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: AnalyticsView,
  },
  {
    path: '/tasks',
    name: 'ActionItems',
    component: ActionItemsView,
  },
  {
    path: '/assessments',
    name: 'Assessments',
    component: AssessmentsView,
    alias: ['/intake'],
  },
  {
    path: '/queue',
    name: 'Queue',
    component: QueueView,
  },
  {
    path: '/profile',
    redirect: '/settings?tab=profile',
  },
  {
    path: '/chat',
    name: 'AgentChat',
    component: AgentChatView,
  },
  {
    path: '/staging',
    name: 'Staging',
    component: StagingView,
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView,
  },
  {
    path: '/guide/:id',
    name: 'InterviewGuide',
    component: InterviewGuideView,
  },
  {
    path: '/diagnostics',
    name: 'Diagnostics',
    component: DiagnosticsView,
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

import { isDemoModeEnabled } from '../demo/demoStorage'
import { recordPageView } from '../utils/beacon'

// Track page visits for GitHub Pages demo mode
router.afterEach((to) => {
  if (
    isDemoModeEnabled() ||
    (typeof window !== 'undefined' && window.location.hostname.includes('github.io'))
  ) {
    recordPageView(to.fullPath)
  }
})

export default router


