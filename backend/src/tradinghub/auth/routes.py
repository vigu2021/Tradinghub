"""Authentication endpoints."""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.crud.user import get_user_by_id
from tradinghub.auth.dependencies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    REFRESH_PATH,
    get_current_user,
)
from tradinghub.auth.errors import InvalidSessionError
from tradinghub.auth.schemas.session import LoginRequest
from tradinghub.auth.schemas.user import RegisterRequest, UserResponse
from tradinghub.auth.security.tokens import (
    ACCESS_TOKEN_LIFETIME,
    REFRESH_TOKEN_LIFETIME,
    AccessTokenClaims,
)
from tradinghub.auth.services.sessions import TokenPair, login_user, logout_user, refresh_session
from tradinghub.auth.services.users import register_user
from tradinghub.core.config import get_settings
from tradinghub.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_MAX_AGE = int(ACCESS_TOKEN_LIFETIME.total_seconds())
REFRESH_MAX_AGE = int(REFRESH_TOKEN_LIFETIME.total_seconds())


def _set_cookie(response: Response, name: str, value: str, max_age: int, path: str) -> None:
    """Write one auth cookie. The flags live here so setting and clearing cannot disagree."""
    settings = get_settings()
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        path=path,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _set_auth_cookies(response: Response, token_pair: TokenPair) -> None:
    """Send both tokens back. The refresh cookie is scoped so the browser sends it nowhere else."""
    _set_cookie(response, ACCESS_COOKIE, token_pair.access_token, ACCESS_MAX_AGE, "/")
    _set_cookie(response, REFRESH_COOKIE, token_pair.refresh_token, REFRESH_MAX_AGE, REFRESH_PATH)


def _clear_auth_cookies(response: Response) -> None:
    """Expire both cookies.

    An empty value with max_age 0 through the same helper, because a cookie is only replaced by
    one carrying the identical name, path, and domain. A mismatch leaves the original in place.
    """
    _set_cookie(response, ACCESS_COOKIE, "", 0, "/")
    _set_cookie(response, REFRESH_COOKIE, "", 0, REFRESH_PATH)


@router.post("/register", status_code=HTTPStatus.CREATED)
async def register(
    payload: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> Response:
    """Register an account. 201 and an empty body whether or not the email was taken.

    The return value is discarded on purpose, and no cookie is set: registering is not signing in.
    """
    await register_user(db, payload.email, payload.password)
    return Response(status_code=HTTPStatus.CREATED)


@router.post("/login")
async def login(
    payload: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)], response: Response
) -> UserResponse:
    """Start a session and set both cookies. Raises InvalidCredentialsError on a failed login."""
    user, token_pair = await login_user(db, email=payload.email, raw_password=payload.password)
    _set_auth_cookies(response, token_pair)
    return UserResponse(id=user.id, email=user.email)


@router.post("/refresh", status_code=HTTPStatus.NO_CONTENT)
async def refresh(
    db: Annotated[AsyncSession, Depends(get_db)],
    raw_refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    """Rotate the session and set both cookies. Raises InvalidSessionError when it cannot.

    A missing cookie fails exactly like a rejected one: a caller learns nothing from which.
    """
    if raw_refresh_token is None:
        raise InvalidSessionError
    token_pair = await refresh_session(db, raw_refresh_token)
    response = Response(status_code=HTTPStatus.NO_CONTENT)
    _set_auth_cookies(response, token_pair)
    return response


@router.post("/logout", status_code=HTTPStatus.NO_CONTENT)
async def logout(
    db: Annotated[AsyncSession, Depends(get_db)],
    raw_refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    """End the session and clear both cookies. Never an error, with or without a live session."""
    if raw_refresh_token is not None:
        await logout_user(db, raw_refresh_token)
    response = Response(status_code=HTTPStatus.NO_CONTENT)
    _clear_auth_cookies(response)
    return response


@router.get("/me")
async def me(
    claims: Annotated[AccessTokenClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Return the signed-in account. Raises InvalidSessionError without a usable access token.

    The one endpoint that queries for a User: the email it answers with is not in the token.
    """
    user = await get_user_by_id(db, claims.user_id)
    if user is None:
        raise InvalidSessionError
    return UserResponse(id=user.id, email=user.email)
