# Business Scenarios — Pragna

All scenarios verified and implemented. Use this document as the reference
for expected behaviour across all chat and skill session flows.

---

## Provider / Model Selection Rules

### Smart Provider Selection (Agent Flow)

When a skill session starts, the backend resolves the LLM for each pipeline slot
(`intake`, `discovery`, `researcher_search`, `researcher_reasoning`,
`researcher_writer`, `reviewer`, `approver`) using this priority:

| Priority | Condition | Result |
|---|---|---|
| 1 | Snapshot per-agent override set AND provider connected | Use snapshot override |
| 2 | User saved an agent_config for this slot AND provider connected | Use user config |
| 3 | Neither above — or configured provider not connected | smart_pick from connected providers |
| Error | User explicitly set a slot to a provider that is NOT connected | HTTP 422 — shown to user |

**Smart-pick preference per slot:**

| Slot | Provider preference order |
|---|---|
| `researcher_search` | Perplexity → Google → Anthropic → OpenAI |
| `researcher_reasoning` | Google → Anthropic → OpenAI → Perplexity |
| `approver` | Anthropic → Google → OpenAI → Perplexity |
| All others | Anthropic → Google → OpenAI → Perplexity |

A user with only one provider configured will always get that provider across
all slots — no "API key not configured for X" errors unless they explicitly
locked a slot to an unavailable provider.

**Status: ✓**

---

## Model Locking Rules

| State | Model picker | Adaptive toggle |
|---|---|---|
| No session | Unlocked — pick freely | Shown if Anthropic selected |
| Skill pipeline running | **Locked** (read-only) | Hidden (n/a during pipeline) |
| Skill pipeline complete | Unlocked | Shown if Anthropic selected |
| Regular chat active | **Locked** | Shown if Anthropic, disabled otherwise |

`modelLocked = !!sessionId && !isComplete`

---

## Regular Chat

### RC-001 — Start a fresh regular chat

No session → model picker available → user types message → send
→ `startSession({ sessionType: 'chat', chatModel, chatProvider })`
→ backend seeds first message into state → `run_chat` → LLM responds

**Status: ✓**

---

### RC-002 — Continue regular chat (messages 2, 3, …)

Session active → user types next message → send
→ `POST /api/chat/continue/{session_id}` adds message and re-invokes graph
→ full conversation history preserved in LangGraph checkpoint
→ LLM receives entire conversation on every turn

**Status: ✓**

---

### RC-003 — Model locked once session starts

After first message is sent, model picker becomes a read-only label.
Model cannot be changed mid-conversation.

**Status: ✓**

---

### RC-004 — Adaptive Thinking toggle

Anthropic model → toggle always visible, ON by default, user can turn off.
Non-Anthropic model → toggle always visible, disabled and forced OFF.
Switching providers resets toggle state automatically.

**Status: ✓**

---

### RC-005 — Resume regular chat from sidebar

User clicks a previous regular chat in sidebar → history loads
→ `isRegularChat = true` (detected from `current_stage === 'chat'`)
→ ChatInput visible, user continues the conversation

No "resume interrupted session" concept for regular chat — there are
no interrupts or pending questions in the regular chat path.

**Status: ✓**

---

### RC-006 — Skill pill before session starts

No session → user can freely add a skill pill, remove it, add a different
one, as many times as they like. Session type is determined only when the
user sends their first message:
- Skill pill present → `agent_flow`
- No pill → `chat`

**Status: ✓**

---

### RC-007 — Skill selected during active regular chat

Session active → user picks a skill → confirmation:
"Starting a skill requires a new chat. Continue?"
→ On confirm: view resets to empty state, skill pill armed
→ User can still change or remove the pill
→ Session starts only when the user sends their first message

**Status: ✓**

---

## Skill / Agent Flow

### SF-001 — Start a skill session

No session, skill pill active → user types project brief → send
→ `startSession({ sessionType: 'agent_flow', flowId: skill.id })`
→ pipeline begins: intake → discovery → research → review → approval

Model picker locked. No chat input during the pipeline (only
discovery answers and confirmation panels are shown).

**Status: ✓**

---

### SF-002 — Pipeline stages run to completion

Each stage streams progress. User answers discovery questions and
confirms understanding. All stages complete. `isComplete = true`.
"Document approved and finalised" banner shown.

**Status: ✓**

---

### SF-003 — Interrupted session — resume

Session stuck mid-pipeline (network error, server restart).
On sidebar restore: `isResumable = true` → banner:
"⚡ This session was interrupted. ↺ Resume Session"
User clicks Resume → pipeline continues from where it stopped.

**Status: ✓**

---

### SF-004 — Pipeline completes → model picker unlocks

`isComplete = true` → model picker unlocks so the user can choose
any configured provider/model for the follow-up conversation.
Adaptive Thinking toggle appears if Anthropic is selected.

**Status: ✓**

---

### SF-005 — Post-completion first message

`isComplete = true`, model picker unlocked → user picks model → types message → send
→ `POST /api/chat/message/{session_id}` with approved document as system context
→ LLM responds using the selected provider/model

Model remains unlocked for all subsequent messages.

**Status: ✓**

---

### SF-006 — Post-completion follow-up chat

Every message after agent_flow completion:
- Model picker unlocked — user can switch provider/model between messages
- Adaptive Thinking available for Anthropic models
- Approved document always in system context
- Each message is independent (document + current message, no accumulated history)

**Status: ✓**

---

### SF-007 — Completion banner is dismissible and reappears on reopen

When agent_flow completes, the "Document approved" banner shows with a ✕ dismiss button.
Dismissing hides it for the current page session only. Reopening the session
(or logging out and back in) shows the banner again — until the user sends
a post-completion message (SF-008).

**Status: ✓**

---

### SF-008 — Session converts to regular chat after first post-completion message

When the user sends the first post-completion message:
- `session_type` in `agent_sessions` is updated from `agent_flow` → `chat`
- On any future restore (including after logout/login), `session_type='chat'`
  is the source of truth → `isRegularChat=true` → NO completion banner shown
- The session behaves as regular chat from this point forward

**Status: ✓**
