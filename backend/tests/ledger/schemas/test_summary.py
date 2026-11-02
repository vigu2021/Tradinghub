from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tradinghub.ledger.schemas.summary import SummaryPeriod


def test_a_period_with_an_offset_is_held_in_utc() -> None:
    """The frontend sends local month boundaries, so October in London starts at 23:00 UTC."""
    period = SummaryPeriod.model_validate(
        {"occurred_from": "2026-10-01T00:00:00+01:00", "occurred_to": "2026-11-01T00:00:00Z"}
    )

    assert period.occurred_from == datetime(2026, 9, 30, 23, tzinfo=UTC)
    assert period.occurred_to == datetime(2026, 11, 1, tzinfo=UTC)


@pytest.mark.parametrize("occurred_to", ["2026-10-01T00:00:00Z", "2026-09-01T00:00:00Z"])
def test_a_period_must_end_after_it_starts(occurred_to: str) -> None:
    """An empty or reversed range is a mistake, not a request for nothing."""
    with pytest.raises(ValidationError):
        SummaryPeriod.model_validate(
            {"occurred_from": "2026-10-01T00:00:00Z", "occurred_to": occurred_to}
        )


def test_a_period_without_a_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SummaryPeriod.model_validate(
            {"occurred_from": "2026-10-01T00:00:00", "occurred_to": "2026-11-01T00:00:00Z"}
        )
