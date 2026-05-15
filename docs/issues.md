# Issues — Next Build

---

## UI-001 — Provider status pills: color and position ✓ Fixed

**Page:** Settings → LLM Providers

**Problem:**
- Not Connected pill should be red, Connected pill should be green
- Pills are currently aligned to the right end of the row — too far from the provider name, hard to notice at a glance

**Fix:**
- Pill moved inline next to provider name (left-aligned, immediately after the name)
- Not connected: red background + red text
- Connected: green background + green text

---

## UI-002 — Installed skill does not appear in skill picker without page refresh ✓ Fixed

**Page:** Skill picker (+ button)

**Problem:**
After installing a skill via the skill directory, the newly installed skill does not appear in the skill picker until the user manually refreshes the browser.

**Fix:**
`fetchFlows()` is now called whenever `appView` returns to `'chat'`, so the skill
picker is always up to date when the user comes back from the configuration page.

---

## UI-003 — Show app version in avatar menu ✓ Fixed

**Page:** Avatar menu (bottom of sidebar)

**Fix:**
- Backend: `GET /api/about` returns `{ "app": "Pragna", "version": "1.0.x" }`
  (reads from `VERSION` file baked into the Docker image)
- Frontend: version shown in avatar menu as `Pragna  v1.0.x`
- `docker/Dockerfile.api`: `COPY VERSION ./VERSION` added

---

## UI-004 — Stale session shows completion banner instead of "data unavailable" ✓ Fixed

**Page:** Chat — clicking a session in Recent Chats

**Problem:**
Sessions with no checkpoint data showed "Document approved" banner.

**Fix:**
When `isComplete` is true but `messages` is empty, show:
"This session's data is no longer available. [Start new chat]"
instead of the completion banner.
