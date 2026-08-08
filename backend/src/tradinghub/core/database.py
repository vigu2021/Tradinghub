"""Database engine, session factory, and the per-request session dependency."""

from collections.abc import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from tradinghub.core.config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base every model inherits from.

    The naming convention gives every index and constraint a deterministic name. Without it
    the database invents them, and Alembic cannot reliably drop or alter what it cannot name.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a database session, closing it even when the request raises.

    Routes own their transactions; this only guarantees the session is closed and any open
    transaction rolled back.
    """
    async with SessionFactory() as session:
        yield session
