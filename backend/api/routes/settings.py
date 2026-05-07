"""
Settings routes — API key management.

GET  /api/settings/keys   → which keys are configured (booleans, never values)
POST /api/settings/keys   → save/update one or more keys (empty fields are skipped)
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from utils.api_keys import encrypt, decrypt, populate_cache, KEY_NAMES

router = APIRouter(prefix="/api/settings", tags=["settings"])


class KeysPayload(BaseModel):
    anthropic:  str = ""
    perplexity: str = ""
    google:     str = ""


@router.get("/keys")
async def get_keys_status(request: Request) -> dict:
    """Returns which keys are configured as booleans — never exposes values."""
    db = request.app.state.db
    stored = await db.get_all_api_keys()
    return {k: (k in stored and bool(stored[k])) for k in KEY_NAMES}


@router.post("/keys")
async def save_keys(payload: KeysPayload, request: Request) -> dict:
    """Encrypt and persist provided keys. Empty strings are ignored (partial update)."""
    db = request.app.state.db

    incoming = {
        "anthropic":  payload.anthropic.strip(),
        "perplexity": payload.perplexity.strip(),
        "google":     payload.google.strip(),
    }

    saved = []
    for key_name, value in incoming.items():
        if value:
            await db.save_api_key(key_name, encrypt(value))
            saved.append(key_name)

    # Refresh in-memory cache with all stored keys after save
    stored = await db.get_all_api_keys()
    decrypted: dict[str, str] = {}
    for k, enc in stored.items():
        try:
            decrypted[k] = decrypt(enc)
        except Exception:
            pass
    populate_cache(decrypted)

    return {"saved": saved, "configured": {k: (k in stored) for k in KEY_NAMES}}
