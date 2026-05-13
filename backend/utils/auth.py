"""
Session management — httpOnly cookie, HS256 JWT.

Pattern mirrors sgummalla_works/express-server:
  - Backend signs a session JWT with JWT_SECRET (HS256)
  - Cookie is httpOnly, sameSite=lax, secure in production
  - Browser never touches the token — it's sent automatically with credentials:'include'
  - get_current_user FastAPI dependency reads the cookie on every protected request
"""

import os
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Request
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

JWT_SECRET    = os.getenv("JWT_SECRET", "change-me")
COOKIE_NAME   = "ta_session"
ALGORITHM     = "HS256"
EXPIRE_HOURS  = 24
FRONTEND_URL  = os.getenv("FRONTEND_URL", "")   # e.g. http://localhost:5173 in dev


@dataclass
class AuthUser:
    sub:     str
    email:   str
    name:    str    = ""
    picture: str    = ""


# ── Token helpers ─────────────────────────────────────────────────────────────

def sign_session(user: AuthUser) -> str:
    payload = {
        "sub":     user.sub,
        "email":   user.email,
        "name":    user.name,
        "picture": user.picture,
        "exp":     datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def verify_session(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])


def cookie_options(secure: bool = False) -> dict:
    return {
        "key":      COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "secure":   secure,
        "max_age":  EXPIRE_HOURS * 3600,
    }


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    ta_session: str | None = Cookie(default=None),
) -> AuthUser:
    """
    Read and validate the session cookie.
    On success: upserts the user in DB and loads their API keys into ContextVar.
    """
    if not ta_session:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = verify_session(ta_session)
    except JWTError:
        raise HTTPException(401, "Session expired — please log in again")

    user = AuthUser(
        sub     = payload["sub"],
        email   = payload.get("email", ""),
        name    = payload.get("name", ""),
        picture = payload.get("picture", ""),
    )

    db = request.app.state.db
    await db.upsert_user(user.sub, user.email, user.name, user.picture)

    from utils.api_keys import decrypt
    from utils.user_context import set_user_context

    raw_keys = await db.get_all_api_keys(user.sub)
    decrypted: dict[str, str] = {}
    for k, enc in raw_keys.items():
        try:
            decrypted[k] = decrypt(enc)
        except Exception:
            pass

    anthropic_mode = await db.get_config(user.sub, "anthropic_mode") or "direct"
    set_user_context(decrypted, anthropic_mode)

    return user
