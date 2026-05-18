# Pragna

A multi-agent AI platform that produces formal Architecture Recommendation Documents through a structured pipeline: intake → discovery → research → review → approval. Supports free-form chat as well.

> **This repo is the frontend (Vue 3 SPA) only.** The backend API lives at [sgummalla79/pragna-api](https://github.com/sgummalla79/pragna-api).

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Node.js | 18+ |
| npm | 9+ |
| pnpm | 8+ (optional, for root scripts) |

---

## Development

The API must be running separately on port 8000. Start it from the `pragna-api` repo.

**Start the frontend dev server:**

```bash
pnpm dev
# or
cd frontend && npm install && npm run dev
```

Vite starts on **http://localhost:5173** and proxies `/api` and `/auth` to `localhost:8000`.

**Stop:**

```bash
pnpm stop
```

**Build for production:**

```bash
cd frontend && npm run build
# outputs to frontend/dist/
```

---

## Tests

```bash
cd frontend
npm install       # first time only
npm run test      # run all tests once
npm run test:watch
```

Tests live in:
- `frontend/src/tests/unit/` — composable unit tests
- `frontend/src/tests/component/` — Vue component tests

---

## Production Deployment

CI/CD is handled by `.github/workflows/build-and-push.yml`:

- **Staging:** push to `staging` branch → auto-builds and deploys `pragna-ui` image
- **Production:** manual `workflow_dispatch` → bumps `VERSION`, builds image, pushes to GHCR, rolls out via `kubectl set image`

**Image:** `ghcr.io/sgummalla79/pragna-ui` (Caddy serving the Vue SPA)

**Required GitHub secrets:**

| Secret | Value |
|---|---|
| `VPS_HOST` | Public IP or hostname of the K3s server |
| `VPS_SSH_KEY` | Private SSH key with root access |

**Manual rollout (without GitHub Actions):**

```bash
VERSION=1.2.3
kubectl set image deployment/pragna-ui \
  pragna-ui=ghcr.io/sgummalla79/pragna-ui:${VERSION} \
  -n pragna
kubectl rollout status deployment/pragna-ui -n pragna --timeout=120s
```

---

## Project Structure

```
pragna-ui/
├── frontend/
│   └── src/
│       ├── api/              # API client (relative paths, proxied in dev)
│       ├── components/       # UI components
│       ├── composables/
│       │   ├── useAgentChat.js   # SSE stream handler, session state
│       │   ├── useTheme.js       # 6 themes
│       │   └── useAuth.js        # Auth0 session management
│       ├── stores/           # Pinia stores
│       ├── views/            # Page-level components
│       └── tests/
│           ├── unit/
│           └── component/
├── docker/
│   ├── Dockerfile.ui         # Node build → Caddy serve
│   ├── Caddyfile.ui          # Static SPA config
│   └── Caddyfile.prod        # Prod reverse proxy config
├── k8s/
│   ├── pragna/               # Production k8s manifests
│   └── pragna-staging/       # Staging k8s manifests
├── scripts/                  # Dev runner
├── .github/workflows/        # CI/CD
├── VERSION                   # Bumped automatically by workflow
└── CLAUDE.md
```
