"""
Smart model defaults per LLM slot.

Used at session start when a skill stage has no explicit per-agent model_config
(null in DB) and the global agent_config doesn't cover the slot either.

Mirrors the SLOT_SUGGESTIONS map in AgentPromptsSettings.vue so the frontend
"Suggest" button and the backend execution default are always in sync.

Rules:
  - researcher_search   → Perplexity Sonar Pro  (live web search capability)
  - researcher_reasoning → Gemini 2.5 Pro        (1M context, deep pattern analysis)
  - approver            → Claude Opus 4.7        (strategic review, highest reasoning)
  - all others          → Claude Sonnet 4.6      (balanced reasoning + speed)
"""

SMART_SLOT_DEFAULTS: dict[str, dict] = {
    "intake":               {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "discovery":            {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "reviewer":             {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
    "approver":             {"provider": "anthropic",  "model": "claude-opus-4-7"},
    "researcher_search":    {"provider": "perplexity", "model": "sonar-pro"},
    "researcher_reasoning": {"provider": "google",     "model": "gemini-2.5-pro"},
    "researcher_writer":    {"provider": "anthropic",  "model": "claude-sonnet-4-6"},
}


def resolve_slot_model(slot: str, agent_cfg: dict) -> dict | None:
    """
    Return the model config for a slot, falling back to smart defaults
    if the slot is not present in the provided agent_cfg.

    Priority:
      1. agent_cfg[slot]              (global config or per-agent override)
      2. SMART_SLOT_DEFAULTS[slot]    (framework smart default)
      3. None                         (caller must handle)
    """
    if slot in agent_cfg:
        return agent_cfg[slot]
    return SMART_SLOT_DEFAULTS.get(slot)
