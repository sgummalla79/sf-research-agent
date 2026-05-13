"""
API key management — Fernet encryption at rest, in-memory cache for agents.

Keys are stored encrypted in the app_settings DB table.
A module-level cache holds decrypted values so agent nodes can read synchronously.

Generate SETTINGS_SECRET once with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os
from cryptography.fernet import Fernet
from utils.provider_registry import PROVIDER_ORDER, PROVIDERS

# All supported provider IDs — drives key storage and UI display
KEY_NAMES: list[str] = PROVIDER_ORDER

KEY_LABELS: dict[str, str] = {pid: PROVIDERS[pid]["key_label"] for pid in PROVIDER_ORDER}

_cache: dict[str, str] = {}
_config_cache: dict[str, str] = {}


def _fernet() -> Fernet:
    secret = os.environ.get("SETTINGS_SECRET", "")
    if not secret:
        raise RuntimeError(
            "SETTINGS_SECRET env var is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(secret.encode() if isinstance(secret, str) else secret)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def populate_cache(decrypted: dict[str, str]) -> None:
    """Load plain-text keys into the in-memory cache. Called on startup and after every save."""
    _cache.clear()
    _cache.update({k: v for k, v in decrypted.items() if v})


def populate_config_cache(config: dict[str, str]) -> None:
    """Load plain-text config values into the in-memory config cache."""
    _config_cache.update({k: v for k, v in config.items() if v is not None})


def get_anthropic_mode() -> str:
    """Return 'bedrock' or 'direct' (default) for the active Anthropic auth mode."""
    return _config_cache.get("anthropic_mode", "direct")


def get_keys() -> dict[str, str]:
    """Return all available plain-text keys (no validation — agents use get_key instead)."""
    return dict(_cache)


def get_key(provider: str) -> str:
    """Return a single decrypted API key. Raises RuntimeError with user-friendly message if missing."""
    value = _cache.get(provider)
    if not value:
        label = KEY_LABELS.get(provider, provider)
        raise RuntimeError(
            f"API key not configured: {label}. "
            "Open Settings → Providers and connect this provider before starting a session."
        )
    return value


def is_configured(provider: str) -> bool:
    """Return True if the given provider has a key in the cache."""
    return bool(_cache.get(provider))


def all_configured() -> bool:
    """Return True only if ALL providers have keys (rarely needed — use is_configured per provider)."""
    return all(_cache.get(k) for k in KEY_NAMES)
