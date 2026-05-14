"""
Chat routes — three POST endpoints, all return an SSE stream.

POST /api/chat/start              — new session from a typed brief
POST /api/chat/upload             — new session from an uploaded document (PDF/DOCX/TXT/MD)
POST /api/chat/reply/{session_id} — resumes after user answers a discovery question

SSE event format (newline-delimited JSON after "data: "):
  stage_start   {"stage": "discovery", "label": "Discovery Agent"}
  token         {"content": "..."}          ← LLM token, streamed in real-time
  stage_end     {"stage": "discovery"}
  question      {"content": "What org type are you targeting?"}   ← graph paused
  done          {"status": "complete|halted", "document_version": 2}
  error         {"message": "..."}
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from pydantic import BaseModel
from api.schemas import ReplyRequest, StartRequest
from config import MAX_FILE_SIZE_MB
from state import AgentState
from utils.agent_config import get_agent_config
from chat_models import CHAT_DEFAULT_MODEL
from framework.defaults import SMART_SLOT_DEFAULTS
from framework.registry import SkillNotFoundError
from utils.file_parser import extract_text, SUPPORTED_EXTENSIONS
from utils.file_storage import save_upload
from utils.auth import AuthUser, get_current_user

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALL_ACCEPTED     = SUPPORTED_EXTENSIONS | IMAGE_EXTENSIONS

router = APIRouter(prefix="/api/chat")


def _get(obj, key, default=None):
    """Safely read from a Pydantic model or dict."""
    if obj is None:
        return default
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


async def _generate_title(text: str) -> str:
    """
    Call Claude Haiku to produce a concise 4-7 word session title.
    Runs in background so it never adds latency to session start.
    """
    import anthropic
    from config import CLAUDE_HAIKU_MODEL
    from utils.api_keys import get_key

    client = anthropic.AsyncAnthropic(api_key=get_key("anthropic"))
    resp   = await client.messages.create(
        model=CLAUDE_HAIKU_MODEL,
        max_tokens=25,
        messages=[{
            "role": "user",
            "content": (
                "Write a short 4-7 word title for this architecture session. "
                "No quotes, no punctuation at end, title case. "
                "Examples: 'Service Cloud Migration for Retail', "
                "'API Token Security Pattern Review', "
                "'Data Cloud Identity Resolution Design'.\n\n"
                f"Session context: {text[:500]}\n\nTitle:"
            ),
        }],
    )
    title = resp.content[0].text.strip().strip("\"'").rstrip(".")
    return title[:100] if title else text[:80]


async def _save_title(db, session_id: str, text: str, user_id: str) -> None:
    """Generate a title and persist it — runs as a fire-and-forget background task."""
    try:
        title = await _generate_title(text)
        await db.update_session_title(session_id, title)
    except Exception:
        pass   # keep the raw snippet if generation fails


def _infer_stage(content: str) -> str | None:
    """
    Fallback stage detection from message content for sessions created before
    we added name= to AIMessages. New sessions use msg.name directly.
    """
    if content.startswith("[Researcher]"): return "researcher"
    if content.startswith("[Reviewer]"):   return "reviewer"
    if content.startswith("[Approver]"):   return "approver"
    return None


# Human-readable labels for each graph node
STAGE_LABELS = {
    "intake":    "Intake Agent",
    "discovery": "Discovery Agent",
    "research":  "Research Agent",
    "review":    "Review Agent",
    "approval":  "Approver Gate",
}


def _sse(event_type: str, payload: dict) -> str:
    """Format a single SSE message."""
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


def _flush_usage(db, config: dict, output: dict, user_id: str = "") -> None:
    """Fire-and-forget: persist usage records accumulated so far so the
    frontend status bar can show live cost after each major stage."""
    import asyncio
    records = output.get("usage_records") if isinstance(output, dict) else None
    if records:
        thread_id = config["configurable"]["thread_id"]
        asyncio.create_task(db.save_usage_records(user_id, thread_id, records))


async def _stream_graph(graph, input_, config, db=None, user_id: str = "") -> AsyncGenerator[str, None]:
    """
    Run the graph with astream_events and translate LangGraph events into SSE messages.
    After the stream ends, inspect state to detect interrupt vs completion.
    """
    try:
        async for event in graph.astream_events(input_, config, version="v2"):
            name = event.get("name", "")
            kind = event["event"]

            # Node started
            if kind == "on_chain_start" and name in STAGE_LABELS:
                yield _sse("stage_start", {
                    "stage": name,
                    "label": STAGE_LABELS[name],
                })

            # LLM token streaming — suppressed for research (document shown via card).
            # For model stream events, name = LLM model name (e.g. "ChatAnthropic"),
            # NOT the node name. The actual node is in metadata.langgraph_node.
            elif kind == "on_chat_model_stream" and \
                    event.get("metadata", {}).get("langgraph_node") != "research":
                chunk = event["data"].get("chunk")
                raw = getattr(chunk, "content", "") if chunk else ""

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

            # Node finished — emit specialised events for researcher/reviewer/approver
            elif kind == "on_chain_end" and name in STAGE_LABELS:
                output = event.get("data", {}).get("output") or {}

                if name == "research":
                    yield _sse("document_ready", {
                        "version":    _get(output, "document_version", 0),
                        "session_id": config["configurable"]["thread_id"],
                    })
                    if db:
                        _flush_usage(db, config, output, user_id)

                elif name == "review":
                    rr = _get(output, "review_result")
                    yield _sse("review_complete", {
                        "passed":          _get(rr, "passed",          False),
                        "feedback":        _get(rr, "feedback",         ""),
                        "critical_issues": _get(rr, "critical_issues",  []),
                    })
                    if db:
                        _flush_usage(db, config, output, user_id)

                elif name == "approval":
                    ar = _get(output, "approval_result")
                    yield _sse("approval_complete", {
                        "status":           _get(ar, "status",           "rejected"),
                        "comments":         _get(ar, "comments",          ""),
                        "required_changes": _get(ar, "required_changes",  []),
                    })
                    if db:
                        _flush_usage(db, config, output, user_id)

                else:
                    yield _sse("stage_end", {"stage": name})

        # ── Stream ended — persist token usage, then check interrupt/complete ──
        state = await graph.aget_state(config)

        if db:
            records = (state.values or {}).get("usage_records", [])
            if records:
                thread_id = config["configurable"]["thread_id"]
                try:
                    await db.save_usage_records(user_id, thread_id, records)
                except Exception:
                    pass  # never let usage errors break the SSE stream

        if state.next:
            # Graph is interrupted — determine interrupt type from the value.
            interrupt_value = None
            for task in state.tasks:
                if task.interrupts:
                    interrupt_value = task.interrupts[0].value
                    break

            sid = config["configurable"]["thread_id"]

            if (
                isinstance(interrupt_value, dict)
                and interrupt_value.get("__type") == "confirm_understanding"
            ):
                # Intake confirmation — show extracted understanding, wait for ack
                yield _sse("confirm_understanding", {
                    "content":    interrupt_value["content"],
                    "session_id": sid,
                })
            else:
                # Discovery question group — list of question strings
                questions = (
                    interrupt_value if isinstance(interrupt_value, list)
                    else ([interrupt_value] if interrupt_value else [])
                )
                yield _sse("question", {
                    "questions":  questions,
                    "session_id": sid,
                })
        else:
            values = state.values
            yield _sse("done", {
                "status": values.get("current_stage", "complete"),
                "document_version": values.get("document_version", 0),
                "revision_count": values.get("revision_count", 0),
            })

    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


@router.post("/start")
async def start_chat(body: StartRequest, request: Request, current_user: AuthUser = Depends(get_current_user)):
    db              = request.app.state.db
    skill_registry  = request.app.state.skill_registry
    graphs          = request.app.state.graphs
    session_id = str(uuid.uuid4())
    config     = {"configurable": {"thread_id": session_id}}

    # Save raw snippet immediately; replace with smart title in background
    await db.record_session(
        session_id, current_user.sub,
        brief_snippet=body.brief[:80].replace('\n', ' '),
        session_type=body.session_type,
        chat_model=body.chat_model or CHAT_DEFAULT_MODEL,
        chat_provider=body.chat_provider,
    )
    asyncio.create_task(_save_title(db, session_id, body.brief, current_user.sub))

    agent_cfg = get_agent_config()

    # ── Resolve graph + flow_config from skill registry ──────────────────────
    flow_config:           dict     = {}
    flow_snapshot_id:      int|None = None
    flow_snapshot_version: int|None = None

    if body.session_type == "agent_flow":
        try:
            skill    = skill_registry.get(body.flow_id)
            snapshot = await db.get_latest_snapshot(current_user.sub, body.flow_id)
            if snapshot:
                db_prompts            = await db.get_prompt_content_for_snapshot(current_user.sub, body.flow_id, snapshot)
                flow_config           = {**skill.all_agent_prompts, **db_prompts}
                flow_snapshot_id      = snapshot["id"]
                flow_snapshot_version = snapshot["snapshot_version"]
                # Merge per-agent model overrides into agent_cfg (trump global defaults)
                model_overrides = await db.get_model_config_for_snapshot(current_user.sub, body.flow_id, snapshot)
                slot_map        = skill.manifest.agent_slot_map
                for agent_key, model_cfg in model_overrides.items():
                    slot = slot_map.get(agent_key)
                    if slot and model_cfg:
                        agent_cfg[slot] = model_cfg
            else:
                flow_config = dict(skill.all_agent_prompts)
        except SkillNotFoundError:
            pass  # unknown skill → empty flow_config, agents use defaults

    # Fill any slots used by this skill that are missing from agent_cfg with smart defaults
    if body.session_type == "agent_flow":
        try:
            _skill = skill_registry.get(body.flow_id)
            for slot in set(_skill.manifest.agent_slot_map.values()):
                if slot not in agent_cfg and slot in SMART_SLOT_DEFAULTS:
                    agent_cfg[slot] = SMART_SLOT_DEFAULTS[slot]
        except Exception:
            pass

    # Save merged agent_cfg (global defaults + per-agent overrides + smart defaults)
    await db.save_config(current_user.sub, f"session_agent_config_{session_id}", __import__("json").dumps(agent_cfg))

    # Pick the compiled graph: skill-specific for agent flows, fallback for chat
    graph = (
        graphs.get(body.flow_id, request.app.state.graph)
        if body.session_type == "agent_flow"
        else request.app.state.graph
    )

    # For free-form chat sessions seed the brief as the first HumanMessage
    # so run_chat always receives a non-empty messages list
    from langchain_core.messages import HumanMessage as _HM
    seed_messages = [_HM(content=body.brief)] if body.session_type == "chat" else []

    initial_state = AgentState(
        session_id=session_id,
        project_brief=body.brief,
        session_agent_config=agent_cfg,
        session_type=body.session_type,
        flow_id=body.flow_id,
        flow_config=flow_config,
        flow_snapshot_id=flow_snapshot_id,
        flow_snapshot_version=flow_snapshot_version,
        chat_model=body.chat_model or CHAT_DEFAULT_MODEL,
        chat_provider=body.chat_provider,
        extended_thinking=body.extended_thinking,
        messages=seed_messages,
    )

    return StreamingResponse(
        _stream_graph(graph, initial_state, config, db, user_id=current_user.sub),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )


@router.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...), current_user: AuthUser = Depends(get_current_user)):
    """
    Accept a PDF, DOCX, TXT, or MD file.
    1. Enforce file type and size limits.
    2. Save the original file to local storage (audit trail).
    3. Extract text immediately — graph never needs the file again.
    4. Start the SSE stream exactly like /start.
    """
    graph = request.app.state.graph

    from pathlib import Path
    suffix = Path(file.filename or "").suffix.lower()

    # ── 1. Validate file type ─────────────────────────────────────────────────
    if suffix not in ALL_ACCEPTED:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Documents: {', '.join(sorted(SUPPORTED_EXTENSIONS))}  "
                f"Images: {', '.join(sorted(IMAGE_EXTENSIONS))}"
            ),
        )

    is_image = suffix in IMAGE_EXTENSIONS

    # ── 2. Enforce size limit ─────────────────────────────────────────────────
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    content   = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit ({len(content) // (1024 * 1024)} MB received).",
        )

    # ── 3. Save to local filesystem ───────────────────────────────────────────
    saved_path = save_upload(file.filename, content)

    # ── 4. For documents: extract text now. For images: intake agent uses vision.
    raw_text = ""
    if not is_image:
        try:
            raw_text = extract_text(file.filename, content)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    # ── 5. Start graph ────────────────────────────────────────────────────────
    db         = request.app.state.db
    session_id = str(uuid.uuid4())
    config     = {"configurable": {"thread_id": session_id}}

    # For documents: title from extracted text. For images: title from filename.
    title_source = raw_text[:500] if (not is_image and raw_text) else f"Architecture diagram: {file.filename}"
    await db.record_session(session_id, current_user.sub, f"{'🖼' if is_image else '📄'} {file.filename}"[:80])
    asyncio.create_task(_save_title(db, session_id, title_source, current_user.sub))

    agent_cfg = get_agent_config()
    await db.save_config(current_user.sub, f"session_agent_config_{session_id}", __import__("json").dumps(agent_cfg))

    initial_state = AgentState(
        session_id=session_id,
        source_type="image" if is_image else "document",
        uploaded_file_path="" if is_image else saved_path,
        uploaded_image_path=saved_path if is_image else "",
        raw_document_text=raw_text,
        session_agent_config=agent_cfg,
    )

    return StreamingResponse(
        _stream_graph(graph, initial_state, config, db, user_id=current_user.sub),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )


@router.get("/session-config/{session_id}")
async def get_session_config(session_id: str, request: Request, current_user: AuthUser = Depends(get_current_user)) -> dict:
    """Return the LLM config that was locked when this session started (read-only)."""
    import json
    db  = request.app.state.db
    raw = await db.get_config(current_user.sub, f"session_agent_config_{session_id}")
    if not raw:
        return {"config": {}}
    try:
        return {"config": json.loads(raw)}
    except Exception:
        return {"config": {}}


@router.get("/document/{session_id}")
async def get_document(session_id: str, request: Request, current_user: AuthUser = Depends(get_current_user)):
    """Fetch the current document draft for a session (used by the document panel)."""
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    state  = await graph.aget_state(config)
    return {
        "content": state.values.get("document_draft", ""),
        "version": state.values.get("document_version", 0),
    }


async def _retitle_session(db, graph, session_id: str, user_id: str) -> None:
    """
    For sessions without a title (NULL brief_snippet), read the LangGraph state
    to get project_brief and generate a smart title in the background.
    Called automatically when the sessions panel is opened.
    """
    try:
        config = {"configurable": {"thread_id": session_id}}
        state  = await graph.aget_state(config)
        brief  = (state.values.get("project_brief") or "").strip()

        # Fall back to first human message if brief isn't set yet
        if not brief:
            for msg in state.values.get("messages", []):
                from langchain_core.messages import HumanMessage as HM
                if isinstance(msg, HM) and isinstance(msg.content, str) and msg.content.strip():
                    brief = msg.content.strip()
                    break

        if brief:
            await _save_title(db, session_id, brief, user_id)
        else:
            await db.update_session_title(session_id, "Architecture Session")
    except Exception:
        pass


@router.get("/sessions")
async def list_sessions(request: Request, current_user: AuthUser = Depends(get_current_user)):
    """
    Returns {pinned:[...], recent:[...]} sorted correctly.
    Fires background retitling for untitled sessions.
    """
    db    = request.app.state.db
    graph = request.app.state.graph
    data  = await db.list_sessions(current_user.sub)

    all_sessions = data["pinned"] + data["recent"]
    untitled     = [s for s in all_sessions if not s.get("brief_snippet")]
    for s in untitled[:10]:
        asyncio.create_task(_retitle_session(db, graph, s["thread_id"], current_user.sub))

    return data


@router.get("/session/{session_id}/restore")
async def restore_session(session_id: str, request: Request, current_user: AuthUser = Depends(get_current_user)):
    """Load a previous session so the frontend can reconstruct the chat."""
    from langchain_core.messages import HumanMessage as HM

    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}

    try:
        state = await graph.aget_state(config)
    except Exception:
        return {"error": "Session not found"}

    values = state.values

    # Serialise messages to plain dicts, preserving the agent stage name
    messages = []
    for msg in values.get("messages", []):
        content = msg.content
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")
                for b in content
                if (isinstance(b, dict) and b.get("type") == "text")
                or (hasattr(b, "type") and getattr(b, "type") == "text")
            )
        # Use msg.name if set (new sessions); fall back to content-based detection
        # for sessions created before we added name= to AIMessages.
        stage = getattr(msg, "name", None) or _infer_stage(content or "")
        messages.append({
            "role":    "user" if isinstance(msg, HM) else "agent",
            "content": content or "",
            "type":    "text",
            "stage":   stage,
        })

    # Detect pending interrupt
    pending_questions = []
    pending_confirmation = None
    if state.next:
        for task in state.tasks:
            if task.interrupts:
                val = task.interrupts[0].value
                if isinstance(val, dict) and val.get("__type") == "confirm_understanding":
                    pending_confirmation = val["content"]
                elif isinstance(val, list):
                    pending_questions = val
                elif val:
                    pending_questions = [val]
                break

    raw_stage = values.get("current_stage") or ""
    # Read session metadata from agent_sessions (source of truth for immutable fields)
    db          = request.app.state.db
    session_row = await db._fetchone(
        f"SELECT session_type, chat_model, chat_provider FROM agent_sessions WHERE thread_id = {db._p()}",
        (session_id,),
    )
    session_type  = (session_row[0] if session_row else None) or "agent_flow"
    session_model = session_row[1] if session_row else None
    session_prov  = (session_row[2] if session_row else None) or "anthropic"
    if not state.next:
        # Graph terminated — keep 'chat' and known terminal stages as-is;
        # anything else (e.g. mid-pipeline crash) normalises to 'complete'.
        terminal_stages = {"complete", "halted", "invalid_input", "chat"}
        resolved_stage  = raw_stage if raw_stage in terminal_stages else "complete"
    else:
        resolved_stage = raw_stage

    return {
        "session_id":           session_id,
        "session_type":         session_type,
        "chat_model":           session_model,
        "chat_provider":        session_prov,
        "current_stage":        resolved_stage,
        "document_version":     values.get("document_version", 0),
        "project_brief":        (values.get("project_brief") or "")[:200],
        "messages":             messages,
        "pending_questions":    pending_questions,
        "pending_confirmation": pending_confirmation,
        "has_document":         bool(values.get("document_draft")),
    }


@router.post("/retry/{session_id}")
async def retry_chat(session_id: str, request: Request, current_user: AuthUser = Depends(get_current_user)):
    """
    Re-stream the graph from its last LangGraph checkpoint.
    Use this after a connection error or exhausted LLM retries.
    Safe to call multiple times — LangGraph resumes from the last
    completed node, so no work is duplicated or lost.
    """
    graph  = request.app.state.graph
    db     = request.app.state.db
    config = {"configurable": {"thread_id": session_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Session not found.")

    current_stage = (state.values or {}).get("current_stage", "")
    if current_stage in ("complete", "halted", "invalid_input"):
        raise HTTPException(status_code=400, detail="Session is already finished — nothing to retry.")

    # Only block if there is an actual human-in-the-loop interrupt pending.
    # state.next being non-empty is NOT enough — it is also truthy when a node
    # errored mid-run and LangGraph still has the node queued for re-execution.
    has_interrupt = any(getattr(t, "interrupts", None) for t in (state.tasks or []))
    if has_interrupt:
        raise HTTPException(
            status_code=400,
            detail="Session is waiting for your input — answer the pending question instead of retrying.",
        )

    asyncio.create_task(db.update_last_modified(session_id))

    return StreamingResponse(
        _stream_graph(graph, None, config, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/reply/{session_id}")
async def reply_chat(session_id: str, body: ReplyRequest, request: Request, current_user: AuthUser = Depends(get_current_user)):
    graph = request.app.state.graph
    db    = request.app.state.db
    config = {"configurable": {"thread_id": session_id}}

    # Bump last_modified so the session surfaces at top of the recent list
    asyncio.create_task(db.update_last_modified(session_id))

    return StreamingResponse(
        _stream_graph(graph, Command(resume=body.answers), config, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Post-completion chat ──────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    text:          str
    chat_model:    str = "claude-sonnet-4-6"
    chat_provider: str = "anthropic"


@router.post("/message/{session_id}")
async def post_completion_message(session_id: str, body: MessageRequest, request: Request, current_user: AuthUser = Depends(get_current_user)):
    """
    Follow-up chat on a completed session.
    Streams a direct LLM response with the approved document as system context.
    No graph is invoked — the pipeline is done.
    """
    from langchain_core.messages import SystemMessage, HumanMessage as HM
    from utils.llm_factory import build_llm

    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Session not found.")

    document = state.values.get("document_draft", "")
    system   = (
        "You are a technical architecture assistant. The user has just completed a full "
        "architecture engagement and the document has been approved. Help them discuss, "
        "clarify, or extend it.\n\n"
        f"Approved architecture document:\n\n{document}"
    )

    llm = build_llm(body.chat_provider, body.chat_model).bind(
        max_tokens=4096,
        streaming=True,
    )

    async def _stream():
        try:
            async for chunk in llm.astream([
                SystemMessage(content=system),
                HM(content=body.text),
            ]):
                text = chunk.content if isinstance(chunk.content, str) else ""
                if text:
                    yield _sse("token", {"content": text})
            yield _sse("done", {"status": "complete"})
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Regular chat continuation ─────────────────────────────────────────────────

@router.post("/continue/{session_id}")
async def continue_chat(session_id: str, body: MessageRequest, request: Request, current_user: AuthUser = Depends(get_current_user)):
    """
    Continue a regular chat session — adds the user message to the graph
    state and re-invokes the graph so conversation history is preserved.
    """
    from langchain_core.messages import HumanMessage as _HM

    graph  = request.app.state.graph
    db     = request.app.state.db
    config = {"configurable": {"thread_id": session_id}}

    await db.update_last_modified(session_id)

    return StreamingResponse(
        _stream_graph(
            graph,
            {"messages": [_HM(content=body.text)]},
            config,
            db,
            user_id=current_user.sub,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Session fork ──────────────────────────────────────────────────────────────

class ForkRequest(BaseModel):
    flow_id:           str
    chat_model:        str  = "claude-sonnet-4-6"
    chat_provider:     str  = "anthropic"
    extended_thinking: bool = False


@router.post("/fork/{session_id}")
async def fork_session(session_id: str, body: ForkRequest, request: Request, current_user: AuthUser = Depends(get_current_user)):
    """
    Start a new session pre-seeded with a completed session's document.
    The new skill's full pipeline runs with the existing document as context.
    """
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry
    graphs         = request.app.state.graphs
    graph          = request.app.state.graph

    config = {"configurable": {"thread_id": session_id}}
    state  = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Original session not found.")

    document    = state.values.get("document_draft", "")
    doc_version = state.values.get("document_version", 1)
    orig_brief  = (state.values.get("project_brief") or "")[:300]

    new_session_id = str(uuid.uuid4())
    new_config     = {"configurable": {"thread_id": new_session_id}}

    await db.record_session(
        new_session_id, current_user.sub,
        brief_snippet=f"↳ {orig_brief[:70]}",
        session_type="agent_flow",
        chat_model=body.chat_model,
        chat_provider=body.chat_provider,
    )
    asyncio.create_task(_save_title(db, new_session_id, f"Follow-up: {orig_brief[:200]}", current_user.sub))

    agent_cfg = get_agent_config()

    flow_config           = {}
    flow_snapshot_id      = None
    flow_snapshot_version = None

    try:
        skill    = skill_registry.get(body.flow_id)
        snapshot = await db.get_latest_snapshot(current_user.sub, body.flow_id)
        if snapshot:
            db_prompts            = await db.get_prompt_content_for_snapshot(current_user.sub, body.flow_id, snapshot)
            flow_config           = {**skill.all_agent_prompts, **db_prompts}
            flow_snapshot_id      = snapshot["id"]
            flow_snapshot_version = snapshot["snapshot_version"]
            model_overrides       = await db.get_model_config_for_snapshot(current_user.sub, body.flow_id, snapshot)
            slot_map              = skill.manifest.agent_slot_map
            for agent_key, model_cfg in model_overrides.items():
                slot = slot_map.get(agent_key)
                if slot and model_cfg:
                    agent_cfg[slot] = model_cfg
        else:
            flow_config = dict(skill.all_agent_prompts)
    except SkillNotFoundError:
        pass

    try:
        _skill = skill_registry.get(body.flow_id)
        for slot in set(_skill.manifest.agent_slot_map.values()):
            if slot not in agent_cfg and slot in SMART_SLOT_DEFAULTS:
                agent_cfg[slot] = SMART_SLOT_DEFAULTS[slot]
    except Exception:
        pass

    await db.save_config(
        current_user.sub,
        f"session_agent_config_{new_session_id}",
        __import__("json").dumps(agent_cfg),
    )

    graph_to_use = graphs.get(body.flow_id, graph)

    brief = (
        f"Continuing from an existing architecture engagement.\n\n"
        f"Original brief: {orig_brief}\n\n"
        f"Existing approved document (v{doc_version}):\n\n{document}"
    )

    initial_state = AgentState(
        session_id            = new_session_id,
        project_brief         = brief,
        source_type           = "document",
        raw_document_text     = document,
        document_draft        = document,
        document_version      = doc_version,
        session_agent_config  = agent_cfg,
        session_type          = "agent_flow",
        flow_id               = body.flow_id,
        flow_config           = flow_config,
        flow_snapshot_id      = flow_snapshot_id,
        flow_snapshot_version = flow_snapshot_version,
        chat_model            = body.chat_model,
        chat_provider         = body.chat_provider,
        extended_thinking     = body.extended_thinking,
    )

    return StreamingResponse(
        _stream_graph(graph_to_use, initial_state, new_config, db, user_id=current_user.sub),
        media_type="text/event-stream",
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id":   new_session_id,
        },
    )


# ── Session management ────────────────────────────────────────────────────────

class RenameRequest(BaseModel):
    title: str


@router.post("/session/{session_id}/pin")
async def pin_session(session_id: str, request: Request, current_user: AuthUser = Depends(get_current_user)):
    try:
        await request.app.state.db.pin_session(session_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/session/{session_id}/pin")
async def unpin_session(session_id: str, request: Request, current_user: AuthUser = Depends(get_current_user)):
    await request.app.state.db.unpin_session(session_id)
    return {"ok": True}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, request: Request, current_user: AuthUser = Depends(get_current_user)):
    await request.app.state.db.delete_session(session_id)
    return {"ok": True}


@router.patch("/session/{session_id}")
async def rename_session(session_id: str, body: RenameRequest, request: Request, current_user: AuthUser = Depends(get_current_user)):
    await request.app.state.db.rename_session(session_id, body.title)
    return {"ok": True}
