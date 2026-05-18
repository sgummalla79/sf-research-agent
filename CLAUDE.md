# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Note:** The backend API lives in a separate repo: `sgummalla79/pragna-api`. This repo is the frontend (Vue 3 SPA) only.

## Development Commands

### Start the frontend
```bash
pnpm dev          # starts frontend dev server on port 5173
pnpm stop         # stop the process
```

### Frontend only
```bash
cd frontend
npm install
npm run dev       # port 5173, proxies /api and /auth to localhost:8000
npm run build     # outputs to frontend/dist/
```

> The API must be running separately on port 8000. Start it from the `pragna-api` repo with `uvicorn api.app:app --reload --port 8000`.

## Architecture Overview

**Pragna** is a multi-agent AI platform. This repo is the Vue 3 SPA that communicates with the FastAPI backend via REST and SSE.

### Frontend (`frontend/src/`)

**Single-page Vue 3 app.** `ChatWindow.vue` is the entire application shell (sidebar, chat area, settings, banners).

**Composables:**
- `useAgentChat.js` — All session state and SSE parsing. `_readStream()` handles all `stage_start / token / stage_end / question / done / error / provider_error` events
- `useTheme.js` — 6 themes; injects `<style id="pragna-theme-vars">` into `<head>` with `!important` to override Vue scoped styles
- `useAuth.js` — Auth0 session management

**API client** (`frontend/src/api/`): All endpoints are relative paths (`/api/*`, `/auth/*`). In dev, Vite proxies these to `localhost:8000`.

### SSE Event Types (emitted by API, consumed by `_handleEvent` in `useAgentChat.js`)

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

- **CI/CD:** Push to `staging` branch auto-deploys UI. Manual `workflow_dispatch` for production.
- **Image:** `ghcr.io/sgummalla79/pragna-ui` (Caddy serving Vue SPA)
- **VERSION file:** Bumped automatically by the workflow; do not bump manually before triggering a build
- **SSE requirement:** Caddy reverse-proxy has `flush_interval -1` and `read_timeout 300s` configured
