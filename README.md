# SF Research Agent

A multi-agent AI system that produces formal Salesforce Architecture Recommendation Documents through a structured 5-stage pipeline: intake → discovery → research → review → approval.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Development Setup](#development-setup)
- [Production Setup](#production-setup)
- [Project Structure](#project-structure)
- [Documentation](#documentation)

---

## Overview

The agent conducts a dynamic discovery session, runs parallel research using Perplexity (current Salesforce documentation) and Gemini (architectural patterns), writes a structured document via Claude, and passes it through a peer review and final approval loop before delivery.

**Supported input types:** typed brief, uploaded document (PDF, DOCX, TXT, MD), or architecture diagram/image.

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in all values:

```bash
cp backend/.env.example backend/.env
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key — [console.anthropic.com](https://console.anthropic.com) |
| `PERPLEXITY_API_KEY` | Yes | Perplexity API key — [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) |
| `GOOGLE_API_KEY` | Yes | Gemini API key — [aistudio.google.com](https://aistudio.google.com) |
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

---

## Development Setup

Uses **SQLite** — no Docker or database server required.

### 1. Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt

cp .env.example .env
# Set DB_BACKEND=sqlite and fill in the three API keys

uvicorn api.app:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok","graph":"ready"}
```

### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Production Setup

### 1. Database

```bash
# Local Docker
docker run --name sf-agent-db \
  -e POSTGRES_USER=agent \
  -e POSTGRES_PASSWORD=agent \
  -e POSTGRES_DB=research_agent \
  -p 5432:5432 -d postgres:16
```

```bash
# backend/.env
DB_BACKEND=postgres
POSTGRES_URI=postgresql://agent:agent@localhost:5432/research_agent
ALLOWED_ORIGINS=https://yourdomain.com
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
    root /path/to/sf-research-agent/frontend/dist;

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
sf-research-agent/
├── backend/                    # Python API + AI agents
│   ├── agents/                 # LangGraph nodes (intake, discovery, researcher, reviewer, approver)
│   ├── api/                    # FastAPI app + SSE streaming routes
│   ├── graph/                  # LangGraph StateGraph builder + conditional edges
│   ├── persistence/            # SQLite / PostgreSQL checkpointer factory
│   ├── utils/                  # File parser, storage, LLM retry wrapper
│   ├── state.py                # AgentState schema
│   ├── config.py               # Environment variable loading
│   ├── main.py                 # CLI entry point (dev helper)
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variable template
├── frontend/                   # Vue 3 chat UI
│   └── src/
│       ├── components/         # ChatWindow.vue
│       └── composables/        # useAgentChat.js
├── docs/                       # Design and requirements documents
└── README.md
```

---

## Documentation

| Document | Description |
|---|---|
| [UI Design](docs/UI_DESIGN.md) | Component layout, sidebar, dark mode, color system |
| [Functional Requirements](docs/FUNCTIONAL_REQUIREMENTS.md) | Feature spec, user flows, agent pipeline |
| [Technical Requirements](docs/TECHNICAL_REQUIREMENTS.md) | Architecture, API, DB schema, infrastructure |
