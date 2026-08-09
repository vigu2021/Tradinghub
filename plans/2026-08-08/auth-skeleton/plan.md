# Auth + Skeleton Implementation Plan

**Goal:** A running FastAPI + Postgres + Next.js system where a user can register, log in, reach a
protected dashboard, and log out, with sessions revocable server-side and login rate limited.

**Architecture:** Two independent processes. FastAPI owns Postgres and all auth decisions, exposing
an HTTP API and a session cookie. Next.js is one consumer of that API, calling it directly from the
browser with `credentials: "include"`. Code is grouped by feature (`auth/`), not by technical layer.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic, argon2-cffi,
pydantic-settings, uv, pytest + pytest-asyncio, Postgres 16 via Docker Compose, Next.js 16 App
Router (Turbopack), TypeScript, Tailwind 4, Playwright.

**Spec:** `plans/2026-08-08/auth-skeleton/spec.md` — read it before starting. This plan implements
it and does not restate its rationale.

---

## How to use this plan

**Vignesh writes the implementation.** This is a guide to work through, not a task list for Claude
to execute. It deliberately does not contain finished implementations of the auth logic — writing
those is the point of the project.

What each task gives you:

- **Files** — exactly what to create or change
- **Interfaces** — exact signatures and types, so later tasks line up with earlier ones
- **Requirements** — what the code must do, numbered, each one independently checkable
- **Tests** — real test code, because these are the acceptance criteria. Write them first if you
  want the TDD loop; either way they must pass before the task is done.
- **Verify** — the exact command to run and what you should see
- **Hints** — the library calls you'd otherwise spend twenty minutes searching for. Looking up an
  API is not learning; deciding what to do with it is.

Mechanical configuration (Docker Compose, Alembic's `env.py`, CORS setup) appears verbatim, because
there is nothing to learn from retyping it and a subtle mistake there costs an afternoon.

Hand any task to Claude by saying so. Default is you write it and Claude reviews.

## Global Constraints

- Python 3.13, Node 22, Postgres 16 — all confirmed installed
- Dependencies managed by `uv`; never `pip install` into the project
- SQLAlchemy 2.0 async style throughout (`AsyncSession`, `select()`), never the 1.x `Query` API
- Minimum password length: **12 characters**
- Session lifetime: **30 days** absolute; `last_seen_at` updated at most once per hour
- Rate limits: **10** failed logins per email, **30** per IP, both in a rolling **15-minute** window
- Cookie: name `session`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` in production only
- Session tokens are stored **only** as SHA-256 hashes. The raw token never touches the database
- No secret has a default value in code; every one comes from the environment
- Errors always use the shape `{"error": {"code": ..., "message": ...}}`
- Passwords and session tokens never appear in logs, including inside request bodies
- Every commit is scanned for secrets first; messages are one line with no tooling attribution

---

## File structure

```
Tradinghub/
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── src/tradinghub/
│   │   ├── main.py             # app factory, CORS, router mounting
│   │   ├── core/               # shared infrastructure; knows nothing about features
│   │   │   ├── config.py       # Settings, loaded once
│   │   │   ├── database.py     # engine, SessionFactory, Base, get_db
│   │   │   ├── errors.py       # AppError + exception handlers
│   │   │   └── logging.py      # structured JSON logs, request IDs
│   │   └── auth/               # one feature, one directory
│   │       ├── models.py       # User, Session, LoginAttempt
│   │       ├── schemas.py      # Pydantic request/response models
│   │       ├── passwords.py    # hash_password, verify_password
│   │       ├── tokens.py       # generate_token, hash_token
│   │       ├── sessions.py     # create_session, get_user_for_token, revoke_session
│   │       ├── rate_limit.py   # check_login_allowed, record_attempt
│   │       ├── dependencies.py # get_current_user
│   │       └── routes.py       # the four endpoints
│   └── tests/                  # mirrors src/ exactly: same paths, same filenames
│       ├── conftest.py
│       ├── test_main.py
│       ├── core/
│       └── auth/
└── frontend/
    ├── middleware.ts
    ├── e2e/auth.spec.ts
    └── src/
        ├── lib/api.ts
        └── app/
            ├── (auth)/login/page.tsx
            ├── (auth)/register/page.tsx
            └── (app)/dashboard/page.tsx
```

---

# Phase 1 — Backend foundation

## Task 1: Postgres and a booting FastAPI app  ✅ DONE

**Files:**
- Create: `docker-compose.yml`, `backend/pyproject.toml`, `backend/.env.example`,
  `backend/src/tradinghub/core/{config,database}.py`, `backend/src/tradinghub/main.py`, `backend/tests/conftest.py`,
  `backend/tests/test_main.py`

**Interfaces produced:**
```python
# core/config.py
class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class Settings(BaseSettings):
    database_url: str
    frontend_origin: str
    cookie_domain: str | None = None
    cookie_secure: bool = False
    environment: Environment = Environment.DEVELOPMENT

def get_settings() -> Settings: ...   # cached, call this rather than instantiating

# core/database.py
Base: type[DeclarativeBase]
engine: AsyncEngine
SessionFactory: async_sessionmaker[AsyncSession]
async def get_db() -> AsyncIterator[AsyncSession]: ...   # FastAPI dependency

# main.py
def create_app() -> FastAPI: ...
```

**Verbatim — `docker-compose.yml`:**
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: tradinghub
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: tradinghub
    # Loopback only: the credentials below are committed, so this must not be network-reachable.
    ports:
      - "127.0.0.1:5432:5432"
    restart: unless-stopped
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tradinghub"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
```

The password here is a local development value and is intentionally in the repo. Production
credentials come from Secrets Manager in slice 5 and never appear in this file.

**Verbatim — `backend/.env.example`:**
```
DATABASE_URL=postgresql+asyncpg://tradinghub:localdev@localhost:5432/tradinghub
FRONTEND_ORIGIN=http://localhost:3000
COOKIE_SECURE=false
ENVIRONMENT=development
```

**Steps:**

- [ ] **1.1** Initialize the backend project.

```bash
cd backend
uv init --name tradinghub --python 3.13
uv add fastapi "uvicorn[standard]" sqlalchemy asyncpg alembic pydantic-settings argon2-cffi
uv add --dev pytest pytest-asyncio httpx
```

- [ ] **1.2** Write `core/config.py`.

Requirements:
1. `Settings` subclasses `BaseSettings` with the fields in the Interfaces block above.
2. It reads from a `.env` file and from real environment variables, environment winning.
3. `database_url` and `frontend_origin` have **no defaults** — a missing value must raise at import
   of the settings object, not at first use.
4. `get_settings()` is cached so the file is parsed once per process.

Hints: `from pydantic_settings import BaseSettings, SettingsConfigDict`;
`model_config = SettingsConfigDict(env_file=".env")`; wrap `get_settings` in `functools.lru_cache`.

- [ ] **1.3** Write `core/database.py`.

Requirements:
1. Create one module-level async engine from `settings.database_url`.
2. Create an `async_sessionmaker` bound to it with `expire_on_commit=False`.
3. `Base` is a `DeclarativeBase` subclass that all models will inherit.
4. `get_db()` yields a session and guarantees it is closed even when the request raises.

Hints: `create_async_engine`, `async_sessionmaker`, `AsyncSession` from
`sqlalchemy.ext.asyncio`. `expire_on_commit=False` matters — without it, accessing an attribute
after commit triggers a lazy refresh that fails outside async context.

- [ ] **1.4** Write `main.py` with a `create_app()` factory that returns a `FastAPI` instance and
      registers one route, `GET /health`, returning `{"status": "ok"}`.

A factory rather than a module-level `app` because tests need to build an app with overridden
dependencies.

- [ ] **1.5** Write `tests/conftest.py` and `tests/test_main.py`.

```python
# tests/conftest.py
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tradinghub.main import create_app

@pytest_asyncio.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

```python
# tests/test_main.py
import pytest

@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Add to `pyproject.toml` so you don't need the marker on every test:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["src"]
```

- [ ] **1.6** Verify.

```bash
docker compose up -d
docker compose ps          # db should be "healthy"
cd backend && cp .env.example .env
uv run pytest -v           # 1 passed
uv run uvicorn tradinghub.main:create_app --factory --reload
curl localhost:8000/health # {"status":"ok"}
```

- [ ] **1.7** Add `.env` and `backend/.venv` to `.gitignore`, then commit.
      Suggested message: `Add backend scaffolding and Postgres compose file`

---

## Task 2: Alembic and the users table  ✅ DONE

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, one migration in `alembic/versions/`,
  `backend/src/tradinghub/auth/models.py`
- Modify: `backend/tests/conftest.py`

**Interfaces produced:**
```python
# auth/models.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID]
    email: Mapped[str]
    password_hash: Mapped[str]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**Steps:**

- [ ] **2.1** Scaffold Alembic in async mode.

```bash
cd backend && uv run alembic init -t async alembic
```

- [ ] **2.2** Point Alembic at your settings and metadata. Replace the relevant parts of
      `alembic/env.py` with:

```python
from tradinghub.config import get_settings
from tradinghub.db import Base
from tradinghub.auth import models  # noqa: F401  — registers tables on Base.metadata

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata
```

The `noqa`'d import is load-bearing: autogenerate only sees models that have been imported. Every
future feature package needs a line here. Add `prepend_sys_path = src` to `alembic.ini` so
`tradinghub` is importable.

- [ ] **2.3** Write `auth/models.py` with the `User` model.

Requirements:
1. `id` is a UUID primary key defaulting to a new UUID4 generated in Python.
2. `email` uses Postgres `CITEXT`, is unique and non-null.
3. `password_hash` is non-null text.
4. `created_at` and `updated_at` are timezone-aware and default to the database's `now()`.
5. `updated_at` also updates on modification.

Hints: `from sqlalchemy.dialects.postgresql import CITEXT`; use
`mapped_column(server_default=func.now())` and `onupdate=func.now()`; `DateTime(timezone=True)` —
a naive timestamp column will silently drop offsets and cause hard-to-see bugs later.

- [ ] **2.4** Generate the migration, then **edit it by hand** to enable the extension first:

```bash
uv run alembic revision --autogenerate -m "create users table"
```

Autogenerate does not know about the extension. Add as the first line of `upgrade()`:
```python
op.execute("CREATE EXTENSION IF NOT EXISTS citext")
```
Read the whole generated file before running it. Autogenerate is a starting point, not an oracle,
and reviewing its output is a habit worth forming now.

- [ ] **2.5** Apply and confirm the schema:

```bash
uv run alembic upgrade head
docker compose exec db psql -U tradinghub -c "\d users"
```
Expected: `email` shows type `citext` with a unique index.

- [ ] **2.6** Add database fixtures to `conftest.py`. Each test runs in a transaction that rolls
      back, so tests never see each other's rows.

```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tradinghub.config import get_settings
from tradinghub.db import get_db
from tradinghub.main import create_app

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(get_settings().database_url)
    connection = await engine.connect()
    transaction = await connection.begin()
    maker = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = maker()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

Tests run against the same Postgres as development. That is fine because everything rolls back —
and it is the whole point, since SQLite has no `citext`.

- [ ] **2.7** Write `tests/auth/test_models.py`:

```python
from sqlalchemy import select
from tradinghub.auth.models import User

async def test_email_is_case_insensitive(db_session):
    db_session.add(User(email="Vig@Example.com", password_hash="x"))
    await db_session.flush()

    found = await db_session.scalar(select(User).where(User.email == "vig@example.com"))
    assert found is not None
```

- [ ] **2.8** Verify with `uv run pytest -v` (2 passed), then commit:
      `Add Alembic and the users table`

---

## Task 3: Password hashing

**Files:**
- Create: `backend/src/tradinghub/auth/passwords.py`, `backend/tests/auth/test_passwords.py`

**Interfaces produced:**
```python
def hash_password(password: str) -> str: ...
def verify_password(password: str, password_hash: str) -> bool: ...
```

**Requirements:**
1. `hash_password` returns an Argon2id hash. Two calls with the same password return **different**
   strings, because the salt is random.
2. `verify_password` returns `True` for a matching password and `False` for a wrong one.
3. `verify_password` returns `False` rather than raising when handed a malformed hash.
4. Neither function logs its input.

Hints: `from argon2 import PasswordHasher`; `from argon2.exceptions import VerifyMismatchError,
VerificationError, InvalidHashError`. Create one module-level `PasswordHasher()` — construction is
not free. `.verify()` raises rather than returning a bool, which is why requirement 3 exists.
Leave the default parameters alone; they follow current OWASP guidance.

**Tests:**
```python
from tradinghub.auth.passwords import hash_password, verify_password

def test_hash_is_salted():
    assert hash_password("correct horse battery") != hash_password("correct horse battery")

def test_verify_accepts_correct_password():
    assert verify_password("correct horse battery", hash_password("correct horse battery"))

def test_verify_rejects_wrong_password():
    assert not verify_password("wrong", hash_password("correct horse battery"))

def test_verify_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-hash")
```

**Verify:** `uv run pytest tests/auth/test_passwords.py -v` — 4 passed.
**Commit:** `Add Argon2 password hashing`

---

## Task 4: Error shape and the register endpoint

**Files:**
- Create: `backend/src/tradinghub/core/errors.py`, `backend/src/tradinghub/auth/{schemas,routes}.py`,
  `backend/tests/auth/test_register.py`
- Modify: `backend/src/tradinghub/main.py`

**Interfaces produced:**
```python
# errors.py
class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None: ...

def register_error_handlers(app: FastAPI) -> None: ...

# auth/schemas.py
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str          # min_length=12

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str

# auth/routes.py
router: APIRouter        # prefix="/auth", tags=["auth"]
```

**Requirements — `errors.py`:**
1. An `AppError` handler renders `{"error": {"code": ..., "message": ...}}` at its status code.
2. A `RequestValidationError` handler renders the same shape with code `validation_error` at 422.
3. A catch-all `Exception` handler logs the exception with a generated request ID and returns code
   `internal_error` at 500, with the ID in the message and **no** traceback in the body.

**Requirements — register:**
4. `POST /auth/register` accepts `{email, password}` and returns **201** with no body.
5. Passwords shorter than 12 characters are rejected by the schema, producing 422.
6. A duplicate email returns **201 with an identical response** to a successful registration. It
   must not reveal that the account exists.
7. Registration does not create a session and sets no cookie.
8. Email is stored as submitted; `citext` handles matching.

Requirement 6 is the one worth pausing on. Check for the existing user and return early on the same
code path — do not let an `IntegrityError` bubble up, since a 500 is itself a signal that the email
exists.

Hints: `EmailStr` needs `uv add "pydantic[email]"`. `Field(min_length=12)`. Mount the router in
`create_app()` and call `register_error_handlers(app)` there too.

**Tests:**
```python
async def test_register_creates_user(client):
    response = await client.post("/auth/register",
                                 json={"email": "a@example.com", "password": "correct horse battery"})
    assert response.status_code == 201

async def test_register_rejects_short_password(client):
    response = await client.post("/auth/register",
                                 json={"email": "b@example.com", "password": "short"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

async def test_duplicate_email_is_indistinguishable_from_success(client):
    payload = {"email": "dupe@example.com", "password": "correct horse battery"}
    first = await client.post("/auth/register", json=payload)
    second = await client.post("/auth/register", json=payload)
    assert first.status_code == second.status_code == 201
    assert first.content == second.content

async def test_register_does_not_set_a_cookie(client):
    response = await client.post("/auth/register",
                                 json={"email": "c@example.com", "password": "correct horse battery"})
    assert "set-cookie" not in response.headers
```

**Verify:** `uv run pytest -v` — 10 passed.
**Commit:** `Add register endpoint and uniform error shape`

---

## Task 5: Sessions table and session logic

**Files:**
- Create: `backend/src/tradinghub/auth/{tokens,sessions}.py`, one migration,
  `backend/tests/auth/test_sessions.py`
- Modify: `backend/src/tradinghub/auth/models.py`

**Interfaces produced:**
```python
# auth/tokens.py
def generate_token() -> str: ...           # secrets.token_urlsafe(32)
def hash_token(token: str) -> str: ...     # sha256 hex digest

# auth/models.py
class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID]
    token_hash: Mapped[str]                # indexed, unique
    user_id: Mapped[uuid.UUID]             # FK users.id, ondelete="CASCADE"
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    last_seen_at: Mapped[datetime]
    user_agent: Mapped[str | None]         # Text
    ip: Mapped[str | None]                 # postgresql.INET, surfaced as str in Python

# auth/sessions.py
SESSION_LIFETIME = timedelta(days=30)

async def create_session(db, user, *, user_agent=None, ip=None) -> str: ...   # returns RAW token
async def get_user_for_token(db, token: str) -> User | None: ...
async def revoke_session(db, token: str) -> None: ...
```

**Requirements:**
1. `create_session` generates a token, stores **only** its hash, sets `expires_at` 30 days out, and
   returns the raw token. The raw token is never persisted or logged.
2. `get_user_for_token` hashes the token, finds the session, and returns the user — or `None` when
   the token is unknown or `expires_at` has passed.
3. `get_user_for_token` updates `last_seen_at` only when it is more than an hour stale, so the
   common path is a read with no write.
4. `revoke_session` deletes the row. Calling it with an unknown token is not an error.
5. `token_hash` is indexed; every authenticated request looks up by it.
6. Deleting a user deletes their sessions, enforced by the database, not by application code.

Hints: `secrets.token_urlsafe(32)` gives ~43 URL-safe characters from 32 random bytes.
`hashlib.sha256(token.encode()).hexdigest()`. Plain SHA-256 is correct here and Argon2 would be
wrong — the input is already 256 bits of entropy, so there is nothing to brute-force, and you need
this fast enough to run on every request. Use `datetime.now(timezone.utc)`, never `utcnow()`.

**Tests:**
```python
async def test_raw_token_is_not_stored(db_session, registered_user):
    token = await create_session(db_session, registered_user)
    stored = await db_session.scalar(select(Session.token_hash))
    assert stored != token

async def test_valid_token_returns_user(db_session, registered_user):
    token = await create_session(db_session, registered_user)
    assert (await get_user_for_token(db_session, token)).id == registered_user.id

async def test_unknown_token_returns_none(db_session):
    assert await get_user_for_token(db_session, "nonsense") is None

async def test_expired_session_returns_none(db_session, registered_user):
    token = await create_session(db_session, registered_user)
    session = await db_session.scalar(select(Session))
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()
    assert await get_user_for_token(db_session, token) is None

async def test_revoke_invalidates_token(db_session, registered_user):
    token = await create_session(db_session, registered_user)
    await revoke_session(db_session, token)
    assert await get_user_for_token(db_session, token) is None
```

Add these to `conftest.py` — Tasks 6 and 7 rely on the same names:

```python
PASSWORD = "correct horse battery staple"

@pytest_asyncio.fixture
async def registered_user(db_session) -> User:
    user = User(email="user@example.com", password_hash=hash_password(PASSWORD))
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture
async def second_user(db_session) -> User:
    user = User(email="second@example.com", password_hash=hash_password(PASSWORD))
    db_session.add(user)
    await db_session.flush()
    return user
```

**Verify:** `uv run alembic upgrade head` then `uv run pytest -v` — 15 passed.
**Commit:** `Add sessions table and session lifecycle`

---

## Task 6: Login, logout, and the current-user dependency

**Files:**
- Create: `backend/src/tradinghub/auth/dependencies.py`, `backend/tests/auth/test_login.py`
- Modify: `backend/src/tradinghub/auth/{routes,schemas}.py`, `backend/src/tradinghub/core/config.py`

**Interfaces produced:**
```python
SESSION_COOKIE_NAME = "session"

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User: ...
# raises AppError("invalid_credentials", 401) when there is no valid session
```

**Requirements — login:**
1. `POST /auth/login` accepts `{email, password}` and returns 200 with `{id, email}`.
2. On success it sets the `session` cookie to the raw token with `HttpOnly`, `SameSite=Lax`,
   `Path=/`, `max_age` matching the 30-day lifetime, `secure` from `settings.cookie_secure`, and
   `domain` from `settings.cookie_domain` when set.
3. A wrong password returns 401 `invalid_credentials`.
4. An unknown email returns **the identical** 401 body.
5. When the email is unknown, still run a password verification against a dummy hash, so response
   time does not reveal which emails exist.
6. `user_agent` and `ip` are recorded on the session from the request.

**Requirements — `get_current_user`:**
7. Reads the cookie, resolves it via `get_user_for_token`, returns the `User`.
8. Raises 401 `invalid_credentials` when the cookie is absent, unknown, or expired.

**Requirements — the rest:**
9. `GET /auth/me` returns `{id, email}` for a valid session, 401 otherwise.
10. `POST /auth/logout` revokes the session server-side **and** deletes the cookie, returning 204.
    It succeeds even with no valid session — logout is never an error.

Requirement 5 is subtle: an early `return` when no user is found makes that path measurably faster
than the wrong-password path, and the difference is enough to enumerate accounts. Hash a fixed
dummy password once at module load and verify against it.

Hints: `response.set_cookie(...)` and `response.delete_cookie(...)` — `delete_cookie` must be
given the same `path` and `domain` or the browser keeps the original. Client IP is
`request.client.host`; behind the ALB in slice 5 it becomes `X-Forwarded-For`, so isolate this in
one small function now.

**Tests:**
```python
async def test_login_sets_httponly_cookie(client, registered_user):
    response = await client.post("/auth/login",
                                 json={"email": registered_user.email, "password": PASSWORD})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie.lower()

async def test_wrong_password_and_unknown_email_are_identical(client, registered_user):
    wrong = await client.post("/auth/login",
                              json={"email": registered_user.email, "password": "wrong-password-x"})
    unknown = await client.post("/auth/login",
                                json={"email": "nobody@example.com", "password": "wrong-password-x"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()

async def test_me_requires_a_session(client):
    assert (await client.get("/auth/me")).status_code == 401

async def test_me_returns_user_when_logged_in(client, registered_user):
    await client.post("/auth/login", json={"email": registered_user.email, "password": PASSWORD})
    response = await client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == registered_user.email

async def test_logout_invalidates_session_server_side(client, registered_user):
    await client.post("/auth/login", json={"email": registered_user.email, "password": PASSWORD})
    await client.post("/auth/logout")
    assert (await client.get("/auth/me")).status_code == 401

async def test_forged_cookie_is_rejected(client):
    client.cookies.set("session", "forged-token-value")
    assert (await client.get("/auth/me")).status_code == 401
```

`AsyncClient` keeps cookies across requests, which is what makes these read naturally.
`test_logout_invalidates_session_server_side` is the important one: it would still pass if logout
only cleared the cookie, so **also** assert the `sessions` row count dropped to zero.

**Verify:** `uv run pytest -v` — 21 passed.
**Commit:** `Add login, logout, and session authentication`

---

## Task 7: Login rate limiting

**Files:**
- Create: `backend/src/tradinghub/auth/rate_limit.py`, one migration,
  `backend/tests/auth/test_rate_limit.py`
- Modify: `backend/src/tradinghub/auth/{models,routes}.py`

**Interfaces produced:**
```python
class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[uuid.UUID]
    email: Mapped[str]          # CITEXT
    ip: Mapped[str | None]      # postgresql.INET
    succeeded: Mapped[bool]
    created_at: Mapped[datetime]

RATE_WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_EMAIL = 10
MAX_FAILURES_PER_IP = 30

async def check_login_allowed(db, email: str, ip: str | None) -> None: ...
    # raises AppError("rate_limited", 429) when over either limit
async def record_attempt(db, email: str, ip: str | None, *, succeeded: bool) -> None: ...
```

**Requirements:**
1. `check_login_allowed` counts **failed** attempts inside the rolling 15-minute window and raises
   when either limit is exceeded. Successful logins never count against you.
2. The 429 response carries a `Retry-After` header in seconds.
3. Login calls `check_login_allowed` **before** verifying the password, so a locked-out attacker
   costs you no Argon2 work.
4. `record_attempt` runs on both success and failure.
5. Only `/auth/login` is limited; `/auth/register` is not, per the spec.
6. Composite indexes on `(email, created_at)` and `(ip, created_at)` — without them this is a
   sequential scan on every login.
7. Attempts are committed even when login fails, so failures actually accumulate. Verify this
   interacts correctly with however routes handle transactions.

**Tests:**
```python
async def test_lockout_after_ten_failures(client, registered_user):
    for _ in range(10):
        await client.post("/auth/login",
                          json={"email": registered_user.email, "password": "wrong-password-x"})
    response = await client.post("/auth/login",
                                 json={"email": registered_user.email, "password": PASSWORD})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert "retry-after" in response.headers

async def test_old_failures_fall_out_of_the_window(client, db_session, registered_user):
    for _ in range(10):
        await client.post("/auth/login",
                          json={"email": registered_user.email, "password": "wrong-password-x"})
    await db_session.execute(
        update(LoginAttempt).values(created_at=datetime.now(timezone.utc) - timedelta(minutes=16))
    )
    await db_session.flush()
    response = await client.post("/auth/login",
                                 json={"email": registered_user.email, "password": PASSWORD})
    assert response.status_code == 200

async def test_lockout_is_per_email(client, registered_user, second_user):
    for _ in range(10):
        await client.post("/auth/login",
                          json={"email": registered_user.email, "password": "wrong-password-x"})
    response = await client.post("/auth/login",
                                 json={"email": second_user.email, "password": PASSWORD})
    assert response.status_code == 200
```

Note the third test shares an IP across both users, so it also proves the per-IP limit of 30 is not
firing early. Rewinding timestamps rather than sleeping keeps the suite fast.

**Verify:** `uv run alembic upgrade head` then `uv run pytest -v` — 24 passed.
**Commit:** `Add login rate limiting`

---

## Task 8: CORS

**Files:**
- Modify: `backend/src/tradinghub/main.py`
- Create: `backend/tests/test_cors.py`

Logging is no longer part of this task: it was pulled forward and implemented separately. See
`plans/2026-08-08/logging/`.

**Verbatim — CORS block in `create_app()`:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
```

`allow_origins` must list the origin explicitly. `["*"]` with `allow_credentials=True` is rejected
by browsers, and it is the single most common way this setup fails. If the frontend later reads a
custom response header, it must be added to `expose_headers` or it will be invisible to JavaScript.

**Requirements — logging:**
1. Logs are emitted as JSON with at least timestamp, level, message, and request ID.
2. A middleware assigns each request an ID and includes it on every log line for that request.
3. Request bodies are never logged. Do not add a "log the body on error" convenience — that is
   exactly how passwords reach disk.

**Tests:**
```python
async def test_preflight_allows_the_frontend_origin(client):
    response = await client.options(
        "/auth/login",
        headers={"Origin": "http://localhost:3000",
                 "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"

async def test_other_origins_are_not_allowed(client):
    response = await client.options(
        "/auth/login",
        headers={"Origin": "http://evil.example.com",
                 "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
```

**Verify:** `uv run pytest -v` — 26 passed. Backend is complete.
**Commit:** `Add CORS and structured request logging`

---

# Phase 2 — Frontend

## Task 9: Next.js scaffold and the API client

**Files:**
- Create: `frontend/` (via CLI), `frontend/src/lib/api.ts`, `frontend/.env.local.example`

**Steps:**

- [ ] **9.1** Already done — the scaffold exists. It was created with:

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --eslint \
  --import-alias "@/*" --use-npm --disable-git --yes
```

You have Next.js 16.3 with Turbopack as the default bundler and Tailwind 4. `npm run build`
succeeds. The route-group directories from the file structure above exist with `.gitkeep`
placeholders, which you can delete as each one gains a real file.

`create-next-app` also generated `frontend/AGENTS.md` (and a one-line `frontend/CLAUDE.md` that
imports it). It is not documentation itself — it is a warning that Next.js 16 broke conventions
from earlier versions, pointing at the real docs bundled in `node_modules/next/dist/docs/`. Consult
those when a tutorial's approach doesn't work; most of what you'll find online targets 13 or 14.
`next dev` rewrites this file if removed, so leave it committed.

- [ ] **9.2** Create `frontend/.env.local.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
`NEXT_PUBLIC_` is required for the browser to see it. Only ever put non-secret values behind that
prefix — anything with it is compiled into the JavaScript bundle and is fully public.

**Interfaces produced:**
```typescript
// src/lib/api.ts
export type ApiError = { code: string; message: string };
export class ApiRequestError extends Error {
  constructor(public readonly error: ApiError, public readonly status: number);
}
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T>;
```

**Requirements:**
1. `apiFetch` prefixes `NEXT_PUBLIC_API_URL` and always sets `credentials: "include"`. Without that
   the cookie is neither sent nor stored, and every request looks anonymous.
2. It sets `Content-Type: application/json` when there is a body.
3. On a non-2xx response it parses the `{error: {code, message}}` shape and throws
   `ApiRequestError`. Callers should never inspect `response.ok` themselves.
4. It returns `null` for 204 responses rather than trying to parse an empty body.
5. It is usable from Server Components too, where cookies must be forwarded explicitly — accept an
   optional cookie header parameter for that case.

**Verify:** `npm run dev`, confirm the default page loads at `localhost:3000`.
**Commit:** `Add Next.js scaffold and API client`

---

## Task 10: Register and login pages

**Files:**
- Create: `frontend/src/app/(auth)/register/page.tsx`, `frontend/src/app/(auth)/login/page.tsx`,
  `frontend/src/app/(auth)/layout.tsx`

**Requirements:**
1. Both are Client Components — they own form state. Mark them `"use client"`.
2. Register posts to `/auth/register`, then redirects to `/login` on success.
3. Login posts to `/auth/login`, then redirects to `/dashboard` on success.
4. Errors from `ApiRequestError` render inline, using the server's `message`. Never invent
   friendlier copy for `invalid_credentials` — it is deliberately vague.
5. The submit button is disabled while a request is in flight, so double-submits cannot happen.
6. Password inputs use `type="password"` and `autoComplete="current-password"` / `"new-password"`.
7. Inputs have real `<label>` elements associated by `htmlFor`. Placeholder-only labels are
   inaccessible.
8. The 429 case shows the rate-limit message rather than a generic failure.

Keep styling minimal — Tailwind defaults, a centered card. Slice 4 owns visual design.

**Verify manually:** register a new account, get redirected to login, log in, land on `/dashboard`
(404 until Task 11 — that is expected). In DevTools → Application → Cookies, confirm a `session`
cookie exists and is flagged `HttpOnly`.
**Commit:** `Add register and login pages`

---

## Task 11: Protected dashboard, middleware, and logout

**Files:**
- Create: `frontend/middleware.ts`, `frontend/src/app/(app)/dashboard/page.tsx`,
  `frontend/src/app/(app)/logout-button.tsx`

**Requirements — middleware:**
1. Matches `/dashboard` and anything beneath it.
2. Redirects to `/login` when the `session` cookie is **absent**.
3. Checks presence only. It does not call the backend and does not validate the token — middleware
   runs on every matching request, and real authorization is the backend's job.

**Requirements — dashboard:**
4. A Server Component that calls `GET /auth/me`, forwarding the incoming cookie via `cookies()`
   from `next/headers`. Server-side fetches do not carry browser cookies automatically.
5. Renders the user's email and a logout button.
6. Redirects to `/login` if the call returns 401 — this is the real gate, catching the expired or
   forged cookies that middleware waves through.

**Requirements — logout:**
7. A Client Component posting to `/auth/logout`, then navigating to `/login`.
8. Uses `router.refresh()` or a full navigation so cached Server Component output for the
   authenticated view is discarded.

Hints: `import { cookies } from "next/headers"` — in current Next.js it is async, so `await` it.
`redirect()` from `next/navigation` throws to interrupt rendering; do not wrap it in a `try`.

**Verify manually:**
1. Visit `/dashboard` logged out → redirected to `/login`
2. Log in → dashboard shows your email
3. Click logout → back at `/login`
4. Press Back → still redirected to `/login`, not a cached dashboard
5. Delete the `session` cookie in DevTools, reload → redirected
6. Edit the cookie to a garbage value, reload → still redirected, proving step 6's server check

**Commit:** `Add protected dashboard and logout`

---

## Task 12: End-to-end test and README

**Files:**
- Create: `frontend/e2e/auth.spec.ts`, `frontend/playwright.config.ts`
- Modify: `README.md`

**Steps:**

- [ ] **12.1** `cd frontend && npm init playwright@latest`

- [ ] **12.2** Write one test covering the full journey:

```typescript
import { test, expect } from "@playwright/test";

test("register, log in, reach the dashboard, log out", async ({ page }) => {
  const email = `user-${Date.now()}@example.com`;
  const password = "correct horse battery staple";

  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /register/i }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText(email)).toBeVisible();

  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});
```

`getByLabel` only works if Task 10's labels are properly associated — the test enforces that
accessibility requirement rather than merely suggesting it. The timestamped email keeps runs
independent, since this test hits a real database and does not roll back.

- [ ] **12.3** Write the README: prerequisites, `docker compose up -d`, backend `.env` and
      `alembic upgrade head`, both dev server commands, and how to run each test suite.

- [ ] **12.4** Verify from a clean state — this is the real test of the README:

```bash
docker compose down -v && docker compose up -d
cd backend && uv run alembic upgrade head && uv run pytest -v   # 26 passed
cd ../frontend && npx playwright test                            # 1 passed
```

- [ ] **12.5** Commit: `Add end-to-end auth test and README`

---

## Definition of done

- [ ] `docker compose up -d` starts Postgres; `alembic upgrade head` builds the schema from scratch
- [ ] Both dev servers start and the frontend can register, log in, and log out against the backend
- [ ] `/dashboard` is unreachable without a valid session, verified with a forged cookie
- [ ] 26 backend tests and 1 Playwright test pass from a clean database
- [ ] `.env.example` is complete and the README documents the startup sequence
- [ ] No secrets committed; every diff was scanned before landing

## Deliberately not in this slice

Email verification, password reset, OAuth, refresh tokens, an active-sessions screen, any trading
feature, and any deployment. Slice 2 begins with the `journal/` package.

**Carried to slice 5:** `Settings` has no guard forcing `cookie_secure` on when
`environment` is `PRODUCTION`. Nothing runs in production yet, so it would be dead code — but the
default is `False`, which fails open. Add the validator as part of the deployment slice, before
anything serves real traffic.
