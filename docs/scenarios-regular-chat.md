# Regular Chat — Scenarios & Status

## RC-001 — Start a fresh regular chat

**Flow:** No session → model picker available → type message → send
→ `startSession({ sessionType: 'chat', chatModel, chatProvider })`
→ backend seeds `HumanMessage(brief)` into state → `run_chat` → LLM responds

**Status: ✓ Implemented**

---

## RC-002 — Continue regular chat (messages 2, 3, …)

**Flow:** Session active (`sessionId` set, `isRegularChat` true) → type next message → send
→ `continueRegularChat(text, model, provider)`
→ `POST /api/chat/continue/{session_id}` adds `HumanMessage` + re-invokes graph
→ `run_chat` receives full message history from checkpoint → responds

**Why graph must be re-invoked (not direct LLM call):**
LangGraph's `add_messages` reducer accumulates history in the checkpoint.
Each turn must go through the graph so history is preserved and the
full conversation is sent to the LLM on every turn.

**Status: ✗ Not implemented**
- Missing `POST /api/chat/continue/{session_id}` endpoint
- Missing `isRegularChat` flag in frontend
- ChatInput hidden after session starts (condition must include `isRegularChat`)
- Missing `continueRegularChat` function in `useAgentChat`

---

## RC-003 — Model locked once session starts

**Flow:** After first send (`sessionId` set), model picker becomes read-only label.

**Status: ✓ Implemented**

---

## RC-004 — Adaptive Thinking toggle

**Flow:** Anthropic model selected → toggle visible, enabled, ON by default.
Non-Anthropic model → toggle visible, disabled, forced OFF.
Switching providers resets toggle state automatically.

**Status: ✓ Implemented**

---

## RC-005 — Resume regular chat from sidebar

**Flow:** User clicks a previous regular chat in sidebar
→ `restoreSession` loads message history
→ `isRegularChat = true` detected from `current_stage === 'chat'`
→ ChatInput visible, user can continue

**Status: ✗ Broken**
- `restore_session` converts `current_stage='chat'` to `'complete'` (wrong)
- `restoreSession` frontend does not detect regular chat and set `isRegularChat`
- ChatInput would show (because `isComplete=true`) but next message goes to
  `post_completion_message` (stateless, does not preserve history)

---

## RC-006 — No "resume interrupted session" for regular chat

**Flow:** Regular chat has no interrupts, no pending questions, no approval.
Clicking a regular chat in sidebar just loads history + continues.
No "Session was interrupted" banner. No retry button.

**Status: ✓ By design** (no interrupt nodes in chat path)

---

## RC-007 — Skill pill before session starts

**Flow:** No session → user picks skill from + menu → pill shows in input bar
→ user can remove it, pick a different skill, remove again, freely
→ session type determined only when user sends first message:
  - Pill present → `agent_flow`
  - No pill → `chat`

**Status: ✓ Implemented**

---

## RC-008 — Skill selected during active regular chat

**Flow:** Session active → user picks skill → confirmation popup:
  "Starting a skill requires a new chat. Continue?"
→ On confirm: `newChat()` resets view, skill pill armed
→ User can still change/remove the pill
→ Session starts only when user sends first message

**Status: ✓ Implemented** (via `flowPopup` confirmation)

---

## Implementation Plan for RC-002 and RC-005

### Backend
1. `restore_session` — preserve `current_stage='chat'` (add to terminal set)
   and return `session_type` field in response
2. `POST /api/chat/continue/{session_id}` — adds `HumanMessage` to state
   and re-invokes graph via `_stream_graph`

### Frontend (`useAgentChat.js`)
1. Add `isRegularChat` ref, clear in `_resetChat`
2. Set `isRegularChat = true` when `_handleEvent` receives `done` with `status='chat'`
3. Set `isRegularChat = true` in `restoreSession` when `data.current_stage === 'chat'`
4. Add `continueRegularChat(text, model, provider)` function
5. Export `isRegularChat` and `continueRegularChat`

### Frontend (`ChatWindow.vue`)
1. Import and use `isRegularChat`, `continueRegularChat`
2. ChatInput condition: add `|| isRegularChat` so it stays visible
3. `handleChatSubmit`: if `isRegularChat && !isComplete` → `continueRegularChat`
