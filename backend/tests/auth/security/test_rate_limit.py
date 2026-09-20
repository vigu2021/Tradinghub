import pytest
from redis.asyncio import Redis

from tradinghub.auth.errors import RateLimitedError
from tradinghub.auth.security.rate_limit import (
    MAX_FAILURES_PER_EMAIL,
    MAX_FAILURES_PER_IP,
    MAX_REGISTRATIONS_PER_IP,
    RATE_WINDOW_SECONDS,
    count_login_attempt,
    count_registration_attempt,
    forgive_login_attempt,
)

EMAIL = "limited@example.com"
IP = "203.0.113.7"


async def _attempt(redis_client: Redis, email: str, ip: str, times: int) -> None:
    for _ in range(times):
        await count_login_attempt(redis_client, email, ip)


async def test_the_email_limit_refuses_the_attempt_after_the_last_allowed_one(
    redis_client: Redis,
) -> None:
    await _attempt(redis_client, EMAIL, IP, MAX_FAILURES_PER_EMAIL)

    with pytest.raises(RateLimitedError):
        await count_login_attempt(redis_client, EMAIL, IP)


async def test_the_ip_limit_counts_across_emails(redis_client: Redis) -> None:
    """One attempt each against many addresses from one IP still locks that IP."""
    for attempt in range(MAX_FAILURES_PER_IP):
        await count_login_attempt(redis_client, f"spray{attempt}@example.com", IP)

    with pytest.raises(RateLimitedError):
        await count_login_attempt(redis_client, "fresh@example.com", IP)
    await count_login_attempt(redis_client, "fresh@example.com", "198.51.100.9")


async def test_the_email_key_ignores_case(redis_client: Redis) -> None:
    """The users table is CITEXT, so a differently-cased address is the same account."""
    await _attempt(redis_client, "Victim@Example.com", IP, MAX_FAILURES_PER_EMAIL)

    with pytest.raises(RateLimitedError):
        await count_login_attempt(redis_client, "victim@example.com", IP)


async def test_an_attempt_starts_a_window_that_later_attempts_do_not_extend(
    redis_client: Redis,
) -> None:
    await _attempt(redis_client, EMAIL, IP, 1)
    ttl_after_first = await redis_client.ttl(f"login:fail:email:{EMAIL}")
    assert 0 < ttl_after_first <= RATE_WINDOW_SECONDS

    await redis_client.expire(f"login:fail:email:{EMAIL}", 60)
    await _attempt(redis_client, EMAIL, IP, 1)

    assert await redis_client.ttl(f"login:fail:email:{EMAIL}") <= 60


async def test_forgiving_forgets_the_email_and_only_its_own_ip_increment(
    redis_client: Redis,
) -> None:
    await _attempt(redis_client, "other@example.com", IP, 3)
    await _attempt(redis_client, EMAIL, IP, MAX_FAILURES_PER_EMAIL)

    await forgive_login_attempt(redis_client, EMAIL, IP)

    await count_login_attempt(redis_client, EMAIL, IP)
    assert await redis_client.get(f"login:fail:ip:{IP}") == str(3 + MAX_FAILURES_PER_EMAIL)


async def test_a_burst_cannot_exceed_the_limit(redis_client: Redis) -> None:
    """Concurrent attempts are counted before any is judged, so a burst gets no free guesses."""
    import asyncio

    outcomes = await asyncio.gather(
        *(count_login_attempt(redis_client, EMAIL, IP) for _ in range(MAX_FAILURES_PER_EMAIL * 4)),
        return_exceptions=True,
    )

    allowed = sum(outcome is None for outcome in outcomes)
    assert allowed == MAX_FAILURES_PER_EMAIL


async def test_registrations_are_limited_per_ip_and_never_forgiven(redis_client: Redis) -> None:
    for _ in range(MAX_REGISTRATIONS_PER_IP):
        await count_registration_attempt(redis_client, IP)

    with pytest.raises(RateLimitedError):
        await count_registration_attempt(redis_client, IP)
    await count_registration_attempt(redis_client, "198.51.100.9")


async def test_registrations_and_logins_do_not_share_a_counter(redis_client: Redis) -> None:
    for _ in range(MAX_REGISTRATIONS_PER_IP):
        await count_registration_attempt(redis_client, IP)

    await count_login_attempt(redis_client, EMAIL, IP)


async def test_every_call_fails_open_when_redis_is_unreachable() -> None:
    dead = Redis.from_url("redis://localhost:1", socket_connect_timeout=0.2)
    try:
        await count_login_attempt(dead, EMAIL, IP)
        await count_registration_attempt(dead, IP)
        await forgive_login_attempt(dead, EMAIL, IP)
    finally:
        await dead.aclose()
