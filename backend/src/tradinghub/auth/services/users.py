"""Account registration."""

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.crud.user import create_user, get_user_by_email
from tradinghub.auth.models.user import User
from tradinghub.auth.security.passwords import hash_password


async def register_user(db: AsyncSession, email: str, raw_password: str) -> User | None:
    """Create an account, or return None when the email is taken. Callers must not tell them apart.

    Hashing precedes the lookup so both paths take the same time.
    """
    password_hash = hash_password(raw_password)
    if await get_user_by_email(db, email) is not None:
        return None
    return await create_user(db, email, password_hash)
