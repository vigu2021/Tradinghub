"""The accounts table: one pot of value, measured in one unit."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, UniqueConstraint, func
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
        CheckConstraint("type IN ('cash', 'crypto', 'stock')", name="accounttype"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(CITEXT)
    unit: Mapped[str]  # What the balance is counted in: GBP, USDT, BTC, AAPL
    type: Mapped[AccountType] = mapped_column(
        Enum(
            AccountType,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
