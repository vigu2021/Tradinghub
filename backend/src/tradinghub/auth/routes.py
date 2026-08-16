"""Authentication endpoints."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.schemas.user import RegisterRequest
from tradinghub.auth.services.users import register_user
from tradinghub.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=HTTPStatus.CREATED)
async def register(
    payload: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> Response:
    """Register an account. 201 and an empty body whether or not the email was taken.

    The return value is discarded on purpose, and no cookie is set: registering is not signing in.
    """
    await register_user(db, payload.email, payload.password)
    return Response(status_code=HTTPStatus.CREATED)
