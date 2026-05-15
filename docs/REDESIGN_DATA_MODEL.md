# Data Model Redesign — Design Discussion

> **Status:** In progress — active design discussion.
> **Purpose:** Documents decisions made, rationale behind them, and topics parked for later discussion.
> **Last updated:** P3 (session start flow), conversation messages, and artifacts model finalised. Pending items: P1, P4, P5, P6, P7, P8, P9.

---

## Table of Contents

1. [Guiding Principles](#1-guiding-principles)
2. [What Stays the Same](#2-what-stays-the-same)
3. [Full Rewrite Decision](#3-full-rewrite-decision)
4. [New Table Design](#4-new-table-design)
5. [Versioning Model](#5-versioning-model)
6. [Model Configuration](#6-model-configuration)
7. [agents/*.md Moved to DB](#7-agentsmd-moved-to-db)
8. [Deployment vs Runtime Responsibility](#8-deployment-vs-runtime-responsibility)
9. [Conversation & Execution Model](#9-conversation--execution-model)
10. [Session Start Flow & AgentState](#10-session-start-flow--agentstate)
11. [Conversation Messages & Artifacts](#11-conversation-messages--artifacts)
12. [Parked — To Discuss Later](#12-parked--to-discuss-later)

---

## 1. Guiding Principles

- Skills are **defined during development/deployment**, not at runtime
- **Structure on disk** (`SKILL.md`), **content in DB** (agent prompts, user config)
- Per-user customisation is layered on top of canonical defaults — defaults are never mutated
- Model configuration is **per agent**, not per slot or per session globally
- The DB is always the source of truth at runtime — no disk fallback during request handling

---

## 2. What Stays the Same (Skill Definition Layer)

> **Note:** See §3 for the full rewrite decision.

- **`SKILL.md` stays on disk** — the pipeline structure (stage order, execution strategies, routing logic, output schemas, context fields, fanout/merge config) does not move to DB
- **`SKILL.md` is the only file that stays on disk** — everything else moves to DB
- The **LangGraph graph** is still compiled from `SKILL.md` at startup and lives in memory
- The **pipeline execution logic** (strategies, engine, edge routing) is unchanged

---

## 3. Full Rewrite Decision

The entire codebase is being rewritten from scratch. The only thing preserved is the **skill definition layer**. Everything else — DB schema, API routes, state, session management, LLM wiring — is new code built on the new model.

### What Is Preserved

| What | Why |
|---|---|
| `SKILL.md` files on disk | Pipeline structure — stages, routing, strategies |
| `framework/schema.py` | `SkillManifest`, `StageConfig`, `FanoutBranch` |
| `framework/loader.py` | `SkillLoader` — reads and validates `SKILL.md` |
| `framework/registry.py` | `SkillRegistry` — caches loaded skills |
| `framework/engine.py` | `SkillEngine` — compiles LangGraph graph (router + chat nodes removed) |
| `framework/strategies/` | All four strategies — intake, interrupt, fanout, structured |
| `framework/context.py` | `build_context` — assembles human turn from state fields |
| `agents/*.md` content | Moves to DB but the content is preserved |

### What Is Rewritten from Scratch

| What | Reason |
|---|---|
| `state.py` | `AgentState` — cleaned up, new fields, session_type gone |
| `persistence/checkpointer.py` | Entire DB schema — new tables |
| `api/routes/chat.py` | All endpoints — new conversation/execution model |
| `api/app.py` | Startup flow |
| `framework/chat.py` | Deleted — regular chat is outside LangGraph |
| `framework/defaults.py` | Slot-based → agent_key-based |
| `utils/user_context.py` | Rewired to new execution model |
| `utils/llm_factory.py` | Adapted to agent_key-based config |
| All existing DB tables | Replaced by new schema |

---

## 4. New Table Design

### Global Tables (not per-user)

#### `skills`
Registry of all available skills on the platform. Populated at deployment time.

```
skills:
  id          GUID PK
  skill_key   TEXT UNIQUE    -- e.g. "architect" (matches directory name on disk)
  name        TEXT           -- e.g. "Technical Architect"
  description TEXT
  icon        TEXT
  version     INTEGER
  created_at  TEXT
```

#### `agents`
Canonical list of agents per skill with their **default prompt content**. Populated at deployment time from the content that previously lived in `agents/*.md` files.

```
agents:
  id            GUID PK
  skill_id      GUID FK → skills.id
  agent_key     TEXT           -- e.g. "discovery", "research-writer"
  label         TEXT           -- e.g. "Discovery Agent"
  slot          TEXT           -- e.g. "discovery", "researcher_writer"
                               -- (open question: populated from SKILL.md at deployment,
                               --  or derived at runtime? — see §8)
  default_content TEXT         -- the full default system prompt
  created_at    TEXT
```

> **Note:** `agents.default_content` is the factory default — the prompt that ships with the skill. It is **never modified** after deployment. All user edits go into `user_agents_versions`.

---

### User-Specific Tables

#### `user_skills`
Tracks which skills a user has installed.

```
user_skills:
  user_id      TEXT FK → users.id
  skill_id     GUID FK → skills.id
  installed_at TEXT
  PRIMARY KEY (user_id, skill_id)
```

#### `user_agents`
Per-user, per-agent state. One row per `(user_id, agent_id)`. Created for every agent in a skill when the user installs the skill.

```
user_agents:
  id               GUID PK
  user_id          TEXT FK → users.id
  agent_id         GUID FK → agents.id
  current_version  INTEGER    -- points to the active published version in user_agents_versions
                              -- NULL is not valid here; always points to at least version 1
  provider_to_use  TEXT       -- e.g. "anthropic" — NULL until configured
  model_to_use     TEXT       -- e.g. "claude-sonnet-4-6" — NULL until configured
  created_at       TEXT
  UNIQUE (user_id, agent_id)
```

> `provider_to_use` and `model_to_use` are NULL immediately after skill install. They are set either via manual configuration on the skill config page or via smart suggest.

#### `user_agents_versions`
The actual prompt content, versioned per user per agent. One row per version.

```
user_agents_versions:
  id             GUID PK
  user_agent_id  GUID FK → user_agents.id
  version        INTEGER        -- sequential: 1, 2, 3, ...
  content        TEXT           -- the full system prompt text
  status         TEXT           -- "draft" or "published"
  created_at     TEXT
  published_at   TEXT           -- NULL if status = "draft"
  UNIQUE (user_agent_id, version)
```

---

### Skill Install Flow

When a user installs a skill (e.g. `architect`):

```
1. INSERT into user_skills (user_id, skill_id)

2. For each agent in the skill (rows in agents table):
     INSERT into user_agents:
       (user_id, agent_id, current_version=1, provider_to_use=NULL, model_to_use=NULL)

     INSERT into user_agents_versions:
       (user_agent_id, version=1, content=agents.default_content, status="published", published_at=now)
```

Version 1 is always the factory default content, published immediately on install.

---

## 5. Versioning Model

### Two statuses only: `draft` and `published`

No `archived` status. The `current_version` pointer in `user_agents` is the single source of truth for what is live. Old published versions stay as `published` — they are just not pointed to. Rollback = update the pointer.

### State machine

```
[no draft] ──edit──► [draft] ──publish──► [published]
               │                               │
           discard                     current_version
               │                       pointer updated
               ▼
          [no draft]
```

### Rules

- **At most one draft** per `(user_agent_id)` at any time
- Saving a draft when one already exists → updates the existing draft row in place (no new row)
- Publishing a draft:
  1. Draft status → `published`, `published_at` = now
  2. `user_agents.current_version` → updated to the newly published version number
  3. Previous published version stays as `published` — it's historical, accessible for rollback
- **Rollback** = update `user_agents.current_version` to point to any older published version

### Version history example

```
user_agents_versions (for one agent, one user):

  version | content | status    | published_at          | is current?
  --------|---------|-----------|----------------------|------------
  1       | "..."   | published | 2026-01-01           | no
  2       | "..."   | published | 2026-02-01           | no
  3       | "..."   | published | 2026-03-01           | YES  ← current_version = 3
  4       | "..."   | draft     | null                 | no (in progress)
```

---

## 6. Model Configuration

### Where it lives

`provider_to_use` and `model_to_use` on `user_agents`. Model choice is **not versioned** — it is orthogonal to prompt content. Changing the model does not create a new prompt version.

### Initial state

Both fields are `NULL` immediately after skill install.

### Three places where model validity is checked

| Check point | Trigger |
|---|---|
| **Skill added to chat** | User selects the skill to start a conversation |
| **Session starts** | Before the pipeline begins executing |
| **Per agent trigger** | Just before each individual agent runs in the pipeline |

At all three points, the **same banner behavior** applies:
- If `provider_to_use` / `model_to_use` is NULL → not configured
- If `provider_to_use` is set but that provider is no longer connected → invalid
- Either condition triggers the banner

### Banner options

**In chat (skill added / session start):**
- Message input is **disabled** until resolved
- Banner offers two actions:
  1. **Configure** → takes user to the skill config page
  2. **Smart suggest** → system auto-picks best provider/model per agent from connected providers → saves to `user_agents` → banner dismissed → input enabled

**On skill config page (deliberate configuration):**
- **Smart suggest button** → auto-fills provider/model per agent
- **Dropdown** → shows models available from the user's connected LLM providers, user picks manually

### Smart suggest logic

Uses the existing slot-based preference chains (from `defaults.py`). Each agent maps to a slot, and each slot has an ordered provider preference:

| Slot | Provider preference order |
|---|---|
| `researcher_search` | Perplexity → Google → Anthropic → OpenAI |
| `researcher_reasoning` | Google → Anthropic → OpenAI → Perplexity |
| `approver` | Anthropic (Opus) → Google → OpenAI → Perplexity |
| All others | Anthropic → Google → OpenAI → Perplexity |

Smart suggest persists the result to `user_agents.provider_to_use` and `user_agents.model_to_use`. It is not session-only.

---

## 7. agents/*.md Moved to DB

### Decision

`agents/*.md` files are moved to DB. They **no longer exist on disk** at runtime.

- The `agents` table stores the default content (what was previously in `agents/*.md`)
- This content is populated **once at deployment time**
- At runtime, prompts are always read from `user_agents_versions` — no disk access for prompts

### What remains on disk

Only `SKILL.md`. Nothing else.

### Deployment responsibility

During development/deployment (not server startup):
1. Developer writes/updates `SKILL.md` and agent prompt content
2. A deployment script / migration populates `skills` and `agents` tables in DB
3. This is a one-time setup per environment — analogous to running DB migrations

Server startup reads from DB. It does not scan disk for agent content.

---

## 8. Deployment vs Runtime Responsibility

| Concern | Who handles it | When |
|---|---|---|
| Define pipeline structure | Developer via `SKILL.md` | Development |
| Populate `skills` + `agents` tables | Deployment script / migration | Deployment |
| Compile LangGraph graph from `SKILL.md` | Server startup | Every restart |
| Seed `user_agents` + `user_agents_versions` v1 | Skill install flow | User action |
| Read agent prompts | From `user_agents_versions` via DB | Every session |
| Validate model config | Three check points (see §5) | Runtime |

---

## 9. Conversation & Execution Model

### Core Concept

A conversation is a **regular chat that can have skills attached to it**. Skills are not the conversation — they run inside it. A conversation can have multiple skills, added at any time (before or during the conversation).

### Key Rules

- When a skill is invoked → regular chat is **disabled** until the skill pipeline completes
- User can invoke the **same skill multiple times** within a conversation — each invocation is a fresh pipeline run using the same snapshot
- Each invocation gets its own **LangGraph thread_id** — executions are independent
- If a model fails mid-execution → user updates the **snapshot only** — the execution row is not touched, the pipeline retries from the last checkpoint using the updated model
- Skill invocation prompt (when multiple skills in conversation) → system asks user which skill to run

---

### Tables

#### `conversation`
Replaces the old `agent_sessions` table. All sessions are conversations.

```
conversation:
  id             GUID PK
  user_id        TEXT FK → users.id
  title          TEXT
  chat_provider  TEXT    -- e.g. "anthropic" — model used for regular chat in this conversation
  chat_model     TEXT    -- e.g. "claude-sonnet-4-6"
  created_at     TEXT
  last_modified  TEXT
```

#### `conversation_skills`
Tracks which skills are added to a conversation. **One row per skill per conversation.** This row IS the snapshot — created at the moment the skill is added (not at conversation start).

```
conversation_skills:
  id               GUID PK  ← this is the skill_snapshot_id
  conversation_id  GUID FK → conversation.id
  skill_id         GUID FK → skills.id
  added_at         TEXT
```

> No `status` field — whether a skill is currently running is derived from `conversation_skill_executions` (`status = 'running'`). No redundant state needed here.

#### `conversation_skill_agents`
The frozen snapshot of each agent's prompt and model at the time the skill was added to the conversation. One row per agent per skill per conversation.

```
conversation_skill_agents:
  id                    GUID PK
  conversation_skill_id GUID FK → conversation_skills.id
  agent_id              GUID FK → agents.id
  version               INTEGER   -- which version was active when snapshot was taken
  content               TEXT      -- denormalized prompt text (frozen, never updated)
  provider              TEXT      -- modifiable if model becomes invalid
  model                 TEXT      -- modifiable if model becomes invalid
```

> **Frozen vs Modifiable:**
> - `content` and `version` — frozen at snapshot time, never changed
> - `provider` and `model` — can be updated via `/conversation_id/skill_snapshot_id` configure page if model becomes invalid
> - Updating models here does NOT affect `user_agents.provider_to_use` / `user_agents.model_to_use` — it only affects this conversation's snapshot

#### `conversation_skill_executions`
One row per skill invocation. Each row is a LangGraph pipeline run.

```
conversation_skill_executions:
  id                    GUID PK  ← used as LangGraph thread_id
  conversation_skill_id GUID FK → conversation_skills.id
  status                TEXT     -- running | complete | halted
  started_at            TEXT
  completed_at          TEXT
```

> The execution row holds **no model or prompt config** — all config is read from `conversation_skill_agents` at runtime.

#### `conversation_skill_execution_stages`
Per-stage audit trail. One row per agent run per execution. Handles mid-execution model changes accurately — if a model fails and is reconfigured, the retry appears as a new row with the new model.

```
conversation_skill_execution_stages:
  id            GUID PK
  execution_id  GUID FK → conversation_skill_executions.id
  agent_key     TEXT     -- e.g. "research-search"
  provider      TEXT     -- what was actually used for this run
  model         TEXT     -- what was actually used for this run
  status        TEXT     -- success | failed
  ran_at        TEXT
```

**Example — mid-execution model change:**
```
execution_id | agent_key       | provider   | model        | status  | ran_at
-------------|-----------------|------------|--------------|---------|-------
exec_001     | discovery       | anthropic  | sonnet-4-6   | success | 10:01
exec_001     | research-search | perplexity | sonar-pro    | failed  | 10:05
exec_001     | research-search | google     | gemini-flash | success | 10:12  ← after reconfigure
exec_001     | review          | anthropic  | sonnet-4-6   | success | 10:15
```

---

### Snapshot Creation Flow

When a skill is added to a conversation:

```
1. INSERT conversation_skills (conversation_id, skill_id)

2. For each agent in the skill:
     INSERT conversation_skill_agents:
       content  ← copied from user_agents_versions WHERE version = user_agents.current_version
       version  ← user_agents.current_version
       provider ← user_agents.provider_to_use
       model    ← user_agents.model_to_use
```

Snapshot is point-in-time. Any future publish or model change on `user_agents` does not affect this conversation.

---

### Skill Invocation Flow

```
User invokes skill in conversation
    → INSERT conversation_skill_executions (id=new UUID, status=running)
    → LangGraph graph runs with thread_id = execution.id
    → Each agent reads config from conversation_skill_agents (via session context)
    → Each agent stage completes → INSERT conversation_skill_execution_stages row
    → Pipeline completes → execution.status = complete | halted
    → Regular chat re-enabled
```

---

### Model Failure Flow (mid-execution)

```
Agent stage fails (provider disconnected)
    → pipeline surfaces error / banner shown
    → User goes to /conversation_id/skill_snapshot_id
    → Updates provider + model on conversation_skill_agents rows
    → Execution retries from last LangGraph checkpoint (same execution.id / thread_id)
    → New conversation_skill_execution_stages row inserted with new model
    → conversation_skill_executions row untouched
```

---

### Configure Page

Route: `/conversation_id/skill_snapshot_id`

- Shows each agent in the skill with current `provider` + `model` from `conversation_skill_agents`
- **Only `provider` and `model` are editable** — prompt content is frozen
- Two options per agent: manual dropdown (from connected providers) or smart suggest
- Saving updates `conversation_skill_agents` rows only — no global user_agents change

---

## 10. Session Start Flow & AgentState

### AgentState — Final Definition

```python
class AgentState(BaseModel):
    # ── Execution identity ────────────────────────────────────────────────────
    execution_id:          str = ""   # = conversation_skill_executions.id = LangGraph thread_id
    conversation_id:       str = ""   # FK to conversation — for mid-execution model failure handling
    conversation_skill_id: str = ""   # FK to conversation_skills (the snapshot) — for model updates

    # ── Stage tracking ────────────────────────────────────────────────────────
    current_stage:  str = "intake"
    revision_count: int = 0

    # ── Stage 1 — Intake ─────────────────────────────────────────────────────
    source_type:         Literal["brief", "document", "image"] = "brief"
    uploaded_file_path:  str = ""
    uploaded_image_path: str = ""
    raw_document_text:   str = ""
    project_brief:       str = ""

    # ── Stage 2 — Discovery ──────────────────────────────────────────────────
    discovery_questions: list[DiscoveryQuestion] = []
    discovery_complete:  bool = False

    # ── Stage 3 — Research ───────────────────────────────────────────────────
    document_draft:   str = ""
    document_version: int = 0

    # ── Stage 4 — Review ─────────────────────────────────────────────────────
    review_result: Optional[ReviewResult] = None

    # ── Stage 5 — Approval ───────────────────────────────────────────────────
    approval_result: Optional[ApprovalResult] = None

    # ── Pipeline config (frozen at execution start) ───────────────────────────
    flow_id:              str  = ""   # e.g. "architect"
    flow_config:          dict = {}   # {agent_key: prompt_content}
    session_agent_config: dict = {}   # {agent_key: {provider, model}}

    # ── Accumulators (append-only via LangGraph reducers) ─────────────────────
    messages:      Annotated[list[BaseMessage], add_messages] = []
    usage_records: Annotated[list[dict], operator.add]        = []
```

**Removed from old AgentState:**
- `session_id` → renamed to `execution_id`
- `session_type` → gone, routing is by endpoint
- `chat_model`, `chat_provider`, `extended_thinking` → chat is outside LangGraph
- `flow_snapshot_id`, `flow_snapshot_version` → replaced by `conversation_skill_id`
- `created_at` → not needed in state, tracked in DB

**`session_agent_config` is now agent_key-based** (not slot-based):
```python
{
    "discovery":          {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "research-search":    {"provider": "perplexity", "model": "sonar-pro"},
    "research-reasoning": {"provider": "google",     "model": "gemini-2.5-pro"},
    "research-writer":    {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "review":             {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "approval":           {"provider": "anthropic",  "model": "claude-opus-4-7"},
}
```

---

### Execution Start Flow

**Endpoint:** `POST /conversation/{conversation_id}/skill/{skill_id}/invoke`

```
1. Auth → get user_id

2. Load conversation_skills row for (conversation_id, skill_id)
   → get conversation_skill_id

3. Check no skill is currently running in this conversation:
   SELECT * FROM conversation_skill_executions cse
   JOIN conversation_skills cs ON cse.conversation_skill_id = cs.id
   WHERE cs.conversation_id = ? AND cse.status = 'running'
   → if found → 409

4. Load conversation_skill_agents for this conversation_skill_id
   → build flow_config          = {agent_key: content}
   → build session_agent_config = {agent_key: {provider, model}}

5. Validate all agents:
   → any provider NULL or disconnected → surface banner (not HTTP error)
   → all valid → proceed

6. Create conversation_skill_executions row
   → new UUID = execution_id = LangGraph thread_id
   → status = 'running'

7. Register session keys (for fanout thread safety)

8. Construct AgentState:
   execution_id          = new execution UUID
   conversation_id       = conversation_id
   conversation_skill_id = conversation_skill_id
   flow_id               = skill.skill_key
   flow_config           = built in step 4
   session_agent_config  = built in step 4
   source_type           = from request body

9. config = {"configurable": {"thread_id": execution_id}, "recursion_limit": 100}

10. Return SSE stream from _stream_graph(graph, initial_state, config)

On stream end:
   → UPDATE conversation_skill_executions SET status = complete|halted, completed_at = now
```

### Re-invocation

Every invocation is **always a completely fresh start**. New `execution_id`, clean `AgentState` — empty brief, no document, `document_version = 0`, `discovery_complete = False`. The previous execution's document is accessible in the conversation as an artifact. User can ask the chat LLM to summarise a previous execution before starting a new one.

### LangGraph thread_id

`config["configurable"]["thread_id"]` = `execution_id`. Each execution is an isolated LangGraph checkpoint thread. Re-invoking the same skill creates a new thread — it does not resume from a prior checkpoint.

---

## 11. Conversation Messages & Artifacts

### Single Messages Table

Every message — regular chat or skill pipeline — goes into one table.

```
conversation_messages:
  id               GUID PK
  conversation_id  GUID FK → conversation.id
  execution_id     GUID FK → conversation_skill_executions.id  ← null for regular chat
  role             TEXT    -- user | assistant
  content          TEXT
  message_type     TEXT    -- chat | stage_summary | question | confirmation | artifact_ref | user_answer
  message_state    TEXT    -- visible | hidden
  artifact_id      GUID FK → conversation_artifacts.id  ← null if no artifact
  created_at       TEXT
```

### message_state

| message_state | When used |
|---|---|
| `visible` | Shown in the conversation UI |
| `hidden` | Not shown — raw pipeline output, token streams replaced by summaries |

### message_type

| message_type | Description |
|---|---|
| `chat` | Regular free-form chat message |
| `stage_summary` | e.g. "[Research] Document v1 produced. 2 parallel branches → writer." |
| `question` | Discovery question(s) from the pipeline |
| `user_answer` | User's answer to a discovery question |
| `confirmation` | confirm_understanding prompt from intake |
| `artifact_ref` | A message that references an artifact — shows a card with a button |

### Artifacts Table

```
conversation_artifacts:
  id               GUID PK
  conversation_id  GUID FK → conversation.id
  execution_id     GUID FK → conversation_skill_executions.id
  artifact_type    TEXT    -- "document" (expandable for future types)
  content          TEXT    -- full document text
  version          INTEGER -- document version number (1, 2, 3...)
  status           TEXT    -- see below
  created_at       TEXT
```

### Artifact status values

| Status | When set |
|---|---|
| `pending_review` | Research stage just produced this version |
| `review_failed` | Reviewer rejected it |
| `review_passed` | Reviewer approved, going to approver |
| `approval_rejected` | Approver rejected it |
| `approved` | Final — pipeline complete |

### Artifact creation point

A new `conversation_artifacts` row is created **after every research stage completes** — not just at execution end. This captures every version including those that subsequently failed review or approval. Complete history is always preserved.

### UI representation

```
Architecture Document v3          ← artifact_ref message (visible)
Review Failed — 2 critical issues ← status shown on card

Architecture Document v4          ← artifact_ref message (visible)
Approved ✓
```

The `artifact_ref` message links to the artifact via `artifact_id`. The UI renders a card with a button to view the full document.

---

## 12. Parked — To Discuss Later

The following topics were raised but explicitly deferred during the discussion.

---

### P1. ~~New agent added to an existing skill~~ 🔮 Future Feature

Explicitly deferred. Not in scope for the current rewrite. When a new agent is added to an existing skill post-deployment, backfilling `user_agents` and existing `conversation_skill_agents` snapshots will be handled as a separate future initiative.

---

### P2. ~~Snapshots — session reproducibility~~ ✅ Resolved

Resolved via `conversation_skill_agents` — a denormalized snapshot taken at the moment a skill is added to a conversation. Content is frozen; only `provider` and `model` are modifiable. See §8.

---

### P3. ~~Session start flow~~ ✅ Resolved

Fully resolved in §10 and §11. AgentState final definition, execution start flow, conversation messages table, artifacts table, re-invocation behaviour, and artifact creation timing all decided.

---

### P4. ~~Per-agent trigger — interrupt mechanism~~ ✅ Resolved

Resolved via P3 execution flow. Node tries to call LLM → provider disconnected → error propagates to `_stream_graph` → caught → banner SSE emitted → user updates `conversation_skill_agents` → execution retries from last LangGraph checkpoint (same `execution_id` / `thread_id`). Same error propagation pattern as the existing code.

---

### P5. ~~`slot` field in `agents` table~~ ✅ Resolved

No `slot` field needed in the `agents` table. SKILL.md stays on disk and is loaded at startup. `skill.manifest.agent_slot_map` already provides `{agent_key → slot}` at runtime. Smart suggest reads slot preference from there — no DB storage needed.

---

### P6. ~~Draft / publish lifecycle — additional details~~ ✅ Resolved

- **Per-agent publish** — each agent has its own publish button. Granular control. Creates a new snapshot.
- **Publish All** — sits at the skill level. Enabled when at least one draft exists across any agent in the skill. Publishes all current drafts in one action. Creates a new snapshot.
- Editing while a draft exists → updates the existing draft row in place (no new row created).
- Publishing never affects in-flight conversations — `conversation_skill_agents` snapshots are frozen at the time the skill was added to the conversation.

---

### P7. ~~`skills` and `agents` table population tooling~~ 🔧 Implementation Detail

Design decision already made: deployment concern, not server startup. Actual tooling (migration script, admin CLI, CI/CD step) to be designed during implementation phase — not a design discussion.

---

### P8. ~~Skill invocation UX~~ ✅ Resolved

User types `/` in the chat input → a command palette panel appears above the input showing all skills added to this conversation (icon + name + description, type to filter — same pattern as Slack slash commands). User selects a skill → frontend calls `POST /conversation/{conversation_id}/skill/{skill_id}/invoke`.

- Pure frontend mechanism — no backend change needed
- Data displayed comes from `skills` table (`icon`, `name`, `description`, `skill_key`)
- Selection never appears in conversation message history
- No LangGraph interrupt involved

---

### P9. ~~Post-skill-completion behaviour~~ ✅ Resolved

- After skill completes → regular chat resumes. Nothing is auto-presented to the user.
- User invokes any skill (same or different) at any time via `/` slash command (see P8).
- Every invocation is always a completely fresh pipeline start regardless of which skill.
- No restriction on order or frequency of skill invocations within a conversation.
