# Tradinghub

A multi-user trading journal. Built in ordered slices, primarily as a way to learn FastAPI,
Next.js, Postgres, and Terraform on AWS in depth.

Slice 1 — hand-rolled authentication — is done. Slice 2 is the trade journal itself.

## Stack

|          |                                                                              |
| -------- | ---------------------------------------------------------------------------- |
| Backend  | FastAPI, SQLAlchemy 2.0 async over asyncpg, Alembic, Pydantic v2, `uv`       |
| Frontend | Next.js 16 App Router, React 19, TypeScript, Tailwind 4, TanStack Query, zod |
| Database | Postgres 16 in Docker                                                        |
| Tests    | pytest for the API, Playwright for the browser                               |

## Prerequisites

Docker, [uv](https://docs.astral.sh/uv/), Python 3.13, and Node 22.

## Getting started

```bash
docker compose up -d                    # Postgres on 127.0.0.1:5433, Redis on 127.0.0.1:6380

cp backend/.env.example backend/.env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # paste into JWT_SECRET
cd backend && uv run alembic upgrade head

cp frontend/.env.local.example frontend/.env.local
cd frontend && npm install
```

`JWT_SECRET` has no default on purpose: the app refuses to start without one rather than signing
tokens with a value that is in the repository.

Then, in two shells:

```bash
make api    # http://localhost:8000, docs at /docs
make web    # http://localhost:3210
```

The frontend's port is not arbitrary. It has to match `FRONTEND_ORIGIN` in `backend/.env`, or CORS
rejects every request and the browser shows a form that silently does nothing.

## Tests

```bash
make test   # pytest
make e2e    # Playwright; needs `make api` running in another shell
make check  # ruff, basedpyright, prettier, tsc, eslint
```

`make e2e` starts the frontend itself but not the backend, which needs a database — a run that
quietly passed against no API would be worse than one that fails to start.

Both suites hit the real development database and do not roll back. The API tests wrap each case
in a transaction; the browser tests register throwaway accounts at `@example.com`.

## How authentication works

Two cookies, both `HttpOnly` and `SameSite=Lax`:

- **`access_token`** — a 15-minute HS256 JWT at `Path=/`. Stateless: `get_current_user` verifies
  the signature and never queries the database.
- **`refresh_token`** — 7 days, opaque, scoped to `Path=/auth` so it is sent nowhere else. Only its
  SHA-256 hash is stored.

Refresh tokens are single-use. Each rotation marks the old row used and issues a successor carrying
the same `family_id`. Presenting an already-used token means two parties hold it, and since the
server cannot tell the thief from the victim, the whole family is revoked and both must sign in
again.

Logins are deliberately uninformative: an unknown email is verified against a fixed dummy hash so
the timing matches a real one, and a wrong password and a missing account return byte-identical
401s.

Route protection lives in the two route-group layouts rather than a proxy, because the only cookie
a proxy could see at `/dashboard` expires forty times faster than the session does. See
`plans/2026-08-08/auth-skeleton/` for the reasoning.

## Layout

```
backend/src/tradinghub/    # auth/ and core/, tests mirror the paths exactly
frontend/src/              # app/, features/auth/, components/ui/, lib/api/
plans/<date>/<feature>/    # spec.md and plan.md, both written before any code
```

## Known gaps

- Login is rate limited per email and per IP; registration is not yet.
- The IP limit reads the socket peer. Behind a load balancer it needs uvicorn's
  `--proxy-headers`, or every caller shares one counter.
- No password strength or breach check; `12345678` is accepted.
- An access token stays valid for up to 15 minutes after logout. Deliberate, and asserted by
  `test_an_access_token_outlives_logout`.
