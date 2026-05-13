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
import asyncio
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from utils.auth import AuthUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

AUTH0_DOMAIN          = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID       = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET   = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_AUDIENCE        = os.getenv("AUTH0_AUDIENCE", "")
AUTH0_CALLBACK_URL    = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:5173/callback")
AUTH0_MGMT_CLIENT_ID  = os.getenv("AUTH0_MGMT_CLIENT_ID", "")
AUTH0_MGMT_CLIENT_SECRET = os.getenv("AUTH0_MGMT_CLIENT_SECRET", "")

_mgmt_token_cache: dict = {}   # {token, expires_at}


# ── Management API token ──────────────────────────────────────────────────────

async def _get_mgmt_token() -> str:
    import time
    if _mgmt_token_cache.get("token") and time.time() < _mgmt_token_cache.get("expires_at", 0) - 60:
        return _mgmt_token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type":    "client_credentials",
                "client_id":     AUTH0_MGMT_CLIENT_ID,
                "client_secret": AUTH0_MGMT_CLIENT_SECRET,
                "audience":      f"https://{AUTH0_DOMAIN}/api/v2/",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    import time
    _mgmt_token_cache["token"]      = data["access_token"]
    _mgmt_token_cache["expires_at"] = time.time() + data.get("expires_in", 86400)
    return data["access_token"]


# ── Connections ───────────────────────────────────────────────────────────────

_connections_cache: list = []


@router.get("/connections")
async def list_connections():
    """
    Return the Auth0 connections enabled for this application.
    Each item: {name, display_name, strategy}
    strategy = "auth0"          → username/password form
    strategy = "google-oauth2"  → social button
    strategy = "github"         → social button
    etc.
    """
    global _connections_cache
    if _connections_cache:
        return {"connections": _connections_cache}

    try:
        token = await _get_mgmt_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{AUTH0_DOMAIN}/api/v2/connections",
                params={
                    "fields":          "name,display_name,strategy,enabled_clients",
                    "enabled_clients": AUTH0_CLIENT_ID,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            all_conns = resp.json()

        _connections_cache = [
            {
                "name":         c["name"],
                "display_name": c.get("display_name") or c["name"],
                "strategy":     c["strategy"],
            }
            for c in all_conns
            if AUTH0_CLIENT_ID in (c.get("enabled_clients") or [])
        ]
    except Exception as exc:
        logger.warning("Could not fetch Auth0 connections: %s", exc)
        _connections_cache = []

    return {"connections": _connections_cache}


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
