#!/usr/bin/env bash
# 同時啟動後端與前端；Ctrl-C 一併結束
set -e
cd "$(dirname "$0")"
# 讓本機開發也能從專案根目錄的 .env 切換 PLC_DATA_ROOT。
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
( cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000 ) &
BACK=$!
( cd frontend && npm run dev ) &
FRONT=$!
trap "kill $BACK $FRONT 2>/dev/null" EXIT
wait
