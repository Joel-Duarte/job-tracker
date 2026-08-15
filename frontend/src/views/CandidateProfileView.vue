<script setup>
import { ref, onMounted } from 'vue'
import { useUIStore } from '../stores/uiStore'
import { CandidateProfileAPI } from '../api/endpoints'
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
} from 'lucide-vue-next'

const uiStore = useUIStore()

const profile = ref(null)
const rawCVInput = ref('')

function copyAnonymizedCV() {
  if (profile.value?.anonymized_text) {
    navigator.clipboard.writeText(profile.value.anonymized_text)
    uiStore.showToast('Sanitized CV copied to clipboard', 'info')
  }
}
const newSkillInput = ref('')
const isProcessing = ref(false)
const isSavingEdits = ref(false)
const isEditingSkills = ref(false)

async function loadProfile() {
  try {
    const res = await CandidateProfileAPI.get()
    if (res.data) {
      profile.value = res.data
      rawCVInput.value = res.data.raw_text || ''
    }
  } catch (err) {
    uiStore.showToast('Could not load CV profile', 'error')
  }
}

async function processCV() {
  if (!rawCVInput.value.trim() || rawCVInput.value.trim().length < 20) {
    uiStore.showToast('Please provide a complete resume or CV text.', 'error')
    return
  }

  isProcessing.value = true
  try {
    const res = await CandidateProfileAPI.save(rawCVInput.value.trim())
    profile.value = res.data
    uiStore.showToast('Resume de-identified and canonical skills extracted!', 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

function addSkill() {
  const skill = newSkillInput.value.trim()
  if (skill && profile.value && !profile.value.extracted_skills.includes(skill)) {
    profile.value.extracted_skills.push(skill)
    newSkillInput.value = ''
    saveProfileEdits()
  }
}

function removeSkill(skill) {
  if (profile.value) {
    profile.value.extracted_skills = profile.value.extracted_skills.filter((s) => s !== skill)
    saveProfileEdits()
  }
}

async function saveProfileEdits() {
  if (!profile.value) return
  isSavingEdits.value = true
  try {
    await CandidateProfileAPI.update(profile.value.id, {
      extracted_skills: profile.value.extracted_skills,
      anonymized_text: profile.value.anonymized_text,
    })
    uiStore.showToast('Skills updated', 'success')
  } catch (err) {
    uiStore.showToast(err.message, 'error')
  } finally {
    isSavingEdits.value = false
  }
}

onMounted(() => {
  loadProfile()
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
        Your CV is processed through an automated privacy sanitization step. Personal information and company names are de-identified, date windows are converted to durations, and canonical technical skills are extracted for programmatic pre-matching.
      </p>
    </div>

    <div class="profile-grid">
      <!-- Left Column: Raw Input & Trigger -->
      <div class="profile-col">
        <div class="card-box">
          <div class="box-header">
            <div class="box-title">
              <FileText :size="16" class="text-primary" />
              <span>Paste Resume / CV Content</span>
            </div>
            <span class="text-xs text-muted">Full raw text</span>
          </div>

          <p class="box-desc">
            Paste your raw resume text here. The AI de-identification model scrubs identifying attributes (real name, addresses, specific past employers) and converts date ranges into years/months.
          </p>

          <textarea
            v-model="rawCVInput"
            rows="14"
            class="form-textarea font-mono text-xs"
            placeholder="Paste your complete resume or CV text here..."
          ></textarea>

          <div class="box-actions">
            <button
              class="btn btn-primary"
              :disabled="isProcessing || !rawCVInput.trim()"
              @click="processCV"
            >
              <Loader2 v-if="isProcessing" class="animate-spin" :size="16" />
              <Sparkles v-else :size="16" />
              <span>{{ isProcessing ? 'De-Identifying & Extracting Skills...' : 'De-Identify & Save Profile' }}</span>
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
            <span class="badge badge-applied">
              {{ profile.years_of_experience ? `${profile.years_of_experience} yrs exp` : 'Active' }}
            </span>
          </div>

          <!-- Domain Badges -->
          <div v-if="profile.domain_expertise?.length" class="meta-tags-row">
            <span class="meta-label">Domain Expertise:</span>
            <span v-for="d in profile.domain_expertise" :key="d" class="domain-badge">
              {{ d }}
            </span>
          </div>

          <!-- Core Competencies -->
          <div v-if="profile.core_competencies?.length" class="meta-tags-row">
            <span class="meta-label">Core Competencies:</span>
            <span v-for="c in profile.core_competencies" :key="c" class="competency-badge">
              {{ c }}
            </span>
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

          <!-- De-Identified Resume Text Preview -->
          <div class="sanitized-preview">
            <div class="preview-header">
              <div>
                <span class="section-label">Sanitized Resume Preview</span>
                <span class="text-xs text-muted block">PII scrubbed • Dates converted to durations • Used for AI match assessments</span>
              </div>
              <button
                v-if="profile.anonymized_text"
                class="btn btn-ghost btn-xs"
                title="Copy sanitized resume text"
                @click="copyAnonymizedCV"
              >
                <Copy :size="13" />
                <span>Copy</span>
              </button>
            </div>
            <div class="sanitized-text font-mono text-xs">
              {{ profile.anonymized_text || 'No anonymized text generated yet.' }}
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
  margin-bottom: 28px;
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
}

.competency-badge {
  background-color: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-success);
  font-weight: 500;
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
  max-height: 160px;
  overflow-y: auto;
  padding: 4px 0;
}

.skill-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background-color: var(--status-applied-bg);
  color: var(--status-applied-text);
  border: 1px solid var(--status-applied-border);
  font-size: 11px;
  font-weight: 500;
}

.skill-remove-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  color: inherit;
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}

.skill-remove-btn:hover {
  opacity: 1;
}

.sanitized-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sanitized-text {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
  max-height: 180px;
  overflow-y: auto;
  white-space: pre-wrap;
  color: var(--text-main);
  line-height: 1.5;
}

.empty-profile-box {
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  padding: 40px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.empty-sub {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 320px;
  line-height: 1.4;
}
</style>
