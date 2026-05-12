"""
In-memory cache for provider model lists.

Populated on startup from DB and refreshed when a provider is connected / refreshed.
Agents and the Agent Config UI read from this to know which models are available.
"""

_cache: dict[str, list[str]] = {}


def populate_models_cache(provider_models: dict[str, list[str]]) -> None:
    """Replace the entire in-memory model cache."""
    _cache.clear()
    _cache.update({k: list(v) for k, v in provider_models.items() if v})


def get_provider_models(provider_id: str) -> list[str]:
    """Return the cached model list for a provider (empty list if not loaded)."""
    return list(_cache.get(provider_id, []))


def get_all_provider_models() -> dict[str, list[str]]:
    """Return a mutable copy of the full cache (provider_id → model list)."""
    return {k: list(v) for k, v in _cache.items()}
