<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import { StagingAPI, ActionItemsAPI, IntakeAPI } from '../../api/endpoints'
import {
  Briefcase,
  Layers,
  Bot,
  Settings,
  Plus,
  Palette,
  Inbox,
  Sparkles,
  FileInput,
  UserCheck,
  CheckSquare,
  Cpu,
  Mail,
  BarChart3,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()

const pendingStagingCount = ref(0)
const pendingTasksCount = ref(0)
const activeQueueCount = ref(0)
const readyAssessmentsCount = ref(0)

async function fetchBadgeCounts() {
  try {
    const res = await StagingAPI.list({ status: 'PENDING', limit: 1 })
    pendingStagingCount.value = res.data.total || 0
  } catch (err) {
    // ignore
  }

  try {
    const resTasks = await ActionItemsAPI.list({ status: 'PENDING', limit: 1 })
    pendingTasksCount.value = resTasks.data.pending_count || 0
  } catch (err) {
    // ignore
  }

  try {
    const resQueue = await IntakeAPI.getEvaluations(100)
    if (Array.isArray(resQueue.data)) {
      activeQueueCount.value = resQueue.data.filter((t) => ['QUEUED', 'PROCESSING'].includes(t.status)).length
      const passedSet = new Set(JSON.parse(localStorage.getItem('job_tracker_passed_assessments') || '[]'))
      readyAssessmentsCount.value = resQueue.data.filter(
        (t) => (t.task_type === 'JOB_ASSESSMENT' || !t.task_type) && t.status === 'COMPLETED' && !passedSet.has(String(t.id))
      ).length
    }
  } catch (err) {
    // ignore
  }
}

onMounted(() => {
  fetchBadgeCounts()
  setInterval(fetchBadgeCounts, 10000)
})
</script>

<template>
  <header class="navbar">
    <div class="nav-left">
      <router-link to="/" class="nav-brand">
        <div class="brand-icon">
          <Sparkles :size="18" class="text-primary" />
        </div>
        <span class="brand-title">JobTracker</span>
      </router-link>

      <nav class="nav-links">
        <router-link
          to="/"
          class="nav-link"
          :class="{ active: route.path === '/' }"
        >
          <Briefcase :size="16" />
          <span>Board</span>
        </router-link>

        <router-link
          to="/assessments"
          class="nav-link"
          :class="{ active: ['/assessments', '/intake'].includes(route.path) }"
        >
          <Sparkles :size="16" />
          <span>Assessments</span>
          <span v-if="readyAssessmentsCount > 0" class="nav-badge" title="Ready for review">
            {{ readyAssessmentsCount }}
          </span>
        </router-link>

        <router-link
          to="/queue"
          class="nav-link"
          :class="{ active: route.path === '/queue' }"
        >
          <Cpu :size="16" />
          <span>AI Queue</span>
          <span v-if="activeQueueCount > 0" class="nav-badge nav-badge-pulse" title="Tasks currently processing">
            {{ activeQueueCount }}
          </span>
        </router-link>

        <router-link
          to="/tasks"
          class="nav-link"
          :class="{ active: route.path === '/tasks' }"
        >
          <CheckSquare :size="16" />
          <span>Tasks</span>
          <span v-if="pendingTasksCount > 0" class="nav-badge">
            {{ pendingTasksCount }}
          </span>
        </router-link>

        <router-link
          to="/analytics"
          class="nav-link"
          :class="{ active: route.path === '/analytics' }"
        >
          <BarChart3 :size="16" />
          <span>Analytics</span>
        </router-link>

        <router-link
          to="/profile"
          class="nav-link"
          :class="{ active: route.path === '/profile' }"
        >
          <UserCheck :size="16" />
          <span>My Profile / CV</span>
        </router-link>

        <router-link
          to="/chat"
          class="nav-link"
          :class="{ active: route.path === '/chat' }"
        >
          <Bot :size="16" />
          <span>Agent Assistant</span>
        </router-link>

        <router-link
          to="/staging"
          class="nav-link"
          :class="{ active: route.path === '/staging' }"
        >
          <Inbox :size="16" />
          <span>Staging</span>
          <span v-if="pendingStagingCount > 0" class="nav-badge">
            {{ pendingStagingCount }}
          </span>
        </router-link>

        <router-link
          to="/settings"
          class="nav-link"
          :class="{ active: route.path === '/settings' }"
        >
          <Settings :size="16" />
          <span>Settings</span>
        </router-link>
      </nav>
    </div>

    <div class="nav-right">
      <button
        class="btn btn-primary btn-ingest"
        @click="uiStore.openJobIntakeModal"
        title="Ingest job URL or specification text for AI qualification"
      >
        <Sparkles :size="14" />
        <span>Job Intake</span>
      </button>

      <button
        class="btn btn-primary btn-ingest"
        @click="uiStore.openIngestModal"
        title="Sync email accounts, paste threads, or upload message files"
      >
        <Mail :size="14" />
        <span>Email Intake</span>
      </button>

      <button
        class="btn-icon theme-toggle"
        @click="uiStore.toggleTheme"
        :title="'Current theme: ' + uiStore.theme"
      >
        <Palette :size="17" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--navbar-height);
  padding: 0 24px;
  background-color: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: -0.02em;
  color: var(--text-main);
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--primary);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  position: relative;
}

.nav-link:hover {
  color: var(--text-main);
  background-color: var(--bg-surface-hover);
}

.nav-link.active {
  color: var(--text-main);
  background-color: var(--bg-surface);
  border-bottom: 2px solid var(--primary);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.nav-badge {
  background-color: var(--status-interview-text);
  color: var(--bg-main);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: var(--radius-full);
}

.nav-badge-pulse {
  background-color: var(--primary);
  color: #fff;
  animation: pulse-glow 2s infinite ease-in-out;
}

@keyframes pulse-glow {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 var(--primary-glow);
  }
  50% {
    transform: scale(1.08);
    box-shadow: 0 0 0 4px rgba(0, 0, 0, 0);
  }
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-main);
}
</style>
