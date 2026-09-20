"""The accounts table: one pot of money, in one currency."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from tradinghub.core.database import Base


class AccountType(StrEnum):
    """What the account is for. Cosmetic: every balance is computed the same way."""

    CASH = "cash"
    CRYPTO = "crypto"
    STOCK = "stock"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "name"),
        # Required by the transactions foreign key: Postgres only lets one reference a
        # combination of columns that is uniquely constrained. Forbids nothing on its own.
        UniqueConstraint("id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(CITEXT)
    currency: Mapped[str]
    type: Mapped[AccountType] = mapped_column(
        Enum(
            AccountType,
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
