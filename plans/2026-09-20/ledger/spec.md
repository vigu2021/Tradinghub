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
| Accounts | A table. Named pots, each with one currency | "Total balance" is meaningless without knowing what is on the exchange versus in the bank. Adding it later would mean a migration on every transaction |
| `kind` on a transaction | `income`, `expense`, `transfer` | Without it, expenses would have to mean "negative amounts", which counts moving money to an exchange as money spent. It is not |
| Transfers | Two linked rows sharing a group id, written by one endpoint | A transfer is two movements. Linking them means deleting one cannot orphan the other |
| Categories | Free text, normalised, offered from ones already used | One table instead of two. Renaming becomes an `UPDATE`, which is rare. A table earns its place when budgets per category arrive |
| Multi-currency | Balances are reported per currency and never summed across them | Adding USD to GBP needs exchange rates, a rate source, and a date for each rate. That is its own feature, not a column |
| Money | `NUMERIC(20, 8)` in Postgres, `Decimal` in Python, strings in JSON and in the browser | A float cannot represent 0.1, and this is money |
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
| `name` | text | not null, 1 to 60 characters, trimmed |
| `currency` | text | not null, 3 to 5 characters, uppercase |
| `created_at` | timestamptz | not null, set by the database |
| `updated_at` | timestamptz | not null, set by the database on every update |

- `UNIQUE (user_id, name)`: two accounts called Binance would be indistinguishable in a picker.
- `UNIQUE (id, user_id)`: redundant on its own, and the target of the composite foreign key above.

### `transactions`

| Column | Type | Rule |
|---|---|---|
| `id` | integer | primary key |
| `user_id` | integer | foreign key to `users.id`, `ON DELETE CASCADE`, not null |
| `account_id` | integer | not null; with `user_id`, a composite foreign key to `accounts` |
| `amount` | numeric(20, 8) | not null, never zero. Positive is money in, negative is money out |
| `kind` | text | not null, `income`, `expense`, or `transfer` |
| `category` | text | nullable, 1 to 40 characters, lowercase. Null on transfers |
| `occurred_at` | timestamptz | not null, when it happened rather than when it was typed |
| `note` | text | nullable, at most 1,000 characters |
| `transfer_group` | uuid | null unless this row is half of a transfer |
| `created_at` | timestamptz | not null, set by the database |
| `updated_at` | timestamptz | not null, set by the database on every update |

**Check constraints**, named through the existing convention so Alembic can alter them:

- `kind` is one of the three values. A check rather than a Postgres enum type, because adding a
  value to an enum is a migration with sharp edges and a check is one line.
- the sign matches the kind: income is positive, expense is negative, a transfer is either.
  This is what makes "sum of expenses" reliably negative without the application policing it.
- `amount` is never zero.
- `transfer_group` is set exactly when `kind` is `transfer`.
- `category` is set exactly when `kind` is not `transfer`. A transfer between your own accounts is
  not spending, so it has nothing to categorise.

**Two indexes:** `(user_id, occurred_at DESC)` for the list, and `(user_id, account_id)` for
per-account balances. Nothing on `category`: it is filtered inside one user's rows, which the
first index already narrows to a few thousand. Add an index when a query plan asks for one.

In Python, `kind` is a `StrEnum` and amounts are `Mapped[Decimal]`.

## API

All twelve require a session through the existing `get_current_user` dependency.

### Accounts

| Method and path | Does | Success | Failures |
|---|---|---|---|
| `POST /accounts` | create | 201 | 409 `account_name_taken`, 422 |
| `GET /accounts` | list own accounts with each balance, name ascending | 200 | |
| `GET /accounts/{id}` | one account with its balance | 200 | 404 |
| `PATCH /accounts/{id}` | rename, or change currency | 200 | 404, 409, 422 |
| `DELETE /accounts/{id}` | remove | 204 | 404, 409 `account_not_empty` |

**Deleting an account with transactions is refused.** The foreign key could cascade, but silently
destroying a year of records because a name was wrong is not a thing this app should do. Move or
delete the transactions first.

**Changing an account's currency is allowed but does not convert anything.** The amounts already
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

The body is the source account, the destination account, a positive amount, when it happened, and
an optional note. It writes two rows in one transaction, sharing a new `transfer_group`.

**Both accounts must be yours, and they must differ.** They may have different currencies, and
nothing is converted: the same number leaves one and arrives in the other. The UI warns when the
currencies differ, because that is usually a mistake.

### Summary

| Method and path | Does | Success |
|---|---|---|
| `GET /summary?from=&to=` | balances now, plus totals for the period | 200 |

`from` and `to` are required ISO timestamps. The frontend computes this week and this month, so
the API stays a date range rather than a set of named periods, and slice 4 can ask it anything.

The response carries: each account with its balance, totals per currency, and for the period the
income total, the expense total, and expenses grouped by category, each per currency. Transfers are
excluded from the income and expense totals and included in balances.

**All of it is computed in SQL**, in a small number of aggregate queries rather than by summing in
Python. Grouping and filtering aggregates in one pass is the Postgres lesson of this slice.

### Input rules

- `name`: trimmed, 1 to 60 characters.
- `currency`: uppercased, 3 to 5 letters.
- `category`: trimmed, lowercased, 1 to 40 characters. Required for income and expense, absent for transfers.
- `amount`: at most 20 digits, 8 after the point, never zero. Accepted as a string or a number, returned as a string.
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
| `/dashboard` | total balance per currency, each account's balance, this month's income and expenses, expenses by category, this week's expenses, and the five most recent transactions |

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
- the check constraints, by writing bad rows past the application: a positive expense, a zero
  amount, a transfer with no group, an unknown kind
- balances: empty account is zero, mixed signs, per currency, unaffected by another user's rows
- transfers: both rows written, group shared, deleting either removes both, patching one is refused,
  same-account and cross-user transfers rejected
- the summary: category grouping, date boundaries inclusive at both ends, transfers excluded from
  income and expense totals but present in balances, currencies kept apart
- list: ordering, each filter, filters combined, `total` against a page, `limit` bounds
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
- the dashboard shows total balance per currency, this month's and this week's expenses, and a
  category breakdown
- no request can read or change another user's account or transaction, proven per endpoint
- the database refuses a transaction pointed at an account that is not its owner's
- balances and totals are exact to eight places, with currencies never summed together
- the backend suite, the Playwright suite, ruff, basedpyright, tsc, eslint, and prettier all pass
- `alembic upgrade head` builds the schema from scratch and `alembic check` reports no drift
