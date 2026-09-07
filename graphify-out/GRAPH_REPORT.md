# Graph Report - job-tracker  (2026-09-07)

## Corpus Check
- 262 files · ~328,419 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3538 nodes · 6748 edges · 251 communities (158 shown, 93 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 752 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3f056c0d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- PostgresTracer
- ApplicationDetailDrawer.vue
- services/agent_tools.py
- OnboardingWizardModal.vue
- ApplicationQuestionModal.vue
- ApplicationsView.vue
- test_new_features.py
- routers/search.py
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- persist_or_stage_job_assessment
- StagingView.vue
- scrape_job_url
- routers/prompts.py
- CompanyDetailDrawer.vue
- patch
- popup.js
- AssessmentsView.vue
- ActionItemModel
- routers/email_accounts.py
- AnalyticsView.vue
- CandidateProfileView.vue
- JobIntakeView.vue
- parse_eml
- EmailAccountsSettings.vue
- FloatingQueueWidget.vue
- test_companies_router.py
- BaseModel
- manifest.json
- sync_email_account
- endpoints.js
- ActionItemsView.vue
- CoverLetterModal.vue
- index.js
- dependencies
- process_evaluation_task
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- routers/candidate_profile.py
- ApplicationEventModel
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- ExtractedEmailInfo
- Base
- fetch_emails_from_account
- datetime
- clean_html_text
- test_email_accounts.py
- routers/staging.py
- LazyAsyncPostgresSaver
- archive_stale_applications
- services/llm.py
- schemas/llm.py
- test_system_settings.py
- trace_operation
- EmailAccountModel
- AsyncSession
- scheduleStudioAutoSave
- CompaniesView.vue
- dock.js
- CompanyLogo.vue
- conftest.py
- 2b3c4d5e6f7a_rename_poc_email_tables.py
- schemas/intake.py
- InterviewReaderModal.vue
- routers/ai_config.py
- search_web
- create_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- test_schemas.py
- extractJobData
- uiStore.js
- TaskTracker
- saveProfileField
- routers/llm.py
- routers/agent_chat.py
- BaseModel
- handleOAuthSuccess
- WebOperationLimiter
- jt
- ApplicationModel
- formatRelativeDate
- Settings
- PostHireModal.vue
- _execute_evaluation_steps
- PrioritySemaphore
- fuzzyMatch.js
- AsyncSession
- loadBindings
- selectItem
- get_task_chat_model
- test_analytics.py
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
- main.py
- Email Synchronization Engine
- Frontend SPA Entry HTML
- handleFileInput
- datetime
- scrubber.js
- asyncio
- canNavigateToEmailStep
- switchTab
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
- normalize_job_url
- d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py
- demoStorage.js
- routers/analytics.py
- patch
- Request
- services/analytics.py
- field_validator
- fetchRoleAlignment
- asyncio
- get_db
- e4f5a6b7c8d9_drop_candidate_cv_is_active.py
- f5a6b7c8d9e0_add_provider_token_cost_columns.py
- load_settings
- onTrackMouseDown
- schemas/extension.py
- AsyncSession
- ApplicationModel
- fixture
- BaseModel
- StrEnum
- CandidateCVModel
- hybrid_property
- patch
- asyncio
- routers/diagnostics.py
- RunnableConfig
- anonymize_and_parse_cv
- UploadFile
- TypedDict
- RunnableConfig
- AsyncSession
- put
- setter
- research_company_context
- GlobalSettingsRead
- delete
- schemas/agent_tools.py
- setter
- BaseModel
- GlobalSettingsUpdate
- BaseModel
- interviewStore.js
- schemas/applications.py
- scrollToBottom
- loadPricingRates
- Connection
- enqueue_cv_profile_processing
- get
- fixture
- LogActivityModal.vue
- FailoverChatModel
- ApplicationSummaryResult
- env.py
- schemas/companies.py
- clip_job_pre_extracted
- get_prompt_template
- getFitScores
- getCurrencySymbol
- test_company_research.py
- routers/intake.py
- test_bulk_transition.py
- clearSelection
- BackgroundTasks
- get
- 1a2b3c4d5e6f_create_role_alignment_dossiers.py
- delete_cv_profile
- BaseModel
- AnalyticsOverviewResponse
- Response
- FunnelMetricsResponse
- RoleAlignmentResponse
- patch
- closeSidebarOnMobile
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
- _encrypt_table_secrets
- get_funnel_metrics
- post
- Any
- BaseModel
- get_badge_counts
- asyncio
- JobAssessmentResult
- advanceAppStage
- rules/graphify.md
- AsyncSession
- closeDrawer
- asyncio
- close
- executeDirectTransition
- handleAnalyzeSpec
- filteredCompanyApplications
- saveEditHeader
- filteredInterviewSessions
- JobAssessmentResult
- delete
- get
- post
- workflows/graphify.md

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 103 edges
2. `CompanyModel` - 97 edges
3. `useUIStore` - 45 edges
4. `ApplicationEventModel` - 37 edges
5. `process_evaluation_task()` - 35 edges
6. `EmailAccountModel` - 34 edges
7. `IntakeEvaluationTaskModel` - 33 edges
8. `EmailPayload` - 33 edges
9. `research_company_context()` - 33 edges
10. `PostgresTracer` - 32 edges

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

## Communities (251 total, 93 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (101): PromptsAPI, accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri (+93 more)

### Community 1 - "PostgresTracer"
Cohesion: 0.06
Nodes (74): AsyncBaseTracer, InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions() (+66 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (58): EventsAPI, ALL_SECTIONS, appStore, companyResearch, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode (+50 more)

### Community 3 - "services/agent_tools.py"
Cohesion: 0.07
Nodes (57): ApplicationEmbeddingModel, Sets a specific system setting by key asynchronously., set_setting(), create_agent_tools(), execute_analyze_pipeline_metrics(), execute_detect_stalled_applications(), execute_evaluate_ai_fit_score(), execute_fetch_webpage_content() (+49 more)

### Community 4 - "OnboardingWizardModal.vue"
Cohesion: 0.03
Nodes (52): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+44 more)

### Community 5 - "ApplicationQuestionModal.vue"
Cohesion: 0.06
Nodes (38): activeCompanyResearchTask, activeQATask, addQuestion(), application, appStore, autoSaveStatus, bulkPasteText, companyResearch (+30 more)

### Community 6 - "ApplicationsView.vue"
Cohesion: 0.03
Nodes (39): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, archiveSortKey, archiveSortOrder (+31 more)

### Community 7 - "test_new_features.py"
Cohesion: 0.18
Nodes (16): GenerateInterviewGuideRequest, clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream(), ApplicationModel, AsyncSession, Async generator that executes `interview_guide_graph.astream(...)` and yields…, Coordinates candidate profile retrieval, job posting lookup, LangGraph… (+8 more)

### Community 8 - "routers/search.py"
Cohesion: 0.33
Nodes (8): AsyncSession, get, Returns matching companies alongside total tracked application count., search_companies(), semantic_search(), CompanySearchResult, BaseModel, SemanticSearchResult

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.04
Nodes (34): activeCancelTask, activeCount, activeFixJDTask, completedCount, expandedDossierDetails, expandedEmailDetails, expandedQADetails, failedCount (+26 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "persist_or_stage_job_assessment"
Cohesion: 0.05
Nodes (66): is_permissive_domain_match(), AsyncSession, Dedicated About Us URL discovery service. Inspects company homepage…, Checks if candidate_url belongs to the root_domain or its subdomains., Discovers the authentic 'About Us' page URL for a company domain. 1. Fetches…, resolve_company_about_url(), clean_company_name(), clean_domain() (+58 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (39): renderEmailBody(), appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, handleSidebarScroll() (+31 more)

### Community 14 - "scrape_job_url"
Cohesion: 0.16
Nodes (25): clean_extracted_text(), has_job_content_keywords(), BaseModel, Validates URL protocol and private IP / loopback address validation (SSRF…, Blazing fast multi-language scraper keyword validation using Python set hash…, Backward-compatible alias for validate_job_content., Normalizes whitespace and strips javascript code blocks, jQuery artifacts, and…, Scrapes a URL using the running Camofox browser automation server. (+17 more)

### Community 15 - "routers/prompts.py"
Cohesion: 0.23
Nodes (14): clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., PromptModel, get_prompt(), list_prompts(), AsyncSession, List all available system prompts., Fetch a specific prompt template by name (e.g., 'email_extraction',… (+6 more)

### Community 16 - "CompanyDetailDrawer.vue"
Cohesion: 0.05
Nodes (27): activeTab, allCompanies, applicationFilter, applicationFilters, appStore, company, filteredMergeCompanies, headerEditForm (+19 more)

### Community 17 - "patch"
Cohesion: 0.20
Nodes (15): compute_programmatic_skill_match(), _is_skill_matched(), _normalize_token(), Checks if a JD required skill matches any skill in the candidate's CV profile., Computes Job Requirement Coverage Ratio between candidate CV skills and the…, asyncio, AsyncSession, test_assess_job_posting_forwards_authoritative_candidate_profile() (+7 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (34): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), extractActiveTab() (+26 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.06
Nodes (35): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkDelete(), bulkMarkAsApplied(), bulkRestore() (+27 more)

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
Nodes (26): CandidateProfileAPI, currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling (+18 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.07
Nodes (30): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+22 more)

### Community 25 - "parse_eml"
Cohesion: 0.18
Nodes (16): _extract_ics_summary(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload., Parses plaintext / raw thread text into EmailPayload., Extracts summary and date info from raw .ics calendar payload. (+8 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (25): EmailAccountsAPI, accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm (+17 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "test_companies_router.py"
Cohesion: 0.09
Nodes (40): bulk_research_companies(), delete_company(), get_company(), get_potential_duplicates(), list_companies(), merge_companies(), AsyncSession, BackgroundTasks (+32 more)

### Community 29 - "BaseModel"
Cohesion: 0.13
Nodes (23): AIHealthStatusRead, AIProviderCreate, AIProviderModelsResponse, AIProviderRead, AIProviderTestResponse, AIProviderUpdate, AITaskBindingCreate, AITaskBindingRead (+15 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "sync_email_account"
Cohesion: 0.21
Nodes (19): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, enable_email_intake_mock(), asyncio, AsyncSession (+11 more)

### Community 32 - "endpoints.js"
Cohesion: 0.10
Nodes (23): ActionItemsAPI, AgentAPI, AnalyticsAPI, CompaniesAPI, IntakeAPI, SearchAPI, StagingAPI, SystemAPI (+15 more)

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
Cohesion: 0.14
Nodes (29): Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., register_running_task(), unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification…, ExtractedJobSpec, JobAssessmentResult (+21 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.07
Nodes (19): appStore, fetchBadgeCounts(), getRouteTitle(), handleVisibilityChange(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount, pendingTasksCount (+11 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.07
Nodes (24): analysisData, application, compensationText, computedRatioText, computedScoreText, criticalRisks, emit, error (+16 more)

### Community 41 - "routers/candidate_profile.py"
Cohesion: 0.31
Nodes (11): Updates skills, summary, or anonymized text for a CV profile., update_cv_profile(), CandidateCVResponse, CandidateCVSaveRequest, CandidateCVUpdateRequest, CVAnonymizationResult, CVParsedDocumentResponse, CVTaskStatusResponse (+3 more)

### Community 42 - "ApplicationEventModel"
Cohesion: 0.11
Nodes (32): ApplicationEventModel, EmailPayload, model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve, process_email_batch_sequential(), process_single_email_graph(), AsyncSession (+24 more)

### Community 43 - "DiagnosticsView.vue"
Cohesion: 0.08
Nodes (21): DiagnosticsAPI, activeCategory, categories, copied, currentView, loadData(), loading, loadingDetail (+13 more)

### Community 44 - "DateTimePicker.vue"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "JobIntakeModal.vue"
Cohesion: 0.09
Nodes (23): activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls(), handleBulkPromptDecision() (+15 more)

### Community 46 - "ExtractedEmailInfo"
Cohesion: 0.17
Nodes (29): StagingItemModel, JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., prune_terminal_state_node(), Any, Prunes transient multi-kilobyte string fields prior to checkpointer… (+21 more)

### Community 47 - "Base"
Cohesion: 0.28
Nodes (11): ApplicationEmbeddingModel, Base, JobPostingModel, OtherEventModel, asyncio, AsyncSession, test_activity_logging_preserves_task_completion(), test_application_patch_updates() (+3 more)

### Community 48 - "fetch_emails_from_account"
Cohesion: 0.12
Nodes (21): _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using…, GmailOAuthAdapter (+13 more)

### Community 50 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "routers/staging.py"
Cohesion: 0.08
Nodes (36): delete_evaluation_task(), dismiss_assessment(), permanently_delete_assessment(), Archives an assessment dossier while keeping it available in Assessments., Permanently deletes an assessment dossier (ready or archived) and its related…, Cancels an ongoing evaluation or dismisses a completed/failed evaluation task., bulk_dismiss_staging_items(), clear_resolved_staging_items() (+28 more)

### Community 53 - "LazyAsyncPostgresSaver"
Cohesion: 0.11
Nodes (11): AsyncPostgresSaver, check_db_connection(), ensure_db_schema(), LazyAsyncPostgresSaver, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, health_check(), get (+3 more)

### Community 54 - "archive_stale_applications"
Cohesion: 0.18
Nodes (18): AgentChatModel, archive_stale_applications(), delete_stale_agent_chats(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or…, Background worker that runs once every interval_seconds., staleness_archiver_worker() (+10 more)

### Community 55 - "services/llm.py"
Cohesion: 0.13
Nodes (21): build_application_company_context(), calibrate_assessment_score_and_recommendation(), extract_job_spec(), generate_application_answers(), generate_cover_letter(), get_active_llm_config(), Any, Applies mathematical bounding and recommendation synchronization to eliminate… (+13 more)

### Community 56 - "schemas/llm.py"
Cohesion: 0.24
Nodes (11): ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem, LanguageMatchResult, OptimizationGaps, ResumeTailoringStrategy, SpokenLanguageRequirement (+3 more)

### Community 57 - "test_system_settings.py"
Cohesion: 0.53
Nodes (5): asyncio, test_email_intake_disabled_guard(), test_global_settings_backward_compatibility(), test_search_provider_settings_and_test_endpoint(), test_system_settings_get_and_patch()

### Community 58 - "trace_operation"
Cohesion: 0.22
Nodes (13): TraceEventModel, Any, AsyncSession, datetime, Persists a programmatic execution trace event into the trace_events table., Async context manager that measures execution time and records diagnostic…, record_diagnostic_event(), trace_operation() (+5 more)

### Community 59 - "EmailAccountModel"
Cohesion: 0.18
Nodes (13): decrypt_secret(), encrypt_secret(), _get_fernet(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows., verify_admin_access(), EmailAccountModel, hybrid_property (+5 more)

### Community 60 - "AsyncSession"
Cohesion: 0.13
Nodes (18): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), AsyncSession, delete, get, Returns stored logs of non-job recruitment emails (e.g. newsletters, automated… (+10 more)

### Community 61 - "scheduleStudioAutoSave"
Cohesion: 0.15
Nodes (16): applyProbeRecommendations(), deleteProvider(), fetchStudioModels(), loadPrompts(), loadProviders(), onStudioProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt() (+8 more)

### Community 62 - "CompaniesView.vue"
Cohesion: 0.08
Nodes (27): bulkProgressActive, bulkProgressCompleted, bulkProgressFailed, bulkProgressTotal, bulkResearchMode, companies, companiesWithoutInfo, duplicateData (+19 more)

### Community 63 - "dock.js"
Cohesion: 0.24
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "CompanyLogo.vue"
Cohesion: 0.11
Nodes (16): attemptIndex, candidateDomains, fallbackInitial, faviconUrl, hasError, isLoaded, props, formatDate() (+8 more)

### Community 65 - "conftest.py"
Cohesion: 0.12
Nodes (19): db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info(), mock_job_email_payload(), postgres_container(), AsyncSession, pytest_collection_modifyitems() (+11 more)

### Community 66 - "2b3c4d5e6f7a_rename_poc_email_tables.py"
Cohesion: 0.60
Nodes (5): downgrade(), _index_exists(), rename poc email tables and indexes Revision ID: 2b3c4d5e6f7a Revises:…, _table_exists(), upgrade()

### Community 67 - "schemas/intake.py"
Cohesion: 0.26
Nodes (13): AssessJobRequest, BulkTaskActionRequest, BulkTaskActionResult, ConfirmAssessmentRequest, DirectEmailIntakeRequest, EmailBatchIntakeRequest, EmailProcessingSummary, EnqueueAssessmentRequest (+5 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 69 - "routers/ai_config.py"
Cohesion: 0.05
Nodes (83): AIHealthStatusRead, AIProviderCreate, AIProviderModel, AIProviderModelsResponse, AIProviderRead, AIProviderTestResponse, AIProviderUpdate, AITaskBindingCreate (+75 more)

### Community 70 - "search_web"
Cohesion: 0.17
Nodes (18): fetch_webpage_content(), AsyncSession, _query_searxng(), Resolves effective search provider and searxng_url from system settings., Executes synchronous DDGS text search in a dedicated thread to avoid blocking…, Asynchronously queries configured search provider (SearXNG or DDGS) and returns…, Scrapes and cleans webpage markdown/text from a target URL using Camofox with…, Asynchronously queries SearXNG JSON API endpoint with timeout. (+10 more)

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

### Community 75 - "test_schemas.py"
Cohesion: 0.16
Nodes (15): AllowedApplicationStatus, ApplicationTransitionRequest, ApplicationUpdate, BulkTransitionRequest, BulkTransitionResult, Any, Any, test_application_transition_request_date_coercion() (+7 more)

### Community 76 - "extractJobData"
Cohesion: 0.22
Nodes (8): extractJobData(), deriveTitleFromDoc(), getText(), getTextIn(), queryFirst(), queryFirstIn(), isCleanTitle(), resolveCanonicalJobUrl()

### Community 77 - "uiStore.js"
Cohesion: 0.12
Nodes (17): AIConfigAPI, uiStore, uiStore, activeCount, hasItems, queue, STAGES, uiStore (+9 more)

### Community 79 - "saveProfileField"
Cohesion: 0.17
Nodes (12): addDomainArea(), addLanguage(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeDomainArea(), removeLanguage(), removeSkill() (+4 more)

### Community 80 - "routers/llm.py"
Cohesion: 0.24
Nodes (15): mask_secret(), LLMConfigModel, get_current_llm_config(), LLMConfigRead, LLMConfigUpdate, Any, AsyncSession, BaseModel (+7 more)

### Community 81 - "routers/agent_chat.py"
Cohesion: 0.15
Nodes (19): AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage, delete_chat(), get_chat(), list_chats() (+11 more)

### Community 83 - "handleOAuthSuccess"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "WebOperationLimiter"
Cohesion: 0.18
Nodes (10): Semaphore, Shared rate and concurrency controls for outbound web operations., A bounded token bucket implemented with scheduled token availability., Limits web request bursts and simultaneous operations per provider. Enforces…, TokenBucket, WebOperationLimiter, asyncio, test_token_bucket_burst_and_rate_limit() (+2 more)

### Community 85 - "jt"
Cohesion: 0.52
Nodes (6): jt script, backup_database(), check_docker(), ensure_env(), open_browser(), show_help()

### Community 86 - "ApplicationModel"
Cohesion: 0.10
Nodes (38): asyncio, ApplicationModel, CompanyModel, asyncio, test_action_items_crud_and_filtering(), test_get_analytics_overview_unit(), test_pipeline_funnel_active_and_dropped_unit(), test_analyze_spec_endpoint_validation_and_enqueue() (+30 more)

### Community 87 - "formatRelativeDate"
Cohesion: 0.28
Nodes (9): formatRelativeDate(), formatDueDateFriendly(), formatScheduledDate(), formatScheduledDateFriendly(), getDueDate(), getDueDateStr(), getScheduledInterviewDate(), getScheduleUrgencyClass() (+1 more)

### Community 88 - "Settings"
Cohesion: 0.18
Nodes (9): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, test_secret_key_auto_generation_and_persistence(), test_secret_key_validation_in_non_dev_environments(), test_security_fernet_secret_key_validation() (+1 more)

### Community 89 - "PostHireModal.vue"
Cohesion: 0.32
Nodes (7): actions, appStore, emit, handleConfirm(), handleDecideLater(), props, submitting

### Community 90 - "_execute_evaluation_steps"
Cohesion: 0.32
Nodes (14): _execute_application_qa_steps(), _execute_company_research_steps(), _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), _execute_role_alignment_dossier_steps(), get_company_research_semaphore() (+6 more)

### Community 91 - "PrioritySemaphore"
Cohesion: 0.16
Nodes (8): cancel_running_task(), get_running_task_ids(), PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs., Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 92 - "fuzzyMatch.js"
Cohesion: 0.25
Nodes (10): fuzzyFilterApplications(), fuzzyScore(), levenshteinDistance(), scoreApplicationMatch(), stringSimilarity(), filteredAndSortedItems, filteredExistingApps, getItemCompany() (+2 more)

### Community 94 - "loadBindings"
Cohesion: 0.16
Nodes (14): applyEmbeddingPreset(), fetchEmbeddingModels(), fetchGlobalModels(), loadBindings(), onEmbeddingProviderChange(), onGlobalProviderChange(), saveEmbeddingBinding(), saveGlobalDefault() (+6 more)

### Community 95 - "selectItem"
Cohesion: 0.15
Nodes (16): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType() (+8 more)

### Community 96 - "get_task_chat_model"
Cohesion: 0.17
Nodes (22): AITaskTestResponse, generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, _clean_base_url(), get_active_llm_config_dict(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model() (+14 more)

### Community 97 - "test_analytics.py"
Cohesion: 0.30
Nodes (11): override_db(), asyncio, AsyncSession, test_auto_recalculate_when_db_has_more_data(), test_get_analytics_overview(), test_get_funnel_metrics_monthly(), test_get_funnel_metrics_weekly(), test_get_role_alignment() (+3 more)

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

### Community 110 - "main.py"
Cohesion: 0.08
Nodes (32): lifespan(), delete_application(), delete_event(), get_staleness_stats(), AsyncSession, delete, get, post (+24 more)

### Community 114 - "datetime"
Cohesion: 0.23
Nodes (3): RoleAlignmentDossierModel, SystemSettingsModel, datetime

### Community 118 - "switchTab"
Cohesion: 0.40
Nodes (5): fetchAnalytics(), fetchFunnelMetrics(), handlePeriodChange(), switchTab(), toggleWorkModel()

### Community 135 - "normalize_job_url"
Cohesion: 0.13
Nodes (18): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, confirm_job_assessment(), _format_graph_result(), Commits an assessed job lead to the application pipeline in ASSESSMENT or…, Accepts user fixes, applies them to DB records, and marks the staged item…, resolve_staging_item(), AsyncSessionMock (+10 more)

### Community 136 - "d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 137 - "demoStorage.js"
Cohesion: 0.30
Nodes (10): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+2 more)

### Community 138 - "routers/analytics.py"
Cohesion: 0.20
Nodes (15): enhance_role_alignment_endpoint(), get_funnel_metrics(), get_overview(), get_role_alignment_dossier_endpoint(), get_role_alignment_endpoint(), AsyncSession, get, Enqueues an asynchronous AI Strategic Dossier synthesis task through the shared… (+7 more)

### Community 141 - "services/analytics.py"
Cohesion: 0.14
Nodes (28): AnalyticsOverviewResponse, BulletReframeItem, FunnelChartStage, FunnelCohortPeriod, FunnelKpiCard, FunnelMetricsResponse, FunnelStageItem, RoleAlignmentResponse (+20 more)

### Community 144 - "fetchRoleAlignment"
Cohesion: 0.50
Nodes (4): fetchRoleAlignment(), handleSearchInput(), onTrackPillClick(), selectTrack()

### Community 146 - "get_db"
Cohesion: 0.25
Nodes (9): get_db(), AsyncSession, asyncio, AsyncSession, test_extension_clip_job_direct(), test_extension_clip_url_pipeline(), test_extension_intake_url_and_jd_routes(), Integration test for POST /applications/{id}/interview-guide and DELETE… (+1 more)

### Community 147 - "e4f5a6b7c8d9_drop_candidate_cv_is_active.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 148 - "f5a6b7c8d9e0_add_provider_token_cost_columns.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 149 - "load_settings"
Cohesion: 0.07
Nodes (66): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously. (+58 more)

### Community 150 - "onTrackMouseDown"
Cohesion: 1.00
Nodes (3): onTrackMouseDown(), onTrackMouseMove(), onTrackMouseUp()

### Community 151 - "schemas/extension.py"
Cohesion: 0.60
Nodes (4): ClipJobRequest, ClipUrlRequest, ExtensionClipResponse, BaseModel

### Community 161 - "CandidateCVModel"
Cohesion: 0.29
Nodes (10): CandidateCVModel, enhance_role_alignment_dossier(), _extract_json_block(), get_role_alignment_dossier(), Any, AsyncSession, Retrieves the existing AI Strategic Dossier from PostgreSQL if generated, or…, Synthesizes a fresh AI Strategic Dossier using LLM task binding and PostgreSQL… (+2 more)

### Community 165 - "routers/diagnostics.py"
Cohesion: 0.28
Nodes (12): export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces(), AsyncSession (+4 more)

### Community 167 - "anonymize_and_parse_cv"
Cohesion: 0.28
Nodes (7): anonymize_and_parse_cv(), De-identifies candidate resume: - Runs local programmatic regex pre-scrubber on…, programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty(), CVAnonymizationResult

### Community 171 - "AsyncSession"
Cohesion: 0.07
Nodes (51): AllowedApplicationStatus, ApplicationAnalyzeSpecRequest, ApplicationQuestionsUpdateRequest, ApplicationTransitionRequest, ApplicationUpdate, AsyncSession, analyze_app_job_spec(), bulk_transition_applications() (+43 more)

### Community 174 - "research_company_context"
Cohesion: 0.11
Nodes (32): build_company_research_queries(), build_employer_signals_query(), build_ratings_query(), _collect_company_evidence(), compute_avg_rating(), _extract_json(), _fetch_selected_pages(), _invoke_llm() (+24 more)

### Community 177 - "schemas/agent_tools.py"
Cohesion: 0.23
Nodes (15): AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, FetchWebpageContentInput, GetCandidateProfileInput, ListApplicationsInput, ManageActionItemsInput (+7 more)

### Community 183 - "schemas/applications.py"
Cohesion: 0.15
Nodes (14): ActionItemDetail, ApplicationAnalyzeSpecRequest, ApplicationDetailResponse, ApplicationEventDetail, ApplicationFilterParams, ApplicationListItem, ApplicationListResponse, ApplicationQuestionsUpdateRequest (+6 more)

### Community 184 - "scrollToBottom"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 187 - "enqueue_cv_profile_processing"
Cohesion: 0.20
Nodes (11): enqueue_cv_profile_processing(), parse_cv_document_file(), BackgroundTasks, post, UploadFile, Parses an uploaded resume file (.pdf, .docx, .doc, .txt) and returns extracted…, Enqueues candidate CV for asynchronous de-identification, duration conversion,…, normalize_resume_text() (+3 more)

### Community 190 - "LogActivityModal.vue"
Cohesion: 0.20
Nodes (10): appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction, submitLog() (+2 more)

### Community 191 - "FailoverChatModel"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 193 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 194 - "schemas/companies.py"
Cohesion: 0.53
Nodes (5): CompanyApplicationItem, CompanyMergeRequest, CompanyRead, CompanyUpdate, BaseModel

### Community 195 - "clip_job_pre_extracted"
Cohesion: 0.22
Nodes (11): clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text…, Receives a job posting URL, scrapes page text (or uses pre-captured HTML), and… (+3 more)

### Community 196 - "get_prompt_template"
Cohesion: 0.11
Nodes (25): Strips <think>...</think> reasoning tags from LLM output text., strip_reasoning_tags(), get_prompt_template(), AsyncSession, Seeds missing prompts into DB upon boot without overwriting existing user…, Retrieves prompt template from DB with in-memory caching, falling back to…, seed_default_prompts(), extract_email_info() (+17 more)

### Community 197 - "getFitScores"
Cohesion: 0.25
Nodes (7): scores, getFitScores(), getAppFitScores(), sortedArchivedApplications, averageFitScore, filteredPassedEvaluations, filteredReadyEvaluations

### Community 198 - "getCurrencySymbol"
Cohesion: 0.50
Nodes (4): formatJobSpecCompensation(), getCurrencySymbol(), formatSalary(), getSalaryTooltip()

### Community 199 - "test_company_research.py"
Cohesion: 0.33
Nodes (6): build_company_research_query(), Constructs a multi-factor DuckDuckGo search query anchored with domain and…, test_build_application_company_context_filters_low_value_research(), test_build_company_research_query(), test_collect_company_evidence_uses_categories_and_deduplicates(), test_generate_cover_letter_injects_company_research()

### Community 200 - "routers/intake.py"
Cohesion: 0.07
Nodes (45): AssessJobRequest, assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations(), enqueue_job_assessment(), ExtensionUrlDirectPayload (+37 more)

### Community 201 - "test_bulk_transition.py"
Cohesion: 0.42
Nodes (10): async_client(), AsyncClient, asyncio, AsyncSession, fixture, test_bulk_transition_archives_open_applications(), test_bulk_transition_creates_timeline_events(), test_bulk_transition_dismisses_pending_action_items_on_terminal() (+2 more)

### Community 202 - "clearSelection"
Cohesion: 0.50
Nodes (4): bulkDeleteSelected(), bulkRetrySelected(), clearSelection(), toggleSelectAll()

### Community 205 - "1a2b3c4d5e6f_create_role_alignment_dossiers.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_exists(), upgrade()

### Community 206 - "delete_cv_profile"
Cohesion: 0.25
Nodes (9): delete_cv_profile(), get_active_cv_profile(), get_cv_task_status(), AsyncSession, delete, get, Retrieves status and stage of an asynchronous CV processing task., Deletes a candidate CV profile. (+1 more)

### Community 214 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 227 - "_encrypt_table_secrets"
Cohesion: 0.50
Nodes (3): _encrypt_table_secrets(), upgrade(), Connection

### Community 228 - "get_funnel_metrics"
Cohesion: 0.67
Nodes (3): get_funnel_metrics(), AsyncSession, get

### Community 232 - "get_badge_counts"
Cohesion: 0.29
Nodes (6): get_badge_counts(), AsyncSession, get, Returns aggregated counts for Navbar and drawer badges in a single optimized DB…, BadgeCountsResponse, BaseModel

### Community 235 - "advanceAppStage"
Cohesion: 0.38
Nodes (7): advanceAppStage(), executeTransition(), getNextStatus(), handleStatusChange(), onDrop(), openDeleteConfirm(), openTransitionModal()

### Community 238 - "closeDrawer"
Cohesion: 0.33
Nodes (6): closeDrawer(), deleteCompany(), fetchCompany(), handleMerge(), loadAllCompaniesForMerge(), openApplication()

## Knowledge Gaps
- **829 isolated node(s):** `graphify`, `Workflow: graphify`, `accountToClear`, `accountToDelete`, `activeTab` (+824 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **93 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `uiStore.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationQuestionModal.vue`, `ApplicationsView.vue`, `demoStorage.js`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `CompanyDetailDrawer.vue`, `AssessmentsView.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `endpoints.js`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `CompaniesView.vue`, `LogActivityModal.vue`, `InterviewReaderModal.vue`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `PostgresTracer`, `services/agent_tools.py`, `normalize_job_url`, `routers/search.py`, `persist_or_stage_job_assessment`, `services/analytics.py`, `get_db`, `ActionItemModel`, `load_settings`, `test_companies_router.py`, `process_evaluation_task`, `ApplicationEventModel`, `ExtractedEmailInfo`, `Base`, `archive_stale_applications`, `clip_job_pre_extracted`, `test_bulk_transition.py`, `test_analytics.py`, `main.py`, `datetime`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `CompanyModel` connect `ApplicationModel` to `test_analytics.py`, `PostgresTracer`, `services/agent_tools.py`, `process_evaluation_task`, `routers/search.py`, `test_bulk_transition.py`, `ApplicationEventModel`, `main.py`, `Base`, `ExtractedEmailInfo`, `get_db`, `load_settings`, `archive_stale_applications`, `test_companies_router.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 81 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `CompanyModel` (e.g. with `search_companies()` and `semantic_search()`) actually correct?**
  _`CompanyModel` has 79 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `useUIStore` (e.g. with `openCoverLetterModal()` and `openCompanyDrawer()`) actually correct?**
  _`useUIStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `graphify`, `Workflow: graphify`, `accountToClear` to the rest of the system?**
  _829 weakly-connected nodes found - possible documentation gaps or missing edges._