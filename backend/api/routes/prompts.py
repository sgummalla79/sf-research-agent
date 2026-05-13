"""
Agent prompt versioning API.

GET  /api/prompts/{flow_id}                        — all agents + current state
PUT  /api/prompts/{flow_id}/{agent_key}/draft       — save/update draft
DELETE /api/prompts/{flow_id}/{agent_key}/draft     — discard draft
POST /api/prompts/{flow_id}/{agent_key}/publish     — publish draft → new snapshot
GET  /api/prompts/{flow_id}/{agent_key}/history     — published version list
GET  /api/prompts/{flow_id}/snapshots               — flow snapshot timeline
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from flows.registry import get_all_flows, get_flow

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class SaveDraftRequest(BaseModel):
    content: str


def _db(request: Request):
    return request.app.state.db


# ── List all agents for a flow ────────────────────────────────────────────────

@router.get("/{flow_id}")
async def get_flow_prompts(flow_id: str, request: Request):
    try:
        flow = get_flow(flow_id)
    except ValueError:
        raise HTTPException(404, f"Flow '{flow_id}' not found")

    db_rows = await _db(request).get_flow_prompts(flow_id)
    by_key  = {r["agent_key"]: r for r in db_rows}

    agents = []
    for key in flow.agent_keys:
        row = by_key.get(key, {})
        agents.append({
            "agent_key":        key,
            "label":            flow.agent_labels.get(key, key),
            "latest_published": row.get("latest_published"),
            "draft":            row.get("draft"),
        })

    return {"flow_id": flow_id, "agents": agents}


# ── Draft management ──────────────────────────────────────────────────────────

@router.put("/{flow_id}/{agent_key}/draft")
async def save_draft(flow_id: str, agent_key: str, body: SaveDraftRequest, request: Request):
    _validate_key(flow_id, agent_key)
    await _db(request).save_prompt_draft(flow_id, agent_key, body.content)
    return {"status": "saved"}


@router.delete("/{flow_id}/{agent_key}/draft")
async def discard_draft(flow_id: str, agent_key: str, request: Request):
    _validate_key(flow_id, agent_key)
    await _db(request).discard_prompt_draft(flow_id, agent_key)
    return {"status": "discarded"}


# ── Publish ───────────────────────────────────────────────────────────────────

@router.post("/{flow_id}/{agent_key}/publish")
async def publish_agent(flow_id: str, agent_key: str, request: Request):
    _validate_key(flow_id, agent_key)
    try:
        result = await _db(request).publish_prompt(flow_id, agent_key)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


# ── Version history ───────────────────────────────────────────────────────────

@router.get("/{flow_id}/{agent_key}/history")
async def get_history(flow_id: str, agent_key: str, request: Request):
    _validate_key(flow_id, agent_key)
    history = await _db(request).get_agent_version_history(flow_id, agent_key)
    return {"flow_id": flow_id, "agent_key": agent_key, "history": history}


# ── Snapshots ─────────────────────────────────────────────────────────────────

@router.get("/{flow_id}/snapshots")
async def list_snapshots(flow_id: str, request: Request):
    snapshots = await _db(request).list_snapshots(flow_id)
    return {"flow_id": flow_id, "snapshots": snapshots}


# ── Helper ────────────────────────────────────────────────────────────────────

def _validate_key(flow_id: str, agent_key: str) -> None:
    try:
        flow = get_flow(flow_id)
    except ValueError:
        raise HTTPException(404, f"Flow '{flow_id}' not found")
    if agent_key not in flow.agent_keys:
        raise HTTPException(404, f"Agent key '{agent_key}' not in flow '{flow_id}'")
