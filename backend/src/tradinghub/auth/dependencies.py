"""Request-scoped auth: who is calling, and where the cookies live."""

from fastapi import Request

from tradinghub.auth.errors import InvalidSessionError
from tradinghub.auth.security.tokens import AccessTokenClaims, decode_access_token

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/auth/refresh"


async def get_current_user(request: Request) -> AccessTokenClaims:
    """Identify the caller from the access token cookie.

    Raises InvalidSessionError when the cookie is absent, expired, or forged; the three are
    indistinguishable to the caller. Never queries the database: a route that needs the full
    User row fetches it itself.
    """
    access_token = request.cookies.get(ACCESS_COOKIE)
    claims = decode_access_token(access_token) if access_token else None
    if claims is None:
        raise InvalidSessionError
    return claims
