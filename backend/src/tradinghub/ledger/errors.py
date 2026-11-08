"""Failures the ledger services raise. Routes let them through; the handler renders them."""

from http import HTTPStatus

from tradinghub.core.errors import AppError


class AccountNotFoundError(AppError):
    """No such account, or someone else's. One answer for both, so probing ids learns nothing."""

    code = "account_not_found"
    message = "Account not found."
    status_code = HTTPStatus.NOT_FOUND


class AccountNameTakenError(AppError):
    """The user already has an account by that name, ignoring case."""

    code = "account_name_taken"
    message = "You already have an account with that name."
    status_code = HTTPStatus.CONFLICT


class TransactionNotFoundError(AppError):
    """No such transaction, or someone else's. One answer for both, as with accounts."""

    code = "transaction_not_found"
    message = "Transaction not found."
    status_code = HTTPStatus.NOT_FOUND


class TransferNotEditableError(AppError):
    """A row of a transfer was patched or deleted on its own. Changing one side alone would
    unbalance the pair, so a transfer is only deleted whole, through /transfers."""

    code = "transfer_not_editable"
    message = "A transfer cannot be changed row by row. Delete the transfer and record it again."
    status_code = HTTPStatus.CONFLICT


class TransferAmountsDifferError(AppError):
    """A transfer between two accounts of the same unit, with different amounts on each side.

    The difference would be a fee in disguise, hidden from every spending total.
    """

    code = "transfer_amounts_differ"
    message = "Between accounts of the same unit, the amount sent must equal the amount received."
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY


class TransferSameAccountError(AppError):
    """A transfer whose source and destination are the same account."""

    code = "transfer_same_account"
    message = "A transfer needs two different accounts."
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
