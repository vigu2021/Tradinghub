"""Ledger endpoints. Every one acts as the signed-in user, taken from the access cookie."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.dependencies import get_current_user
from tradinghub.auth.security.tokens import AccessTokenClaims
from tradinghub.core.database import get_db
from tradinghub.ledger.crud import accounts as account_crud
from tradinghub.ledger.crud import transactions as transaction_crud
from tradinghub.ledger.crud.accounts import AccountWithBalance
from tradinghub.ledger.schemas.accounts import AccountCreate, AccountResponse, AccountUpdate
from tradinghub.ledger.schemas.transactions import (
    TransactionCreate,
    TransactionFilters,
    TransactionPage,
    TransactionResponse,
    TransactionUpdate,
)
from tradinghub.ledger.services import accounts as account_service
from tradinghub.ledger.services import transactions as transaction_service

router = APIRouter(tags=["ledger"])


@router.post("/accounts", status_code=HTTPStatus.CREATED)
async def create_account(
    payload: AccountCreate,
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    """Open an account. Raises AccountNameTakenError when the name is already used."""
    account_with_balance = await account_service.create_account(
        db, user_id=claims.user_id, details=payload
    )
    return _account_response(account_with_balance)


@router.get("/accounts")
async def list_accounts(
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AccountResponse]:
    """Every account the caller owns, archived ones included, name ascending."""
    accounts = await account_crud.list_accounts_with_balances(db, user_id=claims.user_id)
    return [_account_response(account_with_balance) for account_with_balance in accounts]


@router.get("/accounts/{account_id}")
async def get_account(
    account_id: int,
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    """One account with its balance. Raises AccountNotFoundError if it is not the caller's."""
    account_with_balance = await account_service.get_account(
        db, account_id=account_id, user_id=claims.user_id
    )
    return _account_response(account_with_balance)


@router.patch("/accounts/{account_id}")
async def update_account(
    account_id: int,
    payload: AccountUpdate,
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    """Rename, change unit or type, archive or restore.

    Raises AccountNotFoundError if it is not the caller's, and AccountNameTakenError when a rename
    collides.
    """
    account_with_balance = await account_service.update_account(
        db, account_id=account_id, user_id=claims.user_id, changes=payload
    )
    return _account_response(account_with_balance)


@router.post("/transactions", status_code=HTTPStatus.CREATED)
async def create_transaction(
    payload: TransactionCreate,
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionResponse:
    """Record income or an expense. Raises AccountNotFoundError if the account is not yours."""
    transaction = await transaction_service.create_transaction(
        db, user_id=claims.user_id, details=payload
    )
    return TransactionResponse.model_validate(transaction)


@router.get("/transactions")
async def list_transactions(
    filters: Annotated[TransactionFilters, Query()],
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionPage:
    """One page of the caller's transactions, newest first, with the total that match."""
    transactions, total = await transaction_crud.list_transactions(
        db, user_id=claims.user_id, filters=filters
    )
    return TransactionPage(
        items=[TransactionResponse.model_validate(transaction) for transaction in transactions],
        total=total,
    )


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: int,
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionResponse:
    """One transaction. Raises TransactionNotFoundError if it is not the caller's."""
    transaction = await transaction_service.get_transaction(
        db, transaction_id=transaction_id, user_id=claims.user_id
    )
    return TransactionResponse.model_validate(transaction)


@router.patch("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionResponse:
    """Change any subset of fields except the account. Raises TransactionNotFoundError if it is
    not the caller's."""
    transaction = await transaction_service.update_transaction(
        db, transaction_id=transaction_id, user_id=claims.user_id, changes=payload
    )
    return TransactionResponse.model_validate(transaction)


@router.delete("/transactions/{transaction_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove one transaction. Raises TransactionNotFoundError if it is not the caller's."""
    await transaction_service.delete_transaction(
        db, transaction_id=transaction_id, user_id=claims.user_id
    )


def _account_response(account_with_balance: AccountWithBalance) -> AccountResponse:
    account = account_with_balance.account
    return AccountResponse(
        id=account.id,
        name=account.name,
        unit=account.unit,
        type=account.type,
        balance=account_with_balance.balance,
        archived_at=account.archived_at,
    )
