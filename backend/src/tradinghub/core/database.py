"""Database engine, session factory, and the per-request session dependency."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from tradinghub.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base every model inherits from."""


engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a database session, closing it even when the request raises.

    Routes own their transactions; this only guarantees the session is closed and any open
    transaction rolled back.
    """
    async with SessionFactory() as session:
        yield session
