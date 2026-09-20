from datetime import UTC, datetime, timedelta
from http.cookies import Morsel, SimpleCookie

import jwt
import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.dependencies import ACCESS_COOKIE, REFRESH_COOKIE, REFRESH_PATH
from tradinghub.auth.models import Session
from tradinghub.auth.security.rate_limit import MAX_FAILURES_PER_EMAIL, RATE_WINDOW_SECONDS
from tradinghub.auth.security.tokens import ACCESS_TOKEN_LIFETIME, JWT_ALGORITHM
from tradinghub.core.config import get_settings

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
    """Register an account, which signs it in, leaving both cookies on the client."""
    return await client.post("/auth/register", json={"email": email, "password": PASSWORD})


async def _count_sessions(db_session: AsyncSession, user_id: int) -> int | None:
    """Scoped to one account: the development database this suite runs against holds real rows."""
    return await db_session.scalar(
        select(func.count()).select_from(Session).where(Session.user_id == user_id)
    )


async def _log_in(client: AsyncClient, email: str) -> Response:
    """Register, then log in explicitly, for the tests that assert on the login response."""
    await _sign_up(client, email)
    return await client.post("/auth/login", json={"email": email, "password": PASSWORD})


async def _fail_login(client: AsyncClient, email: str, times: int) -> None:
    """Post that many wrong passwords for the email."""
    for _ in range(times):
        await client.post("/auth/login", json={"email": email, "password": "not the password"})


async def test_login_returns_the_account(client: AsyncClient) -> None:
    signed_up = await _sign_up(client, "account@example.com")

    response = await client.post(
        "/auth/login", json={"email": "account@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert response.json() == {"id": signed_up.json()["id"], "email": "account@example.com"}


async def test_login_sets_both_cookies_httponly(client: AsyncClient) -> None:
    response = await _log_in(client, "cookies@example.com")

    assert _cookie(response, ACCESS_COOKIE)["httponly"]
    assert _cookie(response, REFRESH_COOKIE)["httponly"]


async def test_both_cookies_are_samesite_lax(client: AsyncClient) -> None:
    response = await _log_in(client, "samesite@example.com")

    assert _cookie(response, ACCESS_COOKIE)["samesite"] == "lax"
    assert _cookie(response, REFRESH_COOKIE)["samesite"] == "lax"


async def test_cookies_are_secure_when_the_setting_says_so(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "cookie_secure", True)

    response = await _log_in(client, "secure@example.com")

    assert _cookie(response, ACCESS_COOKIE)["secure"]
    assert _cookie(response, REFRESH_COOKIE)["secure"]


async def test_the_refresh_cookie_is_scoped_to_the_auth_routes(client: AsyncClient) -> None:
    response = await _log_in(client, "scoped@example.com")

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
    user_id = (await _sign_up(client, "dropped@example.com")).json()["id"]
    assert await _count_sessions(db_session, user_id) == 1

    await client.post("/auth/logout")

    assert await _count_sessions(db_session, user_id) == 0


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


async def test_login_rejects_an_overlong_password(client: AsyncClient) -> None:
    """Unauthenticated and Argon2-backed, so this is the endpoint the cap matters most on."""
    response = await client.post(
        "/auth/login", json={"email": "any@example.com", "password": "x" * 129}
    )

    assert response.status_code == 422


async def test_lockout_after_too_many_failures(client: AsyncClient) -> None:
    await _sign_up(client, "locked@example.com")
    await _fail_login(client, "locked@example.com", MAX_FAILURES_PER_EMAIL)

    response = await client.post(
        "/auth/login", json={"email": "locked@example.com", "password": PASSWORD}
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert response.headers["Retry-After"] == str(RATE_WINDOW_SECONDS)


async def test_a_successful_login_clears_the_counter(client: AsyncClient) -> None:
    await _sign_up(client, "cleared@example.com")
    await _fail_login(client, "cleared@example.com", MAX_FAILURES_PER_EMAIL - 1)
    await client.post("/auth/login", json={"email": "cleared@example.com", "password": PASSWORD})
    await _fail_login(client, "cleared@example.com", MAX_FAILURES_PER_EMAIL - 1)

    still_allowed = await client.post(
        "/auth/login", json={"email": "cleared@example.com", "password": PASSWORD}
    )
    await _fail_login(client, "cleared@example.com", MAX_FAILURES_PER_EMAIL)
    locked = await client.post(
        "/auth/login", json={"email": "cleared@example.com", "password": PASSWORD}
    )

    assert still_allowed.status_code == 200
    assert locked.status_code == 429  # the counter really restarted, the limiter is live


async def test_the_lockout_is_per_email(client: AsyncClient) -> None:
    """Both accounts share the test client's IP, so this also proves the IP limit is not
    firing early."""
    await _sign_up(client, "victim@example.com")
    await _sign_up(client, "bystander@example.com")
    await _fail_login(client, "victim@example.com", MAX_FAILURES_PER_EMAIL)

    bystander = await client.post(
        "/auth/login", json={"email": "bystander@example.com", "password": PASSWORD}
    )
    victim = await client.post(
        "/auth/login", json={"email": "victim@example.com", "password": PASSWORD}
    )

    assert bystander.status_code == 200
    assert victim.status_code == 429


async def test_an_unknown_email_is_rate_limited_too(client: AsyncClient) -> None:
    """A 429 only for registered addresses would be an enumeration oracle."""
    await _fail_login(client, "ghost@example.com", MAX_FAILURES_PER_EMAIL)

    response = await client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": PASSWORD}
    )

    assert response.status_code == 429


async def test_replaying_a_refresh_token_revokes_the_family_for_good(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Over HTTP on purpose: the revocation has to survive the 401 that reports it.

    The replay raises, and a request that raises is rolled back. Only the deliberate commit in
    refresh_session keeps the DELETE, so removing that commit must fail this test. The
    service-level tests cannot see it: they share one session, where a pending DELETE already
    looks done.
    """
    user_id = (await _sign_up(client, "replayed@example.com")).json()["id"]
    spent_refresh_token = client.cookies[REFRESH_COOKIE]
    await client.post("/auth/refresh")
    assert await _count_sessions(db_session, user_id) == 2

    client.cookies.clear()
    replay = await client.post(
        "/auth/refresh", headers={"Cookie": f"{REFRESH_COOKIE}={spent_refresh_token}"}
    )

    assert replay.status_code == 401
    assert await _count_sessions(db_session, user_id) == 0
