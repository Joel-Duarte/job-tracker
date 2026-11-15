<script setup>
import {
  ArrowLeft,
  Code2,
  FileImage,
  FileText,
  Globe,
  Layers,
  Lightbulb,
  Loader2,
  Save,
  Sparkles,
  Upload,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DiagramCanvasBuilder from '../components/system-design/DiagramCanvasBuilder.vue'
import { useSystemDesignStore } from '../stores/systemDesignStore'
import { useUIStore } from '../stores/uiStore'

const route = useRoute()
const router = useRouter()
const store = useSystemDesignStore()
const uiStore = useUIStore()

const canvasBuilderRef = ref(null)
const canvasNotes = ref('')
const loadedFlow = ref(null)
const activeRevisionVersion = ref(null)
const flowSnapshot = ref({ nodes: [], edges: [], notes: '' })

const showNotesDrawer = ref(false)
const showImageUploadModal = ref(false)
const useWebSearchReview = ref(false)
const stagedDiagramFile = ref(null)
const stagedPreviewUrl = ref('')
const imageNotesInput = ref('')

const sessionId = computed(() => Number(route.params.sessionId))
const session = computed(() => store.activeSession)
const challengeTitle = computed(() => session.value?.challenge?.title || 'Architecture Design Studio')
const guidancePenalty = computed(() => Number(session.value?.diagram_guidance?.penalty_points || 0))
const isStrictInterview = computed(
  () => String(session.value?.mode || '').toUpperCase() === 'INTERVIEW'
)
const revisions = computed(() => session.value?.diagrams_metadata || [])
const canvasRevisions = computed(() =>
  revisions.value.filter((d) => d.diagram_kind === 'canvas')
)
const nextVersionNumber = computed(() => revisions.value.length + 1)

function returnToSession(stage = 'DESIGN') {
  router.push({
    path: '/chat',
    query: {
      mode: 'system_design',
      sessionId: String(sessionId.value),
      stage,
    },
  })
}

async function handleSelectRevision(ver) {
  const rev = revisions.value.find((r) => Number(r.version) === Number(ver))
  if (!rev || rev.diagram_kind !== 'canvas') return
  try {
    const flow = await store.loadDiagramFlow(rev.version)
    loadedFlow.value = flow
    activeRevisionVersion.value = rev.version
    canvasNotes.value = flow.notes || ''
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to load canvas revision', 'error')
  }
}

function handleStartBlankCanvas() {
  loadedFlow.value = null
  activeRevisionVersion.value = null
  canvasBuilderRef.value?.clearCanvas()
}

async function handleRequestHint(hintMode) {
  if (store.loadingDiagramHint) return
  try {
    const currentNodes = canvasBuilderRef.value?.getCurrentNodes?.() || flowSnapshot.value.nodes || []
    const res = await store.requestDiagramHint(hintMode, currentNodes)
    uiStore.showToast(res?.message || 'Component hint unlocked!', 'info')
  } catch (err) {
    uiStore.showToast(err.message || 'Unable to unlock diagram hint', 'error')
  }
}

async function handleSaveCanvas() {
  const snapshot = canvasBuilderRef.value?.getFlowSnapshot?.() || flowSnapshot.value
  if (!snapshot?.nodes?.length || store.uploadingDiagram) {
    if (!snapshot?.nodes?.length) {
      uiStore.showToast('Add at least one component block before saving.', 'warning')
    }
    return null
  }
  try {
    const updated = await store.submitCanvasDiagram({
      ...snapshot,
      notes: canvasNotes.value.trim(),
    })
    const latest = (updated?.diagrams_metadata || []).slice(-1)[0]
    if (latest) {
      activeRevisionVersion.value = latest.version
    }
    uiStore.showToast(`Saved canvas revision v${latest?.version || nextVersionNumber.value}!`, 'success')
    return updated
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to save canvas diagram', 'error')
    return null
  }
}

async function handleAnalyzeArchitecture() {
  if (store.reviewingDiagram) return
  const snapshot = canvasBuilderRef.value?.getFlowSnapshot?.() || flowSnapshot.value
  let targetVersion = revisions.value.length ? revisions.value[revisions.value.length - 1].version : null

  if (snapshot?.nodes?.length) {
    const saved = await handleSaveCanvas()
    if (!saved) return
    const latest = (saved.diagrams_metadata || []).slice(-1)[0]
    targetVersion = latest?.version ?? targetVersion
  }
  if (!targetVersion) {
    uiStore.showToast('Build a canvas diagram or upload an image first.', 'warning')
    return
  }

  try {
    await store.reviewDiagram(targetVersion, useWebSearchReview.value)
    uiStore.showToast('Architecture review completed!', 'success')
    returnToSession('REVIEW')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to analyze architecture', 'error')
  }
}

function stageImageFile(file) {
  if (!file) return
  const validTypes = ['image/png', 'image/jpeg', 'image/webp']
  if (file.type && !validTypes.includes(file.type)) {
    uiStore.showToast('Unsupported image format. Use PNG, JPEG, or WebP.', 'error')
    return
  }
  stagedDiagramFile.value = file
  if (stagedPreviewUrl.value) URL.revokeObjectURL(stagedPreviewUrl.value)
  stagedPreviewUrl.value = URL.createObjectURL(file)
}

function handleStudioPaste(event) {
  if (!showImageUploadModal.value) return
  const items = event.clipboardData?.items || []
  for (const item of items) {
    if (item.type?.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        stageImageFile(file)
        uiStore.showToast('Diagram image pasted!', 'info')
        break
      }
    }
  }
}

async function handleUploadImage() {
  if (!stagedDiagramFile.value || store.uploadingDiagram) return
  try {
    await store.uploadDiagram(stagedDiagramFile.value, imageNotesInput.value)
    stagedDiagramFile.value = null
    if (stagedPreviewUrl.value) {
      URL.revokeObjectURL(stagedPreviewUrl.value)
      stagedPreviewUrl.value = ''
    }
    imageNotesInput.value = ''
    showImageUploadModal.value = false
    uiStore.showToast('Uploaded architecture image revision!', 'success')
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to upload image', 'error')
  }
}

watch(
  () => sessionId.value,
  async (id) => {
    if (!id) return
    await Promise.allSettled([store.loadSession(id), store.fetchDiagramCatalog()])
    const requestedVersion = route.query?.version ? Number(route.query.version) : null
    const targetCanvas =
      (requestedVersion
        ? canvasRevisions.value.find((d) => Number(d.version) === requestedVersion)
        : null) || [...canvasRevisions.value].reverse()[0]
    if (targetCanvas) {
      await handleSelectRevision(targetCanvas.version)
    }
  },
  { immediate: true }
)

onMounted(() => {
  window.addEventListener('paste', handleStudioPaste)
})

onUnmounted(() => {
  window.removeEventListener('paste', handleStudioPaste)
  if (stagedPreviewUrl.value) URL.revokeObjectURL(stagedPreviewUrl.value)
})
</script>

<template>
  <div class="sd-studio-page" data-testid="design-studio-page">
    <!-- Dedicated Slim Top Control Bar -->
    <header class="sd-studio-header" data-testid="design-studio-header">
      <div class="sd-studio-header-left">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="studio-back-btn"
          @click="returnToSession('DESIGN')"
        >
          <ArrowLeft :size="14" />
          <span>Back</span>
        </button>

        <div class="sd-studio-title-wrap">
          <h1 class="sd-studio-title">{{ challengeTitle }}</h1>
          <span v-if="session" class="badge badge-assessment">{{ session.mode }}</span>
        </div>

        <div v-if="canvasRevisions.length" class="sd-studio-rev-group">
          <select
            :value="activeRevisionVersion || ''"
            class="form-select sd-rev-select"
            aria-label="Load canvas revision"
            @change="$event.target.value ? handleSelectRevision($event.target.value) : handleStartBlankCanvas()"
          >
            <option value="">+ New Canvas</option>
            <option
              v-for="rev in canvasRevisions"
              :key="rev.version"
              :value="rev.version"
            >
              v{{ rev.version }} ({{ rev.node_count || 0 }} blocks)
            </option>
          </select>
        </div>
      </div>

      <div class="sd-studio-header-center">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="hint-next-component-btn"
          :disabled="store.loadingDiagramHint"
          @click="handleRequestHint('next_component')"
        >
          <Loader2 v-if="store.loadingDiagramHint" :size="14" class="spin" />
          <Lightbulb v-else :size="14" />
          <span>Hint Block (-3 pts)</span>
        </button>

        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="reveal-bank-btn"
          :disabled="store.loadingDiagramHint || isStrictInterview"
          :title="
            isStrictInterview
              ? 'Disabled in strict INTERVIEW mode.'
              : 'Reveal all expected components (-18 pts base penalty)'
          "
          @click="handleRequestHint('reveal_all')"
        >
          <Layers :size="14" />
          <span>Required Bank</span>
        </button>

        <span
          v-if="guidancePenalty > 0"
          class="badge badge-interview"
          data-testid="guidance-penalty-badge"
        >
          -{{ guidancePenalty }} pts
        </span>
      </div>

      <div class="sd-studio-header-right">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="toggle-studio-notes-btn"
          @click="showNotesDrawer = !showNotesDrawer"
        >
          <FileText :size="14" />
          <span>Notes &amp; JSON</span>
        </button>

        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="open-image-upload-modal-btn"
          @click="showImageUploadModal = true"
        >
          <Upload :size="14" />
          <span>Upload Image</span>
        </button>

        <button
          type="button"
          class="btn btn-secondary btn-sm"
          data-testid="save-canvas-btn"
          :disabled="store.uploadingDiagram"
          @click="handleSaveCanvas"
        >
          <Loader2 v-if="store.uploadingDiagram" :size="14" class="spin" />
          <Save v-else :size="14" />
          <span>Save v{{ nextVersionNumber }}</span>
        </button>

        <button
          type="button"
          class="btn btn-primary btn-sm"
          data-testid="analyze-canvas-btn"
          :disabled="store.reviewingDiagram || store.uploadingDiagram"
          @click="handleAnalyzeArchitecture"
        >
          <Loader2 v-if="store.reviewingDiagram" :size="14" class="spin" />
          <Sparkles v-else :size="14" />
          <span>Analyze</span>
        </button>
      </div>
    </header>

    <!-- Main Full-Viewport Canvas Body -->
    <div class="sd-studio-body">
      <DiagramCanvasBuilder
        ref="canvasBuilderRef"
        v-model:notes="canvasNotes"
        :session="session"
        :catalog="store.diagramCatalog"
        :loaded-flow="loadedFlow"
        @flow-change="flowSnapshot = $event"
      />

      <!-- Optional Slide-Over Notes & Flow JSON Drawer (closed by default) -->
      <aside
        v-if="showNotesDrawer"
        class="sd-studio-drawer"
        data-testid="studio-notes-drawer"
      >
        <div class="sd-drawer-head">
          <h3>Notes &amp; Flow JSON</h3>
          <button type="button" class="sd-icon-close" @click="showNotesDrawer = false">
            <X :size="15" />
          </button>
        </div>

        <label class="sd-field-label">
          <span>Architecture Summary Notes</span>
          <textarea
            v-model="canvasNotes"
            class="form-textarea"
            rows="4"
            data-testid="canvas-notes-input"
            placeholder="Summarize read/write paths, sharding keys, TTL, or trade-offs..."
          />
        </label>

        <label class="sd-drawer-checkbox">
          <input
            v-model="useWebSearchReview"
            type="checkbox"
            data-testid="review-web-search-checkbox"
          />
          <Globe :size="14" />
          <span>Ground AI critique with Web Search</span>
        </label>

        <div class="sd-flow-preview-wrap" data-testid="flow-json-preview">
          <div class="sd-flow-preview-head">
            <Code2 :size="14" />
            <span>
              {{ flowSnapshot.nodes?.length || 0 }} blocks, {{ flowSnapshot.edges?.length || 0 }} flows
            </span>
          </div>
          <pre class="sd-flow-json-pre">{{ JSON.stringify(flowSnapshot, null, 2) }}</pre>
        </div>
      </aside>
    </div>

    <!-- Clean External Image Upload Modal (Excalidraw / PNG / JPEG / WebP) -->
    <div
      v-if="showImageUploadModal"
      class="sd-studio-modal-backdrop"
      data-testid="studio-image-upload-modal"
      @click.self="showImageUploadModal = false"
    >
      <div class="sd-studio-modal">
        <div class="sd-drawer-head">
          <h3>
            <FileImage :size="16" />
            <span>Upload External Architecture Image</span>
          </h3>
          <button type="button" class="sd-icon-close" @click="showImageUploadModal = false">
            <X :size="16" />
          </button>
        </div>

        <p class="sd-muted">
          Prefer Excalidraw, Draw.io, or paper? Upload a PNG, JPEG, or WebP diagram (or press <strong>Ctrl+V</strong> to paste).
        </p>

        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          class="diagram-file-input"
          aria-label="Upload diagram image"
          @change="stageImageFile($event.target?.files?.[0])"
        />

        <img
          v-if="stagedPreviewUrl"
          :src="stagedPreviewUrl"
          alt="Staged diagram preview"
          class="sd-modal-preview-img"
        />

        <input
          v-model="imageNotesInput"
          type="text"
          class="form-input"
          placeholder="Optional revision notes..."
        />

        <div class="sd-modal-actions">
          <button type="button" class="btn btn-secondary" @click="showImageUploadModal = false">
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="!stagedDiagramFile || store.uploadingDiagram"
            @click="handleUploadImage"
          >
            <Loader2 v-if="store.uploadingDiagram" :size="14" class="spin" />
            <Upload v-else :size="14" />
            <span>Upload Image Revision</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sd-studio-page {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  background: var(--bg-app, #0b1120);
  color: var(--text-primary, #f8fafc);
  overflow: hidden;
}

.sd-studio-header {
  min-height: 54px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-shrink: 0;
}

.sd-studio-header-left,
.sd-studio-header-center,
.sd-studio-header-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.sd-studio-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sd-studio-title {
  margin: 0;
  font-size: 0.96rem;
  font-weight: 650;
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sd-rev-select {
  min-width: 145px;
}

.sd-studio-body {
  flex: 1;
  min-height: 0;
  display: flex;
  position: relative;
  overflow: hidden;
}

.sd-studio-drawer {
  width: 310px;
  max-width: 90vw;
  border-left: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex-shrink: 0;
}

.sd-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sd-drawer-head h3 {
  margin: 0;
  font-size: 0.92rem;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.sd-icon-close {
  border: none;
  background: transparent;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
  padding: 4px;
}

.sd-field-label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 0.8rem;
  color: var(--text-secondary, #94a3b8);
}

.sd-drawer-checkbox {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.82rem;
  cursor: pointer;
}

.sd-flow-preview-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px solid var(--border-subtle, #334155);
  border-radius: 8px;
  padding: 10px;
}

.sd-flow-preview-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.sd-flow-json-pre {
  flex: 1;
  margin: 0;
  overflow: auto;
  font-size: 0.72rem;
  line-height: 1.35;
}

.sd-studio-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(15, 23, 42, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.sd-studio-modal {
  width: 480px;
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid var(--border-subtle, #334155);
  background: var(--bg-surface, #1e293b);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sd-modal-preview-img {
  max-height: 220px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid var(--border-subtle, #334155);
}

.sd-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
