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

from pathlib import Path

from api.routes.chat import router as chat_router
from api.routes.settings import router as settings_router
from api.routes.usage import router as usage_router
from api.routes.providers import router as providers_router
from api.routes.flows import router as flows_router
from api.routes.prompts import router as prompts_router
from framework.engine import SkillEngine
from framework.registry import SkillRegistry
from persistence.checkpointer import get_async_checkpointer
from utils.api_keys import decrypt, populate_cache, populate_config_cache
from utils.agent_config import populate_agent_config, DEFAULT_AGENT_CONFIG
from config import DATABASE_URL, DB_BACKEND
from utils.models_cache import populate_models_cache
from utils.provider_registry import PROVIDER_ORDER

_SKILLS_DIR = Path(__file__).parent.parent / "skills"

logger = logging.getLogger(__name__)


def _validate_env() -> None:
    missing = []
    secret = os.getenv("SETTINGS_SECRET", "")
    if not secret:
        missing.append("SETTINGS_SECRET")
    else:
        try:
            from cryptography.fernet import Fernet
            Fernet(secret.encode() if isinstance(secret, str) else secret)
        except Exception:
            logger.critical(
                "SETTINGS_SECRET is set but is not a valid Fernet key.\n"
                "Generate a valid key with:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
            sys.exit(1)
    if DB_BACKEND == "postgres" and not DATABASE_URL:
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
        app.state.db = db

        # ── Build skill registry + one compiled graph per skill ────────────
        skill_registry = SkillRegistry(_SKILLS_DIR)
        skill_registry.load_all()
        app.state.skill_registry = skill_registry

        engine = SkillEngine()
        graphs: dict = {}
        for skill in skill_registry.list_all():
            graphs[skill.manifest.id] = engine.build(skill, db.checkpointer)
            logger.info("Graph compiled for skill '%s'", skill.manifest.id)

        app.state.graphs = graphs
        # Fallback graph for chat sessions (any skill graph works — all include the chat node)
        app.state.graph  = next(iter(graphs.values())) if graphs else None

        # ── Load API keys ──────────────────────────────────────────────────
        stored = await db.get_all_api_keys()
        decrypted: dict[str, str] = {}
        for k, enc in stored.items():
            try:
                decrypted[k] = decrypt(enc)
            except Exception:
                logger.warning("Could not decrypt stored API key: %s", k)
        populate_cache(decrypted)

        # ── Load Anthropic auth mode ───────────────────────────────────────
        anthropic_mode = await db.get_config("anthropic_mode") or "direct"
        populate_config_cache({"anthropic_mode": anthropic_mode})

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

        # ── Seed skill prompt versions (v1 from agents/*.md, once per key) ──
        for skill in skill_registry.list_all():
            flow_id    = skill.manifest.id
            agent_keys = list(skill.all_agent_prompts.keys())
            if not await db.is_skill_seeded(flow_id, agent_keys):
                logger.info(
                    "Seeding prompts for skill '%s' (%d agents)",
                    flow_id, len(agent_keys),
                )
                await db.seed_flow_prompts(flow_id, skill.all_agent_prompts)

        logger.info("Technical Architecture Agent started — graph ready.")
        yield
    logger.info("Technical Architecture Agent shutting down.")


app = FastAPI(title="Technical Architecture Agent", lifespan=lifespan)

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
app.include_router(flows_router)
app.include_router(prompts_router)


@app.get("/health", tags=["ops"])
async def health():
    graphs_ready = hasattr(app.state, "graphs") and bool(app.state.graphs)
    if not graphs_ready:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ok", "graph": "ready", "skills": list(app.state.graphs.keys())}
