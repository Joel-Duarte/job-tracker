<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUIStore } from '../../stores/uiStore'
import { StagingAPI, ActionItemsAPI } from '../../api/endpoints'
import {
  Briefcase,
  Layers,
  Bot,
  Settings,
  Plus,
  Sun,
  Moon,
  Inbox,
  Sparkles,
  FileInput,
  UserCheck,
  CheckSquare,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()

const pendingStagingCount = ref(0)
const pendingTasksCount = ref(0)

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
}

onMounted(() => {
  fetchBadgeCounts()
  setInterval(fetchBadgeCounts, 15000)
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
          <span>Pipeline</span>
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
          to="/intake"
          class="nav-link"
          :class="{ active: route.path === '/intake' }"
        >
          <FileInput :size="16" />
          <span>Job Intake</span>
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
        @click="uiStore.openIngestModal"
        title="Ingest raw email text or drag files"
      >
        <Plus :size="16" />
        <span>Quick Ingest</span>
      </button>

      <button
        class="btn-icon theme-toggle"
        @click="uiStore.toggleTheme"
        :title="uiStore.theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
      >
        <Sun v-if="uiStore.theme === 'dark'" :size="17" />
        <Moon v-else :size="17" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
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
  gap: 10px;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: -0.02em;
  color: var(--text-main);
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--primary);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
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
  border: 1px solid var(--border-color);
}

.nav-badge {
  background-color: var(--status-interview-text);
  color: #000;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
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
