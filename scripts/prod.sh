#!/usr/bin/env bash
set -euo pipefail

echo "Starting production stack (no dev overrides)..."
docker compose -f docker-compose.yml up -d
echo "Production stack is running."
