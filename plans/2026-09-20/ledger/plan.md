# Ledger — implementation plan

Slice 2. Written from `spec.md` in this folder; read that first for the decisions and why they were
made. This file is the ordered work.

## How to use this plan

Ten tasks, each ending in something that runs and can be committed. Build them in order: every task
depends on the one before it. Mark a task done in this file when its **Verify** step passes.

The models already exist and are committed (`backend/src/tradinghub/ledger/models/`). Task 1 turns
them into real tables; nothing else is written yet.

**Every task's verify step includes `make check` and `uv run pytest`.** Those are not repeated below.

## What already exists to copy from

Slice 1 is the template, and following it is usually right:

| For | Look at |
|---|---|
| Data access taking `user_id` | `auth/crud/user.py`, `auth/crud/session.py` |
| A service raising declarative errors | `auth/services/auth.py` |
| Thin routes with `Depends` | `auth/routes.py` |
| Declarative errors | `auth/errors.py`, `core/errors.py` |
| Test fixtures, rolled back per test | `tests/conftest.py` |
| Ownership tests with two users | `tests/auth/test_login.py` |
| Frontend feature folder | `frontend/src/features/auth/` |

---

## Task 1: Migration

**Files:**
- Modify: `backend/alembic/env.py`
- Create: one revision under `backend/alembic/versions/`

**Requirements:**
1. `env.py` imports the ledger models package. The existing auth import binds the name `models`, so
   both need aliases: `from tradinghub.auth import models as auth_models` and the same shape for
   `ledger`. Without this, autogenerate sees only `users` and `sessions` and writes an empty file.
2. Generate with `--autogenerate`, then **read the result before running it**. Three things
   autogenerate gets wrong often enough to check every time:
   - `CITEXT` on `accounts.name`. It may emit plain text, or reference the type without importing
     it. The import is `from sqlalchemy.dialects import postgresql`.
   - the foreign key. It must be one `ForeignKeyConstraint` over `['account_id', 'user_id']`, not
     two separate single-column keys.
   - table order. `accounts` before `transactions` in `upgrade`, and the reverse in `downgrade`.
3. The `citext` extension is already enabled by slice 1's first migration, so nothing to add.

**Verify:**
```
uv run alembic upgrade head
uv run alembic check                                    # no new operations
uv run alembic downgrade base && uv run alembic upgrade head
```
The last line is the one that matters: it proves a fresh clone can build the schema, and catches a
downgrade that drops tables in the wrong order.

**Commit:** `Add the accounts and transactions tables`

---

## Task 2: Accounts, end to end

Five endpoints, with the ownership rule established here and reused by every task after.

**Files:**
- Create: `backend/src/tradinghub/ledger/{schemas,crud,services,errors,routes}.py`,
  `backend/tests/ledger/{test_crud,test_services,test_routes}.py`
- Modify: `backend/src/tradinghub/main.py`

**Interfaces produced:**
```python
# ledger/schemas.py
class AccountCreate(BaseModel):
    name: str                 # 1-60, trimmed
    unit: str                 # 2-10, uppercased
    type: AccountType

class AccountUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    type: AccountType | None = None

class AccountResponse(BaseModel):
    id: int
    name: str
    unit: str
    type: AccountType
    balance: Decimal          # serialised as a string

# ledger/crud.py — every function takes user_id, and this is the only module that queries
async def get_account(db: AsyncSession, user_id: int, account_id: int) -> Account | None: ...
async def list_accounts(db: AsyncSession, user_id: int) -> Sequence[Account]: ...
async def create_account(db: AsyncSession, user_id: int, data: AccountCreate) -> Account: ...
async def delete_account(db: AsyncSession, account: Account) -> None: ...
async def account_balances(db: AsyncSession, user_id: int) -> dict[int, Decimal]: ...
async def count_transactions(db: AsyncSession, user_id: int, account_id: int) -> int: ...

# ledger/errors.py
class AccountNotFoundError(AppError): ...      # 404 account_not_found
class AccountNameTakenError(AppError): ...     # 409 account_name_taken
class AccountNotEmptyError(AppError): ...      # 409 account_not_empty
```

**Requirements:**
1. **The ownership rule.** Every `crud` function takes `user_id` as a required argument and filters
   on it. A route cannot forget it because it cannot call them without it.
2. Someone else's account answers **404**, identical to one that does not exist. Never 403.
3. `name` is trimmed, `unit` uppercased, both by the schema. A duplicate name is **409**, caught
   from `IntegrityError` on the unique constraint rather than a pre-check, because a pre-check
   loses the race. Keep a pre-check only if you want the common case to avoid an exception.
4. `balance` on the response is the sum of that account's transactions, computed in SQL. Zero for an
   account with none, which means `COALESCE`, not a `None` that reaches the schema.
5. `list_accounts` returns balances in **one query for all accounts**, not one query per account.
   `account_balances` exists for exactly that.
6. Deleting an account with transactions is **409 `account_not_empty`**. The foreign key would
   cascade, and silently destroying a year of records because a name was wrong is not acceptable.
7. Changing `unit` is allowed and converts nothing. The stored amounts keep their numbers.
8. Decimals serialise as strings. A float in JSON loses precision on the way to the browser.

**Tests:**
```python
test_an_account_starts_with_a_zero_balance
test_a_balance_is_the_sum_of_its_transactions
test_balances_come_back_in_one_query_for_every_account
test_a_duplicate_name_is_rejected
test_a_name_differing_only_in_case_is_a_duplicate      # CITEXT
test_another_user_may_reuse_the_same_name
test_deleting_an_account_with_transactions_is_refused
test_deleting_an_empty_account_succeeds
test_bobs_account_is_invisible_to_alice                # for all five endpoints
```

**Verify:** the five endpoints by hand through `/docs` or Postman, with two accounts, confirming a
stranger's id gives 404 and not 403.

**Commit:** `Add account endpoints`

---

## Task 3: Transactions, end to end

**Files:**
- Modify: `backend/src/tradinghub/ledger/{schemas,crud,services,errors,routes}.py`
- Create: `backend/tests/ledger/test_transactions.py`

**Interfaces produced:**
```python
# schemas.py
class TransactionCreate(BaseModel):
    account_id: int
    amount: Decimal                  # POSITIVE; the service applies the sign
    kind: TransactionKind            # income or expense only
    category: str | None = None
    occurred_at: datetime            # must carry an offset
    note: str | None = None

class TransactionUpdate(BaseModel): ...          # every field optional
class TransactionResponse(BaseModel): ...        # amount signed, as a string
class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    total: int

class TransactionFilters(BaseModel):
    account_id: int | None = None
    kind: TransactionKind | None = None
    category: str | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    limit: int = 50                  # 1-200
    offset: int = 0

# errors.py
class TransactionNotFoundError(AppError): ...    # 404
class TransferNotEditableError(AppError): ...    # 409 transfer_not_editable
```

**Requirements:**
1. **The API takes a positive amount and a kind; the service applies the sign.** Nobody types a
   minus sign to record rent. One function owns this convention.
2. **That function is the only thing holding the sign rule up**, since you cut the check
   constraint. Its test is listed below and is not optional.
3. `POST /transactions` refuses `kind = transfer` with 422. Transfers have their own endpoint, so a
   half-transfer with no partner cannot be created by accident.
4. A transaction whose `account_id` is not the caller's answers **404**. The service checks it; the
   composite foreign key is the backstop for when that check is wrong.
5. **A transfer row cannot be patched**, answering 409 `transfer_not_editable`. Editing one side
   consistently needs rules about which fields propagate; the honest alternative is one rule,
   delete and record it again.
6. **Deleting any row of a transfer deletes the whole group**, found by `transfer_group_id`. They
   are one event.
7. **Order by `occurred_at DESC, id DESC`.** `occurred_at` alone is not a total order, since
   recording two things on one day is normal, and paging a non-deterministic order shows a row
   twice or skips one. The `id` is load-bearing, not decoration.
8. `total` counts every row matching the filters, not the page.
9. `occurred_at` without an offset is **422**, never a guess at the timezone.
10. `category` is optional, trimmed and lowercased. A purchase can be recorded before it is
    categorised.

**Tests:**
```python
test_an_expense_is_stored_negative                      # the sign rule, whole guarantee
test_income_is_stored_positive
test_posting_a_transfer_through_the_normal_endpoint_is_refused
test_a_transaction_in_a_strangers_account_is_not_found
test_patching_a_transfer_row_is_refused
test_deleting_one_row_of_a_transfer_deletes_the_group
test_paging_is_stable_when_rows_share_an_occurred_at    # fails without id in the order
test_a_naive_timestamp_is_rejected
test_each_filter_narrows_the_list
test_filters_combine
test_total_counts_every_match_not_the_page
```

The paging test is the subtle one: insert several rows with an identical `occurred_at`, walk every
page, and assert no row is seen twice or missed.

**Commit:** `Add transaction endpoints`

---

## Task 4: Transfers

**Files:**
- Modify: `backend/src/tradinghub/ledger/{schemas,services,routes}.py`
- Create: `backend/tests/ledger/test_transfers.py`

**Interfaces produced:**
```python
class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount_sent: Decimal             # positive
    amount_received: Decimal         # positive; differs when the units differ
    fee: Decimal | None = None       # positive
    fee_account_id: int | None = None
    fee_category: str | None = None
    occurred_at: datetime
    note: str | None = None
```

**Requirements:**
1. One `POST /transfers`, writing every row in **one database transaction** with a shared
   `transfer_group_id` generated in Python.
2. Both accounts must be the caller's, and they must differ. Otherwise 404 or 422.
3. **The two transfer rows are equal and opposite when the units match.** Enforce that only then.
   When the units differ the amounts legitimately differ, and enforcing it everywhere rejects the
   first exchange you record.
4. **A fee is a third row**, `kind = expense`, in the same group, against `fee_account_id`. Making
   the transfer rows uneven instead would hide the fee from every spending total, and fees are
   spending.
5. Nothing is converted and no rate is stored. The rate is one amount divided by the other.
6. **Different units on the two sides is how a purchase is recorded.** 30,000 USDT out of a cash
   account and 0.5 BTC into a holding account is a buy. Same unit on both sides is a move. Nothing
   needs a flag; the units say which it is. This is what lets a portfolio tracker land in a later
   slice without touching these tables.

**Tests:**
```python
test_a_transfer_writes_two_rows_sharing_a_group
test_the_balances_move_by_the_amount
test_a_fee_is_a_third_row_in_the_same_group             # -1000 and +995, fee in spending
test_a_transfer_is_excluded_from_the_expense_total
test_the_fee_is_included_in_the_expense_total
test_different_units_may_have_different_amounts         # a purchase
test_the_same_unit_must_be_equal_and_opposite
test_a_transfer_to_the_same_account_is_refused
test_a_transfer_into_a_strangers_account_is_not_found
```

**Commit:** `Add transfers`

---

## Task 5: Summary

The Postgres task of this slice. Everything is aggregated in SQL, not summed in Python.

**Files:**
- Create: `backend/src/tradinghub/ledger/summary.py`, `backend/tests/ledger/test_summary.py`
- Modify: `backend/src/tradinghub/ledger/{schemas,routes}.py`

**Interfaces produced:**
```python
class UnitTotal(BaseModel):
    unit: str
    amount: Decimal

class CategoryTotal(BaseModel):
    category: str | None       # None groups as "uncategorised" in the UI
    unit: str
    amount: Decimal

class SummaryResponse(BaseModel):
    accounts: list[AccountResponse]
    totals: list[UnitTotal]              # balance now, per unit
    income: list[UnitTotal]              # for the period
    expenses: list[UnitTotal]
    by_category: list[CategoryTotal]
```

**Requirements:**
1. `GET /summary?from=&to=`, both required ISO timestamps. The frontend computes "this month" and
   "this week", so the API stays a date range and a later slice can ask it anything.
2. **Transfers are excluded from income and expenses, and included in balances.** Moving your own
   money is not spending. The `kind` filter does this; no special casing.
3. **Units are never summed across each other.** Every total is per unit. Adding GBP to BTC needs
   prices and a price date, which is a later slice and its own table.
4. Date boundaries are **inclusive at both ends**, and a test pins it, because off-by-one on a
   month boundary is invisible and wrong.
5. A few aggregate queries, not one per account or per category. `GROUP BY` with `FILTER` does
   income and expenses in one pass, which is the thing worth learning here.

**Tests:**
```python
test_balances_are_grouped_per_unit
test_income_and_expenses_cover_only_the_period
test_the_period_boundaries_are_inclusive
test_transfers_are_absent_from_income_and_expenses
test_transfers_are_present_in_balances
test_categories_group_and_uncategorised_rows_come_back_as_null
test_another_users_rows_never_appear
```

**Commit:** `Add the ledger summary endpoint`

---

## Task 6: Frontend data layer

**Files:**
- Create: `frontend/src/features/accounts/{api,hooks,types}.ts`,
  `frontend/src/features/transactions/{api,hooks,types}.ts`,
  `frontend/src/components/ui/ErrorBanner.tsx`
- Modify: `frontend/tsconfig.json`, `frontend/src/features/auth/api.ts`,
  the three places the error banner is copy-pasted

**Requirements:**
1. **Query keys as a factory** in each feature: `all`, `list(filters)`, `detail(id)`. One
   invalidation then refreshes every list. Give `authKeys` the same shape while you are there.
2. **Parse responses with zod in `api.ts`**, not just a type parameter. These rows carry decimals,
   nulls and timestamps, and a silent mismatch shows up as `undefined` on screen rather than an
   error at the boundary.
3. Decimals stay **strings** the whole way through. The browser never does arithmetic on money.
4. **Mutations invalidate, they do not patch the cache.** One transaction changes a balance, a
   category total and a list position at once, so working out which cached pages to edit is more
   code than refetching.
5. These queries set their own `staleTime`, shorter than the global two minutes.
6. `noUncheckedIndexedAccess` goes on in `tsconfig.json` **before the first list is written**.
   Turning it on later means fixing every array access at once.
7. Extract the error banner. It is copy-pasted three times already and would be five.

**Verify:** `npm run typecheck`, `npm run lint`, `npm run format:check`.

**Commit:** `Add the ledger data layer`

---

## Task 7: Accounts page

**Files:**
- Create: `frontend/src/app/(app)/accounts/page.tsx`,
  `frontend/src/features/accounts/components/{AccountForm,AccountList}.tsx`
- Modify: `frontend/src/app/(app)/layout.tsx`

**Requirements:**
1. Under `(app)`, so the layout guards it and the page reads the user through
   `useAuthenticatedUser()`. No session checks in the page.
2. Each account with its balance and unit. Add, rename, and delete with a confirm step.
3. **A refused delete shows the readable reason**, not a generic failure. That is what
   `account_not_empty` exists for.
4. An empty state for a user with no accounts, since that is everyone on their first visit.
5. The header gains links for Dashboard, Accounts and Transactions.
6. Follow the existing visual language: the tokens already in `globals.css`, and the `Button` and
   `Field` primitives. No new colours and no new libraries.

**Commit:** `Add the accounts page`

---

## Task 8: Transactions page

**Files:**
- Create: `frontend/src/app/(app)/transactions/page.tsx`,
  `frontend/src/features/transactions/components/{TransactionForm,TransactionTable,TransactionFilters,TransferForm}.tsx`

**Requirements:**
1. A table: date, account, kind, category, amount, note. Filters for account, kind, category and a
   date range. Page controls.
2. **The amount field is a positive number with a kind toggle.** The sign is the API's job. Typing
   a minus sign to record groceries is a bad evening.
3. Separate buttons for a transaction and a transfer, because the transfer form has two accounts
   and an optional fee.
4. The transfer form **warns when the two units differ**, since that is usually a mistake and
   occasionally a purchase.
5. A transfer row is not editable. Show that in the UI rather than letting the 409 surface as a
   surprise.
6. Categories offer the ones already used, from the transactions the page already has. No new
   endpoint for it.

**Commit:** `Add the transactions page`

---

## Task 9: Dashboard

**Files:**
- Modify: `frontend/src/app/(app)/dashboard/page.tsx`
- Create: `frontend/src/features/transactions/components/SummaryTiles.tsx`

**Requirements:**
1. Replace the placeholder. Total balance per unit, each account's balance, this month's income and
   expenses, expenses by category, this week's expenses, and the five most recent transactions.
2. **The frontend computes the date ranges** and passes them to `/summary`. The API knows nothing
   about "this month".
3. Each total is labelled with its unit. A number with no unit is a lie once you hold two.
4. Uncategorised rows are shown as "uncategorised", not hidden.
5. No charts. Those are a later slice, and this is the data they will read.

**Commit:** `Replace the dashboard placeholder with the ledger summary`

---

## Task 10: End-to-end tests and the loose ends

**Files:**
- Create: `frontend/e2e/ledger.spec.ts`
- Create: `backend/postman/tradinghub.postman_collection.json`
- Modify: `CONVENTIONS.md`

**Tests:**
```
create an account, record income and an expense, and the balance follows
a transfer leaves the total unchanged and moves both accounts
a transfer with a fee shows the fee in spending but not the transfer
the dashboard shows this month's expenses and the category breakdown
filtering transactions by account and by date range
deleting an account with transactions is refused with a readable message
the empty state for a user with no accounts
```

**Requirements:**
1. **Every test must fail with its behaviour removed.** Slice 1's review found three that did not.
   Check each one by breaking the code on purpose, then putting it back.
2. A Postman collection, with `{{base_url}}` as a collection variable so it points anywhere. One
   folder for Auth and one each for Accounts and Transactions. A collection was written during
   slice 1, verified with newman, and then lost before it was committed, so this writes it fresh.
   Auth is cookie-based, so Postman's cookie jar carries the session and there is no token to copy.
3. `CONVENTIONS.md` gains its frontend section. It still says frontend conventions are not written,
   and there is now a frontend to write them against: the query key factory, where zod schemas
   live, response parsing, and error branching.

**Verify:** `make check`, `uv run pytest`, `npm run e2e`, and `alembic downgrade base && alembic
upgrade head` one final time.

**Commit:** `Add ledger end-to-end tests`

---

## Definition of done

- [ ] a user can create accounts, record income, expenses and transfers, and edit and delete them
- [ ] the dashboard shows total balance per unit, this month's and this week's expenses, and a
      category breakdown
- [ ] no request can read or change another user's account or transaction, proven per endpoint
- [ ] the database refuses a transaction pointed at an account that is not its owner's
- [ ] an expense stores negative and income stores positive, proven by test, since nothing in the
      database enforces it
- [ ] paging is stable when rows share an `occurred_at`
- [ ] totals are exact to eighteen decimals, with units never summed together
- [ ] `alembic upgrade head` builds the schema from nothing and `alembic check` reports no drift
- [ ] the backend suite, the Playwright suite, ruff, basedpyright, tsc, eslint and prettier all pass

## Deliberately not in this slice

Carried from the spec, so the plan does not quietly grow:

| Left out | Where it goes |
|---|---|
| Prices, valuation, net worth in one currency | A later slice. One new table and a column on `users`, no change to these two tables |
| Trades, P&L, entry and exit | Slice 3, which hangs off `accounts` |
| Binance import and stored API keys | Slice 4 |
| Budgets, a categories table, recurring transactions, receipts | When actually wanted |
| Charts, net worth over time, month-on-month | Slice 5, a read layer over this table |
| Editing one half of a transfer | Deliberate. Delete and record it again |
