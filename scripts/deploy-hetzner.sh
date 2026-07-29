#!/usr/bin/env bash
set -euo pipefail

release_sha="${1:-manual}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

env_file="${PLC_DEPLOY_ENV_FILE:-.env.hetzner}"
frontend_root="/var/www/plc-frontend"

if [[ ! -f "$env_file" ]]; then
  echo "Missing deployment environment file: $project_root/$env_file" >&2
  exit 1
fi

if ! docker network inspect cz-industrial >/dev/null 2>&1; then
  echo "Missing Docker network cz-industrial; deploy Plant Simulator first." >&2
  exit 1
fi

run_as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo -n "$@"
  fi
}

run_as_root bash scripts/configure-nginx-cache.sh

compose=(
  docker compose
  --env-file "$env_file"
  -f docker-compose.hetzner.yml
)

"${compose[@]}" --profile frontend-artifact build backend frontend
"${compose[@]}" up -d postgres
"${compose[@]}" up -d backend

artifact_container="$(docker create plc-frontend:deploy)"
staging_dir="$(mktemp -d)"

cleanup() {
  docker rm -f "$artifact_container" >/dev/null 2>&1 || true
  rm -rf "$staging_dir"
}
trap cleanup EXIT

docker cp "$artifact_container:/usr/share/nginx/html/." "$staging_dir/"
run_as_root install -d -m 755 "$frontend_root"

# 不刪除舊 hash assets；先複製新 assets，最後才更新 index.html，避免短暫 404。
if [[ -d "$staging_dir/assets" ]]; then
  run_as_root install -d -m 755 "$frontend_root/assets"
  run_as_root cp -a "$staging_dir/assets/." "$frontend_root/assets/"
fi
while IFS= read -r -d '' file; do
  run_as_root cp -a "$file" "$frontend_root/"
done < <(find "$staging_dir" -mindepth 1 -maxdepth 1 ! -name assets ! -name index.html -print0)
run_as_root cp -a "$staging_dir/index.html" "$frontend_root/index.html"

for attempt in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/api/livez >/dev/null; then
    echo "PLC deployment healthy: $release_sha"
    exit 0
  fi
  sleep 2
done

echo "PLC backend failed its post-deployment liveness check." >&2
"${compose[@]}" logs --tail=100 backend >&2
exit 1
