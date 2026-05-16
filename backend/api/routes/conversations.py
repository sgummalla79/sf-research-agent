"""
Conversation routes.

POST   /api/conversations                       — create conversation
GET    /api/conversations                       — list user's conversations
GET    /api/conversations/{id}                  — get with messages
PATCH  /api/conversations/{id}                  — rename
DELETE /api/conversations/{id}                  — delete
POST   /api/conversations/{id}/message          — regular chat (SSE)
POST   /api/conversations/{id}/skills           — add skill → creates snapshot
DELETE /api/conversations/{id}/skills/{sid}     — remove skill
GET    /api/conversations/{id}/skills/{sid}/config   — view snapshot model config
PATCH  /api/conversations/{id}/skills/{sid}/config   — update snapshot model config
"""

import asyncio
import json
import logging
from typing import Optional

async def _generate_title(text: str, provider: str, model: str) -> str:
    """Use the conversation's LLM to produce a short 4-7 word title."""
    from utils.llm_factory import build_llm
    from langchain_core.messages import HumanMessage
    try:
        llm  = build_llm(provider, model)
        resp = await llm.ainvoke([HumanMessage(content=(
            "Write a short 4-7 word title for this conversation. "
            "No quotes, no punctuation at end, title case. "
            f"It starts with: {text[:300]}"
        ))])
        title = resp.content.strip().strip("\"'").rstrip(".")
        return title[:100] if title else text[:60]
    except Exception:
        return text[:60]

async def _auto_title(db, conversation_id: str, text: str, provider: str, model: str,
                      user_keys: dict, anthropic_mode: str) -> None:
    """Fire-and-forget — generate and save a title for a new conversation."""
    try:
        from utils.user_context import set_user_context
        set_user_context(user_keys, anthropic_mode)
        title = await _generate_title(text, provider, model)
        await db.conversations.rename(conversation_id, title)
    except Exception as exc:
        log.debug("Auto-title failed for %s: %s", conversation_id, exc)

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.auth import AuthUser, get_current_user

log    = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations")


def _sse(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


# ── Request models ────────────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    title:         Optional[str] = None
    chat_provider: Optional[str] = "anthropic"
    chat_model:    Optional[str] = "claude-sonnet-4-6"


class ChatMessageRequest(BaseModel):
    text:          str
    chat_provider: Optional[str] = None   # override conversation default
    chat_model:    Optional[str] = None


class AddSkillRequest(BaseModel):
    skill_id: str   # the skill_key (e.g. "architect")


class RenameRequest(BaseModel):
    title: str


class UpdateModelConfigRequest(BaseModel):
    agents: list[dict]   # [{agent_id, provider, model}]


# ── Conversation CRUD ─────────────────────────────────────────────────────────

@router.post("")
async def create_conversation(
    body:         CreateConversationRequest,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.create(
        user_id       = current_user.sub,
        title         = body.title,
        chat_provider = body.chat_provider,
        chat_model    = body.chat_model,
    )
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at}


@router.get("")
async def list_conversations(
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db    = request.app.state.db
    convs = await db.conversations.list_for_user(current_user.sub)

    def _fmt(c):
        return {
            "id":            c.id,
            "title":         c.title,
            "chat_provider": c.chat_provider,
            "chat_model":    c.chat_model,
            "created_at":    c.created_at,
            "last_modified": c.last_modified,
            "pinned":        c.pinned,
            "pinned_at":     c.pinned_at,
        }

    pinned = sorted(
        [_fmt(c) for c in convs if c.pinned],
        key=lambda x: x["pinned_at"] or "",
        reverse=True,
    )
    recent = [_fmt(c) for c in convs if not c.pinned]
    return {"pinned": pinned, "recent": recent}


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    request:         Request,
    current_user:    AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = await db.messages.list_for_conversation(conversation_id, visible_only=False)
    skills   = await db.conversations.get_skills_for_conversation(conversation_id)

    return {
        "id":            conv.id,
        "title":         conv.title,
        "chat_provider": conv.chat_provider,
        "chat_model":    conv.chat_model,
        "created_at":    conv.created_at,
        "last_modified": conv.last_modified,
        "messages": [
            {
                "id":            m.id,
                "role":          m.role,
                "content":       m.content,
                "message_type":  m.message_type,
                "message_state": m.message_state,
                "artifact_id":   m.artifact_id,
                "execution_id":  m.execution_id,
                "created_at":    m.created_at,
            }
            for m in messages
        ],
        "skills": [
            {"id": s.id, "skill_id": s.skill_id, "added_at": s.added_at}
            for s in skills
        ],
    }


@router.patch("/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    body:            RenameRequest,
    request:         Request,
    current_user:    AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    await db.conversations.rename(conversation_id, body.title)
    return {"ok": True}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    request:         Request,
    current_user:    AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    await db.conversations.archive(conversation_id)
    return {"ok": True}


# ── Regular chat message (SSE) ────────────────────────────────────────────────

@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    body:            ChatMessageRequest,
    request:         Request,
    current_user:    AuthUser = Depends(get_current_user),
):
    """Stream a regular (non-pipeline) chat response."""
    from langchain_core.messages import HumanMessage as HM, AIMessage, SystemMessage
    from utils.llm_factory import build_llm
    from utils.pricing import usage_record
    from utils.user_api_keys import get_key

    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Check no skill is currently running
    running = await db.executions.get_running(conversation_id)
    if running:
        raise HTTPException(status_code=409, detail="A skill is currently running — wait for it to complete.")

    provider = body.chat_provider or conv.chat_provider or "anthropic"
    model    = body.chat_model    or conv.chat_model    or "claude-sonnet-4-6"

    # Save user message
    await db.messages.create(
        conversation_id = conversation_id,
        role            = "user",
        content         = body.text,
        message_type    = "chat",
        message_state   = "visible",
    )
    await db.conversations.touch(conversation_id)

    # Auto-title on first message
    if not conv.title:
        from utils.user_context import _user_keys, get_anthropic_mode
        asyncio.create_task(_auto_title(
            db, conversation_id, body.text, provider, model,
            _user_keys.get() or {}, get_anthropic_mode(),
        ))

    # Load recent conversation history
    history = await db.messages.list_for_conversation(conversation_id, limit=50, visible_only=False)
    lc_msgs = []
    for m in history[:-1]:   # exclude the message we just saved — will be added as HM below
        if m.role == "user":
            lc_msgs.append(HM(content=m.content or ""))
        else:
            lc_msgs.append(AIMessage(content=m.content or ""))
    lc_msgs.append(HM(content=body.text))

    llm = build_llm(provider, model)

    async def _stream():
        full_response  = ""
        input_tokens   = 0
        output_tokens  = 0
        try:
            async for chunk in llm.astream(lc_msgs):
                text = chunk.content if isinstance(chunk.content, str) else ""
                if text:
                    full_response += text
                    yield _sse("token", {"content": text})
                # Capture token counts from the last chunk's usage metadata
                meta = getattr(chunk, "usage_metadata", None) or {}
                if meta.get("input_tokens"):  input_tokens  = meta["input_tokens"]
                if meta.get("output_tokens"): output_tokens = meta["output_tokens"]

            # Save assistant message
            await db.messages.create(
                conversation_id = conversation_id,
                role            = "assistant",
                content         = full_response,
                message_type    = "chat",
                message_state   = "visible",
            )
            await db.usage.record(conversation_id, provider, model, input_tokens, output_tokens)

            yield _sse("done", {"status": "complete"})
        except Exception as exc:
            log.error("Chat stream error: %s", exc)
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Skill snapshot management ─────────────────────────────────────────────────

@router.post("/{conversation_id}/skills")
async def add_skill(
    conversation_id: str,
    body:            AddSkillRequest,
    request:         Request,
    current_user:    AuthUser = Depends(get_current_user),
):
    """Add a skill to a conversation and create a frozen snapshot."""
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    skill = await db.skills.get_by_key(body.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{body.skill_id}' not found.")

    installed = await db.user_skills.is_installed(current_user.sub, skill.id)
    if not installed:
        raise HTTPException(status_code=400, detail=f"Skill '{body.skill_id}' is not installed.")

    # Build snapshot from current published version (content + model come from version record)
    user_agents = await db.user_agents.get_for_skill(current_user.sub, skill.id)
    agents_data = []
    for ua in user_agents:
        ver = await db.user_agents.get_current_version_record(ua.id)
        agents_data.append({
            "agent_id": ua.agent_id,
            "version":  ua.current_version,
            "content":  ver.content  if ver else "",
            "provider": ver.provider_to_use if ver else None,
            "model":    ver.model_to_use    if ver else None,
        })

    conv_skill = await db.conversations.add_skill(conversation_id, skill.id, agents_data)
    return {
        "ok":               True,
        "conversation_skill_id": conv_skill.id,
        "skill_id":         body.skill_id,
        "agents_count":     len(agents_data),
    }


@router.delete("/{conversation_id}/skills/{conversation_skill_id}")
async def remove_skill(
    conversation_id:       str,
    conversation_skill_id: str,
    request:               Request,
    current_user:          AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    await db.conversations.remove_skill(conversation_skill_id)
    return {"ok": True}


@router.get("/{conversation_id}/skills/{conversation_skill_id}/config")
async def get_skill_config(
    conversation_id:       str,
    conversation_skill_id: str,
    request:               Request,
    current_user:          AuthUser = Depends(get_current_user),
):
    """Return current model config for each agent in this conversation's skill snapshot."""
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    agents = await db.conversations.get_skill_agents(conversation_skill_id)
    return {
        "conversation_skill_id": conversation_skill_id,
        "agents": [
            {
                "id":        a.id,
                "agent_id":  a.agent_id,
                "version":   a.version,
                "provider":  a.provider,
                "model":     a.model,
            }
            for a in agents
        ],
    }


@router.patch("/{conversation_id}/skills/{conversation_skill_id}/config")
async def update_skill_config(
    conversation_id:       str,
    conversation_skill_id: str,
    body:                  UpdateModelConfigRequest,
    request:               Request,
    current_user:          AuthUser = Depends(get_current_user),
):
    """Update provider/model on conversation_skill_agents rows (models only, content frozen)."""
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    for item in body.agents:
        await db.conversations.update_agent_model(
            item["id"], item.get("provider"), item.get("model")
        )

    return {"ok": True, "updated": len(body.agents)}


# ── Pin / unpin ───────────────────────────────────────────────────────────────

@router.post("/{conversation_id}/pin")
async def pin_conversation(
    conversation_id: str,
    request:         Request,
    current_user:    AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    await db.conversations.pin(conversation_id)
    return {"ok": True}


@router.delete("/{conversation_id}/pin")
async def unpin_conversation(
    conversation_id: str,
    request:         Request,
    current_user:    AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    conv = await db.conversations.get_by_id(conversation_id)
    if not conv or conv.user_id != current_user.sub:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    await db.conversations.unpin(conversation_id)
    return {"ok": True}
