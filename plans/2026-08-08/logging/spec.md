# Logging — Design

**Date:** 2026-08-08
**Status:** Approved
**Scope:** Application logging for the backend. Pulled forward from Task 8 of the auth-skeleton
plan, because every task after this one benefits from it and retrofitting log calls is worse than
writing them as you go.

## Goals

1. Readable, scannable output while developing.
2. Machine-parseable output in production, because CloudWatch can query JSON and cannot usefully
   query prose.
3. Third-party libraries silenced to the level where they are useful, not the level they default to.
4. Every line traceable to the request that produced it.
5. Credentials never reach a log, by construction rather than by remembering.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Library | Standard library `logging` with `dictConfig` | No new dependency; structlog's advantage is context binding, which the request-id contextvar already covers |
| Format selection | `LOG_FORMAT` setting; unset means console locally, JSON in production | One switch, sensible default, still overridable to debug prod formatting locally |
| Level | `LOG_LEVEL` setting, default `INFO` | Debugging a specific problem means raising it temporarily, not editing code |
| Structured context | `extra={...}` on log calls, emitted as JSON fields | Native to stdlib logging; no wrapper needed |
| Request correlation | `ContextVar` + a logging `Filter` | Puts the id on *every* record, including third-party ones, without threading it through call signatures |
| Access logs | Own middleware; uvicorn's access logger disabled | Uvicorn's version has no request id, no duration, and logs the query string |

### Rejected

- **structlog.** Genuinely better ergonomics for context binding, but it is a dependency plus a
  parallel logging system to learn alongside stdlib logging, and the request-id contextvar solves
  the specific problem we have. Revisit if log call sites start passing the same `extra` repeatedly.
- **A JSON logging library** (`python-json-logger` and friends). The formatter is about 20 lines.
- **Logging to a file.** Containers log to stdout; the platform collects it. Writing files inside a
  container means log rotation, disk pressure, and logs that vanish with the container.

## Format

**Console (local).** One line, fixed-width columns so the eye can scan down:

```
18:17:26 INFO    tradinghub.access    [60d41b06] GET /auth/login 200
```

**JSON (production).** One object per line:

```json
{"timestamp":"2026-08-08T18:17:26+0000","level":"INFO","logger":"tradinghub.access",
 "message":"GET /auth/login 200","request_id":"60d41b06","method":"POST",
 "path":"/auth/login","status_code":200,"duration_ms":42.1}
```

Anything passed via `extra={...}` becomes a top-level field. Exceptions are rendered into an
`exception` field rather than spanning multiple unparseable lines.

## Third-party log levels

Defaults are chosen by library authors for debugging their library, not for running an application.
Without pinning, application logs are unfindable.

| Logger | Level | Why |
|---|---|---|
| `sqlalchemy.engine` | WARNING | At INFO it logs every statement **and every result row** |
| `sqlalchemy.pool` | WARNING | Connection checkout/checkin chatter |
| `sqlalchemy.dialects` | WARNING | |
| `asyncpg` | WARNING | |
| `watchfiles` | WARNING | One line per filesystem scan under `--reload` |
| `asyncio` | WARNING | |
| `httpx` / `httpcore` | WARNING | Slice 3's Binance client; logs every request at INFO |
| `python_multipart` | WARNING | Per-token parser output on form posts |
| `botocore` / `boto3` / `urllib3` | WARNING | Slice 5 |
| `alembic` | INFO | Migration progress is worth seeing |
| `uvicorn.access` | disabled | Replaced by our middleware |

**Uvicorn needs special handling and this is the non-obvious part.** Uvicorn attaches its *own*
handlers with its *own* formatter to `uvicorn` and `uvicorn.error`. Setting a level is not enough —
those handlers must be cleared and the loggers set to propagate, or production emits uvicorn's
plain-text startup lines interleaved with our JSON, which breaks log ingestion. Verified
empirically: without this, `INFO:     Started server process` appears verbatim alongside JSON.

`disable_existing_loggers` must be `False`, or loggers created before configuration (uvicorn's,
Alembic's) are silently switched off.

## Request correlation

A `ContextVar` holds the current request id. A logging `Filter` stamps it onto every record, so
third-party lines emitted mid-request are correlated too, with no changes to their call sites.

The middleware honours an inbound `X-Request-ID` header when present and generates one otherwise,
then echoes it on the response. Honouring the inbound value is what lets a trace span the frontend,
the load balancer, and the API. Requests outside a request context log `-`.

## Access logging

One line per request: method, path, status, duration in milliseconds, client IP, request id.

Two deliberate exclusions:

- **The query string is never logged.** Query parameters are a common place for tokens and reset
  codes to appear, and access logs are widely readable. Path only.
- **`/health` logs at DEBUG, not INFO.** The load balancer polls it every few seconds; at INFO it
  buries everything else.

## Security

Never logged, and this is a correctness requirement rather than a style preference: passwords,
password hashes, session tokens, raw request bodies, `Authorization` and `Cookie` headers, query
strings. There is no "log the body on error" convenience — that is precisely how credentials reach
disk.

## Non-goals

Metrics, tracing spans, log shipping configuration, sampling, and alerting. Those belong with the
deployment slice, where there is somewhere for them to go.

## Resolved

1. **Library:** stdlib `logging`. Third-party libraries already log through it, so there is one
   system rather than two, and the request-id contextvar covers what structlog's context binding
   would provide.
2. **Access logs:** our own middleware. Uvicorn's has no request id, no duration, and logs the
   query string.
3. **`/health`:** logged at DEBUG.
