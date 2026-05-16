"""
LLM provider management routes.

GET    /api/providers                  — list all providers + AWS Bedrock tile
POST   /api/providers/bedrock/connect  — save Bedrock URL + token
PATCH  /api/providers/bedrock/toggle   — toggle Bedrock active
DELETE /api/providers/bedrock          — remove Bedrock credentials
POST   /api/providers/{id}/connect     — save/update API key (sets isactive=True)
PATCH  /api/providers/{id}/toggle      — toggle isactive without changing the key
DELETE /api/providers/{id}             — disconnect (delete key)
GET    /api/providers/model-info       — metadata for a specific model
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
    api_key: str


class BedrockConnectRequest(BaseModel):
    bedrock_url:   str
    bedrock_token: str


@router.get("")
async def list_providers(request: Request, current_user: AuthUser = Depends(get_current_user)):
    db           = request.app.state.db
    key_statuses = await db.users.get_api_key_statuses(current_user.sub)

    providers = []
    for pid in PROVIDER_ORDER:
        info     = PROVIDERS.get(pid, {})
        has_key  = pid in key_statuses
        isactive = key_statuses.get(pid, False)
        providers.append({
            "id":          pid,
            "name":        info.get("name", pid),
            "connected":   has_key,
            "isactive":    isactive,
            "description": info.get("description", ""),
        })

    # AWS Bedrock — virtual tile keyed on anthropic_bedrock_url
    has_bedrock   = "anthropic_bedrock_url" in key_statuses
    bedrock_active = key_statuses.get("anthropic_bedrock_url", False)
    providers.append({
        "id":          "bedrock",
        "name":        "AWS Bedrock",
        "connected":   has_bedrock,
        "isactive":    bedrock_active,
        "description": "Claude models via AWS Bedrock",
    })

    return {"providers": providers}


# ── AWS Bedrock (literal routes — must be before /{provider_id}) ──────────────

@router.post("/bedrock/connect")
async def connect_bedrock(
    body:         BedrockConnectRequest,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db = request.app.state.db
    await db.users.save_api_key(current_user.sub, "anthropic_bedrock_url",   encrypt(body.bedrock_url,   current_user.sub))
    await db.users.save_api_key(current_user.sub, "anthropic_bedrock_token", encrypt(body.bedrock_token, current_user.sub))
    await db.users.save_api_key(current_user.sub, "anthropic_mode",          encrypt("bedrock",           current_user.sub))
    return {"ok": True, "provider": "bedrock"}


@router.patch("/bedrock/toggle")
async def toggle_bedrock(
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db       = request.app.state.db
    statuses = await db.users.get_api_key_statuses(current_user.sub)
    if "anthropic_bedrock_url" not in statuses:
        raise HTTPException(status_code=404, detail="AWS Bedrock is not configured.")
    new_isactive = not statuses["anthropic_bedrock_url"]
    for key in ("anthropic_bedrock_url", "anthropic_bedrock_token"):
        if key in statuses:
            await db.users.set_api_key_active(current_user.sub, key, new_isactive)
    return {"ok": True, "provider": "bedrock", "isactive": new_isactive}


@router.delete("/bedrock")
async def disconnect_bedrock(
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db = request.app.state.db
    for key in ("anthropic_bedrock_url", "anthropic_bedrock_token", "anthropic_mode"):
        await db.users.delete_api_key(current_user.sub, key)
    return {"ok": True, "provider": "bedrock"}


# ── Regular providers ─────────────────────────────────────────────────────────

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
    return {"ok": True, "provider": provider_id}


@router.patch("/{provider_id}/toggle")
async def toggle_provider(
    provider_id:  str,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db       = request.app.state.db
    statuses = await db.users.get_api_key_statuses(current_user.sub)
    if provider_id not in statuses:
        raise HTTPException(status_code=404, detail=f"No key stored for provider '{provider_id}'.")
    new_isactive = not statuses[provider_id]
    await db.users.set_api_key_active(current_user.sub, provider_id, new_isactive)
    return {"ok": True, "provider": provider_id, "isactive": new_isactive}


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
