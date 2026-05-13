"""
Per-request user context via Python contextvars.

LangGraph nodes run deep in the async call stack and cannot receive the
HTTP request object.  We solve this by storing the calling user's decrypted
API keys in a ContextVar at the start of every authenticated request.
asyncio.create_task() copies the current context, so background tasks
created within the request handler also inherit the correct keys.
"""

from contextvars import ContextVar

_user_keys:        ContextVar[dict] = ContextVar("user_keys",        default={})
_anthropic_mode:   ContextVar[str]  = ContextVar("anthropic_mode",   default="direct")


def set_user_context(keys: dict, anthropic_mode: str = "direct") -> None:
    _user_keys.set(keys)
    _anthropic_mode.set(anthropic_mode)


def get_user_key(provider: str) -> str:
    value = _user_keys.get().get(provider)
    if not value:
        raise RuntimeError(
            f"API key not configured for '{provider}'. "
            "Open Settings → Providers and connect this provider."
        )
    return value


def get_anthropic_mode() -> str:
    return _anthropic_mode.get()


def has_key(provider: str) -> bool:
    return bool(_user_keys.get().get(provider))
