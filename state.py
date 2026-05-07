from __future__ import annotations

from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ── Per-question record from the discovery phase ──────────────────────────────

class DiscoveryQuestion(BaseModel):
    question: str
    answer: Optional[str] = None
    satisfied: bool = False   # True once the agent deems the answer sufficient


# ── Reviewer structured output ─────────────────────────────────────────────────

class ReviewResult(BaseModel):
    passed: bool
    feedback: str             # Always populated; praise or critique
    critical_issues: list[str] = Field(default_factory=list)


# ── Approver structured output ─────────────────────────────────────────────────

class ApprovalResult(BaseModel):
    status: Literal["approved", "rejected"]
    comments: str             # Always populated
    required_changes: list[str] = Field(default_factory=list)


# ── Main graph state ───────────────────────────────────────────────────────────

class AgentState(BaseModel):
    # ── Session metadata ──────────────────────────────────────────────────────
    session_id: str = ""
    created_at: str = ""

    # ── Stage tracking ────────────────────────────────────────────────────────
    current_stage: Literal[
        "intake", "discovery", "research", "review", "approval",
        "complete", "halted", "invalid_input"
    ] = "intake"
    revision_count: int = 0   # increments each time Approver rejects

    # ── Stage 1 — Initial intake ──────────────────────────────────────────────
    source_type: Literal["brief", "document", "image"] = "brief"
    uploaded_file_path: str  = ""  # path to saved document (document uploads)
    uploaded_image_path: str = ""  # path to saved image (image uploads)
    raw_document_text: str   = ""  # extracted text from document — never re-read from disk
    project_brief: str       = ""  # typed brief, doc-extracted summary, or image-extracted brief

    # ── Stage 2 — Dynamic discovery ──────────────────────────────────────────
    discovery_questions: list[DiscoveryQuestion] = Field(default_factory=list)
    discovery_complete: bool = False

    # ── Stage 3 — Research & drafting ────────────────────────────────────────
    document_draft: str = ""
    document_version: int = 0

    # ── Stage 4 — Peer review ─────────────────────────────────────────────────
    review_result: Optional[ReviewResult] = None

    # ── Stage 5 — Approver gate ───────────────────────────────────────────────
    approval_result: Optional[ApprovalResult] = None

    # ── Conversation history (append-only via LangGraph reducer) ─────────────
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
