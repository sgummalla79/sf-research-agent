# Technical Architecture Agent

A multi-agent AI system that produces formal Architecture Recommendation Documents through a structured 5-stage pipeline: intake → discovery → research → review → approval. Platform-agnostic — works with any enterprise or SaaS technology stack.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [First-Time Setup](#first-time-setup)
- [Environment Variables](#environment-variables)
- [Development Setup](#development-setup)
- [Production Setup](#production-setup)
- [Project Structure](#project-structure)
- [Documentation](#documentation)

---

## Overview

The agent conducts a platform-adaptive discovery session, runs parallel research using Perplexity (current platform documentation, limits, and release notes) and Gemini (architectural patterns and design guidance), writes a structured document via Claude, and passes it through a peer review and final approval loop before delivery.

**Supported input types:** typed brief, uploaded document (PDF, DOCX, TXT, MD), or architecture diagram/image.

**Privacy:** All conversations are stored locally only. API keys are encrypted at rest. Nothing is sent to or persisted by model providers beyond the live API call.

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |

---

## First-Time Setup

API keys (Anthropic, Perplexity, Google) are **not** stored in `.env`. They are configured through the in-app **Settings UI** (avatar icon → Settings) and stored encrypted in the database.

1. Start the backend and frontend (see [Development Setup](#development-setup))
2. Open **http://localhost:5173**
3. Click the **avatar icon** (bottom-left) → **Settings**
4. Enter your three API keys — they are validated against each provider before being saved
5. Click **Save Keys** — you are ready to start sessions

You will need:
- **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com)
- **Perplexity API key** — [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
- **Google API key** — [aistudio.google.com](https://aistudio.google.com)

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in all values:

```bash
cp backend/.env.example backend/.env
```

| Variable | Required | Description |
|---|---|---|
| `SETTINGS_SECRET` | **Yes** | Fernet encryption key for API key storage — generate once (see below) |
| `DB_BACKEND` | Yes | `sqlite` (dev) or `postgres` (prod) |
| `SQLITE_PATH` | Dev only | Path to SQLite file, default `data/agent.db` |
| `POSTGRES_URI` | Prod only | Full PostgreSQL connection string |
| `CLAUDE_MODEL` | No | Default: `claude-sonnet-4-6` |
| `PERPLEXITY_MODEL` | No | Default: `sonar-pro` |
| `GEMINI_MODEL` | No | Default: `gemini-2.5-pro` |
| `CLAUDE_HAIKU_MODEL` | No | Default: `claude-haiku-4-5-20251001` |
| `SESSION_TTL_DAYS` | No | Default: `15` |
| `DB_POOL_SIZE` | No | Default: `20` |
| `MAX_DISCOVERY_QUESTIONS` | No | Default: `30` |
| `UPLOAD_DIR` | No | Default: `uploads` |
| `MAX_FILE_SIZE_MB` | No | Default: `10` |
| `MAX_PDF_PAGES` | No | Default: `50` |
| `ALLOWED_ORIGINS` | No | Default: `*` — tighten in production |

### Generating SETTINGS_SECRET

Run this once and paste the output into your `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep this value secret — it is the key used to encrypt your API keys in the database.

---

## Development Setup

Uses **SQLite** — no Docker or database server required.

### Step 1 — Install pnpm (if not already installed)

**Mac / Linux**
```bash
npm install -g pnpm
```

**Windows (PowerShell)**
```powershell
npm install -g pnpm
```

Verify: `pnpm --version`

---

### Step 2 — Set up the Python backend (one-time)

**Mac / Linux**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DB_BACKEND=sqlite and generate SETTINGS_SECRET (see above)
```

**Windows (Command Prompt or PowerShell)**
```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
rem Edit .env: set DB_BACKEND=sqlite and generate SETTINGS_SECRET (see above)
```

---

### Step 3 — Start both servers with one command

Go back to the **project root** and run:

```bash
pnpm install   # first time only
pnpm dev       # works on Mac and Windows
```

Both processes start in parallel with colour-coded output:
- `blue  = backend` (FastAPI on port 8000)
- `green = frontend` (Vite on port 5173)

If either process crashes, the other stops automatically.

---

### Step 4 — Open the app

Open **http://localhost:5173**, then follow [First-Time Setup](#first-time-setup) to configure your API keys.

### Verify backend is healthy

```bash
curl http://localhost:8000/health
# {"status":"ok","graph":"ready"}
```

> **Without pnpm?** Run the two processes manually in separate terminals:
> - Terminal 1: `cd backend && .venv/bin/uvicorn api.app:app --reload --port 8000`
> - Terminal 2: `cd frontend && npm run dev`

---

## Production Setup

### 1. Database

```bash
# Local Docker
docker run --name arch-agent-db \
  -e POSTGRES_USER=agent \
  -e POSTGRES_PASSWORD=agent \
  -e POSTGRES_DB=arch_agent \
  -p 5432:5432 -d postgres:16
```

```bash
# backend/.env
DB_BACKEND=postgres
POSTGRES_URI=postgresql://agent:agent@localhost:5432/arch_agent
ALLOWED_ORIGINS=https://yourdomain.com
SETTINGS_SECRET=<your-fernet-key>
```

### 2. Build frontend

```bash
cd frontend && npm run build
# Output: frontend/dist/
```

### 3. Run backend

```bash
cd backend
pip install gunicorn

gunicorn api.app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

### 4. Nginx (SSE requires buffering off)

```nginx
server {
    root /path/to/technical-architecture-agent/frontend/dist;

    location / { try_files $uri $uri/ /index.html; }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        add_header X-Accel-Buffering no;
    }
}
```

### 5. Infrastructure sizing

| Load | App | DB |
|---|---|---|
| 25/day | 2 vCPU / 2 GB | t3.micro / 2 GB storage |
| 50/day | 2 vCPU / 4 GB | t3.small / 4 GB storage |
| 100/day | 4 vCPU / 8 GB ×2 | t3.medium / 8 GB storage |

---

## Project Structure

```
technical-architecture-agent/
├── backend/                        # Python API + AI agents
│   ├── agents/                     # LangGraph nodes
│   │   ├── base.py                 # BaseAgent — single-LLM-call skeleton
│   │   ├── intake.py               # Stage 1 — document/image intake
│   │   ├── discovery.py            # Stage 2 — dynamic discovery Q&A
│   │   ├── researcher.py           # Stage 3 — parallel search + reasoning + writing
│   │   ├── reviewer.py             # Stage 4 — peer review gate
│   │   ├── approver.py             # Stage 5 — strategic approval gate
│   │   └── chat.py                 # Free-form chat node
│   ├── flows/
│   │   ├── registry.py             # FlowConfig, FLOWS dict, CHAT_MODELS
│   │   └── architect.py            # Default prompts for Technical Architect flow
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py             # SSE streaming endpoints
│   │   │   ├── flows.py            # GET /api/flows — available flows + chat models
│   │   │   ├── prompts.py          # Agent prompt versioning CRUD
│   │   │   ├── providers.py        # Provider management
│   │   │   ├── settings.py         # API key management
│   │   │   └── usage.py            # Token usage endpoints
│   │   └── app.py                  # FastAPI app, lifespan, seeding, CORS
│   ├── graph/                      # LangGraph StateGraph builder + conditional edges
│   ├── persistence/                # SQLite / PostgreSQL checkpointer + all DB tables
│   ├── utils/
│   │   ├── api_keys.py             # Fernet encryption, in-memory key cache
│   │   ├── key_validator.py        # Live API key validation per provider
│   │   ├── pricing.py              # Model pricing constants + cost calculation
│   │   ├── file_parser.py          # PDF/DOCX/TXT/MD text extraction
│   │   ├── file_storage.py         # Upload save/delete
│   │   └── llm_retry.py            # Tenacity retry wrapper for all LLM calls
│   ├── state.py                    # AgentState schema
│   ├── config.py                   # Environment variable loading
│   ├── requirements.txt
│   └── .env.example
├── frontend/                       # Vue 3 chat UI
│   └── src/
│       ├── components/
│       │   ├── ChatWindow.vue      # Main shell (sidebar, chat pane, doc panel)
│       │   ├── ChatInput.vue       # Input box component (model picker, + menu, flows)
│       │   ├── ConfigurationPage.vue  # Agent prompts + agent models config
│       │   ├── SettingsPage.vue    # Providers + usage settings
│       │   └── settings/
│       │       ├── AgentPromptsSettings.vue   # Versioned prompt editor
│       │       ├── AgentConfigSettings.vue    # Per-agent model assignment
│       │       ├── ProvidersSettings.vue      # API key management
│       │       └── UsageSettings.vue
│       └── composables/
│           └── useAgentChat.js     # SSE stream handler, session state
├── scripts/
│   └── dev.js                      # Cross-platform dev runner (port cleanup + health poll)
├── docs/                           # Design and requirements documents
└── README.md
```

---

## Documentation

| Document | Description |
|---|---|
| [UI Design](docs/UI_DESIGN.md) | Layout, shell structure, input component, agent flow UX |
| [Functional Requirements](docs/FUNCTIONAL_REQUIREMENTS.md) | Feature spec, user flows, agent pipeline, prompt versioning |
| [Technical Requirements](docs/TECHNICAL_REQUIREMENTS.md) | Architecture, API endpoints, DB schema, security |
