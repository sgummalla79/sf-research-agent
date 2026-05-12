"""
FastAPI application entry point.

Startup: validates environment, opens async DB, builds LangGraph, loads caches.
Shutdown: pool closes automatically via context manager.
"""

import json
import os
import sys
import logging
import warnings

try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
except ImportError:
    pass
warnings.filterwarnings("ignore", message=".*allowed_objects.*")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.chat import router as chat_router
from api.routes.settings import router as settings_router
from api.routes.usage import router as usage_router
from api.routes.providers import router as providers_router
from graph.builder import build_graph
from persistence.checkpointer import get_async_checkpointer
from utils.api_keys import decrypt, populate_cache
from utils.agent_config import populate_agent_config, DEFAULT_AGENT_CONFIG
from config import DATABASE_URL, DB_BACKEND
from utils.models_cache import populate_models_cache
from utils.provider_registry import PROVIDER_ORDER

logger = logging.getLogger(__name__)


def _validate_env() -> None:
    missing = []
    if not os.getenv("SETTINGS_SECRET"):
        missing.append("SETTINGS_SECRET")
    if DB_BACKEND == "postgres" and not DATABASE_URL:
        # Should not happen — DB_BACKEND is derived from DATABASE_URL — but guard anyway
        missing.append("DATABASE_URL")
    if missing:
        logger.critical(
            "Missing required environment variables: %s\n"
            "Copy .env.example to .env and fill in the required values before starting.",
            ", ".join(missing),
        )
        sys.exit(1)
    logger.info("DB backend: %s", DB_BACKEND.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_env()
    async with get_async_checkpointer() as db:
        app.state.graph = build_graph(db.checkpointer)
        app.state.db    = db

        # ── Load API keys ──────────────────────────────────────────────────
        stored = await db.get_all_api_keys()
        decrypted: dict[str, str] = {}
        for k, enc in stored.items():
            try:
                decrypted[k] = decrypt(enc)
            except Exception:
                logger.warning("Could not decrypt stored API key: %s", k)
        populate_cache(decrypted)

        # ── Load provider model lists ──────────────────────────────────────
        provider_models: dict[str, list[str]] = {}
        for pid in PROVIDER_ORDER:
            raw = await db.get_config(f"models_{pid}")
            if raw:
                try:
                    provider_models[pid] = json.loads(raw)
                except Exception:
                    pass
        populate_models_cache(provider_models)

        # ── Load agent LLM config ──────────────────────────────────────────
        raw_cfg = await db.get_config("agent_config")
        if raw_cfg:
            try:
                populate_agent_config(json.loads(raw_cfg))
            except Exception:
                logger.warning("Could not load agent_config from DB — using defaults")
                populate_agent_config(DEFAULT_AGENT_CONFIG)
        else:
            populate_agent_config(DEFAULT_AGENT_CONFIG)

        logger.info("Salesforce Architecture Agent started — graph ready.")
        yield
    logger.info("Salesforce Architecture Agent shutting down.")


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
app.include_router(settings_router)
app.include_router(usage_router)
app.include_router(providers_router)


@app.get("/health", tags=["ops"])
async def health():
    graph_ready = hasattr(app.state, "graph") and app.state.graph is not None
    if not graph_ready:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ok", "graph": "ready"}
