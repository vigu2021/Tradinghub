"""The sessions table: one row per refresh token."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from tradinghub.core.database import Base


class Session(Base):
    """One refresh token in a login's chain.

    Rotation means a single login produces a chain of these, each superseding the last and all
    sharing a family_id. Only the hash of the token is stored: the raw value lives in the user's
    cookie and nowhere else, so a dump of this table impersonates nobody.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    family_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, index=True)
    hashed_refresh_token: Mapped[str] = mapped_column(unique=True, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
