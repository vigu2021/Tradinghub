"""Database engine, session factory, and the per-request session dependency."""

from collections.abc import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from tradinghub.core.config import get_settings
from tradinghub.core.errors import AppError

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
    """Yield a session and commit it once the request succeeds.

    One transaction per request: a request that crashes rolls back in full, a deliberate 4xx
    keeps what it wrote, and no route or service has to remember to commit. Nothing below this
    may commit, or that guarantee is gone.
    """
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except AppError:
            # A rendered 4xx is not a crash, and the writes on the way to one must outlive it.
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise
