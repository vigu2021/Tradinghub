import hashlib
import secrets


def generate_refresh_token() -> str:
    """Return a fresh refresh token: 32 random bytes, URL-safe."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_refresh_token: str) -> str:
    """Return the hash to store and look up by. Unsalted SHA-256: the input is already random."""
    return hashlib.sha256(raw_refresh_token.encode()).hexdigest()
