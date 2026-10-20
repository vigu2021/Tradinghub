from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.ledger.crud import accounts as account_crud
from tradinghub.ledger.crud.accounts import AccountWithBalance
from tradinghub.ledger.errors import AccountNameTakenError, AccountNotFoundError
from tradinghub.ledger.schemas.accounts import AccountCreate


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
    found = await account_crud.get_account_with_balance(db, account_id=account_id, user_id=user_id)
    if found is None:
        raise AccountNotFoundError
    return found
