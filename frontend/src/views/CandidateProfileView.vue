<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { CandidateProfileAPI, IntakeAPI } from '../api/endpoints'
import { scrubCVText } from '../utils/scrubber'
import {
  ShieldCheck,
  Sparkles,
  FileText,
  Clock,
  Briefcase,
  Layers,
  Plus,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  Eye,
  Edit3,
  Save,
  Copy,
  Lock,
  Shield,
  Info,
  Trash2,
  RotateCcw,
} from 'lucide-vue-next'

const uiStore = useUIStore()

const profile = ref(null)
const rawCVInput = ref('')
const activeInputTab = ref('raw') // 'raw' | 'preview'

// Programmatic local scrub calculation
const localScrubResult = computed(() => scrubCVText(rawCVInput.value))

// State for editing sanitized CV text
const isEditingCV = ref(false)
const editedCVText = ref('')

// Add item inputs
const newSkillInput = ref('')
const newCompetencyInput = ref('')
const newDomainInput = ref('')

const isProcessing = ref(false)
const currentTaskId = ref(null)
const currentTaskStage = ref('QUEUED')
const currentTaskStatus = ref('QUEUED')
const isSavingEdits = ref(false)
const isDeleting = ref(false)

async function loadProfile() {
  try {
    const res = await CandidateProfileAPI.get()
    if (res.data) {
      profile.value = res.data
      rawCVInput.value = res.data.raw_text || ''
    } else {
      profile.value = null
    }
  } catch (err) {
    uiStore.showToast('Could not load CV profile', 'error')
  }
}

async function pollTaskUntilComplete(taskId) {
  const maxAttempts = 300 // 5 minutes max
  let attempts = 0

  while (attempts < maxAttempts) {
    await new Promise((r) => setTimeout(r, 1000))
    attempts++

    try {
      const res = await CandidateProfileAPI.getTaskStatus(taskId)
      const task = res.data
      currentTaskStatus.value = task.status
      currentTaskStage.value = task.stage

      if (task.status === 'COMPLETED') {
        await loadProfile()
        uiStore.showToast('Resume de-identified and canonical profile activated!', 'success')
        isProcessing.value = false
        currentTaskId.value = null
        return
      }

      if (task.status === 'FAILED') {
        uiStore.showToast(task.error_message || 'CV processing failed', 'error')
        isProcessing.value = false
        currentTaskId.value = null
        return
      }
    } catch (err) {
      console.warn('Polling check anomaly, retrying...', err)
    }
  }

  uiStore.showToast('Task is taking longer than expected. It will continue running in the background.', 'info')
  isProcessing.value = false
}

async function processCV() {
  if (!rawCVInput.value.trim() || rawCVInput.value.trim().length < 20) {
    uiStore.showToast('Please provide a complete resume or CV text.', 'error')
    return
  }

  isProcessing.value = true
  currentTaskStatus.value = 'QUEUED'
  currentTaskStage.value = 'QUEUED'

  try {
    const res = await CandidateProfileAPI.save(rawCVInput.value.trim())
    const taskId = res.data.task_id
    currentTaskId.value = taskId
    await pollTaskUntilComplete(taskId)
  } catch (err) {
    uiStore.showToast(err.message || 'Failed to enqueue CV processing', 'error')
    isProcessing.value = false
  }
}

function startEditingCV() {
  editedCVText.value = profile.value?.anonymized_text || ''
  isEditingCV.value = true
}

function cancelEditingCV() {
  isEditingCV.value = false
}

async function saveEditedCV() {
  if (!profile.value) return
  isSavingEdits.value = true
  try {
    const res = await CandidateProfileAPI.update(profile.value.id, {
      anonymized_text: editedCVText.value,
    })
    profile.value.anonymized_text = res.data.anonymized_text
    isEditingCV.value = false
    uiStore.showToast('Sanitized CV updated successfully', 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSavingEdits.value = false
  }
}

function copyAnonymizedCV() {
  if (profile.value?.anonymized_text) {
    navigator.clipboard.writeText(profile.value.anonymized_text)
    uiStore.showToast('Sanitized CV copied to clipboard', 'info')
  }
}

// Skills management
function addSkill() {
  const skill = newSkillInput.value.trim()
  if (skill && profile.value) {
    if (!profile.value.extracted_skills) profile.value.extracted_skills = []
    if (!profile.value.extracted_skills.includes(skill)) {
      profile.value.extracted_skills.push(skill)
      newSkillInput.value = ''
      saveProfileField({ extracted_skills: profile.value.extracted_skills })
    }
  }
}

function removeSkill(skill) {
  if (profile.value?.extracted_skills) {
    profile.value.extracted_skills = profile.value.extracted_skills.filter((s) => s !== skill)
    saveProfileField({ extracted_skills: profile.value.extracted_skills })
  }
}

// Competencies management
function addCompetency() {
  const comp = newCompetencyInput.value.trim()
  if (comp && profile.value) {
    if (!profile.value.core_competencies) profile.value.core_competencies = []
    if (!profile.value.core_competencies.includes(comp)) {
      profile.value.core_competencies.push(comp)
      newCompetencyInput.value = ''
      saveProfileField({ core_competencies: profile.value.core_competencies })
    }
  }
}

function removeCompetency(comp) {
  if (profile.value?.core_competencies) {
    profile.value.core_competencies = profile.value.core_competencies.filter((c) => c !== comp)
    saveProfileField({ core_competencies: profile.value.core_competencies })
  }
}

// Domain expertise management
function addDomain() {
  const domain = newDomainInput.value.trim()
  if (domain && profile.value) {
    if (!profile.value.domain_expertise) profile.value.domain_expertise = []
    if (!profile.value.domain_expertise.includes(domain)) {
      profile.value.domain_expertise.push(domain)
      newDomainInput.value = ''
      saveProfileField({ domain_expertise: profile.value.domain_expertise })
    }
  }
}

function removeDomain(domain) {
  if (profile.value?.domain_expertise) {
    profile.value.domain_expertise = profile.value.domain_expertise.filter((d) => d !== domain)
    saveProfileField({ domain_expertise: profile.value.domain_expertise })
  }
}

async function saveProfileField(patchData) {
  if (!profile.value) return
  isSavingEdits.value = true
  try {
    const res = await CandidateProfileAPI.update(profile.value.id, patchData)
    profile.value = res.data
    uiStore.showToast('Profile updated', 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSavingEdits.value = false
  }
}

async function deleteProfile() {
  if (!profile.value) return
  if (!confirm('Are you sure you want to delete this Candidate Profile? Pre-screening matching will be deactivated until a new CV is added.')) {
    return
  }

  isDeleting.value = true
  try {
    await CandidateProfileAPI.delete(profile.value.id)
    profile.value = null
    rawCVInput.value = ''
    uiStore.showToast('Candidate profile cleared', 'info')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isDeleting.value = false
  }
}

onMounted(async () => {
  await loadProfile()
  try {
    const res = await IntakeAPI.getEvaluations(20)
    if (Array.isArray(res.data)) {
      const activeCVTask = res.data.find(
        (t) => t.task_type === 'CV_EXTRACTION' && ['QUEUED', 'PROCESSING'].includes(t.status)
      )
      if (activeCVTask) {
        isProcessing.value = true
        currentTaskId.value = activeCVTask.id
        currentTaskStatus.value = activeCVTask.status
        currentTaskStage.value = activeCVTask.stage
        pollTaskUntilComplete(activeCVTask.id)
      }
    }
  } catch (err) {
    // ignore
  }
})
</script>

<template>
  <div class="page-container">
    <div class="profile-header">
      <div class="header-badge">
        <ShieldCheck :size="14" />
        <span>Privacy-First Candidate Profile</span>
      </div>
      <h1 class="page-title">Candidate CV & Skills Profile</h1>
      <p class="page-subtitle">
        Your CV is sanitized locally to strip identifying contacts before processing. The AI de-identifies company names, converts date windows to durations, and extracts canonical technical skills for pre-matching.
      </p>
    </div>

    <!-- Cloud vs Local Privacy Advisory Banner -->
    <div class="cloud-privacy-advisory">
      <div class="advisory-icon">
        <Info :size="18" />
      </div>
      <div class="advisory-text">
        <strong>Privacy Tip for Cloud AI Models:</strong>
        <span> If you have configured an external cloud provider (OpenAI, Claude, Gemini, OpenRouter), we strongly recommend replacing specific employer names with generic tags (e.g. <code>[Tier-1 Tech Enterprise]</code>, <code>[Fintech Scaleup]</code>, <code>[E-commerce Startup]</code>) in your raw text before submission. When using local models (Ollama, LM Studio), all processing is 100% private and on-device.</span>
      </div>
    </div>

    <div class="profile-grid">
      <!-- Left Column: Raw Input & Trigger -->
      <div class="profile-col">
        <div class="card-box">
          <div class="box-header">
            <div class="box-title">
              <FileText :size="16" class="text-primary" />
              <span>Resume / CV Content</span>
            </div>
            
            <!-- Input Tabs -->
            <div class="input-tabs">
              <button
                class="tab-btn"
                :class="{ active: activeInputTab === 'raw' }"
                @click="activeInputTab = 'raw'"
              >
                Raw Input
              </button>
              <button
                class="tab-btn"
                :class="{ active: activeInputTab === 'preview' }"
                @click="activeInputTab = 'preview'"
              >
                <Lock :size="12" />
                <span>Local Scrubbed Preview</span>
              </button>
            </div>
          </div>

          <!-- Privacy Shield Advisory Banner -->
          <div class="privacy-shield-callout">
            <div class="shield-callout-header">
              <Shield :size="15" class="text-success flex-shrink-0" />
              <div class="shield-callout-title">
                <strong>Zero-Cloud PII Transmission:</strong> Emails, phones, links, and addresses are scrubbed locally on your device before sending to the AI model.
              </div>
            </div>
            <div v-if="localScrubResult.stats.total > 0" class="shield-stats-badge">
              🛡️ <strong>{{ localScrubResult.stats.total }}</strong> PII item(s) sanitized locally:
              <span v-if="localScrubResult.stats.emails">{{ localScrubResult.stats.emails }} email(s) </span>
              <span v-if="localScrubResult.stats.phones">{{ localScrubResult.stats.phones }} phone(s) </span>
              <span v-if="localScrubResult.stats.urls">{{ localScrubResult.stats.urls }} link(s) </span>
              <span v-if="localScrubResult.stats.addresses">{{ localScrubResult.stats.addresses }} address(es)</span>
            </div>
          </div>

          <!-- Raw Input Tab -->
          <textarea
            v-if="activeInputTab === 'raw'"
            v-model="rawCVInput"
            rows="14"
            class="form-textarea font-mono text-xs"
            placeholder="Paste your complete resume or CV text here..."
          ></textarea>

          <!-- Local Scrubbed Preview Tab -->
          <div
            v-else
            class="local-preview-box font-mono text-xs"
          >
            {{ localScrubResult.scrubbedText || 'Paste resume text to see live local sanitization preview...' }}
          </div>

          <!-- Live Queue Task Progress Card -->
          <div v-if="isProcessing" class="queue-progress-card animate-fade-in">
            <div class="queue-progress-header">
              <div class="queue-status-title">
                <Loader2 class="animate-spin text-primary" :size="16" />
                <span>Processing in AI Queue (Task #{{ currentTaskId || '...' }})</span>
              </div>
              <span class="queue-stage-badge">{{ currentTaskStage }}</span>
            </div>

            <!-- Stepper Indicators -->
            <div class="stepper-track">
              <div
                class="stepper-step"
                :class="{
                  active: currentTaskStage === 'SCRUBBING',
                  complete: ['EXTRACTING', 'SAVING', 'COMPLETE'].includes(currentTaskStage),
                }"
              >
                <div class="step-dot">1</div>
                <span class="step-label">Local PII Scrubbing</span>
              </div>

              <div
                class="stepper-step"
                :class="{
                  active: currentTaskStage === 'EXTRACTING',
                  complete: ['SAVING', 'COMPLETE'].includes(currentTaskStage),
                }"
              >
                <div class="step-dot">2</div>
                <span class="step-label">AI Extraction</span>
              </div>

              <div
                class="stepper-step"
                :class="{
                  active: currentTaskStage === 'SAVING',
                  complete: currentTaskStage === 'COMPLETE',
                }"
              >
                <div class="step-dot">3</div>
                <span class="step-label">Profile Activation</span>
              </div>
            </div>
          </div>

          <div class="box-actions">
            <button
              class="btn btn-primary"
              :disabled="isProcessing || !rawCVInput.trim()"
              @click="processCV"
            >
              <Loader2 v-if="isProcessing" class="animate-spin" :size="16" />
              <Sparkles v-else :size="16" />
              <span>{{ isProcessing ? 'Processing in Queue...' : 'De-Identify & Save Profile' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Right Column: Extracted Canonical Profile -->
      <div class="profile-col">
        <div v-if="profile" class="card-box animate-fade-in">
          <div class="box-header">
            <div class="box-title">
              <ShieldCheck :size="16" class="text-success" />
              <span>Active De-Identified Profile</span>
            </div>
            <div class="header-right-actions">
              <span class="badge badge-applied">
                {{ profile.years_of_experience ? `${profile.years_of_experience} yrs exp` : 'Active' }}
              </span>
              <button
                class="btn btn-ghost btn-xs text-danger"
                title="Delete Profile"
                :disabled="isDeleting"
                @click="deleteProfile"
              >
                <Trash2 :size="13" />
              </button>
            </div>
          </div>

          <!-- Domain Badges & Input -->
          <div class="meta-section">
            <div class="meta-section-header">
              <span class="meta-label">Domain Expertise ({{ profile.domain_expertise?.length || 0 }})</span>
            </div>
            <div class="meta-tags-row">
              <span v-for="d in profile.domain_expertise" :key="d" class="domain-badge">
                <span>{{ d }}</span>
                <button class="chip-remove" @click="removeDomain(d)"><X :size="10" /></button>
              </span>
              <div class="inline-add">
                <input
                  v-model="newDomainInput"
                  type="text"
                  placeholder="+ Add domain..."
                  class="inline-input"
                  @keydown.enter.prevent="addDomain"
                />
              </div>
            </div>
          </div>

          <!-- Core Competencies Badges & Input -->
          <div class="meta-section">
            <div class="meta-section-header">
              <span class="meta-label">Core Competencies ({{ profile.core_competencies?.length || 0 }})</span>
            </div>
            <div class="meta-tags-row">
              <span v-for="c in profile.core_competencies" :key="c" class="competency-badge">
                <span>{{ c }}</span>
                <button class="chip-remove" @click="removeCompetency(c)"><X :size="10" /></button>
              </span>
              <div class="inline-add">
                <input
                  v-model="newCompetencyInput"
                  type="text"
                  placeholder="+ Add competency..."
                  class="inline-input"
                  @keydown.enter.prevent="addCompetency"
                />
              </div>
            </div>
          </div>

          <!-- Skills Management Section -->
          <div class="skills-section">
            <div class="section-top">
              <span class="section-label">Canonical Skills ({{ profile.extracted_skills?.length || 0 }})</span>
              <span class="text-xs text-muted">Used for programmatic pre-screening</span>
            </div>

            <!-- Add Skill Input -->
            <div class="add-skill-bar">
              <input
                v-model="newSkillInput"
                type="text"
                placeholder="Add custom skill (e.g. FastAPI, PostgreSQL, Docker)..."
                class="form-input text-xs"
                @keydown.enter.prevent="addSkill"
              />
              <button class="btn btn-secondary btn-sm" @click="addSkill">
                <Plus :size="14" />
                <span>Add</span>
              </button>
            </div>

            <!-- Skills Tag Cloud -->
            <div class="skills-cloud">
              <span
                v-for="skill in profile.extracted_skills"
                :key="skill"
                class="skill-chip"
              >
                <span>{{ skill }}</span>
                <button class="skill-remove-btn" @click="removeSkill(skill)">
                  <X :size="11" />
                </button>
              </span>
            </div>
          </div>

          <!-- De-Identified Resume Text Preview & Editor -->
          <div class="sanitized-preview">
            <div class="preview-header">
              <div>
                <span class="section-label">Sanitized Resume Preview</span>
                <span class="text-xs text-muted block">Used for AI match assessments & qualification audits</span>
              </div>
              <div class="preview-actions">
                <button
                  v-if="!isEditingCV && profile.anonymized_text"
                  class="btn btn-ghost btn-xs"
                  title="Edit sanitized resume"
                  @click="startEditingCV"
                >
                  <Edit3 :size="13" />
                  <span>Edit</span>
                </button>
                <button
                  v-if="!isEditingCV && profile.anonymized_text"
                  class="btn btn-ghost btn-xs"
                  title="Copy sanitized resume text"
                  @click="copyAnonymizedCV"
                >
                  <Copy :size="13" />
                  <span>Copy</span>
                </button>
              </div>
            </div>

            <!-- Read-only View -->
            <div v-if="!isEditingCV" class="sanitized-text font-mono text-xs">
              {{ profile.anonymized_text || 'No anonymized text generated yet.' }}
            </div>

            <!-- In-place Editor -->
            <div v-else class="cv-editor-box">
              <textarea
                v-model="editedCVText"
                rows="10"
                class="form-textarea font-mono text-xs"
              ></textarea>
              <div class="cv-editor-actions">
                <button class="btn btn-secondary btn-xs" @click="cancelEditingCV">
                  <RotateCcw :size="12" />
                  <span>Cancel</span>
                </button>
                <button class="btn btn-primary btn-xs" :disabled="isSavingEdits" @click="saveEditedCV">
                  <Loader2 v-if="isSavingEdits" class="animate-spin" :size="12" />
                  <Save v-else :size="12" />
                  <span>Save Changes</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-profile-box">
          <ShieldCheck :size="32" class="text-muted" />
          <div class="empty-title">No Candidate Profile Configured</div>
          <p class="empty-sub">
            Paste your CV in the left editor and click "De-Identify & Save Profile" to unlock automated keyword pre-screening and skill fit evaluations.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 60px;
}

.profile-header {
  text-align: center;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background-color: var(--status-offer-bg);
  color: var(--status-offer-text);
  border: 1px solid var(--status-offer-border);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 10px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main);
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 680px;
  margin-top: 4px;
  line-height: 1.5;
}

.cloud-privacy-advisory {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background-color: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.22);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: 24px;
  color: var(--text-main);
  font-size: 12px;
  line-height: 1.5;
}

.advisory-icon {
  color: #3b82f6;
  margin-top: 2px;
  flex-shrink: 0;
}

.advisory-text code {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 11px;
}

.profile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 860px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}

.card-box {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 22px;
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.box-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-tabs {
  display: flex;
  background-color: var(--bg-main);
  padding: 2px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  gap: 2px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-xs, 4px);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--text-main);
}

.tab-btn.active {
  background-color: var(--bg-surface);
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
}

.privacy-shield-callout {
  background-color: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.shield-callout-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.shield-callout-title {
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-main);
}

.shield-stats-badge {
  font-size: 11px;
  color: var(--text-success);
  margin-left: 23px;
  font-weight: 500;
}

.local-preview-box {
  width: 100%;
  min-height: 220px;
  max-height: 380px;
  overflow-y: auto;
  padding: 12px;
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  line-height: 1.5;
}

.box-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.box-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.box-actions {
  display: flex;
  justify-content: flex-end;
}

.meta-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meta-tags-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.meta-label {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.domain-badge {
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--primary);
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.competency-badge {
  background-color: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-success);
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.chip-remove {
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  padding: 0;
}

.chip-remove:hover {
  color: var(--text-danger, #ef4444);
}

.inline-add {
  display: inline-flex;
}

.inline-input {
  background: transparent;
  border: 1px dashed var(--border-color);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  color: var(--text-main);
  width: 110px;
}

.inline-input:focus {
  outline: none;
  border-color: var(--primary);
  width: 140px;
}

.skills-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
}

.add-skill-bar {
  display: flex;
  gap: 8px;
}

.skills-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-main);
}

.skill-remove-btn {
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 0;
}

.skill-remove-btn:hover {
  color: var(--text-danger);
}

.sanitized-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border-color);
  padding-top: 14px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
}

.preview-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sanitized-text {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  max-height: 260px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  line-height: 1.5;
}

.cv-editor-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cv-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.empty-profile-box {
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  padding: 48px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.empty-sub {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 380px;
  line-height: 1.5;
}

.queue-progress-card {
  background-color: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.queue-status-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
}

.queue-stage-badge {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--primary);
}

.stepper-track {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stepper-step {
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0.4;
  transition: all var(--transition-fast);
}

.stepper-step.active {
  opacity: 1;
  font-weight: 600;
  color: var(--primary);
}

.stepper-step.complete {
  opacity: 0.9;
  color: var(--text-success);
}

.step-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: var(--bg-elevated);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
}

.stepper-step.active .step-dot {
  background-color: var(--primary);
  color: white;
  border-color: var(--primary);
}

.stepper-step.complete .step-dot {
  background-color: var(--text-success);
  color: white;
  border-color: var(--text-success);
}

.step-label {
  font-size: 11px;
}
</style>
