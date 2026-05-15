"""
Smart model selection per agent key.

Each agent maps to a slot via skill.manifest.agent_slot_map.
Each slot has an ordered provider preference and best-model-per-provider mapping.

Priority at execution start:
  1. Snapshot model override (from conversation_skill_agents) → used if provider connected
  2. User's saved model config → used if provider connected
  3. Smart pick from connected providers using slot preference
"""

# Best model per provider per slot
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


def available_providers(user_keys: dict) -> set[str]:
    """Return provider IDs for which the user has a non-empty decrypted key."""
    providers: set[str] = set()
    for key_name, key_value in user_keys.items():
        if not key_value:
            continue
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
    Raises ValueError if no providers are connected.
    """
    preference = _SLOT_PREFERENCE.get(slot, _DEFAULT_PREFERENCE)
    for provider in preference:
        if provider in connected:
            models = _PROVIDER_SLOT_MODEL.get(provider, {})
            model  = models.get(slot) or models.get("default", "")
            if model:
                return {"provider": provider, "model": model}

    for provider in connected:
        models = _PROVIDER_SLOT_MODEL.get(provider, {})
        model  = models.get("default", "")
        if model:
            return {"provider": provider, "model": model}

    raise ValueError(
        "No LLM providers are configured. "
        "Go to Settings → Providers and connect at least one provider."
    )


def smart_pick_for_agent(agent_key: str, slot: str, connected: set[str]) -> dict:
    """Smart pick for a specific agent using its slot's preference order."""
    return smart_pick(slot, connected)


def resolve_agent_config(
    agent_slot_map: dict[str, str],   # {agent_key: slot} from skill manifest
    snapshot_cfg:   dict[str, dict],  # {agent_key: {provider, model}} from conversation_skill_agents
    connected:      set[str],
) -> dict[str, dict]:
    """
    Resolve the final per-agent config for an execution.

    For each agent:
      - If snapshot has a valid (non-null) provider that is connected → use it
      - Otherwise → smart_pick from connected providers using the agent's slot
    """
    resolved: dict[str, dict] = {}
    for agent_key, slot in agent_slot_map.items():
        snapshot = snapshot_cfg.get(agent_key, {})
        provider = snapshot.get("provider") if snapshot else None
        model    = snapshot.get("model")    if snapshot else None

        if provider and model and provider in connected:
            resolved[agent_key] = {"provider": provider, "model": model}
        else:
            resolved[agent_key] = smart_pick(slot, connected)

    return resolved
