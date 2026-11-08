from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.ledger.crud import accounts as account_crud
from tradinghub.ledger.crud import transactions as transaction_crud
from tradinghub.ledger.errors import (
    AccountNotFoundError,
    TransactionNotFoundError,
    TransferNotEditableError,
)
from tradinghub.ledger.models import Transaction, TransactionKind
from tradinghub.ledger.schemas.transactions import TransactionCreate, TransactionUpdate


async def create_transaction(
    db: AsyncSession, *, user_id: int, details: TransactionCreate
) -> Transaction:
    """Record income or an expense. Raises AccountNotFoundError if the account is not the user's."""
    if await account_crud.get_account(db, account_id=details.account_id, user_id=user_id) is None:
        raise AccountNotFoundError  # Before the composite foreign key can turn it into a 500
    return await transaction_crud.create_transaction(
        db,
        user_id=user_id,
        account_id=details.account_id,
        amount=_signed(details.amount, details.kind),
        kind=details.kind,
        category=details.category,
        occurred_at=details.occurred_at,
        note=details.note,
    )


async def get_transaction(db: AsyncSession, *, transaction_id: int, user_id: int) -> Transaction:
    """Return the transaction. Raises TransactionNotFoundError if it is not the user's."""
    transaction = await transaction_crud.get_transaction(
        db, transaction_id=transaction_id, user_id=user_id
    )
    if transaction is None:
        raise TransactionNotFoundError
    return transaction


async def update_transaction(
    db: AsyncSession, *, transaction_id: int, user_id: int, changes: TransactionUpdate
) -> Transaction:
    """Apply the fields the caller sent. A null category or note clears it.

    The sign is recomputed whenever the amount or the kind changes, so turning an expense into
    income flips it. Raises TransactionNotFoundError if the transaction is not the user's, and
    TransferNotEditableError if it is any row of a transfer.
    """
    transaction = await get_transaction(db, transaction_id=transaction_id, user_id=user_id)
    if transaction.transfer_group_id is not None:
        raise TransferNotEditableError
    sent = changes.model_dump(exclude_unset=True)

    if changes.amount is not None or changes.kind is not None:
        kind = changes.kind or transaction.kind
        magnitude = changes.amount or transaction.amount.copy_abs()
        sent["amount"] = _signed(magnitude, kind)

    for field, value in sent.items():
        setattr(transaction, field, value)
    await db.flush()
    return transaction


async def delete_transaction(db: AsyncSession, *, transaction_id: int, user_id: int) -> None:
    """Delete one income or expense row.

    Raises TransactionNotFoundError if it is not the user's, and TransferNotEditableError if it
    is any row of a transfer.
    """
    transaction = await get_transaction(db, transaction_id=transaction_id, user_id=user_id)
    if transaction.transfer_group_id is not None:
        raise TransferNotEditableError
    await db.delete(transaction)
    await db.flush()


def _signed(amount: Decimal, kind: TransactionKind) -> Decimal:
    """The one place the sign convention lives: the API takes a positive amount and a kind."""
    # copy_negate rather than * -1: arithmetic rounds to 28 digits, and an amount may have 36
    return amount.copy_negate() if kind is TransactionKind.EXPENSE else amount
