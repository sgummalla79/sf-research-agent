import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("api.access")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        log.info("%s %s %d %.0fms", request.method, request.url.path, response.status_code, ms)
        return response
