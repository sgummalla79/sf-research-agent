# Pragna

A multi-agent AI platform that produces formal Architecture Recommendation Documents through a structured pipeline: intake → discovery → research → review → approval. Supports free-form chat as well.

> **This repo is the frontend (Vue 3 SPA) only.** The backend API lives at [sgummalla79/pragna-api](https://github.com/sgummalla79/pragna-api).

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Node.js | 18+ |
| npm | 9+ |

---

## Development

The API must be running separately on port 8000. Start it from the `pragna-api` repo.

```bash
npm install       # first time only
npm run dev       # http://localhost:5173 — proxies /api and /auth to localhost:8000
npm run build     # outputs to dist/
npm test
```

**Stop the dev server:**
```bash
npm run stop      # macOS/Linux
npm run stop:win  # Windows
```

---

## Tests

```bash
npm test          # run once
npm run test:watch
```

Tests live in:
- `src/tests/unit/` — composable and store unit tests
- `src/tests/component/` — Vue component tests

---

## Production Deployment

CI/CD is handled by two workflows:

| Workflow | Trigger | What it does |
|---|---|---|
| `deploy-staging.yml` | Push to `staging` or manual | Tests → builds `staging-{sha}` → blue-green deploy to `pragna-staging` |
| `deploy-production.yml` | Push to `main` or manual | Tests → patch version bump → builds `{version}` → blue-green deploy to `pragna` |

Manual dispatch on production lets you choose `patch / minor / major` bump.

**Image:** `ghcr.io/sgummalla79/pragna-ui` (Caddy serving the Vue SPA)

**Required GitHub secrets:** `VPS_HOST`, `VPS_SSH_KEY`

**Manual rollout:**
```bash
VERSION=1.2.3
kubectl set image deployment/pragna-ui-green \
  pragna-ui=ghcr.io/sgummalla79/pragna-ui:${VERSION} -n pragna
kubectl rollout status deployment/pragna-ui-green -n pragna --timeout=120s
kubectl patch service pragna-ui -n pragna \
  -p '{"spec":{"selector":{"app":"pragna-ui","slot":"green"}}}'
```

---

## Project Structure

```
pragna-ui/
├── src/
│   ├── api/              # API client (relative paths, proxied in dev)
│   ├── assets/           # SVG logos
│   ├── components/       # UI components
│   ├── composables/      # useAuth, useTheme, useConversations, etc.
│   ├── pages/            # ChatPage, ChatsPage, LoginPage, etc.
│   ├── router/           # Vue Router config
│   ├── stores/           # Pinia stores
│   └── tests/
│       ├── unit/
│       └── component/
├── public/               # Static assets (favicon, icons)
├── docker/
│   ├── Dockerfile.ui     # Node build → Caddy serve
│   ├── Caddyfile.ui      # Static SPA config
│   └── Caddyfile.prod    # Prod reverse proxy config
├── k8s/
│   ├── pragna/           # Production k8s manifests (blue + green)
│   └── pragna-staging/   # Staging k8s manifests (blue + green)
├── scripts/              # Dev runner, preflight checks
├── .github/workflows/    # deploy-staging.yml, deploy-production.yml
├── index.html
├── vite.config.js
├── package.json
└── VERSION               # Bumped automatically by production workflow
```
