"""Redis client and the per-request dependency that hands it out."""

from collections.abc import AsyncIterator

from redis.asyncio import Redis

from tradinghub.core.config import get_settings

redis_client = Redis.from_url(get_settings().redis_url, decode_responses=True)


async def get_redis() -> AsyncIterator[Redis]:
    """Yield the shared client.

    A dependency rather than a direct import so tests can swap in a client on another logical
    database. The client owns a connection pool, so there is nothing to open or close here.
    """
    yield redis_client
