"""
Auth0 JWT verification and FastAPI dependency.

Every protected route declares:
    current_user: AuthUser = Depends(get_current_user)

get_current_user verifies the Bearer token, upserts the user record in the
DB, then loads that user's decrypted API keys into the per-request
ContextVar so all downstream LLM calls use the right credentials.
"""

import os
import logging
from dataclasses import dataclass
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

AUTH0_DOMAIN   = os.getenv("AUTH0_DOMAIN", "")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "")

_bearer = HTTPBearer()


@dataclass
class AuthUser:
    sub:     str    # Auth0 user ID (e.g. "auth0|abc123", "google-oauth2|xyz")
    email:   str
    name:    str    = ""
    picture: str    = ""


# ── JWKS cache ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _jwks() -> dict:
    try:
        return _fetch_jwks()
    except Exception:
        _fetch_jwks.cache_clear()
        return _fetch_jwks()


def _find_rsa_key(kid: str) -> dict | None:
    for key in _jwks().get("keys", []):
        if key.get("kid") == kid:
            return {k: key[k] for k in ("kty", "kid", "use", "n", "e") if k in key}
    # One retry after cache clear
    _fetch_jwks.cache_clear()
    for key in _jwks().get("keys", []):
        if key.get("kid") == kid:
            return {k: key[k] for k in ("kty", "kid", "use", "n", "e") if k in key}
    return None


# ── Token verification ────────────────────────────────────────────────────────

def verify_token(token: str) -> dict:
    try:
        header  = jwt.get_unverified_header(token)
        rsa_key = _find_rsa_key(header.get("kid", ""))
        if not rsa_key:
            raise HTTPException(401, "Unable to find matching public key in JWKS.")
        return jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
    except JWTError as exc:
        raise HTTPException(401, f"Invalid token: {exc}")


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_user(
    request:     Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthUser:
    """
    1. Verify Bearer token (RS256, Auth0 JWKS).
    2. Upsert the user in the DB.
    3. Load the user's encrypted API keys and set them in ContextVar so
       LangGraph nodes and background tasks can call get_key() correctly.
    """
    claims = verify_token(credentials.credentials)

    user = AuthUser(
        sub     = claims["sub"],
        email   = claims.get("email", ""),
        name    = claims.get("name", "") or claims.get("nickname", ""),
        picture = claims.get("picture", ""),
    )

    db = request.app.state.db
    await db.upsert_user(user.sub, user.email, user.name, user.picture)

    # Load this user's API keys into the per-request ContextVar
    from utils.api_keys import decrypt
    from utils.user_context import set_user_context

    raw_keys = await db.get_all_api_keys(user.sub)
    decrypted: dict[str, str] = {}
    for k, enc in raw_keys.items():
        try:
            decrypted[k] = decrypt(enc)
        except Exception:
            logger.warning("Could not decrypt stored key '%s' for user %s", k, user.sub)

    anthropic_mode = await db.get_config(user.sub, "anthropic_mode") or "direct"
    set_user_context(decrypted, anthropic_mode)

    return user
