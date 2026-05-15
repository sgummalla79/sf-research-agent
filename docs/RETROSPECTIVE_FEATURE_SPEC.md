# Feature Specification: Retrospective Agent & Researcher Improvement Loop

## 1. Purpose

After a session reaches the `approved` state, a **Retrospective Agent** runs automatically
as a post-mortem step. It analyses every reviewer and approver verdict across all revision
cycles in the session and produces a structured lessons-learned report.

This report is stored per session and surfaced in a dedicated **Retrospectives** view under
the avatar menu. As more sessions accumulate, the retrospective agent uses a sliding window
of prior session reports to identify cross-session patterns, producing a richer analysis.
This growing pattern library is later used (Phase 2) to improve the researcher agent via
few-shot example injection and a distilled watch list.

---

## 2. Scope

| Phase | What is built |
|---|---|
| **Phase 1 (this spec)** | Retrospective agent, per-session report storage, Retrospectives UI under avatar |
| **Phase 2 (future spec)** | Few-shot RAG injection into researcher, distilled watch list accumulation |

---

## 3. Definitions

| Term | Meaning |
|---|---|
| **Revision cycle** | One pass through researcher → reviewer → approver. Session may have 0–5 cycles. |
| **Retro report** | The structured output of the retrospective agent for one completed session. |
| **Pattern window** | The set of prior session retro reports the agent considers for cross-session analysis. |
| **Watch list** | A distilled list of recurring issues extracted from multiple retro reports (Phase 2). |

---

## 4. When the Retrospective Agent Runs

The retrospective agent runs **once**, automatically, immediately after the approver returns
`status = "approved"`. It runs as a new LangGraph node inserted after `approver` in the
graph and before `END`.

It does **not** run when:
- The session is halted (max revisions exceeded)
- The session is in any incomplete state

The retrospective agent is **non-blocking** — it does not affect the approval result or the
delivered document. If it fails (LLM error, timeout), the session still ends as `approved` and
the failure is logged silently. The user is not shown an error.

---

## 5. Inputs to the Retrospective Agent

The agent reads the following from `AgentState` (all already present, no schema changes needed for Phase 1):

| Input | Source in state | Description |
|---|---|---|
| `project_brief` | `state.project_brief` | Original user brief |
| `discovery_questions` | `state.discovery_questions` | All Q&A pairs from discovery |
| `document_version` | `state.document_version` | How many versions were produced (= number of revision cycles) |
| `review_result` | `state.review_result` | **Final** reviewer verdict (last cycle only — see §5.1) |
| `approval_result` | `state.approval_result` | **Final** approver verdict |
| `messages` | `state.messages` | Full conversation history — contains all intermediate reviewer/approver AIMessages from prior cycles |
| `session_id` | `state.session_id` | For storing the retro report |

### 5.1 Reconstructing All Revision Cycles from Messages

The full revision history is not stored explicitly in `AgentState` — only the **final**
`review_result` and `approval_result` survive (each cycle overwrites the previous). However,
all intermediate verdicts are preserved in `state.messages` as `AIMessage` entries with
`name="reviewer"` and `name="approver"`.

The retrospective agent reconstructs the full cycle history by scanning `state.messages` in
order and extracting all reviewer and approver messages chronologically. This gives it the
complete picture: what was flagged in cycle 1, what was fixed, what persisted into cycle 2, etc.

---

## 6. Retrospective Agent Behaviour

### 6.1 Analysis the agent performs

The agent produces a structured report containing:

**A. Session Summary**
- Scope detected (which clouds / discussion type)
- Number of revision cycles required
- Final disposition: approved in N cycles

**B. Per-Cycle Breakdown**
For each revision cycle (1 through N):
- What the reviewer flagged (critical issues list)
- What the approver flagged (required changes list), if cycle reached approver
- Whether cycle N+1 resolved the prior cycle's issues or introduced new ones

**C. Researcher Pattern Analysis**
Issues classified into three categories:

| Category | Meaning |
|---|---|
| **First-attempt miss** | Issue raised in cycle 1, resolved in cycle 2 — researcher can improve |
| **Persistent miss** | Issue raised in cycle 1, still present in cycle 2+ — researcher is struggling with this pattern |
| **Regression** | Issue was resolved then reappeared — researcher fixed one thing but broke another |

**D. Recurring Gap Identification**
Specific sections or topic areas where issues were concentrated:
- e.g. "Risk Register was flagged in 2 of 3 cycles — consistently not client-specific enough"
- e.g. "Licensing flags were absent in v1 and v2 — only added in v3 under approver pressure"

**E. Researcher Health Score**
A simple signal, not a detailed metric:
- `healthy` — resolved all issues within 1 revision cycle
- `needs_attention` — required 2–3 cycles; some persistent patterns detected
- `stale` — same issues flagged across all cycles with minimal improvement

This score is stored and surfaced in the UI. If a researcher consistently scores `stale`
across multiple sessions, it is a signal that the base researcher system prompt needs
human review.

**F. Recommended Watch Items (per session)**
A short list (max 5 items) of specific, actionable patterns the researcher should watch
for in future sessions of this type:
- e.g. "For Service Cloud implementations: always include Einstein feature prerequisites in Section 3a"
- e.g. "For Data Cloud: credit consumption must be categorised in Section 5, not just mentioned"

These are session-scoped recommendations — they become input to the cross-session watch list
in Phase 2.

### 6.2 Cross-Session Pattern Analysis (sliding window)

From session 10 onward, the agent also receives prior retro reports from the DB and performs
a cross-session pattern analysis:

| Sessions completed | Window used |
|---|---|
| 1–9 | Per-session only (no cross-session analysis) |
| 10–19 | Last 5 completed session retro reports |
| 20–29 | Last 10 completed session retro reports |
| 30+ | Last 20 completed session retro reports |

The cross-session analysis adds:

**G. Cross-Session Pattern Summary**
- Issues that appeared in ≥ 50% of sessions in the window
- Sections most frequently flagged across sessions
- Whether researcher health scores are trending better, stable, or worse

This cross-session section is clearly separated from the per-session analysis in the UI.

---

## 7. Retrospective Report — Data Structure

A new `retro_reports` table in the database stores one row per completed session.

### 7.1 Database Schema

```sql
CREATE TABLE IF NOT EXISTS retro_reports (
    session_id       TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL,
    scope_flags      TEXT NOT NULL,   -- JSON: {service_cloud, experience_cloud, data_cloud, ...}
    revision_cycles  INTEGER NOT NULL,
    health_score     TEXT NOT NULL,   -- 'healthy' | 'needs_attention' | 'stale'
    report_markdown  TEXT NOT NULL,   -- full rendered markdown report
    watch_items      TEXT NOT NULL,   -- JSON: list of strings (max 5)
    session_title    TEXT             -- copied from agent_sessions.brief_snippet for display
);
```

### 7.2 State Schema Addition

Add one field to `AgentState` in `state.py`:

```python
# ── Stage 6 — Retrospective ───────────────────────────────────────────────────
retro_report: Optional[str] = None   # markdown report, populated after approval
```

---

## 8. Graph Changes

### 8.1 New node

```
approver → retrospective → END
```

The `route_after_approval` edge function changes:
- `approved` → `"retrospective"` (currently → `"complete"` / END)
- `halted` → `END` (unchanged)
- `researcher` → `"researcher"` (unchanged)

A new edge `retrospective → END` is unconditional.

### 8.2 New files

| File | Purpose |
|---|---|
| `backend/agents/retrospective.py` | Retrospective agent node function |

### 8.3 Modified files

| File | Change |
|---|---|
| `backend/graph/builder.py` | Add `retrospective` node, update edges |
| `backend/graph/edges.py` | `route_after_approval` returns `"retrospective"` instead of `"complete"` |
| `backend/state.py` | Add `retro_report: Optional[str]` field |
| `backend/persistence/checkpointer.py` | Add `retro_reports` table DDL + `save_retro_report()`, `get_retro_report()`, `list_retro_reports()`, `get_recent_retro_reports(n)` methods |
| `backend/api/routes/chat.py` | Emit `retro_complete` SSE event after retrospective runs |
| `backend/utils/agent_config.py` | Add `"retrospective"` to `AGENT_SLOTS` and `DEFAULT_AGENT_CONFIG` |

---

## 9. SSE Event

When the retrospective agent completes, the backend emits a new SSE event type:

```json
{
  "type": "retro_complete",
  "session_id": "...",
  "health_score": "healthy | needs_attention | stale",
  "revision_cycles": 2
}
```

The frontend receives this and shows a subtle notification:
> *"Retrospective analysis complete — view under Avatar → Retrospectives"*

The full report is NOT sent over SSE — it is fetched on demand via the API.

---

## 10. New API Endpoints

```
GET  /api/retro                          → list all retro reports (session_id, title, health_score, revision_cycles, created_at)
GET  /api/retro/{session_id}             → full retro report for one session (markdown + metadata)
```

No POST/DELETE endpoints needed — retro reports are immutable, created by the agent only.

---

## 11. Retrospectives UI

### 11.1 Entry point

Avatar menu gains a new item:

```
⚡ Providers
⚙  Agent Configuration
📊 Usage & Cost
🔍 Retrospectives       ← new
```

### 11.2 Retrospectives List Page

A new settings section component: `RetrospectivesSettings.vue`

Layout:
```
Retrospectives
─────────────────────────────────────────────────────────
Each completed session that has a retro report appears as a card:

┌─────────────────────────────────────────────────────┐
│  "Service Cloud + Experience Cloud — Acme Corp"      │
│  2 revision cycles  ·  May 14 2026                   │
│  ● needs_attention                                    │
│                                          [View →]    │
└─────────────────────────────────────────────────────┘
```

Health score badge colours:
- `healthy` → green
- `needs_attention` → amber
- `stale` → red

### 11.3 Retro Report Detail View

Clicking "View →" opens the full markdown report rendered inline (same renderer as the
document panel). A "← Back" link returns to the list.

Sections rendered:
1. Session Summary (scope, cycles, final disposition)
2. Per-Cycle Breakdown (expandable per cycle)
3. Researcher Pattern Analysis (first-attempt miss / persistent / regression)
4. Recurring Gap Identification
5. Researcher Health Score (prominent badge)
6. Recommended Watch Items (numbered list)
7. Cross-Session Pattern Summary (only shown if session count ≥ 10, shown as a separate
   bordered section with a header: *"Across last N sessions"*)

---

## 12. Retrospective Agent System Prompt (outline)

The agent is instructed to:

1. Identify how many revision cycles occurred by scanning the message history
2. For each cycle, extract: reviewer critical issues, approver required changes (if cycle reached approver)
3. Track which issues were resolved in subsequent cycles vs persisted vs regressed
4. Classify the researcher's improvement behaviour (healthy / needs_attention / stale)
5. Identify the top recurring gap areas by section (Executive Summary, Risk Register, Licensing, etc.)
6. Produce up to 5 actionable watch items specific to the scope type of this session
7. If cross-session context is provided, add a cross-session pattern section
8. Output the report as clean markdown

The agent is explicitly told:
- Do NOT judge the quality of the final document — the approver already did that
- Do NOT suggest changes to the document — it is already approved
- Focus exclusively on the improvement trajectory across revision cycles
- Be specific: name the section, name the issue, name the cycle it appeared/was resolved
- The watch items must be specific to this session's scope (e.g. Data Cloud watch items
  are irrelevant for a pure pattern-review session)

---

## 13. Agent Slot Configuration

The retrospective agent is added to `AGENT_SLOTS` with a default of Claude Haiku (fast,
low-cost — the analysis does not need a large model for per-session retros). For cross-session
analysis (window ≥ 10 sessions), the slot uses Claude Sonnet to handle the larger context.

| Slot | Default model | Rationale |
|---|---|---|
| `retrospective` | `claude-haiku-4-5-20251001` | Per-session: low context, fast, cheap |

The slot appears in Agent Configuration settings so the user can override it.

---

## 14. Failure Handling

| Failure scenario | Behaviour |
|---|---|
| Retrospective LLM call fails | Log warning, store `health_score = "unknown"`, `report_markdown = ""`. Session still ends as approved. |
| DB write for retro report fails | Log error, session still ends as approved. No retro visible in UI for this session. |
| `get_recent_retro_reports` returns fewer than expected | Agent proceeds with whatever is available; cross-session section is omitted if fewer than 5 reports exist. |

---

## 15. Files Created / Modified — Summary

### New files
| File | Description |
|---|---|
| `backend/agents/retrospective.py` | Retrospective agent node |
| `frontend/src/components/settings/RetrospectivesSettings.vue` | List + detail view |
| `backend/api/routes/retro.py` | `/api/retro` and `/api/retro/{session_id}` |

### Modified files
| File | Change |
|---|---|
| `backend/state.py` | Add `retro_report: Optional[str]` |
| `backend/graph/builder.py` | Add `retrospective` node + edge |
| `backend/graph/edges.py` | `route_after_approval` → `retrospective` on approved |
| `backend/persistence/checkpointer.py` | `retro_reports` table + 4 new DB methods |
| `backend/api/app.py` | Register `retro_router` |
| `backend/api/routes/chat.py` | Emit `retro_complete` SSE event |
| `backend/utils/agent_config.py` | Add `retrospective` slot + default |
| `frontend/src/components/SettingsPage.vue` | Add Retrospectives nav item |

---

## 16. Out of Scope for This Spec

- Phase 2: few-shot RAG injection into researcher context
- Phase 2: distilled watch list persisted to `app_config` and loaded by researcher
- Exporting retro reports (PDF/markdown download)
- Comparing two sessions side-by-side
- User annotations on retro reports
