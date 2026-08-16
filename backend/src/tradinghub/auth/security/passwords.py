"""Argon2id password hashing. Neither function logs its input."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PW_HASHER = PasswordHasher()  # constructed once; the defaults follow current OWASP guidance


def hash_password(raw_password: str) -> str:
    """Return an Argon2id hash, salted per call, so two hashes of one password differ."""
    return PW_HASHER.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    """Return whether the password matches. A wrong password and a corrupt hash both give False."""
    try:
        return PW_HASHER.verify(password_hash, raw_password)
    except (VerificationError, InvalidHashError):
        return False
