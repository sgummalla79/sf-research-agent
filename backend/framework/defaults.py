"""
Smart model selection per LLM slot.

At session start, each slot is resolved against the user's CONNECTED providers.
No provider is assumed — the system works with whatever the user has configured.

Priority:
  1. User explicitly configured this slot → use it; error if provider not connected
  2. User never configured → smart_pick() from connected providers

Smart pick preference per slot (ordered by fit):
  researcher_search    → perplexity (web search) → google → anthropic → openai
  researcher_reasoning → google (1M context)     → anthropic → openai → perplexity
  approver             → anthropic (Opus)         → google → openai → perplexity
  all others           → anthropic (Sonnet)       → google → openai → perplexity
"""

from fastapi import HTTPException

# Best model per provider per slot (slot-specific overrides, else 'default')
_PROVIDER_SLOT_MODEL: dict[str, dict[str, str]] = {
    "anthropic": {
        "default":  "claude-sonnet-4-6",
        "approver": "claude-opus-4-7",
    },
    "google": {
        "default":              "gemini-2.0-flash",
        "researcher_reasoning": "gemini-2.5-pro",
    },
    "perplexity": {
        "default":           "sonar-pro",
        "researcher_search": "sonar-pro",
    },
    "openai": {
        "default": "gpt-4o",
    },
}

# Ordered provider preference per slot
_SLOT_PREFERENCE: dict[str, list[str]] = {
    "researcher_search":    ["perplexity", "google", "anthropic", "openai"],
    "researcher_reasoning": ["google",     "anthropic", "openai", "perplexity"],
    "approver":             ["anthropic",  "google",    "openai", "perplexity"],
}
_DEFAULT_PREFERENCE = ["anthropic", "google", "openai", "perplexity"]


# ── Public API ────────────────────────────────────────────────────────────────

SMART_SLOT_DEFAULTS: dict[str, dict] = {
    "intake":               {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "discovery":            {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "reviewer":             {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "approver":             {"provider": "anthropic",  "model": "claude-opus-4-7"},
    "researcher_search":    {"provider": "perplexity", "model": "sonar-pro"},
    "researcher_reasoning": {"provider": "google",     "model": "gemini-2.5-pro"},
    "researcher_writer":    {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
}


def available_providers(user_keys: dict) -> set[str]:
    """Return the set of provider IDs the user has connected API keys for."""
    providers: set[str] = set()
    for key_name in user_keys:
        if key_name.startswith("anthropic"):
            providers.add("anthropic")
        elif key_name.startswith("google"):
            providers.add("google")
        elif key_name.startswith("perplexity"):
            providers.add("perplexity")
        elif key_name.startswith("openai"):
            providers.add("openai")
        elif key_name.startswith("groq"):
            providers.add("groq")
        elif key_name.startswith("mistral"):
            providers.add("mistral")
    return providers


def smart_pick(slot: str, connected: set[str]) -> dict:
    """
    Pick the best available provider/model for a slot from connected providers.
    Raises ValueError if no providers are connected at all.
    """
    preference = _SLOT_PREFERENCE.get(slot, _DEFAULT_PREFERENCE)
    for provider in preference:
        if provider in connected:
            models = _PROVIDER_SLOT_MODEL.get(provider, {})
            model  = models.get(slot) or models.get("default", "")
            if model:
                return {"provider": provider, "model": model}

    # Last resort: any connected provider
    for provider in connected:
        models = _PROVIDER_SLOT_MODEL.get(provider, {})
        model  = models.get("default", "")
        if model:
            return {"provider": provider, "model": model}

    raise ValueError(
        "No LLM providers are configured. "
        "Go to Settings → Providers and connect at least one provider."
    )


def resolve_agent_config(
    slots:        list[str],
    user_cfg:     dict,          # from user's saved agent_config
    snapshot_cfg: dict,          # per-agent overrides from skill snapshot
    connected:    set[str],      # providers the user has API keys for
    user_cfg_explicit: set[str], # slots the user explicitly set (vs default)
) -> dict:
    """
    Resolve the final per-slot config for a session.

    For each slot:
      - If user explicitly set it and provider is connected → use it
      - If user explicitly set it and provider NOT connected → HTTP 422
      - Otherwise → smart_pick from connected providers
    """
    resolved: dict = {}

    for slot in slots:
        # Snapshot per-agent overrides take highest priority
        desired = snapshot_cfg.get(slot) or user_cfg.get(slot)

        if desired:
            provider = desired.get("provider", "")
            if provider in connected:
                resolved[slot] = desired
            elif slot in user_cfg_explicit:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Slot '{slot}' is configured to use provider '{provider}' "
                        f"but that provider is not connected. "
                        f"Go to Settings → Providers to connect it, "
                        f"or update the agent config in Settings → Configuration."
                    ),
                )
            else:
                # Default pointed to unavailable provider — auto-pick
                resolved[slot] = smart_pick(slot, connected)
        else:
            resolved[slot] = smart_pick(slot, connected)

    return resolved


def resolve_slot_model(slot: str, agent_cfg: dict) -> dict | None:
    """Legacy helper — prefer resolve_agent_config() for new code."""
    if slot in agent_cfg:
        return agent_cfg[slot]
    return SMART_SLOT_DEFAULTS.get(slot)
