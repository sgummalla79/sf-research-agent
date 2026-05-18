# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Note:** The backend API lives in a separate repo: `sgummalla79/pragna-api`. This repo is the frontend (Vue 3 SPA) only.

## Development Commands

```bash
npm install       # first time only
npm run dev       # starts dev server on port 5173 (proxies /api and /auth to localhost:8000)
npm run build     # outputs to dist/
npm test          # run tests once
npm run test:watch
```

> The API must be running separately on port 8000. Start it from the `pragna-api` repo with `uvicorn api.app:app --reload --port 8000`.

## Architecture Overview

**Pragna** is a multi-agent AI platform. This repo is the Vue 3 SPA that communicates with the FastAPI backend via REST and SSE.

### Source (`src/`)

**Single-page Vue 3 app.** Entry point is `src/main.js`, app shell is `src/components/AppLayout.vue`.

**Composables:**
- `useAuth.js` — Auth0 session management
- `useTheme.js` — 6 themes; injects `<style id="pragna-theme-vars">` into `<head>` with `!important` to override Vue scoped styles
- `useConversations.js` — conversation list and session state
- `useDocumentPanel.js` — document panel open/close state

**API client** (`src/api/`): All endpoints are relative paths (`/api/*`, `/auth/*`). In dev, Vite proxies these to `localhost:8000`.

### SSE Event Types (emitted by API, consumed in `src/pages/ChatPage.vue`)

| Event | Payload |
|---|---|
| `stage_start` | `{stage, label}` |
| `token` | `{content}` |
| `stage_end` | `{stage}` |
| `document_ready` | `{version, session_id}` |
| `review_complete` | `{passed, feedback, critical_issues}` |
| `approval_complete` | `{status, comments, required_changes}` |
| `confirm_understanding` | `{content, session_id}` |
| `question` | `{questions[], session_id}` |
| `done` | `{status, document_version}` |
| `error` | `{message}` |
| `provider_error` | `{message, can_smart_pick}` — triggers two-option banner |

### Deployment

- **CI/CD:** Push to `staging` auto-deploys. Push to `main` auto-deploys to production (patch bump). Manual `workflow_dispatch` lets you choose bump type.
- **Blue-green:** Each deploy switches between the `blue` and `green` k8s slots; rolls back automatically on health check failure.
- **Image:** `ghcr.io/sgummalla79/pragna-ui` (Caddy serving Vue SPA)
- **VERSION file:** Bumped automatically by the production workflow; do not bump manually.
- **SSE requirement:** Caddy reverse-proxy has `flush_interval -1` and `read_timeout 300s` configured
