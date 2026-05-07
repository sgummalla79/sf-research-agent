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

from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from pydantic import BaseModel
from api.schemas import ReplyRequest, StartRequest
from config import MAX_FILE_SIZE_MB
from state import AgentState
from utils.file_parser import extract_text, SUPPORTED_EXTENSIONS
from utils.file_storage import save_upload

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
    from utils.api_keys import get_keys

    client = anthropic.AsyncAnthropic(api_key=get_keys()["anthropic"])
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


async def _save_title(db, session_id: str, text: str) -> None:
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
    "intake":     "Intake Agent",
    "discovery":  "Discovery Agent",
    "researcher": "Research Agent",
    "reviewer":   "Review Agent",
    "approver":   "Approver Gate",
}


def _sse(event_type: str, payload: dict) -> str:
    """Format a single SSE message."""
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


async def _stream_graph(graph, input_, config, db=None) -> AsyncGenerator[str, None]:
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

            # LLM token streaming — suppressed for researcher (document shown via card).
            # For model stream events, name = LLM model name (e.g. "ChatAnthropic"),
            # NOT the node name. The actual node is in metadata.langgraph_node.
            elif kind == "on_chat_model_stream" and \
                    event.get("metadata", {}).get("langgraph_node") != "researcher":
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

                if name == "researcher":
                    yield _sse("document_ready", {
                        "version":    _get(output, "document_version", 0),
                        "session_id": config["configurable"]["thread_id"],
                    })

                elif name == "reviewer":
                    rr = _get(output, "review_result")
                    yield _sse("review_complete", {
                        "passed":          _get(rr, "passed",          False),
                        "feedback":        _get(rr, "feedback",         ""),
                        "critical_issues": _get(rr, "critical_issues",  []),
                    })

                elif name == "approver":
                    ar = _get(output, "approval_result")
                    yield _sse("approval_complete", {
                        "status":           _get(ar, "status",           "rejected"),
                        "comments":         _get(ar, "comments",          ""),
                        "required_changes": _get(ar, "required_changes",  []),
                    })

                else:
                    yield _sse("stage_end", {"stage": name})

        # ── Stream ended — persist token usage, then check interrupt/complete ──
        state = await graph.aget_state(config)

        if db:
            records = (state.values or {}).get("usage_records", [])
            if records:
                thread_id = config["configurable"]["thread_id"]
                try:
                    await db.save_usage_records(thread_id, records)
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
async def start_chat(body: StartRequest, request: Request):
    graph      = request.app.state.graph
    db         = request.app.state.db
    session_id = str(uuid.uuid4())
    config     = {"configurable": {"thread_id": session_id}}

    # Save raw snippet immediately; replace with smart title in background
    await db.record_session(session_id, body.brief[:80].replace('\n', ' '))
    asyncio.create_task(_save_title(db, session_id, body.brief))

    initial_state = AgentState(
        session_id=session_id,
        project_brief=body.brief,
    )

    return StreamingResponse(
        _stream_graph(graph, initial_state, config, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )


@router.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
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
    await db.record_session(session_id, f"{'🖼' if is_image else '📄'} {file.filename}"[:80])
    asyncio.create_task(_save_title(db, session_id, title_source))

    initial_state = AgentState(
        session_id=session_id,
        source_type="image" if is_image else "document",
        uploaded_file_path="" if is_image else saved_path,
        uploaded_image_path=saved_path if is_image else "",
        raw_document_text=raw_text,
    )

    return StreamingResponse(
        _stream_graph(graph, initial_state, config, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )


@router.get("/document/{session_id}")
async def get_document(session_id: str, request: Request):
    """Fetch the current document draft for a session (used by the document panel)."""
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    state  = await graph.aget_state(config)
    return {
        "content": state.values.get("document_draft", ""),
        "version": state.values.get("document_version", 0),
    }


async def _retitle_session(db, graph, session_id: str) -> None:
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
            await _save_title(db, session_id, brief)
        else:
            await db.update_session_title(session_id, "Architecture Session")
    except Exception:
        pass


@router.get("/sessions")
async def list_sessions(request: Request):
    """
    Returns {pinned:[...], recent:[...]} sorted correctly.
    Fires background retitling for untitled sessions.
    """
    db    = request.app.state.db
    graph = request.app.state.graph
    data  = await db.list_sessions()

    all_sessions = data["pinned"] + data["recent"]
    untitled     = [s for s in all_sessions if not s.get("brief_snippet")]
    for s in untitled[:10]:
        asyncio.create_task(_retitle_session(db, graph, s["thread_id"]))

    return data


@router.get("/session/{session_id}/restore")
async def restore_session(session_id: str, request: Request):
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

    return {
        "session_id":           session_id,
        "current_stage":        values.get("current_stage", ""),
        "document_version":     values.get("document_version", 0),
        "project_brief":        (values.get("project_brief") or "")[:200],
        "messages":             messages,
        "pending_questions":    pending_questions,
        "pending_confirmation": pending_confirmation,
        "has_document":         bool(values.get("document_draft")),
    }


@router.post("/reply/{session_id}")
async def reply_chat(session_id: str, body: ReplyRequest, request: Request):
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


# ── Session management ────────────────────────────────────────────────────────

class RenameRequest(BaseModel):
    title: str


@router.post("/session/{session_id}/pin")
async def pin_session(session_id: str, request: Request):
    try:
        await request.app.state.db.pin_session(session_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/session/{session_id}/pin")
async def unpin_session(session_id: str, request: Request):
    await request.app.state.db.unpin_session(session_id)
    return {"ok": True}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, request: Request):
    await request.app.state.db.delete_session(session_id)
    return {"ok": True}


@router.patch("/session/{session_id}")
async def rename_session(session_id: str, body: RenameRequest, request: Request):
    await request.app.state.db.rename_session(session_id, body.title)
    return {"ok": True}

