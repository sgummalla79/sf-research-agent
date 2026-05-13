"""
Auth routes — mirrors sgummalla_works/express-server pattern.

All auth flows use httpOnly session cookies (HS256, signed server-side).
The browser never touches a raw token.

GET  /auth/connections          list enabled social connections (Management API, cached 1h)
GET  /auth/initiate             redirect browser to Auth0 /authorize
GET  /auth/callback             Auth0 returns here; exchange code, set cookie, redirect to SPA
POST /auth/token                email/password login; set cookie, return user JSON
POST /auth/logout               clear session cookie
GET  /auth/me                   return current user from cookie (used for bootstrap on mount)
"""

import os
import logging
import time
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from utils.auth import AuthUser, FRONTEND_URL, COOKIE_NAME, sign_session, cookie_options, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

AUTH0_DOMAIN        = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID     = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_CALLBACK_URL  = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:5173/auth/callback")

_KNOWN_LABELS: dict[str, str] = {
    "google-oauth2": "Google",
    "github":        "GitHub",
    "twitter":       "Twitter / X",
    "facebook":      "Facebook",
    "linkedin":      "LinkedIn",
    "microsoft":     "Microsoft",
    "apple":         "Apple",
    "windowslive":   "Microsoft",
}

# ── Management API token ──────────────────────────────────────────────────────

_mgmt_token:      str   = ""
_mgmt_expires_at: float = 0.0


async def _get_mgmt_token() -> str:
    global _mgmt_token, _mgmt_expires_at
    if _mgmt_token and time.time() < _mgmt_expires_at:
        return _mgmt_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type":    "client_credentials",
                "client_id":     AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "audience":      f"https://{AUTH0_DOMAIN}/api/v2/",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    _mgmt_token      = data["access_token"]
    _mgmt_expires_at = time.time() + data.get("expires_in", 86400) - 60
    return _mgmt_token


# ── Connections (cached 1 hour) ───────────────────────────────────────────────

_connections_cache:      list  = []
_connections_expires_at: float = 0.0


@router.get("/connections")
async def list_connections():
    global _connections_cache, _connections_expires_at

    if _connections_cache and time.time() < _connections_expires_at:
        return {"connections": _connections_cache}

    try:
        token = await _get_mgmt_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{AUTH0_DOMAIN}/api/v2/connections",
                params={"client_id": AUTH0_CLIENT_ID,
                        "fields":    "name,strategy,display_name,enabled_clients"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            raw = resp.json()

        _connections_cache = [
            {
                "name":         c["name"],
                "display_name": c.get("display_name") or _KNOWN_LABELS.get(c["name"])
                                or _KNOWN_LABELS.get(c["strategy"]) or c["name"],
                "strategy":     c["strategy"],
            }
            for c in raw
            if c.get("strategy") != "auth0"
            and AUTH0_CLIENT_ID in (c.get("enabled_clients") or [])
        ]
        _connections_expires_at = time.time() + 3600

    except Exception as exc:
        logger.error("Auth0 connections fetch failed: %s", exc, exc_info=True)
        _connections_cache = []

    return {"connections": _connections_cache}


# ── Social login initiate ─────────────────────────────────────────────────────

@router.get("/initiate")
async def initiate_social(connection: str = ""):
    params: dict = {
        "client_id":     AUTH0_CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  AUTH0_CALLBACK_URL,
        "scope":         "openid profile email offline_access",
    }
    if connection:
        params["connection"] = connection
    return RedirectResponse(f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}")


# ── OAuth callback — server-side, sets cookie and redirects to SPA ────────────

@router.get("/callback")
async def oauth_callback(code: str, request: Request, error: str = ""):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/login?error={error}")

    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_resp = await client.post(
                f"https://{AUTH0_DOMAIN}/oauth/token",
                json={
                    "grant_type":    "authorization_code",
                    "client_id":     AUTH0_CLIENT_ID,
                    "client_secret": AUTH0_CLIENT_SECRET,
                    "code":          code,
                    "redirect_uri":  AUTH0_CALLBACK_URL,
                },
                timeout=15,
            )
            if not token_resp.is_success:
                raise ValueError(f"Token exchange failed: {token_resp.text}")
            tokens = token_resp.json()

            # Get user info
            userinfo_resp = await client.get(
                f"https://{AUTH0_DOMAIN}/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                timeout=10,
            )
            userinfo = userinfo_resp.json()

    except Exception as exc:
        logger.error("OAuth callback error: %s", exc)
        return RedirectResponse(f"{FRONTEND_URL}/login?error=auth_failed")

    user = AuthUser(
        sub     = userinfo["sub"],
        email   = userinfo.get("email", ""),
        name    = userinfo.get("name", "") or userinfo.get("nickname", ""),
        picture = userinfo.get("picture", ""),
    )

    db = request.app.state.db
    await db.upsert_user(user.sub, user.email, user.name, user.picture)

    token    = sign_session(user)
    redirect = RedirectResponse(f"{FRONTEND_URL}/")
    redirect.set_cookie(value=token, **cookie_options())
    return redirect


# ── Email / password login ────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:      str
    password:   str
    connection: str = "Username-Password-Authentication"


@router.post("/token")
async def login_with_password(body: LoginRequest, request: Request):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type":    "http://auth0.com/oauth/grant-type/password-realm",
                "realm":         body.connection,
                "username":      body.email,
                "password":      body.password,
                "client_id":     AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "scope":         "openid profile email",
            },
            timeout=15,
        )

    if not resp.is_success:
        detail = resp.json().get("error_description") or "Invalid email or password."
        raise HTTPException(401, detail)

    tokens = resp.json()

    # Fetch userinfo
    async with httpx.AsyncClient() as client:
        ui = await client.get(
            f"https://{AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
    userinfo = ui.json()

    user = AuthUser(
        sub     = userinfo["sub"],
        email   = userinfo.get("email", body.email),
        name    = userinfo.get("name", "") or userinfo.get("nickname", ""),
        picture = userinfo.get("picture", ""),
    )

    db = request.app.state.db
    await db.upsert_user(user.sub, user.email, user.name, user.picture)

    token    = sign_session(user)
    response = JSONResponse({"user": {
        "sub": user.sub, "email": user.email,
        "name": user.name, "picture": user.picture,
    }})
    response.set_cookie(value=token, **cookie_options())
    return response


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME)
    return response


# ── Me (bootstrap) ────────────────────────────────────────────────────────────

@router.get("/me")
async def get_me(current_user: AuthUser = Depends(get_current_user)):
    return {
        "sub":     current_user.sub,
        "email":   current_user.email,
        "name":    current_user.name,
        "picture": current_user.picture,
    }
