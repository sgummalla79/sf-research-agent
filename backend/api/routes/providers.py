"""
Provider management routes.

GET  /api/providers                        → list all providers with key status + cached models
GET  /api/providers/model-info             → pricing + limits for a provider/model pair
POST /api/providers/{provider_id}/connect  → save key, fetch & cache model list
POST /api/providers/{provider_id}/refresh  → re-fetch models for an already-connected provider
DELETE /api/providers/{provider_id}        → remove key + cached model list
"""

import json
import logging

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from fastapi import Query
from utils.api_keys import encrypt, decrypt, populate_cache, populate_config_cache, is_configured
from utils.provider_registry import PROVIDER_ORDER, PROVIDERS, fetch_models
from utils.models_cache import get_all_provider_models, populate_models_cache
from utils.model_metadata import lookup as metadata_lookup, fetch_live as metadata_fetch_live

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("")
async def list_providers(request: Request) -> dict:
    """Return all providers with their connection status and cached model lists."""
    db = request.app.state.db
    stored_keys = await db.get_all_api_keys()
    model_cache = get_all_provider_models()

    providers_out = []
    for pid in PROVIDER_ORDER:
        info = PROVIDERS[pid]

        if pid == "anthropic":
            active_mode = await db.get_config("anthropic_mode") or "direct"
            if active_mode == "bedrock":
                connected = bool(stored_keys.get("anthropic_bedrock_url")) and bool(stored_keys.get("anthropic_bedrock_token"))
            else:
                connected = bool(stored_keys.get("anthropic"))
            entry = {
                "id":          pid,
                "name":        info["name"],
                "description": info["description"],
                "placeholder": info["placeholder"],
                "key_label":   info["key_label"],
                "auth_modes":  info["auth_modes"],
                "active_mode": active_mode,
                "connected":   connected,
                "models":      model_cache.get(pid, []),
            }
        else:
            connected = pid in stored_keys and bool(stored_keys[pid])
            entry = {
                "id":          pid,
                "name":        info["name"],
                "description": info["description"],
                "placeholder": info["placeholder"],
                "key_label":   info["key_label"],
                "connected":   connected,
                "models":      model_cache.get(pid, []),
            }
        providers_out.append(entry)

    return {"providers": providers_out}


@router.get("/model-info")
async def get_model_info(
    provider: str = Query(...),
    model:    str = Query(...),
) -> dict:
    """
    Return context window, max output tokens, and pricing for a provider/model pair.

    Strategy:
      1. Try a live API call (Anthropic only for now) to get accurate context window.
      2. Merge with / fall back to pattern-matched hardcoded metadata.
      3. Return whatever is available; frontend handles missing fields gracefully.
    """
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider!r}")

    # Start with pattern-matched hardcoded data
    meta = metadata_lookup(model) or {}

    # Attempt a live fetch to get more accurate / up-to-date context window
    live = await metadata_fetch_live(provider, model)
    if live:
        meta.update(live)

    return {
        "provider": provider,
        "model":    model,
        "found":    bool(meta),
        **meta,
    }


class ConnectPayload(BaseModel):
    api_key:       str = ""
    mode:          str = "direct"   # "direct" | "bedrock" — Anthropic only
    bedrock_url:   str = ""
    bedrock_token: str = ""


# Keys that belong to each Anthropic auth mode — used for stale-key cleanup on mode switch
_ANTHROPIC_DIRECT_KEYS  = ["anthropic"]
_ANTHROPIC_BEDROCK_KEYS = ["anthropic_bedrock_url", "anthropic_bedrock_token"]


@router.post("/{provider_id}/connect")
async def connect_provider(provider_id: str, payload: ConnectPayload, request: Request) -> dict:
    """Validate + save key(s), then fetch and cache the model list."""
    if provider_id not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id!r}")

    db = request.app.state.db

    if provider_id == "anthropic":
        mode = payload.mode or "direct"

        if mode == "bedrock":
            bedrock_url   = payload.bedrock_url.strip()
            bedrock_token = payload.bedrock_token.strip()
            if not bedrock_url or not bedrock_token:
                raise HTTPException(status_code=422, detail="Bedrock Base URL and Auth Token are both required.")
            try:
                models = await fetch_models("anthropic", "", mode="bedrock", bedrock_url=bedrock_url, bedrock_token=bedrock_token)
            except Exception as exc:
                logger.warning("Anthropic Bedrock connect failed: %s", exc)
                raise HTTPException(status_code=422, detail=f"Could not connect to Anthropic via Bedrock: {exc}")

            # Remove stale direct key
            await db.delete_api_key("anthropic")
            # Save new bedrock credentials
            await db.save_api_key("anthropic_bedrock_url",   encrypt(bedrock_url))
            await db.save_api_key("anthropic_bedrock_token", encrypt(bedrock_token))

        else:  # direct
            api_key = payload.api_key.strip()
            if not api_key:
                raise HTTPException(status_code=422, detail="API key must not be empty.")
            try:
                models = await fetch_models("anthropic", api_key)
            except Exception as exc:
                logger.warning("Anthropic direct connect failed: %s", exc)
                raise HTTPException(status_code=422, detail=f"Could not connect to Anthropic: {exc}")

            # Remove stale bedrock keys
            await db.delete_api_key("anthropic_bedrock_url")
            await db.delete_api_key("anthropic_bedrock_token")
            # Save direct key
            await db.save_api_key("anthropic", encrypt(api_key))

        # Persist mode + model list; reset agent config so stale model names don't linger
        await db.save_config("anthropic_mode", mode)
        await db.save_config(f"models_{provider_id}", json.dumps(models))
        await db.delete_config("agent_config")

    else:
        api_key = payload.api_key.strip()
        if not api_key:
            raise HTTPException(status_code=422, detail="API key must not be empty.")
        try:
            models = await fetch_models(provider_id, api_key)
        except Exception as exc:
            logger.warning("Model fetch failed for %s: %s", provider_id, exc)
            raise HTTPException(
                status_code=422,
                detail=f"Could not connect to {PROVIDERS[provider_id]['name']}: {exc}",
            )
        await db.save_api_key(provider_id, encrypt(api_key))
        await db.save_config(f"models_{provider_id}", json.dumps(models))

    # Refresh in-memory caches
    stored = await db.get_all_api_keys()
    decrypted: dict[str, str] = {}
    for k, enc in stored.items():
        try:
            decrypted[k] = decrypt(enc)
        except Exception:
            pass
    populate_cache(decrypted)

    if provider_id == "anthropic":
        from utils.agent_config import populate_agent_config, DEFAULT_AGENT_CONFIG
        populate_config_cache({"anthropic_mode": mode})
        populate_agent_config(DEFAULT_AGENT_CONFIG)

    all_models = get_all_provider_models()
    all_models[provider_id] = models
    populate_models_cache(all_models)

    return {"connected": True, "provider": provider_id, "models": models}


@router.post("/{provider_id}/refresh")
async def refresh_models(provider_id: str, request: Request) -> dict:
    """Re-fetch the model list for an already-connected provider."""
    if provider_id not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id!r}")

    if not is_configured(provider_id):
        raise HTTPException(status_code=422, detail=f"{PROVIDERS[provider_id]['name']} is not connected.")

    from utils.api_keys import get_key
    api_key = get_key(provider_id)

    try:
        models = await fetch_models(provider_id, api_key)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Refresh failed for {PROVIDERS[provider_id]['name']}: {exc}",
        )

    db = request.app.state.db
    await db.save_config(f"models_{provider_id}", json.dumps(models))

    all_models = get_all_provider_models()
    all_models[provider_id] = models
    populate_models_cache(all_models)

    return {"provider": provider_id, "models": models}


@router.delete("/{provider_id}")
async def disconnect_provider(provider_id: str, request: Request) -> dict:
    """Remove the API key(s) and cached model list for a provider."""
    if provider_id not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id!r}")

    db = request.app.state.db

    if provider_id == "anthropic":
        # Remove all possible Anthropic keys regardless of current mode
        for key in _ANTHROPIC_DIRECT_KEYS + _ANTHROPIC_BEDROCK_KEYS:
            await db.delete_api_key(key)
        await db.delete_config("anthropic_mode")
        await db.delete_config(f"models_{provider_id}")
        await db.delete_config("agent_config")
        populate_config_cache({"anthropic_mode": "direct"})
        from utils.agent_config import populate_agent_config, DEFAULT_AGENT_CONFIG
        populate_agent_config(DEFAULT_AGENT_CONFIG)
    else:
        await db.delete_provider(provider_id)

    # Clear from model cache
    all_models = get_all_provider_models()
    all_models.pop(provider_id, None)
    populate_models_cache(all_models)

    # Refresh key cache
    stored = await db.get_all_api_keys()
    decrypted: dict[str, str] = {}
    for k, enc in stored.items():
        try:
            decrypted[k] = decrypt(enc)
        except Exception:
            pass
    populate_cache(decrypted)

    return {"disconnected": True, "provider": provider_id}
