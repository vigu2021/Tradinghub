from typing import Any

import pytest
from httpx import AsyncClient

from tradinghub.auth.dependencies import ACCESS_COOKIE
from tradinghub.auth.models import User
from tradinghub.auth.security.tokens import encode_access_token

CHASE = {"name": "Chase", "unit": "gbp", "type": "cash"}


def _sign_in(client: AsyncClient, user: User) -> None:
    """Act as this user. Minted directly: logging in is tested in auth, and costs an Argon2 hash."""
    client.cookies.set(ACCESS_COOKIE, encode_access_token(user.id))


async def _open(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    response = await client.post("/accounts", json=CHASE | overrides)
    assert response.status_code == 201, response.text
    return response.json()


async def test_opening_an_account_returns_it_with_a_zero_balance(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)

    opened = await _open(client, name="  Chase  ")

    assert opened == {
        "id": opened["id"],
        "name": "Chase",
        "unit": "GBP",
        "type": "cash",
        "balance": "0",
        "archived_at": None,
    }


async def test_a_name_already_used_is_a_conflict(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    await _open(client)

    response = await client.post("/accounts", json=CHASE | {"name": "chase"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "account_name_taken"


async def test_an_account_reads_back_the_same_as_when_opened(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    opened = await _open(client)

    response = await client.get(f"/accounts/{opened['id']}")

    assert response.status_code == 200
    assert response.json() == opened


async def test_the_list_holds_only_your_accounts_in_name_order(
    client: AsyncClient, alice: User, bob: User
) -> None:
    _sign_in(client, bob)
    await _open(client, name="Revolut")
    _sign_in(client, alice)
    await _open(client, name="Monzo")
    await _open(client, name="Chase")

    response = await client.get("/accounts")

    assert [account["name"] for account in response.json()] == ["Chase", "Monzo"]


@pytest.mark.parametrize("method", ["GET", "PATCH"])
async def test_someone_elses_account_is_not_found(
    client: AsyncClient, alice: User, bob: User, method: str
) -> None:
    """404 rather than 403: a different answer would confirm the id belongs to someone."""
    _sign_in(client, bob)
    bobs_account = await _open(client)
    _sign_in(client, alice)

    response = await client.request(method, f"/accounts/{bobs_account['id']}", json={})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"


async def test_a_missing_account_is_not_found(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)

    response = await client.get("/accounts/999999")

    assert response.status_code == 404


async def test_a_patch_changes_only_the_fields_sent(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    opened = await _open(client)

    response = await client.patch(f"/accounts/{opened['id']}", json={"name": "Chase Saver"})

    assert response.json() == opened | {"name": "Chase Saver"}


async def test_a_null_field_is_left_alone(client: AsyncClient, alice: User) -> None:
    """None of these can be cleared, so null means not sent rather than a 409 from NOT NULL."""
    _sign_in(client, alice)
    opened = await _open(client)

    response = await client.patch(f"/accounts/{opened['id']}", json={"name": None})

    assert response.status_code == 200
    assert response.json() == opened


async def test_renaming_onto_another_accounts_name_is_a_conflict(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    await _open(client)
    monzo = await _open(client, name="Monzo")

    response = await client.patch(f"/accounts/{monzo['id']}", json={"name": "CHASE"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "account_name_taken"


async def test_archiving_twice_keeps_the_first_date(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    opened = await _open(client)
    url = f"/accounts/{opened['id']}"

    first = await client.patch(url, json={"archived": True})
    second = await client.patch(url, json={"archived": True})

    assert first.json()["archived_at"] is not None
    assert second.json()["archived_at"] == first.json()["archived_at"]


async def test_restoring_an_account_clears_its_archive_date(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    opened = await _open(client)
    url = f"/accounts/{opened['id']}"
    await client.patch(url, json={"archived": True})

    response = await client.patch(url, json={"archived": False})

    assert response.json()["archived_at"] is None


async def test_a_body_naming_a_user_is_rejected(client: AsyncClient, alice: User) -> None:
    """The owner comes from the cookie alone, so a user_id in the body is refused, not ignored."""
    _sign_in(client, alice)

    response = await client.post("/accounts", json=CHASE | {"user_id": 1})

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", "/accounts"), ("GET", "/accounts"), ("GET", "/accounts/1"), ("PATCH", "/accounts/1")],
)
async def test_every_account_endpoint_needs_a_session(
    client: AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path, json=CHASE)

    assert response.status_code == 401
