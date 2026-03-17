.PHONY: dev prod down logs migrate build test-backend test-frontend test lint

dev:
	docker compose up -d

prod:
	docker compose -f docker-compose.yml up -d

down:
	docker compose down

logs:
	docker compose logs -f $(service)

migrate:
	docker compose exec backend uv run alembic upgrade head

build:
	docker compose build

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && pnpm test

test: test-backend test-frontend

lint:
	cd backend && uv run ruff check .
	cd frontend && pnpm lint
