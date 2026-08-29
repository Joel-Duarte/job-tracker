# Graph Report - job-tracker  (2026-08-29)

## Corpus Check
- 222 files · ~263,782 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2852 nodes · 5709 edges · 176 communities (115 shown, 61 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 679 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `012efc7b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SettingsView.vue
- PostgresTracer
- ApplicationDetailDrawer.vue
- services/agent_tools.py
- OnboardingWizardModal.vue
- schemas/analytics.py
- ApplicationsView.vue
- routers/applications.py
- EmailPayload
- AgentChatView.vue
- QueueView.vue
- Job Tracker Platform (README)
- Base
- StagingView.vue
- trace_operation
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
- PrioritySemaphore
- EmailAccountsSettings.vue
- FloatingQueueWidget.vue
- get_task_chat_model
- routers/intake.py
- manifest.json
- ProcessedEmailModel
- process_email_batch_sequential
- ActionItemsView.vue
- CoverLetterModal.vue
- uiStore.js
- dependencies
- ExtractedEmailInfo
- AppNavbar.vue
- IngestModal.vue
- MatchAnalysisModal.vue
- update_prompt
- test_analytics.py
- DiagnosticsView.vue
- DateTimePicker.vue
- JobIntakeModal.vue
- CompanyModel
- IntakeEvaluationTaskModel
- fetch_emails_from_account
- test_new_features.py
- BackgroundTasks
- test_email_accounts.py
- FailoverChatModel
- routers/llm.py
- JobAssessmentResult
- ApplicationModel
- routers/staging.py
- fetchActionItems
- conftest.py
- routers/agent_chat.py
- AsyncSession
- endpoints.js
- LogActivityModal.vue
- dock.js
- CompanyLogo.vue
- admin.py
- routers/extension.py
- test_candidate_profile.py
- InterviewReaderModal.vue
- AsyncSession
- delete
- create_account
- System Architecture Documentation
- FloatingAgentChatWidget.vue
- loadEmailAccounts
- test_ai_config.py
- extractJobData
- index.js
- TaskTracker
- saveProfileField
- BackgroundTasks
- get
- process_evaluation_task
- handleOAuthSuccess
- selectItem
- jt script
- scrollToBottom
- formatRelativeDate
- resolve_company_domain
- PostHireModal.vue
- advanceAppStage
- scheduleStudioAutoSave
- fuzzyMatch.js
- syncStudioForm
- loadBindings
- fetchStagingItems
- datetime
- post
- delete
- get
- closeSidebarOnMobile
- GenerateInterviewGuideRequest
- cleanCVText
- pollTaskUntilComplete
- openAddEmailAccountModal
- skill_taxonomy.py
- normalize_job_url
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
- UploadFile
- test_schemas.py
- ApplicationSummaryResult
- patch
- Request
- patch
- post
- field_validator
- asyncio
- asyncio
- services/llm.py
- EmailExtractionResult
- ExtractedJobSpec
- close
- LazyAsyncPostgresSaver
- Any
- executeDirectTransition
- clean_html_text
- BaseModel
- StrEnum
- env.py
- BaseModel
- schemas/intake.py
- Any
- Any
- interviewStore.js
- patch
- asyncio
- datetime
- RunnableConfig
- anonymize_and_parse_cv
- EmailAccountModel
- TypedDict
- RunnableConfig
- setter
- AsyncSession
- delete
- get
- post

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 99 edges
2. `CompanyModel` - 78 edges
3. `ApplicationEventModel` - 42 edges
4. `EmailAccountModel` - 39 edges
5. `useUIStore` - 38 edges
6. `PostgresTracer` - 36 edges
7. `EmailPayload` - 35 edges
8. `Base` - 34 edges
9. `AIProviderModel` - 34 edges
10. `InterviewSimulatorService` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Root Pre-Commit Configuration` --semantically_similar_to--> `Backend Pre-Commit Configuration`  [INFERRED] [semantically similar]
  .pre-commit-config.yaml → backend/.pre-commit-config.yaml
- `seed()` --uses--> `CompanyModel`  [INFERRED]
  seed_db.py → backend/app/models/applications.py
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

## Communities (176 total, 61 thin omitted)

### Community 0 - "SettingsView.vue"
Cohesion: 0.02
Nodes (70): accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri, coverLetterLength (+62 more)

### Community 1 - "PostgresTracer"
Cohesion: 0.08
Nodes (52): AsyncBaseTracer, InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions() (+44 more)

### Community 2 - "ApplicationDetailDrawer.vue"
Cohesion: 0.02
Nodes (46): ALL_SECTIONS, appStore, compEditForm, deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, hasJobSpecData, headerEditForm (+38 more)

### Community 3 - "services/agent_tools.py"
Cohesion: 0.11
Nodes (42): AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, ListApplicationsInput, ManageActionItemsInput, ManageIntakeQueueInput, BaseModel (+34 more)

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
Cohesion: 0.15
Nodes (37): AsyncSession, bulk_transition_applications(), clear_app_interview_guide(), generate_app_cover_letter(), generate_app_interview_guide(), get_application(), get_applications_by_status(), get_cover_letter() (+29 more)

### Community 8 - "EmailPayload"
Cohesion: 0.11
Nodes (26): EmailPayload, _extract_ics_summary(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload., Parses plaintext / raw thread text into EmailPayload. (+18 more)

### Community 9 - "AgentChatView.vue"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "QueueView.vue"
Cohesion: 0.05
Nodes (37): activeCancelTask, activeCount, activeFixJDTask, bulkDeleteSelected(), bulkRetrySelected(), clearSelection(), completedCount, deleteTask() (+29 more)

### Community 11 - "Job Tracker Platform (README)"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "Base"
Cohesion: 0.12
Nodes (28): AgentChatModel, ActionItemModel, ApplicationEmbeddingModel, Base, JobPostingModel, OtherEventModel, CandidateCVModel, TraceEventModel (+20 more)

### Community 13 - "StagingView.vue"
Cohesion: 0.04
Nodes (36): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+28 more)

### Community 14 - "trace_operation"
Cohesion: 0.10
Nodes (37): clean_extracted_text(), has_job_content_keywords(), BaseModel, Validates URL protocol and private IP / loopback address validation (SSRF…, Blazing fast multi-language scraper keyword validation using Python set hash…, Backward-compatible alias for validate_job_content., Normalizes whitespace and strips javascript code blocks, jQuery artifacts, and…, Scrapes a URL using the running Camofox browser automation server. (+29 more)

### Community 15 - "routers/ai_config.py"
Cohesion: 0.06
Nodes (84): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously. (+76 more)

### Community 16 - "main.py"
Cohesion: 0.07
Nodes (38): check_db_connection(), ensure_db_schema(), get_db(), AsyncSession, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, generate_query_embedding(), Generates a vector embedding for an incoming search query string using… (+30 more)

### Community 17 - "routers/candidate_profile.py"
Cohesion: 0.10
Nodes (29): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+21 more)

### Community 18 - "popup.js"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AssessmentsView.vue"
Cohesion: 0.05
Nodes (29): scores, getFitScores(), activeQueueTasks, activeTab, allCompletedTasks, appStore, averageFitScore, bulkArchive() (+21 more)

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
Nodes (26): currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling, isDeleting (+18 more)

### Community 24 - "JobIntakeView.vue"
Cohesion: 0.06
Nodes (27): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+19 more)

### Community 25 - "PrioritySemaphore"
Cohesion: 0.13
Nodes (11): cancel_running_task(), get_running_task_ids(), PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Registers an in-memory running asyncio Task by database task ID., Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs. (+3 more)

### Community 26 - "EmailAccountsSettings.vue"
Cohesion: 0.08
Nodes (24): accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm, emit (+16 more)

### Community 27 - "FloatingQueueWidget.vue"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "get_task_chat_model"
Cohesion: 0.18
Nodes (25): _clean_base_url(), get_active_llm_config_dict(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model(), AsyncSession (+17 more)

### Community 29 - "routers/intake.py"
Cohesion: 0.07
Nodes (51): AssessJobRequest, assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations(), delete_evaluation_task(), enqueue_job_assessment() (+43 more)

### Community 30 - "manifest.json"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "ProcessedEmailModel"
Cohesion: 0.18
Nodes (21): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, BaseModel, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, TaskResponse, enable_email_intake_mock() (+13 more)

### Community 32 - "process_email_batch_sequential"
Cohesion: 0.14
Nodes (19): model_validator, Payload for user manual resolution/override of a staged email or job lead., StagingItemResolve, process_email_batch_sequential(), process_single_email_graph(), AsyncSession, Executes the LangGraph StateGraph pipeline for a single email payload., Sequentially routes emails through the compiled LangGraph pipeline. (+11 more)

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
Cohesion: 0.17
Nodes (28): JobTrackerState, TypedDict, ExtractedEmailInfo, Structured extraction format returned by the LLM service., prune_terminal_state_node(), Any, Prunes transient multi-kilobyte string fields prior to checkpointer…, asyncio (+20 more)

### Community 38 - "AppNavbar.vue"
Cohesion: 0.08
Nodes (16): getRouteTitle(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount, pendingTasksCount, pillLabel, pillTitle, popoverContainerRef (+8 more)

### Community 39 - "IngestModal.vue"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "MatchAnalysisModal.vue"
Cohesion: 0.08
Nodes (22): analysisData, application, compensationText, computedRatioText, computedScoreText, emit, error, gapMitigationText (+14 more)

### Community 41 - "update_prompt"
Cohesion: 0.16
Nodes (15): get_prompt(), list_prompts(), AsyncSession, get, patch, post, List all available system prompts., Fetch a specific prompt template by name ('extraction' or 'summarization'). (+7 more)

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
Cohesion: 0.08
Nodes (26): IntakeAPI, activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls() (+18 more)

### Community 46 - "CompanyModel"
Cohesion: 0.09
Nodes (38): asyncio, ApplicationEventModel, CompanyModel, confirm_job_assessment(), Commits an assessed job lead to the application pipeline in ASSESSMENT or…, Accepts user fixes, applies them to DB records, and marks the staged item…, resolve_staging_item(), test_get_analytics_overview_unit() (+30 more)

### Community 47 - "IntakeEvaluationTaskModel"
Cohesion: 0.28
Nodes (14): Removes a finished or cancelled task from the in-memory registry., unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification…, asyncio, AsyncSession, test_bulk_retry_and_delete_evaluation_tasks(), test_cancel_evaluation_task() (+6 more)

### Community 48 - "fetch_emails_from_account"
Cohesion: 0.12
Nodes (21): _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject)., Synchronous worker that performs actual IMAP connection and retrieval using…, GmailOAuthAdapter (+13 more)

### Community 49 - "test_new_features.py"
Cohesion: 0.11
Nodes (21): clear_prompt_cache(), AsyncSession, Invalidates the in-memory prompt cache for a specific prompt or all prompts., Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), prune_and_sanitize_tool_output(), Any, Sanitizes and prunes tool execution output payloads: - Parses string payloads… (+13 more)

### Community 51 - "test_email_accounts.py"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "FailoverChatModel"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 53 - "routers/llm.py"
Cohesion: 0.10
Nodes (27): _encrypt_table_secrets(), Connection, upgrade(), decrypt_secret(), encrypt_secret(), _get_fernet(), mask_secret(), Encrypt a sensitive value, preserving already encrypted values. (+19 more)

### Community 54 - "JobAssessmentResult"
Cohesion: 0.14
Nodes (23): ExtractedJobSpec, HardMatches, ImpactReframingItem, JobAssessmentResult, LanguageMatchResult, OptimizationGaps, Any, BaseModel (+15 more)

### Community 55 - "ApplicationModel"
Cohesion: 0.18
Nodes (20): ApplicationModel, clear_interview_guide(), Clears the existing interview guide for an application., archive_stale_applications(), delete_stale_agent_chats(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or… (+12 more)

### Community 56 - "routers/staging.py"
Cohesion: 0.09
Nodes (31): delete_application(), Permanently deletes an application and its associated events, postings, and…, bulk_dismiss_staging_items(), clear_resolved_staging_items(), get_staging_item(), list_staging_items(), Bulk dismisses specific staging items or all pending staging items matching…, Fetches full details for a single staged item. (+23 more)

### Community 57 - "fetchActionItems"
Cohesion: 0.33
Nodes (6): deleteTask(), fetchActionItems(), handleSaveTask(), selectMetricTab(), setManualUrgency(), toggleTaskStatus()

### Community 58 - "conftest.py"
Cohesion: 0.12
Nodes (18): db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info(), mock_job_email_payload(), postgres_container(), AsyncSession, fixture (+10 more)

### Community 59 - "routers/agent_chat.py"
Cohesion: 0.19
Nodes (16): get_prompt_template(), Retrieves prompt template from DB with in-memory caching, falling back to…, AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage, delete_chat() (+8 more)

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

### Community 65 - "admin.py"
Cohesion: 0.23
Nodes (13): delete_application(), delete_event(), get_staleness_stats(), AsyncSession, delete, get, post, # TODO: Trigger re-indexing of the embedding for this application based on the… (+5 more)

### Community 66 - "routers/extension.py"
Cohesion: 0.26
Nodes (12): clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text…, Receives a job posting URL, scrapes page text (or uses pre-captured HTML), and… (+4 more)

### Community 67 - "test_candidate_profile.py"
Cohesion: 0.23
Nodes (11): DomainExperienceItem, compute_programmatic_skill_match(), _is_skill_matched(), _normalize_token(), Checks if a JD required skill matches any skill in the candidate's CV profile., Computes Job Requirement Coverage Ratio between candidate CV skills and the…, AsyncSession, test_candidate_profile_crud_and_anonymization() (+3 more)

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

### Community 75 - "test_ai_config.py"
Cohesion: 0.38
Nodes (10): Strips <think>...</think> reasoning tags from LLM output text., strip_reasoning_tags(), asyncio, AsyncSession, test_ai_provider_crud_and_masking(), test_domain_entity_models(), test_global_settings_db_backed(), test_probe_model_capabilities() (+2 more)

### Community 76 - "extractJobData"
Cohesion: 0.22
Nodes (8): extractJobData(), deriveTitleFromDoc(), getText(), getTextIn(), queryFirst(), queryFirstIn(), isCleanTitle(), resolveCanonicalJobUrl()

### Community 77 - "index.js"
Cohesion: 0.19
Nodes (13): apiClient, delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb() (+5 more)

### Community 79 - "saveProfileField"
Cohesion: 0.14
Nodes (14): addCompetency(), addDomainArea(), addLanguage(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeCompetency(), removeDomainArea() (+6 more)

### Community 82 - "process_evaluation_task"
Cohesion: 0.40
Nodes (10): _execute_cover_letter_steps(), _execute_cv_extraction_steps(), _execute_email_sync_steps(), _execute_evaluation_steps(), process_evaluation_task(), AsyncSession, Processes a single queued intake evaluation task asynchronously within the…, generate_cover_letter() (+2 more)

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

### Community 91 - "scheduleStudioAutoSave"
Cohesion: 0.25
Nodes (9): applyProbeRecommendations(), loadPrompts(), resetGlobalDefaultToDefaults(), resetStudioPrompt(), resetStudioTaskToDefaults(), saveStudioTask(), scheduleStudioAutoSave(), selectStudioSuggestedModel() (+1 more)

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

### Community 101 - "GenerateInterviewGuideRequest"
Cohesion: 0.31
Nodes (9): generate_app_interview_guide_stream(), GenerateInterviewGuideRequest, generate_interview_guide(), generate_interview_guide_stream(), AsyncSession, Async generator that executes `interview_guide_graph.astream(...)` and yields…, Coordinates candidate profile retrieval, job posting lookup, LangGraph…, Unit test for generate_interview_guide_stream async generator. (+1 more)

### Community 106 - "cleanCVText"
Cohesion: 0.67
Nodes (3): cleanCVText(), handleFileUpload(), handleFormatCleanClick()

### Community 107 - "pollTaskUntilComplete"
Cohesion: 0.67
Nodes (3): loadProfile(), pollTaskUntilComplete(), processCV()

### Community 108 - "openAddEmailAccountModal"
Cohesion: 0.67
Nodes (3): loadOAuthConfig(), openAddEmailAccountModal(), toggleEmailIntake()

### Community 110 - "normalize_job_url"
Cohesion: 0.08
Nodes (56): Any, normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, cover_letter_node(), db_commit_node(), extraction_node(), fuzzy_match_node(), _get_db() (+48 more)

### Community 137 - "test_schemas.py"
Cohesion: 0.12
Nodes (19): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, AllowedApplicationStatus, ApplicationTransitionRequest, test_application_transition_request_date_coercion() (+11 more)

### Community 146 - "services/llm.py"
Cohesion: 0.15
Nodes (21): ApplicationEmbeddingModel, ApplicationSummaryResult, EmailExtractionResult, assess_job_posting(), extract_email_info(), extract_job_spec(), generate_and_save_application_embedding(), generate_embedding() (+13 more)

### Community 151 - "LazyAsyncPostgresSaver"
Cohesion: 0.21
Nodes (3): AsyncPostgresSaver, LazyAsyncPostgresSaver, setter

### Community 154 - "clean_html_text"
Cohesion: 0.39
Nodes (6): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, test_clean_html_text_decodes_entities_and_formats_breaks(), test_clean_html_text_none_and_empty(), test_clean_html_text_plain_text(), test_clean_html_text_strips_scripts_and_styles()

### Community 157 - "env.py"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 159 - "schemas/intake.py"
Cohesion: 0.26
Nodes (13): AssessJobRequest, BulkTaskActionRequest, BulkTaskActionResult, ConfirmAssessmentRequest, DirectEmailIntakeRequest, EmailBatchIntakeRequest, EmailProcessingSummary, EnqueueAssessmentRequest (+5 more)

### Community 167 - "anonymize_and_parse_cv"
Cohesion: 0.28
Nodes (7): anonymize_and_parse_cv(), De-identifies candidate resume: - Runs local programmatic regex pre-scrubber on…, programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty(), CVAnonymizationResult

### Community 168 - "EmailAccountModel"
Cohesion: 0.31
Nodes (8): EmailAccountModel, asyncio, test_fetch_emails_from_account_imap_threaded(), test_imap_batch_fetching(), asyncio, test_email_intake_disabled_guard(), test_global_settings_backward_compatibility(), test_system_settings_get_and_patch()

## Knowledge Gaps
- **687 isolated node(s):** `accountToClear`, `accountToDelete`, `activeTab`, `activeTaskDef`, `availableMailFolders` (+682 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ApplicationModel` connect `ApplicationModel` to `process_email_batch_sequential`, `admin.py`, `routers/extension.py`, `services/agent_tools.py`, `PostgresTracer`, `GenerateInterviewGuideRequest`, `ExtractedEmailInfo`, `EmailPayload`, `test_ai_config.py`, `Base`, `CompanyModel`, `normalize_job_url`, `main.py`, `IntakeEvaluationTaskModel`, `routers/ai_config.py`, `routers/action_items.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `useUIStore` connect `uiStore.js` to `SettingsView.vue`, `ApplicationDetailDrawer.vue`, `OnboardingWizardModal.vue`, `ApplicationsView.vue`, `AgentChatView.vue`, `QueueView.vue`, `StagingView.vue`, `AssessmentsView.vue`, `AnalyticsView.vue`, `CandidateProfileView.vue`, `JobIntakeView.vue`, `EmailAccountsSettings.vue`, `FloatingQueueWidget.vue`, `ActionItemsView.vue`, `CoverLetterModal.vue`, `AppNavbar.vue`, `IngestModal.vue`, `MatchAnalysisModal.vue`, `JobIntakeModal.vue`, `endpoints.js`, `LogActivityModal.vue`, `InterviewReaderModal.vue`, `index.js`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `CompanyModel` connect `CompanyModel` to `process_email_batch_sequential`, `PostgresTracer`, `routers/extension.py`, `services/agent_tools.py`, `ExtractedEmailInfo`, `routers/applications.py`, `EmailPayload`, `test_ai_config.py`, `Base`, `normalize_job_url`, `IntakeEvaluationTaskModel`, `main.py`, `routers/ai_config.py`, `ApplicationModel`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Are the 59 inferred relationships involving `CompanyModel` (e.g. with `update_application()` and `clip_job_pre_extracted()`) actually correct?**
  _`CompanyModel` has 59 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `EmailAccountModel` (e.g. with `clear_account_processed_emails()` and `clear_all_processed_emails()`) actually correct?**
  _`EmailAccountModel` has 20 INFERRED edges - model-reasoned connections that need verification._