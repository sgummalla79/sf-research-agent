"""
Usage routes — token counts and cost estimates.

GET /api/usage/summary            → totals + per-model breakdown for the current user
GET /api/usage/session/{id}       → totals + per-model breakdown for one session
"""

from fastapi import APIRouter, Depends, Request

from utils.auth import get_user_id

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/summary")
async def get_global_usage(request: Request, user_id: str = Depends(get_user_id)) -> dict:
    return await request.app.state.db.get_global_usage(user_id)


@router.get("/session/{session_id}")
async def get_session_usage(session_id: str, request: Request) -> dict:
    return await request.app.state.db.get_session_usage(session_id)
