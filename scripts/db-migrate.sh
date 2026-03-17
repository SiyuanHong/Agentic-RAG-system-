#!/usr/bin/env bash
set -euo pipefail

echo "Running database migrations..."
docker compose exec backend uv run alembic upgrade head
echo "Migrations complete."
