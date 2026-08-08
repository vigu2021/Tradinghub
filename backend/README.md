# Tradinghub backend

FastAPI + async SQLAlchemy over Postgres. See `../CONVENTIONS.md` for code standards and
`../plans/` for the current spec and implementation plan.

## Running locally

```bash
docker compose up -d          # from the repo root: Postgres 16
cp .env.example .env
uv run uvicorn tradinghub.main:create_app --factory --reload
```

## Checks

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run basedpyright
```
