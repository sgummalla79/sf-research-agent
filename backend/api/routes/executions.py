"""
Execution routes — skill pipeline invocation and control.

POST /api/conversations/{id}/skills/{sid}/invoke  — start pipeline (SSE)
POST /api/executions/{execution_id}/reply         — resume interrupt (SSE)
POST /api/executions/{execution_id}/retry         — retry after model update (SSE)
GET  /api/executions/{execution_id}/stages        — per-stage audit trail
"""

import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel

from state import AgentState
from utils.auth import AuthUser, get_current_user
from framework.defaults import available_providers

log    = logging.getLogger(__name__)
router = APIRouter()

STAGE_LABELS = {
    "intake":    "Intake Agent",
    "discovery": "Discovery Agent",
    "research":  "Research Agent",
    "review":    "Review Agent",
    "approval":  "Approver Gate",
}


def _sse(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


def _get(obj, key, default=None):
    if obj is None:
        return default
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


# ── Request models ────────────────────────────────────────────────────────────

class InvokeRequest(BaseModel):
    brief:               Optional[str] = ""
    original_message:    Optional[str] = ""   # raw user text (with /skill tokens) — saved to DB
    source_type:         Optional[str] = "brief"   # brief | document | image
    uploaded_file_path:  Optional[str] = ""
    uploaded_image_path: Optional[str] = ""
    raw_document_text:   Optional[str] = ""


class ReplyRequest(BaseModel):
    answers: object   # str | list[str]


# ── Core SSE emitter ──────────────────────────────────────────────────────────

async def _stream_graph(
    graph,
    input_,
    config:       dict,
    db,
    execution_id: str,
    conversation_id: str,
) -> AsyncGenerator[str, None]:
    """
    Run the LangGraph pipeline and emit SSE events.
    Persists artifacts after research, records token usage, updates execution status.
    """
    from utils.user_context import _user_keys, get_anthropic_mode, register_execution_keys, unregister_execution_keys

    live_keys = _user_keys.get()
    if live_keys and execution_id:
        register_execution_keys(execution_id, live_keys, get_anthropic_mode())

    config = {**config, "recursion_limit": 100}

    try:
        async for event in graph.astream_events(input_, config, version="v2"):
            name = event.get("name", "")
            kind = event["event"]

            if kind == "on_chain_start" and name in STAGE_LABELS:
                yield _sse("stage_start", {"stage": name, "label": STAGE_LABELS[name]})

            elif kind == "on_chat_model_stream" and \
                    event.get("metadata", {}).get("langgraph_node") != "research":
                chunk = event["data"].get("chunk")
                raw   = getattr(chunk, "content", "") if chunk else ""
                if isinstance(raw, list):
                    text = "".join(
                        (b.get("text", "") if isinstance(b, dict) else getattr(b, "text", ""))
                        for b in raw
                        if (isinstance(b, dict) and b.get("type") == "text")
                        or (hasattr(b, "type") and getattr(b, "type") == "text")
                    )
                elif isinstance(raw, str):
                    text = raw
                else:
                    text = ""
                if text:
                    yield _sse("token", {"content": text})

            elif kind == "on_chain_end" and name in STAGE_LABELS:
                output = event.get("data", {}).get("output") or {}

                if name == "research":
                    doc_version = _get(output, "document_version", 0)
                    doc_draft   = _get(output, "document_draft", "")
                    # Persist artifact
                    if doc_draft and db:
                        try:
                            artifact = await db.artifacts.create(
                                conversation_id = conversation_id,
                                execution_id    = execution_id,
                                content         = doc_draft,
                                version         = doc_version,
                                status          = "pending_review",
                            )
                            yield _sse("document_ready", {
                                "version":     doc_version,
                                "artifact_id": artifact.id,
                                "execution_id": execution_id,
                            })
                        except Exception as exc:
                            log.error("Failed to persist artifact: %s", exc)
                            yield _sse("document_ready", {
                                "version":     doc_version,
                                "execution_id": execution_id,
                            })

                elif name == "review":
                    rr = _get(output, "review_result")
                    yield _sse("review_complete", {
                        "passed":          _get(rr, "passed",          False),
                        "feedback":        _get(rr, "feedback",         ""),
                        "critical_issues": _get(rr, "critical_issues",  []),
                    })

                elif name == "approval":
                    ar = _get(output, "approval_result")
                    yield _sse("approval_complete", {
                        "status":           _get(ar, "status",           "rejected"),
                        "comments":         _get(ar, "comments",          ""),
                        "required_changes": _get(ar, "required_changes",  []),
                    })

                else:
                    yield _sse("stage_end", {"stage": name})

        # ── Stream ended — check interrupt vs complete ─────────────────────
        state = await graph.aget_state(config)

        if db:
            usage_records = (state.values or {}).get("usage_records", [])
            for rec in usage_records:
                try:
                    await db.usage.record(
                        conversation_id = conversation_id,
                        provider        = rec.get("provider") or rec.get("model", "unknown").split("-")[0],
                        model           = rec.get("model", "unknown"),
                        input_tokens    = rec.get("input_tokens", 0),
                        output_tokens   = rec.get("output_tokens", 0),
                    )
                except Exception:
                    pass

        if state.next:
            interrupt_value = None
            for task in state.tasks:
                if task.interrupts:
                    interrupt_value = task.interrupts[0].value
                    break

            if (
                isinstance(interrupt_value, dict)
                and interrupt_value.get("__type") == "confirm_understanding"
            ):
                yield _sse("confirm_understanding", {
                    "content":      interrupt_value["content"],
                    "execution_id": execution_id,
                })
            else:
                questions = (
                    interrupt_value if isinstance(interrupt_value, list)
                    else ([interrupt_value] if interrupt_value else [])
                )
                yield _sse("question", {
                    "questions":    questions,
                    "execution_id": execution_id,
                })
        else:
            values        = state.values
            current_stage = values.get("current_stage", "complete")
            final_status  = current_stage if current_stage in ("complete", "halted", "invalid_input") else "complete"

            if db:
                try:
                    await db.executions.complete(execution_id, final_status)
                except Exception:
                    pass

                # Update latest artifact status
                try:
                    latest = await db.artifacts.get_latest(execution_id)
                    if latest:
                        ar = values.get("approval_result")
                        if ar and hasattr(ar, "status") and ar.status == "approved":
                            await db.artifacts.update_status(latest.id, "approved")
                        elif current_stage == "halted":
                            await db.artifacts.update_status(latest.id, "approval_rejected")
                except Exception:
                    pass

            yield _sse("done", {
                "status":           final_status,
                "document_version": values.get("document_version", 0),
                "revision_count":   values.get("revision_count",   0),
            })

    except Exception as exc:
        import traceback
        msg = str(exc)
        log.error("_stream_graph error: %s\n%s", msg, traceback.format_exc())
        if "API key not configured for" in msg or "No LLM providers are configured" in msg:
            from utils.user_context import connected_providers
            yield _sse("provider_error", {
                "message":        msg,
                "can_smart_pick": bool(connected_providers()),
            })
        else:
            yield _sse("error", {"message": msg})

        if db:
            try:
                await db.executions.complete(execution_id, "halted")
            except Exception:
                pass
    finally:
        if execution_id:
            unregister_execution_keys(execution_id)


# ── Invoke skill pipeline ─────────────────────────────────────────────────────

@router.post("/api/conversations/{conversation_id}/skills/{conversation_skill_id}/invoke")
async def invoke_skill(
    conversation_id:       str,
    conversation_skill_id: str,
    body:                  InvokeRequest,
    request:               Request,
    current_user:          AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    conv_skill = await db.conversations.get_skill(conversation_skill_id)
    if not conv_skill or conv_skill.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Skill snapshot not found.")

    # Guard: only one skill running at a time per conversation
    running = await db.executions.get_running(conversation_id)
    if running:
        raise HTTPException(status_code=409, detail="A skill is already running in this conversation.")

    # Load snapshot agents
    csa_list = await db.conversations.get_skill_agents(conversation_skill_id)
    if not csa_list:
        raise HTTPException(status_code=400, detail="Skill snapshot has no agents.")

    skill = await db.skills.get_by_id(conv_skill.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")

    # Build flow_config and session_agent_config (source: conversation_skill_agents)
    # Slot is included so get_llm_for_agent can smart_pick if provider/model are null
    registry_entry = request.app.state.skill_registry.get(skill.skill_key)
    agent_slot_map = registry_entry.manifest.agent_slot_map if registry_entry else {}

    flow_config:          dict = {}
    session_agent_config: dict = {}
    for csa in csa_list:
        agent = await db.agents.get_by_id(csa.agent_id)
        if agent:
            flow_config[agent.agent_key] = csa.content
            session_agent_config[agent.agent_key] = {
                "provider": csa.provider,
                "model":    csa.model,
                "slot":     agent_slot_map.get(agent.agent_key, "default"),
            }

    # Create execution
    execution    = await db.executions.create(conversation_skill_id)
    execution_id = execution.id

    config = {"configurable": {"thread_id": execution_id}}

    # Save user message — original text (with /skill tokens) if provided, else the brief
    user_content = body.original_message or body.brief
    if user_content:
        await db.messages.create(
            conversation_id = conversation_id,
            execution_id    = execution_id,
            role            = "user",
            content         = user_content,
            message_type    = "chat",
            message_state   = "visible",
        )

    await db.conversations.touch(conversation_id)

    # Auto-title on first invocation (brief becomes the title source)
    if not conv.title and (body.brief or body.raw_document_text):
        from utils.user_context import _user_keys, get_anthropic_mode
        from api.routes.conversations import _auto_title
        title_text  = body.brief or body.raw_document_text or ""
        _cfg        = session_agent_config
        first_agent = next(iter(_cfg.values()), {}) if _cfg else {}
        t_provider  = first_agent.get("provider") or "anthropic"
        t_model     = first_agent.get("model")    or "claude-haiku-4-5-20251001"
        asyncio.create_task(_auto_title(
            db, conversation_id, title_text, t_provider, t_model,
            _user_keys.get() or {}, get_anthropic_mode(),
        ))

    graph = request.app.state.graphs.get(skill.skill_key, request.app.state.graph)

    initial_state = AgentState(
        execution_id          = execution_id,
        conversation_id       = conversation_id,
        conversation_skill_id = conversation_skill_id,
        flow_id               = skill.skill_key,
        flow_config           = flow_config,
        session_agent_config  = session_agent_config,
        source_type           = body.source_type or "brief",
        project_brief         = body.brief or "",
        uploaded_file_path    = body.uploaded_file_path or "",
        uploaded_image_path   = body.uploaded_image_path or "",
        raw_document_text     = body.raw_document_text or "",
    )

    return StreamingResponse(
        _stream_graph(graph, initial_state, config, db, execution_id, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "X-Execution-Id":   execution_id,
        },
    )


# ── Resume interrupt ──────────────────────────────────────────────────────────

@router.post("/api/executions/{execution_id}/reply")
async def reply(
    execution_id: str,
    body:         ReplyRequest,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db        = request.app.state.db
    execution = await db.executions.get_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")

    conv_skill = await db.conversations.get_skill(execution.conversation_skill_id)
    conv       = await db.conversations.get_by_id(conv_skill.conversation_id) if conv_skill else None
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised.")

    skill = await db.skills.get_by_id(conv_skill.skill_id)
    graph = request.app.state.graphs.get(skill.skill_key, request.app.state.graph) if skill else request.app.state.graph

    config = {"configurable": {"thread_id": execution_id}}
    await db.conversations.touch(conv.id)

    return StreamingResponse(
        _stream_graph(graph, Command(resume=body.answers), config, db, execution_id, conv.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Retry ─────────────────────────────────────────────────────────────────────

@router.post("/api/executions/{execution_id}/retry")
async def retry(
    execution_id: str,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    """Re-stream from the last checkpoint. Reads updated model config from snapshot."""
    db        = request.app.state.db
    execution = await db.executions.get_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")

    conv_skill = await db.conversations.get_skill(execution.conversation_skill_id)
    conv       = await db.conversations.get_by_id(conv_skill.conversation_id) if conv_skill else None
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised.")

    # Re-read snapshot (user may have updated model config)
    csa_list      = await db.conversations.get_skill_agents(execution.conversation_skill_id)
    fresh_cfg: dict = {}
    for csa in csa_list:
        agent = await db.agents.get_by_id(csa.agent_id)
        if agent:
            fresh_cfg[agent.agent_key] = {"provider": csa.provider, "model": csa.model}

    skill = await db.skills.get_by_id(conv_skill.skill_id)
    graph = request.app.state.graphs.get(skill.skill_key, request.app.state.graph) if skill else request.app.state.graph

    # Patch the checkpoint with the fresh model config
    config = {"configurable": {"thread_id": execution_id}}
    await graph.aupdate_state(config, {"session_agent_config": fresh_cfg})

    await db.executions.complete(execution_id, "running")   # reset status for retry
    await db.conversations.touch(conv.id)

    return StreamingResponse(
        _stream_graph(graph, None, config, db, execution_id, conv.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Audit trail ───────────────────────────────────────────────────────────────

@router.get("/api/executions/{execution_id}/stages")
async def get_stages(
    execution_id: str,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db     = request.app.state.db
    stages = await db.executions.get_stages(execution_id)
    return {
        "execution_id": execution_id,
        "stages": [
            {
                "id":        s.id,
                "agent_key": s.agent_key,
                "provider":  s.provider,
                "model":     s.model,
                "status":    s.status,
                "ran_at":    s.ran_at,
            }
            for s in stages
        ],
    }
