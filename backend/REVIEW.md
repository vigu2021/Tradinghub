# Backend review

Follow the rules in `../REVIEW.md`. This file lists what to check on this side.

Run from `backend/`: `uv run pytest -q`, `uv run ruff check src tests`,
`uv run basedpyright src tests`.

- **Ownership:** every query that reads or writes a user's rows filters on that user. `user_id` only
  ever comes from the signed cookie.
- **Money:** amounts stay `Decimal` and keep every digit from request to database to response. Signs
  match the stored convention: out is negative.
- **Transactions:** one request is one transaction. A failure leaves nothing half written, and a
  success is not reported before the commit.
- **Input:** anything a schema accepts must also be accepted by Postgres, so bad input is a 4xx.
- **Errors:** every error uses the `{"error": ...}` shape and never echoes secrets or input.
- **Auth:** refresh rotation, reuse revocation, logout and their concurrency.
- **Migrations:** they match the models, and each downgrade works.
- **Tests:** each one fails if its behaviour is removed, and reads from the database when the claim
  is about storage.
