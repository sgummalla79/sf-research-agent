# Pragna

A multi-agent AI platform that produces formal Architecture Recommendation Documents through a structured 5-stage pipeline: intake → discovery → research → review → approval. Supports free-form chat as well.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Clone the Repository](#clone-the-repository)
- [Environment Variables](#environment-variables)
- [Development Setup](#development-setup)
  - [Option A — SQLite (simplest, no database server)](#option-a--sqlite-simplest-no-database-server)
  - [Option B — Local Docker PostgreSQL](#option-b--local-docker-postgresql)
  - [Option C — Cloud PostgreSQL (Neon / Supabase)](#option-c--cloud-postgresql-neon--supabase)
- [First-Time App Setup (all modes)](#first-time-app-setup-all-modes)
- [Running Tests](#running-tests)
  - [Backend Tests](#backend-tests)
  - [Frontend Tests](#frontend-tests)
- [Production Deployment](#production-deployment)
  - [Option 1 — Docker Compose on a VPS (local Docker PostgreSQL)](#option-1--docker-compose-on-a-vps-local-docker-postgresql)
  - [Option 2 — Docker Compose on a VPS (Cloud PostgreSQL)](#option-2--docker-compose-on-a-vps-cloud-postgresql)
  - [Option 3 — CI/CD via GitHub Actions to Kubernetes](#option-3--cicd-via-github-actions-to-kubernetes)
- [Project Structure](#project-structure)

---

## Overview

The agent conducts a platform-adaptive discovery session, runs parallel research using Perplexity (current platform documentation, limits, and release notes) and Gemini (architectural patterns and design guidance), writes a structured document via Claude, and passes it through a peer review and final approval loop before delivery.

**Supported input types:** typed brief, uploaded document (PDF, DOCX, TXT, MD), or architecture diagram/image.

**Privacy:** All conversations are stored locally only. API keys are encrypted at rest. Nothing is sent to or persisted by model providers beyond the live API call.

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| pnpm | 8+ | `npm install -g pnpm` |
| Docker | 24+ | [docker.com](https://www.docker.com/get-started/) — only needed for local Docker DB or full containerised prod |

---

## Clone the Repository

```bash
git clone https://github.com/sgummalla79/sf-research-agent.git
cd sf-research-agent
```

---

## Environment Variables

Copy the example env file and edit it:

```bash
cp backend/.env.example backend/.env
```

**Generate `SETTINGS_SECRET` (run once — paste output into `.env`):**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Generate `JWT_SECRET` (run once — paste output into `.env`):**

```bash
openssl rand -hex 32
```

### Full variable reference

| Variable | Required | Description |
|---|---|---|
| `SETTINGS_SECRET` | **Yes** | Fernet encryption key for API keys stored in the database — generate once and keep secret |
| `JWT_SECRET` | **Yes** | HS256 secret for signing httpOnly session cookies |
| `AUTH0_DOMAIN` | **Yes** | Your Auth0 tenant, e.g. `your-tenant.us.auth0.com` |
| `AUTH0_CLIENT_ID` | **Yes** | Auth0 SPA client ID |
| `AUTH0_CLIENT_SECRET` | **Yes** | Auth0 SPA client secret |
| `AUTH0_CALLBACK_URL` | **Yes** | Redirect URL after Auth0 login (`http://localhost:5173/callback` in dev) |
| `DATABASE_URL` | **Yes** | Full PostgreSQL connection string — omit only if using SQLite mode |
| `DB_PASSWORD` | Compose only | Plain password used in `docker-compose.yml` for the local `db` service |
| `ALLOWED_ORIGINS` | No | Comma-separated allowed CORS origins — default `*`, tighten in prod |
| `FRONTEND_URL` | No | Used in dev redirect flows — default `http://localhost:5173` |
| `CLAUDE_HAIKU_MODEL` | No | Default: `claude-haiku-4-5-20251001` |
| `DB_POOL_SIZE` | No | Default: `10` |
| `MAX_DISCOVERY_QUESTIONS` | No | Default: `30` |
| `MAX_REVISIONS` | No | Default: `5` |
| `UPLOAD_DIR` | No | Default: `uploads` |
| `MAX_FILE_SIZE_MB` | No | Default: `10` |
| `MAX_PDF_PAGES` | No | Default: `50` |
| `LOG_LEVEL` | No | Default: `INFO` |

---

## Development Setup

### Option A — SQLite (simplest, no database server)

> Best for: first run, local exploration, no PostgreSQL available.

**1. Set up Python environment**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure `.env`**

Edit `backend/.env`. The minimum required for SQLite mode:

```env
SETTINGS_SECRET=<your-fernet-key>
JWT_SECRET=<your-jwt-secret>
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your_spa_client_id
AUTH0_CLIENT_SECRET=your_spa_client_secret
AUTH0_CALLBACK_URL=http://localhost:5173/callback
FRONTEND_URL=http://localhost:5173

# SQLite — no DATABASE_URL needed; set the path explicitly if you want
# SQLITE_PATH=data/agent.db
```

> When `DATABASE_URL` is absent, the backend falls back to SQLite automatically.

**3. Install root dependencies and start both servers**

```bash
cd ..                  # back to project root
pnpm install           # first time only
pnpm dev
```

Both servers start with colour-coded output:
- **blue** = FastAPI backend on port 8000
- **green** = Vite frontend on port 5173

---

### Option B — Local Docker PostgreSQL

> Best for: matching production database behaviour on a local machine.

**1. Create `backend/.env`** with the following database block (in addition to the secrets and Auth0 vars above):

```env
SETTINGS_SECRET=<your-fernet-key>
JWT_SECRET=<your-jwt-secret>
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your_spa_client_id
AUTH0_CLIENT_SECRET=your_spa_client_secret
AUTH0_CALLBACK_URL=http://localhost:5173/callback
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173

DATABASE_URL=postgresql://pragna:your_db_password@localhost:5432/pragna
DB_PASSWORD=your_db_password
```

**2. Start a local PostgreSQL container**

```bash
docker compose up db -d
```

This brings up the `db` service from `docker-compose.yml` — a `postgres:16-alpine` container on port 5432 with the `pragna` database pre-created.

Verify it is healthy:

```bash
docker compose ps
# db    "docker-entrypoint.s…"   Up (healthy)
```

**3. Set up Python environment and start**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
pnpm install           # first time only
pnpm dev
```

**4. Stop the database when done**

```bash
docker compose down    # keeps the postgres_data volume
docker compose down -v # also removes the volume (wipes data)
```

---

### Option C — Cloud PostgreSQL (Neon / Supabase)

> Best for: sharing a database between teammates, or mimicking the exact production connection.

**1. Create your database**

- **Neon:** Create a project at [neon.tech](https://neon.tech) → copy the connection string from the dashboard.
- **Supabase:** Create a project at [supabase.com](https://supabase.com) → Settings → Database → Connection string (use the `URI` tab).

**2. Configure `backend/.env`**

```env
SETTINGS_SECRET=<your-fernet-key>
JWT_SECRET=<your-jwt-secret>
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your_spa_client_id
AUTH0_CLIENT_SECRET=your_spa_client_secret
AUTH0_CALLBACK_URL=http://localhost:5173/callback
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173

# Neon
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/pragna?sslmode=require

# Supabase
# DATABASE_URL=postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres
```

> **Neon note:** Neon routes connections through PgBouncer. The backend already sets `autocommit=True, prepare_threshold=None` for compatibility — no extra configuration needed.

**3. Set up Python environment and start**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
pnpm install
pnpm dev
```

---

## First-Time App Setup (all modes)

Once both servers are running:

1. Open **http://localhost:5173**
2. Sign in (Auth0)
3. Click the **avatar icon** (bottom-left) → **Settings**
4. Enter your LLM API keys — each key is validated against the provider before saving:
   - **Anthropic** — [console.anthropic.com](https://console.anthropic.com)
   - **Perplexity** — [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
   - **Google AI Studio** — [aistudio.google.com](https://aistudio.google.com)
5. Click **Save Keys**

Verify the backend is healthy:

```bash
curl http://localhost:8000/health
# {"status":"ok","graph":"ready"}
```

---

## Running Tests

### Backend Tests

The backend test suite uses **pytest** and **pytest-asyncio**. Tests are split into three directories:

| Directory | Contents |
|---|---|
| `backend/tests/unit/` | Pure unit tests — no database required |
| `backend/tests/integration/` | Repository-level tests — require a real PostgreSQL database |
| `backend/tests/e2e/` | Full API tests — FastAPI app running against `pragna_test` DB |

#### Prerequisites

Integration and e2e tests require a `pragna_test` database. If you are using local Docker:

```bash
# Start the db container if not already running
docker compose up db -d

# Create the test database
docker exec -it sf-research-agent-db-1 \
  psql -U pragna -c "CREATE DATABASE pragna_test;"
```

If you are using Neon or Supabase, create a `pragna_test` branch or schema in your cloud console.

#### Running tests

```bash
cd backend
source .venv/bin/activate
```

**All tests:**

```bash
pytest
```

**Unit tests only (no database needed):**

```bash
pytest tests/unit/
```

**Integration tests:**

```bash
pytest tests/integration/
```

**E2E tests:**

```bash
pytest tests/e2e/
```

**With coverage report:**

```bash
pytest --cov=. --cov-report=term-missing
```

**Against a different test database:**

```bash
TEST_DATABASE_URL=postgresql://user:pass@host:5432/pragna_test pytest
```

> By default, tests use `postgresql://pragna:pragna_dev@localhost:5432/pragna_test`. Override with the `TEST_DATABASE_URL` environment variable.

**Useful flags:**

```bash
pytest -x                     # stop on first failure
pytest -v                     # verbose output
pytest tests/e2e/test_conversation.py   # single file
pytest -k "test_health"       # run tests matching a name pattern
```

---

### Frontend Tests

The frontend uses **Vitest** with `@vue/test-utils` and `happy-dom`.

```bash
cd frontend
npm install       # first time only
```

**Run all frontend tests once:**

```bash
npm run test
# or from project root:
# cd frontend && npm run test
```

**Watch mode (re-runs on file changes):**

```bash
npm run test:watch
```

Test files live in:
- `frontend/src/tests/unit/` — unit tests for composables and utilities
- `frontend/src/tests/component/` — component-level tests

---

## Production Deployment

---

### Option 1 — Docker Compose on a VPS (local Docker PostgreSQL)

This deploys the full stack (API + UI + PostgreSQL + Caddy reverse proxy) entirely on one server using Docker Compose.

#### Step 1 — Provision a server

Recommended minimum: 2 vCPU / 2 GB RAM (e.g. DigitalOcean Droplet, Hetzner CX22, AWS t3.small). Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
```

#### Step 2 — Clone the repository on the server

```bash
git clone https://github.com/sgummalla79/sf-research-agent.git /opt/pragna
cd /opt/pragna
```

#### Step 3 — Configure the environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with **production values**:

```env
# ── Secrets ────────────────────────────────────────────────────────────────
SETTINGS_SECRET=<your-fernet-key>
JWT_SECRET=<your-jwt-secret>

# ── Auth0 ─────────────────────────────────────────────────────────────────
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your_spa_client_id
AUTH0_CLIENT_SECRET=your_spa_client_secret
AUTH0_CALLBACK_URL=https://yourdomain.com/callback

# ── Database (local Docker postgres) ─────────────────────────────────────
DATABASE_URL=postgresql://pragna:your_db_password@db:5432/pragna
DB_PASSWORD=your_db_password

# ── CORS ──────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

> The hostname in `DATABASE_URL` is `db` — the Docker Compose service name, resolved on the `internal` network.

#### Step 4 — Configure Caddy

Edit `docker/Caddyfile.prod` and replace `your-domain.com` with your actual domain:

```
yourdomain.com {
    handle /api/* {
        reverse_proxy api:8000 {
            flush_interval -1
            transport http {
                read_timeout 300s
            }
        }
    }

    handle /auth/* {
        reverse_proxy api:8000
    }

    handle {
        reverse_proxy ui:80
    }
}
```

Caddy will automatically provision a TLS certificate via Let's Encrypt. Your server's port 80 and 443 must be publicly reachable.

#### Step 5 — Point your domain

Create an A record at your DNS provider pointing `yourdomain.com` → your server's public IP.

#### Step 6 — Pull images and start

```bash
cd /opt/pragna
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

This starts four containers: `db`, `api`, `ui`, `caddy`.

#### Step 7 — Verify

```bash
# Check all containers are running
docker compose -f docker-compose.prod.yml ps

# Check API health
curl https://yourdomain.com/health
# {"status":"ok","graph":"ready"}

# Tail logs
docker compose -f docker-compose.prod.yml logs -f api
```

#### Updating to a new version

```bash
cd /opt/pragna
git pull
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --no-deps api ui
```

#### Maintenance commands

```bash
# Stop everything (keeps DB data volume)
docker compose -f docker-compose.prod.yml down

# Stop and wipe database (destructive — loses all data)
docker compose -f docker-compose.prod.yml down -v

# Restart only the API
docker compose -f docker-compose.prod.yml restart api

# View DB size and tables
docker exec -it $(docker compose -f docker-compose.prod.yml ps -q db) \
  psql -U pragna -c "\dt"
```

---

### Option 2 — Docker Compose on a VPS (Cloud PostgreSQL)

Same as Option 1 but the `db` container is removed — the API connects to Neon, Supabase, or any managed PostgreSQL.

#### Step 1 — Follow steps 1–2 from Option 1

Clone the repo on your server and install Docker.

#### Step 2 — Configure `backend/.env`

```env
# ── Secrets ────────────────────────────────────────────────────────────────
SETTINGS_SECRET=<your-fernet-key>
JWT_SECRET=<your-jwt-secret>

# ── Auth0 ─────────────────────────────────────────────────────────────────
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your_spa_client_id
AUTH0_CLIENT_SECRET=your_spa_client_secret
AUTH0_CALLBACK_URL=https://yourdomain.com/callback

# ── Cloud PostgreSQL (Neon example) ─────────────────────────────────────
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/pragna?sslmode=require

# ── CORS ──────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
```

#### Step 3 — Create a trimmed compose file

Create `/opt/pragna/docker-compose.cloud-db.yml` with the `db` service removed:

```yaml
services:
  api:
    image: ghcr.io/sgummalla79/pragna-api:latest
    restart: unless-stopped
    env_file: backend/.env
    networks:
      - web

  ui:
    image: ghcr.io/sgummalla79/pragna-ui:latest
    restart: unless-stopped
    networks:
      - web

  caddy:
    image: caddy:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/Caddyfile.prod:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api
      - ui
    networks:
      - web

volumes:
  caddy_data:
  caddy_config:

networks:
  web:
    driver: bridge
```

#### Step 4 — Configure Caddy, point DNS, and start

Same as steps 4–6 in Option 1, but use the new compose file:

```bash
docker compose -f docker-compose.cloud-db.yml pull
docker compose -f docker-compose.cloud-db.yml up -d
```

#### Step 5 — Verify

```bash
curl https://yourdomain.com/health
# {"status":"ok","graph":"ready"}
```

---

### Option 3 — CI/CD via GitHub Actions to Kubernetes

The repository ships with a `workflow_dispatch` workflow at `.github/workflows/build-and-push.yml`. It bumps the version, builds and pushes Docker images to GHCR, then rolls them out to a K3s cluster via SSH.

#### One-time cluster setup

**1. Install K3s on your server:**

```bash
curl -sfL https://get.k3s.io | sh -
```

**2. Apply the Kubernetes namespace and manifests:**

```bash
kubectl apply -f k8s/pragna/namespace.yaml

# Create secrets (fill in all values first)
cp k8s/pragna/secret.template.yaml k8s/pragna/secret.yaml
# Edit k8s/pragna/secret.yaml — base64-encode all values:
#   echo -n "your-value" | base64
kubectl apply -f k8s/pragna/secret.yaml

kubectl apply -f k8s/pragna/
```

**3. Configure required GitHub secrets** (Settings → Secrets → Actions):

| Secret | Value |
|---|---|
| `VPS_HOST` | Public IP or hostname of your server |
| `VPS_SSH_KEY` | Private SSH key with root access to the server |
| `VPS_REPO_PATH` | Absolute path to the cloned repo on the server, e.g. `/opt/pragna` |
| `GHCR_PAT` | GitHub Personal Access Token with `write:packages` scope |

#### Triggering a deployment

1. Go to **Actions** → **Build and Push** → **Run workflow**
2. Select version bump type: `patch`, `minor`, or `major`
3. Click **Run workflow**

The workflow:
1. Bumps `VERSION` and commits it
2. Generates release notes in `release-notes/`
3. Builds `pragna-api` and `pragna-ui` Docker images (no cache) and pushes to GHCR
4. SSHs into the server, runs `kubectl set image` for both deployments
5. Waits for rollout and runs a health check against `https://yourdomain.com/health`

#### Manual rollout (without GitHub Actions)

```bash
# On the server
VERSION=1.2.3   # target version

kubectl set image deployment/pragna-api \
  pragna-api=ghcr.io/sgummalla79/pragna-api:${VERSION} \
  -n pragna

kubectl set image deployment/pragna-ui \
  pragna-ui=ghcr.io/sgummalla79/pragna-ui:${VERSION} \
  -n pragna

kubectl rollout status deployment/pragna-api -n pragna --timeout=120s
kubectl rollout status deployment/pragna-ui  -n pragna --timeout=120s
kubectl get pods -n pragna
```

#### Rollback

```bash
kubectl rollout undo deployment/pragna-api -n pragna
kubectl rollout undo deployment/pragna-ui  -n pragna
```

#### Infrastructure sizing

| Daily sessions | App server | Database |
|---|---|---|
| ~25/day | 2 vCPU / 2 GB | Neon free tier / t3.micro |
| ~50/day | 2 vCPU / 4 GB | Neon launch / t3.small |
| ~100/day | 4 vCPU / 8 GB × 2 | Neon scale / t3.medium |

---

## Project Structure

```
pragna/
├── backend/                        # Python FastAPI + LangGraph agents
│   ├── api/
│   │   ├── app.py                  # FastAPI lifespan, middleware, seeding
│   │   └── routes/
│   │       ├── chat.py             # SSE streaming endpoints
│   │       ├── providers.py        # Provider management
│   │       ├── settings.py         # API key management
│   │       ├── prompts.py          # Agent prompt versioning CRUD
│   │       └── usage.py            # Token usage endpoints
│   ├── framework/
│   │   ├── schema.py               # SkillManifest, StageConfig
│   │   ├── registry.py             # Skill loader + cache
│   │   ├── engine.py               # Compiles SKILL.md → LangGraph StateGraph
│   │   ├── defaults.py             # Smart LLM slot selection
│   │   └── strategies/             # Stage execution patterns (intake, interrupt, structured, fanout)
│   ├── skills/
│   │   └── architect/              # 5-stage architecture pipeline
│   │       ├── SKILL.md            # Pipeline manifest
│   │       └── agents/*.md         # System prompts (versioned in DB)
│   ├── persistence/
│   │   └── checkpointer.py         # SQLite + PostgreSQL backends, all DB tables
│   ├── repositories/               # Data access layer per entity
│   ├── utils/
│   │   ├── llm_factory.py          # LLM client construction
│   │   ├── user_context.py         # Per-request key storage + session store
│   │   ├── api_keys.py             # Fernet encryption
│   │   ├── key_validator.py        # Live API key validation
│   │   ├── pricing.py              # Token cost calculation
│   │   └── file_parser.py          # PDF/DOCX/TXT/MD extraction
│   ├── state.py                    # AgentState (Pydantic + LangGraph reducers)
│   ├── config.py                   # Environment variable loading
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
│       ├── unit/                   # No database required
│       ├── integration/            # Requires pragna_test PostgreSQL database
│       └── e2e/                    # Full API tests against pragna_test database
├── frontend/                       # Vue 3 SPA
│   └── src/
│       ├── components/             # UI components (chat, settings, document, sidebar)
│       ├── composables/
│       │   ├── useAgentChat.js     # SSE stream handler, session state
│       │   └── useDocumentPanel.js
│       ├── pages/                  # ChatPage, etc.
│       ├── stores/                 # Pinia stores
│       └── tests/
│           ├── unit/               # Composable unit tests
│           └── component/          # Vue component tests
├── docker/
│   ├── Dockerfile.api              # Python backend image
│   ├── Dockerfile.ui               # Node build → Caddy serve
│   ├── Caddyfile.prod              # Production reverse proxy config
│   └── Caddyfile.ui                # Static SPA serve config
├── k8s/pragna/                     # Kubernetes manifests
├── scripts/                        # Dev runner, preflight checks
├── docker-compose.yml              # Dev: api + db (local Docker postgres)
├── docker-compose.prod.yml         # Prod: api + ui + db + caddy
├── CLAUDE.md                       # Claude Code guidance
└── README.md
```
