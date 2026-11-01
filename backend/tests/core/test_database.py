from collections.abc import MutableMapping
from types import TracebackType
from typing import Any, Self

import pytest

from tradinghub.core import database
from tradinghub.main import create_app


class _RecordingSession:
    """Stands in for a session, so the real get_db runs with no database underneath."""

    def __init__(self, events: list[str], *, commit_fails: bool = False) -> None:
        self._events = events
        self._commit_fails = commit_fails

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self._events.append("commit")
        if self._commit_fails:
            raise ConnectionError("the database went away")

    async def rollback(self) -> None:
        self._events.append("rollback")


async def _log_out(events: list[str]) -> None:
    """Call the app directly, since an HTTP test client hides when the response is sent."""

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        if message["type"] == "http.response.start":
            events.append(f"response {message['status']}")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/auth/logout",
        "raw_path": b"/auth/logout",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("test", 80),
    }
    await create_app()(scope, receive, send)


async def test_the_commit_happens_before_the_response_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(database, "SessionFactory", lambda: _RecordingSession(events))

    await _log_out(events)

    assert events == ["commit", "response 204"]


async def test_a_failed_commit_is_reported_as_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        database, "SessionFactory", lambda: _RecordingSession(events, commit_fails=True)
    )

    await _log_out(events)

    assert events == ["commit", "rollback", "response 500"]
