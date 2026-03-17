#!/usr/bin/env bash
set -euo pipefail

echo "Starting dev stack..."
docker compose up -d
echo "Dev stack is running. Traefik dashboard at http://localhost:8080"
