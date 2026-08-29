# Graph Report - job-tracker  (2026-08-29)

## Corpus Check
- 225 files · ~273,486 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2925 nodes · 5799 edges · 182 communities (119 shown, 63 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 688 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7f360fce`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- InterviewSimulatorService
- ApplicationDetailDrawer.vue
- services/agent_tools.py
- OnboardingWizardModal.vue
- schemas/analytics.py
- ApplicationsView.vue
- routers/applications.py
- parse_eml
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- Base
- StagingView.vue
- trace_operation
- load_settings
- routers/ai_config.py
- routers/candidate_profile.py
- popup.js
- AssessmentsView.vue
- routers/action_items.py
- routers/email_accounts.py
- AnalyticsView.vue
- CandidateProfileView.vue
- JobIntakeView.vue
- test_candidate_profile.py
- EmailAccountsSettings.vue
- FloatingQueueWidget.vue
- get_task_chat_model
- routers/intake.py
- manifest.json
- ProcessedEmailModel
- ApplicationEventModel
- ActionItemsView.vue
- CoverLetterModal.vue
- endpoints.js
- dependencies
- process_evaluation_task
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- main.py
- test_analytics.py
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- test_bulk_transition.py
- AITaskBindingModel
- fetch_emails_from_account
- datetime
- ApplicationModel
- test_email_accounts.py
- PostgresTracer
- EmailAccountModel
- test_llm_factory.py
- LogActivityModal.vue
- AsyncSession
- scrollToBottom
- routers/agent_chat.py
- IntakeQueueDrawer.vue
- AsyncSession
- extract_usage_from_payload
- fetchActionItems
- dock.js
- CompanyLogo.vue
- conftest.py
- closeSidebarOnMobile
- routers/prompts.py
- InterviewReaderModal.vue
- AsyncSession
- index.js
- create_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- routers/llm.py
- extractJobData
- FailoverChatModel
- TaskTracker
- saveProfileField
- schemas/intake.py
- PrioritySemaphore
- normalize_job_url
- handleOAuthSuccess
- selectItem
- jt script
- SearchView.vue
- formatRelativeDate
- resolve_company_domain
- PostHireModal.vue
- advanceAppStage
- set_ai_task_binding
- fuzzyMatch.js
- scheduleStudioAutoSave
- loadBindings
- fetchStagingItems
- datetime
- clearSelection
- .normalize_work_model
- loadUsageOverview
- Any
- _execute_evaluation_steps
- cleanCVText
- pollTaskUntilComplete
- openAddEmailAccountModal
- skill_taxonomy.py
- ExtractedEmailInfo
- Email Synchronization Engine
- Frontend SPA Entry HTML
- handleFileInput
- emailRenderer.js
- scrubber.js
- AsyncSession
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
- UploadFile
- CompanyModel
- interviewStore.js
- patch
- Request
- patch
- handleAnalyzeSpec
- field_validator
- asyncio
- asyncio
- test_new_features.py
- useQueueStore
- filteredInterviewSessions
- close
- LazyAsyncPostgresSaver
- Any
- executeDirectTransition
- clean_html_text
- JobAssessmentResult
- StrEnum
- env.py
- BaseModel
- BackgroundTasks
- Any
- Any
- AsyncSession
- patch
- asyncio
- datetime
- RunnableConfig
- anonymize_and_parse_cv
- patch
- TypedDict
- RunnableConfig
- post
- put
- setter
- AsyncSession
- delete
- get
- post
- test_extension.py
- BaseModel
- BaseModel
- JobAssessmentResult

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 101 edges
2. `CompanyModel` - 80 edges
3. `ApplicationEventModel` - 42 edges
4. `EmailAccountModel` - 39 edges
5. `useUIStore` - 38 edges
6. `PostgresTracer` - 35 edges
7. `EmailPayload` - 35 edges
8. `Base` - 34 edges
9. `InterviewSimulatorService` - 32 edges
10. `get_task_chat_model()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Root Pre-Commit Configuration` --semantically_similar_to--> `Backend Pre-Commit Configuration`  [INFERRED] [semantically similar]
  .pre-commit-config.yaml → backend/.pre-commit-config.yaml
- `seed()` --uses--> `IntakeEvaluationTaskModel`  [INFERRED]
  seed_db.py → backend/app/models/intake_tasks.py
- `seed()` --uses--> `ApplicationModel`  [INFERRED]
  seed_db.py → backend/app/models/applications.py
- `useQueueStore` --indirect_call--> `enqueueAssessment()`  [INFERRED]
  frontend/src/stores/queueStore.js → extension/utils/api.js
- `Dependabot Configuration` --references--> `Vue 3 Frontend SPA`  [INFERRED]
  .github/dependabot.yml → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Supported AI Provider Ecosystem** — concept_lm_studio_provider, concept_ollama_provider, concept_openai_provider, concept_anthropic_provider, concept_gemini_provider, concept_openrouter_provider, concept_failover_chat_model, concept_ai_task_bindings [EXTRACTED 1.00]
- **CI Quality Gate Lint Test Build** — _github_workflows_backend_ci_backend_ci_workflow, _github_workflows_frontend_ci_frontend_ci_workflow, _pre_commit_config_root_pre_commit, backend__pre_commit_config_backend_pre_commit, concept_ruff_linter [EXTRACTED 1.00]
- **Docker Compose Deployment Variants Production Dev External** — docker_compose_production_stack, docker_compose_dev_dev_stack, docker_compose_external_external_services_override [EXTRACTED 1.00]
- **Backend LangGraph State Machines** — docs_architecture_intake_stategraph, docs_architecture_interview_guide_graph, docs_architecture_mock_interview_simulator [INFERRED 0.85]
- **Companion Browser Extension Architecture** — extension_readme_companion_extension, extension_shadow_dom_dock, extension_popup_popup_html, extension_chromewebstore_docs [INFERRED 0.85]

## Communities (182 total, 63 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (79): PromptsAPI, accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri (+71 more)

### Community 1 - "InterviewSimulatorService"
Cohesion: 0.11
Nodes (46): InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions(), next_question() (+38 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (52): EventsAPI, ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData (+44 more)

### Community 3 - "services/agent_tools.py"
Cohesion: 0.10
Nodes (47): ApplicationEmbeddingModel, AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, ListApplicationsInput, ManageActionItemsInput, ManageIntakeQueueInput (+39 more)

### Community 4 - "OnboardingWizardModal.vue"
Cohesion: 0.03
Nodes (47): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+39 more)

### Community 5 - "schemas/analytics.py"
Cohesion: 0.07
Nodes (52): AnalyticsOverviewResponse, get_funnel_metrics(), get_overview(), get_role_alignment_endpoint(), AsyncSession, get, get_funnel_metrics(), AsyncSession (+44 more)

### Community 6 - "ApplicationsView.vue"
Cohesion: 0.03
Nodes (41): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, archiveSortKey, archiveSortOrder (+33 more)

### Community 7 - "routers/applications.py"
Cohesion: 0.05
Nodes (86): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, analyze_app_job_spec(), bulk_transition_applications(), clear_app_interview_guide() (+78 more)

### Community 8 - "parse_eml"
Cohesion: 0.14
Nodes (20): _extract_ics_summary(), normalize_resume_text(), parse_cv_document(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload. (+12 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.05
Nodes (33): activeCancelTask, activeCount, activeFixJDTask, completedCount, deleteTask(), expandedEmailDetails, failedCount, filteredTasks (+25 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "Base"
Cohesion: 0.11
Nodes (32): AgentChatModel, ActionItemModel, ApplicationEmbeddingModel, Base, JobPostingModel, OtherEventModel, CandidateCVModel, TraceEventModel (+24 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (36): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+28 more)

### Community 14 - "trace_operation"
Cohesion: 0.10
Nodes (37): clean_extracted_text(), has_job_content_keywords(), BaseModel, Validates URL protocol and private IP / loopback address validation (SSRF…, Blazing fast multi-language scraper keyword validation using Python set hash…, Backward-compatible alias for validate_job_content., Normalizes whitespace and strips javascript code blocks, jQuery artifacts, and…, Scrapes a URL using the running Camofox browser automation server. (+29 more)

### Community 15 - "load_settings"
Cohesion: 0.11
Nodes (34): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously. (+26 more)

### Community 16 - "routers/ai_config.py"
Cohesion: 0.19
Nodes (25): _fetch_models_from_endpoint(), _is_embedding_model(), _is_reasoning_model(), list_provider_models(), probe_model_capabilities(), reset_pricing_rates_endpoint(), test_ai_provider(), test_ai_task_binding() (+17 more)

### Community 17 - "routers/candidate_profile.py"
Cohesion: 0.12
Nodes (25): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+17 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.05
Nodes (30): scores, getFitScores(), activeQueueTasks, activeTab, allCompletedTasks, appStore, averageFitScore, bulkArchive() (+22 more)

### Community 20 - "routers/action_items.py"
Cohesion: 0.15
Nodes (27): compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks, delete (+19 more)

### Community 21 - "routers/email_accounts.py"
Cohesion: 0.11
Nodes (36): clear_account_processed_emails(), clear_all_processed_emails(), delete_account(), EmailFoldersResponse, fetch_account_folders(), get_account(), get_oauth_authorize_url(), get_oauth_config() (+28 more)

### Community 22 - "AnalyticsView.vue"
Cohesion: 0.06
Nodes (40): AnalyticsAPI, formatJobSpecCompensation(), getCurrencySymbol(), activeTab, alignmentData, alignmentSubTab, analyticsData, copiedItemKey (+32 more)

### Community 23 - "CandidateProfileView.vue"
Cohesion: 0.05
Nodes (27): CandidateProfileAPI, currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling (+19 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.06
Nodes (27): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+19 more)

### Community 25 - "test_candidate_profile.py"
Cohesion: 0.14
Nodes (19): DomainExperienceItem, LanguageMatchResult, SpokenLanguageRequirement, calibrate_assessment_score_and_recommendation(), Applies mathematical bounding and recommendation synchronization to eliminate…, compute_programmatic_skill_match(), _is_skill_matched(), _normalize_token() (+11 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (25): EmailAccountsAPI, accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm (+17 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "get_task_chat_model"
Cohesion: 0.24
Nodes (17): _clean_base_url(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model(), AsyncSession, Returns cached Embeddings model instance or initializes and caches a new one. (+9 more)

### Community 29 - "routers/intake.py"
Cohesion: 0.07
Nodes (59): AssessJobRequest, assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations(), confirm_job_assessment(), delete_evaluation_task() (+51 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "ProcessedEmailModel"
Cohesion: 0.18
Nodes (21): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, BaseModel, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, TaskResponse, enable_email_intake_mock() (+13 more)

### Community 32 - "ApplicationEventModel"
Cohesion: 0.08
Nodes (44): ApplicationEventModel, clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text… (+36 more)

### Community 33 - "ActionItemsView.vue"
Cohesion: 0.08
Nodes (17): actionItems, activeUrgencyDropdown, applicationsList, currentEditId, displayedTasks, filterTab, isEditing, isLoading (+9 more)

### Community 34 - "CoverLetterModal.vue"
Cohesion: 0.06
Nodes (36): activeCoverLetterTask, application, appStore, autoSaveStatus, charCount, close(), COVER_LETTER_LENGTHS, COVER_LETTER_TONES (+28 more)

### Community 35 - "endpoints.js"
Cohesion: 0.14
Nodes (18): ActionItemsAPI, AgentAPI, AIConfigAPI, IntakeAPI, StagingAPI, SystemSettingsAPI, uiStore, uiStore (+10 more)

### Community 36 - "dependencies"
Cohesion: 0.07
Nodes (28): axios, dompurify, dependencies, axios, dompurify, @lucide/vue, lucide-vue-next, pinia (+20 more)

### Community 37 - "process_evaluation_task"
Cohesion: 0.14
Nodes (30): cancel_running_task(), get_running_task_ids(), Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs., register_running_task(), unregister_running_task() (+22 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.08
Nodes (16): getRouteTitle(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount, pendingTasksCount, pillLabel, pillTitle, popoverContainerRef (+8 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.07
Nodes (24): analysisData, application, compensationText, computedRatioText, computedScoreText, criticalRisks, emit, error (+16 more)

### Community 41 - "main.py"
Cohesion: 0.07
Nodes (37): check_db_connection(), ensure_db_schema(), get_db(), AsyncSession, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, generate_query_embedding(), Generates a vector embedding for an incoming search query string using… (+29 more)

### Community 42 - "test_analytics.py"
Cohesion: 0.29
Nodes (9): override_db(), asyncio, AsyncSession, test_get_analytics_overview(), test_get_funnel_metrics_monthly(), test_get_funnel_metrics_weekly(), test_get_role_alignment(), test_get_role_alignment_filtered_track() (+1 more)

### Community 43 - "DiagnosticsView.vue"
Cohesion: 0.09
Nodes (19): DiagnosticsAPI, activeCategory, categories, copied, loadData(), loading, loadingDetail, loadingTraces (+11 more)

### Community 44 - "DateTimePicker.vue"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "JobIntakeModal.vue"
Cohesion: 0.09
Nodes (23): activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls(), handleBulkPromptDecision() (+15 more)

### Community 46 - "test_bulk_transition.py"
Cohesion: 0.42
Nodes (10): async_client(), AsyncClient, asyncio, AsyncSession, fixture, test_bulk_transition_archives_open_applications(), test_bulk_transition_creates_timeline_events(), test_bulk_transition_dismisses_pending_action_items_on_terminal() (+2 more)

### Community 47 - "AITaskBindingModel"
Cohesion: 0.35
Nodes (13): AIProviderModel, AITaskBindingModel, invalidate_ai_health_cache(), asyncio, AsyncSession, fixture, reset_health_cache(), test_ai_health_cache_ttl_and_invalidation() (+5 more)

### Community 48 - "fetch_emails_from_account"
Cohesion: 0.12
Nodes (21): _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using…, GmailOAuthAdapter (+13 more)

### Community 50 - "ApplicationModel"
Cohesion: 0.18
Nodes (20): ApplicationModel, generate_interview_guide(), Coordinates candidate profile retrieval, job posting lookup, LangGraph…, archive_stale_applications(), delete_stale_agent_chats(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or… (+12 more)

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "PostgresTracer"
Cohesion: 0.11
Nodes (19): ApplicationSummaryResult, AsyncBaseTracer, Strips <think>...</think> reasoning tags from LLM output text., strip_reasoning_tags(), extract_email_info(), extract_job_spec(), get_active_llm_config(), Extracts structured job application metadata from email body using LangChain… (+11 more)

### Community 53 - "EmailAccountModel"
Cohesion: 0.11
Nodes (20): _encrypt_table_secrets(), Connection, upgrade(), decrypt_secret(), encrypt_secret(), _get_fernet(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows. (+12 more)

### Community 54 - "test_llm_factory.py"
Cohesion: 0.20
Nodes (22): get_active_llm_config_dict(), Retrieves runtime LLM configuration from the database., Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem (+14 more)

### Community 55 - "LogActivityModal.vue"
Cohesion: 0.10
Nodes (17): ApplicationsAPI, appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction (+9 more)

### Community 56 - "AsyncSession"
Cohesion: 0.10
Nodes (31): AsyncSession, bulk_dismiss_staging_items(), clear_resolved_staging_items(), get_staging_item(), list_staging_items(), Bulk dismisses specific staging items or all pending staging items matching…, Fetches full details for a single staged item., Purges PROCESSED staging items, optionally older than a given number of days. (+23 more)

### Community 57 - "scrollToBottom"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 58 - "routers/agent_chat.py"
Cohesion: 0.19
Nodes (16): get_prompt_template(), Retrieves prompt template from DB with in-memory caching, falling back to…, AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage, delete_chat() (+8 more)

### Community 59 - "IntakeQueueDrawer.vue"
Cohesion: 0.22
Nodes (5): activeCount, hasItems, queue, STAGES, uiStore

### Community 60 - "AsyncSession"
Cohesion: 0.11
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "extract_usage_from_payload"
Cohesion: 0.17
Nodes (18): update_pricing_rates_endpoint(), calculate_cost_and_savings(), extract_usage_from_payload(), get_all_pricing_rates(), _match_pricing_key(), Matches a model name string (including path / provider prefixes) to a pricing…, Returns all current pricing rates as a list with custom overrides applied., Updates custom pricing rate override in memory. (+10 more)

### Community 62 - "fetchActionItems"
Cohesion: 0.33
Nodes (6): deleteTask(), fetchActionItems(), handleSaveTask(), selectMetricTab(), setManualUrgency(), toggleTaskStatus()

### Community 63 - "dock.js"
Cohesion: 0.23
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "CompanyLogo.vue"
Cohesion: 0.13
Nodes (14): attemptIndex, candidateDomains, fallbackInitial, faviconUrl, hasError, isLoaded, props, formatSalaryRange() (+6 more)

### Community 65 - "conftest.py"
Cohesion: 0.12
Nodes (18): db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info(), mock_job_email_payload(), postgres_container(), AsyncSession, fixture (+10 more)

### Community 66 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 67 - "routers/prompts.py"
Cohesion: 0.17
Nodes (16): verify_admin_access(), get_prompt(), list_prompts(), AsyncSession, get, patch, post, List all available system prompts. (+8 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 69 - "AsyncSession"
Cohesion: 0.19
Nodes (19): AIProviderModel, clear_embeddings_cache(), Clears cached Embeddings model instances., check_ai_provider_health(), create_ai_provider(), delete_ai_provider(), delete_ai_task_binding(), get_ai_health_endpoint() (+11 more)

### Community 70 - "index.js"
Cohesion: 0.21
Nodes (12): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+4 more)

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

### Community 75 - "routers/llm.py"
Cohesion: 0.24
Nodes (15): mask_secret(), LLMConfigModel, get_current_llm_config(), LLMConfigRead, LLMConfigUpdate, Any, AsyncSession, BaseModel (+7 more)

### Community 76 - "extractJobData"
Cohesion: 0.22
Nodes (8): extractJobData(), deriveTitleFromDoc(), getText(), getTextIn(), queryFirst(), queryFirstIn(), isCleanTitle(), resolveCanonicalJobUrl()

### Community 77 - "FailoverChatModel"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 79 - "saveProfileField"
Cohesion: 0.14
Nodes (14): addCompetency(), addDomainArea(), addLanguage(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeCompetency(), removeDomainArea() (+6 more)

### Community 80 - "schemas/intake.py"
Cohesion: 0.26
Nodes (13): AssessJobRequest, BulkTaskActionRequest, BulkTaskActionResult, ConfirmAssessmentRequest, DirectEmailIntakeRequest, EmailBatchIntakeRequest, EmailProcessingSummary, EnqueueAssessmentRequest (+5 more)

### Community 81 - "PrioritySemaphore"
Cohesion: 0.24
Nodes (4): PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 82 - "normalize_job_url"
Cohesion: 0.13
Nodes (17): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, persist_or_stage_job_assessment(), AsyncSession, Persists an AI job assessment to the database. If target_application_id is…, resolve_job_currency(), asyncio, Test that submitting the same job posting URL with different referral… (+9 more)

### Community 83 - "handleOAuthSuccess"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "selectItem"
Cohesion: 0.24
Nodes (11): filteredAndSortedItems, formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType(), getItemCompany(), getItemPosition(), handleKeyDown(), selectItem() (+3 more)

### Community 85 - "jt script"
Cohesion: 0.29
Nodes (7): dev.sh script, jt script, check_docker(), ensure_env(), open_browser(), show_help(), prod.sh script

### Community 86 - "SearchView.vue"
Cohesion: 0.25
Nodes (8): SearchAPI, executeSearch(), handleKeyDown(), hasSearched, loading, results, searchQuery, uiStore

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

### Community 91 - "set_ai_task_binding"
Cohesion: 0.53
Nodes (6): AITaskBindingModel, list_ai_task_bindings(), set_ai_task_binding(), _to_binding_read(), AITaskBindingRead, put

### Community 92 - "fuzzyMatch.js"
Cohesion: 0.48
Nodes (6): fuzzyFilterApplications(), fuzzyScore(), levenshteinDistance(), scoreApplicationMatch(), stringSimilarity(), filteredExistingApps

### Community 93 - "scheduleStudioAutoSave"
Cohesion: 0.20
Nodes (11): applyProbeRecommendations(), deleteProvider(), fetchStudioModels(), loadProviders(), onStudioProviderChange(), saveProvider(), scheduleStudioAutoSave(), selectStudioSuggestedModel() (+3 more)

### Community 94 - "loadBindings"
Cohesion: 0.21
Nodes (12): fetchGlobalModels(), loadBindings(), loadPrompts(), onGlobalProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt(), resetStudioTaskToDefaults(), saveGlobalDefault() (+4 more)

### Community 95 - "fetchStagingItems"
Cohesion: 0.25
Nodes (8): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), handleReopenStagingItem(), quickDismissItem(), submitResolution()

### Community 97 - "clearSelection"
Cohesion: 0.50
Nodes (4): bulkDeleteSelected(), bulkRetrySelected(), clearSelection(), toggleSelectAll()

### Community 99 - "loadUsageOverview"
Cohesion: 0.67
Nodes (3): loadUsageOverview(), resetPricingRatesToDefaults(), savePricingRates()

### Community 101 - "_execute_evaluation_steps"
Cohesion: 0.50
Nodes (8): _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), AsyncSession, generate_cover_letter(), Generates a tailored cover letter using the COVER_LETTER task type and…, IntakeEvaluationTaskModel

### Community 106 - "cleanCVText"
Cohesion: 0.67
Nodes (3): cleanCVText(), handleFileUpload(), handleFormatCleanClick()

### Community 107 - "pollTaskUntilComplete"
Cohesion: 0.67
Nodes (3): loadProfile(), pollTaskUntilComplete(), processCV()

### Community 108 - "openAddEmailAccountModal"
Cohesion: 0.67
Nodes (3): loadOAuthConfig(), openAddEmailAccountModal(), toggleEmailIntake()

### Community 110 - "ExtractedEmailInfo"
Cohesion: 0.07
Nodes (69): Any, JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., cover_letter_node(), db_commit_node(), extraction_node() (+61 more)

### Community 137 - "CompanyModel"
Cohesion: 0.12
Nodes (22): asyncio, CompanyModel, test_get_analytics_overview_unit(), test_get_funnel_performance_metrics_unit(), test_get_role_alignment_unit(), test_analyze_spec_endpoint_validation_and_enqueue(), test_worker_processes_application_assessment(), test_worker_skips_keyword_check_for_user_provided_jd() (+14 more)

### Community 146 - "test_new_features.py"
Cohesion: 0.13
Nodes (18): clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., prune_and_sanitize_tool_output(), Any, Sanitizes and prunes tool execution output payloads: - Parses string payloads…, Splits text semantically using RecursiveCharacterTextSplitter on sentence and…, Cleans raw text (normalizes whitespace, strips noise) and semantically…, split_text_semantically() (+10 more)

### Community 151 - "LazyAsyncPostgresSaver"
Cohesion: 0.21
Nodes (3): AsyncPostgresSaver, LazyAsyncPostgresSaver, setter

### Community 154 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 157 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 167 - "anonymize_and_parse_cv"
Cohesion: 0.28
Nodes (7): anonymize_and_parse_cv(), De-identifies candidate resume: - Runs local programmatic regex pre-scrubber on…, programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty(), CVAnonymizationResult

### Community 178 - "test_extension.py"
Cohesion: 0.60
Nodes (5): asyncio, AsyncSession, test_extension_clip_job_direct(), test_extension_clip_url_pipeline(), test_extension_intake_url_and_jd_routes()

## Knowledge Gaps
- **700 isolated node(s):** `uiStore`, `appStore`, `queueStore`, `{ isCoverLetterModalOpen, coverLetterAppId }`, `application` (+695 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **63 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `endpoints.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `AssessmentsView.vue`, `useQueueStore`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `LogActivityModal.vue`, `IntakeQueueDrawer.vue`, `InterviewReaderModal.vue`, `index.js`, `SearchView.vue`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `ApplicationEventModel`, `InterviewSimulatorService`, `services/agent_tools.py`, `process_evaluation_task`, `routers/applications.py`, `main.py`, `CompanyModel`, `Base`, `ExtractedEmailInfo`, `test_bulk_transition.py`, `normalize_job_url`, `test_extension.py`, `routers/action_items.py`, `routers/intake.py`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `useQueueStore` connect `useQueueStore` to `CoverLetterModal.vue`, `endpoints.js`, `AppNavbar.vue`, `QueueView.vue`, `JobIntakeModal.vue`, `popup.js`, `AssessmentsView.vue`, `JobIntakeView.vue`, `FloatingQueueWidget.vue`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 76 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `CompanyModel` (e.g. with `update_application()` and `clip_job_pre_extracted()`) actually correct?**
  _`CompanyModel` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `EmailAccountModel` (e.g. with `clear_account_processed_emails()` and `clear_all_processed_emails()`) actually correct?**
  _`EmailAccountModel` has 20 INFERRED edges - model-reasoned connections that need verification._