# 🧠 Job Tracker: Local & Cloud AI Provider Setup Guide

Job Tracker is built with a flexible, model-agnostic AI engine powered by **LangChain** and **LangGraph**. It supports everything from **100% private, offline, on-premise local inference** (zero data leaves your home network) to **high-performance cloud providers** (OpenAI, Anthropic Claude, Google Gemini, OpenRouter).

All provider configurations, credentials, and task bindings are managed dynamically via the in-app Settings UI (`/settings`) and stored securely in PostgreSQL with Fernet symmetric encryption.

---

## 🔒 Security & Privacy Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Job Tracker Architecture                         │
│                                                                          │
│  [ Web UI / Extension ]                                                  │
│          │                                                               │
│          ▼                                                               │
│  [ FastAPI Backend ] ─── (Fernet Decrypt) ───► [ PostgreSQL Settings ]   │
│          │                                                               │
│          ▼                                                               │
│  [ FailoverChatModel / Dynamic Router ]                                  │
│     ├─── Primary Provider (e.g., Local LM Studio / Ollama)               │
│     │      └── (Connection refused / Timeout) ──► Transparent Failover   │
│     └─── Secondary Fallback Provider (e.g., OpenAI / Gemini)             │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Runtime Fernet Credential Encryption:** API keys and OAuth secrets are encrypted at rest in PostgreSQL using a machine-specific key (`SECRET_KEY`).
- **Client-Side PII Scrubbing:** Before any candidate CV data is transmitted to an LLM prompt, Job Tracker can automatically redact sensitive personal information (phone numbers, physical addresses, personal email addresses) while retaining skills and project impact metrics.
- **Zero Lock-In:** You can switch models or providers per-task at any time without restarting Docker containers.

---

## 💻 100% Private Offline Local AI

Local inference ensures that your resumes, application histories, and recruiter emails are processed entirely on your local machine or private home lab.

---

### 1. LM Studio

[LM Studio](https://lmstudio.ai/) provides a user-friendly desktop GUI with accelerated GPU inference (Metal on Apple Silicon, CUDA on NVIDIA, ROCm on AMD).

#### A. Setup & Model Download
1. Download and install LM Studio from [lmstudio.ai](https://lmstudio.ai/).
2. In the Search tab, download one of our recommended models:
   - **`qwen2.5-7b-instruct`** or **`qwen2.5-14b-instruct`** *(Top recommendation for general extraction and matching)*
   - **`qwen2.5-coder-7b-instruct`** *(Excellent structured JSON output)*
   - **`deepseek-r1-distill-qwen-7b`** or **`deepseek-r1-distill-qwen-14b`** *(Advanced reasoning & gap analysis)*
   - **`llama-3.2-3b-instruct`** *(Ultra-fast, lightweight for laptops with 8GB RAM)*

#### B. Configure Local Server in LM Studio
1. Open the **Local Server** (Developer) tab in LM Studio (`<->` icon).
2. Load your downloaded model.
3. Configure the server parameters:
   - **Context Length:** Set to at least **8,192** tokens (16,384 or 32,768 recommended for lengthy CVs and job descriptions).
   - **GPU Offload:** Set to **Max** for hardware acceleration.
   - **Serve on Local Network (CORS):** Check **"Enable CORS"** and set Host to `0.0.0.0` or `127.0.0.1`.
   - **Port:** Default is `1234`.
4. Click **"Start Server"**.

#### C. In-App Configuration in Job Tracker
1. Navigate to **Settings** (`/settings`) ➜ **AI Providers** ➜ **Add Provider** (or use the Onboarding Wizard).
2. Select the **Local LM Studio** preset.
3. Set **Base URL**:
   - If Job Tracker is running in Docker on the same machine:
     ```
     http://host.docker.internal:1234/v1
     ```
   - If running on your local LAN (e.g., a separate desktop):
     ```
     http://192.168.1.150:1234/v1
     ```
4. **API Key:** Leave empty or type `lm-studio`.
5. Click **"Test Connection"**. Job Tracker will ping the endpoint and discover all loaded models.
6. Click **Save Provider**.

---

### 2. Ollama

[Ollama](https://ollama.com/) is a lightweight, command-line local LLM runner optimized for macOS, Linux, and Windows.

#### A. Install & Pull Models
Install Ollama and pull your desired models:
```bash
# Pull chat/extraction model
ollama run qwen2.5:7b

# Pull reasoning model (optional)
ollama run deepseek-r1:8b

# Pull vector embedding model (for pgvector semantic search)
ollama pull nomic-embed-text
```

#### B. Enable Network Access for Docker
By default, Ollama only listens on `127.0.0.1`. To allow Job Tracker (inside Docker) to connect:
- **Linux (`systemd`):**
  ```bash
  sudo systemctl edit ollama.service
  ```
  Add the following environment variables:
  ```ini
  [Service]
  Environment="OLLAMA_HOST=0.0.0.0:11434"
  Environment="OLLAMA_ORIGINS=*"
  ```
  Save and restart:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl restart ollama
  ```
- **macOS:**
  ```bash
  launchctl setenv OLLAMA_HOST "0.0.0.0:11434"
  launchctl setenv OLLAMA_ORIGINS "*"
  ```
  Restart the Ollama macOS app.
- **Windows:**
  Set system environment variables `OLLAMA_HOST=0.0.0.0:11434` and `OLLAMA_ORIGINS=*` via Settings ➜ System Properties ➜ Environment Variables, then restart Ollama from the taskbar.

#### C. In-App Configuration in Job Tracker
1. Go to **Settings** ➜ **AI Providers** ➜ **Add Provider**.
2. Select the **Local Ollama** preset.
3. Set **Base URL**:
   ```
   http://host.docker.internal:11434/v1
   ```
4. Click **"Test Connection"** and choose `qwen2.5:7b` (or your pulled model).

---

### 3. vLLM / Custom OpenAI-Compatible Inference Server

If you run high-throughput inference engines such as [vLLM](https://github.com/vllm-project/vllm), [TGI](https://github.com/huggingface/text-generation-inference), [LocalAI](https://localai.io/), or [Aphrodite Engine]:

1. Start your server with an OpenAI-compatible endpoint (e.g. `http://0.0.0.0:8000/v1`).
2. In Job Tracker, choose the **Custom / Other Endpoint** preset.
3. Specify `http://<server-ip>:<port>/v1`, set your concurrency limit, and verify with **Test Connection**.

---

## ☁️ Cloud AI Providers

Job Tracker supports premier cloud foundation models for maximum speed, multilingual fidelity, and reasoning capabilities.

---

### 1. OpenAI

OpenAI provides top-tier general reasoning and structured extraction.

- **Recommended Models:**
  - **`gpt-4o-mini`**: Fast, cost-efficient, outstanding JSON extraction fidelity. (Recommended for `GLOBAL_DEFAULT`, `JD_EXTRACTION`, and `EMAIL_EXTRACTION`).
  - **`gpt-4o`**: Complex multi-stage analysis, in-depth gap evaluation, and mock interview coaching.
  - **`o3-mini`**: Multi-step reasoning and deep resume tailoring.
  - **`text-embedding-3-small`**: Fast, 1536-dimension embeddings for semantic search.
- **Setup:**
  1. Generate an API key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
  2. In Job Tracker, choose **OpenAI**, paste your `sk-...` API key, and test connection.
- **Data Privacy:** OpenAI's Commercial API terms provide **Zero Data Retention (ZDR)** and strictly do not train on API inputs/outputs.

---

### 2. Anthropic Claude

Anthropic models excel at nuanced document analysis, resume writing, and contextual reasoning.

- **Recommended Models:**
  - **`claude-3-7-sonnet-20250219`**: State-of-the-art hybrid reasoning with configurable thinking budgets.
  - **`claude-3-5-sonnet-20241022`**: Superior prose quality for cover letters and interview preparation guides.
  - **`claude-3-5-haiku-20241022`**: Ultra-fast, low latency for email classification and web scraping.
- **Setup:**
  1. Generate an API key at [console.anthropic.com](https://console.anthropic.com/).
  2. In Job Tracker, select **Anthropic**, paste your `sk-ant-...` key, and save.
- **Extended Thinking:** Job Tracker natively supports Anthropic thinking token budgets (`low`: 1024 tokens, `medium`: 2048 tokens, `high`: 4096 tokens) for complex fit assessments.

---

### 3. Google Gemini

Google Gemini delivers high-speed inference with generous free-tier quotas.

- **Recommended Models:**
  - **`gemini-2.0-flash`**: High-speed, multimodal-capable workhorse with massive context handling.
  - **`gemini-2.0-flash-lite`**: Lightweight, rapid response times for real-time interactive tasks.
  - **`gemini-1.5-pro`**: In-depth analytical evaluations.
  - **`text-embedding-004`**: High-accuracy semantic embeddings.
- **Setup:**
  1. Get a free API key at [Google AI Studio](https://aistudio.google.com/).
  2. In Job Tracker, select **Google Gemini**, enter your API key, and test connection.
- **Free Tier:** Google AI Studio offers a free tier suitable for personal job search workloads.

---

### 4. OpenRouter (Unified Model Gateway)

[OpenRouter](https://openrouter.ai/) provides a single unified API to access hundreds of models (DeepSeek-R1, Meta Llama 3.3 70B, Qwen, Mistral, Command R+).

- **Recommended Models:**
  - `deepseek/deepseek-r1` *(Deep reasoning at low cost)*
  - `meta-llama/llama-3.3-70b-instruct` *(Top open-weight flagship)*
  - `anthropic/claude-3.5-haiku`
- **Setup:**
  1. Generate an API key at [openrouter.ai/keys](https://openrouter.ai/keys).
  2. In Job Tracker, select **OpenRouter**, paste your key (`sk-or-v1-...`), and test connection.

---

## 🎛️ AI Task Studio & Per-Task Bindings

Rather than using a single model for every task, Job Tracker's **AI Task Studio** (`/settings` ➜ **AI Task Studio**) allows you to assign specialized models, temperatures, and reasoning budgets to distinct pipeline stages.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           AI Task Studio Matrix                          │
├───────────────────────┬──────────────────────────┬─────────────┬─────────┤
│ Pipeline Task         │ Recommended Model Type   │ Temperature │ Reason  │
├───────────────────────┼──────────────────────────┼─────────────┼─────────┤
│ GLOBAL_DEFAULT        │ Fast Chat / Generalist   │ 0.2         │ None    │
│ JD_EXTRACTION         │ High JSON Fidelity       │ 0.0         │ None    │
│ EMAIL_EXTRACTION      │ Fast Parsing / Low Cost  │ 0.1         │ None    │
│ JOB_ASSESSMENT        │ Reasoning / Analysis     │ 0.2         │ Medium  │
│ INTERVIEW_GUIDE       │ High Context / Synthesis │ 0.3 - 0.4   │ High    │
│ COVER_LETTER          │ Creative / Nuanced Prose │ 0.3         │ Medium  │
│ cv_anonymization      │ Strict Extraction        │ 0.2         │ Medium  │
│ AGENT_REASONING       │ Multi-Turn Conversational│ 0.5         │ High    │
│ EMBEDDING             │ Dense Vector Embedding   │ N/A         │ N/A     │
└───────────────────────┴──────────────────────────┴─────────────┴─────────┘
```

### Task Descriptions
1. **`GLOBAL_DEFAULT`**: Catch-all default model. Any task that is not explicitly customized automatically inherits this provider and model.
2. **`JD_EXTRACTION`**: Parses raw web HTML/markdown from job postings into structured JSON schemas (title, company, salary ranges, technical skill lists).
3. **`EMAIL_EXTRACTION`**: Scans recruitment emails to extract sender details, interview dates, rejection notices, and pending action items.
4. **`JOB_ASSESSMENT`**: Performs a comprehensive audit comparing your candidate CV against the job description, computing fit percentages, match rationales, and strategic gap-closing tips.
5. **`INTERVIEW_GUIDE`**: Synthesizes a structured interview playbook with STAR behavioral stories, company context briefings, and technical defense questions.
6. **`COVER_LETTER`**: Drafts personalized, high-impact cover letters referencing your real past achievements against company values.
7. **`cv_anonymization`**: De-identifies resumes for PII protection and extracts standardized skill taxonomies.
8. **`AGENT_REASONING`**: Powers the conversational assistant (`/assistant`) and mock interview simulator.
9. **`EMBEDDING`**: Generates dense 768- or 1536-dimensional vectors for semantic search in PostgreSQL (`pgvector`).

---

## 🛡️ Transparent Auto-Failover (`FailoverChatModel`)

Job Tracker includes built-in fault tolerance. If your primary AI provider becomes unavailable (e.g. your local LM Studio instance is shut down or goes out of memory), requests are **automatically re-routed to your designated fallback provider** with zero data loss or user disruption.

```
[ Primary: Local LM Studio ] ──(Timeout / Connection Refused)──► [ Failover: Cloud Provider ]
                                                                        │
                                                          [ Logs Failover Telemetry Trace ]
```

### How to Configure Fallback:
1. In **Settings** ➜ **AI Providers**, add both your Primary provider (e.g. *Local LM Studio*) and a Secondary provider (e.g. *OpenAI* or *Google Gemini*).
2. On your Secondary provider card, toggle **"Designated Fallback Provider"**.
3. When active, if the primary provider returns `ConnectError`, `ConnectionRefused`, or times out, Job Tracker automatically executes the task on the fallback provider and logs a diagnostic trace event under `/diagnostics`.

---

## 🔬 Diagnostics & Model Probing

Job Tracker includes an intelligent **Model Prober** in the Settings UI:
- **1-Click Model Discovery:** Automatically queries `/v1/models` to list all models available on your endpoint.
- **Thinking / Reasoning Detection:** Automatically identifies whether a model supports reasoning tags (`<think>`, `reasoning_effort`, `thinking_config`) and configures appropriate parameter envelopes.
- **Latency & Health Audits:** Real-time latency tracking and telemetry recording for all LLM calls.
