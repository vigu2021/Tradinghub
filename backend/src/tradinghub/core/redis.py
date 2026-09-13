from collections.abc import AsyncIterator

from redis.asyncio import Redis

from tradinghub.core.config import get_settings

redis_client = Redis.from_url(get_settings().redis_url, decode_responses=True)


async def get_redis() -> AsyncIterator[Redis]:
    yield redis_client
