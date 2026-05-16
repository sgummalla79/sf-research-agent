"""
Central logging configuration for the Pragna backend.

Features:
  - Correlation ID injected into every log line via a ContextVar + Filter.
    Set once per request in RequestLoggerMiddleware; all loggers pick it up
    automatically — no changes needed in individual modules.
  - Structured, coloured stdout format (K8s / Docker friendly).
  - Sensitive data is NEVER logged:
      - Request/response payloads
      - Authorization / Cookie headers
      - API keys, encrypted values, passwords, secrets

Usage:
    log = logging.getLogger(__name__)
    log.info("something happened")
    # output includes correlation_id automatically
"""

import logging
import logging.handlers
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

# ── Correlation ID ─────────────────────────────────────────────────────────────

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


def new_correlation_id() -> str:
    cid = uuid.uuid4().hex[:12]
    set_correlation_id(cid)
    return cid


# ── Filter: injects correlation_id into every LogRecord ───────────────────────

class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        return True


# ── Formatter ─────────────────────────────────────────────────────────────────

class _Fmt(logging.Formatter):
    LEVEL_WIDTH = 8
    COLORS = {
        logging.DEBUG:    "\033[36m",
        logging.INFO:     "\033[32m",
        logging.WARNING:  "\033[33m",
        logging.ERROR:    "\033[31m",
        logging.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"

    def __init__(self, use_color: bool = True):
        super().__init__()
        self._color = use_color

    def format(self, record: logging.LogRecord) -> str:
        ts    = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        level = record.levelname.ljust(self.LEVEL_WIDTH)
        name  = record.name.ljust(24)
        cid   = getattr(record, "correlation_id", "-")
        msg   = record.getMessage()

        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        if self._color and sys.stdout.isatty():
            col   = self.COLORS.get(record.levelno, "")
            level = f"{col}{level}{self.RESET}"

        return f"{ts}  {level}  {name}  [{cid}]  {msg}"


# ── Configure ─────────────────────────────────────────────────────────────────

def configure_logging(level: str = "INFO") -> None:
    """
    Set up root logger with:
    - stdout handler (for whatever shows in console)
    - rotating file handler: backend/logs/pragna.log, splits every hour, keeps 7 days
    Both include correlation ID via _CorrelationFilter.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()

    fmt    = _Fmt(use_color=False)   # no ANSI in files
    fmt_tty = _Fmt(use_color=True)
    filt   = _CorrelationFilter()

    # ── stdout handler ────────────────────────────────────────────────────────
    stdout_h = logging.StreamHandler(sys.stdout)
    stdout_h.setFormatter(fmt_tty)
    stdout_h.addFilter(filt)
    root.addHandler(stdout_h)

    # ── rotating file handler (1-hour splits, 7 days retention) ──────────────
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "pragna.log"

    file_h = logging.handlers.TimedRotatingFileHandler(
        filename    = log_file,
        when        = "h",        # rotate every hour
        interval    = 1,
        backupCount = 24 * 7,     # keep 7 days
        encoding    = "utf-8",
        utc         = True,
    )
    file_h.setFormatter(fmt)
    file_h.addFilter(filt)
    root.addHandler(file_h)

    # Silence noisy third-party loggers
    for noisy in (
        "httpx", "httpcore",
        "openai._base_client", "anthropic._base_client",
        "langchain", "langchain_core",
        "langchain_anthropic", "langchain_openai", "langchain_google_genai",
        "langgraph",
        "psycopg", "psycopg_pool",
        "urllib3", "asyncio",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
