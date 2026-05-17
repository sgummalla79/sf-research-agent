# Agent Flow — Complete Technical Reference

> **Purpose:** This document is the definitive reference for how the agent pipeline works. Use it for fine-tuning, debugging, and extending the pipeline. Everything here is derived directly from the source code — no assumptions.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Startup & Assembly](#2-startup--assembly)
3. [The Two Session Modes](#3-the-two-session-modes)
4. [Skill Definition: SKILL.md](#4-skill-definition-skillmd)
5. [State Object: AgentState](#5-state-object-agentstate)
6. [Graph Structure & Edge Routing](#6-graph-structure--edge-routing)
7. [The Four Execution Strategies](#7-the-four-execution-strategies)
   - [7A. IntakeStrategy](#7a-intakestrategy)
   - [7B. InterruptStrategy (Discovery)](#7b-interruptstrategy-discovery)
   - [7C. FanoutStrategy (Research)](#7c-fanoutstrategy-research)
   - [7D. StructuredStrategy (Review & Approval)](#7d-structuredstrategy-review--approval)
8. [LLM Slot System](#8-llm-slot-system)
9. [SSE Streaming & Event Protocol](#9-sse-streaming--event-protocol)
10. [API Endpoints](#10-api-endpoints)
11. [Thread Safety & Key Propagation](#11-thread-safety--key-propagation)
12. [Context Assembly](#12-context-assembly)
13. [Retry & Error Handling](#13-retry--error-handling)
14. [Usage Tracking](#14-usage-tracking)
15. [All Coded Scenarios](#15-all-coded-scenarios)
16. [Data Flow Diagram](#16-data-flow-diagram)
17. [Key Files Reference](#17-key-files-reference)
18. [Invariants & Rules Never to Break](#18-invariants--rules-never-to-break)

---

## 1. Overview

**Pragna** is a multi-agent AI platform. Its primary output is an **Architecture Recommendation Document (ARD)** produced by a 5-stage LangGraph pipeline called a **skill**.

The only skill currently implemented is `architect`. The framework is designed so that adding a new skill requires only a new directory under `backend/skills/` with a `SKILL.md` and `agents/*.md` files — no framework code changes.

**High-level flow:**

```
User submits brief / document / image
        │
        ▼
  [intake]       Extract project brief, confirm with user
        │
        ▼
  [discovery]    Ask clarifying questions in a loop until satisfied
        │
        ▼
  [research]     Parallel web search + architecture reasoning → writer synthesises document
        │
        ▼
  [review]       Peer review: PASS or FAIL
        │
  PASS  │  FAIL ──────────────────────────────────────► back to [research]
        ▼
  [approval]     Final gate: APPROVE or REJECT
        │
  APPROVE │  REJECT (× up to 5) ──────────────────────► back to [research]
          ▼
       DONE — Architecture document delivered
```

---

## 2. Startup & Assembly

**File:** `backend/api/app.py`

The FastAPI lifespan function runs once on server start:

### Step 1 — Environment validation
Checks that all required env vars are present and valid:
- `SETTINGS_SECRET` — must be a valid Fernet key (used to encrypt user API keys in DB)
- `JWT_SECRET` — signs session cookies
- `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET` — Auth0 OAuth
- `DATABASE_URL` — required only if `DB_BACKEND == "postgres"`

Hard exits (`sys.exit(1)`) if anything is missing. This prevents silent misconfiguration.

### Step 2 — Database connection
Opens an async DB connection via `get_async_checkpointer()`. The same DB object serves as:
- The LangGraph **checkpointer** (stores pipeline state between HTTP requests)
- The application DB (users, sessions, agent_configs, usage records, prompt snapshots)

Supports SQLite (zero-config, dev) and PostgreSQL (production). PostgreSQL requires `autocommit=True, prepare_threshold=None` for Neon PgBouncer compatibility.

### Step 3 — Skill registry
`SkillRegistry` scans `backend/skills/` for any directory that contains a `SKILL.md` file. For each one, `SkillLoader.load(skill_dir)` runs:

1. Parses `---` YAML frontmatter → skill `id`, `name`, `description`, `icon`, `version`, `agent_labels`
2. Parses `## Pipeline` section → ordered list of stage IDs: `["intake", "discovery", "research", "review", "approval"]`
3. Parses each `## Stage: <id>` block as YAML → a validated `StageConfig` Pydantic object
4. Reads every `agents/*.md` file into memory: `{stem → content}` (e.g. `{"discovery": "...", "research-writer": "..."}`)
5. Reads `references/*.md` (curated knowledge docs) and `assets/*` (templates, CSS) into memory
6. Validates: every stage's required agent key must have a corresponding `.md` file on disk. Fails hard at startup if any are missing.
7. Returns an immutable `LoadedSkill(manifest, skill_dir, agents, references, assets)` dataclass

Result is cached in `SkillRegistry._skills` dict, protected by `threading.RLock`.

### Step 4 — Graph compilation
For each loaded skill, `SkillEngine.build(skill, checkpointer)` builds and compiles a LangGraph `StateGraph(AgentState)`:

1. Adds two built-in nodes: `router` (passthrough lambda) and `chat` (free-form LLM node)
2. For each stage in `skill.manifest.stages`:
   - Looks up `StrategyRegistry.get(stage.execution)` — a self-registered strategy class
   - Calls `strategy.build_node(stage_cfg, skill)` → returns the node function (a plain callable)
   - Registers it as a LangGraph node with the stage's id
3. Sets `router` as the entry point
4. Wires all edges (see §6 for full routing logic)
5. Calls `graph.compile(checkpointer=checkpointer)` → produces the executable `CompiledStateGraph`

### Step 5 — State exposed on app
```python
app.state.graphs         # dict: {skill_id → compiled_graph}
app.state.graph          # first compiled graph (used as default/fallback)
app.state.skill_registry # SkillRegistry instance
app.state.db             # async DB + checkpointer
```

---

## 3. The Two Session Modes

`AgentState.session_type` controls how the router dispatches:

| Mode | Value | Behaviour |
|---|---|---|
| Agent flow | `"agent_flow"` | Full 5-stage pipeline. Uses `flow_id` to pick skill. |
| Free-form chat | `"chat"` | Single `chat` node. No pipeline stages run. |

The `router` node is a passthrough (no-op). Its conditional edge reads `state.session_type`:
- `"chat"` → routes to `chat` node → `END`
- anything else → routes to the first pipeline stage (`intake`)

`session_type` in the `agent_sessions` DB table is the **source of truth** and never changes once set at session creation — except when a post-completion follow-up converts it to `"chat"` via `db.update_session_type()`.

---

## 4. Skill Definition: SKILL.md

**File:** `backend/skills/architect/SKILL.md`

This file is the **single source of truth** for the architect pipeline. No pipeline logic exists in Python code — only the strategies that execute each stage type.

### Full file structure

```
---
name: Architect
id: architect
description: >
  Formal Architecture Recommendation Document via a 5-stage pipeline.
  Platform-agnostic: works with any enterprise or SaaS technology stack.
icon: "⚡"
version: 1
agent_labels:
  intake-document:    "Intake: Document"
  intake-image:       "Intake: Image Analysis"
  discovery:          "Discovery Agent"
  research-search:    "Research: Web Search"
  research-reasoning: "Research: Architecture"
  research-writer:    "Research: Writer"
  review:             "Review Agent"
  approval:           "Approver Gate"
---

## Pipeline

intake → discovery → research → review → approval

## Stage: intake

execution: intake
llm_slot: intake
agents:
  document: intake-document
  image: intake-image
interrupt: confirm_understanding

## Stage: discovery

execution: structured_interrupt
llm_slot: discovery
agent: discovery
output_schema: DiscoveryOutput
interrupt: question

## Stage: research

execution: fanout_merge
llm_slot: researcher_search
fanout:
  - llm_slot: researcher_search
    agent: research-search
  - llm_slot: researcher_reasoning
    agent: research-reasoning
merge:
  llm_slot: researcher_writer
  agent: research-writer

## Stage: review

execution: structured
llm_slot: reviewer
agent: review
output_schema: ReviewResult
context: [document_draft, document_version, discovery_questions]
on_pass: approval
on_fail: research

## Stage: approval

execution: structured
llm_slot: approver
agent: approval
output_schema: ApprovalResult
context: [project_brief, document_draft, document_version, discovery_questions, review_result, revision_count]
on_approve: complete
on_reject: research
max_revisions: 5
```

### Stage config fields explained

| Field | Type | Purpose |
|---|---|---|
| `execution` | string | Which strategy handles this stage. Must match a registered strategy name. |
| `llm_slot` | string | Key into `session_agent_config` for model resolution. |
| `agent` | string | Stem of `agents/<name>.md` — the system prompt file. |
| `agents` | dict | Used by `intake` only. Maps input type (`document`, `image`) to agent stems. |
| `output_schema` | string | Pydantic class name from `state.py` for structured output. |
| `context` | list[str] | State fields to include in the human turn (assembled by `build_context`). |
| `interrupt` | string | Informational label for the interrupt type (not used by code, for readability). |
| `on_pass` / `on_fail` | string | Stage IDs to route to based on `review_result.passed`. Both must be set together. |
| `on_approve` / `on_reject` | string | Stage IDs for approval gate routing. Both must be set together. |
| `max_revisions` | int | Max rejection loops. After this count, routes to `END` with `current_stage="halted"`. Falls back to `config.MAX_REVISIONS` (5). |
| `fanout` | list[FanoutBranch] | Parallel branches for `fanout_merge` strategy. Each branch has `llm_slot` and `agent`. |
| `merge` | FanoutBranch | The writer step that synthesises all fanout branch outputs. |

---

## 5. State Object: AgentState

**File:** `backend/state.py`

A Pydantic model. This single object is the only thing that flows through the entire pipeline. LangGraph merges partial update dicts returned by node functions into it.

### Full field reference

```python
class AgentState(BaseModel):
    # ── Session metadata ──────────────────────────────────────────────────────
    session_id:   str = ""              # UUID, set at session creation
    created_at:   str = ""              # ISO UTC timestamp, set by intake

    # ── Stage tracking ────────────────────────────────────────────────────────
    current_stage: Literal[
        "intake", "discovery", "research", "review", "approval",
        "complete", "halted", "invalid_input", "chat"
    ] = "intake"
    revision_count: int = 0             # incremented each time Approver rejects

    # ── Stage 1 — Intake ─────────────────────────────────────────────────────
    source_type:         Literal["brief", "document", "image"] = "brief"
    uploaded_file_path:  str = ""       # path to saved document on disk
    uploaded_image_path: str = ""       # path to saved image on disk
    raw_document_text:   str = ""       # extracted text from doc — never re-read from disk
    project_brief:       str = ""       # final brief sent to discovery

    # ── Stage 2 — Discovery ──────────────────────────────────────────────────
    discovery_questions: list[DiscoveryQuestion] = []
    discovery_complete:  bool = False

    # ── Stage 3 — Research ───────────────────────────────────────────────────
    document_draft:   str = ""          # the current ARD content
    document_version: int = 0           # incremented on each research run

    # ── Stage 4 — Review ─────────────────────────────────────────────────────
    review_result: Optional[ReviewResult] = None

    # ── Stage 5 — Approval ───────────────────────────────────────────────────
    approval_result: Optional[ApprovalResult] = None

    # ── Conversation history ─────────────────────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages] = []  # APPEND-ONLY

    # ── Token usage ──────────────────────────────────────────────────────────
    usage_records: Annotated[list[dict], operator.add] = []    # APPEND-ONLY

    # ── Session type ──────────────────────────────────────────────────────────
    session_type: Literal["chat", "agent_flow"] = "agent_flow"

    # ── Agent flow config ─────────────────────────────────────────────────────
    flow_id:     str  = "architect"
    flow_config: dict = {}              # agent_key → prompt string (frozen at session start)

    # ── Chat config (used when session_type == "chat") ────────────────────────
    chat_model:        str  = "claude-sonnet-4-6"
    chat_provider:     str  = "anthropic"
    extended_thinking: bool = False

    # ── Prompt snapshot ───────────────────────────────────────────────────────
    flow_snapshot_id:      int | None = None   # DB row id
    flow_snapshot_version: int | None = None   # human-readable version

    # ── LLM config snapshot — NEVER mutated by nodes ─────────────────────────
    session_agent_config: dict = {}     # slot → {provider, model}
```

### LangGraph reducer behaviour

| Field | Reducer | What it means |
|---|---|---|
| `messages` | `add_messages` | Each node appends; old messages are never removed. LangGraph deduplicates by message id. |
| `usage_records` | `operator.add` | Each node appends its cost records. Total accumulates across the whole session. |
| All other fields | Plain overwrite | Last write wins. Nodes return a partial dict; LangGraph merges only the keys present. |

### Structured output types (nested Pydantic models)

**DiscoveryOutput** — what the discovery LLM returns:
```python
class DiscoveryOutput(BaseModel):
    next_questions:     list[str]
    updated_questions:  list[DiscoveryQuestion]
    discovery_complete: bool
    reasoning:          str
```

**DiscoveryQuestion** — one question/answer record:
```python
class DiscoveryQuestion(BaseModel):
    question:  str
    answer:    Optional[str] = None
    satisfied: bool = False             # True once agent deems the answer sufficient
```

**ReviewResult** — what the reviewer LLM returns:
```python
class ReviewResult(BaseModel):
    passed:          bool
    feedback:        str               # always populated; praise if passed, critique if failed
    critical_issues: list[str] = []
```

**ApprovalResult** — what the approver LLM returns:
```python
class ApprovalResult(BaseModel):
    status:           Literal["approved", "rejected"]
    comments:         str              # always populated
    required_changes: list[str] = []
```

---

## 6. Graph Structure & Edge Routing

**File:** `backend/framework/engine.py`

The engine wires five distinct edge patterns:

### Entry edges (router → first stage or chat)
```python
def route(state):
    return "chat" if state.session_type == "chat" else "intake"
```

### Intake edges (invalid_input branches to END)
```python
def route(state):
    return "end" if state.current_stage == "invalid_input" else "discovery"
```

### Loop edges (discovery self-loops until complete)
```python
def route(state):
    return "research" if state.discovery_complete else "discovery"
```
The discovery node is entered repeatedly until `state.discovery_complete == True`.

### Pass/fail edges (review)
```python
def route(state):
    if state.review_result and state.review_result.passed:
        return "approval"      # on_pass
    return "research"          # on_fail
```

### Gate edges (approval — with halt logic)
```python
def route(state):
    if state.approval_result and state.approval_result.status == "approved":
        return "complete"      # → END
    if state.revision_count >= max_revisions:   # max_revisions = 5
        return "halted"        # → END
    return "research"          # on_reject — another full cycle
```

### Full graph topology (architect skill)

```
                     ┌────────────────────────────────────────────────────────┐
                     │                                                        │
START → router → intake → discovery ⟲ → research → review → approval → END  │
              ↓               ↑              ↑          │         │           │
           (chat)          (loop until    (on_fail) ────┘      (on_reject) ──┘
              ↓           complete)                       (revision_count < 5)
             END                                                               │
                                                                    (revision_count ≥ 5)
                                                                           → END (halted)
        (invalid_input → END from intake)
```

**recursion_limit is set to 100** in `_stream_graph` (default LangGraph limit of 25 is too low for a 5-stage pipeline with up to 5 revision cycles × Q&A loops).

---

## 7. The Four Execution Strategies

**Files:** `backend/framework/strategies/`

All strategies inherit from `ExecutionStrategy` (abstract base) and self-register via `StrategyRegistry.register(MyStrategy())` at import time. The engine looks them up by name — it never imports strategy classes directly.

---

### 7A. IntakeStrategy

**Strategy name:** `intake`  
**File:** `backend/framework/strategies/intake.py`  
**Used by:** stage `intake`

#### Purpose
Normalise all three input types (brief text, document, image) into a single `project_brief` string. Everything downstream works only with `project_brief`.

#### Execution paths

**Path 1 — Plain text brief (`state.source_type == "brief"`):**
- Zero LLM calls.
- Wraps `project_brief` in a `HumanMessage`. Returns base state update.
- No interrupt. Proceeds directly to discovery.

**Path 2 — Document upload (`state.source_type == "document"`):**
- Text was already extracted from the file at upload time (by `file_parser.extract_text`) and stored in `state.raw_document_text`. The node never reads the file again.
- Calls LLM using `intake-document.md` system prompt + `"Extract a structured Project Brief from this document.\n\n---\n{raw_document_text}\n---"` as human turn.
- LLM returns plain text (no structured output schema).
- Calls `interrupt({"__type": "confirm_understanding", "content": brief})` — **graph pauses here**.
- Resume: user's correction text appended if non-empty: `brief += "\n\n**User correction:** {correction}"`

**Path 3 — Image upload (`state.source_type == "image"`):**
- Reads image bytes from `state.uploaded_image_path`, base64-encodes them.
- Detects media type from file extension (`.jpg/.jpeg → image/jpeg`, `.png → image/png`, `.gif → image/gif`, `.webp → image/webp`).
- Calls LLM with structured output (`_ImageResult` schema) + vision message (base64 data URL + text instruction).
- Uses `intake-image.md` system prompt.
- `_ImageResult` has three fields: `is_architecture_related (bool)`, `extracted_brief (str)`, `rejection_reason (str)`.
- **If `is_architecture_related == False`:** Sets `current_stage = "invalid_input"`. Returns rejection message as `AIMessage`. Engine routes to `END`.
- **If valid:** Same confirm_understanding interrupt flow as document.

#### State written
```python
{
    "current_stage":  stage.id,       # "intake" or "invalid_input"
    "created_at":     ISO_UTC,
    "project_brief":  str,            # set only on success paths
    "usage_records":  [urec],         # only for document/image (LLM was called)
    "messages":       [HumanMessage, AIMessage],
}
```

---

### 7B. InterruptStrategy (Discovery)

**Strategy name:** `structured_interrupt`  
**File:** `backend/framework/strategies/interrupt.py`  
**Used by:** stage `discovery`

#### Purpose
Ask the user clarifying questions in a loop until the LLM signals it has enough information to proceed to research.

#### Key constants
- `_WINDOW = 30` — how many messages to include as context per invocation
- `MAX_DISCOVERY_QUESTIONS = 30` — hard safety cap from `config.py` (env: `MAX_DISCOVERY_QUESTIONS`)

#### Execution flow (one LangGraph invocation)

1. Slices `state.messages[-30:]` for context window.
2. Ensures window ends with `HumanMessage` (Anthropic requirement — adds "Please begin the discovery session." if needed).
3. Calls LLM with structured output (`DiscoveryOutput` schema) using `discovery.md` system prompt.
4. Checks three **completion conditions** (any one triggers completion):
   - `result.discovery_complete == True` — LLM decided it has enough information
   - `sum(1 for q in result.updated_questions if q.answer) >= MAX_DISCOVERY_QUESTIONS` — safety cap
   - `not result.next_questions` — LLM returned empty question list
5. **If complete:** Returns `{"discovery_complete": True, ...}`. Loop edge routes to `research`.
6. **If not complete:**
   - Calls `interrupt(result.next_questions)` — **graph pauses**, questions list sent as interrupt value.
   - `_stream_graph` detects this, emits `question` SSE with the list.
   - Resume value: list of answer strings (one per question, position-aligned).
   - Reconciles answers: `zip(result.next_questions, answers)` → updates matching `DiscoveryQuestion` objects.
   - Appends Q&A as `AIMessage` (questions) + `HumanMessage` (Q1/A1 format) to messages.
   - Returns `{"discovery_complete": False, ...}`.
   - Loop edge routes back to `discovery` again.

#### This node is entered multiple times in sequence

LangGraph re-enters the `discovery` node on every resume because the loop edge evaluates `state.discovery_complete`. The message history accumulates across all invocations, giving the LLM full context of all prior Q&A.

#### State written
```python
{
    "current_stage":       "discovery",
    "discovery_questions": list[DiscoveryQuestion],  # growing list with answers filled in
    "discovery_complete":  bool,
    "usage_records":       [urec],
    "messages":            [AIMessage, HumanMessage],  # only on non-complete path
}
```

---

### 7C. FanoutStrategy (Research)

**Strategy name:** `fanout_merge`  
**File:** `backend/framework/strategies/fanout.py`  
**Used by:** stage `research`

#### Purpose
Run independent research in parallel, then synthesise all outputs into the Architecture Recommendation Document.

#### Stage config (from SKILL.md)
```yaml
fanout:
  - llm_slot: researcher_search    # → Perplexity sonar-pro (web search)
    agent: research-search
  - llm_slot: researcher_reasoning # → Google gemini-2.5-pro (architecture reasoning)
    agent: research-reasoning
merge:
  llm_slot: researcher_writer      # → Anthropic claude-sonnet-4-6 (synthesis)
  agent: research-writer
```

#### Step 1 — Pre-flight: key capture for threads
Before launching any thread:
```python
_captured_keys = get_session_keys(state.session_id)   # reads _session_store dict
_captured_mode = get_session_mode(state.session_id)
```
This is the **critical** step. LangGraph's internal `asyncio.create_task` loses the ContextVar. The session store dict survives all context boundaries.

#### Step 2 — Parallel branches
`ThreadPoolExecutor(max_workers=len(stage.fanout))` — one thread per branch. The architect skill has 2 branches, so `max_workers=2`.

Each `run_branch(branch)` thread:
1. **Re-establishes user context** at thread start: `set_user_context(_captured_keys, _captured_mode)` — sets ContextVar inside this thread so `get_user_key()` works.
2. Gets LLM: `get_llm_for_slot(branch.llm_slot, state.session_agent_config)`
3. Gets system prompt: `state.flow_config[branch.agent]`
4. Builds context: `build_context(["project_brief", "discovery_questions"], state)`
5. Calls: `invoke_with_retry(llm, [SystemMessage(prompt), HumanMessage(context)])`
6. Returns: `(branch.agent, response.content, usage_record)`

Results collected via `as_completed`. Branch output order is non-deterministic.

#### Step 3 — Merge writer (sequential after all branches complete)
Assembles `research_block`: all branch outputs joined as markdown sections with `---` separators and headings derived from `branch.agent.replace('-', ' ').title()`.

**First document (`state.document_version == 0`):**
```
{project_brief + discovery_questions}

## Research Outputs
{research_block}

Using the research above, produce the complete Architecture Recommendation Document.
```

**Revision (`state.document_version > 0`):**
```
{document_draft + document_version + approval_result + review_result}

## Refreshed Research
{research_block}

Instructions:
1. Add ## Revision Summary listing every change.
2. Resolve all flagged items with [RESOLVED: <comment>].
3. Do not rewrite sections that were not flagged.
4. Output the complete updated document.
```

Resets `review_result = None` and `approval_result = None` so the review/approval nodes start fresh.

Increments `document_version` by 1.

**Token streaming is suppressed** for the `research` node in `_stream_graph`. The complete document appears via `document_ready` SSE when the node finishes.

#### State written
```python
{
    "current_stage":    "research",
    "document_draft":   str,                           # full ARD text
    "document_version": state.document_version + 1,
    "review_result":    None,                          # cleared for fresh review
    "approval_result":  None,                          # cleared for fresh approval
    "usage_records":    [urec_branch1, urec_branch2, urec_writer],
    "messages":         [AIMessage],                   # brief summary message
}
```

---

### 7D. StructuredStrategy (Review & Approval)

**Strategy name:** `structured`  
**File:** `backend/framework/strategies/structured.py`  
**Used by:** stages `review` and `approval`

#### Purpose
Single LLM call with structured output. No interrupts. No loops within the node — routing loops are handled by the graph edges.

#### Execution flow

1. Gets LLM with structured output: `get_llm_for_slot(slot, config).with_structured_output(schema_cls, include_raw=True)`
2. Gets system prompt: `state.flow_config[stage.agent_key]`
3. Builds human turn: `build_context(stage.context or _DEFAULT_CONTEXT, state)`
4. Calls: `invoke_with_retry(llm, [SystemMessage(prompt), HumanMessage(context)])`
5. Calls `_build_state_update(stage, state, result, urec)` to map result type to state fields

#### Review stage specifics

- **LLM slot:** `reviewer` → Anthropic claude-sonnet-4-6
- **Schema:** `ReviewResult` — `passed`, `feedback`, `critical_issues`
- **Context fields:** `document_draft`, `document_version`, `discovery_questions`
- **SSE emitted after node end:** `review_complete {passed, feedback, critical_issues}`
- **Routing:** `passed=True → approval` (on_pass), `passed=False → research` (on_fail)

#### Approval stage specifics

- **LLM slot:** `approver` → Anthropic claude-opus-4-7 (the heaviest model in the pipeline)
- **Schema:** `ApprovalResult` — `status ("approved"|"rejected")`, `comments`, `required_changes`
- **Context fields:** `project_brief`, `document_draft`, `document_version`, `discovery_questions`, `review_result`, `revision_count`
- On rejection: `revision_count` is incremented in the returned state update
- **SSE emitted after node end:** `approval_complete {status, comments, required_changes}`
- **Routing:** `approved → END (complete)`, `rejected + count < 5 → research`, `rejected + count ≥ 5 → END (halted)`

#### State written (review)
```python
{
    "current_stage": "review",
    "review_result": ReviewResult,
    "usage_records": [urec],
    "messages":      [AIMessage("Review PASSED/FAILED. {feedback}")],
}
```

#### State written (approval)
```python
{
    "current_stage":   "approval",
    "approval_result": ApprovalResult,
    "revision_count":  state.revision_count + (1 if rejected else 0),
    "usage_records":   [urec],
    "messages":        [AIMessage("Decision: APPROVED/REJECTED. {comments}")],
}
```

---

## 8. LLM Slot System

**File:** `backend/framework/defaults.py`

### The 7 slots and their defaults

| Slot | Default Provider | Default Model | Role in pipeline |
|---|---|---|---|
| `intake` | anthropic | claude-sonnet-4-6 | Brief/doc/image extraction |
| `discovery` | anthropic | claude-sonnet-4-6 | Structured Q&A |
| `researcher_search` | perplexity | sonar-pro | Web-grounded research |
| `researcher_reasoning` | google | gemini-2.5-pro | Architecture analysis (1M context) |
| `researcher_writer` | anthropic | claude-sonnet-4-6 | ARD synthesis |
| `reviewer` | anthropic | claude-sonnet-4-6 | Peer review |
| `approver` | anthropic | claude-opus-4-7 | Final gate (heaviest model) |

### Smart pick preference order per slot

```python
_SLOT_PREFERENCE = {
    "researcher_search":    ["perplexity", "google", "anthropic", "openai"],
    "researcher_reasoning": ["google",     "anthropic", "openai", "perplexity"],
    "approver":             ["anthropic",  "google",    "openai", "perplexity"],
}
_DEFAULT_PREFERENCE = ["anthropic", "google", "openai", "perplexity"]
# (all other slots use _DEFAULT_PREFERENCE)
```

### Best model per provider per slot

```python
_PROVIDER_SLOT_MODEL = {
    "anthropic": {
        "default":  "claude-sonnet-4-6",
        "approver": "claude-opus-4-7",
    },
    "google": {
        "default":              "gemini-2.0-flash",
        "researcher_reasoning": "gemini-2.5-pro",
    },
    "perplexity": {
        "default":           "sonar-pro",
        "researcher_search": "sonar-pro",
    },
    "openai": {
        "default": "gpt-4o",
    },
}
```

### Resolution priority (per slot, evaluated at session start)

1. **Snapshot model override** (stored in DB alongside prompt snapshot) — used if that provider is currently connected.
2. **User's explicitly saved config** from DB (`agent_config` key) — used if provider connected. If provider is NOT connected: raises `HTTP 422` (explicit configuration that's now broken).
3. **Smart pick** from connected providers — uses preference order above.

`session_agent_config` is written to DB (`session_agent_config_{session_id}` key) and injected into the initial `AgentState`. **Nodes read it, never write it.**

### Retry with smart_pick

When the user calls `/retry/{session_id}?smart_pick=true`:
- `force_smart_pick=True` is passed to `_resolve_agent_cfg`
- Saved `agent_config` is ignored entirely
- Every slot is re-resolved via `smart_pick()` from currently connected providers
- Result is patched into checkpoint state via `graph.aupdate_state()`

---

## 9. SSE Streaming & Event Protocol

**File:** `backend/api/routes/chat.py`, function `_stream_graph`

All responses are `text/event-stream` (SSE). Format:
```
data: {"type": "<event_type>", ...payload...}\n\n
```

### Full event catalogue

| Event | When emitted | Payload |
|---|---|---|
| `stage_start` | LangGraph `on_chain_start` for a known stage node | `{stage: str, label: str}` |
| `token` | LangGraph `on_chat_model_stream` from any non-research node | `{content: str}` — one text chunk |
| `stage_end` | LangGraph `on_chain_end` for intake or discovery | `{stage: str}` |
| `document_ready` | LangGraph `on_chain_end` for `research` | `{version: int, session_id: str}` |
| `review_complete` | LangGraph `on_chain_end` for `review` | `{passed: bool, feedback: str, critical_issues: [str]}` |
| `approval_complete` | LangGraph `on_chain_end` for `approval` | `{status: str, comments: str, required_changes: [str]}` |
| `confirm_understanding` | After stream: interrupt with `__type == "confirm_understanding"` | `{content: str, session_id: str}` |
| `question` | After stream: interrupt with question list | `{questions: [str], session_id: str}` |
| `done` | After stream: `state.next` is empty (pipeline finished) | `{status: str, document_version: int, revision_count: int}` |
| `error` | Any unhandled exception in `_stream_graph` | `{message: str}` |
| `provider_error` | RuntimeError "API key not configured for..." | `{message: str, can_smart_pick: bool}` |

### Stage labels (for stage_start)

```python
STAGE_LABELS = {
    "intake":    "Intake Agent",
    "discovery": "Discovery Agent",
    "research":  "Research Agent",
    "review":    "Review Agent",
    "approval":  "Approver Gate",
}
```

### Token streaming note

`on_chat_model_stream` events where `metadata.langgraph_node == "research"` are **suppressed**. The research node runs in `ThreadPoolExecutor` threads — no streaming is possible. The document appears all at once via `document_ready`.

For multi-modal content (list of blocks), only blocks with `type == "text"` are extracted and emitted as tokens.

### Interrupt detection after stream

After `astream_events` completes, `_stream_graph` calls `graph.aget_state(config)`:
- If `state.next` is non-empty → graph is paused at an interrupt:
  - Iterates `state.tasks` to find the first `task.interrupts[0].value`
  - If `isinstance(value, dict) and value["__type"] == "confirm_understanding"` → emits `confirm_understanding`
  - Otherwise (list of strings) → emits `question`
- If `state.next` is empty → emits `done` with `status = state.values["current_stage"]`

### done status values

| `status` value | Meaning |
|---|---|
| `"complete"` | Approval granted, document is final |
| `"halted"` | Max revisions reached, pipeline stopped |
| `"invalid_input"` | Image was not architecture-related |
| `"chat"` | Free-form chat session completed |

---

## 10. API Endpoints

**File:** `backend/api/routes/chat.py`

### POST /api/chat/start

Starts a new session from a typed brief or free-form chat message.

**Request body (`StartRequest`):**
```json
{
    "brief":             "string",
    "session_type":      "agent_flow" | "chat",
    "flow_id":           "architect",
    "chat_model":        "claude-sonnet-4-6",
    "chat_provider":     "anthropic",
    "extended_thinking": false
}
```

**Processing:**
1. Generates `session_id` (UUID4)
2. Records session in DB
3. Fires background title generation (Claude Haiku, fire-and-forget)
4. Loads skill + latest prompt snapshot from DB
5. Builds `flow_config` (snapshot prompts override file prompts)
6. Resolves `session_agent_config` per §8
7. Constructs `AgentState` with all resolved config frozen in
8. Returns SSE stream

**Response headers:**
- `X-Session-Id: <session_id>` — frontend reads this to know the session id before the stream starts
- `Content-Type: text/event-stream`

---

### POST /api/chat/upload

Starts a session from an uploaded file.

**Accepted types:**
- Documents: `.pdf`, `.docx`, `.txt`, `.md`
- Images: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

**Size limit:** 10 MB (configurable via `MAX_FILE_SIZE_MB` env var).

**Processing:**
1. Validates file type and size
2. Saves original file to `uploads/` directory (audit trail)
3. For documents: extracts text immediately via `file_parser` (the graph never re-reads the file)
4. For images: stores path only — intake node uses vision at runtime
5. Sets `source_type = "image" | "document"` in initial state

---

### POST /api/chat/reply/{session_id}

Resumes a graph that is paused at an interrupt (discovery question or confirm_understanding).

**Request body (`ReplyRequest`):**
```json
{ "answers": "string or list of strings" }
```

**Processing:**
- Calls `_stream_graph(graph, Command(resume=body.answers), config)`
- LangGraph's `Command(resume=value)` resumes the interrupted node with `value` as the return value of `interrupt()`

---

### POST /api/chat/retry/{session_id}

Re-streams from the last LangGraph checkpoint.

**Query params:** `?smart_pick=true` — forces smart-pick ignoring saved config.

**Use case:** Provider became unavailable after session was created. Or user got a `provider_error` SSE and wants to retry with available providers.

**Processing:**
1. Checks session exists and is not already complete/halted
2. Checks no pending interrupt exists (would need `/reply` not `/retry`)
3. Re-resolves `session_agent_config` (optionally with smart_pick)
4. If resolution fails with 422: returns HTTP 409 `provider_unavailable`
5. If no providers at all: returns HTTP 409 `no_providers`
6. Patches checkpoint via `graph.aupdate_state(config, {"session_agent_config": fresh_cfg})`
7. Streams with `input_=None` (continues from checkpoint, does not reset state)

---

### POST /api/chat/message/{session_id}

Post-completion follow-up on a finished agent_flow session. **Does not use the graph.**

**Processing:**
1. Reads `document_draft` from graph checkpoint
2. Updates `session_type = "chat"` in DB
3. Builds system message: "You are a technical architecture assistant. The approved document: {document}"
4. Streams direct LLM response via `llm.astream([SystemMessage, HumanMessage])`

---

### POST /api/chat/continue/{session_id}

Continues a regular chat session (session_type was "chat" from the start).

**Processing:**
- Appends `HumanMessage(body.text)` to state via `{"messages": [HumanMessage(text)]}`
- Re-invokes graph → router → chat node → runs `run_chat`

---

### POST /api/chat/fork/{session_id}

Creates a new session pre-seeded with a completed session's approved document.

**Processing:**
1. Reads `document_draft`, `document_version`, `project_brief` from source session
2. Creates new session with `source_type="document"`, `raw_document_text=document`, `document_draft=document`
3. Starts full pipeline (intake → discovery → research → review → approval)
4. The writer will be in revision mode immediately (document_version > 0) but the brief is enriched

**Use case:** Run a different skill or a re-analysis against the same approved document.

---

### GET /api/chat/session/{session_id}/restore

Reconstructs a previous session for the frontend. Reads LangGraph checkpoint state and serialises messages, detects pending interrupts, resolves `current_stage`.

**Terminal stage normalisation:** If the graph finished (no `state.next`) but `current_stage` is not in `{"complete", "halted", "invalid_input", "chat"}` — e.g. the session crashed mid-pipeline — it normalises to `"complete"`.

---

### GET /api/chat/document/{session_id}

Returns `{content, version}` — the current `document_draft` and `document_version` from checkpoint state.

---

## 11. Thread Safety & Key Propagation

**File:** `backend/utils/user_context.py`

### The problem

LangGraph runs synchronous node functions via `run_in_executor` inside tasks created with:
```python
asyncio.create_task(coro, context=<langgraph_internal_context>)
```

This context **does not inherit** the HTTP request's `_user_keys` ContextVar. Inside node threads, `get_user_key(provider)` finds nothing and raises `RuntimeError`.

### Two mechanisms (belt and suspenders)

**Mechanism 1 — ContextVar `_user_keys`:**
```python
_user_keys:      ContextVar[dict] = ContextVar("user_keys",      default={})
_anthropic_mode: ContextVar[str]  = ContextVar("anthropic_mode", default="direct")
```
Set at auth middleware time via `set_user_context(keys, mode)`. Works for async code and threads that LangChain creates via `copy_context()` (intake, discovery, review, approval strategies use this path).

**Mechanism 2 — Session key store:**
```python
_session_store: dict[str, dict] = {}
_session_store_lock: threading.Lock = threading.Lock()
```
A plain thread-safe dict: `{session_id → {"keys": {...}, "mode": "..."}}`

- **Written:** `_stream_graph` calls `register_session_keys(session_id, keys)` BEFORE `astream_events` starts
- **Read:** `fanout.py`'s `run_branch` calls `get_session_keys(session_id)` at thread start, then calls `set_user_context(keys, mode)` to re-establish the ContextVar inside the `ThreadPoolExecutor` thread
- **Cleaned up:** `_stream_graph` calls `unregister_session_keys(session_id)` in `finally` block

### `_resolve_keys(session_id)` — unified accessor

```python
def _resolve_keys(session_id: str = "") -> dict:
    keys = _user_keys.get()       # try ContextVar first (fast path)
    if keys:
        return keys
    if session_id:
        stored = get_session_keys(session_id)   # fall back to session store
        if stored:
            return stored
    return {}
```

### Why fanout needs explicit re-establishment

The `ThreadPoolExecutor` threads in `fanout.py` are created by `concurrent.futures` — they have their own OS threads with no asyncio context at all. The ContextVar is not inherited. `set_user_context()` must be called explicitly at the top of each `run_branch` thread before any LLM call.

The other strategies (intake, interrupt, structured) run inside LangChain-managed threads that DO use `copy_context()` — the ContextVar works there without extra effort.

---

## 12. Context Assembly

**File:** `backend/framework/context.py`

`build_context(fields: list[str], state: AgentState) → str`

Assembles the human-turn message by formatting each declared state field using a registered formatter. Empty or None values are silently skipped.

### Field formatters

| Field name | Formatted output |
|---|---|
| `project_brief` | `## Project Brief\n{value}` |
| `document_draft` | `## Document Under Review\n{value}` |
| `document_version` | `_Document version: {N}_` |
| `discovery_questions` | `## Discovery Answers\n- **{question}**: {answer}` (only answered ones) |
| `review_result` | `## Technical Review Result\nStatus: PASSED/FAILED\n{feedback}\n**Critical issues:** ...` |
| `approval_result` | `## Previous Approver Feedback\n{comments}\n**Required changes:** ...` |
| `revision_count` | `_Revision {N} of this document._` (omitted if 0) |

Sections are joined with `\n\n`. Unknown fields fall back to `## {Title Case}\n{value}`.

### Per-stage context declarations (from SKILL.md)

| Stage | Context fields used |
|---|---|
| `intake` | N/A — uses state fields directly (raw_document_text, uploaded_image_path) |
| `discovery` | `messages` (windowed, not via build_context) |
| `research` (fanout) | `project_brief`, `discovery_questions` |
| `research` (writer, initial) | `project_brief`, `discovery_questions` |
| `research` (writer, revision) | `document_draft`, `document_version`, `approval_result`, `review_result` |
| `review` | `document_draft`, `document_version`, `discovery_questions` |
| `approval` | `project_brief`, `document_draft`, `document_version`, `discovery_questions`, `review_result`, `revision_count` |

---

## 13. Retry & Error Handling

**File:** `backend/utils/llm_retry.py`

### LLM call retry (tenacity)

Wraps every `llm.invoke(messages)` call:
```python
@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=2, max=32),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, WARNING),
    reraise=True,
)
def invoke_with_retry(llm, messages): ...
```

**Retryable signals** (substring match in exception message):
`rate limit`, `429`, `500`, `503`, `timeout`, `connection`, `overloaded`, `temporarily unavailable`, `resource exhausted`, `internal server error`, `api_error`

**Backoff:** 2s → 4s → 8s → 16s → 32s (max). Up to 5 attempts. Reraises after all attempts exhausted.

### _stream_graph exception handling

```python
except Exception as exc:
    if "API key not configured for" in msg or "No LLM providers are configured" in msg:
        yield _sse("provider_error", {
            "message":        msg,
            "can_smart_pick": bool(connected_providers()),
        })
    else:
        yield _sse("error", {"message": msg})
```

`provider_error` is a special event that triggers a two-option banner in the frontend:
- "Configure Providers" → opens Settings → Providers
- "Use Smart Config" → calls `/retry?smart_pick=true`

`can_smart_pick` is `False` when no providers are connected at all (can't smart-pick from zero providers).

### Retry endpoint error codes

| HTTP Code | `error` field | Meaning |
|---|---|---|
| 409 | `provider_unavailable` | Saved config points to disconnected provider |
| 409 | `no_providers` | Zero providers connected |
| 400 | — | Session already complete/halted, or pending interrupt exists |
| 404 | — | Session not found |

---

## 14. Usage Tracking

**File:** `backend/utils/pricing.py`

Every LLM call (every `invoke_with_retry`) produces a usage record:
```python
{
    "agent":         str,   # stage.id (e.g. "research", "review")
    "model":         str,   # model name (e.g. "claude-sonnet-4-6")
    "input_tokens":  int,
    "output_tokens": int,
    "cost_usd":      float, # (input * input_price + output * output_price) / 1_000_000
    "created_at":    str,   # ISO UTC
}
```

Records accumulate in `state.usage_records` via the `operator.add` reducer (never overwritten).

### Flush points (fire-and-forget background tasks)

- After `research` node ends (`on_chain_end`)
- After `review` node ends
- After `approval` node ends
- After the full stream ends (final flush from `aget_state`)

Flush failures are silently swallowed — they never break the SSE stream.

### Known prices (per 1M tokens)

| Model | Input | Output |
|---|---|---|
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-haiku-4-5-20251001 | $0.80 | $4.00 |
| sonar-pro | $3.00 | $15.00 |
| gemini-2.5-pro | $1.25 | $10.00 |

Models not in `MODEL_PRICING` get `$0.00` cost (unknown pricing).

---

## 15. All Coded Scenarios

### Scenario 1 — Happy path (text brief → approved document)
```
/start {brief, session_type="agent_flow"}
→ intake: passes through (no LLM)
→ discovery: LLM asks questions, user answers via /reply × N
→ discovery_complete=True
→ research: 2 parallel branches + writer → document v1
→ review: PASS
→ approval: APPROVED
→ done {status: "complete", document_version: 1}
```

### Scenario 2 — Document upload with user correction
```
/upload (PDF/DOCX/TXT)
→ intake: LLM extracts brief from raw_document_text
→ PAUSE: confirm_understanding SSE emitted
→ /reply {answers: "The system uses microservices, not monolith"}
→ brief amended: "... **User correction:** The system uses microservices..."
→ discovery → research → review → approval → done
```

### Scenario 3 — Image upload rejected (not architecture-related)
```
/upload (image)
→ intake: vision LLM → _ImageResult {is_architecture_related: false}
→ current_stage = "invalid_input"
→ edge routes to END
→ done {status: "invalid_input"}
```

### Scenario 4 — Image upload accepted
```
/upload (image)
→ intake: vision LLM → _ImageResult {is_architecture_related: true, extracted_brief: "..."}
→ PAUSE: confirm_understanding SSE
→ /reply → brief confirmed/corrected
→ discovery → research → review → approval → done
```

### Scenario 5 — Review fails, triggers single revision
```
... → research (v1) → review: FAIL {critical_issues: [...]}
→ on_fail: research
→ research (v2): revision mode — adds Revision Summary, resolves flags
→ review: PASS
→ approval: APPROVED
→ done {document_version: 2}
```

### Scenario 6 — Approval rejects, triggers revision cycle
```
... → review: PASS → approval: REJECTED {required_changes: [...]}
→ revision_count = 1
→ on_reject: research
→ research (v2): revision mode
→ review: PASS → approval: APPROVED
→ done {document_version: 2, revision_count: 1}
```

### Scenario 7 — Max revisions reached (halted)
```
... → approval: REJECTED (5th time)
→ revision_count = 5
→ edge: revision_count >= max_revisions (5) → END
→ done {status: "halted", revision_count: 5}
```

### Scenario 8 — Provider not configured mid-pipeline
```
Any node → get_llm_for_slot → build_llm → get_key("anthropic")
→ get_user_key raises RuntimeError("API key not configured for 'anthropic'...")
→ _stream_graph catches it
→ provider_error {message: "...", can_smart_pick: true/false}
```

### Scenario 9 — Retry with smart_pick after provider error
```
/retry/{session_id}?smart_pick=true
→ force_smart_pick=True: ignores saved agent_config
→ smart_pick from connected providers
→ graph.aupdate_state: patches session_agent_config in checkpoint
→ SSE stream resumes from last checkpoint position
```

### Scenario 10 — Post-completion follow-up chat
```
(pipeline done, approval granted)
User sends message
→ /message/{session_id}
→ graph NOT invoked
→ direct LLM stream with document as system context
→ session_type updated to "chat" in DB
→ done {status: "complete"}
```

### Scenario 11 — Free-form chat session
```
/start {session_type: "chat", chat_model: "claude-sonnet-4-6", chat_provider: "anthropic"}
→ router: session_type == "chat" → chat node
→ run_chat: standard or extended_thinking mode
→ done {status: "chat"}
```

### Scenario 12 — Extended thinking mode
```
/start {session_type: "chat", extended_thinking: true, chat_provider: "anthropic"}
→ chat node → _run_with_thinking
→ Anthropic SDK direct call (not LangChain):
    client.messages.create(model=..., thinking={"type":"enabled","budget_tokens":10000})
→ Extracts text blocks (skips thinking blocks)
→ done
```

### Scenario 13 — Chat continuation (adding turns)
```
/continue/{session_id}
→ {"messages": [HumanMessage(body.text)]} appended to state
→ graph re-invoked → router → chat node
→ run_chat sees full conversation history in state.messages
→ responds with next AI turn
```

### Scenario 14 — Session fork
```
(session A is complete with document_draft)
/fork/session_A {flow_id: "architect"}
→ new session B created
→ initial_state: source_type="document", raw_document_text=A.document_draft,
                 document_draft=A.document_draft, document_version=A.document_version
→ full pipeline runs for session B (research will be in revision mode from the start)
```

### Scenario 15 — Transient LLM failure with retry
```
invoke_with_retry(llm, messages)
→ LLM returns 429 (rate limited)
→ tenacity catches: is_retryable("rate limit") → True
→ sleep 2s, retry
→ LLM returns 503
→ sleep 4s, retry
→ LLM succeeds on 3rd attempt
```

### Scenario 16 — Session restore after browser refresh
```
GET /session/{session_id}/restore
→ reads LangGraph checkpoint via aget_state
→ serialises messages (preserves stage name from msg.name or content heuristic)
→ detects pending interrupt (confirm_understanding or question)
→ returns: {messages, pending_questions, pending_confirmation, current_stage, has_document}
Frontend reconstructs the UI from this response
```

---

## 16. Data Flow Diagram

```
HTTP Request
    │
    ▼
RequestLoggerMiddleware → auth middleware (sets _user_keys ContextVar)
    │
    ▼
FastAPI route handler (/api/chat/start | /upload | /reply | /retry | ...)
    │
    │  resolves: flow_config (prompts), session_agent_config (models)
    │
    ▼
_stream_graph(graph, input_, config)
    │
    │  register_session_keys(session_id, keys)  ← belt-and-suspenders for threads
    │  config["recursion_limit"] = 100
    │
    ▼
graph.astream_events(input_, config, version="v2")
    │
    ├── on_chain_start [intake]      → SSE: stage_start
    │       │
    │       ▼ IntakeStrategy.node(state)
    │       ├── brief:    no LLM → pass through
    │       ├── document: LLM(intake-document) → extract brief
    │       │             interrupt(confirm_understanding) → SSE: confirm_understanding
    │       └── image:    LLM(intake-image, vision) → _ImageResult
    │                     → invalid: current_stage="invalid_input" → END
    │                     → valid: interrupt(confirm_understanding) → SSE: confirm_understanding
    │
    ├── on_chain_start [discovery]   → SSE: stage_start
    │       │
    │       ▼ InterruptStrategy.node(state)  [loops until complete]
    │       LLM(discovery, DiscoveryOutput) → questions
    │       interrupt(questions) → SSE: question
    │       [user answers via /reply → Command(resume=answers)]
    │       [loop back to discovery if not complete]
    │
    ├── on_chain_start [research]    → SSE: stage_start
    │       │
    │       ▼ FanoutStrategy.node(state)
    │       ThreadPoolExecutor (2 workers):
    │         ├── run_branch(research-search)    [Perplexity sonar-pro]
    │         └── run_branch(research-reasoning) [Google gemini-2.5-pro]
    │       (branches run concurrently, no token streaming)
    │       merge_writer(research-writer)         [Anthropic claude-sonnet-4-6]
    │       → SSE: document_ready
    │
    ├── on_chain_start [review]      → SSE: stage_start
    │       │
    │       ▼ StructuredStrategy.node(state)
    │       LLM(review, ReviewResult) → {passed, feedback, critical_issues}
    │       → SSE: review_complete
    │       [on_fail → back to research]
    │
    ├── on_chain_start [approval]    → SSE: stage_start
    │       │
    │       ▼ StructuredStrategy.node(state)
    │       LLM(approval, ApprovalResult) → {status, comments, required_changes}
    │       → SSE: approval_complete
    │       [on_reject → back to research (up to 5×)]
    │       [approved → END]
    │
    └── stream ends
            │
            ▼
        graph.aget_state(config)
        state.next?
          ├── yes → detect interrupt type → SSE: question | confirm_understanding
          └── no  → SSE: done {status, document_version, revision_count}
            │
            ▼
        unregister_session_keys(session_id)
```

---

## 17. Key Files Reference

| File | Role |
|---|---|
| `backend/api/app.py` | FastAPI startup: env validation, DB, skill registry, graph compilation |
| `backend/api/routes/chat.py` | All SSE endpoints + `_stream_graph` central emitter |
| `backend/state.py` | `AgentState` + all structured output Pydantic models |
| `backend/framework/schema.py` | `SkillManifest` + `StageConfig` + `FanoutBranch` — validated at load time |
| `backend/framework/loader.py` | `SkillLoader` — parses SKILL.md + reads agents/ into `LoadedSkill` |
| `backend/framework/registry.py` | `SkillRegistry` — thread-safe skill cache, `load_all()` at startup |
| `backend/framework/engine.py` | `SkillEngine.build()` — compiles `StateGraph` from `LoadedSkill` |
| `backend/framework/strategies/base.py` | `ExecutionStrategy` ABC + `StrategyRegistry` |
| `backend/framework/strategies/intake.py` | `IntakeStrategy` — brief/document/image input normalisation |
| `backend/framework/strategies/interrupt.py` | `InterruptStrategy` — discovery Q&A loop |
| `backend/framework/strategies/fanout.py` | `FanoutStrategy` — parallel research + merge writer |
| `backend/framework/strategies/structured.py` | `StructuredStrategy` — review + approval |
| `backend/framework/defaults.py` | Slot resolution: `smart_pick`, `resolve_agent_config`, `SMART_SLOT_DEFAULTS` |
| `backend/framework/context.py` | `build_context` — assembles human-turn from state fields |
| `backend/framework/chat.py` | `run_chat` — free-form chat node (standard + extended thinking) |
| `backend/utils/user_context.py` | ContextVar + session store for cross-thread key propagation |
| `backend/utils/llm_factory.py` | `build_llm(provider, model)` + `get_llm_for_slot(slot, config)` |
| `backend/utils/llm_retry.py` | `invoke_with_retry` — tenacity retry wrapper for all LLM calls |
| `backend/utils/api_keys.py` | Fernet encryption/decryption per user (HKDF-derived keys) |
| `backend/utils/pricing.py` | `usage_record` + `cost_usd` — token cost tracking |
| `backend/config.py` | Global constants: `MAX_REVISIONS=5`, `MAX_DISCOVERY_QUESTIONS=30`, `SESSION_TTL_DAYS=15` |
| `backend/persistence/checkpointer.py` | Async SQLite + PostgreSQL checkpointer for LangGraph |
| `backend/skills/architect/SKILL.md` | Pipeline declaration — the only skill currently |
| `backend/skills/architect/agents/*.md` | System prompts for each agent (8 files) |

---

## 18. Invariants & Rules Never to Break

These are load-bearing design constraints. Breaking any of them will cause subtle bugs.

1. **`session_agent_config` is frozen at session start.** Nodes must never write to it. It is only ever patched externally via `graph.aupdate_state()` during a retry.

2. **`session_type` in the DB `agent_sessions` table is the source of truth** for whether a session is `chat` or `agent_flow`. Never infer it from LangGraph checkpoint state.

3. **`recursion_limit = 100` must stay.** The default of 25 is too low for 5 stages × discovery loops × up to 5 revision cycles.

4. **PostgreSQL connections must use `autocommit=True, prepare_threshold=None`.** Neon PgBouncer rejects prepared statements.

5. **`register_session_keys` must be called before `astream_events` starts.** If called after, fanout branch threads may start before the keys are registered and fail with `provider_error`.

6. **`fanout.py` `run_branch` must call `set_user_context` at thread start.** This is the only mechanism that works inside `ThreadPoolExecutor` threads. Without it, `get_user_key()` will raise for every call in a thread.

7. **`review_result` and `approval_result` must be reset to `None` by the research node.** The review/approval structured strategy reads these fields — if they carry over from the previous cycle, the LLM gets misleading prior-cycle context.

8. **`document_version` starts at 0 and is incremented by the research node.** The fanout strategy checks `document_version == 0` to decide between initial-document and revision prompts. Starting at a non-zero value will skip the initial document prompt.

9. **`on_pass/on_fail` must both be set or both omitted.** Same for `on_approve/on_reject`. This is enforced as a Pydantic validator in `StageConfig`.

10. **`fanout_merge` requires both `fanout` and `merge`.** Enforced at load time and by the strategy at node build time.

11. **`MAX_REVISIONS = 5` applies globally** unless overridden per-stage via `max_revisions:` in SKILL.md. The gate edge compares `state.revision_count >= max_revisions` — it halts at 5 rejections, not 5 revision cycles (first rejection → count=1, so on the 5th rejection count reaches 5).

12. **Prompt content lives in `state.flow_config`, never imported directly.** Nodes always read `state.flow_config.get(stage.agent_key, "")`. This is what makes prompt snapshots work — the snapshot overrides happen at session start when `flow_config` is built.

13. **`usage_records` and `messages` use LangGraph reducers and are append-only.** Never return a full list replacement for these fields; only return the new records to append. Returning the full list would duplicate all prior entries.

14. **Token streaming is suppressed for the `research` node** (`langgraph_node != "research"` check in `_stream_graph`). Do not remove this check — the research node has no streaming; the document appears via `document_ready`.
