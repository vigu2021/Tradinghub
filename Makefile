.PHONY: db api web migrate test e2e check check-api check-web

db:
	docker compose up -d db

api: db
	cd backend && uv run uvicorn tradinghub.main:create_app --factory --reload

web:
	cd frontend && npm run dev

migrate: db
	cd backend && uv run alembic upgrade head

test:
	cd backend && uv run pytest

# Needs the API running: `make api` in another shell. Playwright starts the frontend itself.
e2e:
	cd frontend && npm run e2e

check: check-api check-web

check-api:
	cd backend && uv run ruff check src tests && uv run ruff format --check src tests && uv run basedpyright src tests

check-web:
	cd frontend && npm run format:check && npm run typecheck && npm run lint
