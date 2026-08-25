# Responsive Design Guide & AI Agent Prompts

This guide defines global responsive standards for the Job Tracker Vue 3 application and provides modular, copy-pasteable prompts optimized for downstream AI coding agents. Each prompt provides explicit instructions to adapt views and components across mobile, tablet, and desktop viewports while preserving design philosophy, Vue 3 reactivity, and Pinia state management.

---

## 1. Global Responsive Standards

### Breakpoints & Viewport Tokens
| Device Tier | Breakpoint Query | Target Viewport Range | Key Layout Behavior |
| :--- | :--- | :--- | :--- |
| **Mobile** | `@media (max-width: 767px)` | `< 768px` | Single-column stacking, collapsible hamburger menu drawer, full-screen modals, bottom action bars, CSS horizontal scroll snap for Kanban boards. |
| **Tablet** | `@media (min-width: 768px) and (max-width: 1023px)` | `768px - 1023px` | 2-column grids, condensed navigation bar, semi-expanded sidebar drawers, auto-fit card grids. |
| **Desktop** | `@media (min-width: 1024px)` | `>= 1024px` | Full multi-column Kanban board, sticky sidebars, side-by-side split view panes, expanded data tables. |

```css
/* Responsive Design System Tokens (frontend/src/style.css) */
:root {
  --breakpoint-mobile: 767px;
  --breakpoint-tablet: 1023px;
  --breakpoint-desktop: 1024px;

  /* Fluid Spacing Scale */
  --space-xs: clamp(0.25rem, 0.5vw, 0.375rem);
  --space-sm: clamp(0.5rem, 1vw, 0.75rem);
  --space-md: clamp(0.875rem, 1.5vw, 1.25rem);
  --space-lg: clamp(1.25rem, 2.5vw, 2rem);
  --space-xl: clamp(1.75rem, 3.5vw, 3rem);

  /* Fluid Typography Scale */
  --font-size-xs: clamp(0.7rem, 0.75vw, 0.75rem);
  --font-size-sm: clamp(0.75rem, 0.85vw, 0.8125rem);
  --font-size-base: clamp(0.8125rem, 1vw, 0.875rem);
  --font-size-lg: clamp(0.9375rem, 1.25vw, 1.125rem);
  --font-size-xl: clamp(1.125rem, 1.75vw, 1.5rem);
  --font-size-2xl: clamp(1.375rem, 2.25vw, 2rem);

  /* Touch Targets */
  --min-touch-target: 48px;
}
```

### Touch Targets & Accessibility Standards
- **Minimum Interactive Size**: All clickable controls (buttons, icon triggers, tabs, table action items, context menu triggers) MUST have a touch target area of at least `48x48px` on mobile (`< 768px`). Where visual size is smaller (e.g. 24x24px icons), transparent padding or pseudo-elements (`::after`) must expand the hit target to `48x48px`.
- **Form Control Sizing**: Text inputs, drop-down selects, and buttons on mobile must feature a minimum height of `44px` to prevent misclicks and zoom jumps on iOS (`font-size: 16px` on input focus if required).
- **Safe Area Insets**: Fixed floating bars, toasts, and mobile drawers must respect `env(safe-area-inset-bottom)` and `env(safe-area-inset-top)` for modern mobile devices (e.g., iPhone notch/home bar).

### Mobile Navigation & Layout Patterns
1. **Collapsible Header & Drawer**: Navigation controls collapse into a mobile slide-out drawer on `< 768px` viewports, accessed via a sticky top navbar hamburger trigger.
2. **Horizontal Scroll Snap (Kanban & Tables)**:
   - For Kanban columns on mobile, use `scroll-snap-type: x mandatory` with `scroll-snap-align: center` on `.kanban-column` elements to enable natural swipe gestures.
   - For data tables, container viewports wrap in an overflowing box with custom horizontal scroll indicators.
3. **Full-Viewport Overlays**: Modals (`.inner-modal-box`) and slide-over drawers (`.drawer-container`) scale to `width: 100vw; height: 100vh; max-height: 100dvh; border-radius: 0;` on viewports `< 768px` with fixed bottom primary submit buttons.

---

## 2. View-by-View Prompts

### Prompt: Applications Board & Table View
```markdown
### Target File
`frontend/src/views/ApplicationsView.vue`

### Prompt Context & Instructions
Refactor `frontend/src/views/ApplicationsView.vue` to make the Applications Board fully responsive across mobile (< 768px), tablet (768px-1023px), and desktop (>= 1024px) viewports.

#### Layout Shifts & Responsive Adaptation
1. **Controls & Filters Header (`.controls-bar`)**:
   - On Desktop (>= 1024px): Display search bar, segmented view toggles (Active, Archived, Past Wins), dropdown filters, and view switcher side-by-side.
   - On Mobile (< 768px): Stack controls vertically. Wrap pipeline mode buttons (`.pipeline-mode-toggle`) into a full-width horizontally scrollable pill container. Make search input (`.search-input-wrapper`) 100% width. Move date and work model filters into a collapsible "Filters" drawer trigger to preserve screen real estate.
2. **Kanban Board (`.kanban-board`)**:
   - On Desktop (>= 1024px): Display 3-column side-by-side grid (`grid-template-columns: repeat(3, minmax(320px, 1fr))`).
   - On Mobile (< 768px): Convert `.kanban-board` into a CSS horizontal swipe carousel (`display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 12px; padding: 0 12px;`). Set `.kanban-column` width to `calc(100vw - 48px)` with `scroll-snap-align: center`. Add swipe pagination dot indicators at the bottom.
3. **Data Table (`.data-table`)**:
   - On Mobile (< 768px): Wrap `.data-table` in a horizontally scrollable container (`overflow-x: auto`), or transform table rows into responsive stacked cards showing Company, Position, Stage Pill, and Quick Action buttons.
4. **Teleported Context Menus & Drag Dock**:
   - Ensure the teleported card dropdown menu (`.card-teleport-menu`) clamps within viewport boundaries (`max-width: 90vw`) and adjusts hit areas for touch targets (min 48px touch height).
   - Convert drag-and-drop actions into quick swipe actions or context menu options on touch devices.

#### Preservation & Integrity Requirements
- Preserve Pinia state bindings (`useApplicationsStore`, `useUIStore`).
- Maintain exact filtering reactivity (`searchQuery`, `selectedWorkModel`, `selectedDateRange`, `minMatchScore`).
- Keep drag-and-drop events fully functional on desktop while offering touch-friendly fallbacks on mobile.
```

---

### Prompt: AI Assessments View
```markdown
### Target File
`frontend/src/views/AssessmentsView.vue`

### Prompt Context & Instructions
Refactor `frontend/src/views/AssessmentsView.vue` to optimize layout, grid cards, and assessment evaluation details across mobile (< 768px) and tablet viewports.

#### Layout Shifts & Responsive Adaptation
1. **Stats Summary Bar (`.stats-grid`)**:
   - Desktop: 4-column horizontal stats bar (`grid-template-columns: repeat(4, 1fr)`).
   - Mobile (< 768px): Stack into a 2x2 grid (`grid-template-columns: repeat(2, 1fr)`), reducing internal padding to 10px and icon sizing to 16px.
2. **Assessment Cards Grid (`.assessments-grid`)**:
   - Desktop: Multi-column grid (`grid-template-columns: repeat(auto-fill, minmax(340px, 1fr))`).
   - Mobile (< 768px): Single-column full-width layout (`grid-template-columns: 1fr`).
3. **Assessment Card Actions & Details**:
   - Stack action buttons (Review Assessment, Generate Cover Letter, View Listing) vertically on mobile with 100% width and 48px touch targets.
   - Ensure radar charts, match score badges (`.score-badge-card`), and skill tag wraps flow gracefully without horizontal overflowing.

#### Preservation & Integrity Requirements
- Maintain Vue reactivity with `useQueueStore` and `useApplicationsStore`.
- Preserve modal popups (`openMatchAnalysisModal`, `openCoverLetterModal`) and SSE status updates.
```

---

### Prompt: Action Items & Tasks View
```markdown
### Target File
`frontend/src/views/ActionItemsView.vue`

### Prompt Context & Instructions
Make `frontend/src/views/ActionItemsView.vue` fully responsive across mobile and desktop devices.

#### Layout Shifts & Responsive Adaptation
1. **Filters & Search Header**:
   - Stack status filters (Pending, Completed, Overdue) into a full-width pill bar on mobile.
   - Make task creation input forms and date filters collapse into vertical stacks.
2. **Task List & Grouping**:
   - On Mobile (< 768px): Convert task rows into touch-friendly cards. Position checkbox triggers on the left with min 48x48px hit areas.
   - Move due date badges, priority indicators, and company tag pills below the task title.
3. **Action Triggers**:
   - Stack edit, complete, and delete action icons into a bottom action row or right-aligned menu on mobile cards.

#### Preservation & Integrity Requirements
- Maintain full CRUD reactivity with `ActionItemsAPI`.
- Preserve optimistic task completion updates and toast notifications.
```

---

### Prompt: Analytics & Market Intelligence View
```markdown
### Target File
`frontend/src/views/AnalyticsView.vue`

### Prompt Context & Instructions
Refactor `frontend/src/views/AnalyticsView.vue` to make charts, metrics grids, market intelligence benchmarks, and funnel conversion views mobile-ready.

#### Layout Shifts & Responsive Adaptation
1. **Sub-Tab Navigation**:
   - Render "Overview", "Funnel Metrics", and "Market Intelligence" tabs as a full-width segmented bar or horizontally scrollable pill strip on mobile.
2. **Metrics & KPI Grid (`.metrics-grid`)**:
   - Desktop: 4-column layout.
   - Tablet: 2-column layout.
   - Mobile (< 768px): Single column layout (`1fr`), adjusting font sizes to `clamp(1.2rem, 4vw, 1.75rem)` for primary metric values.
3. **Charts & Visualizations (Funnel Charts, Salary Distribution Bar Charts)**:
   - Make SVG / Canvas / CSS bar charts scale fluidly (`width: 100%; height: auto; min-height: 220px`).
   - On mobile, rotate horizontal funnel bar labels or render compact legend lists below chart containers.
4. **Benchmark & Salary Breakdown Tables**:
   - Convert skill salary tables into responsive cards on mobile, displaying median salary, sample count, and outlier trimming tags in a stacked layout.

#### Preservation & Integrity Requirements
- Preserve date range filtering params (`period`, `num_periods`).
- Maintain reactivity when toggling between pipeline funnel and market benchmarks.
```

---

### Prompt: Agent Chat & Interview Simulator View
```markdown
### Target File
`frontend/src/views/AgentChatView.vue`

### Prompt Context & Instructions
Refactor `frontend/src/views/AgentChatView.vue` to optimize the dual-mode AI Chat / Mock Interview Simulator interface for mobile (< 768px) screens.

#### Layout Shifts & Responsive Adaptation
1. **Sidebar Navigation (Thread History & Personas)**:
   - Desktop: Fixed side pane (width 280px).
   - Mobile (< 768px): Transform sidebar into a collapsible slide-out drawer triggered by a top toolbar button ("History / Personas"). Add backdrop overlay.
2. **Chat Container & Message Thread**:
   - Ensure message bubbles (`.chat-bubble`) scale fluidly up to `width: 90%` on mobile.
   - Make code blocks and markdown tables inside messages scroll horizontally (`overflow-x: auto`) without breaking parent container layout.
3. **Interactive Mock Interview HUD Split-Pane**:
   - Desktop: Split pane with question area on left and real-time STAR scoring HUD on right.
   - Mobile (< 768px): Stack layout vertically. Position STAR criteria badges, real-time score gauge, and exemplar rewrites in an expandable accordion section above or below the active speech/text input box.
4. **Input Bar & Dictation Controls**:
   - Fix chat input bar to screen bottom (`position: sticky` or `fixed`). Ensure Web Speech API dictation button has a clear 48x48px hit area.

#### Preservation & Integrity Requirements
- Preserve Pinia `useAgentChatStore` and `useInterviewStore` bindings.
- Preserve real-time Web Speech API audio recording, SSE streaming response tokens, and persona switching.
```

---

### Prompt: Staging Leads & Smart-Link View
```markdown
### Target File
`frontend/src/views/StagingView.vue`

### Prompt Context & Instructions
Adapt `frontend/src/views/StagingView.vue` to ensure inbound email staging leads and smart application linking cards render smoothly on mobile devices.

#### Layout Shifts & Responsive Adaptation
1. **Staging List Layout**:
   - Desktop: Split table or 2-column view (Inbound List vs Staging Detail Pane).
   - Mobile (< 768px): Single-column view with master-detail navigation. Clicking a staging lead opens a full-screen detail view with a top "Back to Staging" button.
2. **Smart Link Banner (`.smart-link-banner`)**:
   - On mobile, stack matching application suggestions vertically with clear 1-click "Link Application" and "Create New Lead" buttons (min height 44px).

#### Preservation & Integrity Requirements
- Preserve `StagingAPI` list, link, and reject state reactivity.
```

---

### Prompt: Evaluation Queue View
```markdown
### Target File
`frontend/src/views/QueueView.vue`

### Prompt Context & Instructions
Refactor `frontend/src/views/QueueView.vue` to make the background intake evaluation task queue fully responsive on mobile screens.

#### Layout Shifts & Responsive Adaptation
1. **Task Queue Header Controls**:
   - Stack bulk action buttons ("Bulk Retry", "Bulk Delete", "Clear Completed") vertically or into a dropdown menu on mobile (< 768px).
2. **Evaluation Task Cards / Rows**:
   - Display task stage steppers (`SCRAPING` -> `EXTRACTING` -> `EVALUATING` -> `COVER_LETTER`) as compact horizontal icons or collapsible vertical progress lists on mobile.
   - On tasks with errors (`SCRAPE_FAILED:`, `INVALID_JOB_CONTENT:`), ensure "Provide Description" / "Edit Job Description" modal triggers expand to full width.

#### Preservation & Integrity Requirements
- Maintain `useQueueStore` polling intervals (1.5s active / 4s idle) and snapshot rollbacks.
```

---

### Prompt: Settings & Profile Management View
```markdown
### Target File
`frontend/src/views/SettingsView.vue`

### Prompt Context & Instructions
Refactor `frontend/src/views/SettingsView.vue` to optimize tab navigation, AI provider configuration, and system feature toggles for mobile viewports.

#### Layout Shifts & Responsive Adaptation
1. **Tab Navigation Bar (`.settings-tabs`)**:
   - Desktop: Horizontal tab list or left sidebar navigation.
   - Mobile (< 768px): Convert tabs into a horizontally scrollable pill strip (`overflow-x: auto; white-space: nowrap`) or a select dropdown picker ("AI Providers", "Candidate CV Profile", "Feature Toggles", "Email Accounts").
2. **AI Provider Cards & Feature Toggle Sliders**:
   - Stack provider configuration inputs, API key fields, and ping status badges vertically on mobile.
   - Ensure range sliders (`.form-range`) and checkbox toggles have 48px touch targets.

#### Preservation & Integrity Requirements
- Maintain system settings persistence (`uiStore.fetchSystemSettings`, `saveSettings`) and AI health check triggers.
```

---

### Prompt: Candidate Profile & CV Intake Sub-View
```markdown
### Target File
`frontend/src/views/CandidateProfileView.vue`

### Prompt Context & Instructions
Adapt `frontend/src/views/CandidateProfileView.vue` for mobile devices.

#### Layout Shifts & Responsive Adaptation
1. **Header & Quick Action Buttons**:
   - Stack "Input / Update CV", "Remove CV", and "Export Anonymized CV" buttons vertically on mobile (< 768px).
2. **CV Modal & Raw Text / Scrubbed Preview Tabs**:
   - Make CV file upload drag-and-drop box touch-friendly with clear file picker triggers.
   - Stack Privacy Advisory Banner and de-identified text preview pane cleanly.

#### Preservation & Integrity Requirements
- Preserve `CandidateProfileAPI.parseFile` upload handlers and PII de-identification flow.
```

---

### Prompt: AI Interview Preparation Guide View
```markdown
### Target File
`frontend/src/views/InterviewGuideView.vue`

### Prompt Context & Instructions
Refactor `frontend/src/views/InterviewGuideView.vue` to ensure deep-linked interview preparation guides display legibly on mobile viewports.

#### Layout Shifts & Responsive Adaptation
1. **Header & Company Meta Section**:
   - Stack company logo, role title, fit score pill, and action controls vertically on mobile.
2. **Guide Section Grid / Accordions**:
   - On Desktop: Multi-column grid for Technical Questions, System Design, Behavioral STAR scenarios, and Company Insights.
   - On Mobile (< 768px): Transform sections into vertical accordions or stacked cards. Ensure markdown text and exemplar code blocks fit within 100% viewport width.

#### Preservation & Integrity Requirements
- Maintain route parameter handling (`/guide/:id`) and PDF/print export functionality.
```

---

### Prompt: System Diagnostics View
```markdown
### Target File
`frontend/src/views/DiagnosticsView.vue`

### Prompt Context & Instructions
Adapt `frontend/src/views/DiagnosticsView.vue` for mobile viewports.

#### Layout Shifts & Responsive Adaptation
1. **Telemetry Filter Controls**:
   - Stack category, status, and date range filters vertically on mobile.
2. **Trace Log Data Table / JSON Inspector**:
   - Wrap server-side telemetry trace logs in an overflowing table box.
   - Render JSON payload inspection modals with full-screen bounds and scrollable code viewers on mobile.

#### Preservation & Integrity Requirements
- Maintain backend trace polling and filter query params (`/diagnostics/traces`).
```

---

## 3. Component-by-Component Prompts

### Prompt: Application Main Navbar Component
```markdown
### Target File
`frontend/src/components/layout/AppNavbar.vue`

### Prompt Context & Instructions
Refactor `frontend/src/components/layout/AppNavbar.vue` to implement a mobile slide-out drawer menu and adaptive toolbar.

#### Responsive Adaptation Requirements
1. **Desktop Layout (>= 1024px)**:
   - Render brand icon, main navigation links (Applications, Assessments, Tasks, Staging, Analytics, Agent), AI Health pill, "Job Intake" button, "Email Intake" button, Theme switcher, and Settings gear icon in horizontal flex layout.
2. **Mobile Layout (< 768px)**:
   - Hide desktop navigation links behind a hamburger menu trigger button (`<button class="mobile-menu-trigger">`).
   - Clicking hamburger trigger toggles a slide-out drawer from the left (`width: 280px; height: 100vh; position: fixed; z-index: 1000;`).
   - Inside drawer: render stacked navigation links with badge counters, user profile indicator, and settings access.
   - On main top navbar bar, display Brand Icon, AI Health Pill (compact mode), "Job Intake" (+) action icon button, and Hamburger Trigger.
3. **Touch Targets & Polish**:
   - Ensure all navbar action icons and drawer menu items have minimum `48x48px` hit targets.

#### Preservation Requirements
- Maintain `uiStore` theme popover toggle, AI health polling trigger, and route active link bindings.
```

---

### Prompt: Application Detail Drawer Component
```markdown
### Target File
`frontend/src/components/drawers/ApplicationDetailDrawer.vue`

### Prompt Context & Instructions
Refactor `frontend/src/components/drawers/ApplicationDetailDrawer.vue` to provide a full-width experience on mobile while retaining the side drawer on desktop.

#### Responsive Adaptation Requirements
1. **Desktop Layout (>= 1024px)**:
   - Slide-over drawer on right side (`width: 600px; max-width: 90vw; height: 100vh;`).
2. **Mobile Layout (< 768px)**:
   - Expand drawer to full viewport width (`width: 100vw; height: 100vh; max-height: 100dvh; top: 0; right: 0; border-radius: 0;`).
   - Sticky top bar inside drawer with prominent Close (`X`) button and application title.
   - Stack detail tabs (Overview, Timeline Events, Interview Notes, Action Items) into a sticky horizontal scroll bar.
   - Sticky bottom action bar containing primary stage transition actions ("Move to Interview", "Log Activity", "Edit Application").

#### Preservation Requirements
- Preserve Pinia `uiStore.isDetailOpen`, `uiStore.activeDetailAppId`, timeline event fetching, and note saving.
```

---

### Prompt: Job Intake Modal Component
```markdown
### Target File
`frontend/src/components/modals/JobIntakeModal.vue`

### Prompt Context & Instructions
Adapt `frontend/src/components/modals/JobIntakeModal.vue` for mobile screens.

#### Responsive Adaptation Requirements
1. **Modal Frame**:
   - Desktop: Centered modal (`max-width: 560px`).
   - Mobile (< 768px): Full-screen modal (`width: 100vw; height: 100vh; border-radius: 0; margin: 0;`).
2. **Input Mode Switcher (URL vs Raw Text)**:
   - Make mode selection tabs fill 100% width with equal touch targets (`48px` height).
3. **Form Controls**:
   - Expand URL input field and raw job description textarea to fill viewport height dynamically. Ensure submit button ("Start AI Qualification") is fixed to the bottom footer.

#### Preservation Requirements
- Maintain `queueStore.enqueueAssessment` handling, form validation, and modal close triggers.
```

---

### Prompt: Cover Letter Modal Component
```markdown
### Target File
`frontend/src/components/modals/CoverLetterModal.vue`

### Prompt Context & Instructions
Refactor `frontend/src/components/modals/CoverLetterModal.vue` for mobile viewports.

#### Responsive Adaptation Requirements
1. **Layout Adaptations**:
   - On Mobile (< 768px), expand modal to full screen bounds (`100vw x 100vh`).
   - Stack the collapsible "Regenerate & Tone Options" control panel above the cover letter editor/viewer.
   - Position "Copy to Clipboard", "Download PDF/Docx", and "Regenerate" buttons into a sticky bottom action footer with 48px touch targets.

#### Preservation Requirements
- Maintain `uiStore` cover letter modal state, tone selection reactivity, custom instructions input, and API save endpoints.
```

---

### Prompt: Match Analysis Modal Component
```markdown
### Target File
`frontend/src/components/modals/MatchAnalysisModal.vue`

### Prompt Context & Instructions
Adapt `frontend/src/components/modals/MatchAnalysisModal.vue` for mobile screens.

#### Responsive Adaptation Requirements
1. **Score Display & Breakdown**:
   - Desktop: Side-by-side rectangular `.score-badge-card` and breakdown radar chart / category bars.
   - Mobile (< 768px): Stack overall fit score badge card on top, followed by missing skills, matching skills, and qualitative AI rationale in vertical sequence.

#### Preservation Requirements
- Preserve skill match score tier styling (`getFitBadgeClass`) and taxonomy display logic.
```

---

### Prompt: Ingest & Email Sync Modal Component
```markdown
### Target File
`frontend/src/components/modals/IngestModal.vue`

### Prompt Context & Instructions
Adapt `frontend/src/components/modals/IngestModal.vue` for mobile screens.

#### Responsive Adaptation Requirements
1. **Tabs & Sync Controls**:
   - Stack account selection dropdown, manual thread paste textarea, and message file upload dropzone into a single scrollable column on mobile (< 768px).

#### Preservation Requirements
- Maintain IMAP/OAuth sync API calls and manual thread submission logic.
```

---

### Prompt: Onboarding Wizard Modal Component
```markdown
### Target File
`frontend/src/components/modals/OnboardingWizardModal.vue`

### Prompt Context & Instructions
Refactor `frontend/src/components/modals/OnboardingWizardModal.vue` to make the 4-step onboarding experience fully responsive on mobile screens.

#### Responsive Adaptation Requirements
1. **Stepper Header**:
   - Desktop: Horizontal 4-step progress indicator bar with titles.
   - Mobile (< 768px): Compact step indicator (`Step X of 4`) with a horizontal progress bar.
2. **Step Contents (AI Provider Presets, CV Intake, Feature Toggles, Completion)**:
   - Stack provider preset cards (LM Studio, Ollama, OpenAI, Anthropic, Gemini) vertically on mobile.
   - Ensure "Test Connection" and "Next Step" buttons are easily tapable at the bottom.

#### Preservation Requirements
- Preserve onboarding completion flag (`has_completed_onboarding`) and router navigation to `/applications`.
```

---

### Prompt: Floating Evaluation Queue Widget
```markdown
### Target File
`frontend/src/components/layout/FloatingQueueWidget.vue`

### Prompt Context & Instructions
Adapt `frontend/src/components/layout/FloatingQueueWidget.vue` for mobile viewports.

#### Responsive Adaptation Requirements
1. **Floating Pill & Expanded Drawer**:
   - Mobile (< 768px): Position floating pill in bottom-right corner with `bottom: 80px; right: 16px; z-index: 900;` to avoid overlapping main mobile navigation bars.
   - Expanded task drawer should open as a bottom sheet (`width: 100vw; max-height: 70vh; border-radius: 16px 16px 0 0;`).

#### Preservation Requirements
- Maintain Pinia `useQueueStore` live task polling and task status badge indicators.
```

---

### Prompt: Floating Agent Chat Widget Component
```markdown
### Target File
`frontend/src/components/agent/FloatingAgentChatWidget.vue`

### Prompt Context & Instructions
Adapt `frontend/src/components/agent/FloatingAgentChatWidget.vue` for mobile viewports.

#### Responsive Adaptation Requirements
1. **Widget Position & Expanded Window**:
   - On Desktop: Floating action button in bottom-right corner expanding to a 420x600px popup window.
   - On Mobile (< 768px): Expanded widget takes full viewport (`100vw x 100vh`) with a top header collapse button.

#### Preservation Requirements
- Maintain agent tool execution state, message history, and Pinia agent chat store bindings.
```

---

### Prompt: Date-Time Picker Component
```markdown
### Target File
`frontend/src/components/common/DateTimePicker.vue`

### Prompt Context & Instructions
Adapt `frontend/src/components/common/DateTimePicker.vue` for mobile touch interaction.

#### Responsive Adaptation Requirements
1. **Popover Positioning & Teleport**:
   - Ensure popover rendered via `<Teleport to="body">` calculates `getBoundingClientRect()` dynamic viewport coordinates correctly on mobile orientation changes.
   - Center popover modal on screen for viewports < 768px with large touchable date/time selection grids (min 44px hit targets).

#### Preservation Requirements
- Preserve `v-model` date string formatting and Vue reactivity.
```

---

### Prompt: Toast Notification System Component
```markdown
### Target File
`frontend/src/components/common/ToastNotification.vue`

### Prompt Context & Instructions
Adapt `frontend/src/components/common/ToastNotification.vue` for mobile viewports.

#### Responsive Adaptation Requirements
1. **Positioning & Safe Areas**:
   - Desktop: `position: fixed; bottom: 24px; left: 24px; z-index: 9999;`.
   - Mobile (< 768px): Center toast at top or bottom of viewport (`left: 50%; transform: translateX(-50%); width: calc(100vw - 32px); max-width: 400px; bottom: max(16px, env(safe-area-inset-bottom));`).

#### Preservation Requirements
- Maintain auto-dismiss timeouts and toast message queue reactivity in `uiStore`.
```
