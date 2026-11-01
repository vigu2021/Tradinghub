from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from tradinghub.ledger.schemas.transfers import TransferCreate

MOVE: dict[str, Any] = {
    "from_account_id": 1,
    "to_account_id": 2,
    "amount_sent": "1000",
    "amount_received": "1000",
    "occurred_at": "2026-10-01T09:00:00Z",
}


def test_a_transfer_needs_no_fee() -> None:
    transfer = TransferCreate.model_validate(MOVE)

    assert transfer.amount_sent == Decimal(1000)
    assert transfer.fee is None


def test_a_fee_category_is_normalised_like_any_category() -> None:
    transfer = TransferCreate.model_validate(
        MOVE | {"fee": "5", "fee_account_id": 2, "fee_category": " Fees "}
    )

    assert transfer.fee_category == "fees"


@pytest.mark.parametrize(
    "fee_fields",
    [{"fee": "5"}, {"fee_account_id": 2}, {"fee_category": "fees"}],
)
def test_half_a_fee_is_rejected(fee_fields: dict[str, Any]) -> None:
    """A fee with no account to charge, or an account with no fee, says nothing usable."""
    with pytest.raises(ValidationError):
        TransferCreate.model_validate(MOVE | fee_fields)


@pytest.mark.parametrize("field", ["amount_sent", "amount_received", "fee"])
@pytest.mark.parametrize("amount", ["0", "-5"])
def test_every_amount_must_be_positive(field: str, amount: str) -> None:
    """The service applies the signs, so a signed amount here would come out backwards."""
    with pytest.raises(ValidationError):
        TransferCreate.model_validate(MOVE | {"fee_account_id": 2, "fee": "5"} | {field: amount})


def test_a_time_without_a_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TransferCreate.model_validate(MOVE | {"occurred_at": "2026-10-01T09:00:00"})


def test_a_caller_cannot_supply_the_group() -> None:
    """The service generates it. A caller choosing one could attach rows to another transfer."""
    with pytest.raises(ValidationError):
        TransferCreate.model_validate(MOVE | {"transfer_group_id": "x"})
