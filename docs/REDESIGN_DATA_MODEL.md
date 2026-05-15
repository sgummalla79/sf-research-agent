# Data Model Redesign — Design Discussion

> **Status:** In progress — active design discussion.
> **Purpose:** Documents decisions made, rationale behind them, and topics parked for later discussion.
> **Last updated:** Conversation & execution model finalised. Pending items: new agent backfill, session start flow, skill invocation UX, deployment tooling.

---

## Table of Contents

1. [Guiding Principles](#1-guiding-principles)
2. [What Stays the Same](#2-what-stays-the-same)
3. [New Table Design](#3-new-table-design)
4. [Versioning Model](#4-versioning-model)
5. [Model Configuration](#5-model-configuration)
6. [agents/*.md Moved to DB](#6-agentsmd-moved-to-db)
7. [Deployment vs Runtime Responsibility](#7-deployment-vs-runtime-responsibility)
8. [Conversation & Execution Model](#8-conversation--execution-model)
9. [Parked — To Discuss Later](#9-parked--to-discuss-later)

---

## 1. Guiding Principles

- Skills are **defined during development/deployment**, not at runtime
- **Structure on disk** (`SKILL.md`), **content in DB** (agent prompts, user config)
- Per-user customisation is layered on top of canonical defaults — defaults are never mutated
- Model configuration is **per agent**, not per slot or per session globally
- The DB is always the source of truth at runtime — no disk fallback during request handling

---

## 2. What Stays the Same

- **`SKILL.md` stays on disk** — the pipeline structure (stage order, execution strategies, routing logic, output schemas, context fields, fanout/merge config) does not move to DB
- **`SKILL.md` is the only file that stays on disk** — everything else moves to DB
- The **LangGraph graph** is still compiled from `SKILL.md` at startup and lives in memory
- The **pipeline execution logic** (strategies, engine, edge routing) is unchanged

---

## 3. New Table Design

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

## 4. Versioning Model

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

## 5. Model Configuration

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

## 6. agents/*.md Moved to DB

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

## 7. Deployment vs Runtime Responsibility

| Concern | Who handles it | When |
|---|---|---|
| Define pipeline structure | Developer via `SKILL.md` | Development |
| Populate `skills` + `agents` tables | Deployment script / migration | Deployment |
| Compile LangGraph graph from `SKILL.md` | Server startup | Every restart |
| Seed `user_agents` + `user_agents_versions` v1 | Skill install flow | User action |
| Read agent prompts | From `user_agents_versions` via DB | Every session |
| Validate model config | Three check points (see §5) | Runtime |

---

## 8. Conversation & Execution Model

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
  id            GUID PK
  user_id       TEXT FK → users.id
  title         TEXT
  created_at    TEXT
  last_modified TEXT
```

#### `conversation_skills`
Tracks which skills are added to a conversation. **One row per skill per conversation.** This row IS the snapshot — created at the moment the skill is added (not at conversation start).

```
conversation_skills:
  id            GUID PK  ← this is the skill_snapshot_id
  conversation_id  GUID FK → conversation.id
  skill_id      GUID FK → skills.id
  added_at      TEXT
  status        TEXT     -- pending | active | complete | halted
```

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
1. INSERT conversation_skills (conversation_id, skill_id, status=pending)

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

## 9. Parked — To Discuss Later

The following topics were raised but explicitly deferred during the discussion.

---

### P1. New agent added to an existing skill

When a new agent is added to a skill (new row in `agents` table, new entry in `SKILL.md`) after users have already installed the skill — their `user_agents` table has no row for the new agent, and existing `conversation_skill_agents` snapshots won't include it either. Gap detection and backfill strategy not yet decided.

---

### P2. ~~Snapshots — session reproducibility~~ ✅ Resolved

Resolved via `conversation_skill_agents` — a denormalized snapshot taken at the moment a skill is added to a conversation. Content is frozen; only `provider` and `model` are modifiable. See §8.

---

### P3. Session start flow

How exactly does a session resolve its config from the new tables at runtime? Specifically:
- What does `AgentState.flow_config` look like — loaded from `conversation_skill_agents`?
- What does `AgentState.session_agent_config` look like — loaded from `conversation_skill_agents` per agent?
- How does the execution's `thread_id` flow into LangGraph config?
Full discussion deferred.

---

### P4. Per-agent trigger — interrupt mechanism for mid-pipeline model invalidity

If a model becomes invalid while the pipeline is running (e.g. during research), the pipeline needs to surface the banner and pause. The user updates `conversation_skill_agents`, then retries. The mechanism for pausing the pipeline at the node level and resuming needs design. Deferred.

---

### P5. `slot` field in `agents` table

Each agent maps to a slot (e.g. `"researcher_search"`, `"reviewer"`) which drives smart suggest logic. Open question: is this populated from `SKILL.md` at deployment time (static), or derived dynamically at runtime? Deferred.

---

### P6. Draft / publish lifecycle — additional details

High-level versioning model is agreed (draft → published, pointer-based, no archived). Finer details not yet discussed:
- UI behaviour when user edits while a draft already exists (update in place)
- Bulk publish (all agents at once) vs per-agent publish
- Whether publishing affects any in-flight conversations (it should not — snapshots are frozen)

---

### P7. `skills` and `agents` table population tooling

Deployment concern — not server startup. Actual tooling (migration script, admin CLI, CI/CD step) not yet designed.

---

### P8. Skill invocation UX

When a conversation has multiple skills and user wants to invoke one — the system asks which skill. The exact mechanism (structured UI with buttons/cards vs free text vs command) not yet decided. Affects whether this is a LangGraph interrupt or a frontend-side pre-pipeline decision.

---

### P9. Post-skill-completion behaviour

After a skill pipeline completes (approved or halted) within a conversation:
- Can user invoke a different skill from the same conversation?
- Can user switch back to regular free-form chat?
- Can user invoke the same skill again (yes, decided) — what does the conversation UI show for multiple executions of the same skill?
Not yet fully designed.
