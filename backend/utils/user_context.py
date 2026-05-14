"""
Per-request user context via Python contextvars.

LangGraph nodes run deep in the async call stack and cannot receive the
HTTP request object.  We solve this by storing the calling user's decrypted
API keys in a ContextVar at the start of every authenticated request.
asyncio.create_task() copies the current context, so background tasks
created within the request handler also inherit the correct keys.
"""

import logging
from contextvars import ContextVar

log = logging.getLogger(__name__)

_user_keys:        ContextVar[dict] = ContextVar("user_keys",        default={})
_anthropic_mode:   ContextVar[str]  = ContextVar("anthropic_mode",   default="direct")


def set_user_context(keys: dict, anthropic_mode: str = "direct") -> None:
    _user_keys.set(keys)
    _anthropic_mode.set(anthropic_mode)


def _lc_configurable() -> dict:
    """
    Return the LangChain runnable config's 'configurable' dict for the current
    execution context.  This is set by LangChain's run_in_executor and propagates
    correctly into synchronous node threads where our own _user_keys ContextVar
    is unavailable (lost through LangGraph's internal asyncio.create_task).
    """
    try:
        from langchain_core.runnables.config import var_child_runnable_config
        cfg = var_child_runnable_config.get({})
        return cfg.get("configurable") or {}
    except Exception:
        return {}


def _resolve_keys() -> dict:
    """Return the best available user-keys dict for this execution context."""
    keys = _user_keys.get()
    if keys:
        return keys
    # Fallback for LangGraph node threads where ContextVar is not propagated
    injected = _lc_configurable().get("_pragna_user_keys")
    if injected:
        log.debug("_resolve_keys: using injected keys from LangChain config")
        return injected
    return {}


def get_user_key(provider: str) -> str:
    keys = _resolve_keys()
    value = keys.get(provider)
    log.info("get_user_key  provider=%s  found=%s  keys_present=%s  via_lc=%s",
             provider, bool(value), list(keys.keys()), not bool(_user_keys.get()))
    if not value:
        raise RuntimeError(
            f"API key not configured for '{provider}'. "
            "Open Settings → Providers and connect this provider."
        )
    return value


def get_anthropic_mode() -> str:
    mode = _anthropic_mode.get()
    if mode != "direct":
        return mode
    # Also check injected config for bedrock mode
    injected_mode = _lc_configurable().get("_pragna_anthropic_mode")
    return injected_mode or mode


def has_key(provider: str) -> bool:
    return bool(_resolve_keys().get(provider))


def connected_providers() -> set[str]:
    """Return the set of providers for which a decrypted key exists in this request context."""
    from framework.defaults import available_providers
    return available_providers(_resolve_keys())
