"""Per-request context and access logging."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from tradinghub.core.logging import request_id

REQUEST_ID_HEADER = "X-Request-ID"

# Polled by the load balancer every few seconds; at INFO it buries everything else.
QUIET_PATHS = frozenset({"/health"})

logger = logging.getLogger("tradinghub.access")


def _elapsed_ms(started: float) -> float:
    """Milliseconds since a perf_counter reading, rounded for readability."""
    return round((time.perf_counter() - started) * 1000, 2)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, then log one line per request.

    The path is logged without its query string: query parameters are a common place for
    tokens and reset codes to appear, and access logs are widely readable.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        current_id = incoming or uuid.uuid4().hex
        token = request_id.set(current_id)
        request.state.request_id = current_id
        started = time.perf_counter()
        context = {
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
        }
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "%s %s failed",
                request.method,
                request.url.path,
                extra={**context, "duration_ms": _elapsed_ms(started)},
            )
            raise
        else:
            level = logging.DEBUG if request.url.path in QUIET_PATHS else logging.INFO
            logger.log(
                level,
                "%s %s %s",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    **context,
                    "status_code": response.status_code,
                    "duration_ms": _elapsed_ms(started),
                },
            )
            response.headers[REQUEST_ID_HEADER] = request_id.get()
            return response
        finally:
            # Reset in finally: a failed request must not leak its id into the next one.
            request_id.reset(token)
