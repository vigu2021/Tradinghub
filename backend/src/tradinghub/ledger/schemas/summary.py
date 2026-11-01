"""The query string and response body of the summary endpoint."""

from typing import Self

from pydantic import BaseModel, model_validator

from tradinghub.core.schemas import DecimalString, RequestModel, UtcDatetime
from tradinghub.ledger.schemas.accounts import AccountResponse


class SummaryPeriod(RequestModel):
    """The query string of GET /summary. The range includes its start and excludes its end."""

    occurred_from: UtcDatetime
    occurred_to: UtcDatetime

    @model_validator(mode="after")
    def _start_is_before_end(self) -> Self:
        if self.occurred_from >= self.occurred_to:
            raise ValueError("occurred_from must be before occurred_to")
        return self


class UnitTotal(BaseModel):
    unit: str
    amount: DecimalString


class CategoryTotal(BaseModel):
    category: str | None  # None means uncategorised
    unit: str
    amount: DecimalString


class SummaryResponse(BaseModel):
    """Balances as they stand now, and what came in and went out during the period.

    Every total is per unit, because adding GBP to BTC needs prices. Transfers count in balances
    but not in income or expenses, and expense amounts are positive: what was spent.
    """

    accounts: list[AccountResponse]
    totals: list[UnitTotal]
    income: list[UnitTotal]
    expenses: list[UnitTotal]
    by_category: list[CategoryTotal]
