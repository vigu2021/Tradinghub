"""Failures the auth services raise. Routes let them through; the handler renders them."""

from http import HTTPStatus

from tradinghub.core.errors import AppError


class InvalidCredentialsError(AppError):
    """A login with an unknown email or a wrong password.

    One class for both deliberately. Separate codes would tell a caller which emails are
    registered, which is what the dummy hash in the login service exists to hide.
    """

    code = "invalid_credentials"
    message = "Email or password is incorrect."
    status_code = HTTPStatus.UNAUTHORIZED


class InvalidSessionError(AppError):
    """A refresh or access token that is unknown, expired, or already spent.

    One class for all of them, for the same reason as above: which one it was is exactly what a
    thief testing a stolen token wants to learn. Distinct from a failed login because the endpoint
    already gives that away, and the frontend needs to tell "log in again" from "you typed it
    wrong".
    """

    code = "invalid_session"
    message = "Your session has expired. Please log in again."
    status_code = HTTPStatus.UNAUTHORIZED


class EmailTakenError(AppError):
    """Registration with an email that already has an account.

    Registering signs you in, so a duplicate cannot be answered the same way as a success: one
    sets cookies and one cannot. Enumeration is therefore unavoidable here, and saying so plainly
    is more useful than leaking the same fact through a missing cookie. Rate limiting is what
    makes it expensive to exploit.
    """

    code = "email_taken"
    message = "That email is already registered."
    status_code = HTTPStatus.CONFLICT
