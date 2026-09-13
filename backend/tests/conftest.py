from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tradinghub.core.config import get_settings
from tradinghub.core.database import get_db
from tradinghub.core.redis import get_redis
from tradinghub.main import create_app


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a session inside a transaction that is rolled back when the test ends.

    Tests therefore never see each other's rows, and the schema is never rebuilt.
    join_transaction_mode is explicit because routes commit inside this outer transaction;
    "create_savepoint" turns those commits into savepoint releases so the final rollback
    still discards everything.
    """
    # NullPool: each test runs in its own event loop, and a pooled connection created in one
    # loop cannot be reused in another.
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    """A client on Redis logical database 1, flushed when the test ends.

    Its own client rather than the module-level one, for the same event-loop reason as the
    engine above. Database 1 keeps test counters away from a dev server on database 0.
    """
    client = Redis.from_url(get_settings().redis_url, db=1, decode_responses=True)
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, redis_client: Redis) -> AsyncIterator[AsyncClient]:
    """An HTTP client wired straight to the ASGI app, sharing the test's transaction."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        """Mirror get_db, so a route that relies on the request-scoped commit is really tested."""
        yield db_session
        await db_session.commit()

    async def override_get_redis() -> AsyncIterator[Redis]:
        yield redis_client

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
