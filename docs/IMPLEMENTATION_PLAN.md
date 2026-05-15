# Implementation Plan: Backend Rewrite — New Data Model

## Context

After an extensive design discussion, the entire backend is being rewritten to a new data model that:
- Replaces session-centric state with a conversation + skill execution model
- Moves agent prompts from disk to DB (per-user versioning)
- Introduces clean separation: skills (global) → user_skills (installed) → conversation_skills (snapshot) → executions
- Drops SQLite, goes Postgres-only with Docker
- Enforces SOLID principles throughout — repositories, services, clean layers
- Preserves only the skill definition layer (SKILL.md, strategies, engine, loader, schema)

Reference documents:
- `docs/AGENT_FLOW.md` — original flow documentation
- `docs/REDESIGN_DATA_MODEL.md` — complete design decisions

---

## What Is Preserved (Do Not Touch)

```
backend/skills/                          ← SKILL.md + agents content (moves to DB but ref'd)
backend/framework/schema.py              ← SkillManifest, StageConfig, FanoutBranch
backend/framework/loader.py              ← SkillLoader
backend/framework/registry.py           ← SkillRegistry
backend/framework/engine.py             ← SkillEngine (router + chat nodes removed)
backend/framework/strategies/           ← All 4 strategies (intake, interrupt, fanout, structured)
backend/framework/context.py            ← build_context
backend/utils/llm_retry.py              ← invoke_with_retry (tenacity wrapper, keep as-is)
backend/utils/pricing.py                ← cost_usd, usage_record (keep as-is)
backend/utils/file_parser.py            ← extract_text (keep as-is)
backend/utils/file_storage.py           ← save_upload (keep as-is)
```

---

## What Is Deleted / Rewritten

```
backend/state.py                         → rewritten
backend/config.py                        → rewritten (Postgres-only)
backend/chat_models.py                   → deleted (chat is outside LangGraph)
backend/persistence/                     → fully rewritten
backend/api/                             → fully rewritten
backend/framework/chat.py               → deleted
backend/framework/defaults.py           → rewritten (agent_key-based)
backend/utils/user_context.py           → rewritten
backend/utils/llm_factory.py            → rewritten (agent_key-based)
backend/utils/api_keys.py               → replaced by utils/user_api_keys.py
backend/utils/agent_config.py           → deleted
backend/utils/auth.py                   → rewritten
backend/utils/models_cache.py           → rewritten
backend/utils/model_metadata.py         → rewritten
backend/utils/key_validator.py          → rewritten
backend/utils/provider_registry.py     → kept/adapted
backend/utils/log.py                    → kept
```

---

## Phase 0 — Backup & Cleanup

### Step 0.1 — Git tag
```bash
git tag backup/pre-rewrite
git push origin backup/pre-rewrite
```

### Step 0.2 — Selective deletion
Delete everything listed above in "What Is Deleted". The preserved files stay in place.

### Step 0.3 — Update requirements.txt
Remove:
- `langgraph-checkpoint-sqlite`
- `aiosqlite`

Add:
- `pytest>=8.0`
- `pytest-asyncio>=0.23`
- `alembic>=1.13`

---

## Phase 1 — Infrastructure

### Step 1.1 — docker-compose.yml (root level)
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: pragna
      POSTGRES_USER: pragna
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pragna"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    env_file: backend/.env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app

volumes:
  postgres_data:
```

### Step 1.2 — backend/.env.example
- `DATABASE_URL=postgresql://pragna:password@localhost:5432/pragna`
- Remove `SQLITE_PATH`, `DB_BACKEND`
- Add `DB_PASSWORD`

---

## Phase 2 — Database Schema (Alembic Migrations)

### Step 2.1 — Alembic setup
```
backend/alembic/
  alembic.ini
  env.py
  versions/
    0001_initial_schema.py
```

### Step 2.2 — Migration 0001: All 16 Tables (in FK dependency order)

**Platform:**
```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT '⚡',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skills(id),
    agent_key TEXT NOT NULL,
    label TEXT,
    default_content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(skill_id, agent_key)
);
```

**Users:**
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT, picture TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_login TIMESTAMPTZ
);

CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id),
    key_name TEXT NOT NULL,
    encrypted_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, key_name)
);

CREATE TABLE user_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id),
    key TEXT NOT NULL, value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, key)
);

CREATE TABLE user_skills (
    user_id TEXT NOT NULL REFERENCES users(id),
    skill_id UUID NOT NULL REFERENCES skills(id),
    installed_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY(user_id, skill_id)
);

CREATE TABLE user_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    current_version INTEGER NOT NULL DEFAULT 1,
    provider_to_use TEXT,
    model_to_use TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, agent_id)
);

CREATE TABLE user_agents_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_agent_id UUID NOT NULL REFERENCES user_agents(id),
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft','published')),
    created_at TIMESTAMPTZ DEFAULT now(),
    published_at TIMESTAMPTZ,
    UNIQUE(user_agent_id, version)
);
```

**Conversations:**
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT, chat_provider TEXT, chat_model TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_modified TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    skill_id UUID NOT NULL REFERENCES skills(id),
    added_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_skill_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_skill_id UUID NOT NULL REFERENCES conversation_skills(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    version INTEGER NOT NULL,
    content TEXT NOT NULL,   -- frozen, never updated
    provider TEXT,           -- modifiable if model becomes invalid
    model TEXT               -- modifiable if model becomes invalid
);

CREATE TABLE conversation_skill_executions (
    id UUID PRIMARY KEY,     -- used as LangGraph thread_id
    conversation_skill_id UUID NOT NULL REFERENCES conversation_skills(id),
    status TEXT NOT NULL CHECK(status IN ('running','complete','halted')),
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE conversation_skill_execution_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES conversation_skill_executions(id),
    agent_key TEXT NOT NULL,
    provider TEXT, model TEXT,
    status TEXT NOT NULL CHECK(status IN ('success','failed')),
    ran_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    execution_id UUID REFERENCES conversation_skill_executions(id),
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content TEXT,
    message_type TEXT NOT NULL CHECK(message_type IN (
        'chat','stage_summary','question','user_answer','confirmation','artifact_ref'
    )),
    message_state TEXT NOT NULL CHECK(message_state IN ('visible','hidden')),
    artifact_id UUID,        -- FK added below after artifacts table
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    execution_id UUID NOT NULL REFERENCES conversation_skill_executions(id),
    artifact_type TEXT NOT NULL DEFAULT 'document',
    content TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'pending_review','review_failed','review_passed','approval_rejected','approved'
    )),
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE conversation_messages
    ADD CONSTRAINT fk_artifact FOREIGN KEY (artifact_id) REFERENCES conversation_artifacts(id);

CREATE TABLE token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    provider TEXT, model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Indexes:**
```sql
CREATE INDEX idx_conversations_user       ON conversations(user_id);
CREATE INDEX idx_conv_skills_conv         ON conversation_skills(conversation_id);
CREATE INDEX idx_conv_skill_agents_cs     ON conversation_skill_agents(conversation_skill_id);
CREATE INDEX idx_executions_cs            ON conversation_skill_executions(conversation_skill_id);
CREATE INDEX idx_stages_execution         ON conversation_skill_execution_stages(execution_id);
CREATE INDEX idx_messages_conversation    ON conversation_messages(conversation_id);
CREATE INDEX idx_messages_execution       ON conversation_messages(execution_id);
CREATE INDEX idx_artifacts_execution      ON conversation_artifacts(execution_id);
CREATE INDEX idx_token_usage_conversation ON token_usage(conversation_id);
CREATE INDEX idx_user_agents_user         ON user_agents(user_id);
CREATE INDEX idx_user_agents_versions_ua  ON user_agents_versions(user_agent_id);
```

---

## Phase 3 — Core Domain Models & State

### `backend/state.py` (rewrite)

```python
class AgentState(BaseModel):
    # Execution identity
    execution_id:          str = ""   # = conversation_skill_executions.id = LangGraph thread_id
    conversation_id:       str = ""
    conversation_skill_id: str = ""

    # Stage tracking
    current_stage:  str = "intake"
    revision_count: int = 0

    # Intake
    source_type:         Literal["brief","document","image"] = "brief"
    uploaded_file_path:  str = ""
    uploaded_image_path: str = ""
    raw_document_text:   str = ""
    project_brief:       str = ""

    # Discovery
    discovery_questions: list[DiscoveryQuestion] = []
    discovery_complete:  bool = False

    # Research
    document_draft:   str = ""
    document_version: int = 0

    # Review / Approval
    review_result:   Optional[ReviewResult]   = None
    approval_result: Optional[ApprovalResult] = None

    # Pipeline config (frozen at execution start)
    flow_id:              str  = ""
    flow_config:          dict = {}   # {agent_key: prompt_content}
    session_agent_config: dict = {}   # {agent_key: {provider, model}}

    # Accumulators (append-only via LangGraph reducers)
    messages:      Annotated[list[BaseMessage], add_messages] = []
    usage_records: Annotated[list[dict], operator.add]        = []
```

### `backend/config.py` (rewrite — Postgres only)
- `DATABASE_URL` required, no SQLite fallback
- Keep: `MAX_REVISIONS=5`, `MAX_DISCOVERY_QUESTIONS=30`, `PERPLEXITY_API_BASE`, `CLAUDE_HAIKU_MODEL`, `UPLOAD_DIR`, `MAX_FILE_SIZE_MB`

---

## Phase 4 — Repository Layer

Each repository owns exactly one domain. SRP strictly enforced.

```
backend/repositories/
    __init__.py
    base.py                    ← BaseRepository — _exec, _fetchone, _fetchall
    skill_repository.py        ← SkillRepository
    agent_repository.py        ← AgentRepository
    user_repository.py         ← UserRepository
    user_skill_repository.py   ← UserSkillRepository
    user_agent_repository.py   ← UserAgentRepository
    conversation_repository.py ← ConversationRepository
    execution_repository.py    ← ExecutionRepository
    message_repository.py      ← MessageRepository
    artifact_repository.py     ← ArtifactRepository
    usage_repository.py        ← UsageRepository
```

Key method signatures per repository:

| Repository | Key methods |
|---|---|
| SkillRepository | `get_by_key`, `list_all`, `upsert` |
| AgentRepository | `get_by_skill`, `get_by_key`, `upsert` |
| UserAgentRepository | `install_skill_agents`, `save_draft`, `publish`, `publish_all` |
| ConversationRepository | `create`, `add_skill` (→ snapshot), `get_skill_agents`, `update_agent_model`, `list_for_user` |
| ExecutionRepository | `create`, `complete`, `get_running`, `record_stage` |
| MessageRepository | `create`, `list_for_conversation` |
| ArtifactRepository | `create`, `update_status`, `get_latest` |
| UsageRepository | `record`, `get_by_conversation` |

---

## Phase 5 — Utilities (Rewrite)

| File | What changes |
|---|---|
| `utils/user_api_keys.py` | Fernet per-user encryption (same HKDF logic, renamed from api_keys.py) |
| `utils/user_context.py` | ContextVar + `_session_store` keyed by `execution_id` (not session_id) |
| `utils/llm_factory.py` | `get_llm_for_agent(agent_key, session_agent_config)` replaces slot-based lookup |
| `framework/defaults.py` | `smart_pick_for_agent(agent_key, slot, connected)` — slot derived from manifest |

---

## Phase 6 — Framework Updates

### `framework/engine.py`
- Remove `run_chat` import, `chat` node, `router` node
- Remove `_add_entry_edges`, `_add_chat_edges`
- `graph.set_entry_point("intake")` directly

### `framework/strategies/` (4 files — minimal change)
- Replace every `get_llm_for_slot(stage.llm_slot, ...)` → `get_llm_for_agent(stage.agent_key, ...)`

---

## Phase 7 — Persistence Layer

### `persistence/db.py`
- `AsyncConnectionPool` (Postgres only, `autocommit=True` not needed — no PgBouncer)
- Alembic `command.upgrade(alembic_cfg, "head")` on startup
- `AsyncPostgresSaver` for LangGraph
- `DBContext` holds: `checkpointer`, `pool`, all repository instances

### `persistence/seed.py`
- `seed_skills(db, skill_registry)` — idempotent `ON CONFLICT DO NOTHING`
- Populates `skills` + `agents` from loaded `LoadedSkill` objects

---

## Phase 8 — API Layer

### `api/app.py` startup sequence
1. Validate env
2. Open Postgres pool
3. Run Alembic migrations
4. Load SkillRegistry from disk
5. Seed skills + agents (idempotent)
6. Compile LangGraph graphs (entry point = `intake`, no router/chat)
7. Mount routers

### Route files

```
api/routes/
    health.py         GET /health
    auth.py           Auth0 OAuth (largely unchanged)
    providers.py      Connect/disconnect/refresh LLM providers
    skills.py         List + install/uninstall skills
    agents.py         Prompt versioning (draft/publish per-agent + skill-level publish all)
    conversations.py  CRUD + regular chat SSE
    executions.py     Invoke skill SSE + reply + retry
    artifacts.py      GET artifact content
    usage.py          Token usage by conversation
```

### New endpoint map

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations` | List user's conversations |
| GET | `/api/conversations/{id}` | Get conversation with messages |
| PATCH | `/api/conversations/{id}` | Rename |
| DELETE | `/api/conversations/{id}` | Delete |
| POST | `/api/conversations/{id}/message` | Regular chat (SSE) |
| POST | `/api/conversations/{id}/skills` | Add skill → creates snapshot |
| DELETE | `/api/conversations/{id}/skills/{sid}` | Remove skill |
| GET | `/api/conversations/{id}/skills/{sid}/config` | View snapshot model config |
| PATCH | `/api/conversations/{id}/skills/{sid}/config` | Update snapshot model config |
| POST | `/api/conversations/{id}/skills/{sid}/invoke` | Invoke skill pipeline (SSE) |
| POST | `/api/executions/{id}/reply` | Resume interrupt (SSE) |
| POST | `/api/executions/{id}/retry` | Retry after model update (SSE) |
| GET | `/api/executions/{id}/stages` | Stage audit trail |
| GET | `/api/skills/{skill_id}/agents` | All agents + versions |
| PUT | `/api/skills/{skill_id}/agents/{key}/draft` | Save draft |
| DELETE | `/api/skills/{skill_id}/agents/{key}/draft` | Discard draft |
| POST | `/api/skills/{skill_id}/agents/{key}/publish` | Per-agent publish |
| POST | `/api/skills/{skill_id}/publish` | Publish all drafts |

### `_stream_graph` (core SSE emitter)
1. Validate all agents have connected providers
2. `register_execution_keys(execution_id, user_keys)`
3. `config = {"configurable": {"thread_id": execution_id}, "recursion_limit": 100}`
4. `astream_events` → SSE translation (same event types as before)
5. On `research` node end → `artifact_repository.create(...)`, update status
6. On stream end → `aget_state` → detect interrupt vs complete
7. `execution_repository.complete(execution_id, status)`
8. `usage_repository.record(...)` for each usage_record in state
9. `unregister_execution_keys(execution_id)`

---

## Phase 9 — Tests

```
backend/tests/
    conftest.py
    unit/
        test_state.py          AgentState reducers, field defaults
        test_defaults.py       smart_pick_for_agent, resolve_agent_config
        test_context.py        build_context field formatters
        test_pricing.py        cost_usd calculations
    integration/
        test_repositories.py   All repository CRUD against real test DB
        test_migrations.py     Alembic migration applies cleanly
        test_skill_seed.py     seed_skills populates tables correctly
    e2e/
        test_conversation.py   Create conversation → chat → message saved
        test_skill_invoke.py   Add skill → invoke → reply to question
        test_versioning.py     Draft → publish → current_version updated
        test_model_config.py   Update snapshot model → retry → stage audit
```

- `pragna_test` DB — transactions roll back after each test
- `pytest-asyncio` for async tests
- Tests written alongside each phase, not after

---

## Phase 10 — Frontend Wiring

### New composables
- `useConversations.js` — replaces session management
- `useSkillExecution.js` — skill invocation SSE
- `useSkillConfig.js` — snapshot model configuration
- Slash command palette for skill invocation via `/`
- Artifact cards with status badges

### Endpoint mapping (old → new)

| Old | New |
|---|---|
| `POST /api/chat/start` | `POST /api/conversations` + `/skills/{sid}/invoke` |
| `POST /api/chat/reply/{id}` | `POST /api/executions/{id}/reply` |
| `POST /api/chat/retry/{id}` | `POST /api/executions/{id}/retry` |
| `GET /api/chat/sessions` | `GET /api/conversations` |
| `GET /api/chat/session/{id}/restore` | `GET /api/conversations/{id}` |
| `POST /api/chat/message/{id}` | `POST /api/conversations/{id}/message` |
| `GET /api/chat/document/{id}` | `GET /api/artifacts/{id}` |

---

## Phase 11 — Production Docker

### docker-compose.prod.yml
- Same as dev, add `restart: unless-stopped`
- No bind-mount volume for live reload
- Caddy reverse proxy in front of API + UI

### Backup cron (set up on production server)
```bash
0 2 * * * pg_dump -U pragna pragna | gzip > /backups/pragna_$(date +%Y%m%d).sql.gz
```

---

## Verification

```bash
# Start local Postgres
docker compose up db

# Run backend
cd backend && uvicorn api.app:app --reload --port 8000

# Health check
curl http://localhost:8000/health
# → {"status": "ok", "db": "ready", "skills": ["architect"]}

# Tests
pytest tests/unit/         # no DB required
pytest tests/integration/  # requires test DB
pytest tests/e2e/          # full stack
```

### E2E smoke test checklist
1. Create conversation → verify `conversations` row
2. Add architect skill → verify `conversation_skills` + `conversation_skill_agents` rows
3. Invoke skill with brief → verify `conversation_skill_executions` row (status=running)
4. Reply to discovery question → verify pipeline continues
5. Check `conversation_artifacts` created after research stage
6. Verify `token_usage` rows accumulate
7. Verify `conversation_skill_execution_stages` has full audit trail
8. Approve → verify execution status=complete

---

## Implementation Order

```
0. Backup tag + selective deletion + requirements update
1. docker-compose.yml + .env.example
2. Alembic setup + migration 0001 (all 16 tables)
3. state.py + config.py
4. repositories/ (base + all 10 domain repos)
5. persistence/db.py + persistence/seed.py
6. utils/ (user_api_keys, user_context, llm_factory) + framework/defaults.py
7. framework/engine.py + framework/strategies/ (llm lookup swap)
8. api/app.py + api/routes/ (all 9 route files)
9. tests/ (unit → integration → e2e, written per phase)
10. frontend/ (new composables + endpoint updates)
11. docker-compose.prod.yml + production deployment
```
