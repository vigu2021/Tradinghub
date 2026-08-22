# Frontend data layer — implementation plan

**Spec:** `plans/2026-08-22/frontend-data-layer/spec.md` — read it first. This plan implements it and
does not restate its rationale.

**Tech:** Next.js 16.3 (App Router, Turbopack), React 19, TypeScript, Tailwind 4, axios, TanStack
Query v5, React Hook Form.

---

## How to use this plan

**You write the implementation.** Each task gives you the interfaces so later tasks line up
with earlier ones, numbered requirements you can check one at a time, the exact command to verify,
and hints for the library calls that would otherwise cost twenty minutes of searching. Looking up an
API is not learning; deciding what to do with it is.

Mechanical configuration appears verbatim, because there is nothing to learn from retyping it.

Every task ends green: `npx tsc --noEmit`, `npx eslint src`, and `npm run build` all pass before you
move on. Run them from `frontend/`.

**A warning specific to this stack:** `frontend/AGENTS.md` exists because Next 16 broke conventions
from 13 and 14. Most tutorials you find target the old versions. The bundled docs in
`node_modules/next/dist/docs/` are the authority.

---

## Task 1: Dependencies and the environment file

**Files:**
- Modify: `frontend/package.json`, `frontend/.gitignore`
- Create: `frontend/.env.local`, `frontend/.env.local.example`

**Steps:**

```bash
cd frontend
npm install axios @tanstack/react-query react-hook-form
npm install -D @tanstack/react-query-devtools
```

`.env.local.example`, committed:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Copy it to `.env.local`, which is not committed. `NEXT_PUBLIC_` is required for the browser to see
the value. Only ever put non-secret values behind that prefix — anything with it is compiled into
the JavaScript bundle and is fully public.

**Requirements:**
1. `.gitignore` must stop ignoring the example. Next's default has a blanket `.env*`, so add
   `!.env.local.example` beneath it, or the file you are meant to commit stays invisible.

**Verify:** `git status` shows `.env.local.example` as untracked and `.env.local` as ignored.

---

## Task 2: Error types

**Files:**
- Create: `frontend/src/lib/api/errors.ts`

**Interfaces produced:**
```typescript
export const API_CODES: {
  invalidCredentials: "invalid_credentials";
  invalidSession: "invalid_session";
  validation: "validation_error";
  internal: "internal_error";
};

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
}
export class NetworkError extends Error {}

export function messageFor(error: unknown): string;
```

**Requirements:**
1. `API_CODES` carries exactly the codes the backend emits. Check them against
   `backend/src/tradinghub/core/errors.py` and `backend/src/tradinghub/auth/errors.py` rather than
   trusting this list — if they disagree, the backend is right.
2. `ApiError` is thrown when the server answered with its envelope. `NetworkError` when it did not:
   no status and no code, because there genuinely are none.
3. `messageFor` turns any thrown value into a line a user can read. An `ApiError` already carries a
   message written for users, so return it. Anything else gets a generic line — never `String(error)`,
   which puts stack-trace fragments on screen.

**Hints:**
- `as const` on the codes object gives you literal types instead of `string`.
- Subclassing `Error` in TypeScript: call `super(message)` first, then set `this.name`, or the name
  in a stack trace stays `"Error"`.

**Verify:** `npx tsc --noEmit`.

---

## Task 3: The axios client

The heart of the layer. Take your time here.

**Files:**
- Create: `frontend/src/lib/api/client.ts`

**Interfaces produced:**
```typescript
export const apiClient: AxiosInstance;
```

**Requirements:**
1. One instance from `axios.create`, with `baseURL` from `process.env.NEXT_PUBLIC_API_URL` and
   **`withCredentials: true`**. Without that flag the browser neither sends nor stores cookies, and
   every request looks anonymous — the most common cause of a cookie-auth frontend that silently
   never signs in.
2. A response interceptor converts every `AxiosError` into an `ApiError` or a `NetworkError`.
   Nothing outside this file may see an axios type.
3. A response with a status but without the `{error: {code, message}}` envelope is a `NetworkError`,
   not an `ApiError` with undefined fields. Proxies and gateways answer in their own shape.
4. **On `invalid_session` only**, rotate the session once and replay the original request. Not on
   every 401: a wrong password is also a 401, and refreshing there spends a rotation on every typo.
5. Never retry the refresh call itself, and never retry a request twice. Mark the config.
6. **Concurrent 401s share one rotation.** This is requirement 4's real difficulty and the one to
   get right — see below.
7. The interceptor never redirects. It throws; navigation belongs to the UI.

Requirement 6 is the one to think hardest about. A refresh token is single use. If five requests
401 at once and each starts its own rotation, four of them replay a token the first already spent —
which your backend correctly reads as theft and answers by revoking the entire family. The client
logs itself out by tripping the server's own alarm. It will not reproduce on your machine making
one request at a time, and it will happen the first time a real page fires three queries on mount.

The shape that solves it: a module-level `Promise | null` holding the rotation in flight. Callers
that arrive while it is set await the same promise; it is cleared when the rotation settles.

**Hints:**
- `axios.isAxiosError(error)` is the type guard. The rejection handler receives `unknown`.
- `error.response` is `undefined` when the request never completed.
- `apiClient.request(config)` replays a request from its config.
- To mark a config as retried, widen the type:
  `type Retriable = InternalAxiosRequestConfig & { retried?: boolean }`.
- `interceptors.response.use(null, handler)` when you only care about failures.
- `??=` assigns only when the left side is nullish — exactly the "start one if none is running"
  shape.
- A function returning `config is Retriable` lets you narrow once and use `config.retried` after,
  instead of repeating a null check.
- Six chained conditions inside an `if` is a smell. Give the rule a name.

**Verify:** `npx tsc --noEmit` and `npx eslint src`. Nothing exercises it yet — that comes in Task 8.

---

## Task 4: The Query provider

**Files:**
- Create: `frontend/src/lib/query-provider.tsx`
- Modify: `frontend/src/app/layout.tsx`

**Interfaces produced:**
```typescript
export function QueryProvider({ children }: { children: ReactNode }): JSX.Element;
```

**Requirements:**
1. `"use client"` at the top. A provider holds state, so it cannot be a Server Component.
2. **Create the `QueryClient` inside `useState(() => new QueryClient())`, never at module scope.**
   A module-level client is shared across requests on the server, which leaks one user's cached
   data into another user's response. This is a real vulnerability, not a style preference.
3. Retry a flaky connection, never an `ApiError`. A 401 or a 422 is the server's decision, and
   asking three times changes nothing.
4. A `staleTime` of about 30 seconds, so moving between pages does not refetch the user constantly.
5. Mount it in `app/layout.tsx` wrapping `{children}`, inside `<body>`.
6. Add `<ReactQueryDevtools />` inside the provider. It is excluded from production builds
   automatically, and it is the fastest way to see what the cache is actually doing while you learn.

**Hints:**
- `useState(() => new QueryClient())` — pass the *function*, not `useState(new QueryClient())`. The
  second one constructs a client on every render and throws them away.
- The retry option is `retry: (failureCount, error) => boolean`.
- Defaults go in `new QueryClient({ defaultOptions: { queries: {...}, mutations: {...} } })`.

**Verify:** `npm run dev`, load `localhost:3000`, and confirm the devtools flower appears in the
corner.

---

## Task 5: Auth types and endpoint functions

**Files:**
- Create: `frontend/src/features/auth/types.ts`, `frontend/src/features/auth/api.ts`

**Interfaces produced:**
```typescript
// types.ts — each type carries a comment naming its Pydantic source
export type User = { id: number; email: string };
export type LoginRequest = { email: string; password: string };
export type RegisterRequest = { email: string; password: string };

// api.ts
export const authKeys: { me: readonly ["auth", "me"] };
export function login(body: LoginRequest): Promise<User>;
export function register(body: RegisterRequest): Promise<void>;
export function logout(): Promise<void>;
export function getCurrentUser(): Promise<User>;
```

**Requirements:**
1. Read the real schemas before writing the mirrors:
   `backend/src/tradinghub/auth/schemas/`. Each type gets a comment naming the model it mirrors,
   because nothing else connects them.
2. These are plain async functions. No hooks, no React — that keeps them callable from anywhere and
   makes Task 6 trivial.
3. `register` and `logout` return `void`: the backend answers 201 and 204 with empty bodies.
4. Query keys live here, next to the functions that fill them, so a key is never spelled twice.

**Hints:**
- `apiClient.post<User>("/auth/login", body)` returns `{ data }`. Return `data`, not the response —
  the axios response type must not escape `lib/api`.
- `as const` on the key array gives TanStack Query a literal tuple type.

**Verify:** `npx tsc --noEmit`.

---

## Task 6: Auth hooks

**Files:**
- Create: `frontend/src/features/auth/hooks.ts`

**Interfaces produced:**
```typescript
export function useUser(): UseQueryResult<User>;
export function useLogin(): UseMutationResult<User, Error, LoginRequest>;
export function useRegister(): UseMutationResult<void, Error, RegisterRequest>;
export function useLogout(): UseMutationResult<void, Error, void>;
```

**Requirements:**
1. `"use client"`.
2. `useUser` is a `useQuery` over `authKeys.me` and `getCurrentUser`. It will reject for a signed-out
   visitor, which is correct — but note the client rotates an expired session first, so someone
   returning after 20 minutes is signed back in without noticing.
3. `useLogin` writes the returned user straight into the cache with `setQueryData(authKeys.me, user)`.
   The header then updates with no second round trip.
4. `useLogout` calls `queryClient.clear()`. Invalidating only `authKeys.me` would leave the previous
   account's trades sitting in the cache for the next person to sign in on that browser.
5. `useRegister` touches no cache: registering deliberately signs nobody in.

**Hints:**
- `useQueryClient()` inside the hook, not a module-level client.
- Mutations take `mutationFn`; `onSuccess` receives the value it resolved with.

**Verify:** `npx tsc --noEmit`.

---

## Task 7: Validation rules and the two forms

**Files:**
- Create: `frontend/src/features/auth/validation.ts`,
  `frontend/src/features/auth/components/LoginForm.tsx`,
  `frontend/src/features/auth/components/RegisterForm.tsx`

**Interfaces produced:**
```typescript
export const MIN_PASSWORD_LENGTH = 8;
export const rules: {
  email: RegisterOptions;
  currentPassword: RegisterOptions;   // login
  newPassword: RegisterOptions;       // register
};

export function LoginForm(): JSX.Element;
export function RegisterForm(): JSX.Element;
```

**Requirements:**
1. **Login enforces no password length rule; register enforces 8 characters.** This asymmetry is
   deliberate and needs a comment saying so, or someone will "fix" it by copying the register rule
   across. Rejecting a six-character password at the login form tells an attacker it is too short to
   be a real password — the leak the identical 401 exists to prevent.
2. The email pattern is deliberately loose. `EmailStr` on the server is the authority; a clever
   regex rejects addresses that are valid.
3. Both forms use `useForm<T>()` with the request type as the generic, so field names are checked
   against your own types.
4. `noValidate` on the `<form>`: React Hook Form owns validation now, and two validators fighting
   produces two different error styles for the same mistake.
5. Field errors render per field. The server error renders once, near the submit button.
6. Disable the submit button while the mutation is pending, and say so in its label.
7. `RegisterForm` has no "email already taken" branch. The backend answers 201 either way — there is
   nothing to branch on, and everyone lands on `/login`.
8. `LoginForm` renders one message for every failure. Do not try to be more specific: the server
   answers wrong-password and unknown-email identically on purpose.
9. Accessibility, which is cheap now and expensive later: every input has a `<label htmlFor>`, error
   text carries `role="alert"`, invalid fields carry `aria-invalid`.

**Hints:**
- `{...register("email", rules.email)}` spreads the field's props onto the input.
- `handleSubmit(values => ...)` returns the submit handler and calls `preventDefault` for you.
- Field errors are `formState.errors.email?.message`.
- Mutation state is `isPending` in v5, not `isLoading`.
- `mutate(values, { onSuccess })` for per-call navigation, keeping the hook free of routing.
- `useRouter` comes from `next/navigation`, never `next/router`, in the App Router.

**Verify:** `npx tsc --noEmit`, `npx eslint src`, `npm run build`.

---

## Task 8: Pages, and clicking through it

**Files:**
- Create: `frontend/src/app/(auth)/login/page.tsx`,
  `frontend/src/app/(auth)/register/page.tsx`,
  `frontend/src/app/(app)/dashboard/page.tsx`
- Delete: the `.gitkeep` in each of those directories

**Requirements:**
1. Each page is thin: a heading, the form, a link to the other page. No fetching, no form logic.
2. The dashboard calls `useUser()` and shows the email, with something rendered while it is pending.
   It is not protected yet — `middleware.ts` is a later task — so signed out it will simply show its
   error state. That is expected at this point, not a bug to chase.
3. Styling is out of scope. Unstyled and working beats styled and broken; the design pass comes
   after this is verified end to end.

**Verify:** the whole point of the task.

```bash
docker compose up -d db
cd backend && uv run uvicorn --factory tradinghub.main:create_app --port 8000
cd frontend && npm run dev
```

Then in the browser, with devtools open on the Network tab:

1. Register at `/register` → lands on `/login`.
2. Sign in → lands on `/dashboard` showing your email.
3. Check Application → Cookies: `access_token` on `/`, `refresh_token` on `/auth`, both `HttpOnly`.
4. Sign in with a wrong password → one message, no cookies set.
5. Delete the `access_token` cookie by hand and reload the dashboard. You should see a 401, then a
   `POST /auth/refresh`, then the retried `/auth/me` succeeding. **That is the interceptor working**,
   and it is the single most satisfying thing to watch in this whole task.

**Commit:** `Add the frontend data layer and auth forms`

---

## Where this leaves you

`middleware.ts` and the protected-route redirect, the visual design pass, and the Playwright e2e —
including the concurrency test for the rotation guard that the spec flags as the known gap.
