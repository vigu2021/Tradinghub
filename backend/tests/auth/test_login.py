from datetime import UTC, datetime, timedelta
from http.cookies import Morsel, SimpleCookie

import jwt
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.dependencies import ACCESS_COOKIE, REFRESH_COOKIE, REFRESH_PATH
from tradinghub.auth.models import Session
from tradinghub.auth.security.tokens import ACCESS_TOKEN_LIFETIME, JWT_ALGORITHM

PASSWORD = "correct horse battery"


def _cookie(response: Response, name: str) -> Morsel[str]:
    """Return the parsed Set-Cookie the response sent for that name."""
    for header in response.headers.get_list("set-cookie"):
        jar = SimpleCookie()
        jar.load(header)
        if name in jar:
            return jar[name]
    raise AssertionError(f"no Set-Cookie for {name} in {response.headers.get_list('set-cookie')}")


async def _sign_up(client: AsyncClient, email: str) -> Response:
    """Register an account and log into it, leaving both cookies on the client."""
    await client.post("/auth/register", json={"email": email, "password": PASSWORD})
    return await client.post("/auth/login", json={"email": email, "password": PASSWORD})


async def test_login_returns_the_account(client: AsyncClient) -> None:
    response = await _sign_up(client, "account@example.com")

    assert response.status_code == 200
    assert response.json() == {"id": response.json()["id"], "email": "account@example.com"}


async def test_login_sets_both_cookies_httponly(client: AsyncClient) -> None:
    response = await _sign_up(client, "cookies@example.com")

    assert _cookie(response, ACCESS_COOKIE)["httponly"]
    assert _cookie(response, REFRESH_COOKIE)["httponly"]


async def test_the_refresh_cookie_is_scoped_to_the_auth_routes(client: AsyncClient) -> None:
    response = await _sign_up(client, "scoped@example.com")

    assert _cookie(response, ACCESS_COOKIE)["path"] == "/"
    assert _cookie(response, REFRESH_COOKIE)["path"] == REFRESH_PATH


async def test_a_wrong_password_and_an_unknown_email_answer_identically(
    client: AsyncClient,
) -> None:
    await client.post("/auth/register", json={"email": "known@example.com", "password": PASSWORD})

    wrong_password = await client.post(
        "/auth/login", json={"email": "known@example.com", "password": "not the password"}
    )
    unknown_email = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.content == unknown_email.content


async def test_a_failed_login_sets_no_cookies(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert response.headers.get_list("set-cookie") == []


async def test_me_needs_a_token(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_session"


async def test_me_rejects_a_forged_token(client: AsyncClient) -> None:
    client.cookies.set(ACCESS_COOKIE, "not-a-jwt-at-all")

    response = await client.get("/auth/me")

    assert response.status_code == 401


async def test_me_rejects_a_token_signed_with_another_secret(client: AsyncClient) -> None:
    issued_at = datetime.now(UTC)
    forged = jwt.encode(
        {"sub": "1", "iat": issued_at, "exp": issued_at + ACCESS_TOKEN_LIFETIME},
        "not-the-real-secret-but-long-enough-for-hs256",
        algorithm=JWT_ALGORITHM,
    )
    client.cookies.set(ACCESS_COOKIE, forged)

    response = await client.get("/auth/me")

    assert response.status_code == 401


async def test_me_rejects_an_expired_token(client: AsyncClient) -> None:
    from tradinghub.core.config import get_settings

    issued_at = datetime.now(UTC) - ACCESS_TOKEN_LIFETIME - timedelta(minutes=1)
    expired = jwt.encode(
        {"sub": "1", "iat": issued_at, "exp": issued_at + ACCESS_TOKEN_LIFETIME},
        get_settings().jwt_secret,
        algorithm=JWT_ALGORITHM,
    )
    client.cookies.set(ACCESS_COOKIE, expired)

    response = await client.get("/auth/me")

    assert response.status_code == 401


async def test_me_returns_the_signed_in_account(client: AsyncClient) -> None:
    await _sign_up(client, "whoami@example.com")

    response = await client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "whoami@example.com"


async def test_refresh_issues_a_new_refresh_token(client: AsyncClient) -> None:
    await _sign_up(client, "rotates@example.com")
    first_refresh_token = client.cookies[REFRESH_COOKIE]

    response = await client.post("/auth/refresh")

    assert response.status_code == 204
    assert client.cookies[REFRESH_COOKIE] != first_refresh_token


async def test_the_access_token_from_a_refresh_works(client: AsyncClient) -> None:
    await _sign_up(client, "refreshed@example.com")
    await client.post("/auth/refresh")

    response = await client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "refreshed@example.com"


async def test_refresh_without_a_cookie_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_session"


async def test_logout_clears_both_cookies(client: AsyncClient) -> None:
    await _sign_up(client, "clears@example.com")

    response = await client.post("/auth/logout")

    assert response.status_code == 204
    assert _cookie(response, ACCESS_COOKIE)["max-age"] == "0"
    assert _cookie(response, REFRESH_COOKIE)["max-age"] == "0"
    assert ACCESS_COOKIE not in client.cookies
    assert REFRESH_COOKIE not in client.cookies


async def test_logout_drops_the_session_row(client: AsyncClient, db_session: AsyncSession) -> None:
    await _sign_up(client, "dropped@example.com")
    assert await db_session.scalar(select(func.count()).select_from(Session)) == 1

    await client.post("/auth/logout")

    assert await db_session.scalar(select(func.count()).select_from(Session)) == 0


async def test_logout_without_a_session_still_succeeds(client: AsyncClient) -> None:
    response = await client.post("/auth/logout")

    assert response.status_code == 204


async def test_an_access_token_outlives_logout(client: AsyncClient) -> None:
    """The revocation gap, asserted on purpose.

    Nothing can revoke an issued access token, so logout takes up to ACCESS_TOKEN_LIFETIME to
    bite. Shortening that lifetime is the only lever. If this test ever fails, someone added a
    database lookup to get_current_user and the design changed.
    """
    await _sign_up(client, "gap@example.com")
    access_token = client.cookies[ACCESS_COOKIE]
    await client.post("/auth/logout")

    client.cookies.set(ACCESS_COOKIE, access_token)

    response = await client.get("/auth/me")

    assert response.status_code == 200
