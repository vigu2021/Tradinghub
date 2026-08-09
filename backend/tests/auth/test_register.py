from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models import User

PASSWORD = "correct horse battery"


def _payload(email: str, password: str = PASSWORD) -> dict[str, str]:
    return {"email": email, "password": password}


async def test_register_creates_user(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json=_payload("a@example.com"))

    assert response.status_code == 201


async def test_register_persists_the_user(client: AsyncClient, db_session: AsyncSession) -> None:
    await client.post("/auth/register", json=_payload("persisted@example.com"))

    user = await db_session.scalar(select(User).where(User.email == "persisted@example.com"))

    assert user is not None


async def test_the_stored_hash_is_not_the_password(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/auth/register", json=_payload("hashed@example.com"))

    user = await db_session.scalar(select(User).where(User.email == "hashed@example.com"))

    assert user is not None
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2id$")


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json=_payload("b@example.com", "short"))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_register_rejects_a_malformed_email(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json=_payload("not-an-email"))

    assert response.status_code == 422


async def test_a_rejected_password_is_never_echoed_back(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json=_payload("c@example.com", "short"))

    assert "short" not in response.text


async def test_duplicate_email_is_indistinguishable_from_success(client: AsyncClient) -> None:
    payload = _payload("dupe@example.com")

    first = await client.post("/auth/register", json=payload)
    second = await client.post("/auth/register", json=payload)

    assert first.status_code == second.status_code == 201
    assert first.content == second.content


async def test_registering_twice_leaves_one_account(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    payload = _payload("once@example.com")
    await client.post("/auth/register", json=payload)
    await client.post("/auth/register", json=payload)

    users = (await db_session.scalars(select(User).where(User.email == "once@example.com"))).all()

    assert len(users) == 1


async def test_the_second_registration_does_not_change_the_password(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/auth/register", json=_payload("keeper@example.com"))
    original = await db_session.scalar(
        select(User.password_hash).where(User.email == "keeper@example.com")
    )

    await client.post("/auth/register", json=_payload("keeper@example.com", "a different password"))

    current = await db_session.scalar(
        select(User.password_hash).where(User.email == "keeper@example.com")
    )
    assert current == original


async def test_register_does_not_set_a_cookie(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json=_payload("d@example.com"))

    assert "set-cookie" not in response.headers
