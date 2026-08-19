"""Session lifecycle: login, refresh with rotation, logout."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.crud.session import create_session
from tradinghub.auth.crud.user import get_user_by_email
from tradinghub.auth.models.user import User
from tradinghub.auth.security.passwords import hash_password, verify_password
from tradinghub.auth.security.tokens import (
    REFRESH_TOKEN_LIFETIME,
    encode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)

# Verified against when the email is unknown, so both failures cost one Argon2 verify. Random,
# so nothing can match it.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


@dataclass(frozen=True, slots=True)
class TokenPair:
    """The two raw tokens a caller receives. Only the refresh token's hash is ever stored."""

    access_token: str
    refresh_token: str


async def login(
    db: AsyncSession, *, email: str, raw_password: str
) -> tuple[User, TokenPair] | None:
    """Start a new session family, or return None for an unknown email or a wrong password.

    The two failures are indistinguishable in both content and timing; callers must keep them that
    way. Returns the user because the route answers with it, saving a second lookup.
    """
    user = await get_user_by_email(db, email)
    password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    # Kept out of the if: short-circuiting would skip the verify for an unknown email, and the
    # faster reply tells an attacker which addresses are registered.
    password_matches = verify_password(raw_password=raw_password, password_hash=password_hash)
    if user is None or not password_matches:
        return None

    refresh_token = generate_refresh_token()
    await create_session(
        db,
        user_id=user.id,
        family_id=uuid.uuid4(),
        hashed_refresh_token=hash_refresh_token(refresh_token),
        expires_at=datetime.now(UTC) + REFRESH_TOKEN_LIFETIME,
    )
    return user, TokenPair(
        access_token=encode_access_token(user.id),
        refresh_token=refresh_token,
    )
