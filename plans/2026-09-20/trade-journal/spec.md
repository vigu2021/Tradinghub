# Trade journal

Slice 3. A signed-in user can record, list, edit, close, and delete their own trades. Manual entry
only.

A trade belongs to an account, so this slice sits on top of slice 2's accounts and transactions. It
was originally specced as slice 2 and reordered once money came first: building it earlier would
have meant adding `account_id` later with a migration and a backfill.

**In one line:** one table, five endpoints, three pages.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| What one row is | A round trip: one position from open to close | It is how a person reviews trading. Slice 3's raw fills get their own table with a foreign key to the trade they were folded into, so this table does not change when the import arrives |
| Scaling in and out | Entered as an average price | Exact legs are slice 3's fills. Modelling them now would be building slice 3's data model a slice early |
| Money | `NUMERIC(20, 8)` in Postgres, `Decimal` in Python, strings in JSON and in the browser | A float cannot represent 0.1. Eight places matches Binance's precision |
| P&L | Computed from the row, never stored | A stored copy goes stale the moment a trade is edited |
| Symbol | One string, `BTCUSDT` or `AAPL` | Binance reports pairs that way, so slice 4 imports them unchanged, and the same column holds a stock ticker |
| Currency | An explicit column, not inferred from the symbol | `BTCUSDT` encodes its quote currency; `AAPL` encodes nothing. Once one journal holds both, a P&L of `+312.40` is ambiguous without it |
| Which account | `account_id`, a required foreign key to slice 2's `accounts` | A trade is money in a particular place. It also lets slice 5 report trading performance per account |
| Fees | One total per trade | Entry and exit fees are not reviewed separately |
| Tags | A Postgres text array on the row | One table instead of three. Renaming a tag everywhere becomes an `UPDATE`, which is rare in a personal journal |
| Delete | Hard delete | Nothing references a trade yet |
| Primary key | Integer, per `CONVENTIONS.md` | Ids are guessable, so the ownership rule below is the only protection a trade has |
| Create and edit UI | Separate pages, one shared form | Linkable, and the Back button works. A slide-over needs focus trapping and URL syncing to do properly |
| Paging | `limit` and `offset`, response carries `total` | A journal holds thousands of rows, and a paged table needs the total anyway |
| Backend package | `journal/`, flat files | What the conventions table prescribes. `auth/` grew subpackages because it has several models and a security layer; one model does not need them |

## The ownership rule

Every query against `trades` filters by the signed-in user's id, and the filter lives in the data
access functions, which take `user_id` as a required argument. A route cannot forget it because it
cannot call them without it.

A trade that belongs to someone else answers **404 `trade_not_found`**, identical to one that does
not exist. Never 403: that would confirm the id is real.

This is tested for every endpoint from the first commit, with two accounts: B cannot read, change,
or delete A's trade, and A's trades never appear in B's list.

## Data model

One new table. One Alembic revision.

| Column | Type | Rule |
|---|---|---|
| `id` | integer | primary key |
| `user_id` | integer | foreign key to `users.id`, `ON DELETE CASCADE`, not null |
| `account_id` | integer | not null; with `user_id`, a composite foreign key to `accounts`, the same shape slice 2 uses for transactions |
| `symbol` | text | not null, stored uppercase |
| `currency` | text | not null, 3 to 5 characters, uppercase. What the P&L is denominated in |
| `side` | text | not null, `long` or `short` |
| `quantity` | numeric(20, 8) | not null, greater than zero |
| `entry_price` | numeric(20, 8) | not null, greater than zero |
| `entry_at` | timestamptz | not null |
| `exit_price` | numeric(20, 8) | null while open, greater than zero when set |
| `exit_at` | timestamptz | null while open |
| `fees` | numeric(20, 8) | not null, default 0, not negative |
| `notes` | text | nullable |
| `tags` | text[] | not null, default empty |
| `created_at` | timestamptz | not null, set by the database |
| `updated_at` | timestamptz | not null, set by the database on every update |

**Check constraints**, named through the existing naming convention so Alembic can alter them:

- `side` is one of the two values. A check rather than a Postgres `ENUM`, because adding a value to
  an enum type is a migration with sharp edges and a check is one line to change.
- `exit_price` and `exit_at` are both null or both set. A trade is open or closed; half-closed
  cannot be stored.
- `exit_at` is not before `entry_at`.
- the positivity rules in the table above.

**One index:** `(user_id, entry_at DESC)`, for "my trades, newest first". No index on `symbol` or
`tags`: both filters run inside one user's rows, which the index above already narrows to a few
thousand at most. Add one when a query plan asks for it.

In Python, `side` is a `StrEnum` and the model uses `Mapped[Decimal]`.

## P&L

A pure function in `journal/pnl.py`, tested on its own:

```
long:   (exit_price - entry_price) * quantity - fees
short:  (entry_price - exit_price) * quantity - fees
open:   None
```

`Decimal` arithmetic throughout, quantised to eight places. The API returns it; the frontend never
computes it.

## API

All five require a session through the existing `get_current_user` dependency.

| Method and path | Does | Success | Failures |
|---|---|---|---|
| `POST /trades` | create, open or already closed | 201, the trade | 422 |
| `GET /trades` | list own trades, `entry_at` descending then `id` descending | 200, a page | 422 on a bad query parameter |
| `GET /trades/{id}` | one trade | 200 | 404 |
| `PATCH /trades/{id}` | change any subset of fields | 200, the updated trade | 404, 422 |
| `DELETE /trades/{id}` | remove | 204 | 404 |

**A trade in a response** carries every column except `user_id`, plus `status` (`open` or `closed`)
and `pnl` (a decimal string, or null while open). Decimals are strings: `"0.00012345"`.

**Closing a trade is a PATCH** that sets `exit_price` and `exit_at`. There is no close endpoint.
Reopening is a PATCH that sets both to null.

**The rules are checked against the trade as it would be after the change.** A PATCH carrying only
`exit_price` on an open trade is a 422, because the merged result is half-closed. Create and update
share one rule function so they cannot drift. The database constraints are the last line, not the
first: a violation that reaches them is a bug, and surfaces as a 500.

**Input rules**

- `symbol`: 2 to 20 characters, letters and digits, uppercased on the way in. The form offers
  symbols already used, so `BTCUSD` and `BTCUSDT` do not silently split a filter.
- `currency`: uppercased, 3 to 5 letters. The form defaults it from the last trade with the same symbol.
- `account_id`: must be one of the caller's accounts, or 404.
- decimals: at most 20 digits, 8 after the point. Accepted as strings or numbers, returned as strings.
- timestamps: ISO 8601 with an offset. A naive timestamp is a 422, never a guess at the timezone.
- `tags`: at most 10, each 1 to 30 characters, trimmed, lowercased, deduplicated.
- `notes`: at most 5,000 characters.

**List query parameters**

| Parameter | Meaning | Default |
|---|---|---|
| `limit` | page size, 1 to 200 | 50 |
| `offset` | rows to skip, 0 or more | 0 |
| `symbol` | exact match, case-insensitive | none |
| `status` | `open` or `closed` | none |
| `tag` | trades whose tags contain it | none |

The response is `{ "items": [...], "total": n }`, where `total` counts every row matching the
filters, not just the page.

**Errors.** One new code, `trade_not_found` (404), declared like the auth errors. Invalid input
uses the existing `validation_error` (422), which deliberately reports only that validation failed.
The frontend form enforces the same rules first, so a user sees field-level messages there.

## Backend structure

```
backend/src/tradinghub/journal/
├── models.py      # Trade, TradeSide
├── schemas.py     # TradeCreate, TradeUpdate, TradeResponse, TradePage, TradeFilters
├── crud.py        # every function takes user_id; the only place trades are queried
├── services.py    # create, update with the merged-state check, delete
├── pnl.py         # the pure P&L function
├── errors.py      # TradeNotFoundError
└── routes.py      # the five endpoints
```

Layering is slice 1's: routes call services, services call `crud`. Routes stay thin adapters.
Public functions above private helpers, per the conventions. `tests/journal/` mirrors it file for
file. `alembic/env.py` gains the model import, and `main.py` includes the router.

## Frontend

Three pages under `(app)`, so the layout guards them and each reads the user through
`useAuthenticatedUser()`.

| Page | Shows |
|---|---|
| `/trades` | a table, newest first: symbol, side, quantity, entry, exit, P&L, status, tags. Filters for symbol, status, tag. Page controls. A "New trade" button. An empty state for a journal with no trades |
| `/trades/new` | the trade form, empty |
| `/trades/[id]` | the same form, filled in, and a Delete button with a confirm step |

The header gains a "Trades" link. `/dashboard` and the post-login redirect do not change, so no
existing test moves. Slice 4 owns the dashboard.

```
frontend/src/features/trades/
├── api.ts         # the five calls, tradeKeys, response parsing
├── hooks.ts       # useTrades, useTrade, useCreateTrade, useUpdateTrade, useDeleteTrade
├── types.ts       # zod schemas: the form, the trade, the page
└── components/    # TradeForm, TradeTable, TradeFilters
```

**The form** is React Hook Form with a zod schema carrying the same rules as the API: exit price
and time both filled or both empty, exit not before entry, the decimal and tag limits. Times are
entered in the browser's local zone and sent with their offset.

**Decimals stay strings.** The browser never does arithmetic on money. It formats for display.

**Mutations invalidate, they do not patch the cache.** Create, update, and delete invalidate every
trade list. A list is filtered and paged, so working out which cached pages a change belongs on is
more code than refetching.

### Carried in from the slice 1 review

These waited for this slice because this is where they start to matter.

- **Query keys as a factory:** `tradeKeys.all`, `tradeKeys.list(filters)`, `tradeKeys.detail(id)`,
  so one call invalidates every list. `authKeys` takes the same shape.
- **Responses are parsed with zod in `api.ts`,** not just asserted with a type parameter. A trade
  carries decimals, nulls, and timestamps, where a silent mismatch shows up as `undefined` on screen.
- **Trade queries set their own stale time,** shorter than the global two minutes.
- **The error banner becomes a component.** It is copy-pasted three times and would be five.
- **`noUncheckedIndexedAccess`** goes on in `tsconfig.json` before the first list is written.
- **`CONVENTIONS.md` gets its frontend section,** recording the decisions above, and notes that
  `journal/` is flat where `auth/` is not, and why.

## Testing

**Backend**, against real Postgres in the rolled-back transaction fixture:

- ownership, for all five endpoints, with two accounts
- P&L: long, short, fees, a losing trade, an open trade, eight-place precision
- the merged-state rule: PATCH with one exit field, closing, reopening, exit before entry
- the database constraints themselves, by writing a bad row past the application
- input rules: naive timestamp, lowercase symbol normalised, too many tags, negative fees
- list: ordering, each filter, filters combined, `total` against a page, `limit` bounds
- a failed create leaves no row, using the fixture that now rolls back like production

**Frontend**, Playwright against the live API:

- create a trade and see it in the list
- close it and see its P&L
- edit it, delete it with the confirm step
- filter by status
- the form refuses a half-closed trade before reaching the server, asserted on the request log
- the empty state

Each test must fail with its behaviour removed. Slice 1's review found tests that did not, and the
plan checks each new one the same way.

**Postman:** a Trades folder joins the existing collection.

## Out of scope

| Left out | Where it goes |
|---|---|
| Account balances, deposits, withdrawals | Slice 2, already built. A trade's P&L does not post a transaction: the balance query adds closed-trade P&L to the ledger sum, so there is no second copy to keep in sync |
| A table for Binance API keys | Slice 4. It holds a read-only key and its secret, encrypted at rest, one row per user. Nothing in this slice would read it |
| Fills, partial exits, a `source` column marking manual entry from imported | Slice 4's own migration. The `source` column is what stops the importer overwriting a trade typed by hand |
| Statistics, equity curve, per-symbol breakdowns, date ranges | Slice 5, a read layer over this table |
| Leverage, spot versus futures, stop loss, target, screenshots, a rating | When a real need appears. Tags and notes carry them until then |
| Sorting options, inline editing, bulk actions, CSV, tag autocomplete | Not needed to keep a journal |
| Pruning spent session rows, the silent API URL fallback | Slice 6, with deployment |

## Done when

- a user can create, list, filter, page through, edit, close, reopen, and delete their own trades in the browser
- no request can read or change another user's trade, proven per endpoint
- P&L is right to eight places for longs and shorts, and absent for open trades
- the backend suite, the Playwright suite, ruff, basedpyright, tsc, eslint, and prettier all pass
- `alembic upgrade head` builds the schema from scratch and `alembic check` reports no drift
