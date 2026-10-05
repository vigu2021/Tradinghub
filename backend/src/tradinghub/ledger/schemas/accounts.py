"""Request and response bodies for the account endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from tradinghub.core.schemas import RequestModel
from tradinghub.ledger.models import AccountType

AccountName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Unit = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=2, max_length=10)
]


class AccountCreate(RequestModel):
    name: AccountName
    unit: Unit
    type: AccountType


class AccountUpdate(RequestModel):
    """A partial update: an omitted field is left alone.

    archived is a boolean rather than a timestamp. The caller says what it wants and the service
    decides when, which is also what keeps a second archive from overwriting the first date.
    """

    name: AccountName | None = None
    unit: Unit | None = None
    type: AccountType | None = None
    archived: bool | None = None


class AccountResponse(BaseModel):
    """An account and what is in it. Carries no user_id: the caller knows who they are.

    archived_at rather than a boolean, so the UI can say when an account was closed. The request
    is the other way round: it sends a boolean, because only the server should set the timestamp.
    """

    id: int
    name: str
    unit: str
    type: AccountType
    balance: Decimal
    archived_at: datetime | None
