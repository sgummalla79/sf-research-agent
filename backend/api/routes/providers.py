"""
LLM provider management routes.

GET    /api/providers               — list all providers with connection status
POST   /api/providers/{id}/connect  — save/update API key for a provider
DELETE /api/providers/{id}          — disconnect (delete key)
GET    /api/providers/model-info    — get metadata for a specific model

Model lists are NOT cached. The frontend uses hardcoded defaults per provider
(curated, stable lists that rarely change). No /refresh endpoint is needed.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from utils.auth import AuthUser, get_current_user
from utils.user_api_keys import encrypt
from utils.provider_registry import PROVIDERS, PROVIDER_ORDER

log    = logging.getLogger(__name__)
router = APIRouter(prefix="/api/providers")


class ConnectRequest(BaseModel):
    api_key:        str
    mode:           Optional[str] = "direct"   # direct | bedrock
    bedrock_url:    Optional[str] = None
    bedrock_token:  Optional[str] = None


@router.get("")
async def list_providers(request: Request, current_user: AuthUser = Depends(get_current_user)):
    db            = request.app.state.db
    encrypted_keys = await db.users.get_all_api_keys(current_user.sub)
    connected_ids  = {k.split("_")[0] for k in encrypted_keys if encrypted_keys[k]}

    providers = []
    for pid in PROVIDER_ORDER:
        info = PROVIDERS.get(pid, {})
        providers.append({
            "id":          pid,
            "name":        info.get("name", pid),
            "connected":   pid in connected_ids,
            "icon":        info.get("icon", ""),
            "auth_modes":  info.get("auth_modes"),
            "description": info.get("description", ""),
        })
    return {"providers": providers}


@router.post("/{provider_id}/connect")
async def connect_provider(
    provider_id:  str,
    body:         ConnectRequest,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    if provider_id not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    db  = request.app.state.db
    enc = encrypt(body.api_key, current_user.sub)
    await db.users.save_api_key(current_user.sub, provider_id, enc)

    if provider_id == "anthropic" and body.mode == "bedrock":
        await db.users.save_api_key(
            current_user.sub, "anthropic_mode", encrypt("bedrock", current_user.sub)
        )
        if body.bedrock_url:
            await db.users.save_api_key(
                current_user.sub, "anthropic_bedrock_url", encrypt(body.bedrock_url, current_user.sub)
            )
        if body.bedrock_token:
            await db.users.save_api_key(
                current_user.sub, "anthropic_bedrock_token", encrypt(body.bedrock_token, current_user.sub)
            )

    return {"ok": True, "provider": provider_id}


@router.delete("/{provider_id}")
async def disconnect_provider(
    provider_id:  str,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db = request.app.state.db
    await db.users.delete_api_key(current_user.sub, provider_id)
    return {"ok": True}


@router.get("/model-info")
async def model_info(
    provider: str,
    model:    str,
    request:  Request,
    current_user: AuthUser = Depends(get_current_user),
):
    from utils.model_metadata import get_model_info
    info = get_model_info(provider, model)
    return info or {"provider": provider, "model": model}
