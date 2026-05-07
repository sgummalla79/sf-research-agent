"""
Settings routes — API key management.

GET  /api/settings/keys   → which keys are configured (booleans, never values)
POST /api/settings/keys   → validate then save/update one or more keys
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from utils.api_keys import encrypt, decrypt, populate_cache, KEY_NAMES
from utils.key_validator import validate_keys

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
    """Validate then encrypt and persist provided keys. Empty strings are skipped."""
    db = request.app.state.db

    incoming = {
        "anthropic":  payload.anthropic.strip(),
        "perplexity": payload.perplexity.strip(),
        "google":     payload.google.strip(),
    }
    new_keys = {k: v for k, v in incoming.items() if v}

    # Validate every key that was provided before touching the DB
    if new_keys:
        errors = await validate_keys(new_keys)
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})

    saved = []
    for key_name, value in new_keys.items():
        await db.save_api_key(key_name, encrypt(value))
        saved.append(key_name)

    # Refresh in-memory cache
    stored = await db.get_all_api_keys()
    decrypted: dict[str, str] = {}
    for k, enc in stored.items():
        try:
            decrypted[k] = decrypt(enc)
        except Exception:
            pass
    populate_cache(decrypted)

    return {"saved": saved, "configured": {k: (k in stored) for k in KEY_NAMES}}
