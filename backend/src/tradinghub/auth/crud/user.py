"""Queries against the users table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return the account with that email, or None. Matching is case-insensitive via citext."""
    return await db.scalar(select(User).where(User.email == email))


async def create_user(db: AsyncSession, email: str, password_hash: str) -> User:
    """Insert an account and flush, so the returned User carries its id and timestamps."""
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    await db.flush()
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Return the account with that id, or None. Used by the one route that needs more than the
    access token carries."""
    return await db.get(User, user_id)
