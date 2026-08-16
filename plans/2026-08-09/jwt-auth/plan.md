# Plan — JWT access and refresh tokens

Replaces Tasks 5 and 6 of `plans/2026-08-08/auth-skeleton/plan.md`. Spec: `spec.md` in this folder.

Task numbering continues from the auth-skeleton plan, so Task 7 (rate limiting) still follows.

## Layout after this slice

```
auth/
├── models/
│   ├── user.py
│   └── session.py          # new: the refresh-token store
├── schemas/
│   ├── user.py
│   └── session.py          # new: LoginRequest
├── crud/
│   ├── user.py
│   └── session.py          # new
├── services/
│   ├── users.py
│   └── sessions.py         # new: login, refresh, logout
├── security.py             # grows: JWT encode/decode, token generation
├── dependencies.py         # new: get_current_user
└── routes.py               # grows: login, refresh, logout, me
```

---

## Task 5: Sessions table  ✅ DONE (migration `0742d8e39597`)

**Files:**
- Create: `backend/src/tradinghub/auth/models/session.py`, one migration,
  `backend/tests/auth/models/test_session.py` ← still outstanding
- Modify: `backend/src/tradinghub/auth/models/__init__.py`

**Interface produced:**
```python
class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int]
    user_id: Mapped[int]                   # FK users.id, ondelete="CASCADE"
    family_id: Mapped[uuid.UUID]           # indexed; shared by every token in one login chain
    hashed_refresh_token: Mapped[str]      # indexed, unique
    used_at: Mapped[datetime | None]       # set when this token is exchanged; non-null means spent
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
```

**Requirements:**
1. `hashed_refresh_token` is unique and indexed — every refresh looks up by it.
2. `family_id` is indexed — reuse detection revokes a whole family at once.
3. Deleting a user deletes their sessions, enforced by the database via `ondelete="CASCADE"`.
4. `used_at` defaults to NULL. A non-null value means the token has already been exchanged, which
   is what makes replay detectable.
5. All timestamps are timezone-aware (`DateTime(timezone=True)`).

Primary keys are integers, matching `users`. `family_id` stays a UUID: it is generated in Python at
login before any row exists, so a sequence would buy nothing, and it is never exposed.

Do **not** add `last_seen_at`. The auth-skeleton design touched it on every authenticated request;
here the row is only read on refresh, so there is nothing to track. `user_agent` and `ip` are
likewise omitted until there is a session-management screen that displays them.

**Tests (outstanding):** a session row cascades away with its user; `hashed_refresh_token` rejects
duplicates; `used_at` starts NULL.

**Verify:** `uv run alembic upgrade head` then `uv run pytest -v`.
**Commit:** `Add sessions table`

---

## Task 6: Token helpers

**Files:**
- Modify: `backend/src/tradinghub/auth/security.py`, `backend/src/tradinghub/core/config.py`,
  `backend/tests/auth/test_security.py`, `backend/.env.example`

**Interfaces produced:**
```python
# security.py — still pure: no database, no request context
ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_LIFETIME = timedelta(days=30)

def generate_refresh_token() -> str: ...        # secrets.token_urlsafe(32)
def hash_refresh_token(token: str) -> str: ...  # sha256 hex digest
def encode_access_token(user_id: int, session_id: int) -> str: ...
def decode_access_token(token: str) -> AccessTokenClaims | None: ...   # None when invalid
```

**Requirements:**
1. `generate_refresh_token` returns ~43 URL-safe characters from 32 random bytes.
2. `hash_refresh_token` is plain SHA-256. Argon2 would be wrong here: the input is already 256 bits
   of entropy so there is nothing to brute-force, and this runs on the refresh path.
3. `decode_access_token` returns `None` — never raises — for an expired token, a bad signature, a
   malformed string, or a missing claim. Callers turn that into a 401.
4. `decode_access_token` verifies the signature and `exp`. A decode that skips verification is the
   single most common JWT vulnerability; `jwt.decode` must never be called with
   `options={"verify_signature": False}`.
5. `jwt_secret` is a required setting with no default, so a missing value fails at startup.
6. Neither function logs a token.

Hints: `uv add pyjwt`. `jwt.encode(claims, secret, algorithm="HS256")`;
`jwt.decode(token, secret, algorithms=["HS256"])` raises `jwt.InvalidTokenError` (the base class
covering expiry, signature, and malformed input) — catch that one and return `None`.
Use `datetime.now(timezone.utc)`, never `utcnow()`. Return claims as a small frozen dataclass or
Pydantic model rather than a raw dict, so `sub` — a string per the JWT spec, even though ids are
integers — is converted back to `int` in exactly one place.

**Tests:** a round trip returns the same user id; a token signed with a different secret returns
None; an expired token returns None; a tampered payload returns None; garbage returns None; two
refresh tokens differ; the hash is not the token.

**Verify:** `uv run pytest -v`.
**Commit:** `Add JWT and refresh token helpers`

---

## Task 7: Session crud and the login flow

**Files:**
- Create: `backend/src/tradinghub/auth/crud/session.py`,
  `backend/src/tradinghub/auth/services/sessions.py`,
  `backend/src/tradinghub/auth/schemas/session.py`,
  `backend/tests/auth/services/test_sessions.py`

**Interfaces produced:**
```python
# crud/session.py — queries only, never commits
async def get_session_by_token_hash(db, hashed_refresh_token: str) -> Session | None: ...
async def create_session(db, *, user_id: int, family_id: uuid.UUID,
                         hashed_refresh_token: str, expires_at: datetime) -> Session: ...
async def mark_session_used(db, session: Session) -> None: ...
async def revoke_family(db, family_id: uuid.UUID) -> None: ...
async def revoke_session(db, session: Session) -> None: ...

# services/sessions.py
@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str

async def login(db, email: str, raw_password: str) -> TokenPair | None
async def refresh(db, refresh_token: str) -> TokenPair | None
async def logout(db, refresh_token: str) -> None
```

**Requirements:**
1. `login` returns `None` for both an unknown email and a wrong password, and takes the same time
   in each case — verify against a fixed dummy hash when the user is absent, exactly as the
   auth-skeleton spec requires. An early `return` on "no such user" is an enumeration oracle.
2. `login` starts a new family: `family_id` is a fresh UUID equal to nothing else.
3. `refresh` returns `None` when the token is unknown, expired, or already used.
4. **When the presented token has a non-null `used_at`, revoke the entire family before returning
   `None`.** This is reuse detection and it is the reason the design is safe.
5. A successful `refresh` marks the presented session used and inserts a successor row carrying the
   **same** `family_id`.
6. The raw refresh token is never persisted and never logged — only its hash.
7. `logout` deletes the session for that token. An unknown token is not an error.
8. Nothing in this module commits; `get_db` owns the transaction.

Requirement 4 is the one to write a test for first. The natural implementation returns `None` on a
used token without revoking anything, which looks correct, passes an obvious test, and leaves a
stolen token usable until it expires.

**Tests:** login returns a pair for correct credentials and None for both failure modes with
matching timing; refresh rotates and the old token then fails; **replaying a used token revokes the
family, so a sibling token issued from the same login also stops working**; an expired refresh
token fails; logout makes the token fail; a forged token fails.

**Verify:** `uv run pytest -v`.
**Commit:** `Add session lifecycle with refresh rotation`

---

## Task 8: Endpoints and the current-user dependency

**Files:**
- Create: `backend/src/tradinghub/auth/dependencies.py`, `backend/tests/auth/test_login.py`
- Modify: `backend/src/tradinghub/auth/routes.py`, `backend/src/tradinghub/core/config.py`

**Interfaces produced:**
```python
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/auth/refresh"

async def get_current_user(request: Request) -> CurrentUser: ...
# raises AppError("invalid_credentials", 401) when the access token is absent or invalid
```

**Requirements:**
1. `POST /auth/login` returns 200 with `{id, email}` and sets both cookies.
2. `POST /auth/refresh` returns 204 and sets both cookies. 401 on any failure.
3. `POST /auth/logout` clears both cookies and deletes the session, returning 204. It succeeds with
   no valid session — logout is never an error.
4. `GET /auth/me` returns `{id, email}` for a valid access token, 401 otherwise.
5. Both cookies are `HttpOnly`, `SameSite=Lax`, `Secure` from `settings.cookie_secure`, with
   `domain` from `settings.cookie_domain` when set. The refresh cookie uses `Path=/auth/refresh`.
6. `delete_cookie` must be given the same `path` and `domain` as `set_cookie`, or the browser keeps
   the original.
7. **`get_current_user` performs no database query.** It decodes the access token and builds the
   caller's identity from the claims. A route that needs the full `User` row queries for it
   explicitly.

Requirement 7 is the whole point of the design and the easiest thing to undo by accident. Returning
a `User` from `get_current_user` invites `Depends(get_current_user)` everywhere and a query per
request, at which case sessions would have been simpler. Return a small `CurrentUser` value object
holding `user_id` and `session_id` so the distinction is visible at the call site.

`GET /auth/me` therefore does query — it returns an email, which is not in the token. That is fine
and deliberate: it is one endpoint, not every endpoint.

**Tests:** login sets two HttpOnly cookies and the refresh one is scoped to `/auth/refresh`; wrong
password and unknown email are byte-identical 401s; `/auth/me` needs a token; a forged token is
rejected; a token signed with the wrong secret is rejected; logout clears cookies **and** drops the
row; refresh issues a working new access token; **an access token still works for its remaining
lifetime after logout, and the test says so explicitly** so the revocation gap is documented in
code rather than discovered later.

**Verify:** `uv run pytest -v`.
**Commit:** `Add login, refresh, logout, and the current-user dependency`

---

## Downstream changes

**Task 9 (rate limiting, was Task 7):** unchanged. It counts failed login attempts and does not
care what a success issues. Consider rate limiting `/auth/refresh` too — a stolen refresh token
being ground against reuse detection is worth slowing down.

**Task 12 (API client, was Task 9):** `lib/api.ts` must, on a 401, call `POST /auth/refresh` once
and replay the original request; if the refresh also fails, redirect to login. Put it in one
wrapper, never at call sites. Guard against a refresh storm: concurrent 401s should await a single
in-flight refresh rather than firing one each.

**`spec.md` of the auth-skeleton slice:** its "The cookie" table and the `get_current_user`
paragraph are superseded by this folder. Leave the file as the historical record; this plan is the
current one.
