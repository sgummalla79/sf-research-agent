"""
Settings routes — API key management and agent LLM configuration.

GET  /api/settings/keys          → which keys are configured (booleans, never values)
POST /api/settings/keys          → validate then save/update one or more keys
GET  /api/settings/agent-config  → current per-agent provider/model config + available options
POST /api/settings/agent-config  → save per-agent provider/model config
"""

import json

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from utils.api_keys import encrypt, decrypt, populate_cache, KEY_NAMES
from utils.key_validator import validate_keys
from utils.agent_config import AGENT_SLOTS, SLOT_LABELS, DEFAULT_AGENT_CONFIG, get_agent_config, populate_agent_config
from utils.models_cache import get_provider_models
from utils.provider_registry import PROVIDERS

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


@router.get("/agent-config")
async def get_agent_config_route() -> dict:
    """Returns current per-agent provider/model config along with available options."""
    return {
        "config":   get_agent_config(),
        "slots":    AGENT_SLOTS,
        "labels":   SLOT_LABELS,
        "defaults": DEFAULT_AGENT_CONFIG,
    }


class AgentConfigPayload(BaseModel):
    config: dict  # {slot: {provider, model}}


@router.post("/agent-config")
async def save_agent_config_route(payload: AgentConfigPayload, request: Request) -> dict:
    """Validate and persist per-agent provider/model config."""
    errors: dict[str, str] = {}
    for slot, cfg in payload.config.items():
        if slot not in AGENT_SLOTS:
            errors[slot] = f"Unknown agent slot: {slot!r}"
            continue
        provider = cfg.get("provider", "")
        model    = cfg.get("model", "")
        if provider not in PROVIDERS:
            errors[slot] = f"Unknown provider: {provider!r}"
            continue
        # Validate model against the dynamically fetched list.
        # If no models have been fetched yet for this provider, skip validation
        # (user may configure before refreshing, agents will fail at runtime if wrong).
        cached = get_provider_models(provider)
        if cached and model not in cached:
            errors[slot] = (
                f"Model '{model}' was not found in the fetched model list for {PROVIDERS[provider]['name']}. "
                f"Go to Providers and refresh models, or pick a model from the dropdown."
            )

    if errors:
        raise HTTPException(status_code=422, detail={"config_errors": errors})

    db = request.app.state.db
    await db.save_config("agent_config", json.dumps(payload.config))
    populate_agent_config(payload.config)

    return {"saved": True, "config": get_agent_config()}
