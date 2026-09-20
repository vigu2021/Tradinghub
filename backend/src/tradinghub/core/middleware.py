"""Per-request context and access logging."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from http import HTTPStatus

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from tradinghub.core.errors import error_response
from tradinghub.core.logging import UNSET, request_id, user_id

REQUEST_ID_HEADER = "X-Request-ID"

# Polled by the load balancer every few seconds; at INFO it buries everything else.
QUIET_PATHS = frozenset({"/health"})

logger = logging.getLogger("tradinghub.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, log one line per request, and render any unexpected failure.

    An unhandled exception becomes a 500 carrying a reference the user can quote, never a
    traceback. It is rendered here rather than by an exception handler because this middleware
    sits inside CORS: the browser can read the response, and it carries the request id.

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
            response = error_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_error",
                f"Internal error. Reference: {current_id}",
            )
            response.headers[REQUEST_ID_HEADER] = current_id
            return response
        else:
            level = logging.DEBUG if request.url.path in QUIET_PATHS else logging.INFO
            user_token = user_id.set(getattr(request.state, "user_id", UNSET))
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
            user_id.reset(user_token)
            response.headers[REQUEST_ID_HEADER] = request_id.get()
            return response
        finally:
            # Reset in finally: a failed request must not leak its id into the next one.
            request_id.reset(token)


def _elapsed_ms(started: float) -> float:
    """Milliseconds since a perf_counter reading, rounded for readability."""
    return round((time.perf_counter() - started) * 1000, 2)
