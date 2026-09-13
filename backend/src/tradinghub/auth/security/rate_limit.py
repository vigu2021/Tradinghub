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
    return f"login:fail:email:{email}"


def _ip_key(ip: str) -> str:
    return f"login:fail:ip:{ip}"


async def check_login_allowed(redis: Redis, email: str, ip: str) -> None:
    """Raise RateLimitedError when the email or the IP is at its failure limit.

    Read-only, and run before any password work so a locked-out caller costs nothing.
    A Redis outage is logged and treated as allowed: the limiter is a defence, not the
    authorization.
    """
    keys = [_email_key(email), _ip_key(ip)]
    try:
        failure_counts = await redis.mget(keys)
    except RedisError:
        logger.warning("redis unreachable, skipping rate limit check")
        return

    email_failures = int(failure_counts[0] or 0)
    ip_failures = int(failure_counts[1] or 0)
    if email_failures >= MAX_FAILURES_PER_EMAIL or ip_failures >= MAX_FAILURES_PER_IP:
        logger.warning(
            "login rate limited",
            extra={"email_failures": email_failures, "ip_failures": ip_failures},
        )
        raise RateLimitedError


async def record_login_failure(redis: Redis, email: str, ip: str) -> None:
    """Count one failure against both the email and the IP.

    EXPIRE with NX starts the window on the first failure and leaves it alone after, so the
    window is fixed rather than sliding. A Redis outage is logged and the failure goes
    uncounted.
    """
    keys = [_email_key(email), _ip_key(ip)]
    try:
        async with redis.pipeline() as pipe:
            for key in keys:
                pipe.incr(key)
                pipe.expire(key, RATE_WINDOW_SECONDS, nx=True)
            await pipe.execute()
    except RedisError:
        logger.warning("redis unreachable, login failure not recorded")


async def clear_login_failures(redis: Redis, email: str) -> None:
    """Forget the email's failures after a successful login.

    Only the email key: a correct password vouches for the account owner, not for everyone
    behind the IP. A Redis outage is logged; the counter expires on its own.
    """
    try:
        await redis.delete(_email_key(email))
    except RedisError:
        logger.warning("redis unreachable, login failures not cleared")
