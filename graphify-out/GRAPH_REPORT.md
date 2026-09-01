# Graph Report - job-tracker  (2026-09-01)

## Corpus Check
- 231 files · ~284,761 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3034 nodes · 6007 edges · 203 communities (128 shown, 75 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 702 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `25ea402c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- PostgresTracer
- ApplicationDetailDrawer.vue
- services/agent_tools.py
- OnboardingWizardModal.vue
- test_skill_normalizer.py
- ApplicationsView.vue
- cancel_evaluation_task
- parse_eml
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- seed_development_dataset
- StagingView.vue
- normalize_job_url
- routers/applications.py
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
- EmailPayload
- ActionItemsView.vue
- CoverLetterModal.vue
- LogActivityModal.vue
- dependencies
- process_evaluation_task
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- routers/search.py
- ExtractedEmailInfo
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- schemas/staging.py
- IntakeQueueDrawer.vue
- fetch_emails_from_account
- datetime
- clean_html_text
- test_email_accounts.py
- AsyncSession
- decrypt_secret
- test_llm_factory.py
- test_persist_job_assessment_unrestricted_urls
- loadBindings
- scrollToBottom
- get_active_llm_config_dict
- uiStore.js
- AsyncSession
- routers/diagnostics.py
- ApplicationModel
- dock.js
- CompanyLogo.vue
- conftest.py
- closeSidebarOnMobile
- routers/prompts.py
- InterviewReaderModal.vue
- AIProviderModel
- index.js
- create_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- clearSelection
- extractJobData
- FailoverChatModel
- TaskTracker
- saveProfileField
- schemas/intake.py
- PrioritySemaphore
- BaseModel
- handleOAuthSuccess
- selectItem
- jt
- SearchView.vue
- formatRelativeDate
- resolve_company_domain
- PostHireModal.vue
- advanceAppStage
- AITaskBindingModel
- fuzzyMatch.js
- AsyncSession
- scheduleStudioAutoSave
- fetchStagingItems
- datetime
- BaseModel
- asyncio
- loadUsageOverview
- Any
- fixture
- a1b2c3d4e5f6_add_cover_letter_fields.py
- b2c3d4e5f6a7_update_email_accounts_and_onboarding_settings.py
- c1d2e3f4a5b6_add_is_fallback_to_ai_providers.py
- c2d3e4f5a6b7_add_interview_sessions_question_mode.py
- cleanCVText
- pollTaskUntilComplete
- openAddEmailAccountModal
- skill_taxonomy.py
- Any
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
- d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py
- CompanyModel
- interviewStore.js
- patch
- Request
- patch
- handleAnalyzeSpec
- field_validator
- Base
- asyncio
- test_new_features.py
- e4f5a6b7c8d9_drop_candidate_cv_is_active.py
- f5a6b7c8d9e0_add_provider_token_cost_columns.py
- filteredInterviewSessions
- close
- LazyAsyncPostgresSaver
- Any
- executeDirectTransition
- EmailAccountModel
- JobAssessmentResult
- StrEnum
- env.py
- BaseModel
- routers/analytics.py
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
- get_db
- BaseModel
- BaseModel
- getCurrencySymbol
- JobAssessmentResult
- enhance_role_alignment_dossier
- loadPricingRates
- Connection
- delete
- get
- fixture
- test_analytics.py
- routers/agent_chat.py
- services/llm.py
- endpoints.js
- getFitScores
- main.py
- switchTab
- 1a2b3c4d5e6f_create_role_alignment_dossiers.py
- fetchRoleAlignment
- onTrackMouseDown
- AnalyticsOverviewResponse
- Response
- FunnelMetricsResponse
- RoleAlignmentResponse

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 100 edges
2. `CompanyModel` - 79 edges
3. `useUIStore` - 40 edges
4. `ApplicationEventModel` - 39 edges
5. `PostgresTracer` - 35 edges
6. `EmailAccountModel` - 35 edges
7. `EmailPayload` - 34 edges
8. `InterviewSimulatorService` - 32 edges
9. `process_evaluation_task()` - 32 edges
10. `get_task_chat_model()` - 31 edges

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

## Communities (203 total, 75 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (84): PromptsAPI, accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri (+76 more)

### Community 1 - "PostgresTracer"
Cohesion: 0.09
Nodes (52): AsyncBaseTracer, InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions() (+44 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (52): EventsAPI, ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData (+44 more)

### Community 3 - "services/agent_tools.py"
Cohesion: 0.10
Nodes (47): ApplicationEmbeddingModel, AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, ListApplicationsInput, ManageActionItemsInput, ManageIntakeQueueInput (+39 more)

### Community 4 - "OnboardingWizardModal.vue"
Cohesion: 0.03
Nodes (51): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+43 more)

### Community 5 - "test_skill_normalizer.py"
Cohesion: 0.17
Nodes (19): extract_skills_from_text(), hybrid_extract_skills(), normalize_skill(), normalize_skills_list(), Skill Canonicalization Engine. Provides multi-stage skill normalization,…, Helper to split compound skills unless protected., Normalizes an array of skills with compound splitting, removes duplicates…, Scans raw text using pre-compiled regex patterns to deterministically detect… (+11 more)

### Community 6 - "ApplicationsView.vue"
Cohesion: 0.03
Nodes (39): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, archiveSortKey, archiveSortOrder (+31 more)

### Community 7 - "cancel_evaluation_task"
Cohesion: 0.14
Nodes (15): cancel_running_task(), Cancels an active background asyncio.Task in memory. Disconnects the active…, cancel_evaluation_task(), get_evaluation_task(), get_extension_config(), get_task_status(), list_evaluation_tasks(), get (+7 more)

### Community 8 - "parse_eml"
Cohesion: 0.14
Nodes (20): _extract_ics_summary(), normalize_resume_text(), parse_cv_document(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload. (+12 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.05
Nodes (34): activeCancelTask, activeCount, activeFixJDTask, completedCount, deleteTask(), expandedEmailDetails, failedCount, fetchTasks() (+26 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "seed_development_dataset"
Cohesion: 0.12
Nodes (26): delete_application(), delete_event(), get_staleness_stats(), AsyncSession, delete, get, post, # TODO: Trigger re-indexing of the embedding for this application based on the… (+18 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (36): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+28 more)

### Community 14 - "normalize_job_url"
Cohesion: 0.05
Nodes (64): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, TraceEventModel, clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post (+56 more)

### Community 15 - "routers/applications.py"
Cohesion: 0.05
Nodes (88): asyncio, _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, CandidateCVModel, analyze_app_job_spec() (+80 more)

### Community 16 - "routers/ai_config.py"
Cohesion: 0.06
Nodes (86): clear_embeddings_cache(), Clears cached Embeddings model instances., AIProviderModel, AITaskBindingModel, check_ai_provider_health(), create_ai_provider(), delete_ai_provider(), delete_ai_task_binding() (+78 more)

### Community 17 - "routers/candidate_profile.py"
Cohesion: 0.12
Nodes (25): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+17 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.06
Nodes (28): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkMarkAsApplied(), evaluationTasks, expandedTaskIds (+20 more)

### Community 20 - "routers/action_items.py"
Cohesion: 0.15
Nodes (27): compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks, delete (+19 more)

### Community 21 - "routers/email_accounts.py"
Cohesion: 0.11
Nodes (34): clear_account_processed_emails(), clear_all_processed_emails(), delete_account(), EmailFoldersResponse, get_account(), get_oauth_authorize_url(), get_oauth_config(), list_account_folders() (+26 more)

### Community 22 - "AnalyticsView.vue"
Cohesion: 0.05
Nodes (33): activeTab, alignmentData, alignmentSubTab, analyticsData, analyticsStore, copiedItemKey, currentAlignmentKey, currentDossier (+25 more)

### Community 23 - "CandidateProfileView.vue"
Cohesion: 0.05
Nodes (27): CandidateProfileAPI, currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling (+19 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.07
Nodes (30): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+22 more)

### Community 25 - "test_candidate_profile.py"
Cohesion: 0.14
Nodes (19): DomainExperienceItem, LanguageMatchResult, SpokenLanguageRequirement, calibrate_assessment_score_and_recommendation(), Applies mathematical bounding and recommendation synchronization to eliminate…, compute_programmatic_skill_match(), _is_skill_matched(), _normalize_token() (+11 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (25): EmailAccountsAPI, accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm (+17 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (27): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+19 more)

### Community 28 - "get_task_chat_model"
Cohesion: 0.20
Nodes (19): generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, _clean_base_url(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model() (+11 more)

### Community 29 - "routers/intake.py"
Cohesion: 0.08
Nodes (46): AssessJobRequest, assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), clear_completed_evaluations(), confirm_job_assessment(), delete_evaluation_task(), enqueue_job_assessment() (+38 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "ProcessedEmailModel"
Cohesion: 0.18
Nodes (21): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, BaseModel, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, TaskResponse, enable_email_intake_mock() (+13 more)

### Community 32 - "EmailPayload"
Cohesion: 0.19
Nodes (17): EmailPayload, process_email_batch_sequential(), process_single_email_graph(), AsyncSession, Executes the LangGraph StateGraph pipeline for a single email payload., Sequentially routes emails through the compiled LangGraph pipeline., enable_email_intake_mock(), asyncio (+9 more)

### Community 33 - "ActionItemsView.vue"
Cohesion: 0.08
Nodes (23): actionItems, activeUrgencyDropdown, applicationsList, currentEditId, deleteTask(), displayedTasks, fetchActionItems(), filterTab (+15 more)

### Community 34 - "CoverLetterModal.vue"
Cohesion: 0.06
Nodes (36): activeCoverLetterTask, application, appStore, autoSaveStatus, charCount, close(), COVER_LETTER_LENGTHS, COVER_LETTER_TONES (+28 more)

### Community 35 - "LogActivityModal.vue"
Cohesion: 0.10
Nodes (17): ApplicationsAPI, appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction (+9 more)

### Community 36 - "dependencies"
Cohesion: 0.07
Nodes (28): axios, dompurify, dependencies, axios, dompurify, @lucide/vue, lucide-vue-next, pinia (+20 more)

### Community 37 - "process_evaluation_task"
Cohesion: 0.17
Nodes (26): Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., register_running_task(), unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification…, ExtractedJobSpec, JobAssessmentResult (+18 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.08
Nodes (19): ActionItemsAPI, StagingAPI, SystemAPI, fetchBadgeCounts(), getRouteTitle(), handleVisibilityChange(), isHealthPopoverOpen, isMobileMenuOpen (+11 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.07
Nodes (24): analysisData, application, compensationText, computedRatioText, computedScoreText, criticalRisks, emit, error (+16 more)

### Community 41 - "routers/search.py"
Cohesion: 0.33
Nodes (8): AsyncSession, get, Returns matching companies alongside total tracked application count., search_companies(), semantic_search(), CompanySearchResult, BaseModel, SemanticSearchResult

### Community 42 - "ExtractedEmailInfo"
Cohesion: 0.11
Nodes (40): StagingItemModel, JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., prune_terminal_state_node(), Any, Prunes transient multi-kilobyte string fields prior to checkpointer… (+32 more)

### Community 43 - "DiagnosticsView.vue"
Cohesion: 0.08
Nodes (21): DiagnosticsAPI, activeCategory, categories, copied, currentView, loadData(), loading, loadingDetail (+13 more)

### Community 44 - "DateTimePicker.vue"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "JobIntakeModal.vue"
Cohesion: 0.09
Nodes (23): activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls(), handleBulkPromptDecision() (+15 more)

### Community 46 - "schemas/staging.py"
Cohesion: 0.24
Nodes (9): BaseModel, model_validator, Schema for displaying an item in the staging queue., Paginated wrapper for staging list endpoint., Payload for user manual resolution/override of a staged email or job lead., StagingBulkDismissResponse, StagingItemRead, StagingItemResolve (+1 more)

### Community 47 - "IntakeQueueDrawer.vue"
Cohesion: 0.22
Nodes (5): activeCount, hasItems, queue, STAGES, uiStore

### Community 48 - "fetch_emails_from_account"
Cohesion: 0.13
Nodes (18): fetch_account_folders(), Fetches list of available mail folders / labels from IMAP, Gmail API, or…, fetch_emails_from_account(), Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, GmailOAuthAdapter, MicrosoftGraphAdapter, Any, datetime (+10 more)

### Community 50 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "AsyncSession"
Cohesion: 0.10
Nodes (27): AsyncSession, bulk_dismiss_staging_items(), clear_resolved_staging_items(), get_staging_item(), list_staging_items(), Bulk dismisses specific staging items or all pending staging items matching…, Fetches full details for a single staged item., Purges PROCESSED staging items, optionally older than a given number of days. (+19 more)

### Community 53 - "decrypt_secret"
Cohesion: 0.15
Nodes (12): _encrypt_table_secrets(), upgrade(), decrypt_secret(), encrypt_secret(), _get_fernet(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows., hybrid_property (+4 more)

### Community 54 - "test_llm_factory.py"
Cohesion: 0.22
Nodes (20): Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem, OptimizationGaps, ResumeTailoringStrategy (+12 more)

### Community 55 - "test_persist_job_assessment_unrestricted_urls"
Cohesion: 0.24
Nodes (5): Any, asyncio, Test that submitting the same job posting URL with different referral…, test_persist_job_assessment_unrestricted_urls(), field_validator

### Community 56 - "loadBindings"
Cohesion: 0.33
Nodes (7): fetchGlobalModels(), loadBindings(), onGlobalProviderChange(), saveGlobalDefault(), scheduleGlobalAutoSave(), selectGlobalSuggestedModel(), syncGlobalForm()

### Community 57 - "scrollToBottom"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 58 - "get_active_llm_config_dict"
Cohesion: 0.22
Nodes (17): get_active_llm_config_dict(), Retrieves runtime LLM configuration from the database., mask_secret(), LLMConfigModel, get_current_llm_config(), LLMConfigRead, LLMConfigUpdate, Any (+9 more)

### Community 59 - "uiStore.js"
Cohesion: 0.14
Nodes (14): AIConfigAPI, uiStore, uiStore, popoverRef, uiStore, router, uiStore, setDemoModeEnabled() (+6 more)

### Community 60 - "AsyncSession"
Cohesion: 0.11
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "routers/diagnostics.py"
Cohesion: 0.28
Nodes (12): export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces(), AsyncSession (+4 more)

### Community 62 - "ApplicationModel"
Cohesion: 0.15
Nodes (26): ApplicationEventModel, ApplicationModel, archive_stale_applications(), delete_stale_agent_chats(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or…, Background worker that runs once every interval_seconds. (+18 more)

### Community 63 - "dock.js"
Cohesion: 0.23
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "CompanyLogo.vue"
Cohesion: 0.12
Nodes (15): attemptIndex, candidateDomains, fallbackInitial, faviconUrl, hasError, isLoaded, props, formatDate() (+7 more)

### Community 65 - "conftest.py"
Cohesion: 0.12
Nodes (19): db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info(), mock_job_email_payload(), postgres_container(), AsyncSession, pytest_collection_modifyitems() (+11 more)

### Community 66 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 67 - "routers/prompts.py"
Cohesion: 0.18
Nodes (16): PromptModel, get_prompt(), list_prompts(), AsyncSession, get, patch, post, List all available system prompts. (+8 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 70 - "index.js"
Cohesion: 0.19
Nodes (13): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+5 more)

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

### Community 75 - "clearSelection"
Cohesion: 0.50
Nodes (4): bulkDeleteSelected(), bulkRetrySelected(), clearSelection(), toggleSelectAll()

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
Cohesion: 0.19
Nodes (6): get_running_task_ids(), PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Returns list of currently active running task IDs., Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 83 - "handleOAuthSuccess"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "selectItem"
Cohesion: 0.24
Nodes (11): filteredAndSortedItems, formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType(), getItemCompany(), getItemPosition(), handleKeyDown(), selectItem() (+3 more)

### Community 85 - "jt"
Cohesion: 0.60
Nodes (5): jt script, check_docker(), ensure_env(), open_browser(), show_help()

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

### Community 92 - "fuzzyMatch.js"
Cohesion: 0.48
Nodes (6): fuzzyFilterApplications(), fuzzyScore(), levenshteinDistance(), scoreApplicationMatch(), stringSimilarity(), filteredExistingApps

### Community 94 - "scheduleStudioAutoSave"
Cohesion: 0.15
Nodes (16): applyProbeRecommendations(), deleteProvider(), fetchStudioModels(), loadPrompts(), loadProviders(), onStudioProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt() (+8 more)

### Community 95 - "fetchStagingItems"
Cohesion: 0.22
Nodes (9): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), handleReopenStagingItem(), handleVisibilityChange(), quickDismissItem() (+1 more)

### Community 97 - "BaseModel"
Cohesion: 0.15
Nodes (31): AnalyticsOverviewResponse, BulletReframeItem, BulletRewriteItem, ExecutiveTrackFit, FunnelChartStage, FunnelCohortPeriod, FunnelKpiCard, FunnelMetricsResponse (+23 more)

### Community 102 - "a1b2c3d4e5f6_add_cover_letter_fields.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 103 - "b2c3d4e5f6a7_update_email_accounts_and_onboarding_settings.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 104 - "c1d2e3f4a5b6_add_is_fallback_to_ai_providers.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 105 - "c2d3e4f5a6b7_add_interview_sessions_question_mode.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 106 - "cleanCVText"
Cohesion: 0.67
Nodes (3): cleanCVText(), handleFileUpload(), handleFormatCleanClick()

### Community 107 - "pollTaskUntilComplete"
Cohesion: 0.67
Nodes (3): loadProfile(), pollTaskUntilComplete(), processCV()

### Community 108 - "openAddEmailAccountModal"
Cohesion: 0.67
Nodes (3): loadOAuthConfig(), openAddEmailAccountModal(), toggleEmailIntake()

### Community 110 - "Any"
Cohesion: 0.05
Nodes (82): Any, get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not… (+74 more)

### Community 136 - "d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 137 - "CompanyModel"
Cohesion: 0.26
Nodes (14): CompanyModel, asyncio, test_action_items_crud_and_filtering(), async_client(), AsyncClient, asyncio, AsyncSession, fixture (+6 more)

### Community 144 - "Base"
Cohesion: 0.13
Nodes (13): ActionItemModel, ApplicationEmbeddingModel, Base, JobPostingModel, OtherEventModel, Accepts user fixes, applies them to DB records, and marks the staged item…, resolve_staging_item(), test_domain_entity_models() (+5 more)

### Community 146 - "test_new_features.py"
Cohesion: 0.13
Nodes (18): clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., prune_and_sanitize_tool_output(), Any, Sanitizes and prunes tool execution output payloads: - Parses string payloads…, Splits text semantically using RecursiveCharacterTextSplitter on sentence and…, Cleans raw text (normalizes whitespace, strips noise) and semantically…, split_text_semantically() (+10 more)

### Community 147 - "e4f5a6b7c8d9_drop_candidate_cv_is_active.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 148 - "f5a6b7c8d9e0_add_provider_token_cost_columns.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 151 - "LazyAsyncPostgresSaver"
Cohesion: 0.21
Nodes (3): AsyncPostgresSaver, LazyAsyncPostgresSaver, setter

### Community 154 - "EmailAccountModel"
Cohesion: 0.20
Nodes (13): EmailAccountModel, _clean_header(), _fetch_imap_emails_sync(), datetime, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using…, asyncio, test_fetch_emails_from_account_imap_threaded() (+5 more)

### Community 157 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 159 - "routers/analytics.py"
Cohesion: 0.24
Nodes (12): enhance_role_alignment_endpoint(), get_funnel_metrics(), get_overview(), get_role_alignment_dossier_endpoint(), get_role_alignment_endpoint(), AsyncSession, get, Enqueues an asynchronous AI Strategic Dossier synthesis task through the shared… (+4 more)

### Community 167 - "anonymize_and_parse_cv"
Cohesion: 0.28
Nodes (7): anonymize_and_parse_cv(), De-identifies candidate resume: - Runs local programmatic regex pre-scrubber on…, programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty(), CVAnonymizationResult

### Community 178 - "get_db"
Cohesion: 0.39
Nodes (7): get_db(), AsyncSession, asyncio, AsyncSession, test_extension_clip_job_direct(), test_extension_clip_url_pipeline(), test_extension_intake_url_and_jd_routes()

### Community 182 - "getCurrencySymbol"
Cohesion: 0.50
Nodes (4): formatJobSpecCompensation(), getCurrencySymbol(), formatSalary(), getSalaryTooltip()

### Community 184 - "enhance_role_alignment_dossier"
Cohesion: 0.35
Nodes (10): RoleAlignmentDossierModel, RoleAlignmentDossierPayload, RoleAlignmentDossierResponse, enhance_role_alignment_dossier(), _extract_json_block(), get_role_alignment_dossier(), AsyncSession, Retrieves the existing AI Strategic Dossier from PostgreSQL if generated, or… (+2 more)

### Community 190 - "test_analytics.py"
Cohesion: 0.23
Nodes (14): clear_analytics_cache(), Clears in-memory caches for analytics computations. If domain is provided…, override_db(), asyncio, AsyncSession, fixture, test_auto_recalculate_when_db_has_more_data(), test_get_analytics_overview() (+6 more)

### Community 191 - "routers/agent_chat.py"
Cohesion: 0.17
Nodes (19): get_prompt_template(), Retrieves prompt template from DB with in-memory caching, falling back to…, AgentChatModel, AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage (+11 more)

### Community 192 - "services/llm.py"
Cohesion: 0.14
Nodes (13): ApplicationSummaryResult, Strips <think>...</think> reasoning tags from LLM output text., strip_reasoning_tags(), extract_email_info(), extract_job_spec(), get_active_llm_config(), Extracts structured job application metadata from email body using LangChain…, Synthesizes a narrative status snapshot from timeline events using LangChain… (+5 more)

### Community 194 - "endpoints.js"
Cohesion: 0.23
Nodes (11): AgentAPI, AnalyticsAPI, IntakeAPI, SystemSettingsAPI, DEFAULT_ALIGNMENT, DEFAULT_FUNNEL, DEFAULT_OVERVIEW, loadCachedData() (+3 more)

### Community 199 - "getFitScores"
Cohesion: 0.25
Nodes (7): scores, getFitScores(), getAppFitScores(), sortedArchivedApplications, averageFitScore, filteredPassedEvaluations, filteredReadyEvaluations

### Community 200 - "main.py"
Cohesion: 0.10
Nodes (19): check_db_connection(), ensure_db_schema(), Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, health_check(), lifespan(), get, Health check endpoint for application and database connectivity. Returns 200 OK… (+11 more)

### Community 204 - "switchTab"
Cohesion: 0.40
Nodes (5): fetchAnalytics(), fetchFunnelMetrics(), handlePeriodChange(), switchTab(), toggleWorkModel()

### Community 205 - "1a2b3c4d5e6f_create_role_alignment_dossiers.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_exists(), upgrade()

### Community 207 - "fetchRoleAlignment"
Cohesion: 0.50
Nodes (4): fetchRoleAlignment(), handleSearchInput(), onTrackPillClick(), selectTrack()

### Community 208 - "onTrackMouseDown"
Cohesion: 1.00
Nodes (3): onTrackMouseDown(), onTrackMouseMove(), onTrackMouseUp()

## Knowledge Gaps
- **723 isolated node(s):** `DEFAULT_OVERVIEW`, `DEFAULT_FUNNEL`, `DEFAULT_ALIGNMENT`, `uiStore`, `analyticsStore` (+718 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **75 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `uiStore.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `AssessmentsView.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `LogActivityModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `IntakeQueueDrawer.vue`, `endpoints.js`, `InterviewReaderModal.vue`, `index.js`, `SearchView.vue`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `EmailPayload`, `PostgresTracer`, `BaseModel`, `services/agent_tools.py`, `process_evaluation_task`, `routers/search.py`, `CompanyModel`, `ExtractedEmailInfo`, `seed_development_dataset`, `normalize_job_url`, `Any`, `Base`, `routers/applications.py`, `get_db`, `routers/action_items.py`, `routers/intake.py`, `test_analytics.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `CompanyModel` connect `CompanyModel` to `EmailPayload`, `BaseModel`, `PostgresTracer`, `services/agent_tools.py`, `process_evaluation_task`, `routers/search.py`, `ExtractedEmailInfo`, `seed_development_dataset`, `normalize_job_url`, `routers/applications.py`, `Base`, `Any`, `get_db`, `ApplicationModel`, `routers/intake.py`, `test_analytics.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Are the 63 inferred relationships involving `CompanyModel` (e.g. with `update_application()` and `clip_job_pre_extracted()`) actually correct?**
  _`CompanyModel` has 63 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 22 INFERRED edges - model-reasoned connections that need verification._
- **What connects `DEFAULT_OVERVIEW`, `DEFAULT_FUNNEL`, `DEFAULT_ALIGNMENT` to the rest of the system?**
  _723 weakly-connected nodes found - possible documentation gaps or missing edges._