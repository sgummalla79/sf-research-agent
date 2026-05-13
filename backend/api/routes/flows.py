"""
Flows routes.

GET /api/flows  →  list the current user's installed agent flows + chat models
"""

from fastapi import APIRouter, Depends, Request

from chat_models import CHAT_MODELS, CHAT_DEFAULT_MODEL
from utils.auth import AuthUser, get_current_user

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("")
async def list_flows(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Return only this user's installed agent flows and the chat model list."""
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
    return {
        "flows":              flows,
        "chat_models":        CHAT_MODELS,
        "chat_default_model": CHAT_DEFAULT_MODEL,
    }
