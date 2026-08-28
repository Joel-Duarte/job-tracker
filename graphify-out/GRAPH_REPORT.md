# Graph Report - job-tracker  (2026-08-28)

## Corpus Check
- 237 files · ~256,430 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2727 nodes · 5849 edges · 135 communities (113 shown, 22 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 578 edges (avg confidence: 0.94)
- Token cost: 12,500 input · 3,200 output

## Community Hubs (Navigation)
- Settings & Mail Configuration UI
- Mock Interview Simulation Engine
- Application Detail Drawer UI
- Backend App Settings & Security
- Onboarding Wizard Workflow
- Recruitment Analytics & Funnel API
- Applications Kanban Board UI
- Database Connection & Schema Manager
- Job Intake & AI Evaluation Router
- Agent Chat & Interview Assistant UI
- Intake Queue Management UI
- CI Workflows & Repo Infrastructure
- Agent Tools & Function Schemas
- Staging & Triage Queue UI
- Browser Extension Ingestion Router
- AI Provider & Model Binding Config
- Core SQLAlchemy Domain Models
- Candidate CV Profile & Parsing API
- Browser Extension Service Worker
- AI Assessments Dashboard UI
- Dynamic LLM Factory & Model Routing
- Email Synchronization & OAuth Router
- Analytics Dashboard View
- Candidate Profile Management UI
- Job Intake Ingestion View
- Mock Interview Simulation Engine
- Settings & Configuration UI
- Floatingqueuewidget Module
- Settings & Configuration UI
- Test Suite: graph_state
- Settings & Configuration UI
- Candidate Profile & CV Processing
- Mock Interview Simulation Engine
- Pageheader Module
- Coverlettermodal Module
- Settings & Configuration UI
- Package Module
- Action Items Module
- Settings & Configuration UI
- Ingestmodal Module
- Kanban Applications Board UI
- Diagnostics & Telemetry Tracing
- Dynamic LLM Factory & Model Routing
- Endpoints Module
- Datetimepicker Module
- Jobintakemodal Module
- Settings & Configuration UI
- Mock Interview Simulation Engine
- Email Sync & Account Management
- SQLAlchemy Domain Data Models
- Settings & Configuration UI
- Email Sync & Account Management
- Mock Interview Simulation Engine
- Email Sync & Account Management
- Prompts Module
- SQLAlchemy Domain Data Models
- Staging & Ambiguous Lead Triage
- Test Suite: domain_resolver
- Mock Interview Simulation Engine
- Conversational Agent & Chat UI
- Events Module
- Staging & Ambiguous Lead Triage
- Test Suite: file_parser
- Settings & Configuration UI
- Kanban Applications Board UI
- Endpoints Module
- Ai Queue Module
- Core Settings & Security Config
- Interviewreadermodal Module
- Dynamic LLM Factory & Model Routing
- Settings & Configuration UI
- Settings & Configuration UI
- Mock Interview Simulation Engine
- Conversational Agent & Chat UI
- Settings & Configuration UI
- Database Engine & Session Management
- Browser Extension Client Runtime
- Mock Interview Simulation Engine
- Task Tracker Module
- Candidate Profile & CV Processing
- Interview Preparation Guide Generator
- Test Suite: test_bulk_transition
- Logactivitymodal Module
- Settings & Configuration UI
- Staging & Ambiguous Lead Triage
- Dev Module
- Mock Interview Simulation Engine
- Kanban Applications Board UI
- Settings & Configuration UI
- Posthiremodal Module
- Kanban Applications Board UI
- Recruitment Analytics & Metrics
- Staging & Ambiguous Lead Triage
- Settings & Configuration UI
- Settings & Configuration UI
- Staging & Ambiguous Lead Triage
- Database Schema Migrations
- Intake Evaluation & Lead Ingestion
- Candidate Profile & CV Processing
- Browser Extension Backend Ingestion
- Mock Interview Simulation Engine
- Candidate Profile & CV Processing
- Candidate Profile & CV Processing
- Candidate Profile & CV Processing
- Settings & Configuration UI
- Skill Taxonomy Module
- Mock Interview Simulation Engine
- Architecture Module
- Index Module
- Onboarding Wizard Workflow
- Emailrenderer Module
- Candidate Profile & CV Processing
- Mock Interview Simulation Engine
- Settings & Configuration UI
- Staging & Ambiguous Lead Triage
- Pre-Commit Module
- CI/CD & Repository Infrastructure
- CI/CD & Repository Infrastructure
- Quickstart Module
- User Guide Module
- Browser Extension Client Runtime
- Browser Extension Client Runtime
- Icon-128 Module
- Icon-48 Module
- Pyproject Module
- Responsive-Design-Guide Module

## God Nodes (most connected - your core abstractions)
1. `ApplicationModel` - 135 edges
2. `CompanyModel` - 95 edges
3. `IntakeEvaluationTaskModel` - 63 edges
4. `ApplicationEventModel` - 57 edges
5. `EmailAccountModel` - 42 edges
6. `AIProviderModel` - 39 edges
7. `Base` - 38 edges
8. `PostgresTracer` - 38 edges
9. `useUIStore` - 38 edges
10. `ActionItemModel` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Root Pre-Commit Configuration` --semantically_similar_to--> `Backend Pre-Commit Configuration`  [INFERRED] [semantically similar]
  .pre-commit-config.yaml → backend/.pre-commit-config.yaml
- `seed()` --uses--> `ApplicationModel`  [INFERRED]
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
- **Companion Browser Extension Architecture** — extension_readme_companion_extension, extension_shadow_dom_dock, extension_popup_popup_html, extension_chromewebstore_docs [INFERRED 0.85]
- **Backend LangGraph State Machines** — docs_architecture_intake_stategraph, docs_architecture_interview_guide_graph, docs_architecture_mock_interview_simulator [INFERRED 0.85]

## Communities (135 total, 22 thin omitted)

### Community 0 - "Settings & Mail Configuration UI"
Cohesion: 0.02
Nodes (70): accountToClear, accountToDelete, activeTab, activeTaskDef, availableMailFolders, bindings, copiedRedirectUri, coverLetterLength (+62 more)

### Community 1 - "Mock Interview Simulation Engine"
Cohesion: 0.06
Nodes (69): AsyncBaseTracer, InterviewSessionModel, delete_session(), drill_down(), evaluate_answer(), finalize_session(), get_session(), list_sessions() (+61 more)

### Community 2 - "Application Detail Drawer UI"
Cohesion: 0.03
Nodes (43): ALL_SECTIONS, appStore, close(), deletingEventId, { detailActiveTab: activeTab }, emailModalViewMode, executeDirectTransition(), handleDeleteApplication() (+35 more)

### Community 3 - "Backend App Settings & Security"
Cohesion: 0.07
Nodes (59): _get_or_generate_secret_key(), model_validator, Always constructs the connection URI dynamically from current settings., Reads persistent SECRET_KEY from PROJECT_ROOT/data/.sec_key or auto-generates a…, Settings, _get_fernet(), bulk_transition_applications(), clear_app_interview_guide() (+51 more)

### Community 4 - "Onboarding Wizard Workflow"
Cohesion: 0.03
Nodes (47): availableMailFolders, availableModels, copiedRedirectUri, createdEmailAccountId, currentEmailProvider, currentStep, customModelMode, cvFileRef (+39 more)

### Community 5 - "Recruitment Analytics & Funnel API"
Cohesion: 0.08
Nodes (53): get_funnel_metrics(), get_overview(), get_role_alignment_endpoint(), AsyncSession, get, get_funnel_metrics(), AsyncSession, get (+45 more)

### Community 6 - "Applications Kanban Board UI"
Cohesion: 0.04
Nodes (34): activeColumnIndex, activeGuideAppId, activeMenuApp, analysisAppId, appStore, appToDelete, closeCardMenu(), draggedApp (+26 more)

### Community 7 - "Database Connection & Schema Manager"
Cohesion: 0.06
Nodes (45): check_db_connection(), ensure_db_schema(), get_db(), AsyncSession, Tests the connection to PostgreSQL and logs the connected database name., Ensures required extensions exist, provisions any missing database tables from…, generate_query_embedding(), Generates a vector embedding for an incoming search query string using… (+37 more)

### Community 8 - "Job Intake & AI Evaluation Router"
Cohesion: 0.09
Nodes (53): assess_job_lead(), bulk_delete_evaluation_tasks(), bulk_retry_evaluation_tasks(), cancel_evaluation_task(), clear_completed_evaluations(), confirm_job_assessment(), delete_evaluation_task(), enqueue_job_assessment() (+45 more)

### Community 9 - "Agent Chat & Interview Assistant UI"
Cohesion: 0.04
Nodes (29): activeMode, appSearchQuery, appStore, candidateAnswer, chatContainer, chatStore, eligibleApplications, filteredApplications (+21 more)

### Community 10 - "Intake Queue Management UI"
Cohesion: 0.05
Nodes (37): activeCancelTask, activeCount, activeFixJDTask, bulkDeleteSelected(), bulkRetrySelected(), clearSelection(), completedCount, deleteTask() (+29 more)

### Community 11 - "CI Workflows & Repo Infrastructure"
Cohesion: 0.08
Nodes (45): Dependabot Configuration, Pull Request Template, Backend CI Workflow, Deploy Frontend to GitHub Pages Workflow, Frontend CI Workflow, Root Pre-Commit Configuration, Job Tracker System Overview (AGENTS.md), Backend Pre-Commit Configuration (+37 more)

### Community 12 - "Agent Tools & Function Schemas"
Cohesion: 0.11
Nodes (42): AnalyzePipelineMetricsInput, ApplicationDetailsInput, DetectStalledApplicationsInput, EvaluateAIFitScoreInput, ListApplicationsInput, ManageActionItemsInput, ManageIntakeQueueInput, BaseModel (+34 more)

### Community 13 - "Staging & Triage Queue UI"
Cohesion: 0.05
Nodes (35): appSearchQuery, appStore, clearOlderThanDays, computedUrgency, computedUrgencyLabel, emailViewMode, hasMore, hasNextItem (+27 more)

### Community 14 - "Browser Extension Ingestion Router"
Cohesion: 0.10
Nodes (39): clip_job_pre_extracted(), clip_job_url(), _extract_text_from_html(), AsyncSession, post, Directly accepts pre-extracted DOM metadata (company, title, description, url)…, Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text…, Receives a job posting URL, scrapes page text (or uses pre-captured HTML), and… (+31 more)

### Community 15 - "AI Provider & Model Binding Config"
Cohesion: 0.14
Nodes (40): clear_embeddings_cache(), Clears cached Embeddings model instances., create_ai_provider(), delete_ai_provider(), delete_ai_task_binding(), _fetch_models_from_endpoint(), get_ai_health_endpoint(), get_global_settings() (+32 more)

### Community 16 - "Core SQLAlchemy Domain Models"
Cohesion: 0.12
Nodes (25): AgentChatModel, ActionItemModel, ApplicationEmbeddingModel, ApplicationEventModel, Base, JobPostingModel, OtherEventModel, CandidateCVModel (+17 more)

### Community 17 - "Candidate CV Profile & Parsing API"
Cohesion: 0.09
Nodes (35): delete_cv_profile(), enqueue_cv_profile_processing(), get_active_cv_profile(), get_cv_task_status(), parse_cv_document_file(), AsyncSession, BackgroundTasks, delete (+27 more)

### Community 18 - "Browser Extension Service Worker"
Cohesion: 0.14
Nodes (32): checkNotifications(), setupAlarm(), updateBadgeCounter(), applyTheme(), checkBackendConnection(), currentSettings, escapeHtml(), handleCaptureSubmit() (+24 more)

### Community 19 - "AI Assessments Dashboard UI"
Cohesion: 0.06
Nodes (24): activeQueueTasks, activeTab, allCompletedTasks, appStore, bulkArchive(), bulkMarkAsApplied(), evaluationTasks, expandedTaskIds (+16 more)

### Community 20 - "Dynamic LLM Factory & Model Routing"
Cohesion: 0.13
Nodes (33): _clean_base_url(), get_active_llm_config_dict(), _get_cached_embeddings_model(), get_chat_model(), get_embeddings_model(), get_task_chat_model(), get_task_embeddings_model(), AsyncSession (+25 more)

### Community 21 - "Email Synchronization & OAuth Router"
Cohesion: 0.11
Nodes (34): clear_account_processed_emails(), clear_all_processed_emails(), delete_account(), EmailFoldersResponse, get_account(), get_oauth_authorize_url(), get_oauth_config(), list_account_folders() (+26 more)

### Community 22 - "Analytics Dashboard View"
Cohesion: 0.07
Nodes (32): getCurrencySymbol(), activeTab, alignmentData, alignmentSubTab, analyticsData, copiedItemKey, customSearchQuery, dateOptions (+24 more)

### Community 23 - "Candidate Profile Management UI"
Cohesion: 0.06
Nodes (24): currentTaskId, currentTaskStage, currentTaskStatus, editedCVText, editedSummaryText, fileInput, isCancelling, isDeleting (+16 more)

### Community 24 - "Job Intake Ingestion View"
Cohesion: 0.06
Nodes (27): activeTasks, appStore, completedTasks, confirmAndSaveLead(), copiedJd, copiedUrl, deleteTask(), dismissedLinkedInUrl (+19 more)

### Community 25 - "Mock Interview Simulation Engine"
Cohesion: 0.16
Nodes (30): Registers an in-memory running asyncio Task by database task ID., Removes a finished or cancelled task from the in-memory registry., register_running_task(), unregister_running_task(), IntakeEvaluationTaskModel, Persisted queue for asynchronous job lead intake & AI qualification…, ExtractedJobSpec, Structured job details extracted from raw webpage or pasted job description… (+22 more)

### Community 26 - "Settings & Configuration UI"
Cohesion: 0.08
Nodes (25): EmailAccountsAPI, accountToDelete, buildEmailAccountPayload(), confirmClearAllHistory(), confirmDeleteAccount(), copiedRedirectUri, editingAccount, emailAccountForm (+17 more)

### Community 27 - "Floatingqueuewidget Module"
Cohesion: 0.07
Nodes (26): activeCount, activeFixJDTask, activeTasks, closeMenu(), failedCount, failedTasks, fixJDJobUrl, fixJDRawText (+18 more)

### Community 28 - "Settings & Configuration UI"
Cohesion: 0.14
Nodes (28): get_setting(), get_system_settings_model(), load_settings(), Any, AsyncSession, Saves system settings from a dictionary supporting lower-case and upper-case…, Fetches the singleton system settings model (id=1), creating it if it does not…, Retrieves a specific system setting by key asynchronously. (+20 more)

### Community 29 - "Test Suite: graph_state"
Cohesion: 0.20
Nodes (29): JobTrackerState, TypedDict, cover_letter_node(), db_commit_node(), extraction_node(), fuzzy_match_node(), _get_db(), is_email_already_processed() (+21 more)

### Community 30 - "Settings & Configuration UI"
Cohesion: 0.06
Nodes (31): action, default_icon, default_popup, background, service_worker, type, browser_specific_settings, gecko (+23 more)

### Community 31 - "Candidate Profile & CV Processing"
Cohesion: 0.11
Nodes (29): get_prompt_template(), Retrieves prompt template from DB with in-memory caching, falling back to…, anonymize_and_parse_cv(), assess_job_posting(), extract_job_spec(), generate_cover_letter(), generate_embedding(), get_active_llm_config() (+21 more)

### Community 32 - "Mock Interview Simulation Engine"
Cohesion: 0.14
Nodes (28): EmailPayload, ExtractedEmailInfo, Structured extraction format returned by the LLM service., process_email_batch_sequential(), process_single_email_graph(), AsyncSession, Executes the LangGraph StateGraph pipeline for a single email payload., Sequentially routes emails through the compiled LangGraph pipeline. (+20 more)

### Community 33 - "Pageheader Module"
Cohesion: 0.08
Nodes (23): actionItems, activeUrgencyDropdown, applicationsList, currentEditId, deleteTask(), displayedTasks, fetchActionItems(), filterTab (+15 more)

### Community 34 - "Coverlettermodal Module"
Cohesion: 0.07
Nodes (25): application, appStore, autoSaveStatus, charCount, close(), COVER_LETTER_LENGTHS, COVER_LETTER_TONES, currentLengthLabel (+17 more)

### Community 35 - "Settings & Configuration UI"
Cohesion: 0.12
Nodes (17): AIConfigAPI, uiStore, uiStore, activeCount, hasItems, queue, STAGES, uiStore (+9 more)

### Community 36 - "Package Module"
Cohesion: 0.07
Nodes (28): axios, dompurify, dependencies, axios, dompurify, @lucide/vue, lucide-vue-next, pinia (+20 more)

### Community 37 - "Action Items Module"
Cohesion: 0.15
Nodes (27): compute_live_urgency(), create_action_item(), delete_action_item(), list_action_items(), override_action_item_urgency(), AsyncSession, BackgroundTasks, delete (+19 more)

### Community 38 - "Settings & Configuration UI"
Cohesion: 0.07
Nodes (18): ActionItemsAPI, StagingAPI, getRouteTitle(), isHealthPopoverOpen, isMobileMenuOpen, pendingStagingCount, pendingTasksCount, pillLabel (+10 more)

### Community 39 - "Ingestmodal Module"
Cohesion: 0.07
Nodes (22): activeTab, appStore, emailAccounts, handleEmailSync(), ingestResult, isDragging, isSubmitting, loadEmailAccounts() (+14 more)

### Community 40 - "Kanban Applications Board UI"
Cohesion: 0.07
Nodes (24): analysisData, application, compensationText, computedScoreText, emit, error, gapMitigationText, isLoading (+16 more)

### Community 41 - "Diagnostics & Telemetry Tracing"
Cohesion: 0.14
Nodes (24): TraceEventModel, export_diagnostics(), _extract_tracer_task_name(), get_diagnostics_stats(), get_single_trace(), get_traces(), _parse_filter_datetime(), purge_traces() (+16 more)

### Community 42 - "Dynamic LLM Factory & Model Routing"
Cohesion: 0.19
Nodes (25): AsyncSession, Seeds missing prompts into DB upon boot without overwriting existing user…, seed_default_prompts(), ApplicationSummaryResult, EmailExtractionResult, HardMatches, ImpactReframingItem, OptimizationGaps (+17 more)

### Community 43 - "Endpoints Module"
Cohesion: 0.09
Nodes (19): DiagnosticsAPI, activeCategory, categories, copied, loadData(), loading, loadingDetail, loadingTraces (+11 more)

### Community 44 - "Datetimepicker Module"
Cohesion: 0.08
Nodes (18): calendarDays, clearValue(), confirmSelection(), containerRef, DAYS_OF_WEEK, displayText, emit, isOpen (+10 more)

### Community 45 - "Jobintakemodal Module"
Cohesion: 0.09
Nodes (23): activeTab, copiedJd, copiedUrl, dismissedLinkedInUrl, dismissLinkedInWarning(), executeEnqueue(), extractUrls(), handleBulkPromptDecision() (+15 more)

### Community 46 - "Settings & Configuration UI"
Cohesion: 0.13
Nodes (20): clean_html_text(), Converts HTML-rich or markup-tainted text into clean, readable plain text: 1.…, _clean_header(), fetch_emails_from_account(), _fetch_imap_emails_sync(), datetime, Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft…, Helper to decode encoded email headers (e.g. Subject). (+12 more)

### Community 47 - "Mock Interview Simulation Engine"
Cohesion: 0.12
Nodes (21): normalize_job_url(), Cleans leading and trailing whitespace while preserving the exact original URL,…, JobAssessmentResult, Any, field_validator, persist_or_stage_job_assessment(), Any, AsyncSession (+13 more)

### Community 48 - "Email Sync & Account Management"
Cohesion: 0.13
Nodes (16): fetch_account_folders(), Fetches list of available mail folders / labels from IMAP, Gmail API, or…, GmailOAuthAdapter, MicrosoftGraphAdapter, Any, datetime, Adapter for Google Gmail REST API with incremental history IDs., OAuth2 adapter for Microsoft Graph (Outlook / Microsoft 365). (+8 more)

### Community 49 - "SQLAlchemy Domain Data Models"
Cohesion: 0.18
Nodes (22): CompanyModel, asyncio, AsyncSession, When exactly 1 application exists for a matched company, auto-link to it even…, When multiple applications exist for a company, disambiguate by position or…, Recruiter outreach for a new company should route to Staging Queue for review., An email with a completely different position for a company with 1 active…, An email for a company with only a REJECTED / terminal application routes to… (+14 more)

### Community 50 - "Settings & Configuration UI"
Cohesion: 0.10
Nodes (20): apiClient, AgentAPI, AnalyticsAPI, CandidateProfileAPI, EventsAPI, IntakeAPI, InterviewSimulatorAPI, PromptsAPI (+12 more)

### Community 51 - "Email Sync & Account Management"
Cohesion: 0.17
Nodes (22): generate_oauth_state(), Generates a signed cryptographic state token for OAuth CSRF protection., Validates the OAuth CSRF state token and guards against replay attacks., validate_oauth_state(), asyncio, AsyncSession, Test clearing email deduplication history and resetting sync cursor for a…, Test clearing all email deduplication history and resetting sync cursors across… (+14 more)

### Community 52 - "Mock Interview Simulation Engine"
Cohesion: 0.18
Nodes (21): ProcessedEmailModel, Single source of truth for all email deduplication. Every email that passes…, BaseModel, Triggers asynchronous email sync for a date window with keyword pre-filtering.…, sync_email_account(), SyncFolderRequest, TaskResponse, enable_email_intake_mock() (+13 more)

### Community 53 - "Email Sync & Account Management"
Cohesion: 0.18
Nodes (12): _encrypt_table_secrets(), Connection, upgrade(), decrypt_secret(), encrypt_secret(), Encrypt a sensitive value, preserving already encrypted values., Decrypt a value, retaining compatibility with legacy plaintext rows., EmailAccountModel (+4 more)

### Community 54 - "Prompts Module"
Cohesion: 0.17
Nodes (18): clear_prompt_cache(), Invalidates the in-memory prompt cache for a specific prompt or all prompts., PromptModel, get_prompt(), list_prompts(), AsyncSession, get, patch (+10 more)

### Community 55 - "SQLAlchemy Domain Data Models"
Cohesion: 0.20
Nodes (19): ApplicationModel, archive_stale_applications(), Any, AsyncSession, Finds all applications in active stages where last_activity_at (or…, asyncio, AsyncSession, test_application_patch_updates() (+11 more)

### Community 56 - "Staging & Ambiguous Lead Triage"
Cohesion: 0.18
Nodes (20): StagingItemModel, clear_resolved_staging_items(), get_staging_item(), list_staging_items(), AsyncSession, delete, get, Fetches full details for a single staged item. (+12 more)

### Community 57 - "Test Suite: domain_resolver"
Cohesion: 0.20
Nodes (19): clean_domain(), extract_domain_from_url(), is_ats_hostname(), query_clearbit_autocomplete(), Domain resolution service for extracting and discovering official company…, Checks if a given hostname belongs to a known ATS or job board., Extracts the company domain from a job posting URL if it is not an ATS., Queries Clearbit's public autocomplete API to find the company's official… (+11 more)

### Community 58 - "Mock Interview Simulation Engine"
Cohesion: 0.12
Nodes (18): db_session(), FallbackPostgresConnection, is_port_open(), mock_extracted_job_info(), mock_job_email_payload(), postgres_container(), AsyncSession, fixture (+10 more)

### Community 59 - "Conversational Agent & Chat UI"
Cohesion: 0.15
Nodes (19): AgentChatRead, AgentChatRequest, AgentChatResponse, chat_with_agent(), ChatMessage, delete_chat(), get_chat(), list_chats() (+11 more)

### Community 60 - "Events Module"
Cohesion: 0.16
Nodes (18): delete_event(), list_action_required_events(), list_application_events(), list_other_events(), AsyncSession, delete, get, patch (+10 more)

### Community 61 - "Staging & Ambiguous Lead Triage"
Cohesion: 0.19
Nodes (15): bulk_dismiss_staging_items(), post, Bulk dismisses specific staging items or all pending staging items matching…, Accepts user fixes, applies them to DB records, and marks the staged item…, resolve_staging_item(), BaseModel, model_validator, Schema for displaying an item in the staging queue. (+7 more)

### Community 62 - "Test Suite: file_parser"
Cohesion: 0.18
Nodes (16): _extract_ics_summary(), parse_eml(), parse_msg(), parse_txt(), parse_uploaded_file(), Parses Microsoft Outlook .msg binary bytes into EmailPayload., Parses plaintext / raw thread text into EmailPayload., Extracts summary and date info from raw .ics calendar payload. (+8 more)

### Community 63 - "Settings & Configuration UI"
Cohesion: 0.23
Nodes (16): checkFloatingAiHealthGating(), enableDraggable(), onMouseMove(), onMouseUp(), escapeHtml(), extractPageJobData(), loadSettings(), renderDockUI() (+8 more)

### Community 64 - "Kanban Applications Board UI"
Cohesion: 0.15
Nodes (12): fallbackInitial, faviconUrl, hasError, isLoaded, props, formatSalaryRange(), getCompanyDomain(), getCompanyFaviconUrl() (+4 more)

### Community 65 - "Endpoints Module"
Cohesion: 0.13
Nodes (10): ApplicationsAPI, router, routes, recordPageView(), application, error, hasCopied, isLoading (+2 more)

### Community 66 - "Ai Queue Module"
Cohesion: 0.16
Nodes (8): cancel_running_task(), get_running_task_ids(), PrioritySemaphore, ProviderConcurrencyManager, A semaphore that grants locks based on priority. Waiters with a lower priority…, Cancels an active background asyncio.Task in memory. Disconnects the active…, Returns list of currently active running task IDs., Manages per-provider concurrency pools using dynamic PrioritySemaphore…

### Community 67 - "Core Settings & Security Config"
Cohesion: 0.37
Nodes (14): AIProviderModel, AITaskBindingModel, check_ai_provider_health(), invalidate_ai_health_cache(), asyncio, AsyncSession, fixture, reset_health_cache() (+6 more)

### Community 68 - "Interviewreadermodal Module"
Cohesion: 0.13
Nodes (9): application, emit, error, hasCopied, isFullScreen, isLoading, props, router (+1 more)

### Community 69 - "Dynamic LLM Factory & Model Routing"
Cohesion: 0.29
Nodes (4): FailoverChatModel, Any, Transparent failover wrapper around primary and secondary LangChain…, Exception

### Community 70 - "Settings & Configuration UI"
Cohesion: 0.22
Nodes (13): patch, update_global_settings(), get_system_settings(), AsyncSession, get, patch, update_system_settings(), GlobalSettingsRead (+5 more)

### Community 71 - "Settings & Configuration UI"
Cohesion: 0.18
Nodes (12): create_account(), patch, post, Add a new email account configuration., Update settings or credentials for an existing email account., update_account(), EmailAccountBase, EmailAccountCreate (+4 more)

### Community 72 - "Mock Interview Simulation Engine"
Cohesion: 0.15
Nodes (14): Camofox Stealth Scraper, Intake StateGraph, Interview Guide Graph, Mock Interview Simulator Service, pg_trgm GIN Trigram Matching, pgvector HNSW Cosine Indexing, Reasoning Suppression (0-effort), System Architecture Documentation (+6 more)

### Community 73 - "Conversational Agent & Chat UI"
Cohesion: 0.18
Nodes (11): chatMessagesContainer, chatStore, handleKeyDown(), handleSendMessage(), inputMessage, isOpen, route, router (+3 more)

### Community 74 - "Settings & Configuration UI"
Cohesion: 0.15
Nodes (14): buildEmailAccountPayload(), confirmClearAccountHistory(), confirmClearAllHistory(), confirmDeleteAccount(), fetchEmailFolders(), handleOAuthSuccessMessage(), handleStep2NextIMAP(), loadEmailAccounts() (+6 more)

### Community 75 - "Database Engine & Session Management"
Cohesion: 0.21
Nodes (3): AsyncPostgresSaver, LazyAsyncPostgresSaver, setter

### Community 76 - "Browser Extension Client Runtime"
Cohesion: 0.22
Nodes (8): extractJobData(), deriveTitleFromDoc(), getText(), getTextIn(), queryFirst(), queryFirstIn(), isCleanTitle(), resolveCanonicalJobUrl()

### Community 77 - "Mock Interview Simulation Engine"
Cohesion: 0.32
Nodes (9): delay(), handleDemoRequest(), adjustRelativeDates(), getDemoDb(), initDemoDb(), isDemoModeEnabled(), resetDemoDb(), saveDemoDb() (+1 more)

### Community 79 - "Candidate Profile & CV Processing"
Cohesion: 0.17
Nodes (12): addCompetency(), addDomainArea(), addSkill(), adjustDomainYears(), adjustTotalYears(), removeCompetency(), removeDomainArea(), removeSkill() (+4 more)

### Community 80 - "Interview Preparation Guide Generator"
Cohesion: 0.27
Nodes (10): GenerateInterviewGuideRequest, clear_interview_guide(), generate_interview_guide(), generate_interview_guide_stream(), AsyncSession, Async generator that executes `interview_guide_graph.astream(...)` and yields…, Coordinates candidate profile retrieval, job posting lookup, LangGraph…, Clears the existing interview guide for an application. (+2 more)

### Community 81 - "Test Suite: test_bulk_transition"
Cohesion: 0.42
Nodes (10): async_client(), AsyncClient, asyncio, AsyncSession, fixture, test_bulk_transition_archives_open_applications(), test_bulk_transition_creates_timeline_events(), test_bulk_transition_dismisses_pending_action_items_on_terminal() (+2 more)

### Community 82 - "Logactivitymodal Module"
Cohesion: 0.20
Nodes (10): appStore, emit, EVENT_TYPES, eventType, isSubmitting, props, requiresAction, submitLog() (+2 more)

### Community 83 - "Settings & Configuration UI"
Cohesion: 0.22
Nodes (11): buildEmailAccountPayload(), checkOAuthStatusManually(), fetchUserFolders(), handleOAuthMessage(), handleOAuthSuccess(), handleStep4SaveEmail(), handleStep4SaveFinalSettings(), handleStorageEvent() (+3 more)

### Community 84 - "Staging & Ambiguous Lead Triage"
Cohesion: 0.24
Nodes (11): filteredAndSortedItems, formatEventTypeLabel(), getAutoDetectedStatus(), getDetectedEventType(), getItemCompany(), getItemPosition(), handleKeyDown(), selectItem() (+3 more)

### Community 85 - "Dev Module"
Cohesion: 0.29
Nodes (7): dev.sh script, jt script, check_docker(), ensure_env(), open_browser(), show_help(), prod.sh script

### Community 86 - "Mock Interview Simulation Engine"
Cohesion: 0.20
Nodes (10): handleDrillDown(), handleEvaluateAnswer(), handleFinalizeSession(), handleKeyDown(), handleNextQuestion(), handleRestartSameSimulation(), handleSendMessage(), handleStartAnotherSimulation() (+2 more)

### Community 87 - "Kanban Applications Board UI"
Cohesion: 0.28
Nodes (9): formatRelativeDate(), formatDueDateFriendly(), formatScheduledDate(), formatScheduledDateFriendly(), getDueDate(), getDueDateStr(), getScheduledInterviewDate(), getScheduleUrgencyClass() (+1 more)

### Community 88 - "Settings & Configuration UI"
Cohesion: 0.25
Nodes (9): applyProbeRecommendations(), loadPrompts(), resetGlobalDefaultToDefaults(), resetStudioPrompt(), resetStudioTaskToDefaults(), saveStudioTask(), scheduleStudioAutoSave(), selectStudioSuggestedModel() (+1 more)

### Community 89 - "Posthiremodal Module"
Cohesion: 0.32
Nodes (7): actions, appStore, emit, handleConfirm(), handleDecideLater(), props, submitting

### Community 90 - "Kanban Applications Board UI"
Cohesion: 0.32
Nodes (8): advanceAppStage(), executeTransition(), getNextStatus(), handleStatusChange(), onDrop(), openDeleteConfirm(), openTransitionModal(), quickRejectApp()

### Community 91 - "Recruitment Analytics & Metrics"
Cohesion: 0.48
Nodes (6): asyncio, test_get_analytics_overview(), test_get_funnel_metrics_monthly(), test_get_funnel_metrics_weekly(), test_get_role_alignment(), test_get_role_alignment_filtered_track()

### Community 92 - "Staging & Ambiguous Lead Triage"
Cohesion: 0.48
Nodes (6): fuzzyFilterApplications(), fuzzyScore(), levenshteinDistance(), scoreApplicationMatch(), stringSimilarity(), filteredExistingApps

### Community 93 - "Settings & Configuration UI"
Cohesion: 0.33
Nodes (7): deleteProvider(), fetchStudioModels(), loadProviders(), onStudioProviderChange(), saveProvider(), selectStudioTask(), syncStudioForm()

### Community 94 - "Settings & Configuration UI"
Cohesion: 0.33
Nodes (7): fetchGlobalModels(), loadBindings(), onGlobalProviderChange(), saveGlobalDefault(), scheduleGlobalAutoSave(), selectGlobalSuggestedModel(), syncGlobalForm()

### Community 95 - "Staging & Ambiguous Lead Triage"
Cohesion: 0.29
Nodes (7): dismissCurrentItem(), executeBulkDismissSelected(), executeClearResolved(), executeDismissAllPending(), fetchStagingItems(), quickDismissItem(), submitResolution()

### Community 96 - "Database Schema Migrations"
Cohesion: 0.47
Nodes (4): do_run_migrations(), Connection, run_async_migrations(), run_migrations_online()

### Community 97 - "Intake Evaluation & Lead Ingestion"
Cohesion: 0.33
Nodes (6): get_extension_config(), get_task_status(), get, Request, Programmatically returns exposed endpoint URLs and AI readiness status for…, Retrieves live progress for an ongoing or completed email intake task.

### Community 98 - "Candidate Profile & CV Processing"
Cohesion: 0.47
Nodes (4): programmatic_scrub_cv(), Programmatically sanitizes direct PII (emails, phone numbers, profile URLs,…, test_programmatic_scrub_cv_emails_phones_urls(), test_programmatic_scrub_cv_empty()

### Community 99 - "Browser Extension Backend Ingestion"
Cohesion: 0.60
Nodes (5): asyncio, AsyncSession, test_extension_clip_job_direct(), test_extension_clip_url_pipeline(), test_extension_intake_url_and_jd_routes()

### Community 100 - "Mock Interview Simulation Engine"
Cohesion: 0.33
Nodes (6): closeSidebarOnMobile(), enterInterviewFromChat(), handleLoadChat(), handleLoadInterviewSession(), handleNewSimulation(), handleResetChat()

### Community 101 - "Candidate Profile & CV Processing"
Cohesion: 0.50
Nodes (4): compute_programmatic_skill_match(), _normalize_token(), Computes hybrid exact + rapidfuzz skill overlap between candidate CV skills and…, test_programmatic_skill_matcher_aliases_and_ratios()

### Community 106 - "Candidate Profile & CV Processing"
Cohesion: 0.67
Nodes (3): cleanCVText(), handleFileUpload(), handleFormatCleanClick()

### Community 107 - "Candidate Profile & CV Processing"
Cohesion: 0.67
Nodes (3): loadProfile(), pollTaskUntilComplete(), processCV()

### Community 108 - "Settings & Configuration UI"
Cohesion: 0.67
Nodes (3): loadOAuthConfig(), openAddEmailAccountModal(), toggleEmailIntake()

## Knowledge Gaps
- **657 isolated node(s):** `backend`, `manifest_version`, `name`, `version`, `description` (+652 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ApplicationModel` connect `SQLAlchemy Domain Data Models` to `Mock Interview Simulation Engine`, `Backend App Settings & Security`, `Recruitment Analytics & Funnel API`, `Database Connection & Schema Manager`, `Job Intake & AI Evaluation Router`, `Agent Tools & Function Schemas`, `Browser Extension Ingestion Router`, `Core SQLAlchemy Domain Models`, `Mock Interview Simulation Engine`, `Settings & Configuration UI`, `Test Suite: graph_state`, `Candidate Profile & CV Processing`, `Mock Interview Simulation Engine`, `Action Items Module`, `Mock Interview Simulation Engine`, `SQLAlchemy Domain Data Models`, `Events Module`, `Staging & Ambiguous Lead Triage`, `Interview Preparation Guide Generator`, `Test Suite: test_bulk_transition`, `Browser Extension Backend Ingestion`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `useUIStore` connect `Settings & Configuration UI` to `Settings & Mail Configuration UI`, `Application Detail Drawer UI`, `Onboarding Wizard Workflow`, `Applications Kanban Board UI`, `Agent Chat & Interview Assistant UI`, `Intake Queue Management UI`, `Staging & Triage Queue UI`, `AI Assessments Dashboard UI`, `Analytics Dashboard View`, `Candidate Profile Management UI`, `Job Intake Ingestion View`, `Settings & Configuration UI`, `Floatingqueuewidget Module`, `Pageheader Module`, `Coverlettermodal Module`, `Settings & Configuration UI`, `Ingestmodal Module`, `Kanban Applications Board UI`, `Jobintakemodal Module`, `Settings & Configuration UI`, `Interviewreadermodal Module`, `Mock Interview Simulation Engine`, `Logactivitymodal Module`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `EmailAccountModel` connect `Email Sync & Account Management` to `Mock Interview Simulation Engine`, `Settings & Configuration UI`, `Job Intake & AI Evaluation Router`, `Settings & Configuration UI`, `Core SQLAlchemy Domain Models`, `Email Sync & Account Management`, `Email Sync & Account Management`, `Mock Interview Simulation Engine`, `Email Synchronization & OAuth Router`, `Mock Interview Simulation Engine`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 91 inferred relationships involving `ApplicationModel` (e.g. with `create_action_item()` and `list_action_items()`) actually correct?**
  _`ApplicationModel` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 61 inferred relationships involving `CompanyModel` (e.g. with `get_applications_by_status()` and `list_applications()`) actually correct?**
  _`CompanyModel` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `IntakeEvaluationTaskModel` (e.g. with `generate_app_cover_letter()` and `regenerate_app_cover_letter()`) actually correct?**
  _`IntakeEvaluationTaskModel` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `ApplicationEventModel` (e.g. with `update_action_item()` and `delete_event()`) actually correct?**
  _`ApplicationEventModel` has 26 INFERRED edges - model-reasoned connections that need verification._