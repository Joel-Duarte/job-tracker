<script setup>
import { ref } from 'vue'
import { ExternalLink, Copy, Check, Download, Upload, ChevronDown, ChevronUp, Loader2 } from 'lucide-vue-next'

const props = defineProps({
  title: { type: String, default: 'Use External Frontier Chat (ChatGPT / Claude / Gemini)' },
  subtitle: {
    type: String,
    default: 'Copy the self-contained prompt with your CV, JD & company research, run it anywhere for free, then paste the output below.',
  },
  prepareLabel: { type: String, default: 'Prepare & Copy Prompt' },
  importLabel: { type: String, default: 'Import & Save Result' },
  pastePlaceholder: { type: String, default: 'Paste the external AI response here...' },
  prepareDisabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  promptData: { type: Object, default: null },
  testIdPrefix: { type: String, default: 'frontier-bridge' },
})

const emit = defineEmits(['prepare', 'import'])

const isExpanded = ref(false)
const pastedText = ref('')
const justCopied = ref(false)

async function copyPromptToClipboard() {
  const txt = props.promptData?.markdown_prompt
  if (!txt) return
  try {
    await navigator.clipboard?.writeText(txt)
    justCopied.value = true
    setTimeout(() => {
      justCopied.value = false
    }, 2000)
  } catch {
    // User can still copy directly from the preview box
  }
}

function downloadPromptFile() {
  const txt = props.promptData?.markdown_prompt
  if (!txt) return
  const blob = new Blob([txt], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = props.promptData?.filename || 'frontier-prompt.md'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function handleImportClick() {
  const val = pastedText.value.trim()
  if (!val) return
  emit('import', val)
}

defineExpose({
  clearImport() {
    pastedText.value = ''
  },
  open() {
    isExpanded.value = true
  },
})
</script>

<template>
  <div class="frontier-bridge-card" :data-testid="testIdPrefix">
    <button
      type="button"
      class="frontier-bridge-header"
      :data-testid="`${testIdPrefix}-toggle`"
      @click="isExpanded = !isExpanded"
    >
      <div class="frontier-bridge-title-row">
        <ExternalLink :size="14" class="text-primary" />
        <span class="frontier-bridge-title">{{ title }}</span>
      </div>
      <div class="frontier-bridge-toggle-hint">
        <span>{{ isExpanded ? 'Hide' : 'Copy Prompt / Paste Output' }}</span>
        <ChevronUp v-if="isExpanded" :size="15" />
        <ChevronDown v-else :size="15" />
      </div>
    </button>

    <div v-if="isExpanded" class="frontier-bridge-body">
      <p class="frontier-bridge-sub">{{ subtitle }}</p>

      <div class="frontier-bridge-actions">
        <button
          type="button"
          class="btn btn-secondary btn-xs"
          :disabled="loading || prepareDisabled"
          :data-testid="`${testIdPrefix}-prepare-btn`"
          @click="$emit('prepare')"
        >
          <Loader2 v-if="loading" :size="13" class="animate-spin" />
          <Copy v-else :size="13" />
          <span>{{ loading ? 'Preparing...' : prepareLabel }}</span>
        </button>

        <button
          v-if="promptData?.markdown_prompt"
          type="button"
          class="btn btn-secondary btn-xs"
          :data-testid="`${testIdPrefix}-copy-btn`"
          @click="copyPromptToClipboard"
        >
          <Check v-if="justCopied" :size="13" class="text-success" />
          <Copy v-else :size="13" />
          <span>{{ justCopied ? 'Copied!' : 'Copy Again' }}</span>
        </button>

        <button
          v-if="promptData?.markdown_prompt"
          type="button"
          class="btn btn-secondary btn-xs"
          :data-testid="`${testIdPrefix}-download-btn`"
          @click="downloadPromptFile"
        >
          <Download :size="13" />
          <span>Download .md</span>
        </button>
      </div>

      <textarea
        v-if="promptData?.markdown_prompt"
        :value="promptData.markdown_prompt"
        readonly
        rows="4"
        class="frontier-bridge-textarea frontier-preview"
        :data-testid="`${testIdPrefix}-prompt-preview`"
      ></textarea>

      <div class="frontier-import-box">
        <textarea
          v-model="pastedText"
          rows="4"
          class="frontier-bridge-textarea"
          :placeholder="pastePlaceholder"
          :data-testid="`${testIdPrefix}-import-input`"
        ></textarea>
        <div class="frontier-import-footer">
          <button
            type="button"
            class="btn btn-primary btn-xs"
            :disabled="!pastedText.trim()"
            :data-testid="`${testIdPrefix}-import-btn`"
            @click="handleImportClick"
          >
            <Upload :size="13" />
            <span>{{ importLabel }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.frontier-bridge-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
  overflow: hidden;
}

.frontier-bridge-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-main);
  text-align: left;
}

.frontier-bridge-header:hover {
  background: var(--bg-hover);
}

.frontier-bridge-title-row {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  font-weight: 600;
}

.frontier-bridge-toggle-hint {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--text-muted);
}

.frontier-bridge-body {
  padding: 10px 12px 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.frontier-bridge-sub {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}

.frontier-bridge-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.frontier-bridge-textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 11.5px;
  padding: 8px;
  resize: vertical;
}

.frontier-preview {
  color: var(--text-muted);
}

.frontier-import-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.frontier-import-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
