"""Request bodies for the session endpoints: login, refresh, logout."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """A login submission. No length rule on the password: a 422 would leak what the 401 hides."""

    email: EmailStr
    password: str
