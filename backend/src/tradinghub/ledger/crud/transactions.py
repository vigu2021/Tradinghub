from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.ledger.models import Transaction
from tradinghub.ledger.schemas.transactions import TransactionFilters


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
