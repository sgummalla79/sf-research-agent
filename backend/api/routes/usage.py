"""
Usage routes — token counts and cost estimates.

GET /api/usage/summary            → totals + per-agent breakdown across all sessions
GET /api/usage/session/{id}       → totals + per-agent breakdown for one session
"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/summary")
async def get_global_usage(request: Request) -> dict:
    return await request.app.state.db.get_global_usage()


@router.get("/session/{session_id}")
async def get_session_usage(session_id: str, request: Request) -> dict:
    return await request.app.state.db.get_session_usage(session_id)
