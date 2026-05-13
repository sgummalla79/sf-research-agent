"""
Flows routes.

GET /api/flows              → list available agent flows + chat models
"""

from fastapi import APIRouter

from flows.registry import get_all_flows, CHAT_MODELS, CHAT_DEFAULT_MODEL

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("")
async def list_flows() -> dict:
    """Return all available agent flows and the curated chat model list."""
    flows = [
        {
            "id":          f.id,
            "name":        f.name,
            "description": f.description,
            "icon":        f.icon,
        }
        for f in get_all_flows().values()
    ]
    return {
        "flows":              flows,
        "chat_models":        CHAT_MODELS,
        "chat_default_model": CHAT_DEFAULT_MODEL,
    }
