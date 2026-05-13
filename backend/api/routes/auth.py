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

# Comma-separated list of Auth0 connection names configured for this app.
# Set in .env — no Management API needed.
_RAW_CONNECTIONS = os.getenv("AUTH0_CONNECTIONS", "")

# Strategy is inferred from the connection name convention used by Auth0.
_STRATEGY_MAP = {
    "google-oauth2":   "google-oauth2",
    "github":          "github",
    "linkedin":        "linkedin",
    "twitter":         "twitter",
    "facebook":        "facebook",
    "microsoft":       "microsoft",
    "apple":           "apple",
    "windowslive":     "windowslive",
}

def _infer_strategy(name: str) -> str:
    lower = name.lower()
    for key, strategy in _STRATEGY_MAP.items():
        if key in lower:
            return strategy
    return "auth0"   # fallback → database / username-password connection


_DISPLAY_NAMES = {
    "google-oauth2": "Google",
    "github":        "GitHub",
    "linkedin":      "LinkedIn",
    "twitter":       "Twitter / X",
    "facebook":      "Facebook",
    "microsoft":     "Microsoft",
    "apple":         "Apple",
    "windowslive":   "Microsoft",
}

def _display_name(name: str, strategy: str) -> str:
    return _DISPLAY_NAMES.get(strategy, name.replace("-", " ").title())


# ── Connections ───────────────────────────────────────────────────────────────

@router.get("/connections")
async def list_connections():
    """
    Return the connections configured for this app via AUTH0_CONNECTIONS env var.
    No Management API required.
    Each item: {name, display_name, strategy}
      strategy = "auth0"         → show username/password form
      strategy = "google-oauth2" → show social button
    """
    connections = []
    for raw in _RAW_CONNECTIONS.split(","):
        name = raw.strip()
        if not name:
            continue
        strategy = _infer_strategy(name)
        connections.append({
            "name":         name,
            "display_name": _display_name(name, strategy),
            "strategy":     strategy,
        })
    return {"connections": connections}


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
