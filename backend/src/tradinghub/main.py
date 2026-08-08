"""Application factory."""

from fastapi import APIRouter, FastAPI

from tradinghub.core.config import get_settings

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
    get_settings()

    app = FastAPI(title="Tradinghub API")
    app.include_router(router)
    return app
