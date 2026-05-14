# Issues — Next Build

---

## UI-001 — Provider status pills: color and position

**Page:** Settings → LLM Providers

**Problem:**
- Not Connected pill should be red, Connected pill should be green
- Pills are currently aligned to the right end of the row — too far from the provider name, hard to notice at a glance

**Expected:**
- Pills appear immediately after the provider name (inline, left-aligned)
- Red for not connected, green for connected

---

## UI-002 — Installed skill does not appear in skill picker without page refresh

**Page:** Skill picker (+ button)

**Problem:**
After installing a skill via the skill directory, the newly installed skill does not appear in the skill picker until the user manually refreshes the browser.

**Expected:**
Skill picker updates reactively immediately after installation — no refresh required.

**Likely cause:**
The installed skills list in the frontend is fetched once on mount and not re-fetched after a successful install action.

---

## UI-003 — Show app version in avatar menu via About

**Page:** Avatar menu (bottom of sidebar)

**Problem:**
No way to see which version of Pragna is running without checking the server.

**Expected:**
- Add an **About** item to the avatar dropdown menu
- About shows the current version number (read from the `VERSION` file baked into the image at build time)
- Version should be surfaced via a backend endpoint (e.g. `GET /health` already returns it, or a dedicated `GET /api/about`) so the frontend can display it

**Implementation notes:**
- At Docker build time, copy `VERSION` file into the image or pass it as a build arg
- Expose it via the API so the frontend doesn't need to bundle it separately
- Display format: `Pragna v1.0.2`

---

## UI-004 — Stale session shows completion banner instead of "data unavailable"

**Page:** Chat — clicking a session in Recent Chats

**Problem:**
Sessions that exist in the sidebar but have no checkpoint data (e.g. after a DB
migration wipe) load and show the "Document approved and finalised" banner with no
messages. This is confusing — the user thinks a session completed but there is
actually no content.

**Expected:**
When a session is opened and no checkpoint/message data is found, show a clear
message: "This session's data is no longer available. Start a new session." with
a button to open a new chat.

**Likely cause:**
The frontend receives an empty or null state from the backend when checkpoint data
is missing, and the chat window falls through to the "complete" stage banner as a
default.

**Implementation notes:**
- Backend: when GET session state returns empty/null messages, return a specific
  indicator (e.g. `{ "empty": true }`) so the frontend can distinguish "no data"
  from "completed session"
- Frontend: check for empty state before rendering the completion banner
- Also: on startup, clean up `agent_sessions` rows that have no corresponding
  `checkpoints` row (orphaned sessions) so they never appear in the sidebar
