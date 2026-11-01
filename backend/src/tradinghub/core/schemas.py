"""The base every request body inherits from, and types shared by responses."""

from datetime import UTC, datetime
from decimal import Context, Decimal
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
)

# A string in JSON, since a float would lose precision. Normalised, because NUMERIC(36, 18) hands
# every value back with 18 decimal places, and -900 should not read as -900.000000000000000000.
# The context is wide enough for all 36 digits: the default one rounds to 28.
WIDE = Context(prec=38)
DecimalString = Annotated[
    Decimal, PlainSerializer(lambda value: format(value.normalize(WIDE), "f"), return_type=str)
]

# What an INTEGER primary key can hold. Anything else cannot exist, and asyncpg refuses to send it.
RowId = Annotated[int, Field(ge=1, le=2**31 - 1)]

# Postgres text cannot store NUL, though JSON can carry it. For StringConstraints on stored text.
NO_NUL_PATTERN = r"^[^\x00]*$"


def _parse_iso_8601(value: object) -> datetime:
    # Pydantic would otherwise read a bare number as a Unix timestamp, in seconds or milliseconds.
    if not isinstance(value, str):
        raise ValueError("must be an ISO 8601 string")
    return datetime.fromisoformat(value)


# A naive time is a 422, never a guess at the timezone.
UtcDatetime = Annotated[
    AwareDatetime,
    BeforeValidator(_parse_iso_8601),
    Field(ge=datetime(1900, 1, 1, tzinfo=UTC), lt=datetime(2100, 1, 1, tzinfo=UTC)),
    AfterValidator(lambda value: value.astimezone(UTC)),
]


class RequestModel(BaseModel):
    """A request body. An unknown field is a 422, not something to ignore.

    Pydantic discards unexpected fields by default, which on a partial update means a misspelled
    field name returns 200 and changes nothing. Responses do not inherit this: we build those
    ourselves, so an unexpected field cannot appear.
    """

    model_config = ConfigDict(extra="forbid")
