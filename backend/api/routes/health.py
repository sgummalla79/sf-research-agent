import os
from pathlib import Path
from fastapi import APIRouter, Request

router = APIRouter()


def _read_version() -> str:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "VERSION"
        if candidate.exists():
            return candidate.read_text().strip()
    return os.getenv("APP_VERSION", "")


@router.get("/api/about")
async def about():
    return {"version": _read_version()}


@router.get("/health")
async def health(request: Request):
    db     = request.app.state.db
    graphs = request.app.state.graphs or {}
    try:
        await db.pool.check()
        db_status = "ready"
    except Exception:
        db_status = "unavailable"

    return {
        "status": "ok" if db_status == "ready" else "degraded",
        "db":     db_status,
        "skills": list(graphs.keys()),
    }
