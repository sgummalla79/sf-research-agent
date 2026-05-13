"""
Provider management routes — per user.

GET    /api/providers                        → list all providers with key status + cached models
GET    /api/providers/model-info             → pricing + limits for a provider/model pair
POST   /api/providers/{provider_id}/connect  → save key, fetch & cache model list
POST   /api/providers/{provider_id}/refresh  → re-fetch models for an already-connected provider
DELETE /api/providers/{provider_id}          → remove key + cached model list
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from utils.api_keys import encrypt, decrypt
from utils.auth import AuthUser, get_current_user
from utils.provider_registry import PROVIDER_ORDER, PROVIDERS, fetch_models
from utils.model_metadata import lookup as metadata_lookup, fetch_live as metadata_fetch_live

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/providers", tags=["providers"])

_ANTHROPIC_DIRECT_KEYS  = ["anthropic"]
_ANTHROPIC_BEDROCK_KEYS = ["anthropic_bedrock_url", "anthropic_bedrock_token"]


async def _get_user_models(db, user_id: str, provider_id: str) -> list:
    raw = await db.get_config(user_id, f"models_{provider_id}")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return []


@router.get("")
async def list_providers(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    db          = request.app.state.db
    stored_keys = await db.get_all_api_keys(current_user.sub)

    providers_out = []
    for pid in PROVIDER_ORDER:
        info   = PROVIDERS[pid]
        models = await _get_user_models(db, current_user.sub, pid)

        if pid == "anthropic":
            active_mode = await db.get_config(current_user.sub, "anthropic_mode") or "direct"
            if active_mode == "bedrock":
                connected = bool(stored_keys.get("anthropic_bedrock_url")) and \
                            bool(stored_keys.get("anthropic_bedrock_token"))
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
                "models":      models,
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
                "models":      models,
            }
        providers_out.append(entry)

    return {"providers": providers_out}


@router.get("/model-info")
async def get_model_info(
    provider: str = Query(...),
    model:    str = Query(...),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider!r}")
    meta = metadata_lookup(model) or {}
    live = await metadata_fetch_live(provider, model)
    if live:
        meta.update(live)
    return {"provider": provider, "model": model, "found": bool(meta), **meta}


class ConnectPayload(BaseModel):
    api_key:       str = ""
    mode:          str = "direct"
    bedrock_url:   str = ""
    bedrock_token: str = ""


@router.post("/{provider_id}/connect")
async def connect_provider(
    provider_id: str,
    payload: ConnectPayload,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    if provider_id not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id!r}")

    db  = request.app.state.db
    uid = current_user.sub

    if provider_id == "anthropic":
        mode = payload.mode or "direct"
        if mode == "bedrock":
            bedrock_url   = payload.bedrock_url.strip()
            bedrock_token = payload.bedrock_token.strip()
            if not bedrock_url or not bedrock_token:
                raise HTTPException(422, "Bedrock Base URL and Auth Token are both required.")
            try:
                models = await fetch_models("anthropic", "", mode="bedrock",
                                            bedrock_url=bedrock_url, bedrock_token=bedrock_token)
            except Exception as exc:
                raise HTTPException(422, f"Could not connect to Anthropic via Bedrock: {exc}")

            await db.delete_api_key(uid, "anthropic")
            await db.save_api_key(uid, "anthropic_bedrock_url",   encrypt(bedrock_url))
            await db.save_api_key(uid, "anthropic_bedrock_token", encrypt(bedrock_token))
        else:
            api_key = payload.api_key.strip()
            if not api_key:
                raise HTTPException(422, "API key must not be empty.")
            try:
                models = await fetch_models("anthropic", api_key)
            except Exception as exc:
                raise HTTPException(422, f"Could not connect to Anthropic: {exc}")

            await db.delete_api_key(uid, "anthropic_bedrock_url")
            await db.delete_api_key(uid, "anthropic_bedrock_token")
            await db.save_api_key(uid, "anthropic", encrypt(api_key))

        await db.save_config(uid, "anthropic_mode",         mode)
        await db.save_config(uid, f"models_{provider_id}", json.dumps(models))
    else:
        api_key = payload.api_key.strip()
        if not api_key:
            raise HTTPException(422, "API key must not be empty.")
        try:
            models = await fetch_models(provider_id, api_key)
        except Exception as exc:
            raise HTTPException(
                422,
                f"Could not connect to {PROVIDERS[provider_id]['name']}: {exc}",
            )
        await db.save_api_key(uid, provider_id, encrypt(api_key))
        await db.save_config(uid, f"models_{provider_id}", json.dumps(models))

    return {"connected": True, "provider": provider_id, "models": models}


@router.post("/{provider_id}/refresh")
async def refresh_models(
    provider_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    if provider_id not in PROVIDERS:
        raise HTTPException(404, f"Unknown provider: {provider_id!r}")

    from utils.api_keys import get_key, is_configured
    if not is_configured(provider_id):
        raise HTTPException(422, f"{PROVIDERS[provider_id]['name']} is not connected.")

    api_key = get_key(provider_id)
    try:
        models = await fetch_models(provider_id, api_key)
    except Exception as exc:
        raise HTTPException(422, f"Refresh failed for {PROVIDERS[provider_id]['name']}: {exc}")

    db  = request.app.state.db
    uid = current_user.sub
    await db.save_config(uid, f"models_{provider_id}", json.dumps(models))
    return {"provider": provider_id, "models": models}


@router.delete("/{provider_id}")
async def disconnect_provider(
    provider_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    if provider_id not in PROVIDERS:
        raise HTTPException(404, f"Unknown provider: {provider_id!r}")

    db  = request.app.state.db
    uid = current_user.sub

    if provider_id == "anthropic":
        for key in _ANTHROPIC_DIRECT_KEYS + _ANTHROPIC_BEDROCK_KEYS:
            await db.delete_api_key(uid, key)
        await db.delete_config(uid, "anthropic_mode")
        await db.delete_config(uid, f"models_{provider_id}")
    else:
        await db.delete_provider(uid, provider_id)
        await db.delete_config(uid, f"models_{provider_id}")

    return {"disconnected": True, "provider": provider_id}
