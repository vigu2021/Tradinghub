# Tradinghub

Multi-user trading journal. Built in ordered slices, primarily to learn FastAPI, Next.js, Postgres,
and Terraform on AWS in depth.

## Planning documents

All specs and plans live under `plans/`, nested by date then feature:

```
plans/
└── 2026-08-08/
    └── auth-skeleton/
        ├── spec.md    # what we're building and why
        └── plan.md    # the implementation plan: ordered steps
```

Planning material goes here and nowhere else. Do not create a `docs/` directory for it.

## Code conventions

See `CONVENTIONS.md`.

## Who writes the code

Implementation is written by hand, not by Claude. Claude designs, plans, explains, and reviews.
Write implementation code only when explicitly handed a specific piece, and only that piece.

## Commits

Scan the staged diff for secrets before every commit. Commit messages are one line, plain, with no
tooling attribution of any kind.

Committing directly to `main` is fine here — solo project, nothing deployed. Revisit if
collaborators or a deployed environment appear.

## Slice order

1. Auth + skeleton — hand-rolled sessions, no email or OAuth
2. Ledger — accounts, transactions, balances, spending by period
3. Net worth — prices, a reporting unit, one estimated total
4. Binance import — read-only API keys, fills recorded automatically
5. Spot — cost basis, realised gains, holdings valued
6. Trades — futures: positions, margin, funding
7. Charting + dashboard
8. Terraform on AWS

The order has been revised twice, both times for the same reason: each slice has to sit on data
the one before it already stores.

- **Ledger before trades.** A trade belongs to an account, so building trades first would mean
  adding `account_id` later as a migration and a backfill.
- **Net worth before the Binance import.** Showing a total in one currency needs prices, and
  Binance's price endpoint is public market data with no API key. So the thing most worth seeing
  arrives without the credential storage and encryption the authenticated import requires.
- **Spot after the import.** Recording a spot buy already works in slice 2: it is a transfer whose
  two sides have different units. What spot adds is interpretation, cost basis and realised gain,
  and that is far less tedious once fills import themselves.
- **Futures separate from spot.** A futures position is not a holding. You own nothing; you have
  margin behind an obligation, with funding charged over time. It needs its own table.

Each slice gets its own `plans/` folder containing a `spec.md` and a `plan.md`, both written and
approved before any code.
