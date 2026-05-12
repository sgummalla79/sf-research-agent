"""
Per-agent LLM configuration — in-memory cache for agent slot → provider/model mappings.

Agents read from this cache synchronously via get_slot_config(slot).
The cache is populated on startup from DB and refreshed when settings are saved.
"""

AGENT_SLOTS = [
    "intake",
    "discovery",
    "researcher_search",
    "researcher_reasoning",
    "researcher_writer",
    "reviewer",
    "approver",
]

SLOT_LABELS = {
    "intake":               "Intake Agent",
    "discovery":            "Discovery Agent",
    "researcher_search":    "Research: Web Search",
    "researcher_reasoning": "Research: Architecture",
    "researcher_writer":    "Research: Document Writer",
    "reviewer":             "Review Agent",
    "approver":             "Approver Agent",
}

# Available models per provider — update as new models are released
PROVIDER_MODELS: dict[str, list[str]] = {
    "anthropic": [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "google": [
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ],
    "perplexity": [
        "sonar-pro",
        "sonar",
        "sonar-reasoning-pro",
    ],
}

# Defaults match the current hardcoded behaviour
DEFAULT_AGENT_CONFIG: dict[str, dict] = {
    "intake":               {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "discovery":            {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "researcher_search":    {"provider": "perplexity", "model": "sonar-pro"},
    "researcher_reasoning": {"provider": "google",     "model": "gemini-2.5-pro"},
    "researcher_writer":    {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "reviewer":             {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "approver":             {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
}

_cache: dict[str, dict] = {k: dict(v) for k, v in DEFAULT_AGENT_CONFIG.items()}


def populate_agent_config(config: dict) -> None:
    """Load agent config into in-memory cache. Unknown slots are ignored; model names are
    trusted as-is (validation against fetched model lists happens at save time)."""
    _cache.clear()
    _cache.update({k: dict(v) for k, v in DEFAULT_AGENT_CONFIG.items()})
    for slot, cfg in config.items():
        if slot not in AGENT_SLOTS:
            continue
        provider = cfg.get("provider", "")
        model    = cfg.get("model", "")
        if provider in PROVIDER_MODELS and model:
            _cache[slot] = {"provider": provider, "model": model}


def get_agent_config() -> dict:
    """Return a copy of the full agent config dict."""
    return {k: dict(v) for k, v in _cache.items()}


def get_slot_config(slot: str) -> dict:
    """Return {provider, model} for a specific agent slot."""
    return dict(_cache.get(slot, DEFAULT_AGENT_CONFIG[slot]))
