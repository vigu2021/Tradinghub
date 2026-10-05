"""The base every request body inherits from."""

from pydantic import BaseModel, ConfigDict


class RequestModel(BaseModel):
    """A request body. An unknown field is a 422, not something to ignore.

    Pydantic discards unexpected fields by default, which on a partial update means a misspelled
    field name returns 200 and changes nothing. Responses do not inherit this: we build those
    ourselves, so an unexpected field cannot appear.
    """

    model_config = ConfigDict(extra="forbid")
