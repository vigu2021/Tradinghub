import pytest
from redis.asyncio import Redis

from tradinghub.auth.errors import RateLimitedError
from tradinghub.auth.security.rate_limit import (
    MAX_FAILURES_PER_EMAIL,
    MAX_FAILURES_PER_IP,
    RATE_WINDOW_SECONDS,
    check_login_allowed,
    clear_login_failures,
    record_login_failure,
)

EMAIL = "limited@example.com"
IP = "203.0.113.7"


async def _fail(redis_client: Redis, email: str, ip: str, times: int) -> None:
    for _ in range(times):
        await record_login_failure(redis_client, email, ip)


async def test_the_email_limit_refuses_at_the_threshold(redis_client: Redis) -> None:
    await _fail(redis_client, EMAIL, IP, MAX_FAILURES_PER_EMAIL - 1)
    await check_login_allowed(redis_client, EMAIL, IP)

    await _fail(redis_client, EMAIL, IP, 1)

    with pytest.raises(RateLimitedError):
        await check_login_allowed(redis_client, EMAIL, IP)


async def test_the_ip_limit_counts_across_emails(redis_client: Redis) -> None:
    """One failure each against many addresses from one IP still locks that IP."""
    for attempt in range(MAX_FAILURES_PER_IP):
        await record_login_failure(redis_client, f"spray{attempt}@example.com", IP)

    with pytest.raises(RateLimitedError):
        await check_login_allowed(redis_client, "fresh@example.com", IP)
    await check_login_allowed(redis_client, "fresh@example.com", "198.51.100.9")


async def test_the_email_key_ignores_case(redis_client: Redis) -> None:
    """The users table is CITEXT, so a differently-cased address is the same account."""
    await _fail(redis_client, "Victim@Example.com", IP, MAX_FAILURES_PER_EMAIL)

    with pytest.raises(RateLimitedError):
        await check_login_allowed(redis_client, "victim@example.com", IP)


async def test_a_failure_starts_a_window_that_later_failures_do_not_extend(
    redis_client: Redis,
) -> None:
    await _fail(redis_client, EMAIL, IP, 1)
    ttl_after_first = await redis_client.ttl(f"login:fail:email:{EMAIL}")
    assert 0 < ttl_after_first <= RATE_WINDOW_SECONDS

    await redis_client.expire(f"login:fail:email:{EMAIL}", 60)
    await _fail(redis_client, EMAIL, IP, 1)

    assert await redis_client.ttl(f"login:fail:email:{EMAIL}") <= 60


async def test_clearing_forgets_the_email_but_not_the_ip(redis_client: Redis) -> None:
    await _fail(redis_client, EMAIL, IP, MAX_FAILURES_PER_EMAIL)

    await clear_login_failures(redis_client, EMAIL)

    await check_login_allowed(redis_client, EMAIL, IP)
    assert await redis_client.get(f"login:fail:ip:{IP}") == str(MAX_FAILURES_PER_EMAIL)


async def test_every_call_fails_open_when_redis_is_unreachable() -> None:
    dead = Redis.from_url("redis://localhost:1", socket_connect_timeout=0.2)
    try:
        await check_login_allowed(dead, EMAIL, IP)
        await record_login_failure(dead, EMAIL, IP)
        await clear_login_failures(dead, EMAIL)
    finally:
        await dead.aclose()
