from fastapi import APIRouter, Request

router = APIRouter()


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
