import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tradinghub.auth.crud.session import get_session_by_token_hash
from tradinghub.auth.crud.user import create_user
from tradinghub.auth.errors import EmailTakenError, InvalidCredentialsError, InvalidSessionError
from tradinghub.auth.models import Session, User
from tradinghub.auth.security.passwords import hash_password
from tradinghub.auth.security.tokens import hash_refresh_token
from tradinghub.auth.services import auth
from tradinghub.auth.services.auth import (
    TokenPair,
    login_user,
    logout_user,
    refresh_session,
    register_user,
    start_session,
)
from tradinghub.core.config import get_settings

PASSWORD = "correct-horse-battery"
IP = "127.0.0.1"


async def _account(db_session: AsyncSession, email: str) -> User:
    return await create_user(db_session, email, await hash_password(PASSWORD))


async def _login(db_session: AsyncSession, email: str) -> str:
    """Register an account, start a session for it, and return the raw refresh token.

    Goes through start_session rather than login_user: the refresh and logout tests are not
    about passwords or rate limits, and skipping both keeps them free of Redis.
    """
    user = await _account(db_session, email)
    token_pair = await start_session(db_session, user.id)
    return token_pair.refresh_token


async def _expire(db_session: AsyncSession, raw_refresh_token: str) -> None:
    session = await get_session_by_token_hash(db_session, hash_refresh_token(raw_refresh_token))
    assert session is not None
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.flush()


async def test_losing_the_registration_race_is_an_email_taken_error(
    db_session: AsyncSession, redis_client: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two registrations can both pass the lookup; the unique constraint settles it."""
    await _account(db_session, "raced@example.com")

    async def lookup_that_ran_before_the_other_insert(*_: object) -> None:
        return None

    monkeypatch.setattr(auth, "get_user_by_email", lookup_that_ran_before_the_other_insert)

    with pytest.raises(EmailTakenError):
        await register_user(
            db_session, redis_client, email="raced@example.com", raw_password=PASSWORD, ip=IP
        )


async def test_login_returns_the_user_and_a_pair(
    db_session: AsyncSession, redis_client: Redis
) -> None:
    user = await _account(db_session, "login@example.com")

    logged_in_user, token_pair = await login_user(
        db_session, redis_client, email="login@example.com", raw_password=PASSWORD, ip=IP
    )

    assert logged_in_user.id == user.id
    assert token_pair.access_token
    assert token_pair.refresh_token


async def test_login_rejects_a_wrong_password(
    db_session: AsyncSession, redis_client: Redis
) -> None:
    await _account(db_session, "wrong@example.com")

    with pytest.raises(InvalidCredentialsError):
        await login_user(
            db_session, redis_client, email="wrong@example.com", raw_password="nope", ip=IP
        )


async def test_login_rejects_an_unknown_email(
    db_session: AsyncSession, redis_client: Redis
) -> None:
    with pytest.raises(InvalidCredentialsError):
        await login_user(
            db_session, redis_client, email="nobody@example.com", raw_password=PASSWORD, ip=IP
        )


async def test_login_verifies_a_hash_even_for_an_unknown_email(
    db_session: AsyncSession, redis_client: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    verified: list[tuple[str, str]] = []

    async def counting_verify(*, raw_password: str, password_hash: str) -> bool:
        verified.append((raw_password, password_hash))
        return False

    monkeypatch.setattr(auth, "verify_password", counting_verify)

    with pytest.raises(InvalidCredentialsError):
        await login_user(
            db_session, redis_client, email="nobody@example.com", raw_password=PASSWORD, ip=IP
        )

    assert verified == [(PASSWORD, auth.DUMMY_PASSWORD_HASH)]


async def test_login_succeeds_when_redis_is_down(db_session: AsyncSession) -> None:
    """The limiter is a defence, not the authorization: an outage must not lock everyone out."""
    await _account(db_session, "outage@example.com")
    dead_redis = Redis.from_url("redis://localhost:1", socket_connect_timeout=0.2)
    try:
        user, _ = await login_user(
            db_session, dead_redis, email="outage@example.com", raw_password=PASSWORD, ip=IP
        )
    finally:
        await dead_redis.aclose()

    assert user.email == "outage@example.com"


async def test_login_starts_a_new_family_each_time(
    db_session: AsyncSession, redis_client: Redis
) -> None:
    await _account(db_session, "families@example.com")

    _, first_pair = await login_user(
        db_session, redis_client, email="families@example.com", raw_password=PASSWORD, ip=IP
    )
    _, second_pair = await login_user(
        db_session, redis_client, email="families@example.com", raw_password=PASSWORD, ip=IP
    )

    first_session = await get_session_by_token_hash(
        db_session, hash_refresh_token(first_pair.refresh_token)
    )
    second_session = await get_session_by_token_hash(
        db_session, hash_refresh_token(second_pair.refresh_token)
    )
    assert first_session is not None
    assert second_session is not None
    assert first_session.family_id != second_session.family_id


async def test_refresh_issues_a_new_pair(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "rotate@example.com")

    token_pair = await refresh_session(db_session, first_token)

    assert token_pair.refresh_token != first_token


async def test_refresh_keeps_the_successor_in_the_family(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "chain@example.com")
    first_session = await get_session_by_token_hash(db_session, hash_refresh_token(first_token))
    assert first_session is not None

    token_pair = await refresh_session(db_session, first_token)

    successor = await get_session_by_token_hash(
        db_session, hash_refresh_token(token_pair.refresh_token)
    )
    assert successor is not None
    assert successor.family_id == first_session.family_id


async def test_refresh_burns_the_token_it_rotated(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "burn@example.com")
    await refresh_session(db_session, first_token)

    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, first_token)


async def test_replaying_a_used_token_kills_its_siblings(db_session: AsyncSession) -> None:
    stolen_token = await _login(db_session, "theft@example.com")
    successor = await refresh_session(db_session, stolen_token)

    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, stolen_token)

    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, successor.refresh_token)


async def test_replaying_a_used_token_empties_the_family(db_session: AsyncSession) -> None:
    stolen_token = await _login(db_session, "sweep@example.com")
    stolen_session = await get_session_by_token_hash(db_session, hash_refresh_token(stolen_token))
    assert stolen_session is not None
    family_id = stolen_session.family_id
    await refresh_session(db_session, stolen_token)

    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, stolen_token)

    remaining = await db_session.scalar(
        select(func.count()).select_from(Session).where(Session.family_id == family_id)
    )
    assert remaining == 0


async def test_refresh_rejects_an_expired_token(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "expired@example.com")
    await _expire(db_session, first_token)

    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, first_token)


async def test_refresh_rejects_an_unknown_token(db_session: AsyncSession) -> None:
    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, "never-issued-by-us")


async def test_logout_kills_the_token(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "logout@example.com")

    await logout_user(db_session, first_token)

    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, first_token)


async def test_logout_with_a_stale_token_kills_the_live_successor(
    db_session: AsyncSession,
) -> None:
    stale_token = await _login(db_session, "robbed@example.com")
    successor = await refresh_session(db_session, stale_token)

    await logout_user(db_session, stale_token)

    with pytest.raises(InvalidSessionError):
        await refresh_session(db_session, successor.refresh_token)


async def test_logout_ignores_an_unknown_token(db_session: AsyncSession) -> None:
    await logout_user(db_session, "never-issued-by-us")


async def test_two_requests_racing_one_token_cannot_both_rotate() -> None:
    """The row lock in get_session_by_token_hash, proven with two real transactions.

    The shared db_session fixture cannot show this: it is one transaction, and a transaction
    never waits on its own lock. So this test commits for real and deletes its account after.
    Without the lock both requests read used_at as NULL, both rotate, and a thief replaying a
    token at the same moment as its owner keeps a live session with no reuse ever detected.
    """
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    email = f"race-{uuid.uuid4().hex}@example.com"

    async def one_request(raw_refresh_token: str) -> TokenPair | InvalidSessionError:
        """Mirror get_db: one transaction, committed on success, rolled back on failure."""
        async with session_factory() as db:
            try:
                token_pair = await refresh_session(db, raw_refresh_token)
                await db.commit()
            except InvalidSessionError as error:
                await db.rollback()
                return error
            return token_pair

    try:
        async with session_factory() as db:
            user = await create_user(db, email, await hash_password(PASSWORD))
            contested_token = (await start_session(db, user.id)).refresh_token
            await db.commit()

        outcomes = await asyncio.gather(one_request(contested_token), one_request(contested_token))

        async with session_factory() as db:
            surviving_rows = await db.scalar(
                select(func.count()).select_from(Session).where(Session.user_id == user.id)
            )
        assert sorted(type(outcome).__name__ for outcome in outcomes) == [
            "InvalidSessionError",
            "TokenPair",
        ]
        assert surviving_rows == 0
    finally:
        async with session_factory() as db:
            await db.execute(delete(User).where(User.email == email))
            await db.commit()
        await engine.dispose()
