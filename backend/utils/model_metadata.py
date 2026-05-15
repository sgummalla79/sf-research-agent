"""
Static model metadata — context window, capabilities, pricing tier.
"""

_MODEL_INFO: dict[str, dict] = {
    "claude-opus-4-7":          {"context_window": 200_000, "provider": "anthropic"},
    "claude-sonnet-4-6":        {"context_window": 200_000, "provider": "anthropic"},
    "claude-haiku-4-5-20251001":{"context_window": 200_000, "provider": "anthropic"},
    "gemini-2.5-pro":           {"context_window": 1_000_000, "provider": "google"},
    "gemini-2.0-flash":         {"context_window": 1_000_000, "provider": "google"},
    "sonar-pro":                {"context_window": 127_072, "provider": "perplexity"},
    "sonar":                    {"context_window": 127_072, "provider": "perplexity"},
    "gpt-4o":                   {"context_window": 128_000, "provider": "openai"},
    "gpt-4o-mini":              {"context_window": 128_000, "provider": "openai"},
}


def get_model_info(provider: str, model: str) -> dict | None:
    info = _MODEL_INFO.get(model)
    if info:
        return {"provider": provider, "model": model, **info}
    return None
