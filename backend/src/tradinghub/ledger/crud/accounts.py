from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.ledger.models import Transaction
from tradinghub.ledger.models.account import Account, AccountType


@dataclass(frozen=True, slots=True)
class AccountWithBalance:
    account: Account
    balance: Decimal


async def get_account(db: AsyncSession, *, account_id: int, user_id: int) -> Account | None:
    """Return the account without its balance, or None if it does not exist or is someone else's.

    For checks that need only the row, such as whose it is or what unit it counts in.
    """
    return await db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )


async def get_accounts(
    db: AsyncSession, *, account_ids: list[int], user_id: int
) -> dict[int, Account]:
    """Return those of the accounts that are the user's, by id. Any others are simply absent."""
    statement = select(Account).where(Account.id.in_(account_ids), Account.user_id == user_id)
    rows = (await db.scalars(statement)).all()
    return {row.id: row for row in rows}


async def get_account_with_balance(
    db: AsyncSession, *, account_id: int, user_id: int
) -> AccountWithBalance | None:
    """Return one account with its balance, or None if it does not exist or belongs to someone else.

    The two cases are deliberately indistinguishable: telling them apart would confirm that an
    id is real.
    """
    statement = _accounts_with_balances_statement(user_id).where(Account.id == account_id)
    row = (await db.execute(statement)).one_or_none()
    return AccountWithBalance(*row) if row else None


async def list_accounts_with_balances(
    db: AsyncSession, *, user_id: int
) -> list[AccountWithBalance]:
    """Return every account the user owns with its balance, name ascending.

    One query rather than one per account. An account with no transactions has a balance of zero,
    not None, and is still listed. Archived accounts are included, because the money in one is
    still the user's.
    """
    statement = _accounts_with_balances_statement(user_id).order_by(Account.name)
    rows = (await db.execute(statement)).all()
    return [AccountWithBalance(account, balance) for (account, balance) in rows]


async def create_account(
    db: AsyncSession, *, user_id: int, name: str, unit: str, type: AccountType
) -> Account:
    """Insert an account and flush, so the returned object carries its id and timestamps.

    Raises IntegrityError when the user already has an account with that name. The comparison is
    case-insensitive, since name is CITEXT.
    """
    account = Account(user_id=user_id, name=name, unit=unit, type=type)
    db.add(account)
    await db.flush()
    return account


def _accounts_with_balances_statement(user_id: int) -> Select[tuple[Account, Decimal]]:
    return (
        select(Account, func.coalesce(func.sum(Transaction.amount), 0))
        .outerjoin(Transaction, Transaction.account_id == Account.id)
        .where(Account.user_id == user_id)
        .group_by(Account.id)
    )
