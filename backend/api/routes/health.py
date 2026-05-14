"""
GET /health — comprehensive readiness check.

Checks every runtime dependency the API needs to serve traffic:
  - All required environment variables are present
  - SETTINGS_SECRET is a valid Fernet key
  - JWT_SECRET is set and not a placeholder
  - Auth0 variables are configured
  - Database is reachable (SELECT 1)
  - All required tables exist (our schema + LangGraph checkpoint tables)
  - At least one skill graph is compiled and ready

Returns 200 when all checks pass, 503 when any critical check fails.
Used by both the K8s readinessProbe and livenessProbe.
"""

import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["ops"])

_REQUIRED_ENV = [
    "SETTINGS_SECRET",
    "JWT_SECRET",
    "AUTH0_DOMAIN",
    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_CALLBACK_URL",
    "FRONTEND_URL",
]

_REQUIRED_TABLES = [
    # Application tables
    "users",
    "agent_sessions",
    "app_settings",
    "token_usage",
    "app_config",
    "agent_prompt_versions",
    "flow_prompt_snapshots",
    "installed_skills",
    # LangGraph checkpoint tables
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
]


def _check_env() -> dict:
    present = []
    missing = []
    for var in _REQUIRED_ENV:
        if os.environ.get(var, "").strip():
            present.append(var)
        else:
            missing.append(var)
    return {"ok": len(missing) == 0, "present": present, "missing": missing}


def _check_settings_secret() -> dict:
    secret = os.environ.get("SETTINGS_SECRET", "").strip()
    if not secret:
        return {"ok": False, "error": "SETTINGS_SECRET is not set"}
    try:
        from cryptography.fernet import Fernet
        Fernet(secret.encode())
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": f"Invalid Fernet key: {exc}"}


def _check_jwt_secret() -> dict:
    val = os.environ.get("JWT_SECRET", "").strip()
    if not val:
        return {"ok": False, "error": "JWT_SECRET is not set"}
    if val in ("change-me", "secret", "your-secret"):
        return {"ok": False, "error": "JWT_SECRET is a placeholder — set a real secret"}
    if len(val) < 32:
        return {"ok": False, "error": f"JWT_SECRET is too short ({len(val)} chars, need ≥ 32)"}
    return {"ok": True}


def _check_auth0() -> dict:
    vars_set = {v: bool(os.environ.get(v, "").strip()) for v in [
        "AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET", "AUTH0_CALLBACK_URL"
    ]}
    missing = [k for k, v in vars_set.items() if not v]
    return {"ok": len(missing) == 0, "missing": missing}


async def _check_database(db) -> dict:
    try:
        # Simple connectivity probe
        if db._backend == "sqlite":
            await db._fetchone("SELECT 1")
        else:
            await db._fetchone("SELECT 1")
        return {"ok": True, "backend": db._backend, "reachable": True}
    except Exception as exc:
        return {"ok": False, "backend": db._backend, "reachable": False, "error": str(exc)}


async def _check_tables(db) -> dict:
    try:
        missing = []
        for table in _REQUIRED_TABLES:
            if db._backend == "sqlite":
                row = await db._fetchone(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
            else:
                row = await db._fetchone(
                    "SELECT tablename FROM pg_catalog.pg_tables "
                    "WHERE schemaname='public' AND tablename=%s",
                    (table,),
                )
            if not row:
                missing.append(table)
        return {
            "ok": len(missing) == 0,
            "total": len(_REQUIRED_TABLES),
            "missing": missing,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "missing": _REQUIRED_TABLES}


def _check_skills(request: Request) -> dict:
    graphs = getattr(request.app.state, "graphs", None)
    if not graphs:
        return {"ok": False, "error": "No skill graphs compiled — app may still be starting"}
    return {"ok": True, "loaded": list(graphs.keys())}


@router.get("/health")
async def health(request: Request):
    db = getattr(request.app.state, "db", None)

    checks: dict = {}

    # ── Static checks (no I/O) ────────────────────────────────────────────────
    checks["env_vars"]        = _check_env()
    checks["settings_secret"] = _check_settings_secret()
    checks["jwt_secret"]      = _check_jwt_secret()
    checks["auth0"]           = _check_auth0()
    checks["skills"]          = _check_skills(request)

    # ── DB checks (async I/O) ─────────────────────────────────────────────────
    if db is None:
        checks["database"] = {"ok": False, "error": "DB not initialised — app still starting"}
        checks["tables"]   = {"ok": False, "error": "DB not initialised"}
    else:
        checks["database"] = await _check_database(db)
        checks["tables"]   = await _check_tables(db)

    # ── Overall status ────────────────────────────────────────────────────────
    all_ok = all(v.get("ok", False) for v in checks.values())

    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status":  "ok" if all_ok else "degraded",
            "checks":  checks,
        },
    )
