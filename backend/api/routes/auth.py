"""
Auth0 proxy routes — all traffic stays on our domain.

GET  /auth/connections          list enabled Auth0 connections (cached)
POST /auth/token                username/password login
POST /auth/callback             social OAuth code exchange
GET  /auth/me                   current user profile (requires JWT)
POST /auth/refresh              exchange refresh token for new access token
"""

import os
import logging
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from utils.auth import AuthUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

AUTH0_DOMAIN        = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID     = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_AUDIENCE      = os.getenv("AUTH0_AUDIENCE", "")
AUTH0_CALLBACK_URL  = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:5173/callback")

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

# ── Management API token (same SPA credentials, client_credentials grant) ────

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
    _mgmt_expires_at = time.time() + data.get("expires_in", 86400) - 60  # refresh 60s early
    return _mgmt_token


# ── Connections (cached 1 hour) ───────────────────────────────────────────────

_connections_cache:      list  = []
_connections_expires_at: float = 0.0


@router.get("/connections")
async def list_connections():
    """
    Fetch social connections enabled for this app from Auth0 Management API.
    Uses the same AUTH0_CLIENT_ID + AUTH0_CLIENT_SECRET (client_credentials grant).
    Results are cached for 1 hour.
    Each item: {name, display_name, strategy}
    """
    global _connections_cache, _connections_expires_at

    if _connections_cache and time.time() < _connections_expires_at:
        return {"connections": _connections_cache}

    try:
        token = await _get_mgmt_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{AUTH0_DOMAIN}/api/v2/connections",
                params={
                    "client_id": AUTH0_CLIENT_ID,
                    "fields":    "name,strategy,display_name,enabled_clients",
                },
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
            if c.get("strategy") != "auth0"                          # social only
            and AUTH0_CLIENT_ID in (c.get("enabled_clients") or [])  # enabled for this app
        ]
        _connections_expires_at = time.time() + 3600   # cache 1 hour

    except Exception as exc:
        logger.error("Auth0 connections fetch failed: %s", exc, exc_info=True)
        _connections_cache = []

    return {"connections": _connections_cache}


# ── Social login initiate ─────────────────────────────────────────────────────

@router.get("/initiate")
async def initiate_social(connection: str = ""):
    """
    Redirect the browser to Auth0's /authorize endpoint for a specific
    social connection.  Called by the frontend for social login buttons.
    All Auth0 config lives server-side — no VITE_ vars needed in the browser.
    """
    from fastapi.responses import RedirectResponse
    from urllib.parse import urlencode

    params = {
        "client_id":     AUTH0_CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  AUTH0_CALLBACK_URL,
        "scope":         "openid profile email offline_access",
    }
    if connection:
        params["connection"] = connection

    url = f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"
    return RedirectResponse(url)


# ── Username / password login ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:      str
    password:   str
    connection: str = "Username-Password-Authentication"


@router.post("/token")
async def login_with_password(body: LoginRequest):
    """Proxy the Resource Owner Password Grant to Auth0."""
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
                "audience":      AUTH0_AUDIENCE,
                "scope":         "openid profile email offline_access",
            },
            timeout=15,
        )

    if resp.status_code != 200:
        detail = resp.json().get("error_description") or resp.json().get("error") or "Login failed."
        raise HTTPException(status_code=401, detail=detail)

    return resp.json()


# ── Social OAuth code exchange ────────────────────────────────────────────────

class CallbackRequest(BaseModel):
    code:         str
    redirect_uri: Optional[str] = None


@router.post("/callback")
async def oauth_callback(body: CallbackRequest):
    """Exchange an authorization code (from social login) for tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type":    "authorization_code",
                "client_id":     AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "code":          body.code,
                "redirect_uri":  body.redirect_uri or AUTH0_CALLBACK_URL,
            },
            timeout=15,
        )

    if resp.status_code != 200:
        detail = resp.json().get("error_description") or "Code exchange failed."
        raise HTTPException(status_code=401, detail=detail)

    return resp.json()


# ── Token refresh ─────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type":    "refresh_token",
                "client_id":     AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "refresh_token": body.refresh_token,
            },
            timeout=15,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Refresh failed — please log in again.")

    return resp.json()


# ── Current user ──────────────────────────────────────────────────────────────

@router.get("/me")
async def get_me(current_user: AuthUser = Depends(get_current_user)):
    return {
        "sub":     current_user.sub,
        "email":   current_user.email,
        "name":    current_user.name,
        "picture": current_user.picture,
    }
