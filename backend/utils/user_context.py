"""
Per-request user context via Python contextvars + session-scoped key store.

LangGraph nodes run deep in the async call stack and cannot receive the
HTTP request object.  We use two mechanisms:

1. ContextVar — works for async code and threads created directly from the
   request's asyncio task.

2. Session key store — a plain dict keyed by session_id that survives across
   all asyncio/thread context boundaries.  This is the definitive fallback for
   LangGraph nodes running inside ThreadPoolExecutor threads that do NOT inherit
   the request's ContextVar (lost via LangGraph's internal asyncio.create_task).

Nodes read keys via _resolve_keys() which tries ContextVar first (fast path),
then the session store.  fanout.py also calls set_user_context() explicitly at
the start of each run_branch thread as a belt-and-suspenders guard.
"""

import logging
import threading
from contextvars import ContextVar

log = logging.getLogger(__name__)

_user_keys:      ContextVar[dict] = ContextVar("user_keys",      default={})
_anthropic_mode: ContextVar[str]  = ContextVar("anthropic_mode", default="direct")

# Session-scoped store: {session_id: {"keys": {...}, "mode": "direct"|"bedrock"}}
# Written at request start, read inside node threads regardless of context propagation.
_session_store:      dict[str, dict] = {}
_session_store_lock: threading.Lock  = threading.Lock()


def set_user_context(keys: dict, anthropic_mode: str = "direct") -> None:
    _user_keys.set(keys)
    _anthropic_mode.set(anthropic_mode)


def register_session_keys(session_id: str, keys: dict, mode: str = "direct") -> None:
    """Store decrypted keys for a session so node threads can retrieve them."""
    if not session_id or not keys:
        return
    with _session_store_lock:
        _session_store[session_id] = {"keys": keys, "mode": mode}
    log.debug("register_session_keys  session=%s  providers=%s", session_id, list(keys.keys()))


def unregister_session_keys(session_id: str) -> None:
    """Remove session keys once a stream ends (cleanup, not strictly required)."""
    with _session_store_lock:
        _session_store.pop(session_id, None)


def get_session_keys(session_id: str) -> dict:
    with _session_store_lock:
        return _session_store.get(session_id, {}).get("keys", {})


def get_session_mode(session_id: str) -> str:
    with _session_store_lock:
        return _session_store.get(session_id, {}).get("mode", "direct")


def _resolve_keys(session_id: str = "") -> dict:
    """
    Return the best available user-keys dict for this execution context.
    Priority: ContextVar → session store.
    """
    keys = _user_keys.get()
    if keys:
        return keys
    if session_id:
        stored = get_session_keys(session_id)
        if stored:
            log.debug("_resolve_keys  using session store  session=%s", session_id)
            return stored
    return {}


def get_user_key(provider: str) -> str:
    keys = _user_keys.get()
    value = keys.get(provider) if keys else None
    log.info("get_user_key  provider=%s  found=%s  keys_present=%s",
             provider, bool(value), list(keys.keys()))
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


def connected_providers() -> set[str]:
    """Return the set of providers for which a decrypted key exists in this request context."""
    from framework.defaults import available_providers
    return available_providers(_user_keys.get())
