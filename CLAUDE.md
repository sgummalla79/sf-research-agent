# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Start everything (recommended)
```bash
pnpm dev          # starts backend (port 8000) + frontend (port 5173) together
pnpm stop         # stop both processes
```

### Backend only
```bash
cd backend
pip install -r requirements.txt
uvicorn api.app:app --reload --port 8000
```

### Frontend only
```bash
cd frontend
npm install
npm run dev       # port 5173, proxies /api and /auth to localhost:8000
npm run build     # outputs to frontend/dist/
```

### Health check
```bash
curl http://localhost:8000/health
# → {"status":"ok","graph":"ready"}
```

### Generate SETTINGS_SECRET (required once)
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Syntax check a Python file
```bash
python3 -m py_compile backend/<path/to/file.py>
```

## Environment Setup

Copy `backend/.env.example` to `backend/.env`. Required variables:

| Variable | Purpose |
|---|---|
| `SETTINGS_SECRET` | Fernet key for encrypting user API keys in DB |
| `JWT_SECRET` | Signs session cookies (`openssl rand -hex 32`) |
| `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET` | Auth0 OAuth |
| `DATABASE_URL` | Empty → SQLite; `postgresql://...` → PostgreSQL |

User LLM API keys (Anthropic, OpenAI, Google, Perplexity, etc.) are **not** in `.env` — they're entered via the Settings UI and stored encrypted in the database using `SETTINGS_SECRET`.

## Architecture Overview

**Pragna** is a multi-agent AI platform that runs structured pipelines ("skills") to produce Architecture Recommendation Documents. It supports free-form chat as well.

### Backend (`backend/`)

**Request flow:** FastAPI → `api/routes/chat.py` → LangGraph `astream_events` → SSE stream to browser.

**Key files:**
- `api/app.py` — FastAPI lifespan: loads DB, compiles all skill graphs, registers middleware
- `api/routes/chat.py` — All SSE streaming endpoints; `_stream_graph()` is the central SSE emitter
- `state.py` — `AgentState` (Pydantic + LangGraph reducers) — the single state object flowing through the pipeline
- `framework/defaults.py` — Smart LLM slot selection: `available_providers()`, `smart_pick()`, `resolve_agent_config()`
- `utils/user_context.py` — Per-request user key storage; `set_user_context()` called in auth middleware, `get_user_key()` called in node threads. Also holds `_session_store` (thread-safe dict) for key propagation into LangGraph executor threads
- `utils/llm_factory.py` — `build_llm(provider, model)` and `get_llm_for_slot(slot, session_config)` — only entry point for constructing LLM clients

**Framework (`framework/`):**
- `schema.py` — `SkillManifest` and `StageConfig` parsed from `SKILL.md` files
- `registry.py` — Loads and caches skills from `backend/skills/`
- `engine.py` — Compiles a `SkillManifest` into a LangGraph `StateGraph`
- `strategies/` — Stage execution patterns:
  - `intake.py` — Handles brief/document/image input, emits confirmation interrupt
  - `interrupt.py` — Structured output with `question` interrupt (discovery)
  - `structured.py` — Plain structured output (review, approval)
  - `fanout.py` — Parallel branches (`ThreadPoolExecutor`) + merge writer (research)

**Persistence (`persistence/checkpointer.py`):**
- Implements both SQLite and PostgreSQL backends behind the same async interface
- Stores LangGraph checkpoints AND custom tables (users, sessions, agent_configs, usage)
- PostgreSQL requires `autocommit=True, prepare_threshold=None` for Neon PgBouncer compatibility

### Skills (`backend/skills/`)

Each skill is a directory containing:
- `SKILL.md` — Manifest: pipeline stages, execution strategies, llm_slots, routing logic
- `agents/*.md` — System prompts for each agent, versioned in DB as snapshots

Currently: `architect/` (5-stage architecture pipeline). Framework is extensible — add a new directory to add a new skill.

### Frontend (`frontend/src/`)

**Single-page Vue 3 app. One big component:** `ChatWindow.vue` is the entire application shell (sidebar, chat area, settings, banners).

**Composables:**
- `useAgentChat.js` — All session state and SSE parsing. `_readStream()` handles all `stage_start / token / stage_end / question / done / error / provider_error` events
- `useTheme.js` — 6 themes; injects `<style id="pragna-theme-vars">` into `<head>` with `!important` to override Vue scoped styles
- `useAuth.js` — Auth0 session management

**SSE event types** (emitted by backend, consumed by `_handleEvent` in `useAgentChat.js`):

| Event | Payload |
|---|---|
| `stage_start` | `{stage, label}` |
| `token` | `{content}` |
| `stage_end` | `{stage}` |
| `document_ready` | `{version, session_id}` |
| `review_complete` | `{passed, feedback, critical_issues}` |
| `approval_complete` | `{status, comments, required_changes}` |
| `confirm_understanding` | `{content, session_id}` |
| `question` | `{questions[], session_id}` |
| `done` | `{status, document_version}` |
| `error` | `{message}` |
| `provider_error` | `{message, can_smart_pick}` — triggers two-option banner |

### LLM Provider / Key Architecture

**Critical subtlety:** LangGraph runs synchronous node functions via `run_in_executor` inside tasks created with `asyncio.create_task(context=<langgraph_internal_context>)`. This context **does not** inherit the HTTP request's `_user_keys` ContextVar. Two mechanisms handle this:

1. `_stream_graph()` calls `register_session_keys(session_id, keys)` before streaming — stores keys in `utils/user_context._session_store` (plain thread-safe dict)
2. `fanout.py`'s `node()` calls `get_session_keys(state.session_id)` and `set_user_context()` at the start of each `run_branch` thread before any LLM call

All other strategies (intake, structured, interrupt) run in LangChain-managed threads where the ContextVar is accessible through `copy_context()`.

### LLM Slot System

Each pipeline stage is assigned an `llm_slot` in `SKILL.md`. Slots: `intake`, `discovery`, `researcher_search`, `researcher_reasoning`, `researcher_writer`, `reviewer`, `approver`.

`resolve_agent_config()` in `framework/defaults.py` resolves slot → `{provider, model}` using priority: snapshot override → user saved config → smart_pick from connected providers. Smart-pick preference chains are slot-specific (e.g. `researcher_search` prefers Perplexity → Google → Anthropic → OpenAI).

### Deployment

- **CI/CD:** Manual `workflow_dispatch` in `.github/workflows/build-and-push.yml` — triggers version bump, Docker build (`no-cache`), push to GHCR, `kubectl set image` on K3s cluster
- **Images:** `ghcr.io/sgummalla79/pragna-api` (uvicorn) and `pragna-ui` (Caddy serving Vue SPA)
- **VERSION file:** Bumped automatically by the workflow; do not bump manually before triggering a build
- **SSE requirement:** All proxies/load balancers must have `proxy_buffering off` and `proxy_read_timeout 300s`

## Key Invariants

- `session_agent_config` in `AgentState` is **frozen at session start** and patched on retry via `graph.aupdate_state()` — nodes must not write to it
- `session_type` in `agent_sessions` DB table is the **source of truth** for whether a session is a pipeline run or regular chat — do not infer from LangGraph checkpoint state
- `recursion_limit: 100` is set in `_stream_graph()` — the default of 25 is too low for a 5-stage pipeline with revision cycles
- PostgreSQL connections must use `autocommit=True, prepare_threshold=None` — Neon PgBouncer rejects prepared statements
