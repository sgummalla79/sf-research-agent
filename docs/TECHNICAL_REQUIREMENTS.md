# Technical Requirements — Technical Architecture Agent

## 1. System Architecture

```
                        ┌─────────────────────────────┐
                        │        Vue 3 Frontend        │
                        │  (Vite, ChatWindow.vue,      │
                        │   ChatInput.vue)             │
                        └──────────────┬──────────────┘
                                       │  HTTP / SSE
                        ┌──────────────▼──────────────┐
                        │       FastAPI Backend        │
                        │   /api/chat/*                │
                        │   /api/flows/*               │
                        │   /api/prompts/*             │
                        │   /api/settings/*            │
                        │   /api/usage/*               │
                        └──────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │     LangGraph Orchestrator   │
                        │  chat node + 5-stage flow    │
                        └──┬───────┬────────┬─────────┘
                           │       │        │
              ┌────────────▼─┐  ┌──▼──┐  ┌─▼──────────┐
              │   Perplexity │  │Gemini│  │   Claude   │
              │  Sonar Pro   │  │2.5Pro│  │ Sonnet 4.6 │
              │ (web search) │  │(arch │  │(intake,    │
              │              │  │ patt)│  │ write, rev)│
              └──────────────┘  └─────┘  └────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │   PostgreSQL / SQLite        │
                        │  (LangGraph checkpointer     │
                        │   + agent_sessions           │
                        │   + app_settings             │
                        │   + token_usage              │
                        │   + agent_prompt_versions    │
                        │   + flow_prompt_snapshots)   │
                        └─────────────────────────────┘
```

---

## 2. Tech Stack

### Backend

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.11+ |
| API framework | FastAPI | 0.115+ |
| ASGI server | Uvicorn / Gunicorn | 0.30+ / latest |
| AI orchestration | LangGraph | 0.2+ |
| LLM client (Claude) | langchain-anthropic | 0.2+ |
| LLM client (Gemini) | langchain-google-genai | 2.0+ |
| LLM client (Perplexity) | langchain-openai (custom base URL) | 0.2+ |
| DB checkpointer (Postgres) | langgraph-checkpoint-postgres | 1.0+ |
| DB checkpointer (SQLite) | langgraph-checkpoint-sqlite | 1.0+ |
| PostgreSQL driver | psycopg3 | 3.1+ |
| SQLite driver | aiosqlite | 0.19+ |
| Retry logic | tenacity | 8.2+ |
| Encryption | cryptography (Fernet) | 42.0+ |
| File parsing | pypdf, python-docx | 4.0+ / 1.1+ |
| Env config | python-dotenv | 1.0+ |

### Frontend

| Component | Technology | Version |
|---|---|---|
| Language | JavaScript (ES2022) | — |
| Framework | Vue 3 | 3.4+ |
| Build tool | Vite | 5.0+ |
| Markdown rendering | marked | 12.0+ |
| HTTP / SSE | native `fetch` + `ReadableStream` | — |

---

## 3. LangGraph State Machine

### AgentState schema

```python
class AgentState(BaseModel):
    session_id:             str
    created_at:             str
    current_stage:          Literal["intake","discovery","research","review","approval",
                                    "complete","halted","invalid_input"]
    revision_count:         int
    source_type:            Literal["brief","document","image"]
    uploaded_file_path:     str
    uploaded_image_path:    str
    raw_document_text:      str
    project_brief:          str
    discovery_questions:    list[DiscoveryQuestion]
    discovery_complete:     bool
    document_draft:         str
    document_version:       int
    review_result:          Optional[ReviewResult]
    approval_result:        Optional[ApprovalResult]
    messages:               Annotated[list[BaseMessage], add_messages]
    usage_records:          Annotated[list[dict], operator.add]
    session_type:           Literal["chat", "agent_flow"]
    flow_id:                str
    flow_config:            dict     # prompts loaded from DB snapshot at session start
    flow_snapshot_id:       int | None
    flow_snapshot_version:  int | None
    chat_model:             str
    extended_thinking:      bool
    session_agent_config:   dict     # LLM model config locked at session start
```

### Graph topology

```
router ──► chat (free-form) ──► END
       │
       └──► intake ──► discovery ⟲ (interrupt per question group)
                           │
                           ▼ (discovery_complete=True)
                       researcher ──► reviewer ──► approver
                           ▲               │           │
                           │   (FAILED)    │           │ (REJECTED)
                           └───────────────┘           │
                           ▲                           │
                           └───────────────────────────┘
                                           │ (APPROVED)
                                          END
```

---

## 4. Agent Architecture

### BaseAgent (agents/base.py)

All single-LLM-call agents extend `BaseAgent`:

```python
class BaseAgent:
    prompt_key: str   # key in state.flow_config
    llm_slot:   str   # key in session_agent_config
    schema:     type | None = None  # Pydantic structured output

    def __call__(self, state): ...        # LangGraph node entry point
    def _build_llm(self, state): ...      # get slot LLM + optional schema wrap
    def _build_messages(self, state): ... # default: [system + human]
    def _build_human_prompt(self, state): ...  # override in subclass
    def _post_process(self, state, result, urec): ...  # override in subclass
```

| Agent | Class | Overrides |
|---|---|---|
| Discovery | `DiscoveryAgent(BaseAgent)` | `_build_messages` (windowed history), `_post_process` (interrupt loop) |
| Reviewer | `ReviewerAgent(BaseAgent)` | `_build_human_prompt`, `_post_process` |
| Approver | `ApproverAgent(BaseAgent)` | `_build_human_prompt`, `_post_process` |
| Researcher | plain function | fan-out pattern (3 LLMs in parallel) |
| Intake | plain function | IO routing (file vs image paths) |

### LLM Model Assignment

| Agent | Model | Rationale |
|---|---|---|
| Intake (text extraction) | Claude Sonnet 4.6 | Reasoning + document understanding |
| Intake (image validation) | Claude Sonnet 4.6 (Vision) | Multimodal — validates architecture diagrams |
| Discovery | Claude Sonnet 4.6 | Reasoning — classifies platform, generates targeted questions |
| Researcher (Step 1a) | Perplexity Sonar Pro | Real-time web search — official documentation, limits, release notes |
| Researcher (Step 1b) | Gemini 2.5 Pro | Large context + architectural pattern reasoning |
| Researcher (Step 2) | Claude Sonnet 4.6 | Document writing — structured multi-section output |
| Reviewer | Claude Sonnet 4.6 | Structured checklist evaluation |
| Approver | Claude Sonnet 4.6 | 7-lens strategic review |
| Chat (free-form) | User-selected | Sonnet 4.6 default; Extended Thinking via Anthropic SDK |
| Session title generation | Claude Haiku 4.5 | Fast + cost-efficient, fires in background |

---

## 5. Prompt Versioning

### Flow Config Loading (at session start)

1. Get latest `flow_prompt_snapshots` row for the flow
2. For each agent key in the snapshot's `agent_versions` map, fetch the exact published content from `agent_prompt_versions`
3. Merge DB content on top of code defaults: `flow_config = {**code_defaults, **db_prompts}`
4. Store `flow_snapshot_id` and `flow_snapshot_version` in `AgentState`

### Seeding (first boot)

If `agent_prompt_versions` has no published rows for a flow, seed all agents with v1 from the code defaults in `flows/<flow_id>.py` and create `flow_prompt_snapshots` v1.

---

## 6. API Endpoints

### Chat (SSE streaming)

| Method | Path | Description |
|---|---|---|
| POST | `/api/chat/start` | Start new session; returns SSE stream + `X-Session-Id` header |
| POST | `/api/chat/upload` | Start from file upload; returns SSE stream |
| POST | `/api/chat/reply/{id}` | Resume after interrupt (discovery answer / confirmation) |
| POST | `/api/chat/retry/{id}` | Retry interrupted session |
| GET  | `/api/chat/document/{id}` | Fetch current document draft |
| GET  | `/api/chat/session-config/{id}` | Fetch locked agent model config for a session |

### Session management

| Method | Path | Description |
|---|---|---|
| GET    | `/api/chat/sessions` | List all sessions `{pinned:[...], recent:[...]}` |
| GET    | `/api/chat/session/{id}/restore` | Load full session state |
| POST   | `/api/chat/session/{id}/pin` | Pin session (max 10) |
| DELETE | `/api/chat/session/{id}/pin` | Unpin session |
| PATCH  | `/api/chat/session/{id}` | Rename session `{"title": "..."}` |
| DELETE | `/api/chat/session/{id}` | Delete session + uploaded files |

### Flows

| Method | Path | Description |
|---|---|---|
| GET | `/api/flows` | Available agent flows + chat models + default model |

### Agent prompt versioning

| Method | Path | Description |
|---|---|---|
| GET    | `/api/prompts/{flow_id}` | All agents + current draft/published state |
| PUT    | `/api/prompts/{flow_id}/{agent_key}/draft` | Save/update draft |
| DELETE | `/api/prompts/{flow_id}/{agent_key}/draft` | Discard draft |
| POST   | `/api/prompts/{flow_id}/{agent_key}/publish` | Publish draft → new flow snapshot |
| GET    | `/api/prompts/{flow_id}/{agent_key}/history` | Published version list |
| GET    | `/api/prompts/{flow_id}/snapshots` | Flow snapshot timeline |

### Settings & providers

| Method | Path | Description |
|---|---|---|
| GET  | `/api/settings/keys` | Configured status per provider (never values) |
| POST | `/api/settings/keys` | Validate + encrypt + store API keys |

### Usage

| Method | Path | Description |
|---|---|---|
| GET | `/api/usage/session/{id}` | Token usage + cost by model for one session |
| GET | `/api/usage/summary` | Total usage across all sessions |

### System

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe — `{"status":"ok","graph":"ready"}` |

### SSE Event Types

| Event | Payload | Description |
|---|---|---|
| `stage_start` | `{stage, label}` | Agent node started |
| `token` | `{content}` | LLM text token |
| `stage_end` | `{stage}` | Agent node completed |
| `document_ready` | `{version, session_id}` | Researcher produced a document |
| `review_complete` | `{passed, feedback, critical_issues}` | Reviewer verdict |
| `approval_complete` | `{status, comments, required_changes}` | Approver verdict |
| `confirm_understanding` | `{content, session_id}` | Intake paused for confirmation |
| `question` | `{questions[], session_id}` | Discovery paused for answers |
| `done` | `{status, document_version, revision_count}` | Graph completed or halted |
| `error` | `{message}` | Unhandled exception |

---

## 7. Database Schema

### LangGraph tables (managed by LangGraph)

- `checkpoints` — full state snapshot per node execution
- `checkpoint_blobs` — content-addressed state values
- `checkpoint_writes` — in-flight node writes

### Application tables

```sql
CREATE TABLE agent_sessions (
    thread_id      TEXT PRIMARY KEY,
    created_at     TEXT NOT NULL,
    brief_snippet  TEXT,
    last_modified  TEXT,
    pinned         INTEGER DEFAULT 0,
    pinned_at      TEXT
);

CREATE TABLE app_settings (
    key_name        TEXT PRIMARY KEY,      -- "anthropic" | "perplexity" | "google"
    encrypted_value TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE app_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE token_usage (
    thread_id     TEXT NOT NULL,
    agent         TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd      REAL DEFAULT 0,
    created_at    TEXT NOT NULL
);

-- Per-agent versioned prompts
CREATE TABLE agent_prompt_versions (
    id           INTEGER PRIMARY KEY,   -- SERIAL on PostgreSQL
    flow_id      TEXT NOT NULL,         -- "architect"
    agent_key    TEXT NOT NULL,         -- "DISCOVERY_SYSTEM_PROMPT"
    version      INTEGER NOT NULL,      -- 1, 2, 3 …
    content      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'draft',  -- 'draft' | 'published'
    created_at   TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX idx_apv_flow_key ON agent_prompt_versions(flow_id, agent_key);

-- Auto-created on every publish; sessions lock to a snapshot
CREATE TABLE flow_prompt_snapshots (
    id               INTEGER PRIMARY KEY,  -- SERIAL on PostgreSQL
    flow_id          TEXT NOT NULL,
    snapshot_version INTEGER NOT NULL,
    agent_versions   TEXT NOT NULL,        -- JSON: {"DISCOVERY_SYSTEM_PROMPT": 2, …}
    created_at       TEXT NOT NULL,
    triggered_by     TEXT NOT NULL         -- which agent_key triggered this snapshot
);
```

---

## 8. API Key Security

### Storage

- API keys are **never stored in `.env`** and never committed to source control
- Stored encrypted in `app_settings` using **Fernet symmetric encryption** (AES-128-CBC + HMAC)
- Encryption key (`SETTINGS_SECRET`) lives only in `.env` and never reaches the client

### Validation

Before a key is saved, it is validated against the provider's live API. All three run in parallel via `ThreadPoolExecutor`. HTTP 422 with per-key errors if any key is rejected.

### Runtime

In-memory cache holds decrypted keys after startup. Missing key → `RuntimeError` propagates as an SSE `error` event.

---

## 9. File Handling

### Upload flow

1. Extension validated (415 if unsupported)
2. Size checked (413 if exceeded) — both client and server
3. Saved to `UPLOAD_DIR/{stem}_{uuid}{ext}`
4. Documents: text extracted immediately into `AgentState.raw_document_text`
5. Images: saved to disk; Claude Vision reads during intake

### Supported formats

| Type | Extensions |
|---|---|
| Documents | `.pdf`, `.docx`, `.doc`, `.txt`, `.md` |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` |

---

## 10. Memory & Token Management

### Message windowing (Discovery agent)

Only the last 30 messages from `state.messages` are passed to the Discovery LLM.

### Selective context per agent

| Agent | Messages | Context source |
|---|---|---|
| Discovery | Last 30 messages | Conversational history |
| Researcher (all 3) | None | `state.project_brief` + `state.discovery_questions` |
| Reviewer | None | `state.document_draft` + `state.discovery_questions` |
| Approver | None | `state.project_brief` + `state.document_draft` + `state.review_result` |

---

## 11. Error Resilience

### LLM retry (all agents)

`invoke_with_retry` wraps every LLM call with tenacity:
- Retries on: rate limits (429), timeouts, 503, connection errors, "overloaded"
- Policy: exponential backoff, min 2s, max 32s, up to 5 attempts

### Database backend switching

The checkpointer factory reads `DB_BACKEND` at startup. Switch between SQLite and PostgreSQL via `.env` — no code changes required.

---

## 12. Security

| Concern | Mitigation |
|---|---|
| API keys | Fernet-encrypted in DB. Never in `.env`, never committed. Never returned to client. |
| SETTINGS_SECRET | In `.env` only (gitignored). Protects all stored API keys. |
| CORS | `ALLOWED_ORIGINS` env var; defaults to `*` for dev, must be restricted in prod |
| File uploads | Extension allowlist + size limit enforced both client and server |
| Session isolation | Sessions identified by UUID4 `thread_id` |
| SQL injection | All queries use parameterised statements |

---

## 13. Model Pricing (for cost estimation)

Prices in USD per 1,000,000 tokens. Update `backend/utils/pricing.py` when rates change.

| Model | Input | Output |
|---|---|---|
| `claude-sonnet-4-6` | $3.00 | $15.00 |
| `claude-haiku-4-5-20251001` | $0.80 | $4.00 |
| `sonar-pro` | $3.00 | $15.00 |
| `gemini-2.5-pro` | $1.25 | $10.00 |

---

## 14. Performance Targets (10 concurrent sessions)

| Metric | Target |
|---|---|
| Session start (text brief) | < 2s to first token |
| Intake (document extraction) | < 5s to show extracted brief |
| Intake (image validation) | < 8s to show extracted brief |
| Discovery question (single) | < 3s per response |
| Researcher (parallel research + writing) | 60–120s total |
| Reviewer | < 15s |
| Approver | < 15s |
| Session list load | < 500ms |
| Session title generation | < 1s (background, non-blocking) |
| API key validation | 2–5s (3 providers in parallel) |

---

## 15. Future Considerations

| Item | Notes |
|---|---|
| Authentication | Add JWT or API key auth to all `/api/` routes before public deployment |
| Rate limiting | Add `slowapi` to limit `/start` and `/upload` per IP |
| Additional agent flows | Add `flows/<name>.py` + entry in `flows/registry.py` — no other code changes |
| RAG integration | Connect official vendor documentation as a vector store per platform |
| Export to Word | Add DOCX export alongside PDF and Markdown |
| Multi-user / teams | Add workspace concept; share sessions between team members |
| Per-user key isolation | If multi-user is added, scope API keys per user rather than globally |
