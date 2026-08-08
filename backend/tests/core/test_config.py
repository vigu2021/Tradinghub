from pathlib import Path

import pytest
from pydantic import ValidationError

from tradinghub.core.config import get_settings
from tradinghub.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """get_settings is cached, so a test that changes the environment must start clean."""
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
