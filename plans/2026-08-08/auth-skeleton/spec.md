# Slice 1: Auth + Skeleton — Design

**Date:** 2026-08-08
**Status:** Approved
**Scope:** First of five slices. Delivers a working FastAPI + Postgres + Next.js system where users
can register, log in, and log out, with a protected but near-empty dashboard.

## Context

Tradinghub is a multi-user trading journal. The project's primary goal is depth in FastAPI, Next.js,
Postgres, and Terraform on AWS, so managed services and batteries-included frameworks were
deliberately rejected where they would replace the learning.

The full product was decomposed into five ordered slices. Each gets its own spec, plan, and build
cycle. This document covers slice 1 only.

| Slice | Delivers |
|---|---|
| 1 | Auth + skeleton (this spec) |
| 2 | Trade journal CRUD |
| 3 | Binance read-only fill import |
| 4 | Charting + dashboard |
| 5 | Terraform on AWS |

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Audience | Multi-user product | Strangers will sign up; data isolation and abuse resistance are requirements, not optional |
| Auth build | Hand-rolled on vetted primitives | Maximum FastAPI learning; crypto itself is never invented, only composed |
| Session mechanism | Opaque token in Postgres, delivered as a cookie | Revocable by design, no refresh-token rotation, unreadable by JavaScript |
| Network topology | Sibling subdomains (`app.` / `api.`) | Keeps FastAPI a genuine standalone API for the slice 3 worker; costs one CORS block |
| Code organization | Domain-oriented packaging, no tactical DDD | Feature-first packages scale; repositories and entities are unearned at this complexity |
| Repo layout | One repo, two folders, only Postgres in Docker | Native dev servers and debuggers work unobstructed while learning both frameworks |
| Local database | Docker Compose, Postgres 16 | Pins the exact version AWS will run; trivial to reset |

### Explicit non-goals for slice 1

- Email verification and password reset (deferred; would require an email provider)
- OAuth / "log in with Google" (deferred; a second auth path with its own edge cases)
- Any trading functionality — the dashboard exists only to prove the auth gate works
- Deployment of any kind; slice 1 runs locally

## Architecture

```
Tradinghub/
├── docker-compose.yml          # Postgres 16 only
├── backend/
│   ├── pyproject.toml          # deps via uv
│   ├── alembic/                # migrations, from the first commit
│   ├── src/tradinghub/
│   │   ├── main.py             # app factory, CORS, router mounting
│   │   ├── config.py           # pydantic-settings, fails loudly on missing vars
│   │   ├── db.py               # async engine, session dependency
│   │   ├── errors.py           # exception handlers, uniform error shape
│   │   ├── logging.py          # structured JSON logs, request IDs
│   │   └── auth/
│   │       ├── models.py       # User, Session, LoginAttempt
│   │       ├── schemas.py      # request/response shapes
│   │       ├── passwords.py    # argon2id hash + verify
│   │       ├── tokens.py       # generate + hash session tokens
│   │       ├── sessions.py     # create / look up / revoke
│   │       ├── rate_limit.py   # failed-attempt counting
│   │       ├── dependencies.py # get_current_user
│   │       └── routes.py       # the four endpoints
│   └── tests/
└── frontend/
    ├── middleware.ts           # cheap presence gate on protected paths
    ├── e2e/                    # Playwright
    └── src/
        ├── lib/api.ts          # fetch wrapper, always credentials: "include"
        └── app/
            ├── (auth)/login, register
            └── (app)/dashboard
```

### Backend stack

SQLAlchemy 2.0 in async mode over asyncpg, with Alembic for migrations. Async is FastAPI's real
concurrency model and a large part of what learning it in depth means. Alembic is present from the
first commit because the schema changes constantly through slices 2 and 3, and retrofitting
migrations later is painful.

Password hashing uses `argon2-cffi` directly rather than passlib. Passlib has been effectively
unmaintained for years and warns on modern Python; Argon2id is the current recommendation.

Dependencies are managed with `uv`.

### Frontend stack

Next.js 16 App Router with TypeScript and Tailwind 4. Server Components are the default; client
components appear only where forms need interactivity. Next.js 16 differs from the 13/14-era
conventions most tutorials assume — notably `cookies()` is async.

`middleware.ts` performs a cheap presence-check on the session cookie to redirect obviously
anonymous users away from protected routes. It deliberately does **not** validate the session —
that is the backend's job, and middleware runs on every request. Real authorization always happens
in FastAPI.

### The seam

FastAPI knows nothing about Next.js. It exposes an HTTP API, sets a cookie, and validates that
cookie. Next.js is one consumer among several to come. Nothing in the backend assumes a browser is
calling it, which is what keeps the slice 3 Binance worker from requiring a rewrite.

## Data model

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. Sequential integers leak user count and invite enumeration |
| `email` | citext | Unique. Case-insensitivity enforced by Postgres, not by every code path remembering to lowercase |
| `password_hash` | text | Argon2id |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### `sessions`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `token_hash` | text | SHA-256 of the token. Indexed. The raw token is **never** stored |
| `user_id` | UUID | FK to users, `ON DELETE CASCADE` |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz | 30 days after creation |
| `last_seen_at` | timestamptz | Updated at most once per hour |
| `user_agent` | text | For a future "active sessions" screen; unread in slice 1 |
| `ip` | inet | Same |

Storing only the hash means a database dump yields values that cannot be replayed as cookies. Same
reasoning as password hashing, at the cost of one line.

### `login_attempts`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `email` | citext | Indexed with `created_at` |
| `ip` | inet | Indexed with `created_at` |
| `succeeded` | boolean | |
| `created_at` | timestamptz | |

Append-only. The rate limiter counts over this table rather than an in-memory counter, so limits
survive restarts and remain correct across multiple backend instances on AWS.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Create a session, set the cookie |
| POST | `/auth/logout` | Delete the session, clear the cookie |
| GET | `/auth/me` | Return the current user, or 401 `invalid_credentials` when anonymous |

## Flows

**Register.** Validate email format and a minimum password length of 12 characters, hash with
Argon2id, insert. A
duplicate email returns a response identical to success — otherwise the endpoint becomes a tool for
discovering who holds an account. Registration does not create a session; the user lands on the
login page.

**Login.** Check the rate limiter *before* touching the password. Look up the user, verify the hash,
record the attempt either way. On success, generate a token with `secrets.token_urlsafe(32)`, store
its SHA-256 hash as a new session row, and set the cookie to the raw token. Wrong email and wrong password
return the same generic error, and Argon2 verification runs even when no user was found so response
timing does not reveal which emails exist.

**Authenticated request.** A `get_current_user` dependency reads the cookie, hashes it, looks up the
session by hash, rejects when missing or expired, and returns the user. Routes needing a user simply
declare the dependency. `last_seen_at` is updated at most hourly, so the typical request is a single
indexed read with no write.

**Logout.** Delete the session row, then clear the cookie. Server-side deletion is what makes it
real; clearing the cookie alone would leave a token that still works if it was ever captured.

**Rate limiting.** Both limits use the same rolling 15-minute window: more than 10 failed attempts
for one email, or more than 30 failed attempts from one IP, returns 429 with a `Retry-After` header
and no password check. Only `/auth/login` is rate limited in slice 1; `/auth/register` is not.

## The cookie

| Attribute | Value | Reason |
|---|---|---|
| Name | `session` | |
| `HttpOnly` | yes | XSS cannot read it |
| `SameSite` | `Lax` | Not sent on cross-site form posts |
| `Secure` | production only | Local development is plain HTTP on localhost |
| `Domain` | `.yourdomain.com` in production | Lets `app.` and `api.` share it |
| `Path` | `/` | |
| Lifetime | 30 days | Matches `expires_at` |

Because the browser calls FastAPI directly, every frontend `fetch` must set
`credentials: "include"`, and FastAPI's CORS config must set `allow_credentials=True` with the
frontend origin listed explicitly. A wildcard origin is not permitted alongside credentials; this
combination is the most common way the setup fails.

In local development the cookie is issued for plain `localhost` with `Secure` off. Different ports
are still the same site, so no special handling is needed.

## Error handling

All errors share one shape so the frontend has a single thing to parse:

```json
{"error": {"code": "invalid_credentials", "message": "Email or password is incorrect."}}
```

A central FastAPI exception handler produces it; individual routes do not assemble their own.

| Code | Status |
|---|---|
| `validation_error` | 422 |
| `invalid_credentials` | 401 |
| `rate_limited` | 429 |
| `internal_error` | 500 |

The 500 handler logs the real exception with a request ID and returns only that ID. Stack traces
never reach the browser.

Logging is structured JSON from the start, because CloudWatch can query JSON and cannot usefully
query prose. Passwords and session tokens are never logged, including within request bodies.

## Configuration

All settings load from environment variables through `pydantic-settings`, which fails at startup
when a required variable is missing rather than at the first request that needs it. A committed
`.env.example` documents every variable; the real `.env` is gitignored. No secret has a default
value in code.

## Testing

Backend tests run against a real Postgres in a container, never SQLite — SQLite lacks `citext`, and
the point of a test is to exercise what actually runs. Each test runs in a transaction that rolls
back, giving isolation without rebuilding the schema.

Required coverage for slice 1:

- Registration rejects a duplicate email without revealing that it exists
- Login fails on a wrong password
- A valid cookie reaches a protected route
- An absent, forged, or expired cookie does not
- Logout invalidates the session server-side, not just in the browser
- The rate limiter trips at the threshold and releases after the window

One Playwright end-to-end run covers the frontend: register, log in, reach the dashboard, log out,
get bounced. Component-level frontend tests are not worth writing while the UI is two forms.

## Definition of done

- `docker compose up` starts Postgres; `alembic upgrade head` builds the schema
- Both dev servers start and the frontend can register, log in, and log out against the backend
- `/dashboard` is unreachable without a valid session
- The backend test suite and the Playwright run both pass
- `.env.example` is complete and the README documents the startup sequence

## Future slices

**Slice 2 — trade journal.** A `journal/` package: trades with entry, exit, size, fees, notes, and
tags, plus computed P&L. Manual entry only. Every query filters by the current user, with isolation
tests from the first commit.

**Slice 3 — Binance.** A `binance/` package: read-only API keys encrypted at rest, a background job
pulling fills, reconciliation into journal entries. The worker talks to Postgres and Binance
directly, which is what the standalone-API topology decision bought.

**Slice 4 — charting and dashboard.** Candles with the user's own executions overlaid, plus
aggregate statistics. A pure read layer over slices 2 and 3.

**Slice 5 — Terraform on AWS.** Intended shape: ECS Fargate for both containers behind one
Application Load Balancer, RDS Postgres in private subnets, secrets in Secrets Manager, Terraform
state in S3 with DynamoDB locking. Fargate over EC2 to avoid patching servers, and over Lambda
because a persistent Binance worker fits Lambda poorly. Roughly $60–90/month, with a cheaper
single-EC2 variant near $15 if cost outweighs learning the production-shaped setup. This slice gets
its own spec.
