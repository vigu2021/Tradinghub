# Ledger

Slice 2. A signed-in user records where their money is and every movement in or out of it, then
sees their balance and what they spent over any period.

This replaces the original slice 2, which was the trade journal. A trade belongs to an account, so
accounts have to exist first: building trades first would mean adding `account_id` later with a
migration and a backfill. It is also the better order to learn in, because accounts and
transactions are plain CRUD while trades carry P&L and a two-state lifecycle.

**In one line:** two tables, twelve endpoints, three pages.

## What it is for

Personal financial management, not a trading journal. Salary, rent, groceries, a subscription, a
deposit to an exchange, a withdrawal back out. Trading is one part of it and arrives in slice 3.

Three questions it answers, all arithmetic over one table:

- what is my balance, in each account and in total
- what did I spend this month, and on what
- what did I spend this week

## Decisions

| Decision | Choice | Why |
|---|---|---|
| The core shape | A signed-amount ledger: one row per movement, positive in, negative out | A new kind of spending is a new category, never a new table. This is the generic part, and it is small |
| Not double-entry | One row per movement against one account, not balanced debit and credit pairs | Double-entry is more correct and is what real accounting software does. It is also months of work and hard to make pleasant to use. This model can grow into it later without discarding anything |
| Accounts | A table. Named pots, each measured in one unit | "Total balance" is meaningless without knowing what is on the exchange versus in the bank. Adding it later would mean a migration on every transaction |
| `unit` rather than `currency` | One column holding `GBP`, `USDT`, `BTC`, or `AAPL` | A share is not a currency, so the honest name is the unit the balance is counted in. It also means a holding is just an account whose unit is not money, which is what lets a portfolio tracker land later with no change to these two tables |
| `kind` on a transaction | `income`, `expense`, `transfer` | Without it, expenses would have to mean "negative amounts", which counts moving money to an exchange as money spent. It is not |
| Transfers | Two equal and opposite rows sharing a group id, written by one endpoint | A transfer is two movements. The shared id means deleting one cannot orphan the other |
| Transfer fees | A third row, an expense, sharing the same group id | Making the two transfer rows uneven would hide the fee. Fees are spending and belong in the category breakdown |
| Account `type` | `cash`, `crypto`, or `stock`, a fixed set | Purely cosmetic, for grouping and icons. No balance depends on it |
| The amount sign | Applied by the service, not enforced by the database | The API takes a positive amount and a kind, so nobody types a minus sign to record rent. One function owns the convention, and one test holds it up |
| Categories | Free text, normalised, offered from ones already used | One table instead of two. Renaming becomes an `UPDATE`, which is rare. A table earns its place when budgets per category arrive |
| Many units | Balances are reported per unit and never summed across them | Adding USD to GBP, or GBP to BTC, needs prices and a price date. That is its own feature and its own table, not a column here |
| Money and quantities | `NUMERIC(36, 18)` in Postgres, `Decimal` in Python, strings in JSON and in the browser | A float cannot represent 0.1, and this is money. 18 decimals because an account's unit may be an Ethereum-style token, where 18 is the native precision. Widening later rewrites the table; widening now is free |
| Balances | Computed by summing transactions, never stored | A stored total goes stale the moment a row is edited. Same rule as P&L in slice 3 |
| Primary keys | Integer, per `CONVENTIONS.md` | Ids are guessable, so the ownership rule below is the only protection a row has |
| Package layout | `ledger/` with a `models/` subpackage | Two models, the same shape `auth/` already uses |

## The ownership rule

Unchanged from slice 1's lesson, and it now covers two tables.

Every query filters by the signed-in user's id, and the filter lives in the data access functions,
which take `user_id` as a required argument. A route cannot forget it because it cannot call them
without it.

Someone else's account or transaction answers **404**, identical to one that does not exist. Never
403: that would confirm the id is real.

**A transaction's account must belong to the same user.** The service checks it, and the database
enforces it too, through a composite foreign key: `transactions (account_id, user_id)` references
`accounts (id, user_id)`, which needs a redundant `UNIQUE (id, user_id)` on accounts. A bug in the
service then cannot write a transaction into a stranger's account, because Postgres refuses the
row. One extra constraint for a whole class of bug in the one place where it would be worst.

Tested for every endpoint from the first commit, with two accounts belonging to two users.

## Data model

Two tables. One Alembic revision.

### `accounts`

| Column | Type | Rule |
|---|---|---|
| `id` | integer | primary key |
| `user_id` | integer | foreign key to `users.id`, `ON DELETE CASCADE`, not null |
| `name` | citext | not null, 1 to 60 characters, trimmed |
| `unit` | text | not null, 2 to 10 characters, uppercase. `GBP`, `USDT`, `BTC`, `AAPL` |
| `type` | text | not null, `cash`, `crypto`, or `stock` |
| `created_at` | timestamptz | not null, set by the database |
| `updated_at` | timestamptz | not null, set by the database on every update |

- `UNIQUE (user_id, name)`: two accounts called Binance would be indistinguishable in a picker.
  `name` is `CITEXT`, the case-insensitive type `users.email` already uses, so "Chase" and "chase"
  collide in the database rather than relying on the application to lowercase them.
- `UNIQUE (id, user_id)`: redundant on its own, and the target of the composite foreign key above.
  Postgres will not create a foreign key over a pair of columns unless a constraint lists exactly
  that pair.
- `type` is checked against its three values. Stored as text rather than a Postgres enum type,
  because adding a value to an enum is a migration with sharp edges and a check is one line.

**There is no archiving.** An account is deleted or it is not. Deleting one that still has
transactions is refused by the service, so the cascade below only fires when a user is deleted.

### `transactions`

| Column | Type | Rule |
|---|---|---|
| `id` | integer | primary key |
| `user_id` | integer | not null; with `account_id`, a composite foreign key to `accounts` |
| `account_id` | integer | not null; see above |
| `amount` | numeric(36, 18) | not null, in the account's own unit. Positive is money in, negative is money out |
| `kind` | text | not null, `income`, `expense`, or `transfer` |
| `category` | text | nullable, 1 to 40 characters, lowercase |
| `occurred_at` | timestamptz | not null, when it happened rather than when it was typed |
| `note` | text | nullable, at most 1,000 characters |
| `transfer_group_id` | uuid | null unless this row is part of a transfer |
| `created_at` | timestamptz | not null, set by the database |
| `updated_at` | timestamptz | not null, set by the database on every update |

**There is one foreign key, and it covers both columns:** `(account_id, user_id)` references
`accounts (id, user_id)`, cascading on delete. Postgres therefore refuses any row whose account is
not that user's, whatever wrote it. No separate key to `users` is needed, because deleting a user
cascades to their accounts and from there to their transactions.

**One check constraint:** `kind` is one of the three values, generated from the enum. Deliberately
nothing else. The sign rule, the non-zero rule, and the category rules all live in the schema
layer, because a violation of any of them is either visible on screen or harmless to every total.
The sign rule is the one worth watching: without a constraint, the test that posts an expense and
asserts the stored amount is negative is the only thing holding it up.

**One index:** `(user_id, occurred_at)`. Every query in this slice starts by filtering to one user,
so `user_id` leads. Balances and category groupings run over the few thousand rows that index
already narrows to. Add another when a query plan asks for one, which is cheap: an index is the
only part of a schema that can be added later with no migration risk at all.

In Python, `kind` is a `StrEnum` and amounts are `Mapped[Decimal]`.

## API

All twelve require a session through the existing `get_current_user` dependency.

### Accounts

| Method and path | Does | Success | Failures |
|---|---|---|---|
| `POST /accounts` | create | 201 | 409 `account_name_taken`, 422 |
| `GET /accounts` | list own accounts with each balance, name ascending | 200 | |
| `GET /accounts/{id}` | one account with its balance | 200 | 404 |
| `PATCH /accounts/{id}` | rename, or change unit | 200 | 404, 409, 422 |
| `DELETE /accounts/{id}` | remove | 204 | 404, 409 `account_not_empty` |

**Deleting an account with transactions is refused.** The foreign key could cascade, but silently
destroying a year of records because a name was wrong is not a thing this app should do. Move or
delete the transactions first.

**Changing an account's unit is allowed but does not convert anything.** The amounts already
recorded keep their numbers and are simply now labelled differently. The API does not stop you, and
the UI warns.

### Transactions

| Method and path | Does | Success | Failures |
|---|---|---|---|
| `POST /transactions` | create an income or expense | 201 | 404 if the account is not yours, 422 |
| `GET /transactions` | list own, `occurred_at` descending then `id` descending | 200 | 422 |
| `GET /transactions/{id}` | one | 200 | 404 |
| `PATCH /transactions/{id}` | change any subset | 200 | 404, 409 on a transfer row, 422 |
| `DELETE /transactions/{id}` | remove; a transfer takes both halves | 204 | 404 |

**The list order needs both columns.** `occurred_at` alone is not a total order, since recording
two things on one day is normal. Paging over a non-deterministic order can show a row twice or skip
one entirely, so `id` is the tiebreaker, not decoration.

**`POST /transactions` refuses `kind = transfer`.** Transfers are created by their own endpoint, so
a half-transfer with no partner cannot exist.

**A transfer row cannot be patched**, answering 409 `transfer_not_editable`. Editing one half
consistently means rules about which fields propagate to the other, and the honest alternative is
one rule: delete it and record it again. This is a deliberate limit, written down so it is not
mistaken for an oversight.

**Deleting either half of a transfer deletes both.** They are one event.

### Transfers

| Method and path | Does | Success | Failures |
|---|---|---|---|
| `POST /transfers` | move money between two of your accounts | 201, both rows | 404, 422 |

The body is the source account, the destination account, the amount leaving, the amount arriving,
an optional fee with its category, when it happened, and an optional note. It writes every row in
one database transaction, sharing a new `transfer_group_id`.

**A fee is its own expense row**, in the same group, against whichever account was charged. The
two transfer rows stay equal and opposite so the fee cannot hide inside an uneven pair. Withdrawing
1,000 from a bank into an exchange that charges 5 is three rows: -1000 transfer, +1000 transfer,
-5 expense. The balances come to -1000 and +995, and the 5 appears in the spending breakdown.

**Both accounts must be yours, and they must differ.** They may have different currencies, and
nothing is converted. The amounts leaving and arriving are given separately, so a GBP account
sending 1,000 into a USDT account records -1000 and +1250. The exchange rate is not stored, because
it is one amount divided by the other.

**Equal and opposite is a same-unit rule only.** The service enforces it when both accounts share
a unit and must not when they differ, or the first exchange you record is rejected. Two rows with
different units are how a purchase is recorded: 30,000 USDT out of one account, 0.5 BTC into
another. Two rows with the same unit are a move, not a trade.

### Summary

| Method and path | Does | Success |
|---|---|---|
| `GET /summary?from=&to=` | balances now, plus totals for the period | 200 |

`from` and `to` are required ISO timestamps. The frontend computes this week and this month, so
the API stays a date range rather than a set of named periods, and slice 4 can ask it anything.

The response carries: each account with its balance, totals per unit, and for the period the
income total, the expense total, and expenses grouped by category, each per unit. Transfers are
excluded from the income and expense totals and included in balances.

**All of it is computed in SQL**, in a small number of aggregate queries rather than by summing in
Python. Grouping and filtering aggregates in one pass is the Postgres lesson of this slice.

### Input rules

- `name`: trimmed, 1 to 60 characters.
- `unit`: uppercased, 2 to 10 characters, letters and digits.
- `category`: trimmed, lowercased, 1 to 40 characters. Optional, so a purchase can be recorded
  before it is categorised. The breakdown groups those under "uncategorised".
- `amount`: sent as a positive number with a `kind`; the service applies the sign. At most 20
  digits, 8 after the point, never zero. Accepted as a string or a number, returned signed as a
  string.
- `type`: one of `cash`, `crypto`, `stock`.
- `occurred_at`: ISO 8601 with an offset. A naive timestamp is a 422, never a guess at the timezone.
- `note`: at most 1,000 characters.

### Errors

Four new codes, declared like the auth errors: `account_not_found` and `transaction_not_found`
(404), `account_name_taken` and `account_not_empty` (409), `transfer_not_editable` (409). Invalid
input keeps the existing `validation_error` (422), and the frontend form enforces the same rules
first so a user sees field-level messages.

## Backend structure

```
backend/src/tradinghub/ledger/
├── models/
│   ├── __init__.py       # imports both, so Alembic can see them
│   ├── account.py
│   └── transaction.py
├── schemas.py            # requests, responses, filters, the summary shape
├── crud.py               # every function takes user_id; the only place these tables are queried
├── services.py           # create, update, delete, transfers, the ownership checks
├── summary.py            # the aggregate queries
├── errors.py
└── routes.py
```

Layering is slice 1's: routes call services, services call `crud`. Routes stay thin adapters.
Public functions above private helpers. `tests/ledger/` mirrors it file for file. `alembic/env.py`
gains the model import, and `main.py` includes the router.

## Frontend

Three pages under `(app)`, so the layout guards them and each reads the user through
`useAuthenticatedUser()`.

| Page | Shows |
|---|---|
| `/accounts` | each account with its balance, add, rename, delete with a confirm step |
| `/transactions` | a table: date, account, kind, category, amount, note. Filters for account, kind, category, and date range. Page controls. Buttons for new transaction and new transfer |
| `/dashboard` | total balance per unit, each account's balance, this month's income and expenses, expenses by category, this week's expenses, and the five most recent transactions |

The dashboard replaces today's placeholder. The header gains links for Dashboard, Accounts, and
Transactions. The post-login redirect does not change, so no existing test moves.

```
frontend/src/features/accounts/      api.ts, hooks.ts, types.ts, components/
frontend/src/features/transactions/  api.ts, hooks.ts, types.ts, components/
```

Transactions import the account type; accounts know nothing about transactions.

**Forms** are React Hook Form with zod, carrying the same rules as the API. Amounts are entered as
a positive number with the kind chosen separately, and the sign is applied on the way out, because
typing a minus sign to record groceries is a bad way to spend an evening.

**Decimals stay strings.** The browser never does arithmetic on money. Totals arrive computed.

**Mutations invalidate, they do not patch the cache.** Any write invalidates transactions,
accounts, and the summary, because a single transaction changes a balance, a category total, and a
list position at once.

### Carried in from the slice 1 review

These waited for the first feature with lists, and this is it.

- **Query keys as a factory** for both features, so one call invalidates every list.
- **Responses are parsed with zod in `api.ts`,** not asserted with a type parameter. These rows
  carry decimals, nulls, and timestamps, where a silent mismatch shows up as `undefined` on screen.
- **These queries set their own stale time,** shorter than the global two minutes.
- **The error banner becomes a component.** It is copy-pasted three times already.
- **`noUncheckedIndexedAccess`** goes on in `tsconfig.json` before the first list is written.
- **`CONVENTIONS.md` gets its frontend section**, recording these decisions.

## Testing

**Backend**, against real Postgres in the rolled-back transaction fixture:

- ownership, for all twelve endpoints, with two users
- the composite foreign key: a transaction aimed at a stranger's account is refused by the database
- the sign convention, which nothing in the database enforces: post an expense, read the row back,
  assert the stored amount is negative. Same for income. These two tests are the whole guarantee
- the `kind` check, by writing an unknown kind past the application
- account names collide case-insensitively: "Chase" and "chase" cannot both exist for one user,
  but another user may have their own "Chase"
- balances: empty account is zero, mixed signs, per unit, unaffected by another user's rows
- transfers: both rows written, group shared, deleting any row removes the whole group, patching
  one is refused, same-account and cross-user transfers rejected
- a transfer with a fee: three rows, the balances land at -1000 and +995, and the fee shows in the
  expense total while the two transfer rows do not
- a transfer between accounts with different units, with different amounts on each side, is
  accepted and the equal-and-opposite rule does not fire. This is also how a purchase is recorded
- the summary: category grouping, date boundaries inclusive at both ends, transfers excluded from
  income and expense totals but present in balances, currencies kept apart
- list: each filter, filters combined, `total` against a page, `limit` bounds
- paging is stable when several rows share one `occurred_at`: walk every page and assert no row is
  seen twice or missed. This fails without `id` in the order
- account deletion refused while transactions exist, allowed once they are gone
- a failed create leaves no row, using the fixture that now rolls back like production

**Frontend**, Playwright against the live API:

- create an account, record income and an expense, see the balance change
- a transfer between two accounts leaves the total unchanged and both accounts moved
- the dashboard shows this month's expenses and the category breakdown
- filter transactions by account and by date range
- delete an account with transactions is refused with a readable message
- the empty state, for a user with no accounts yet

Each test must fail with its behaviour removed. Slice 1's review found tests that did not, and the
plan checks each new one the same way.

**Postman:** an Accounts folder and a Transactions folder join the existing collection.

## Out of scope

| Left out | Where it goes |
|---|---|
| Trades and P&L | Slice 3. A trade belongs to an account, which is why this slice comes first |
| Binance import, stored API keys, real exchange balances | Slice 4. One encrypted row per user, and its own spec |
| Budgets per category, and a categories table | When budgets are actually wanted. Free text carries it until then |
| Currency conversion and a single grand total | Needs a rate source and a rate date per transaction. Its own feature |
| Recurring transactions, receipts, attachments, splitting one payment across categories | Not needed to answer the three questions above |
| Charts, net worth over time, month-on-month comparisons | Slice 5, a read layer over this table |
| Editing one half of a transfer | Deliberate. Delete and record it again |
| Pruning spent session rows, the silent API URL fallback | Slice 6, with deployment |

## Done when

- a user can create accounts, record income, expenses, and transfers, and edit and delete them
- the dashboard shows total balance per unit, this month's and this week's expenses, and a
  category breakdown
- no request can read or change another user's account or transaction, proven per endpoint
- the database refuses a transaction pointed at an account that is not its owner's
- balances and totals are exact to eight places, with currencies never summed together
- the backend suite, the Playwright suite, ruff, basedpyright, tsc, eslint, and prettier all pass
- `alembic upgrade head` builds the schema from scratch and `alembic check` reports no drift
