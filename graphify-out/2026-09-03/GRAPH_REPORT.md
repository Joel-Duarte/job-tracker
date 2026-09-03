# Graph Report - job-tracker  (2026-09-03)

## Corpus Check
- 256 files · ~320,446 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3472 nodes · 6702 edges · 227 communities (152 shown, 75 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 730 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `033e9357`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- get_task_chat_model
- ApplicationDetailDrawer.vue
- services/agent_tools.py
- OnboardingWizardModal.vue
- ApplicationQuestionModal.vue
- ApplicationsView.vue
- test_pricing_service.py
- ExtractedEmailInfo
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- resolve_company_domain
- StagingView.vue
- normalize_job_url
- save_settings
- CompanyDetailDrawer.vue
- test_candidate_profile.py
- popup.js
- AssessmentsView.vue
- ActionItemModel
- routers/email_accounts.py
- AnalyticsView.vue
- CandidateProfileView.vue
- JobIntakeView.vue
- load_settings
- EmailAccountsSettings.vue
- FloatingQueueWidget.vue
- CompanyModel
- routers/intake.py
- manifest.json
- sync_email_account
- test_new_features.py
- ActionItemsView.vue
- CoverLetterModal.vue
- index.js
- dependencies
- process_evaluation_task
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- test_skill_normalizer.py
- EmailPayload
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- test_application_questions.py
- routers/system_settings.py
- fetch_emails_from_account
- datetime
- clean_html_text
- test_email_accounts.py
- bulk_dismiss_staging_items
- LazyAsyncPostgresSaver
- test_llm_factory.py
- research_company_context
- get_embeddings_model
- test_system_settings.py
- trace_operation
- endpoints.js
- AsyncSession
- scheduleStudioAutoSave
- CompaniesView.vue
- dock.js
- CompanyLogo.vue
- test_analytics.py
- 2b3c4d5e6f7a_rename_poc_email_tables.py
- get_db
- InterviewReaderModal.vue
- routers/ai_config.py
- _execute_evaluation_steps
- create_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- clearSelection
- extractJobData
- demoStorage.js
- TaskTracker
- saveProfileField
- schemas/intake.py
- parse_eml
- BaseModel
- handleOAuthSuccess
- WebOperationLimiter
- jt
- asyncio
- formatRelativeDate
- patch
- PostHireModal.vue
- advanceAppStage
- SearchView.vue
- fuzzyMatch.js
- AsyncSession
- loadBindings
- selectItem
- routers/llm.py
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
- seed_development_dataset
- Email Synchronization Engine
- Frontend SPA Entry HTML
- handleFileInput
- test_ai_health.py
- scrubber.js
- asyncio
- canNavigateToEmailStep
- PrioritySemaphore
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
- FailoverChatModel
- d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py
- EmailAccountModel
- AsyncSession
- patch
- Request
- schemas/applications.py
- field_validator
- PostgresTracer
- test_delete_assessment_task_archives_application
- ApplicationModel
- e4f5a6b7c8d9_drop_candidate_cv_is_active.py
- f5a6b7c8d9e0_add_provider_token_cost_columns.py
- set_ai_task_binding
- LogActivityModal.vue
- schemas/extension.py
- test_ai_config.py
- test_bulk_transition.py
- fixture
- IntakeQueueDrawer.vue
- StrEnum
- Any
- hybrid_property
- patch
- asyncio
- main.py
- RunnableConfig
- programmatic_scrub_cv
- UploadFile
- TypedDict
- RunnableConfig
- AsyncSession
- put
- setter
- getFitScores
- GlobalSettingsRead
- delete
- switchTab
- setter
- BaseModel
- GlobalSettingsUpdate
- BaseModel
- test_extension.py
- _encrypt_table_secrets
- CandidateCVModel
- loadPricingRates
- Connection
- .exchange_code_for_tokens
- get
- fixture
- close
- routers/agent_chat.py
- get_prompt_template
- env.py
- schemas/companies.py
- scrollToBottom
- executeDirectTransition
- handleAnalyzeSpec
- getCurrencySymbol
- Any
- Base
- closeSidebarOnMobile
- fetchRoleAlignment
- BackgroundTasks
- onTrackMouseDown
- 1a2b3c4d5e6f_create_role_alignment_dossiers.py
- interviewStore.js
- BaseModel
- AnalyticsOverviewResponse
- Response
- FunnelMetricsResponse
- RoleAlignmentResponse
- JobAssessmentResult
- filteredInterviewSessions
- asyncio
- AsyncSession
- BackgroundTasks
- datetime
- delete
- get
- post
- deleteTask
- formatLeadUrl
- patch
- post

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 116 edges
2. `CompanyModel` - 104 edges
3. `useUIStore` - 45 edges
4. `ApplicationEventModel` - 40 edges
5. `process_evaluation_task()` - 36 edges
6. `EmailAccountModel` - 34 edges
7. `PostgresTracer` - 34 edges
8. `EmailPayload` - 33 edges
9. `research_company_context()` - 32 edges
10. `get_task_chat_model()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Root Pre-Commit Configuration` --semantically_similar_to--> `Backend Pre-Commit Configuration`  [INFERRED] [semantically similar]
  .pre-commit-config.yaml → backend/.pre-commit-config.yaml
- `useQueueStore` --indirect_call--> `enqueueAssessment()`  [INFERRED]
  frontend/src/stores/queueStore.js → extension/utils/api.js
- `seed()` --uses--> `CompanyModel`  [INFERRED]
  seed_db.py → backend/app/models/applications.py
- `seed()` --uses--> `IntakeEvaluationTaskModel`  [INFERRED]
  seed_db.py → backend/app/models/intake_tasks.py
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

## Communities (227 total, 75 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (100): accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri, coverLetterLength (+92 more)

### Community 1 - "get_task_chat_model"
Cohesion: 0.10
Nodes (52): ApplicationModel, get_task_chat_model(), Dynamically loads and initializes a LangChain BaseChatModel based on task…, InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session() (+44 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (52): ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData, headerEditForm (+44 more)

### Community 3 - "services/agent_tools.py"
Cohesion: 0.09
Nodes (51): AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, FetchWebpageContentInput, GetCandidateProfileInput, ListApplicationsInput, ManageActionItemsInput (+43 more)

### Community 4 - "OnboardingWizardModal.vue"
Cohesion: 0.03
Nodes (52): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+44 more)

### Community 5 - "ApplicationQuestionModal.vue"
Cohesion: 0.06
Nodes (38): activeCompanyResearchTask, activeQATask, addQuestion(), application, appStore, autoSaveStatus, bulkPasteText, companyResearch (+30 more)

### Community 6 - "ApplicationsView.vue"
Cohesion: 0.03
Nodes (39): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, archiveSortKey, archiveSortOrder (+31 more)

### Community 7 - "test_pricing_service.py"
Cohesion: 0.06
Nodes (56): Any, export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces() (+48 more)

### Community 8 - "ExtractedEmailInfo"
Cohesion: 0.17
Nodes (28): JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., prune_terminal_state_node(), Any, Prunes transient multi-kilobyte string fields prior to checkpointer…, asyncio (+20 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.04
Nodes (34): activeCancelTask, activeCount, activeFixJDTask, completedCount, expandedDossierDetails, expandedEmailDetails, expandedQADetails, failedCount (+26 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "resolve_company_domain"
Cohesion: 0.20
Nodes (19): clean_domain(), extract_domain_from_url(), is_ats_hostname(), query_clearbit_autocomplete(), Domain resolution service for extracting and discovering official company…, Checks if a given hostname belongs to a known ATS or job board., Extracts the company domain from a job posting URL if it is not an ATS., Queries Clearbit's public autocomplete API to find the company's official… (+11 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (39): renderEmailBody(), appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, handleSidebarScroll() (+31 more)

### Community 14 - "normalize_job_url"
Cohesion: 0.08
Nodes (60): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, OtherEventModel, cover_letter_node(), db_commit_node(), extraction_node(), fuzzy_match_node(), _get_db() (+52 more)

### Community 15 - "save_settings"
Cohesion: 0.27
Nodes (12): Saves system settings from a dictionary supporting lower-case and upper-case…, save_settings(), update_global_settings(), GlobalSettingsRead, GlobalSettingsUpdate, asyncio, test_cover_letter_api_endpoints(), test_cover_letter_node_generates_when_above_threshold() (+4 more)

### Community 16 - "CompanyDetailDrawer.vue"
Cohesion: 0.05
Nodes (36): activeTab, allCompanies, applicationFilter, applicationFilters, appStore, closeDrawer(), company, deleteCompany() (+28 more)

### Community 17 - "test_candidate_profile.py"
Cohesion: 0.07
Nodes (48): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+40 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.06
Nodes (33): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkDelete(), bulkMarkAsApplied(), bulkRestore() (+25 more)

### Community 20 - "ActionItemModel"
Cohesion: 0.13
Nodes (30): ActionItemModel, compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks (+22 more)

### Community 21 - "routers/email_accounts.py"
Cohesion: 0.16
Nodes (24): EmailFoldersResponse, fetch_account_folders(), get_oauth_authorize_url(), get_oauth_config(), list_account_folders(), MailFolderItem, oauth_callback(), _oauth_state_client_id() (+16 more)

### Community 22 - "AnalyticsView.vue"
Cohesion: 0.05
Nodes (33): activeTab, alignmentData, alignmentSubTab, analyticsData, analyticsStore, copiedItemKey, currentAlignmentKey, currentDossier (+25 more)

### Community 23 - "CandidateProfileView.vue"
Cohesion: 0.06
Nodes (25): currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling, isDeleting (+17 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.07
Nodes (30): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+22 more)

### Community 25 - "load_settings"
Cohesion: 0.29
Nodes (12): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously., Sets a specific system setting by key asynchronously. (+4 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (25): EmailAccountsAPI, accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm (+17 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "CompanyModel"
Cohesion: 0.09
Nodes (41): CompanyModel, bulk_research_companies(), delete_company(), get_company(), get_potential_duplicates(), list_companies(), merge_companies(), AsyncSession (+33 more)

### Community 29 - "routers/intake.py"
Cohesion: 0.06
Nodes (60): AssessJobRequest, assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations(), delete_evaluation_task(), dismiss_assessment() (+52 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "sync_email_account"
Cohesion: 0.19
Nodes (20): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, TaskResponse, enable_email_intake_mock(), asyncio (+12 more)

### Community 32 - "test_new_features.py"
Cohesion: 0.12
Nodes (23): clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., GenerateInterviewGuideRequest, clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream(), AsyncSession, Async generator that executes `interview_guide_graph.astream(...)` and yields… (+15 more)

### Community 33 - "ActionItemsView.vue"
Cohesion: 0.08
Nodes (23): actionItems, activeUrgencyDropdown, applicationsList, currentEditId, deleteTask(), displayedTasks, fetchActionItems(), filterTab (+15 more)

### Community 34 - "CoverLetterModal.vue"
Cohesion: 0.05
Nodes (40): activeCoverLetterTask, application, appStore, autoSaveStatus, charCount, close(), companyResearch, COVER_LETTER_LENGTHS (+32 more)

### Community 35 - "index.js"
Cohesion: 0.13
Nodes (10): ApplicationsAPI, router, routes, recordPageView(), application, error, hasCopied, isLoading (+2 more)

### Community 36 - "dependencies"
Cohesion: 0.07
Nodes (28): axios, dompurify, dependencies, axios, dompurify, @lucide/vue, lucide-vue-next, pinia (+20 more)

### Community 37 - "process_evaluation_task"
Cohesion: 0.12
Nodes (33): cancel_running_task(), get_running_task_ids(), Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs., register_running_task(), unregister_running_task() (+25 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.07
Nodes (21): ActionItemsAPI, SystemAPI, appStore, fetchBadgeCounts(), getRouteTitle(), handleVisibilityChange(), isHealthPopoverOpen, isMobileMenuOpen (+13 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.07
Nodes (24): analysisData, application, compensationText, computedRatioText, computedScoreText, criticalRisks, emit, error (+16 more)

### Community 41 - "test_skill_normalizer.py"
Cohesion: 0.17
Nodes (19): extract_skills_from_text(), hybrid_extract_skills(), normalize_skill(), normalize_skills_list(), Skill Canonicalization Engine. Provides multi-stage skill normalization,…, Helper to split compound skills unless protected., Normalizes an array of skills with compound splitting, removes duplicates…, Scans raw text using pre-compiled regex patterns to deterministically detect… (+11 more)

### Community 42 - "EmailPayload"
Cohesion: 0.11
Nodes (32): StagingItemModel, EmailPayload, model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve, process_email_batch_sequential(), process_single_email_graph(), AsyncSession (+24 more)

### Community 43 - "DiagnosticsView.vue"
Cohesion: 0.08
Nodes (21): DiagnosticsAPI, activeCategory, categories, copied, currentView, loadData(), loading, loadingDetail (+13 more)

### Community 44 - "DateTimePicker.vue"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "JobIntakeModal.vue"
Cohesion: 0.09
Nodes (23): activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls(), handleBulkPromptDecision() (+15 more)

### Community 46 - "test_application_questions.py"
Cohesion: 0.27
Nodes (10): ApplicationQuestionsUpdateRequest, generate_application_form_answers(), get_application_questions(), update_application_questions(), ApplicationQuestionItem, ApplicationQuestionsResponse, ApplicationQuestionsUpdateRequest, GenerateApplicationQuestionsRequest (+2 more)

### Community 47 - "routers/system_settings.py"
Cohesion: 0.25
Nodes (13): get_system_settings(), AsyncSession, get, patch, post, Validates connectivity to a search provider (such as SearXNG) before saving…, test_search_provider(), update_system_settings() (+5 more)

### Community 48 - "fetch_emails_from_account"
Cohesion: 0.12
Nodes (22): _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using…, GmailOAuthAdapter (+14 more)

### Community 50 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "bulk_dismiss_staging_items"
Cohesion: 0.09
Nodes (32): bulk_dismiss_staging_items(), clear_resolved_staging_items(), get_staging_item(), list_staging_items(), AsyncSession, delete, get, post (+24 more)

### Community 53 - "LazyAsyncPostgresSaver"
Cohesion: 0.11
Nodes (11): AsyncPostgresSaver, check_db_connection(), ensure_db_schema(), LazyAsyncPostgresSaver, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, health_check(), get (+3 more)

### Community 54 - "test_llm_factory.py"
Cohesion: 0.20
Nodes (21): ApplicationSummaryResult, Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem, OptimizationGaps (+13 more)

### Community 55 - "research_company_context"
Cohesion: 0.06
Nodes (60): build_company_research_queries(), build_company_research_query(), build_employer_signals_query(), build_ratings_query(), _collect_company_evidence(), compute_avg_rating(), _extract_json(), _fetch_selected_pages() (+52 more)

### Community 56 - "get_embeddings_model"
Cohesion: 0.21
Nodes (18): _clean_base_url(), get_active_llm_config_dict(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_embeddings_model(), AsyncSession, Strips <think>...</think> reasoning tags from LLM output text. (+10 more)

### Community 57 - "test_system_settings.py"
Cohesion: 0.53
Nodes (5): asyncio, test_email_intake_disabled_guard(), test_global_settings_backward_compatibility(), test_search_provider_settings_and_test_endpoint(), test_system_settings_get_and_patch()

### Community 58 - "trace_operation"
Cohesion: 0.24
Nodes (13): TraceEventModel, Any, AsyncSession, datetime, Persists a programmatic execution trace event into the trace_events table., Async context manager that measures execution time and records diagnostic…, record_diagnostic_event(), trace_operation() (+5 more)

### Community 59 - "endpoints.js"
Cohesion: 0.11
Nodes (27): AgentAPI, AIConfigAPI, AnalyticsAPI, CandidateProfileAPI, EventsAPI, IntakeAPI, PromptsAPI, StagingAPI (+19 more)

### Community 60 - "AsyncSession"
Cohesion: 0.11
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "scheduleStudioAutoSave"
Cohesion: 0.15
Nodes (16): applyProbeRecommendations(), deleteProvider(), fetchStudioModels(), loadPrompts(), loadProviders(), onStudioProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt() (+8 more)

### Community 62 - "CompaniesView.vue"
Cohesion: 0.08
Nodes (29): CompaniesAPI, bulkProgressActive, bulkProgressCompleted, bulkProgressFailed, bulkProgressTotal, bulkResearchMode, companies, companiesWithoutInfo (+21 more)

### Community 63 - "dock.js"
Cohesion: 0.23
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "CompanyLogo.vue"
Cohesion: 0.12
Nodes (15): attemptIndex, candidateDomains, fallbackInitial, faviconUrl, hasError, isLoaded, props, formatDate() (+7 more)

### Community 65 - "test_analytics.py"
Cohesion: 0.08
Nodes (34): Clears all server-side analytics caches across Overview, Funnel, and Role…, recalculate_analytics(), clear_analytics_cache(), Clears in-memory caches for analytics computations. If domain is provided…, db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info() (+26 more)

### Community 66 - "2b3c4d5e6f7a_rename_poc_email_tables.py"
Cohesion: 0.60
Nodes (5): downgrade(), _index_exists(), rename poc email tables and indexes Revision ID: 2b3c4d5e6f7a Revises:…, _table_exists(), upgrade()

### Community 67 - "get_db"
Cohesion: 0.15
Nodes (18): get_db(), AsyncSession, verify_admin_access(), get_prompt(), list_prompts(), AsyncSession, get, patch (+10 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 69 - "routers/ai_config.py"
Cohesion: 0.10
Nodes (39): AIHealthStatusRead, AIProviderCreate, AIProviderModel, AIProviderModelsResponse, AIProviderRead, AIProviderTestResponse, AIProviderUpdate, AITaskTestResponse (+31 more)

### Community 70 - "_execute_evaluation_steps"
Cohesion: 0.40
Nodes (12): _execute_application_qa_steps(), _execute_company_research_steps(), _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), _execute_role_alignment_dossier_steps(), get_company_research_semaphore() (+4 more)

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

### Community 77 - "demoStorage.js"
Cohesion: 0.26
Nodes (11): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+3 more)

### Community 79 - "saveProfileField"
Cohesion: 0.17
Nodes (12): addDomainArea(), addLanguage(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeDomainArea(), removeLanguage(), removeSkill() (+4 more)

### Community 80 - "schemas/intake.py"
Cohesion: 0.26
Nodes (13): AssessJobRequest, BulkTaskActionRequest, BulkTaskActionResult, ConfirmAssessmentRequest, DirectEmailIntakeRequest, EmailBatchIntakeRequest, EmailProcessingSummary, EnqueueAssessmentRequest (+5 more)

### Community 81 - "parse_eml"
Cohesion: 0.18
Nodes (16): _extract_ics_summary(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload., Parses plaintext / raw thread text into EmailPayload., Extracts summary and date info from raw .ics calendar payload. (+8 more)

### Community 83 - "handleOAuthSuccess"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "WebOperationLimiter"
Cohesion: 0.18
Nodes (10): Semaphore, Shared rate and concurrency controls for outbound web operations., A bounded token bucket implemented with scheduled token availability., Limits web request bursts and simultaneous operations per provider. Enforces…, TokenBucket, WebOperationLimiter, asyncio, test_token_bucket_burst_and_rate_limit() (+2 more)

### Community 85 - "jt"
Cohesion: 0.52
Nodes (6): jt script, backup_database(), check_docker(), ensure_env(), open_browser(), show_help()

### Community 86 - "asyncio"
Cohesion: 0.12
Nodes (24): asyncio, test_get_analytics_overview_unit(), test_get_funnel_performance_metrics_unit(), test_get_role_alignment_unit(), test_pipeline_funnel_active_and_dropped_unit(), test_analyze_spec_endpoint_validation_and_enqueue(), test_worker_processes_application_assessment(), test_worker_skips_keyword_check_for_user_provided_jd() (+16 more)

### Community 87 - "formatRelativeDate"
Cohesion: 0.28
Nodes (9): formatRelativeDate(), formatDueDateFriendly(), formatScheduledDate(), formatScheduledDateFriendly(), getDueDate(), getDueDateStr(), getScheduledInterviewDate(), getScheduleUrgencyClass() (+1 more)

### Community 88 - "patch"
Cohesion: 0.18
Nodes (10): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, test_secret_key_auto_generation_and_persistence(), test_secret_key_validation_in_non_dev_environments(), test_security_fernet_secret_key_validation() (+2 more)

### Community 89 - "PostHireModal.vue"
Cohesion: 0.32
Nodes (7): actions, appStore, emit, handleConfirm(), handleDecideLater(), props, submitting

### Community 90 - "advanceAppStage"
Cohesion: 0.38
Nodes (7): advanceAppStage(), executeTransition(), getNextStatus(), handleStatusChange(), onDrop(), openDeleteConfirm(), openTransitionModal()

### Community 91 - "SearchView.vue"
Cohesion: 0.25
Nodes (8): SearchAPI, executeSearch(), handleKeyDown(), hasSearched, loading, results, searchQuery, uiStore

### Community 92 - "fuzzyMatch.js"
Cohesion: 0.25
Nodes (10): fuzzyFilterApplications(), fuzzyScore(), levenshteinDistance(), scoreApplicationMatch(), stringSimilarity(), filteredAndSortedItems, filteredExistingApps, getItemCompany() (+2 more)

### Community 94 - "loadBindings"
Cohesion: 0.16
Nodes (14): applyEmbeddingPreset(), fetchEmbeddingModels(), fetchGlobalModels(), loadBindings(), onEmbeddingProviderChange(), onGlobalProviderChange(), saveEmbeddingBinding(), saveGlobalDefault() (+6 more)

### Community 95 - "selectItem"
Cohesion: 0.15
Nodes (16): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType() (+8 more)

### Community 96 - "routers/llm.py"
Cohesion: 0.24
Nodes (15): mask_secret(), LLMConfigModel, get_current_llm_config(), LLMConfigRead, LLMConfigUpdate, Any, AsyncSession, BaseModel (+7 more)

### Community 97 - "BaseModel"
Cohesion: 0.06
Nodes (66): enhance_role_alignment_endpoint(), get_funnel_metrics(), get_overview(), get_role_alignment_dossier_endpoint(), get_role_alignment_endpoint(), AsyncSession, get, Enqueues an asynchronous AI Strategic Dossier synthesis task through the shared… (+58 more)

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

### Community 110 - "seed_development_dataset"
Cohesion: 0.12
Nodes (23): delete_application(), get_staleness_stats(), AsyncSession, delete, get, post, Truncates all tables in the database, resetting primary keys. Requires explicit…, Populates the database with rich mock development data. If database is not… (+15 more)

### Community 114 - "test_ai_health.py"
Cohesion: 0.33
Nodes (14): AIProviderModel, AITaskBindingModel, invalidate_ai_health_cache(), asyncio, AsyncSession, fixture, reset_health_cache(), test_ai_health_cache_ttl_and_invalidation() (+6 more)

### Community 118 - "PrioritySemaphore"
Cohesion: 0.24
Nodes (4): PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 135 - "FailoverChatModel"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 136 - "d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 137 - "EmailAccountModel"
Cohesion: 0.25
Nodes (9): decrypt_secret(), encrypt_secret(), _get_fernet(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows., EmailAccountModel, hybrid_property, setter (+1 more)

### Community 138 - "AsyncSession"
Cohesion: 0.20
Nodes (12): clear_account_processed_emails(), clear_all_processed_emails(), delete_account(), get_account(), list_accounts(), AsyncSession, delete, Deletes all email deduplication history records for a specific account and… (+4 more)

### Community 141 - "schemas/applications.py"
Cohesion: 0.11
Nodes (31): list_applications(), ActionItemDetail, AllowedApplicationStatus, ApplicationAnalyzeSpecRequest, ApplicationByStatusResult, ApplicationDetailResponse, ApplicationEventDetail, ApplicationFilterParams (+23 more)

### Community 144 - "PostgresTracer"
Cohesion: 0.31
Nodes (6): AsyncBaseTracer, PostgresTracer, asyncio, test_postgres_tracer_background_persist_and_flush(), test_postgres_tracer_does_not_clear_global_run_map(), Run

### Community 145 - "test_delete_assessment_task_archives_application"
Cohesion: 0.38
Nodes (6): asyncio, AsyncSession, Ensure clear-completed deletes worker tasks but strictly preserves…, Ensure deleting a job assessment task transitions linked assessment application…, test_clear_completed_preserves_job_assessment(), test_delete_assessment_task_archives_application()

### Community 146 - "ApplicationModel"
Cohesion: 0.13
Nodes (27): ApplicationModel, archive_stale_applications(), Any, Finds all applications in active stages where last_activity_at (or…, asyncio, test_action_items_crud_and_filtering(), asyncio, test_application_qa_worker_invokes_company_research() (+19 more)

### Community 147 - "e4f5a6b7c8d9_drop_candidate_cv_is_active.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 148 - "f5a6b7c8d9e0_add_provider_token_cost_columns.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 149 - "set_ai_task_binding"
Cohesion: 0.31
Nodes (9): AITaskBindingCreate, AITaskBindingModel, AITaskBindingRead, list_ai_task_bindings(), set_ai_task_binding(), _to_binding_read(), update_pricing_rates_endpoint(), PricingRateBatchUpdate (+1 more)

### Community 150 - "LogActivityModal.vue"
Cohesion: 0.20
Nodes (10): appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction, submitLog() (+2 more)

### Community 151 - "schemas/extension.py"
Cohesion: 0.60
Nodes (4): ClipJobRequest, ClipUrlRequest, ExtensionClipResponse, BaseModel

### Community 152 - "test_ai_config.py"
Cohesion: 0.50
Nodes (8): asyncio, AsyncSession, test_ai_provider_crud_and_masking(), test_domain_entity_models(), test_pricing_rates_endpoints(), test_probe_model_capabilities(), test_task_binding_and_execution(), test_task_binding_custom_extra_body()

### Community 153 - "test_bulk_transition.py"
Cohesion: 0.42
Nodes (10): async_client(), AsyncClient, asyncio, AsyncSession, fixture, test_bulk_transition_archives_open_applications(), test_bulk_transition_creates_timeline_events(), test_bulk_transition_dismisses_pending_action_items_on_terminal() (+2 more)

### Community 155 - "IntakeQueueDrawer.vue"
Cohesion: 0.22
Nodes (5): activeCount, hasItems, queue, STAGES, uiStore

### Community 165 - "main.py"
Cohesion: 0.06
Nodes (50): ApplicationEmbeddingModel, generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, lifespan(), ApplicationEmbeddingModel, ApplicationEventModel, JobPostingModel, delete_event() (+42 more)

### Community 167 - "programmatic_scrub_cv"
Cohesion: 0.47
Nodes (4): programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty()

### Community 171 - "AsyncSession"
Cohesion: 0.11
Nodes (32): AllowedApplicationStatus, ApplicationAnalyzeSpecRequest, ApplicationTransitionRequest, ApplicationUpdate, AsyncSession, analyze_app_job_spec(), bulk_transition_applications(), clear_app_interview_guide() (+24 more)

### Community 174 - "getFitScores"
Cohesion: 0.25
Nodes (7): scores, getFitScores(), getAppFitScores(), sortedArchivedApplications, averageFitScore, filteredPassedEvaluations, filteredReadyEvaluations

### Community 177 - "switchTab"
Cohesion: 0.40
Nodes (5): fetchAnalytics(), fetchFunnelMetrics(), handlePeriodChange(), switchTab(), toggleWorkModel()

### Community 182 - "test_extension.py"
Cohesion: 0.60
Nodes (5): asyncio, AsyncSession, test_extension_clip_job_direct(), test_extension_clip_url_pipeline(), test_extension_intake_url_and_jd_routes()

### Community 183 - "_encrypt_table_secrets"
Cohesion: 0.50
Nodes (3): _encrypt_table_secrets(), upgrade(), Connection

### Community 184 - "CandidateCVModel"
Cohesion: 0.29
Nodes (10): CandidateCVModel, enhance_role_alignment_dossier(), _extract_json_block(), get_role_alignment_dossier(), Any, AsyncSession, Retrieves the existing AI Strategic Dossier from PostgreSQL if generated, or…, Synthesizes a fresh AI Strategic Dossier using LLM task binding and PostgreSQL… (+2 more)

### Community 191 - "routers/agent_chat.py"
Cohesion: 0.15
Nodes (19): AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage, delete_chat(), get_chat(), list_chats() (+11 more)

### Community 192 - "get_prompt_template"
Cohesion: 0.12
Nodes (27): get_prompt_template(), AsyncSession, Retrieves prompt template from DB with in-memory caching, falling back to…, anonymize_and_parse_cv(), assess_job_posting(), build_application_company_context(), extract_email_info(), extract_job_spec() (+19 more)

### Community 193 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 194 - "schemas/companies.py"
Cohesion: 0.53
Nodes (5): CompanyApplicationItem, CompanyMergeRequest, CompanyRead, CompanyUpdate, BaseModel

### Community 195 - "scrollToBottom"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 198 - "getCurrencySymbol"
Cohesion: 0.50
Nodes (4): formatJobSpecCompensation(), getCurrencySymbol(), formatSalary(), getSalaryTooltip()

### Community 200 - "Base"
Cohesion: 0.14
Nodes (9): AgentChatModel, Base, PromptModel, RoleAlignmentDossierModel, delete_stale_agent_chats(), AsyncSession, Background worker that runs once every interval_seconds., staleness_archiver_worker() (+1 more)

### Community 201 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 202 - "fetchRoleAlignment"
Cohesion: 0.50
Nodes (4): fetchRoleAlignment(), handleSearchInput(), onTrackPillClick(), selectTrack()

### Community 204 - "onTrackMouseDown"
Cohesion: 1.00
Nodes (3): onTrackMouseDown(), onTrackMouseMove(), onTrackMouseUp()

### Community 205 - "1a2b3c4d5e6f_create_role_alignment_dossiers.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_exists(), upgrade()

## Knowledge Gaps
- **822 isolated node(s):** `uiStore`, `appStore`, `{ isCompanyDrawerOpen, selectedCompanyId }`, `company`, `isLoading` (+817 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **75 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `endpoints.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationQuestionModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `CompanyDetailDrawer.vue`, `AssessmentsView.vue`, `LogActivityModal.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `IntakeQueueDrawer.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `CompaniesView.vue`, `InterviewReaderModal.vue`, `demoStorage.js`, `SearchView.vue`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `get_task_chat_model`, `services/agent_tools.py`, `test_pricing_service.py`, `ExtractedEmailInfo`, `normalize_job_url`, `save_settings`, `test_delete_assessment_task_archives_application`, `ActionItemModel`, `test_ai_config.py`, `test_bulk_transition.py`, `CompanyModel`, `test_new_features.py`, `main.py`, `process_evaluation_task`, `EmailPayload`, `test_application_questions.py`, `test_extension.py`, `test_analytics.py`, `Base`, `asyncio`, `seed_development_dataset`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `CompanyModel` connect `CompanyModel` to `get_task_chat_model`, `services/agent_tools.py`, `test_pricing_service.py`, `ExtractedEmailInfo`, `normalize_job_url`, `save_settings`, `test_delete_assessment_task_archives_application`, `ApplicationModel`, `test_ai_config.py`, `test_bulk_transition.py`, `main.py`, `process_evaluation_task`, `EmailPayload`, `test_application_questions.py`, `test_extension.py`, `research_company_context`, `test_analytics.py`, `Base`, `asyncio`, `seed_development_dataset`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 88 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 88 INFERRED edges - model-reasoned connections that need verification._
- **Are the 82 inferred relationships involving `CompanyModel` (e.g. with `search_companies()` and `semantic_search()`) actually correct?**
  _`CompanyModel` has 82 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `useUIStore` (e.g. with `openCoverLetterModal()` and `openCompanyDrawer()`) actually correct?**
  _`useUIStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 20 INFERRED edges - model-reasoned connections that need verification._