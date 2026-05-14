"""
FastAPI application entry point.

Startup: validates environment, opens async DB, builds LangGraph skill graphs.
API keys and user config are now fully per-user — no global caches at startup.
"""

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
from pathlib import Path

# config must be the first project import — it calls load_dotenv() so all
# subsequent os.getenv() calls at module level see the .env values.
import config  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.routes.usage import router as usage_router
from api.routes.providers import router as providers_router
from api.routes.flows import router as flows_router
from api.routes.prompts import router as prompts_router
from api.routes.skills import router as skills_router
from config import DATABASE_URL, DB_BACKEND
from framework.engine import SkillEngine
from framework.registry import SkillRegistry
from persistence.checkpointer import get_async_checkpointer

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

    if not os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET") == "change-me":
        missing.append("JWT_SECRET  (generate with: openssl rand -hex 32)")

    for var in ("AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET"):
        if not os.getenv(var):
            missing.append(var)

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
        app.state.graph  = next(iter(graphs.values())) if graphs else None

        logger.info("Pragna started — graph ready.")
        yield

    logger.info("Pragna shutting down.")


app = FastAPI(title="Pragna", lifespan=lifespan)

_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(usage_router)
app.include_router(providers_router)
app.include_router(flows_router)
app.include_router(prompts_router)
app.include_router(skills_router)
