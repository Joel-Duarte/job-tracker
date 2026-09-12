<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import {
  X,
  Check,
  Copy,
  FileText,
  Sparkles,
  Upload,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Share2,
} from 'lucide-vue-next'
import { CompaniesAPI } from '../../api/endpoints'
import { useUIStore } from '../../stores/uiStore'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  company: {
    type: Object,
    default: null,
  },
  initialTab: {
    type: String,
    default: 'export', // 'export' | 'prompt' | 'import'
  },
})

const emit = defineEmits(['update:modelValue', 'close', 'imported'])

const uiStore = useUIStore()

const activeTab = ref(props.initialTab || 'export')
const includeNotes = ref(true)
const copiedMarkdown = ref(false)
const copiedPrompt = ref(false)
const importJsonText = ref('')
const isSubmittingImport = ref(false)
const importTextareaRef = ref(null)

// Retain last known non-null company so closing the background drawer does not wipe the modal
const activeCompany = ref(props.company)
watch(
  () => props.company,
  (newCompany) => {
    if (newCompany) {
      activeCompany.value = newCompany
    }
  },
  { immediate: true }
)

const currentCompany = computed(() => activeCompany.value || props.company)

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      if (props.company) {
        activeCompany.value = props.company
      }
      activeTab.value = props.initialTab || 'export'
      copiedMarkdown.value = false
      copiedPrompt.value = false
      importJsonText.value = ''
      if (activeTab.value === 'import') {
        nextTick(() => {
          importTextareaRef.value?.focus()
        })
      }
    }
  }
)

watch(activeTab, (tab) => {
  if (tab === 'import') {
    nextTick(() => {
      importTextareaRef.value?.focus()
    })
  }
})

function closeModal() {
  if (isSubmittingImport.value) return
  emit('update:modelValue', false)
  emit('close')
}

// --------------------------------------------------------------------------
// Safe Data Normalization Helpers
// --------------------------------------------------------------------------
function getSafeResearch(comp) {
  if (!comp) return {}
  let cr = comp.company_research || {}
  if (typeof cr === 'string') {
    try {
      cr = JSON.parse(cr)
    } catch {
      cr = {}
    }
  }
  return typeof cr === 'object' && cr !== null ? cr : {}
}

function normalizeText(val) {
  if (val == null) return ''
  if (Array.isArray(val)) {
    return val
      .map((item) => {
        if (item == null) return ''
        if (typeof item === 'string') return item.trim()
        if (typeof item === 'object') {
          if (item.fact) {
            return item.source_url ? `${item.fact} (${item.source_url})` : item.fact
          }
          return JSON.stringify(item)
        }
        return String(item).trim()
      })
      .filter(Boolean)
      .join('\n')
  }
  if (typeof val === 'object') {
    return JSON.stringify(val, null, 2)
  }
  return String(val).trim()
}

function toList(val) {
  if (val == null) return []
  if (Array.isArray(val)) {
    return val
      .map((x) => {
        if (x == null) return ''
        if (typeof x === 'string') return x.trim()
        if (typeof x === 'object') {
          if (x.fact) {
            return x.source_url ? `${x.fact} (${x.source_url})` : x.fact
          }
          if (x.name) return String(x.name).trim()
          if (x.title) return String(x.title).trim()
          if (x.label && x.url) return `${x.label}: ${x.url}`
          return JSON.stringify(x)
        }
        return String(x).trim()
      })
      .filter(Boolean)
  }
  if (typeof val === 'string') {
    const trimmed = val.trim()
    if (!trimmed) return []
    if (trimmed.includes('\n')) {
      return trimmed
        .split('\n')
        .map((s) => s.replace(/^[-*•]\s*/, '').trim())
        .filter(Boolean)
    }
    return [trimmed]
  }
  return []
}

// --------------------------------------------------------------------------
// Tab 1: Formatted Markdown Dossier
// --------------------------------------------------------------------------
const markdownDossier = computed(() => {
  const c = currentCompany.value
  if (!c) return ''
  const cr = getSafeResearch(c)

  const lines = []
  lines.push(`# Company Intelligence Dossier: ${c.name || 'Company'}`)
  if (c.domain) lines.push(`- **Website / Domain:** https://${c.domain}`)
  if (c.about_url) lines.push(`- **About Page:** ${c.about_url}`)
  lines.push('')

  // 1. Mission & Core Products
  const summaryText = normalizeText(cr.summary)
  lines.push('## 1. Mission & Core Products')
  lines.push(summaryText || '_Not yet researched._')
  lines.push('')

  // 2. Customers & Problem Space
  const missionText = normalizeText(cr.company_mission_and_customer)
  if (missionText) {
    lines.push('## 2. Customers & Problem Space')
    lines.push(missionText)
    lines.push('')
  }

  // 3. Engineering Culture & Tech Stack
  const cultureText = normalizeText(cr.engineering_culture)
  if (cultureText) {
    lines.push('## 3. Engineering Culture & Tech Stack')
    lines.push(cultureText)
    lines.push('')
  }

  // 4. Products & Technical Domains
  const products = toList(cr.products_and_technical_domain)
  if (products.length > 0) {
    lines.push('## 4. Products & Technical Domains')
    products.forEach((p) => lines.push(`- ${p}`))
    lines.push('')
  }

  // 5. Recent Initiatives & Milestones
  const initiatives = toList(cr.recent_initiatives)
  if (initiatives.length > 0) {
    lines.push('## 5. Recent Initiatives & Milestones')
    if (Array.isArray(cr.recent_initiatives)) {
      initiatives.forEach((i) => lines.push(`- ${i}`))
    } else {
      lines.push(normalizeText(cr.recent_initiatives))
    }
    lines.push('')
  }

  // 6. Strategic Priorities
  const priorities = toList(cr.strategic_priorities)
  if (priorities.length > 0) {
    lines.push('## 6. Strategic Priorities')
    priorities.forEach((p) => lines.push(`- ${p}`))
    lines.push('')
  }

  // 7. Company Language to Mirror
  const language = toList(cr.language_to_mirror)
  if (language.length > 0) {
    lines.push('## 7. Company Language to Mirror')
    language.forEach((l) => lines.push(`- ${l}`))
    lines.push('')
  }

  // 8. Candidate Alignment Angles
  const angles = toList(cr.candidate_alignment_angles)
  if (angles.length > 0) {
    lines.push('## 8. Candidate Alignment Angles')
    angles.forEach((a) => lines.push(`- ${a}`))
    lines.push('')
  }

  // 9. Verified Facts & Metrics
  const facts = toList(cr.verified_facts)
  if (facts.length > 0) {
    lines.push('## 9. Verified Facts & Metrics')
    facts.forEach((f) => lines.push(`- ${f}`))
    lines.push('')
  }

  // Optional candidate notes, pros, and red flags
  if (includeNotes.value) {
    const hasNotes = Boolean(c.notes && typeof c.notes === 'string' && c.notes.trim())
    const pros = toList(c.pros)
    const flags = toList(c.red_flags)

    if (hasNotes || pros.length > 0 || flags.length > 0) {
      lines.push('---')
      lines.push('## Candidate Private Notes & Signals')
      if (hasNotes) {
        lines.push('### Personal Notes')
        lines.push(c.notes.trim())
        lines.push('')
      }
      if (pros.length > 0) {
        lines.push('### Key Pros')
        pros.forEach((p) => lines.push(`- ${p}`))
        lines.push('')
      }
      if (flags.length > 0) {
        lines.push('### Red Flags & Watchouts')
        flags.forEach((f) => lines.push(`- ${f}`))
        lines.push('')
      }
    }
  }

  return lines.join('\n')
})

async function copyMarkdown() {
  if (!markdownDossier.value) return
  try {
    await navigator.clipboard.writeText(markdownDossier.value)
    copiedMarkdown.value = true
    uiStore.showToast('Company Markdown dossier copied to clipboard!', 'success')
    setTimeout(() => {
      copiedMarkdown.value = false
    }, 2200)
  } catch (err) {
    uiStore.showToast('Failed to copy to clipboard', 'error')
  }
}

// --------------------------------------------------------------------------
// Tab 2: AI Prompt to Fill Missing Info
// --------------------------------------------------------------------------
const llmPrompt = computed(() => {
  const c = currentCompany.value
  if (!c) return ''
  const cr = getSafeResearch(c)

  const knownSections = []
  const summaryText = normalizeText(cr.summary)
  if (summaryText) knownSections.push(`- Summary: ${summaryText.slice(0, 180)}...`)
  const cultureText = normalizeText(cr.engineering_culture)
  if (cultureText) knownSections.push(`- Culture & Tech Stack: ${cultureText.slice(0, 180)}...`)
  const products = toList(cr.products_and_technical_domain)
  if (products.length) knownSections.push(`- Known Products: ${products.slice(0, 4).join(', ')}`)

  const missingFields = []
  if (!summaryText) missingFields.push('- `summary`: Executive overview of the company, mission, and industry positioning.')
  if (!normalizeText(cr.company_mission_and_customer)) missingFields.push('- `company_mission_and_customer`: Core mission statement, target customers (B2B/B2C/Enterprise), and problem space.')
  if (!cultureText) missingFields.push('- `engineering_culture`: Engineering culture, development methodology, architecture, and technology stack.')
  const initiatives = toList(cr.recent_initiatives)
  if (!initiatives.length) missingFields.push('- `recent_initiatives`: Major recent product launches, engineering milestones, or business changes.')
  if (!products.length) missingFields.push('- `products_and_technical_domain`: Array of core products, platforms, and technical domain specializations.')
  const priorities = toList(cr.strategic_priorities)
  if (!priorities.length) missingFields.push('- `strategic_priorities`: Array of current strategic business and tech priorities.')
  const language = toList(cr.language_to_mirror)
  if (!language.length) missingFields.push('- `language_to_mirror`: Array of company-specific terminology, product mantras, and cultural buzzwords to mirror.')
  const angles = toList(cr.candidate_alignment_angles)
  if (!angles.length) missingFields.push('- `candidate_alignment_angles`: Array of strategic positioning angles for candidates interviewing here.')

  return `You are an expert tech company researcher and career strategist.
I need comprehensive, up-to-date intelligence on "${c.name || 'Company'}"${c.domain ? ` (Domain: ${c.domain})` : ''} to prepare for job applications and technical interviews.

### EXISTING KNOWN CONTEXT:
- Company Name: ${c.name || 'Unknown'}
- Domain: ${c.domain || 'Not specified'}
${c.about_url ? `- About URL: ${c.about_url}` : ''}
${knownSections.length ? knownSections.join('\n') : '- No previous research recorded.'}

### REQUIRED INTELLIGENCE TO FILL / ENRICH:
${missingFields.length ? missingFields.join('\n') : 'Please review and enrich all sections with current, high-fidelity information.'}

### OUTPUT INSTRUCTIONS:
1. Conduct thorough research based on public sources (company website, engineering blogs, tech talks, public roadmaps, press releases).
2. Return ONLY a single raw valid JSON object matching the schema below.
3. Do NOT wrap with conversational preamble or commentary outside the JSON block.

\`\`\`json
{
  "summary": "Concise 2-3 paragraph overview of the company, business model, and market position.",
  "company_mission_and_customer": "Core mission statement, target customer segments, and problem space solved.",
  "engineering_culture": "Engineering culture, architecture principles, tech stack, and dev practices.",
  "recent_initiatives": "Major recent tech launches, engineering milestones, or strategic pivots.",
  "products_and_technical_domain": [
    "Core product or platform 1",
    "Technical domain or solution 2"
  ],
  "strategic_priorities": [
    "Priority 1",
    "Priority 2"
  ],
  "language_to_mirror": [
    "Company keyword or internal mantra 1",
    "Domain term 2"
  ],
  "candidate_alignment_angles": [
    "Strategic angle 1: how a candidate can create impact",
    "Strategic angle 2: positioning narrative"
  ]
}
\`\`\``
})

async function copyPrompt() {
  if (!llmPrompt.value) return
  try {
    await navigator.clipboard.writeText(llmPrompt.value)
    copiedPrompt.value = true
    uiStore.showToast('AI prompt copied! Paste into Claude, ChatGPT, or Gemini.', 'success')
    setTimeout(() => {
      copiedPrompt.value = false
    }, 2200)
  } catch (err) {
    uiStore.showToast('Failed to copy prompt to clipboard', 'error')
  }
}

// --------------------------------------------------------------------------
// Tab 3: Import & Overwrite JSON
// --------------------------------------------------------------------------
function stripCodeFences(text) {
  if (!text) return ''
  let clean = text.trim()
  if (clean.startsWith('```')) {
    clean = clean.replace(/^```(?:json)?\s*\n?/, '').replace(/\n?```\s*$/, '')
  }
  return clean.trim()
}

const validationResult = computed(() => {
  const raw = stripCodeFences(importJsonText.value)
  if (!raw) {
    return {
      status: 'empty',
      message: 'Paste JSON to validate and preview detected fields.',
      isValid: false,
      parsed: null,
      detectedFields: [],
    }
  }

  let parsed
  try {
    parsed = JSON.parse(raw)
  } catch (err) {
    return {
      status: 'syntax_error',
      message: `Invalid JSON syntax: ${err.message}`,
      isValid: false,
      parsed: null,
      detectedFields: [],
    }
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return {
      status: 'not_object',
      message: 'JSON must be a key-value object {...}, not an array or primitive value.',
      isValid: false,
      parsed: null,
      detectedFields: [],
    }
  }

  const KNOWN_FIELDS = [
    { key: 'summary', label: 'Summary', type: 'text' },
    { key: 'company_mission_and_customer', label: 'Mission & Customer', type: 'text' },
    { key: 'engineering_culture', label: 'Culture & Tech Stack', type: 'text' },
    { key: 'recent_initiatives', label: 'Recent Initiatives', type: 'flexible' },
    { key: 'products_and_technical_domain', label: 'Products', type: 'list' },
    { key: 'strategic_priorities', label: 'Priorities', type: 'list' },
    { key: 'language_to_mirror', label: 'Language to Mirror', type: 'list' },
    { key: 'candidate_alignment_angles', label: 'Alignment Angles', type: 'list' },
    { key: 'verified_facts', label: 'Verified Facts', type: 'list' },
  ]

  const detected = []
  for (const f of KNOWN_FIELDS) {
    const val = parsed[f.key]
    if (val != null) {
      if (f.type === 'text') {
        const str = normalizeText(val)
        if (str) {
          detected.push({ key: f.key, label: f.label, count: str.length, isList: false })
        }
      } else if (f.type === 'list') {
        const list = toList(val)
        if (list.length > 0) {
          detected.push({ key: f.key, label: f.label, count: list.length, isList: true })
        }
      } else if (f.type === 'flexible') {
        if (Array.isArray(val) && val.length > 0) {
          detected.push({ key: f.key, label: f.label, count: val.length, isList: true })
        } else {
          const str = normalizeText(val)
          if (str) {
            detected.push({ key: f.key, label: f.label, count: str.length, isList: false })
          }
        }
      }
    }
  }

  if (detected.length === 0) {
    return {
      status: 'no_fields',
      message: 'JSON object contains no recognized company intelligence fields or all fields are empty.',
      isValid: false,
      parsed: null,
      detectedFields: [],
    }
  }

  return {
    status: 'valid',
    message: 'Valid intelligence payload ready to apply.',
    isValid: true,
    parsed,
    detectedFields: detected,
  }
})

async function handleApplyImport() {
  const c = currentCompany.value
  if (!validationResult.value.isValid || !c) return
  isSubmittingImport.value = true
  try {
    const data = validationResult.value.parsed
    const existingResearch = getSafeResearch(c)
    const cleanedResearch = {
      ...existingResearch,
      summary: normalizeText(data.summary),
      company_mission_and_customer: normalizeText(data.company_mission_and_customer),
      engineering_culture: normalizeText(data.engineering_culture),
      recent_initiatives: Array.isArray(data.recent_initiatives)
        ? toList(data.recent_initiatives)
        : normalizeText(data.recent_initiatives),
      products_and_technical_domain: toList(data.products_and_technical_domain),
      strategic_priorities: toList(data.strategic_priorities),
      language_to_mirror: toList(data.language_to_mirror),
      candidate_alignment_angles: toList(data.candidate_alignment_angles),
    }
    if (data.verified_facts) {
      cleanedResearch.verified_facts = Array.isArray(data.verified_facts)
        ? data.verified_facts
        : toList(data.verified_facts)
    }

    const payload = {
      company_research: cleanedResearch,
      research_status: 'COMPLETED',
    }

    const res = await CompaniesAPI.update(c.id, payload)
    activeCompany.value = res.data
    uiStore.showToast(`Company intelligence updated for "${c.name}"!`, 'success')
    emit('imported', res.data)
    closeModal()
  } catch (err) {
    uiStore.showToast(err.response?.data?.detail || 'Failed to update company research', 'error')
  } finally {
    isSubmittingImport.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="modelValue"
        class="modal-backdrop"
        role="dialog"
        aria-modal="true"
        aria-label="Company Intelligence Export & Import"
        @click.self="closeModal"
      >
        <div class="modal-card intel-modal">
          <!-- Header -->
          <div class="modal-header">
            <div class="modal-header-title-wrap">
              <div class="modal-header-icon-wrap">
                <Share2 :size="18" class="icon-primary" />
              </div>
              <div>
                <h3 class="modal-title">Company Intelligence Hub</h3>
                <p class="modal-subtitle">
                  {{ currentCompany?.name || 'Company' }} — Export for external AI models or import verified research
                </p>
              </div>
            </div>
            <button
              type="button"
              class="btn-close"
              title="Close modal"
              :disabled="isSubmittingImport"
              @click="closeModal"
            >
              <X :size="18" />
            </button>
          </div>

          <!-- Navigation Tabs -->
          <div class="intel-modal-tabs">
            <button
              type="button"
              class="intel-tab-btn"
              :class="{ active: activeTab === 'export' }"
              @click="activeTab = 'export'"
            >
              <FileText :size="14" />
              <span>Export Dossier</span>
            </button>
            <button
              type="button"
              class="intel-tab-btn"
              :class="{ active: activeTab === 'prompt' }"
              @click="activeTab = 'prompt'"
            >
              <Sparkles :size="14" />
              <span>AI Prompt (Fill Info)</span>
            </button>
            <button
              type="button"
              class="intel-tab-btn"
              :class="{ active: activeTab === 'import' }"
              @click="activeTab = 'import'"
            >
              <Upload :size="14" />
              <span>Import JSON</span>
            </button>
          </div>

          <!-- Body Content -->
          <div class="modal-body">
            <!-- TAB 1: EXPORT DOSSIER -->
            <div v-if="activeTab === 'export'" class="tab-pane-content">
              <div class="tab-controls-row">
                <label class="toggle-checkbox-label">
                  <input
                    v-model="includeNotes"
                    type="checkbox"
                    class="custom-checkbox"
                  />
                  <span>Include private candidate notes, pros & red flags</span>
                </label>
                <button
                  type="button"
                  class="btn btn-primary btn-sm btn-copy-action"
                  @click="copyMarkdown"
                >
                  <Check v-if="copiedMarkdown" :size="14" />
                  <Copy v-else :size="14" />
                  <span>{{ copiedMarkdown ? 'Copied!' : 'Copy Markdown' }}</span>
                </button>
              </div>

              <div class="preview-box-wrap">
                <textarea
                  readonly
                  class="markdown-preview-textarea"
                  :value="markdownDossier"
                  aria-label="Markdown Dossier Preview"
                ></textarea>
              </div>
            </div>

            <!-- TAB 2: AI PROMPT TO FILL INFO -->
            <div v-else-if="activeTab === 'prompt'" class="tab-pane-content">
              <div class="tab-explainer-banner">
                <Sparkles :size="16" class="icon-primary flex-shrink-0" />
                <p class="text-xs">
                  Copy this prompt into Claude, ChatGPT, or Gemini. It lists what is currently known about <strong>{{ currentCompany?.name || 'this company' }}</strong>, highlights missing fields, and specifies the exact JSON schema to return.
                </p>
              </div>

              <div class="tab-controls-row">
                <span class="text-xs text-muted">Ready-to-paste prompt template:</span>
                <button
                  type="button"
                  class="btn btn-primary btn-sm btn-copy-action"
                  @click="copyPrompt"
                >
                  <Check v-if="copiedPrompt" :size="14" />
                  <Copy v-else :size="14" />
                  <span>{{ copiedPrompt ? 'Copied!' : 'Copy AI Prompt' }}</span>
                </button>
              </div>

              <div class="preview-box-wrap">
                <textarea
                  readonly
                  class="prompt-preview-textarea"
                  :value="llmPrompt"
                  aria-label="AI Prompt Preview"
                ></textarea>
              </div>
            </div>

            <!-- TAB 3: IMPORT & OVERWRITE JSON -->
            <div v-else-if="activeTab === 'import'" class="tab-pane-content">
              <div class="tab-explainer-banner">
                <Upload :size="16" class="icon-primary flex-shrink-0" />
                <p class="text-xs">
                  Paste the JSON object generated by Claude, ChatGPT, or Gemini. We will automatically validate the syntax, check that it contains company intelligence, and allow you to overwrite this company profile.
                </p>
              </div>

              <div class="form-group">
                <label class="form-label" for="import-json-textarea">
                  <span>Paste AI-Generated JSON</span>
                  <span class="text-muted font-normal text-xs">(Markdown code fences are automatically stripped)</span>
                </label>
                <textarea
                  id="import-json-textarea"
                  ref="importTextareaRef"
                  v-model="importJsonText"
                  class="form-textarea import-code-textarea"
                  rows="9"
                  placeholder='{\n  "summary": "...",\n  "engineering_culture": "...",\n  "products_and_technical_domain": ["..."]\n}'
                  :disabled="isSubmittingImport"
                ></textarea>
              </div>

              <!-- Validation Feedback Box -->
              <div
                class="validation-status-card"
                :class="`status-${validationResult.status}`"
              >
                <div class="status-header">
                  <CheckCircle2
                    v-if="validationResult.status === 'valid'"
                    :size="16"
                    class="status-icon icon-success"
                  />
                  <AlertCircle
                    v-else-if="validationResult.status === 'syntax_error' || validationResult.status === 'not_object'"
                    :size="16"
                    class="status-icon icon-error"
                  />
                  <AlertTriangle
                    v-else-if="validationResult.status === 'no_fields'"
                    :size="16"
                    class="status-icon icon-warning"
                  />
                  <span v-else class="status-icon-dot"></span>
                  <span class="status-message">{{ validationResult.message }}</span>
                </div>

                <!-- Detected Fields Badges -->
                <div v-if="validationResult.detectedFields.length" class="detected-fields-grid">
                  <div
                    v-for="field in validationResult.detectedFields"
                    :key="field.key"
                    class="detected-field-badge"
                  >
                    <Check :size="12" class="field-check-icon" />
                    <span class="field-badge-name">{{ field.label }}</span>
                    <span class="field-badge-count">
                      {{ field.isList ? `${field.count} items` : `${field.count} chars` }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Overwrite Warning Banner -->
              <div v-if="validationResult.isValid" class="overwrite-warning-banner">
                <AlertTriangle :size="14" class="warning-icon" />
                <span>
                  Note: Applying will replace the current intelligence profile for <strong>{{ currentCompany?.name || 'this company' }}</strong>.
                </span>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="isSubmittingImport"
              @click="closeModal"
            >
              {{ activeTab === 'import' ? 'Cancel' : 'Close' }}
            </button>

            <button
              v-if="activeTab === 'export'"
              type="button"
              class="btn btn-primary btn-sm"
              @click="copyMarkdown"
            >
              <Check v-if="copiedMarkdown" :size="14" />
              <Copy v-else :size="14" />
              <span>{{ copiedMarkdown ? 'Copied!' : 'Copy Markdown' }}</span>
            </button>

            <button
              v-else-if="activeTab === 'prompt'"
              type="button"
              class="btn btn-primary btn-sm"
              @click="copyPrompt"
            >
              <Check v-if="copiedPrompt" :size="14" />
              <Copy v-else :size="14" />
              <span>{{ copiedPrompt ? 'Copied!' : 'Copy AI Prompt' }}</span>
            </button>

            <button
              v-else-if="activeTab === 'import'"
              type="button"
              class="btn btn-primary btn-sm btn-apply-overwrite"
              :disabled="!validationResult.isValid || isSubmittingImport"
              @click="handleApplyImport"
            >
              <Loader2 v-if="isSubmittingImport" :size="14" class="animate-spin" />
              <Check v-else :size="14" />
              <span>Apply & Overwrite Research</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: var(--bg-backdrop, rgba(0, 0, 0, 0.75));
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100000;
  padding: 16px;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-card {
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-fade-enter-from .modal-card {
  transform: scale(0.96) translateY(8px);
}

.intel-modal {
  width: 100%;
  max-width: 680px;
  max-height: 90vh;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg, 8px);
  box-shadow: var(--shadow-xl, 0 20px 25px -5px rgba(0, 0, 0, 0.4));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: var(--font-sans);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background-color: var(--bg-surface);
  flex-shrink: 0;
}

.modal-header-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md, 6px);
  background: var(--primary-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-primary {
  color: var(--primary);
}

.modal-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 2px 0 0 0;
}

.btn-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xs, 2px);
  transition: color var(--transition-fast, 0.15s ease), background var(--transition-fast, 0.15s ease);
}

.btn-close:hover {
  color: var(--text-main);
  background: var(--bg-surface-hover);
}

/* Tabs */
.intel-modal-tabs {
  display: flex;
  gap: 2px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  flex-shrink: 0;
}

.intel-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast, 0.15s ease);
}

.intel-tab-btn:hover {
  color: var(--text-main);
}

.intel-tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}

/* Body */
.modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  flex: 1;
}

.tab-pane-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tab-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toggle-checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}

.custom-checkbox {
  accent-color: var(--primary);
  cursor: pointer;
}

.tab-explainer-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background-color: var(--primary-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 6px);
  color: var(--text-main);
  line-height: 1.45;
}

.preview-box-wrap {
  position: relative;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 6px);
  background-color: var(--bg-input);
  overflow: hidden;
}

.markdown-preview-textarea,
.prompt-preview-textarea {
  width: 100%;
  height: 280px;
  padding: 12px 14px;
  background-color: transparent;
  border: none;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.55;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  white-space: pre;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

.import-code-textarea {
  width: 100%;
  padding: 10px 12px;
  background-color: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 6px);
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--transition-fast, 0.15s ease);
}

.import-code-textarea:focus {
  border-color: var(--primary);
}

/* Validation status card */
.validation-status-card {
  padding: 10px 12px;
  border-radius: var(--radius-md, 6px);
  border: 1px solid var(--border-color);
  background-color: var(--bg-elevated);
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--text-muted);
}

.icon-success {
  color: var(--text-success);
}

.icon-error {
  color: var(--text-danger);
}

.icon-warning {
  color: var(--text-warning);
}

.status-valid {
  border-color: var(--border-subtle);
  background-color: var(--bg-surface);
}

.status-syntax_error,
.status-not_object {
  border-color: var(--text-danger);
  background-color: var(--bg-surface);
}

.status-no_fields {
  border-color: var(--text-warning);
  background-color: var(--bg-surface);
}

.status-message {
  font-weight: 500;
  color: var(--text-main);
}

.detected-fields-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detected-field-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: var(--radius-sm, 4px);
  background-color: var(--primary-subtle);
  border: 1px solid var(--border-subtle);
  font-size: 11px;
}

.field-check-icon {
  color: var(--text-success);
}

.field-badge-name {
  font-weight: 600;
  color: var(--text-main);
}

.field-badge-count {
  color: var(--text-secondary);
}

.overwrite-warning-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--text-warning);
  border-radius: var(--radius-sm, 4px);
  color: var(--text-warning);
  font-size: 11px;
}

.warning-icon {
  flex-shrink: 0;
}

/* Footer */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid var(--border-subtle);
  background-color: var(--bg-surface);
  flex-shrink: 0;
}

.btn-copy-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-apply-overwrite {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
