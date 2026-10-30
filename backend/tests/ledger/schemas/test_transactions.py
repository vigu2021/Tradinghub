from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from tradinghub.ledger.models import TransactionKind
from tradinghub.ledger.schemas.transactions import (
    TransactionCreate,
    TransactionFilters,
    TransactionUpdate,
)

RENT: dict[str, Any] = {
    "account_id": 1,
    "amount": "900",
    "kind": "expense",
    "category": "  Rent ",
    "occurred_at": "2026-10-01T09:00:00Z",
}


def test_a_valid_body_is_normalised() -> None:
    transaction = TransactionCreate.model_validate(RENT)

    assert transaction.amount == Decimal(900)
    assert transaction.kind is TransactionKind.EXPENSE
    assert transaction.category == "rent"
    assert transaction.occurred_at == datetime(2026, 10, 1, 9, tzinfo=UTC)


def test_a_transfer_cannot_be_created_as_a_transaction() -> None:
    """It would be one half with no partner. Transfers have their own endpoint."""
    with pytest.raises(ValidationError):
        TransactionCreate.model_validate(RENT | {"kind": "transfer"})


@pytest.mark.parametrize("amount", ["0", "-900"])
def test_an_amount_must_be_positive(amount: str) -> None:
    """The kind carries the direction. A signed amount as well would let the two disagree."""
    with pytest.raises(ValidationError):
        TransactionCreate.model_validate(RENT | {"amount": amount})


def test_more_decimals_than_the_column_holds_are_rejected() -> None:
    """NUMERIC(36, 18) would round the 19th decimal away without telling anyone."""
    with pytest.raises(ValidationError):
        TransactionCreate.model_validate(RENT | {"amount": "0.0000000000000000001"})


def test_a_time_without_a_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate.model_validate(RENT | {"occurred_at": "2026-10-01T09:00:00"})


def test_an_update_knows_which_fields_were_sent() -> None:
    """A null note clears it, an omitted one leaves it alone: only fields_set tells them apart."""
    update = TransactionUpdate.model_validate({"note": None})

    assert update.model_dump(exclude_unset=True) == {"note": None}


@pytest.mark.parametrize("field", ["amount", "kind", "occurred_at"])
def test_an_update_cannot_null_a_required_field(field: str) -> None:
    """Without this the database refuses it at flush, and the request fails as a 500."""
    with pytest.raises(ValidationError):
        TransactionUpdate.model_validate({field: None})


@pytest.mark.parametrize("limit", [0, 201])
def test_the_page_size_is_bounded(limit: int) -> None:
    with pytest.raises(ValidationError):
        TransactionFilters(limit=limit)


def test_a_misspelled_filter_is_rejected_rather_than_ignored() -> None:
    """Ignored, it would return every transaction while the caller believes they filtered."""
    with pytest.raises(ValidationError):
        TransactionFilters.model_validate({"acount_id": 3})


def test_a_category_filter_is_normalised_like_a_stored_category() -> None:
    """Otherwise ?category=Rent would never match the stored "rent"."""
    assert TransactionFilters(category=" Rent ").category == "rent"
