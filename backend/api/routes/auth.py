"""
Auth0 OAuth routes.

GET  /auth/me          — bootstrap: return current user or 401
GET  /auth/initiate    — redirect to Auth0 login
GET  /auth/callback    — exchange code, set session cookie, redirect to frontend
POST /auth/logout      — clear session cookie
"""

import os
import logging
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse

from utils.auth import (
    AuthUser,
    get_current_user,
    exchange_code_for_tokens,
    get_userinfo,
    _make_session_token,
    AUTH0_DOMAIN,
    AUTH0_CLIENT_ID,
    AUTH0_CALLBACK_URL,
    FRONTEND_URL,
)

log    = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")

_COOKIE_NAME = "session"
_SECURE      = os.getenv("COOKIE_SECURE", "false").lower() == "true"


@router.get("/me")
async def me(request: Request):
    try:
        user = await get_current_user(request)
        # Upsert user in DB
        db = request.app.state.db
        await db.users.upsert(user.sub, user.email, user.name, user.picture)
        return {"sub": user.sub, "email": user.email, "name": user.name, "picture": user.picture}
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})


@router.get("/initiate")
async def initiate():
    url = (
        f"https://{AUTH0_DOMAIN}/authorize"
        f"?response_type=code"
        f"&client_id={AUTH0_CLIENT_ID}"
        f"&redirect_uri={AUTH0_CALLBACK_URL}"
        f"&scope=openid+profile+email"
    )
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: str, request: Request, response: Response):
    try:
        tokens   = await exchange_code_for_tokens(code)
        userinfo = await get_userinfo(tokens["access_token"])
        user     = AuthUser(
            sub     = userinfo["sub"],
            email   = userinfo.get("email", ""),
            name    = userinfo.get("name"),
            picture = userinfo.get("picture"),
        )
        # Upsert user in DB
        db = request.app.state.db
        await db.users.upsert(user.sub, user.email, user.name, user.picture)

        token = _make_session_token(user)
        resp  = RedirectResponse(url=f"{FRONTEND_URL}/")
        resp.set_cookie(
            key      = _COOKIE_NAME,
            value    = token,
            httponly = True,
            samesite = "lax",
            secure   = _SECURE,
            max_age  = 60 * 60 * 24 * 30,  # 30 days
        )
        return resp
    except Exception as exc:
        log.error("Auth callback failed: %s", exc)
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=auth_failed")


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(_COOKIE_NAME)
    return {"ok": True}
