"""
Stage 4 — Peer Validation Agent

One-way review: reads the document, returns a structured verdict.
Never "chats" with the researcher — verdict is passed via state only.
"""

from langchain_core.messages import AIMessage

from agents.base import BaseAgent
from state import AgentState, ReviewResult


class ReviewerAgent(BaseAgent):
    prompt_key = "REVIEWER_SYSTEM_PROMPT"
    llm_slot   = "reviewer"
    schema     = ReviewResult

    def _build_human_prompt(self, state: AgentState) -> str:
        scope_note = ""
        if state.discovery_questions:
            answered   = [q for q in state.discovery_questions if q.answer]
            scope_note = (
                "\nDiscovery answers for context (use to validate document completeness):\n"
                + "\n".join(f"  Q: {q.question}\n  A: {q.answer}" for q in answered)
            )

        return (
            f"Review the following Architecture Recommendation Document"
            f" (version {state.document_version}).{scope_note}\n\n"
            f"{'─' * 64}\nDOCUMENT:\n{state.document_draft}\n{'─' * 64}\n\n"
            "Work through the review checklist systematically.\n"
            "Return your structured verdict with:\n"
            "  - passed: true/false\n"
            "  - feedback: overall assessment (2–4 sentences)\n"
            "  - critical_issues: list of specific, actionable strings (empty list if passed)"
        )

    def _post_process(self, state: AgentState, result: ReviewResult, urec) -> dict:
        status = "PASSED" if result.passed else "FAILED"
        return {
            "current_stage": "review",
            "review_result": result,
            "usage_records": [urec],
            "messages": [
                AIMessage(name="reviewer", content=f"[Reviewer] Review {status}. {result.feedback}")
            ],
        }


run_reviewer = ReviewerAgent()
