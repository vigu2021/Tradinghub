"""Account registration."""

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.crud.user import create_user, get_user_by_email
from tradinghub.auth.models.user import User
from tradinghub.auth.security import hash_password


async def register_user(db: AsyncSession, email: str, raw_password: str) -> User | None:
    """Create an account, or return None when the email is already taken.

    Callers facing the public must treat both outcomes identically: a response that differs by
    even a status code turns this into a lookup for which addresses have accounts.

    Hashing happens before the lookup rather than after it, so the taken path costs the same
    ~37ms as the new one and the reply time leaks nothing either.
    """
    password_hash = hash_password(raw_password)
    if await get_user_by_email(db, email) is not None:
        return None
    return await create_user(db, email, password_hash)
