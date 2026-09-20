"""Application settings, loaded once from the environment."""

from enum import StrEnum
from functools import lru_cache
from typing import ClassVar, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# HS256 signs with a 256-bit key; anything shorter is weaker than the algorithm it feeds.
JWT_SECRET_MIN_LENGTH = 32


class Environment(StrEnum):
    """Where the application is running."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    """How log lines are rendered."""

    CONSOLE = "console"
    JSON = "json"


class LogLevel(StrEnum):
    """Standard library log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Settings for the whole application.

    Raises ValidationError at construction when a required variable is absent, when the JWT
    secret is too short to be one, or when production is configured to send cookies over plain
    HTTP. A misconfigured deployment fails at startup rather than on the first request that
    needs the value.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    frontend_origin: str
    cookie_domain: str | None = None
    cookie_secure: bool = False
    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat | None = None
    jwt_secret: str = Field(min_length=JWT_SECRET_MIN_LENGTH)
    redis_url: str

    @model_validator(mode="after")
    def _require_secure_cookies_in_production(self) -> Self:
        if self.environment is Environment.PRODUCTION and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true when ENVIRONMENT is production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, parsing the environment only on the first call."""
    return Settings()  # pyright: ignore[reportCallIssue]
