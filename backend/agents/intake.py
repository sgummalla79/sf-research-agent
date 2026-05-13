"""
Stage 1 — Initial Intake Agent

Two paths:
  brief    → pass through directly; no LLM call needed.
  uploaded → extract project brief via LLM (document text or image vision),
             then pause for user confirmation before discovery begins.

The source type (document vs image) is a format detail handled inside
_extract_from_upload — the pipeline treats both the same way.
"""

import base64
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from utils.llm_factory import get_llm_for_slot, slot_model
from utils.llm_retry import invoke_with_retry
from utils.pricing import usage_record
from state import AgentState


class ImageAnalysisResult(BaseModel):
    is_architecture_related: bool
    extracted_brief:         str
    rejection_reason:        str


_MEDIA_TYPES = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}


def _extract_from_upload(state: AgentState) -> tuple[str | None, dict, str]:
    """
    Extract a project brief from any uploaded content.
    Returns (brief, usage_record, rejection_reason).
    brief is None only when an image fails the architecture relevance check.
    """
    if state.source_type == "image" and state.uploaded_image_path:
        suffix     = Path(state.uploaded_image_path).suffix.lower()
        media_type = _MEDIA_TYPES.get(suffix, "image/jpeg")

        with open(state.uploaded_image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        llm = get_llm_for_slot("intake", state.session_agent_config).with_structured_output(
            ImageAnalysisResult, include_raw=True
        )
        raw    = invoke_with_retry(llm, [
            SystemMessage(content=state.flow_config.get("INTAKE_IMAGE_SYSTEM_PROMPT")),
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                {"type": "text",      "text": "Analyse this image and return your structured assessment."},
            ]),
        ])
        result: ImageAnalysisResult = raw["parsed"]
        urec = usage_record("intake", slot_model("intake", state.session_agent_config),
                            getattr(raw.get("raw"), "usage_metadata", None))

        if not result.is_architecture_related:
            return None, urec, result.rejection_reason
        return result.extracted_brief, urec, ""

    # Document (PDF, DOCX, TXT, MD — text already extracted into raw_document_text)
    llm      = get_llm_for_slot("intake", state.session_agent_config)
    response = invoke_with_retry(llm, [
        SystemMessage(content=state.flow_config.get("INTAKE_DOCUMENT_PROMPT")),
        HumanMessage(content=f"Extract a structured Project Brief from this document.\n\n---\n{state.raw_document_text}\n---"),
    ])
    urec = usage_record("intake", slot_model("intake", state.session_agent_config),
                        getattr(response, "usage_metadata", None))
    return response.content, urec, ""


def _extract_correction(raw) -> str:
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return (raw or "").strip()


def run_intake(state: AgentState) -> dict:
    base = {
        "current_stage": "intake",
        "created_at":    datetime.now(timezone.utc).isoformat(),
    }

    # ── Plain text brief — user wrote it, no extraction needed ───────────────
    if state.source_type == "brief":
        return {
            **base,
            "messages": [HumanMessage(content=f"Project brief:\n\n{state.project_brief}")],
        }

    # ── Uploaded content (document or image) — extract brief, then confirm ───
    brief, urec, rejection = _extract_from_upload(state)

    if rejection:
        return {
            **base,
            "current_stage": "invalid_input",
            "usage_records": [urec],
            "messages": [
                HumanMessage(content=f"[{state.source_type.capitalize()} uploaded]"),
                AIMessage(name="intake", content=(
                    f"I'm unable to use this upload as the basis for an architecture session.\n\n"
                    f"**Reason:** {rejection}\n\n"
                    "Please upload an architecture diagram, system design sketch, or a document "
                    "describing the project."
                )),
            ],
        }

    # Pause — let user read, verify, and optionally correct the extraction
    correction = _extract_correction(interrupt({
        "__type":  "confirm_understanding",
        "content": brief,
    }))
    if correction:
        brief += f"\n\n**User correction:** {correction}"

    return {
        **base,
        "project_brief": brief,
        "usage_records": [urec],
        "messages": [
            HumanMessage(content=f"[{state.source_type.capitalize()} uploaded]"),
            AIMessage(name="intake", content=brief),
        ],
    }
