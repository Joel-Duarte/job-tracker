# Graph Report - job-tracker  (2026-09-02)

## Corpus Check
- 235 files · ~294,493 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3110 nodes · 6183 edges · 216 communities (135 shown, 81 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 691 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ea0f681d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- InterviewSimulatorService
- ApplicationDetailDrawer.vue
- ApplicationModel
- OnboardingWizardModal.vue
- ApplicationQuestionModal.vue
- ApplicationsView.vue
- PostgresTracer
- extract_usage_from_payload
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- seed_development_dataset
- StagingView.vue
- trace_operation
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
- ApplicationEventModel
- ActionItemsView.vue
- CoverLetterModal.vue
- LogActivityModal.vue
- dependencies
- process_evaluation_task
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- test_skill_normalizer.py
- ExtractedEmailInfo
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- test_schemas.py
- AsyncSession
- fetch_emails_from_account
- datetime
- clean_html_text
- test_email_accounts.py
- routers/staging.py
- routers/llm.py
- test_llm_factory.py
- datetime
- patch
- EmailAccountModel
- AIProviderModel
- endpoints.js
- AsyncSession
- scheduleStudioAutoSave
- schemas/applications.py
- dock.js
- CompanyLogo.vue
- test_analytics.py
- 2b3c4d5e6f7a_rename_poc_email_tables.py
- routers/prompts.py
- InterviewReaderModal.vue
- AIProviderModel
- index.js
- update_account
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
- routers/extension.py
- formatRelativeDate
- resolve_company_domain
- PostHireModal.vue
- advanceAppStage
- AITaskBindingModel
- fuzzyMatch.js
- AsyncSession
- loadBindings
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
- _execute_evaluation_steps
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
- routers/diagnostics.py
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
- routers/agent_chat.py
- services/llm.py
- normalize_job_url
- useQueueStore
- scrollToBottom
- SearchView.vue
- IntakeQueueDrawer.vue
- get_badge_counts
- env.py
- main.py
- closeSidebarOnMobile
- persist_or_stage_job_assessment
- get_funnel_metrics
- switchTab
- 1a2b3c4d5e6f_create_role_alignment_dossiers.py
- interviewStore.js
- fetchRoleAlignment
- onTrackMouseDown
- AnalyticsOverviewResponse
- Response
- FunnelMetricsResponse
- RoleAlignmentResponse
- cancel_running_task
- filteredInterviewSessions
- asyncio

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 121 edges
2. `CompanyModel` - 85 edges
3. `useUIStore` - 41 edges
4. `ApplicationEventModel` - 40 edges
5. `EmailAccountModel` - 35 edges
6. `EmailPayload` - 34 edges
7. `PostgresTracer` - 34 edges
8. `process_evaluation_task()` - 33 edges
9. `get_task_chat_model()` - 32 edges
10. `ActionItemModel` - 30 edges

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

## Communities (216 total, 81 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (84): accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri, coverLetterLength (+76 more)

### Community 1 - "InterviewSimulatorService"
Cohesion: 0.10
Nodes (49): ApplicationModel, InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions() (+41 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (51): ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData, headerEditForm (+43 more)

### Community 3 - "ApplicationModel"
Cohesion: 0.11
Nodes (48): ApplicationEmbeddingModel, ApplicationModel, AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, ListApplicationsInput, ManageActionItemsInput (+40 more)

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
Cohesion: 0.13
Nodes (20): AsyncBaseTracer, CandidateCVModel, GenerateInterviewGuideRequest, clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream(), AsyncSession, Async generator that executes `interview_guide_graph.astream(...)` and yields… (+12 more)

### Community 8 - "extract_usage_from_payload"
Cohesion: 0.14
Nodes (23): get_usage_overview_endpoint(), update_pricing_rates_endpoint(), calculate_comparative_provider_costs(), calculate_cost_and_savings(), extract_usage_from_payload(), get_all_pricing_rates(), _match_pricing_key(), Matches a model name string (including path / provider prefixes) to a pricing… (+15 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.04
Nodes (35): activeCancelTask, activeCount, activeFixJDTask, completedCount, deleteTask(), expandedDossierDetails, expandedEmailDetails, expandedQADetails (+27 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "seed_development_dataset"
Cohesion: 0.24
Nodes (12): build_dossier(), build_structured_spec(), is_database_empty(), maybe_seed_dev_data(), AsyncSession, Checks if development seeding is enabled and database is empty. If both…, Checks if the database has zero applications and companies., Populates a rich, 90-day rolling development test dataset following `guide.md`… (+4 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (36): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+28 more)

### Community 14 - "trace_operation"
Cohesion: 0.09
Nodes (38): TraceEventModel, clean_extracted_text(), has_job_content_keywords(), BaseModel, Validates URL protocol and private IP / loopback address validation (SSRF…, Blazing fast multi-language scraper keyword validation using Python set hash…, Backward-compatible alias for validate_job_content., Normalizes whitespace and strips javascript code blocks, jQuery artifacts, and… (+30 more)

### Community 15 - "routers/applications.py"
Cohesion: 0.14
Nodes (36): analyze_app_job_spec(), bulk_transition_applications(), clear_app_interview_guide(), delete_application(), generate_app_cover_letter(), generate_app_interview_guide(), generate_app_interview_guide_stream(), generate_application_form_answers() (+28 more)

### Community 16 - "routers/ai_config.py"
Cohesion: 0.17
Nodes (24): _fetch_models_from_endpoint(), get_pricing_rates_endpoint(), _is_embedding_model(), _is_reasoning_model(), list_provider_models(), probe_model_capabilities(), reset_pricing_rates_endpoint(), test_ai_provider() (+16 more)

### Community 17 - "routers/candidate_profile.py"
Cohesion: 0.06
Nodes (45): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+37 more)

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
Cohesion: 0.15
Nodes (24): EmailFoldersResponse, get_oauth_authorize_url(), get_oauth_config(), list_account_folders(), list_accounts(), MailFolderItem, oauth_callback(), _oauth_state_client_id() (+16 more)

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
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "get_task_chat_model"
Cohesion: 0.22
Nodes (19): _clean_base_url(), get_active_llm_config_dict(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model(), AsyncSession (+11 more)

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
Cohesion: 0.11
Nodes (32): ApplicationEventModel, EmailPayload, model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve, process_email_batch_sequential(), process_single_email_graph(), AsyncSession (+24 more)

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
Cohesion: 0.13
Nodes (31): get_running_task_ids(), Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., Returns list of currently active running task IDs., register_running_task(), unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification… (+23 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.07
Nodes (20): ActionItemsAPI, SystemAPI, fetchBadgeCounts(), getRouteTitle(), handleVisibilityChange(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount (+12 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.06
Nodes (29): analysisData, application, compensationText, computedRatioText, computedScoreText, criticalRisks, emit, error (+21 more)

### Community 41 - "test_skill_normalizer.py"
Cohesion: 0.17
Nodes (19): extract_skills_from_text(), hybrid_extract_skills(), normalize_skill(), normalize_skills_list(), Skill Canonicalization Engine. Provides multi-stage skill normalization,…, Helper to split compound skills unless protected., Normalizes an array of skills with compound splitting, removes duplicates…, Scans raw text using pre-compiled regex patterns to deterministically detect… (+11 more)

### Community 42 - "ExtractedEmailInfo"
Cohesion: 0.17
Nodes (29): StagingItemModel, JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., prune_terminal_state_node(), Any, Prunes transient multi-kilobyte string fields prior to checkpointer… (+21 more)

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
Cohesion: 0.21
Nodes (13): AllowedApplicationStatus, ApplicationTransitionRequest, ApplicationUpdate, BulkTransitionRequest, BulkTransitionResult, Any, test_application_transition_request_date_coercion(), test_application_update_job_spec_fields() (+5 more)

### Community 47 - "AsyncSession"
Cohesion: 0.18
Nodes (20): clear_embeddings_cache(), Clears cached Embeddings model instances., create_ai_provider(), delete_ai_task_binding(), get_ai_health_endpoint(), get_global_settings(), list_ai_providers(), list_ai_task_bindings() (+12 more)

### Community 48 - "fetch_emails_from_account"
Cohesion: 0.13
Nodes (21): fetch_account_folders(), Fetches list of available mail folders / labels from IMAP, Gmail API, or…, _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject). (+13 more)

### Community 50 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "routers/staging.py"
Cohesion: 0.09
Nodes (29): bulk_dismiss_staging_items(), clear_resolved_staging_items(), get_staging_item(), list_staging_items(), Bulk dismisses specific staging items or all pending staging items matching…, Fetches full details for a single staged item., Purges PROCESSED staging items, optionally older than a given number of days., Marks a staged item as REJECTED if it is a false positive or non-job email. (+21 more)

### Community 53 - "routers/llm.py"
Cohesion: 0.05
Nodes (38): AsyncPostgresSaver, _encrypt_table_secrets(), upgrade(), check_db_connection(), ensure_db_schema(), LazyAsyncPostgresSaver, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from… (+30 more)

### Community 54 - "test_llm_factory.py"
Cohesion: 0.23
Nodes (19): AsyncSession, Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem, OptimizationGaps (+11 more)

### Community 55 - "datetime"
Cohesion: 0.22
Nodes (6): AgentChatModel, Base, OtherEventModel, RoleAlignmentDossierModel, datetime, DeclarativeBase

### Community 56 - "patch"
Cohesion: 0.18
Nodes (10): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, test_secret_key_auto_generation_and_persistence(), test_secret_key_validation_in_non_dev_environments(), test_security_fernet_secret_key_validation() (+2 more)

### Community 57 - "EmailAccountModel"
Cohesion: 0.16
Nodes (17): EmailAccountModel, clear_account_processed_emails(), clear_all_processed_emails(), create_account(), delete_account(), get_account(), AsyncSession, delete (+9 more)

### Community 58 - "AIProviderModel"
Cohesion: 0.32
Nodes (16): AIProviderModel, AITaskBindingModel, check_ai_provider_health(), delete_ai_provider(), invalidate_ai_health_cache(), asyncio, AsyncSession, fixture (+8 more)

### Community 59 - "endpoints.js"
Cohesion: 0.15
Nodes (17): AgentAPI, AIConfigAPI, EventsAPI, PromptsAPI, StagingAPI, SystemSettingsAPI, uiStore, uiStore (+9 more)

### Community 60 - "AsyncSession"
Cohesion: 0.11
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "scheduleStudioAutoSave"
Cohesion: 0.20
Nodes (11): applyProbeRecommendations(), deleteProvider(), fetchStudioModels(), loadProviders(), onStudioProviderChange(), saveProvider(), scheduleStudioAutoSave(), selectStudioSuggestedModel() (+3 more)

### Community 62 - "schemas/applications.py"
Cohesion: 0.20
Nodes (13): update_application_questions(), ActionItemDetail, ApplicationAnalyzeSpecRequest, ApplicationEventDetail, ApplicationFilterParams, ApplicationQuestionItem, ApplicationQuestionsResponse, ApplicationQuestionsUpdateRequest (+5 more)

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

### Community 67 - "routers/prompts.py"
Cohesion: 0.17
Nodes (18): clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., PromptModel, get_prompt(), list_prompts(), AsyncSession, get, patch (+10 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 70 - "index.js"
Cohesion: 0.19
Nodes (13): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+5 more)

### Community 71 - "update_account"
Cohesion: 0.24
Nodes (9): patch, Update settings or credentials for an existing email account., update_account(), EmailAccountBase, EmailAccountCreate, EmailAccountResponse, EmailAccountUpdate, BaseModel (+1 more)

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
Cohesion: 0.24
Nodes (4): PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 83 - "handleOAuthSuccess"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "selectItem"
Cohesion: 0.24
Nodes (11): filteredAndSortedItems, formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType(), getItemCompany(), getItemPosition(), handleKeyDown(), selectItem() (+3 more)

### Community 85 - "jt"
Cohesion: 0.60
Nodes (5): jt script, check_docker(), ensure_env(), open_browser(), show_help()

### Community 86 - "routers/extension.py"
Cohesion: 0.26
Nodes (12): clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text…, Receives a job posting URL, scrapes page text (or uses pre-captured HTML), and… (+4 more)

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

### Community 94 - "loadBindings"
Cohesion: 0.21
Nodes (12): fetchGlobalModels(), loadBindings(), loadPrompts(), onGlobalProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt(), resetStudioTaskToDefaults(), saveGlobalDefault() (+4 more)

### Community 95 - "fetchStagingItems"
Cohesion: 0.22
Nodes (9): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), handleReopenStagingItem(), handleVisibilityChange(), quickDismissItem() (+1 more)

### Community 97 - "BaseModel"
Cohesion: 0.13
Nodes (36): AsyncSession, AITaskBindingUpdate, PricingRateUpdate, AnalyticsOverviewResponse, BulletReframeItem, BulletRewriteItem, ExecutiveTrackFit, FunnelChartStage (+28 more)

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

### Community 116 - "_execute_evaluation_steps"
Cohesion: 0.34
Nodes (13): _execute_application_qa_steps(), _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), _execute_role_alignment_dossier_steps(), AsyncSession, anonymize_and_parse_cv() (+5 more)

### Community 136 - "d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 137 - "test_bulk_transition.py"
Cohesion: 0.42
Nodes (10): async_client(), AsyncClient, asyncio, AsyncSession, fixture, test_bulk_transition_archives_open_applications(), test_bulk_transition_creates_timeline_events(), test_bulk_transition_dismisses_pending_action_items_on_terminal() (+2 more)

### Community 144 - "CompanyModel"
Cohesion: 0.08
Nodes (44): asyncio, ActionItemModel, CompanyModel, JobPostingModel, Accepts user fixes, applies them to DB records, and marks the staged item…, resolve_staging_item(), archive_stale_applications(), delete_stale_agent_chats() (+36 more)

### Community 146 - "routers/diagnostics.py"
Cohesion: 0.28
Nodes (12): export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces(), AsyncSession (+4 more)

### Community 147 - "e4f5a6b7c8d9_drop_candidate_cv_is_active.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 148 - "f5a6b7c8d9e0_add_provider_token_cost_columns.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 151 - "load_settings"
Cohesion: 0.09
Nodes (38): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously. (+30 more)

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
Cohesion: 0.29
Nodes (9): enhance_role_alignment_dossier(), _extract_json_block(), get_role_alignment_dossier(), Any, AsyncSession, Retrieves the existing AI Strategic Dossier from PostgreSQL if generated, or…, Synthesizes a fresh AI Strategic Dossier using LLM task binding and PostgreSQL…, Robustly extracts JSON object from LLM output. (+1 more)

### Community 191 - "routers/agent_chat.py"
Cohesion: 0.15
Nodes (19): AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage, delete_chat(), get_chat(), list_chats() (+11 more)

### Community 192 - "services/llm.py"
Cohesion: 0.11
Nodes (29): ApplicationSummaryResult, Strips <think>...</think> reasoning tags from LLM output text., strip_reasoning_tags(), get_prompt_template(), Retrieves prompt template from DB with in-memory caching, falling back to…, assess_job_posting(), extract_email_info(), extract_job_spec() (+21 more)

### Community 193 - "normalize_job_url"
Cohesion: 0.24
Nodes (10): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, AsyncSessionMock, asyncio, Unit test using mock AsyncSession to verify persist_or_stage_job_assessment…, test_normalize_job_url_edge_cases(), test_normalize_job_url_preserves_full_url(), test_normalize_job_url_preserves_job_identifiers() (+2 more)

### Community 194 - "useQueueStore"
Cohesion: 0.22
Nodes (11): AnalyticsAPI, IntakeAPI, retryTask(), DEFAULT_ALIGNMENT, DEFAULT_FUNNEL, DEFAULT_OVERVIEW, loadCachedData(), saveCachedData() (+3 more)

### Community 195 - "scrollToBottom"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 196 - "SearchView.vue"
Cohesion: 0.25
Nodes (8): SearchAPI, executeSearch(), handleKeyDown(), hasSearched, loading, results, searchQuery, uiStore

### Community 197 - "IntakeQueueDrawer.vue"
Cohesion: 0.22
Nodes (5): activeCount, hasItems, queue, STAGES, uiStore

### Community 198 - "get_badge_counts"
Cohesion: 0.29
Nodes (6): get_badge_counts(), AsyncSession, get, Returns aggregated counts for Navbar and drawer badges in a single optimized DB…, BadgeCountsResponse, BaseModel

### Community 199 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 200 - "main.py"
Cohesion: 0.07
Nodes (36): get_db(), AsyncSession, generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, lifespan(), delete_application(), delete_event(), get_staleness_stats() (+28 more)

### Community 201 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 202 - "persist_or_stage_job_assessment"
Cohesion: 0.50
Nodes (4): persist_or_stage_job_assessment(), AsyncSession, Persists an AI job assessment to the database. If target_application_id is…, resolve_job_currency()

### Community 203 - "get_funnel_metrics"
Cohesion: 0.67
Nodes (3): get_funnel_metrics(), AsyncSession, get

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
- **748 isolated node(s):** `route`, `uiStore`, `activeTab`, `providers`, `loadingProviders` (+743 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **81 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `endpoints.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationQuestionModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `AssessmentsView.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `LogActivityModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `useQueueStore`, `InterviewReaderModal.vue`, `IntakeQueueDrawer.vue`, `index.js`, `SearchView.vue`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `InterviewSimulatorService`, `PostgresTracer`, `test_bulk_transition.py`, `routers/applications.py`, `CompanyModel`, `routers/action_items.py`, `load_settings`, `routers/intake.py`, `ApplicationEventModel`, `process_evaluation_task`, `ExtractedEmailInfo`, `datetime`, `schemas/applications.py`, `services/llm.py`, `test_analytics.py`, `main.py`, `persist_or_stage_job_assessment`, `routers/extension.py`, `Any`, `_execute_evaluation_steps`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `Base` connect `datetime` to `ApplicationEventModel`, `InterviewSimulatorService`, `ApplicationModel`, `routers/prompts.py`, `process_evaluation_task`, `env.py`, `ExtractedEmailInfo`, `trace_operation`, `CompanyModel`, `routers/llm.py`, `load_settings`, `EmailAccountModel`, `ProcessedEmailModel`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 96 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 96 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `CompanyModel` (e.g. with `get_applications_by_status()` and `list_applications()`) actually correct?**
  _`CompanyModel` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 24 INFERRED edges - model-reasoned connections that need verification._
- **What connects `route`, `uiStore`, `activeTab` to the rest of the system?**
  _748 weakly-connected nodes found - possible documentation gaps or missing edges._