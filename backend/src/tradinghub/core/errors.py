"""One error shape for every failure: {"error": {"code": ..., "message": ...}}.

A stable machine-readable code lets the frontend branch on the failure without parsing prose, and
lets the message change without breaking it.
"""

import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """An expected failure, raised where it is detected and rendered by the handler below.

    Subclasses declare the three fields and are raised without arguments. This class is never
    raised on its own: it has no values to render. Headers are optional: most errors have none,
    a rate limit carries Retry-After.
    """

    code: str
    message: str
    status_code: HTTPStatus
    headers: ClassVar[Mapping[str, str]] = {}  # Mapping: shared across subclasses, never mutated

    def __init__(self) -> None:
        super().__init__(self.message)


def _error_response(
    status_code: HTTPStatus, code: str, message: str, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Install handlers so no route has to format its own error body."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        return _error_response(error.status_code, error.code, error.message, error.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        """Report only that validation failed. Pydantic's errors() echoes the offending input,
        which on a registration is the password."""
        return _error_response(
            HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "The request is invalid."
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        """Return a reference the user can quote, never a traceback.

        The id comes from request.state, not the context var: RequestContextMiddleware has already
        reset the latter by the time this runs.
        """
        reference = request.state.request_id
        logger.exception("unhandled error", extra={"path": request.url.path})
        return _error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "internal_error",
            f"Internal error. Reference: {reference}",
        )
