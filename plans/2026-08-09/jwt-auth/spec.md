# JWT access and refresh tokens

Supersedes Tasks 5 and 6 of `plans/2026-08-08/auth-skeleton/`. Tasks 1-4 (users, password hashing,
error shape, register) and Tasks 7-12 are unchanged, except where noted at the end.

## Why this exists

The auth-skeleton slice specified opaque server-side sessions: one random token, a row in
`sessions`, a database lookup on every authenticated request. That design is correct for this
application and would have been less work.

This slice replaces it with stateless access tokens plus stored refresh tokens, for two reasons —
one honest, one aspirational:

- **Learning.** Access/refresh is the dominant pattern in the industry and worth having built once,
  including the parts that are easy to get wrong.
- **Read scale.** An access token is verified by signature, so an authenticated request costs no
  database round trip. That only matters at a volume this application will not reach for a long
  time.

**What it costs, stated plainly:** logout no longer takes effect immediately. See "The revocation
gap" below. If that trade ever stops being acceptable, the fix is to go back to sessions, not to
add a token blocklist — a blocklist is a database lookup per request, which is the thing the access
token existed to avoid.

## Shape

Two tokens, deliberately different in kind.

| | Access token | Refresh token |
|---|---|---|
| Format | JWT, HS256 | Opaque random string |
| Lifetime | 15 minutes | 30 days |
| Stored server-side | No | Yes, SHA-256 hash only |
| Revocable | No, until it expires | Yes, immediately |
| Sent on | Every request | Only `POST /auth/refresh` |
| Cookie path | `/` | `/auth/refresh` |

The refresh token is **not** a JWT. It must be revocable, and a JWT's defining property is that it
is not. Making it a JWT would mean looking it up in the database anyway to check revocation, which
is all cost and no benefit.

The `sessions` table survives unchanged in spirit: it is now the refresh-token store.

## Token contents

The access token JWT carries only what is needed to identify the caller and bound its validity:

```json
{"sub": "<user id>", "sid": <session id>, "iat": ..., "exp": ...}
```

- `sub` — the user id. `get_current_user` builds the caller's identity from this without a query.
  Ids are integers, but `sub` is a string: the JWT spec requires it, and libraries reject a numeric
  one. Convert back to `int` in exactly one place, when decoding.
- `sid` — the session row that minted this token, so a future audit can tie an access token to a
  login.
- No email, no roles, no anything that can go stale. A JWT is a snapshot; anything mutable in it is
  a bug waiting for someone to change it in the database and wonder why the token disagrees.

Signed with HS256 and a single secret. RS256 exists for when other services must verify tokens
without being able to mint them; there is one backend here, so the extra key management buys
nothing.

## Rotation and reuse detection

This is the part that makes the design safe rather than merely fashionable, and skipping it is how
these systems get broken.

Every call to `POST /auth/refresh`:

1. Hashes the presented refresh token and looks up the session.
2. If the session is missing or expired — 401.
3. **If the session is already marked used — the token has been replayed. Revoke every session in
   its family and return 401.**
4. Otherwise: mark it used, create a successor session in the same family, and return a new access
   token plus the new refresh token.

Refresh tokens are therefore single-use. A "family" is a login: the chain of successive refresh
tokens descending from one `POST /auth/login`, linked by a shared `family_id`.

Step 3 is the whole point. If an attacker steals a refresh token, one of two things happens: they
use it before the legitimate user, or after. Either way the *second* use is a replay of an
already-used token, which trips detection and kills the family. Both parties get logged out, which
is the correct outcome — an unexplained logout is a survivable annoyance, a silently shared account
is not.

Without rotation, a stolen refresh token is a permanent account key that survives password changes.
That is strictly worse than the session design this slice replaces.

## The revocation gap

Logout deletes the session row. The refresh token stops working immediately. **The outstanding
access token keeps working until it expires**, up to 15 minutes later.

This is inherent to stateless tokens, not an implementation shortcut. It means:

- "Log out everywhere" is accurate within 15 minutes, not instantly.
- A user who logs out on a shared computer is exposed for up to 15 minutes if the attacker already
  holds the access token — though the token is in an `HttpOnly` cookie, so holding it requires
  having compromised the machine, at which point there are worse problems.
- Changing a password revokes sessions, again with the same 15-minute tail.

Fifteen minutes is the dial. Shorter narrows the gap and increases refresh traffic; longer does the
opposite. Do not "fix" this with a revoked-token table.

## Cookies

| | Access | Refresh |
|---|---|---|
| Name | `access_token` | `refresh_token` |
| `HttpOnly` | yes | yes |
| `SameSite` | `Lax` | `Lax` |
| `Secure` | production only | production only |
| `Path` | `/` | `/auth/refresh` |
| `Max-Age` | 15 minutes | 30 days |

Both are `HttpOnly`. The access token does **not** go in `localStorage` — that is the common
tutorial advice and it is wrong: any XSS on the page can read it and exfiltrate it, which is
precisely what `HttpOnly` prevents.

The refresh cookie's `Path=/auth/refresh` means the browser only sends it to the endpoint that
consumes it. A stolen access token expires in 15 minutes; a stolen refresh token is a 30-day key,
so it should be exposed as rarely as possible.

## Endpoints

| Endpoint | Behaviour |
|---|---|
| `POST /auth/login` | Verify credentials, create a session, set both cookies, return `{id, email}` |
| `POST /auth/refresh` | Rotate as described above, set both cookies, return 204 |
| `POST /auth/logout` | Delete the session row, clear both cookies, return 204 |
| `GET /auth/me` | Verify the access token signature, return `{id, email}`, 401 otherwise |

`GET /auth/me` performs no database query on the happy path. That is the entire performance
argument for this design, so it is worth not quietly undoing it later by loading the user "just to
be safe".

Login remains uniform: an unknown email and a wrong password produce the same 401 body, and the
same timing, per the auth-skeleton spec.

## Settings

| Setting | Default | Notes |
|---|---|---|
| `jwt_secret` | none — required | Missing value fails at startup, not on first login |
| `access_token_lifetime` | 15 minutes | |
| `refresh_token_lifetime` | 30 days | |

`jwt_secret` is a real secret: anyone holding it can mint a valid access token for any user id.
It belongs in the environment, never in the repository, and rotating it invalidates every
outstanding access token — which is the emergency lever if one is ever leaked.

## What carries over unchanged

- Argon2id password hashing, uniform register, the error shape, request ids and logging.
- Task 7's login rate limiting, which is about failed password attempts and is indifferent to what
  the successful path issues.
- Tasks 9-12's frontend work, with one change: the API client must retry once through
  `POST /auth/refresh` on a 401 and then replay the original request. That retry is the visible
  cost of the 15-minute access token, and it belongs in one place in `lib/api.ts` rather than at
  every call site.

## Known gaps

- No password reset, so a user who registers twice and forgets the original password is stuck.
  Carried from the auth-skeleton spec.
- `jwt_secret` rotation logs everyone out. Supporting overlapping keys means a key id in the JWT
  header and a map of secrets; not worth it at one backend with no users.
- No "list my active sessions" or per-device revocation UI. The `sessions` table deliberately does
  **not** carry `user_agent` or `ip`: nothing reads them today, and the two are only meaningful
  together, on a screen that displays them. Add both when that screen exists — `ip` is personal
  data, so collecting it wants a reason and a retention policy rather than being kept by default.
