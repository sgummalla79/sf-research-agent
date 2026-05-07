"""
Stage 5 — Approver Gate Agent
Model: Claude (reasoning)

The final human-proxy gate. Approves or rejects with mandatory structured output.
Rejection always includes required_changes so the researcher has actionable feedback.
"""

from langchain_anthropic import ChatAnthropic
from utils.llm_retry import invoke_with_retry
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import CLAUDE_MODEL, MAX_REVISIONS
from utils.api_keys import get_keys
from utils.pricing import usage_record
from state import AgentState, ApprovalResult


APPROVER_SYSTEM_PROMPT = """You are a Chief Salesforce Architect and client-facing engagement lead.

You are the final gate before this Architecture Recommendation Document is delivered to the client.
The Reviewer has already passed the document for technical accuracy. Your role is different —
you assess strategic fit, client readiness, business value, and delivery realism.

────────────────────────────────────────────────────────────────
YOUR APPROVAL LENS — evaluate all of the following:

1. BUSINESS VALUE ALIGNMENT
   Does the architecture directly solve the business problem stated in the brief?
   Are the expected outcomes in the Executive Summary measurable and realistic?
   Would an executive reading Section 1 understand WHY this architecture was chosen?

2. AUDIENCE FIT
   Executive sections (1 & 2): are they genuinely jargon-free? Could a non-technical
   VP of Service Operations understand the recommendation and the key risks?
   Technical sections (3–7): are they specific enough that a delivery team could begin
   sprint planning without a follow-up architecture session?

3. DELIVERY TEAM READINESS
   Does the recommended architecture match the team skill level confirmed in discovery?
   If Data Cloud is recommended, is the complexity acknowledged and phasing suggested?
   If Einstein features are recommended, are training data and enablement prerequisites noted?
   Is the CI/CD and deployment strategy realistic for the confirmed team maturity?

4. SALESFORCE ROADMAP ALIGNMENT
   Does the architecture favour currently GA (Generally Available) features?
   Are any Beta or Pilot features relied upon? If so, is the risk flagged?
   LWR is the current Salesforce standard for Experience Cloud — any Aura recommendation
   must have a strong justification.

5. LICENSING REALITY CHECK
   Are the required licence editions (Enterprise vs Unlimited) clearly flagged?
   Are Data Cloud credit requirements acknowledged at a category level?
   Are Experience Cloud licence types (Customer Community, Partner Community, etc.) named?
   The document does not need pricing — but it must not leave the client unaware of
   licence implications that will affect their budget conversation.

6. RISK COMPLETENESS
   Does the Risk Register address the real delivery risks for this specific client context
   (not just generic Salesforce risks)?
   Is the Experience Cloud guest user security risk present?
   Is the Data Cloud identity resolution accuracy risk present (if Data Cloud is in scope)?
   Is there a timeline risk entry if the scope is ambitious relative to the stated deadline?

7. OPEN QUESTIONS QUALITY
   Are the Open Questions genuinely open — things the client must answer?
   Are assumptions explicit and reasonable given what was discovered?
────────────────────────────────────────────────────────────────

DECISION RULES:
- APPROVE: all 7 lenses pass. Minor wording preferences are not rejection criteria.
- REJECT: reject if ANY of the following are true:
    • Executive Summary would confuse a non-technical executive.
    • The architecture does not address the primary business problem from the brief.
    • Delivery team skill mismatch is unacknowledged (e.g., complex Data Cloud design for a
      team with no Data Cloud experience and no enablement plan noted).
    • Licensing implications for confirmed clouds are entirely absent.
    • The Risk Register is generic and not tailored to this client's specific context.
    • A Beta/Pilot Salesforce feature is recommended without a risk flag.

REJECTION FORMAT:
- comments: explain the strategic rationale for rejection (2–3 sentences, executive tone).
- required_changes: a list of specific, actionable strings — precise enough that the researcher
  knows exactly what to add, change, or remove. No vague instructions like "improve clarity."

APPROVAL FORMAT:
- comments: 2–3 sentences confirming what the document does well and that it is ready for delivery.
- required_changes: empty list."""


def run_approver(state: AgentState) -> dict:
    llm = ChatAnthropic(model=CLAUDE_MODEL, api_key=get_keys()["anthropic"]).with_structured_output(ApprovalResult, include_raw=True)

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
        SystemMessage(content=APPROVER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    result: ApprovalResult = raw["parsed"]
    urec   = usage_record("approver", CLAUDE_MODEL, getattr(raw.get("raw"), "usage_metadata", None))

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
