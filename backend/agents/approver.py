"""
Stage 5 — Approver Gate Agent

The final human-proxy gate. Approves or rejects with mandatory structured output.
Rejection always includes required_changes so the researcher has actionable feedback.
"""

from utils.llm_retry import invoke_with_retry
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import MAX_REVISIONS
from utils.llm_factory import get_llm_for_slot, slot_model
from utils.pricing import usage_record
from state import AgentState, ApprovalResult

def run_approver(state: AgentState) -> dict:
    llm = get_llm_for_slot("approver", state.session_agent_config).with_structured_output(ApprovalResult, include_raw=True)

    revision_note = (
        f"\nIMPORTANT: This is revision {state.revision_count} of {MAX_REVISIONS} allowed. "
        "Be precise about what is still missing — do not re-raise issues that were already resolved."
        if state.revision_count > 0 else ""
    )

    # Include the original brief so the Approver can check alignment
    brief_section = f"""## Original Project Brief
{state.project_brief}
""" if state.project_brief else ""

    # Include discovery answers for context
    discovery_section = ""
    if state.discovery_questions:
        answered = [q for q in state.discovery_questions if q.answer]
        if answered:
            discovery_section = "## Key Discovery Answers\n" + "\n".join(
                f"  Q: {q.question}\n  A: {q.answer}" for q in answered
            ) + "\n"

    prompt = f"""{brief_section}{discovery_section}
## Reviewer Verdict (technical review already passed)
{state.review_result.feedback if state.review_result else "N/A"}
{revision_note}

────────────────────────────────────────────────────────────────
DOCUMENT TO APPROVE (version {state.document_version}):
{state.document_draft}
────────────────────────────────────────────────────────────────

Apply your 7-lens strategic review. Return your structured verdict."""

    # Approver does NOT need conversation history — all required context is
    # already structured in the prompt: brief, discovery answers, document, reviewer verdict.
    raw    = invoke_with_retry(llm, [
        SystemMessage(content=state.flow_config.get("APPROVER_SYSTEM_PROMPT")),
        HumanMessage(content=prompt),
    ])
    result: ApprovalResult = raw["parsed"]
    urec   = usage_record("approver", slot_model("approver", state.session_agent_config), getattr(raw.get("raw"), "usage_metadata", None))

    new_revision_count = state.revision_count + (1 if result.status == "rejected" else 0)

    return {
        "current_stage": "approval",
        "approval_result": result,
        "revision_count": new_revision_count,
        "usage_records": [urec],
        "messages": [
            AIMessage(
                name="approver",
                content=f"[Approver] Decision: {result.status.upper()}. {result.comments}"
            )
        ],
    }
