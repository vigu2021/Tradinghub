import asyncio

from tradinghub.auth.security.passwords import hash_password, verify_password

PASSWORD = "correct horse battery"


async def test_hash_is_salted() -> None:
    assert await hash_password(PASSWORD) != await hash_password(PASSWORD)


async def test_verify_accepts_correct_password() -> None:
    password_hash = await hash_password(PASSWORD)

    assert await verify_password(raw_password=PASSWORD, password_hash=password_hash)


async def test_verify_rejects_wrong_password() -> None:
    password_hash = await hash_password(PASSWORD)

    assert not await verify_password(raw_password="wrong", password_hash=password_hash)


async def test_verify_rejects_malformed_hash() -> None:
    assert not await verify_password(raw_password="anything", password_hash="not-a-hash")


async def test_hash_never_contains_the_password() -> None:
    assert PASSWORD not in await hash_password(PASSWORD)


async def test_hashing_leaves_the_event_loop_free() -> None:
    """Argon2 inline would hold the loop for the whole hash, and the ticker would never run."""
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.001)
            ticks += 1

    ticking = asyncio.create_task(ticker())
    await hash_password(PASSWORD)
    ticking.cancel()

    assert ticks > 0
