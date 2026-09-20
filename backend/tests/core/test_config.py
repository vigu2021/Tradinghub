from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradinghub.core.config import JWT_SECRET_MIN_LENGTH, Environment, get_settings
from tradinghub.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """get_settings is cached, so a test that changes the environment must start clean.

    And end clean: a test here that builds valid settings from a fake environment would otherwise
    leave them cached for every test that runs after this module.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_app_fails_when_a_required_setting_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)  # away from the real .env
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)

    with pytest.raises(ValidationError):
        _ = create_app()


def test_unknown_environment_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")
    monkeypatch.setenv("ENVIRONMENT", "prod")  # a typo that must not silently pass

    with pytest.raises(ValidationError):
        _ = get_settings()


def _complete_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6380")
    monkeypatch.setenv("JWT_SECRET", "x" * JWT_SECRET_MIN_LENGTH)


def test_a_complete_environment_is_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _complete_environment(monkeypatch, tmp_path)

    assert get_settings().environment is Environment.DEVELOPMENT


def test_an_empty_jwt_secret_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """.env.example ships it empty, so forgetting to fill it in must fail at startup."""
    _complete_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("JWT_SECRET", "")

    with pytest.raises(ValidationError):
        _ = get_settings()


def test_a_short_jwt_secret_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _complete_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("JWT_SECRET", "x" * (JWT_SECRET_MIN_LENGTH - 1))

    with pytest.raises(ValidationError):
        _ = get_settings()


def test_production_refuses_insecure_cookies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _complete_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(ValidationError):
        _ = get_settings()


def test_production_accepts_secure_cookies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _complete_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COOKIE_SECURE", "true")

    assert get_settings().cookie_secure is True
