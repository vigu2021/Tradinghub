.PHONY: db api web migrate test check

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

check:
	cd backend && uv run ruff check src tests && uv run ruff format --check src tests && uv run basedpyright src tests
