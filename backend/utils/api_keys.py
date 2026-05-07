"""
API key management — Fernet encryption at rest, in-memory cache for agents.

Keys are stored encrypted in the app_settings DB table.
A module-level cache holds decrypted values so agent nodes can read synchronously.

Generate SETTINGS_SECRET once with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os
from cryptography.fernet import Fernet

KEY_NAMES = ["anthropic", "perplexity", "google"]

KEY_LABELS = {
    "anthropic":  "Anthropic API Key (Claude — Intake, Discovery, Research, Review, Approver)",
    "perplexity": "Perplexity API Key (Research Agent — live web search)",
    "google":     "Google API Key (Research Agent — Gemini architectural patterns)",
}

_cache: dict[str, str] = {}


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


def get_keys() -> dict[str, str]:
    """
    Return plain-text keys. Raises RuntimeError with a user-friendly message if any
    required key is missing. Called synchronously by agent nodes.
    """
    missing = [k for k in KEY_NAMES if not _cache.get(k)]
    if missing:
        labels = ", ".join(KEY_LABELS[k].split(" (")[0] for k in missing)
        raise RuntimeError(
            f"API keys not configured: {labels}. "
            "Open Settings (avatar menu) and save your API keys before starting a session."
        )
    return dict(_cache)


def all_configured() -> bool:
    return all(_cache.get(k) for k in KEY_NAMES)
