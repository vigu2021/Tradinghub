import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models import Session, User


async def _user(db_session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="x")
    db_session.add(user)
    await db_session.flush()
    return user


def _session(user: User, hashed_refresh_token: str, **overrides: object) -> Session:
    fields: dict[str, object] = {
        "user_id": user.id,
        "hashed_refresh_token": hashed_refresh_token,
        "expires_at": datetime.now(UTC) + timedelta(days=30),
    }
    return Session(**{**fields, **overrides})


async def test_a_new_session_is_unspent(db_session: AsyncSession) -> None:
    user = await _user(db_session, "unspent@example.com")
    session = _session(user, "hash-unspent")
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)

    assert session.used_at is None


async def test_a_new_session_gets_a_family_id(db_session: AsyncSession) -> None:
    user = await _user(db_session, "family@example.com")
    session = _session(user, "hash-family")
    db_session.add(session)
    await db_session.flush()

    assert isinstance(session.family_id, uuid.UUID)


async def test_siblings_can_share_a_family_id(db_session: AsyncSession) -> None:
    user = await _user(db_session, "chain@example.com")
    family_id = uuid.uuid4()
    db_session.add(_session(user, "hash-first", family_id=family_id))
    db_session.add(_session(user, "hash-second", family_id=family_id))

    await db_session.flush()

    count = await db_session.scalar(
        select(func.count()).select_from(Session).where(Session.family_id == family_id)
    )
    assert count == 2


async def test_the_token_hash_is_unique(db_session: AsyncSession) -> None:
    user = await _user(db_session, "dupe@example.com")
    db_session.add(_session(user, "hash-collision"))
    await db_session.flush()

    db_session.add(_session(user, "hash-collision"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_a_session_needs_a_real_user(db_session: AsyncSession) -> None:
    db_session.add(
        Session(
            user_id=999_999,
            hashed_refresh_token="hash-orphan",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_deleting_a_user_deletes_their_sessions(db_session: AsyncSession) -> None:
    user = await _user(db_session, "cascade@example.com")
    db_session.add(_session(user, "hash-cascade"))
    await db_session.flush()

    await db_session.delete(user)
    await db_session.flush()

    remaining = await db_session.scalar(
        select(func.count()).select_from(Session).where(Session.user_id == user.id)
    )
    assert remaining == 0


async def test_deleting_a_user_leaves_other_users_sessions(db_session: AsyncSession) -> None:
    doomed = await _user(db_session, "doomed@example.com")
    survivor = await _user(db_session, "survivor@example.com")
    db_session.add(_session(doomed, "hash-doomed"))
    db_session.add(_session(survivor, "hash-survivor"))
    await db_session.flush()

    await db_session.delete(doomed)
    await db_session.flush()

    remaining = await db_session.scalar(
        select(func.count()).select_from(Session).where(Session.user_id == survivor.id)
    )
    assert remaining == 1


async def test_timestamps_are_timezone_aware(db_session: AsyncSession) -> None:
    user = await _user(db_session, "tz@example.com")
    session = _session(user, "hash-tz")
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)

    assert session.created_at.tzinfo is not None
    assert session.expires_at.tzinfo is not None
