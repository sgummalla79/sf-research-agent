"""
Agent prompt versioning API.

GET  /api/prompts/{flow_id}                        — all agents + current state
PUT  /api/prompts/{flow_id}/{agent_key}/draft       — save/update draft
DELETE /api/prompts/{flow_id}/{agent_key}/draft     — discard draft
POST /api/prompts/{flow_id}/{agent_key}/publish     — publish draft → new snapshot
GET  /api/prompts/{flow_id}/{agent_key}/history     — published version list
GET  /api/prompts/{flow_id}/snapshots               — flow snapshot timeline
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from framework.registry import SkillNotFoundError

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class SaveDraftRequest(BaseModel):
    content:      str
    agent_model: Optional[dict] = None   # {"provider": "...", "model": "..."} or null


def _db(request: Request):
    return request.app.state.db


def _skill(request: Request, flow_id: str):
    try:
        return request.app.state.skill_registry.get(flow_id)
    except SkillNotFoundError:
        raise HTTPException(404, f"Skill '{flow_id}' not found")


# ── List all agents for a flow ────────────────────────────────────────────────

@router.get("/{flow_id}")
async def get_flow_prompts(flow_id: str, request: Request):
    skill   = _skill(request, flow_id)
    db_rows = await _db(request).get_flow_prompts(flow_id)
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
    return {"flow_id": flow_id, "agents": agents}


# ── Draft management ──────────────────────────────────────────────────────────

@router.put("/{flow_id}/{agent_key}/draft")
async def save_draft(flow_id: str, agent_key: str, body: SaveDraftRequest, request: Request):
    _validate_key(request, flow_id, agent_key)
    await _db(request).save_prompt_draft(flow_id, agent_key, body.content, body.agent_model)
    return {"status": "saved"}


@router.delete("/{flow_id}/{agent_key}/draft")
async def discard_draft(flow_id: str, agent_key: str, request: Request):
    _validate_key(request, flow_id, agent_key)
    await _db(request).discard_prompt_draft(flow_id, agent_key)
    return {"status": "discarded"}


# ── Publish ───────────────────────────────────────────────────────────────────

@router.post("/{flow_id}/{agent_key}/publish")
async def publish_agent(flow_id: str, agent_key: str, request: Request):
    _validate_key(request, flow_id, agent_key)
    try:
        result = await _db(request).publish_prompt(flow_id, agent_key)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


# ── Version history ───────────────────────────────────────────────────────────

@router.get("/{flow_id}/{agent_key}/history")
async def get_history(flow_id: str, agent_key: str, request: Request):
    _validate_key(request, flow_id, agent_key)
    history = await _db(request).get_agent_version_history(flow_id, agent_key)
    return {"flow_id": flow_id, "agent_key": agent_key, "history": history}


# ── Snapshots ─────────────────────────────────────────────────────────────────

@router.get("/{flow_id}/snapshots")
async def list_snapshots(flow_id: str, request: Request):
    snapshots = await _db(request).list_snapshots(flow_id)
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
