#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

exec ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8100}" --reload
