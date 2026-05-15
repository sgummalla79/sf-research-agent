"""
Usage routes — token counts and cost estimates (per user).

GET /api/usage/summary            → totals + per-agent breakdown for this user
GET /api/usage/session/{id}       → totals + per-agent breakdown for one session
"""

from fastapi import APIRouter, Depends, Request

from utils.auth import AuthUser, get_current_user

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/summary")
async def get_global_usage(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    return await request.app.state.db.get_global_usage(current_user.sub)


@router.get("/session/{session_id}")
async def get_session_usage(
    session_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    return await request.app.state.db.get_session_usage(session_id)
