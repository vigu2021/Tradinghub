import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from tradinghub.core.config import get_settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int


def generate_refresh_token() -> str:
    """Return a fresh refresh token: 32 random bytes, URL-safe."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_refresh_token: str) -> str:
    """Return the hash to store and look up by. Unsalted SHA-256: the input is already random."""
    return hashlib.sha256(raw_refresh_token.encode()).hexdigest()


def encode_access_token(user_id: int) -> str:
    """Return a signed access token for this user, valid for ACCESS_TOKEN_LIFETIME.

    The lifetime is also how long logout takes to bite: nothing can revoke an issued token.
    """
    issued_at = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + ACCESS_TOKEN_LIFETIME,
    }
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(access_token: str) -> AccessTokenClaims | None:
    """Verify the signature and expiry, returning the claims. None for any invalid token.

    The caller cannot tell expired from forged, and should not: both are a 401.
    """
    try:
        access_token_claims = jwt.decode(
            access_token, get_settings().jwt_secret, algorithms=[JWT_ALGORITHM]
        )
    except jwt.InvalidTokenError:
        return None
    return AccessTokenClaims(user_id=int(access_token_claims["sub"]))
