"""Application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy import text

from tradinghub.auth.routes import router as auth_router
from tradinghub.core.config import get_settings
from tradinghub.core.database import engine
from tradinghub.core.errors import register_error_handlers
from tradinghub.core.logging import configure_logging
from tradinghub.core.middleware import RequestContextMiddleware
from tradinghub.core.redis import redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Check the database is reachable on startup, close pooled connections on shutdown.

    Redis is checked but not required: the rate limiter fails open, so a missing Redis
    degrades one defence rather than the whole app.

    Raises:
        OSError, DBAPIError: when Postgres cannot be reached.
    """
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    try:
        await redis_client.ping()
    except RedisError:
        logger.error("redis unreachable at startup, rate limiting is disabled")
    yield
    await redis_client.aclose()
    await engine.dispose()


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

    app = FastAPI(title="Tradinghub API", lifespan=lifespan)
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
    app.include_router(auth_router)
    return app
