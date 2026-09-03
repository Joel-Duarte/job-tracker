# Graph Report - job-tracker  (2026-09-03)

## Corpus Check
- 256 files · ~320,036 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3468 nodes · 6687 edges · 227 communities (157 shown, 70 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 715 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2629c55e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- InterviewSimulatorService
- ApplicationDetailDrawer.vue
- services/agent_tools.py
- OnboardingWizardModal.vue
- ApplicationQuestionModal.vue
- ApplicationsView.vue
- test_pricing_service.py
- graph_nodes.py
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- resolve_company_domain
- StagingView.vue
- scrape_job_url
- get_applications_by_status
- CompanyDetailDrawer.vue
- test_candidate_profile.py
- popup.js
- AssessmentsView.vue
- routers/action_items.py
- EmailAccountModel
- AnalyticsView.vue
- CandidateProfileView.vue
- JobIntakeView.vue
- search_web
- EmailAccountsSettings.vue
- FloatingQueueWidget.vue
- CompanyModel
- routers/intake.py
- manifest.json
- ProcessedEmailModel
- PostgresTracer
- ActionItemsView.vue
- CoverLetterModal.vue
- index.js
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
- schemas/applications.py
- load_settings
- fetch_emails_from_account
- datetime
- clean_html_text
- test_email_accounts.py
- bulk_dismiss_staging_items
- LazyAsyncPostgresSaver
- test_llm_factory.py
- research_company_context
- get_task_chat_model
- test_system_settings.py
- trace_operation
- uiStore.js
- routers/events.py
- scheduleStudioAutoSave
- CompaniesView.vue
- dock.js
- CompanyLogo.vue
- test_analytics.py
- 2b3c4d5e6f7a_rename_poc_email_tables.py
- routers/prompts.py
- InterviewReaderModal.vue
- routers/ai_config.py
- _execute_evaluation_steps
- update_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- clearSelection
- extractJobData
- demoStorage.js
- TaskTracker
- saveProfileField
- schemas/intake.py
- EmailPayload
- BaseModel
- handleOAuthSuccess
- WebOperationLimiter
- jt
- ApplicationModel
- formatRelativeDate
- Settings
- PostHireModal.vue
- advanceAppStage
- endpoints.js
- fuzzyMatch.js
- AsyncSession
- loadBindings
- fetchStagingItems
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
- test_list_assessments_from_persistent_applications
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
- decrypt_secret
- get_badge_counts
- patch
- Request
- test_schemas.py
- field_validator
- generate_cover_letter
- test_delete_assessment_task_archives_application
- archive_stale_applications
- e4f5a6b7c8d9_drop_candidate_cv_is_active.py
- f5a6b7c8d9e0_add_provider_token_cost_columns.py
- get_prompt_template
- LogActivityModal.vue
- schemas/extension.py
- routers/diagnostics.py
- test_bulk_transition.py
- fixture
- selectItem
- StrEnum
- Any
- hybrid_property
- patch
- asyncio
- routers/search.py
- RunnableConfig
- programmatic_scrub_cv
- UploadFile
- TypedDict
- RunnableConfig
- AsyncSession
- put
- setter
- get_application
- GlobalSettingsRead
- delete_evaluation_task
- switchTab
- setter
- BaseModel
- GlobalSettingsUpdate
- BaseModel
- test_application_transitions.py
- fetchActionItems
- enhance_role_alignment_dossier
- loadPricingRates
- Connection
- JobAssessmentResult
- IntakeEvaluationTaskResponse
- fixture
- close
- routers/agent_chat.py
- services/llm.py
- env.py
- schemas/companies.py
- scrollToBottom
- executeDirectTransition
- handleAnalyzeSpec
- getCurrencySymbol
- emailRenderer.js
- ApplicationEventModel
- closeSidebarOnMobile
- fetchRoleAlignment
- normalize_job_url
- onTrackMouseDown
- 1a2b3c4d5e6f_create_role_alignment_dossiers.py
- interviewStore.js
- handleSidebarScroll
- AnalyticsOverviewResponse
- Response
- FunnelMetricsResponse
- RoleAlignmentResponse
- bulk_transition_applications
- filteredInterviewSessions
- asyncio
- AsyncSession
- BackgroundTasks
- datetime
- delete
- get
- .normalize_work_model
- deleteTask
- formatLeadUrl
- patch
- post

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 115 edges
2. `CompanyModel` - 103 edges
3. `useUIStore` - 45 edges
4. `ApplicationEventModel` - 40 edges
5. `process_evaluation_task()` - 37 edges
6. `PostgresTracer` - 34 edges
7. `EmailAccountModel` - 34 edges
8. `EmailPayload` - 33 edges
9. `research_company_context()` - 32 edges
10. `get_task_chat_model()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Root Pre-Commit Configuration` --semantically_similar_to--> `Backend Pre-Commit Configuration`  [INFERRED] [semantically similar]
  .pre-commit-config.yaml → backend/.pre-commit-config.yaml
- `seed()` --uses--> `IntakeEvaluationTaskModel`  [INFERRED]
  seed_db.py → backend/app/models/intake_tasks.py
- `seed()` --uses--> `CompanyModel`  [INFERRED]
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

## Communities (227 total, 70 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (101): PromptsAPI, accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri (+93 more)

### Community 1 - "InterviewSimulatorService"
Cohesion: 0.10
Nodes (49): ApplicationModel, InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions() (+41 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (54): EventsAPI, ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData (+46 more)

### Community 3 - "services/agent_tools.py"
Cohesion: 0.09
Nodes (49): AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, FetchWebpageContentInput, GetCandidateProfileInput, ListApplicationsInput, ManageActionItemsInput (+41 more)

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
Cohesion: 0.08
Nodes (40): Any, build_interview_guide_graph(), extractor_node(), InterviewGuideState, Generates the clean semantic HTML for the current section in the queue., Routes back to section_generator_node if more sections remain and iteration…, Builds and compiles the LangGraph state machine for Interview Guide generation., Ensures company name and position are properly set. (+32 more)

### Community 8 - "graph_nodes.py"
Cohesion: 0.21
Nodes (27): cover_letter_node(), db_commit_node(), extraction_node(), fuzzy_match_node(), _get_db(), is_email_already_processed(), normalize_and_dedupe_node(), _parse_email_date() (+19 more)

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
Nodes (36): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+28 more)

### Community 14 - "scrape_job_url"
Cohesion: 0.10
Nodes (36): clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text…, Receives a job posting URL, scrapes page text (or uses pre-captured HTML), and… (+28 more)

### Community 15 - "get_applications_by_status"
Cohesion: 0.50
Nodes (4): AllowedApplicationStatus, get_applications_by_status(), Replicates the status search CTE query to fetch applications, event counts, and…, ApplicationByStatusResult

### Community 16 - "CompanyDetailDrawer.vue"
Cohesion: 0.05
Nodes (36): activeTab, allCompanies, applicationFilter, applicationFilters, appStore, closeDrawer(), company, deleteCompany() (+28 more)

### Community 17 - "test_candidate_profile.py"
Cohesion: 0.07
Nodes (49): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+41 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.06
Nodes (30): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkMarkAsApplied(), evaluationTasks, expandedTaskIds (+22 more)

### Community 20 - "routers/action_items.py"
Cohesion: 0.15
Nodes (27): compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks, delete (+19 more)

### Community 21 - "EmailAccountModel"
Cohesion: 0.10
Nodes (40): EmailAccountModel, clear_account_processed_emails(), clear_all_processed_emails(), create_account(), delete_account(), EmailFoldersResponse, fetch_account_folders(), get_account() (+32 more)

### Community 22 - "AnalyticsView.vue"
Cohesion: 0.05
Nodes (33): activeTab, alignmentData, alignmentSubTab, analyticsData, analyticsStore, copiedItemKey, currentAlignmentKey, currentDossier (+25 more)

### Community 23 - "CandidateProfileView.vue"
Cohesion: 0.06
Nodes (26): CandidateProfileAPI, currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling (+18 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.07
Nodes (30): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+22 more)

### Community 25 - "search_web"
Cohesion: 0.19
Nodes (16): fetch_webpage_content(), AsyncSession, _query_searxng(), Resolves effective search provider and searxng_url from system settings., Executes synchronous DDGS text search in a dedicated thread to avoid blocking…, Asynchronously queries configured search provider (SearXNG or DDGS) and returns…, Scrapes and cleans webpage markdown/text from a target URL using Camofox with…, Asynchronously queries SearXNG JSON API endpoint with timeout. (+8 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (25): EmailAccountsAPI, accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm (+17 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "CompanyModel"
Cohesion: 0.10
Nodes (41): CompanyModel, bulk_research_companies(), delete_company(), get_company(), get_potential_duplicates(), list_companies(), merge_companies(), AsyncSession (+33 more)

### Community 29 - "routers/intake.py"
Cohesion: 0.08
Nodes (47): AssessJobRequest, assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations(), confirm_job_assessment(), enqueue_job_assessment() (+39 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "ProcessedEmailModel"
Cohesion: 0.18
Nodes (21): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, BaseModel, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, TaskResponse, enable_email_intake_mock() (+13 more)

### Community 32 - "PostgresTracer"
Cohesion: 0.11
Nodes (22): AsyncBaseTracer, GenerateInterviewGuideRequest, process_single_email_graph(), AsyncSession, Executes the LangGraph StateGraph pipeline for a single email payload., clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream() (+14 more)

### Community 33 - "ActionItemsView.vue"
Cohesion: 0.08
Nodes (17): actionItems, activeUrgencyDropdown, applicationsList, currentEditId, displayedTasks, filterTab, isEditing, isLoading (+9 more)

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

### Community 41 - "test_skill_normalizer.py"
Cohesion: 0.17
Nodes (19): extract_skills_from_text(), hybrid_extract_skills(), normalize_skill(), normalize_skills_list(), Skill Canonicalization Engine. Provides multi-stage skill normalization,…, Helper to split compound skills unless protected., Normalizes an array of skills with compound splitting, removes duplicates…, Scans raw text using pre-compiled regex patterns to deterministically detect… (+11 more)

### Community 42 - "ExtractedEmailInfo"
Cohesion: 0.08
Nodes (51): StagingItemModel, JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve (+43 more)

### Community 43 - "DiagnosticsView.vue"
Cohesion: 0.08
Nodes (21): DiagnosticsAPI, activeCategory, categories, copied, currentView, loadData(), loading, loadingDetail (+13 more)

### Community 44 - "DateTimePicker.vue"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "JobIntakeModal.vue"
Cohesion: 0.09
Nodes (23): activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls(), handleBulkPromptDecision() (+15 more)

### Community 46 - "schemas/applications.py"
Cohesion: 0.18
Nodes (20): ApplicationQuestionsUpdateRequest, get_application_questions(), update_application_questions(), ActionItemDetail, ApplicationAnalyzeSpecRequest, ApplicationDetailResponse, ApplicationEventDetail, ApplicationFilterParams (+12 more)

### Community 47 - "load_settings"
Cohesion: 0.08
Nodes (47): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously. (+39 more)

### Community 48 - "fetch_emails_from_account"
Cohesion: 0.10
Nodes (24): _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using…, GmailOAuthAdapter (+16 more)

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
Cohesion: 0.25
Nodes (17): ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem, OptimizationGaps, ResumeTailoringStrategy, VocabularyTranslationItem, asyncio (+9 more)

### Community 55 - "research_company_context"
Cohesion: 0.11
Nodes (32): build_company_research_queries(), build_employer_signals_query(), build_ratings_query(), _collect_company_evidence(), compute_avg_rating(), _extract_json(), _fetch_selected_pages(), _invoke_llm() (+24 more)

### Community 56 - "get_task_chat_model"
Cohesion: 0.17
Nodes (22): AIProviderTestResponse, generate_query_embedding(), Generates a vector embedding for an incoming search query string using…, _clean_base_url(), get_active_llm_config_dict(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model() (+14 more)

### Community 57 - "test_system_settings.py"
Cohesion: 0.53
Nodes (5): asyncio, test_email_intake_disabled_guard(), test_global_settings_backward_compatibility(), test_search_provider_settings_and_test_endpoint(), test_system_settings_get_and_patch()

### Community 58 - "trace_operation"
Cohesion: 0.25
Nodes (12): Any, AsyncSession, datetime, Persists a programmatic execution trace event into the trace_events table., Async context manager that measures execution time and records diagnostic…, record_diagnostic_event(), trace_operation(), asyncio (+4 more)

### Community 59 - "uiStore.js"
Cohesion: 0.12
Nodes (17): AIConfigAPI, uiStore, uiStore, activeCount, hasItems, queue, STAGES, uiStore (+9 more)

### Community 60 - "routers/events.py"
Cohesion: 0.12
Nodes (21): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), move_event_to_staging(), AsyncSession, delete, get (+13 more)

### Community 61 - "scheduleStudioAutoSave"
Cohesion: 0.15
Nodes (16): applyProbeRecommendations(), deleteProvider(), fetchStudioModels(), loadPrompts(), loadProviders(), onStudioProviderChange(), resetGlobalDefaultToDefaults(), resetStudioPrompt() (+8 more)

### Community 62 - "CompaniesView.vue"
Cohesion: 0.08
Nodes (28): bulkProgressActive, bulkProgressCompleted, bulkProgressFailed, bulkProgressTotal, bulkResearchMode, companies, companiesWithoutInfo, computeAvgRating() (+20 more)

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

### Community 67 - "routers/prompts.py"
Cohesion: 0.18
Nodes (17): verify_admin_access(), PromptModel, get_prompt(), list_prompts(), AsyncSession, get, patch, post (+9 more)

### Community 68 - "InterviewReaderModal.vue"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 69 - "routers/ai_config.py"
Cohesion: 0.09
Nodes (46): AIHealthStatusRead, AIProviderCreate, AIProviderModel, AIProviderModelsResponse, AIProviderRead, AIProviderUpdate, AITaskBindingCreate, AITaskBindingModel (+38 more)

### Community 70 - "_execute_evaluation_steps"
Cohesion: 0.29
Nodes (15): _execute_application_qa_steps(), _execute_company_research_steps(), _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), _execute_role_alignment_dossier_steps(), get_company_research_semaphore() (+7 more)

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

### Community 77 - "demoStorage.js"
Cohesion: 0.29
Nodes (10): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+2 more)

### Community 79 - "saveProfileField"
Cohesion: 0.17
Nodes (12): addDomainArea(), addLanguage(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeDomainArea(), removeLanguage(), removeSkill() (+4 more)

### Community 80 - "schemas/intake.py"
Cohesion: 0.26
Nodes (13): AssessJobRequest, BulkTaskActionRequest, BulkTaskActionResult, ConfirmAssessmentRequest, DirectEmailIntakeRequest, EmailBatchIntakeRequest, EmailProcessingSummary, EnqueueAssessmentRequest (+5 more)

### Community 81 - "EmailPayload"
Cohesion: 0.16
Nodes (19): EmailPayload, _extract_ics_summary(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload., Parses plaintext / raw thread text into EmailPayload. (+11 more)

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
Nodes (32): asyncio, get_db(), AsyncSession, ApplicationModel, CandidateCVModel, asyncio, test_action_items_crud_and_filtering(), test_get_analytics_overview_unit() (+24 more)

### Community 87 - "formatRelativeDate"
Cohesion: 0.28
Nodes (9): formatRelativeDate(), formatDueDateFriendly(), formatScheduledDate(), formatScheduledDateFriendly(), getDueDate(), getDueDateStr(), getScheduledInterviewDate(), getScheduleUrgencyClass() (+1 more)

### Community 88 - "Settings"
Cohesion: 0.18
Nodes (9): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, test_secret_key_auto_generation_and_persistence(), test_secret_key_validation_in_non_dev_environments(), test_security_fernet_secret_key_validation() (+1 more)

### Community 89 - "PostHireModal.vue"
Cohesion: 0.32
Nodes (7): actions, appStore, emit, handleConfirm(), handleDecideLater(), props, submitting

### Community 90 - "advanceAppStage"
Cohesion: 0.38
Nodes (7): advanceAppStage(), executeTransition(), getNextStatus(), handleStatusChange(), onDrop(), openDeleteConfirm(), openTransitionModal()

### Community 91 - "endpoints.js"
Cohesion: 0.10
Nodes (23): ActionItemsAPI, AgentAPI, AnalyticsAPI, CompaniesAPI, IntakeAPI, SearchAPI, StagingAPI, SystemAPI (+15 more)

### Community 92 - "fuzzyMatch.js"
Cohesion: 0.48
Nodes (6): fuzzyFilterApplications(), fuzzyScore(), levenshteinDistance(), scoreApplicationMatch(), stringSimilarity(), filteredExistingApps

### Community 94 - "loadBindings"
Cohesion: 0.16
Nodes (14): applyEmbeddingPreset(), fetchEmbeddingModels(), fetchGlobalModels(), loadBindings(), onEmbeddingProviderChange(), onGlobalProviderChange(), saveEmbeddingBinding(), saveGlobalDefault() (+6 more)

### Community 95 - "fetchStagingItems"
Cohesion: 0.22
Nodes (9): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), handleReopenStagingItem(), handleVisibilityChange(), quickDismissItem() (+1 more)

### Community 96 - "routers/llm.py"
Cohesion: 0.24
Nodes (15): mask_secret(), LLMConfigModel, get_current_llm_config(), LLMConfigRead, LLMConfigUpdate, Any, AsyncSession, BaseModel (+7 more)

### Community 97 - "BaseModel"
Cohesion: 0.06
Nodes (71): enhance_role_alignment_endpoint(), get_funnel_metrics(), get_overview(), get_role_alignment_dossier_endpoint(), get_role_alignment_endpoint(), AsyncSession, get, Enqueues an asynchronous AI Strategic Dossier synthesis task through the shared… (+63 more)

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
Cohesion: 0.24
Nodes (12): build_dossier(), build_structured_spec(), is_database_empty(), maybe_seed_dev_data(), AsyncSession, Checks if development seeding is enabled and database is empty. If both…, Checks if the database has zero applications and companies., Populates a rich, 90-day rolling development test dataset following `guide.md`… (+4 more)

### Community 114 - "test_ai_health.py"
Cohesion: 0.33
Nodes (14): AIProviderModel, AITaskBindingModel, invalidate_ai_health_cache(), asyncio, AsyncSession, fixture, reset_health_cache(), test_ai_health_cache_ttl_and_invalidation() (+6 more)

### Community 116 - "test_list_assessments_from_persistent_applications"
Cohesion: 0.26
Nodes (12): asyncio, AsyncSession, Ensure DELETE /api/v1/intake/assessments/{app_id} archives the application., Ensure GET /api/v1/intake/assessments retrieves applications in ASSESSMENT…, Archived assessment dossiers remain available independently of queue tasks., Clearing the queue removes completed worker rows without removing the dossier., Ensure clearing completed evaluation tasks never removes persistent assessments., test_archived_assessment_remains_listed() (+4 more)

### Community 118 - "PrioritySemaphore"
Cohesion: 0.16
Nodes (8): cancel_running_task(), get_running_task_ids(), PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs., Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 135 - "FailoverChatModel"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 136 - "d3e4f5a6b7c8_add_candidate_cv_spoken_languages.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 137 - "decrypt_secret"
Cohesion: 0.17
Nodes (11): _encrypt_table_secrets(), upgrade(), decrypt_secret(), encrypt_secret(), _get_fernet(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows., hybrid_property (+3 more)

### Community 138 - "get_badge_counts"
Cohesion: 0.29
Nodes (6): get_badge_counts(), AsyncSession, get, Returns aggregated counts for Navbar and drawer badges in a single optimized DB…, BadgeCountsResponse, BaseModel

### Community 141 - "test_schemas.py"
Cohesion: 0.21
Nodes (13): AllowedApplicationStatus, ApplicationTransitionRequest, ApplicationUpdate, BulkTransitionRequest, BulkTransitionResult, Any, test_application_transition_request_date_coercion(), test_application_update_job_spec_fields() (+5 more)

### Community 144 - "generate_cover_letter"
Cohesion: 0.21
Nodes (14): build_company_research_query(), Constructs a multi-factor DuckDuckGo search query anchored with domain and…, build_application_company_context(), generate_cover_letter(), Selects a small, application-safe subset of company research., Generates a tailored cover letter using the COVER_LETTER task type and…, asyncio, test_build_application_company_context_filters_low_value_research() (+6 more)

### Community 145 - "test_delete_assessment_task_archives_application"
Cohesion: 0.38
Nodes (6): asyncio, AsyncSession, Ensure clear-completed deletes worker tasks but strictly preserves…, Ensure deleting a job assessment task transitions linked assessment application…, test_clear_completed_preserves_job_assessment(), test_delete_assessment_task_archives_application()

### Community 146 - "archive_stale_applications"
Cohesion: 0.26
Nodes (14): archive_stale_applications(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or…, async_client(), AsyncClient, asyncio, AsyncSession (+6 more)

### Community 147 - "e4f5a6b7c8d9_drop_candidate_cv_is_active.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 148 - "f5a6b7c8d9e0_add_provider_token_cost_columns.py"
Cohesion: 0.83
Nodes (3): _column_exists(), downgrade(), upgrade()

### Community 149 - "get_prompt_template"
Cohesion: 0.21
Nodes (12): clear_prompt_cache(), get_prompt_template(), AsyncSession, Invalidates the in-memory prompt cache for a specific prompt or all prompts., Seeds missing prompts into DB upon boot without overwriting existing user…, Retrieves prompt template from DB with in-memory caching, falling back to…, seed_default_prompts(), asyncio (+4 more)

### Community 150 - "LogActivityModal.vue"
Cohesion: 0.20
Nodes (10): appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction, submitLog() (+2 more)

### Community 151 - "schemas/extension.py"
Cohesion: 0.60
Nodes (4): ClipJobRequest, ClipUrlRequest, ExtensionClipResponse, BaseModel

### Community 152 - "routers/diagnostics.py"
Cohesion: 0.28
Nodes (12): export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces(), AsyncSession (+4 more)

### Community 153 - "test_bulk_transition.py"
Cohesion: 0.42
Nodes (10): async_client(), AsyncClient, asyncio, AsyncSession, fixture, test_bulk_transition_archives_open_applications(), test_bulk_transition_creates_timeline_events(), test_bulk_transition_dismisses_pending_action_items_on_terminal() (+2 more)

### Community 155 - "selectItem"
Cohesion: 0.24
Nodes (11): filteredAndSortedItems, formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType(), getItemCompany(), getItemPosition(), handleKeyDown(), selectItem() (+3 more)

### Community 165 - "routers/search.py"
Cohesion: 0.33
Nodes (8): AsyncSession, get, Returns matching companies alongside total tracked application count., search_companies(), semantic_search(), CompanySearchResult, BaseModel, SemanticSearchResult

### Community 167 - "programmatic_scrub_cv"
Cohesion: 0.47
Nodes (4): programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty()

### Community 171 - "AsyncSession"
Cohesion: 0.15
Nodes (27): ApplicationAnalyzeSpecRequest, ApplicationTransitionRequest, ApplicationUpdate, AsyncSession, analyze_app_job_spec(), clear_app_interview_guide(), delete_application(), generate_app_cover_letter() (+19 more)

### Community 174 - "get_application"
Cohesion: 0.53
Nodes (6): get_application(), list_applications(), _to_utc(), CompanySummary, EventSummary, get

### Community 176 - "delete_evaluation_task"
Cohesion: 0.29
Nodes (7): delete_evaluation_task(), dismiss_assessment(), permanently_delete_assessment(), delete, Archives an assessment dossier while keeping it available in Assessments., Permanently deletes an archived assessment and its related application data., Cancels an ongoing evaluation or dismisses a completed/failed evaluation task.

### Community 177 - "switchTab"
Cohesion: 0.40
Nodes (5): fetchAnalytics(), fetchFunnelMetrics(), handlePeriodChange(), switchTab(), toggleWorkModel()

### Community 182 - "test_application_transitions.py"
Cohesion: 0.57
Nodes (6): asyncio, AsyncSession, test_activity_logging_preserves_task_completion(), test_application_patch_updates(), test_application_transitions_and_deletion(), test_system_badges_cache_invalidation_fields()

### Community 183 - "fetchActionItems"
Cohesion: 0.33
Nodes (6): deleteTask(), fetchActionItems(), handleSaveTask(), selectMetricTab(), setManualUrgency(), toggleTaskStatus()

### Community 184 - "enhance_role_alignment_dossier"
Cohesion: 0.29
Nodes (9): enhance_role_alignment_dossier(), _extract_json_block(), get_role_alignment_dossier(), Any, AsyncSession, Retrieves the existing AI Strategic Dossier from PostgreSQL if generated, or…, Synthesizes a fresh AI Strategic Dossier using LLM task binding and PostgreSQL…, Robustly extracts JSON object from LLM output. (+1 more)

### Community 188 - "IntakeEvaluationTaskResponse"
Cohesion: 0.18
Nodes (13): get_evaluation_task(), get_extension_config(), get_task_status(), list_assessments(), list_evaluation_tasks(), get, Retrieves all pending job assessments directly from persistent applications…, Retrieves all queued, processing, and recent evaluation tasks from PostgreSQL. (+5 more)

### Community 191 - "routers/agent_chat.py"
Cohesion: 0.15
Nodes (19): AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage, delete_chat(), get_chat(), list_chats() (+11 more)

### Community 192 - "services/llm.py"
Cohesion: 0.13
Nodes (23): ApplicationSummaryResult, assess_job_posting(), extract_job_spec(), generate_application_answers(), generate_embedding(), get_active_llm_config(), Any, AsyncSession (+15 more)

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

### Community 200 - "ApplicationEventModel"
Cohesion: 0.07
Nodes (38): ApplicationEmbeddingModel, lifespan(), AgentChatModel, ActionItemModel, ApplicationEmbeddingModel, ApplicationEventModel, Base, JobPostingModel (+30 more)

### Community 201 - "closeSidebarOnMobile"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 202 - "fetchRoleAlignment"
Cohesion: 0.50
Nodes (4): fetchRoleAlignment(), handleSearchInput(), onTrackPillClick(), selectTrack()

### Community 203 - "normalize_job_url"
Cohesion: 0.12
Nodes (19): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, persist_or_stage_job_assessment(), Any, AsyncSession, JobAssessmentResult, Persists an AI job assessment to the database. If target_application_id is…, resolve_job_currency() (+11 more)

### Community 204 - "onTrackMouseDown"
Cohesion: 1.00
Nodes (3): onTrackMouseDown(), onTrackMouseMove(), onTrackMouseUp()

### Community 205 - "1a2b3c4d5e6f_create_role_alignment_dossiers.py"
Cohesion: 0.83
Nodes (3): downgrade(), _table_exists(), upgrade()

### Community 213 - "bulk_transition_applications"
Cohesion: 0.50
Nodes (4): bulk_transition_applications(), Transitions all applications whose status is in payload.from_statuses to…, BulkTransitionRequest, BulkTransitionResult

## Knowledge Gaps
- **822 isolated node(s):** `uiStore`, `appStore`, `queueStore`, `{ isAppQuestionsModalOpen, appQuestionsAppId }`, `application` (+817 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **70 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `useUIStore` connect `uiStore.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationQuestionModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `CompanyDetailDrawer.vue`, `AssessmentsView.vue`, `LogActivityModal.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `CompaniesView.vue`, `InterviewReaderModal.vue`, `demoStorage.js`, `endpoints.js`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `ApplicationModel` connect `ApplicationModel` to `InterviewSimulatorService`, `services/agent_tools.py`, `graph_nodes.py`, `scrape_job_url`, `test_delete_assessment_task_archives_application`, `archive_stale_applications`, `routers/action_items.py`, `test_bulk_transition.py`, `CompanyModel`, `routers/intake.py`, `PostgresTracer`, `routers/search.py`, `process_evaluation_task`, `ExtractedEmailInfo`, `load_settings`, `test_application_transitions.py`, `test_analytics.py`, `ApplicationEventModel`, `normalize_job_url`, `seed_development_dataset`, `test_list_assessments_from_persistent_applications`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `CompanyModel` connect `CompanyModel` to `test_analytics.py`, `InterviewSimulatorService`, `services/agent_tools.py`, `routers/search.py`, `process_evaluation_task`, `ApplicationEventModel`, `graph_nodes.py`, `ExtractedEmailInfo`, `normalize_job_url`, `seed_development_dataset`, `load_settings`, `generate_cover_letter`, `test_delete_assessment_task_archives_application`, `archive_stale_applications`, `test_list_assessments_from_persistent_applications`, `ApplicationModel`, `test_application_transitions.py`, `test_bulk_transition.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 87 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 87 INFERRED edges - model-reasoned connections that need verification._
- **Are the 81 inferred relationships involving `CompanyModel` (e.g. with `search_companies()` and `semantic_search()`) actually correct?**
  _`CompanyModel` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `useUIStore` (e.g. with `openCoverLetterModal()` and `openCompanyDrawer()`) actually correct?**
  _`useUIStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 20 INFERRED edges - model-reasoned connections that need verification._