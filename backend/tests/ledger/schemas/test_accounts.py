from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tradinghub.ledger.models import AccountType
from tradinghub.ledger.schemas.accounts import AccountCreate, AccountResponse, AccountUpdate


def test_a_name_is_trimmed_and_a_unit_is_uppercased() -> None:
    """The schema normalises, so no service has to remember to."""
    account = AccountCreate(name="  Chase  ", unit=" gbp ", type=AccountType.CASH)

    assert account.name == "Chase"
    assert account.unit == "GBP"


def test_an_update_may_change_one_field_alone() -> None:
    """PATCH is partial. Renaming must not require restating the unit and type."""
    update = AccountUpdate(name="Chase checking")

    assert update.model_dump(exclude_unset=True) == {"name": "Chase checking"}


def test_an_update_distinguishes_archiving_from_leaving_it_alone() -> None:
    assert AccountUpdate(archived=True).archived is True
    assert AccountUpdate(archived=False).archived is False
    assert AccountUpdate(name="Chase").archived is None


def test_a_misspelled_field_is_rejected_rather_than_ignored() -> None:
    """Without extra="forbid" this returns 200 and silently changes nothing."""
    with pytest.raises(ValidationError):
        AccountUpdate(nmae="Chase")  # type: ignore[call-arg]


def test_a_caller_cannot_claim_a_user_id() -> None:
    """Ownership comes from the cookie. A body that tries to set it is a 422."""
    with pytest.raises(ValidationError):
        AccountCreate(name="Chase", unit="GBP", type=AccountType.CASH, user_id=7)  # type: ignore[call-arg]


def test_an_empty_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AccountCreate(name="   ", unit="GBP", type=AccountType.CASH)


def test_an_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AccountCreate(name="Chase", unit="GBP", type="bogus")  # type: ignore[arg-type]


def test_a_response_carries_no_user_id() -> None:
    response = AccountResponse(
        id=1,
        name="Chase",
        unit="GBP",
        type=AccountType.CASH,
        balance=Decimal("0"),
        archived_at=None,
    )

    assert "user_id" not in response.model_dump()


def test_a_response_says_when_an_account_was_archived() -> None:
    """A timestamp rather than a flag, so the UI can show when rather than only whether."""
    closed_at = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)

    response = AccountResponse(
        id=1,
        name="Chase",
        unit="GBP",
        type=AccountType.CASH,
        balance=Decimal("0"),
        archived_at=closed_at,
    )

    assert response.archived_at == closed_at
