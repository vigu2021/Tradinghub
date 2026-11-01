from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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


RENT = {
    "amount": "900",
    "kind": "expense",
    "category": "Rent",
    "occurred_at": "2026-10-01T09:00:00Z",
    "note": "October",
}


async def _record(client: AsyncClient, account_id: int, **overrides: str) -> dict[str, Any]:
    response = await client.post(
        "/transactions", json=RENT | {"account_id": account_id} | overrides
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_an_expense_is_stored_negative_and_reaches_the_balance(
    client: AsyncClient, alice: User
) -> None:
    """The caller sends a positive amount and a kind. Nobody types a minus sign for rent."""
    _sign_in(client, alice)
    account = await _open(client)

    recorded = await _record(client, account["id"])
    balance = (await client.get(f"/accounts/{account['id']}")).json()["balance"]

    assert recorded == {
        "id": recorded["id"],
        "account_id": account["id"],
        "amount": "-900",
        "kind": "expense",
        "category": "rent",
        "occurred_at": "2026-10-01T09:00:00Z",
        "note": "October",
        "transfer_group_id": None,
    }
    assert balance == "-900"


async def test_income_is_stored_positive(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    account = await _open(client)

    recorded = await _record(client, account["id"], amount="2000", kind="income")

    assert recorded["amount"] == "2000"


async def test_a_transaction_reads_back_the_same_as_when_recorded(
    client: AsyncClient, db_session: AsyncSession, alice: User
) -> None:
    """The stored NUMERIC comes back with 18 decimals, and the response must not show them.

    expunge_all makes the read go to the database: the test shares one session, which would
    otherwise hand back the object the POST left in memory.
    """
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"])
    db_session.expunge_all()

    response = await client.get(f"/transactions/{recorded['id']}")

    assert response.json() == recorded


async def test_recording_into_someone_elses_account_is_not_found(
    client: AsyncClient, alice: User, bob: User
) -> None:
    _sign_in(client, bob)
    bobs_account = await _open(client)
    _sign_in(client, alice)

    response = await client.post("/transactions", json=RENT | {"account_id": bobs_account["id"]})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"


async def test_a_transfer_cannot_be_recorded_here(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    account = await _open(client)

    response = await client.post(
        "/transactions", json=RENT | {"account_id": account["id"], "kind": "transfer"}
    )

    assert response.status_code == 422


async def test_every_digit_of_a_large_amount_survives(
    client: AsyncClient, db_session: AsyncSession, alice: User
) -> None:
    """36 significant digits, which Decimal arithmetic would round to 28 without a word."""
    _sign_in(client, alice)
    account = await _open(client, unit="SHIB")
    huge = "123456789012345678.123456789012345678"

    recorded = await _record(client, account["id"], amount=huge)
    db_session.expunge_all()
    read = (await client.get(f"/transactions/{recorded['id']}")).json()["amount"]
    balance = (await client.get(f"/accounts/{account['id']}")).json()["balance"]

    assert recorded["amount"] == read == balance == f"-{huge}"


async def test_an_amount_sent_as_a_json_number_is_rejected_and_not_recorded(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    account = await _open(client)

    response = await client.post(
        "/transactions",
        json=RENT | {"account_id": account["id"], "amount": 0.123456789012345678},
    )

    assert response.status_code == 422
    assert await _balance(client, account["id"]) == "0"


async def test_a_new_amount_and_kind_together_take_the_new_sign(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"])

    response = await client.patch(
        f"/transactions/{recorded['id']}", json={"amount": "2000", "kind": "income"}
    )

    assert response.json()["amount"] == "2000"


async def test_a_new_amount_keeps_income_positive(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"], amount="2000", kind="income")

    response = await client.patch(f"/transactions/{recorded['id']}", json={"amount": "2100"})

    assert response.json()["amount"] == "2100"


async def test_the_list_is_one_page_of_your_own_with_a_total(
    client: AsyncClient, alice: User, bob: User
) -> None:
    _sign_in(client, bob)
    await _record(client, (await _open(client))["id"])
    _sign_in(client, alice)
    account = await _open(client)
    for _ in range(3):
        await _record(client, account["id"])

    response = await client.get("/transactions", params={"limit": 2})

    page = response.json()
    assert (len(page["items"]), page["total"]) == (2, 3)
    assert {item["account_id"] for item in page["items"]} == {account["id"]}


async def test_the_list_filters_from_the_query_string(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    account = await _open(client)
    salary = await _record(client, account["id"], amount="2000", kind="income")
    await _record(client, account["id"])

    response = await client.get("/transactions", params={"kind": "income"})

    assert [item["id"] for item in response.json()["items"]] == [salary["id"]]


@pytest.mark.parametrize("query", [{"limit": "500"}, {"acount_id": "1"}])
async def test_a_bad_list_query_is_rejected(
    client: AsyncClient, alice: User, query: dict[str, str]
) -> None:
    """A misspelled filter ignored would return everything while the caller thinks they filtered."""
    _sign_in(client, alice)

    response = await client.get("/transactions", params=query)

    assert response.status_code == 422


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_someone_elses_transaction_is_not_found(
    client: AsyncClient, alice: User, bob: User, method: str
) -> None:
    _sign_in(client, bob)
    bobs = await _record(client, (await _open(client))["id"])
    _sign_in(client, alice)

    response = await client.request(method, f"/transactions/{bobs['id']}", json={})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "transaction_not_found"


async def test_a_new_amount_keeps_the_expense_negative(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"])

    response = await client.patch(f"/transactions/{recorded['id']}", json={"amount": "950"})

    assert response.json()["amount"] == "-950"


async def test_turning_an_expense_into_income_flips_the_sign(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"])

    response = await client.patch(f"/transactions/{recorded['id']}", json={"kind": "income"})

    assert response.json()["amount"] == "900"


async def test_a_null_note_clears_it_and_leaves_the_rest(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"])

    response = await client.patch(f"/transactions/{recorded['id']}", json={"note": None})

    assert response.json() == recorded | {"note": None}


async def test_a_null_amount_is_rejected(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"])

    response = await client.patch(f"/transactions/{recorded['id']}", json={"amount": None})

    assert response.status_code == 422


async def test_a_transaction_cannot_move_to_another_account(
    client: AsyncClient, alice: User
) -> None:
    """The account is fixed once recorded. One in the wrong place is deleted and recorded again."""
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")
    recorded = await _record(client, chase["id"])

    response = await client.patch(
        f"/transactions/{recorded['id']}", json={"account_id": monzo["id"]}
    )

    assert response.status_code == 422


async def test_a_deleted_transaction_is_gone(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    recorded = await _record(client, (await _open(client))["id"])

    deleted = await client.delete(f"/transactions/{recorded['id']}")
    read = await client.get(f"/transactions/{recorded['id']}")

    assert deleted.status_code == 204
    assert read.status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/transactions"),
        ("GET", "/transactions"),
        ("GET", "/transactions/1"),
        ("PATCH", "/transactions/1"),
        ("DELETE", "/transactions/1"),
    ],
)
async def test_every_transaction_endpoint_needs_a_session(
    client: AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path, json={})

    assert response.status_code == 401


TUITION = {
    "amount_sent": "1000",
    "amount_received": "1000",
    "occurred_at": "2026-10-02T09:00:00Z",
    "note": "Tuition",
}


async def _transfer(
    client: AsyncClient, from_account_id: int, to_account_id: int, **overrides: str | int
) -> list[dict[str, Any]]:
    response = await client.post(
        "/transfers",
        json=TUITION
        | {"from_account_id": from_account_id, "to_account_id": to_account_id}
        | overrides,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _balance(client: AsyncClient, account_id: int) -> str:
    return (await client.get(f"/accounts/{account_id}")).json()["balance"]


async def test_a_transfer_writes_two_rows_in_one_group_and_moves_both_balances(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")

    source, destination = await _transfer(client, chase["id"], monzo["id"])

    assert source["amount"] == "-1000"
    assert source["kind"] == "transfer"
    assert destination["amount"] == "1000"
    assert destination["kind"] == "transfer"
    assert source["transfer_group_id"] is not None
    assert source["transfer_group_id"] == destination["transfer_group_id"]
    assert await _balance(client, chase["id"]) == "-1000"
    assert await _balance(client, monzo["id"]) == "1000"


async def test_a_fee_is_a_third_row_counted_as_an_expense(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")

    source, _, fee = await _transfer(
        client,
        chase["id"],
        monzo["id"],
        fee="5",
        fee_account_id=chase["id"],
        fee_category="Fees",
    )

    assert fee["account_id"] == chase["id"]
    assert fee["amount"] == "-5"
    assert fee["kind"] == "expense"
    assert fee["category"] == "fees"
    assert fee["transfer_group_id"] == source["transfer_group_id"]
    assert await _balance(client, chase["id"]) == "-1005"
    assert await _balance(client, monzo["id"]) == "1000"


async def test_a_fee_can_be_charged_to_the_destination(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")

    await _transfer(client, chase["id"], monzo["id"], fee="5", fee_account_id=monzo["id"])

    assert await _balance(client, monzo["id"]) == "995"


async def test_different_units_can_move_different_amounts(client: AsyncClient, alice: User) -> None:
    """How a purchase is recorded: nothing is converted, and the gap between them is the price."""
    _sign_in(client, alice)
    usdt = await _open(client, name="USDT", unit="USDT")
    btc = await _open(client, name="BTC", unit="BTC")

    source, destination = await _transfer(
        client, usdt["id"], btc["id"], amount_sent="30000", amount_received="0.5"
    )

    assert source["amount"] == "-30000"
    assert destination["amount"] == "0.5"


async def test_every_digit_of_a_large_transfer_survives(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")
    amount = "123456789012345678.123456789012345678"

    source, destination = await _transfer(
        client, chase["id"], monzo["id"], amount_sent=amount, amount_received=amount
    )

    assert source["amount"] == f"-{amount}"
    assert destination["amount"] == amount


async def test_one_unit_with_differing_amounts_is_rejected(
    client: AsyncClient, alice: User
) -> None:
    """The gap would be a fee in disguise, hidden from every spending total."""
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")

    response = await client.post(
        "/transfers",
        json=TUITION
        | {
            "from_account_id": chase["id"],
            "to_account_id": monzo["id"],
            "amount_received": "995",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "transfer_amounts_differ"
    assert await _balance(client, chase["id"]) == "0"


async def test_the_same_account_twice_is_rejected(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    chase = await _open(client)

    response = await client.post(
        "/transfers",
        json=TUITION | {"from_account_id": chase["id"], "to_account_id": chase["id"]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "transfer_same_account"


async def test_a_fee_can_come_from_a_third_account(client: AsyncClient, alice: User) -> None:
    """A Binance trade can pay its fee in BNB, from an account the trade itself never touches."""
    _sign_in(client, alice)
    usdt = await _open(client, name="USDT", unit="USDT")
    btc = await _open(client, name="BTC", unit="BTC")
    bnb = await _open(client, name="BNB", unit="BNB")

    source, _, fee = await _transfer(
        client,
        usdt["id"],
        btc["id"],
        amount_sent="30000",
        amount_received="0.5",
        fee="0.01",
        fee_account_id=bnb["id"],
    )

    assert fee["account_id"] == bnb["id"]
    assert fee["kind"] == "expense"
    assert fee["transfer_group_id"] == source["transfer_group_id"]
    assert await _balance(client, usdt["id"]) == "-30000"
    assert await _balance(client, bnb["id"]) == "-0.01"


async def test_a_fee_on_someone_elses_account_is_not_found(
    client: AsyncClient, alice: User, bob: User
) -> None:
    _sign_in(client, bob)
    bobs_account = await _open(client)
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")

    response = await client.post(
        "/transfers",
        json=TUITION
        | {
            "from_account_id": chase["id"],
            "to_account_id": monzo["id"],
            "fee": "5",
            "fee_account_id": bobs_account["id"],
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"
    assert await _balance(client, chase["id"]) == "0"


async def test_half_a_fee_is_rejected(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")

    response = await client.post(
        "/transfers",
        json=TUITION | {"from_account_id": chase["id"], "to_account_id": monzo["id"], "fee": "5"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("bobs_side", ["from_account_id", "to_account_id"])
async def test_a_transfer_touching_someone_elses_account_is_not_found(
    client: AsyncClient, alice: User, bob: User, bobs_side: str
) -> None:
    _sign_in(client, bob)
    bobs_account = await _open(client)
    _sign_in(client, alice)
    alices_account = await _open(client)
    sides = {"from_account_id": alices_account["id"], "to_account_id": alices_account["id"]}

    response = await client.post(
        "/transfers", json=TUITION | sides | {bobs_side: bobs_account["id"]}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"
    assert await _balance(client, alices_account["id"]) == "0"


@pytest.mark.parametrize("row", [0, 1, 2])
async def test_no_row_of_a_transfer_can_be_edited(
    client: AsyncClient, alice: User, row: int
) -> None:
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")
    rows = await _transfer(client, chase["id"], monzo["id"], fee="5", fee_account_id=chase["id"])

    response = await client.patch(f"/transactions/{rows[row]['id']}", json={"note": "Changed"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "transfer_not_editable"


@pytest.mark.parametrize("row", [0, 1, 2])
async def test_deleting_any_row_deletes_the_whole_transfer_and_nothing_else(
    client: AsyncClient, alice: User, row: int
) -> None:
    _sign_in(client, alice)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")
    rent = await _record(client, chase["id"])
    rows = await _transfer(client, chase["id"], monzo["id"], fee="5", fee_account_id=chase["id"])
    other_transfer = await _transfer(
        client, chase["id"], monzo["id"], amount_sent="1", amount_received="1"
    )

    response = await client.delete(f"/transactions/{rows[row]['id']}")

    assert response.status_code == 204
    assert await _balance(client, chase["id"]) == "-901"
    assert await _balance(client, monzo["id"]) == "1"
    assert (await client.get(f"/transactions/{rent['id']}")).status_code == 200
    assert (await client.get(f"/transactions/{other_transfer[0]['id']}")).status_code == 200


async def test_deleting_a_plain_transaction_leaves_the_others(
    client: AsyncClient, alice: User
) -> None:
    """Plain rows all have a null group, which must not count as sharing one."""
    _sign_in(client, alice)
    chase = await _open(client)
    rent = await _record(client, chase["id"])
    await _record(client, chase["id"], amount="50")

    await client.delete(f"/transactions/{rent['id']}")

    assert await _balance(client, chase["id"]) == "-50"


async def test_deleting_someone_elses_transfer_row_is_not_found(
    client: AsyncClient, alice: User, bob: User
) -> None:
    _sign_in(client, bob)
    chase = await _open(client)
    monzo = await _open(client, name="Monzo")
    rows = await _transfer(client, chase["id"], monzo["id"])
    bobs_cookie = client.cookies[ACCESS_COOKIE]
    _sign_in(client, alice)

    response = await client.delete(f"/transactions/{rows[0]['id']}")

    assert response.status_code == 404
    client.cookies.set(ACCESS_COOKIE, bobs_cookie)
    assert await _balance(client, monzo["id"]) == "1000"


async def test_a_transfer_needs_a_session(client: AsyncClient) -> None:
    response = await client.post("/transfers", json={})

    assert response.status_code == 401


TOO_BIG_ID = 2**31


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", f"/accounts/{TOO_BIG_ID}"),
        ("PATCH", f"/accounts/{TOO_BIG_ID}"),
        ("GET", f"/transactions/{TOO_BIG_ID}"),
        ("PATCH", f"/transactions/{TOO_BIG_ID}"),
        ("DELETE", f"/transactions/{TOO_BIG_ID}"),
        ("GET", f"/transactions?account_id={TOO_BIG_ID}"),
        ("GET", f"/transactions?offset={2**63}"),
    ],
)
async def test_a_number_the_database_cannot_hold_is_rejected_in_a_url(
    client: AsyncClient, alice: User, method: str, path: str
) -> None:
    _sign_in(client, alice)

    response = await client.request(method, path, json={})

    assert response.status_code == 422


async def test_an_id_the_database_cannot_hold_is_rejected_in_a_body(
    client: AsyncClient, alice: User
) -> None:
    _sign_in(client, alice)
    account = await _open(client)

    transaction = await client.post("/transactions", json=RENT | {"account_id": TOO_BIG_ID})
    transfer = await client.post(
        "/transfers",
        json=TUITION | {"from_account_id": account["id"], "to_account_id": TOO_BIG_ID},
    )

    assert transaction.status_code == 422
    assert transfer.status_code == 422


@pytest.mark.parametrize("field", ["note", "category"])
async def test_a_nul_character_in_transaction_text_is_rejected(
    client: AsyncClient, alice: User, field: str
) -> None:
    _sign_in(client, alice)
    account = await _open(client)

    response = await client.post(
        "/transactions", json=RENT | {"account_id": account["id"], field: "a\u0000b"}
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["name", "unit"])
async def test_a_nul_character_in_account_text_is_rejected(
    client: AsyncClient, alice: User, field: str
) -> None:
    _sign_in(client, alice)

    response = await client.post("/accounts", json=CHASE | {field: "a\u0000b"})

    assert response.status_code == 422


async def test_a_nul_character_in_a_filter_is_rejected(client: AsyncClient, alice: User) -> None:
    _sign_in(client, alice)

    response = await client.get("/transactions", params={"category": "a\u0000b"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "occurred_at",
    [
        1700000000,
        "1700000000",
        1e11,
        "0001-01-01T00:00:00+14:00",
        "9999-12-31T23:59:59-14:00",
        "1899-12-31T23:59:59Z",
        "2100-01-01T00:00:00Z",
    ],
)
async def test_a_time_that_is_not_a_sensible_iso_8601_value_is_rejected(
    client: AsyncClient, alice: User, occurred_at: float | str
) -> None:
    _sign_in(client, alice)
    account = await _open(client)

    response = await client.post(
        "/transactions",
        json=RENT | {"account_id": account["id"], "occurred_at": occurred_at},
    )

    assert response.status_code == 422


async def test_a_time_reads_the_same_when_recorded_and_when_read_back(
    client: AsyncClient, db_session: AsyncSession, alice: User
) -> None:
    """Sent with an offset, it comes back in UTC both times, not as whatever the caller sent."""
    _sign_in(client, alice)
    account = await _open(client)

    recorded = await _record(client, account["id"], occurred_at="2026-10-01T10:00:00+01:00")
    db_session.expunge_all()
    read = await client.get(f"/transactions/{recorded['id']}")

    assert recorded["occurred_at"] == "2026-10-01T09:00:00Z"
    assert read.json()["occurred_at"] == "2026-10-01T09:00:00Z"
