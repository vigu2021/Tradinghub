from httpx import AsyncClient

FRONTEND_ORIGIN = "http://localhost:3000"

PREFLIGHT_HEADERS = {"Access-Control-Request-Method": "POST"}


async def test_preflight_allows_the_frontend_origin(client: AsyncClient) -> None:
    response = await client.options(
        "/auth/login", headers={"Origin": FRONTEND_ORIGIN, **PREFLIGHT_HEADERS}
    )

    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_other_origins_are_not_allowed(client: AsyncClient) -> None:
    response = await client.options(
        "/auth/login", headers={"Origin": "http://evil.example.com", **PREFLIGHT_HEADERS}
    )

    assert "access-control-allow-origin" not in response.headers


async def test_a_disallowed_method_fails_preflight(client: AsyncClient) -> None:
    response = await client.options(
        "/auth/login",
        headers={"Origin": FRONTEND_ORIGIN, "Access-Control-Request-Method": "DELETE"},
    )

    assert response.status_code == 400
    assert "DELETE" not in response.headers["access-control-allow-methods"]


async def test_a_simple_response_carries_the_origin(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"Origin": FRONTEND_ORIGIN})

    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
