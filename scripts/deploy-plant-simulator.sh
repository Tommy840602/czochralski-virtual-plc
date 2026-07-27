#!/usr/bin/env bash
set -euo pipefail

simulator_root="${1:-/srv/plant-simulator/app}"

if [[ ! -f "$simulator_root/compose.yaml" ]]; then
  echo "Missing Plant Simulator release at $simulator_root." >&2
  exit 1
fi

cd "$simulator_root"
docker compose up -d --build plant-simulator

for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8090/healthz >/dev/null; then
    echo "Plant Simulator deployment healthy."
    exit 0
  fi
  sleep 2
done

echo "Plant Simulator failed its post-deployment health check." >&2
docker compose logs --tail=100 plant-simulator >&2
exit 1
