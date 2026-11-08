import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.ledger.crud import accounts as account_crud
from tradinghub.ledger.crud import transactions as transaction_crud
from tradinghub.ledger.errors import (
    AccountNotFoundError,
    TransferAmountsDifferError,
    TransferNotFoundError,
    TransferSameAccountError,
)
from tradinghub.ledger.models import Transaction, TransactionKind
from tradinghub.ledger.schemas.transfers import TransferCreate


async def create_transfer(
    db: AsyncSession, *, user_id: int, details: TransferCreate
) -> list[Transaction]:
    """Record both sides of a transfer, plus any fee as an expense, under one group id.

    The fee can come from a third account, as when a Binance trade pays its fee in BNB. Raises
    TransferSameAccountError, AccountNotFoundError or TransferAmountsDifferError, all before a row
    is written.
    """
    if details.from_account_id == details.to_account_id:
        raise TransferSameAccountError

    account_ids = {details.from_account_id, details.to_account_id}
    if details.fee_account_id is not None:
        account_ids.add(details.fee_account_id)
    accounts = await account_crud.get_accounts(db, account_ids=list(account_ids), user_id=user_id)
    if len(accounts) != len(account_ids):
        raise AccountNotFoundError

    same_unit = accounts[details.from_account_id].unit == accounts[details.to_account_id].unit
    if same_unit and details.amount_sent != details.amount_received:
        raise TransferAmountsDifferError

    group = uuid.uuid4()
    # copy_negate rather than * -1: arithmetic rounds to 28 digits, and an amount may have 36
    transactions = [
        _transaction_row(
            user_id, group, details, details.from_account_id, details.amount_sent.copy_negate()
        ),
        _transaction_row(user_id, group, details, details.to_account_id, details.amount_received),
    ]
    # An expense, so the fee counts as spending. The schema requires both fields together; checking
    # both here is for the type checker.
    if details.fee is not None and details.fee_account_id is not None:
        transactions.append(
            _transaction_row(
                user_id,
                group,
                details,
                details.fee_account_id,
                details.fee.copy_negate(),
                TransactionKind.EXPENSE,
                details.fee_category,
            )
        )
    await transaction_crud.create_transactions(db, transactions=transactions)
    return transactions


async def delete_transfer(db: AsyncSession, *, transfer_group_id: uuid.UUID, user_id: int) -> None:
    """Delete every row of the transfer, fee included.

    Raises TransferNotFoundError if no row of it is the user's.
    """
    deleted = await transaction_crud.delete_transfer_group(
        db, transfer_group_id=transfer_group_id, user_id=user_id
    )
    if not deleted:
        raise TransferNotFoundError


def _transaction_row(
    user_id: int,
    group: uuid.UUID,
    details: TransferCreate,
    account_id: int,
    amount: Decimal,
    kind: TransactionKind = TransactionKind.TRANSFER,
    category: str | None = None,
) -> Transaction:
    return Transaction(
        user_id=user_id,
        account_id=account_id,
        amount=amount,
        kind=kind,
        category=category,
        occurred_at=details.occurred_at,
        note=details.note,
        transfer_group_id=group,
    )
