"""
Flows routes.

GET /api/flows  →  list available agent flows + chat models
"""

from fastapi import APIRouter, Request

from chat_models import CHAT_MODELS, CHAT_DEFAULT_MODEL

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("")
async def list_flows(request: Request) -> dict:
    """Return only installed agent flows and the chat model list."""
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry

    installed = await db.get_installed_skill_ids()
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
