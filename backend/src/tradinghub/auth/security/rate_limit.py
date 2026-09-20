"""Login rate limiting: failure counters in Redis, keyed by email and by IP."""

import logging
from typing import Final

from redis.asyncio import Redis
from redis.exceptions import RedisError

from tradinghub.auth.errors import RateLimitedError

RATE_WINDOW_SECONDS: Final[int] = RateLimitedError.retry_after_seconds
MAX_FAILURES_PER_EMAIL: Final[int] = 10
MAX_FAILURES_PER_IP: Final[int] = 30

logger = logging.getLogger(__name__)


def _email_key(email: str) -> str:
    # casefold: the users table is CITEXT, so Alice@ and alice@ are one account and must share
    # one counter. Pydantic's EmailStr lowercases only the domain.
    return f"login:fail:email:{email.casefold()}"


def _ip_key(ip: str) -> str:
    return f"login:fail:ip:{ip}"


async def count_login_attempt(redis: Redis, email: str, ip: str) -> None:
    """Count the attempt against both keys, then raise RateLimitedError if either is over its limit.

    Increment first and decide from the returned count, so a burst of concurrent attempts is
    counted before any of them is judged: a read-then-write check would let every request in the
    burst see the same stale count. EXPIRE with NX starts the window on the first attempt and
    leaves it alone after, so the window is fixed rather than sliding. Runs before any password
    work, so a locked-out caller costs one round trip. A Redis outage is logged and treated as
    allowed: the limiter is a defence, not the authorization.
    """
    try:
        async with redis.pipeline() as pipeline:
            for key in (_email_key(email), _ip_key(ip)):
                pipeline.incr(key)
                pipeline.expire(key, RATE_WINDOW_SECONDS, nx=True)
            email_attempts, _, ip_attempts, _ = await pipeline.execute()
    except RedisError:
        logger.warning("redis unreachable, login attempt not counted", exc_info=True)
        return

    if email_attempts > MAX_FAILURES_PER_EMAIL or ip_attempts > MAX_FAILURES_PER_IP:
        logger.warning(
            "login rate limited",
            extra={"email_attempts": email_attempts, "ip_attempts": ip_attempts},
        )
        raise RateLimitedError


async def forgive_login_attempt(redis: Redis, email: str, ip: str) -> None:
    """Undo the count for an attempt that turned out to be a correct password.

    The email key goes entirely: a correct password vouches for the account owner. The IP key
    only loses this attempt's increment, since a shared address may have other people's failures
    on it. Together with count_login_attempt this means only failures accumulate. A Redis outage
    is logged; the counters expire on their own.
    """
    # Known edge: if the IP key expired between the INCR and this DECR it is recreated at -1 with
    # no TTL. Harmless: negative never refuses, and the next INCR's EXPIRE NX gives it a window.
    try:
        async with redis.pipeline() as pipeline:
            pipeline.delete(_email_key(email))
            pipeline.decr(_ip_key(ip))
            await pipeline.execute()
    except RedisError:
        logger.warning("redis unreachable, login attempt not forgiven", exc_info=True)
