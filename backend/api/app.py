"""
FastAPI application entry point.

Startup: validates environment, opens async Postgres pool, builds LangGraph.
Shutdown: pool closes automatically via context manager.
"""

import os
import sys
import logging
import warnings

# Suppress LangGraph's LangChainPendingDeprecationWarning about allowed_objects.
# Filter by the actual class (not message text) so it matches regardless of
# when the module is first imported in the process.
try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
except ImportError:
    pass
# Belt-and-suspenders: also suppress by message text
warnings.filterwarnings("ignore", message=".*allowed_objects.*")
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.chat import router as chat_router
from graph.builder import build_graph
from persistence.checkpointer import get_async_checkpointer

logger = logging.getLogger(__name__)

# ── Environment validation ────────────────────────────────────────────────────

_ALWAYS_REQUIRED = ["ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY", "GOOGLE_API_KEY"]


def _validate_env() -> None:
    missing = [v for v in _ALWAYS_REQUIRED if not os.getenv(v)]

    # POSTGRES_URI only required when not using SQLite
    if os.getenv("DB_BACKEND", "postgres") != "sqlite" and not os.getenv("POSTGRES_URI"):
        missing.append("POSTGRES_URI")

    if missing:
        logger.critical(
            "Missing required environment variables: %s\n"
            "Copy .env.example to .env and fill in all values before starting.",
            ", ".join(missing),
        )
        sys.exit(1)


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_env()
    async with get_async_checkpointer() as db:
        app.state.graph = build_graph(db.checkpointer)
        app.state.db    = db      # exposed for record_session() calls in routes
        logger.info("Salesforce Architecture Agent started — graph ready.")
        yield
    logger.info("Salesforce Architecture Agent shutting down.")


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Salesforce Architecture Agent", lifespan=lifespan)

_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

app.include_router(chat_router)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health():
    """
    Lightweight probe for load balancers and uptime monitors.
    Returns 200 once the app has started and the graph is ready.
    """
    graph_ready = hasattr(app.state, "graph") and app.state.graph is not None
    if not graph_ready:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ok", "graph": "ready"}
