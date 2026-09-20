"""Argon2id password hashing. Neither function logs its input."""

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_HASHER = PasswordHasher()  # constructed once; the defaults follow current OWASP guidance


async def hash_password(raw_password: str) -> str:
    """Return an Argon2id hash, salted per call, so two hashes of one password differ.

    Runs in a worker thread: Argon2 is deliberately slow, and inline it would stall every other
    request on the event loop for as long as it takes.
    """
    return await asyncio.to_thread(PASSWORD_HASHER.hash, raw_password)


async def verify_password(*, raw_password: str, password_hash: str) -> bool:
    """Return whether the password matches. A wrong password and a corrupt hash both give False.

    Runs in a worker thread, for the same reason as hash_password.
    """
    return await asyncio.to_thread(_verify, raw_password, password_hash)


def _verify(raw_password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, raw_password)
    except (VerificationError, InvalidHashError):
        return False
