"""
Flows routes.

GET /api/flows  →  list the current user's installed agent flows + chat models
"""

from fastapi import APIRouter, Depends, Request

from chat_models import CHAT_MODELS_BY_PROVIDER, CHAT_DEFAULT_MODEL, CHAT_DEFAULT_PROVIDER
from utils.auth import AuthUser, get_current_user

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("")
async def list_flows(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Return only this user's installed agent flows and chat models for connected providers."""
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry

    installed = await db.get_installed_skill_ids(current_user.sub)
    flows = [
        {
            "id":          skill.manifest.id,
            "name":        skill.manifest.name,
            "description": skill.manifest.description,
            "icon":        skill.manifest.icon,
        }
        for skill in skill_registry.list_all()
        if skill.manifest.id in installed
    ]

    # Only return models for providers the user has connected
    connected_keys = await db.get_all_api_keys(current_user.sub)
    connected_providers = {
        pid for pid in CHAT_MODELS_BY_PROVIDER
        if any(k.startswith(pid) for k in connected_keys)
    }

    chat_models = [
        model
        for pid in CHAT_MODELS_BY_PROVIDER
        if pid in connected_providers
        for model in CHAT_MODELS_BY_PROVIDER[pid]
    ]

    # Pick the default: first model marked default from a connected provider,
    # fall back to global default if Anthropic is connected, else first model
    default = next(
        (m for m in chat_models if m.get("default")),
        chat_models[0] if chat_models else None,
    )

    theme = await db.get_config(current_user.sub, "theme_color") or "default"

    return {
        "flows":                 flows,
        "chat_models":           chat_models,
        "chat_default_model":    default["model"]    if default else CHAT_DEFAULT_MODEL,
        "chat_default_provider": default["provider"] if default else CHAT_DEFAULT_PROVIDER,
        "theme":                 theme,
    }
