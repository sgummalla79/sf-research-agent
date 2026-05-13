"""
Stage 3 — Deep Research & Drafting Agent

  Step 1a — researcher_search slot (Perplexity Sonar Pro, runs in parallel)
    Real-time web search: current platform limits, release notes, known issues,
    and citations from official vendor documentation.

  Step 1b — researcher_reasoning slot (Gemini 2.5 Pro, runs in parallel)
    Deep architectural reasoning. Derives topics from the project context.

  Steps 1a + 1b run concurrently — no extra latency cost.

  Step 2 — researcher_writer slot (Claude Sonnet)
    Receives both research outputs and writes the Architecture Recommendation Document.
"""

from concurrent.futures import ThreadPoolExecutor

from utils.llm_retry import invoke_with_retry
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from utils.llm_factory import get_llm_for_slot, slot_model
from utils.pricing import usage_record
from state import AgentState


def _discovery_summary(state: AgentState) -> str:
    return "\n".join(
        f"- {q.question}: {q.answer}"
        for q in state.discovery_questions if q.answer
    )


# ── Step 1a: Perplexity — current facts, limits, citations ────────────────────

def _gather_perplexity(state: AgentState) -> tuple:
    prompt = (
        f"## Project Brief\n{state.project_brief}\n\n"
        f"## Discovery Answers\n{_discovery_summary(state)}\n\n"
        "Research the platforms, APIs, limits, and official documentation "
        "relevant to this architecture engagement."
    )

    llm = get_llm_for_slot("researcher_search", state.session_agent_config)
    response = invoke_with_retry(llm, [
        SystemMessage(content=state.flow_config.get("PERPLEXITY_SYSTEM_PROMPT")),
        HumanMessage(content=prompt),
    ])
    return (
        f"## SEARCH RESEARCH — Current Facts & Citations\n\n{response.content}",
        usage_record("researcher", slot_model("researcher_search", state.session_agent_config), getattr(response, "usage_metadata", None)),
    )


# ── Step 1b: Gemini — deep patterns, architectural reasoning ──────────────────

def _gather_gemini(state: AgentState) -> tuple:
    prompt = (
        f"## Project Brief\n{state.project_brief}\n\n"
        f"## Discovery Answers\n{_discovery_summary(state)}\n\n"
        "Provide architectural pattern guidance and design recommendations "
        "for this engagement."
    )

    llm = get_llm_for_slot("researcher_reasoning", state.session_agent_config)
    response = invoke_with_retry(llm, [
        SystemMessage(content=state.flow_config.get("GEMINI_SYSTEM_PROMPT")),
        HumanMessage(content=prompt),
    ])
    return (
        f"## ARCHITECTURE RESEARCH — Patterns & Design Guidance\n\n{response.content}",
        usage_record("researcher", slot_model("researcher_reasoning", state.session_agent_config), getattr(response, "usage_metadata", None)),
    )


# ── Step 2: Write / revise the Architecture Recommendation Document ────────────

def _write_document(state: AgentState, perplexity_research: str, gemini_research: str) -> tuple:
    llm = get_llm_for_slot("researcher_writer", state.session_agent_config)
    discovery = _discovery_summary(state)

    if state.document_version == 0:
        user_prompt = (
            f"## Project Brief\n{state.project_brief}\n\n"
            f"## Discovery Answers\n{discovery}\n\n"
            f"## Research Context\n{perplexity_research}\n\n---\n\n{gemini_research}\n\n---\n\n"
            "Using all of the above, produce the complete Architecture Recommendation Document.\n"
            "Use exact limit values from the Search Research. Apply architectural patterns from the Architecture Research."
        )
    else:
        approver_section = ""
        if state.approval_result:
            changes = "\n".join(f"  - {c}" for c in state.approval_result.required_changes)
            approver_section = (
                f"\n## Approver Rejection Comments (ALL must be resolved)\n"
                f"{state.approval_result.comments}\n\nRequired changes:\n{changes}"
            )

        reviewer_section = ""
        if state.review_result:
            issues = "\n".join(f"  - {i}" for i in state.review_result.critical_issues)
            reviewer_section = (
                f"\n## Reviewer Feedback (ALL critical issues must be resolved)\n"
                f"{state.review_result.feedback}\n\nCritical issues:\n{issues}"
            )

        user_prompt = (
            f"## Prior Document (version {state.document_version})\n{state.document_draft}"
            f"{approver_section}{reviewer_section}\n\n"
            f"## Refreshed Research Context\n"
            f"{perplexity_research}\n\n---\n\n{gemini_research}\n\n---\n\n"
            "Instructions:\n"
            "1. Add ## Revision Summary at the top listing every change made.\n"
            "2. Resolve every flagged item. Mark each: [RESOLVED: <comment>]\n"
            "3. Do NOT rewrite sections that were not flagged — preserve verbatim.\n"
            "4. Output the complete updated document."
        )

    response = invoke_with_retry(llm, [
        SystemMessage(content=state.flow_config.get("WRITER_SYSTEM_PROMPT")),
        HumanMessage(content=user_prompt),
    ])
    return (
        response.content,
        usage_record("researcher", slot_model("researcher_writer", state.session_agent_config), getattr(response, "usage_metadata", None)),
    )


# ── Node function ─────────────────────────────────────────────────────────────

def run_researcher(state: AgentState) -> dict:
    with ThreadPoolExecutor(max_workers=2) as pool:
        perplexity_future = pool.submit(_gather_perplexity, state)
        gemini_future     = pool.submit(_gather_gemini,     state)

        perplexity_research, urec_pplx   = perplexity_future.result()
        gemini_research,     urec_gemini = gemini_future.result()

    document, urec_writer = _write_document(state, perplexity_research, gemini_research)
    new_version = state.document_version + 1

    return {
        "current_stage":    "research",
        "document_draft":   document,
        "document_version": new_version,
        "review_result":    None,
        "approval_result":  None,
        "usage_records":    [urec_pplx, urec_gemini, urec_writer],
        "messages": [
            AIMessage(
                name="researcher",
                content=(
                    f"[Researcher] Document v{new_version} produced. "
                    f"Research: Search + Reasoning in parallel → Writer."
                )
            )
        ],
    }
