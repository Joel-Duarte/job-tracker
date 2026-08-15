import { createRouter, createWebHistory } from 'vue-router'
import ApplicationsView from '../views/ApplicationsView.vue'
import ActionItemsView from '../views/ActionItemsView.vue'
import JobIntakeView from '../views/JobIntakeView.vue'
import CandidateProfileView from '../views/CandidateProfileView.vue'
import AgentChatView from '../views/AgentChatView.vue'
import StagingView from '../views/StagingView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  {
    path: '/',
    name: 'Applications',
    component: ApplicationsView,
  },
  {
    path: '/tasks',
    name: 'ActionItems',
    component: ActionItemsView,
  },
  {
    path: '/intake',
    name: 'JobIntake',
    component: JobIntakeView,
  },
  {
    path: '/profile',
    name: 'CandidateProfile',
    component: CandidateProfileView,
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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
