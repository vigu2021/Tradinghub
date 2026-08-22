"""Queries against the sessions table: the refresh-token store."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models.session import Session


async def get_session_by_token_hash(db: AsyncSession, hashed_refresh_token: str) -> Session | None:
    """Return the session holding that token hash, or None.

    Used and expired rows are returned too. Reuse detection needs to see a burnt row rather than
    be told the token is unknown.
    """
    return await db.scalar(
        select(Session).where(Session.hashed_refresh_token == hashed_refresh_token)
    )


async def create_session(
    db: AsyncSession,
    *,
    user_id: int,
    family_id: uuid.UUID,
    hashed_refresh_token: str,
    expires_at: datetime,
) -> Session:
    """Insert a refresh token and flush, so the returned Session carries its id.

    A fresh family_id starts a login. Passing an existing one makes this row a successor in that
    chain, which is the difference between login and refresh.
    """
    session = Session(
        user_id=user_id,
        family_id=family_id,
        hashed_refresh_token=hashed_refresh_token,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    return session


async def mark_session_used(db: AsyncSession, session: Session) -> None:
    """Burn a refresh token, so a later replay of it is detectable."""
    session.used_at = datetime.now(UTC)


async def revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    """Delete every session in a login chain. Reuse detection revokes the whole family."""
    await db.execute(delete(Session).where(Session.family_id == family_id))
