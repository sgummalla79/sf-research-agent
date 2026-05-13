"""
Stage 1 — Initial Intake Agent
Model: Claude (reasoning + vision)

Three paths:
  brief    → pass through as-is; stamp session metadata.
  document → Claude reads extracted text → extracts project brief →
             PAUSES for user confirmation before discovery starts.
  image    → Claude Vision validates + extracts →
             PAUSES for user confirmation before discovery starts.

The confirmation interrupt ensures the user reads and verifies what was
understood BEFORE discovery questions appear. They can also type corrections
which get appended to the project brief.
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

# ── Document extraction prompt ────────────────────────────────────────────────

# ── Image validation + extraction prompt ──────────────────────────────────────

class ImageAnalysisResult(BaseModel):
    is_architecture_related: bool
    extracted_brief: str
    rejection_reason: str

_MEDIA_TYPES = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}

def _analyze_image(image_path: str, session_cfg: dict, flow_config: dict) -> ImageAnalysisResult:
    suffix     = Path(image_path).suffix.lower()
    media_type = _MEDIA_TYPES.get(suffix, "image/jpeg")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    llm = get_llm_for_slot("intake", session_cfg).with_structured_output(ImageAnalysisResult, include_raw=True)

    raw = invoke_with_retry(llm, [
        SystemMessage(content=flow_config.get("INTAKE_IMAGE_SYSTEM_PROMPT")),
        HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
            {"type": "text",      "text": "Analyse this image and return your structured assessment."},
        ]),
    ])
    return raw["parsed"], usage_record("intake", slot_model("intake", session_cfg), getattr(raw.get("raw"), "usage_metadata", None))

# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_correction(raw) -> str:
    """
    interrupt() resumes with whatever was passed to Command(resume=...).
    ReplyRequest sends answers: list[str], so raw arrives as a list.
    Extract the first element and normalise to a plain string.
    """
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return (raw or "").strip()

# ── Node function ─────────────────────────────────────────────────────────────

def run_intake(state: AgentState) -> dict:
    base = {
        "current_stage": "intake",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # ── Image path ────────────────────────────────────────────────────────────
    if state.source_type == "image" and state.uploaded_image_path:
        result, urec = _analyze_image(state.uploaded_image_path, state.session_agent_config, state.flow_config)

        if not result.is_architecture_related:
            return {
                **base,
                "current_stage": "invalid_input",
                "usage_records": [urec],
                "messages": [
                    HumanMessage(content="[Image uploaded]"),
                    AIMessage(name="intake", content=(
                        f"I'm unable to use this image as the basis for an architecture session.\n\n"
                        f"**Reason:** {result.rejection_reason}\n\n"
                        "Please upload an architecture diagram, system design sketch, "
                        "whiteboard photo, UML diagram, or similar technical drawing."
                    )),
                ],
            }

        extracted_brief = result.extracted_brief
        # Pause — let user read and verify the extraction before discovery starts
        correction = _extract_correction(interrupt({
            "__type":  "confirm_understanding",
            "content": extracted_brief,
        }))

        if correction:
            extracted_brief += f"\n\n**User correction:** {correction}"

        return {
            **base,
            "project_brief": extracted_brief,
            "usage_records": [urec],
            "messages": [
                HumanMessage(content="[Architecture image uploaded]"),
                AIMessage(name="intake", content=extracted_brief),
            ],
        }

    # ── Document path ─────────────────────────────────────────────────────────
    if state.source_type == "document" and state.raw_document_text:
        llm      = get_llm_for_slot("intake", state.session_agent_config)
        response = invoke_with_retry(llm, [
            SystemMessage(content=state.flow_config.get("INTAKE_DOCUMENT_PROMPT")),
            HumanMessage(content=(
                f"Extract a structured Project Brief from this document.\n\n"
                f"---\n{state.raw_document_text}\n---"
            )),
        ])

        extracted_brief = response.content
        urec_doc = usage_record("intake", slot_model("intake", state.session_agent_config), getattr(response, "usage_metadata", None))
        # Pause — let user read and verify the extraction before discovery starts
        correction = _extract_correction(interrupt({
            "__type":  "confirm_understanding",
            "content": extracted_brief,
        }))

        if correction:
            extracted_brief += f"\n\n**User correction:** {correction}"

        return {
            **base,
            "project_brief": extracted_brief,
            "usage_records": [urec_doc],
            "messages": [
                HumanMessage(content="[Document uploaded]"),
                AIMessage(name="intake", content=extracted_brief),
            ],
        }

    # ── Plain text brief — no confirmation needed, user wrote it themselves ───
    return {
        **base,
        "messages": [
            HumanMessage(content=f"Project brief:\n\n{state.project_brief}")
        ],
    }
