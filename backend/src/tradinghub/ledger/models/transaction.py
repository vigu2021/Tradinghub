"""The transactions table: one row per movement of money into or out of an account."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKeyConstraint, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from tradinghub.core.database import Base


class TransactionKind(StrEnum):
    """Income and expense are spending; a transfer is the same money in a different pot.

    A transfer's two rows are equal and opposite. Any fee is a separate expense row sharing the
    group, so it stays visible as spending instead of hiding inside an uneven transfer.
    """

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            ondelete="CASCADE",
        ),
        Index("ix_transactions_user_id_occurred_at", "user_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    account_id: Mapped[int]
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 8))  # Signed: out is negative
    kind: Mapped[TransactionKind] = mapped_column(
        Enum(
            TransactionKind,
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    category: Mapped[str | None]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None]
    transfer_group_id: Mapped[uuid.UUID | None]  # Both sides of a transfer, plus any fee
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
