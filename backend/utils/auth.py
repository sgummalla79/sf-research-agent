"""
Service JWT validation — FastAPI dependency for authenticated routes.

Tokens are HS256 JWTs signed by the Express server with the shared JWT_SECRET.
Express mints a short-lived (30s) token per request containing the user's Auth0
sub claim as the `sub` field.

Dev mode: if JWT_SECRET is not set, all requests resolve to "dev-user" so the
backend works standalone (pnpm dev:mac) without Express in front of it.

Usage:
    @router.get("/sessions")
    async def list(user_id: str = Depends(get_user_id)):
        ...
"""

import logging
import os

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger  = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)

DEV_USER_ID = "dev-user"


async def get_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """
    Validate the HS256 service JWT issued by the Express proxy and return
    the user ID (Auth0 sub claim).

    Falls back to 'dev-user' when JWT_SECRET is not configured — allows
    running the backend standalone locally without Express.
    """
    jwt_secret = os.environ.get("JWT_SECRET", "")

    # ── Dev mode ─────────────────────────────────────────────────────────────
    if not jwt_secret:
        return DEV_USER_ID

    # ── Require token ─────────────────────────────────────────────────────────
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Validate ──────────────────────────────────────────────────────────────
    token = credentials.credentials
    try:
        payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token missing sub claim")
        return user_id
    except Exception as exc:
        logger.warning("Service JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired service token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
