"""Application factory."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradinghub.core.config import get_settings
from tradinghub.core.errors import register_error_handlers
from tradinghub.core.logging import configure_logging
from tradinghub.core.middleware import RequestContextMiddleware

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Deliberately does not touch the database."""
    return {"status": "ok"}


def create_app() -> FastAPI:
    """Build the FastAPI application.

    A factory rather than a module-level instance so tests can build an app with overridden
    dependencies.

    Raises:
        ValidationError: when a required setting is missing.
    """
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title="Tradinghub API")
    register_error_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],  # "*" with credentials is refused by browsers
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)
    return app
