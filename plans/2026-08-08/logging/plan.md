# Logging Implementation Plan

**Goal:** Readable logs locally, JSON in production, third-party noise suppressed, every line
carrying a request id.

**Spec:** `plans/2026-08-08/logging/spec.md` — read it first. This plan implements it and does not
restate the rationale.

**Slots into:** the auth-skeleton plan, replacing Task 8's logging half. Do it before Task 3, so
every task after it can log.

---

## Task L1: Settings and log configuration

**Files:**
- Modify: `backend/src/tradinghub/core/config.py`, `backend/.env.example`
- Create: `backend/src/tradinghub/core/logging.py`, `backend/tests/core/test_logging.py`

**Interfaces produced:**
```python
# core/config.py
class LogFormat(StrEnum):
    CONSOLE = "console"
    JSON = "json"

class LogLevel(StrEnum):
    DEBUG = "DEBUG"; INFO = "INFO"; WARNING = "WARNING"; ERROR = "ERROR"

# added to Settings
log_level: LogLevel = LogLevel.INFO
log_format: LogFormat | None = None      # None means "match the environment"

# core/logging.py
NO_REQUEST = "-"
request_id: ContextVar[str]                      # default NO_REQUEST
THIRD_PARTY_LEVELS: dict[str, str]               # the table from the spec

class RequestIdFilter(logging.Filter): ...
class JsonFormatter(logging.Formatter): ...

def resolve_log_format(settings: Settings) -> LogFormat: ...
def build_logging_config(settings: Settings) -> dict[str, Any]: ...
def configure_logging(settings: Settings) -> None: ...
```

**Requirements:**
1. `resolve_log_format` returns `settings.log_format` when set; otherwise JSON for
   `Environment.PRODUCTION` and CONSOLE for everything else.
2. `RequestIdFilter` sets `record.request_id` from the contextvar on every record.
3. `JsonFormatter` emits one JSON object per line with `timestamp`, `level`, `logger`, `message`,
   `request_id`.
4. Anything passed via `extra={...}` appears as a top-level field. Standard `LogRecord` attributes
   do not. Derive the standard set from a throwaway `LogRecord` rather than hardcoding a list.
5. Exceptions render into an `exception` field, never as extra lines.
6. `build_logging_config` returns the dict; `configure_logging` applies it. Separating them is what
   makes the config testable without mutating global logging state.
7. `disable_existing_loggers` is `False`.
8. Every logger in `THIRD_PARTY_LEVELS` gets its level set.
9. `uvicorn` and `uvicorn.error` have `handlers: []` and `propagate: True`. **Setting only the level
   is not enough** — uvicorn attaches its own handlers with its own formatter, and leaving them
   produces plain text interleaved with JSON in production.
10. `uvicorn.access` gets `handlers: []`, `propagate: False`; Task L2 replaces it.
11. The handler writes to stdout, never a file.

Hints: `logging.config.dictConfig`; `{"()": RequestIdFilter}` is dictConfig's syntax for "call this
callable"; `frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)` gives the standard
field names; `json.dumps(..., default=str)` so a stray datetime cannot crash a log call.

**Tests:** console is the default locally; JSON is the default in production; an explicit
`log_format` overrides the environment; the JSON formatter emits a parseable object with the
expected keys; `extra` fields appear; exceptions land in `exception`; the filter stamps the current
request id; `sqlalchemy.engine` and `watchfiles` are pinned to WARNING.

Build `Settings` in tests with `Settings.model_validate({...})` rather than `Settings(...)`, which
avoids a second type-checker suppression.

**Verify:** `uv run pytest tests/core/test_logging.py -v`
**Commit:** `Add structured logging configuration`

---

## Task L2: Request context and access logging

**Files:**
- Create: `backend/src/tradinghub/core/middleware.py`
- Modify: `backend/tests/core/test_logging.py`

**Interfaces produced:**
```python
REQUEST_ID_HEADER = "X-Request-ID"
QUIET_PATHS = frozenset({"/health"})

class RequestContextMiddleware(BaseHTTPMiddleware): ...
```

**Requirements:**
1. Sets the `request_id` contextvar from an inbound `X-Request-ID` header, or a fresh
   `uuid.uuid4().hex` when absent.
2. Resets the contextvar in a `finally`, so a failed request cannot leak its id into the next one.
3. Logs one line per request to the `tradinghub.access` logger with `method`, `path`,
   `status_code`, `duration_ms`, `client_ip` in `extra`.
4. **The query string is never logged** — `request.url.path`, never `request.url`.
5. Paths in `QUIET_PATHS` log at DEBUG; everything else at INFO.
6. An unhandled exception is logged with `logger.exception` and re-raised, never swallowed.
7. The response carries `X-Request-ID` so a caller can quote it in a bug report.
8. Duration measured with `time.perf_counter`, not `time.time` — the latter jumps when the clock
   is adjusted.

**Tests:** the response carries a request id; an inbound id is preserved; `/health` produces no
INFO record; another path logs with `status_code`, `path`, and a non-negative `duration_ms`; a
query string containing a secret does not appear in `caplog.text`.

Read dynamic record attributes as `record.__dict__["status_code"]` — attribute access fails the type
checker, and `getattr` with a constant fails the linter.

**Verify:** `uv run pytest tests/core -v`
**Commit:** `Add request context and access logging`

---

## Task L3: Wire it up and verify both formats

**Files:**
- Modify: `backend/src/tradinghub/main.py`, `CONVENTIONS.md`,
  `plans/2026-08-08/auth-skeleton/plan.md`

**Requirements:**
1. `create_app()` calls `configure_logging(get_settings())` before building the app, so startup
   itself is logged in the right format.
2. `RequestContextMiddleware` is added to the app.
3. `CONVENTIONS.md`'s logging section points at the real setup.
4. The auth-skeleton plan's Task 8 drops its logging half and keeps CORS.

**Verify — run the server, do not infer:**

```bash
# console
uv run uvicorn tradinghub.main:create_app --factory --port 8000
curl localhost:8000/health          # expect NO access line (DEBUG)
curl localhost:8000/nope            # expect one INFO line with a request id
curl -H "X-Request-ID: trace-me" localhost:8000/nope   # expect [trace-me]
```

Uvicorn's own startup lines must appear in *our* format. If they still read
`INFO:     Started server process`, requirement 9 of Task L1 is not working.

```bash
# production
LOG_FORMAT=json ENVIRONMENT=production uv run uvicorn tradinghub.main:create_app --factory
```

Then assert programmatically that **every** non-blank output line parses as JSON — eyeballing it
misses exactly the uvicorn lines this is meant to catch.

**Commit:** `Wire logging into the application`

---

## Definition of done

- [ ] Local output is one readable line per event, including uvicorn's
- [ ] Production output is one JSON object per line, with no exceptions, verified by a parser
- [ ] `sqlalchemy.engine` at INFO does not appear; raising `LOG_LEVEL=DEBUG` still does not surface it
- [ ] A request id appears on every line produced during a request, including third-party lines
- [ ] `/health` does not appear at INFO
- [ ] A query string containing a token does not appear in any log line
- [ ] Full suite, ruff, and basedpyright all pass
