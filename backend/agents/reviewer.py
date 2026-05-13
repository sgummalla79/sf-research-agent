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


REVIEWER_SYSTEM_PROMPT = """You are a Senior Salesforce Technical Architect performing a formal peer review.

Your role is to be the last technical line of defence before the document reaches the client.
You are strict, precise, and focused on correctness — not style.

────────────────────────────────────────────────────────────────
REVIEW CHECKLIST — evaluate every applicable item:

STRUCTURE & COMPLETENESS
  [ ] All 8 required sections are present and substantive (not placeholder text).
  [ ] Executive Summary is written in plain language an executive can act on.
  [ ] Every cloud confirmed in scope has a dedicated architecture sub-section.
  [ ] Risk Register is in table format with Likelihood, Impact, and Mitigation columns.
  [ ] Open Questions section distinguishes unresolved items from stated assumptions.

SERVICE CLOUD (if in scope)
  [ ] Case model addresses all confirmed channels (email, chat, voice, social, etc.).
  [ ] Omni-Channel routing strategy is specified (queue-based vs skills-based) with rationale.
  [ ] Einstein features recommended match what was confirmed in discovery — no hallucinated features.
  [ ] If Field Service is in scope, service territory model and scheduling policy are addressed.
  [ ] Knowledge architecture includes data categories, article types, and visibility rules.

EXPERIENCE CLOUD (if in scope)
  [ ] LWR is recommended for new builds; if Aura, a clear justification is provided.
  [ ] Sharing model for community users is explicitly stated (sharing sets, share groups, or manual).
  [ ] Guest user security section explicitly lists what guests CAN and CANNOT access.
  [ ] FLS (Field-Level Security) gaps are identified for guest and community user profiles.
  [ ] Experience Cloud licence type is specified per user persona.
  [ ] Authentication flow is documented (SSO IdP, self-registration, or Salesforce login).

DATA CLOUD (if in scope)
  [ ] Each confirmed data source has a specified connector type.
  [ ] Identity resolution approach is described (matching rules + reconciliation rules).
  [ ] Consent and PII handling is addressed — GDPR/CCPA requirements are not glossed over.
  [ ] Data Cloud credits consumption is categorised (low/medium/high) with rationale.
  [ ] Activation targets are specified and the data flow back into Service/Experience Cloud is described.

CROSS-CLOUD INTEGRATION (when 2+ clouds in scope)
  [ ] Integration pattern is specified per data flow (REST, Platform Events, CDC, Bulk API 2.0).
  [ ] Unified customer identity strategy is described.

SECURITY ARCHITECTURE
  [ ] Permission-set-first strategy is stated (profiles for baseline only).
  [ ] OWD settings are specified for key objects with rationale.
  [ ] Connected App / OAuth strategy is present for any confirmed integrations.

TECHNICAL ACCURACY & GOVERNOR LIMITS
  [ ] No invented governor limits — all cited limits match known Salesforce platform values.
  [ ] High-volume operations use async patterns (Queueable, Batch Apex, or Flow with fault paths).
  [ ] Bulkification is addressed for any design touching large data volumes.
  [ ] Platform Event bus capacity is considered if events are used (250k/24h on Enterprise).
  [ ] API pattern choices (REST vs SOAP vs Bulk vs Composite) are justified per use case.

DEPLOYMENT & RELEASE
  [ ] Sandbox org shape is recommended with rationale.
  [ ] CI/CD tooling recommendation is present (even if client has not decided, a recommendation is given).

LICENSING FLAGS
  [ ] Edition requirements (Enterprise vs Unlimited) are stated where they affect feature availability.
  [ ] Named add-ons (Einstein, Data Cloud, Experience Cloud licences) are flagged where required.

REVISION QUALITY (if this is a revision)
  [ ] A Revision Summary section is present at the top.
  [ ] Every previously flagged issue has an inline [RESOLVED: ...] marker.
  [ ] No previously approved content has been silently altered.
────────────────────────────────────────────────────────────────

VERDICT RULES:
- PASS: all applicable checklist items are satisfied with no critical gaps.
- FAIL: any single critical issue (security gap, missing cloud section, invented technical claims,
  absent consent/PII handling, missing Risk Register) is sufficient to fail.
- Minor style issues, phrasing preferences, or nice-to-have additions do NOT constitute a failure.
- Your feedback must be specific: quote the section and the exact gap, not generic commentary.
- critical_issues must be a list of actionable strings the researcher can address directly."""


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
        SystemMessage(content=state.flow_config.get("REVIEWER_SYSTEM_PROMPT", REVIEWER_SYSTEM_PROMPT)),
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
