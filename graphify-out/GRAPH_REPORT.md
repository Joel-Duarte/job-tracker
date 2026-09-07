# Graph Report - job-tracker  (2026-09-07)

## Corpus Check
- 260 files · ~328,025 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3531 nodes · 6744 edges · 245 communities (159 shown, 86 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 746 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1e9c698a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- InterviewSimulatorService
- ApplicationDetailDrawer.vue
- datetime
- OnboardingWizardModal.vue
- ApplicationQuestionModal.vue
- ApplicationsView.vue
- test_pricing_service.py
- routers/search.py
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- persist_or_stage_job_assessment
- StagingView.vue
- scrape_job_url
- seed_default_prompts
- CompanyDetailDrawer.vue
- test_candidate_profile.py
- popup.js
- AssessmentsView.vue
- routers/action_items.py
- routers/email_accounts.py
- AnalyticsView.vue
- CandidateProfileView.vue
- JobIntakeView.vue
- asyncio
- EmailAccountsSettings.vue
- FloatingQueueWidget.vue
- resolve_or_create_company
- post
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
- routers/candidate_profile.py
- ApplicationEventModel
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- ExtractedEmailInfo
- test_skill_normalizer.py
- GmailOAuthAdapter
- datetime
- clean_html_text
- test_email_accounts.py
- routers/staging.py
- LazyAsyncPostgresSaver
- archive_stale_applications
- services/llm.py
- routers/system_settings.py
- test_system_settings.py
- trace_operation
- decrypt_secret
- routers/events.py
- scheduleStudioAutoSave
- CompaniesView.vue
- dock.js
- CompanyLogo.vue
- test_analytics.py
- 2b3c4d5e6f7a_rename_poc_email_tables.py
- routers/llm.py
- InterviewReaderModal.vue
- routers/ai_config.py
- search_web
- create_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- section_generator_node
- extractJobData
- uiStore.js
- TaskTracker
- saveProfileField
- schemas/intake.py
- routers/agent_chat.py
- BaseModel
- handleOAuthSuccess
- WebOperationLimiter
- jt
- ApplicationModel
- formatRelativeDate
- schemas/applications.py
- PostHireModal.vue
- _execute_evaluation_steps
- PrioritySemaphore
- fuzzyMatch.js
- AsyncSession
- loadBindings
- selectItem
- get_task_chat_model
- services/analytics.py
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
- routers/analytics.py
- d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py
- demoStorage.js
- EmailAccountModel
- patch
- Request
- BaseModel
- field_validator
- fetchRoleAlignment
- asyncio
- load_settings
- e4f5a6b7c8d9_drop_candidate_cv_is_active.py
- f5a6b7c8d9e0_add_provider_token_cost_columns.py
- graph_nodes.py
- onTrackMouseDown
- schemas/extension.py
- AsyncSession
- ApplicationModel
- fixture
- BaseModel
- StrEnum
- PostgresTracer
- hybrid_property
- patch
- asyncio
- patch
- RunnableConfig
- programmatic_scrub_cv
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
- endpoints.js
- test_application_questions.py
- get_prompt_template
- loadPricingRates
- Connection
- AsyncSession
- get
- fixture
- FailoverChatModel
- LogActivityModal.vue
- ApplicationSummaryResult
- env.py
- schemas/companies.py
- scrollToBottom
- get_active_llm_config_dict
- normalize_job_url
- getCurrencySymbol
- interviewStore.js
- routers/intake.py
- closeSidebarOnMobile
- clearSelection
- BackgroundTasks
- get
- 1a2b3c4d5e6f_create_role_alignment_dossiers.py
- test_ai_config.py
- BaseModel
- AnalyticsOverviewResponse
- Response
- FunnelMetricsResponse
- RoleAlignmentResponse
- patch
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
- _encrypt_table_secrets
- test_persist_job_assessment_unrestricted_urls
- post
- useQueueStore
- BaseModel
- FastAPI
- asyncio
- JobAssessmentResult
- advanceAppStage
- set_ai_task_binding
- test_extension.py
- closeDrawer
- asyncio
- filteredCompanyApplications
- saveEditHeader
- delete
- get
- post

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

## Communities (245 total, 86 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (100): accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri, coverLetterLength (+92 more)

### Community 1 - "InterviewSimulatorService"
Cohesion: 0.10
Nodes (49): InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions(), next_question() (+41 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (62): ALL_SECTIONS, appStore, close(), companyResearch, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode (+54 more)

### Community 3 - "datetime"
Cohesion: 0.08
Nodes (40): ActionItemModel, ApplicationEmbeddingModel, Base, RoleAlignmentDossierModel, create_agent_tools(), execute_analyze_pipeline_metrics(), execute_detect_stalled_applications(), execute_evaluate_ai_fit_score() (+32 more)

### Community 4 - "OnboardingWizardModal.vue"
Cohesion: 0.03
Nodes (52): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+44 more)

### Community 5 - "ApplicationQuestionModal.vue"
Cohesion: 0.06
Nodes (38): activeCompanyResearchTask, activeQATask, addQuestion(), application, appStore, autoSaveStatus, bulkPasteText, companyResearch (+30 more)

### Community 6 - "ApplicationsView.vue"
Cohesion: 0.03
Nodes (41): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, archiveSortKey, archiveSortOrder (+33 more)

### Community 7 - "test_pricing_service.py"
Cohesion: 0.10
Nodes (34): Any, export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces() (+26 more)

### Community 8 - "routers/search.py"
Cohesion: 0.24
Nodes (10): generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, AsyncSession, get, Returns matching companies alongside total tracked application count., search_companies(), semantic_search(), CompanySearchResult (+2 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.04
Nodes (33): activeCancelTask, activeCount, activeFixJDTask, completedCount, expandedDossierDetails, expandedEmailDetails, expandedQADetails, failedCount (+25 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "persist_or_stage_job_assessment"
Cohesion: 0.08
Nodes (47): is_permissive_domain_match(), AsyncSession, Dedicated About Us URL discovery service. Inspects company homepage…, Checks if candidate_url belongs to the root_domain or its subdomains., Discovers the authentic 'About Us' page URL for a company domain. 1. Fetches…, resolve_company_about_url(), clean_company_name(), clean_domain() (+39 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (39): renderEmailBody(), appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, handleSidebarScroll() (+31 more)

### Community 14 - "scrape_job_url"
Cohesion: 0.10
Nodes (36): clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text…, Receives a job posting URL, scrapes page text (or uses pre-captured HTML), and… (+28 more)

### Community 15 - "seed_default_prompts"
Cohesion: 0.12
Nodes (24): clear_prompt_cache(), AsyncSession, Invalidates the in-memory prompt cache for a specific prompt or all prompts., Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), PromptModel, get_prompt(), list_prompts() (+16 more)

### Community 16 - "CompanyDetailDrawer.vue"
Cohesion: 0.05
Nodes (27): activeTab, allCompanies, applicationFilter, applicationFilters, appStore, company, filteredMergeCompanies, headerEditForm (+19 more)

### Community 17 - "test_candidate_profile.py"
Cohesion: 0.16
Nodes (16): anonymize_and_parse_cv(), De-identifies candidate resume: - Runs local programmatic regex pre-scrubber on…, compute_programmatic_skill_match(), _is_skill_matched(), _normalize_token(), Checks if a JD required skill matches any skill in the candidate's CV profile., Computes Job Requirement Coverage Ratio between candidate CV skills and the…, asyncio (+8 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.06
Nodes (35): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkDelete(), bulkMarkAsApplied(), bulkRestore() (+27 more)

### Community 20 - "routers/action_items.py"
Cohesion: 0.15
Nodes (27): compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks, delete (+19 more)

### Community 21 - "routers/email_accounts.py"
Cohesion: 0.14
Nodes (26): EmailFoldersResponse, get_account(), get_oauth_authorize_url(), get_oauth_config(), list_account_folders(), list_accounts(), MailFolderItem, oauth_callback() (+18 more)

### Community 22 - "AnalyticsView.vue"
Cohesion: 0.05
Nodes (33): activeTab, alignmentData, alignmentSubTab, analyticsData, analyticsStore, copiedItemKey, currentAlignmentKey, currentDossier (+25 more)

### Community 23 - "CandidateProfileView.vue"
Cohesion: 0.06
Nodes (26): CandidateProfileAPI, currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling (+18 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.07
Nodes (30): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+22 more)

### Community 25 - "asyncio"
Cohesion: 0.08
Nodes (35): asyncio, test_pipeline_funnel_active_and_dropped_unit(), AsyncSession, Ensure DELETE /api/v1/intake/assessments/{app_id} archives the application., Ensure GET /api/v1/intake/assessments retrieves applications in ASSESSMENT…, Archived assessment dossiers remain available independently of queue tasks., Clearing the queue removes completed worker rows without removing the dossier., Ensure ready assessments (status='ASSESSMENT') can be permanently deleted. (+27 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (25): EmailAccountsAPI, accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm (+17 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "resolve_or_create_company"
Cohesion: 0.09
Nodes (40): bulk_research_companies(), delete_company(), get_company(), get_potential_duplicates(), list_companies(), merge_companies(), AsyncSession, BackgroundTasks (+32 more)

### Community 29 - "post"
Cohesion: 0.07
Nodes (45): ApplicationAnalyzeSpecRequest, analyze_app_job_spec(), generate_app_cover_letter(), regenerate_app_cover_letter(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations() (+37 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "sync_email_account"
Cohesion: 0.21
Nodes (19): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, enable_email_intake_mock(), asyncio, AsyncSession (+11 more)

### Community 32 - "test_new_features.py"
Cohesion: 0.18
Nodes (16): GenerateInterviewGuideRequest, clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream(), ApplicationModel, AsyncSession, Async generator that executes `interview_guide_graph.astream(...)` and yields…, Coordinates candidate profile retrieval, job posting lookup, LangGraph… (+8 more)

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
Cohesion: 0.17
Nodes (26): Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., register_running_task(), unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification…, ExtractedJobSpec, JobAssessmentResult (+18 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.07
Nodes (19): appStore, fetchBadgeCounts(), getRouteTitle(), handleVisibilityChange(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount, pendingTasksCount (+11 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.06
Nodes (29): analysisData, application, compensationText, computedRatioText, computedScoreText, criticalRisks, emit, error (+21 more)

### Community 41 - "routers/candidate_profile.py"
Cohesion: 0.06
Nodes (49): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+41 more)

### Community 42 - "ApplicationEventModel"
Cohesion: 0.10
Nodes (35): ApplicationEventModel, StagingItemModel, EmailPayload, model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve, process_email_batch_sequential(), process_single_email_graph() (+27 more)

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
Nodes (28): JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., prune_terminal_state_node(), Any, Prunes transient multi-kilobyte string fields prior to checkpointer…, asyncio (+20 more)

### Community 47 - "test_skill_normalizer.py"
Cohesion: 0.17
Nodes (19): extract_skills_from_text(), hybrid_extract_skills(), normalize_skill(), normalize_skills_list(), Skill Canonicalization Engine. Provides multi-stage skill normalization,…, Helper to split compound skills unless protected., Normalizes an array of skills with compound splitting, removes duplicates…, Scans raw text using pre-compiled regex patterns to deterministically detect… (+11 more)

### Community 48 - "GmailOAuthAdapter"
Cohesion: 0.13
Nodes (16): fetch_account_folders(), Fetches list of available mail folders / labels from IMAP, Gmail API, or…, GmailOAuthAdapter, MicrosoftGraphAdapter, Any, datetime, Adapter for Google Gmail REST API with incremental history IDs., OAuth2 adapter for Microsoft Graph (Outlook / Microsoft 365). (+8 more)

### Community 50 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "routers/staging.py"
Cohesion: 0.10
Nodes (30): bulk_dismiss_staging_items(), clear_resolved_staging_items(), get_staging_item(), list_staging_items(), AsyncSession, Bulk dismisses specific staging items or all pending staging items matching…, Fetches full details for a single staged item., Purges PROCESSED staging items, optionally older than a given number of days. (+22 more)

### Community 53 - "LazyAsyncPostgresSaver"
Cohesion: 0.11
Nodes (12): AsyncPostgresSaver, check_db_connection(), ensure_db_schema(), LazyAsyncPostgresSaver, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, health_check(), lifespan() (+4 more)

### Community 54 - "archive_stale_applications"
Cohesion: 0.19
Nodes (18): AgentChatModel, archive_stale_applications(), delete_stale_agent_chats(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or…, Background worker that runs once every interval_seconds., staleness_archiver_worker() (+10 more)

### Community 55 - "services/llm.py"
Cohesion: 0.09
Nodes (33): ApplicationEmbeddingModel, execute_semantic_vector_search(), Performs semantic vector search across pgvector application embeddings, with…, assess_job_posting(), build_application_company_context(), calibrate_assessment_score_and_recommendation(), extract_email_info(), extract_job_spec() (+25 more)

### Community 56 - "routers/system_settings.py"
Cohesion: 0.19
Nodes (17): get_system_settings(), AsyncSession, get, patch, post, Validates connectivity to a search provider (such as SearXNG) before saving…, test_search_provider(), update_system_settings() (+9 more)

### Community 57 - "test_system_settings.py"
Cohesion: 0.53
Nodes (5): asyncio, test_email_intake_disabled_guard(), test_global_settings_backward_compatibility(), test_search_provider_settings_and_test_endpoint(), test_system_settings_get_and_patch()

### Community 58 - "trace_operation"
Cohesion: 0.24
Nodes (13): TraceEventModel, Any, AsyncSession, datetime, Persists a programmatic execution trace event into the trace_events table., Async context manager that measures execution time and records diagnostic…, record_diagnostic_event(), trace_operation() (+5 more)

### Community 59 - "decrypt_secret"
Cohesion: 0.23
Nodes (9): decrypt_secret(), encrypt_secret(), _get_fernet(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows., verify_admin_access(), hybrid_property, setter (+1 more)

### Community 60 - "routers/events.py"
Cohesion: 0.12
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "scheduleStudioAutoSave"
Cohesion: 0.15
Nodes (16): applyProbeRecommendations(), deleteProvider(), fetchStudioModels(), loadPrompts(), loadProviders(), onStudioProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt() (+8 more)

### Community 62 - "CompaniesView.vue"
Cohesion: 0.08
Nodes (27): bulkProgressActive, bulkProgressCompleted, bulkProgressFailed, bulkProgressTotal, bulkResearchMode, companies, companiesWithoutInfo, duplicateData (+19 more)

### Community 63 - "dock.js"
Cohesion: 0.23
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "CompanyLogo.vue"
Cohesion: 0.12
Nodes (15): attemptIndex, candidateDomains, fallbackInitial, faviconUrl, hasError, isLoaded, props, formatDate() (+7 more)

### Community 65 - "test_analytics.py"
Cohesion: 0.09
Nodes (29): db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info(), mock_job_email_payload(), postgres_container(), AsyncSession, pytest_collection_modifyitems() (+21 more)

### Community 66 - "2b3c4d5e6f7a_rename_poc_email_tables.py"
Cohesion: 0.60
Nodes (5): downgrade(), _index_exists(), rename poc email tables and indexes Revision ID: 2b3c4d5e6f7a Revises:…, _table_exists(), upgrade()

### Community 67 - "routers/llm.py"
Cohesion: 0.24
Nodes (15): mask_secret(), LLMConfigModel, get_current_llm_config(), LLMConfigRead, LLMConfigUpdate, Any, AsyncSession, BaseModel (+7 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 69 - "routers/ai_config.py"
Cohesion: 0.11
Nodes (38): AIHealthStatusRead, AIProviderCreate, AIProviderModel, AIProviderModelsResponse, AIProviderRead, AIProviderTestResponse, AIProviderUpdate, clear_embeddings_cache() (+30 more)

### Community 70 - "search_web"
Cohesion: 0.20
Nodes (16): AsyncSession, _query_searxng(), Resolves effective search provider and searxng_url from system settings., Executes synchronous DDGS text search in a dedicated thread to avoid blocking…, Asynchronously queries configured search provider (SearXNG or DDGS) and returns…, Asynchronously queries SearXNG JSON API endpoint with timeout., Validates SearXNG instance connectivity and JSON format availability., resolve_search_provider_settings() (+8 more)

### Community 71 - "create_account"
Cohesion: 0.24
Nodes (9): create_account(), post, Add a new email account configuration., EmailAccountBase, EmailAccountCreate, EmailAccountResponse, EmailAccountUpdate, BaseModel (+1 more)

### Community 72 - "System Architecture Documentation"
Cohesion: 0.15
Nodes (14): Camofox Stealth Scraper, Intake StateGraph, Interview Guide Graph, Mock Interview Simulator Service, pg_trgm GIN Trigram Matching, pgvector HNSW Cosine Indexing, Reasoning Suppression (0-effort), System Architecture Documentation (+6 more)

### Community 73 - "FloatingAgentChatWidget.vue"
Cohesion: 0.18
Nodes (11): chatMessagesContainer, chatStore, handleKeyDown(), handleSendMessage(), inputMessage, isOpen, route, router (+3 more)

### Community 74 - "loadEmailAccounts"
Cohesion: 0.15
Nodes (14): buildEmailAccountPayload(), confirmClearAccountHistory(), confirmClearAllHistory(), confirmDeleteAccount(), fetchEmailFolders(), handleOAuthSuccessMessage(), handleStep2NextIMAP(), loadEmailAccounts() (+6 more)

### Community 75 - "section_generator_node"
Cohesion: 0.16
Nodes (19): build_interview_guide_graph(), extractor_node(), InterviewGuideState, Any, Generates the clean semantic HTML for the current section in the queue., Routes back to section_generator_node if more sections remain and iteration…, Builds and compiles the LangGraph state machine for Interview Guide generation., Ensures company name and position are properly set. (+11 more)

### Community 76 - "extractJobData"
Cohesion: 0.22
Nodes (8): extractJobData(), deriveTitleFromDoc(), getText(), getTextIn(), queryFirst(), queryFirstIn(), isCleanTitle(), resolveCanonicalJobUrl()

### Community 77 - "uiStore.js"
Cohesion: 0.11
Nodes (18): AIConfigAPI, uiStore, uiStore, openCoverLetterModal(), activeCount, hasItems, queue, STAGES (+10 more)

### Community 79 - "saveProfileField"
Cohesion: 0.17
Nodes (12): addDomainArea(), addLanguage(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeDomainArea(), removeLanguage(), removeSkill() (+4 more)

### Community 80 - "schemas/intake.py"
Cohesion: 0.26
Nodes (13): AssessJobRequest, BulkTaskActionRequest, BulkTaskActionResult, ConfirmAssessmentRequest, DirectEmailIntakeRequest, EmailBatchIntakeRequest, EmailProcessingSummary, EnqueueAssessmentRequest (+5 more)

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
Cohesion: 0.09
Nodes (46): get_db(), AsyncSession, ApplicationModel, CompanyModel, JobPostingModel, CandidateCVModel, Accepts user fixes, applies them to DB records, and marks the staged item…, resolve_staging_item() (+38 more)

### Community 87 - "formatRelativeDate"
Cohesion: 0.28
Nodes (9): formatRelativeDate(), formatDueDateFriendly(), formatScheduledDate(), formatScheduledDateFriendly(), getDueDate(), getDueDateStr(), getScheduledInterviewDate(), getScheduleUrgencyClass() (+1 more)

### Community 88 - "schemas/applications.py"
Cohesion: 0.11
Nodes (23): ActionItemDetail, AllowedApplicationStatus, ApplicationDetailResponse, ApplicationEventDetail, ApplicationFilterParams, ApplicationListItem, ApplicationListResponse, ApplicationTransitionRequest (+15 more)

### Community 89 - "PostHireModal.vue"
Cohesion: 0.32
Nodes (7): actions, appStore, emit, handleConfirm(), handleDecideLater(), props, submitting

### Community 90 - "_execute_evaluation_steps"
Cohesion: 0.29
Nodes (16): get_setting(), Retrieves a specific system setting by key asynchronously., _execute_application_qa_steps(), _execute_company_research_steps(), _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps() (+8 more)

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
Cohesion: 0.22
Nodes (18): AITaskTestResponse, _clean_base_url(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model(), AsyncSession (+10 more)

### Community 97 - "services/analytics.py"
Cohesion: 0.12
Nodes (31): get_funnel_metrics(), AsyncSession, get, AnalyticsOverviewResponse, BulletReframeItem, FunnelChartStage, FunnelCohortPeriod, FunnelKpiCard (+23 more)

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
Nodes (26): OtherEventModel, delete_application(), delete_event(), get_staleness_stats(), AsyncSession, delete, get, post (+18 more)

### Community 114 - "test_ai_health.py"
Cohesion: 0.29
Nodes (15): AIProviderModel, AITaskBindingModel, SystemSettingsModel, invalidate_ai_health_cache(), asyncio, AsyncSession, fixture, reset_health_cache() (+7 more)

### Community 118 - "switchTab"
Cohesion: 0.40
Nodes (5): fetchAnalytics(), fetchFunnelMetrics(), handlePeriodChange(), switchTab(), toggleWorkModel()

### Community 135 - "routers/analytics.py"
Cohesion: 0.18
Nodes (16): enhance_role_alignment_endpoint(), get_funnel_metrics(), get_overview(), get_role_alignment_dossier_endpoint(), get_role_alignment_endpoint(), AsyncSession, get, Enqueues an asynchronous AI Strategic Dossier synthesis task through the shared… (+8 more)

### Community 136 - "d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 137 - "demoStorage.js"
Cohesion: 0.30
Nodes (10): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+2 more)

### Community 138 - "EmailAccountModel"
Cohesion: 0.29
Nodes (11): EmailAccountModel, _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using… (+3 more)

### Community 141 - "BaseModel"
Cohesion: 0.10
Nodes (34): AIHealthStatusRead, AIProviderCreate, AIProviderModelsResponse, AIProviderRead, AIProviderTestResponse, AIProviderUpdate, AITaskBindingCreate, AITaskBindingRead (+26 more)

### Community 144 - "fetchRoleAlignment"
Cohesion: 0.50
Nodes (4): fetchRoleAlignment(), handleSearchInput(), onTrackPillClick(), selectTrack()

### Community 146 - "load_settings"
Cohesion: 0.27
Nodes (12): get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Sets a specific system setting by key asynchronously., Loads system settings as a dictionary with both canonical lower-case and upper-… (+4 more)

### Community 147 - "e4f5a6b7c8d9_drop_candidate_cv_is_active.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 148 - "f5a6b7c8d9e0_add_provider_token_cost_columns.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 149 - "graph_nodes.py"
Cohesion: 0.25
Nodes (24): cover_letter_node(), db_commit_node(), extraction_node(), fuzzy_match_node(), _get_db(), is_email_already_processed(), normalize_and_dedupe_node(), _parse_email_date() (+16 more)

### Community 150 - "onTrackMouseDown"
Cohesion: 1.00
Nodes (3): onTrackMouseDown(), onTrackMouseMove(), onTrackMouseUp()

### Community 151 - "schemas/extension.py"
Cohesion: 0.60
Nodes (4): ClipJobRequest, ClipUrlRequest, ExtensionClipResponse, BaseModel

### Community 161 - "PostgresTracer"
Cohesion: 0.31
Nodes (6): AsyncBaseTracer, PostgresTracer, asyncio, test_postgres_tracer_background_persist_and_flush(), test_postgres_tracer_does_not_clear_global_run_map(), Run

### Community 165 - "patch"
Cohesion: 0.18
Nodes (10): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, test_secret_key_auto_generation_and_persistence(), test_secret_key_validation_in_non_dev_environments(), test_security_fernet_secret_key_validation() (+2 more)

### Community 167 - "programmatic_scrub_cv"
Cohesion: 0.47
Nodes (4): programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty()

### Community 171 - "AsyncSession"
Cohesion: 0.11
Nodes (31): AllowedApplicationStatus, ApplicationTransitionRequest, ApplicationUpdate, AsyncSession, bulk_transition_applications(), clear_app_interview_guide(), delete_application(), generate_app_interview_guide() (+23 more)

### Community 174 - "research_company_context"
Cohesion: 0.08
Nodes (42): build_company_research_queries(), build_company_research_query(), build_employer_signals_query(), build_ratings_query(), _collect_company_evidence(), compute_avg_rating(), _extract_json(), _fetch_selected_pages() (+34 more)

### Community 177 - "schemas/agent_tools.py"
Cohesion: 0.23
Nodes (15): AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, FetchWebpageContentInput, GetCandidateProfileInput, ListApplicationsInput, ManageActionItemsInput (+7 more)

### Community 182 - "endpoints.js"
Cohesion: 0.09
Nodes (24): ActionItemsAPI, AgentAPI, AnalyticsAPI, CompaniesAPI, EventsAPI, IntakeAPI, PromptsAPI, SearchAPI (+16 more)

### Community 183 - "test_application_questions.py"
Cohesion: 0.29
Nodes (9): ApplicationQuestionsUpdateRequest, generate_application_form_answers(), update_application_questions(), ApplicationQuestionItem, ApplicationQuestionsResponse, ApplicationQuestionsUpdateRequest, GenerateApplicationQuestionsRequest, test_application_questions_schemas() (+1 more)

### Community 184 - "get_prompt_template"
Cohesion: 0.24
Nodes (11): get_prompt_template(), Retrieves prompt template from DB with in-memory caching, falling back to…, enhance_role_alignment_dossier(), _extract_json_block(), get_role_alignment_dossier(), Any, AsyncSession, Retrieves the existing AI Strategic Dossier from PostgreSQL if generated, or… (+3 more)

### Community 187 - "AsyncSession"
Cohesion: 0.22
Nodes (11): clear_account_processed_emails(), clear_all_processed_emails(), delete_account(), AsyncSession, delete, patch, Deletes all email deduplication history records for a specific account and…, Update settings or credentials for an existing email account. (+3 more)

### Community 190 - "FailoverChatModel"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 191 - "LogActivityModal.vue"
Cohesion: 0.20
Nodes (10): appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction, submitLog() (+2 more)

### Community 193 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 194 - "schemas/companies.py"
Cohesion: 0.53
Nodes (5): CompanyApplicationItem, CompanyMergeRequest, CompanyRead, CompanyUpdate, BaseModel

### Community 195 - "scrollToBottom"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 196 - "get_active_llm_config_dict"
Cohesion: 0.36
Nodes (10): get_active_llm_config_dict(), Retrieves runtime LLM configuration from the database., asyncio, AsyncSession, test_extract_email_info_runnable(), test_extract_job_spec_runnable(), test_get_active_llm_config_db(), test_get_active_llm_config_fallback() (+2 more)

### Community 197 - "normalize_job_url"
Cohesion: 0.24
Nodes (10): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, AsyncSessionMock, asyncio, Unit test using mock AsyncSession to verify persist_or_stage_job_assessment…, test_normalize_job_url_edge_cases(), test_normalize_job_url_preserves_full_url(), test_normalize_job_url_preserves_job_identifiers() (+2 more)

### Community 198 - "getCurrencySymbol"
Cohesion: 0.50
Nodes (4): formatJobSpecCompensation(), getCurrencySymbol(), formatSalary(), getSalaryTooltip()

### Community 200 - "routers/intake.py"
Cohesion: 0.10
Nodes (27): AssessJobRequest, assess_job_lead(), confirm_job_assessment(), delete_evaluation_task(), dismiss_assessment(), ExtensionUrlDirectPayload, _format_graph_result(), get_extension_config() (+19 more)

### Community 201 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 202 - "clearSelection"
Cohesion: 0.50
Nodes (4): bulkDeleteSelected(), bulkRetrySelected(), clearSelection(), toggleSelectAll()

### Community 205 - "1a2b3c4d5e6f_create_role_alignment_dossiers.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_exists(), upgrade()

### Community 206 - "test_ai_config.py"
Cohesion: 0.36
Nodes (10): Strips <think>...</think> reasoning tags from LLM output text., strip_reasoning_tags(), asyncio, AsyncSession, test_ai_provider_crud_and_masking(), test_global_settings_db_backed(), test_pricing_rates_endpoints(), test_probe_model_capabilities() (+2 more)

### Community 227 - "_encrypt_table_secrets"
Cohesion: 0.50
Nodes (3): _encrypt_table_secrets(), upgrade(), Connection

### Community 228 - "test_persist_job_assessment_unrestricted_urls"
Cohesion: 0.50
Nodes (3): asyncio, Test that submitting the same job posting URL with different referral…, test_persist_job_assessment_unrestricted_urls()

### Community 232 - "FastAPI"
Cohesion: 0.25
Nodes (7): get_badge_counts(), AsyncSession, get, Returns aggregated counts for Navbar and drawer badges in a single optimized DB…, BadgeCountsResponse, BaseModel, FastAPI

### Community 235 - "advanceAppStage"
Cohesion: 0.38
Nodes (7): advanceAppStage(), executeTransition(), getNextStatus(), handleStatusChange(), onDrop(), openDeleteConfirm(), openTransitionModal()

### Community 236 - "set_ai_task_binding"
Cohesion: 0.31
Nodes (9): AITaskBindingCreate, AITaskBindingModel, AITaskBindingRead, list_ai_task_bindings(), set_ai_task_binding(), _to_binding_read(), update_pricing_rates_endpoint(), PricingRateBatchUpdate (+1 more)

### Community 237 - "test_extension.py"
Cohesion: 0.60
Nodes (5): asyncio, AsyncSession, test_extension_clip_job_direct(), test_extension_clip_url_pipeline(), test_extension_intake_url_and_jd_routes()

### Community 238 - "closeDrawer"
Cohesion: 0.33
Nodes (6): closeDrawer(), deleteCompany(), fetchCompany(), handleMerge(), loadAllCompaniesForMerge(), openApplication()

## Knowledge Gaps
- **827 isolated node(s):** `accountToClear`, `accountToDelete`, `activeTab`, `activeTaskDef`, `availableMailFolders` (+822 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **86 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `uiStore.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationQuestionModal.vue`, `ApplicationsView.vue`, `demoStorage.js`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `CompanyDetailDrawer.vue`, `AssessmentsView.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `endpoints.js`, `CompaniesView.vue`, `LogActivityModal.vue`, `InterviewReaderModal.vue`, `useQueueStore`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `InterviewSimulatorService`, `datetime`, `routers/search.py`, `persist_or_stage_job_assessment`, `scrape_job_url`, `routers/action_items.py`, `graph_nodes.py`, `asyncio`, `resolve_or_create_company`, `process_evaluation_task`, `ApplicationEventModel`, `ExtractedEmailInfo`, `archive_stale_applications`, `test_application_questions.py`, `test_analytics.py`, `routers/intake.py`, `services/analytics.py`, `test_extension.py`, `seed_development_dataset`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `CompanyModel` connect `ApplicationModel` to `test_analytics.py`, `InterviewSimulatorService`, `datetime`, `process_evaluation_task`, `routers/search.py`, `ApplicationEventModel`, `test_extension.py`, `seed_development_dataset`, `research_company_context`, `ExtractedEmailInfo`, `graph_nodes.py`, `archive_stale_applications`, `test_application_questions.py`, `asyncio`, `resolve_or_create_company`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 81 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `CompanyModel` (e.g. with `search_companies()` and `semantic_search()`) actually correct?**
  _`CompanyModel` has 79 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `useUIStore` (e.g. with `openCoverLetterModal()` and `openCompanyDrawer()`) actually correct?**
  _`useUIStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `accountToClear`, `accountToDelete`, `activeTab` to the rest of the system?**
  _827 weakly-connected nodes found - possible documentation gaps or missing edges._