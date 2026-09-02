# Graph Report - job-tracker  (2026-09-02)

## Corpus Check
- 235 files · ~292,225 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3104 nodes · 6200 edges · 203 communities (126 shown, 77 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 686 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2063ecce`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- InterviewSimulatorService
- ApplicationDetailDrawer.vue
- test_agent_tools_unit_handlers
- OnboardingWizardModal.vue
- ApplicationQuestionModal.vue
- ApplicationsView.vue
- PostgresTracer
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
- ActionItemModel
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
- StagingItemModel
- ActionItemsView.vue
- CoverLetterModal.vue
- endpoints.js
- dependencies
- process_evaluation_task
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- services/agent_tools.py
- ExtractedEmailInfo
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- test_schemas.py
- trace_operation
- EmailPayload
- datetime
- clean_html_text
- test_email_accounts.py
- bulk_dismiss_staging_items
- EmailAccountModel
- test_llm_factory.py
- test_persist_job_assessment_unrestricted_urls
- patch
- LogActivityModal.vue
- routers/llm.py
- uiStore.js
- AsyncSession
- syncStudioForm
- ApplicationModel
- dock.js
- CompanyLogo.vue
- test_analytics.py
- 2b3c4d5e6f7a_rename_poc_email_tables.py
- Base
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
- _encrypt_table_secrets
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
- 0a1b2c3d4e5f_add_application_questions.py
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
- prune_terminal_state_node
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
- test_bulk_transition.py
- .exchange_code_for_tokens
- patch
- Request
- patch
- handleAnalyzeSpec
- field_validator
- CompanyModel
- asyncio
- test_intake_paste_endpoint
- e4f5a6b7c8d9_drop_candidate_cv_is_active.py
- f5a6b7c8d9e0_add_provider_token_cost_columns.py
- .normalize_work_model
- close
- load_settings
- Any
- executeDirectTransition
- test_system_settings.py
- JobAssessmentResult
- StrEnum
- ApplicationEmbeddingModel
- BaseModel
- routers/analytics.py
- Any
- Any
- hybrid_property
- patch
- asyncio
- datetime
- RunnableConfig
- programmatic_scrub_cv
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
- setter
- BaseModel
- BackgroundTasks
- BaseModel
- getCurrencySymbol
- JobAssessmentResult
- enhance_role_alignment_dossier
- loadPricingRates
- Connection
- delete
- get
- fixture
- BaseModel
- get_prompt_template
- _execute_evaluation_steps
- useQueueStore
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
1. `ApplicationModel` - 127 edges
2. `CompanyModel` - 87 edges
3. `ApplicationEventModel` - 43 edges
4. `useUIStore` - 41 edges
5. `PostgresTracer` - 36 edges
6. `EmailAccountModel` - 35 edges
7. `EmailPayload` - 34 edges
8. `process_evaluation_task()` - 33 edges
9. `InterviewSimulatorService` - 32 edges
10. `get_task_chat_model()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Root Pre-Commit Configuration` --semantically_similar_to--> `Backend Pre-Commit Configuration`  [INFERRED] [semantically similar]
  .pre-commit-config.yaml → backend/.pre-commit-config.yaml
- `seed()` --uses--> `CompanyModel`  [INFERRED]
  seed_db.py → backend/app/models/applications.py
- `seed()` --uses--> `IntakeEvaluationTaskModel`  [INFERRED]
  seed_db.py → backend/app/models/intake_tasks.py
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

## Communities (203 total, 77 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (83): accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri, coverLetterLength (+75 more)

### Community 1 - "InterviewSimulatorService"
Cohesion: 0.11
Nodes (46): InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions(), next_question() (+38 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (51): ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData, headerEditForm (+43 more)

### Community 3 - "test_agent_tools_unit_handlers"
Cohesion: 0.14
Nodes (27): execute_analyze_pipeline_metrics(), execute_detect_stalled_applications(), execute_evaluate_ai_fit_score(), execute_get_application_details(), execute_list_applications(), execute_manage_action_items(), execute_manage_intake_queue(), execute_query_market_benchmarks() (+19 more)

### Community 4 - "OnboardingWizardModal.vue"
Cohesion: 0.03
Nodes (51): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+43 more)

### Community 5 - "ApplicationQuestionModal.vue"
Cohesion: 0.07
Nodes (32): activeQATask, addQuestion(), application, appStore, autoSaveStatus, bulkPasteText, copySuccessMap, customInstructions (+24 more)

### Community 6 - "ApplicationsView.vue"
Cohesion: 0.03
Nodes (41): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, archiveSortKey, archiveSortOrder (+33 more)

### Community 7 - "PostgresTracer"
Cohesion: 0.12
Nodes (19): AsyncBaseTracer, Strips <think>...</think> reasoning tags from LLM output text., strip_reasoning_tags(), CandidateCVModel, clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream(), AsyncSession (+11 more)

### Community 8 - "parse_eml"
Cohesion: 0.23
Nodes (12): _extract_ics_summary(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload., Parses plaintext / raw thread text into EmailPayload., Extracts summary and date info from raw .ics calendar payload. (+4 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (47): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, closeSidebarOnMobile(), eligibleApplications (+39 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.04
Nodes (35): activeCancelTask, activeCount, activeFixJDTask, completedCount, deleteTask(), expandedDossierDetails, expandedEmailDetails, expandedQADetails (+27 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "seed_development_dataset"
Cohesion: 0.23
Nodes (13): build_dossier(), build_structured_spec(), is_database_empty(), maybe_seed_dev_data(), AsyncSession, Checks if development seeding is enabled and database is empty. If both…, Checks if the database has zero applications and companies., Populates a rich, 90-day rolling development test dataset following `guide.md`… (+5 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (36): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+28 more)

### Community 14 - "normalize_job_url"
Cohesion: 0.07
Nodes (51): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)… (+43 more)

### Community 15 - "routers/applications.py"
Cohesion: 0.11
Nodes (48): analyze_app_job_spec(), clear_app_interview_guide(), delete_application(), generate_app_cover_letter(), generate_app_interview_guide(), generate_app_interview_guide_stream(), generate_application_form_answers(), get_application() (+40 more)

### Community 16 - "routers/ai_config.py"
Cohesion: 0.05
Nodes (91): get_db(), AsyncSession, clear_embeddings_cache(), Clears cached Embeddings model instances., AIProviderModel, AITaskBindingModel, check_ai_provider_health(), create_ai_provider() (+83 more)

### Community 17 - "routers/candidate_profile.py"
Cohesion: 0.06
Nodes (48): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+40 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.06
Nodes (28): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkMarkAsApplied(), evaluationTasks, expandedTaskIds (+20 more)

### Community 20 - "ActionItemModel"
Cohesion: 0.15
Nodes (28): ActionItemModel, compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks (+20 more)

### Community 21 - "routers/email_accounts.py"
Cohesion: 0.11
Nodes (36): clear_account_processed_emails(), clear_all_processed_emails(), delete_account(), EmailFoldersResponse, fetch_account_folders(), get_account(), get_oauth_authorize_url(), get_oauth_config() (+28 more)

### Community 22 - "AnalyticsView.vue"
Cohesion: 0.05
Nodes (33): activeTab, alignmentData, alignmentSubTab, analyticsData, analyticsStore, copiedItemKey, currentAlignmentKey, currentDossier (+25 more)

### Community 23 - "CandidateProfileView.vue"
Cohesion: 0.06
Nodes (26): currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling, isDeleting (+18 more)

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
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "get_task_chat_model"
Cohesion: 0.23
Nodes (18): _clean_base_url(), get_active_llm_config_dict(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model(), AsyncSession (+10 more)

### Community 29 - "routers/intake.py"
Cohesion: 0.07
Nodes (56): AssessJobRequest, assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations(), delete_evaluation_task(), enqueue_job_assessment() (+48 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "ProcessedEmailModel"
Cohesion: 0.18
Nodes (21): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, BaseModel, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, TaskResponse, enable_email_intake_mock() (+13 more)

### Community 32 - "StagingItemModel"
Cohesion: 0.15
Nodes (20): StagingItemModel, model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve, process_email_batch_sequential(), process_single_email_graph(), AsyncSession, Executes the LangGraph StateGraph pipeline for a single email payload. (+12 more)

### Community 33 - "ActionItemsView.vue"
Cohesion: 0.08
Nodes (23): actionItems, activeUrgencyDropdown, applicationsList, currentEditId, deleteTask(), displayedTasks, fetchActionItems(), filterTab (+15 more)

### Community 34 - "CoverLetterModal.vue"
Cohesion: 0.06
Nodes (36): activeCoverLetterTask, application, appStore, autoSaveStatus, charCount, close(), COVER_LETTER_LENGTHS, COVER_LETTER_TONES (+28 more)

### Community 35 - "endpoints.js"
Cohesion: 0.07
Nodes (25): ActionItemsAPI, AgentAPI, ApplicationsAPI, CandidateProfileAPI, EventsAPI, InterviewSimulatorAPI, PromptsAPI, SearchAPI (+17 more)

### Community 36 - "dependencies"
Cohesion: 0.07
Nodes (28): axios, dompurify, dependencies, axios, dompurify, @lucide/vue, lucide-vue-next, pinia (+20 more)

### Community 37 - "process_evaluation_task"
Cohesion: 0.17
Nodes (26): Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., register_running_task(), unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification…, ExtractedJobSpec, JobAssessmentResult (+18 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.08
Nodes (18): fetchBadgeCounts(), getRouteTitle(), handleVisibilityChange(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount, pendingTasksCount, pillLabel (+10 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.06
Nodes (29): analysisData, application, compensationText, computedRatioText, computedScoreText, criticalRisks, emit, error (+21 more)

### Community 41 - "services/agent_tools.py"
Cohesion: 0.27
Nodes (18): ApplicationEmbeddingModel, AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, ListApplicationsInput, ManageActionItemsInput, ManageIntakeQueueInput (+10 more)

### Community 42 - "ExtractedEmailInfo"
Cohesion: 0.20
Nodes (24): JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., asyncio, AsyncSession, When exactly 1 application exists for a matched company, auto-link to it even…, When multiple applications exist for a company, disambiguate by position or… (+16 more)

### Community 43 - "DiagnosticsView.vue"
Cohesion: 0.08
Nodes (21): DiagnosticsAPI, activeCategory, categories, copied, currentView, loadData(), loading, loadingDetail (+13 more)

### Community 44 - "DateTimePicker.vue"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "JobIntakeModal.vue"
Cohesion: 0.09
Nodes (23): activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls(), handleBulkPromptDecision() (+15 more)

### Community 46 - "test_schemas.py"
Cohesion: 0.18
Nodes (15): bulk_transition_applications(), Transitions all applications whose status is in payload.from_statuses to…, AllowedApplicationStatus, ApplicationTransitionRequest, ApplicationUpdate, BulkTransitionRequest, BulkTransitionResult, Any (+7 more)

### Community 47 - "trace_operation"
Cohesion: 0.24
Nodes (13): TraceEventModel, Any, AsyncSession, datetime, Persists a programmatic execution trace event into the trace_events table., Async context manager that measures execution time and records diagnostic…, record_diagnostic_event(), trace_operation() (+5 more)

### Community 48 - "EmailPayload"
Cohesion: 0.10
Nodes (29): EmailPayload, _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using… (+21 more)

### Community 50 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "bulk_dismiss_staging_items"
Cohesion: 0.13
Nodes (22): bulk_dismiss_staging_items(), clear_resolved_staging_items(), list_staging_items(), Bulk dismisses specific staging items or all pending staging items matching…, Purges PROCESSED staging items, optionally older than a given number of days., BaseModel, Schema for displaying an item in the staging queue., Paginated wrapper for staging list endpoint. (+14 more)

### Community 53 - "EmailAccountModel"
Cohesion: 0.19
Nodes (12): decrypt_secret(), encrypt_secret(), _get_fernet(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows., EmailAccountModel, hybrid_property, setter (+4 more)

### Community 54 - "test_llm_factory.py"
Cohesion: 0.23
Nodes (19): Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem, OptimizationGaps, ResumeTailoringStrategy (+11 more)

### Community 55 - "test_persist_job_assessment_unrestricted_urls"
Cohesion: 0.50
Nodes (3): asyncio, Test that submitting the same job posting URL with different referral…, test_persist_job_assessment_unrestricted_urls()

### Community 56 - "patch"
Cohesion: 0.18
Nodes (10): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, test_secret_key_auto_generation_and_persistence(), test_secret_key_validation_in_non_dev_environments(), test_security_fernet_secret_key_validation() (+2 more)

### Community 57 - "LogActivityModal.vue"
Cohesion: 0.20
Nodes (10): appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction, submitLog() (+2 more)

### Community 58 - "routers/llm.py"
Cohesion: 0.24
Nodes (15): mask_secret(), LLMConfigModel, get_current_llm_config(), LLMConfigRead, LLMConfigUpdate, Any, AsyncSession, BaseModel (+7 more)

### Community 59 - "uiStore.js"
Cohesion: 0.12
Nodes (17): AIConfigAPI, uiStore, uiStore, activeCount, hasItems, queue, STAGES, uiStore (+9 more)

### Community 60 - "AsyncSession"
Cohesion: 0.11
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "syncStudioForm"
Cohesion: 0.33
Nodes (7): deleteProvider(), fetchStudioModels(), loadProviders(), onStudioProviderChange(), saveProvider(), selectStudioTask(), syncStudioForm()

### Community 62 - "ApplicationModel"
Cohesion: 0.16
Nodes (21): ApplicationModel, archive_stale_applications(), delete_stale_agent_chats(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or…, Background worker that runs once every interval_seconds., staleness_archiver_worker() (+13 more)

### Community 63 - "dock.js"
Cohesion: 0.23
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "CompanyLogo.vue"
Cohesion: 0.12
Nodes (15): attemptIndex, candidateDomains, fallbackInitial, faviconUrl, hasError, isLoaded, props, formatDate() (+7 more)

### Community 65 - "test_analytics.py"
Cohesion: 0.07
Nodes (35): Clears all server-side analytics caches across Overview, Funnel, and Role…, recalculate_analytics(), clear_analytics_cache(), Clears in-memory caches for analytics computations. If domain is provided…, db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info() (+27 more)

### Community 66 - "2b3c4d5e6f7a_rename_poc_email_tables.py"
Cohesion: 0.60
Nodes (5): downgrade(), _index_exists(), rename poc email tables and indexes Revision ID: 2b3c4d5e6f7a Revises:…, _table_exists(), upgrade()

### Community 67 - "Base"
Cohesion: 0.06
Nodes (39): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online(), clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., verify_admin_access(), AgentChatModel (+31 more)

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
Cohesion: 0.16
Nodes (8): cancel_running_task(), get_running_task_ids(), PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs., Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 83 - "handleOAuthSuccess"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "selectItem"
Cohesion: 0.24
Nodes (11): filteredAndSortedItems, formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType(), getItemCompany(), getItemPosition(), handleKeyDown(), selectItem() (+3 more)

### Community 85 - "jt"
Cohesion: 0.60
Nodes (5): jt script, check_docker(), ensure_env(), open_browser(), show_help()

### Community 86 - "_encrypt_table_secrets"
Cohesion: 0.50
Nodes (3): _encrypt_table_secrets(), upgrade(), Connection

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
Nodes (16): applyProbeRecommendations(), fetchGlobalModels(), loadBindings(), loadPrompts(), onGlobalProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt(), resetStudioTaskToDefaults() (+8 more)

### Community 95 - "fetchStagingItems"
Cohesion: 0.22
Nodes (9): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), handleReopenStagingItem(), handleVisibilityChange(), quickDismissItem() (+1 more)

### Community 97 - "BaseModel"
Cohesion: 0.12
Nodes (37): AsyncSession, get_funnel_metrics(), AsyncSession, get, AnalyticsOverviewResponse, BulletReframeItem, BulletRewriteItem, ExecutiveTrackFit (+29 more)

### Community 100 - "0a1b2c3d4e5f_add_application_questions.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

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
Cohesion: 0.12
Nodes (41): Any, cover_letter_node(), db_commit_node(), extraction_node(), fuzzy_match_node(), _get_db(), is_email_already_processed(), normalize_and_dedupe_node() (+33 more)

### Community 116 - "prune_terminal_state_node"
Cohesion: 0.50
Nodes (4): prune_terminal_state_node(), Any, Prunes transient multi-kilobyte string fields prior to checkpointer…, test_prune_terminal_state_node()

### Community 136 - "d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 137 - "test_bulk_transition.py"
Cohesion: 0.42
Nodes (10): async_client(), AsyncClient, asyncio, AsyncSession, fixture, test_bulk_transition_archives_open_applications(), test_bulk_transition_creates_timeline_events(), test_bulk_transition_dismisses_pending_action_items_on_terminal() (+2 more)

### Community 144 - "CompanyModel"
Cohesion: 0.10
Nodes (35): asyncio, ApplicationEventModel, CompanyModel, JobPostingModel, OtherEventModel, confirm_job_assessment(), Commits an assessed job lead to the application pipeline in ASSESSMENT or…, Accepts user fixes, applies them to DB records, and marks the staged item… (+27 more)

### Community 146 - "test_intake_paste_endpoint"
Cohesion: 0.67
Nodes (4): asyncio, AsyncSession, test_intake_paste_endpoint(), test_intake_upload_endpoint()

### Community 147 - "e4f5a6b7c8d9_drop_candidate_cv_is_active.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 148 - "f5a6b7c8d9e0_add_provider_token_cost_columns.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 151 - "load_settings"
Cohesion: 0.05
Nodes (52): AsyncPostgresSaver, get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not… (+44 more)

### Community 154 - "test_system_settings.py"
Cohesion: 0.60
Nodes (4): asyncio, test_email_intake_disabled_guard(), test_global_settings_backward_compatibility(), test_system_settings_get_and_patch()

### Community 159 - "routers/analytics.py"
Cohesion: 0.33
Nodes (10): enhance_role_alignment_endpoint(), get_funnel_metrics(), get_overview(), get_role_alignment_dossier_endpoint(), get_role_alignment_endpoint(), AsyncSession, get, Enqueues an asynchronous AI Strategic Dossier synthesis task through the shared… (+2 more)

### Community 167 - "programmatic_scrub_cv"
Cohesion: 0.47
Nodes (4): programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty()

### Community 182 - "getCurrencySymbol"
Cohesion: 0.50
Nodes (4): formatJobSpecCompensation(), getCurrencySymbol(), formatSalary(), getSalaryTooltip()

### Community 184 - "enhance_role_alignment_dossier"
Cohesion: 0.35
Nodes (10): RoleAlignmentDossierModel, RoleAlignmentDossierPayload, RoleAlignmentDossierResponse, enhance_role_alignment_dossier(), _extract_json_block(), get_role_alignment_dossier(), AsyncSession, Retrieves the existing AI Strategic Dossier from PostgreSQL if generated, or… (+2 more)

### Community 191 - "get_prompt_template"
Cohesion: 0.10
Nodes (29): get_prompt_template(), AsyncSession, Retrieves prompt template from DB with in-memory caching, falling back to…, AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage (+21 more)

### Community 192 - "_execute_evaluation_steps"
Cohesion: 0.11
Nodes (35): ApplicationSummaryResult, _execute_application_qa_steps(), _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), _execute_role_alignment_dossier_steps(), AsyncSession (+27 more)

### Community 194 - "useQueueStore"
Cohesion: 0.22
Nodes (11): AnalyticsAPI, IntakeAPI, retryTask(), DEFAULT_ALIGNMENT, DEFAULT_FUNNEL, DEFAULT_OVERVIEW, loadCachedData(), saveCachedData() (+3 more)

### Community 200 - "main.py"
Cohesion: 0.07
Nodes (33): generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, lifespan(), delete_application(), delete_event(), get_staleness_stats(), AsyncSession, delete (+25 more)

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
- **747 isolated node(s):** `uiStore`, `uiStore`, `router`, `appStore`, `{ detailActiveTab: activeTab }` (+742 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **77 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `uiStore.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationQuestionModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `AssessmentsView.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `endpoints.js`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `LogActivityModal.vue`, `useQueueStore`, `InterviewReaderModal.vue`, `index.js`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `InterviewSimulatorService`, `test_agent_tools_unit_handlers`, `PostgresTracer`, `test_bulk_transition.py`, `seed_development_dataset`, `normalize_job_url`, `routers/applications.py`, `CompanyModel`, `ActionItemModel`, `load_settings`, `StagingItemModel`, `process_evaluation_task`, `services/agent_tools.py`, `ExtractedEmailInfo`, `test_schemas.py`, `EmailPayload`, `_execute_evaluation_steps`, `test_analytics.py`, `Base`, `main.py`, `BaseModel`, `Any`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `CompanyModel` connect `CompanyModel` to `StagingItemModel`, `test_analytics.py`, `InterviewSimulatorService`, `Base`, `test_agent_tools_unit_handlers`, `process_evaluation_task`, `main.py`, `services/agent_tools.py`, `test_bulk_transition.py`, `ExtractedEmailInfo`, `seed_development_dataset`, `normalize_job_url`, `routers/applications.py`, `Any`, `EmailPayload`, `load_settings`, `ApplicationModel`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 98 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `CompanyModel` (e.g. with `get_applications_by_status()` and `list_applications()`) actually correct?**
  _`CompanyModel` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `uiStore`, `uiStore`, `router` to the rest of the system?**
  _747 weakly-connected nodes found - possible documentation gaps or missing edges._