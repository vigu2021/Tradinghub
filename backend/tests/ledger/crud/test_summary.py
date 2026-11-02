from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models import User
from tradinghub.ledger.crud.accounts import create_account
from tradinghub.ledger.crud.summary import (
    get_balances_per_unit,
    get_expenses_by_category,
    get_income_and_expenses_per_unit,
)
from tradinghub.ledger.models import Account, AccountType, Transaction, TransactionKind
from tradinghub.ledger.schemas.summary import CategoryTotal, SummaryPeriod, UnitTotal
from tradinghub.ledger.schemas.transfers import TransferCreate
from tradinghub.ledger.services.transfers import create_transfer

MID_SEPTEMBER = datetime(2026, 9, 15, tzinfo=UTC)
OCTOBER = datetime(2026, 10, 1, tzinfo=UTC)
MID_OCTOBER = datetime(2026, 10, 15, tzinfo=UTC)
NOVEMBER = datetime(2026, 11, 1, tzinfo=UTC)
OCTOBER_PERIOD = SummaryPeriod.model_validate(
    {"occurred_from": OCTOBER.isoformat(), "occurred_to": NOVEMBER.isoformat()}
)


async def _account(
    db_session: AsyncSession, user: User, unit: str = "GBP", name: str = ""
) -> Account:
    return await create_account(
        db_session, user_id=user.id, name=name or unit, unit=unit, type=AccountType.CASH
    )


async def _record(
    db_session: AsyncSession,
    account: Account,
    amount: str,
    *,
    kind: TransactionKind = TransactionKind.EXPENSE,
    category: str | None = "food",
    occurred_at: datetime = MID_OCTOBER,
) -> None:
    db_session.add(
        Transaction(
            user_id=account.user_id,
            account_id=account.id,
            amount=Decimal(amount),
            kind=kind,
            category=category,
            occurred_at=occurred_at,
        )
    )
    await db_session.flush()


async def _transfer(
    db_session: AsyncSession, sender: Account, receiver: Account, **overrides: str | int
) -> None:
    details = TransferCreate.model_validate(
        {
            "from_account_id": sender.id,
            "to_account_id": receiver.id,
            "amount_sent": "500",
            "amount_received": "500",
            "occurred_at": MID_OCTOBER.isoformat(),
        }
        | overrides
    )
    await create_transfer(db_session, user_id=sender.user_id, details=details)


async def _income_and_expenses(
    db_session: AsyncSession, user: User
) -> tuple[list[UnitTotal], list[UnitTotal]]:
    totals = await get_income_and_expenses_per_unit(
        db_session, user_id=user.id, period=OCTOBER_PERIOD
    )
    return totals.income, totals.expenses


async def test_balances_are_grouped_per_unit(db_session: AsyncSession, alice: User) -> None:
    """Never summed across units, and a unit with no transactions yet is listed at zero."""
    chase = await _account(db_session, alice, "GBP", "Chase")
    monzo = await _account(db_session, alice, "GBP", "Monzo")
    wallet = await _account(db_session, alice, "BTC")
    await _account(db_session, alice, "EUR")
    await _record(db_session, chase, "100", kind=TransactionKind.INCOME)
    await _record(db_session, monzo, "-30")
    await _record(db_session, wallet, "0.5", kind=TransactionKind.INCOME)

    assert await get_balances_per_unit(db_session, user_id=alice.id) == [
        UnitTotal(unit="BTC", amount=Decimal("0.5")),
        UnitTotal(unit="EUR", amount=Decimal(0)),
        UnitTotal(unit="GBP", amount=Decimal(70)),
    ]


async def test_balances_count_every_date_and_archived_accounts(
    db_session: AsyncSession, alice: User
) -> None:
    """A balance is what you hold now, so neither the period nor archiving hides money."""
    account = await _account(db_session, alice)
    await _record(
        db_session, account, "100", kind=TransactionKind.INCOME, occurred_at=MID_SEPTEMBER
    )
    await _record(db_session, account, "-30", occurred_at=NOVEMBER)
    account.archived_at = NOVEMBER
    await db_session.flush()

    assert await get_balances_per_unit(db_session, user_id=alice.id) == [
        UnitTotal(unit="GBP", amount=Decimal(70))
    ]


async def test_income_and_expenses_cover_only_the_period(
    db_session: AsyncSession, alice: User
) -> None:
    """Expenses come back positive: what was spent. A unit with none of a kind is left out."""
    gbp = await _account(db_session, alice, "GBP")
    btc = await _account(db_session, alice, "BTC")
    await _record(db_session, gbp, "2000", kind=TransactionKind.INCOME)
    await _record(db_session, gbp, "-900")
    await _record(db_session, gbp, "-1", occurred_at=MID_SEPTEMBER)
    await _record(db_session, gbp, "-2", occurred_at=NOVEMBER + timedelta(days=1))
    await _record(db_session, btc, "0.1", kind=TransactionKind.INCOME)

    income, expenses = await _income_and_expenses(db_session, alice)

    assert income == [
        UnitTotal(unit="BTC", amount=Decimal("0.1")),
        UnitTotal(unit="GBP", amount=Decimal(2000)),
    ]
    assert expenses == [UnitTotal(unit="GBP", amount=Decimal(900))]


async def test_the_period_includes_its_start_and_excludes_its_end(
    db_session: AsyncSession, alice: User
) -> None:
    """A row at midnight on the first counts in the month it starts, never in two months."""
    account = await _account(db_session, alice)
    await _record(db_session, account, "-10", occurred_at=OCTOBER)
    await _record(db_session, account, "-20", occurred_at=NOVEMBER)

    _, expenses = await _income_and_expenses(db_session, alice)
    by_category = await get_expenses_by_category(
        db_session, user_id=alice.id, period=OCTOBER_PERIOD
    )

    assert expenses == [UnitTotal(unit="GBP", amount=Decimal(10))]
    assert by_category == [CategoryTotal(category="food", unit="GBP", amount=Decimal(10))]


async def test_transfers_are_absent_from_income_and_expenses(
    db_session: AsyncSession, alice: User
) -> None:
    """Moving your own money is neither earning nor spending."""
    await _transfer(
        db_session,
        await _account(db_session, alice, "GBP"),
        await _account(db_session, alice, "BTC"),
    )

    income, expenses = await _income_and_expenses(db_session, alice)
    by_category = await get_expenses_by_category(
        db_session, user_id=alice.id, period=OCTOBER_PERIOD
    )

    assert (income, expenses, by_category) == ([], [], [])


async def test_the_fee_is_included_in_the_expense_total(
    db_session: AsyncSession, alice: User
) -> None:
    """The 500 moved is not spending, but the 3 fee is, and it lands under its own category."""
    chase = await _account(db_session, alice, "GBP", "Chase")
    monzo = await _account(db_session, alice, "GBP", "Monzo")
    await _record(db_session, chase, "-40")
    await _transfer(db_session, chase, monzo, fee="3", fee_account_id=chase.id, fee_category="fees")

    _, expenses = await _income_and_expenses(db_session, alice)
    by_category = await get_expenses_by_category(
        db_session, user_id=alice.id, period=OCTOBER_PERIOD
    )

    assert expenses == [UnitTotal(unit="GBP", amount=Decimal(43))]
    assert by_category == [
        CategoryTotal(category="food", unit="GBP", amount=Decimal(40)),
        CategoryTotal(category="fees", unit="GBP", amount=Decimal(3)),
    ]


async def test_transfers_are_present_in_balances(db_session: AsyncSession, alice: User) -> None:
    gbp = await _account(db_session, alice, "GBP")
    btc = await _account(db_session, alice, "BTC")
    await _record(db_session, gbp, "1000", kind=TransactionKind.INCOME)
    await _transfer(db_session, gbp, btc, amount_received="0.01")

    assert await get_balances_per_unit(db_session, user_id=alice.id) == [
        UnitTotal(unit="BTC", amount=Decimal("0.01")),
        UnitTotal(unit="GBP", amount=Decimal(500)),
    ]


async def test_categories_group_and_uncategorised_rows_come_back_as_null(
    db_session: AsyncSession, alice: User
) -> None:
    """Grouped per category and unit, units in order, the biggest spend first within each."""
    gbp = await _account(db_session, alice, "GBP")
    eur = await _account(db_session, alice, "EUR")
    await _record(db_session, gbp, "-30", category="food")
    await _record(db_session, gbp, "-5", category="food")
    await _record(db_session, gbp, "-900", category="rent")
    await _record(db_session, gbp, "-2", category=None)
    await _record(db_session, gbp, "-1", category=None)
    await _record(db_session, eur, "-8", category="food")
    await _record(db_session, gbp, "5000", kind=TransactionKind.INCOME, category="salary")

    assert await get_expenses_by_category(db_session, user_id=alice.id, period=OCTOBER_PERIOD) == [
        CategoryTotal(category="food", unit="EUR", amount=Decimal(8)),
        CategoryTotal(category="rent", unit="GBP", amount=Decimal(900)),
        CategoryTotal(category="food", unit="GBP", amount=Decimal(35)),
        CategoryTotal(category=None, unit="GBP", amount=Decimal(3)),
    ]


async def test_another_users_rows_never_appear(
    db_session: AsyncSession, alice: User, bob: User
) -> None:
    bobs_account = await _account(db_session, bob)
    await _record(db_session, bobs_account, "100", kind=TransactionKind.INCOME)
    await _record(db_session, bobs_account, "-40")

    income, expenses = await _income_and_expenses(db_session, alice)
    by_category = await get_expenses_by_category(
        db_session, user_id=alice.id, period=OCTOBER_PERIOD
    )

    assert await get_balances_per_unit(db_session, user_id=alice.id) == []
    assert (income, expenses, by_category) == ([], [], [])
