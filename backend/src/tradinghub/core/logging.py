"""Logging setup: readable lines locally, one JSON object per line in production.

Every record carries the current request id, so a single request can be followed across every
line it produced even when requests interleave.
"""

import json
import logging
import logging.config
from contextvars import ContextVar
from typing import Any

from tradinghub.core.config import Environment, LogFormat, Settings

UNSET = "-"

request_id: ContextVar[str] = ContextVar("request_id", default=UNSET)
user_id: ContextVar[str] = ContextVar("user_id", default=UNSET)  # set once a session resolves

CONTEXT_FIELDS = ("request_id", "user_id")

THIRD_PARTY_LEVELS: dict[str, str] = {
    "sqlalchemy.engine": "WARNING",  # at INFO: every statement and every result row
    "sqlalchemy.pool": "WARNING",
    "sqlalchemy.dialects": "WARNING",
    "asyncpg": "WARNING",
    "asyncio": "WARNING",
    "watchfiles": "WARNING",  # at INFO: a line per filesystem scan under --reload
    "httpx": "WARNING",
    "httpcore": "WARNING",
    "python_multipart": "WARNING",
    "botocore": "WARNING",
    "boto3": "WARNING",
    "urllib3": "WARNING",
    "alembic": "INFO",
}

# Anything on a record that is not one of these came from extra=, and is context worth emitting.
_STANDARD_FIELDS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "asctime",
    "message",
    "taskName",
    "color_message",
    *CONTEXT_FIELDS,
}


class ContextFilter(logging.Filter):
    """Stamp the current request context onto every record, including third-party ones.

    Lives on the handler rather than a logger: only there does it reach records from SQLAlchemy
    and uvicorn, which never pass through our own loggers' filters.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        record.user_id = user_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render one JSON object per line, which is what log aggregators can actually query."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **{field: getattr(record, field, UNSET) for field in CONTEXT_FIELDS},
        }
        payload.update(
            {key: value for key, value in record.__dict__.items() if key not in _STANDARD_FIELDS}
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)  # default=str: a stray object must not crash a log


def resolve_log_format(settings: Settings) -> LogFormat:
    """Return the configured format, or the sensible default for the environment."""
    if settings.log_format is not None:
        return settings.log_format
    if settings.environment is Environment.PRODUCTION:
        return LogFormat.JSON
    return LogFormat.CONSOLE


def build_logging_config(settings: Settings) -> dict[str, Any]:
    """Build the dictConfig. Separate from applying it so tests can inspect it."""
    return {
        "version": 1,
        "disable_existing_loggers": False,  # True switches off uvicorn's and Alembic's loggers
        "filters": {"context": {"()": ContextFilter}},
        "formatters": {
            LogFormat.CONSOLE.value: {
                "format": (
                    "%(asctime)s %(levelname)-7s %(name)-24s "
                    "[%(request_id)s %(user_id)s] %(message)s"
                ),
                "datefmt": "%H:%M:%S",
            },
            LogFormat.JSON.value: {"()": JsonFormatter},
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": resolve_log_format(settings).value,
                "filters": ["context"],
            }
        },
        "root": {"handlers": ["stdout"], "level": settings.log_level.value},
        "loggers": {
            **{name: {"level": level} for name, level in THIRD_PARTY_LEVELS.items()},
            # Uvicorn attaches its own handlers with its own format. A level alone is not enough:
            # without clearing them, production emits its plain text interleaved with our JSON.
            "uvicorn": {"handlers": [], "propagate": True},
            "uvicorn.error": {"level": "INFO", "handlers": [], "propagate": True},
            "uvicorn.access": {"handlers": [], "propagate": False},  # RequestContextMiddleware
        },
    }


def configure_logging(settings: Settings) -> None:
    """Apply the logging configuration for this process."""
    logging.config.dictConfig(build_logging_config(settings))
