"""
Central logging configuration for Pragna backend.

Call configure_logging() once at application startup (before any other imports
that use logging). After that, every module gets a properly formatted logger
via logging.getLogger(__name__).

Format (stdout — K8s / Docker captures it):
    2026-05-14T07:12:01.234Z  INFO  api.middleware  POST /api/chat/start  200  143ms  user=auth0|xxx

Sensitive data is never logged:
  - Auth tokens / JWT payloads
  - API keys or encrypted values
  - Passwords or secrets
"""

import logging
import sys
from datetime import datetime, timezone


# ── Custom formatter ──────────────────────────────────────────────────────────

class _Fmt(logging.Formatter):
    LEVEL_WIDTH = 8
    COLORS = {
        logging.DEBUG:    "\033[36m",   # cyan
        logging.INFO:     "\033[32m",   # green
        logging.WARNING:  "\033[33m",   # yellow
        logging.ERROR:    "\033[31m",   # red
        logging.CRITICAL: "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_color: bool = True):
        super().__init__()
        self._color = use_color

    def format(self, record: logging.LogRecord) -> str:
        ts    = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        level = record.levelname.ljust(self.LEVEL_WIDTH)
        name  = record.name.ljust(24)
        msg   = record.getMessage()

        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        if self._color and sys.stderr.isatty():
            col   = self.COLORS.get(record.levelno, "")
            level = f"{col}{level}{self.RESET}"

        return f"{ts}  {level}  {name}  {msg}"


# ── Configure ─────────────────────────────────────────────────────────────────

def configure_logging(level: str = "INFO") -> None:
    """
    Set up root logger. Call once at startup before other project imports.
    Silences noisy third-party loggers that pollute the output.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any handlers uvicorn/gunicorn already attached
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_Fmt(use_color=True))
    root.addHandler(handler)

    # ── Silence noisy third-party loggers ─────────────────────────────────────
    for noisy in (
        "httpx",
        "httpcore",
        "openai._base_client",
        "anthropic._base_client",
        "langchain",
        "langchain_core",
        "langchain_anthropic",
        "langchain_openai",
        "langchain_google_genai",
        "langgraph",
        "psycopg",
        "psycopg_pool",
        "urllib3",
        "asyncio",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # uvicorn access log is replaced by our middleware — silence its default
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
