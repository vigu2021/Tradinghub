"""Application settings, loaded once from the environment."""

from enum import StrEnum
from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Where the application is running."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Settings for the whole application.

    Raises ValidationError at construction when a required variable is absent, so a
    misconfigured deployment fails at startup rather than on the first request that needs it.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    frontend_origin: str
    cookie_domain: str | None = None
    cookie_secure: bool = False
    environment: Environment = Environment.DEVELOPMENT


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, parsing the environment only on the first call."""
    return Settings()  # pyright: ignore[reportCallIssue]
