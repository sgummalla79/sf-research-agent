"""
Request logging middleware.

Logs every HTTP request with:
  - Method + path (query string stripped of sensitive params)
  - Authenticated user ID (sub claim from session cookie, if present)
  - HTTP status code
  - Wall-clock duration in ms

Skipped:
  - GET /health  (too frequent, adds noise)
  - Static assets / favicon

Example output:
  POST /api/chat/start        user=auth0|abc123   201  143ms
  GET  /api/flows             user=auth0|abc123   200   18ms
  POST /auth/token            user=anonymous      200   87ms
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.request")

# Routes that generate too much noise — skip logging them
_SKIP_PATHS = {"/health", "/favicon.ico", "/favicon.svg"}


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in _SKIP_PATHS:
            return await call_next(request)

        start   = time.perf_counter()
        response = await call_next(request)
        ms      = (time.perf_counter() - start) * 1000

        # Extract user identity without touching the cookie value
        user_id = getattr(getattr(request.state, "_user", None), "sub", None)
        user    = f"user={user_id}" if user_id else "user=anonymous"

        logger.info(
            "%-6s %-45s  %-36s  %d  %.0fms",
            request.method,
            path,
            user,
            response.status_code,
            ms,
        )

        return response
