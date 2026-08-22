from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.crud.session import get_session_by_token_hash
from tradinghub.auth.crud.user import create_user
from tradinghub.auth.errors import InvalidCredentialsError, InvalidSessionError
from tradinghub.auth.models import Session, User
from tradinghub.auth.security.passwords import hash_password
from tradinghub.auth.security.tokens import hash_refresh_token
from tradinghub.auth.services import sessions
from tradinghub.auth.services.sessions import login, logout, refresh

PASSWORD = "correct-horse-battery"


async def _account(db_session: AsyncSession, email: str) -> User:
    return await create_user(db_session, email, hash_password(PASSWORD))


async def _login(db_session: AsyncSession, email: str) -> str:
    """Register an account, log it in, and return the raw refresh token."""
    await _account(db_session, email)
    _, token_pair = await login(db_session, email=email, raw_password=PASSWORD)
    return token_pair.refresh_token


async def _expire(db_session: AsyncSession, raw_refresh_token: str) -> None:
    session = await get_session_by_token_hash(db_session, hash_refresh_token(raw_refresh_token))
    assert session is not None
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.flush()


async def test_login_returns_the_user_and_a_pair(db_session: AsyncSession) -> None:
    user = await _account(db_session, "login@example.com")

    logged_in_user, token_pair = await login(
        db_session, email="login@example.com", raw_password=PASSWORD
    )

    assert logged_in_user.id == user.id
    assert token_pair.access_token
    assert token_pair.refresh_token


async def test_login_rejects_a_wrong_password(db_session: AsyncSession) -> None:
    await _account(db_session, "wrong@example.com")

    with pytest.raises(InvalidCredentialsError):
        await login(db_session, email="wrong@example.com", raw_password="nope")


async def test_login_rejects_an_unknown_email(db_session: AsyncSession) -> None:
    with pytest.raises(InvalidCredentialsError):
        await login(db_session, email="nobody@example.com", raw_password=PASSWORD)


async def test_login_verifies_a_hash_even_for_an_unknown_email(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    verified: list[tuple[str, str]] = []

    def counting_verify(*, raw_password: str, password_hash: str) -> bool:
        verified.append((raw_password, password_hash))
        return False

    monkeypatch.setattr(sessions, "verify_password", counting_verify)

    with pytest.raises(InvalidCredentialsError):
        await login(db_session, email="nobody@example.com", raw_password=PASSWORD)

    assert verified == [(PASSWORD, sessions.DUMMY_PASSWORD_HASH)]


async def test_login_starts_a_new_family_each_time(db_session: AsyncSession) -> None:
    await _account(db_session, "families@example.com")

    _, first_pair = await login(db_session, email="families@example.com", raw_password=PASSWORD)
    _, second_pair = await login(db_session, email="families@example.com", raw_password=PASSWORD)

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

    token_pair = await refresh(db_session, first_token)

    assert token_pair.refresh_token != first_token


async def test_refresh_keeps_the_successor_in_the_family(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "chain@example.com")
    first_session = await get_session_by_token_hash(db_session, hash_refresh_token(first_token))
    assert first_session is not None

    token_pair = await refresh(db_session, first_token)

    successor = await get_session_by_token_hash(
        db_session, hash_refresh_token(token_pair.refresh_token)
    )
    assert successor is not None
    assert successor.family_id == first_session.family_id


async def test_refresh_burns_the_token_it_rotated(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "burn@example.com")
    await refresh(db_session, first_token)

    with pytest.raises(InvalidSessionError):
        await refresh(db_session, first_token)


async def test_replaying_a_used_token_kills_its_siblings(db_session: AsyncSession) -> None:
    stolen_token = await _login(db_session, "theft@example.com")
    successor = await refresh(db_session, stolen_token)

    with pytest.raises(InvalidSessionError):
        await refresh(db_session, stolen_token)

    with pytest.raises(InvalidSessionError):
        await refresh(db_session, successor.refresh_token)


async def test_replaying_a_used_token_empties_the_family(db_session: AsyncSession) -> None:
    stolen_token = await _login(db_session, "sweep@example.com")
    stolen_session = await get_session_by_token_hash(db_session, hash_refresh_token(stolen_token))
    assert stolen_session is not None
    family_id = stolen_session.family_id
    await refresh(db_session, stolen_token)

    with pytest.raises(InvalidSessionError):
        await refresh(db_session, stolen_token)

    remaining = await db_session.scalar(
        select(func.count()).select_from(Session).where(Session.family_id == family_id)
    )
    assert remaining == 0


async def test_refresh_rejects_an_expired_token(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "expired@example.com")
    await _expire(db_session, first_token)

    with pytest.raises(InvalidSessionError):
        await refresh(db_session, first_token)


async def test_refresh_rejects_an_unknown_token(db_session: AsyncSession) -> None:
    with pytest.raises(InvalidSessionError):
        await refresh(db_session, "never-issued-by-us")


async def test_logout_kills_the_token(db_session: AsyncSession) -> None:
    first_token = await _login(db_session, "logout@example.com")

    await logout(db_session, first_token)

    with pytest.raises(InvalidSessionError):
        await refresh(db_session, first_token)


async def test_logout_with_a_stale_token_kills_the_live_successor(
    db_session: AsyncSession,
) -> None:
    stale_token = await _login(db_session, "robbed@example.com")
    successor = await refresh(db_session, stale_token)

    await logout(db_session, stale_token)

    with pytest.raises(InvalidSessionError):
        await refresh(db_session, successor.refresh_token)


async def test_logout_ignores_an_unknown_token(db_session: AsyncSession) -> None:
    await logout(db_session, "never-issued-by-us")
