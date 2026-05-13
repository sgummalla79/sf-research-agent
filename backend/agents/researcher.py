"""
Stage 3 — Deep Research & Drafting Agent
Three-step approach with parallel research:

  Step 1a — researcher_search slot (default: Perplexity Sonar Pro, runs in parallel)
    Real-time web search: current platform limits, release notes, known issues,
    and citations from official vendor documentation.

  Step 1b — researcher_reasoning slot (default: Gemini 2.5 Pro, runs in parallel)
    Deep architectural reasoning with 1M token context.

  Steps 1a + 1b run concurrently — no extra latency cost.

  Step 2 — researcher_writer slot (default: Claude Sonnet)
    Receives both research outputs as combined context.
    Writes (or revises) the full Architecture Recommendation Document.
"""

from concurrent.futures import ThreadPoolExecutor

from utils.llm_retry import invoke_with_retry
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from utils.llm_factory import get_llm_for_slot, slot_model
from utils.pricing import usage_record
from state import AgentState

_YEAR = "2026"

# ── Shared scope detection ─────────────────────────────────────────────────────

def _detect_scope(state: AgentState) -> dict:
    """
    Detect which platforms are in scope and what type of architecture discussion
    this is, so each research step can ask the right platform-specific questions.
    """
    combined = (
        (state.project_brief or "") + " " +
        " ".join(q.answer or "" for q in state.discovery_questions)
    ).lower()

    # ── Platform detection ────────────────────────────────────────────────────
    platforms = {
        "salesforce":  any(w in combined for w in [
            "salesforce", "service cloud", "experience cloud", "data cloud",
            "sales cloud", "marketing cloud", "apex", "lwc", "soql", "visualforce",
            "salesforce org", "trailhead", "sfdx",
        ]),
        "servicenow":  any(w in combined for w in [
            "servicenow", "service now", "snow", "itsm", "itom", "hrsd", "csmm",
            "glide", "scoped app", "mid server", "integrationhub",
        ]),
        "microsoft":   any(w in combined for w in [
            "microsoft", "azure", "sharepoint", "teams", "dynamics 365",
            "power platform", "power apps", "power automate", "dataverse", "m365",
        ]),
        "workday":     any(w in combined for w in [
            "workday", "workday studio", "eib", "workday extend", "hcm workday",
            "workday financials", "adaptive planning",
        ]),
        "mulesoft":    any(w in combined for w in [
            "mulesoft", "anypoint", "cloudhub", "raml", "runtime fabric",
            "mule", "mulesoft api",
        ]),
        "sap":         any(w in combined for w in [
            "sap", "s/4hana", "s4hana", "btp", "abap", "fiori", "ariba",
        ]),
    }

    # ── Salesforce module detection (only when Salesforce is in scope) ────────
    sf_modules: dict = {}
    if platforms["salesforce"]:
        sf_modules = {
            "service_cloud":    any(w in combined for w in [
                "service cloud", "case", "omni-channel", "knowledge", "field service", "entitlement",
            ]),
            "experience_cloud": any(w in combined for w in [
                "experience cloud", "community", "portal", "lwr", "aura site", "self-service",
            ]),
            "data_cloud":       any(w in combined for w in [
                "data cloud", "cdp", "identity resolution", "segment", "activation", "data stream",
            ]),
        }

    # ── Discussion type detection (cross-platform) ────────────────────────────
    discussion = {
        "is_auth":        any(w in combined for w in [
            "token", "oauth", "credential", "jwt", "api key", "authentication",
            "named credential", "sso", "saml", "mfa",
        ]),
        "is_integration": any(w in combined for w in [
            "integration", "api", "proxy", "middleware", "webhook", "rest", "soap",
            "esb", "message bus", "event driven", "platform event",
        ]),
        "is_data":        any(w in combined for w in [
            "data model", "migration", "etl", "elt", "data lake", "warehouse",
            "sync", "replication", "cdc", "bulk",
        ]),
        "is_security":    any(w in combined for w in [
            "security", "permission", "access control", "compliance", "hipaa",
            "gdpr", "pci", "fedramp", "sharing", "profile", "role",
        ]),
        "is_performance": any(w in combined for w in [
            "performance", "scale", "governor", "throttle", "throughput",
            "latency", "cache", "async", "queue", "batch",
        ]),
    }

    return {**platforms, **discussion, "sf_modules": sf_modules}


def _discovery_summary(state: AgentState) -> str:
    return "\n".join(
        f"- {q.question}: {q.answer}"
        for q in state.discovery_questions if q.answer
    )


# ── Step 1a: Perplexity — current facts, limits, citations ────────────────────

def _gather_perplexity(state: AgentState, scope: dict) -> tuple:
    topics = []
    sf = scope.get("sf_modules", {})

    # ── Salesforce ────────────────────────────────────────────────────────────
    if scope["salesforce"]:
        topics += [
            f"Salesforce governor limits {_YEAR} — exact values: SOQL rows, DML statements, heap size, CPU time, API daily limits for Enterprise and Unlimited",
            f"Salesforce latest release GA features — what is now generally available vs beta",
        ]
        if sf.get("service_cloud"):
            topics += [
                f"Salesforce Service Cloud Omni-Channel routing limits {_YEAR} — queue-based vs skills-based current limits",
                f"Salesforce Knowledge limits and best practice {_YEAR} — Classic vs Lightning Knowledge status",
                f"Einstein for Service GA features {_YEAR} — Classification, Article Recommendations, Copilot for Service",
            ]
        if sf.get("experience_cloud"):
            topics += [
                f"Salesforce Experience Cloud LWR vs Aura {_YEAR} — official recommendation and Aura timeline",
                f"Experience Cloud guest user security {_YEAR} — current CVEs, OWASP risks, Salesforce advisories",
                f"Experience Cloud licence types and per-user limits {_YEAR}",
            ]
        if sf.get("data_cloud"):
            topics += [
                f"Salesforce Data Cloud identity resolution limits {_YEAR} — matching rules, accuracy, known limitations",
                f"Salesforce Data Cloud credits model {_YEAR} — exact consumption rates by operation type",
                f"Salesforce Data Cloud consent management {_YEAR} — GDPR/CCPA compliance features",
            ]

    # ── ServiceNow ────────────────────────────────────────────────────────────
    if scope["servicenow"]:
        topics += [
            f"ServiceNow platform limits and quotas {_YEAR} — API rate limits, script execution quotas, memory limits",
            f"ServiceNow latest release GA features — what is now generally available",
            f"ServiceNow integration options {_YEAR} — IntegrationHub vs REST Message vs MID Server — official guidance",
            f"ServiceNow scoped vs global application design — current best practice {_YEAR}",
        ]

    # ── Microsoft 365 / Power Platform ───────────────────────────────────────
    if scope["microsoft"]:
        topics += [
            f"Microsoft Power Platform limits {_YEAR} — API request limits, connector throttling, Dataverse storage quotas",
            f"Microsoft Azure integration service limits {_YEAR} — Logic Apps, Service Bus, Event Grid quotas",
            f"Microsoft 365 compliance and governance features {_YEAR} — DLP, sensitivity labels, Purview",
        ]

    # ── Workday ───────────────────────────────────────────────────────────────
    if scope["workday"]:
        topics += [
            f"Workday integration API limits and quotas {_YEAR} — EIB row limits, RaaS throttling, Studio constraints",
            f"Workday Extend platform capabilities and limitations {_YEAR}",
            f"Workday latest release GA features — what is now generally available",
        ]

    # ── MuleSoft ──────────────────────────────────────────────────────────────
    if scope["mulesoft"]:
        topics += [
            f"MuleSoft CloudHub 2.0 limits and sizing {_YEAR} — vCore allocation, message limits, replay windows",
            f"MuleSoft Anypoint Platform API limits {_YEAR} — client ID enforcement, rate limiting, SLA tiers",
        ]

    # ── SAP ───────────────────────────────────────────────────────────────────
    if scope["sap"]:
        topics += [
            f"SAP BTP limits and service quotas {_YEAR} — API Management, Integration Suite, HANA Cloud sizing",
            f"SAP S/4HANA integration best practices {_YEAR} — BTP Integration Suite vs direct RFC vs OData",
        ]

    # ── Cross-platform discussion types ───────────────────────────────────────
    if scope["is_auth"]:
        topics += [
            f"OAuth 2.0 patterns {_YEAR} — client credentials, PKCE, token refresh, storage best practices",
            "Zero-trust credential management — secrets manager, vault rotation, least-privilege patterns",
        ]

    if scope["is_security"]:
        topics += [
            f"OWASP API Security Top 10 {_YEAR} — current list and mitigation patterns",
            "Zero-trust architecture for SaaS and enterprise platform integrations",
        ]

    # ── Fallback: no specific platform detected ───────────────────────────────
    if not topics:
        topics = [
            f"Enterprise architecture best practices {_YEAR} — integration, security, scalability patterns",
            "Cloud architecture patterns — API gateway, event-driven, microservices trade-offs",
            "API security patterns — OAuth 2.0, mTLS, zero-trust principles",
        ]

    topic_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))

    prompt = (
        f"Research these topics and return a citation-rich fact sheet.\n"
        f"For each topic: current value/status, relevant limits, any recent changes, source URL.\n\n"
        f"## Project scope (for context only)\n{_discovery_summary(state)}\n\n"
        f"## Topics to research\n{topic_list}"
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

def _gather_gemini(state: AgentState, scope: dict) -> tuple:
    topics = []
    sf = scope.get("sf_modules", {})

    # ── Salesforce ────────────────────────────────────────────────────────────
    if scope["salesforce"]:
        topics += [
            "Salesforce Well-Architected Framework — Trust, Adaptability, Customer Success, Efficiency pillars applied to this context",
            "Salesforce integration patterns — REST API vs Bulk API vs Platform Events vs CDC vs Composite API — when to use each",
            "Salesforce security architecture — permission-set-first model, OWD design, sharing rule hierarchy",
            "Salesforce CI/CD and DevOps — SFDX, scratch org strategy, deployment pipeline design",
        ]
        if sf.get("service_cloud"):
            topics += [
                "Service Cloud architecture — case model design, Omni-Channel routing strategy, multi-channel service design",
                "Einstein for Service implementation — training data requirements, phased rollout, bot design patterns",
                "Knowledge management architecture — data category hierarchy, article lifecycle, unified Knowledge strategy",
            ]
        if sf.get("experience_cloud"):
            topics += [
                "Experience Cloud architecture — LWR site design, sharing model patterns, SSO integration",
                "Experience Cloud authentication — self-registration flows, identity provider integration patterns",
            ]
        if sf.get("data_cloud"):
            topics += [
                "Data Cloud architecture — data ingestion design, DMO mapping, identity resolution ruleset design",
                "Data Cloud integration with Service Cloud and Experience Cloud — unified profile, activation, real-time personalisation",
            ]

    # ── ServiceNow ────────────────────────────────────────────────────────────
    if scope["servicenow"]:
        topics += [
            "ServiceNow architecture patterns — scoped application design, table hierarchy, customisation vs configuration boundary",
            "ServiceNow integration architecture — IntegrationHub spoke design vs REST Message vs MID Server — decision framework",
            "ServiceNow ITSM process design — incident, change, problem management best practices",
            "ServiceNow upgrade strategy — avoiding customisation conflicts, upgrade ring and test approach",
        ]

    # ── Microsoft 365 / Power Platform ───────────────────────────────────────
    if scope["microsoft"]:
        topics += [
            "Power Platform architecture — Canvas vs Model-driven app design, Dataverse schema design, ALM strategy",
            "Microsoft 365 integration architecture — Graph API patterns, Teams extensibility, SharePoint integration design",
            "Azure integration services — Logic Apps vs Functions vs Service Bus vs Event Grid — decision framework",
        ]

    # ── Workday ───────────────────────────────────────────────────────────────
    if scope["workday"]:
        topics += [
            "Workday integration architecture — EIB vs Studio vs Cloud Connect vs Extend — decision framework",
            "Workday data model patterns — business object design, calculated fields, custom report types",
            "Workday security architecture — domain security policies, functional areas, intersection security",
        ]

    # ── MuleSoft ──────────────────────────────────────────────────────────────
    if scope["mulesoft"]:
        topics += [
            "MuleSoft API-led connectivity — Experience / Process / System layer design and anti-patterns",
            "MuleSoft error handling architecture — dead letter queue, retry policies, circuit breaker patterns",
            "MuleSoft deployment architecture — CloudHub 2.0 vs Runtime Fabric — when to use each",
        ]

    # ── SAP ───────────────────────────────────────────────────────────────────
    if scope["sap"]:
        topics += [
            "SAP BTP architecture patterns — Integration Suite design, API Management, event mesh",
            "SAP S/4HANA extension patterns — side-by-side vs in-app extension, Clean Core principles",
        ]

    # ── Cross-platform discussion types ───────────────────────────────────────
    if scope["is_integration"]:
        topics += [
            "Enterprise integration patterns — synchronous vs asynchronous, at-least-once vs exactly-once, idempotency design",
            "API design best practices — versioning, pagination, error codes, backward compatibility",
        ]

    if scope["is_auth"]:
        topics += [
            "Authentication architecture patterns — OAuth 2.0 flows, token refresh, credential rotation, storage design",
        ]

    if scope["is_performance"]:
        topics += [
            "Performance and scalability patterns — async processing, caching strategies, queue-based load levelling",
        ]

    # ── Fallback: no specific platform or discussion type detected ────────────
    if not topics:
        topics = [
            "Cloud architecture patterns — API gateway, event-driven, microservices, serverless — when each is appropriate",
            "Security architecture principles — zero trust, defence in depth, least privilege",
            "Data architecture patterns — event sourcing, CQRS, saga, outbox pattern",
        ]

    topic_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))

    prompt = (
        f"Provide deep architectural guidance on these topics.\n"
        f"For each: recommended pattern, design rationale, key trade-offs, and when to deviate.\n\n"
        f"## Project scope (from discovery)\n"
        f"Brief: {state.project_brief}\n{_discovery_summary(state)}\n\n"
        f"## Architectural topics\n{topic_list}"
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
            f"## Refreshed Research Context (re-run for this revision)\n"
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
    scope = _detect_scope(state)

    # Step 1: run search + reasoning in parallel — no extra latency cost
    with ThreadPoolExecutor(max_workers=2) as pool:
        perplexity_future = pool.submit(_gather_perplexity, state, scope)
        gemini_future     = pool.submit(_gather_gemini,     state, scope)

        perplexity_research, urec_pplx   = perplexity_future.result()
        gemini_research,     urec_gemini = gemini_future.result()

    # Step 2: write the document with both research outputs
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
                    f"Research: Search (current facts) + Reasoning (patterns) in parallel → Writer."
                )
            )
        ],
    }
