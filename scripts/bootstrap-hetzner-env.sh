#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$project_root/.env.hetzner"

if [[ -f "$target" ]]; then
  if ! grep -q '^PLC_DB_PASSWORD=' "$target"; then
    printf "PLC_DB_PASSWORD='%s'\n" "$(openssl rand -hex 32)" >> "$target"
  fi
  chmod 600 "$target"
  exit 0
fi

is_plc_env() {
  local candidate="$1"
  grep -q '^PLC_AUTH_USERNAME=' "$candidate" &&
    grep -q '^PLC_AUTH_PASSWORD=' "$candidate" &&
    grep -q '^PLC_AUTH_SECRET=' "$candidate"
}

ensure_database_password() {
  local candidate="$1"
  if ! grep -q '^PLC_DB_PASSWORD=' "$candidate"; then
    printf "PLC_DB_PASSWORD='%s'\n" "$(openssl rand -hex 32)" >> "$candidate"
  fi
  chmod 600 "$candidate"
}

while IFS= read -r -d '' candidate; do
  [[ "$candidate" == "$target" ]] && continue
  if is_plc_env "$candidate"; then
    install -m 600 "$candidate" "$target"
    ensure_database_password "$target"
    echo "Migrated existing PLC environment from $candidate."
    exit 0
  fi
done < <(
  find /srv /opt /home -maxdepth 8 -type f \
    \( -name '.env.hetzner' -o -name '.env.prod' -o -name '.env' \) \
    -print0 2>/dev/null
)

if command -v docker >/dev/null 2>&1; then
  while IFS= read -r container_id; do
    [[ -z "$container_id" ]] && continue
    if ! container_env="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container_id")"; then
      continue
    fi
    auth_username="$(printf '%s\n' "$container_env" | sed -n 's/^PLC_AUTH_USERNAME=//p' | head -n 1)"
    auth_password="$(printf '%s\n' "$container_env" | sed -n 's/^PLC_AUTH_PASSWORD=//p' | head -n 1)"
    auth_secret="$(printf '%s\n' "$container_env" | sed -n 's/^PLC_AUTH_SECRET=//p' | head -n 1)"

    if [[ -n "$auth_username" && -n "$auth_password" && -n "$auth_secret" ]]; then
      auth_username="${auth_username//\'/\\\'}"
      auth_password="${auth_password//\'/\\\'}"
      auth_secret="${auth_secret//\'/\\\'}"
      umask 077
      {
        printf "PLC_AUTH_USERNAME='%s'\n" "$auth_username"
        printf "PLC_AUTH_PASSWORD='%s'\n" "$auth_password"
        printf "PLC_AUTH_SECRET='%s'\n" "$auth_secret"
        printf 'PLC_INGOT_CACHE_SIZE=16\n'
        printf 'PLC_RUNTIME_ENABLED=true\n'
        printf 'PLC_SCAN_INTERVAL_SECONDS=0.2\n'
        printf 'PLC_PLANT_OPCUA_ENDPOINT=opc.tcp://plant-simulator:4840/plant-simulator/server/\n'
        printf 'PLC_PLANT_OPCUA_NAMESPACE=urn:tommy-huang:cz-plant-simulator\n'
        printf 'PLC_PLANT_API_URL=http://plant-simulator:8090\n'
        printf 'SA_KEY_PATH=/home/tommy/spc-platform/deploy/hetzner/sa-key.json\n'
      } > "$target"
      ensure_database_password "$target"
      echo "Migrated PLC authentication from the existing backend container."
      exit 0
    fi
  done < <(docker ps --quiet)
fi

echo "Missing $target and no existing PLC deployment environment was found." >&2
echo "Create it from deploy/.env.hetzner.example, then rerun the deploy job." >&2
exit 1
