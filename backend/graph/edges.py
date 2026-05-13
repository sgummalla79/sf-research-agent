"""
Conditional edge functions — each returns the name of the next node.
Keeping routing logic here (separate from agent logic) makes the graph easy to audit.
"""

from config import MAX_REVISIONS
from state import AgentState


def route_entry(state: AgentState) -> str:
    """Route to chat node or agent flow based on session_type."""
    if state.session_type == "chat":
        return "chat"
    return "intake"


def route_after_chat(state: AgentState) -> str:
    """Chat node always ends after one response — no looping pipeline."""
    return "end"


def route_after_intake(state: AgentState) -> str:
    """
    Invalid image → end immediately with a clear rejection message.
    Everything else (brief, document, valid image) → proceed to discovery.
    """
    if state.current_stage == "invalid_input":
        return "end"
    return "discovery"


def route_after_discovery(state: AgentState) -> str:
    """Stay in discovery until the agent marks it complete."""
    if state.discovery_complete:
        return "researcher"
    return "discovery"


def route_after_review(state: AgentState) -> str:
    """
    Reviewer passes  → send to approver.
    Reviewer rejects → send back to researcher to revise before re-submitting.
    """
    if state.review_result and state.review_result.passed:
        return "approver"
    return "researcher"


def route_after_approval(state: AgentState) -> str:
    """
    Approved         → end the graph (complete).
    Rejected         → back to researcher (document must be revised + re-reviewed).
    Too many loops   → halt to prevent infinite cycling.
    """
    if state.approval_result and state.approval_result.status == "approved":
        return "complete"

    if state.revision_count >= MAX_REVISIONS:
        return "halted"

    # Rejection: researcher must address approver comments, then reviewer validates again
    return "researcher"
