"""Request and response bodies for the auth endpoints."""

from pydantic import BaseModel, EmailStr, Field

MIN_PASSWORD_LENGTH = 8

# RFC 5321's limit on a full address.
MAX_EMAIL_LENGTH = 254

# Argon2 hashes whatever it is given, so an unbounded password is a cheap way to burn CPU.
MAX_PASSWORD_LENGTH = 128


class RegisterRequest(BaseModel):
    """A registration submission, rejected by the schema before any route code runs."""

    email: EmailStr = Field(max_length=MAX_EMAIL_LENGTH)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class LoginRequest(BaseModel):
    """A login submission.

    No minimum on the password: a 422 would tell an attacker no real password is that short, which
    is what the 401 hides. The maximum is different — the cap is public either way, and without it
    an unauthenticated caller can make Argon2 chew through a megabyte per request.
    """

    email: EmailStr = Field(max_length=MAX_EMAIL_LENGTH)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class UserResponse(BaseModel):
    """The public view of an account. Never carries the password hash."""

    id: int
    email: str
