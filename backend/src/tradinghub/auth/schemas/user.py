"""Request and response bodies for user accounts."""

from pydantic import BaseModel, EmailStr, Field

MIN_PASSWORD_LENGTH = 8


class RegisterRequest(BaseModel):
    """A registration submission, rejected by the schema before any route code runs."""

    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class UserResponse(BaseModel):
    """The public view of an account. Never carries the password hash."""

    id: int
    email: str
