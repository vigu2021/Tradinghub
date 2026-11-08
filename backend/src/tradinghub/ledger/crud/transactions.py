from datetime import datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.ledger.models import Transaction, TransactionKind
from tradinghub.ledger.schemas.transactions import TransactionFilters


async def get_transaction(
    db: AsyncSession, *, transaction_id: int, user_id: int
) -> Transaction | None:
    """Return the transaction, or None if it does not exist or belongs to someone else."""
    return await db.scalar(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )


async def list_transactions(
    db: AsyncSession, *, user_id: int, filters: TransactionFilters
) -> tuple[list[Transaction], int]:
    """Return one page of the user's transactions, newest first, and how many match in all.

    Filters combine with AND. The date range includes occurred_from and excludes occurred_to, so
    consecutive months never both count a row stamped exactly at midnight. id breaks ties in the
    order, so paging through rows that share a time never shows one twice or skips one.
    """
    conditions: list[ColumnElement[bool]] = [Transaction.user_id == user_id]
    if filters.account_id is not None:
        conditions.append(Transaction.account_id == filters.account_id)
    if filters.kind is not None:
        conditions.append(Transaction.kind == filters.kind)
    if filters.category is not None:
        conditions.append(Transaction.category == filters.category)
    if filters.occurred_from is not None:
        conditions.append(Transaction.occurred_at >= filters.occurred_from)
    if filters.occurred_to is not None:
        conditions.append(Transaction.occurred_at < filters.occurred_to)

    count_statement = select(func.count()).select_from(Transaction).where(*conditions)
    page_statement = (
        select(Transaction)
        .where(*conditions)
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )

    total = await db.scalar(count_statement) or 0
    rows = await db.scalars(page_statement)
    return list(rows), total


async def create_transaction(
    db: AsyncSession,
    *,
    user_id: int,
    account_id: int,
    amount: Decimal,
    kind: TransactionKind,
    category: str | None,
    occurred_at: datetime,
    note: str | None,
) -> Transaction:
    """Insert a transaction and flush, so the returned object carries its id.

    amount is stored as given, so the caller has already applied the sign. Raises IntegrityError
    when the account is not this user's: the composite foreign key refuses it.
    """
    transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        amount=amount,
        kind=kind,
        category=category,
        occurred_at=occurred_at,
        note=note,
    )
    db.add(transaction)
    await db.flush()
    return transaction


async def create_transactions(db: AsyncSession, *, transactions: list[Transaction]) -> None:
    """Insert several transactions in one flush, so each given object carries its id afterwards.

    Raises IntegrityError when an account is not this user's: the composite foreign key refuses it.
    """
    db.add_all(transactions)
    await db.flush()


async def delete_transaction(db: AsyncSession, *, transaction_id: int, user_id: int) -> bool:
    """Delete the user's transaction.

    Return False if there was nothing to delete, theirs or anyone's.
    """
    deleted_ids = await db.scalars(
        delete(Transaction)
        .where(Transaction.user_id == user_id, Transaction.id == transaction_id)
        .returning(Transaction.id)
    )
    return bool(deleted_ids.all())
