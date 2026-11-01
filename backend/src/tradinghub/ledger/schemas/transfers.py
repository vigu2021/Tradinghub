"""Request body for recording a transfer."""

from typing import Self

from pydantic import AwareDatetime, model_validator

from tradinghub.core.schemas import RequestModel
from tradinghub.ledger.schemas.transactions import Amount, Category, Note


class TransferCreate(RequestModel):
    """Money leaving one of the caller's accounts and arriving in another.

    Both amounts are positive. They differ when the units do: that is how a purchase is recorded,
    and nothing is converted. Whether the accounts are allowed is the service's call; this only
    checks that the fee fields make sense together.
    """

    from_account_id: int
    to_account_id: int
    amount_sent: Amount
    amount_received: Amount
    fee: Amount | None = None
    fee_account_id: int | None = None
    fee_category: Category | None = None
    occurred_at: AwareDatetime
    note: Note | None = None

    @model_validator(mode="after")
    def _fee_fields_agree(self) -> Self:
        if (self.fee is None) != (self.fee_account_id is None):
            raise ValueError("fee and fee_account_id come together")
        if self.fee is None and self.fee_category is not None:
            raise ValueError("fee_category needs a fee")
        return self
