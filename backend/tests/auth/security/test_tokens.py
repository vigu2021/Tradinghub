import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from tradinghub.auth.security.tokens import (
    ACCESS_TOKEN_LIFETIME,
    JWT_ALGORITHM,
    AccessTokenClaims,
    decode_access_token,
    encode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from tradinghub.core.config import get_settings

USER_ID = 42

# Long enough that PyJWT does not warn about HMAC key length; the value itself is irrelevant.
ANOTHER_SECRET = "a-different-secret-long-enough-for-sha256"


def _payload(access_token: str) -> dict[str, Any]:
    """Read the claims without verifying, the way anyone holding the token could."""
    encoded = access_token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))


def _token_expiring(delta: timedelta, secret: str | None = None) -> str:
    claims = {"sub": str(USER_ID), "exp": datetime.now(UTC) + delta}
    return jwt.encode(claims, secret or get_settings().jwt_secret, algorithm=JWT_ALGORITHM)


def test_refresh_tokens_are_unique() -> None:
    assert generate_refresh_token() != generate_refresh_token()


def test_a_refresh_token_carries_enough_entropy() -> None:
    assert len(generate_refresh_token()) >= 32


def test_hashing_a_refresh_token_is_repeatable() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) == hash_refresh_token(token)


def test_the_hash_is_not_the_token() -> None:
    token = generate_refresh_token()

    assert hash_refresh_token(token) != token


def test_different_refresh_tokens_hash_differently() -> None:
    assert hash_refresh_token(generate_refresh_token()) != hash_refresh_token(
        generate_refresh_token()
    )


def test_an_access_token_round_trips() -> None:
    claims = decode_access_token(encode_access_token(USER_ID))

    assert claims == AccessTokenClaims(user_id=USER_ID)


def test_the_user_id_comes_back_as_an_int() -> None:
    claims = decode_access_token(encode_access_token(USER_ID))

    assert claims is not None
    assert isinstance(claims.user_id, int)


def test_an_access_token_expires() -> None:
    payload = _payload(encode_access_token(USER_ID))

    assert payload["exp"] - payload["iat"] == ACCESS_TOKEN_LIFETIME.total_seconds()


def test_an_expired_token_is_rejected() -> None:
    assert decode_access_token(_token_expiring(timedelta(seconds=-1))) is None


def test_a_token_signed_with_another_secret_is_rejected() -> None:
    assert decode_access_token(_token_expiring(timedelta(minutes=5), ANOTHER_SECRET)) is None


def test_a_tampered_payload_is_rejected() -> None:
    header, _, signature = encode_access_token(USER_ID).split(".")
    forged_claims = json.dumps({"sub": "1", "exp": 9_999_999_999}).encode()
    forged_payload = base64.urlsafe_b64encode(forged_claims).rstrip(b"=").decode()

    assert decode_access_token(f"{header}.{forged_payload}.{signature}") is None


def test_garbage_is_rejected() -> None:
    assert decode_access_token("not.a.token") is None


def test_an_empty_token_is_rejected() -> None:
    assert decode_access_token("") is None


def test_the_access_token_never_contains_the_secret() -> None:
    assert get_settings().jwt_secret not in encode_access_token(USER_ID)
