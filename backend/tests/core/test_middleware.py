from httpx import ASGITransport, AsyncClient

from tradinghub.core.middleware import REQUEST_ID_HEADER
from tradinghub.main import create_app

FRONTEND_ORIGIN = "http://localhost:3210"


async def _crash() -> None:
    raise ZeroDivisionError("a bug nobody anticipated")


async def _get_crashing_route(headers: dict[str, str]) -> tuple[int, dict[str, str], dict]:
    app = create_app()
    app.add_api_route("/crash", _crash)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/crash", headers=headers)
    return response.status_code, dict(response.headers), response.json()


async def test_an_unexpected_error_is_a_500_in_the_usual_shape() -> None:
    status_code, _, body = await _get_crashing_route({})

    assert status_code == 500
    assert body["error"]["code"] == "internal_error"
    assert "ZeroDivisionError" not in body["error"]["message"]


async def test_the_reference_in_a_500_is_the_request_id() -> None:
    _, headers, body = await _get_crashing_route({REQUEST_ID_HEADER: "req-from-the-browser"})

    assert headers[REQUEST_ID_HEADER.lower()] == "req-from-the-browser"
    assert "req-from-the-browser" in body["error"]["message"]


async def test_the_browser_can_read_a_500() -> None:
    """Without CORS headers the frontend sees a network failure and never the reference."""
    _, headers, _ = await _get_crashing_route({"Origin": FRONTEND_ORIGIN})

    assert headers["access-control-allow-origin"] == FRONTEND_ORIGIN
