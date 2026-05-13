"""
Stage 4 — Peer Validation Agent

One-way review: reads the document, returns a structured verdict.
Never "chats" with the researcher — verdict is passed via state only.
"""

from utils.llm_retry import invoke_with_retry
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from utils.llm_factory import get_llm_for_slot, slot_model
from utils.pricing import usage_record
from state import AgentState, ReviewResult

def run_reviewer(state: AgentState) -> dict:
    llm = get_llm_for_slot("reviewer", state.session_agent_config).with_structured_output(ReviewResult, include_raw=True)

    scope_note = ""
    if state.discovery_questions:
        answered = [q for q in state.discovery_questions if q.answer]
        scope_note = "Discovery answers for context (use to validate document completeness):\n" + "\n".join(
            f"  Q: {q.question}\n  A: {q.answer}" for q in answered
        )

    prompt = f"""Review the following Architecture Recommendation Document (version {state.document_version}).

{scope_note}

────────────────────────────────────────────────────────────────
DOCUMENT:
{state.document_draft}
────────────────────────────────────────────────────────────────

Work through the review checklist systematically.
Return your structured verdict with:
  - passed: true/false
  - feedback: overall assessment (2–4 sentences)
  - critical_issues: list of specific, actionable strings (empty list if passed)"""

    # Reviewer does NOT need conversation history — it works entirely from
    # structured state: document_draft + discovery_questions (already in prompt).
    raw    = invoke_with_retry(llm, [
        SystemMessage(content=state.flow_config.get("REVIEWER_SYSTEM_PROMPT")),
        HumanMessage(content=prompt),
    ])
    result: ReviewResult = raw["parsed"]
    urec   = usage_record("reviewer", slot_model("reviewer", state.session_agent_config), getattr(raw.get("raw"), "usage_metadata", None))

    status = "PASSED" if result.passed else "FAILED"
    return {
        "current_stage": "review",
        "review_result": result,
        "usage_records": [urec],
        "messages": [
            AIMessage(name="reviewer", content=f"[Reviewer] Review {status}. {result.feedback}")
        ],
    }
