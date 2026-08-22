"""Session lifecycle: login, refresh with rotation, logout."""

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.crud.session import (
    create_session,
    get_session_by_token_hash,
    mark_session_used,
    revoke_family,
)
from tradinghub.auth.crud.user import get_user_by_email
from tradinghub.auth.errors import InvalidCredentialsError, InvalidSessionError
from tradinghub.auth.models.user import User
from tradinghub.auth.security.passwords import hash_password, verify_password
from tradinghub.auth.security.tokens import (
    REFRESH_TOKEN_LIFETIME,
    encode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)

logger = logging.getLogger(__name__)

# Verified against when the email is unknown, so both failures cost one Argon2 verify. Random,
# so nothing can match it.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


@dataclass(frozen=True, slots=True)
class TokenPair:
    """The two raw tokens a caller receives. Only the refresh token's hash is ever stored."""

    access_token: str
    refresh_token: str


async def _issue_token_pair(db: AsyncSession, *, user_id: int, family_id: uuid.UUID) -> TokenPair:
    """Mint a pair and record the session. Only the refresh token's hash is stored."""
    refresh_token = generate_refresh_token()
    await create_session(
        db,
        user_id=user_id,
        family_id=family_id,
        hashed_refresh_token=hash_refresh_token(refresh_token),
        expires_at=datetime.now(UTC) + REFRESH_TOKEN_LIFETIME,
    )
    return TokenPair(access_token=encode_access_token(user_id), refresh_token=refresh_token)


async def login(db: AsyncSession, *, email: str, raw_password: str) -> tuple[User, TokenPair]:
    """Start a new session family. Raises InvalidCredentialsError for a bad email or a bad password.

    One exception for both, raised after the same work, so the two failures are indistinguishable
    in content and in timing. Returns the user because the route answers with it, saving a second
    lookup.
    """
    user = await get_user_by_email(db, email)
    password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH

    # Kept out of the if: short-circuiting would skip the verify for an unknown email, and the
    # faster reply tells an attacker which addresses are registered.
    password_matches = verify_password(raw_password=raw_password, password_hash=password_hash)
    if user is None or not password_matches:
        raise InvalidCredentialsError

    token_pair = await _issue_token_pair(db, user_id=user.id, family_id=uuid.uuid4())
    return user, token_pair


async def refresh(db: AsyncSession, raw_refresh_token: str) -> TokenPair:
    """Rotate a refresh token. Raises InvalidSessionError if it is unknown, expired, or spent.

    Spending a token twice means it leaked: the thief and the real client both hold it, and
    nothing here can tell them apart. The whole family goes, so neither of them keeps a session.
    """
    current_session = await get_session_by_token_hash(db, hash_refresh_token(raw_refresh_token))
    # Nothing to rotate: a revoked or logged-out token is deleted, so it looks like a fake one.
    if current_session is None:
        raise InvalidSessionError

    # Already used, so someone has a copy. We can't tell thief from client, so nobody keeps it.
    if current_session.used_at is not None:
        logger.warning(
            "refresh token reuse",
            extra={
                "user_id": current_session.user_id,
                "family_id": str(current_session.family_id),
            },
        )
        await revoke_family(db, current_session.family_id)
        await db.commit()  # the 401 that follows would roll the revocation back
        raise InvalidSessionError

    # The refresh token has expired. Nothing to rotate here, this user logs in again.
    if current_session.expires_at < datetime.now(UTC):
        raise InvalidSessionError

    # Burn this one and issue the next, keeping the family_id so the chain stays linked.
    await mark_session_used(db, current_session)
    return await _issue_token_pair(
        db, user_id=current_session.user_id, family_id=current_session.family_id
    )


async def logout(db: AsyncSession, raw_refresh_token: str) -> None:
    """End the whole login chain this token belongs to. An unknown token is not an error.

    The family goes rather than the one row, because a client that logs out holding an already
    used token has been robbed: its successor is live in someone else's browser, and deleting
    only what was presented would leave that session running and destroy the evidence of it.
    """
    current_session = await get_session_by_token_hash(db, hash_refresh_token(raw_refresh_token))
    if current_session is not None:
        await revoke_family(db, current_session.family_id)
