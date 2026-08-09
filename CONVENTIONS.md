# Code Conventions

The standard for Python in this repo. It accounts for FastAPI, async SQLAlchemy, and the decisions
recorded in `plans/*/spec.md`, and it overrides any general Python style guidance that conflicts
with it.

Frontend conventions are not covered yet; they get added when Phase 2 starts.

## Project structure

The layout exists so a file's location is predictable from a description of the work, without
reading the tree.

- **`core/`** holds shared infrastructure — configuration, database, errors, logging. It must never
  import from a feature package. If something in `core/` needs to know about auth, it belongs in
  `auth/` instead.
- **Each feature is one directory** (`auth/`, later `journal/`, `binance/`) containing everything
  about it: models, schemas, routes, and its own logic.
- **`main.py`** is the entry point and wires features together. Nothing imports from it.

Within a feature package, use the same filenames every time, so the same question resolves to the
same path in every feature:

| File | Holds |
|---|---|
| `models.py` | SQLAlchemy models |
| `schemas.py` | Pydantic request/response types |
| `routes.py` | The endpoints |
| `dependencies.py` | FastAPI dependencies |
| `<topic>.py` | Focused logic — `passwords.py`, `tokens.py`, `rate_limit.py` |

**`tests/` mirrors `src/` exactly** — same directories, same filenames with a `test_` prefix.
`src/tradinghub/auth/sessions.py` is tested by `tests/auth/test_sessions.py`, and nowhere else.
A test whose location cannot be derived from the module it covers is in the wrong place.

## Tooling

| Concern | Tool |
|---|---|
| Type checking | `basedpyright` |
| Linting and formatting | `ruff` |
| Tests | `pytest` with `asyncio_mode = "auto"` |
| Dependencies | `uv` — never `pip install` into the project |

Follow what basedpyright reports. Guidance written against `mypy --strict` does not transfer
cleanly — basedpyright is stricter in some places and differently strict in others.

## Functions

There is no line limit. Length is a symptom worth looking at, not a rule to satisfy — a flat
30-line sequence can be clearer than six one-line helpers that only make sense together.

Extract a helper when **the extracted part has a name that means something on its own**. If you
have to invent a name like `_do_login_part_two`, the split is wrong; leave it inline.

What actually matters:

- **One level of abstraction per function.** Mixing "validate the request" with byte-level string
  manipulation in the same body is the real smell, at any length.
- **Return early.** Nesting past two levels usually means a guard clause is missing.
- **One reason to change.** A function that grew because it accumulated unrelated responsibilities
  should be split; one that is simply a long linear sequence should not.
- **Testable in isolation.** If you cannot test it without elaborate setup, the problem is its
  dependencies, not its size.

Around 40 lines, stop and look. Usually there is a genuine seam. Sometimes there isn't, and forcing
one makes the code worse.

## Types

- Every parameter and return value is annotated. No exceptions.
- Modern syntax only: `list[str]` not `List[str]`, `str | None` not `Optional[str]`.
- `Sequence` / `Mapping` for read-only parameters.
- `Protocol` for describing a shape a caller depends on — it needs no inheritance and keeps the
  implementer unaware of you. Reach for an abstract base class only when subclasses should share
  actual implementation.
- `StrEnum` for a fixed set of string values that is shared across modules or persisted to the
  database — status, role, category. `Literal["light", "dark"]` for a small closed set used in one
  place; basedpyright narrows it exhaustively and Pydantic validates it at no runtime cost. Either
  way, never a bare `str` with an implied set of valid values.

## Data containers

A house preference, not an industry ranking:

1. **Pydantic `BaseModel`** for anything crossing a trust boundary — request bodies, responses,
   settings, external API payloads. Validation belongs at the edge.
2. **`@dataclass(frozen=True, slots=True)`** for internal containers with no validation needs.
3. **`TypedDict`** for the shape of a JSON payload you do not own and do not want to instantiate.
4. **Plain classes** only when behavior is the point.

### Carve-out: SQLAlchemy models

SQLAlchemy models inherit `DeclarativeBase`. SQLAlchemy 2.0 does offer `MappedAsDataclass`, which
would make them real dataclasses — we deliberately do not use it. The spec makes models the domain
objects directly, with no separate entity layer, so do not "fix" a model into a dataclass and do
not add a repository layer wrapping the session. That is a project decision, not a rule of Python.

Pydantic schemas in `schemas.py` are the boundary types. Models are the persistence types. Both
exist on purpose; they are not duplication.

## Database schema

Constraint and index names come from the `naming_convention` on `Base.metadata` in
`core/database.py`. Never name a constraint by hand, and never let one be created without it —
Alembic cannot reliably drop or alter a constraint whose name the database invented.

| Kind | Pattern | Example |
|---|---|---|
| Primary key | `pk_<table>` | `pk_users` |
| Unique | `uq_<table>_<column>` | `uq_users_email` |
| Index | `ix_<table>_<column>` | `ix_sessions_token_hash` |
| Foreign key | `fk_<table>_<column>_<referred table>` | `fk_sessions_user_id_users` |
| Check | `ck_<table>_<name>` | `ck_users_email_not_blank` |

Table names are plural snake_case (`users`, `login_attempts`); column names are singular
snake_case. Timestamps are always `TIMESTAMP WITH TIME ZONE` — a naive column silently drops the
offset and the bug only appears outside UTC. Primary keys are UUIDs, not serial integers, since
sequential ids leak row counts and invite enumeration once they appear in URLs.

Foreign keys state their delete behavior explicitly (`ondelete="CASCADE"` for rows that cannot
outlive their parent). Relying on the application to clean up is how orphans accumulate.

Every schema change is an Alembic migration, generated with `--autogenerate` and then **read
before running**. Autogenerate does not know about extensions, data backfills, or concurrent index
creation, so those are added by hand.

## Naming

Full words. Code is read far more than written.

| Avoid | Use |
|---|---|
| `ctx` | `context` |
| `msg` | `message` |
| `req` / `res` | `request` / `response` |
| `err` | `error` or `exception` |
| `val` | `value` |
| `fn` / `func` | `function` |
| `cfg` | `config` or `configuration` |
| `idx` | `index` |
| `tmp` | `temporary`, or something descriptive |
| `ret` | `result`, or something descriptive |
| `deps` | `dependencies` |
| `params` | `parameters` |
| `i`, `j`, `k` | `index`, `row`, `column` — unless a genuinely trivial loop |

Fine as-is: `url`, `id`, `api`, `http`, `db`, `ip`, and `*args` / `**kwargs`, which are idiomatic
Python and should not be expanded. `e` in `except ... as e` and `f` in `with open(...) as f` are
also fine — Google's guide permits both — though the fuller name is never wrong.

The `deps` and `params` rows apply to **your** names, not to a framework's. FastAPI's decorator
takes `dependencies=[...]`, pytest uses `params`; mirror the library's spelling rather than
inventing a mismatch.

Name a parameter for the **role it plays**, not for its type — the annotation already carries the
type. Use a type-echoing name only when a function takes two values of related types and the role
alone would be ambiguous.

## Errors

- Catch specific exceptions. Never a bare `except:`.
- Log with context before re-raising.
- Use the `AppError` hierarchy in `errors.py` for anything reaching the client — never let a raw
  exception shape a response body.
- Every error the API returns uses `{"error": {"code": ..., "message": ...}}`. This deliberately
  overrides FastAPI's default `{"detail": ...}`, which is why the exception handlers exist — do not
  "fix" a handler back to the default.

## Logging

Configured in `core/logging.py`: readable lines locally, one JSON object per line in production,
selected by `LOG_FORMAT` (unset means "match the environment"). See
`plans/2026-08-08/logging/spec.md` for the reasoning.

- `logging`, never `print`.
- Module-level `logger = logging.getLogger(__name__)`.
- Lazy interpolation: `logger.info("Fetching %s", url)`, not an f-string.
- Structured context goes in `extra={...}`, which becomes top-level JSON fields. Prefer
  `logger.info("login failed", extra={"user_id": user.id})` over formatting values into the message.
- `logger.exception(...)` inside an `except` block, never `logger.error(str(error))` — the former
  keeps the traceback.
- A new noisy third-party logger goes in `THIRD_PARTY_LEVELS`, not into a filter at the call site.

**Never logged**, and this is correctness rather than style: passwords, password hashes, session
tokens, raw request bodies, `Authorization` and `Cookie` headers, and query strings. Do not add a
"log the body on error" convenience — that is precisely how credentials reach disk.

## Async

- `async def` for anything doing I/O.
- Await every coroutine. An un-awaited coroutine never runs; Python emits a `RuntimeWarning` and
  basedpyright reports it. Treat either as an error, not noise.
- `asyncio.TaskGroup` for genuinely concurrent work. The Python docs prefer it over
  `asyncio.gather()` because a failing child cancels its siblings instead of leaving them running.
  Use `gather(..., return_exceptions=True)` only when partial success is the intended semantics.
- **Never share one `AsyncSession` across concurrent tasks.** SQLAlchemy documents this as unsafe.
  The request-scoped session from `get_db` is for sequential work only; each concurrent task that
  touches the database needs its own session from `session_factory`.
- No blocking calls directly inside an `async def` — no `time.sleep`, no synchronous HTTP client,
  no blocking file read. One blocking call stalls the entire event loop, not just that request.
- When a blocking or CPU-bound call is unavoidable, offload it rather than inlining it:
  `await asyncio.to_thread(...)`, or declare the path operation with plain `def` so FastAPI runs it
  in its threadpool. **Password hashing is the live example** — Argon2 is deliberately expensive
  and must not run inline on the loop.
- SQLAlchemy 2.0 async style only: `AsyncSession`, `select()`, `await session.scalar(...)`. The
  1.x `Query` API does not work here.

Argon2id parameters follow the OWASP Password Storage floor: `m=19456` (19 MiB), `t=2`, `p=1`.
Do not lower them for speed; the cost is the point.

## Docstrings and comments

- Public functions get a docstring. State what it does, and state if it raises.
- Document parameters with `Args:` when their meaning is not obvious from the signature. A separate
  `Returns:` section is optional when the function returns `None`, or when the summary line already
  starts with "Return…" and fully describes the result.
- Comments explain *why*, never *what*. If a comment restates the code, delete it.
- No comments addressed to a reviewer ("changed this because…"). That belongs in the commit message.

## Suppression comments

`# noqa`, `# type: ignore`, `# pyright: ignore`, `# pragma: no cover` — fix the underlying issue
instead. Treat one of these appearing in a diff as a defect, not a style nit.

**The one permitted exception:** a known false positive in a third-party library's typing, where
every alternative is worse than the ignore. It must be narrowly scoped to the specific rule, on the specific
line, with a comment above it explaining why the checker is wrong.

There is currently exactly one in the codebase, in `config.py`:

```python
# database_url and frontend_origin are populated by pydantic-settings from the environment,
# which the type checker cannot see. Omitting them here is what makes a missing variable
# raise ValidationError at startup.
return Settings()  # pyright: ignore[reportCallIssue]
```

If that count ever exceeds two or three, the rule is being abused rather than applied.

## Tests

- Anything touching the database runs against real Postgres in a container, never SQLite. `citext`
  and the Postgres UUID type are load-bearing in the schema, and the app runs on asyncpg — a SQLite
  suite would exercise a different dialect *and* a different driver. Tests involving no database
  need no container.
- Each test rolls back in a transaction. Tests never depend on ordering or on each other's rows.
- Test names state the behavior: `test_expired_session_returns_none`, not `test_session_2`.
- Assert on behavior, not implementation. A test that breaks on a rename without a behavior change
  is a liability.
- Security-relevant behavior gets an explicit test. "Logout invalidates the session server-side" is
  a test, not an assumption.
