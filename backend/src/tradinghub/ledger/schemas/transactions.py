"""Request and response bodies for the transaction endpoints."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from tradinghub.core.schemas import (
    NO_NUL_PATTERN,
    DecimalString,
    RequestModel,
    RowId,
    UtcDatetime,
)
from tradinghub.ledger.models import TransactionKind


def _amount_must_be_a_string(amount: object) -> object:
    # A JSON number is already a float by the time it gets here, with its digits rounded away.
    if not isinstance(amount, str):
        raise ValueError("amount must be a string")
    return amount


# Positive: the kind says which way the money went, and the service applies the sign. The
# digits match NUMERIC(36, 18), which would otherwise round extra decimals away without a word.
Amount = Annotated[
    Decimal,
    BeforeValidator(_amount_must_be_a_string),
    Field(gt=0, max_digits=36, decimal_places=18),
]
# Transfers have their own endpoint, so a lone half of one cannot be created or patched in.
SpendingKind = Literal[TransactionKind.INCOME, TransactionKind.EXPENSE]
Category = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=40,
        pattern=NO_NUL_PATTERN,
    ),
]
Note = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500, pattern=NO_NUL_PATTERN)
]


class TransactionCreate(RequestModel):
    account_id: RowId
    amount: Amount
    kind: SpendingKind
    category: Category | None = None
    occurred_at: UtcDatetime
    note: Note | None = None


class TransactionUpdate(RequestModel):
    """A partial update: an omitted field is left alone, and a null category or note clears it.

    The account is fixed once recorded: a transaction in the wrong account is deleted and recorded
    again, so sending account_id is a 422. The service reads which fields were sent, not which are
    None, because here null means something. It means nothing for the other three, which the
    database requires, so a null for one of them is a 422.
    """

    amount: Amount | None = None
    kind: SpendingKind | None = None
    category: Category | None = None
    occurred_at: UtcDatetime | None = None
    note: Note | None = None

    @model_validator(mode="after")
    def _required_fields_are_not_null(self) -> Self:
        for field in ("amount", "kind", "occurred_at"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TransactionFilters(RequestModel):
    """The query string of GET /transactions. Every filter is optional and they combine."""

    account_id: RowId | None = None
    kind: TransactionKind | None = None
    category: Category | None = None
    occurred_from: UtcDatetime | None = None
    occurred_to: UtcDatetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=2**63 - 1)  # What Postgres OFFSET can hold


class TransactionResponse(BaseModel):
    """One transaction. The amount is signed here: out is negative, as stored."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    amount: DecimalString
    kind: TransactionKind
    category: str | None
    occurred_at: datetime
    note: str | None
    transfer_group_id: uuid.UUID | None


class TransactionPage(BaseModel):
    """One page of a list. total counts every match, so the UI can say how many pages there are."""

    items: list[TransactionResponse]
    total: int
