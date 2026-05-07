# Technical Requirements Document — SF Research Agent

## 1. System Architecture

```
                        ┌─────────────────────────────┐
                        │        Vue 3 Frontend        │
                        │   (Vite, ChatWindow.vue)     │
                        └──────────────┬──────────────┘
                                       │  HTTP / SSE
                        ┌──────────────▼──────────────┐
                        │       FastAPI Backend        │
                        │   /api/chat/* endpoints      │
                        │   /api/settings/*            │
                        │   /api/usage/*               │
                        └──────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │     LangGraph Orchestrator   │
                        │  (5-node StateGraph)         │
                        └──┬───────┬────────┬─────────┘
                           │       │        │
              ┌────────────▼─┐  ┌──▼──┐  ┌─▼──────────┐
              │   Perplexity │  │Gemini│  │   Claude   │
              │  Sonar Pro   │  │2.5Pro│  │ Sonnet 4.6 │
              │(live web     │  │(arch │  │(intake,    │
              │ search)      │  │ patt)│  │ write, rev)│
              └──────────────┘  └─────┘  └────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │   PostgreSQL / SQLite        │
                        │  (LangGraph checkpointer     │
                        │   + agent_sessions           │
                        │   + app_settings             │
                        │   + token_usage)             │
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
    session_id:           str
    created_at:           str
    current_stage:        Literal["intake","discovery","research","review","approval","complete","halted","invalid_input"]
    revision_count:       int
    source_type:          Literal["brief","document","image"]
    uploaded_file_path:   str
    uploaded_image_path:  str
    raw_document_text:    str
    project_brief:        str
    discovery_questions:  list[DiscoveryQuestion]
    discovery_complete:   bool
    document_draft:       str
    document_version:     int
    review_result:        Optional[ReviewResult]
    approval_result:      Optional[ApprovalResult]
    messages:             Annotated[list[BaseMessage], add_messages]
    usage_records:        Annotated[list[dict], operator.add]   # appended by each agent
```

### Graph topology

```
intake ──► discovery ⟲ (interrupt per question group)
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

## 4. LLM Model Assignment

| Agent | Model | Rationale |
|---|---|---|
| Intake (text extraction) | Claude Sonnet 4.6 | Reasoning + document understanding |
| Intake (image validation) | Claude Sonnet 4.6 (Vision) | Multimodal — validates architecture diagrams |
| Discovery | Claude Sonnet 4.6 | Reasoning — classifies discussion type, generates targeted questions |
| Researcher (Step 1a) | Perplexity Sonar Pro | Real-time web search — current Salesforce limits, citations, release notes |
| Researcher (Step 1b) | Gemini 2.5 Pro | Large context + architectural pattern reasoning |
| Researcher (Step 2) | Claude Sonnet 4.6 | Document writing — follows structured 8-section template |
| Reviewer | Claude Sonnet 4.6 | Reasoning — structured checklist evaluation |
| Approver | Claude Sonnet 4.6 | Reasoning — 7-lens strategic review |
| Session title generation | Claude Haiku 4.5 | Fast + cost-efficient, fires in background |

### Parallel execution (Researcher)

Perplexity and Gemini run concurrently via `ThreadPoolExecutor(max_workers=2)`. Claude writing waits for both to complete.

### Token usage capture

Every LLM call captures `response.usage_metadata`. Structured-output calls use `include_raw=True` to access token counts alongside the parsed Pydantic result. Usage records are appended to `AgentState.usage_records` and flushed to the `token_usage` table after each graph stream segment.

---

## 5. API Endpoints

### Chat (SSE streaming)

| Method | Path | Description |
|---|---|---|
| POST | `/api/chat/start` | Start new session from text brief; returns SSE stream |
| POST | `/api/chat/upload` | Start new session from file upload; returns SSE stream |
| POST | `/api/chat/reply/{session_id}` | Resume graph after interrupt (discovery answer / confirmation) |
| GET | `/api/chat/document/{session_id}` | Fetch current document draft as JSON |

### Session management

| Method | Path | Description |
|---|---|---|
| GET | `/api/chat/sessions` | List all sessions `{pinned:[...], recent:[...]}` |
| GET | `/api/chat/session/{id}/restore` | Load full session state for frontend reconstruction |
| POST | `/api/chat/session/{id}/pin` | Pin session (max 10) |
| DELETE | `/api/chat/session/{id}/pin` | Unpin session |
| PATCH | `/api/chat/session/{id}` | Rename session `{"title": "..."}` |
| DELETE | `/api/chat/session/{id}` | Delete session + uploaded files |

### Settings

| Method | Path | Description |
|---|---|---|
| GET | `/api/settings/keys` | Returns `{anthropic: bool, perplexity: bool, google: bool}` — configured status only, never values |
| POST | `/api/settings/keys` | Validate keys against provider APIs, then encrypt and store. Returns HTTP 422 with per-key errors if any key is rejected. |

### Usage

| Method | Path | Description |
|---|---|---|
| GET | `/api/usage/session/{id}` | Token usage + cost breakdown by model for one session |
| GET | `/api/usage/summary` | Total usage + breakdown across all sessions |

### System

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe — returns `{"status":"ok","graph":"ready"}` |

### SSE Event Types

| Event | Payload | Description |
|---|---|---|
| `stage_start` | `{stage, label}` | Agent node started |
| `token` | `{content}` | LLM text token (suppressed for researcher) |
| `stage_end` | `{stage}` | Agent node completed |
| `document_ready` | `{version, session_id}` | Researcher produced a document |
| `review_complete` | `{passed, feedback, critical_issues}` | Reviewer verdict |
| `approval_complete` | `{status, comments, required_changes}` | Approver verdict |
| `confirm_understanding` | `{content, session_id}` | Intake paused for user confirmation |
| `question` | `{questions[], session_id}` | Discovery paused for user answers |
| `done` | `{status, document_version, revision_count}` | Graph completed or halted |
| `error` | `{message}` | Unhandled exception |

---

## 6. Database Schema

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
    encrypted_value TEXT NOT NULL,         -- Fernet-encrypted API key
    updated_at      TEXT NOT NULL
);

CREATE TABLE token_usage (
    thread_id     TEXT NOT NULL,
    agent         TEXT NOT NULL,           -- "intake" | "discovery" | "researcher" | etc.
    model         TEXT NOT NULL,           -- "claude-sonnet-4-6" | "sonar-pro" | etc.
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd      REAL DEFAULT 0,
    created_at    TEXT NOT NULL
);
```

**Usage query pattern:** group by `model` to aggregate across all agents that used the same model.

---

## 7. API Key Security

### Storage

- API keys are **never stored in `.env`** and never committed to source control
- Stored encrypted in `app_settings` table using **Fernet symmetric encryption** (AES-128-CBC + HMAC)
- Encryption key (`SETTINGS_SECRET`) lives only in `.env` and never reaches the client

### Validation

Before a key is saved, it is validated against its provider's API:
- **Anthropic** — `anthropic.Anthropic(api_key=key).models.list()`
- **Perplexity** — `openai.OpenAI(api_key=key, base_url=...).models.list()`
- **Google** — `google.generativeai.list_models()`

All three validations run in parallel via `ThreadPoolExecutor`. HTTP 422 is returned with per-key error messages if any key is rejected.

### Runtime

An in-memory cache holds decrypted keys after startup. Agents call `get_keys()` synchronously. If any key is missing, a `RuntimeError` with a user-friendly message propagates as an SSE `error` event.

---

## 8. File Handling

### Upload flow

1. Extension validated (415 if unsupported)
2. Size checked against `MAX_FILE_SIZE_MB` (413 if exceeded) — both client and server
3. Saved to `UPLOAD_DIR/{stem}_{uuid}{ext}`
4. Documents: text extracted immediately; stored in `AgentState.raw_document_text`
5. Images: saved to disk; Claude Vision reads from disk during intake

### Supported formats

| Type | Extensions |
|---|---|
| Documents | `.pdf`, `.docx`, `.doc`, `.txt`, `.md` |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` |

---

## 9. Memory & Token Management

### Message windowing (Discovery agent)

Only the last 30 messages from `state.messages` are passed to the Discovery LLM.

### Selective context per agent

| Agent | Messages passed | Context source |
|---|---|---|
| Discovery | Last 30 messages | Conversational history needed |
| Researcher (all 3 LLMs) | None | Uses structured `state.discovery_questions` |
| Reviewer | None | Uses `state.document_draft` + `state.discovery_questions` |
| Approver | None | Uses `state.project_brief` + `state.document_draft` + `state.review_result` |

---

## 10. Error Resilience

### LLM retry (all agents)

`invoke_with_retry` wraps every LLM call with tenacity:
- Retries on: rate limits (429), timeouts, 503, connection errors, "overloaded"
- Policy: exponential backoff, min 2s, max 32s, up to 5 attempts

### Database backend switching

The checkpointer factory reads `DB_BACKEND` at startup. Switch between SQLite and PostgreSQL via `.env` only — no code changes required.

---

## 11. Security

| Concern | Mitigation |
|---|---|
| API keys | Stored Fernet-encrypted in DB. Never in `.env`, never committed. Never returned to client. |
| SETTINGS_SECRET | In `.env` only (gitignored). Protects all stored API keys. |
| CORS | `ALLOWED_ORIGINS` env var; defaults to `*` for dev, must be restricted in prod |
| File uploads | Extension allowlist + size limit enforced both client and server |
| Session isolation | Sessions identified by UUID4 `thread_id`; no auth currently (add JWT/API key before production exposure) |
| SQL injection | All queries use parameterised statements |

---

## 12. Model Pricing (for cost estimation)

Prices in USD per 1,000,000 tokens. Update `backend/utils/pricing.py` when rates change.

| Model | Input | Output |
|---|---|---|
| `claude-sonnet-4-6` | $3.00 | $15.00 |
| `claude-haiku-4-5-20251001` | $0.80 | $4.00 |
| `sonar-pro` | $3.00 | $15.00 |
| `gemini-2.5-pro` | $1.25 | $10.00 |

---

## 13. Performance Targets (10 concurrent sessions)

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
| API key validation (Save Settings) | 2–5s (3 providers in parallel) |

---

## 14. Observability

- Structured logging via Python `logging` module
- Startup validation: missing `SETTINGS_SECRET` or `POSTGRES_URI` cause immediate `sys.exit(1)`
- `/health` endpoint for load balancer probes
- Session cleanup logs count of expired sessions deleted
- LangGraph pending deprecation warnings suppressed

---

## 15. Future Considerations

| Item | Notes |
|---|---|
| Authentication | Add JWT or API key auth to all `/api/` routes before public deployment |
| Rate limiting | Add `slowapi` to limit `/start` and `/upload` per IP |
| Switch to Gemini Search | Replace Perplexity with Gemini 2.5 Pro + Search grounding when available; one function change in `backend/agents/researcher.py` |
| RAG integration | Connect Salesforce Help documentation as a vector store for the research step |
| Salesforce Metadata API | Validate architecture recommendations against real org limits via Tooling API |
| Export to Word | Add DOCX export alongside PDF and Markdown |
| Multi-user / teams | Add workspace concept; share sessions between team members |
| Per-user key isolation | If multi-user is added, scope API keys per user rather than globally |
