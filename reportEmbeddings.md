# Audit Report: Embedding Generation, Storage, Payload, and Consumption

## Executive Summary

This report provides a comprehensive code audit of vector embedding creation, payload construction, database storage, lifecycle queue triggers, and search consumption across the backend codebase.

Vector embeddings in this application are strictly **application-centric**. They capture structured status snapshots and event updates for tracked job applications (`ApplicationModel`). Standalone entities such as raw resumes (`CandidateProfileModel`) and standalone job postings (`JobPostingModel`) do **not** generate or store individual vector embeddings.

---

## 1. Embedding Provider & Model Resolution Architecture

### 1.1 Resolution Cascade & Task Bindings
Embedding models are resolved dynamically in `backend/app/core/llm_factory.py` through two primary functions:
* `get_task_embeddings_model(db, **override_kwargs)`: Preferred loader. Queries the database table `ai_task_bindings` (`AITaskBindingModel`) for an active binding where `task_type == 'EMBEDDING'`. If configured, it resolves the underlying provider configuration from `ai_providers` (`AIProviderModel`).
* `get_embeddings_model(db, **override_kwargs)`: Fallback loader. Loads global defaults from active `LLMConfigModel` or returns system defaults (`UNCONFIGURED_EMBEDDING_MODEL = "text-embedding-3-small"`).

### 1.2 Provider Support & Backend Adjustments
Embedding model initialization relies on LangChain's `init_embeddings`.
* Supported normalized providers: `openai`, `anthropic`, `ollama`, `google_genai`.
* Local/Custom Providers (`custom`, `lmstudio`, `vllm`, `local`, `openrouter`) map to the `openai` provider adapter.
* **Local Provider Compatibility Override**: For `provider == "openai"`, the initialization explicitly sets `check_embedding_ctx_length = False` and `tiktoken_enabled = False`. This prevents local OpenAI-compatible endpoints (such as LM Studio or Ollama) from failing on tiktoken token counting.

### 1.3 In-Memory Instance Caching
Embedding model instances are cached in `_EMBEDDINGS_CACHE` (a dictionary in `llm_factory.py`) using a deterministic key generated from sorted initialization arguments `tuple(sorted((k, str(v)) for k, v in init_kwargs.items()))`.
* Cache invalidation is triggered via `clear_embeddings_cache()`, which is called whenever AI configurations or provider bindings are saved or updated (`app/routers/ai_config.py`).

### 1.4 Vector Dimension Constraints & Verification
* **Dimension Expectation**: The database schema strictly defines vector columns as `Vector(768)` (768 dimensions).
* **Connectivity Verification**: The endpoint `POST /api/v1/ai-config/verify-embeddings` in `app/routers/ai_config.py` verifies embedding provider connectivity by calling `aembed_query("Connectivity verification probe.")` and verifying vector generation.

---

## 2. Text Payload & Data Construction

### 2.1 Embedding Payload Generator
Application embedding content is created in `generate_and_save_application_embedding` located in `backend/app/services/llm.py`.

The text input payload is constructed from:
1. Application position title (`application.position`).
2. Company name (`application.company.name` or `"Unknown Company"`).
3. Current application status (`application.status`).
4. Most recent timeline event (`ApplicationEventModel`), including event date, event type (`email_event_type`), event summary (`email_summary`), and pending action details (`email_action`).

#### Payload Formatting Schema:
```text
Job Application: {position} at {company_name}.
Status: {status}.
Latest Update ({event_date}): [{event_type}] {event_summary}.
Action Required: {email_action}
```
*(Note: `Action Required` is appended only if `email_action_required` is True and `email_action` is present).*

### 2.2 Metadata Payload (`metadata` JSONB)
Alongside the raw text payload, a structured JSON metadata payload is saved in the `metadata` column:
```json
{
  "company": "<Company Name>",
  "position": "<Position Title>",
  "status": "<Application Status>",
  "updated_at": "<ISO-8601 Timestamp>"
}
```

### 2.3 Input Normalization & Local Server Array Fallback
The `generate_embedding(db, text_input, embeddings_model)` helper in `app/services/llm.py` handles vector generation with specific fault tolerance:
1. **Payload Pre-processing**: Strings are stripped; dicts or lists are serialized to JSON strings. Empty payloads fallback to `"Job Application"`.
2. **Array Input Fallback**: Local OpenAI-compatible local servers (LM Studio, Ollama) require JSON input as a string array (`{"input": ["..."]}`). `generate_embedding` attempts `embeddings.aembed_documents([cleaned_text])` first. If `aembed_documents` fails or is unsupported, it falls back to `embeddings.aembed_query(cleaned_text)`.

### 2.4 Semantic Truncation Utilities
For large text processing in LLM tasks, `app/services/llm.py` provides `truncate_text_semantically` and `split_text_semantically`. These utilities use `RecursiveCharacterTextSplitter` from `langchain_text_splitters` splitting along Markdown and sentence boundaries (`["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""]`).

---

## 3. Storage Architecture & Database Schema

### 3.1 ORM Model & Database Table
Embeddings are stored in PostgreSQL using the `pgvector` extension.

* **Model Class**: `ApplicationEmbeddingModel` in `backend/app/models/applications.py`.
* **Table Name**: `email_application_embeddings`.

### 3.2 Table Schema Definition
| Column Name | SQL Type | Modifiers / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `email_application_id` | `BigInteger` | `PRIMARY KEY`, `FK(email_applications.id ON DELETE CASCADE)` | One-to-one foreign key link to application |
| `content` | `Text` | `NOT NULL` | Exact raw formatted text string fed into embedding model |
| `metadata` (`metadata_`) | `JSONB` | `NOT NULL`, `DEFAULT '{}'::jsonb` | Structured JSON metadata (company, position, status, updated_at) |
| `embedding` | `pgvector.sqlalchemy.Vector(768)` | `NOT NULL` | 768-dimensional float vector array |
| `updated_at` | `DateTime(TZ)` | `SERVER DEFAULT func.now()` | Record last update timestamp |

### 3.3 Indexing Strategy
The table defines a Hierarchical Navigable Small World (HNSW) vector index using cosine distance operators:
* **Index Name**: `email_application_embeddings_idx`
* **Index Method**: `hnsw`
* **Operator Class**: `vector_cosine_ops` (`postgresql_ops={"embedding": "vector_cosine_ops"}`)

### 3.4 Entity Coverage & Exclusions
* **Embedded Entities**:
  * `ApplicationModel` (`email_applications`): Embedded via `ApplicationEmbeddingModel`.
* **Non-Embedded Entities**:
  * `JobPostingModel` (`job_postings`): Raw markdown job descriptions, salary ranges, and extracted requirements do **not** have standalone vector embeddings.
  * `CandidateProfileModel` (`candidate_profile`) & Resumes: Candidate resumes and profile records do **not** generate or store vector embeddings.
  * `ApplicationEventModel`, `OtherEventModel`, `ActionItemModel`: Individual events and action items do not have separate vector tables; their summaries are embedded as part of the parent application record.

---

## 4. Lifecycle, Execution Triggers, and Queue System

### 4.1 System Control Toggle
Embedding generation is controlled globally by system setting `ENABLE_EMBEDDINGS` (boolean, default `True`, managed via `app/core/config_manager.py`). If set to `False`, background embedding workers log a skip message and exit immediately.

### 4.2 Background Task Execution Architecture
Embedding generation is decoupled from primary request transactions using `async_enqueue_application_embedding(application_id)` in `app/services/llm.py`:
1. **Task Queue Registration**: Creates a queued task record in `IntakeEvaluationTaskModel` (`task_type="EMBEDDING"`, `status="QUEUED"`, `stage="QUEUED"`).
2. **Concurrency Slot Acquisition**: Acquires a Priority 2 execution slot via `concurrency_manager` in `app/core/ai_queue.py` bound to the active EMBEDDING provider's `max_concurrency`.
3. **Task State Updates**: Updates status to `PROCESSING` (`stage="EMBEDDING"`), invokes `generate_and_save_application_embedding` in a short-lived session, and marks task as `COMPLETED` or `FAILED`.
4. **Transaction Isolation**: Data retrieval, external LLM network I/O, and database vector persistence are executed in distinct, short-lived transactions to avoid holding open connection pool connections during external network calls.

### 4.3 Lifecycle Event Triggers
Embedding generation is triggered across the application lifecycle:
* **Deferred During Raw Intake**: Embedding generation is explicitly deferred during raw intake confirm-assessment to optimize initial processing speed (`app/routers/intake.py`).
* **Application Status Updates**: Enqueued when an application status changes or updates via `app/routers/applications.py`.
* **Staging Pipeline Resolution**: Executed when staged items are resolved and committed in `app/routers/staging.py`.
* **Browser Extension Submissions**: Executed when new applications are captured via `app/routers/extension.py`.
* **Action Items**: Enqueued when action items trigger updates in `app/routers/action_items.py`.
* **Conversational Agent Status Transitions**: Updated when the agent tool `update_application_status` changes application pipeline status in `app/services/agent_tools.py`.
* **Development Seed Dataset**: Seeding development mock data (`app/services/seed_data.py`) explicitly omits embedding generation (`embeddings_count == 0`).

---

## 5. Consumption & Semantic Search Architecture

### 5.1 Public Semantic Search API Endpoint
* **Endpoint**: `GET /api/v1/search/semantic` (`backend/app/routers/search.py`)
* **Input Parameters**:
  * `q` (string): Natural language query.
  * `limit` (int, default 10): Maximum results to return.
  * `max_distance` (float, default 0.60): Maximum allowable cosine distance.
* **Execution Flow**:
  1. Generates query vector embedding using `generate_query_embedding(q)` in `app/core/embeddings.py`.
  2. Calculates pgvector cosine distance: `distance_expr = ApplicationEmbeddingModel.embedding.cosine_distance(query_vector)`.
  3. Joins `ApplicationModel` and `CompanyModel`.
  4. Applies distance filter: `WHERE (embedding <=> $1::vector) < max_distance` (0.60 threshold).
  5. Sorts by distance ascending (`ORDER BY distance ASC`).
  6. Calculates and returns similarity score: `similarity_score = round(1.0 - distance, 6)`.

### 5.2 Conversational AI Agent Search Tool
* **Tool Name**: `semantic_vector_search` (`backend/app/services/agent_tools.py`).
* **Implementation Function**: `execute_semantic_vector_search(db, query, limit)`.
* **Execution Flow**:
  1. Checks if `ENABLE_EMBEDDINGS` is active.
  2. **Fallback Mode (Embeddings Disabled)**: Runs SQL `ILIKE` keyword search across `CompanyModel.name`, `ApplicationModel.position`, and `ApplicationModel.status`. Returns results tagged with `"similarity_score": "Keyword Match (Fast)"`.
  3. **Vector Mode**: Generates query vector via `generate_embedding(db, query)`, calculates cosine distance, sorts ascending, and formats similarity percentage: `sim_pct = round(max(0.0, min(100.0, (1.0 - float(dist)) * 100.0)), 1)`.

---

## Summary Matrix

| Entity / Topic | Vector Embedded? | Storage Location | Key Source Code References |
| :--- | :--- | :--- | :--- |
| **Tracked Application** | **Yes** | Table `email_application_embeddings`, column `embedding` (`Vector(768)`) | `app/models/applications.py`, `app/services/llm.py` |
| **Job Posting / JD** | **No** | Stored as text/JSON in `job_postings` table | `app/models/applications.py` |
| **Candidate Resume / Profile** | **No** | Stored as text/JSON in `candidate_profile` table | `app/models/candidate_profile.py` |
| **Timeline Events / Action Items** | **No (Indirect)** | Event summaries embedded inside parent Application payload | `app/models/applications.py`, `app/services/llm.py` |
| **Embedding Generation** | N/A | LangChain `init_embeddings` via `AITaskBindingModel` | `app/core/llm_factory.py`, `app/services/llm.py` |
| **Search & Consumption** | N/A | Cosine distance (`<=>`), HNSW index, threshold < 0.60 | `app/routers/search.py`, `app/services/agent_tools.py` |
