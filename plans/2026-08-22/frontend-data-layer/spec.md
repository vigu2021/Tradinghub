# Frontend data layer

**Goal:** one place the browser talks to the API, one place types live, one place server state is
cached. Everything Phase 2 builds on, and everything slice 2's trade journal inherits without
redesign.

**Scope:** the data layer, the auth forms that exercise it, and the project structure that holds
both. Not the visual design, not the protected-route middleware, not the Playwright test.

**Depends on:** the auth API from `plans/2026-08-09/jwt-auth/`, shipped and tested: five endpoints,
cookie sessions, refresh rotation with reuse detection, `{"error": {"code", "message"}}` on every
failure.

---

## Decisions

| Question | Decision | Why |
|---|---|---|
| Types | Hand-written, mirroring Pydantic | Small surface, and writing them is part of learning the stack |
| Transport | axios | Interceptors are the natural home for the 401 retry; throws on non-2xx |
| Server state | TanStack Query | Slice 2 is CRUD: lists, mutations, invalidation |
| Client state | None | With cookie auth there is nothing left for a store to hold |
| Errors | One `ApiError` class + code constants | Three branches in the UI; a hierarchy would cost a registry for no gain |
| Forms | React Hook Form, no zod | Two fields each; zod earns itself at the trade form's cross-field rules |
| Structure | Feature-first | Mirrors the backend's `auth/` grouping |

Three of these are trades rather than wins, and are worth recording as such.

**Hand-written types** means nothing enforces the mirror. A renamed Pydantic field leaves the
frontend compiling and failing at runtime, and the Playwright e2e is the only thing that will
notice. Renaming a backend response field is a two-file change by convention. Generating from
`/openapi.json` remains available if the drift ever bites.

**axios over `fetch`** buys ergonomics for about 13kB: interceptors, automatic JSON, and throwing on
non-2xx. `fetch` is native and needs none of it. A deliberate purchase, not a default.

**No Zustand.** With cookie auth, "am I signed in" is `/auth/me` — server state, owned by Query.
Filters belong in URL search params so they survive a refresh. A store holding the current user
would be a second source of truth that disagrees with the server the moment a session is revoked.

---

## Structure

```
frontend/src/
├── app/                          routing only — thin pages that compose features
│   ├── layout.tsx                mounts QueryProvider
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   └── (app)/
│       └── dashboard/page.tsx
├── features/
│   └── auth/
│       ├── api.ts                endpoint functions and query keys
│       ├── hooks.ts              useUser, useLogin, useLogout, useRegister
│       ├── types.ts              mirrors of the auth Pydantic schemas
│       ├── validation.ts         field rules shared by the two forms
│       └── components/           LoginForm, RegisterForm
├── lib/
│   ├── api/
│   │   ├── client.ts             axios instance and interceptors
│   │   └── errors.ts             ApiError, NetworkError, API_CODES
│   └── query-provider.tsx
└── components/ui/                Button, Input, Field — when they earn themselves
```

Three rules keep it from rotting:

1. **`app/` is thin.** A page is a route, a layout, and composition. No fetching logic, no forms
   defined inline. A page file past a screenful means its contents belong in the feature.
2. **Features never import each other.** What two features share moves down to `lib/` or
   `components/ui/`, never sideways. Sideways imports are how a cycle appears that cannot be
   unpicked later.
3. **Imports flow one way.** `app/` → `features/` → `lib/`. Never the reverse.

The test of the structure is slice 2: trade journal CRUD becomes `features/trades/` with the same
files plus a page. A new feature is a new directory, not edits across five layers.

---

## The client

One axios instance, `withCredentials: true`. Without that flag the browser neither sends nor stores
the cookies and every request is anonymous — it is the single most common reason a cookie-auth
frontend "mysteriously" stays logged out.

One response interceptor does two jobs.

### Normalising failures

An `AxiosError` becomes an `ApiError` when the server answered with the error envelope, or a
`NetworkError` when the request never completed. A response that has a status but not the envelope
is also a `NetworkError`: a proxy or gateway answers in its own shape, and pretending otherwise
means reading `undefined.code` in a catch block.

Nothing outside `lib/api` sees an axios type. That is what makes replacing the transport a one-file
change.

### The 401 retry

Retry once, but **only when `code === "invalid_session"`**.

A wrong password at the login form is also a 401. Refreshing there is pointless work on every typo
and spends a rotation nobody asked for. Splitting `InvalidCredentialsError` from
`InvalidSessionError` on the backend is what makes this a one-line condition rather than a path
allowlist someone forgets to update.

Two guards: never retry the refresh call itself, or a failing refresh recurses into itself; never
retry a request twice.

### One rotation at a time

A refresh token is single use. Concurrent 401s must await the same rotation. Five parallel requests
each starting their own means four replay a token the first already spent, the server reads that as
theft, and it revokes the family — the client logging itself out by tripping the server's own alarm.

This is the subtlest code in the layer.

### What the interceptor does not do

It does not redirect. Navigation is a UI concern and an interceptor cannot reach `next/navigation`
anyway. A failed refresh surfaces as `ApiError` with code `invalid_session`; the page-level redirect
belongs in `middleware.ts`, which is out of scope here.

---

## Query wiring

The `QueryClient` is created inside `useState(() => new QueryClient())`, never at module scope. A
module-level client is shared across requests on the server and leaks one user's cache into
another's response.

Defaults set once: retry a flaky connection but never an `ApiError` — a 401 or a 422 is the server's
decision, not a blip — and a short `staleTime` on the current user.

Login seeds the cache with the user it received; logout clears the whole cache, so no data outlives
the account that fetched it.

---

## Forms

React Hook Form, rules in one shared object keyed by autocomplete value: `email`,
`currentPassword`, `newPassword`.

The asymmetry is deliberate and belongs in a comment: register enforces the 8-character minimum,
login enforces no length rule at all, mirroring `LoginRequest` having no `Field(min_length=...)`.
Rejecting a short password client-side would tell an attacker the password is too short to be real
— the same leak the 401 exists to prevent.

The email pattern is deliberately loose. `EmailStr` on the server is the authority, and a clever
regex rejects addresses that are valid.

`RegisterForm` has no "email already taken" branch: the backend answers 201 either way, so there is
nothing to branch on and everyone lands on the login page.

---

## Testing

No unit test framework. Vitest and MSW are a toolchain for one module, and the flows are covered by
the Playwright e2e in Task 12.

**The known gap:** the single-flight rotation guard is the subtlest code here and nothing tests it.
Task 12 should include an e2e that expires the access token and fires several requests at once,
asserting exactly one refresh reaches the server. If that proves too fiddly in Playwright, add
Vitest for that one function rather than leave it unverified — the failure mode is the client
revoking its own session, and it will not reproduce on a developer machine making one request at a
time.

---

## Out of scope

Visual design and the shared UI primitives beyond their names. `middleware.ts`. The Playwright e2e
itself. Login rate limiting, deferred in `plans/2026-08-08/auth-skeleton/plan.md` until after
Phase 2.
