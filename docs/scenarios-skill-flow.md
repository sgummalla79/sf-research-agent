# Skill / Agent Flow — Scenarios & Status

## SF-001 — Start a skill session

**Flow:** No session → skill pill active → user types project brief → send
→ `startSession({ sessionType: 'agent_flow', flowId: skill.id })`
→ pipeline begins: intake → discovery → research → review → approval

Model picker locked for the entire pipeline duration.
No ChatInput shown (only the pending-questions and confirm panels).

**Status: ✓ Implemented**

---

## SF-002 — Pipeline stages run to completion

**Flow:** Each stage streams progress. User answers discovery questions,
confirms understanding. All stages complete. `isComplete = true`.
"Document approved and finalised" banner shows.

**Status: ✓ Implemented**

---

## SF-003 — Interrupted session — resume

**Flow:** Session stuck mid-pipeline (network error, server restart).
On restore: `isResumable = true` → banner: "Session was interrupted. ↺ Resume"
User clicks Resume → `retrySession()` → pipeline continues from where it stopped.

**Status: ✓ Implemented**

---

## SF-004 — Agent flow completes → model picker unlocks

**Flow:** `isComplete = true` → model picker must unlock so user can
choose any configured provider/model for the follow-up chat.
Adaptive Thinking toggle appears if Anthropic is selected.

**Status: ✗ Fixed in this branch**
`modelLocked` changed from `!!sessionId` to `!!sessionId && !isComplete && !isRegularChat`

---

## SF-005 — Post-completion first message

**Flow:** `isComplete = true`, model picker unlocked → user picks model
→ types message → send → `sendMessage(text, model, provider)`
→ `POST /api/chat/message/{session_id}` with document as system context
→ LLM responds using selected provider/model
→ Model remains unlocked for all subsequent messages

**Status: ✓ Works** (after SF-004 fix)

---

## SF-006 — Post-completion is regular chat

**Flow:** Every message after agent_flow completion:
- Model picker unlocked (can switch providers between messages)
- Adaptive Thinking toggle available for Anthropic models
- Document context always in system prompt
- Each message is independent (document + current message)

User is free to change model on every message. No session locking.

**Status: ✓ Works** (after SF-004 fix)

---

## modelLocked logic summary

| State | sessionId | isComplete | isRegularChat | modelLocked |
|---|---|---|---|---|
| No session | false | false | false | false |
| Agent_flow running | true | false | false | **true** |
| Agent_flow complete | true | true | false | false |
| Regular chat active | true | false | true | false |
