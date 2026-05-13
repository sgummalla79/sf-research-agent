"""
Agent prompt versioning API — per user.

GET    /api/prompts/{flow_id}                        — all agents + current state
PUT    /api/prompts/{flow_id}/{agent_key}/draft       — save/update draft
DELETE /api/prompts/{flow_id}/{agent_key}/draft       — discard draft
POST   /api/prompts/{flow_id}/publish                — publish ALL agents (skill-level)
GET    /api/prompts/{flow_id}/snapshots              — skill version timeline
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from framework.registry import SkillNotFoundError
from utils.auth import AuthUser, get_current_user

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class SaveDraftRequest(BaseModel):
    content:     str
    agent_model: Optional[dict] = None


def _db(request: Request):
    return request.app.state.db


def _skill(request: Request, flow_id: str):
    try:
        return request.app.state.skill_registry.get(flow_id)
    except SkillNotFoundError:
        raise HTTPException(404, f"Skill '{flow_id}' not found")


# ── List all agents for a flow ────────────────────────────────────────────────

@router.get("/{flow_id}")
async def get_flow_prompts(
    flow_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    skill   = _skill(request, flow_id)
    db_rows = await _db(request).get_flow_prompts(current_user.sub, flow_id)
    by_key  = {r["agent_key"]: r for r in db_rows}

    slot_map = skill.manifest.agent_slot_map
    agents = [
        {
            "agent_key":        key,
            "label":            skill.manifest.agent_labels.get(key, key),
            "llm_slot":         slot_map.get(key),
            "latest_published": by_key.get(key, {}).get("latest_published"),
            "draft":            by_key.get(key, {}).get("draft"),
        }
        for key in skill.manifest.ordered_agent_keys
    ]
    has_draft = any(a["draft"] for a in agents)
    return {"flow_id": flow_id, "agents": agents, "has_draft": has_draft}


# ── Draft management ──────────────────────────────────────────────────────────

@router.put("/{flow_id}/{agent_key}/draft")
async def save_draft(
    flow_id:   str,
    agent_key: str,
    body:      SaveDraftRequest,
    request:   Request,
    current_user: AuthUser = Depends(get_current_user),
):
    _validate_key(request, flow_id, agent_key)
    await _db(request).save_prompt_draft(
        current_user.sub, flow_id, agent_key, body.content, body.agent_model
    )
    return {"status": "saved"}


@router.delete("/{flow_id}/{agent_key}/draft")
async def discard_draft(
    flow_id:   str,
    agent_key: str,
    request:   Request,
    current_user: AuthUser = Depends(get_current_user),
):
    _validate_key(request, flow_id, agent_key)
    await _db(request).discard_prompt_draft(current_user.sub, flow_id, agent_key)
    return {"status": "discarded"}


# ── Skill-level publish ───────────────────────────────────────────────────────

@router.post("/{flow_id}/publish")
async def publish_skill(
    flow_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    skill      = _skill(request, flow_id)
    agent_keys = skill.manifest.ordered_agent_keys
    result     = await _db(request).publish_skill(current_user.sub, flow_id, agent_keys)
    if not result["published_agents"]:
        raise HTTPException(400, "No unpublished drafts to publish.")
    return result


# ── Snapshots ─────────────────────────────────────────────────────────────────

@router.get("/{flow_id}/snapshots")
async def list_snapshots(
    flow_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    snapshots = await _db(request).list_snapshots(current_user.sub, flow_id)
    return {"flow_id": flow_id, "snapshots": snapshots}


# ── Helper ────────────────────────────────────────────────────────────────────

def _validate_key(request: Request, flow_id: str, agent_key: str) -> None:
    skill = _skill(request, flow_id)
    if agent_key not in skill.agents:
        raise HTTPException(
            404,
            f"Agent key '{agent_key}' not found in skill '{flow_id}'. "
            f"Available: {skill.manifest.ordered_agent_keys}",
        )
