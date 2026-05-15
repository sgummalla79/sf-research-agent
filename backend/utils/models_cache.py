"""
Fetch available models from LLM provider APIs.
Results are cached in user_config by the providers route.
"""

from __future__ import annotations


async def fetch_models(provider_id: str) -> list[dict]:
    """Return [{id, name}] for available models from the given provider."""
    from utils.user_api_keys import get_key

    if provider_id == "anthropic":
        return [
            {"id": "claude-opus-4-7",         "name": "Claude Opus 4.7"},
            {"id": "claude-sonnet-4-6",        "name": "Claude Sonnet 4.6"},
            {"id": "claude-haiku-4-5-20251001","name": "Claude Haiku 4.5"},
        ]

    if provider_id == "google":
        return [
            {"id": "gemini-2.5-pro",   "name": "Gemini 2.5 Pro"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        ]

    if provider_id == "perplexity":
        return [
            {"id": "sonar-pro",        "name": "Sonar Pro"},
            {"id": "sonar",            "name": "Sonar"},
        ]

    if provider_id == "openai":
        return [
            {"id": "gpt-4o",       "name": "GPT-4o"},
            {"id": "gpt-4o-mini",  "name": "GPT-4o Mini"},
        ]

    return []
