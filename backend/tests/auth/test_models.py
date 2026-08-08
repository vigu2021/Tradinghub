import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models import User


async def test_email_lookup_is_case_insensitive(db_session: AsyncSession) -> None:
    db_session.add(User(email="Vig@Example.com", password_hash="x"))
    await db_session.flush()

    found = await db_session.scalar(select(User).where(User.email == "vig@example.com"))

    assert found is not None


async def test_emails_differing_only_in_case_collide(db_session: AsyncSession) -> None:
    db_session.add(User(email="vig@example.com", password_hash="x"))
    await db_session.flush()

    db_session.add(User(email="VIG@EXAMPLE.COM", password_hash="x"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_new_user_gets_an_id_and_timestamps(db_session: AsyncSession) -> None:
    user = User(email="timestamps@example.com", password_hash="x")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.created_at is not None
    assert user.created_at.tzinfo is not None
