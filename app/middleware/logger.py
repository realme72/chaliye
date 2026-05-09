from __future__ import annotations

"""
Logger middleware — assigns a trace ID to every request and logs the full
request/response lifecycle so you can reconstruct any API call from its trace ID.

Usage in log statements anywhere in the call stack:
    logger = logging.getLogger(__name__)
    logger.info("something happened")   # trace_id injected automatically

The trace ID is propagated via a ContextVar, so it flows correctly through
async code without any explicit passing.
"""

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

# ── Context variable ───────────────────────────────────────────────────────
# Set once per request; readable by any code running in that async context.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


class TraceIDLogFilter(logging.Filter):
    """Injects trace_id into every LogRecord so the formatter can include it."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get("-")  # type: ignore[attr-defined]
        return True


def configure_logging() -> None:
    """Call once at startup to wire the trace-ID filter into the root logger."""
    fmt = "%(asctime)s %(levelname)-8s [%(trace_id)s] %(name)s: %(message)s"
    handler = logging.StreamHandler()
    handler.addFilter(TraceIDLogFilter())
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


logger = logging.getLogger(__name__)


class LoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Honour a trace ID forwarded from an upstream gateway; generate one otherwise.
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        token = trace_id_var.set(trace_id)
        request.state.trace_id = trace_id

        logger.info("→ %s %s", request.method, request.url.path)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("✗ %s %s — unhandled error after %.1fms: %s",
                         request.method, request.url.path, elapsed, exc)
            raise
        finally:
            trace_id_var.reset(token)

        elapsed = (time.perf_counter() - start) * 1000
        logger.info("← %s %s %d (%.1fms)",
                    request.method, request.url.path, response.status_code, elapsed)

        response.headers["X-Trace-ID"] = trace_id
        return response
