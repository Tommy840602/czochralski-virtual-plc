#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "configure-nginx-cache.sh must run as root" >&2
  exit 1
fi

site_config="${PLC_NGINX_SITE_CONFIG:-/etc/nginx/sites-available/plc.conf}"
if [[ ! -f "$site_config" && -f /etc/nginx/sites-enabled/plc.conf ]]; then
  site_config="/etc/nginx/sites-enabled/plc.conf"
fi
if [[ ! -f "$site_config" ]]; then
  echo "PLC nginx site config not found: $site_config" >&2
  exit 1
fi

resolved_config="$(readlink -f "$site_config")"
staged_config="$(mktemp)"
backup_config="${resolved_config}.pre-cache-policy"
dcs_allowed_ip="${PLC_DCS_ALLOWED_IP:-178.104.225.148}"

if [[ ! "$dcs_allowed_ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "PLC_DCS_ALLOWED_IP must be an IPv4 address" >&2
  exit 1
fi

cleanup() {
  rm -f "$staged_config"
}
trap cleanup EXIT

awk -v dcs_allowed_ip="$dcs_allowed_ip" '
  /^[[:space:]]*# BEGIN PLC DCS BRIDGE/ {
    skipping = 1
    next
  }
  /^[[:space:]]*# END PLC DCS BRIDGE/ {
    skipping = 0
    next
  }
  /^[[:space:]]*# BEGIN PLC CACHE POLICY/ {
    skipping = 1
    next
  }
  /^[[:space:]]*# END PLC CACHE POLICY/ {
    skipping = 0
    next
  }
  skipping {
    next
  }
  !inserted && /^[[:space:]]*location \/ \{/ {
    print "    # BEGIN PLC DCS BRIDGE"
    print "    # Read-only telemetry bridge restricted to the DCS production VM."
    print "    location = /api/integration/dcs/v1/snapshot {"
    print "        allow " dcs_allowed_ip ";"
    print "        deny all;"
    print "        proxy_pass http://127.0.0.1:8000/internal/dcs/v1/snapshot;"
    print "        proxy_http_version 1.1;"
    print "        proxy_set_header Host $host;"
    print "        proxy_set_header X-Real-IP $remote_addr;"
    print "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
    print "        proxy_set_header X-Forwarded-Proto $scheme;"
    print "        proxy_read_timeout 10s;"
    print "    }"
    print "    # END PLC DCS BRIDGE"
    print ""
    print "    # BEGIN PLC CACHE POLICY"
    print "    # index.html 每次重新驗證；hashed assets 可長期快取。"
    print "    location = /index.html {"
    print "        expires -1;"
    print "        try_files /index.html =404;"
    print "    }"
    print ""
    print "    location /assets/ {"
    print "        expires 1y;"
    print "        try_files $uri =404;"
    print "    }"
    print "    # END PLC CACHE POLICY"
    print ""
    inserted = 1
  }
  {
    print
  }
  END {
    if (!inserted) {
      exit 42
    }
  }
' "$resolved_config" > "$staged_config" || {
  echo "Unable to locate PLC SPA location in $resolved_config" >&2
  exit 1
}

if cmp -s "$resolved_config" "$staged_config"; then
  echo "PLC nginx cache policy already current."
  exit 0
fi

cp -a "$resolved_config" "$backup_config"
install -m 644 "$staged_config" "$resolved_config"
if ! nginx -t; then
  cp -a "$backup_config" "$resolved_config"
  nginx -t
  echo "Invalid nginx cache policy; restored $backup_config" >&2
  exit 1
fi

systemctl reload nginx
echo "PLC nginx cache policy and DCS bridge installed."
