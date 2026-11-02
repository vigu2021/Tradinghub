from decimal import Decimal

import pytest
from pydantic import BaseModel

from tradinghub.core.schemas import DecimalString

LARGEST_AMOUNT = "999999999999999999.999999999999999999"


class _Total(BaseModel):
    amount: DecimalString


@pytest.mark.parametrize(
    ("stored", "sent"),
    [
        ("-900.000000000000000000", "-900"),
        ("1000.000000000000000000", "1000"),
        ("0E-18", "0"),
        ("0.000000000000000001", "0.000000000000000001"),
        (LARGEST_AMOUNT, LARGEST_AMOUNT),
    ],
)
def test_a_decimal_is_sent_without_trailing_zeros_or_an_exponent(stored: str, sent: str) -> None:
    assert _Total(amount=Decimal(stored)).model_dump(mode="json") == {"amount": sent}


def test_a_sum_wider_than_any_one_amount_keeps_every_digit() -> None:
    """What Postgres returns for 101 of the largest amounts: 39 digits, more than one row holds."""
    total = "100999999999999999999.999999999999999899"

    assert _Total(amount=Decimal(total)).model_dump(mode="json") == {"amount": total}
