from typing import NamedTuple

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import coalesce

from tradinghub.ledger.models import Account, Transaction, TransactionKind
from tradinghub.ledger.schemas.summary import CategoryTotal, SummaryPeriod, UnitTotal


class IncomeAndExpenses(NamedTuple):
    income: list[UnitTotal]
    expenses: list[UnitTotal]


async def get_balances_per_unit(db: AsyncSession, *, user_id: int) -> list[UnitTotal]:
    statement = (
        select(Account.unit, coalesce(func.sum(Transaction.amount), 0))
        .select_from(Account)
        .outerjoin(Transaction, Account.id == Transaction.account_id)
        .where(Account.user_id == user_id)
        .group_by(Account.unit)
        .order_by(Account.unit)
    )
    rows = (await db.execute(statement)).all()
    return [UnitTotal(unit=unit, amount=amount) for unit, amount in rows]


async def get_income_and_expenses_per_unit(
    db: AsyncSession, *, user_id: int, period: SummaryPeriod
) -> IncomeAndExpenses:
    statement = (
        select(
            Account.unit,
            func.sum(Transaction.amount).filter(Transaction.kind == TransactionKind.INCOME),
            -func.sum(Transaction.amount).filter(Transaction.kind == TransactionKind.EXPENSE),
        )
        .select_from(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(*_owned_and_within_period(user_id, period))
        .group_by(Account.unit)
        .order_by(Account.unit)
    )
    rows = (await db.execute(statement)).all()
    income = [UnitTotal(unit=unit, amount=amount) for unit, amount, _ in rows if amount is not None]
    expenses = [
        UnitTotal(unit=unit, amount=amount) for unit, _, amount in rows if amount is not None
    ]
    return IncomeAndExpenses(income=income, expenses=expenses)


async def get_expenses_by_category(
    db: AsyncSession, *, user_id: int, period: SummaryPeriod
) -> list[CategoryTotal]:
    spent = -func.sum(Transaction.amount)
    statement = (
        select(Transaction.category, Account.unit, spent)
        .select_from(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(
            *_owned_and_within_period(user_id, period), Transaction.kind == TransactionKind.EXPENSE
        )
        .group_by(Transaction.category, Account.unit)
        .order_by(Account.unit, spent.desc())
    )
    rows = (await db.execute(statement)).all()
    return [
        CategoryTotal(category=category, unit=unit, amount=amount)
        for category, unit, amount in rows
    ]


def _owned_and_within_period(user_id: int, period: SummaryPeriod) -> list[ColumnElement[bool]]:
    return [
        Transaction.user_id == user_id,
        Transaction.occurred_at >= period.occurred_from,
        Transaction.occurred_at < period.occurred_to,
    ]
