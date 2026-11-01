from httpx import ASGITransport, AsyncClient

from tradinghub.main import create_app


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


async def test_an_unknown_path_uses_the_usual_error_shape() -> None:
    async with _client() as client:
        response = await client.get("/no-such-path")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found."}}


async def test_a_wrong_method_uses_the_usual_error_shape_and_keeps_its_headers() -> None:
    async with _client() as client:
        response = await client.delete("/auth/login")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
    assert response.headers["allow"] == "POST"


async def test_an_unreadable_body_uses_the_usual_error_shape() -> None:
    async with _client() as client:
        response = await client.post(
            "/auth/login", content=b"\xff", headers={"content-type": "application/json"}
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
