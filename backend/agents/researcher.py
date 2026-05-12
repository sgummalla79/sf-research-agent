"""
Stage 3 — Deep Research & Drafting Agent
Three-step approach with parallel research:

  Step 1a — researcher_search slot (default: Perplexity Sonar Pro, runs in parallel)
    Real-time web search: current governor limits, Spring/Summer release notes,
    known issues, and citations from Salesforce Help + Trailhead.

  Step 1b — researcher_reasoning slot (default: Gemini 2.5 Pro, runs in parallel)
    Deep architectural reasoning with 1M token context.

  Steps 1a + 1b run concurrently — no extra latency cost.

  Step 2 — researcher_writer slot (default: Claude Sonnet)
    Receives both research outputs as combined context.
    Writes (or revises) the full 8-section Architecture Recommendation Document.
"""

from concurrent.futures import ThreadPoolExecutor

from utils.llm_retry import invoke_with_retry
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from utils.llm_factory import get_llm_for_slot, slot_model
from utils.pricing import usage_record
from state import AgentState


# ── Shared scope detection ─────────────────────────────────────────────────────

def _detect_scope(state: AgentState) -> dict:
    """
    Detect both Salesforce cloud scope AND the overall discussion type.
    Prevents the researcher from pulling Salesforce-specific docs for
    integration/pattern discussions where Salesforce is a component, not the subject.
    """
    combined = (
        (state.project_brief or "") + " " +
        " ".join(q.answer or "" for q in state.discovery_questions)
    ).lower()

    # Only flag Salesforce clouds if the session is actually about implementing them
    sf_impl_signals = ["service cloud", "experience cloud", "data cloud", "sales cloud",
                       "omni-channel", "lightning", "apex", "lwc", "visualforce",
                       "salesforce org", "salesforce implementation"]
    is_sf_implementation = any(w in combined for w in sf_impl_signals)

    return {
        # Salesforce cloud flags — gated on is_sf_implementation
        "service_cloud":    is_sf_implementation and any(w in combined for w in ["service cloud", "case", "omni-channel", "knowledge", "field service", "entitlement"]),
        "experience_cloud": is_sf_implementation and any(w in combined for w in ["experience cloud", "community", "portal", "lwr", "aura", "self-service"]),
        "data_cloud":       is_sf_implementation and any(w in combined for w in ["data cloud", "cdp", "identity resolution", "segment", "activation", "data stream"]),
        # Discussion type flags
        "is_sf_implementation": is_sf_implementation,
        "is_auth_pattern":      any(w in combined for w in ["token", "oauth", "credential", "named credential", "jwt", "api key", "authentication"]),
        "is_integration":       any(w in combined for w in ["proxy", "api", "integration", "middleware", "webhook", "rest", "soap", "esb", "mulesoft"]),
        "is_pattern_review":    any(w in combined for w in ["pattern", "is this good", "best practice", "review", "evaluate", "architectural pattern"]),
    }


def _discovery_summary(state: AgentState) -> str:
    return "\n".join(
        f"- {q.question}: {q.answer}"
        for q in state.discovery_questions if q.answer
    )


# ── Step 1a: Perplexity — current facts, limits, citations ────────────────────

PERPLEXITY_SYSTEM_PROMPT = """You are a Salesforce technical research assistant with real-time
access to Salesforce documentation, Trailhead, release notes, and community resources.

Focus exclusively on CURRENT, VERIFIABLE facts:
- Exact governor limit values (as of the latest Salesforce release)
- Features that are GA vs Beta vs Pilot in the current release
- Known issues, deprecations, or migration requirements
- Recent Spring/Summer release changes relevant to the topics
- Cite every fact with its source (Salesforce Help URL, release note, or Trailhead)

Do not give architectural opinions — only verifiable, cited facts."""


def _gather_perplexity(state: AgentState, scope: dict) -> tuple:
    # Base topics always included when Salesforce is involved
    topics = []

    if scope["is_sf_implementation"]:
        topics += [
            "Salesforce governor limits 2026 — exact values: SOQL rows, DML statements, heap size, CPU time, API daily limits for Enterprise and Unlimited",
            "Salesforce Spring/Summer 2026 release highlights relevant to the clouds in scope",
            "Salesforce Permission Set Groups vs Profiles — current best practice and any deprecation timeline",
        ]

    # Auth / token pattern topics
    if scope["is_auth_pattern"]:
        topics += [
            "Salesforce Named Credentials and External Credentials 2026 — current recommended pattern for outbound API auth, token storage, and refresh",
            "Salesforce Platform Cache vs Custom Metadata vs Custom Settings for credential/token storage — current best practice 2026",
            "OAuth 2.0 client credentials flow in Salesforce 2026 — when to use, how to configure, token refresh strategies",
        ]

    # Integration / proxy pattern topics
    if scope["is_integration"]:
        topics += [
            "Salesforce outbound REST callout best practices 2026 — error handling, retry, timeout limits (120s callout timeout), Continuation for async patterns",
            "Salesforce callout governor limits 2026 — total callouts per transaction, cumulative timeout, concurrent limit",
            "API proxy patterns with Salesforce 2026 — when to use MuleSoft vs Apigee vs custom middleware, trade-offs",
        ]

    # If no specific topics detected, fall back to general architecture research
    if not topics:
        topics = [
            "Enterprise integration architecture best practices 2026 — API gateway patterns, proxy design, token management",
            "API security patterns 2026 — token passing, credential isolation, zero-trust principles",
            "Microservices and API proxy design patterns — industry standards and Salesforce-specific considerations",
        ]

    if scope["service_cloud"]:
        topics += [
            "Salesforce Omni-Channel routing limits and configuration 2026 — queue-based vs skills-based current limits",
            "Einstein for Service GA features 2026 — Einstein Classification, Article Recommendations, Bots, Copilot for Service",
            "Salesforce Service Cloud Voice 2026 — supported telephony partners, Amazon Connect limits",
            "Salesforce Knowledge limits and migration status 2026 — Classic vs Lightning Knowledge",
        ]

    if scope["experience_cloud"]:
        topics += [
            "Salesforce Experience Cloud LWR vs Aura 2026 — official recommendation and Aura end-of-life timeline if any",
            "Experience Cloud guest user security 2026 — current known CVEs, OWASP risks, Salesforce security advisories",
            "Experience Cloud licence types and limits 2026 — Customer Community, Partner Community, Digital Experiences per-user limits",
        ]

    if scope["data_cloud"]:
        topics += [
            "Salesforce Data Cloud identity resolution limits 2026 — matching rule types, accuracy considerations, known limitations",
            "Salesforce Data Cloud credits model 2026 — exact credit consumption rates by operation type",
            "Salesforce Data Cloud consent management 2026 — GDPR/CCPA compliance features, data retention configuration",
        ]

    topic_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))

    prompt = f"""Research these topics and return a citation-rich fact sheet.
For each topic: current value/status, relevant limits, any recent changes, source URL.

## Project scope (for context only)
{_discovery_summary(state)}

## Topics to research
{topic_list}"""

    llm = get_llm_for_slot("researcher_search", state.session_agent_config)
    response = invoke_with_retry(llm, [
        SystemMessage(content=PERPLEXITY_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    return (
        f"## SEARCH RESEARCH — Current Facts & Citations\n\n{response.content}",
        usage_record("researcher", slot_model("researcher_search", state.session_agent_config), getattr(response, "usage_metadata", None)),
    )


# ── Step 1b: Gemini — deep patterns, architectural reasoning ──────────────────

GEMINI_SYSTEM_PROMPT = """You are a Principal Salesforce Architect providing deep architectural
guidance based on platform best practices and proven design patterns.

Focus exclusively on ARCHITECTURAL PATTERNS and DESIGN DECISIONS:
- Recommended design patterns for the confirmed Salesforce clouds
- Integration architecture approaches and trade-offs
- Security model design (sharing model, permission architecture)
- Scalability and performance design considerations
- Deployment and release management patterns
- Salesforce Well-Architected Framework application

Do not focus on specific limit values — those will come from a separate research source.
Focus on HOW to design the system, not WHAT the current numbers are."""


def _gather_gemini(state: AgentState, scope: dict) -> tuple:
    topics = [
        "Salesforce Well-Architected Framework 2026 — how to apply Trust, Adaptability, Customer Success, and Efficiency pillars to a multi-cloud implementation",
        "Salesforce integration architecture patterns — when to use REST API vs Bulk API 2.0 vs Platform Events vs CDC vs Composite API",
        "Salesforce security architecture patterns — permission-set-first model, OWD design, sharing rule hierarchy best practices",
        "Salesforce CI/CD and DevOps patterns — Gearset vs Copado vs raw SFDX, scratch org strategy, sandbox org shape design",
    ]

    if scope["service_cloud"]:
        topics += [
            "Service Cloud architecture patterns — case model design, Omni-Channel routing strategy selection, channel architecture for multi-channel service",
            "Einstein for Service implementation patterns — training data requirements, phased rollout approach, bot design patterns",
            "Knowledge management architecture — data category hierarchy design, article lifecycle, unified Knowledge strategy across channels",
        ]

    if scope["experience_cloud"]:
        topics += [
            "Experience Cloud architecture patterns — LWR site design, component architecture, performance optimisation patterns",
            "Experience Cloud sharing model design — when to use sharing sets vs share groups vs Apex sharing, guest user security model",
            "Experience Cloud authentication architecture — SSO patterns, self-registration flows, identity provider integration",
        ]

    if scope["data_cloud"]:
        topics += [
            "Data Cloud architecture patterns — data ingestion design, DMO mapping strategy, identity resolution ruleset design",
            "Data Cloud to Service Cloud + Experience Cloud integration — unified profile strategy, activation patterns, real-time personalisation",
            "Data Cloud consent and privacy architecture — consent object design, GDPR/CCPA implementation patterns",
        ]

    topic_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))

    prompt = f"""Provide deep architectural guidance on these topics for a Salesforce implementation.
For each topic: recommended pattern, design rationale, key trade-offs, and when to deviate.

## Project scope (from discovery)
Brief: {state.project_brief}
{_discovery_summary(state)}

## Architectural topics
{topic_list}"""

    llm = get_llm_for_slot("researcher_reasoning", state.session_agent_config)
    response = invoke_with_retry(llm, [
        SystemMessage(content=GEMINI_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    return (
        f"## ARCHITECTURE RESEARCH — Patterns & Design Guidance\n\n{response.content}",
        usage_record("researcher", slot_model("researcher_reasoning", state.session_agent_config), getattr(response, "usage_metadata", None)),
    )


# ── Step 2: Claude — write the structured document ────────────────────────────

WRITER_SYSTEM_PROMPT = """You are a Principal Enterprise Architect writing a formal
Architecture Recommendation Document.

You have been given:
  1. A project brief and discovery answers (the confirmed requirements and context)
  2. A PERPLEXITY research brief — verified current facts, citations, platform limits
  3. A GEMINI research brief — deep architectural patterns and design guidance

────────────────────────────────────────────────────────────────
STEP 1 — IDENTIFY THE DISCUSSION TYPE

Read the brief and determine what kind of architecture document is needed.
Do NOT default to a full Salesforce Cloud implementation template for every session.

  • PATTERN REVIEW / DESIGN QUESTION → concise focused document (3–4 sections)
    Sections: Summary & Verdict | Design Analysis | Recommendations | Risks
    Length: 400–800 words. No Salesforce cloud sections unless relevant.

  • INTEGRATION / API ARCHITECTURE → integration-focused document
    Sections: Summary | Integration Design | Security & Auth | Error Handling |
              Operational Considerations | Risks
    Length: 600–1200 words.

  • SECURITY / AUTH DESIGN → security-focused document
    Sections: Summary | Current Design Assessment | Recommended Pattern |
              Implementation Guidance | Risks
    Length: 500–1000 words.

  • FULL SALESFORCE CLOUD IMPLEMENTATION → comprehensive 8-section document
    Use the full structure below ONLY when the session is about building on
    Salesforce Service Cloud, Experience Cloud, Data Cloud, or similar.

────────────────────────────────────────────────────────────────
FULL SALESFORCE IMPLEMENTATION STRUCTURE (use only when appropriate):

## 1. Executive Summary
   Business problem + recommended approach (3–5 sentences).
   Top 3 measurable outcomes. Headline licensing note. Top 2 risks + mitigations.

## 2. Architectural Goals & Constraints
   Goals from discovery. Hard constraints. Explicit assumptions.

## 3. Recommended Architecture
   Sub-section per confirmed cloud:
   ### 3a. Service Cloud (if confirmed)
   ### 3b. Experience Cloud (if confirmed)
   ### 3c. Data Cloud (if confirmed)
   ### 3d. Cross-Cloud Integration Design (if 2+ clouds)

## 4. Security Architecture
   Permission-set-first strategy. FLS. OWD. Connected App/OAuth. Guest user lockdown.

## 5. Technical Recommendations & Governor Limit Considerations
   Use EXACT limit values from the Perplexity research brief — never invent numbers.
   Async vs sync, bulkification, API strategy, Platform Events capacity, tech stack.

## 6. Deployment & Release Strategy
   Sandbox org shape. CI/CD tooling. Scratch orgs. Deployment sequencing.

## 7. Risk Register
   Table: Risk | Likelihood (H/M/L) | Impact (H/M/L) | Mitigation

## 8. Open Questions & Assumptions
────────────────────────────────────────────────────────────────

WRITING STANDARDS:
- Match document length and depth to the complexity of the question.
  A pattern review does not need 8 sections. A cloud implementation does.
- Use exact limit values from Perplexity research — never invent numbers.
- Architecture patterns: draw from Gemini research — cite the reasoning.
- Salesforce Well-Architected Framework: reference where genuinely applicable,
  not as a mandatory checkbox for every document.
- Executive sections (1–2): jargon-free. Technical sections (3–7): precise.
- Flag edition requirements and add-ons without inventing prices.
- Output as clean Markdown with tables where helpful.

ON REVISION:
- Add ## Revision Summary at the top listing every change.
- Mark each resolved comment: [RESOLVED: <original comment>]
- Do NOT rewrite sections that were not flagged."""


def _write_document(
    state: AgentState,
    perplexity_research: str,
    gemini_research: str,
) -> str:
    llm = get_llm_for_slot("researcher_writer", state.session_agent_config)

    discovery = _discovery_summary(state)

    if state.document_version == 0:
        user_prompt = f"""## Project Brief
{state.project_brief}

## Discovery Answers
{discovery}

## Research Context
{perplexity_research}

---

{gemini_research}

---

Using all of the above, produce the complete 8-section Architecture Recommendation Document.
Use exact limit values from the Perplexity research. Apply architectural patterns from the Gemini research."""

    else:
        approver_section = ""
        if state.approval_result:
            changes = "\n".join(f"  - {c}" for c in state.approval_result.required_changes)
            approver_section = f"""
## Approver Rejection Comments (ALL must be resolved)
{state.approval_result.comments}

Required changes:
{changes}"""

        reviewer_section = ""
        if state.review_result:
            issues = "\n".join(f"  - {i}" for i in state.review_result.critical_issues)
            reviewer_section = f"""
## Reviewer Feedback (ALL critical issues must be resolved)
{state.review_result.feedback}

Critical issues:
{issues}"""

        user_prompt = f"""## Prior Document (version {state.document_version})
{state.document_draft}
{approver_section}
{reviewer_section}

## Refreshed Research Context (re-run for this revision)
{perplexity_research}

---

{gemini_research}

---

Instructions:
1. Add ## Revision Summary at the top listing every change made.
2. Resolve every flagged item. Mark each: [RESOLVED: <comment>]
3. Do NOT rewrite sections that were not flagged — preserve verbatim.
4. Output the complete updated document."""

    # Researcher does NOT need conversation history — all context is already
    # structured in user_prompt: brief, discovery Q&A, research output, and
    # (on revision) the full prior document + feedback. Passing *state.messages
    # would only add noise from the discovery chat and revision logs.
    response = invoke_with_retry(llm, [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])

    return response.content, usage_record("researcher", slot_model("researcher_writer", state.session_agent_config), getattr(response, "usage_metadata", None))


# ── Node function ─────────────────────────────────────────────────────────────

def run_researcher(state: AgentState) -> dict:
    scope = _detect_scope(state)

    # Step 1: run Perplexity + Gemini in parallel — no extra latency cost
    with ThreadPoolExecutor(max_workers=2) as pool:
        perplexity_future = pool.submit(_gather_perplexity, state, scope)
        gemini_future     = pool.submit(_gather_gemini,     state, scope)

        perplexity_research, urec_pplx  = perplexity_future.result()
        gemini_research,     urec_gemini = gemini_future.result()

    # Step 2: Claude writes the document with both research outputs
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
                    f"Research: Perplexity (current facts) + Gemini (patterns) in parallel → Claude (writing)."
                )
            )
        ],
    }
