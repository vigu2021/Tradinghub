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
