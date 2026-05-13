"""
Stage 5 — Approver Gate Agent

The final human-proxy gate. Approves or rejects with mandatory structured output.
Rejection always includes required_changes so the researcher has actionable feedback.
"""

from langchain_core.messages import AIMessage

from agents.base import BaseAgent
from config import MAX_REVISIONS
from state import AgentState, ApprovalResult


class ApproverAgent(BaseAgent):
    prompt_key = "APPROVER_SYSTEM_PROMPT"
    llm_slot   = "approver"
    schema     = ApprovalResult

    def _build_human_prompt(self, state: AgentState) -> str:
        revision_note = (
            f"\nIMPORTANT: This is revision {state.revision_count} of {MAX_REVISIONS} allowed. "
            "Be precise about what is still missing — do not re-raise issues that were already resolved."
        ) if state.revision_count > 0 else ""

        brief_section = f"## Original Project Brief\n{state.project_brief}\n\n" if state.project_brief else ""

        discovery_section = ""
        if state.discovery_questions:
            answered = [q for q in state.discovery_questions if q.answer]
            if answered:
                discovery_section = (
                    "## Key Discovery Answers\n"
                    + "\n".join(f"  Q: {q.question}\n  A: {q.answer}" for q in answered)
                    + "\n\n"
                )

        reviewer_feedback = state.review_result.feedback if state.review_result else "N/A"

        return (
            f"{brief_section}{discovery_section}"
            f"## Reviewer Verdict (technical review already passed)\n{reviewer_feedback}\n"
            f"{revision_note}\n\n"
            f"{'─' * 64}\n"
            f"DOCUMENT TO APPROVE (version {state.document_version}):\n"
            f"{state.document_draft}\n"
            f"{'─' * 64}\n\n"
            "Apply your 7-lens strategic review. Return your structured verdict."
        )

    def _post_process(self, state: AgentState, result: ApprovalResult, urec) -> dict:
        new_revision_count = state.revision_count + (1 if result.status == "rejected" else 0)
        return {
            "current_stage":  "approval",
            "approval_result": result,
            "revision_count":  new_revision_count,
            "usage_records":  [urec],
            "messages": [
                AIMessage(
                    name="approver",
                    content=f"[Approver] Decision: {result.status.upper()}. {result.comments}",
                )
            ],
        }


run_approver = ApproverAgent()
