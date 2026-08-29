# Graph Report - job-tracker  (2026-08-29)

## Corpus Check
- 220 files · ~261,197 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2817 nodes · 5753 edges · 169 communities (121 shown, 48 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 640 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f7587ec4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- InterviewSimulatorService
- ApplicationDetailDrawer.vue
- routers/applications.py
- OnboardingWizardModal.vue
- services/analytics.py
- ApplicationsView.vue
- routers/intake.py
- AsyncSession
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- services/agent_tools.py
- StagingView.vue
- scrape_job_url
- routers/ai_config.py
- main.py
- routers/candidate_profile.py
- popup.js
- AssessmentsView.vue
- routers/action_items.py
- routers/email_accounts.py
- AnalyticsView.vue
- CandidateProfileView.vue
- JobIntakeView.vue
- IntakeEvaluationTaskModel
- EmailAccountsSettings.vue
- FloatingQueueWidget.vue
- get_task_chat_model
- normalize_job_url
- manifest.json
- routers/extension.py
- ApplicationEventModel
- ActionItemsView.vue
- CoverLetterModal.vue
- uiStore.js
- dependencies
- ExtractedEmailInfo
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- routers/prompts.py
- test_analytics.py
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- update_application
- GenerateInterviewGuideRequest
- EmailAccountModel
- test_llm_factory.py
- assess_job_lead
- test_email_accounts.py
- ProcessedEmailModel
- routers/llm.py
- EmailPayload
- ApplicationModel
- bulk_dismiss_staging_items
- fetchActionItems
- conftest.py
- routers/agent_chat.py
- AsyncSession
- endpoints.js
- LogActivityModal.vue
- dock.js
- CompanyLogo.vue
- interview_guide_graph.py
- PrioritySemaphore
- close
- InterviewReaderModal.vue
- AsyncSession
- executeDirectTransition
- create_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- load_settings
- extractJobData
- index.js
- TaskTracker
- saveProfileField
- BackgroundTasks
- admin.py
- routers/system_settings.py
- handleOAuthSuccess
- selectItem
- jt script
- scrollToBottom
- formatRelativeDate
- resolve_company_domain
- PostHireModal.vue
- advanceAppStage
- routers/diagnostics.py
- fuzzyMatch.js
- syncStudioForm
- loadBindings
- fetchStagingItems
- datetime
- Any
- delete
- get
- closeSidebarOnMobile
- AsyncSession
- cleanCVText
- pollTaskUntilComplete
- openAddEmailAccountModal
- skill_taxonomy.py
- JobTrackerState
- Email Synchronization Engine
- Frontend SPA Entry HTML
- handleFileInput
- emailRenderer.js
- scrubber.js
- filteredInterviewSessions
- canNavigateToEmailStep
- handleSidebarScroll
- pre-commit.sh
- Bug Report Issue Template
- Feature Request Issue Template
- Quickstart & Daily Driving Guide
- User Guide
- Extension Icon 128px
- Extension Icon 48px
- Frontend Favicon 128px
- Frontend Favicon 48px
- backend
- Responsive Design Guide
- BackgroundTasks
- BaseModel
- delete
- get
- post
- Request
- patch
- post
- UploadFile
- asyncio
- Base
- test_new_features.py
- test_schemas.py
- interviewStore.js
- FailoverChatModel
- _execute_evaluation_steps
- LazyAsyncPostgresSaver
- Any
- asyncio
- AIProviderModel
- BaseModel
- StrEnum
- env.py
- services/llm.py
- schemas/intake.py
- trace_operation
- .exchange_code_for_tokens
- routers/search.py
- patch
- asyncio
- PostgresTracer
- scheduleStudioAutoSave
- programmatic_scrub_cv
- Any

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 112 edges
2. `CompanyModel` - 86 edges
3. `ApplicationEventModel` - 46 edges
4. `IntakeEvaluationTaskModel` - 44 edges
5. `EmailAccountModel` - 40 edges
6. `Base` - 38 edges
7. `useUIStore` - 38 edges
8. `PostgresTracer` - 37 edges
9. `AIProviderModel` - 35 edges
10. `EmailPayload` - 35 edges

## Surprising Connections (you probably didn't know these)
- `Root Pre-Commit Configuration` --semantically_similar_to--> `Backend Pre-Commit Configuration`  [INFERRED] [semantically similar]
  .pre-commit-config.yaml → backend/.pre-commit-config.yaml
- `seed()` --uses--> `IntakeEvaluationTaskModel`  [INFERRED]
  seed_db.py → backend/app/models/intake_tasks.py
- `useQueueStore` --indirect_call--> `enqueueAssessment()`  [INFERRED]
  frontend/src/stores/queueStore.js → extension/utils/api.js
- `Dependabot Configuration` --references--> `Vue 3 Frontend SPA`  [INFERRED]
  .github/dependabot.yml → README.md
- `Deploy Frontend to GitHub Pages Workflow` --references--> `Vue 3 Frontend SPA`  [INFERRED]
  .github/workflows/deploy-pages.yml → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Supported AI Provider Ecosystem** — concept_lm_studio_provider, concept_ollama_provider, concept_openai_provider, concept_anthropic_provider, concept_gemini_provider, concept_openrouter_provider, concept_failover_chat_model, concept_ai_task_bindings [EXTRACTED 1.00]
- **CI Quality Gate Lint Test Build** — _github_workflows_backend_ci_backend_ci_workflow, _github_workflows_frontend_ci_frontend_ci_workflow, _pre_commit_config_root_pre_commit, backend__pre_commit_config_backend_pre_commit, concept_ruff_linter [EXTRACTED 1.00]
- **Docker Compose Deployment Variants Production Dev External** — docker_compose_production_stack, docker_compose_dev_dev_stack, docker_compose_external_external_services_override [EXTRACTED 1.00]
- **Backend LangGraph State Machines** — docs_architecture_intake_stategraph, docs_architecture_interview_guide_graph, docs_architecture_mock_interview_simulator [INFERRED 0.85]
- **Companion Browser Extension Architecture** — extension_readme_companion_extension, extension_shadow_dom_dock, extension_popup_popup_html, extension_chromewebstore_docs [INFERRED 0.85]

## Communities (169 total, 48 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (70): accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri, coverLetterLength (+62 more)

### Community 1 - "InterviewSimulatorService"
Cohesion: 0.11
Nodes (46): InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions(), next_question() (+38 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (46): ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData, headerEditForm (+38 more)

### Community 3 - "routers/applications.py"
Cohesion: 0.23
Nodes (23): bulk_transition_applications(), get_application(), list_applications(), Transitions all applications whose status is in payload.from_statuses to…, _to_utc(), update_cover_letter(), ActionItemDetail, ApplicationByStatusResult (+15 more)

### Community 4 - "OnboardingWizardModal.vue"
Cohesion: 0.03
Nodes (47): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+39 more)

### Community 5 - "services/analytics.py"
Cohesion: 0.09
Nodes (49): get_funnel_metrics(), get_overview(), get_role_alignment_endpoint(), AsyncSession, get, get_funnel_metrics(), AsyncSession, get (+41 more)

### Community 6 - "ApplicationsView.vue"
Cohesion: 0.03
Nodes (39): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, archiveSortKey, archiveSortOrder (+31 more)

### Community 7 - "routers/intake.py"
Cohesion: 0.10
Nodes (36): generate_app_cover_letter(), regenerate_app_cover_letter(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), confirm_job_assessment(), enqueue_job_assessment(), fix_jd_evaluation_task() (+28 more)

### Community 8 - "AsyncSession"
Cohesion: 0.14
Nodes (20): AsyncSession, clear_app_interview_guide(), delete_application(), get_applications_by_status(), get_cover_letter(), Replicates the status search CTE query to fetch applications, event counts, and…, Permanently deletes an application and its associated events, postings, and…, clear_completed_evaluations() (+12 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.05
Nodes (37): activeCancelTask, activeCount, activeFixJDTask, bulkDeleteSelected(), bulkRetrySelected(), clearSelection(), completedCount, deleteTask() (+29 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "services/agent_tools.py"
Cohesion: 0.11
Nodes (42): AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, ListApplicationsInput, ManageActionItemsInput, ManageIntakeQueueInput, BaseModel (+34 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (36): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+28 more)

### Community 14 - "scrape_job_url"
Cohesion: 0.16
Nodes (25): clean_extracted_text(), has_job_content_keywords(), BaseModel, Validates URL protocol and private IP / loopback address validation (SSRF…, Blazing fast multi-language scraper keyword validation using Python set hash…, Backward-compatible alias for validate_job_content., Normalizes whitespace and strips javascript code blocks, jQuery artifacts, and…, Scrapes a URL using the running Camofox browser automation server. (+17 more)

### Community 15 - "routers/ai_config.py"
Cohesion: 0.14
Nodes (38): clear_embeddings_cache(), Clears cached Embeddings model instances., create_ai_provider(), delete_ai_provider(), delete_ai_task_binding(), _fetch_models_from_endpoint(), get_ai_health_endpoint(), get_global_settings() (+30 more)

### Community 16 - "main.py"
Cohesion: 0.09
Nodes (25): check_db_connection(), ensure_db_schema(), get_db(), AsyncSession, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, health_check(), lifespan() (+17 more)

### Community 17 - "routers/candidate_profile.py"
Cohesion: 0.08
Nodes (39): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+31 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.06
Nodes (24): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkMarkAsApplied(), evaluationTasks, expandedTaskIds (+16 more)

### Community 20 - "routers/action_items.py"
Cohesion: 0.15
Nodes (27): compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks, delete (+19 more)

### Community 21 - "routers/email_accounts.py"
Cohesion: 0.11
Nodes (36): clear_account_processed_emails(), clear_all_processed_emails(), delete_account(), EmailFoldersResponse, fetch_account_folders(), get_account(), get_oauth_authorize_url(), get_oauth_config() (+28 more)

### Community 22 - "AnalyticsView.vue"
Cohesion: 0.06
Nodes (39): formatJobSpecCompensation(), getCurrencySymbol(), activeTab, alignmentData, alignmentSubTab, analyticsData, copiedItemKey, customSearchQuery (+31 more)

### Community 23 - "CandidateProfileView.vue"
Cohesion: 0.06
Nodes (24): currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling, isDeleting (+16 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.06
Nodes (27): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+19 more)

### Community 25 - "IntakeEvaluationTaskModel"
Cohesion: 0.18
Nodes (23): Removes a finished or cancelled task from the in-memory registry., unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification…, ExtractedJobSpec, JobAssessmentResult, Any, field_validator (+15 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (24): accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm, emit (+16 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "get_task_chat_model"
Cohesion: 0.22
Nodes (19): _clean_base_url(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model(), AsyncSession, Returns cached Embeddings model instance or initializes and caches a new one. (+11 more)

### Community 29 - "normalize_job_url"
Cohesion: 0.14
Nodes (17): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, persist_or_stage_job_assessment(), AsyncSession, Persists an AI job assessment to the database. If target_application_id is…, resolve_job_currency(), asyncio, Test that submitting the same job posting URL with different referral… (+9 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "routers/extension.py"
Cohesion: 0.19
Nodes (15): clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text…, Receives a job posting URL, scrapes page text (or uses pre-captured HTML), and… (+7 more)

### Community 32 - "ApplicationEventModel"
Cohesion: 0.12
Nodes (26): ApplicationEventModel, model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve, process_email_batch_sequential(), Sequentially routes emails through the compiled LangGraph pipeline., enable_email_intake_mock(), asyncio (+18 more)

### Community 33 - "ActionItemsView.vue"
Cohesion: 0.08
Nodes (17): actionItems, activeUrgencyDropdown, applicationsList, currentEditId, displayedTasks, filterTab, isEditing, isLoading (+9 more)

### Community 34 - "CoverLetterModal.vue"
Cohesion: 0.06
Nodes (36): activeCoverLetterTask, application, appStore, autoSaveStatus, charCount, close(), COVER_LETTER_LENGTHS, COVER_LETTER_TONES (+28 more)

### Community 35 - "uiStore.js"
Cohesion: 0.12
Nodes (17): AIConfigAPI, uiStore, uiStore, activeCount, hasItems, queue, STAGES, uiStore (+9 more)

### Community 36 - "dependencies"
Cohesion: 0.07
Nodes (28): axios, dompurify, dependencies, axios, dompurify, @lucide/vue, lucide-vue-next, pinia (+20 more)

### Community 37 - "ExtractedEmailInfo"
Cohesion: 0.21
Nodes (22): ExtractedEmailInfo, Structured extraction format returned by the LLM service., asyncio, AsyncSession, When exactly 1 application exists for a matched company, auto-link to it even…, When multiple applications exist for a company, disambiguate by position or…, Recruiter outreach for a new company should route to Staging Queue for review., An email with a completely different position for a company with 1 active… (+14 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.08
Nodes (16): getRouteTitle(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount, pendingTasksCount, pillLabel, pillTitle, popoverContainerRef (+8 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.07
Nodes (25): analysisData, application, compensationText, computedScoreText, emit, error, gapMitigationText, isLoading (+17 more)

### Community 41 - "routers/prompts.py"
Cohesion: 0.16
Nodes (17): clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., get_prompt(), list_prompts(), AsyncSession, get, patch, post (+9 more)

### Community 42 - "test_analytics.py"
Cohesion: 0.48
Nodes (6): asyncio, test_get_analytics_overview(), test_get_funnel_metrics_monthly(), test_get_funnel_metrics_weekly(), test_get_role_alignment(), test_get_role_alignment_filtered_track()

### Community 43 - "DiagnosticsView.vue"
Cohesion: 0.09
Nodes (19): DiagnosticsAPI, activeCategory, categories, copied, loadData(), loading, loadingDetail, loadingTraces (+11 more)

### Community 44 - "DateTimePicker.vue"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "JobIntakeModal.vue"
Cohesion: 0.08
Nodes (26): IntakeAPI, activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls() (+18 more)

### Community 46 - "update_application"
Cohesion: 0.15
Nodes (12): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, Partially updates a job application and enqueues background vector embedding…, update_application(), test_secret_key_auto_generation_and_persistence() (+4 more)

### Community 47 - "GenerateInterviewGuideRequest"
Cohesion: 0.29
Nodes (10): generate_app_interview_guide(), generate_app_interview_guide_stream(), GenerateInterviewGuideRequest, clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream(), AsyncSession, Async generator that executes `interview_guide_graph.astream(...)` and yields… (+2 more)

### Community 48 - "EmailAccountModel"
Cohesion: 0.10
Nodes (29): EmailAccountModel, _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using… (+21 more)

### Community 49 - "test_llm_factory.py"
Cohesion: 0.22
Nodes (22): get_active_llm_config_dict(), Retrieves runtime LLM configuration from the database., Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem (+14 more)

### Community 50 - "assess_job_lead"
Cohesion: 0.20
Nodes (14): Any, AssessJobRequest, assess_job_lead(), ExtensionUrlDirectPayload, _format_graph_result(), intake_extension_jd_elements(), intake_extension_url(), Receives URL directly from browser extension send-url button and triggers AI… (+6 more)

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "ProcessedEmailModel"
Cohesion: 0.21
Nodes (19): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, enable_email_intake_mock(), asyncio, AsyncSession (+11 more)

### Community 53 - "routers/llm.py"
Cohesion: 0.10
Nodes (27): _encrypt_table_secrets(), Connection, upgrade(), decrypt_secret(), encrypt_secret(), _get_fernet(), mask_secret(), Encrypt a sensitive value, preserving already encrypted values. (+19 more)

### Community 54 - "EmailPayload"
Cohesion: 0.18
Nodes (17): EmailPayload, _extract_ics_summary(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload., Parses plaintext / raw thread text into EmailPayload. (+9 more)

### Community 55 - "ApplicationModel"
Cohesion: 0.13
Nodes (34): ApplicationModel, CompanyModel, asyncio, test_action_items_crud_and_filtering(), asyncio, AsyncSession, test_application_patch_updates(), test_application_transitions_and_deletion() (+26 more)

### Community 56 - "bulk_dismiss_staging_items"
Cohesion: 0.09
Nodes (32): bulk_dismiss_staging_items(), clear_resolved_staging_items(), get_staging_item(), list_staging_items(), AsyncSession, delete, get, post (+24 more)

### Community 57 - "fetchActionItems"
Cohesion: 0.33
Nodes (6): deleteTask(), fetchActionItems(), handleSaveTask(), selectMetricTab(), setManualUrgency(), toggleTaskStatus()

### Community 58 - "conftest.py"
Cohesion: 0.12
Nodes (18): db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info(), mock_job_email_payload(), postgres_container(), AsyncSession, fixture (+10 more)

### Community 59 - "routers/agent_chat.py"
Cohesion: 0.18
Nodes (17): get_prompt_template(), AsyncSession, Retrieves prompt template from DB with in-memory caching, falling back to…, AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage (+9 more)

### Community 60 - "AsyncSession"
Cohesion: 0.11
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "endpoints.js"
Cohesion: 0.12
Nodes (17): ActionItemsAPI, AgentAPI, AnalyticsAPI, CandidateProfileAPI, EmailAccountsAPI, EventsAPI, PromptsAPI, SearchAPI (+9 more)

### Community 62 - "LogActivityModal.vue"
Cohesion: 0.10
Nodes (17): ApplicationsAPI, appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction (+9 more)

### Community 63 - "dock.js"
Cohesion: 0.23
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "CompanyLogo.vue"
Cohesion: 0.13
Nodes (14): attemptIndex, candidateDomains, fallbackInitial, faviconUrl, hasError, isLoaded, props, formatSalaryRange() (+6 more)

### Community 65 - "interview_guide_graph.py"
Cohesion: 0.20
Nodes (17): build_interview_guide_graph(), extractor_node(), InterviewGuideState, Any, RunnableConfig, TypedDict, Generates the clean semantic HTML for the current section in the queue., Routes back to section_generator_node if more sections remain and iteration… (+9 more)

### Community 66 - "PrioritySemaphore"
Cohesion: 0.13
Nodes (11): cancel_running_task(), get_running_task_ids(), PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Registers an in-memory running asyncio Task by database task ID., Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs. (+3 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 71 - "create_account"
Cohesion: 0.18
Nodes (12): create_account(), patch, post, Add a new email account configuration., Update settings or credentials for an existing email account., update_account(), EmailAccountBase, EmailAccountCreate (+4 more)

### Community 72 - "System Architecture Documentation"
Cohesion: 0.15
Nodes (14): Camofox Stealth Scraper, Intake StateGraph, Interview Guide Graph, Mock Interview Simulator Service, pg_trgm GIN Trigram Matching, pgvector HNSW Cosine Indexing, Reasoning Suppression (0-effort), System Architecture Documentation (+6 more)

### Community 73 - "FloatingAgentChatWidget.vue"
Cohesion: 0.18
Nodes (11): chatMessagesContainer, chatStore, handleKeyDown(), handleSendMessage(), inputMessage, isOpen, route, router (+3 more)

### Community 74 - "loadEmailAccounts"
Cohesion: 0.15
Nodes (14): buildEmailAccountPayload(), confirmClearAccountHistory(), confirmClearAllHistory(), confirmDeleteAccount(), fetchEmailFolders(), handleOAuthSuccessMessage(), handleStep2NextIMAP(), loadEmailAccounts() (+6 more)

### Community 75 - "load_settings"
Cohesion: 0.17
Nodes (23): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously. (+15 more)

### Community 76 - "extractJobData"
Cohesion: 0.22
Nodes (8): extractJobData(), deriveTitleFromDoc(), getText(), getTextIn(), queryFirst(), queryFirstIn(), isCleanTitle(), resolveCanonicalJobUrl()

### Community 77 - "index.js"
Cohesion: 0.19
Nodes (13): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+5 more)

### Community 79 - "saveProfileField"
Cohesion: 0.17
Nodes (12): addCompetency(), addDomainArea(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeCompetency(), removeDomainArea(), removeSkill() (+4 more)

### Community 81 - "admin.py"
Cohesion: 0.14
Nodes (20): delete_application(), delete_event(), get_staleness_stats(), AsyncSession, delete, get, post, # TODO: Trigger re-indexing of the embedding for this application based on the… (+12 more)

### Community 82 - "routers/system_settings.py"
Cohesion: 0.21
Nodes (14): verify_admin_access(), patch, update_global_settings(), get_system_settings(), AsyncSession, get, patch, update_system_settings() (+6 more)

### Community 83 - "handleOAuthSuccess"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "selectItem"
Cohesion: 0.24
Nodes (11): filteredAndSortedItems, formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType(), getItemCompany(), getItemPosition(), handleKeyDown(), selectItem() (+3 more)

### Community 85 - "jt script"
Cohesion: 0.29
Nodes (7): dev.sh script, jt script, check_docker(), ensure_env(), open_browser(), show_help(), prod.sh script

### Community 86 - "scrollToBottom"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 87 - "formatRelativeDate"
Cohesion: 0.28
Nodes (9): formatRelativeDate(), formatDueDateFriendly(), formatScheduledDate(), formatScheduledDateFriendly(), getDueDate(), getDueDateStr(), getScheduledInterviewDate(), getScheduleUrgencyClass() (+1 more)

### Community 88 - "resolve_company_domain"
Cohesion: 0.20
Nodes (19): clean_domain(), extract_domain_from_url(), is_ats_hostname(), query_clearbit_autocomplete(), Domain resolution service for extracting and discovering official company…, Checks if a given hostname belongs to a known ATS or job board., Extracts the company domain from a job posting URL if it is not an ATS., Queries Clearbit's public autocomplete API to find the company's official… (+11 more)

### Community 89 - "PostHireModal.vue"
Cohesion: 0.32
Nodes (7): actions, appStore, emit, handleConfirm(), handleDecideLater(), props, submitting

### Community 90 - "advanceAppStage"
Cohesion: 0.38
Nodes (7): advanceAppStage(), executeTransition(), getNextStatus(), handleStatusChange(), onDrop(), openDeleteConfirm(), openTransitionModal()

### Community 91 - "routers/diagnostics.py"
Cohesion: 0.25
Nodes (13): export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces(), AsyncSession (+5 more)

### Community 92 - "fuzzyMatch.js"
Cohesion: 0.48
Nodes (6): fuzzyFilterApplications(), fuzzyScore(), levenshteinDistance(), scoreApplicationMatch(), stringSimilarity(), filteredExistingApps

### Community 93 - "syncStudioForm"
Cohesion: 0.33
Nodes (7): deleteProvider(), fetchStudioModels(), loadProviders(), onStudioProviderChange(), saveProvider(), selectStudioTask(), syncStudioForm()

### Community 94 - "loadBindings"
Cohesion: 0.33
Nodes (7): fetchGlobalModels(), loadBindings(), onGlobalProviderChange(), saveGlobalDefault(), scheduleGlobalAutoSave(), selectGlobalSuggestedModel(), syncGlobalForm()

### Community 95 - "fetchStagingItems"
Cohesion: 0.25
Nodes (8): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), handleReopenStagingItem(), quickDismissItem(), submitResolution()

### Community 100 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 106 - "cleanCVText"
Cohesion: 0.67
Nodes (3): cleanCVText(), handleFileUpload(), handleFormatCleanClick()

### Community 107 - "pollTaskUntilComplete"
Cohesion: 0.67
Nodes (3): loadProfile(), pollTaskUntilComplete(), processCV()

### Community 108 - "openAddEmailAccountModal"
Cohesion: 0.67
Nodes (3): loadOAuthConfig(), openAddEmailAccountModal(), toggleEmailIntake()

### Community 110 - "JobTrackerState"
Cohesion: 0.14
Nodes (35): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, JobTrackerState, TypedDict, cover_letter_node(), db_commit_node(), extraction_node(), fuzzy_match_node() (+27 more)

### Community 145 - "Base"
Cohesion: 0.15
Nodes (23): AgentChatModel, ActionItemModel, ApplicationEmbeddingModel, Base, JobPostingModel, OtherEventModel, CandidateCVModel, TraceEventModel (+15 more)

### Community 146 - "test_new_features.py"
Cohesion: 0.14
Nodes (18): prune_and_sanitize_tool_output(), Any, Sanitizes and prunes tool execution output payloads: - Parses string payloads…, Splits text semantically using RecursiveCharacterTextSplitter on sentence and…, Cleans raw text (normalizes whitespace, strips noise) and semantically…, split_text_semantically(), truncate_text_semantically(), asyncio (+10 more)

### Community 147 - "test_schemas.py"
Cohesion: 0.19
Nodes (13): Transitions application to a new column/stage (e.g. TECHNICAL_INTERVIEW, OFFER,…, transition_application(), AllowedApplicationStatus, ApplicationTransitionRequest, ApplicationUpdate, test_application_transition_request_date_coercion(), test_application_update_job_spec_fields(), test_bulk_transition_request_schema() (+5 more)

### Community 149 - "FailoverChatModel"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 150 - "_execute_evaluation_steps"
Cohesion: 0.50
Nodes (8): _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), AsyncSession, generate_cover_letter(), Generates a tailored cover letter using the COVER_LETTER task type and…, IntakeEvaluationTaskModel

### Community 151 - "LazyAsyncPostgresSaver"
Cohesion: 0.21
Nodes (3): AsyncPostgresSaver, LazyAsyncPostgresSaver, setter

### Community 153 - "asyncio"
Cohesion: 0.33
Nodes (7): asyncio, test_get_analytics_overview_unit(), test_get_funnel_performance_metrics_unit(), test_get_role_alignment_unit(), test_delete_application_event(), test_delete_other_event(), test_move_event_to_staging()

### Community 154 - "AIProviderModel"
Cohesion: 0.38
Nodes (13): AIProviderModel, AITaskBindingModel, check_ai_provider_health(), asyncio, AsyncSession, fixture, reset_health_cache(), test_ai_health_cache_ttl_and_invalidation() (+5 more)

### Community 157 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 158 - "services/llm.py"
Cohesion: 0.13
Nodes (20): ApplicationEmbeddingModel, ApplicationSummaryResult, anonymize_and_parse_cv(), extract_email_info(), extract_job_spec(), generate_and_save_application_embedding(), generate_embedding(), get_active_llm_config() (+12 more)

### Community 159 - "schemas/intake.py"
Cohesion: 0.26
Nodes (13): AssessJobRequest, BulkTaskActionRequest, BulkTaskActionResult, ConfirmAssessmentRequest, DirectEmailIntakeRequest, EmailBatchIntakeRequest, EmailProcessingSummary, EnqueueAssessmentRequest (+5 more)

### Community 160 - "trace_operation"
Cohesion: 0.27
Nodes (12): Any, AsyncSession, datetime, Persists a programmatic execution trace event into the trace_events table., Async context manager that measures execution time and records diagnostic…, record_diagnostic_event(), trace_operation(), asyncio (+4 more)

### Community 162 - "routers/search.py"
Cohesion: 0.24
Nodes (10): generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, AsyncSession, get, Returns matching companies alongside total tracked application count., search_companies(), semantic_search(), CompanySearchResult (+2 more)

### Community 165 - "PostgresTracer"
Cohesion: 0.27
Nodes (6): AsyncBaseTracer, PostgresTracer, asyncio, test_postgres_tracer_background_persist_and_flush(), test_postgres_tracer_does_not_clear_global_run_map(), Run

### Community 166 - "scheduleStudioAutoSave"
Cohesion: 0.25
Nodes (9): applyProbeRecommendations(), loadPrompts(), resetGlobalDefaultToDefaults(), resetStudioPrompt(), resetStudioTaskToDefaults(), saveStudioTask(), scheduleStudioAutoSave(), selectStudioSuggestedModel() (+1 more)

### Community 167 - "programmatic_scrub_cv"
Cohesion: 0.47
Nodes (4): programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty()

## Knowledge Gaps
- **681 isolated node(s):** `uiStore`, `appStore`, `queueStore`, `{ isCoverLetterModalOpen, coverLetterAppId }`, `application` (+676 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `uiStore.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `AssessmentsView.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `endpoints.js`, `LogActivityModal.vue`, `InterviewReaderModal.vue`, `index.js`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `ApplicationEventModel`, `InterviewSimulatorService`, `routers/search.py`, `asyncio`, `services/analytics.py`, `ExtractedEmailInfo`, `routers/intake.py`, `load_settings`, `services/agent_tools.py`, `JobTrackerState`, `GenerateInterviewGuideRequest`, `main.py`, `admin.py`, `Base`, `routers/action_items.py`, `IntakeEvaluationTaskModel`, `normalize_job_url`, `routers/extension.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `EmailAccountModel` connect `EmailAccountModel` to `ApplicationEventModel`, `create_account`, `Base`, `test_email_accounts.py`, `routers/email_accounts.py`, `routers/llm.py`, `conftest.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 78 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 78 INFERRED edges - model-reasoned connections that need verification._
- **Are the 60 inferred relationships involving `CompanyModel` (e.g. with `update_application()` and `clip_job_pre_extracted()`) actually correct?**
  _`CompanyModel` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `IntakeEvaluationTaskModel` (e.g. with `generate_app_cover_letter()` and `regenerate_app_cover_letter()`) actually correct?**
  _`IntakeEvaluationTaskModel` has 28 INFERRED edges - model-reasoned connections that need verification._