"""Request-scoped auth: who is calling, and where the cookies live."""

from fastapi import Request

from tradinghub.auth.errors import InvalidSessionError
from tradinghub.auth.security.tokens import AccessTokenClaims, decode_access_token
from tradinghub.core.logging import user_id

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/auth"


async def get_current_user(request: Request) -> AccessTokenClaims:
    """Identify the caller from the access token cookie.

    Raises InvalidSessionError when the cookie is absent, expired, or forged; the three are
    indistinguishable to the caller. Never queries the database: a route that needs the full
    User row fetches it itself.

    Records the user id for logging twice: the context var reaches log lines written during the
    request, and request.state reaches the access line, which the middleware writes from a
    different task.
    """
    access_token = request.cookies.get(ACCESS_COOKIE)
    claims = decode_access_token(access_token) if access_token else None
    if claims is None:
        raise InvalidSessionError

    user_id.set(str(claims.user_id))
    request.state.user_id = str(claims.user_id)
    return claims
