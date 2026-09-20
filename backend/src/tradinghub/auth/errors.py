"""Failures the auth services raise. Routes let them through; the handler renders them."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import ClassVar

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


class RateLimitedError(AppError):
    """Too many login failures or registrations for this email or IP inside the window.

    Retry-After is the full window rather than the time until release: the exact remaining time
    buys a user nothing and would tell an attacker precisely when to resume. The window lives
    here, not in the limiter, because the limiter imports this class and the reverse import
    would be circular.
    """

    retry_after_seconds = 15 * 60

    code = "rate_limited"
    message = "Too many attempts. Please try again later."
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    headers: ClassVar[Mapping[str, str]] = {"Retry-After": str(retry_after_seconds)}
