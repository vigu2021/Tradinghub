from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.ledger.crud import accounts as account_crud
from tradinghub.ledger.crud.accounts import AccountWithBalance
from tradinghub.ledger.errors import AccountNameTakenError, AccountNotFoundError
from tradinghub.ledger.schemas.accounts import AccountCreate, AccountUpdate


async def create_account(
    db: AsyncSession, *, user_id: int, details: AccountCreate
) -> AccountWithBalance:
    """Create an account. Raises AccountNameTakenError when the user already has one by that name.

    No lookup first: the unique constraint decides, so two racing requests cannot both win.
    """
    try:
        account = await account_crud.create_account(
            db, user_id=user_id, name=details.name, unit=details.unit, type=details.type
        )
    except IntegrityError as error:
        raise AccountNameTakenError from error
    return AccountWithBalance(account, Decimal(0))


async def get_account(db: AsyncSession, *, account_id: int, user_id: int) -> AccountWithBalance:
    """Return the account with its balance. Raises AccountNotFoundError if it is not the user's."""
    account_with_balance = await account_crud.get_account_with_balance(
        db, account_id=account_id, user_id=user_id
    )
    if account_with_balance is None:
        raise AccountNotFoundError
    return account_with_balance


async def update_account(
    db: AsyncSession, *, account_id: int, user_id: int, changes: AccountUpdate
) -> AccountWithBalance:
    """Apply the fields the caller sent and leave the rest alone.

    A null counts as not sent, since none of these can be cleared. Archiving keeps the first
    date, and a new unit converts nothing. Raises AccountNotFoundError if the account is not the
    user's, and AccountNameTakenError when a rename collides.
    """
    account_with_balance = await get_account(db, account_id=account_id, user_id=user_id)
    account = account_with_balance.account

    for field, value in changes.model_dump(exclude_none=True, exclude={"archived"}).items():
        setattr(account, field, value)

    if changes.archived is False:  # Special case: a flag, not a column. It drives archived_at
        account.archived_at = None
    elif changes.archived and account.archived_at is None:
        account.archived_at = datetime.now(UTC)

    try:
        await db.flush()
    except IntegrityError as error:
        raise AccountNameTakenError from error
    return account_with_balance
