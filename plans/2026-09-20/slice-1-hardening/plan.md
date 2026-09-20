# Slice 1 hardening

Three independent reviews of slice 1 (backend, frontend, and a second full-stack pass) were merged
and deduplicated here. Every item marked **verified** was checked against the code after the
reviews came in. Nothing is architectural rework; every fix is local.

All automated checks pass today: 112 backend tests, 12 Playwright tests, ruff, basedpyright,
prettier, tsc, eslint, and `alembic check`. These findings are what those checks cannot see.

**Status 2026-09-20: Parts A and B are complete.** Part C is for the slice 2 plan.

Owner column: **you** = high learning value for the stack this project exists to teach.
**hand off** = mechanical, low learning value. **decide** = a decision, not code.

---

## Part A — blockers

### A1. Refresh rotation is not atomic  ·  ✅ done
`auth/crud/session.py:12-20`, `auth/services/auth.py:112-138`

`get_session_by_token_hash` is a plain `SELECT`, and `mark_session_used` sets an attribute that is
flushed later. Two requests presenting the same token both read `used_at is None` before either
writes, so both rotate. A probe with a barrier produced two live successors and no reuse warning.
A thief who replays a stolen token at the same moment as the real client keeps a self-renewing
session, and the family is never revoked. Reuse detection only holds sequentially, which is the
one condition it was not built for.

This is the same bug as the rate limiter's burst race, in Postgres instead of Redis, and it has
the same two fixes:
- lock: `select(Session).where(...).with_for_update()`, so the second reader waits and then sees
  `used_at` set; or
- conditional write: `UPDATE sessions SET used_at = now() WHERE id = :id AND used_at IS NULL`, and
  treat `rowcount == 0` as reuse. This is the `INCR`-then-decide shape.

Test with two real connections, not the shared `db_session`: one transaction cannot race itself.

**Do A1 and A2 together.** See the warning under A2.

Done with the lock: `.with_for_update()` in `get_session_by_token_hash`. Proven by
`test_two_requests_racing_one_token_cannot_both_rotate`, which runs two real transactions with
`asyncio.gather` and asserts one rotation, one `InvalidSessionError`, and an empty family. It
fails with the lock removed. It commits for real and deletes its own account afterwards.

### A2. Two tabs refreshing at once look like theft  ·  ✅ done
`frontend/src/lib/api/client.ts:34-47`

`refreshInFlight` is module state, so it coordinates requests inside one tab only. Two tabs whose
access tokens expire together both POST `/auth/refresh` with the same cookie.

**Today A1's race hides this:** both tabs rotate and nobody notices. **Once A1 is fixed, the
second tab's refresh is correctly detected as reuse, the family is revoked, and the user is signed
out of every tab.** Fixing A1 alone turns a silent security hole into a visible usability bug.

Fix on the client with the Web Locks API: wrap the rotation in
`navigator.locks.request("tradinghub-refresh", ...)`, and inside the lock re-check whether another
tab already rotated before spending the token. Keep the server strict. A server-side grace window
for recent reuse was considered and rejected: it is exactly the window a thief needs.
Add a two-tab Playwright test.

Done, and simpler than planned: the refresh POST is wrapped in
`navigator.locks.request("tradinghub-refresh", ...)` and nothing else. No re-check is needed
inside the lock, because tabs share cookies: by the time a waiting tab gets in, the cookie the
browser attaches is the new one, so its refresh is an ordinary rotation and costs one spare
request. Proven by the e2e test "two tabs whose access token expires together both stay signed
in", which holds the first refresh until a second arrives and releases both together. It fails
with the lock removed.

### A3. The test fixture cannot see a rollback  ·  ✅ done
`tests/conftest.py:64-67`, `auth/services/auth.py:127`

`override_get_db` says it mirrors `get_db` but omits the `try / except: rollback; raise`. No test
in the suite exercises rollback-on-error. Consequence: the one deliberate `db.commit()` in the
codebase, the one that makes family revocation survive the 401 that follows it, can be deleted and
every test still passes. Confirmed by stubbing `commit` to a no-op.

Slice 2 inherits this fixture, so every "the request failed, therefore nothing was written"
guarantee in trade CRUD would be untested by construction.

Fix the override to match `get_db` exactly, then add an HTTP-level test: POST `/auth/refresh`
twice with the same cookie and assert the family's rows are gone. It must fail when the commit is
removed. Prove that by removing it once.

Done: `test_replaying_a_refresh_token_revokes_the_family_for_good` in `tests/auth/test_login.py`.
Proven by mutation: with the commit removed it fails under the corrected fixture and wrongly
passes under the old one. Slice 1 has no other request that writes before it fails, so there is
no second test for plain rollback; slice 2 will have many, and the fixture is now ready for them.

### A4. Argon2 runs on the event loop  ·  ✅ done
`auth/security/passwords.py:11,17`

`CONVENTIONS.md:204` names this exact case. `hash` and `verify` are synchronous and called from
`async def` services, so every other request on the worker waits. Measured: about 37 ms per call,
and 20 concurrent registrations took `/health` from 2.6 ms to 74.9 ms.

Fix inside `passwords.py` so callers only gain an `await`:
`await asyncio.to_thread(PASSWORD_HASHER.hash, raw_password)`. Bound the concurrency with a
semaphore so a burst cannot exhaust the default thread pool. Rename `PW_HASHER` while there.

Done, without the semaphore: the default executor is already bounded, so it would change nothing
today. `DUMMY_PASSWORD_HASH` is built at import, where nothing can be awaited, so it calls
`PASSWORD_HASHER.hash` directly. `test_hashing_leaves_the_event_loop_free` runs a ticker beside a
hash and fails when the hash is put back inline.

### A5. Signed-in state is derived from two fields that can disagree  ·  ✅ done
`frontend/src/app/(app)/layout.tsx:17-28`, `frontend/src/app/(auth)/layout.tsx:17-23`,
`frontend/src/features/auth/hooks.ts:30-39`

React Query keeps the last good `data` when a background refetch fails, so `isError` and `data`
can both be truthy. The app layout redirects to `/login` on `isError`; the auth layout redirects to
`/dashboard` when `data` exists. When a session dies after having worked, the tab bounces between
them forever, and the dead account's email stays on screen.

Three more symptoms share this root and one fix:
- any user-query error redirects, so a brief network outage signs a valid user out;
- logout navigates only because a cleared cache refetches, 401s, and fails a rotation;
- guarded pages render `null` while pending, so every reload flashes blank.

Fix: one `useSession()` returning `"unknown" | "authenticated" | "anonymous" | "unreachable"`,
derived from `status` and the error type. `ApiError` with `invalid_session` means anonymous and
clears the cache; `NetworkError` means unreachable and shows a retry, never a redirect. Both
layouts read that one value. `useLogout` calls `router.replace("/login")` itself. The layout
renders a skeleton while unknown.

Done as `useSession()` in `features/auth/hooks.ts`, derived from the query's `status` and never
its `data`. No cache clearing on `invalid_session` was added: once nothing reads stale data,
clearing it changes nothing. Two e2e tests hold it, and each fails with its bug put back: "a
session that dies while the dashboard is open ends at the login screen" uses Playwright's clock
to pass the stale time and a focus event to trigger the refetch, and "a lost connection offers a
retry instead of signing the visitor out" aborts `/auth/me`.

### A6. CORS allows only GET and POST  ·  ✅ done
`backend/src/tradinghub/main.py:73`

The first PATCH or DELETE in slice 2 fails at preflight and surfaces as "could not reach the
server". Added `PATCH` and `DELETE` plus `expose_headers=["Retry-After", "X-Request-ID"]`. `PUT`
was left out on purpose: nothing planned uses it, and it keeps a disallowed method for the
preflight test to use.

### A7. 500 responses carry no CORS headers and no request id  ·  ✅ done
`core/errors.py:63-76`, `main.py:68-75`

`exception_handler(Exception)` is installed on Starlette's `ServerErrorMiddleware`, which sits
outside both `CORSMiddleware` and `RequestContextMiddleware`. The body is right, but the browser
sees a CORS failure, so the reference id the handler exists to deliver never arrives. Every
unhandled slice 2 error inherits this. Worth doing by hand: it is the clearest lesson available in
how Starlette orders middleware. Catch and render inside `RequestContextMiddleware.dispatch`.

Done: the middleware returns the 500 itself and the `Exception` handler in `core/errors.py` is
gone. `add_middleware` wraps outward, so CORS, added last, is outermost and sees that response.
Covered by `tests/core/test_middleware.py`, which fails if the middleware re-raises.

### A8. Integer primary keys contradict the conventions  ·  ✅ decided: integers
`auth/models/user.py:17`, `auth/models/session.py:17`, `CONVENTIONS.md:118`

Conventions say UUIDs, because sequential ids leak row counts and invite enumeration once they are
in URLs. Both tables use serial integers, a choice the jwt-auth plan made on purpose. Slice 2 puts
trade ids in URLs. Either migrate now, with two tables and no production data, or amend the
conventions. Leaving them in disagreement is the worst option. A reasonable split: keep integers
for `users` and `sessions`, which never appear in a URL, and use UUIDs for everything that does.

Decided 2026-09-20: integer primary keys everywhere, and `CONVENTIONS.md` now says so. The
consequence for slice 2 is that a trade id in a URL is guessable, so every trade query must be
scoped to the owner. That was required anyway; with integer keys it is the only protection.

---

## Part B — cheap, ride along

| # | Item | Where | Owner |
|---|---|---|---|
| B1 | Rate-limit `/auth/register` by IP, before hashing. Reuses the limiter; good practice after Task 7 | `auth/routes.py:72`, `services/auth.py:67` | ✅ done |
| B2 | Concurrent duplicate registration returns 500. Catch `IntegrityError` around `create_user`, raise `EmailTakenError`; keep the pre-check as the fast path | `services/auth.py:71-75` | ✅ done |
| B3 | `%` in `DATABASE_URL` crashes every alembic command through configparser interpolation. Escape it, or bypass the ini | `alembic/env.py:23` | ✅ done |
| B4 | Empty or short `JWT_SECRET` is accepted at startup and fails at first login. `Field(min_length=32)` | `core/config.py:49` | ✅ done |
| B5 | `cookie_secure` has no production guard. `model_validator` rejecting production without it. Assert `Secure` and `SameSite` in the cookie test | `core/config.py:45` | ✅ done |
| B6 | A signed token with no `exp` is accepted; a missing or non-numeric `sub` raises a 500. `options={"require": ["exp", "iat", "sub"]}` and widen the except | `security/tokens.py:44-55` | ✅ done |
| B7 | `make api` starts Postgres but not Redis, so a fresh setup runs with limiting silently off. README still says login has no rate limiting and omits Redis from startup | `Makefile:3`, `README.md:24,93` | ✅ done |
| B8 | Frontend has no `RATE_LIMITED` code, drops `Retry-After`, and leaves submit enabled, so a locked-out user keeps raising the shared IP counter. Add the code, read the header (needs A6), disable submit for the window | `lib/api/errors.ts`, `client.ts`, `LoginForm.tsx` | ✅ done |
| B9 | `ApiError.code` is `string`, so `"email_takn"` compiles. Type it as the code union plus `string & {}`; add an `isApiError(error, code)` helper | `lib/api/errors.ts:12-21` | ✅ done |
| B10 | `(data as Envelope).error` throws on a `null` or array body, leaking a raw `TypeError` past the client | `lib/api/client.ts:26` | ✅ done |
| B11 | Wrong-password e2e registers, then visits `/login` still signed in; passes by timing. Await the redirect, then clear cookies | `e2e/auth.spec.ts:130` | ✅ done |
| B12 | No e2e covers a successful login; every green path registers | `e2e/auth.spec.ts` | ✅ done |
| B13 | Three e2e tests pass with their named behaviour removed: dashboard guard, "before reaching the server", sign-out clearing the previous account | `e2e/auth.spec.ts:34,154,166` | ✅ done |
| B14 | `user_id` log context var is never set; every line shows `-`. Set it in `get_current_user` | `core/logging.py:18` | ✅ done |
| B15 | `assert response.json() == {"id": response.json()["id"], ...}` cannot fail on the id | `tests/auth/test_login.py:55` | ✅ done |

Notes on what landed:
- B8: `ApiError` carries an optional `retryAfterSeconds` read from the `Retry-After` header. The
  login form shows "Try again in N minutes" and keeps the button disabled for that long. Its e2e
  test mocks the 429 rather than earning it, so the suite does not spend the shared IP counter.
- B1: `count_registration_attempt`, thirty per IP per window, counted before the lookup and the
  hash, never forgiven. Login and registration share one private `_count` helper. The error
  message became generic, "Too many attempts", since it now serves both.
- The Playwright suite registers and fails logins from one address, so `e2e/global-setup.ts`
  deletes exactly its own two counters, `register:ip:127.0.0.1` and `login:fail:ip:127.0.0.1`,
  before each run. It first used `FLUSHDB`; a follow-up review pointed out that would wipe
  anything else the development Redis comes to hold. A separate test API on its own Redis
  database was considered and rejected as far more machinery than two `DEL`s.
- Follow-up review, two more session fixes. Only `invalid_session` means signed out: once 500s
  became readable `ApiError`s (A7), `useSession()` was treating a server error as a dead session.
  And a refresh that fails on the network now surfaces as a `NetworkError` instead of being
  folded into "rotation refused", which had turned a dropped connection into a redirect to
  login. Each has an e2e test that fails with the fix reverted.
- B9: `isApiError(error, code?)` accepts only a `KnownApiCode`, so a typo in a branch is a compile
  error. `ApiError.code` itself stays open (`ApiCode`), because the backend may send a code this
  frontend has not learned yet.
- B14: the user id is set in `get_current_user`, but the access line is written by the middleware
  in a different task that cannot see that context var, so `request.state` carries it across.
- B4 and B5 changed two logging tests that built production settings without secure cookies.

## Part C — carry into the slice 2 plan

- Spent and expired session rows are never pruned, about 96 rows per user per day. Needs a cleanup
  job and an index on `expires_at`. Belongs with the deploy slice.
- Response bodies are asserted, not validated. Zod already parses requests; trades carry decimals,
  nullable exits, and timestamps, so parse responses at the `api.ts` boundary from slice 2 on.
- `authKeys` is a flat object. Settle the `all / list(filters) / detail(id)` key factory now.
- `staleTime` of two minutes is global and would silently apply to trade lists.
- Silent `localhost:8000` fallback for the API URL. Throw at module load instead.
- Enable `noUncheckedIndexedAccess` before slice 2 introduces lists.
- `router.push` after login leaves `/login` in history; use `replace`.
- The error banner is copy-pasted three times; extract it.
- Tests do not mirror `src/` fully: no direct tests for `core/errors.py`, `core/middleware.py`,
  `auth/dependencies.py`.
- `auth/` uses subpackages where the conventions table prescribes flat files. Decide before
  `journal/` copies it, and write the answer down.
- `CONVENTIONS.md` still says frontend conventions are not written. The decisions above are its
  content.
- `workers: 1` in Playwright is now load-bearing: the suite shares one IP counter of 30.

## Suggested order

A3 first, because it makes the fixture honest and every later backend fix is then properly tested.
Then A1 with A2, A4, A7, A5. A6 and the Part B hand-offs can land in parallel at any point.
Decide A8 before slice 2's first migration.
