import json
import logging
import sys

import pytest
from httpx import AsyncClient

from tradinghub.core.config import Environment, LogFormat, Settings
from tradinghub.core.logging import (
    THIRD_PARTY_LEVELS,
    UNSET,
    ContextFilter,
    JsonFormatter,
    build_logging_config,
    request_id,
    resolve_log_format,
    user_id,
)
from tradinghub.core.middleware import REQUEST_ID_HEADER

ACCESS_LOGGER = "tradinghub.access"


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "frontend_origin": "http://localhost:3000",
    }
    return Settings.model_validate({**defaults, **overrides})


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="tradinghub.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_console_is_the_default_locally() -> None:
    assert resolve_log_format(_settings()) is LogFormat.CONSOLE


def test_json_is_the_default_in_production() -> None:
    assert resolve_log_format(_settings(environment=Environment.PRODUCTION)) is LogFormat.JSON


def test_an_explicit_format_overrides_the_environment() -> None:
    settings = _settings(environment=Environment.PRODUCTION, log_format=LogFormat.CONSOLE)

    assert resolve_log_format(settings) is LogFormat.CONSOLE


def test_json_formatter_emits_one_parseable_object() -> None:
    payload = json.loads(JsonFormatter().format(_record(request_id="abc123", user_id="user-7")))

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "tradinghub.test"
    assert payload["request_id"] == "abc123"
    assert payload["user_id"] == "user-7"


def test_json_formatter_falls_back_when_context_is_absent() -> None:
    payload = json.loads(JsonFormatter().format(_record()))

    assert payload["request_id"] == UNSET
    assert payload["user_id"] == UNSET


def test_json_formatter_includes_extra_context() -> None:
    record = _record(request_id="abc123", status_code=404, duration_ms=1.5)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["status_code"] == 404
    assert payload["duration_ms"] == 1.5


def test_json_formatter_records_exceptions_inline() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record()
        record.exc_info = sys.exc_info()

    rendered = JsonFormatter().format(record)

    assert "\n" not in rendered
    assert "ValueError: boom" in json.loads(rendered)["exception"]


def test_filter_stamps_the_current_context() -> None:
    request_token = request_id.set("req-42")
    user_token = user_id.set("user-7")
    record = _record()
    try:
        assert ContextFilter().filter(record) is True
    finally:
        request_id.reset(request_token)
        user_id.reset(user_token)

    assert record.__dict__["request_id"] == "req-42"
    assert record.__dict__["user_id"] == "user-7"


def test_filter_stamps_placeholders_outside_a_request() -> None:
    record = _record()

    ContextFilter().filter(record)

    assert record.__dict__["request_id"] == UNSET
    assert record.__dict__["user_id"] == UNSET


def test_noisy_libraries_are_pinned_above_info() -> None:
    assert THIRD_PARTY_LEVELS["sqlalchemy.engine"] == "WARNING"
    assert THIRD_PARTY_LEVELS["watchfiles"] == "WARNING"
    assert THIRD_PARTY_LEVELS["httpx"] == "WARNING"


def test_uvicorn_loggers_lose_their_own_handlers() -> None:
    loggers = build_logging_config(_settings())["loggers"]

    assert loggers["uvicorn"] == {"handlers": [], "propagate": True}
    assert loggers["uvicorn.error"]["handlers"] == []
    assert loggers["uvicorn.error"]["propagate"] is True
    assert loggers["uvicorn.access"]["propagate"] is False


def test_existing_loggers_are_not_disabled() -> None:
    assert build_logging_config(_settings())["disable_existing_loggers"] is False


async def test_response_carries_a_request_id(client: AsyncClient) -> None:
    assert (await client.get("/health")).headers[REQUEST_ID_HEADER]


async def test_an_inbound_request_id_is_preserved(client: AsyncClient) -> None:
    response = await client.get("/health", headers={REQUEST_ID_HEADER: "caller-supplied"})

    assert response.headers[REQUEST_ID_HEADER] == "caller-supplied"


async def test_health_is_not_logged_at_info(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=ACCESS_LOGGER):
        await client.get("/health")

    assert caplog.records == []


async def test_other_paths_are_logged_with_context(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=ACCESS_LOGGER):
        await client.get("/does-not-exist")

    record = caplog.records[0]
    assert record.__dict__["status_code"] == 404
    assert record.__dict__["path"] == "/does-not-exist"
    assert record.__dict__["duration_ms"] >= 0


async def test_query_strings_are_never_logged(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=ACCESS_LOGGER):
        await client.get("/does-not-exist?token=super-secret")

    assert "super-secret" not in caplog.text
