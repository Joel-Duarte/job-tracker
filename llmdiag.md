# Diagnostic Analysis Report: LLM, LangChain & Graph Workflows (llmdiag.md)

This report presents a comprehensive static analysis of all LLM integrations, LangChain components, and LangGraph workflows within the application codebase. Findings are categorized into structural and operational degradation risks: **Graph & Chain Topology Issues**, **Prompt & Context Inefficiencies**, and **Implementation & Concurrency Bottlenecks**. Detailed step-by-step remediation instructions are provided for every identified issue.

---

## 1. Graph & Chain Topology Issues

### 1.1 Cyclical Topology & Infinite Loop Risk in Interview Guide Generation
* **Affected Component / File**: `backend/app/services/interview_guide_graph.py` (`section_generator_node`, `should_continue_sections`, `build_interview_guide_graph`)
* **Static Pattern Analysis**:
  In `interview_guide_graph.py`, the state graph routes through conditional edge `should_continue_sections`. This function checks:
  ```python
  idx = state.get("current_section_index", 0)
  if idx < len(target_sections):
      return "section_generator"
  return END
  ```
  `section_generator_node` updates `current_section_index` by returning `{"current_section_index": idx + 1}`. However, if an uncaught exception occurs during prompt template retrieval or `ainvoke` execution, or if state updates fail to increment `current_section_index` properly while state persists across checkpointer steps, `should_continue_sections` will continually evaluate to `"section_generator"`, causing the node to loop back onto itself endlessly.
* **Performance & Resource Degradation**:
  * **Unbounded Invocations**: Without explicit loop bounds built into the node or routing condition, the graph relies solely on the outer `recursion_limit` parameter passed to `ainvoke`.
  * **Thread & Model Exhaustion**: A stuck worker thread will execute $N$ redundant LLM calls until hit by outer limits, consuming API quota and blocking worker concurrency slots.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `should_continue_sections`, `section_generator_node`, `build_interview_guide_graph`
* **Step-by-Step Remediation Plan**:
  1. **Add Safety Counter to State**:
     Modify `InterviewGuideState` in `interview_guide_graph.py` to include `iteration_count: int`. Initialize `iteration_count: 0` in `initial_state`.
  2. **Increment Counter in Section Generator**:
     Inside `section_generator_node`, increment `iteration_count` on every execution return (`"iteration_count": state.get("iteration_count", 0) + 1`).
  3. **Enforce Hard Circuit Breaker in Conditional Edge**:
     In `should_continue_sections`, enforce a hard threshold:
     ```python
     max_allowed = len(target_sections) + 2
     if idx >= len(target_sections) or state.get("iteration_count", 0) >= max_allowed:
         logger.warning("Reached section limit or safety circuit breaker in guide graph.")
         return END
     return "section_generator"
     ```
  4. **Alternative Refactoring (Map-Reduce Parallelization)**:
     Replace the sequential self-loop with LangGraph's `Send` API or `asyncio.gather` inside a single generator node to execute all target sections concurrently, completely eliminating the loop edge.

---

### 1.2 Unoptimized Sequential Reasoning Loop in Conversational Agent
* **Affected Component / File**: `backend/app/routers/agent_chat.py` (`chat_with_agent`)
* **Static Pattern Analysis**:
  The conversational agent executes a fixed `for turn in range(max_turns):` loop (where `max_turns = 4`). Inside each turn:
  ```python
  response = await model_with_tools.ainvoke(messages, config={"callbacks": [PostgresTracer()]})
  messages.append(response)
  tool_calls = getattr(response, "tool_calls", None)
  ...
  for tc in tool_calls:
      ...
      tool_result = await selected_tool.ainvoke(tool_args, ...)
      messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))
  ```
  When the model returns multiple tool calls in a single turn (e.g. `semantic_vector_search` AND `get_action_items`), the router executes them sequentially inside a `for tc in tool_calls:` loop rather than concurrently.
* **Performance & Resource Degradation**:
  * **Cumulative Serial Latency**: Total turn response time equals $T_{\text{LLM\_1}} + T_{\text{Tool\_1}} + T_{\text{Tool\_2}} + T_{\text{LLM\_2}}$, causing high time-to-first-byte (TTFB).
  * **Unbounded Context Growth**: Every intermediate `AIMessage` and `ToolMessage` is appended directly into the `messages` array without pruning, inflating token counts exponentially across subsequent turns in the loop.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `for turn in range(max_turns):`, `for tc in tool_calls:`, `model_with_tools.ainvoke`
* **Step-by-Step Remediation Plan**:
  1. **Parallelize Tool Execution**:
     Replace the sequential tool call loop in `chat_with_agent` with `asyncio.gather`:
     ```python
     async def run_tool(tc):
         tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
         tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
         tool_id = tc.get("id", f"call_{turn}") if isinstance(tc, dict) else getattr(tc, "id", f"call_{turn}")
         selected_tool = tool_map.get(tool_name)
         if selected_tool:
             try:
                 res = await selected_tool.ainvoke(tool_args, config={"callbacks": [PostgresTracer()]})
                 return ToolMessage(content=str(res), tool_call_id=tool_id), tool_name, tool_args, res
             except Exception as err:
                 return ToolMessage(content=json.dumps({"error": str(err)}), tool_call_id=tool_id), tool_name, tool_args, None
         return ToolMessage(content=json.dumps({"error": f"Tool '{tool_name}' missing"}), tool_call_id=tool_id), tool_name, tool_args, None

     tool_results = await asyncio.gather(*[run_tool(tc) for tc in tool_calls])
     for tool_msg, name, args, res in tool_results:
         messages.append(tool_msg)
         if res is not None:
             actions_performed.append({"action": name, "args": args, "result": res})
     ```
  2. **Sanitize & Limit Tool Results**:
     Apply JSON pruning on `tool_msg.content` before appending to `messages` to keep only relevant fields and cap result array lengths.

---

### 1.3 State Checkpointer Serialization & Storage Bloat in Intake Pipeline
* **Affected Component / File**: `backend/app/services/intake_graph.py` & `backend/app/services/graph_nodes.py` (`build_intake_graph`, `scrape_enrich_node`, `JobTrackerState`)
* **Static Pattern Analysis**:
  The intake graph uses `AsyncPostgresSaver` (`postgres_saver`) as a checkpointer for `JobTrackerState`. Throughout graph execution (`normalize_and_dedupe` -> `extraction` -> `fuzzy_match` -> `scrape_enrich` -> `db_commit` -> `summarize_embed`), large state payloads—including raw scraped webpage markdown (`scraped_spec`), full raw email bodies (`body`), and extracted dictionaries—are stored in state and serialized to PostgreSQL on every node boundary.
* **Performance & Resource Degradation**:
  * **Postgres Serialization Bottleneck**: Large strings in checkpointer state trigger heavy JSON/MsgPack serialization and write operations on every step transition.
  * **DB State Storage Accumulation**: Checkpoint tables accumulate historical state blobs containing duplicate raw text across processing runs.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `build_intake_graph`, `scrape_enrich_node`, `JobTrackerState`, `postgres_saver`
* **Step-by-Step Remediation Plan**:
  1. **Define Terminal State Pruning Node**:
     In `graph_nodes.py`, add `prune_terminal_state_node(state: JobTrackerState)` that clears transient string fields:
     ```python
     async def prune_terminal_state_node(state: JobTrackerState, config: RunnableConfig) -> dict[str, Any]:
         return {"scraped_spec": None, "body": ""}
     ```
  2. **Route Graph Exits Through Pruning**:
     In `intake_graph.py`, insert `prune_terminal_state` before `END` in terminal branches so that final checkpointer state snapshots do not persist multi-kilobyte text fields.
  3. **Use Transient Memory for Scraped Content**:
     Pass scraped text out-of-band via temporary cache or ephemeral state attributes rather than accumulating them in the persistent `JobTrackerState` TypedDict.

---

## 2. Prompt & Context Inefficiencies

### 2.1 Unbounded Webpage Raw Markdown Ingestion in Job Spec Extraction
* **Affected Component / File**: `backend/app/services/llm.py` (`extract_job_spec`) & `backend/app/core/prompts.py` (`DEFAULT_PROMPTS["jd_extraction"]`)
* **Static Pattern Analysis**:
  `extract_job_spec` accepts `raw_webpage_data: str` and injects it directly into `ChatPromptTemplate` via:
  ```python
  chain = prompt | structured_llm
  result = await chain.ainvoke({"raw_webpage_data": raw_webpage_data, ...})
  ```
  Scraped webpages converted from HTML to Markdown often contain 20,000–50,000+ characters of raw text, navigation headers, cookie disclosures, script fragments, and footer links. No pre-filtering, token counting, or semantic chunking is performed prior to sending the text to the LLM.
* **Performance & Resource Degradation**:
  * **Input Token Inflation**: Consumes tens of thousands of tokens per extraction request, escalating API costs.
  * **Model Attention Degradation**: High noise-to-signal ratio impairs structured output extraction accuracy and increases generation latency.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `extract_job_spec`, `raw_webpage_data`, `jd_extraction`
* **Step-by-Step Remediation Plan**:
  1. **Implement DOM/Markdown Cleaning Helper**:
     In `file_parser.py` or `scraper.py`, strip out navigation boilerplate, cookie notices, header/footer text, and social share links using regex or BeautifulSoup / HTML-to-text filters.
  2. **Apply Semantic Truncation in `extract_job_spec`**:
     In `llm.py`, wrap incoming `raw_webpage_data` with `truncate_text_semantically` before prompt insertion:
     ```python
     from app.services.llm import truncate_text_semantically
     cleaned_data = truncate_text_semantically(raw_webpage_data, max_chars=12000)
     ```
  3. **Update Prompt Context Variables**:
     Pass `cleaned_data` into `chain.ainvoke({"raw_webpage_data": cleaned_data})` to bound token usage to maximum ~3,000 tokens per call.

---

### 2.2 Unsanitized Tool Output & Message Accumulation in Agent Chat Memory
* **Affected Component / File**: `backend/app/routers/agent_chat.py` (`chat_with_agent`)
* **Static Pattern Analysis**:
  When loading chat history (`if chat_record:`), all historical messages—including full `ToolMessage` payloads containing raw database JSON records (e.g. 20+ applications returned by `list_applications` or full event histories from `get_application_details`)—are loaded into memory and passed directly to `model_with_tools.ainvoke`:
  ```python
  elif m_data.get("role") == "tool":
      messages.append(ToolMessage(content=m_data.get("content", ""), tool_call_id=...))
  ```
* **Performance & Resource Degradation**:
  * **Exponential Token Growth**: On subsequent turns in a multi-turn chat, input context size grows quadratically ($O(N^2)$ token overhead), quickly exhausting model context limits and slowing down reasoning times.
  * **Cost Escalation**: Users exchanging multiple messages re-submit massive historical tool payloads on every new question.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `m_data.get("role") == "tool"`, `ToolMessage`, `chat_with_agent`
* **Step-by-Step Remediation Plan**:
  1. **Create Tool Output Pruning Utility**:
     In `agent_tools.py`, create `prune_and_sanitize_tool_output(content: str, max_items: int = 5)`:
     ```python
     def prune_and_sanitize_tool_output(content: str, max_items: int = 5) -> str:
         try:
             data = json.loads(content)
             if isinstance(data, list):
                 pruned = data[:max_items]
                 return json.dumps(pruned, separators=(',', ':'))
             elif isinstance(data, dict):
                 # Strip redundant metadata
                 data.pop("metadata", None)
                 return json.dumps(data, separators=(',', ':'))
         except Exception:
             pass
         return content[:2000]
     ```
  2. **Sanitize Restored History Tool Messages**:
     When reconstructing `ToolMessage` instances from `chat_record.messages`, pass `m_data.get("content", "")` through `prune_and_sanitize_tool_output`.
  3. **Enforce Response Limit Guards**:
     Set lower default `limit` parameters on agent tools (e.g., `limit: int = 5` for `list_applications`).

---

### 2.3 Repeated Context Transmission in Multi-Section Interview Guide Generation
* **Affected Component / File**: `backend/app/services/interview_guide_graph.py` (`section_generator_node`, `SECTION_DESCRIPTIONS`)
* **Static Pattern Analysis**:
  The interview guide graph generates sections sequentially by calling `section_generator_node` for each item in `target_sections` (up to 6 sections). On **every section iteration**, the node formats and sends full copies of:
  - `jd_text[:4000]` (~1,000 tokens)
  - `cv_text[:4000]` (~1,000 tokens)
  - `company_context` (~500 tokens)
  - System prompt `interview_guide` (~500 tokens)
* **Performance & Resource Degradation**:
  * **Redundant Token Ingestion**: Generating a complete 6-section guide transmits the exact same ~3,000 tokens of input context 6 separate times, resulting in 18,000+ redundant input tokens per guide request.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `section_generator_node`, `SECTION_DESCRIPTIONS`, `interview_guide`
* **Step-by-Step Remediation Plan**:
  1. **Option A: Batch Single-Pass Generation**:
     Modify the graph to issue a single LLM invocation that requests structured JSON/HTML output for all selected sections in `target_sections` simultaneously, returning a dictionary of section HTML blocks.
  2. **Option B: Provider Prompt Caching Headers**:
     If sequential section generation is required for UI streaming, append provider-specific prompt caching headers (such as Anthropic's `"type": "ephemeral"` or OpenAI's automatic prompt caching) on static prompt blocks (`jd_text`, `cv_text`, system prompt) so that subsequent turns reuse cached tokens at a 90% cost/latency reduction.

---

### 2.4 Uncached Database Prompt Lookup Invocations
* **Affected Component / File**: `backend/app/core/prompts.py` (`get_prompt_template`) & `backend/app/services/llm.py`
* **Static Pattern Analysis**:
  `get_prompt_template(session, prompt_name)` executes a database query (`select(PromptModel.template).where(...)`) on every single LLM call across all services:
  ```python
  stmt = select(PromptModel.template).where(PromptModel.name == prompt_name)
  result = await session.execute(stmt)
  ```
  There is no in-memory cache layer for prompt templates. Furthermore, `DEFAULT_PROMPTS` contains duplicate prompt text (e.g., `"email_extraction"` and `"extraction"` are identical 100-line strings).
* **Performance & Resource Degradation**:
  * **I/O Bottleneck**: Unnecessary SQL query overhead prior to every LLM invocation adds latency and database connection overhead.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `get_prompt_template`, `DEFAULT_PROMPTS`, `PromptModel`
* **Step-by-Step Remediation Plan**:
  1. **Add In-Memory Prompt Cache**:
     In `prompts.py`, introduce a global dict `_PROMPT_CACHE: dict[str, str] = {}` and an `asyncio.Lock()`.
  2. **Check Cache Before DB Query**:
     In `get_prompt_template`, check if `prompt_name` exists in `_PROMPT_CACHE`. If present, return immediately without touching PostgreSQL.
  3. **Add Cache Invalidation Hook**:
     Expose `invalidate_prompt_cache(prompt_name: str | None = None)` and call it inside the admin router when prompt templates are edited via API (`PUT /prompts/{name}`).
  4. **Deduplicate Default Prompts**:
     Alias `DEFAULT_PROMPTS["email_extraction"] = DEFAULT_PROMPTS["extraction"]` to eliminate duplicate prompt memory storage.

---

## 3. Implementation & Concurrency Bottlenecks

### 3.1 Inline Blocking Database Writes in Tracing Callback Lifecycle
* **Affected Component / File**: `backend/app/services/postgres_tracer.py` (`PostgresTracer`, `_persist_run`)
* **Static Pattern Analysis**:
  `PostgresTracer` inherits from `AsyncBaseTracer`. In `_persist_run`:
  ```python
  async def _persist_run(self, run: Run) -> None:
      ...
      async with AsyncSessionLocal() as session:
          event = TraceEventModel(...)
          session.add(event)
          await session.commit()
      ...
      finally:
          self.run_map.clear()
  ```
  Every trace event triggers a synchronous `await session.commit()` inside the primary execution pipeline of the LLM call. Additionally, calling `self.run_map.clear()` in `finally:` clears global run mappings for concurrent tasks sharing tracer instances.
* **Performance & Resource Degradation**:
  * **Latency Injection**: Adds database disk write latency directly to the critical path of every LLM and chain invocation.
  * **Concurrency Bug Risk**: Clearing `self.run_map` globally corrupts active run state for concurrent async LLM invocations.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `PostgresTracer`, `_persist_run`, `self.run_map.clear()`
* **Step-by-Step Remediation Plan**:
  1. **Background Task Offloading**:
     In `PostgresTracer`, track pending background persistence tasks in `self._background_tasks: set[asyncio.Task] = set()`.
  2. **Non-Blocking Task Dispatch**:
     Refactor `_persist_run(self, run: Run)` to spawn `task = asyncio.create_task(self._persist_run_async(run))` without awaiting it in the critical request path. Add a completion callback to discard finished tasks (`task.add_done_callback(self._background_tasks.discard)`).
  3. **Remove Global `self.run_map.clear()`**:
     Delete `self.run_map.clear()` from the `finally:` block so that LangChain's `AsyncBaseTracer` cleans up run mappings per specific `run.id` without interfering with concurrent runs.
  4. **Provide Explicit `flush()` Helper**:
     Implement `async def flush(self) -> None:` that awaits `asyncio.gather(*self._background_tasks)` for test fixtures or graceful shutdown hooks.

---

### 3.2 Database Connection Pool Lock During External Embedding Network I/O
* **Affected Component / File**: `backend/app/services/llm.py` (`generate_and_save_application_embedding`, `generate_embedding`)
* **Static Pattern Analysis**:
  `generate_and_save_application_embedding(db, application_id)` accepts an active `AsyncSession` (`db`). While holding this session open, it performs an external HTTP network request to generate vectors:
  ```python
  vector = await generate_embedding(db, str(content_to_embed))
  ```
  Inside `generate_embedding`:
  ```python
  embeddings = await get_task_embeddings_model(db)
  vector = await embeddings.aembed_query(cleaned_text)
  ```
  The database session is held open across external network calls to embedding providers (e.g., local Ollama/LM Studio or OpenAI APIs).
* **Performance & Resource Degradation**:
  * **Connection Pool Starvation**: When multiple application updates or background queue workers run concurrently, open database sessions are tied up awaiting external network I/O, leading to SQLAlchemy `TimeoutError` / pool starvation.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `generate_and_save_application_embedding`, `generate_embedding`, `aembed_query`
* **Step-by-Step Remediation Plan**:
  1. **Separate Data Reading Phase**:
     Read the required application metadata, company name, and timeline events in a short initial database transaction, then close/release the session.
  2. **Execute Network Embedding Call Out-of-Session**:
     Call `vector = await generate_embedding(None, str(content_to_embed))` using a standalone session or detached configuration lookup so that network I/O occurs with zero active DB transaction holds.
  3. **Separate Data Persistence Phase**:
     Open a new short-lived `AsyncSession` transaction solely to upsert the vector into `ApplicationEmbeddingModel` and call `await db.commit()`.

---

### 3.3 Synchronous Full-Graph Execution & Lack of SSE Streaming in Interview Guide
* **Affected Component / File**: `backend/app/services/interview_guide.py` (`generate_interview_guide`) & `backend/app/routers/applications.py`
* **Static Pattern Analysis**:
  The interview guide API endpoint awaits the full completion of `interview_guide_graph.ainvoke(...)`:
  ```python
  final_state = await interview_guide_graph.ainvoke(initial_state, config=...)
  ```
  The client must wait for 1 web research step + $N$ sequential section generation steps before receiving any HTTP response. No Server-Sent Events (SSE) or WebSocket streaming is utilized for guide generation.
* **Performance & Resource Degradation**:
  * **High Latency & Request Timeout Risk**: Generation takes 20 to 50 seconds depending on LLM model latency. High risk of HTTP client timeouts (e.g. 30s gateway timeout).
  * **Poor Perceived UX**: User interface shows a spinner with zero progress feedback until the entire guide is finished.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `interview_guide_graph.ainvoke`, `generate_interview_guide`, `GenerateInterviewGuideRequest`
* **Step-by-Step Remediation Plan**:
  1. **Create Streaming Generator Function**:
     In `interview_guide.py`, add `generate_interview_guide_stream(db, application_id, request)` utilizing `interview_guide_graph.astream(...)`:
     ```python
     async for event in interview_guide_graph.astream(initial_state, config=..., stream_mode="updates"):
         for node_name, node_output in event.items():
             if "completed_sections" in node_output:
                 latest_section = node_output["completed_sections"][-1]
                 yield f"data: {json.dumps({'node': node_name, 'section_html': latest_section})}\n\n"
     ```
  2. **Add SSE Endpoint to Application Router**:
     In `routers/applications.py`, expose `POST /applications/{id}/interview-guide/stream` returning FastAPI's `StreamingResponse(generate_interview_guide_stream(...), media_type="text/event-stream")`.
  3. **Update Frontend UI Handler**:
     Connect the frontend `InterviewGuideView` to listen to SSE events and render section cards incrementally as events arrive.

---

### 3.4 Uncached Embeddings Model Re-instantiation in Agent Semantic Search Tool
* **Affected Component / File**: `backend/app/services/agent_tools.py` (`execute_semantic_vector_search`)
* **Static Pattern Analysis**:
  The `semantic_vector_search` tool function calls `await generate_embedding(db, query)` every time it is invoked by the conversational agent. `generate_embedding` calls `get_task_embeddings_model(db)` which re-evaluates database task bindings and initializes `init_embeddings(...)` on every call.
* **Performance & Resource Degradation**:
  * **Redundant Model Initialization**: Instantiating embedding model objects repeatedly during agent tool-calling turns adds unnecessary object creation and configuration resolution overhead.
* **Implementation Strategy & Search Vectors**:
  * **Search Vectors**: `execute_semantic_vector_search`, `generate_embedding`, `get_task_embeddings_model`
* **Step-by-Step Remediation Plan**:
  1. **Add Embeddings Model Instance Cache**:
     In `llm_factory.py`, maintain `_EMBEDDINGS_MODEL_CACHE: dict[str, Embeddings] = {}` keyed by `(provider_type, model_name, base_url)`.
  2. **Reuse Cached Embedding Model**:
     In `get_task_embeddings_model`, check if an identical configuration instance already exists in `_EMBEDDINGS_MODEL_CACHE`. If match exists, return the cached `Embeddings` instance directly.
  3. **Provide Invalidation Mechanism**:
     Clear `_EMBEDDINGS_MODEL_CACHE` whenever AI Provider settings or Task Bindings are updated via administrative routers (`/ai-config/bindings`).

---

## Summary Matrix of Diagnostic Findings & Remediation Procedures

| Diagnostic Area | Primary Affected Component | Root Cause | Severity / Impact | Remediation Summary |
| :--- | :--- | :--- | :--- | :--- |
| **Graph Topology** | `interview_guide_graph.py` | State index routing without safety loop bounds | High (Infinite loop risk) | Add `iteration_count` state counter & circuit breaker guard in `should_continue_sections`. |
| **Graph Topology** | `agent_chat.py` | Serial execution of multiple tool calls per turn | Medium (High latency) | Execute tool calls in parallel using `asyncio.gather(*[tool.ainvoke(...)])`. |
| **Graph Topology** | `intake_graph.py` | Checkpointer serialization of unpruned raw text | Medium (Postgres DB bloat) | Route terminal graph exits through `prune_terminal_state_node` to clear transient strings. |
| **Prompt & Context** | `llm.py` (`extract_job_spec`) | Unbounded raw scraped HTML/markdown injection | High (Token cost & noise) | Strip HTML DOM boilerplate & call `truncate_text_semantically(data, max_chars=12000)`. |
| **Prompt & Context** | `agent_chat.py` | Unsanitized historical `ToolMessage` array ingestion | High (Quadratic token bloat) | Apply `prune_and_sanitize_tool_output` to limit array items in restored tool messages. |
| **Prompt & Context** | `interview_guide_graph.py` | Duplicate transmission of 3,000+ token context | Medium (Redundant input tokens) | Use single-pass multi-section generation or provider prompt caching headers. |
| **Prompt & Context** | `prompts.py` | Uncached SQL query per prompt lookup | Low (Unnecessary DB reads) | Wrap `get_prompt_template` with in-memory `_PROMPT_CACHE` and invalidation hooks. |
| **Concurrency** | `postgres_tracer.py` | Synchronous inline `commit()` during tracer callback | High (Pipeline latency & state bug) | Offload trace persistence to non-blocking background `asyncio.Task` & remove global `run_map.clear()`. |
| **Concurrency** | `llm.py` | DB session held open during network embedding I/O | High (DB connection pool exhaustion) | Decouple DB reads and vector updates into separate short transactions around network I/O. |
| **Concurrency** | `interview_guide.py` | Synchronous `ainvoke` blocking HTTP response | High (UX delay & HTTP timeout) | Expose SSE endpoint `POST /applications/{id}/interview-guide/stream` using `astream`. |
| **Concurrency** | `agent_tools.py` | Re-initialization of embedding model per vector query | Low (Minor tool execution overhead) | Cache initialized `Embeddings` model instances in `llm_factory.py`. |

---
*End of Diagnostic Report (`llmdiag.md`).*
